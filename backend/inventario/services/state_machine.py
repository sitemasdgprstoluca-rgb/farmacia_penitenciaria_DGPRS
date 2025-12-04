"""
ISS-012: Máquina de estados formal para requisiciones.

Implementa un patrón State Machine robusto que:
- Define transiciones válidas entre estados
- Valida precondiciones para cada transición
- Registra historial de cambios de estado
- Emite eventos/hooks para acciones post-transición
"""
import logging
from datetime import datetime
from typing import Optional, Dict, List, Callable, Any
from dataclasses import dataclass, field
from enum import Enum

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class EstadoRequisicion(str, Enum):
    """Estados posibles de una requisición."""
    BORRADOR = 'borrador'
    ENVIADA = 'enviada'
    AUTORIZADA = 'autorizada'
    PARCIAL = 'parcial'
    RECHAZADA = 'rechazada'
    SURTIDA = 'surtida'
    RECIBIDA = 'recibida'
    CANCELADA = 'cancelada'
    
    @classmethod
    def choices(cls):
        return [(e.value, e.value.title()) for e in cls]
    
    @classmethod
    def terminales(cls):
        """Estados que no permiten más transiciones."""
        return [cls.RECIBIDA, cls.CANCELADA]
    
    @classmethod
    def editables(cls):
        """Estados que permiten editar la requisición."""
        return [cls.BORRADOR]
    
    @classmethod
    def surtibles(cls):
        """Estados desde los que se puede surtir."""
        return [cls.AUTORIZADA, cls.PARCIAL]


@dataclass
class TransicionEstado:
    """Define una transición de estado con sus precondiciones."""
    origen: EstadoRequisicion
    destino: EstadoRequisicion
    nombre: str
    precondiciones: List[Callable] = field(default_factory=list)
    requiere_motivo: bool = False
    requiere_usuario: bool = True
    descripcion: str = ""


class TransicionInvalidaError(Exception):
    """Error cuando se intenta una transición no permitida."""
    def __init__(self, origen: str, destino: str, motivo: str = None):
        self.origen = origen
        self.destino = destino
        self.motivo = motivo or f"Transición de '{origen}' a '{destino}' no permitida"
        super().__init__(self.motivo)


class PrecondicionFallidaError(Exception):
    """Error cuando una precondición de transición falla."""
    def __init__(self, precondicion: str, detalle: str = None):
        self.precondicion = precondicion
        self.detalle = detalle or f"Precondición fallida: {precondicion}"
        super().__init__(self.detalle)


