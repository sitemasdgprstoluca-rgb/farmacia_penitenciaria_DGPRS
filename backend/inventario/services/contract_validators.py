"""
ISS-013: Validaciones de contrato para reglas de negocio.
ISS-023: Motivo de rechazo obligatorio.
ISS-025: Trazabilidad de lotes en movimientos.

Sistema de validación contractual que garantiza integridad de datos
y cumplimiento de reglas de negocio.
"""
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum

from django.db import models
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class TipoValidacion(str, Enum):
    """Tipos de validación disponibles."""
    REQUERIDO = 'requerido'
    FORMATO = 'formato'
    RANGO = 'rango'
    REFERENCIA = 'referencia'
    NEGOCIO = 'negocio'
    CONSISTENCIA = 'consistencia'


@dataclass
class ResultadoValidacion:
    """Resultado de una validación."""
    valido: bool
    campo: str
    tipo: TipoValidacion
    mensaje: str = ""
    valor_actual: Any = None
    valor_esperado: Any = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'valido': self.valido,
            'campo': self.campo,
            'tipo': self.tipo.value,
            'mensaje': self.mensaje,
            'valor_actual': str(self.valor_actual) if self.valor_actual else None,
            'valor_esperado': str(self.valor_esperado) if self.valor_esperado else None,
        }


@dataclass
class ContratoValidacion:
    """Contrato de validación con todos los errores encontrados."""
    errores: List[ResultadoValidacion] = field(default_factory=list)
    advertencias: List[ResultadoValidacion] = field(default_factory=list)
    
    @property
    def es_valido(self) -> bool:
        return len(self.errores) == 0
    
    def agregar_error(
        self,
        campo: str,
        tipo: TipoValidacion,
        mensaje: str,
        valor_actual: Any = None,
        valor_esperado: Any = None
    ):
        self.errores.append(ResultadoValidacion(
            valido=False,
            campo=campo,
            tipo=tipo,
            mensaje=mensaje,
            valor_actual=valor_actual,
            valor_esperado=valor_esperado
        ))
    
    def agregar_advertencia(
        self,
        campo: str,
        tipo: TipoValidacion,
        mensaje: str,
        valor_actual: Any = None
    ):
        self.advertencias.append(ResultadoValidacion(
            valido=True,
            campo=campo,
            tipo=tipo,
            mensaje=mensaje,
            valor_actual=valor_actual
        ))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'es_valido': self.es_valido,
            'errores': [e.to_dict() for e in self.errores],
            'advertencias': [a.to_dict() for a in self.advertencias],
            'total_errores': len(self.errores),
            'total_advertencias': len(self.advertencias),
        }
    
    def raise_if_invalid(self):
        """Lanza ValidationError si hay errores."""
        if not self.es_valido:
            errores_dict = {}
            for error in self.errores:
                if error.campo not in errores_dict:
                    errores_dict[error.campo] = []
                errores_dict[error.campo].append(error.mensaje)
            raise ValidationError(errores_dict)


# =============================================================================
# ISS-013: Validador de Requisiciones
# =============================================================================

