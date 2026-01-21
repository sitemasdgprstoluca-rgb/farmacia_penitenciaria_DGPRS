"""
ISS-004 FIX (audit20): Servicio transaccional para transferencias de inventario.

Este servicio garantiza atomicidad al transferir stock entre centros:
1. Valida stock disponible en centro origen
2. Bloquea lotes con select_for_update() para evitar race conditions
3. Ejecuta movimiento de salida en origen
4. Ejecuta movimiento de entrada en destino (o crea lote espejo)
5. Registra auditoría

USO:
    from inventario.services.transfer_service import TransferService
    
    resultado = TransferService.ejecutar_transferencia(
        lote_origen=lote,
        cantidad=100,
        centro_destino=centro,
        usuario=request.user,
        motivo="Abastecimiento mensual"
    )
"""
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.core.exceptions import ValidationError
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class TransferenciaResultado:
    """Resultado de una operación de transferencia."""
    exitoso: bool
    mensaje: str
    movimiento_salida_id: Optional[int] = None
    movimiento_entrada_id: Optional[int] = None
    lote_destino_id: Optional[int] = None
    cantidad_transferida: int = 0
    errores: List[str] = None
    
    def __post_init__(self):
        if self.errores is None:
            self.errores = []


class TransferService:
    """
    ISS-004 FIX (audit20): Servicio para transferencias atómicas de inventario.
    
    Garantiza:
    - Atomicidad: Todo o nada
    - Bloqueo optimista: select_for_update() en lotes
    - Validación de stock por centro
    - Trazabilidad completa
    """
    
    @staticmethod
    @transaction.atomic
    def ejecutar_transferencia(
        lote_origen,
        cantidad: int,
        centro_destino,
        usuario,
        motivo: str = None,
        referencia: str = None,
        crear_lote_destino: bool = True,
    ) -> TransferenciaResultado:
        """
        Ejecuta una transferencia atómica de inventario.
        
        Args:
            lote_origen: Lote de donde sale el stock
            cantidad: Cantidad a transferir
            centro_destino: Centro que recibe el stock
            usuario: Usuario que ejecuta la operación
            motivo: Motivo de la transferencia
            referencia: Referencia externa (ej: número de remisión)
            crear_lote_destino: Si True, crea lote espejo en destino si no existe
            
        Returns:
            TransferenciaResultado con detalles de la operación
        """
        from core.models import Lote, Movimiento, Centro
        
        errores = []
        
        # 1. Validaciones básicas
        if cantidad <= 0:
            return TransferenciaResultado(
                exitoso=False,
                mensaje="La cantidad debe ser mayor a 0",
                errores=["cantidad <= 0"]
            )
        
        if not lote_origen:
            return TransferenciaResultado(
                exitoso=False,
                mensaje="Debe especificar un lote de origen",
                errores=["lote_origen es None"]
            )
        
        if not centro_destino:
            return TransferenciaResultado(
                exitoso=False,
                mensaje="Debe especificar un centro de destino",
                errores=["centro_destino es None"]
            )
        
        # 2. Bloquear lote origen con select_for_update
        try:
            lote_bloqueado = Lote.objects.select_for_update(nowait=False).get(pk=lote_origen.pk)
        except Lote.DoesNotExist:
            return TransferenciaResultado(
                exitoso=False,
                mensaje=f"El lote {lote_origen.pk} ya no existe",
                errores=["lote no encontrado"]
            )
        
        # 3. Re-validar después del bloqueo (pudo cambiar)
        centro_origen = lote_bloqueado.centro
        
        if centro_origen and centro_origen.id == centro_destino.id:
            return TransferenciaResultado(
                exitoso=False,
                mensaje="El centro origen y destino son el mismo",
                errores=["centro_origen == centro_destino"]
            )
        
        if not lote_bloqueado.activo:
            return TransferenciaResultado(
                exitoso=False,
                mensaje=f"El lote {lote_bloqueado.numero_lote} está inactivo",
                errores=["lote inactivo"]
            )
        
        if lote_bloqueado.cantidad_actual < cantidad:
            return TransferenciaResultado(
                exitoso=False,
                mensaje=(
                    f"Stock insuficiente. Disponible: {lote_bloqueado.cantidad_actual}, "
                    f"Solicitado: {cantidad}"
                ),
                errores=["stock insuficiente"]
            )
        
        # 4. Buscar o crear lote destino
        lote_destino = None
        if crear_lote_destino:
            # Buscar lote espejo (mismo numero_lote + producto en centro destino)
            lote_destino = Lote.objects.filter(
                numero_lote=lote_bloqueado.numero_lote,
                producto=lote_bloqueado.producto,
                centro=centro_destino,
                activo=True,
            ).first()
            
            if not lote_destino:
                # Crear lote espejo
                lote_destino = Lote.objects.create(
                    numero_lote=lote_bloqueado.numero_lote,
                    producto=lote_bloqueado.producto,
                    cantidad_inicial=0,
                    cantidad_actual=0,
                    fecha_fabricacion=lote_bloqueado.fecha_fabricacion,
                    fecha_caducidad=lote_bloqueado.fecha_caducidad,
                    precio_unitario=lote_bloqueado.precio_unitario,
                    numero_contrato=lote_bloqueado.numero_contrato,
                    marca=lote_bloqueado.marca,
                    centro=centro_destino,
                    activo=True,
                )
                logger.info(
                    f"ISS-004: Creado lote espejo {lote_destino.id} en centro {centro_destino.id} "
                    f"para transferencia desde lote {lote_bloqueado.id}"
                )
            
            # Bloquear lote destino también
            lote_destino = Lote.objects.select_for_update().get(pk=lote_destino.pk)
        
        # 5. Ejecutar movimiento de SALIDA en origen
        motivo_salida = motivo or f"Transferencia a {centro_destino.nombre}"
        
        movimiento_salida = Movimiento(
            tipo='transferencia',
            producto=lote_bloqueado.producto,
            lote=lote_bloqueado,
            cantidad=cantidad,
            centro_origen=centro_origen,
            centro_destino=centro_destino,
            usuario=usuario,
            motivo=motivo_salida,
            referencia=referencia,
        )
        movimiento_salida.save(skip_validation=True)  # Ya validamos arriba
        
        # 6. Decrementar stock en lote origen
        lote_bloqueado.cantidad_actual = F('cantidad_actual') - cantidad
        lote_bloqueado.save(update_fields=['cantidad_actual', 'updated_at'], skip_validation=True)
        lote_bloqueado.refresh_from_db()
        
        # 7. Ejecutar movimiento de ENTRADA en destino
        movimiento_entrada = None
        if lote_destino:
            motivo_entrada = motivo or f"Transferencia desde {centro_origen.nombre if centro_origen else 'Farmacia Central'}"
            
            movimiento_entrada = Movimiento(
                tipo='entrada',
                producto=lote_destino.producto,
                lote=lote_destino,
                cantidad=cantidad,
                centro_origen=centro_origen,
                centro_destino=centro_destino,
                usuario=usuario,
                motivo=motivo_entrada,
                referencia=referencia,
            )
            movimiento_entrada.save(skip_validation=True)
            
            # Incrementar stock en lote destino
            lote_destino.cantidad_actual = F('cantidad_actual') + cantidad
            lote_destino.save(update_fields=['cantidad_actual', 'updated_at'], skip_validation=True)
            lote_destino.refresh_from_db()
        
        # 8. Log de auditoría
        logger.info(
            f"ISS-004: Transferencia exitosa. "
            f"Lote {lote_bloqueado.numero_lote}: {cantidad} unidades. "
            f"Origen: {centro_origen.nombre if centro_origen else 'Farmacia Central'} -> "
            f"Destino: {centro_destino.nombre}. "
            f"Usuario: {usuario.username if usuario else 'N/A'}"
        )
        
        return TransferenciaResultado(
            exitoso=True,
            mensaje=f"Transferencia de {cantidad} unidades completada exitosamente",
            movimiento_salida_id=movimiento_salida.id,
            movimiento_entrada_id=movimiento_entrada.id if movimiento_entrada else None,
            lote_destino_id=lote_destino.id if lote_destino else None,
            cantidad_transferida=cantidad,
        )
    
    @staticmethod
    @transaction.atomic
    def ejecutar_transferencia_multiple(
        items: List[Dict[str, Any]],
        centro_destino,
        usuario,
        motivo: str = None,
        referencia: str = None,
    ) -> List[TransferenciaResultado]:
        """
        Ejecuta múltiples transferencias en una sola transacción atómica.
        
        Args:
            items: Lista de {'lote': Lote, 'cantidad': int}
            centro_destino: Centro destino común
            usuario: Usuario que ejecuta
            motivo: Motivo común
            referencia: Referencia común
            
        Returns:
            Lista de TransferenciaResultado
            
        Raises:
            ValidationError si alguna transferencia falla (rollback total)
        """
        resultados = []
        errores_globales = []
        
        for idx, item in enumerate(items):
            lote = item.get('lote')
            cantidad = item.get('cantidad', 0)
            
            resultado = TransferService.ejecutar_transferencia(
                lote_origen=lote,
                cantidad=cantidad,
                centro_destino=centro_destino,
                usuario=usuario,
                motivo=motivo,
                referencia=referencia,
            )
            
            resultados.append(resultado)
            
            if not resultado.exitoso:
                errores_globales.append(
                    f"Item {idx + 1} (Lote {lote.numero_lote if lote else 'N/A'}): {resultado.mensaje}"
                )
        
        # Si hubo errores, hacer rollback total
        if errores_globales:
            raise ValidationError({
                'transferencia': errores_globales
            })
        
        return resultados
