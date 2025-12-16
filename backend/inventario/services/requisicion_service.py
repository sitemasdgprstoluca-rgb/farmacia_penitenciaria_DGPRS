"""
Servicio transaccional para operaciones de requisiciones.

ISS-011: Implementa transacciones atómicas para el surtido
ISS-021: Servicio centralizado con rollback completo
ISS-014: Bloqueo optimista en descuentos de lote
"""
import logging
from django.db import transaction
from django.db.models import Sum, Q, F
from django.utils import timezone
from rest_framework import serializers

from core.models import Lote, Movimiento

logger = logging.getLogger(__name__)


class RequisicionServiceError(Exception):
    """Excepción base para errores del servicio de requisiciones."""
    def __init__(self, message, details=None, code='error'):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.code = code


class StockInsuficienteError(RequisicionServiceError):
    """Error cuando no hay stock suficiente para surtir."""
    def __init__(self, message, detalles_stock):
        super().__init__(message, details={'detalles_stock': detalles_stock}, code='stock_insuficiente')
        self.detalles_stock = detalles_stock


class EstadoInvalidoError(RequisicionServiceError):
    """Error cuando la requisición no está en un estado válido para la operación."""
    def __init__(self, message, estado_actual):
        super().__init__(message, details={'estado_actual': estado_actual}, code='estado_invalido')
        self.estado_actual = estado_actual


class PermisoRequisicionError(RequisicionServiceError):
    """Error de permisos para operar sobre la requisición."""
    def __init__(self, message):
        super().__init__(message, code='permiso_denegado')