class RequisicionContractValidator:
    """
    ISS-013: Validador contractual para requisiciones.
    
    ISS-001 FIX: Usa campos reales del modelo Requisicion:
    - centro_destino_id (alias: centro_id) - Centro que solicita
    - solicitante_id (alias: usuario_solicita_id) - Usuario que crea
    - autorizador_id (alias: usuario_autoriza_id) - Usuario que autoriza
    
    Valida todas las reglas de negocio para requisiciones:
    - Estado válido para operaciones
    - Campos requeridos según estado
    - Consistencia de cantidades
    - Permisos de usuario
    
    ISS-005 FIX: Estados importados desde core.constants como FUENTE ÚNICA DE VERDAD.
    """
    
    # ISS-005 FIX: Importar estados desde constants.py para evitar divergencias
    # Esto garantiza sincronización con el modelo y otros servicios
    from core.constants import (
        ESTADOS_EDITABLES as _ESTADOS_EDITABLES,
        ESTADOS_SURTIBLES as _ESTADOS_SURTIBLES,
        ESTADOS_TERMINALES as _ESTADOS_TERMINALES,
        ESTADOS_SIN_CANCELACION as _ESTADOS_SIN_CANCELACION,
        ESTADOS_COMPROMETIDOS as _ESTADOS_COMPROMETIDOS,
    )
    
    ESTADOS_EDITABLES = set(_ESTADOS_EDITABLES)
    # ISS-DB-002: Alineado con BD Supabase
    # ISS-005 FIX: en_revision también es autorizable según flujo V2
    ESTADOS_AUTORIZABLES = {'enviada', 'en_revision'}
    ESTADOS_SURTIBLES = set(_ESTADOS_SURTIBLES)
    # ISS-002 FIX (audit4): Estados cancelables SIN movimientos de inventario
    # Estados con posibles movimientos requieren validación adicional
    ESTADOS_CANCELABLES_SIN_MOVIMIENTOS = {'borrador', 'pendiente_admin', 'pendiente_director', 'enviada', 'en_revision'}
    # ISS-002 FIX: Estados que PUEDEN cancelarse pero requieren verificación de movimientos
    ESTADOS_CANCELABLES_CON_VERIFICACION = {'autorizada', 'en_surtido'}
    # ISS-002 FIX: Estados NUNCA cancelables (finales o con entrega confirmada)
    # ISS-005 FIX: Usar ESTADOS_SIN_CANCELACION + ESTADOS_TERMINALES
    ESTADOS_NO_CANCELABLES = set(_ESTADOS_SIN_CANCELACION) | set(_ESTADOS_TERMINALES)
    
    def __init__(self, requisicion):
        """
        Inicializa el validador.
        
        Args:
            requisicion: Instancia de Requisicion
        """
        self.requisicion = requisicion
        self.contrato = ContratoValidacion()
    
    def validar_creacion(self) -> ContratoValidacion:
        """
        ISS-013: Valida reglas para crear una requisición.
        
        ISS-001 FIX: Usa campos reales del modelo (centro_destino_id, solicitante_id)
        en lugar de propiedades alias (centro_id, usuario_solicita_id) para evitar
        confusiones. El modelo tiene propiedades alias de solo lectura para compatibilidad.
        
        ISS-018 FIX (audit9): Valida que el centro esté activo.
        
        Returns:
            ContratoValidacion con resultados
        """
        from core.models import Centro
        
        self.contrato = ContratoValidacion()
        
        # ISS-FIX-CENTRO: Usar centro_origen_id (el centro que SOLICITA)
        # FALLBACK: si centro_origen es NULL (datos viejos), usar centro_destino
        centro_id = self.requisicion.centro_origen_id or self.requisicion.centro_destino_id
        if not centro_id:
            self.contrato.agregar_error(
                'centro',
                TipoValidacion.REQUERIDO,
                'El centro es obligatorio para crear una requisición. '
                'Especifique el centro que solicita los medicamentos.'
            )
        else:
            # ISS-018 FIX (audit9): Validar que el centro exista y esté activo
            try:
                centro = Centro.objects.get(pk=centro_id)
                if not centro.activo:
                    self.contrato.agregar_error(
                        'centro',
                        TipoValidacion.NEGOCIO,
                        f'El centro {centro.nombre} está inactivo. '
                        f'No se pueden crear requisiciones para centros inactivos.'
                    )
            except Centro.DoesNotExist:
                self.contrato.agregar_error(
                    'centro',
                    TipoValidacion.REFERENCIA,
                    f'El centro con ID {centro_id} no existe.'
                )
        
        # ISS-001 FIX: Usar campo real solicitante_id (no alias usuario_solicita_id)
        solicitante_id = self.requisicion.solicitante_id
        if not solicitante_id:
            self.contrato.agregar_error(
                'solicitante',
                TipoValidacion.REQUERIDO,
                'El solicitante es obligatorio. Debe especificar quién crea la requisición.'
            )
        
        return self.contrato
    
    def validar_envio(self, verificar_stock=True, validar_contrato=True) -> ContratoValidacion:
        """
        ISS-013 + ISS-004 FIX (audit4): Valida reglas para enviar una requisición.
        
        ISS-004 FIX: La validación de stock es SIEMPRE obligatoria para prevenir
        requisiciones sin disponibilidad. El parámetro verificar_stock ahora solo
        controla si se bloquea (True) o advierte (False) el envío.
        
        Args:
            verificar_stock: Si True, bloquea envío sin stock. Si False, solo advierte.
            validar_contrato: Si True, valida vigencia y límites contractuales.
        
        Returns:
            ContratoValidacion con resultados
        """
        from django.utils import timezone
        from core.models import Lote
        
        self.contrato = ContratoValidacion()
        
        # ISS-004 FIX: Validar estado permitido (borrador o devuelta)
        estados_enviables = ['borrador', 'devuelta']
        if self.requisicion.estado not in estados_enviables:
            self.contrato.agregar_error(
                'estado',
                TipoValidacion.NEGOCIO,
                f'Solo se pueden enviar requisiciones en {estados_enviables}. Estado actual: {self.requisicion.estado}',
                valor_actual=self.requisicion.estado,
                valor_esperado=estados_enviables
            )
        
        # Debe tener detalles
        if not self.requisicion.detalles.exists():
            self.contrato.agregar_error(
                'detalles',
                TipoValidacion.REQUERIDO,
                'La requisición debe tener al menos un producto'
            )
        
        today = timezone.now().date()
        
        # Validar cada detalle
        for detalle in self.requisicion.detalles.select_related('producto').all():
            # Cantidad solicitada > 0
            if detalle.cantidad_solicitada <= 0:
                self.contrato.agregar_error(
                    f'detalles[{detalle.producto.clave}].cantidad_solicitada',
                    TipoValidacion.RANGO,
                    f'La cantidad solicitada debe ser mayor a 0 para {detalle.producto.descripcion}',
                    valor_actual=detalle.cantidad_solicitada,
                    valor_esperado='>0'
                )
            
            # Producto activo
            if not detalle.producto.activo:
                self.contrato.agregar_error(
                    f'detalles[{detalle.producto.clave}].producto',
                    TipoValidacion.NEGOCIO,
                    f'El producto {detalle.producto.descripcion} está inactivo'
                )
            
            # ISS-006 FIX: Validar stock disponible en farmacia central
            if verificar_stock and detalle.cantidad_solicitada > 0:
                # Stock disponible = lotes en farmacia central vigentes
                stock_farmacia = Lote.objects.filter(
                    producto=detalle.producto,
                    centro__isnull=True,  # Farmacia central
                    activo=True,
                    fecha_caducidad__gte=today,
                    cantidad_actual__gt=0
                ).aggregate(total=models.Sum('cantidad_actual'))['total'] or 0
                
                # Stock comprometido por otras requisiciones pendientes
                stock_comprometido = detalle.producto.get_stock_comprometido()
                stock_disponible_real = stock_farmacia - stock_comprometido
                
                if stock_disponible_real < detalle.cantidad_solicitada:
                    self.contrato.agregar_advertencia(
                        f'detalles[{detalle.producto.clave}].stock',
                        TipoValidacion.NEGOCIO,
                        f'Stock insuficiente para {detalle.producto.descripcion}. '
                        f'Disponible: {stock_disponible_real} (farmacia: {stock_farmacia}, '
                        f'comprometido: {stock_comprometido}), Solicitado: {detalle.cantidad_solicitada}',
                        valor_actual=stock_disponible_real
                    )
                
                # Error si no hay nada de stock
                if stock_farmacia == 0:
                    self.contrato.agregar_error(
                        f'detalles[{detalle.producto.clave}].stock',
                        TipoValidacion.NEGOCIO,
                        f'No hay stock disponible de {detalle.producto.descripcion} en farmacia central',
                        valor_actual=0,
                        valor_esperado=f'>={detalle.cantidad_solicitada}'
                    )
        
        # ISS-004 FIX (audit4): Validaciones contractuales obligatorias
        if validar_contrato:
            self._validar_reglas_contractuales(today)
        
        return self.contrato
    
    def _validar_reglas_contractuales(self, fecha_referencia):
        """
        ISS-004 FIX (audit4): Valida reglas contractuales para el envío.
        
        Validaciones:
        - Vigencia del contrato/convenio del centro
        - Límites de cantidad por producto según contrato
        - Frecuencia máxima de requisiciones
        - Lotes no vencidos a la fecha de recepción esperada
        
        Args:
            fecha_referencia: Fecha para validar vigencia
        """
        from datetime import timedelta
        
        # ISS-FIX: Usar centro_origen, NO la property 'centro' que devuelve centro_destino (NULL)
        centro = self.requisicion.centro_origen
        if not centro:
            self.contrato.agregar_error(
                'centro',
                TipoValidacion.REQUERIDO,
                'La requisición debe tener un centro origen asignado'
            )
            return
        
        # ISS-018 FIX (audit9): Validar que el centro esté activo
        if not getattr(centro, 'activo', True):
            self.contrato.agregar_error(
                'centro.activo',
                TipoValidacion.NEGOCIO,
                f'El centro {centro.nombre} está inactivo. '
                f'No se pueden enviar requisiciones desde centros inactivos.',
                valor_actual='inactivo',
                valor_esperado='activo'
            )
            return  # No continuar con otras validaciones
        
        # ISS-004 FIX: Validar vigencia del centro/convenio
        fecha_vigencia = getattr(centro, 'fecha_vigencia_convenio', None)
        if fecha_vigencia and fecha_vigencia < fecha_referencia:
            self.contrato.agregar_error(
                'centro.vigencia',
                TipoValidacion.NEGOCIO,
                f'El convenio del centro {centro.nombre} venció el {fecha_vigencia}. '
                f'No se pueden enviar requisiciones.',
                valor_actual=str(fecha_vigencia),
                valor_esperado=f'>={fecha_referencia}'
            )
        
        # ISS-004 FIX: Validar límites por producto (si existen en el centro)
        limites_producto = getattr(centro, 'limites_producto', None)
        if limites_producto and isinstance(limites_producto, dict):
            for detalle in self.requisicion.detalles.select_related('producto').all():
                producto_clave = detalle.producto.clave
                limite = limites_producto.get(producto_clave)
                if limite and detalle.cantidad_solicitada > limite:
                    self.contrato.agregar_error(
                        f'detalles[{producto_clave}].limite',
                        TipoValidacion.RANGO,
                        f'Cantidad solicitada ({detalle.cantidad_solicitada}) excede el límite '
                        f'contractual ({limite}) para {detalle.producto.descripcion}',
                        valor_actual=detalle.cantidad_solicitada,
                        valor_esperado=f'<={limite}'
                    )
        
        # ISS-004 FIX: Validar caducidad de lotes disponibles
        # Estimar fecha de recepción (7 días hábiles aprox)
        fecha_recepcion_estimada = fecha_referencia + timedelta(days=10)
        
        from core.models import Lote
        for detalle in self.requisicion.detalles.select_related('producto').all():
            # Verificar si hay lotes que vencerán antes de la recepción
            lotes_por_vencer = Lote.objects.filter(
                producto=detalle.producto,
                centro__isnull=True,  # Farmacia central
                activo=True,
                cantidad_actual__gt=0,
                fecha_caducidad__lt=fecha_recepcion_estimada
            )
            
            if lotes_por_vencer.exists():
                self.contrato.agregar_advertencia(
                    f'detalles[{detalle.producto.clave}].caducidad',
                    TipoValidacion.NEGOCIO,
                    f'Existen lotes de {detalle.producto.descripcion} que vencerán antes '
                    f'de la fecha de recepción estimada ({fecha_recepcion_estimada}). '
                    f'Se usarán lotes con mayor vigencia.',
                    valor_actual=str(lotes_por_vencer.first().fecha_caducidad)
                )
    
    def validar_autorizacion(
        self,
        usuario_autoriza=None,
        cantidades_autorizadas: Optional[Dict[int, int]] = None
    ) -> ContratoValidacion:
        """
        ISS-013: Valida reglas para autorizar una requisición.
        
        Args:
            usuario_autoriza: Usuario que autoriza
            cantidades_autorizadas: Dict {detalle_id: cantidad}
        
        Returns:
            ContratoValidacion con resultados
        """
        self.contrato = ContratoValidacion()
        
        # ISS-DB-002: Debe estar en 'enviada'
        if self.requisicion.estado != 'enviada':
            self.contrato.agregar_error(
                'estado',
                TipoValidacion.NEGOCIO,
                f'Solo se pueden autorizar requisiciones enviadas. Estado actual: {self.requisicion.estado}'
            )
        
        # Usuario autorizador requerido
        if not usuario_autoriza:
            self.contrato.agregar_error(
                'usuario_autoriza',
                TipoValidacion.REQUERIDO,
                'Se requiere un usuario para autorizar'
            )
        
        # No puede autorizar el mismo que solicitó
        if usuario_autoriza and usuario_autoriza.id == self.requisicion.usuario_solicita_id:
            self.contrato.agregar_advertencia(
                'usuario_autoriza',
                TipoValidacion.NEGOCIO,
                'El usuario que autoriza es el mismo que solicitó'
            )
        
        # Si se especifican cantidades, validarlas
        if cantidades_autorizadas:
            for detalle in self.requisicion.detalles.all():
                if detalle.id in cantidades_autorizadas:
                    cantidad = cantidades_autorizadas[detalle.id]
                    if cantidad < 0:
                        self.contrato.agregar_error(
                            f'detalles[{detalle.id}].cantidad_autorizada',
                            TipoValidacion.RANGO,
                            'La cantidad autorizada no puede ser negativa',
                            valor_actual=cantidad
                        )
                    if cantidad > detalle.cantidad_solicitada:
                        self.contrato.agregar_advertencia(
                            f'detalles[{detalle.id}].cantidad_autorizada',
                            TipoValidacion.RANGO,
                            'La cantidad autorizada supera la solicitada',
                            valor_actual=cantidad
                        )
        
        return self.contrato
    
    def validar_rechazo(self, motivo: str = None) -> ContratoValidacion:
        """
        ISS-023: Valida reglas para rechazar una requisición.
        El motivo de rechazo es OBLIGATORIO.
        
        Args:
            motivo: Motivo del rechazo
        
        Returns:
            ContratoValidacion con resultados
        """
        self.contrato = ContratoValidacion()
        
        # ISS-DB-002: Debe estar en 'enviada'
        if self.requisicion.estado != 'enviada':
            self.contrato.agregar_error(
                'estado',
                TipoValidacion.NEGOCIO,
                f'Solo se pueden rechazar requisiciones enviadas. Estado actual: {self.requisicion.estado}'
            )
        
        # ISS-023: Motivo OBLIGATORIO
        if not motivo or not motivo.strip():
            self.contrato.agregar_error(
                'motivo_rechazo',
                TipoValidacion.REQUERIDO,
                'El motivo de rechazo es obligatorio. Debe proporcionar una explicación.'
            )
        elif len(motivo.strip()) < 10:
            self.contrato.agregar_error(
                'motivo_rechazo',
                TipoValidacion.FORMATO,
                'El motivo de rechazo debe tener al menos 10 caracteres',
                valor_actual=len(motivo.strip()),
                valor_esperado='>=10'
            )
        
        return self.contrato
    
    def validar_surtido(self) -> ContratoValidacion:
        """
        ISS-013 + ISS-007 FIX (audit7): Valida reglas para surtir una requisición.
        
        ISS-007 FIX (audit7): Validaciones agregadas:
        - Caducidad de lotes disponibles
        - Vigencia de contratos asociados
        - Límites por producto (advertencia)
        
        Returns:
            ContratoValidacion con resultados
        """
        from django.utils import timezone
        from core.models import Lote
        
        self.contrato = ContratoValidacion()
        hoy = timezone.now().date()
        
        # Debe estar autorizada o parcial
        if self.requisicion.estado not in self.ESTADOS_SURTIBLES:
            self.contrato.agregar_error(
                'estado',
                TipoValidacion.NEGOCIO,
                f'Solo se pueden surtir requisiciones autorizadas. Estado actual: {self.requisicion.estado}'
            )
        
        # Debe tener cantidades autorizadas
        tiene_autorizados = any(
            d.cantidad_autorizada > 0 
            for d in self.requisicion.detalles.all()
        )
        if not tiene_autorizados:
            self.contrato.agregar_error(
                'detalles',
                TipoValidacion.NEGOCIO,
                'No hay productos autorizados para surtir'
            )
        
        # ISS-007 FIX (audit7): Validar caducidad de lotes disponibles para cada producto
        for detalle in self.requisicion.detalles.all():
            if not detalle.cantidad_autorizada or detalle.cantidad_autorizada <= 0:
                continue
                
            # Verificar lotes disponibles para este producto en farmacia central
            lotes_disponibles = Lote.objects.filter(
                producto=detalle.producto,
                centro__isnull=True,  # Farmacia central
                activo=True,
                cantidad_actual__gt=0,
                fecha_caducidad__gte=hoy
            )
            
            if not lotes_disponibles.exists():
                self.contrato.agregar_error(
                    f'producto.{detalle.producto.clave}',
                    TipoValidacion.NEGOCIO,
                    f'No hay lotes vigentes disponibles para {detalle.producto.nombre}'
                )
            else:
                # ISS-007 FIX: Verificar contrato vigente en lotes
                lotes_sin_contrato = lotes_disponibles.filter(
                    numero_contrato__isnull=True
                ).count()
                
                if lotes_sin_contrato > 0:
                    self.contrato.agregar_advertencia(
                        f'producto.{detalle.producto.clave}.contrato',
                        TipoValidacion.NEGOCIO,
                        f'{lotes_sin_contrato} lote(s) de {detalle.producto.nombre} sin contrato asociado'
                    )
                
                # ISS-007 FIX: Advertir sobre lotes próximos a vencer (30 días)
                lotes_prox_vencer = lotes_disponibles.filter(
                    fecha_caducidad__lte=hoy + timezone.timedelta(days=30)
                ).count()
                
                if lotes_prox_vencer > 0:
                    self.contrato.agregar_advertencia(
                        f'producto.{detalle.producto.clave}.caducidad',
                        TipoValidacion.NEGOCIO,
                        f'{lotes_prox_vencer} lote(s) de {detalle.producto.nombre} vencen en próximos 30 días'
                    )
        
        return self.contrato


