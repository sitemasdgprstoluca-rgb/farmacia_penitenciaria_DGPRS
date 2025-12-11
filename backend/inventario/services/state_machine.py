"""
ISS-012: Máquina de estados formal para requisiciones.

Implementa un patrón State Machine robusto que:
- Define transiciones válidas entre estados
- Valida precondiciones para cada transición
- Registra historial de cambios de estado
- Emite eventos/hooks para acciones post-transición

ISS-001/002/003 FIX (audit8): Estados y transiciones importados desde
core.constants como FUENTE ÚNICA DE VERDAD.
"""
import logging
from datetime import datetime
from typing import Optional, Dict, List, Callable, Any
from dataclasses import dataclass, field
from enum import Enum

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

# ISS-001/002/003 FIX (audit8): Importar desde constants como FUENTE ÚNICA
from core.constants import (
    TRANSICIONES_REQUISICION,
    ESTADOS_SURTIBLES,
    ESTADOS_EDITABLES,
    ESTADOS_TERMINALES,
    ESTADOS_EDICION_LIMITADA,
    ESTADOS_SIN_EDICION,
)
from core.lote_helpers import LoteQueryHelper  # ISS-001 FIX (audit15)

logger = logging.getLogger(__name__)


class EstadoRequisicion(str, Enum):
    """
    Estados posibles de una requisición.
    ISS-DB-002: Alineados con CHECK constraint de BD Supabase.
    FLUJO V2: Estados jerárquicos con trazabilidad completa
    """
    # Estados del flujo del centro
    BORRADOR = 'borrador'                    # Médico creando la solicitud
    PENDIENTE_ADMIN = 'pendiente_admin'      # Esperando autorización Administrador Centro
    PENDIENTE_DIRECTOR = 'pendiente_director'  # Esperando autorización Director Centro
    
    # Estados del flujo de farmacia
    ENVIADA = 'enviada'                      # Enviada a Farmacia Central
    EN_REVISION = 'en_revision'              # Farmacia está revisando
    AUTORIZADA = 'autorizada'                # Farmacia autorizó + fecha recolección
    EN_SURTIDO = 'en_surtido'                # En proceso de preparación
    SURTIDA = 'surtida'                      # Lista para recolección
    ENTREGADA = 'entregada'                  # Entregada y confirmada
    
    # Estados finales negativos
    RECHAZADA = 'rechazada'                  # Rechazada en cualquier punto
    VENCIDA = 'vencida'                      # No se recolectó en fecha límite
    CANCELADA = 'cancelada'                  # Cancelada por el solicitante
    DEVUELTA = 'devuelta'                    # Devuelta al centro para corrección
    
    # Compatibilidad legacy
    PARCIAL = 'parcial'                      # Deprecated: usar en_surtido
    
    @classmethod
    def choices(cls):
        return [
            ('borrador', 'Borrador'),
            ('pendiente_admin', 'Pendiente Administrador'),
            ('pendiente_director', 'Pendiente Director'),
            ('enviada', 'Enviada'),
            ('en_revision', 'En Revisión'),
            ('autorizada', 'Autorizada'),
            ('en_surtido', 'En Surtido'),
            ('surtida', 'Surtida'),
            ('entregada', 'Entregada'),
            ('rechazada', 'Rechazada'),
            ('vencida', 'Vencida'),
            ('cancelada', 'Cancelada'),
            ('devuelta', 'Devuelta'),
            ('parcial', 'Parcialmente Surtida'),
        ]
    
    @classmethod
    def terminales(cls):
        """ISS-001/002/003 FIX (audit8): Estados terminales desde constants."""
        return [cls(e) for e in ESTADOS_TERMINALES if e in [m.value for m in cls]]
    
    @classmethod
    def editables(cls):
        """ISS-001/002/003 FIX (audit8): Estados editables desde constants."""
        return [cls(e) for e in ESTADOS_EDITABLES if e in [m.value for m in cls]]
    
    @classmethod
    def estados_sin_edicion(cls):
        """ISS-001/002/003 FIX (audit8): Estados sin edición desde constants."""
        return [cls(e) for e in ESTADOS_SIN_EDICION if e in [m.value for m in cls]]
    
    @classmethod
    def estados_edicion_limitada(cls):
        """ISS-001/002/003 FIX (audit8): Estados con edición limitada desde constants."""
        return [cls(e) for e in ESTADOS_EDICION_LIMITADA if e in [m.value for m in cls]]
    
    @classmethod
    def surtibles(cls):
        """ISS-001/002/003 FIX (audit8): Estados surtibles desde constants."""
        return [cls(e) for e in ESTADOS_SURTIBLES if e in [m.value for m in cls]]
    
    @classmethod
    def pendientes_centro(cls):
        """Estados donde el Centro debe actuar."""
        return [cls.BORRADOR, cls.DEVUELTA]
    
    @classmethod
    def pendientes_farmacia(cls):
        """Estados donde Farmacia debe actuar."""
        return [cls.ENVIADA, cls.EN_REVISION, cls.AUTORIZADA, cls.EN_SURTIDO]


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
    
    Define el flujo completo (alineado con BD Supabase):
    
    BORRADOR → ENVIADA → AUTORIZADA/PARCIAL/RECHAZADA
                            ↓
                         EN_SURTIDO → SURTIDA → ENTREGADA
                         
    Cualquier estado (excepto terminales) → CANCELADA
    
    ISS-001/002/003 FIX (audit8): MATRIZ_TRANSICIONES generada desde constants.
    """
    
    # Definición de todas las transiciones válidas
    TRANSICIONES: Dict[str, TransicionEstado] = {}
    
    # ISS-001/002/003 FIX (audit8): Generar matriz desde TRANSICIONES_REQUISICION
    @classmethod
    def _generar_matriz_transiciones(cls):
        """Genera MATRIZ_TRANSICIONES desde constants.TRANSICIONES_REQUISICION."""
        matriz = {}
        for origen_str, destinos_str in TRANSICIONES_REQUISICION.items():
            try:
                origen_enum = EstadoRequisicion(origen_str)
                destinos_enum = []
                for d in destinos_str:
                    try:
                        destinos_enum.append(EstadoRequisicion(d))
                    except ValueError:
                        pass  # Estado no existe en enum, ignorar
                matriz[origen_enum] = destinos_enum
            except ValueError:
                pass  # Estado no existe en enum, ignorar
        return matriz
    
    # Matriz generada dinámicamente desde constants
    MATRIZ_TRANSICIONES = None  # Se inicializa en __init_subclass__ o al primer uso
    
    @classmethod
    def get_matriz_transiciones(cls):
        """Obtener matriz de transiciones, generándola si es necesario."""
        if cls.MATRIZ_TRANSICIONES is None:
            cls.MATRIZ_TRANSICIONES = cls._generar_matriz_transiciones()
        return cls.MATRIZ_TRANSICIONES
    
    # Roles requeridos para cada tipo de transición
    # FLUJO V2: Roles jerárquicos del centro y farmacia
    ROLES_TRANSICION = {
        # Acciones del centro penitenciario
        'enviar_admin': ['medico'],
        'autorizar_admin': ['administrador_centro', 'admin'],
        'autorizar_director': ['director_centro', 'admin'],
        
        # Acciones de farmacia central
        'recibir_farmacia': ['farmacia', 'admin'],
        'autorizar_farmacia': ['farmacia', 'admin'],
        'surtir': ['farmacia', 'admin'],
        'confirmar_entrega': ['medico', 'administrador_centro', 'director_centro', 'centro', 'admin'],
        
        # Acciones especiales
        'devolver': ['administrador_centro', 'director_centro', 'farmacia', 'admin'],
        'reenviar': ['medico', 'administrador_centro', 'admin'],
        'rechazar': ['administrador_centro', 'director_centro', 'farmacia', 'admin'],
        'cancelar': ['medico', 'administrador_centro', 'director_centro', 'farmacia', 'admin'],
        'marcar_vencida': ['farmacia', 'admin'],
        
        # Compatibilidad legacy
        'enviar': ['medico', 'centro', 'farmacia', 'admin'],
        'autorizar': ['farmacia', 'admin'],
        'recibir': ['medico', 'centro', 'farmacia', 'admin']
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
        
        transiciones_permitidas = self.get_matriz_transiciones().get(self.estado_actual, [])
        return destino_enum in transiciones_permitidas
    
    def get_transiciones_disponibles(self) -> List[str]:
        """
        Retorna las transiciones disponibles desde el estado actual.
        
        Returns:
            list: Lista de estados destino posibles
        """
        transiciones = self.get_matriz_transiciones().get(self.estado_actual, [])
        return [t.value for t in transiciones]
    
    def es_estado_terminal(self) -> bool:
        """Verifica si el estado actual es terminal."""
        return self.estado_actual in EstadoRequisicion.terminales()
    
    def es_editable(self) -> bool:
        """Verifica si la requisición puede editarse."""
        return self.estado_actual in EstadoRequisicion.editables()
    
    def validar_edicion(self, campos_editados: List[str] = None) -> List[str]:
        """
        ISS-004 FIX (audit4): Valida si la edición es permitida.
        
        Args:
            campos_editados: Lista de campos que se quieren editar
            
        Returns:
            list: Lista de errores (vacía si es permitido)
        """
        errores = []
        campos_editados = campos_editados or []
        
        # Campos sensibles que afectan inventario/autorizaciones
        campos_sensibles = {
            'cantidad_solicitada', 'cantidad_autorizada', 'producto',
            'detalles', 'items', 'centro_destino'
        }
        
        # Campos que siempre se pueden editar (notas/observaciones)
        campos_libres = {'notas', 'observaciones', 'comentario'}
        
        campos_sensibles_editados = set(campos_editados) & campos_sensibles
        
        # Estados sin edición
        if self.estado_actual in EstadoRequisicion.estados_sin_edicion():
            errores.append(
                f"ISS-004: No se permite editar requisiciones en estado '{self.estado_actual.value}'. "
                "La requisición ya fue autorizada o procesada."
            )
            return errores
        
        # Estados con edición limitada
        if self.estado_actual in EstadoRequisicion.estados_edicion_limitada():
            if campos_sensibles_editados:
                errores.append(
                    f"ISS-004: En estado '{self.estado_actual.value}' solo se pueden editar "
                    f"observaciones/notas. No se permite modificar: {', '.join(campos_sensibles_editados)}. "
                    "La requisición debe devolverse a borrador para cambios mayores."
                )
        
        return errores
    
    def requiere_revalidacion(self) -> bool:
        """
        ISS-004 FIX (audit4): Indica si el estado actual requiere revalidación tras edición.
        """
        return self.estado_actual in EstadoRequisicion.estados_edicion_limitada()
    
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
        ISS-001 FIX (audit4): Requiere estado en_surtido, NO puede venir de autorizada directamente.
        ISS-001 FIX (audit11): Solo cuenta lotes con estado 'disponible'.
        """
        from django.db.models import Sum
        from django.utils import timezone
        from core.models import Lote
        
        hoy = timezone.now().date()
        errores = []
        
        # ISS-001 FIX (audit4): Validar que viene de en_surtido
        if self.estado_actual != EstadoRequisicion.EN_SURTIDO:
            errores.append(
                f"Solo se puede surtir desde estado 'en_surtido'. "
                f"Estado actual: '{self.estado_actual.value}'"
            )
            return errores
        
        for detalle in self.requisicion.detalles.select_related('producto'):
            cantidad_requerida = (detalle.cantidad_autorizada or detalle.cantidad_solicitada) - (detalle.cantidad_surtida or 0)
            if cantidad_requerida <= 0:
                continue
            
            # ISS-001 FIX (audit15): Usar LoteQueryHelper - NO usar estado__in
            # El campo 'estado' es propiedad calculada, no existe en BD
            stock_disponible = LoteQueryHelper.get_stock_disponible(
                producto=detalle.producto,
                solo_farmacia_central=True,
            )
            
            if stock_disponible < cantidad_requerida:
                errores.append(
                    f"Stock insuficiente en farmacia central para {detalle.producto.clave}: "
                    f"requerido {cantidad_requerida}, disponible {stock_disponible}"
                )
        
        return errores
    
    def _validar_precondiciones_en_surtido(self) -> List[str]:
        """
        ISS-003 FIX (audit10): Valida precondiciones para iniciar surtido.
        ISS-001 FIX (audit11): Solo cuenta lotes con estado 'disponible'.
        
        Esta validación se ejecuta al transicionar de AUTORIZADA → EN_SURTIDO.
        Verifica ANTES de reservar inventario que:
        1. Hay stock suficiente en farmacia central
        2. Hay lotes vigentes (no caducados)
        3. Hay lotes con estado 'disponible' (no bloqueados/retirados)
        4. Los lotes tienen cantidad mínima requerida
        
        CRÍTICO: Esta validación previene requisiciones que no pueden surtirse,
        evitando inventarios negativos y discrepancias.
        """
        from django.db.models import Sum
        from django.utils import timezone
        from core.models import Lote
        
        hoy = timezone.now().date()
        errores = []
        
        # Validar que viene de autorizada
        if self.estado_actual not in [EstadoRequisicion.AUTORIZADA]:
            errores.append(
                f"Solo se puede iniciar surtido desde estado 'autorizada'. "
                f"Estado actual: '{self.estado_actual.value}'"
            )
            return errores
        
        # Validar stock y lotes para cada producto
        for detalle in self.requisicion.detalles.select_related('producto'):
            cantidad_requerida = detalle.cantidad_autorizada or detalle.cantidad_solicitada
            if cantidad_requerida <= 0:
                errores.append(
                    f"Cantidad inválida para {detalle.producto.clave}: {cantidad_requerida}"
                )
                continue
            
            # ISS-001 FIX (audit15): Usar LoteQueryHelper - NO usar estado__in
            # El campo 'estado' es propiedad calculada, no existe en BD
            validacion = LoteQueryHelper.validar_stock_surtido(
                producto=detalle.producto,
                cantidad_requerida=cantidad_requerida,
                solo_farmacia_central=True,
            )
            
            stock_disponible = validacion['stock_disponible']
            
            if not validacion['valido']:
                # Listar lotes disponibles para diagnóstico
                lotes_info = [
                    f"  - Lote {l['numero_lote']}: {l['cantidad_actual']} uds (vence: {l['fecha_caducidad']})"
                    for l in validacion['lotes']
                ]
                lotes_str = "\n".join(lotes_info) if lotes_info else "  (ninguno disponible)"
                
                errores.append(
                    f"Stock insuficiente para '{detalle.producto.clave}' ({detalle.producto.nombre}): "
                    f"requerido {cantidad_requerida}, disponible {stock_disponible}.\n"
                    f"Lotes disponibles en farmacia central:\n{lotes_str}"
                )
            
            # ISS-003 FIX (audit15): Advertencia de lotes próximos a vencer
            # Usar advertencias del helper
            if validacion['advertencias'] and validacion['valido']:
                logger.warning(
                    f"Requisición {self.requisicion.folio or self.requisicion.id}: "
                    f"Producto {detalle.producto.clave}: {validacion['advertencias']}"
                )
        
        return errores
    
    def _validar_precondiciones_cancelar(self) -> List[str]:
        """
        ISS-002 FIX (audit4): Valida precondiciones para cancelar.
        
        Verifica:
        1. Estado permite cancelación
        2. No hay movimientos de inventario asociados
        3. Si hay movimientos, requiere proceso de devolución
        """
        from core.models import Movimiento
        
        errores = []
        
        # ISS-002 FIX: Estados que NO permiten cancelación
        estados_sin_cancelar = [
            EstadoRequisicion.SURTIDA,
            EstadoRequisicion.ENTREGADA,
            EstadoRequisicion.RECHAZADA,
            EstadoRequisicion.VENCIDA,
            EstadoRequisicion.CANCELADA
        ]
        
        if self.estado_actual in estados_sin_cancelar:
            errores.append(
                f"No se puede cancelar desde estado '{self.estado_actual.value}'. "
                "Las requisiciones surtidas o finalizadas no pueden cancelarse."
            )
            return errores
        
        # ISS-002 FIX: Verificar si hay movimientos de inventario
        movimientos = Movimiento.objects.filter(requisicion=self.requisicion)
        if movimientos.exists():
            total_mov = movimientos.count()
            errores.append(
                f"La requisición tiene {total_mov} movimientos de inventario asociados. "
                "No se puede cancelar sin revertir los movimientos primero. "
                "Use el proceso de devolución para reintegrar el stock."
            )
        
        return errores
    
    def _validar_segregacion_funciones(self, usuario, accion: str) -> List[str]:
        """
        ISS-003 FIX (audit4): Valida segregación de funciones.
        
        Verifica que el usuario no haya ejecutado una acción incompatible
        en la misma requisición.
        
        Args:
            usuario: Usuario que intenta la acción
            accion: Acción a ejecutar (autorizar_farmacia, surtir, etc.)
        """
        errores = []
        
        if not usuario or not hasattr(self.requisicion, 'id'):
            return errores
        
        # Mapeo de acciones a campos de usuario en la requisición
        acciones_usuario = {
            'crear': self.requisicion.solicitante,
            'autorizar_admin': getattr(self.requisicion, 'administrador_centro', None),
            'autorizar_director': getattr(self.requisicion, 'director_centro', None),
            'autorizar_farmacia': getattr(self.requisicion, 'autorizador_farmacia', None),
            'surtir': getattr(self.requisicion, 'surtidor', None),
        }
        
        # Reglas de segregación
        reglas = [
            ('crear', 'autorizar_admin', 'El creador no puede autorizar como administrador'),
            ('crear', 'autorizar_director', 'El creador no puede autorizar como director'),
            ('crear', 'autorizar_farmacia', 'El creador no puede autorizar en farmacia'),
            ('autorizar_admin', 'autorizar_director', 'El mismo usuario no puede hacer ambas autorizaciones del centro'),
            ('autorizar_farmacia', 'surtir', 'El autorizador de farmacia no puede ser el surtidor'),
        ]
        
        usuario_id = getattr(usuario, 'id', None)
        if not usuario_id:
            return errores
        
        for accion1, accion2, mensaje in reglas:
            if accion in [accion1, accion2]:
                # Verificar la otra acción del par
                otra_accion = accion2 if accion == accion1 else accion1
                usuario_otra = acciones_usuario.get(otra_accion)
                
                if usuario_otra and getattr(usuario_otra, 'id', None) == usuario_id:
                    errores.append(
                        f"ISS-003: Segregación de funciones - {mensaje}. "
                        f"Usuario {usuario.username} ya ejecutó '{otra_accion}' en esta requisición."
                    )
        
        return errores
    
    def _validar_precondiciones_recibir(self) -> List[str]:
        """
        ISS-003 FIX (audit8): Valida precondiciones para marcar como recibida/entregada.
        
        Validaciones:
        1. Todos los items deben tener cantidad_surtida > 0
        2. Deben existir movimientos de inventario correspondientes
        3. No debe haber entregas duplicadas
        """
        from django.db.models import Sum
        from core.models import Movimiento
        
        errores = []
        
        # 1. Verificar que todos los items fueron surtidos (parcial o completo)
        for detalle in self.requisicion.detalles.all():
            if (detalle.cantidad_surtida or 0) <= 0:
                errores.append(f"El producto {detalle.producto.clave} no fue surtido")
        
        # ISS-003 FIX (audit8): Verificar existencia de movimientos de inventario
        # Debe haber movimientos de salida (farmacia) y entrada (centro)
        movimientos_salida = Movimiento.objects.filter(
            requisicion=self.requisicion,
            tipo='salida'
        ).aggregate(total=Sum('cantidad'))['total'] or 0
        
        movimientos_entrada = Movimiento.objects.filter(
            requisicion=self.requisicion,
            tipo='entrada'
        ).aggregate(total=Sum('cantidad'))['total'] or 0
        
        if movimientos_salida == 0 and movimientos_entrada == 0:
            errores.append(
                "No se encontraron movimientos de inventario para esta requisición. "
                "El surtido debe completarse antes de confirmar la entrega."
            )
        
        # ISS-003 FIX (audit8): Verificar balance salidas/entradas
        # Las salidas son negativas, entradas positivas - balance debe ser ~0
        balance = abs(movimientos_salida) - movimientos_entrada
        if abs(balance) > 0.01:  # Pequeño margen por redondeos
            logger.warning(
                f"ISS-003: Inconsistencia de movimientos en requisición {self.requisicion.numero}. "
                f"Salidas: {abs(movimientos_salida)}, Entradas: {movimientos_entrada}, Balance: {balance}"
            )
            errores.append(
                f"Inconsistencia de inventario: salidas ({abs(movimientos_salida)}) "
                f"no coinciden con entradas ({movimientos_entrada})"
            )
        
        # ISS-003 FIX (audit8): Verificar que no es entrega duplicada
        if self.requisicion.estado == 'entregada':
            errores.append("Esta requisición ya fue marcada como entregada anteriormente")
        
        return errores
    
    def validar_transicion(self, destino: str, motivo: str = None, usuario=None) -> List[str]:
        """
        Valida una transición incluyendo precondiciones.
        
        ISS-003 FIX (audit4): Incluye validación de segregación de funciones.
        
        Args:
            destino: Estado destino
            motivo: Motivo de la transición (requerido para rechazos/devoluciones)
            usuario: Usuario que ejecuta la transición (para segregación)
            
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
        # FLUJO V2: Precondiciones para cada tipo de transición
        
        # Enviar a administrador (médico → admin)
        if destino_enum == EstadoRequisicion.PENDIENTE_ADMIN:
            errores.extend(self._validar_precondiciones_enviar())
            if usuario:
                errores.extend(self._validar_segregacion_funciones(usuario, 'enviar_admin'))
        
        # Enviar a farmacia (director → farmacia)
        elif destino_enum == EstadoRequisicion.ENVIADA:
            errores.extend(self._validar_precondiciones_enviar())
            if usuario:
                errores.extend(self._validar_segregacion_funciones(usuario, 'autorizar_director'))
        
        # Autorizar (admin/director/farmacia)
        # ISS-003 FIX (audit4): Validar segregación según el rol
        elif destino_enum == EstadoRequisicion.PENDIENTE_DIRECTOR:
            errores.extend(self._validar_precondiciones_autorizar())
            if usuario:
                errores.extend(self._validar_segregacion_funciones(usuario, 'autorizar_admin'))
        
        elif destino_enum == EstadoRequisicion.EN_REVISION:
            errores.extend(self._validar_precondiciones_autorizar())
        
        elif destino_enum == EstadoRequisicion.AUTORIZADA:
            errores.extend(self._validar_precondiciones_autorizar())
            if usuario:
                errores.extend(self._validar_segregacion_funciones(usuario, 'autorizar_farmacia'))
        
        # ISS-003 FIX (audit10): Transición a en_surtido requiere validación de stock
        # Esta es la transición crítica donde se reserva inventario
        elif destino_enum == EstadoRequisicion.EN_SURTIDO:
            # Validar que hay productos autorizados
            errores.extend(self._validar_precondiciones_autorizar())
            # ISS-003 FIX (audit10): Validar existencias ANTES de iniciar surtido
            errores.extend(self._validar_precondiciones_en_surtido())
        
        # Surtir - ISS-003 FIX: segregación autorizar/surtir
        elif destino_enum == EstadoRequisicion.SURTIDA:
            errores.extend(self._validar_precondiciones_surtir())
            if usuario:
                errores.extend(self._validar_segregacion_funciones(usuario, 'surtir'))
        
        # Entregar
        elif destino_enum == EstadoRequisicion.ENTREGADA:
            errores.extend(self._validar_precondiciones_recibir())
            # Validar fecha límite de recolección
            if hasattr(self.requisicion, 'fecha_recoleccion_limite'):
                from django.utils import timezone
                fecha_limite = self.requisicion.fecha_recoleccion_limite
                if fecha_limite and timezone.now() > fecha_limite:
                    errores.append(
                        f"La fecha límite de recolección ({fecha_limite.strftime('%d/%m/%Y %H:%M')}) "
                        "ha expirado. La requisición debe marcarse como vencida."
                    )
        
        # Rechazar - requiere motivo
        elif destino_enum == EstadoRequisicion.RECHAZADA:
            if not motivo or not motivo.strip():
                errores.append("Se requiere un motivo para rechazar la requisición")
        
        # Devolver - requiere motivo
        elif destino_enum == EstadoRequisicion.DEVUELTA:
            if not motivo or not motivo.strip():
                errores.append("Se requiere un motivo para devolver la requisición")
        
        # Vencida - validar que esté surtida
        elif destino_enum == EstadoRequisicion.VENCIDA:
            if self.estado_actual != EstadoRequisicion.SURTIDA:
                errores.append("Solo requisiciones surtidas pueden marcarse como vencidas")
        
        # ISS-002 FIX (audit4): Cancelar - validar movimientos
        elif destino_enum == EstadoRequisicion.CANCELADA:
            errores.extend(self._validar_precondiciones_cancelar())
        
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
        # ISS-003 FIX (audit4): Pasar usuario para validar segregación
        if validar_precondiciones:
            errores = self.validar_transicion(destino_lower, motivo, usuario=usuario)
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
        
        # FLUJO V2: Registrar actores y fechas según la transición
        
        # Enviar a administrador del centro
        if destino_enum == EstadoRequisicion.PENDIENTE_ADMIN:
            self.requisicion.fecha_envio_admin = timezone.now()
        
        # Autorización del administrador del centro
        elif destino_enum == EstadoRequisicion.PENDIENTE_DIRECTOR:
            self.requisicion.fecha_autorizacion_admin = timezone.now()
            self.requisicion.fecha_envio_director = timezone.now()
            if usuario:
                self.requisicion.administrador_centro = usuario
        
        # Autorización del director → enviar a farmacia
        elif destino_enum == EstadoRequisicion.ENVIADA:
            self.requisicion.fecha_autorizacion_director = timezone.now()
            self.requisicion.fecha_envio_farmacia = timezone.now()
            if usuario:
                self.requisicion.director_centro = usuario
        
        # Farmacia recibe
        elif destino_enum == EstadoRequisicion.EN_REVISION:
            self.requisicion.fecha_recepcion_farmacia = timezone.now()
            if usuario:
                self.requisicion.receptor_farmacia = usuario
        
        # Farmacia autoriza
        elif destino_enum == EstadoRequisicion.AUTORIZADA:
            self.requisicion.fecha_autorizacion_farmacia = timezone.now()
            self.requisicion.fecha_autorizacion = timezone.now()
            if usuario:
                self.requisicion.autorizador_farmacia = usuario
                self.requisicion.autorizador = usuario
        
        # Surtido
        elif destino_enum == EstadoRequisicion.SURTIDA:
            self.requisicion.fecha_surtido = timezone.now()
            if usuario:
                self.requisicion.surtidor = usuario
        
        # Entrega
        elif destino_enum == EstadoRequisicion.ENTREGADA:
            self.requisicion.fecha_entrega = timezone.now()
            self.requisicion.fecha_firma_recepcion = timezone.now()
            if usuario:
                self.requisicion.usuario_firma_recepcion = usuario
            if observaciones:
                self.requisicion.notas = (self.requisicion.notas or '') + f'\n[Recepción] {observaciones}'
        
        # Rechazo
        elif destino_enum == EstadoRequisicion.RECHAZADA:
            self.requisicion.motivo_rechazo = motivo
        
        # Devolución
        elif destino_enum == EstadoRequisicion.DEVUELTA:
            self.requisicion.motivo_devolucion = motivo
        
        # Vencimiento
        elif destino_enum == EstadoRequisicion.VENCIDA:
            self.requisicion.fecha_vencimiento = timezone.now()
            self.requisicion.motivo_vencimiento = motivo or "Fecha límite de recolección expirada"
        
        # Compatibilidad legacy
        elif destino_enum == EstadoRequisicion.PARCIAL:
            self.requisicion.fecha_autorizacion = timezone.now()
            if usuario:
                self.requisicion.autorizador = usuario
        
        # Guardar cambios
        self.requisicion.save()
        
        # ISS-005 FIX (audit8): Persistir historial en BD para trazabilidad
        self._persistir_historial(estado_anterior, destino_enum.value, usuario, motivo)
        
        # Mantener historial en memoria para compatibilidad
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
    
    def _persistir_historial(self, estado_anterior, estado_nuevo, usuario, motivo):
        """
        ISS-005 FIX (audit8): Persiste transición de estado en tabla de historial.
        
        Usa RequisicionHistorialEstados para auditoría completa y persistente.
        """
        try:
            from core.models import RequisicionHistorialEstados
            
            # Determinar acción según la transición
            accion = self._determinar_accion_historial(estado_anterior, estado_nuevo)
            
            RequisicionHistorialEstados.objects.create(
                requisicion=self.requisicion,
                estado_anterior=estado_anterior,
                estado_nuevo=estado_nuevo,
                accion=accion,
                usuario=usuario,
                observaciones=motivo or f'Transición automática: {estado_anterior} → {estado_nuevo}',
                ip_address=None,  # Se puede obtener del request si está disponible
            )
            
            logger.debug(
                f"ISS-005: Historial persistido para requisición {self.requisicion.numero}: "
                f"{estado_anterior} → {estado_nuevo}"
            )
        except Exception as e:
            # No bloquear la transición si falla el historial, solo advertir
            logger.error(
                f"ISS-005: Error persistiendo historial para requisición {self.requisicion.numero}: {e}"
            )
    
    def _determinar_accion_historial(self, estado_anterior, estado_nuevo):
        """Determina el código de acción para el historial."""
        # Mapeo de transiciones a acciones
        transicion_a_accion = {
            ('borrador', 'pendiente_admin'): 'enviar_admin',
            ('pendiente_admin', 'pendiente_director'): 'autorizar_admin',
            ('pendiente_director', 'enviada'): 'autorizar_director',
            ('enviada', 'en_revision'): 'recibir_farmacia',
            ('en_revision', 'autorizada'): 'autorizar_farmacia',
            ('autorizada', 'en_surtido'): 'iniciar_surtido',
            ('en_surtido', 'surtida'): 'completar_surtido',
            ('surtida', 'entregada'): 'confirmar_entrega',
            # Estados negativos
            ('en_revision', 'rechazada'): 'rechazar',
            ('en_revision', 'devuelta'): 'devolver',
        }
        
        return transicion_a_accion.get((estado_anterior, estado_nuevo), 'transicion')
    
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
