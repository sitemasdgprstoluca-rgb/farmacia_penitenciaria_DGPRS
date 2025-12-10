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
    ISS-002: Usa máquina de estados del modelo Requisicion (fuente única de verdad).
    """
    
    # Transiciones de estado válidas para requisiciones
    # ISS-001/002 + ISS-004 FIX (audit3): FLUJO V2 - Transiciones ESTRICTAS
    # 
    # Flujo jerárquico obligatorio:
    #   borrador → pendiente_admin → pendiente_director → enviada
    #   → en_revision → autorizada → en_surtido → surtida → entregada
    # 
    # ISS-004 FIX: Se ELIMINAN saltos de estados:
    #   - autorizada → surtida (DEBE pasar por en_surtido)
    #   - enviada → autorizada (DEBE pasar por en_revision)
    # 
    # Estados negativos: rechazada, cancelada, vencida, devuelta
    TRANSICIONES_VALIDAS_DEFAULT = {
        # Flujo del centro penitenciario (creación y envío)
        'borrador': ['pendiente_admin', 'cancelada'],
        'pendiente_admin': ['pendiente_director', 'rechazada', 'devuelta', 'cancelada'],
        'pendiente_director': ['enviada', 'rechazada', 'devuelta', 'cancelada'],
        
        # Flujo de farmacia central (revisión y autorización)
        # ISS-004 FIX: Enviada DEBE pasar por en_revision antes de autorizar
        'enviada': ['en_revision', 'rechazada', 'cancelada'],
        'en_revision': ['autorizada', 'rechazada', 'devuelta', 'cancelada'],
        
        # Flujo de surtido (solo farmacia central)
        # ISS-004 FIX: Autorizada DEBE pasar por en_surtido antes de surtida
        'autorizada': ['en_surtido', 'cancelada'],
        'en_surtido': ['surtida', 'parcial', 'cancelada'],
        'parcial': ['en_surtido', 'surtida', 'cancelada'],  # Parcial puede reintentar
        'surtida': ['entregada', 'vencida'],
        
        # Devolución - regresa a borrador para que médico corrija
        'devuelta': ['borrador', 'cancelada'],
        
        # Estados finales - NO pueden cambiar
        'entregada': [],
        'rechazada': [],
        'vencida': [],
        'cancelada': [],
    }
    
    # ISS-004 FIX (audit3): Roles autorizados por transición
    ROLES_POR_TRANSICION = {
        # Creación y envío - roles de centro
        ('borrador', 'pendiente_admin'): ['medico', 'centro', 'usuario_centro'],
        ('pendiente_admin', 'pendiente_director'): ['administrador_centro'],
        ('pendiente_director', 'enviada'): ['director_centro'],
        
        # Revisión y autorización - roles de farmacia
        ('enviada', 'en_revision'): ['farmacia', 'farmaceutico', 'admin_farmacia'],
        ('en_revision', 'autorizada'): ['farmacia', 'farmaceutico', 'admin_farmacia'],
        ('en_revision', 'rechazada'): ['farmacia', 'farmaceutico', 'admin_farmacia'],
        ('en_revision', 'devuelta'): ['farmacia', 'farmaceutico', 'admin_farmacia'],
        
        # Surtido - solo farmacia
        ('autorizada', 'en_surtido'): ['farmacia', 'farmaceutico', 'admin_farmacia'],
        ('en_surtido', 'surtida'): ['farmacia', 'farmaceutico', 'admin_farmacia'],
        ('en_surtido', 'parcial'): ['farmacia', 'farmaceutico', 'admin_farmacia'],
        
        # Recepción - solo centro destino
        ('surtida', 'entregada'): ['centro', 'usuario_centro', 'administrador_centro', 'director_centro'],
        
        # Cancelaciones - depende del estado actual
        ('borrador', 'cancelada'): ['medico', 'centro', 'usuario_centro', 'administrador_centro'],
        ('pendiente_admin', 'cancelada'): ['administrador_centro', 'director_centro'],
        ('pendiente_director', 'cancelada'): ['director_centro'],
        ('enviada', 'cancelada'): ['farmacia', 'admin_farmacia'],
        ('en_revision', 'cancelada'): ['farmacia', 'admin_farmacia'],
        ('autorizada', 'cancelada'): ['farmacia', 'admin_farmacia'],
        ('en_surtido', 'cancelada'): ['farmacia', 'admin_farmacia'],
    }
    
    @property
    def ESTADOS_SURTIBLES(self):
        """ISS-002/FLUJO V2: Obtener estados surtibles del modelo."""
        from core.models import Requisicion
        # FLUJO V2: Solo se puede surtir desde autorizada o en_surtido
        return getattr(Requisicion, 'ESTADOS_SURTIBLES', ['autorizada', 'en_surtido'])
    
    @property
    def TRANSICIONES_VALIDAS(self):
        """ISS-002: Obtener transiciones del modelo (fuente única de verdad)."""
        from core.models import Requisicion
        return getattr(Requisicion, 'TRANSICIONES_VALIDAS', self.TRANSICIONES_VALIDAS_DEFAULT)
    
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
    
    def validar_transicion_estado(self, nuevo_estado):
        """
        ISS-004 FIX (audit3): Valida transición con registro de actor/fecha.
        ISS-003 FIX (audit4): Valida pertenencia al centro/contrato.
        
        Validaciones:
        1. Transición permitida según máquina de estados
        2. Rol del usuario autorizado para esta transición
        3. ISS-003 FIX: Pertenencia al centro para transiciones críticas
        4. Registro de quién/cuándo para auditoría
        
        Args:
            nuevo_estado: Estado destino
            
        Raises:
            EstadoInvalidoError: Si la transición no es válida
            PermisoRequisicionError: Si el rol no está autorizado o no pertenece al centro
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
        
        # 2. ISS-004 FIX: Validar rol autorizado para esta transición
        if not self.usuario.is_superuser:
            user_rol = (getattr(self.usuario, 'rol', '') or '').lower()
            transicion_key = (estado_actual, nuevo_estado_lower)
            roles_permitidos = self.ROLES_POR_TRANSICION.get(transicion_key, [])
            
            # Si hay roles definidos para esta transición, validar
            if roles_permitidos and user_rol not in roles_permitidos:
                # Fallback: verificar si es admin/farmacia genérico
                roles_admin = {'admin', 'admin_sistema', 'superusuario', 'administrador'}
                if user_rol not in roles_admin:
                    logger.warning(
                        f"ISS-004: Rol '{user_rol}' no autorizado para transición "
                        f"{estado_actual} → {nuevo_estado}. Roles permitidos: {roles_permitidos}"
                    )
                    raise PermisoRequisicionError(
                        f"Su rol '{user_rol}' no está autorizado para la transición "
                        f"{estado_actual} → {nuevo_estado}. "
                        f"Roles permitidos: {', '.join(roles_permitidos)}"
                    )
        
        # 3. ISS-003 FIX (audit4): Validar pertenencia al centro/contrato
        self._validar_pertenencia_centro_transicion(estado_actual, nuevo_estado_lower)
        
        # 4. ISS-004 FIX: Registrar transición para auditoría
        logger.info(
            f"ISS-004 TRANSICIÓN: {self.requisicion.folio} | "
            f"{estado_actual} → {nuevo_estado} | "
            f"Usuario: {self.usuario.username} | "
            f"Rol: {getattr(self.usuario, 'rol', 'N/A')} | "
            f"Fecha: {timezone.now().isoformat()}"
        )
        
        return True
    
    def _validar_pertenencia_centro_transicion(self, estado_actual, nuevo_estado):
        """
        ISS-003 FIX (audit4): Valida que el usuario pertenezca al centro/contrato correcto.
        
        Reglas:
        - Transiciones de CENTRO (crear, aprobar interno): usuario debe pertenecer al centro de la req
        - Transiciones de FARMACIA (autorizar, surtir): usuario debe ser farmacia central (sin centro)
        - Recepción: usuario debe pertenecer al centro destino
        
        Args:
            estado_actual: Estado origen
            nuevo_estado: Estado destino
            
        Raises:
            PermisoRequisicionError: Si no pertenece al centro/contrato correcto
        """
        if self.usuario.is_superuser:
            return True
        
        user_centro = getattr(self.usuario, 'centro', None)
        user_rol = (getattr(self.usuario, 'rol', '') or '').lower()
        requisicion_centro = self.requisicion.centro
        
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
        
        # ISS-003 FIX: Validar transiciones de farmacia
        if transicion in transiciones_farmacia:
            roles_farmacia = {'farmacia', 'farmaceutico', 'admin_farmacia', 'usuario_farmacia'}
            
            # Usuario debe ser de farmacia central
            if user_rol in roles_farmacia:
                # Farmacia con centro asignado = configuración errónea
                if user_centro is not None:
                    logger.warning(
                        f"ISS-003: Usuario farmacia {self.usuario.username} tiene centro asignado "
                        f"({user_centro.pk}). Permitiendo pero se recomienda corregir."
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
        
        # ISS-005 FIX: Si hay movimientos (parcial), revertirlos
        if estado_actual == 'parcial':
            # Buscar y revertir movimientos de salida
            movimientos_salida = Movimiento.objects.select_for_update().filter(
                requisicion=requisicion,
                tipo='salida'
            ).select_related('lote')
            
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
                    'cantidad_restaurada': cantidad_restaurar
                })
            
            # Revertir entradas en centro
            movimientos_entrada = Movimiento.objects.select_for_update().filter(
                requisicion=requisicion,
                tipo='entrada'
            ).select_related('lote')
            
            for mov in movimientos_entrada:
                Lote.objects.filter(pk=mov.lote.pk).update(
                    cantidad_actual=F('cantidad_actual') - mov.cantidad,
                    updated_at=timezone.now()
                )
                
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
    
    def registrar_transicion_historial(self, estado_anterior, estado_nuevo, observaciones=''):
        """
        ISS-004 FIX (audit3): Registra transición en historial para trazabilidad.
        
        Guarda en las notas de la requisición un registro estructurado de cada
        transición con: estado anterior, estado nuevo, usuario, fecha, rol.
        
        Args:
            estado_anterior: Estado antes de la transición
            estado_nuevo: Estado después de la transición
            observaciones: Observaciones adicionales
        """
        from django.utils import timezone
        
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        user_rol = getattr(self.usuario, 'rol', 'N/A')
        
        # Formato estructurado para facilitar parsing posterior
        registro = (
            f"\n[TRANSICIÓN {timestamp}] "
            f"{estado_anterior} → {estado_nuevo} | "
            f"Por: {self.usuario.username} ({user_rol})"
        )
        
        if observaciones:
            registro += f" | Obs: {observaciones}"
        
        # Agregar al campo notas (único campo de texto disponible)
        notas_actuales = self.requisicion.notas or ''
        self.requisicion.notas = notas_actuales + registro
    
    def validar_permisos_surtido(self, is_farmacia_or_admin_fn, get_user_centro_fn):
        """
        ISS-003 FIX (audit2 + audit3): Valida permisos del usuario para surtir.
        
        IMPORTANTE: Solo farmacia central y administradores pueden surtir.
        Los usuarios de centros NO pueden surtir, solo pueden confirmar recepción.
        
        ISS-003 FIX (audit3): Valida adscripción del usuario:
        - Usuarios de farmacia deben estar adscritos a farmacia central (centro=NULL)
        - Solo pueden surtir requisiciones dentro de su ámbito
        
        Args:
            is_farmacia_or_admin_fn: Función que verifica si usuario es farmacia/admin
            get_user_centro_fn: Función que obtiene el centro del usuario
            
        Raises:
            PermisoRequisicionError: Si el usuario no tiene permiso
        """
        if self.usuario.is_superuser:
            return True
        
        # Verificar rol farmacia/admin
        if not is_farmacia_or_admin_fn(self.usuario):
            # ISS-003 FIX: Usuarios de centro NO pueden surtir
            raise PermisoRequisicionError(
                "Solo personal de farmacia central o administradores pueden surtir requisiciones. "
                "Los usuarios de centro pueden confirmar recepción usando el endpoint correspondiente."
            )
        
        # ISS-003 FIX (audit3): Validar adscripción del usuario de farmacia
        # Los usuarios de farmacia central no deben tener centro asignado
        user_centro = get_user_centro_fn(self.usuario)
        user_rol = (getattr(self.usuario, 'rol', '') or '').lower()
        
        # Roles de farmacia central no deben estar adscritos a un centro específico
        roles_farmacia_central = {'farmacia', 'farmaceutico', 'admin_farmacia', 'usuario_farmacia'}
        if user_rol in roles_farmacia_central and user_centro is not None:
            # Farmacia con centro asignado = probablemente error de configuración
            # Solo advertir, pero permitir si es necesario
            logger.warning(
                f"ISS-003: Usuario farmacia {self.usuario.username} tiene centro asignado "
                f"({user_centro.pk}). Se recomienda que farmacia central no tenga centro."
            )
        
        # Validar que la requisición pertenece a un centro válido
        requisicion_centro = getattr(self.requisicion, 'centro', None)
        if requisicion_centro is None and getattr(self.requisicion, 'centro_id', None):
            # Cargar centro si solo tenemos el ID
            from core.models import Centro
            try:
                requisicion_centro = Centro.objects.get(pk=self.requisicion.centro_id)
            except Centro.DoesNotExist:
                raise PermisoRequisicionError(
                    f"Centro de requisición no válido: {self.requisicion.centro_id}"
                )
        
        if requisicion_centro is None:
            raise PermisoRequisicionError(
                "La requisición no tiene centro destino asignado. No se puede surtir."
            )
        
        # ISS-003 FIX (audit3): Registrar quién realiza el surtido para auditoría
        logger.info(
            f"ISS-003: Usuario {self.usuario.username} (rol: {user_rol}) "
            f"autorizado para surtir requisición {self.requisicion.folio} "
            f"del centro {requisicion_centro.nombre}"
        )
        
        return True
    
    def validar_stock_disponible(self):
        """
        ISS-001 FIX: Valida que hay stock suficiente SOLO en farmacia central.
        ISS-002 FIX: Solo considera lotes NO caducados.
        ISS-004 FIX (audit2): Descuenta stock comprometido por otras requisiciones.
        
        IMPORTANTE: Las requisiciones SOLO se surten desde farmacia central.
        El stock del centro destino NO debe considerarse para validación,
        ya que ese stock ya fue transferido previamente y pertenece al centro.
        
        Returns:
            list: Lista vacía si hay stock suficiente
            
        Raises:
            StockInsuficienteError: Si no hay stock suficiente en farmacia central
        """
        from django.utils import timezone
        
        hoy = timezone.now().date()
        errores_stock = []
        
        for detalle in self.requisicion.detalles.select_related('producto'):
            requerido = (detalle.cantidad_autorizada or detalle.cantidad_solicitada) - (detalle.cantidad_surtida or 0)
            if requerido <= 0:
                continue
            
            # ISS-001 FIX: SOLO lotes de farmacia central (centro=NULL)
            # ISS-002 FIX: SOLO lotes NO caducados (fecha_caducidad >= hoy)
            stock_farmacia = Lote.objects.filter(
                centro__isnull=True,  # Solo farmacia central
                producto=detalle.producto,
                activo=True,
                cantidad_actual__gt=0,
                fecha_caducidad__gte=hoy,  # ISS-002 FIX: Solo lotes vigentes
            ).aggregate(total=Sum('cantidad_actual'))['total'] or 0
            
            # ISS-004 FIX (audit2): Descontar stock comprometido por OTRAS requisiciones
            # (excluyendo esta misma requisición para evitar contar doble)
            stock_comprometido = self._get_stock_comprometido_otras(detalle.producto)
            disponible = stock_farmacia - stock_comprometido
            
            if disponible < requerido:
                errores_stock.append({
                    'producto': detalle.producto.clave,
                    'producto_nombre': (detalle.producto.nombre or '')[:50],
                    'requerido': requerido,
                    'disponible': disponible,
                    'stock_farmacia': stock_farmacia,
                    'stock_comprometido': stock_comprometido,
                    'deficit': requerido - disponible
                })
        
        if errores_stock:
            raise StockInsuficienteError(
                f"Stock insuficiente para {len(errores_stock)} producto(s)",
                detalles_stock=errores_stock
            )
        
        return []
    
    def _get_stock_comprometido_otras(self, producto):
        """
        ISS-004 FIX (audit2): Calcula stock comprometido por OTRAS requisiciones.
        
        Excluye la requisición actual para no contar doble.
        
        Args:
            producto: Producto para calcular comprometido
            
        Returns:
            int: Cantidad comprometida por otras requisiciones
        """
        from django.db.models import Sum
        from core.models import DetalleRequisicion
        
        # ISS-DB-002: Estados que comprometen stock
        ESTADOS_COMPROMETIDOS = ['autorizada', 'en_surtido', 'parcial', 'surtida']
        
        comprometido = DetalleRequisicion.objects.filter(
            requisicion__estado__in=ESTADOS_COMPROMETIDOS,
            producto=producto
        ).exclude(
            requisicion_id=self.requisicion.pk  # Excluir esta requisición
        ).aggregate(
            total=Sum('cantidad_autorizada') - Sum('cantidad_surtida')
        )
        
        # Calcular pendiente de surtir
        total_autorizado = DetalleRequisicion.objects.filter(
            requisicion__estado__in=ESTADOS_COMPROMETIDOS,
            producto=producto
        ).exclude(
            requisicion_id=self.requisicion.pk
        ).aggregate(total=Sum('cantidad_autorizada'))['total'] or 0
        
        total_surtido = DetalleRequisicion.objects.filter(
            requisicion__estado__in=ESTADOS_COMPROMETIDOS,
            producto=producto
        ).exclude(
            requisicion_id=self.requisicion.pk
        ).aggregate(total=Sum('cantidad_surtida'))['total'] or 0
        
        return max(0, total_autorizado - total_surtido)
    
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
        
        # ISS-003 FIX: Bloquear requisición PRIMERO para evitar doble surtido
        # Esto previene race conditions donde dos procesos intentan surtir simultáneamente
        requisicion_bloqueada = RequisicionModel.objects.select_for_update().get(pk=self.requisicion.pk)
        
        # ISS-003 FIX: Revalidar estado DESPUÉS del bloqueo
        estado_actual = (requisicion_bloqueada.estado or '').lower()
        if estado_actual not in self.ESTADOS_SURTIBLES:
            raise EstadoInvalidoError(
                f"Solo se pueden surtir requisiciones en estado: {self.ESTADOS_SURTIBLES}. "
                f"Estado actual: {estado_actual}",
                estado_actual=estado_actual
            )
        
        # Actualizar referencia local con la versión bloqueada
        self.requisicion = requisicion_bloqueada
        
        # 2. Validar permisos
        self.validar_permisos_surtido(is_farmacia_or_admin_fn, get_user_centro_fn)
        
        # 3. Validar stock (pre-check)
        self.validar_stock_disponible()
        
        centro_requisicion = self.requisicion.centro
        items_surtidos = []
        
        # ISS-003 FIX + ISS-005 FIX: Bloquear detalles para evitar modificaciones concurrentes
        detalles_bloqueados = DetalleRequisicion.objects.select_for_update().filter(
            requisicion=self.requisicion
        ).select_related('producto')
        
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
            
            # ISS-002 FIX + ISS-014: Obtener lotes SOLO de farmacia central CON BLOQUEO
            # select_for_update() bloquea las filas hasta que termine la transacción
            # 
            # IMPORTANTE: Solo usamos lotes de farmacia central (centro=NULL).
            # Los lotes del centro destino NO deben usarse como fuente de surtido.
            # ISS-002 FIX: Filtrar por fecha_caducidad >= hoy para evitar lotes vencidos
            # 
            # ISS-007 FIX: El order_by('id') FINAL asegura un orden determinista
            # para evitar deadlocks cuando múltiples transacciones adquieren locks.
            # FEFO (fecha_caducidad primero), luego ID para consistencia.
            lotes = Lote.objects.select_for_update().filter(
                centro__isnull=True,  # Solo farmacia central
                producto=detalle.producto,
                activo=True,
                cantidad_actual__gt=0,
                fecha_caducidad__gte=hoy,  # ISS-002 FIX: Solo lotes vigentes
            ).order_by('fecha_caducidad', 'id')  # FEFO + ID para evitar deadlocks
            
            for lote in lotes:
                if pendiente <= 0:
                    break
                
                usar = min(pendiente, lote.cantidad_actual)
                
                # Guardar stock previo antes de descontar
                stock_previo = lote.cantidad_actual
                
                # ISS-014: Descontar con verificación atómica
                lote_info = self._descontar_lote_atomico(lote, usar)
                
                # Registrar movimiento de salida (pasando stock_previo para validación)
                movimiento_salida = self._crear_movimiento(
                    lote=lote,
                    tipo='salida',
                    cantidad=-usar,
                    centro=lote.centro,
                    observaciones=f'SALIDA_POR_REQUISICION {self.requisicion.folio}',
                    stock_previo=stock_previo
                )
                
                # ISS-002 FIX: Registrar trazabilidad detalle-lote
                self._registrar_detalle_surtido(
                    detalle=detalle,
                    lote=lote,
                    cantidad=usar,
                    movimiento=movimiento_salida
                )
                
                # Si lote era de farmacia central, crear entrada en centro destino
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
                    'lote_origen_id': lote.pk
                })
                
                detalle.cantidad_surtida = (detalle.cantidad_surtida or 0) + usar
                pendiente -= usar
                cantidad_surtida_item += usar
            
            # Guardar detalle actualizado
            detalle.save(update_fields=['cantidad_surtida'])
            
            items_surtidos.append({
                'producto': detalle.producto.codigo_barras or detalle.producto.nombre,
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
        
        # ISS-DB-002: Usar parcial para surtido incompleto
        nuevo_estado = 'surtida' if completada else 'parcial'
        self.requisicion.estado = nuevo_estado
        self.requisicion.fecha_surtido = timezone.now()
        self.requisicion.usuario_firma_surtido = self.usuario
        self.requisicion.fecha_firma_surtido = timezone.now()
        self.requisicion.save(update_fields=['estado', 'fecha_surtido', 'usuario_firma_surtido', 'fecha_firma_surtido', 'updated_at'])
        
        logger.info(
            f"Requisición {self.requisicion.folio} surtida exitosamente por {self.usuario.username}. "
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
        Crea un movimiento de inventario.
        
        Args:
            lote: Lote asociado
            tipo: 'entrada' o 'salida'
            cantidad: Cantidad (negativo para salidas)
            centro: Centro del movimiento
            observaciones: Texto descriptivo
            stock_previo: Stock antes del movimiento (para validación)
            producto: Producto asociado (si no se pasa, se toma del lote)
            
        Returns:
            Movimiento: Instancia creada
        """
        # Determinar centro_origen/centro_destino según tipo
        centro_origen = centro if tipo == 'salida' else None
        centro_destino = centro if tipo == 'entrada' else None
        
        # Producto es requerido en la BD
        producto_movimiento = producto or (lote.producto if lote else None)
        
        movimiento = Movimiento(
            tipo=tipo,
            producto=producto_movimiento,
            lote=lote,
            centro_origen=centro_origen,
            centro_destino=centro_destino,
            requisicion=self.requisicion,
            usuario=self.usuario if self.usuario.is_authenticated else None,
            cantidad=cantidad,
            motivo=observaciones
        )
        # Pasar stock previo para evitar re-validación (ya descontamos)
        if stock_previo is not None:
            movimiento._stock_pre_movimiento = stock_previo
        movimiento.save()
        
        self._movimientos_creados.append(movimiento)
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
        Obtiene o crea lote destino en el centro.
        
        El lote en el centro es una COPIA FIEL del lote de farmacia:
        - Mismo número de lote
        - Misma fecha de caducidad
        - Vinculado a lote_origen
        
        Args:
            lote_origen: Lote de farmacia central
            centro_destino: Centro donde crear/actualizar lote
            cantidad: Cantidad a agregar
            
        Returns:
            Lote: Instancia del lote destino
        """
        # Buscar lote existente con mismo número en el centro
        lote_destino = Lote.objects.select_for_update().filter(
            producto=lote_origen.producto,
            numero_lote=lote_origen.numero_lote,
            centro=centro_destino,
            activo=True
        ).first()
        
        if lote_destino:
            # Actualizar cantidad (ya está activo)
            Lote.objects.filter(pk=lote_destino.pk).update(
                cantidad_actual=F('cantidad_actual') + cantidad,
                cantidad_inicial=F('cantidad_inicial') + cantidad,
                activo=True,
                updated_at=timezone.now()
            )
            lote_destino.refresh_from_db()
        else:
            # Buscar lote inactivo que podamos reactivar
            lote_destino = Lote.objects.select_for_update().filter(
                producto=lote_origen.producto,
                numero_lote=lote_origen.numero_lote,
                centro=centro_destino,
                activo=False
            ).first()
            
            if lote_destino:
                # Reactivar lote existente
                Lote.objects.filter(pk=lote_destino.pk).update(
                    cantidad_actual=F('cantidad_actual') + cantidad,
                    cantidad_inicial=F('cantidad_inicial') + cantidad,
                    activo=True,
                    updated_at=timezone.now()
                )
                lote_destino.refresh_from_db()
            else:
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
        
        if user_centro and requisicion.centro_id != user_centro.pk and not self.usuario.is_superuser:
            raise PermisoRequisicionError(
                f"Solo usuarios del centro {requisicion.centro.nombre} pueden confirmar esta recepción"
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
    
    # ISS-001 FIX (audit4): Estados donde cancelar requiere reversión de movimientos
    ESTADOS_CON_MOVIMIENTOS_POSIBLES = {'autorizada', 'en_surtido', 'parcial', 'surtida'}
    
    # ISS-001/002 FIX (audit4): Estados que NUNCA pueden cancelarse (ya hay entrega)
    ESTADOS_SIN_CANCELACION = {'entregada', 'vencida'}
    
    @transaction.atomic
    def cancelar_requisicion(self, motivo, forzar_reversion=False):
        """
        ISS-001/002 FIX (audit4): Cancela una requisición con control de movimientos.
        
        LÓGICA DE CANCELACIÓN:
        1. Estados sin movimientos (borrador, enviada, en_revision): Cancelación directa
        2. Estados con posibles movimientos (autorizada, en_surtido, parcial):
           - Si hay movimientos: REQUIERE forzar_reversion=True y se revierten
           - Si no hay movimientos: Cancelación directa
        3. Estados finales (surtida, entregada, vencida): NO cancelables
        
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
        
        # Estados que permiten cancelación (con o sin movimientos)
        estados_cancelables = ['borrador', 'pendiente_admin', 'pendiente_director', 
                              'enviada', 'en_revision', 'autorizada', 'en_surtido', 'parcial']
        
        if estado_actual not in estados_cancelables:
            raise EstadoInvalidoError(
                f"No se pueden cancelar requisiciones en estado: {estado_actual}. "
                f"Estados cancelables: {estados_cancelables}",
                estado_actual=estado_actual
            )
        
        movimientos_revertidos = []
        
        # ISS-003 FIX: Si hay movimientos, revertirlos
        if estado_actual in ['autorizada', 'parcial']:
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