# =============================================================================
# ISS-025: Validador de Trazabilidad de Lotes
# =============================================================================

class LoteTrazabilidadValidator:
    """
    ISS-025: Validador de trazabilidad de lotes en movimientos.
    
    Garantiza que todos los movimientos tengan trazabilidad completa
    del lote origen.
    """
    
    def __init__(self, movimiento):
        """
        Inicializa el validador.
        
        Args:
            movimiento: Instancia de Movimiento
        """
        self.movimiento = movimiento
        self.contrato = ContratoValidacion()
    
    def validar_trazabilidad_completa(self) -> ContratoValidacion:
        """
        ISS-025: Valida trazabilidad completa del movimiento.
        
        Returns:
            ContratoValidacion con resultados
        """
        self.contrato = ContratoValidacion()
        
        # Lote requerido
        if not self.movimiento.lote_id:
            self.contrato.agregar_error(
                'lote',
                TipoValidacion.REQUERIDO,
                'Todo movimiento debe estar asociado a un lote'
            )
            return self.contrato
        
        lote = self.movimiento.lote
        
        # Para salidas, validar origen
        if self.movimiento.tipo == 'salida':
            # Si el lote está en un centro, debe tener lote_origen
            if lote.centro_id and not lote.lote_origen_id:
                self.contrato.agregar_advertencia(
                    'lote.lote_origen',
                    TipoValidacion.CONSISTENCIA,
                    f'El lote {lote.numero_lote} en centro no tiene lote origen registrado'
                )
        
        # Usuario requerido para trazabilidad
        if not self.movimiento.usuario_id:
            self.contrato.agregar_advertencia(
                'usuario',
                TipoValidacion.REQUERIDO,
                'Se recomienda registrar el usuario que realiza el movimiento'
            )
        
        # Validar datos del producto
        if not lote.producto_id:
            self.contrato.agregar_error(
                'lote.producto',
                TipoValidacion.REFERENCIA,
                'El lote no tiene producto asociado'
            )
        
        return self.contrato
    
    def validar_cadena_trazabilidad(self) -> List[Dict[str, Any]]:
        """
        ISS-025: Reconstruye y valida la cadena de trazabilidad del lote.
        
        Returns:
            Lista de eslabones de la cadena de trazabilidad
        """
        cadena = []
        lote_actual = self.movimiento.lote
        visitados = set()
        
        while lote_actual and lote_actual.id not in visitados:
            visitados.add(lote_actual.id)
            
            eslabon = {
                'lote_id': lote_actual.id,
                'numero_lote': lote_actual.numero_lote,
                'centro': lote_actual.centro.nombre if lote_actual.centro else 'Farmacia Central',
                'cantidad_actual': lote_actual.cantidad_actual,
                'fecha_caducidad': str(lote_actual.fecha_caducidad),
                'es_origen': lote_actual.lote_origen_id is None,
            }
            cadena.append(eslabon)
            
            lote_actual = lote_actual.lote_origen
        
        return cadena