class RequisicionStateMachine:
    """
    ISS-012: Máquina de estados para requisiciones.
    
    Define el flujo completo:
    
    BORRADOR → ENVIADA → AUTORIZADA/PARCIAL/RECHAZADA
                         ↓
                      SURTIDA → RECIBIDA
                         
    Cualquier estado (excepto terminales) → CANCELADA
    """
    
    # Definición de todas las transiciones válidas
    TRANSICIONES: Dict[str, TransicionEstado] = {}
    
    # Matriz de transiciones: origen → [destinos posibles]
    MATRIZ_TRANSICIONES = {
        EstadoRequisicion.BORRADOR: [
            EstadoRequisicion.ENVIADA,
            EstadoRequisicion.CANCELADA
        ],
        EstadoRequisicion.ENVIADA: [
            EstadoRequisicion.AUTORIZADA,
            EstadoRequisicion.PARCIAL,
            EstadoRequisicion.RECHAZADA,
            EstadoRequisicion.CANCELADA
        ],
        EstadoRequisicion.AUTORIZADA: [
            EstadoRequisicion.SURTIDA,
            EstadoRequisicion.CANCELADA
        ],
        EstadoRequisicion.PARCIAL: [
            EstadoRequisicion.SURTIDA,
            EstadoRequisicion.AUTORIZADA,  # Re-autorizar completo
            EstadoRequisicion.CANCELADA
        ],
        EstadoRequisicion.RECHAZADA: [
            EstadoRequisicion.CANCELADA
        ],
        EstadoRequisicion.SURTIDA: [
            EstadoRequisicion.RECIBIDA
        ],
        EstadoRequisicion.RECIBIDA: [],  # Estado terminal
        EstadoRequisicion.CANCELADA: []  # Estado terminal
    }
    
    # Roles requeridos para cada tipo de transición
    ROLES_TRANSICION = {
        'enviar': ['centro', 'farmacia', 'admin'],
        'autorizar': ['farmacia', 'admin'],
        'rechazar': ['farmacia', 'admin'],
        'surtir': ['farmacia', 'admin'],
        'recibir': ['centro', 'farmacia', 'admin'],
        'cancelar': ['centro', 'farmacia', 'admin']  # El dueño puede cancelar
    }
    
    def __init__(self, requisicion):
        """
        Inicializa la máquina de estados.
        
        Args:
            requisicion: Instancia del modelo Requisicion
        """
        self.requisicion = requisicion
        self._historial = []
    
    @property
    def estado_actual(self) -> EstadoRequisicion:
        """Retorna el estado actual como enum."""
        try:
            return EstadoRequisicion(self.requisicion.estado or 'borrador')
        except ValueError:
            logger.warning(f"Estado inválido: {self.requisicion.estado}, usando borrador")
            return EstadoRequisicion.BORRADOR
    
    def puede_transicionar_a(self, destino: str) -> bool:
        """
        Verifica si la transición es válida sin ejecutarla.
        
        Args:
            destino: Estado destino (string o enum)
            
        Returns:
            bool: True si la transición es válida
        """
        try:
            destino_enum = EstadoRequisicion(destino.lower()) if isinstance(destino, str) else destino
        except ValueError:
            return False
        
        transiciones_permitidas = self.MATRIZ_TRANSICIONES.get(self.estado_actual, [])
        return destino_enum in transiciones_permitidas
    
    def get_transiciones_disponibles(self) -> List[str]:
        """
        Retorna las transiciones disponibles desde el estado actual.
        
        Returns:
            list: Lista de estados destino posibles
        """
        transiciones = self.MATRIZ_TRANSICIONES.get(self.estado_actual, [])
        return [t.value for t in transiciones]
    
    def es_estado_terminal(self) -> bool:
        """Verifica si el estado actual es terminal."""
        return self.estado_actual in EstadoRequisicion.terminales()
    
    def es_editable(self) -> bool:
        """Verifica si la requisición puede editarse."""
        return self.estado_actual in EstadoRequisicion.editables()
    
    def es_surtible(self) -> bool:
        """Verifica si la requisición puede surtirse."""
        return self.estado_actual in EstadoRequisicion.surtibles()
    
    def _validar_precondiciones_enviar(self) -> List[str]:
        """Valida precondiciones para enviar requisición."""
        errores = []
        
        # Debe tener al menos un detalle
        if not self.requisicion.detalles.exists():
            errores.append("La requisición debe tener al menos un producto")
        
        # Todos los productos deben estar activos
        for detalle in self.requisicion.detalles.select_related('producto'):
            if not detalle.producto.activo:
                errores.append(f"El producto {detalle.producto.clave} está inactivo")
            if detalle.cantidad_solicitada <= 0:
                errores.append(f"Cantidad inválida para {detalle.producto.clave}")
        
        return errores
    
    def _validar_precondiciones_autorizar(self) -> List[str]:
        """Valida precondiciones para autorizar."""
        errores = []
        
        # Debe tener detalles
        if not self.requisicion.detalles.exists():
            errores.append("No hay productos para autorizar")
        
        return errores
    
    def _validar_precondiciones_surtir(self) -> List[str]:
        """
        ISS-001/ISS-002 FIX: Valida precondiciones para surtir.
        
        SOLO valida stock en farmacia central, no incluye stock del centro destino.
        ISS-002 FIX: Solo considera lotes NO caducados.
        """
        from django.db.models import Sum
        from django.utils import timezone
        from core.models import Lote
        
        hoy = timezone.now().date()
        errores = []
        
        for detalle in self.requisicion.detalles.select_related('producto'):
            cantidad_requerida = (detalle.cantidad_autorizada or detalle.cantidad_solicitada) - (detalle.cantidad_surtida or 0)
            if cantidad_requerida <= 0:
                continue
            
            # ISS-001/ISS-002 FIX: Stock SOLO en farmacia central (centro=NULL)
            # ISS-002 FIX: Solo lotes vigentes (fecha_caducidad >= hoy)
            stock_disponible = Lote.objects.filter(
                centro__isnull=True,  # Solo farmacia central
                producto=detalle.producto,
                estado='disponible',
                deleted_at__isnull=True,
                cantidad_actual__gt=0,
                fecha_caducidad__gte=hoy,  # ISS-002 FIX: Solo lotes vigentes
            ).aggregate(total=Sum('cantidad_actual'))['total'] or 0
            
            if stock_disponible < cantidad_requerida:
                errores.append(
                    f"Stock insuficiente en farmacia central para {detalle.producto.clave}: "
                    f"requerido {cantidad_requerida}, disponible {stock_disponible}"
                )
        
        return errores
    
    def _validar_precondiciones_recibir(self) -> List[str]:
        """Valida precondiciones para marcar como recibida."""
        errores = []
        
        # Verificar que todos los items fueron surtidos (parcial o completo)
        for detalle in self.requisicion.detalles.all():
            if (detalle.cantidad_surtida or 0) <= 0:
                errores.append(f"El producto {detalle.producto.clave} no fue surtido")
        
        return errores
    
    def validar_transicion(self, destino: str, motivo: str = None) -> List[str]:
        """
        Valida una transición incluyendo precondiciones.
        
        Args:
            destino: Estado destino
            motivo: Motivo de la transición (requerido para rechazos)
            
        Returns:
            list: Lista de errores (vacía si es válida)
        """
        errores = []
        
        try:
            destino_enum = EstadoRequisicion(destino.lower())
        except ValueError:
            return [f"Estado '{destino}' no es válido"]
        
        # Validar transición en matriz
        if not self.puede_transicionar_a(destino):
            transiciones = self.get_transiciones_disponibles()
            return [
                f"Transición de '{self.estado_actual.value}' a '{destino}' no permitida. "
                f"Transiciones válidas: {', '.join(transiciones) or 'ninguna'}"
            ]
        
        # Validar precondiciones según destino
        if destino_enum == EstadoRequisicion.ENVIADA:
            errores.extend(self._validar_precondiciones_enviar())
        
        elif destino_enum == EstadoRequisicion.AUTORIZADA:
            errores.extend(self._validar_precondiciones_autorizar())
        
        elif destino_enum == EstadoRequisicion.SURTIDA:
            errores.extend(self._validar_precondiciones_surtir())
        
        elif destino_enum == EstadoRequisicion.RECIBIDA:
            errores.extend(self._validar_precondiciones_recibir())
        
        elif destino_enum == EstadoRequisicion.RECHAZADA:
            if not motivo or not motivo.strip():
                errores.append("Se requiere un motivo para rechazar la requisición")
        
        return errores
    
    @transaction.atomic
    def transicionar(
        self, 
        destino: str, 
        usuario=None, 
        motivo: str = None,
        observaciones: str = None,
        validar_precondiciones: bool = True
    ) -> bool:
        """
        Ejecuta una transición de estado.
        
        Args:
            destino: Estado destino
            usuario: Usuario que realiza la transición
            motivo: Motivo (requerido para rechazos)
            observaciones: Observaciones adicionales
            validar_precondiciones: Si validar precondiciones
            
        Returns:
            bool: True si la transición fue exitosa
            
        Raises:
            TransicionInvalidaError: Si la transición no es válida
            PrecondicionFallidaError: Si una precondición falla
        """
        destino_lower = destino.lower()
        
        # Validar transición y precondiciones
        if validar_precondiciones:
            errores = self.validar_transicion(destino_lower, motivo)
            if errores:
                raise PrecondicionFallidaError(
                    precondicion="validacion_transicion",
                    detalle="; ".join(errores)
                )
        elif not self.puede_transicionar_a(destino_lower):
            raise TransicionInvalidaError(
                origen=self.estado_actual.value,
                destino=destino_lower
            )
        
        estado_anterior = self.estado_actual.value
        destino_enum = EstadoRequisicion(destino_lower)
        
        # Aplicar cambios según el tipo de transición
        self.requisicion.estado = destino_enum.value
        
        if destino_enum == EstadoRequisicion.RECHAZADA:
            self.requisicion.motivo_rechazo = motivo
        
        if destino_enum in [EstadoRequisicion.AUTORIZADA, EstadoRequisicion.PARCIAL]:
            self.requisicion.fecha_autorizacion = timezone.now()
            if usuario:
                self.requisicion.usuario_autoriza = usuario
        
        if destino_enum == EstadoRequisicion.RECIBIDA:
            self.requisicion.fecha_recibido = timezone.now()
            if usuario:
                self.requisicion.usuario_recibe = usuario
            if observaciones:
                self.requisicion.observaciones_recepcion = observaciones
        
        # Guardar cambios
        self.requisicion.save()
        
        # Registrar en historial
        self._historial.append({
            'timestamp': timezone.now(),
            'origen': estado_anterior,
            'destino': destino_enum.value,
            'usuario': getattr(usuario, 'username', None),
            'motivo': motivo
        })
        
        logger.info(
            f"Requisición {self.requisicion.folio}: "
            f"transición {estado_anterior} → {destino_enum.value} "
            f"por {getattr(usuario, 'username', 'sistema')}"
        )
        
        return True
    
    def get_historial(self) -> List[Dict]:
        """Retorna el historial de transiciones de esta sesión."""
        return self._historial.copy()
    
    def __repr__(self):
        return f"<RequisicionStateMachine folio={self.requisicion.folio} estado={self.estado_actual.value}>"


# =============================================================================
# Mixin para ViewSets
# =============================================================================

class StateMachineMixin:
    """
    Mixin para ViewSets que provee acceso a la máquina de estados.
    
    Uso:
        class RequisicionViewSet(StateMachineMixin, viewsets.ModelViewSet):
            ...
            def autorizar(self, request, pk=None):
                sm = self.get_state_machine()
                sm.transicionar('autorizada', usuario=request.user)
    """
    
    def get_state_machine(self, instance=None) -> RequisicionStateMachine:
        """
        Obtiene la máquina de estados para la instancia actual.
        
        Args:
            instance: Instancia opcional (usa get_object() si no se proporciona)
            
        Returns:
            RequisicionStateMachine
        """
        if instance is None:
            instance = self.get_object()
        return RequisicionStateMachine(instance)
    
    def validar_transicion_o_error(self, estado_destino: str, motivo: str = None):
        """
        Valida una transición y lanza error HTTP si falla.
        
        Raises:
            ValidationError: Si la transición no es válida
        """
        sm = self.get_state_machine()
        errores = sm.validar_transicion(estado_destino, motivo)
        
        if errores:
            raise ValidationError({'estado': errores})