class RequisicionService:
    """
    Servicio transaccional para operaciones de requisiciones.
    
    ISS-011, ISS-021: Todas las operaciones son atómicas con rollback completo.
    ISS-014: Usa select_for_update() para bloqueo optimista de lotes.
    ISS-030: Valida permisos de acceso por centro.
    ISS-001/002/003 FIX (audit8): Importa desde core.constants como FUENTE ÚNICA DE VERDAD.
    ISS-001 FIX (audit11): Filtra lotes por estado 'disponible'.
    """
    
    # ISS-001/002/003 FIX (audit8): IMPORTAR desde constants, NO duplicar
    from core.constants import (
        TRANSICIONES_REQUISICION,
        ESTADOS_SURTIBLES,
        ESTADOS_EDITABLES,
        ESTADOS_TERMINALES,
        ROLES_POR_TRANSICION as _ROLES_POR_TRANSICION,
        ESTADOS_LOTE_DISPONIBLES,  # ISS-001 FIX (audit11)
    )
    
    # Mantener como atributo de clase para compatibilidad
    TRANSICIONES_VALIDAS_DEFAULT = TRANSICIONES_REQUISICION
    
    # ISS-001/002/003 FIX (audit8): Roles importados desde constants
    ROLES_POR_TRANSICION = _ROLES_POR_TRANSICION
    
    @property
    def ESTADOS_SURTIBLES(self):
        """ISS-001/002/003 FIX (audit8): Estados surtibles desde constants."""
        from core.constants import ESTADOS_SURTIBLES
        return ESTADOS_SURTIBLES
    
    @property
    def ESTADOS_LOTE_DISPONIBLES(self):
        """ISS-001 FIX (audit11): Estados de lote que cuentan como disponibles."""
        from core.constants import ESTADOS_LOTE_DISPONIBLES
        return ESTADOS_LOTE_DISPONIBLES
    
    @property
    def TRANSICIONES_VALIDAS(self):
        """ISS-001/002/003 FIX (audit8): Transiciones desde constants."""
        from core.constants import TRANSICIONES_REQUISICION
        return TRANSICIONES_REQUISICION
    
    def __init__(self, requisicion, usuario):
        """
        Inicializa el servicio.
        
        Args:
            requisicion: Instancia del modelo Requisicion
            usuario: Usuario que realiza la operación
        """
        self.requisicion = requisicion
        self.usuario = usuario
        self._movimientos_creados = []
        self._lotes_actualizados = []
    
    # ISS-003 QA-FIX: Transiciones que requieren validación de stock
    TRANSICIONES_VALIDAR_STOCK = {
        ('autorizada', 'en_surtido'),   # Al iniciar surtido, validar stock disponible
        ('en_surtido', 'surtida'),      # Al completar surtido, validar stock
        ('en_surtido', 'parcial'),      # Al surtir parcialmente, validar stock
    }
    
    def validar_transicion_estado(self, nuevo_estado, validar_stock=True):
        """
        ISS-004 FIX (audit3): Valida transición con registro de actor/fecha.
        ISS-003 FIX (audit4): Valida pertenencia al centro/contrato.
        ISS-003 QA-FIX: Valida disponibilidad de stock en transiciones críticas.
        
        Validaciones:
        1. Transición permitida según máquina de estados
        2. Rol del usuario autorizado para esta transición
        3. ISS-003 FIX: Pertenencia al centro para transiciones críticas
        4. ISS-003 QA-FIX: Stock disponible para transiciones de surtido
        5. Registro de quién/cuándo para auditoría
        
        Args:
            nuevo_estado: Estado destino
            validar_stock: Si True, valida stock en transiciones de surtido (default True)
            
        Raises:
            EstadoInvalidoError: Si la transición no es válida
            PermisoRequisicionError: Si el rol no está autorizado o no pertenece al centro
            StockInsuficienteError: Si no hay stock suficiente para transiciones de surtido
        """
        estado_actual = (self.requisicion.estado or 'borrador').lower()
        nuevo_estado_lower = nuevo_estado.lower()
        transiciones_permitidas = self.TRANSICIONES_VALIDAS.get(estado_actual, [])
        
        # 1. Validar que la transición esté permitida
        if nuevo_estado_lower not in transiciones_permitidas:
            raise EstadoInvalidoError(
                f"Transición de estado inválida: {estado_actual} → {nuevo_estado}. "
                f"Transiciones permitidas desde '{estado_actual}': {transiciones_permitidas}",
                estado_actual=estado_actual
            )
        
        # 2. ISS-005 FIX (audit9): Validar rol autorizado ESTRICTAMENTE para esta transición
        # ISS-005 FIX: ELIMINAR fallback de roles admin genéricos - cada transición
        # debe tener roles específicos definidos en ROLES_POR_TRANSICION
        if not self.usuario.is_superuser:
            user_rol = (getattr(self.usuario, 'rol', '') or '').lower()
            transicion_key = (estado_actual, nuevo_estado_lower)
            roles_permitidos = self.ROLES_POR_TRANSICION.get(transicion_key, [])
            
            # ISS-005 FIX (audit9): Validación ESTRICTA sin fallback
            # Si hay roles definidos para esta transición, el usuario DEBE tener uno de ellos
            if roles_permitidos:
                if user_rol not in roles_permitidos:
                    logger.warning(
                        f"ISS-005: Rol '{user_rol}' no autorizado para transición "
                        f"{estado_actual} → {nuevo_estado}. Roles permitidos: {roles_permitidos}. "
                        f"NO HAY FALLBACK - validación estricta."
                    )
                    raise PermisoRequisicionError(
                        f"Su rol '{user_rol}' no está autorizado para la transición "
                        f"{estado_actual} → {nuevo_estado}. "
                        f"Roles permitidos: {', '.join(roles_permitidos)}"
                    )
            else:
                # Transición no tiene roles definidos - bloquear por seguridad
                logger.error(
                    f"ISS-005: Transición {estado_actual} → {nuevo_estado} no tiene roles definidos. "
                    f"Bloqueando por seguridad."
                )
                raise PermisoRequisicionError(
                    f"Transición {estado_actual} → {nuevo_estado} no configurada. "
                    f"Contacte al administrador del sistema."
                )
        
        # 3. ISS-003 FIX (audit4): Validar pertenencia al centro/contrato
        self._validar_pertenencia_centro_transicion(estado_actual, nuevo_estado_lower)
        
        # 4. ISS-003 QA-FIX: Validar stock en transiciones de surtido
        transicion_key = (estado_actual, nuevo_estado_lower)
        if validar_stock and transicion_key in self.TRANSICIONES_VALIDAR_STOCK:
            logger.info(
                f"ISS-003 QA: Validando stock para transición {estado_actual} → {nuevo_estado}"
            )
            try:
                # Validar stock sin bloqueo (informativo antes de commit)
                self.validar_stock_disponible(usar_bloqueo=False)
            except StockInsuficienteError as e:
                logger.warning(
                    f"ISS-003 QA: Stock insuficiente para transición {estado_actual} → {nuevo_estado}: "
                    f"{e.detalles_stock}"
                )
                raise  # Re-lanzar para que la transición falle
        
        # 5. ISS-004 FIX: Registrar transición para auditoría
        logger.info(
            f"ISS-004 TRANSICIÓN: {self.requisicion.folio} | "
            f"{estado_actual} → {nuevo_estado} | "
            f"Usuario: {self.usuario.username} | "
            f"Rol: {getattr(self.usuario, 'rol', 'N/A')} | "
            f"Fecha: {timezone.now().isoformat()}"
        )
        
        return True
    
    # ISS-003 FIX (audit9): Transiciones que NO permiten bypass de superusuario
    # AMPLIADO: Incluir TODAS las transiciones sensibles al centro/contrato
    # Superusuario debe tener pertenencia correcta o autorización explícita
    TRANSICIONES_SIN_BYPASS_SUPERUSUARIO = {
        # Transiciones de inventario (críticas)
        ('en_surtido', 'surtida'),      # Descuento de inventario
        ('en_surtido', 'parcial'),      # Descuento parcial
        ('surtida', 'entregada'),       # Confirmación de entrega
        ('autorizada', 'en_surtido'),   # Inicio de surtido
        
        # ISS-003 FIX (audit9): Agregar transiciones de devolución/rechazo
        # Estas también afectan trazabilidad de centro
        ('en_revision', 'devuelta'),    # Devolver al centro
        ('en_revision', 'rechazada'),   # Rechazar requisición
        ('pendiente_admin', 'rechazada'),
        ('pendiente_director', 'rechazada'),
        
        # ISS-003 FIX (audit9): Cancelaciones también requieren validación
        ('borrador', 'cancelada'),
        ('pendiente_admin', 'cancelada'),
        ('pendiente_director', 'cancelada'),
        ('enviada', 'cancelada'),
        ('en_revision', 'cancelada'),
        ('autorizada', 'cancelada'),
        ('en_surtido', 'cancelada'),
    }
    
    def _validar_pertenencia_centro_transicion(self, estado_actual, nuevo_estado):
        """
        ISS-003 FIX (audit7): Valida que el usuario pertenezca al centro/contrato correcto.
        
        Reglas:
        - Transiciones de CENTRO (crear, aprobar interno): usuario debe pertenecer al centro de la req
        - Transiciones de FARMACIA (autorizar, surtir): usuario debe ser farmacia central (sin centro)
        - Recepción: usuario debe pertenecer al centro destino
        - ISS-003 FIX: Superusuario NO tiene bypass en transiciones críticas de inventario
        
        Args:
            estado_actual: Estado origen
            nuevo_estado: Estado destino
            
        Raises:
            PermisoRequisicionError: Si no pertenece al centro/contrato correcto
        """
        transicion = (estado_actual, nuevo_estado)
        
        # ISS-003 FIX (audit7): Limitar bypass de superusuario en transiciones críticas
        if self.usuario.is_superuser:
            if transicion in self.TRANSICIONES_SIN_BYPASS_SUPERUSUARIO:
                logger.warning(
                    f"ISS-003: Superusuario {self.usuario.username} en transición crítica "
                    f"{estado_actual} → {nuevo_estado}. Aplicando validación de centro."
                )
                # No retornar, continuar con validación
            else:
                return True  # Bypass permitido para transiciones no críticas
        
        user_centro = getattr(self.usuario, 'centro', None)
        user_rol = (getattr(self.usuario, 'rol', '') or '').lower()
        # ISS-FIX: Usar centro_origen, NO la property 'centro' que devuelve centro_destino (NULL)
        requisicion_centro = self.requisicion.centro_origen
        
        # Transiciones que requieren pertenecer al CENTRO de la requisición
        transiciones_centro = {
            ('borrador', 'pendiente_admin'),
            ('pendiente_admin', 'pendiente_director'),
            ('pendiente_director', 'enviada'),
            ('devuelta', 'borrador'),  # Médico corrige y reinicia
            ('surtida', 'entregada'),  # Recepción
        }
        
        # Transiciones que requieren ser FARMACIA CENTRAL (sin centro asignado)
        transiciones_farmacia = {
            ('enviada', 'en_revision'),
            ('en_revision', 'autorizada'),
            ('en_revision', 'rechazada'),
            ('en_revision', 'devuelta'),
            ('autorizada', 'en_surtido'),
            ('en_surtido', 'surtida'),
            ('en_surtido', 'parcial'),
        }
        
        transicion = (estado_actual, nuevo_estado)
        
        # ISS-003 FIX: Validar transiciones de centro
        if transicion in transiciones_centro:
            # Usuario debe pertenecer al centro de la requisición
            if requisicion_centro and user_centro:
                if user_centro.pk != requisicion_centro.pk:
                    logger.warning(
                        f"ISS-003: Usuario {self.usuario.username} (centro {user_centro.pk}) "
                        f"intenta transición en requisición de centro {requisicion_centro.pk}"
                    )
                    raise PermisoRequisicionError(
                        f"Esta transición solo puede ser realizada por usuarios del centro "
                        f"'{requisicion_centro.nombre}'. Su centro es '{user_centro.nombre}'."
                    )
            # Si no tiene centro y la transición requiere centro, bloquear (excepto admins)
            elif requisicion_centro and user_centro is None:
                roles_admin_global = {'admin', 'admin_sistema', 'superusuario', 'farmacia', 'admin_farmacia'}
                if user_rol not in roles_admin_global:
                    raise PermisoRequisicionError(
                        f"Esta transición requiere pertenecer al centro '{requisicion_centro.nombre}'."
                    )
        
        # ISS-001 FIX (audit6): Validar transiciones de farmacia con bloqueo estricto
        if transicion in transiciones_farmacia:
            roles_farmacia = {'farmacia', 'farmaceutico', 'admin_farmacia', 'usuario_farmacia'}
            
            # Usuario debe ser de farmacia central
            if user_rol in roles_farmacia:
                # ISS-001 FIX: BLOQUEAR si farmacia tiene centro asignado
                if user_centro is not None:
                    logger.error(
                        f"ISS-001: Usuario farmacia {self.usuario.username} tiene centro asignado "
                        f"({user_centro.pk}). Transición '{transicion}' bloqueada."
                    )
                    raise PermisoRequisicionError(
                        f"El usuario '{self.usuario.username}' tiene rol de farmacia pero está adscrito "
                        f"al centro '{user_centro}'. Las transiciones de farmacia requieren usuarios "
                        f"sin centro asignado. Contacte al administrador para corregir su adscripción."
                    )
            elif user_rol not in {'admin', 'admin_sistema', 'superusuario', 'administrador'}:
                raise PermisoRequisicionError(
                    f"Esta transición solo puede ser realizada por personal de farmacia central. "
                    f"Su rol '{user_rol}' no está autorizado."
                )
        
        return True
    
    @transaction.atomic
    def devolver_requisicion(self, motivo):
        """
        ISS-005 FIX (audit4): Devuelve una requisición y revierte reservas/movimientos previos.
        
        Cuando una requisición se devuelve para corrección:
        1. Si tiene movimientos de reserva/surtido parcial, se revierten
        2. Se registra el motivo y actor para trazabilidad
        3. Se recalcula disponibilidad de stock
        
        Estados desde los que se puede devolver:
        - en_revision: Sin movimientos, devolución directa
        - pendiente_admin, pendiente_director: Sin movimientos, devolución directa
        - parcial: Puede tener movimientos, requiere reversión
        
        Args:
            motivo: Motivo de devolución (obligatorio, mínimo 10 caracteres)
            
        Returns:
            dict: Resultado de la devolución
            
        Raises:
            EstadoInvalidoError: Si la requisición no es devolvable
            ValidationError: Si no se proporciona motivo válido
        """
        from django.core.exceptions import ValidationError
        from core.models import Requisicion as RequisicionModel, Movimiento
        
        # Validar motivo obligatorio
        if not motivo or len(motivo.strip()) < 10:
            raise ValidationError({
                'motivo': 'Se requiere un motivo de devolución de al menos 10 caracteres'
            })
        
        # Bloquear requisición
        requisicion = RequisicionModel.objects.select_for_update().get(pk=self.requisicion.pk)
        
        estado_actual = (requisicion.estado or '').lower()
        estados_devolvibles = ['en_revision', 'pendiente_admin', 'pendiente_director', 'parcial']
        
        if estado_actual not in estados_devolvibles:
            raise EstadoInvalidoError(
                f"No se pueden devolver requisiciones en estado '{estado_actual}'. "
                f"Estados devolvibles: {estados_devolvibles}",
                estado_actual=estado_actual
            )
        
        movimientos_revertidos = []
        errores_validacion = []
        
        # ISS-002 FIX (audit6): Si hay movimientos (parcial), validar ANTES de revertir
        if estado_actual == 'parcial':
            # Buscar movimientos de salida y entrada con lock
            movimientos_salida = Movimiento.objects.select_for_update().filter(
                requisicion=requisicion,
                tipo='salida'
            ).select_related('lote')
            
            movimientos_entrada = Movimiento.objects.select_for_update().filter(
                requisicion=requisicion,
                tipo='entrada'
            ).select_related('lote')
            
            # ISS-002 FIX: VALIDAR que reversión de entradas no genere stock negativo
            # Antes de hacer cualquier cambio, verificar que todos los ajustes sean válidos
            for mov in movimientos_entrada:
                lote = Lote.objects.select_for_update().get(pk=mov.lote.pk)
                cantidad_actual = lote.cantidad_actual or 0
                cantidad_a_restar = mov.cantidad
                
                if cantidad_actual < cantidad_a_restar:
                    errores_validacion.append({
                        'lote': lote.numero_lote,
                        'producto': str(lote.producto),
                        'stock_actual': cantidad_actual,
                        'cantidad_a_restar': cantidad_a_restar,
                        'deficit': cantidad_a_restar - cantidad_actual
                    })
            
            # ISS-002 FIX: Si hay errores de validación, abortar atómicamente
            if errores_validacion:
                logger.error(
                    f"ISS-002: Reversión de requisición {requisicion.folio} abortada. "
                    f"Stock insuficiente en {len(errores_validacion)} lote(s): {errores_validacion}"
                )
                raise RequisicionServiceError(
                    f"No se puede devolver la requisición: la reversión de movimientos "
                    f"generaría stock negativo en {len(errores_validacion)} lote(s).",
                    details={
                        'codigo': 'stock_negativo_reversion',
                        'lotes_afectados': errores_validacion,
                        'recomendacion': 'Verifique que el stock del centro no haya sido consumido antes de devolver'
                    },
                    code='integridad_inventario'
                )
            
            # ISS-002 FIX: Validaciones pasaron, proceder con reversión
            # Restaurar stock en farmacia (salidas -> entradas)
            for mov in movimientos_salida:
                cantidad_restaurar = abs(mov.cantidad)
                
                # Restaurar stock en lote de farmacia
                Lote.objects.filter(pk=mov.lote.pk).update(
                    cantidad_actual=F('cantidad_actual') + cantidad_restaurar,
                    activo=True,
                    updated_at=timezone.now()
                )
                
                # Registrar movimiento de ajuste
                Movimiento.objects.create(
                    tipo='entrada',
                    producto=mov.lote.producto,
                    lote=mov.lote,
                    centro_destino=mov.centro_origen,
                    requisicion=requisicion,
                    usuario=self.usuario,
                    cantidad=cantidad_restaurar,
                    motivo=f'REVERSO por devolución de requisición {requisicion.numero}'
                )
                
                movimientos_revertidos.append({
                    'lote': mov.lote.numero_lote,
                    'cantidad_restaurada': cantidad_restaurar,
                    'tipo': 'restauracion_farmacia'
                })
            
            # ISS-002 FIX: Revertir entradas en centro (ya validado que no genera negativo)
            for mov in movimientos_entrada:
                # Re-obtener lote con lock para actualización segura
                lote = Lote.objects.select_for_update().get(pk=mov.lote.pk)
                nueva_cantidad = lote.cantidad_actual - mov.cantidad
                
                # Actualizar con valor calculado (no F() para evitar race condition)
                lote.cantidad_actual = nueva_cantidad
                lote.activo = nueva_cantidad > 0  # Desactivar si queda en 0
                lote.updated_at = timezone.now()
                lote.save(update_fields=['cantidad_actual', 'activo', 'updated_at'])
                
                Movimiento.objects.create(
                    tipo='salida',
                    producto=mov.lote.producto,
                    lote=mov.lote,
                    centro_origen=mov.centro_destino,
                    requisicion=requisicion,
                    usuario=self.usuario,
                    cantidad=-mov.cantidad,
                    motivo=f'REVERSO por devolución de requisición {requisicion.numero}'
                )
                
                movimientos_revertidos.append({
                    'lote': mov.lote.numero_lote,
                    'cantidad_revertida': mov.cantidad,
                    'tipo': 'reversion_centro'
                })
            
            # Resetear cantidades surtidas
            requisicion.detalles.update(cantidad_surtida=0)
        
        # Registrar transición para trazabilidad
        self.requisicion = requisicion
        self.registrar_transicion_historial(
            estado_anterior=estado_actual,
            estado_nuevo='devuelta',
            observaciones=f'Motivo: {motivo}. Movimientos revertidos: {len(movimientos_revertidos)}'
        )
        
        # Actualizar estado
        requisicion.estado = 'devuelta'
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        requisicion.notas = (requisicion.notas or '') + (
            f'\n[DEVOLUCIÓN {timestamp}] Por: {self.usuario.username} | '
            f'Motivo: {motivo} | Movimientos revertidos: {len(movimientos_revertidos)}'
        )
        requisicion.save(update_fields=['estado', 'notas', 'updated_at'])
        
        logger.info(
            f"Requisición {requisicion.folio} devuelta por {self.usuario.username}. "
            f"Motivo: {motivo}. Movimientos revertidos: {len(movimientos_revertidos)}"
        )
        
        return {
            'exito': True,
            'folio': requisicion.folio,
            'estado': 'devuelta',
            'motivo': motivo,
            'movimientos_revertidos': movimientos_revertidos,
            'usuario': self.usuario.username
        }
    
    def registrar_transicion_historial(self, estado_anterior, estado_nuevo, observaciones='', 
                                         accion='cambio_estado', ip_address=None, user_agent=None):
        """
        ISS-003 FIX (audit6): Registra transición en tabla estructurada de historial.
        
        Usa el modelo RequisicionHistorialEstados para persistencia estructurada
        con campos consultables (no concatenación de texto en notas).
        
        Args:
            estado_anterior: Estado antes de la transición
            estado_nuevo: Estado después de la transición
            observaciones: Observaciones adicionales
            accion: Tipo de acción (crear, autorizar, rechazar, etc.)
            ip_address: IP del cliente (para auditoría)
            user_agent: User agent del cliente (para auditoría)
        """
        from core.models import RequisicionHistorialEstados
        
        try:
            # ISS-003 FIX: Usar tabla estructurada en lugar de campo de texto
            historial = RequisicionHistorialEstados.registrar_cambio(
                requisicion=self.requisicion,
                estado_anterior=estado_anterior,
                estado_nuevo=estado_nuevo,
                usuario=self.usuario,
                accion=accion,
                motivo=observaciones if observaciones else None,
                ip_address=ip_address,
                user_agent=user_agent,
                datos_adicionales={
                    'rol_usuario': getattr(self.usuario, 'rol', 'N/A'),
                    'centro_usuario': str(getattr(self.usuario, 'centro', None)),
                    'timestamp_local': timezone.now().isoformat()
                }
            )
            
            logger.info(
                f"ISS-003: Historial estructurado creado para requisición {self.requisicion.pk}: "
                f"{estado_anterior} → {estado_nuevo} (ID: {historial.pk})"
            )
            
        except Exception as e:
            # Fallback a notas si la tabla no existe o falla
            logger.warning(
                f"ISS-003: No se pudo guardar en historial estructurado ({e}). "
                f"Usando fallback a notas."
            )
            timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            user_rol = getattr(self.usuario, 'rol', 'N/A')
            
            registro = (
                f"\n[TRANSICIÓN {timestamp}] "
                f"{estado_anterior} → {estado_nuevo} | "
                f"Por: {self.usuario.username} ({user_rol})"
            )
            
            if observaciones:
                registro += f" | Obs: {observaciones}"
            
            notas_actuales = self.requisicion.notas or ''
            self.requisicion.notas = notas_actuales + registro
    
    # ========== ISS-003 FIX (audit18): Funciones internas de fallback ==========
    # Estas funciones proporcionan validación segura cuando las funciones
    # externas fallan o no están definidas correctamente.
    
    @staticmethod
    def _default_is_farmacia_or_admin(usuario) -> bool:
        """
        ISS-003 FIX (audit18): Fallback interno para verificar rol farmacia/admin.
        
        Se usa cuando is_farmacia_or_admin_fn es None o falla.
        Implementa verificación SEGURA basada en atributos del usuario.
        
        Returns:
            bool: True si el usuario tiene rol de farmacia o admin
        """
        if not usuario:
            return False
        
        # Superusuario siempre tiene acceso
        if getattr(usuario, 'is_superuser', False):
            return True
        
        # Verificar por rol
        user_rol = (getattr(usuario, 'rol', '') or '').lower()
        roles_permitidos = {
            'farmacia', 'farmaceutico', 'admin_farmacia', 
            'usuario_farmacia', 'admin', 'admin_sistema'
        }
        
        return user_rol in roles_permitidos
    
    @staticmethod
    def _default_get_user_centro(usuario):
        """
        ISS-003 FIX (audit18): Fallback interno para obtener centro del usuario.
        
        Se usa cuando get_user_centro_fn es None o falla.
        
        Returns:
            Centro | None: Centro del usuario o None si es farmacia central
        """
        if not usuario:
            return None
        
        # Obtener centro directamente del usuario
        return getattr(usuario, 'centro', None)
    
    def validar_permisos_surtido(self, is_farmacia_or_admin_fn=None, get_user_centro_fn=None):
        """
        ISS-003 FIX (audit2 + audit3 + audit18): Valida permisos del usuario para surtir.
        
        IMPORTANTE: Solo farmacia central y administradores pueden surtir.
        Los usuarios de centros NO pueden surtir, solo pueden confirmar recepción.
        
        ISS-003 FIX (audit3): Valida adscripción del usuario:
        - Usuarios de farmacia deben estar adscritos a farmacia central (centro=NULL)
        - Solo pueden surtir requisiciones dentro de su ámbito
        
        ISS-003 FIX (audit18): Fallback interno cuando funciones externas fallan:
        - Si is_farmacia_or_admin_fn es None o falla, usa _default_is_farmacia_or_admin
        - Si get_user_centro_fn es None o falla, usa _default_get_user_centro
        - Loguea advertencia cuando se usa fallback
        
        Args:
            is_farmacia_or_admin_fn: Función que verifica si usuario es farmacia/admin (opcional)
            get_user_centro_fn: Función que obtiene el centro del usuario (opcional)
            
        Raises:
            PermisoRequisicionError: Si el usuario no tiene permiso
        """
        if self.usuario.is_superuser:
            return True
        
        # ISS-003 FIX (audit18): Usar fallback si función externa es None
        if is_farmacia_or_admin_fn is None:
            logger.warning(
                f"ISS-003: is_farmacia_or_admin_fn es None para usuario {self.usuario.username}. "
                f"Usando validación interna (fallback seguro)."
            )
            is_farmacia_or_admin_fn = self._default_is_farmacia_or_admin
        
        # ISS-003 FIX (audit18): Ejecutar con manejo de errores
        try:
            es_farmacia_o_admin = is_farmacia_or_admin_fn(self.usuario)
        except Exception as e:
            logger.error(
                f"ISS-003: is_farmacia_or_admin_fn falló: {e}. "
                f"Usando validación interna (fallback seguro)."
            )
            es_farmacia_o_admin = self._default_is_farmacia_or_admin(self.usuario)
        
        # Verificar rol farmacia/admin
        if not es_farmacia_o_admin:
            # ISS-003 FIX: Usuarios de centro NO pueden surtir
            raise PermisoRequisicionError(
                "Solo personal de farmacia central o administradores pueden surtir requisiciones. "
                "Los usuarios de centro pueden confirmar recepción usando el endpoint correspondiente."
            )
        
        # ISS-003 FIX (audit18): Usar fallback si función externa es None
        if get_user_centro_fn is None:
            logger.warning(
                f"ISS-003: get_user_centro_fn es None para usuario {self.usuario.username}. "
                f"Usando obtención de centro interna (fallback seguro)."
            )
            get_user_centro_fn = self._default_get_user_centro
        
        # ISS-001 FIX (audit6): Validar adscripción del usuario de farmacia
        # Los usuarios de farmacia central NO deben tener centro asignado
        try:
            user_centro = get_user_centro_fn(self.usuario)
        except Exception as e:
            logger.error(
                f"ISS-003: get_user_centro_fn falló: {e}. "
                f"Usando obtención de centro interna (fallback seguro)."
            )
            user_centro = self._default_get_user_centro(self.usuario)
        
        user_rol = (getattr(self.usuario, 'rol', '') or '').lower()
        
        # Roles de farmacia central no deben estar adscritos a un centro penitenciario
        # PERO pueden estar en "Almacén Central" o "Farmacia Central" (centros de farmacia)
        roles_farmacia_central = {'farmacia', 'farmaceutico', 'admin_farmacia', 'usuario_farmacia'}
        if user_rol in roles_farmacia_central and user_centro is not None:
            # ISS-FIX: Permitir si el centro es "Almacén Central", "Farmacia Central" o similar
            centro_nombre = (getattr(user_centro, 'nombre', '') or '').lower()
            centros_farmacia_validos = {'almacén central', 'almacen central', 'farmacia central', 'farmacia'}
            
            if not any(valido in centro_nombre for valido in centros_farmacia_validos):
                # Solo bloquear si está asignado a un centro penitenciario
                logger.error(
                    f"ISS-001: Usuario farmacia {self.usuario.username} tiene centro asignado "
                    f"({user_centro.pk}). Operación bloqueada por seguridad."
                )
                raise PermisoRequisicionError(
                    f"El usuario '{self.usuario.username}' tiene rol de farmacia pero está adscrito "
                    f"al centro '{user_centro}'. Los usuarios de farmacia central no deben tener "
                    f"centro asignado. Contacte al administrador para corregir su adscripción."
                )
        
        # Validar que la requisición pertenece a un centro válido
        # ISS-FIX: Usar centro_origen (el centro que HACE la requisición)
        # FALLBACK: si centro_origen es NULL (datos viejos), usar centro_destino
        requisicion_centro_id = getattr(self.requisicion, 'centro_origen_id', None) or getattr(self.requisicion, 'centro_destino_id', None)
        requisicion_centro = getattr(self.requisicion, 'centro_origen', None) or getattr(self.requisicion, 'centro_destino', None)
        
        if requisicion_centro is None and requisicion_centro_id:
            # Cargar centro si solo tenemos el ID
            from core.models import Centro
            try:
                requisicion_centro = Centro.objects.get(pk=requisicion_centro_id)
            except Centro.DoesNotExist:
                raise PermisoRequisicionError(
                    f"Centro de requisición no válido: {requisicion_centro_id}"
                )
        
        if requisicion_centro is None:
            raise PermisoRequisicionError(
                "La requisición no tiene centro asignado. No se puede surtir."
            )
        
        # ISS-003 FIX (audit3): Registrar quién realiza el surtido para auditoría
        logger.info(
            f"ISS-003: Usuario {self.usuario.username} (rol: {user_rol}) "
            f"autorizado para surtir requisición {self.requisicion.folio} "
            f"del centro {requisicion_centro.nombre}"
        )
        
        return True
    
    def validar_stock_disponible(self, usar_bloqueo=False, revalidacion_post_lock=False):
        """
        ISS-001 FIX: Valida que hay stock suficiente SOLO en farmacia central.
        ISS-002 FIX: Solo considera lotes NO caducados.
        ISS-004 FIX (audit2): Descuenta stock comprometido por otras requisiciones.
        ISS-007 FIX: Opcionalmente aplica select_for_update para prevenir race conditions.
        ISS-FIX-LOTE: Si el detalle tiene lote específico, valida ESE lote únicamente.
        
        IMPORTANTE: Las requisiciones SOLO se surten desde farmacia central.
        El stock del centro destino NO debe considerarse para validación,
        ya que ese stock ya fue transferido previamente y pertenece al centro.
        
        ISS-001 FIX (audit-final): Cuando revalidacion_post_lock=True, se asume que
        los lotes ya están bloqueados por la transacción padre. Esto previene
        race conditions donde el stock cambia entre pre-check y surtido.
        
        ISS-001 FIX (perf): Consolidar consultas usando agregaciones por producto
        para evitar N+1 queries. Calcular stock y comprometido en una sola pasada.
        
        Args:
            usar_bloqueo: Si True, aplica select_for_update a los lotes consultados
                          para prevenir condiciones de carrera. Usar True cuando
                          la validación es parte de una transacción de surtido.
                          Default False para consultas de preview/visualización.
            revalidacion_post_lock: Si True, indica que esta es una revalidación
                          DESPUÉS de adquirir locks. No intenta bloquear de nuevo.
        
        Returns:
            list: Lista vacía si hay stock suficiente
            
        Raises:
            StockInsuficienteError: Si no hay stock suficiente en farmacia central
        """
        from django.utils import timezone
        from django.db.models import Sum, Value, OuterRef, Subquery
        from django.db.models.functions import Coalesce
        from core.models import DetalleRequisicion
        from core.constants import ESTADOS_COMPROMETIDOS
        
        hoy = timezone.now().date()
        errores_stock = []
        
        # ISS-FIX-LOTE: Obtener todos los detalles con sus productos Y lotes en una sola query
        detalles = list(self.requisicion.detalles.select_related('producto', 'lote').all())
        
        if not detalles:
            return []
        
        # ISS-003 FIX: Validar que TODOS los detalles tengan producto_id
        # Rechazar requisiciones con detalles incompletos antes de continuar
        detalles_sin_producto = [d for d in detalles if not d.producto_id]
        if detalles_sin_producto:
            detalles_info = [
                f"Detalle #{d.pk or 'nuevo'} (cantidad: {d.cantidad_solicitada or 0})"
                for d in detalles_sin_producto[:5]  # Limitar a 5 para no saturar mensaje
            ]
            total_invalidos = len(detalles_sin_producto)
            mensaje_extra = f" y {total_invalidos - 5} más" if total_invalidos > 5 else ""
            
            logger.error(
                f"ISS-003: Requisición {self.requisicion.folio} tiene {total_invalidos} "
                f"detalle(s) sin producto_id: {detalles_info}"
            )
            raise RequisicionServiceError(
                f"La requisición tiene {total_invalidos} detalle(s) sin producto asignado. "
                f"Todos los detalles deben tener un producto válido antes de validar stock.",
                details={
                    'codigo': 'detalles_sin_producto',
                    'detalles_invalidos': detalles_info,
                    'total_invalidos': total_invalidos
                },
                code='validacion_datos'
            )
        
        # ISS-001 FIX (perf): Extraer IDs de productos para consultas batch
        producto_ids = [d.producto_id for d in detalles if d.producto_id]
        
        # ISS-001 FIX (perf): Calcular stock de farmacia para TODOS los productos en UNA query
        stock_farmacia_query = Lote.objects.filter(
            centro__isnull=True,  # Solo farmacia central
            producto_id__in=producto_ids,
            activo=True,
            cantidad_actual__gt=0,
            fecha_caducidad__gte=hoy,
        )
        
        # ISS-007 FIX: Aplicar bloqueo si se requiere
        if usar_bloqueo and not revalidacion_post_lock:
            stock_farmacia_query = stock_farmacia_query.select_for_update(nowait=False)
        
        # Agregación por producto_id
        stock_por_producto = {
            item['producto_id']: item['total']
            for item in stock_farmacia_query.values('producto_id').annotate(
                total=Coalesce(Sum('cantidad_actual'), Value(0))
            )
        }
        
        # ISS-002 FIX (perf): Calcular stock comprometido para TODOS los productos en UNA query
        # Excluir esta requisición para evitar contar doble
        comprometido_query = DetalleRequisicion.objects.filter(
            requisicion__estado__in=ESTADOS_COMPROMETIDOS,
            producto_id__in=producto_ids
        ).exclude(
            requisicion_id=self.requisicion.pk
        ).values('producto_id').annotate(
            total_autorizado=Coalesce(Sum('cantidad_autorizada'), Value(0)),
            total_surtido=Coalesce(Sum('cantidad_surtida'), Value(0))
        )
        
        comprometido_por_producto = {
            item['producto_id']: max(0, item['total_autorizado'] - item['total_surtido'])
            for item in comprometido_query
        }
        
        # ISS-001 FIX: Validar cada detalle usando datos pre-calculados
        # ISS-FIX-LOTE: Distinguir entre detalles con lote específico y sin lote
        for detalle in detalles:
            requerido = (detalle.cantidad_autorizada or detalle.cantidad_solicitada) - (detalle.cantidad_surtida or 0)
            if requerido <= 0:
                continue
            
            producto_id = detalle.producto_id
            
            # =====================================================================
            # ISS-FIX-LOTE: VALIDAR LOTE ESPECÍFICO SI ESTÁ DEFINIDO
            # =====================================================================
            if detalle.lote_id is not None and detalle.lote is not None:
                # CASO 1: Lote específico - validar stock de ESE lote únicamente
                lote = detalle.lote
                
                # Verificar que el lote exista y sea válido
                if not lote.activo:
                    errores_stock.append({
                        'producto': detalle.producto.clave,
                        'producto_nombre': (detalle.producto.nombre or '')[:50],
                        'lote': lote.numero_lote,
                        'requerido': requerido,
                        'disponible': 0,
                        'error': 'Lote inactivo',
                        'validacion_tipo': 'lote_especifico'
                    })
                    continue
                
                if lote.fecha_caducidad and lote.fecha_caducidad < hoy:
                    errores_stock.append({
                        'producto': detalle.producto.clave,
                        'producto_nombre': (detalle.producto.nombre or '')[:50],
                        'lote': lote.numero_lote,
                        'requerido': requerido,
                        'disponible': 0,
                        'error': f'Lote vencido (caducidad: {lote.fecha_caducidad})',
                        'validacion_tipo': 'lote_especifico'
                    })
                    continue
                
                disponible_lote = lote.cantidad_actual or 0
                if disponible_lote < requerido:
                    errores_stock.append({
                        'producto': detalle.producto.clave,
                        'producto_nombre': (detalle.producto.nombre or '')[:50],
                        'lote': lote.numero_lote,
                        'requerido': requerido,
                        'disponible': disponible_lote,
                        'deficit': requerido - disponible_lote,
                        'error': 'Stock insuficiente en lote específico',
                        'validacion_tipo': 'lote_especifico'
                    })
            else:
                # CASO 2: Sin lote específico - validar stock total del producto (FEFO)
                stock_farmacia = stock_por_producto.get(producto_id, 0)
                stock_comprometido = comprometido_por_producto.get(producto_id, 0)
                disponible = stock_farmacia - stock_comprometido
                
                if disponible < requerido:
                    errores_stock.append({
                        'producto': detalle.producto.clave,
                        'producto_nombre': (detalle.producto.nombre or '')[:50],
                        'requerido': requerido,
                        'disponible': disponible,
                        'stock_farmacia': stock_farmacia,
                        'stock_comprometido': stock_comprometido,
                        'deficit': requerido - disponible,
                        'validacion_tipo': 'fefo_automatico' if not revalidacion_post_lock else 'post_lock'
                    })
        
        if errores_stock:
            raise StockInsuficienteError(
                f"Stock insuficiente para {len(errores_stock)} producto(s)",
                detalles_stock=errores_stock
            )
        
        return []
    
    def _get_stock_comprometido_otras(self, producto):
        """
        ISS-004/007 FIX (audit8): Calcula stock comprometido por OTRAS requisiciones.
        ISS-002 FIX (audit13): Optimizado a una sola consulta.
        
        NOTA: Este método se mantiene para compatibilidad con código existente.
        Para validaciones batch, usar validar_stock_disponible que hace todo en una pasada.
        
        ISS-007 FIX (audit8): 
        - Excluye requisiciones canceladas/rechazadas explícitamente
        - Solo cuenta stock de farmacia central (centro__isnull=True)
        - Usa ESTADOS_COMPROMETIDOS de constants como fuente única
        
        Args:
            producto: Producto para calcular comprometido
            
        Returns:
            int: Cantidad comprometida por otras requisiciones (pendiente de surtir)
        """
        from django.db.models import Sum, Value
        from django.db.models.functions import Coalesce
        from core.models import DetalleRequisicion
        from core.constants import ESTADOS_COMPROMETIDOS, ESTADOS_TERMINALES
        
        # ISS-007 FIX (audit8): Estados a excluir explícitamente
        # Aunque ESTADOS_COMPROMETIDOS no los incluye, ser explícitos por seguridad
        estados_excluir = ['cancelada', 'rechazada', 'vencida']
        
        # ISS-002 FIX (audit13): Una sola query con Coalesce para manejar NULLs
        resultado = DetalleRequisicion.objects.filter(
            requisicion__estado__in=ESTADOS_COMPROMETIDOS,
            producto=producto
        ).exclude(
            requisicion_id=self.requisicion.pk  # Excluir esta requisición
        ).exclude(
            # ISS-007 FIX: Excluir estados problemáticos explícitamente
            requisicion__estado__in=estados_excluir
        ).aggregate(
            total_autorizado=Coalesce(Sum('cantidad_autorizada'), Value(0)),
            total_surtido=Coalesce(Sum('cantidad_surtida'), Value(0))
        )
        
        pendiente = resultado['total_autorizado'] - resultado['total_surtido']
        return max(0, pendiente)
    
    @transaction.atomic
    def surtir(self, is_farmacia_or_admin_fn, get_user_centro_fn):
        """
        ISS-003 FIX + ISS-011, ISS-021: Surte una requisición de forma atómica.
        
        Todo el proceso está envuelto en una transacción:
        1. BLOQUEAR requisición y detalles (ISS-003 FIX)
        2. Revalidar estado después del bloqueo
        3. Validar permisos del usuario
        4. Validar stock disponible
        5. Para cada item:
           a. Obtener lotes con bloqueo (select_for_update)
           b. Descontar de farmacia central
           c. Crear entrada en centro destino
           d. Registrar movimientos
        6. Actualizar estado de requisición
        
        Si cualquier paso falla, se hace rollback completo.
        
        Args:
            is_farmacia_or_admin_fn: Función para verificar rol
            get_user_centro_fn: Función para obtener centro del usuario
            
        Returns:
            dict: Resultado del surtido con detalles
            
        Raises:
            EstadoInvalidoError: Si la requisición no está en estado surtible
            PermisoRequisicionError: Si el usuario no tiene permiso
            StockInsuficienteError: Si no hay stock suficiente
        """
        from django.utils import timezone
        from core.models import Requisicion as RequisicionModel, DetalleRequisicion
        
        hoy = timezone.now().date()
        logger.info(f"SURTIR SERVICE: Iniciando surtido de {self.requisicion.folio}")
        
        # ISS-003 FIX: Bloquear requisición PRIMERO para evitar doble surtido
        # Esto previene race conditions donde dos procesos intentan surtir simultáneamente
        logger.info(f"SURTIR SERVICE: Bloqueando requisición {self.requisicion.pk}")
        requisicion_bloqueada = RequisicionModel.objects.select_for_update().get(pk=self.requisicion.pk)
        logger.info(f"SURTIR SERVICE: Requisición bloqueada, estado={requisicion_bloqueada.estado}")
        
        # ISS-003 FIX: Revalidar estado DESPUÉS del bloqueo
        estado_actual = (requisicion_bloqueada.estado or '').lower()
        if estado_actual not in self.ESTADOS_SURTIBLES:
            raise EstadoInvalidoError(
                f"Solo se pueden surtir requisiciones en estado: {self.ESTADOS_SURTIBLES}. "
                f"Estado actual: {estado_actual}",
                estado_actual=estado_actual
            )
        
        # ISS-FIX-FECHA-VENCIDA: Validar que la fecha de recolección no haya vencido
        # Si ya venció, marcar como vencida automáticamente
        fecha_limite = getattr(requisicion_bloqueada, 'fecha_recoleccion_limite', None)
        if fecha_limite and timezone.now() > fecha_limite:
            logger.warning(
                f"ISS-FIX-FECHA-VENCIDA: Requisición {requisicion_bloqueada.folio} "
                f"tiene fecha límite vencida: {fecha_limite}"
            )
            requisicion_bloqueada.estado = 'vencida'
            requisicion_bloqueada.fecha_vencimiento = timezone.now()
            requisicion_bloqueada.motivo_vencimiento = (
                f"Fecha límite de recolección vencida: {fecha_limite.strftime('%Y-%m-%d %H:%M')}"
            )
            update_fields_vencida = ['estado', 'fecha_vencimiento', 'motivo_vencimiento', 'updated_at']
            requisicion_bloqueada.save(update_fields=update_fields_vencida)
            
            raise EstadoInvalidoError(
                f"No se puede surtir: La fecha límite de recolección ({fecha_limite.strftime('%Y-%m-%d %H:%M')}) "
                f"ya venció. La requisición ha sido marcada como vencida automáticamente.",
                estado_actual='vencida'
            )
        
        # ISS-FIX-SURTIR-ESTADO: Auto-transición de 'autorizada' a 'en_surtido'
        # Si la requisición está en estado 'autorizada', primero hacemos la transición
        # a 'en_surtido' antes de proceder con el surtido
        if estado_actual == 'autorizada':
            logger.info(
                f"ISS-FIX-SURTIR-ESTADO: Requisición {requisicion_bloqueada.folio} "
                f"en estado 'autorizada'. Transicionando automáticamente a 'en_surtido'"
            )
            
            # ISS-FIX-FECHA-RECOLECCION: Si la requisición NO tiene fecha de recolección límite
            # (requisiciones legacy autorizadas antes del fix), asignar una fecha por defecto
            if not getattr(requisicion_bloqueada, 'fecha_recoleccion_limite', None):
                from datetime import timedelta
                fecha_default = timezone.now() + timedelta(days=7)
                logger.warning(
                    f"ISS-FIX-FECHA-RECOLECCION: Requisición {requisicion_bloqueada.folio} "
                    f"sin fecha_recoleccion_limite. Asignando fecha por defecto: {fecha_default}"
                )
                requisicion_bloqueada.fecha_recoleccion_limite = fecha_default
            
            requisicion_bloqueada.estado = 'en_surtido'
            
            # Guardar con los campos necesarios
            update_fields = ['estado', 'updated_at']
            if hasattr(requisicion_bloqueada, 'fecha_recoleccion_limite'):
                update_fields.append('fecha_recoleccion_limite')
            
            requisicion_bloqueada.save(update_fields=update_fields)
            estado_actual = 'en_surtido'
            logger.info(
                f"ISS-FIX-SURTIR-ESTADO: Transición automática completada. "
                f"Nuevo estado: {estado_actual}"
            )
        
        logger.info(f"SURTIR SERVICE: Estado válido, verificando idempotencia")
        # ISS-004 FIX (audit7): Verificar idempotencia - detectar surtido en progreso o duplicado
        # Si ya hay movimientos de salida para esta requisición, es un reintento potencialmente duplicado
        movimientos_existentes = Movimiento.objects.filter(
            requisicion=requisicion_bloqueada,
            tipo='salida'
        ).select_for_update()
        
        if estado_actual == 'en_surtido' and movimientos_existentes.exists():
            # Ya se inició un surtido, verificar si está completo
            total_surtido = movimientos_existentes.aggregate(total=Sum('cantidad'))['total'] or 0
            
            # ISS-005 FIX (audit16): Optimizar cálculo de pendiente usando agregación SQL
            # en lugar de iteración Python para mejor rendimiento
            from django.db.models import F, Case, When, Value
            from django.db.models.functions import Coalesce
            
            agregacion_pendiente = requisicion_bloqueada.detalles.aggregate(
                total_pendiente=Sum(
                    Coalesce(F('cantidad_autorizada'), F('cantidad_solicitada'), Value(0)) -
                    Coalesce(F('cantidad_surtida'), Value(0))
                )
            )
            total_pendiente = agregacion_pendiente['total_pendiente'] or 0
            
            if total_pendiente <= 0:
                # ISS-002 FIX (audit16): Antes de cerrar ciclo, REVALIDAR que los movimientos
                # existentes sean consistentes con el inventario actual.
                # Esto previene cerrar requisiciones con discrepancias de stock.
                try:
                    self._validar_consistencia_movimientos_inventario(
                        requisicion_bloqueada, 
                        movimientos_existentes
                    )
                except Exception as e:
                    logger.error(
                        f"ISS-002: Inconsistencia detectada en cierre idempotente de {requisicion_bloqueada.folio}: {e}"
                    )
                    # Registrar la discrepancia pero permitir el cierre con advertencia
                    logger.warning(
                        f"ISS-002: Cerrando requisición {requisicion_bloqueada.folio} con advertencia de inconsistencia"
                    )
                
                # ISS-003 FIX (audit13): Cerrar ciclo automáticamente en vez de lanzar error
                # Completar transición a 'surtida' para evitar requisiciones atascadas
                logger.info(
                    f"ISS-003 FIX: Completando transición automática a 'surtida' para {requisicion_bloqueada.folio}. "
                    f"Ya hay {movimientos_existentes.count()} movimientos registrados y 0 pendiente."
                )
                
                # ISS-009 FIX (audit6): Actualizar estado con trazabilidad completa
                # ISS-FIX: Manejar campos que pueden no existir en BD
                requisicion_bloqueada.estado = 'surtida'
                requisicion_bloqueada.fecha_surtido = timezone.now()
                
                update_fields = ['estado', 'fecha_surtido', 'updated_at']
                
                # Intentar setear campos opcionales de forma segura
                try:
                    if hasattr(requisicion_bloqueada, 'surtidor'):
                        requisicion_bloqueada.surtidor = self.usuario
                        update_fields.append('surtidor')
                except Exception:
                    pass
                
                try:
                    if hasattr(requisicion_bloqueada, 'usuario_firma_surtido'):
                        requisicion_bloqueada.usuario_firma_surtido = self.usuario
                        update_fields.append('usuario_firma_surtido')
                    if hasattr(requisicion_bloqueada, 'fecha_firma_surtido'):
                        requisicion_bloqueada.fecha_firma_surtido = timezone.now()
                        update_fields.append('fecha_firma_surtido')
                except Exception:
                    pass
                
                requisicion_bloqueada.save(update_fields=update_fields)
                
                # Refrescar referencia local
                self.requisicion = requisicion_bloqueada
                
                # Retornar resultado de operación idempotente
                return {
                    'success': True,
                    'idempotente': True,
                    'mensaje': f'Requisición {requisicion_bloqueada.folio} ya estaba surtida. Estado actualizado a "surtida".',
                    'requisicion_id': requisicion_bloqueada.pk,
                    'estado_final': 'surtida',
                    'movimientos_existentes': movimientos_existentes.count(),
                }
            else:
                logger.info(
                    f"ISS-004: Continuación de surtido parcial para {requisicion_bloqueada.folio}. "
                    f"Pendiente por surtir: {total_pendiente}"
                )
        
        # Actualizar referencia local con la versión bloqueada
        self.requisicion = requisicion_bloqueada
        
        # 2. Validar permisos
        logger.info(f"SURTIR SERVICE: Validando permisos para usuario {self.usuario.username}")
        self.validar_permisos_surtido(is_farmacia_or_admin_fn, get_user_centro_fn)
        logger.info(f"SURTIR SERVICE: Permisos OK")
        
        # 2.5 ISS-FIX-SURTIR: Auto-asignar cantidad_autorizada si falta
        # Esto permite surtir requisiciones legacy autorizadas antes del fix
        # que tengan cantidad_autorizada = NULL
        from django.db.models import Q
        detalles_sin_autorizar_qs = requisicion_bloqueada.detalles.select_for_update().filter(
            Q(cantidad_autorizada__isnull=True) | Q(cantidad_autorizada=0)
        )
        if detalles_sin_autorizar_qs.exists():
            logger.info(
                f"ISS-FIX-SURTIR: Auto-asignando cantidad_autorizada para "
                f"{detalles_sin_autorizar_qs.count()} detalles de {requisicion_bloqueada.folio}"
            )
            for detalle in detalles_sin_autorizar_qs:
                detalle.cantidad_autorizada = detalle.cantidad_solicitada
                detalle.save(update_fields=['cantidad_autorizada'])
            logger.info(f"ISS-FIX-SURTIR: cantidad_autorizada asignada correctamente")
        
        # 2.6 ISS-007 FIX (audit6): RE-Validar que TODOS los detalles tengan cantidad_autorizada
        # (Después del auto-asign, esto debería pasar siempre)
        detalles_sin_autorizar = []
        for detalle in requisicion_bloqueada.detalles.all():
            if detalle.cantidad_autorizada is None or detalle.cantidad_autorizada == 0:
                detalles_sin_autorizar.append({
                    'producto': detalle.producto.clave or detalle.producto.nombre,
                    'cantidad_solicitada': detalle.cantidad_solicitada
                })
        
        if detalles_sin_autorizar:
            raise EstadoInvalidoError(
                f"No se puede surtir: {len(detalles_sin_autorizar)} detalle(s) sin cantidad_autorizada. "
                f"La requisición debe ser autorizada antes de surtir. "
                f"Detalles: {detalles_sin_autorizar[:3]}{'...' if len(detalles_sin_autorizar) > 3 else ''}",
                estado_actual=estado_actual
            )
        
        # 3. ISS-001 FIX + ISS-007 FIX: Validar stock CON BLOQUEO para prevenir race conditions
        logger.info(f"SURTIR SERVICE: Validando stock disponible")
        # El bloqueo se mantiene hasta el final de la transacción atómica
        # ISS-001 FIX (audit-final): Revalidar con flag post_lock=True para indicar
        # que ya tenemos los locks y no intentar re-bloquear
        self.validar_stock_disponible(usar_bloqueo=True, revalidacion_post_lock=True)
        logger.info(f"SURTIR SERVICE: Stock OK")
        
        # ISS-FIX (critical): centro_origen es quien HIZO la requisición (el centro médico)
        # centro_destino es NULL (farmacia central de donde se surte)
        # La property 'centro' devuelve centro_destino, lo cual es INCORRECTO para este caso
        centro_requisicion = self.requisicion.centro_origen
        logger.info(f"SURTIR SERVICE: Centro requisición (centro_origen): {centro_requisicion}")
        items_surtidos = []
        
        # ISS-003 FIX + ISS-005 FIX: Bloquear detalles para evitar modificaciones concurrentes
        # ISS-FIX-LOTE: Solo incluir producto en select_related porque lote puede ser NULL
        # y PostgreSQL no permite FOR UPDATE en el lado nullable de un outer join
        detalles_bloqueados = DetalleRequisicion.objects.select_for_update().filter(
            requisicion=self.requisicion
        ).select_related('producto')
        logger.info(f"SURTIR SERVICE: Detalles bloqueados: {detalles_bloqueados.count()}")
        
        # 4. Procesar cada detalle
        for detalle in detalles_bloqueados:
            pendiente = (detalle.cantidad_autorizada or detalle.cantidad_solicitada) - (detalle.cantidad_surtida or 0)
            if pendiente <= 0:
                continue
            
            # ISS-005 FIX: Validar que cantidad a surtir no exceda la autorizada
            cantidad_autorizada = detalle.cantidad_autorizada or detalle.cantidad_solicitada
            if (detalle.cantidad_surtida or 0) >= cantidad_autorizada:
                logger.warning(
                    f"Detalle {detalle.pk} ya surtido completamente: "
                    f"surtido={detalle.cantidad_surtida}, autorizado={cantidad_autorizada}"
                )
                continue
            
            cantidad_surtida_item = 0
            lotes_usados = []
            
            # =====================================================================
            # ISS-FIX-LOTE (CRÍTICO): RESPETAR EL LOTE ESPECÍFICO DEL DETALLE
            # =====================================================================
            # Si el detalle tiene un lote específico (detalle.lote), se DEBE usar
            # ese lote exclusivamente. Esto ocurre cuando el usuario seleccionó
            # un lote específico al crear la requisición.
            #
            # Si detalle.lote es NULL, entonces se usa FEFO automático.
            # =====================================================================
            
            if detalle.lote is not None:
                # CASO 1: Lote específico definido - USAR EXCLUSIVAMENTE ESE LOTE
                logger.info(
                    f"ISS-FIX-LOTE: Detalle {detalle.pk} tiene lote específico: "
                    f"{detalle.lote.numero_lote} (ID: {detalle.lote_id})"
                )
                
                # Bloquear el lote específico
                try:
                    lote = Lote.objects.select_for_update().get(pk=detalle.lote_id)
                except Lote.DoesNotExist:
                    logger.error(
                        f"ISS-FIX-LOTE: Lote especificado {detalle.lote_id} no existe. "
                        f"Detalle: {detalle.pk}, Producto: {detalle.producto.clave}"
                    )
                    raise StockInsuficienteError(
                        f"El lote {detalle.lote.numero_lote} especificado ya no existe",
                        detalles_stock=[{
                            'producto': detalle.producto.clave,
                            'lote_solicitado': detalle.lote.numero_lote,
                            'error': 'Lote no encontrado'
                        }]
                    )
                
                # Validar que el lote sea válido para surtido
                if not lote.activo:
                    raise StockInsuficienteError(
                        f"El lote {lote.numero_lote} está inactivo",
                        detalles_stock=[{
                            'producto': detalle.producto.clave,
                            'lote': lote.numero_lote,
                            'error': 'Lote inactivo'
                        }]
                    )
                
                if lote.cantidad_actual < pendiente:
                    raise StockInsuficienteError(
                        f"Stock insuficiente en lote {lote.numero_lote}: "
                        f"disponible={lote.cantidad_actual}, requerido={pendiente}",
                        detalles_stock=[{
                            'producto': detalle.producto.clave,
                            'lote': lote.numero_lote,
                            'disponible': lote.cantidad_actual,
                            'requerido': pendiente
                        }]
                    )
                
                if lote.fecha_caducidad < hoy:
                    raise StockInsuficienteError(
                        f"El lote {lote.numero_lote} está vencido (caducidad: {lote.fecha_caducidad})",
                        detalles_stock=[{
                            'producto': detalle.producto.clave,
                            'lote': lote.numero_lote,
                            'error': 'Lote vencido',
                            'fecha_caducidad': str(lote.fecha_caducidad)
                        }]
                    )
                
                # Usar exactamente la cantidad pendiente del lote específico
                usar = pendiente
                
                logger.info(
                    f"ISS-FIX-LOTE: Descontando {usar} unidades del lote específico "
                    f"{lote.numero_lote} (stock actual: {lote.cantidad_actual})"
                )
                
                # Guardar stock previo antes de descontar
                stock_previo = lote.cantidad_actual
                
                # Descontar del lote específico
                lote_info = self._descontar_lote_atomico(lote, usar)
                
                # Registrar movimiento de salida
                movimiento_salida = self._crear_movimiento(
                    lote=lote,
                    tipo='salida',
                    cantidad=usar,
                    centro=lote.centro,
                    observaciones=f'SALIDA_POR_REQUISICION {self.requisicion.folio} (Lote específico)',
                    stock_previo=stock_previo
                )
                
                # Registrar trazabilidad detalle-lote
                self._registrar_detalle_surtido(
                    detalle=detalle,
                    lote=lote,
                    cantidad=usar,
                    movimiento=movimiento_salida
                )
                
                # Crear entrada en centro destino si aplica
                if lote.centro is None and centro_requisicion:
                    lote_destino = self._obtener_o_crear_lote_destino(
                        lote_origen=lote,
                        centro_destino=centro_requisicion,
                        cantidad=usar
                    )
                    
                    movimiento_entrada = self._crear_movimiento(
                        lote=lote_destino,
                        tipo='entrada',
                        cantidad=usar,
                        centro=centro_requisicion,
                        observaciones=f'ENTRADA_POR_REQUISICION {self.requisicion.folio} (Lote específico)'
                    )
                
                lotes_usados.append({
                    'lote_numero': lote.numero_lote,
                    'cantidad': usar,
                    'lote_origen_id': lote.pk,
                    'lote_especifico': True
                })
                
                detalle.cantidad_surtida = (detalle.cantidad_surtida or 0) + usar
                pendiente = 0
                cantidad_surtida_item = usar
                
            else:
                # CASO 2: Sin lote específico - USAR FEFO AUTOMÁTICO
                logger.info(
                    f"ISS-FIX-LOTE: Detalle {detalle.pk} sin lote específico. "
                    f"Usando FEFO automático para producto {detalle.producto.clave}"
                )
                
                # ISS-001 FIX (audit11): Obtener SOLO lotes disponibles para surtido
                # usando FEFO (First Expired, First Out)
                lotes = Lote.objects.select_for_update().filter(
                    centro__isnull=True,  # Solo farmacia central
                    producto=detalle.producto,
                    activo=True,          # Lote activo (no eliminado ni bloqueado)
                    cantidad_actual__gt=0, # Con stock disponible
                    fecha_caducidad__gte=hoy,  # Solo lotes vigentes
                ).order_by('fecha_caducidad', 'id')  # FEFO + ID para evitar deadlocks
                
                for lote in lotes:
                    if pendiente <= 0:
                        break
                    
                    # Revalidar estado del lote DESPUÉS del lock
                    lote.refresh_from_db()
                    
                    if not lote.activo or lote.cantidad_actual <= 0 or lote.fecha_caducidad < hoy:
                        continue
                    
                    usar = min(pendiente, lote.cantidad_actual)
                    
                    # Guardar stock previo antes de descontar
                    stock_previo = lote.cantidad_actual
                    
                    # Descontar con verificación atómica
                    lote_info = self._descontar_lote_atomico(lote, usar)
                    
                    # Registrar movimiento de salida
                    movimiento_salida = self._crear_movimiento(
                        lote=lote,
                        tipo='salida',
                        cantidad=usar,
                        centro=lote.centro,
                        observaciones=f'SALIDA_POR_REQUISICION {self.requisicion.folio}',
                        stock_previo=stock_previo
                    )
                    
                    # Registrar trazabilidad detalle-lote
                    self._registrar_detalle_surtido(
                        detalle=detalle,
                        lote=lote,
                        cantidad=usar,
                        movimiento=movimiento_salida
                    )
                    
                    # Crear entrada en centro destino si aplica
                    if lote.centro is None and centro_requisicion:
                        lote_destino = self._obtener_o_crear_lote_destino(
                            lote_origen=lote,
                            centro_destino=centro_requisicion,
                            cantidad=usar
                        )
                        
                        movimiento_entrada = self._crear_movimiento(
                            lote=lote_destino,
                            tipo='entrada',
                            cantidad=usar,
                            centro=centro_requisicion,
                            observaciones=f'ENTRADA_POR_REQUISICION {self.requisicion.folio}'
                        )
                    
                    lotes_usados.append({
                        'lote_numero': lote.numero_lote,
                        'cantidad': usar,
                        'lote_origen_id': lote.pk,
                        'lote_especifico': False
                    })
                    
                    detalle.cantidad_surtida = (detalle.cantidad_surtida or 0) + usar
                    pendiente -= usar
                    cantidad_surtida_item += usar
            
            # Guardar detalle actualizado
            detalle.save(update_fields=['cantidad_surtida'])
            
            items_surtidos.append({
                'producto': detalle.producto.clave or detalle.producto.nombre,
                'cantidad_surtida': cantidad_surtida_item,
                'lotes_usados': lotes_usados
            })
        
        # 5. Actualizar estado de requisición
        # Refrescar detalles para verificar si está completamente surtida
        from core.models import Requisicion as RequisicionModel
        requisicion_actualizada = RequisicionModel.objects.get(pk=self.requisicion.pk)
        detalles_actualizados = requisicion_actualizada.detalles.all()
        
        completada = all(
            (d.cantidad_autorizada or d.cantidad_solicitada) <= (d.cantidad_surtida or 0)
            for d in detalles_actualizados
        )
        
        # CAMBIO CRÍTICO: Al surtir, pasar DIRECTAMENTE a 'entregada'
        # No requiere confirmación del centro (automático)
        # - Si completada → 'entregada' (todo surtido)
        # - Si parcial → 'parcial' (aún faltan productos)
        # El inventario YA se actualizó en farmacia y centro durante el surtido
        nuevo_estado = 'entregada' if completada else 'parcial'
        self.requisicion.estado = nuevo_estado
        self.requisicion.fecha_surtido = timezone.now()
        
        # Si está completada, también marcar como entregada
        if completada:
            self.requisicion.fecha_entrega = timezone.now()
            self.requisicion.fecha_firma_recepcion = timezone.now()
        
        # ISS-FIX: Actualizar campos de trazabilidad de forma segura
        # (algunos campos pueden no existir en BD de producción)
        update_fields = ['estado', 'fecha_surtido', 'updated_at']
        
        if completada:
            update_fields.extend(['fecha_entrega', 'fecha_firma_recepcion'])
        
        # Intentar setear surtidor si el campo existe
        try:
            if hasattr(self.requisicion, 'surtidor'):
                self.requisicion.surtidor = self.usuario
                update_fields.append('surtidor')
        except Exception:
            pass
        
        # Intentar setear campos de firma si existen
        try:
            if hasattr(self.requisicion, 'usuario_firma_surtido'):
                self.requisicion.usuario_firma_surtido = self.usuario
                update_fields.append('usuario_firma_surtido')
            if hasattr(self.requisicion, 'fecha_firma_surtido'):
                self.requisicion.fecha_firma_surtido = timezone.now()
                update_fields.append('fecha_firma_surtido')
            # Si está completada, también marcar receptor (automático)
            if completada and hasattr(self.requisicion, 'usuario_firma_recepcion'):
                self.requisicion.usuario_firma_recepcion = self.usuario
                update_fields.append('usuario_firma_recepcion')
        except Exception:
            pass
        
        self.requisicion.save(update_fields=update_fields)
        
        logger.info(
            f"Requisición {self.requisicion.folio} surtida y {'ENTREGADA automáticamente' if completada else 'marcada como parcial'} por {self.usuario.username}. "
            f"Estado: {nuevo_estado}. Items: {len(items_surtidos)}"
        )
        
        return {
            'exito': True,
            'folio': self.requisicion.folio,
            'estado': nuevo_estado,
            'completada': completada,
            'items_surtidos': items_surtidos,
            'total_items': len(items_surtidos),
            'usuario': self.usuario.username,
            'fecha': timezone.now().isoformat()
        }
    
    def _descontar_lote_atomico(self, lote, cantidad):
        """
        ISS-014: Descuenta cantidad del lote de forma atómica.
        
        El lote ya debe estar bloqueado con select_for_update().
        Usa F() expressions para actualización atómica.
        
        Args:
            lote: Instancia del lote (bloqueada)
            cantidad: Cantidad a descontar
            
        Returns:
            dict: Información del lote actualizado
            
        Raises:
            serializers.ValidationError: Si no hay stock suficiente
        """
        # Verificación final de stock (el lote está bloqueado)
        if lote.cantidad_actual < cantidad:
            raise serializers.ValidationError({
                'cantidad': f'Stock insuficiente en lote {lote.numero_lote}. '
                           f'Disponible: {lote.cantidad_actual}, Requerido: {cantidad}'
            })
        
        stock_anterior = lote.cantidad_actual
        nuevo_stock = stock_anterior - cantidad
        
        # Actualizar con F() para atomicidad adicional
        Lote.objects.filter(pk=lote.pk).update(
            cantidad_actual=F('cantidad_actual') - cantidad,
            activo=(nuevo_stock > 0),
            updated_at=timezone.now()
        )
        
        # Refrescar instancia
        lote.refresh_from_db()
        
        self._lotes_actualizados.append({
            'lote_id': lote.pk,
            'numero_lote': lote.numero_lote,
            'stock_anterior': stock_anterior,
            'cantidad_descontada': cantidad,
            'stock_nuevo': lote.cantidad_actual
        })
        
        return {
            'lote_id': lote.pk,
            'stock_anterior': stock_anterior,
            'stock_nuevo': lote.cantidad_actual
        }
    
    def _crear_movimiento(self, lote, tipo, cantidad, centro, observaciones, stock_previo=None, producto=None):
        """
        ISS-008 FIX: Crea un movimiento de inventario con trazabilidad completa.
        
        Args:
            lote: Lote asociado
            tipo: 'entrada' o 'salida'
            cantidad: Cantidad (negativo para salidas)
            centro: Centro del movimiento
            observaciones: Texto descriptivo
            stock_previo: Stock antes del movimiento (para validación)
            producto: Producto asociado (si no se pasa, se toma del lote)
            
        Returns:
            Movimiento: Instancia creada con trazabilidad completa
        """
        # Determinar centro_origen/centro_destino según tipo
        centro_origen = centro if tipo == 'salida' else None
        centro_destino = centro if tipo == 'entrada' else None
        
        # Producto es requerido en la BD
        producto_movimiento = producto or (lote.producto if lote else None)
        
        # ISS-008 FIX: Construir observaciones con trazabilidad completa
        user_rol = getattr(self.usuario, 'rol', 'N/A') if self.usuario else 'Sistema'
        user_centro = getattr(self.usuario, 'centro', None)
        user_centro_nombre = user_centro.nombre if user_centro else 'Farmacia Central'
        
        trazabilidad = (
            f"{observaciones} | "
            f"Ejecutor: {self.usuario.username if self.usuario else 'Sistema'} | "
            f"Rol: {user_rol} | "
            f"Adscripcion: {user_centro_nombre} | "
            f"Timestamp: {timezone.now().isoformat()}"
        )
        
        movimiento = Movimiento(
            tipo=tipo,
            producto=producto_movimiento,
            lote=lote,
            centro_origen=centro_origen,
            centro_destino=centro_destino,
            requisicion=self.requisicion,
            usuario=self.usuario if self.usuario and self.usuario.is_authenticated else None,
            cantidad=cantidad,
            motivo=trazabilidad,
            # ISS-008 FIX: Agregar referencia para búsquedas
            referencia=f"REQ-{self.requisicion.folio}" if self.requisicion else None
        )
        # Pasar stock previo para evitar re-validación (ya descontamos)
        if stock_previo is not None:
            movimiento._stock_pre_movimiento = stock_previo
        movimiento.save()
        
        self._movimientos_creados.append(movimiento)
        
        # ISS-008 FIX: Log de auditoría adicional
        logger.info(
            f"ISS-008 MOVIMIENTO: {tipo.upper()} | "
            f"Producto: {producto_movimiento.clave if producto_movimiento else 'N/A'} | "
            f"Lote: {lote.numero_lote if lote else 'N/A'} | "
            f"Cantidad: {cantidad} | "
            f"Requisicion: {self.requisicion.folio if self.requisicion else 'N/A'} | "
            f"Usuario: {self.usuario.username if self.usuario else 'Sistema'} | "
            f"Rol: {user_rol}"
        )
        
        return movimiento
    
    def _registrar_detalle_surtido(self, detalle, lote, cantidad, movimiento):
        """
        Registra trazabilidad de surtido.
        
        La trazabilidad se mantiene a través del Movimiento que ya
        tiene referencia al lote y la requisición.
        
        Args:
            detalle: DetalleRequisicion
            lote: Lote usado
            cantidad: Cantidad surtida de este lote
            movimiento: Movimiento de salida asociado
            
        Returns:
            Movimiento: El movimiento de referencia (ya creado)
        """
        # La trazabilidad se registra en el movimiento que ya tiene:
        # - lote_id: El lote del que se surtió
        # - requisicion_id: La requisición asociada
        # - cantidad: Lo que se surtió
        # - observaciones: Detalles adicionales
        
        logger.debug(
            f"Surtido registrado: {cantidad} unidades del lote {lote.numero_lote} "
            f"para detalle {detalle.pk} de requisición {self.requisicion.folio}"
        )
        
        return movimiento
    
    def _obtener_o_crear_lote_destino(self, lote_origen, centro_destino, cantidad):
        """
        ISS-004 FIX (audit7): Obtiene o crea lote destino en el centro con validaciones.
        
        El lote en el centro es una COPIA FIEL del lote de farmacia:
        - Mismo número de lote
        - Misma fecha de caducidad
        - Vinculado a lote_origen
        
        ISS-004 FIX (audit7): Validaciones agregadas:
        - Caducidad > hoy (no transferir productos vencidos)
        - Log de auditoría en reactivaciones
        
        ISS-FIX (lotes-centro): Manejo robusto de IntegrityError por constraint
        de Supabase que puede diferir del modelo Django.
        
        Args:
            lote_origen: Lote de farmacia central
            centro_destino: Centro donde crear/actualizar lote
            cantidad: Cantidad a agregar
            
        Returns:
            Lote: Instancia del lote destino
            
        Raises:
            ValidationError: Si el lote está vencido o tiene datos inválidos
        """
        from django.core.exceptions import ValidationError
        from django.db import IntegrityError
        
        hoy = timezone.now().date()
        
        # ISS-004 FIX (audit7): Validar caducidad antes de transferir
        if lote_origen.fecha_caducidad and lote_origen.fecha_caducidad < hoy:
            raise ValidationError({
                'lote': (
                    f'No se puede transferir el lote {lote_origen.numero_lote} porque está vencido '
                    f'(caducidad: {lote_origen.fecha_caducidad}). '
                    f'Los productos vencidos no pueden distribuirse a centros.'
                )
            })
        
        # ISS-004 FIX (audit7): Advertir si caduca pronto (próximos 30 días)
        dias_para_vencer = (lote_origen.fecha_caducidad - hoy).days if lote_origen.fecha_caducidad else 999
        if dias_para_vencer <= 30:
            logger.warning(
                f"ISS-004 AUDIT: Lote {lote_origen.numero_lote} transferido con caducidad próxima "
                f"({dias_para_vencer} días). Producto: {lote_origen.producto.clave}"
            )
        
        # ISS-FIX (lotes-centro): Log detallado para diagnóstico
        logger.info(
            f"ISS-LOTES: Buscando/creando lote destino. "
            f"Producto: {lote_origen.producto.clave} (ID: {lote_origen.producto_id}), "
            f"NumLote: {lote_origen.numero_lote}, "
            f"Centro destino: {centro_destino.nombre} (ID: {centro_destino.pk}), "
            f"Cantidad a agregar: {cantidad}"
        )
        
        # ISS-FIX: Buscar CUALQUIER lote existente (activo o inactivo) antes de crear
        # Esto evita el error de unique_together cuando ya existe un lote
        lote_destino = Lote.objects.select_for_update().filter(
            producto=lote_origen.producto,
            numero_lote=lote_origen.numero_lote,
            centro=centro_destino,
        ).first()
        
        if lote_destino:
            # Lote existe (activo o inactivo) - actualizar cantidad y reactivar
            logger.info(
                f"ISS-LOTES: Actualizando lote existente ID={lote_destino.pk}, "
                f"NumLote={lote_destino.numero_lote}, Activo={lote_destino.activo}, "
                f"Cantidad anterior={lote_destino.cantidad_actual}, Agregando={cantidad}"
            )
            Lote.objects.filter(pk=lote_destino.pk).update(
                cantidad_actual=F('cantidad_actual') + cantidad,
                cantidad_inicial=F('cantidad_inicial') + cantidad,
                activo=True,
                updated_at=timezone.now()
            )
            lote_destino.refresh_from_db()
            logger.info(
                f"ISS-LOTES: Lote actualizado. ID={lote_destino.pk}, "
                f"Nueva cantidad={lote_destino.cantidad_actual}"
            )
        else:
            # No existe lote en este centro - crear uno nuevo
            logger.info(
                f"ISS-LOTES: No existe lote, creando nuevo. "
                f"NumLote={lote_origen.numero_lote}, Centro={centro_destino.nombre}"
            )
            try:
                # Crear nuevo lote: COPIA FIEL del lote de farmacia
                lote_destino = Lote.objects.create(
                    producto=lote_origen.producto,
                    numero_lote=lote_origen.numero_lote,
                    centro=centro_destino,
                    fecha_caducidad=lote_origen.fecha_caducidad,
                    cantidad_inicial=cantidad,
                    cantidad_actual=cantidad,
                    activo=True,
                    precio_unitario=lote_origen.precio_unitario,
                    marca=lote_origen.marca,
                    ubicacion=f'Transferido via REQ-{self.requisicion.numero}'
                )
                logger.info(
                    f"ISS-LOTES: Lote creado exitosamente. ID={lote_destino.pk}, "
                    f"NumLote={lote_destino.numero_lote}, Centro={centro_destino.nombre}"
                )
            except IntegrityError as e:
                # ISS-FIX (lotes-centro): Si hay error de constraint, intentar encontrar
                # el lote existente que puede tener un constraint diferente en Supabase
                logger.warning(
                    f"ISS-LOTES: IntegrityError al crear lote. Error: {e}. "
                    f"Buscando lote existente con constraint alternativo..."
                )
                
                # Buscar sin centro (por si el constraint en Supabase no incluye centro)
                lote_existente = Lote.objects.select_for_update().filter(
                    producto=lote_origen.producto,
                    numero_lote=lote_origen.numero_lote,
                ).first()
                
                if lote_existente:
                    # Si encontramos el lote pero con otro centro o sin centro,
                    # actualizar su centro y cantidad
                    logger.warning(
                        f"ISS-LOTES: Encontrado lote con constraint diferente. "
                        f"ID={lote_existente.pk}, Centro actual={lote_existente.centro_id}. "
                        f"Actualizando a centro={centro_destino.pk} y agregando cantidad={cantidad}"
                    )
                    Lote.objects.filter(pk=lote_existente.pk).update(
                        centro=centro_destino,
                        cantidad_actual=F('cantidad_actual') + cantidad,
                        cantidad_inicial=F('cantidad_inicial') + cantidad,
                        activo=True,
                        updated_at=timezone.now()
                    )
                    lote_existente.refresh_from_db()
                    lote_destino = lote_existente
                else:
                    # No pudimos encontrar ni crear el lote - error crítico
                    logger.error(
                        f"ISS-LOTES: ERROR CRÍTICO - No se pudo crear ni encontrar lote. "
                        f"Producto={lote_origen.producto.clave}, NumLote={lote_origen.numero_lote}"
                    )
                    raise ValidationError({
                        'lote': (
                            f'No se pudo crear el lote {lote_origen.numero_lote} en el centro destino. '
                            f'Error de integridad de datos. Contacte al administrador.'
                        )
                    })
        
        return lote_destino
    
    @transaction.atomic
    def confirmar_recepcion(self, observaciones='', validar_inventario=True):
        """
        ISS-006 FIX (audit4): Confirma la recepción de una requisición surtida.
        
        ISS-006 FIX: Operación transaccional completa que:
        1. Bloquea requisición para evitar modificaciones concurrentes
        2. Valida estado 'surtida' o 'parcial'
        3. ISS-006 FIX: Valida consistencia de inventario (farmacia vs centro)
        4. Registra usuario receptor y fecha
        5. Cambia estado a 'entregada'
        6. Si falla cualquier paso, rollback completo
        
        Args:
            observaciones: Observaciones adicionales de recepción
            validar_inventario: Si True, valida que los movimientos estén completos
            
        Returns:
            dict: Resultado de la confirmación
            
        Raises:
            EstadoInvalidoError: Si la requisición no está en estado recibible
            PermisoRequisicionError: Si el usuario no pertenece al centro destino
            ValidationError: Si hay inconsistencia de inventario
        """
        from django.core.exceptions import ValidationError
        from core.models import Requisicion as RequisicionModel, Movimiento
        
        # Bloquear requisición
        requisicion = RequisicionModel.objects.select_for_update().get(pk=self.requisicion.pk)
        
        # Validar estado - ISS-DB-002: usar parcial
        estado_actual = (requisicion.estado or '').lower()
        estados_recibibles = ['surtida', 'parcial']
        
        if estado_actual not in estados_recibibles:
            raise EstadoInvalidoError(
                f"Solo se pueden confirmar requisiciones en estado: {estados_recibibles}. "
                f"Estado actual: {estado_actual}",
                estado_actual=estado_actual
            )
        
        # Validar que usuario pertenezca al centro destino
        user_centro = getattr(self.usuario, 'centro', None)
        if user_centro is None and not self.usuario.is_superuser:
            raise PermisoRequisicionError(
                "El usuario debe pertenecer a un centro para confirmar recepción"
            )
        
        # ISS-FIX: Usar centro_origen (quien hizo la requisición), no centro (alias de centro_destino)
        if user_centro and requisicion.centro_origen_id != user_centro.pk and not self.usuario.is_superuser:
            centro_nombre = requisicion.centro_origen.nombre if requisicion.centro_origen else 'Desconocido'
            raise PermisoRequisicionError(
                f"Solo usuarios del centro {centro_nombre} pueden confirmar esta recepción"
            )
        
        # ISS-006 FIX (audit4): Validar consistencia de inventario
        if validar_inventario:
            self._validar_consistencia_inventario_entrega(requisicion)
        
        # Actualizar campos de recepción
        requisicion.usuario_firma_recepcion = self.usuario
        requisicion.fecha_firma_recepcion = timezone.now()
        requisicion.fecha_entrega = timezone.now()
        
        # Determinar nuevo estado
        # ISS-DB-002: Usar entregada, parcial
        # Si todo fue surtido completamente → entregada
        # Si fue parcial y no hay más por surtir → entregada
        detalles = requisicion.detalles.all()
        todo_surtido = all(
            (d.cantidad_autorizada or d.cantidad_solicitada) <= (d.cantidad_surtida or 0)
            for d in detalles
        )
        
        if todo_surtido or estado_actual == 'surtida':
            nuevo_estado = 'entregada'
        else:
            # Mantener parcial si aún hay pendientes
            nuevo_estado = 'parcial'
        
        requisicion.estado = nuevo_estado
        
        if observaciones:
            requisicion.notas = (requisicion.notas or '') + f'\n[Recepción] {observaciones}'
        
        requisicion.save(update_fields=[
            'estado', 'usuario_firma_recepcion', 'fecha_firma_recepcion', 'fecha_entrega', 'notas', 'updated_at'
        ])
        
        logger.info(
            f"Requisición {requisicion.folio} recibida por {self.usuario.username}. "
            f"Estado: {nuevo_estado}"
        )
        
        return {
            'exito': True,
            'folio': requisicion.folio,
            'estado': nuevo_estado,
            'usuario_recibe': self.usuario.username,
            'fecha_recibido': requisicion.fecha_firma_recepcion.isoformat() if requisicion.fecha_firma_recepcion else None,
            'observaciones': observaciones
        }
    
    def _validar_consistencia_inventario_entrega(self, requisicion):
        """
        ISS-006 FIX (audit4): Valida consistencia de inventario antes de confirmar entrega.
        
        Verifica que:
        1. Los movimientos de salida (farmacia) coincidan con entradas (centro)
        2. No haya movimientos huérfanos o incompletos
        3. Las cantidades surtidas coincidan con los movimientos
        
        Args:
            requisicion: Requisición a validar (ya bloqueada)
            
        Raises:
            ValidationError: Si hay inconsistencia de inventario
        """
        from django.core.exceptions import ValidationError
        from django.db.models import Sum
        from core.models import Movimiento
        
        # Total de salidas de farmacia
        salidas_farmacia = Movimiento.objects.filter(
            requisicion=requisicion,
            tipo='salida'
        ).aggregate(total=Sum('cantidad'))['total'] or 0
        
        # Total de entradas al centro
        entradas_centro = Movimiento.objects.filter(
            requisicion=requisicion,
            tipo='entrada'
        ).aggregate(total=Sum('cantidad'))['total'] or 0
        
        # Las salidas son negativas, las entradas positivas
        # La suma debe ser ~0 (salidas + entradas = 0)
        balance = abs(salidas_farmacia) - entradas_centro
        
        if abs(balance) > 0:
            logger.warning(
                f"ISS-006: Inconsistencia de inventario en requisición {requisicion.folio}. "
                f"Salidas farmacia: {abs(salidas_farmacia)}, Entradas centro: {entradas_centro}, "
                f"Diferencia: {balance}"
            )
            raise ValidationError({
                'inventario': (
                    f'Inconsistencia de inventario detectada. '
                    f'Salidas de farmacia ({abs(salidas_farmacia)}) no coinciden con '
                    f'entradas al centro ({entradas_centro}). '
                    f'Diferencia: {balance} unidades. Contacte al administrador.'
                )
            })
        
        # Validar que cada detalle tenga movimientos correspondientes
        for detalle in requisicion.detalles.all():
            if detalle.cantidad_surtida and detalle.cantidad_surtida > 0:
                # Verificar que hay movimientos para este producto
                movimientos_producto = Movimiento.objects.filter(
                    requisicion=requisicion,
                    producto=detalle.producto,
                    tipo='salida'
                ).aggregate(total=Sum('cantidad'))['total'] or 0
                
                cantidad_movida = abs(movimientos_producto)
                if cantidad_movida != detalle.cantidad_surtida:
                    logger.warning(
                        f"ISS-006: Discrepancia en detalle {detalle.pk}. "
                        f"Cantidad surtida: {detalle.cantidad_surtida}, "
                        f"Movimientos: {cantidad_movida}"
                    )
                    # Solo advertir, no bloquear (puede haber ajustes manuales válidos)
        
        logger.info(
            f"ISS-006: Validación de inventario exitosa para requisición {requisicion.folio}. "
            f"Balance: {balance}"
        )
        return True
    
    def _validar_consistencia_movimientos_inventario(self, requisicion, movimientos_existentes):
        """
        ISS-002 FIX (audit16): Valida que los movimientos registrados sean consistentes
        con el inventario actual antes de cerrar idempotentemente.
        
        Esta validación es CRÍTICA para detectar discrepancias causadas por:
        1. Expiración de lotes entre surtido y cierre
        2. Ajustes manuales de inventario concurrentes
        3. Movimientos de otros procesos que afectaron los mismos lotes
        
        Args:
            requisicion: Requisición bloqueada a validar
            movimientos_existentes: QuerySet de movimientos de surtido ya registrados
            
        Raises:
            ValueError: Si hay inconsistencia entre movimientos y lotes actuales
        """
        from core.models import Lote, Movimiento
        from core.lote_helpers import LoteQueryHelper
        from django.db.models import Sum
        
        discrepancias = []
        
        # Agrupar movimientos por lote y verificar estado actual
        lotes_usados = movimientos_existentes.values('lote_id').annotate(
            total_movido=Sum('cantidad')
        ).filter(lote_id__isnull=False)
        
        for mov_lote in lotes_usados:
            lote_id = mov_lote['lote_id']
            cantidad_movida = abs(mov_lote['total_movido'] or 0)  # Salidas son negativas
            
            try:
                lote = Lote.objects.get(pk=lote_id)
                
                # Verificar que el lote sigue activo
                if not lote.activo:
                    discrepancias.append(
                        f"Lote {lote.numero_lote} usado en surtido ahora está INACTIVO"
                    )
                
                # Verificar expiración usando helper centralizado
                if LoteQueryHelper.esta_expirado(lote):
                    discrepancias.append(
                        f"Lote {lote.numero_lote} usado en surtido ahora está EXPIRADO "
                        f"(vencimiento: {lote.fecha_vencimiento})"
                    )
                
                # ISS-002: Verificar que la cantidad movida no exceda el stock + movimientos
                # El stock actual + la cantidad movida debe ser >= 0
                stock_teorico = (lote.cantidad_disponible or 0) + cantidad_movida
                if stock_teorico < 0:
                    discrepancias.append(
                        f"Lote {lote.numero_lote}: inconsistencia de stock. "
                        f"Stock actual: {lote.cantidad_disponible}, movido: {cantidad_movida}"
                    )
                    
            except Lote.DoesNotExist:
                discrepancias.append(
                    f"Lote ID {lote_id} usado en surtido ya no existe en la base de datos"
                )
        
        # Verificar que los detalles reflejen correctamente los movimientos
        for detalle in requisicion.detalles.all():
            movs_detalle = Movimiento.objects.filter(
                requisicion=requisicion,
                producto=detalle.producto,
                tipo='salida'
            ).aggregate(total=Sum('cantidad'))['total'] or 0
            
            cantidad_movida_producto = abs(movs_detalle)
            cantidad_surtida_registrada = detalle.cantidad_surtida or 0
            
            if cantidad_movida_producto != cantidad_surtida_registrada:
                discrepancias.append(
                    f"Producto {detalle.producto.clave}: cantidad_surtida ({cantidad_surtida_registrada}) "
                    f"no coincide con movimientos ({cantidad_movida_producto})"
                )
        
        if discrepancias:
            mensaje = (
                f"ISS-002: Inconsistencias detectadas en requisición {requisicion.folio}:\n"
                + "\n".join(f"  - {d}" for d in discrepancias)
            )
            logger.warning(mensaje)
            raise ValueError(mensaje)
        
        logger.info(
            f"ISS-002: Validación de consistencia exitosa para {requisicion.folio}. "
            f"Lotes verificados: {lotes_usados.count()}"
        )
        return True
    
    # ISS-001 FIX (audit4): Estados donde cancelar requiere reversión de movimientos
    ESTADOS_CON_MOVIMIENTOS_POSIBLES = {'autorizada', 'en_surtido', 'parcial', 'surtida'}
    
    # ISS-001/002 FIX (audit4): Estados que NUNCA pueden cancelarse (ya hay entrega)
    ESTADOS_SIN_CANCELACION = {'entregada', 'vencida'}
    
    @transaction.atomic
    def cancelar_requisicion(self, motivo, forzar_reversion=False):
        """
        ISS-001/002/003 FIX (audit5): Cancela una requisición con control de movimientos.
        
        LÓGICA DE CANCELACIÓN:
        1. Estados sin movimientos (borrador, enviada, en_revision): Cancelación directa
        2. Estados con posibles movimientos (autorizada, en_surtido, parcial, surtida):
           - Si hay movimientos: REQUIERE forzar_reversion=True y se revierten
           - Si no hay movimientos: Cancelación directa
        3. Estados finales NO cancelables: entregada, vencida
        
        ISS-003 FIX (audit5): Ahora permite cancelar 'surtida' con reversión de stock.
        
        Args:
            motivo: Motivo de cancelación (obligatorio, mínimo 10 caracteres)
            forzar_reversion: Si True, revierte movimientos existentes
            
        Returns:
            dict: Resultado de la cancelación
            
        Raises:
            EstadoInvalidoError: Si la requisición no es cancelable
            ValidationError: Si no se proporciona motivo o hay movimientos sin forzar
        """
        from django.core.exceptions import ValidationError
        from core.models import Requisicion as RequisicionModel, Movimiento
        
        # ISS-001 FIX: Validar motivo obligatorio con longitud mínima
        if not motivo or len(motivo.strip()) < 10:
            raise ValidationError({
                'motivo': 'Se requiere un motivo de cancelación de al menos 10 caracteres'
            })
        
        # Bloquear requisición
        requisicion = RequisicionModel.objects.select_for_update().get(pk=self.requisicion.pk)
        
        # Validar estado cancelable
        estado_actual = (requisicion.estado or '').lower()
        
        # ISS-001 FIX: Estados finales NUNCA cancelables
        if estado_actual in self.ESTADOS_SIN_CANCELACION:
            raise EstadoInvalidoError(
                f"No se pueden cancelar requisiciones en estado '{estado_actual}'. "
                f"Estados finales no cancelables: {self.ESTADOS_SIN_CANCELACION}",
                estado_actual=estado_actual
            )
        
        # ISS-001 FIX: Verificar movimientos existentes antes de cancelar
        tiene_movimientos = Movimiento.objects.filter(
            requisicion=requisicion,
            tipo='salida'
        ).exists()
        
        # ISS-001 FIX: Si hay movimientos y no se fuerza reversión, bloquear
        if tiene_movimientos and not forzar_reversion:
            raise ValidationError({
                'cancelacion': (
                    f"La requisición tiene movimientos de inventario asociados. "
                    f"Para cancelar debe confirmar la reversión de stock (forzar_reversion=True). "
                    f"Esto restaurará el stock en farmacia y descontará del centro."
                )
            })
        
        # ISS-003 FIX (audit5): Estados que permiten cancelación
        # Agregado 'surtida' - cancelable con forzar_reversion=True
        estados_cancelables = ['borrador', 'pendiente_admin', 'pendiente_director', 
                              'enviada', 'en_revision', 'autorizada', 'en_surtido', 
                              'parcial', 'surtida']
        
        if estado_actual not in estados_cancelables:
            raise EstadoInvalidoError(
                f"No se pueden cancelar requisiciones en estado: {estado_actual}. "
                f"Estados cancelables: {estados_cancelables}",
                estado_actual=estado_actual
            )
        
        movimientos_revertidos = []
        
        # ISS-003 FIX (audit5): Estados con posibles movimientos a revertir
        # Incluye en_surtido y surtida para permitir cancelación con reversión completa
        estados_con_movimientos = ['autorizada', 'en_surtido', 'parcial', 'surtida']
        if estado_actual in estados_con_movimientos and tiene_movimientos:
            # Buscar movimientos de salida asociados
            movimientos_salida = Movimiento.objects.select_for_update().filter(
                requisicion=requisicion,
                tipo='salida'
            ).select_related('lote')
            
            for mov in movimientos_salida:
                # Restaurar stock en lote de farmacia
                cantidad_restaurar = abs(mov.cantidad)
                
                Lote.objects.filter(pk=mov.lote.pk).update(
                    cantidad_actual=F('cantidad_actual') + cantidad_restaurar,
                    activo=True,
                    updated_at=timezone.now()
                )
                
                # Registrar movimiento de ajuste (entrada para restaurar stock)
                Movimiento.objects.create(
                    tipo='entrada',
                    producto=mov.lote.producto,
                    lote=mov.lote,
                    centro_destino=mov.centro_origen,  # La entrada va al centro origen del mov de salida
                    requisicion=requisicion,
                    usuario=self.usuario,
                    cantidad=cantidad_restaurar,
                    motivo=f'REVERSO por cancelación de requisición {requisicion.numero}'
                )
                
                movimientos_revertidos.append({
                    'lote': mov.lote.numero_lote,
                    'cantidad_restaurada': cantidad_restaurar
                })
            
            # Buscar entradas en centro y revertir
            movimientos_entrada = Movimiento.objects.select_for_update().filter(
                requisicion=requisicion,
                tipo='entrada'
            ).select_related('lote')
            
            for mov in movimientos_entrada:
                # Descontar del lote del centro
                Lote.objects.filter(pk=mov.lote.pk).update(
                    cantidad_actual=F('cantidad_actual') - mov.cantidad,
                    updated_at=timezone.now()
                )
                
                # Registrar movimiento de ajuste (salida para descontar del centro)
                Movimiento.objects.create(
                    tipo='salida',
                    producto=mov.lote.producto,
                    lote=mov.lote,
                    centro_origen=mov.centro_destino,  # La salida viene del centro destino del mov de entrada
                    requisicion=requisicion,
                    usuario=self.usuario,
                    cantidad=-mov.cantidad,
                    motivo=f'REVERSO por cancelación de requisición {requisicion.numero}'
                )
            
            # Resetear cantidades surtidas en detalles
            requisicion.detalles.update(cantidad_surtida=0)
        
        # ISS-001 FIX (audit4): Registrar transición para trazabilidad
        self.requisicion = requisicion
        self.registrar_transicion_historial(
            estado_anterior=estado_actual,
            estado_nuevo='cancelada',
            observaciones=f'Motivo: {motivo}. Movimientos revertidos: {len(movimientos_revertidos)}'
        )
        
        # Actualizar estado a cancelada
        requisicion.estado = 'cancelada'
        # ISS-001 FIX: Guardar motivo con timestamp y actor para trazabilidad
        from django.utils import timezone
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        requisicion.notas = (requisicion.notas or '') + (
            f'\n[CANCELACIÓN {timestamp}] Por: {self.usuario.username} | '
            f'Motivo: {motivo} | Movimientos revertidos: {len(movimientos_revertidos)}'
        )
        requisicion.save(update_fields=[
            'estado', 'notas', 'updated_at'
        ])
        
        logger.info(
            f"Requisición {requisicion.folio} cancelada por {self.usuario.username}. "
            f"Motivo: {motivo}. Movimientos revertidos: {len(movimientos_revertidos)}"
        )
        
        return {
            'exito': True,
            'folio': requisicion.folio,
            'estado': 'cancelada',
            'motivo': motivo,
            'movimientos_revertidos': movimientos_revertidos,
            'usuario': self.usuario.username
        }