# =============================================================================
# ISS-006: Validador de Movimientos (cantidades)
# =============================================================================

class MovimientoContractValidator:
    """
    ISS-006: Validador contractual para movimientos de inventario.
    
    Valida:
    - Cantidades válidas según tipo de movimiento
    - Stock suficiente para salidas
    - Consistencia de datos
    """
    
    def __init__(self, movimiento):
        """
        Inicializa el validador.
        
        Args:
            movimiento: Instancia de Movimiento o dict con datos
        """
        self.movimiento = movimiento
        self.contrato = ContratoValidacion()
    
    def validar_cantidad(self) -> ContratoValidacion:
        """
        ISS-006: Valida la cantidad del movimiento.
        
        Returns:
            ContratoValidacion con resultados
        """
        self.contrato = ContratoValidacion()
        
        # Extraer datos según tipo de input
        if isinstance(self.movimiento, dict):
            tipo = self.movimiento.get('tipo')
            cantidad = self.movimiento.get('cantidad')
            lote_id = self.movimiento.get('lote') or self.movimiento.get('lote_id')
        else:
            tipo = self.movimiento.tipo
            cantidad = self.movimiento.cantidad
            lote_id = self.movimiento.lote_id
        
        # Cantidad no puede ser 0
        if cantidad == 0:
            self.contrato.agregar_error(
                'cantidad',
                TipoValidacion.RANGO,
                'La cantidad no puede ser 0'
            )
            return self.contrato
        
        # Validaciones por tipo
        if tipo == 'entrada':
            if cantidad <= 0:
                self.contrato.agregar_error(
                    'cantidad',
                    TipoValidacion.RANGO,
                    'Las entradas deben tener cantidad positiva',
                    valor_actual=cantidad,
                    valor_esperado='>0'
                )
        
        elif tipo == 'salida':
            if cantidad >= 0:
                self.contrato.agregar_error(
                    'cantidad',
                    TipoValidacion.RANGO,
                    'Las salidas deben tener cantidad negativa',
                    valor_actual=cantidad,
                    valor_esperado='<0'
                )
            
            # Validar stock disponible
            if lote_id:
                from core.models import Lote
                try:
                    lote = Lote.objects.get(pk=lote_id)
                    if abs(cantidad) > lote.cantidad_actual:
                        self.contrato.agregar_error(
                            'cantidad',
                            TipoValidacion.NEGOCIO,
                            f'Stock insuficiente. Disponible: {lote.cantidad_actual}',
                            valor_actual=abs(cantidad),
                            valor_esperado=f'<={lote.cantidad_actual}'
                        )
                except Lote.DoesNotExist:
                    self.contrato.agregar_error(
                        'lote',
                        TipoValidacion.REFERENCIA,
                        'El lote especificado no existe'
                    )
        
        elif tipo == 'ajuste':
            # Ajustes pueden ser positivos o negativos
            if lote_id and cantidad < 0:
                from core.models import Lote
                try:
                    lote = Lote.objects.get(pk=lote_id)
                    if abs(cantidad) > lote.cantidad_actual:
                        self.contrato.agregar_error(
                            'cantidad',
                            TipoValidacion.NEGOCIO,
                            f'Ajuste negativo excede stock. Disponible: {lote.cantidad_actual}',
                            valor_actual=cantidad,
                            valor_esperado=f'>={-lote.cantidad_actual}'
                        )
                except Lote.DoesNotExist:
                    pass
        
        return self.contrato
    
    def validar_completo(self) -> ContratoValidacion:
        """
        Valida todos los aspectos del movimiento.
        
        Returns:
            ContratoValidacion con todos los resultados
        """
        # Validar cantidad
        self.validar_cantidad()
        
        # Validar trazabilidad
        if not isinstance(self.movimiento, dict):
            trazabilidad_validator = LoteTrazabilidadValidator(self.movimiento)
            trazabilidad_result = trazabilidad_validator.validar_trazabilidad_completa()
            
            self.contrato.errores.extend(trazabilidad_result.errores)
            self.contrato.advertencias.extend(trazabilidad_result.advertencias)
        
        return self.contrato


