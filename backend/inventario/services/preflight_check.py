"""
ISS-005: Preflight check de stock.

Sistema de verificación previa de stock antes de operaciones críticas.
Permite detectar problemas de inventario antes de ejecutar transacciones.
"""
import logging
from datetime import date, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

from django.db import connection
from django.db.models import Sum, Q, F, Count
from django.utils import timezone

logger = logging.getLogger(__name__)


class NivelAlerta(Enum):
    """Niveles de alerta para preflight check."""
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class PreflightItem:
    """Resultado de verificación de un item individual."""
    producto_clave: str
    producto_descripcion: str
    cantidad_requerida: int
    cantidad_disponible: int
    nivel: NivelAlerta
    mensaje: str
    detalles: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def es_valido(self) -> bool:
        return self.nivel in (NivelAlerta.OK, NivelAlerta.WARNING)
    
    @property
    def deficit(self) -> int:
        return max(0, self.cantidad_requerida - self.cantidad_disponible)


@dataclass
class PreflightResult:
    """Resultado completo del preflight check."""
    puede_proceder: bool
    nivel_general: NivelAlerta
    items: List[PreflightItem]
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    tiempo_verificacion_ms: float = 0.0
    
    @property
    def resumen(self) -> Dict[str, Any]:
        return {
            'puede_proceder': self.puede_proceder,
            'nivel': self.nivel_general.value,
            'total_items': len(self.items),
            'items_ok': sum(1 for i in self.items if i.nivel == NivelAlerta.OK),
            'items_warning': sum(1 for i in self.items if i.nivel == NivelAlerta.WARNING),
            'items_error': sum(1 for i in self.items if i.nivel == NivelAlerta.ERROR),
            'items_critical': sum(1 for i in self.items if i.nivel == NivelAlerta.CRITICAL),
            'warnings': self.warnings,
            'errors': self.errors,
            'tiempo_ms': self.tiempo_verificacion_ms,
        }