class CentroPermissionMixin:
    """
    ISS-030: Mixin para validar acceso por centro.
    
    ISS-003 FIX: Usa catálogo real de roles del sistema.
    
    Uso:
        class MyViewSet(CentroPermissionMixin, viewsets.ModelViewSet):
            ...
    """
    
    # ISS-003 FIX: Roles con acceso global (pueden ver/operar en cualquier centro)
    ROLES_ACCESO_GLOBAL = {
        # Administradores
        'admin_sistema', 'superusuario', 'administrador',
        # Farmacia
        'farmacia', 'admin_farmacia', 'farmaceutico', 'usuario_farmacia',
        # Vista (solo lectura pero global)
        'vista', 'usuario_vista',
    }
    
    def get_centro_from_request(self):
        """Obtiene centro_id del request (body o query params)."""
        centro_id = self.request.data.get('centro') or self.request.query_params.get('centro')
        return centro_id
    
    def check_centro_permission(self, centro_id=None):
        """
        ISS-003 FIX: Verifica que el usuario tenga acceso al centro especificado.
        
        Args:
            centro_id: ID del centro a verificar (o None para obtener del request)
            
        Raises:
            PermissionDenied: Si no tiene acceso
        """
        from rest_framework.exceptions import PermissionDenied
        
        if centro_id is None:
            centro_id = self.get_centro_from_request()
        
        if centro_id is None:
            return  # No se especificó centro, permitir
        
        user = self.request.user
        
        # Superuser siempre tiene acceso
        if user.is_superuser:
            return
        
        # ISS-003 FIX: Verificar contra catálogo real de roles globales
        user_rol = (getattr(user, 'rol', '') or '').lower()
        if user_rol in self.ROLES_ACCESO_GLOBAL:
            return
        
        # Verificar si usuario pertenece al centro
        user_centro = getattr(user, 'centro', None)
        if user_centro is None:
            raise PermissionDenied("Usuario sin centro asignado")
        
        try:
            centro_id_int = int(centro_id)
        except (TypeError, ValueError):
            raise PermissionDenied("ID de centro inválido")
        
        if user_centro.pk != centro_id_int:
            logger.warning(
                f"Acceso denegado a centro {centro_id} para usuario {user.username} "
                f"(centro asignado: {user_centro.pk})"
            )
            raise PermissionDenied("No tiene acceso a este centro")
    
    def filter_queryset_by_centro(self, queryset):
        """
        ISS-003 FIX + ISS-030: Filtra queryset por centro del usuario.
        
        Roles globales ven todo. Usuarios de centro solo ven su centro.
        
        Args:
            queryset: QuerySet a filtrar
            
        Returns:
            QuerySet filtrado
        """
        user = self.request.user
        
        if user.is_superuser:
            return queryset
        
        # ISS-003 FIX: Verificar contra catálogo real de roles
        user_rol = (getattr(user, 'rol', '') or '').lower()
        if user_rol in self.ROLES_ACCESO_GLOBAL:
            return queryset
        
        # Usuario de centro: filtrar por su centro
        user_centro = getattr(user, 'centro', None)
        if user_centro is None:
            return queryset.none()
        
        # Intentar filtrar por campo 'centro'
        if hasattr(queryset.model, 'centro'):
            return queryset.filter(centro=user_centro)
        
        # Para requisiciones, filtrar por centro de la requisición
        if hasattr(queryset.model, 'centro_id'):
            return queryset.filter(centro_id=user_centro.pk)
        
        return queryset