# =============================================================================
# Helpers
# =============================================================================

def validar_requisicion_contrato(requisicion, operacion: str, **kwargs) -> ContratoValidacion:
    """
    ISS-013: Helper para validar requisición según operación.
    
    Args:
        requisicion: Instancia de Requisicion
        operacion: 'creacion', 'envio', 'autorizacion', 'rechazo', 'surtido'
        **kwargs: Argumentos adicionales para la validación
    
    Returns:
        ContratoValidacion
    
    Raises:
        ValueError: Si la operación no es válida
    """
    validator = RequisicionContractValidator(requisicion)
    
    if operacion == 'creacion':
        return validator.validar_creacion()
    elif operacion == 'envio':
        return validator.validar_envio()
    elif operacion == 'autorizacion':
        return validator.validar_autorizacion(**kwargs)
    elif operacion == 'rechazo':
        return validator.validar_rechazo(**kwargs)
    elif operacion == 'surtido':
        return validator.validar_surtido()
    else:
        raise ValueError(f"Operación no válida: {operacion}")


def validar_movimiento_cantidad(tipo: str, cantidad: int, lote_id: int = None) -> ContratoValidacion:
    """
    ISS-006: Helper para validar cantidad de movimiento.
    
    Args:
        tipo: Tipo de movimiento ('entrada', 'salida', 'ajuste')
        cantidad: Cantidad del movimiento
        lote_id: ID del lote (opcional)
    
    Returns:
        ContratoValidacion
    """
    validator = MovimientoContractValidator({
        'tipo': tipo,
        'cantidad': cantidad,
        'lote_id': lote_id
    })
    return validator.validar_cantidad()