class PreflightStockCheck:
    """
    ISS-005: Servicio de verificación previa de stock.
    
    Realiza verificaciones antes de:
    - Enviar requisiciones
    - Surtir requisiciones
    - Realizar movimientos de salida
    - Transferencias entre centros
    """
    
    def __init__(self, centro=None, usuario=None):
        """
        Args:
            centro: Centro para verificar (None = farmacia central)
            usuario: Usuario que realiza la operación
        """
        self.centro = centro
        self.usuario = usuario
    
    def verificar_requisicion(self, requisicion) -> PreflightResult:
        """
        ISS-005: Verifica stock antes de enviar/surtir una requisición.
        
        Args:
            requisicion: Instancia de Requisicion con detalles
            
        Returns:
            PreflightResult con el análisis completo
        """
        import time
        from core.models import Lote, DetalleRequisicion
        
        inicio = time.time()
        items = []
        warnings = []
        errors = []
        
        # Obtener detalles de la requisición
        detalles = DetalleRequisicion.objects.filter(
            requisicion=requisicion
        ).select_related('producto')
        
        if not detalles.exists():
            return PreflightResult(
                puede_proceder=False,
                nivel_general=NivelAlerta.ERROR,
                items=[],
                errors=["La requisición no tiene productos"],
                tiempo_verificacion_ms=(time.time() - inicio) * 1000
            )
        
        for detalle in detalles:
            item = self._verificar_producto(
                producto=detalle.producto,
                cantidad_requerida=detalle.cantidad_solicitada
            )
            items.append(item)
            
            # Agregar warnings específicos
            if item.nivel == NivelAlerta.WARNING:
                warnings.append(item.mensaje)
            elif item.nivel in (NivelAlerta.ERROR, NivelAlerta.CRITICAL):
                errors.append(item.mensaje)
        
        # Determinar nivel general
        niveles = [i.nivel for i in items]
        if NivelAlerta.CRITICAL in niveles:
            nivel_general = NivelAlerta.CRITICAL
            puede_proceder = False
        elif NivelAlerta.ERROR in niveles:
            nivel_general = NivelAlerta.ERROR
            puede_proceder = False
        elif NivelAlerta.WARNING in niveles:
            nivel_general = NivelAlerta.WARNING
            puede_proceder = True  # Puede proceder con advertencias
        else:
            nivel_general = NivelAlerta.OK
            puede_proceder = True
        
        tiempo_ms = (time.time() - inicio) * 1000
        
        logger.info(
            f"ISS-005: Preflight check requisición {requisicion.folio}: "
            f"{nivel_general.value} en {tiempo_ms:.2f}ms"
        )
        
        return PreflightResult(
            puede_proceder=puede_proceder,
            nivel_general=nivel_general,
            items=items,
            warnings=warnings,
            errors=errors,
            tiempo_verificacion_ms=tiempo_ms
        )
    
    def verificar_movimiento_salida(
        self,
        lote,
        cantidad: int
    ) -> PreflightResult:
        """
        ISS-005: Verifica stock antes de un movimiento de salida.
        
        Args:
            lote: Lote del cual se extraerá
            cantidad: Cantidad a extraer
            
        Returns:
            PreflightResult
        """
        import time
        inicio = time.time()
        
        items = []
        warnings = []
        errors = []
        
        # Verificar estado del lote
        if not lote.activo:
            errors.append(f"El lote {lote.numero_lote} está inactivo/eliminado")
            nivel = NivelAlerta.CRITICAL
        elif lote.estado == 'vencido':
            errors.append(f"El lote {lote.numero_lote} está vencido")
            nivel = NivelAlerta.ERROR
        elif lote.estado == 'agotado':
            errors.append(f"El lote {lote.numero_lote} está agotado")
            nivel = NivelAlerta.ERROR
        elif lote.cantidad_actual < cantidad:
            deficit = cantidad - lote.cantidad_actual
            errors.append(
                f"Stock insuficiente en lote {lote.numero_lote}: "
                f"disponible {lote.cantidad_actual}, requerido {cantidad} (déficit: {deficit})"
            )
            nivel = NivelAlerta.ERROR
        elif lote.cantidad_actual == cantidad:
            warnings.append(
                f"El lote {lote.numero_lote} quedará agotado después de esta operación"
            )
            nivel = NivelAlerta.WARNING
        else:
            nivel = NivelAlerta.OK
        
        # Verificar caducidad próxima
        if lote.fecha_caducidad:
            dias_para_caducar = (lote.fecha_caducidad - date.today()).days
            if dias_para_caducar < 0:
                errors.append(f"El lote {lote.numero_lote} ya caducó")
                nivel = NivelAlerta.ERROR
            elif dias_para_caducar <= 30:
                warnings.append(
                    f"El lote {lote.numero_lote} caduca en {dias_para_caducar} días"
                )
        
        item = PreflightItem(
            producto_clave=lote.producto.clave,
            producto_descripcion=lote.producto.descripcion[:50],
            cantidad_requerida=cantidad,
            cantidad_disponible=lote.cantidad_actual,
            nivel=nivel,
            mensaje=errors[0] if errors else (warnings[0] if warnings else "OK"),
            detalles={
                'lote_id': lote.id,
                'numero_lote': lote.numero_lote,
                'estado': lote.estado,
                'fecha_caducidad': str(lote.fecha_caducidad) if lote.fecha_caducidad else None,
            }
        )
        items.append(item)
        
        puede_proceder = nivel in (NivelAlerta.OK, NivelAlerta.WARNING)
        tiempo_ms = (time.time() - inicio) * 1000
        
        return PreflightResult(
            puede_proceder=puede_proceder,
            nivel_general=nivel,
            items=items,
            warnings=warnings,
            errors=errors,
            tiempo_verificacion_ms=tiempo_ms
        )
    
    def verificar_transferencia(
        self,
        productos_cantidades: List[Dict[str, Any]],
        centro_destino
    ) -> PreflightResult:
        """
        ISS-005: Verifica stock antes de una transferencia.
        
        Args:
            productos_cantidades: Lista de {'producto': Producto, 'cantidad': int}
            centro_destino: Centro destino de la transferencia
            
        Returns:
            PreflightResult
        """
        import time
        inicio = time.time()
        
        items = []
        warnings = []
        errors = []
        
        for item_data in productos_cantidades:
            producto = item_data['producto']
            cantidad = item_data['cantidad']
            
            item = self._verificar_producto(producto, cantidad)
            items.append(item)
            
            if item.nivel == NivelAlerta.WARNING:
                warnings.append(item.mensaje)
            elif item.nivel in (NivelAlerta.ERROR, NivelAlerta.CRITICAL):
                errors.append(item.mensaje)
        
        # Determinar nivel general
        niveles = [i.nivel for i in items]
        if NivelAlerta.CRITICAL in niveles:
            nivel_general = NivelAlerta.CRITICAL
        elif NivelAlerta.ERROR in niveles:
            nivel_general = NivelAlerta.ERROR
        elif NivelAlerta.WARNING in niveles:
            nivel_general = NivelAlerta.WARNING
        else:
            nivel_general = NivelAlerta.OK
        
        puede_proceder = nivel_general in (NivelAlerta.OK, NivelAlerta.WARNING)
        tiempo_ms = (time.time() - inicio) * 1000
        
        return PreflightResult(
            puede_proceder=puede_proceder,
            nivel_general=nivel_general,
            items=items,
            warnings=warnings,
            errors=errors,
            tiempo_verificacion_ms=tiempo_ms
        )
    
    def _verificar_producto(
        self,
        producto,
        cantidad_requerida: int
    ) -> PreflightItem:
        """Verifica disponibilidad de un producto específico."""
        from core.models import Lote
        
        # Construir filtro base
        filtro = Q(
            producto=producto,
            activo=True,
            cantidad_actual__gt=0
        )
        
        # Filtrar por centro si aplica
        if self.centro:
            filtro &= Q(centro=self.centro)
        else:
            filtro &= Q(centro__isnull=True)  # Solo farmacia central
        
        # Calcular stock disponible
        resultado = Lote.objects.filter(filtro).aggregate(
            total=Sum('cantidad_actual'),
            lotes_count=Count('id')
        )
        
        cantidad_disponible = resultado['total'] or 0
        lotes_count = resultado['lotes_count'] or 0
        
        # Determinar nivel de alerta
        if cantidad_disponible == 0:
            nivel = NivelAlerta.CRITICAL
            mensaje = f"Sin stock de {producto.clave}"
        elif cantidad_disponible < cantidad_requerida:
            deficit = cantidad_requerida - cantidad_disponible
            nivel = NivelAlerta.ERROR
            mensaje = f"Stock insuficiente de {producto.clave}: déficit de {deficit} unidades"
        elif cantidad_disponible < cantidad_requerida * 1.2:
            # Stock justo (menos del 20% de margen)
            nivel = NivelAlerta.WARNING
            mensaje = f"Stock ajustado de {producto.clave}: quedará {cantidad_disponible - cantidad_requerida} unidades"
        else:
            nivel = NivelAlerta.OK
            mensaje = f"Stock suficiente de {producto.clave}"
        
        # Verificar lotes próximos a vencer
        lotes_por_vencer = Lote.objects.filter(
            filtro,
            fecha_caducidad__lte=date.today() + timedelta(days=30)
        ).count()
        
        detalles = {
            'lotes_disponibles': lotes_count,
            'lotes_por_vencer_30d': lotes_por_vencer,
            'producto_activo': producto.activo,
        }
        
        if lotes_por_vencer > 0 and nivel == NivelAlerta.OK:
            nivel = NivelAlerta.WARNING
            mensaje = f"{producto.clave}: {lotes_por_vencer} lote(s) próximo(s) a vencer"
        
        return PreflightItem(
            producto_clave=producto.clave,
            producto_descripcion=producto.descripcion[:50],
            cantidad_requerida=cantidad_requerida,
            cantidad_disponible=cantidad_disponible,
            nivel=nivel,
            mensaje=mensaje,
            detalles=detalles
        )
    
    def verificar_integridad_lote(self, lote) -> Dict[str, Any]:
        """
        ISS-005: Verifica integridad de un lote específico.
        
        Returns:
            Dict con resultados de integridad
        """
        from core.models import Movimiento
        
        problemas = []
        
        # Verificar cantidad actual vs movimientos
        movimientos = Movimiento.objects.filter(lote=lote)
        entradas = movimientos.filter(tipo='entrada').aggregate(
            total=Sum('cantidad')
        )['total'] or 0
        salidas = abs(movimientos.filter(tipo='salida').aggregate(
            total=Sum('cantidad')
        )['total'] or 0)
        ajustes = movimientos.filter(tipo='ajuste').aggregate(
            total=Sum('cantidad')
        )['total'] or 0
        
        stock_calculado = lote.cantidad_inicial + entradas - salidas + ajustes
        
        if stock_calculado != lote.cantidad_actual:
            problemas.append({
                'tipo': 'discrepancia_stock',
                'mensaje': f"Stock en sistema: {lote.cantidad_actual}, calculado: {stock_calculado}",
                'severidad': 'error'
            })
        
        # Verificar estado vs cantidad
        if lote.cantidad_actual == 0 and lote.estado == 'disponible':
            problemas.append({
                'tipo': 'estado_inconsistente',
                'mensaje': "Lote con cantidad 0 marcado como disponible",
                'severidad': 'warning'
            })
        
        # Verificar caducidad vs estado
        if lote.fecha_caducidad and lote.fecha_caducidad < date.today():
            if lote.estado != 'vencido':
                problemas.append({
                    'tipo': 'caducidad_no_marcada',
                    'mensaje': "Lote caducado no marcado como vencido",
                    'severidad': 'warning'
                })
        
        return {
            'lote_id': lote.id,
            'numero_lote': lote.numero_lote,
            'integridad_ok': len(problemas) == 0,
            'problemas': problemas,
            'stock_sistema': lote.cantidad_actual,
            'stock_calculado': stock_calculado,
            'movimientos_count': movimientos.count(),
        }


def verificar_stock_preflight(requisicion, usuario=None) -> PreflightResult:
    """
    ISS-005: Función helper para verificación rápida de preflight.
    
    Args:
        requisicion: Requisición a verificar
        usuario: Usuario que realiza la operación
        
    Returns:
        PreflightResult
    """
    checker = PreflightStockCheck(
        centro=requisicion.centro,
        usuario=usuario
    )
    return checker.verificar_requisicion(requisicion)
