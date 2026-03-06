# -*- coding: utf-8 -*-
from rest_framework import serializers
from django.db.models import Sum
from django.utils import timezone
from .models import (
    User, Centro, Producto, Lote, Requisicion, DetalleRequisicion, 
    Movimiento, AuditoriaLogs, ImportacionLogs, Notificacion, ConfiguracionSistema,
    TemaGlobal, HojaRecoleccion, DetalleHojaRecoleccion, UserProfile,
    ProductoImagen, LoteDocumento, Donacion, DetalleDonacion, SalidaDonacion,
    ProductoDonacion,  # Catálogo independiente de donaciones
    RequisicionHistorialEstados,  # FLUJO V2
    # Módulo de Dispensaciones
    Paciente, Dispensacion, DetalleDispensacion, HistorialDispensacion,
    # Módulo de Compras Caja Chica
    CompraCajaChica, DetalleCompraCajaChica, InventarioCajaChica,
    MovimientoCajaChica, HistorialCompraCajaChica,
)
from .constants import EXTRA_PERMISSIONS
import logging
import re

logger = logging.getLogger(__name__)

# =============================================================================
# PERMISOS POR ROL
# =============================================================================

# =============================================================================
# PERMISOS POR ROL - FLUJO V2
# =============================================================================
# Incluye permisos del flujo jerárquico de requisiciones:
# - autorizarAdmin: Autorizar como Administrador del Centro
# - autorizarDirector: Autorizar como Director del Centro
# - recibirFarmacia: Recibir requisiciones en Farmacia Central
# - autorizarFarmacia: Autorizar requisiciones en Farmacia Central
# - asignarFechaRecoleccion: Asignar fecha límite de recolección
# =============================================================================

PERMISOS_POR_ROL = {
    'ADMIN': {
        'verDashboard': True,
        'verProductos': True,
        'verLotes': True,
        'verRequisiciones': True,
        'verDonaciones': True,
        'verCentros': True,
        'verUsuarios': True,
        'verReportes': True,
        'verTrazabilidad': True,
        'verAuditoria': True,
        'verNotificaciones': True,
        'verPerfil': True,
        'verMovimientos': True,
        'configurarTema': True,
        'crearRequisicion': True,
        'editarRequisicion': True,
        'eliminarRequisicion': True,
        'enviarRequisicion': True,
        'autorizarRequisicion': True,
        'rechazarRequisicion': True,
        'surtirRequisicion': True,
        'cancelarRequisicion': True,
        'confirmarRecepcion': True,
        'descargarHojaRecoleccion': True,
        # FLUJO V2: Permisos jerárquicos
        'autorizarAdmin': True,
        'autorizarDirector': True,
        'recibirFarmacia': True,
        'autorizarFarmacia': True,
        'asignarFechaRecoleccion': True,
        'devolverRequisicion': True,
        # Permisos de notificaciones
        'gestionarNotificaciones': True,
        # PERMISOS DE DISPENSACIONES - Admin tiene todos
        'verDispensaciones': True,
        'crearDispensacion': True,
        'editarDispensacion': True,
        'dispensar': True,
        'cancelarDispensacion': True,
    },
    'FARMACIA': {
        'verDashboard': True,
        'verProductos': True,
        'verLotes': True,
        'verRequisiciones': True,
        'verDonaciones': True,  # ISS-FIX: Farmacia SÍ puede ver/gestionar donaciones
        'verCentros': True,
        'verUsuarios': False,  # ISS-FIX: Farmacia NO gestiona usuarios
        'verReportes': True,
        'verTrazabilidad': True,
        'verAuditoria': False,
        'verNotificaciones': True,
        'verPerfil': True,
        'verMovimientos': True,
        'configurarTema': False,  # ISS-FIX: Solo admin puede personalizar tema
        'crearRequisicion': False,
        'editarRequisicion': False,
        'eliminarRequisicion': False,
        'enviarRequisicion': False,
        'autorizarRequisicion': True,
        'rechazarRequisicion': True,
        'surtirRequisicion': True,
        'cancelarRequisicion': True,
        'confirmarRecepcion': False,
        'descargarHojaRecoleccion': True,
        # FLUJO V2: Permisos de farmacia central
        'autorizarAdmin': False,
        'autorizarDirector': False,
        'recibirFarmacia': True,
        'autorizarFarmacia': True,
        'asignarFechaRecoleccion': True,
        'devolverRequisicion': True,
        # Permisos de notificaciones
        'gestionarNotificaciones': True,
        # PERMISOS DE DISPENSACIONES - Farmacia solo AUDITA (ver)
        'verDispensaciones': True,
        'crearDispensacion': False,
        'editarDispensacion': False,
        'dispensar': False,
        'cancelarDispensacion': False,
    },
    # FLUJO V2: Rol de Médico del Centro (crea requisiciones)
    'MEDICO': {
        'verDashboard': True,
        'verProductos': True,
        'verLotes': False,
        'verRequisiciones': True,
        'verDonaciones': False,
        'verCentros': False,
        'verUsuarios': False,
        'verReportes': False,
        'verTrazabilidad': False,
        'verAuditoria': False,
        'verNotificaciones': True,
        'verPerfil': True,
        'verMovimientos': True,  # ISS-FIX: Médico PUEDE ver movimientos de su centro (salidas/consumos)
        'configurarTema': False,
        'crearRequisicion': True,
        'editarRequisicion': True,
        'eliminarRequisicion': True,
        'enviarRequisicion': True,
        'autorizarRequisicion': False,
        'rechazarRequisicion': False,
        'surtirRequisicion': False,
        'cancelarRequisicion': True,
        'confirmarRecepcion': False,  # ELIMINAR: Automático al surtir
        'descargarHojaRecoleccion': True,
        # FLUJO V2: Solo puede crear y enviar
        'autorizarAdmin': False,
        'autorizarDirector': False,
        'recibirFarmacia': False,
        'autorizarFarmacia': False,
        'asignarFechaRecoleccion': False,
        'devolverRequisicion': False,
        # Permisos de notificaciones
        'gestionarNotificaciones': False,
        # PERMISOS DE DISPENSACIONES - Médico es el operador principal
        'verDispensaciones': True,
        'crearDispensacion': True,
        'editarDispensacion': True,
        'dispensar': True,
        'cancelarDispensacion': True,
    },
    # FLUJO V2: Rol de Administrador del Centro (primera autorización)
    'ADMINISTRADOR_CENTRO': {
        'verDashboard': True,
        'verProductos': True,
        'verLotes': False,
        'verRequisiciones': True,
        'verDonaciones': False,
        'verCentros': False,
        'verUsuarios': False,
        'verReportes': False,  # Centro NO ve reportes
        'verTrazabilidad': False,  # Centro NO ve trazabilidad
        'verAuditoria': False,
        'verNotificaciones': True,
        'verPerfil': True,
        'verMovimientos': True,  # ISS-FIX: Admin Centro puede VER movimientos (solo lectura)
        'configurarTema': False,
        'crearRequisicion': False,
        'editarRequisicion': False,
        'eliminarRequisicion': False,
        'enviarRequisicion': False,
        'autorizarRequisicion': False,
        'rechazarRequisicion': True,
        'surtirRequisicion': False,
        'cancelarRequisicion': False,
        'confirmarRecepcion': False,  # ELIMINAR: Automático al surtir
        'descargarHojaRecoleccion': True,
        # FLUJO V2: Puede autorizar como administrador
        'autorizarAdmin': True,
        'autorizarDirector': False,
        'recibirFarmacia': False,
        'autorizarFarmacia': False,
        'asignarFechaRecoleccion': False,
        'devolverRequisicion': True,
        # Permisos de notificaciones
        'gestionarNotificaciones': False,
        # PERMISOS DE DISPENSACIONES - Admin Centro solo VE (auditoría)
        'verDispensaciones': True,
        'crearDispensacion': False,
        'editarDispensacion': False,
        'dispensar': False,
        'cancelarDispensacion': False,
    },
    # FLUJO V2: Rol de Director del Centro (segunda autorización)
    'DIRECTOR_CENTRO': {
        'verDashboard': True,
        'verProductos': True,
        'verLotes': False,
        'verRequisiciones': True,
        'verDonaciones': False,
        'verCentros': False,
        'verUsuarios': False,
        'verReportes': False,  # Centro NO ve reportes
        'verTrazabilidad': False,  # Centro NO ve trazabilidad
        'verAuditoria': False,
        'verNotificaciones': True,
        'verPerfil': True,
        'verMovimientos': True,  # ISS-FIX: Director puede VER movimientos (solo lectura)
        'configurarTema': False,
        'crearRequisicion': False,
        'editarRequisicion': False,
        'eliminarRequisicion': False,
        'enviarRequisicion': False,
        'autorizarRequisicion': False,
        'rechazarRequisicion': True,
        'surtirRequisicion': False,
        'cancelarRequisicion': False,
        'confirmarRecepcion': False,  # ELIMINAR: Automático al surtir
        'descargarHojaRecoleccion': True,
        # FLUJO V2: Puede autorizar como director
        'autorizarAdmin': False,
        'autorizarDirector': True,
        'recibirFarmacia': False,
        'autorizarFarmacia': False,
        'asignarFechaRecoleccion': False,
        'devolverRequisicion': True,
        # Permisos de notificaciones
        'gestionarNotificaciones': False,
        # PERMISOS DE DISPENSACIONES - Director solo VE (auditoría)
        'verDispensaciones': True,
        'crearDispensacion': False,
        'editarDispensacion': False,
        'dispensar': False,
        'cancelarDispensacion': False,
    },
    'CENTRO': {
        'verDashboard': True,
        'verProductos': True,
        'verLotes': True,
        'verRequisiciones': True,
        'verDonaciones': False,
        'verCentros': False,
        'verUsuarios': False,
        'verReportes': False,  # Centro NO ve reportes
        'verTrazabilidad': False,  # Centro NO ve trazabilidad
        'verAuditoria': False,
        'verNotificaciones': True,
        'verPerfil': True,
        'verMovimientos': True,
        'configurarTema': False,
        'crearRequisicion': True,
        'editarRequisicion': True,
        'eliminarRequisicion': True,
        'enviarRequisicion': True,
        'autorizarRequisicion': False,
        'rechazarRequisicion': False,
        'surtirRequisicion': False,
        'cancelarRequisicion': True,
        'confirmarRecepcion': False,  # ELIMINAR: Automático al surtir
        'descargarHojaRecoleccion': True,
        # FLUJO V2
        'autorizarAdmin': False,
        'autorizarDirector': False,
        'recibirFarmacia': False,
        'autorizarFarmacia': False,
        'asignarFechaRecoleccion': False,
        'devolverRequisicion': False,
        # Permisos de notificaciones
        'gestionarNotificaciones': False,
        # PERMISOS DE DISPENSACIONES - Centro genérico solo VE (auditoría)
        'verDispensaciones': True,
        'crearDispensacion': False,
        'editarDispensacion': False,
        'dispensar': False,
        'cancelarDispensacion': False,
    },
    'VISTA': {
        'verDashboard': True,
        'verProductos': True,
        'verLotes': True,
        'verRequisiciones': True,
        'verDonaciones': True,
        'verCentros': True,
        'verUsuarios': True,
        'verReportes': False,  # Solo admin/farmacia pueden ver reportes
        'verTrazabilidad': False,  # Solo admin/farmacia pueden ver trazabilidad
        'verAuditoria': False,
        'verNotificaciones': True,
        'verPerfil': True,
        'verMovimientos': True,
        'configurarTema': False,
        'crearRequisicion': False,
        'editarRequisicion': False,
        'eliminarRequisicion': False,
        'enviarRequisicion': False,
        'autorizarRequisicion': False,
        'rechazarRequisicion': False,
        'surtirRequisicion': False,
        'cancelarRequisicion': False,
        'confirmarRecepcion': False,
        'descargarHojaRecoleccion': True,
        # FLUJO V2
        'autorizarAdmin': False,
        'autorizarDirector': False,
        'recibirFarmacia': False,
        'autorizarFarmacia': False,
        'asignarFechaRecoleccion': False,
        'devolverRequisicion': False,
        # Permisos de notificaciones
        'gestionarNotificaciones': False,
        # PERMISOS DE DISPENSACIONES - Vista NO puede ver (datos sensibles)
        'verDispensaciones': False,
        'crearDispensacion': False,
        'editarDispensacion': False,
        'dispensar': False,
        'cancelarDispensacion': False,
    },
    'SIN_ROL': {
        'verDashboard': False,
        'verProductos': False,
        'verLotes': False,
        'verRequisiciones': False,
        'verDonaciones': False,
        'verCentros': False,
        'verUsuarios': False,
        'verReportes': False,
        'verTrazabilidad': False,
        'verAuditoria': False,
        'verNotificaciones': False,
        'verPerfil': False,
        'verMovimientos': False,
        'configurarTema': False,
        'crearRequisicion': False,
        'editarRequisicion': False,
        'eliminarRequisicion': False,
        'enviarRequisicion': False,
        'autorizarRequisicion': False,
        'rechazarRequisicion': False,
        'surtirRequisicion': False,
        'cancelarRequisicion': False,
        'confirmarRecepcion': False,
        'descargarHojaRecoleccion': False,
        # FLUJO V2
        'autorizarAdmin': False,
        'autorizarDirector': False,
        'recibirFarmacia': False,
        'autorizarFarmacia': False,
        'asignarFechaRecoleccion': False,
        'devolverRequisicion': False,
        # Permisos de notificaciones
        'gestionarNotificaciones': False,
        # PERMISOS DE DISPENSACIONES - Sin rol no puede hacer nada
        'verDispensaciones': False,
        'crearDispensacion': False,
        'editarDispensacion': False,
        'dispensar': False,
        'cancelarDispensacion': False,
    },
}


def _infer_rol_from_user(user):
    """
    ISS-PERMS FIX: Infiere el rol del usuario cuando el campo rol está vacío.
    ISS-DIRECTOR FIX: Ahora infiere roles específicos basándose en permisos.
    
    Orden de inferencia:
    1. Si is_superuser -> admin_sistema
    2. Si is_staff -> farmacia
    3. Si tiene perm_autorizar_director=True -> director_centro
    4. Si tiene perm_autorizar_admin=True -> administrador_centro
    5. Si tiene perm_crear_requisicion=True -> medico
    6. Si tiene centro asignado -> centro
    7. Default -> vista (solo lectura, más seguro)
    """
    if not user:
        return ''
    
    # Inferir basándose en otros campos
    if getattr(user, 'is_superuser', False):
        return 'admin_sistema'
    
    if getattr(user, 'is_staff', False):
        return 'farmacia'  # Staff sin superuser = farmacia
    
    # ISS-DIRECTOR FIX: Inferir rol específico por permisos personalizados
    # Verificar permisos del flujo para roles de centro específicos
    if getattr(user, 'perm_autorizar_director', None) is True:
        return 'director_centro'
    
    if getattr(user, 'perm_autorizar_admin', None) is True:
        return 'administrador_centro'
    
    if getattr(user, 'perm_crear_requisicion', None) is True:
        # Usuario con permiso de crear requisiciones = médico
        centro = getattr(user, 'centro', None) or getattr(user, 'centro_id', None)
        if centro:
            return 'medico'
    
    # Si tiene centro asignado sin permisos específicos, es usuario de centro genérico
    centro = getattr(user, 'centro', None) or getattr(user, 'centro_id', None)
    if centro:
        return 'centro'
    
    # Default: usuario vista (más restrictivo, más seguro)
    return 'vista'


def _resolve_rol(user):
    """Resuelve el rol del usuario al formato normalizado para permisos.
    
    FLUJO V2: Incluye roles jerárquicos del centro.
    ISS-PERMS FIX: Ahora infiere rol si el campo está vacío.
    """
    if not user:
        return 'SIN_ROL'
    if user.is_superuser:
        return 'ADMIN'
    
    # Obtener rol del campo, o inferir si está vacío
    normalized = (user.rol or '').lower().strip()
    
    # Si no hay rol en el campo, inferirlo
    if not normalized or normalized in ['null', 'none', '']:
        normalized = _infer_rol_from_user(user)
        logger.info(f"_resolve_rol: Rol inferido para {getattr(user, 'username', 'unknown')}: {normalized}")
    
    # Admin del sistema
    if normalized in ['admin', 'admin_sistema', 'superusuario']:
        return 'ADMIN'
    # Personal de Farmacia Central
    if normalized in ['farmacia', 'admin_farmacia']:
        return 'FARMACIA'
    # FLUJO V2: Roles específicos del centro
    if normalized == 'medico':
        return 'MEDICO'
    if normalized == 'administrador_centro':
        return 'ADMINISTRADOR_CENTRO'
    if normalized == 'director_centro':
        return 'DIRECTOR_CENTRO'
    # Usuario genérico de centro
    if normalized in ['centro', 'usuario_normal', 'solicitante', 'usuario_centro']:
        return 'CENTRO'
    # Solo vista
    if normalized in ['vista', 'usuario_vista']:
        return 'VISTA'
    
    # Fallback final basado en otros atributos
    if getattr(user, 'centro', None) or getattr(user, 'centro_id', None):
        logger.info(f"_resolve_rol: Usuario {getattr(user, 'username', 'unknown')} tiene centro, asignando CENTRO")
        return 'CENTRO'
    
    return 'VISTA'  # ISS-PERMS FIX: Default a VISTA en lugar de SIN_ROL


def build_perm_map(user):
    """Construye el mapa de permisos para el usuario.
    
    FLUJO V2: Incluye permisos granulares del flujo jerárquico.
    """
    rol = _resolve_rol(user)
    base = PERMISOS_POR_ROL.get(rol, PERMISOS_POR_ROL['SIN_ROL']).copy()
    if user and user.is_superuser:
        for key in base.keys():
            base[key] = True
    if user:
        # Mapeo de campos de BD a claves de permisos del frontend
        perm_fields = {
            'perm_dashboard': 'verDashboard',
            'perm_productos': 'verProductos',
            'perm_lotes': 'verLotes',
            'perm_requisiciones': 'verRequisiciones',
            'perm_centros': 'verCentros',
            'perm_usuarios': 'verUsuarios',
            'perm_reportes': 'verReportes',
            'perm_trazabilidad': 'verTrazabilidad',
            'perm_auditoria': 'verAuditoria',
            'perm_notificaciones': 'verNotificaciones',
            'perm_movimientos': 'verMovimientos',
            'perm_donaciones': 'verDonaciones',
            # FLUJO V2: Permisos granulares del flujo
            'perm_crear_requisicion': 'crearRequisicion',
            'perm_autorizar_admin': 'autorizarAdmin',
            'perm_autorizar_director': 'autorizarDirector',
            'perm_recibir_farmacia': 'recibirFarmacia',
            'perm_autorizar_farmacia': 'autorizarFarmacia',
            'perm_surtir': 'surtirRequisicion',
            'perm_confirmar_entrega': 'confirmarRecepcion',
            # DISPENSACIONES: Permiso personalizado
            'perm_dispensaciones': 'verDispensaciones',
        }
        for field, perm_key in perm_fields.items():
            custom_value = getattr(user, field, None)
            if custom_value is not None:
                base[perm_key] = custom_value
    return base


# =============================================================================
# USER SERIALIZER
# =============================================================================

class CentroNestedSerializer(serializers.ModelSerializer):
    """Serializer anidado para mostrar centro en usuarios"""
    class Meta:
        model = Centro
        fields = ['id', 'nombre']


class UserSerializer(serializers.ModelSerializer):
    # Para lectura: devuelve objeto {id, nombre}
    centro = CentroNestedSerializer(read_only=True)
    # Para escritura: acepta ID numérico y lo guarda directamente en centro_id
    centro_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    centro_nombre = serializers.CharField(source='centro.nombre', read_only=True, allow_null=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    permisos = serializers.SerializerMethodField()
    # ISS-PERMS FIX: Rol efectivo (inferido si el campo está vacío)
    rol_efectivo = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'rol', 'rol_efectivo', 'centro', 'centro_id', 'centro_nombre', 'password', 
            'adscripcion', 'permisos', 'is_active', 'is_superuser',
            'date_joined', 'last_login',
            # Permisos personalizados por módulo
            'perm_dashboard', 'perm_productos', 'perm_lotes',
            'perm_requisiciones', 'perm_centros', 'perm_usuarios',
            'perm_reportes', 'perm_trazabilidad', 'perm_auditoria',
            'perm_notificaciones', 'perm_movimientos', 'perm_donaciones',
            # FLUJO V2: Permisos granulares del flujo de requisiciones
            'perm_crear_requisicion', 'perm_autorizar_admin',
            'perm_autorizar_director', 'perm_recibir_farmacia',
            'perm_autorizar_farmacia', 'perm_surtir', 'perm_confirmar_entrega'
        ]
        read_only_fields = ['date_joined', 'last_login']
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
            'email': {'required': False, 'allow_blank': True},
            'first_name': {'required': False, 'allow_blank': True},
            'last_name': {'required': False, 'allow_blank': True},
            'adscripcion': {'required': False, 'allow_blank': True},
        }

    def get_permisos(self, obj):
        return build_perm_map(obj)
    
    def get_rol_efectivo(self, obj):
        """ISS-PERMS FIX: Devuelve el rol real usado para permisos (inferido si campo vacío)"""
        return _resolve_rol(obj)
    
    def validate_username(self, value):
        if not value or len(value) < 3:
            raise serializers.ValidationError('El username debe tener al menos 3 caracteres')
        instance_id = self.instance.id if self.instance else None
        if User.objects.filter(username__iexact=value).exclude(id=instance_id).exists():
            raise serializers.ValidationError('El username ya esta en uso')
        return value.lower()
    
    def validate_password(self, value):
        """Valida que la contraseña cumpla los requisitos mínimos"""
        # Si es update, la contraseña es opcional
        if self.instance is not None:
            return value
        
        # Para creación, la contraseña es obligatoria
        if not value or value.strip() == '':
            raise serializers.ValidationError('La contraseña es obligatoria para nuevos usuarios')
        
        if len(value) < 8:
            raise serializers.ValidationError('La contraseña debe tener al menos 8 caracteres')
        
        return value
    
    def validate_centro_id(self, value):
        """Valida que el centro_id exista si se proporciona"""
        if value is not None:
            if not Centro.objects.filter(id=value).exists():
                raise serializers.ValidationError(f'Centro con ID {value} no existe')
        return value
    
    def validate(self, attrs):
        """Validación a nivel de objeto - asegura que la contraseña esté presente al crear"""
        # Si es creación (no hay instance), la contraseña es obligatoria
        if self.instance is None:
            password = attrs.get('password')
            if not password or (isinstance(password, str) and password.strip() == ''):
                raise serializers.ValidationError({
                    'password': 'La contraseña es obligatoria para nuevos usuarios'
                })
        return attrs
    
    def create(self, validated_data):
        from django.db import transaction
        
        password = validated_data.pop('password', None)
        # Extraer centro_id y asignarlo al campo centro
        centro_id = validated_data.pop('centro_id', None)
        
        # ISS-SEC: No loguear validated_data ya que contiene PII (nombre, email, etc.)
        logger.info(f"UserSerializer.create - Creating user with centro_id: {centro_id}")
        logger.info(f"UserSerializer.create - password received: {'YES' if password else 'NO'}")
        
        # ISS-PASSWORD FIX: Usar transacción para asegurar integridad
        with transaction.atomic():
            user = User(**validated_data)
            # Asignar centro directamente usando el ID
            if centro_id is not None:
                user.centro_id = centro_id
            
            if password:
                user.set_password(password)
                logger.info(f"UserSerializer.create - Password set for user {user.username}")
            else:
                user.set_unusable_password()
                logger.warning(f"UserSerializer.create - NO PASSWORD SET for user {user.username} - user won't be able to login!")
            user.save()
            
            # ISS-PASSWORD FIX: Verificar que la contraseña se guardó correctamente
            if password:
                user.refresh_from_db()
                can_auth = user.check_password(password)
                logger.info(f"UserSerializer.create - Password verification after save: {can_auth}")
                if not can_auth:
                    logger.error(f"UserSerializer.create - PASSWORD VERIFICATION FAILED for {user.username}!")
                    # Reintentar el guardado de la contraseña
                    user.set_password(password)
                    user.save(update_fields=['password'])
                    user.refresh_from_db()
                    # Verificar de nuevo
                    if not user.check_password(password):
                        raise serializers.ValidationError(
                            {'password': 'Error crítico: No se pudo guardar la contraseña. Contacte al administrador.'}
                        )
                    logger.info(f"UserSerializer.create - Password fixed on retry for {user.username}")
        
        logger.info(f"UserSerializer.create - User saved: id={user.id}, centro_id={user.centro_id}, is_active={user.is_active}")
        return user
    
    def update(self, instance, validated_data):
        from django.db import transaction
        
        password = validated_data.pop('password', None)
        # Extraer centro_id
        centro_id = validated_data.pop('centro_id', None)
        
        # ISS-SEC: No loguear validated_data ya que contiene PII (nombre, email, etc.)
        logger.info(f"UserSerializer.update - Updating user id={instance.id}, centro_id: {centro_id}")
        
        # ISS-PASSWORD FIX: Usar transacción para asegurar integridad
        with transaction.atomic():
            # Actualizar campos normales
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            
            # Asignar centro_id explícitamente (incluso si es None para quitar asignación)
            if 'centro_id' in self.initial_data:
                instance.centro_id = centro_id
                logger.info(f"UserSerializer.update - Setting centro_id to: {centro_id}")
            
            if password:
                instance.set_password(password)
                logger.info(f"UserSerializer.update - Setting new password for {instance.username}")
            
            instance.save()
            
            # ISS-PASSWORD FIX: Verificar que la contraseña se guardó si se cambió
            if password:
                instance.refresh_from_db()
                can_auth = instance.check_password(password)
                logger.info(f"UserSerializer.update - Password verification: {can_auth}")
                if not can_auth:
                    logger.error(f"UserSerializer.update - PASSWORD VERIFICATION FAILED for {instance.username}!")
                    # Reintentar
                    instance.set_password(password)
                    instance.save(update_fields=['password'])
                    instance.refresh_from_db()
                    if not instance.check_password(password):
                        raise serializers.ValidationError(
                            {'password': 'Error crítico: No se pudo guardar la contraseña. Contacte al administrador.'}
                        )
                    logger.info(f"UserSerializer.update - Password fixed on retry for {instance.username}")
        
        logger.info(f"UserSerializer.update - User saved: id={instance.id}, centro_id={instance.centro_id}")
        return instance


# =============================================================================
# CENTRO SERIALIZER
# =============================================================================

class CentroSerializer(serializers.ModelSerializer):
    total_requisiciones = serializers.SerializerMethodField()
    total_usuarios = serializers.SerializerMethodField()
    
    class Meta:
        model = Centro
        fields = [
            'id', 'nombre', 'direccion', 'telefono', 'email',
            'activo', 'total_requisiciones', 'total_usuarios',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_total_requisiciones(self, obj):
        # PERFORMANCE: Usar anotación del ViewSet si existe, evita N+1 queries
        total_anotado = getattr(obj, 'requisiciones_count', None)
        if total_anotado is not None:
            return total_anotado
        # Fallback: query directa (evitar si es posible)
        from django.db.models import Q
        return Requisicion.objects.filter(
            Q(centro_origen=obj) | Q(centro_destino=obj)
        ).count()
    
    def get_total_usuarios(self, obj):
        # PERFORMANCE: Usar anotación del ViewSet si existe, evita N+1 queries
        total_anotado = getattr(obj, 'usuarios_count', None)
        if total_anotado is not None:
            return total_anotado
        # Fallback: query directa
        return obj.usuarios.filter(is_active=True).count()


# =============================================================================
# PRODUCTO SERIALIZER
# =============================================================================

class ProductoSerializer(serializers.ModelSerializer):
    stock_actual = serializers.SerializerMethodField()
    lotes_activos = serializers.SerializerMethodField()
    marca = serializers.SerializerMethodField()
    # ISS-FIX: Unidad base normalizada para filtros del frontend
    unidad_base = serializers.SerializerMethodField()
    # ISS-TRAZ: Indicadores para bloquear edición de campos críticos
    tiene_lotes = serializers.SerializerMethodField()
    tiene_movimientos = serializers.SerializerMethodField()
    # ISS-PROD-VAR: Campos de variante por presentación
    codigo_base = serializers.SerializerMethodField()
    es_variante_flag = serializers.SerializerMethodField()
    variantes_asociadas = serializers.SerializerMethodField()
    # AUDITORÍA: quién registró y quién modificó última vez
    creado_por_nombre = serializers.SerializerMethodField()
    modificado_por_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = [
            'id', 'clave', 'nombre', 'nombre_comercial', 'descripcion', 'unidad_medida',
            'unidad_base',  # ISS-FIX: Campo agregado para filtros
            'categoria', 'sustancia_activa', 'presentacion', 'concentracion',
            'via_administracion', 'requiere_receta', 'es_controlado',
            'stock_minimo', 'stock_actual', 'activo', 'imagen',
            'lotes_activos', 'marca', 'tiene_lotes', 'tiene_movimientos',
            # ISS-PROD-VAR
            'codigo_base', 'es_variante_flag', 'variantes_asociadas',
            'created_at', 'updated_at',
            # AUDITORÍA
            'creado_por_nombre', 'modificado_por_nombre',
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'stock_actual', 'marca', 'unidad_base',
            'tiene_lotes', 'tiene_movimientos',
            'codigo_base', 'es_variante_flag', 'variantes_asociadas',
            'creado_por_nombre', 'modificado_por_nombre',
        ]
        extra_kwargs = {
            'clave': {'required': True},
            'nombre': {'required': True},
            'presentacion': {'required': True},
            'descripcion': {'required': False, 'allow_null': True, 'allow_blank': True},
            'nombre_comercial': {'required': False, 'allow_null': True, 'allow_blank': True},
        }
    
    def get_unidad_base(self, obj):
        """
        ISS-FIX: Normaliza la unidad de medida compuesta a su forma base.
        Ejemplo: "CAJA CON 20 TABLETAS" -> "CAJA"
        """
        from core.constants import normalizar_unidad_medida
        return normalizar_unidad_medida(obj.unidad_medida)

    def get_creado_por_nombre(self, obj):
        """Lee nombre del creador desde anotación SQL (_creado_por_nombre) inyectada por el ViewSet."""
        return getattr(obj, '_creado_por_nombre', None) or None

    def get_modificado_por_nombre(self, obj):
        """Lee nombre del último modificador desde anotación SQL (_modificado_por_nombre) inyectada por el ViewSet."""
        return getattr(obj, '_modificado_por_nombre', None) or None

    def get_stock_actual(self, obj):
        # Priorizar stock_calculado (anotación) sobre el campo
        return getattr(obj, 'stock_calculado', None) or obj.stock_actual or 0
    
    def get_lotes_activos(self, obj):
        """
        TRAZABILIDAD: Cuenta lotes ÚNICOS (consolidados por numero_lote).
        Un lote físico distribuido en múltiples centros cuenta como 1.
        """
        # PERFORMANCE: Usar anotación del ViewSet si existe
        lotes_unicos_count = getattr(obj, 'lotes_unicos_count', None)
        if lotes_unicos_count is not None:
            return lotes_unicos_count
        
        # ISS-FIX: Obtener centro del request para filtrar correctamente
        request = self.context.get('request')
        user_centro = None
        if request and hasattr(request, 'user'):
            user = request.user
            if not user.is_superuser:
                rol = getattr(user, 'rol', '').lower()
                if rol not in ('admin', 'farmacia', 'administrador', 'usuario_farmacia', 'admin_farmacia', 'vista'):
                    user_centro = getattr(user, 'centro', None)
        
        # Fallback: usar prefetch_related si disponible
        if hasattr(obj, '_prefetched_objects_cache') and 'lotes' in obj._prefetched_objects_cache:
            lotes_filtrados = [l for l in obj.lotes.all() if l.activo and l.cantidad_actual > 0]
            if user_centro:
                lotes_filtrados = [l for l in lotes_filtrados if l.centro_id == user_centro.id]
            # TRAZABILIDAD: Contar lotes únicos por numero_lote
            numeros_unicos = set(l.numero_lote for l in lotes_filtrados)
            return len(numeros_unicos)
        
        # Último recurso: query directa con filtro de centro
        filtro = {'activo': True, 'cantidad_actual__gt': 0}
        if user_centro:
            filtro['centro'] = user_centro
        # TRAZABILIDAD: Contar valores distintos de numero_lote
        return obj.lotes.filter(**filtro).values('numero_lote').distinct().count()
    
    def get_marca(self, obj):
        """
        PERFORMANCE: Obtiene marca del lote principal (mayor cantidad).
        Usa anotación del ViewSet o prefetch_related para evitar N+1 queries.
        """
        # Priorizar anotación del ViewSet
        marca_anotada = getattr(obj, 'marca_principal', None)
        if marca_anotada:
            return marca_anotada
        # Usar prefetch_related si disponible
        if hasattr(obj, '_prefetched_objects_cache') and 'lotes' in obj._prefetched_objects_cache:
            lotes_ordenados = sorted(
                [l for l in obj.lotes.all() if l.activo and l.cantidad_actual > 0],
                key=lambda x: x.cantidad_actual,
                reverse=True
            )
            return lotes_ordenados[0].marca if lotes_ordenados and lotes_ordenados[0].marca else None
        # Último recurso: query directa
        lote = obj.lotes.filter(activo=True, cantidad_actual__gt=0).order_by('-cantidad_actual').first()
        return lote.marca if lote and lote.marca else None
    
    def validate_clave(self, value):
        """Clave es requerida, única, entre 1 y 50 caracteres."""
        if not value or value.strip() == '':
            raise serializers.ValidationError('La clave es requerida')
        clave_limpia = value.strip().upper()
        if len(clave_limpia) > 50:
            raise serializers.ValidationError('La clave no puede exceder 50 caracteres')
        return clave_limpia
    
    def validate_nombre(self, value):
        """Nombre es requerido y debe tener al menos 3 caracteres."""
        if not value or value.strip() == '':
            raise serializers.ValidationError('El nombre es requerido')
        nombre_limpio = value.strip()
        if len(nombre_limpio) < 3:
            raise serializers.ValidationError('El nombre debe tener al menos 3 caracteres')
        if len(nombre_limpio) > 500:
            raise serializers.ValidationError('El nombre no puede exceder 500 caracteres')
        return nombre_limpio
    
    def validate_unidad_medida(self, value):
        """
        ISS-FIX: Permite texto libre en unidad_medida para mejor manejo de farmacia.
        
        Ejemplos válidos: "CAJA", "CAJA CON 7 OVULOS", "GOTERO CON 15 MILILITROS"
        La BD acepta character varying sin restricción de choices.
        """
        if not value:
            return 'PIEZA'  # Default
        
        # Limpiar y convertir a mayúsculas
        valor_limpio = str(value).strip().upper()
        
        # Validar longitud máxima (la BD permite hasta ~255 caracteres)
        if len(valor_limpio) > 100:
            raise serializers.ValidationError('La unidad de medida no puede exceder 100 caracteres')
        
        return valor_limpio
    
    def validate_categoria(self, value):
        """Normaliza y valida categoría."""
        from core.constants import CATEGORIAS_VALIDAS
        if not value:
            return 'medicamento'  # Default
        valor_normalizado = value.strip().lower()
        if valor_normalizado not in CATEGORIAS_VALIDAS:
            raise serializers.ValidationError(
                f'Categoría no válida: {value}. Opciones: {", ".join(CATEGORIAS_VALIDAS)}'
            )
        return valor_normalizado
    
    def validate_presentacion(self, value):
        """Presentación es requerida y debe tener contenido válido."""
        if not value or value.strip() == '':
            raise serializers.ValidationError('La presentación es requerida')
        presentacion_limpia = value.strip().upper()
        if len(presentacion_limpia) < 2:
            raise serializers.ValidationError('La presentación debe tener al menos 2 caracteres')
        if len(presentacion_limpia) > 200:
            raise serializers.ValidationError('La presentación no puede exceder 200 caracteres')
        return presentacion_limpia
    
    def validate_stock_minimo(self, value):
        """Stock mínimo debe ser un número no negativo."""
        if value is None:
            return 0  # Default
        if value < 0:
            raise serializers.ValidationError('El stock mínimo no puede ser negativo')
        return value
    
    def validate(self, attrs):
        return attrs
    
    def get_tiene_lotes(self, obj):
        """
        ISS-TRAZ: Indica si el producto tiene lotes asociados.
        Si tiene lotes, algunos campos críticos no son editables.
        """
        return obj.lotes.exists()
    
    def get_tiene_movimientos(self, obj):
        """
        ISS-TRAZ: Indica si el producto tiene movimientos registrados.
        Si tiene movimientos, los campos críticos están completamente bloqueados.
        """
        from .models import Movimiento
        return Movimiento.objects.filter(producto=obj).exists()

    # ------------------------------------------------------------------
    # ISS-PROD-VAR: Campos de variante por presentación
    # ------------------------------------------------------------------

    def get_codigo_base(self, obj):
        """Código base sin sufijo de variante (ej. '663.2' → '663', '663' → '663')."""
        from core.utils.producto_variante import extraer_codigo_base
        return extraer_codigo_base(obj.clave)

    def get_es_variante_flag(self, obj):
        """True si la clave tiene sufijo numérico de variante (ej. '663.2')."""
        from core.utils.producto_variante import es_variante
        return es_variante(obj.clave)

    def get_variantes_asociadas(self, obj):
        """
        Lista de claves hermanas (mismo código base).
        Incluye al propio producto y sus variantes.
        Devuelve lista ligera: [{'clave': '663', 'presentacion': '...'}, ...]
        """
        try:
            from core.utils.producto_variante import extraer_codigo_base, _claves_del_mismo_base
            base = extraer_codigo_base(obj.clave)
            hermanas = _claves_del_mismo_base(base).only('clave', 'presentacion')
            return [
                {'clave': p.clave, 'presentacion': p.presentacion or ''}
                for p in hermanas.order_by('clave')
            ]
        except Exception:
            return []

    def update(self, instance, validated_data):
        """
        ISS-TRAZ: Proteger campos críticos en productos con lotes/movimientos.
        
        Campos protegidos si tiene LOTES (campos obligatorios):
        - clave: Identificador único, usado en reportes y trazabilidad
        - nombre: Afecta reportes históricos
        - presentacion: Afecta trazabilidad de lotes
        - unidad_medida: Afecta cálculos de stock en reportes
        - categoria: Afecta clasificación en reportes
        
        Campos SIEMPRE editables (informativos/opcionales):
        - nombre_comercial, descripcion, stock_minimo, activo, imagen
        - sustancia_activa, concentracion, via_administracion
        - requiere_receta, es_controlado
        """
        from .models import Movimiento
        
        tiene_lotes = instance.lotes.exists()
        
        errores = {}
        
        # Si tiene lotes, los campos obligatorios NO pueden cambiar
        if tiene_lotes:
            campos_protegidos = {
                'clave': 'clave',
                'nombre': 'nombre',
                'presentacion': 'presentación',
                'unidad_medida': 'unidad de medida',
                'categoria': 'categoría',
            }
            
            for campo, nombre in campos_protegidos.items():
                if campo in validated_data:
                    valor_nuevo = validated_data[campo]
                    valor_actual = getattr(instance, campo)
                    
                    # Normalizar para comparación (manejar None y strings)
                    if valor_nuevo is None:
                        valor_nuevo = ''
                    if valor_actual is None:
                        valor_actual = ''
                    
                    # Comparar valores normalizados
                    if str(valor_nuevo).strip().upper() != str(valor_actual).strip().upper():
                        errores[campo] = f'No se puede modificar {nombre} de un producto con lotes asociados'
        
        if errores:
            raise serializers.ValidationError(errores)
        
        # Remover campos protegidos del validated_data para evitar cambios accidentales
        if tiene_lotes:
            for campo in ['clave', 'nombre', 'presentacion', 'unidad_medida', 'categoria']:
                validated_data.pop(campo, None)
        
        return super().update(instance, validated_data)


# =============================================================================
# LOTE PARCIALIDAD SERIALIZER
# =============================================================================

class LoteParcialidadSerializer(serializers.ModelSerializer):
    """
    Serializer para el historial de entregas parciales de un lote.
    
    Permite registrar cada entrega parcial con:
    - Fecha de entrega
    - Cantidad recibida
    - Datos opcionales de factura/remisión/proveedor
    - Campos de auditoría para sobre-entregas
    """
    usuario_nombre = serializers.CharField(source='usuario.get_full_name', read_only=True)
    lote_numero = serializers.CharField(source='lote.numero_lote', read_only=True)
    
    class Meta:
        from .models import LoteParcialidad
        model = LoteParcialidad
        fields = [
            'id', 'lote', 'lote_numero', 'fecha_entrega', 'cantidad',
            'numero_factura', 'numero_remision', 'proveedor', 'notas',
            'es_sobreentrega', 'motivo_override',
            'usuario', 'usuario_nombre', 'created_at'
        ]
        read_only_fields = ['id', 'usuario', 'usuario_nombre', 'created_at', 'lote_numero', 'es_sobreentrega']
    
    def validate_cantidad(self, value):
        if value <= 0:
            raise serializers.ValidationError('La cantidad debe ser mayor a cero.')
        return value
    
    def validate_fecha_entrega(self, value):
        from django.utils import timezone
        hoy = timezone.now().date()
        if value > hoy:
            raise serializers.ValidationError('La fecha de entrega no puede ser futura.')
        return value
    
    def create(self, validated_data):
        # Asignar usuario automáticamente
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['usuario'] = request.user
        return super().create(validated_data)


# =============================================================================
# LOTE SERIALIZER
# =============================================================================

class LoteSerializer(serializers.ModelSerializer):
    # ISS-DB: Campos alineados con schema de productos (clave, nombre)
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_clave = serializers.CharField(source='producto.clave', read_only=True)
    # AUDITORÍA: quién registró y quién modificó última vez
    creado_por_nombre = serializers.SerializerMethodField()
    modificado_por_nombre = serializers.SerializerMethodField()
    producto_descripcion = serializers.CharField(source='producto.nombre', read_only=True)  # Alias para compatibilidad
    producto_info = serializers.SerializerMethodField()  # Info adicional del producto (presentación, unidad)
    # centro=null → lote de Farmacia Central (FK nullable en BD)
    # Declarado explícitamente para garantizar required=False, allow_null=True sin depender de extra_kwargs
    centro = serializers.PrimaryKeyRelatedField(
        queryset=Centro.objects.all(),
        required=False,
        allow_null=True,
    )
    centro_nombre = serializers.CharField(source='centro.nombre', read_only=True, allow_null=True)
    dias_para_caducar = serializers.SerializerMethodField()
    estado = serializers.SerializerMethodField()
    alerta_caducidad = serializers.SerializerMethodField()  # Para compatibilidad con frontend
    porcentaje_consumido = serializers.SerializerMethodField()  # Para tabla de lotes
    # precio_unitario tiene precision 12, default 0 en BD
    precio_unitario = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    # Campo 'precio_compra' para compatibilidad con frontend (alias de precio_unitario)
    precio_compra = serializers.DecimalField(source='precio_unitario', max_digits=12, decimal_places=2, required=False, allow_null=True)
    # ISS-DB-004: fecha_caducidad es NOT NULL en BD, hacerlo explícitamente obligatorio
    fecha_caducidad = serializers.DateField(required=True, help_text='Obligatorio. Usar 2099-12-31 para insumos sin caducidad.')
    # Documentos asociados al lote
    documentos = serializers.SerializerMethodField()
    tiene_documentos = serializers.SerializerMethodField()
    # ISS-TRAZ: Indicar si el lote tiene movimientos (para bloquear edición de campos críticos)
    tiene_movimientos = serializers.SerializerMethodField()
    # ISS-INV-001: Campo cantidad_contrato y cálculo de pendiente
    cantidad_contrato = serializers.IntegerField(required=False, allow_null=True, help_text='Cantidad según contrato para este lote')
    # ISS-INV-003: Contrato global por clave de producto
    cantidad_contrato_global = serializers.IntegerField(required=False, allow_null=True, help_text='Cantidad total del contrato global por clave de producto')
    cantidad_pendiente = serializers.SerializerMethodField(help_text='Cantidad pendiente por recibir del lote (contrato_lote - surtido)')
    cantidad_pendiente_global = serializers.SerializerMethodField(help_text='Cantidad pendiente global por clave (contrato_global - sum recibidos)')
    cantidad_recibido_global = serializers.SerializerMethodField(help_text='Total recibido del contrato global (usa cantidad_inicial, NO cantidad_actual)')
    total_inventario_global = serializers.SerializerMethodField(help_text='Total en inventario actual de todos los lotes del contrato (suma cantidad_actual)')
    # Campos de parcialidades (historial de entregas)
    parcialidades = serializers.SerializerMethodField(help_text='Historial de entregas parciales del lote')
    total_parcialidades = serializers.SerializerMethodField(help_text='Suma de cantidades de todas las parcialidades')
    num_entregas = serializers.SerializerMethodField(help_text='Número de entregas parciales registradas')
    ultima_fecha_entrega = serializers.SerializerMethodField(help_text='Fecha de la última entrega registrada')
    
    class Meta:
        model = Lote
        fields = [
            'id', 'producto', 'producto_nombre', 'producto_clave', 'producto_descripcion',
            'producto_info',  # Información adicional del producto
            'centro', 'centro_nombre',
            'numero_lote', 'fecha_caducidad', 'fecha_fabricacion',
            # ISS-INV-001/003: Campos de cantidades para control de contratos
            'cantidad_contrato',         # Total según contrato para ESTE LOTE (ej: 300)
            'cantidad_contrato_global',  # Total según contrato GLOBAL por clave (ej: 1000)
            'cantidad_inicial',          # Total surtido/recibido en este lote (ej: 84)
            'cantidad_actual',           # Stock disponible (ej: 75)
            'cantidad_pendiente',        # Calculado: contrato_lote - inicial (ej: 216)
            'cantidad_pendiente_global', # Calculado: contrato_global - sum(inicial de todos los lotes del contrato)
            'cantidad_recibido_global',  # Calculado: sum(inicial de todos los lotes del contrato)
            'total_inventario_global',   # Calculado: sum(actual de todos los lotes del contrato) - LO QUE REALMENTE HAY
            'precio_unitario', 'precio_compra',
            'numero_contrato', 'marca', 'ubicacion', 'activo', 'estado',
            'dias_para_caducar', 'alerta_caducidad', 'porcentaje_consumido',
            'documentos', 'tiene_documentos', 'tiene_movimientos',
            # Parcialidades (historial de entregas)
            'parcialidades', 'total_parcialidades', 'num_entregas', 'ultima_fecha_entrega',
            'created_at', 'updated_at',
            # AUDITORÍA
            'creado_por_nombre', 'modificado_por_nombre',
        ]
        read_only_fields = ['created_at', 'updated_at', 'estado', 'documentos', 'tiene_documentos', 'tiene_movimientos', 'cantidad_pendiente', 'cantidad_pendiente_global', 'cantidad_recibido_global', 'total_inventario_global', 'parcialidades', 'total_parcialidades', 'num_entregas', 'ultima_fecha_entrega', 'creado_por_nombre', 'modificado_por_nombre', 'created_by']
        extra_kwargs = {
            'cantidad_inicial': {'required': False},  # Requerido solo en creación (validate_cantidad_inicial)
            'cantidad_contrato': {'required': False, 'allow_null': True},
            'cantidad_contrato_global': {'required': False, 'allow_null': True},
            'numero_contrato': {'required': False, 'allow_null': True, 'allow_blank': True},
            'marca': {'required': False, 'allow_null': True, 'allow_blank': True},
            'ubicacion': {'required': False, 'allow_null': True, 'allow_blank': True},
            # ISS-FIX: fecha_fabricacion (fecha de entrega) explícitamente editable
            'fecha_fabricacion': {'required': False, 'allow_null': True},
            # NOTA: 'centro' se declara explícitamente como campo (no en extra_kwargs)
            # porque DRF prohíbe mezclar declaración explícita + extra_kwargs para el mismo campo.
        }
    
    def get_creado_por_nombre(self, obj):
        """
        Lee nombre del creador desde anotación SQL (_creado_por_nombre) inyectada por LoteViewSet.
        
        El ViewSet ya maneja el fallback de forma eficiente con Coalesce en SQL:
        - Primera opción: usuario desde created_by_id
        - Fallback automático: usuario de la primera parcialidad
        
        Si este campo es None, indica un problema de integridad de datos (lote sin 
        created_by_id Y sin parcialidades). Se loguea para auditoría.
        """
        nombre = getattr(obj, '_creado_por_nombre', None)
        
        # ALERTA: Si es None aquí, hay un problema de integridad de datos
        if not nombre:
            logger.warning(
                f"Lote ID {obj.id} sin creador identificable: "
                f"created_by_id es NULL y no tiene parcialidades con usuario. "
                f"Revisar integridad de datos."
            )
        
        return nombre

    def get_modificado_por_nombre(self, obj):
        """Lee nombre del último modificador desde anotación SQL (_modificado_por_nombre) inyectada por LoteViewSet."""
        return getattr(obj, '_modificado_por_nombre', None) or None

    def get_cantidad_pendiente(self, obj):
        """
        ISS-INV-001: Calcula cantidad pendiente por recibir del contrato POR LOTE.
        Si cantidad_contrato es NULL, retorna NULL (no aplica).
        """
        if obj.cantidad_contrato is None:
            return None
        return max(0, obj.cantidad_contrato - (obj.cantidad_inicial or 0))
    
    def get_cantidad_pendiente_global(self, obj):
        """
        ISS-INV-003: Calcula cantidad pendiente GLOBAL por clave de producto.
        Suma todos los cantidad_inicial de lotes con mismo producto + numero_contrato.
        
        CRÍTICO: Usa cantidad_inicial (recibido), NO cantidad_actual (disponible).
        Las salidas NO afectan el contrato. Ej: Contrato 500, recibido 200, salió 100 → falta 300 (no 400).
        
        Retorna:
        - NULL si cantidad_contrato_global no está definido
        - Positivo si faltan unidades por recibir
        - Negativo si hay exceso (se recibió más de lo contratado)
        - Cero si coincide exactamente
        """
        if obj.cantidad_contrato_global is None or not obj.numero_contrato:
            return None
        
        # Sumar todos los cantidad_inicial de lotes del mismo producto y contrato.
        # Sin activo=True: lotes inactivos también consumen contrato.
        from django.db.models import Sum
        total_recibido = Lote.objects.filter(
            producto=obj.producto,
            numero_contrato__iexact=obj.numero_contrato.strip(),
        ).aggregate(total=Sum('cantidad_inicial'))['total'] or 0

        # Retornar diferencia REAL (puede ser negativo si hay exceso)
        pendiente = obj.cantidad_contrato_global - total_recibido
        return pendiente
    
    def get_cantidad_recibido_global(self, obj):
        """
        ISS-INV-003: Calcula total RECIBIDO del contrato global.
        
        CRÍTICO: Usa cantidad_inicial (recibido), NO cantidad_actual (disponible).
        Así las salidas NO afectan el total recibido del contrato.
        
        Retorna:
        - NULL si no hay contrato global
        - Total de cantidad_inicial sumada de todos los lotes del contrato
        """
        if obj.cantidad_contrato_global is None or not obj.numero_contrato:
            return None
        
        # Sin activo=True: lotes inactivos también consumieron el contrato.
        from django.db.models import Sum
        total_recibido = Lote.objects.filter(
            producto=obj.producto,
            numero_contrato__iexact=obj.numero_contrato.strip(),
        ).aggregate(total=Sum('cantidad_inicial'))['total'] or 0

        return total_recibido
    
    def get_total_inventario_global(self, obj):
        """
        ISS-INV-003: Calcula TOTAL EN INVENTARIO de todos los lotes del contrato.
        
        CRÍTICO: Usa cantidad_actual (disponible ahora), NO cantidad_inicial.
        Esto muestra lo que REALMENTE hay en stock después de todas las salidas.
        
        Retorna:
        - NULL si no hay contrato global
        - Total de cantidad_actual sumada de todos los lotes del contrato
        
        Ejemplo:
        - Contrato: 500
        - Lote 1: inicial=200, actual=100 (salió 100)
        - Lote 2: inicial=150, actual=150
        - Total Inventario: 100 + 150 = 250
        - Pendiente: 500 - 200 (inicial) = 300
        """
        if obj.cantidad_contrato_global is None or not obj.numero_contrato:
            return None
        
        # Para inventario disponible sí filtrar activo=True: lotes inactivos
        # no aportan stock físico aunque hayan consumido contrato.
        from django.db.models import Sum
        total_inventario = Lote.objects.filter(
            producto=obj.producto,
            numero_contrato__iexact=obj.numero_contrato.strip(),
            activo=True
        ).aggregate(total=Sum('cantidad_actual'))['total'] or 0

        return total_inventario
    
    def get_parcialidades(self, obj):
        """
        Devuelve el historial de entregas parciales del lote.
        Solo incluye los últimos 10 registros para no sobrecargar respuestas.
        Usa datos precargados si están disponibles (prefetch_related).
        """
        # Usar datos precargados si existen (evita N+1 queries)
        if hasattr(obj, '_prefetched_objects_cache') and 'parcialidades' in obj._prefetched_objects_cache:
            parcialidades = sorted(obj.parcialidades.all(), key=lambda x: x.fecha_entrega, reverse=True)[:10]
        else:
            from .models import LoteParcialidad
            parcialidades = LoteParcialidad.objects.filter(lote=obj).order_by('-fecha_entrega')[:10]
        return LoteParcialidadSerializer(parcialidades, many=True).data
    
    def get_total_parcialidades(self, obj):
        """Suma de cantidades de todas las parcialidades registradas."""
        # Usar datos precargados si existen (evita N+1 queries)
        if hasattr(obj, '_prefetched_objects_cache') and 'parcialidades' in obj._prefetched_objects_cache:
            return sum(p.cantidad for p in obj.parcialidades.all())
        from django.db.models import Sum
        from .models import LoteParcialidad
        total = LoteParcialidad.objects.filter(lote=obj).aggregate(total=Sum('cantidad'))['total']
        return total or 0
    
    def get_num_entregas(self, obj):
        """Número de entregas parciales registradas para este lote."""
        # Usar datos precargados si existen (evita N+1 queries)
        if hasattr(obj, '_prefetched_objects_cache') and 'parcialidades' in obj._prefetched_objects_cache:
            return len(obj.parcialidades.all())
        from .models import LoteParcialidad
        return LoteParcialidad.objects.filter(lote=obj).count()
    
    def get_ultima_fecha_entrega(self, obj):
        """
        Fecha de la última entrega registrada (o fecha_fabricacion como fallback).
        
        AUTO-SINCRONIZACIÓN: Si el lote no tiene fecha_fabricacion pero tiene
        parcialidades, actualiza automáticamente el lote con la primera fecha.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Usar datos precargados si existen (evita N+1 queries)
        if hasattr(obj, '_prefetched_objects_cache') and 'parcialidades' in obj._prefetched_objects_cache:
            parcialidades = list(obj.parcialidades.all())
            if parcialidades:
                fechas = [p.fecha_entrega for p in parcialidades if p.fecha_entrega]
                if fechas:
                    # AUTO-SYNC: Si lote no tiene fecha pero hay parcialidades
                    if obj.fecha_fabricacion is None:
                        primera_fecha = min(fechas)
                        try:
                            from .models import Lote
                            Lote.objects.filter(pk=obj.pk).update(fecha_fabricacion=primera_fecha)
                            obj.fecha_fabricacion = primera_fecha  # Actualizar en memoria
                            logger.info(f"[SERIALIZER-SYNC] Lote {obj.numero_lote}: fecha_fabricacion = {primera_fecha}")
                        except Exception as e:
                            logger.warning(f"[SERIALIZER-SYNC] Error sincronizando fecha lote {obj.pk}: {e}")
                    return max(fechas)
            return obj.fecha_fabricacion
        
        from .models import LoteParcialidad
        ultima = LoteParcialidad.objects.filter(lote=obj).order_by('-fecha_entrega').first()
        if ultima and ultima.fecha_entrega:
            # AUTO-SYNC: Si lote no tiene fecha pero hay parcialidades
            if obj.fecha_fabricacion is None:
                primera = LoteParcialidad.objects.filter(lote=obj).order_by('fecha_entrega').first()
                if primera and primera.fecha_entrega:
                    try:
                        from .models import Lote
                        Lote.objects.filter(pk=obj.pk).update(fecha_fabricacion=primera.fecha_entrega)
                        obj.fecha_fabricacion = primera.fecha_entrega
                        logger.info(f"[SERIALIZER-SYNC] Lote {obj.numero_lote}: fecha_fabricacion = {primera.fecha_entrega}")
                    except Exception as e:
                        logger.warning(f"[SERIALIZER-SYNC] Error sincronizando fecha lote {obj.pk}: {e}")
            return ultima.fecha_entrega
        
        # Fallback: usar fecha_fabricacion si existe (datos legacy)
        return obj.fecha_fabricacion
    
    def get_producto_info(self, obj):
        """Devuelve información adicional del producto para mostrar en tabla/formulario."""
        if obj.producto:
            return {
                'presentacion': obj.producto.presentacion or '',
                'unidad_medida': obj.producto.unidad_medida or 'PIEZA',
            }
        return None
    
    def to_internal_value(self, data):
        # Si viene 'precio_compra' pero no 'precio_unitario', mapear automáticamente
        if 'precio_compra' in data and 'precio_unitario' not in data:
            data = data.copy()
            data['precio_unitario'] = data.pop('precio_compra')
        return super().to_internal_value(data)
    
    def validate_fecha_caducidad(self, value):
        """
        ISS-DB-004: Validar que fecha_caducidad esté presente (NOT NULL en BD).
        Además, validar que no esté más de 8 años en el futuro.
        """
        if value is None:
            raise serializers.ValidationError(
                'La fecha de caducidad es obligatoria. Use 2099-12-31 para insumos sin caducidad.'
            )
        
        # VALIDACIÓN: Fechas de caducidad no pueden estar más de 8 años en el futuro
        # Usa relativedelta para considerar años bisiestos correctamente
        from datetime import date
        from dateutil.relativedelta import relativedelta
        fecha_actual = date.today()
        fecha_maxima = fecha_actual + relativedelta(years=8)
        
        if value > fecha_maxima:
            raise serializers.ValidationError(
                f'Fecha de caducidad muy lejana ({value.strftime("%d/%m/%Y")}). '
                f'Máximo permitido: 8 años desde hoy ({fecha_maxima.strftime("%d/%m/%Y")}). '
                f'Verifique que el formato sea correcto (DD/MM/AAAA).'
            )
        
        return value
    
    def validate_numero_lote(self, value):
        """Número de lote es requerido y no puede estar vacío."""
        if not value or value.strip() == '':
            raise serializers.ValidationError('El número de lote es requerido')
        return value.strip()
    
    def validate_cantidad_inicial(self, value):
        """
        ISS-SEC-002: cantidad_inicial SOLO se establece al CREAR un lote.
        
        En UPDATE se rechaza explícitamente: la cantidad inicial no es editable.
        Para reabastecer un lote, usar Movimientos → Entrada.
        """
        if self.instance is not None:
            # UPDATE: rechazar explícitamente cualquier intento de modificar
            if value is not None and value != self.instance.cantidad_inicial:
                raise serializers.ValidationError(
                    'La cantidad inicial no es editable. '
                    'Para reabastecer un lote, registre un Movimiento de Entrada.'
                )
            # Si envían el mismo valor, simplemente ignorar (no es un cambio)
            return self.instance.cantidad_inicial
        
        # CREATE: es obligatorio y debe ser > 0
        if value is None:
            raise serializers.ValidationError('La cantidad inicial es requerida al crear un lote.')
        if value < 0:
            raise serializers.ValidationError('La cantidad inicial no puede ser negativa.')
        if value == 0:
            raise serializers.ValidationError('La cantidad inicial debe ser mayor a cero.')
        return value
    
    def validate_precio_unitario(self, value):
        """
        Precio unitario debe ser no negativo.
        Si es None, se usa el default 0.
        """
        if value is None:
            return 0  # Default a 0 si no se proporciona
        if value < 0:
            raise serializers.ValidationError('El precio unitario no puede ser negativo')
        return value
    
    def validate(self, attrs):
        """
        ISS-007 FIX (audit9): Validaciones de entrada bajo contrato.
        
        Si el lote tiene numero_contrato, busca el Contrato y valida:
        1. Que el contrato esté vigente (fechas y activo)
        2. Que la cantidad no exceda límites del ContratoProducto
        3. Que el monto total no exceda el monto máximo del contrato
        4. Que la fecha de caducidad sea válida
        
        NOTA: El modelo Contrato es opcional (puede no existir en la BD).
        """
        from django.core.exceptions import ValidationError as DjangoValidationError
        
        numero_contrato = attrs.get('numero_contrato')
        producto = attrs.get('producto')
        cantidad = attrs.get('cantidad_inicial', 0)
        fecha_caducidad = attrs.get('fecha_caducidad')
        
        # ISS-007: Si hay numero_contrato, buscar y validar el Contrato (si existe el modelo)
        if numero_contrato and producto and cantidad > 0:
            try:
                # Intentar importar el modelo Contrato (puede no existir)
                from .models import Contrato
                
                # Buscar contrato por número
                contrato = Contrato.objects.filter(
                    numero_contrato=numero_contrato,
                    activo=True
                ).first()
                
                if contrato:
                    # Usar método validar_entrada del modelo Contrato
                    contrato.validar_entrada(
                        producto=producto,
                        cantidad=cantidad,
                        fecha_caducidad=fecha_caducidad
                    )
                # Si no existe contrato con ese número, solo es advertencia (no bloquea)
                # porque el contrato podría estar en otro sistema o ser legacy
                
            except ImportError:
                # El modelo Contrato no existe - continuar sin validación de contrato
                pass
            except DjangoValidationError as e:
                # Convertir ValidationError de Django a DRF
                if hasattr(e, 'message_dict'):
                    raise serializers.ValidationError(e.message_dict)
                raise serializers.ValidationError({'numero_contrato': str(e)})
        
        # ISS-INV-001: Validar contrato del LOTE INDIVIDUAL
        # NOTA: Solo advertencia, no bloqueo - permite sobreentregas
        cantidad_contrato_lote = attrs.get('cantidad_contrato')
        if cantidad_contrato_lote is not None and cantidad_contrato_lote > 0 and cantidad > 0:
            # La cantidad_inicial del lote excede su cantidad_contrato - solo advertir
            if cantidad > cantidad_contrato_lote:
                excedente = cantidad - cantidad_contrato_lote
                logger.warning(
                    f'⚠️ Sobreentrega lote: cantidad_inicial ({cantidad}) > contrato_lote ({cantidad_contrato_lote}). '
                    f'Excedente: {excedente}'
                )
                # Guardar alerta para incluir en respuesta
                self._alerta_contrato_lote = (
                    f'⚠️ La cantidad recibida ({cantidad}) excede el contrato del lote ({cantidad_contrato_lote}) '
                    f'por {excedente} unidades. Se registra como sobreentrega.'
                )
        
        # ISS-INV-003: Validar contrato GLOBAL por clave de producto
        # Si el lote tiene cantidad_contrato_global, verificar si la suma de
        # todos los lotes del mismo producto+contrato excedería el global.
        ccg = attrs.get('cantidad_contrato_global')
        if ccg is None and numero_contrato and producto:
            # Heredar ccg de lotes existentes con mismo producto+contrato.
            # Sin activo=True: lotes inactivos también consumieron del contrato.
            existing_ccg = Lote.objects.filter(
                producto=producto,
                numero_contrato__iexact=numero_contrato.strip(),
                cantidad_contrato_global__isnull=False,
            ).values_list('cantidad_contrato_global', flat=True).first()
            if existing_ccg is not None:
                ccg = existing_ccg
                attrs['cantidad_contrato_global'] = ccg

        if ccg is not None and numero_contrato and producto and cantidad > 0:
            # Sumar cantidad_inicial de lotes existentes con mismo producto+contrato.
            # Sin activo=True: lotes inactivos también consumieron del contrato.
            total_existente = Lote.objects.filter(
                producto=producto,
                numero_contrato__iexact=numero_contrato.strip(),
            ).aggregate(total=Sum('cantidad_inicial'))['total'] or 0

            # Si estamos editando, restar la cantidad_inicial actual del lote
            # (se descuenta para no contar dos veces el mismo lote).
            if self.instance:
                total_existente -= (self.instance.cantidad_inicial or 0)

            total_proyectado = total_existente + cantidad
            if total_proyectado > ccg:
                excedente = total_proyectado - ccg
                disponible = max(0, ccg - total_existente)
                # ADVERTENCIA en lugar de bloqueo - permitir sobreentregas con notificación
                logger.warning(
                    f'⚠️ Sobreentrega global: cantidad ({cantidad}) + existente ({total_existente}) = '
                    f'{total_proyectado} > CCG ({ccg}). Excedente: {excedente}'
                )
                self._alerta_contrato_global = (
                    f'⚠️ Se excede el contrato GLOBAL por {excedente} unidades. '
                    f'Total contratado global: {ccg}, ya recibido: {total_existente}, '
                    f'total proyectado: {total_proyectado}. Se registra como sobreentrega.'
                )

        return super().validate(attrs)
    
    def create(self, validated_data):
        """
        ISS-SEC-004: Al crear un lote, cantidad_actual = cantidad_inicial.
        ISS-INV-003: Propagar cantidad_contrato_global a lotes hermanos.
        
        El cliente NO puede establecer cantidad_actual directamente.
        Siempre se calcula internamente para evitar inconsistencias.
        """
        cantidad_inicial = validated_data.get('cantidad_inicial', 0)
        # cantidad_actual siempre = cantidad_inicial en la creación
        validated_data['cantidad_actual'] = cantidad_inicial

        # ─── CCG hard-block concurrent-safe ──────────────────────────────────
        # validate() ya rechaza el exceso, pero corre fuera de transacción y
        # no adquiere locks, por lo que dos requests simultáneos podrían pasar.
        # Aquí repetimos la validación DENTRO de transaction.atomic() con
        # SELECT FOR UPDATE sobre todos los lotes del contrato, igual que en
        # base.py (registrar_movimiento_stock) para entradas vía movimientos.
        ccg_v = validated_data.get('cantidad_contrato_global')
        nc_v = validated_data.get('numero_contrato')
        prod_v = validated_data.get('producto')
        if ccg_v and nc_v and prod_v and cantidad_inicial > 0:
            from django.db import transaction as _dbtx
            from django.db.models import Sum as _dSum
            with _dbtx.atomic():
                list(
                    Lote.objects.select_for_update().filter(
                        producto=prod_v,
                        numero_contrato__iexact=nc_v.strip(),
                    ).values_list('id', flat=True)
                )
                total_ya = (
                    Lote.objects.filter(
                        producto=prod_v,
                        numero_contrato__iexact=nc_v.strip(),
                    ).aggregate(total=_dSum('cantidad_inicial'))['total'] or 0
                )
                proyectado = total_ya + cantidad_inicial
                if proyectado > ccg_v:
                    exceso = proyectado - ccg_v
                    # ADVERTENCIA en lugar de bloqueo - permitir sobreentregas
                    logger.warning(
                        f'⚠️ Sobreentrega global (concurrente): cantidad ({cantidad_inicial}) + '
                        f'existente ({total_ya}) = {proyectado} > CCG ({ccg_v}). Exceso: {exceso}'
                    )
                    self._alerta_contrato_global = (
                        f'⚠️ Se excede el contrato GLOBAL por {exceso} unidades. '
                        f'Contrato global: {ccg_v}, ya recibido: {total_ya}, '
                        f'este lote agrega: {cantidad_inicial}, total: {proyectado}. '
                        f'Se registra como sobreentrega.'
                    )
        # ─────────────────────────────────────────────────────────────────────

        # =====================================================================
        # MERGE vs AUTO-SUFIJO: Si existe lote idéntico (mismo numero_lote,
        # producto, centro Y fecha_caducidad), hacer MERGE sumando cantidad.
        # Si existe pero con diferente caducidad, crear con sufijo .2, .3...
        # =====================================================================
        numero_lote_original = validated_data.get('numero_lote', '')
        lote_base = numero_lote_original
        producto_val = validated_data.get('producto')
        centro_val = validated_data.get('centro')  # None = farmacia central
        fecha_caducidad_val = validated_data.get('fecha_caducidad')

        # Buscar lote IDÉNTICO (mismo numero_lote, producto, centro, caducidad)
        lote_identico = Lote.objects.filter(
            numero_lote__iexact=numero_lote_original,
            producto=producto_val,
            centro=centro_val,
            fecha_caducidad=fecha_caducidad_val,
            activo=True,
        ).first()

        if lote_identico:
            # ─── MERGE: Sumar cantidad al lote existente ───
            cantidad_agregar = cantidad_inicial
            lote_identico.cantidad_inicial = (lote_identico.cantidad_inicial or 0) + cantidad_agregar
            lote_identico.cantidad_actual = (lote_identico.cantidad_actual or 0) + cantidad_agregar
            lote_identico.save(update_fields=['cantidad_inicial', 'cantidad_actual'])
            
            # Crear parcialidad para registrar esta entrega adicional
            from .models import LoteParcialidad
            from datetime import date
            request = self.context.get('request')
            user = getattr(request, 'user', None) if request else None
            fecha_entrega = validated_data.get('fecha_fabricacion') or date.today()
            LoteParcialidad.objects.create(
                lote=lote_identico,
                fecha_entrega=fecha_entrega,
                cantidad=cantidad_agregar,
                proveedor=validated_data.get('marca', ''),
                numero_factura=validated_data.get('numero_contrato', ''),
                notas=f'Merge automático - cantidad añadida al lote existente',
                usuario=user if user and user.is_authenticated else None
            )
            
            logger.info(
                f"MERGE: Lote {lote_identico.numero_lote} actualizado. "
                f"+{cantidad_agregar} unidades. Nueva cantidad: {lote_identico.cantidad_inicial}"
            )
            
            # Marcar para que la vista sepa que fue merge
            self._lote_merge_realizado = {
                'lote_id': lote_identico.pk,
                'numero_lote': lote_identico.numero_lote,
                'cantidad_agregada': cantidad_agregar,
                'nueva_cantidad_total': lote_identico.cantidad_inicial,
            }
            
            return lote_identico

        # Buscar si existe lote con mismo número pero DIFERENTE caducidad
        sufijo = 2
        numero_lote_candidato = numero_lote_original
        while Lote.objects.filter(
            numero_lote__iexact=numero_lote_candidato,
            producto=producto_val,
            centro=centro_val,
        ).exists():
            numero_lote_candidato = f"{lote_base}.{sufijo}"
            sufijo += 1
            if sufijo > 100:
                break  # salvaguarda ante bucle infinito improbable

        if numero_lote_candidato != numero_lote_original:
            validated_data['numero_lote'] = numero_lote_candidato
            self._numero_lote_auto_renombrado = {
                'original': numero_lote_original,
                'asignado': numero_lote_candidato,
            }

        instance = super().create(validated_data)
        
        # Auto-propagar cantidad_contrato_global a otros lotes con mismo producto+contrato
        ccg = instance.cantidad_contrato_global
        if ccg is not None and instance.numero_contrato and instance.producto:
            Lote.objects.filter(
                producto=instance.producto,
                numero_contrato__iexact=instance.numero_contrato.strip(),
                activo=True,
            ).exclude(pk=instance.pk).update(cantidad_contrato_global=ccg)
        
        return instance
    
    def update(self, instance, validated_data):
        """
        ISS-SEC-003: Protección integral en actualización de lotes.
        
        Reglas de negocio blindadas:
        1. cantidad_inicial: NUNCA editable (se ignora silenciosamente)
        2. cantidad_actual: read_only (ya protegido en Meta)
        3. cantidad_contrato: Solo editable por Farmacia/Admin, con auditoría
        4. Campos protegidos si hay movimientos: producto, numero_lote, fecha_caducidad, numero_contrato
        """
        from .models import Movimiento
        from .signals import registrar_auditoria
        
        # =====================================================================
        # PASO 1: Remover cantidad_inicial — NUNCA editable vía API
        # Para reabastecer, usar Movimiento de Entrada
        # =====================================================================
        validated_data.pop('cantidad_inicial', None)
        
        # =====================================================================
        # PASO 2: Verificar permisos para cantidad_contrato
        # Solo Farmacia/Admin pueden modificar cantidad_contrato
        # =====================================================================
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        
        if 'cantidad_contrato' in validated_data:
            nuevo_contrato = validated_data['cantidad_contrato']
            viejo_contrato = instance.cantidad_contrato
            
            if nuevo_contrato != viejo_contrato:
                # Verificar permiso: solo farmacia/admin
                from .permissions import RoleHelper
                if not user or not RoleHelper.is_farmacia_or_admin(user):
                    raise serializers.ValidationError({
                        'cantidad_contrato': 'Solo usuarios de Farmacia o Admin pueden modificar la cantidad del contrato.'
                    })
                
                # ISS-AUDIT: Registrar cambio de cantidad_contrato con detalle
                registrar_auditoria(
                    modelo='Lote',
                    objeto=instance,
                    accion='modificar_contrato',
                    cambios={
                        'cantidad_contrato': {
                            'anterior': viejo_contrato,
                            'nuevo': nuevo_contrato,
                        },
                        'numero_lote': instance.numero_lote,
                        'producto': str(instance.producto),
                        'usuario': user.username if user else 'sistema',
                    }
                )
        
        # =====================================================================
        # PASO 3: Proteger campos críticos si hay movimientos
        # =====================================================================
        tiene_movimientos = Movimiento.objects.filter(lote=instance).exists()
        
        if tiene_movimientos:
            campos_protegidos = {
                'producto': 'producto',
                'numero_lote': 'código de lote', 
                'fecha_caducidad': 'fecha de caducidad',
                'numero_contrato': 'número de contrato',
            }
            
            errores = {}
            for campo, nombre in campos_protegidos.items():
                if campo in validated_data:
                    valor_nuevo = validated_data[campo]
                    valor_actual = getattr(instance, campo)
                    
                    if campo == 'producto':
                        valor_actual_id = valor_actual.id if valor_actual else None
                        valor_nuevo_id = valor_nuevo.id if valor_nuevo else None
                        if valor_nuevo_id != valor_actual_id:
                            errores[campo] = f'No se puede modificar el {nombre} de un lote con movimientos registrados'
                    elif valor_nuevo != valor_actual:
                        errores[campo] = f'No se puede modificar la {nombre} de un lote con movimientos registrados'
            
            if errores:
                raise serializers.ValidationError(errores)
            
            for campo in campos_protegidos.keys():
                validated_data.pop(campo, None)
        
        # =====================================================================
        # PASO 4: Auditoría completa con datos anteriores/nuevos
        # =====================================================================
        datos_anteriores = {}
        datos_nuevos = {}
        for campo, valor_nuevo in validated_data.items():
            valor_actual = getattr(instance, campo, None)
            # Manejar FKs
            if hasattr(valor_actual, 'pk'):
                valor_actual = valor_actual.pk
            if hasattr(valor_nuevo, 'pk'):
                valor_nuevo = valor_nuevo.pk
            if valor_actual != valor_nuevo:
                datos_anteriores[campo] = str(valor_actual) if valor_actual is not None else None
                datos_nuevos[campo] = str(valor_nuevo) if valor_nuevo is not None else None
        
        result = super().update(instance, validated_data)
        
        # ISS-INV-003: Auto-propagar cantidad_contrato_global al editar
        ccg = result.cantidad_contrato_global
        if ccg is not None and result.numero_contrato and result.producto:
            Lote.objects.filter(
                producto=result.producto,
                numero_contrato__iexact=result.numero_contrato.strip(),
                activo=True,
            ).exclude(pk=result.pk).update(cantidad_contrato_global=ccg)
        
        # Solo registrar auditoría si hubo cambios reales
        if datos_anteriores:
            registrar_auditoria(
                modelo='Lote',
                objeto=result,
                accion='actualizar',
                cambios={
                    'datos_anteriores': datos_anteriores,
                    'datos_nuevos': datos_nuevos,
                    'usuario': user.username if user else 'sistema',
                    'numero_lote': result.numero_lote,
                }
            )
        
        return result
    
    def get_dias_para_caducar(self, obj):
        if obj.fecha_caducidad:
            delta = obj.fecha_caducidad - timezone.now().date()
            return delta.days
        return None
    
    def get_estado(self, obj):
        # Propiedad calculada basada en cantidad y fecha
        if obj.cantidad_actual <= 0:
            return 'agotado'
        if obj.fecha_caducidad and obj.fecha_caducidad < timezone.now().date():
            return 'caducado'
        return 'disponible'
    
    def get_alerta_caducidad(self, obj):
        """
        Calcula el nivel de alerta basado en días para caducar.
        Alineado con la clasificación SIFP:
        - Normal: > 6 meses (180 días)
        - Próximo: 3-6 meses (90-180 días)
        - Crítico: < 3 meses (90 días)
        - Vencido: < 0 días
        """
        if not obj.fecha_caducidad:
            return 'normal'
        dias = (obj.fecha_caducidad - timezone.now().date()).days
        if dias < 0:
            return 'vencido'
        elif dias < 90:
            return 'critico'
        elif dias < 180:
            return 'proximo'
        return 'normal'
    
    def get_porcentaje_consumido(self, obj):
        """Calcula el porcentaje de consumo del lote."""
        if obj.cantidad_inicial and obj.cantidad_inicial > 0:
            consumido = obj.cantidad_inicial - obj.cantidad_actual
            return round((consumido / obj.cantidad_inicial) * 100)
        return 0
    
    def get_documentos(self, obj):
        """Obtiene los documentos asociados al lote."""
        # Usar prefetch si está disponible, sino hacer query
        if hasattr(obj, '_prefetched_objects_cache') and 'documentos' in obj._prefetched_objects_cache:
            docs = obj._prefetched_objects_cache['documentos']
        else:
            docs = obj.documentos.all()[:5]  # Limitar a 5 más recientes
        
        return [{
            'id': doc.id,
            'tipo_documento': doc.tipo_documento,
            'numero_documento': doc.numero_documento,
            'archivo': doc.archivo,
            'nombre_archivo': doc.nombre_archivo,
            'fecha_documento': doc.fecha_documento,
        } for doc in docs]
    
    def get_tiene_documentos(self, obj):
        """Indica si el lote tiene documentos asociados."""
        if hasattr(obj, '_prefetched_objects_cache') and 'documentos' in obj._prefetched_objects_cache:
            return len(obj._prefetched_objects_cache['documentos']) > 0
        return obj.documentos.exists()
    
    def get_tiene_movimientos(self, obj):
        """
        ISS-TRAZ: Indica si el lote tiene movimientos registrados.
        Si tiene movimientos, los campos críticos no son editables.
        """
        from .models import Movimiento
        return Movimiento.objects.filter(lote=obj).exists()


# =============================================================================
# =============================================================================
# FLUJO V2: HISTORIAL DE ESTADOS SERIALIZER
# =============================================================================

class RequisicionHistorialEstadosSerializer(serializers.ModelSerializer):
    """
    FLUJO V2: Serializer para el historial inmutable de cambios de estado.
    
    Proporciona información completa para auditoría y visualización
    del timeline de requisiciones.
    """
    usuario_nombre = serializers.SerializerMethodField()
    accion_display = serializers.SerializerMethodField()
    estado_anterior_display = serializers.SerializerMethodField()
    estado_nuevo_display = serializers.SerializerMethodField()
    fecha_cambio_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = RequisicionHistorialEstados
        fields = [
            'id',
            'requisicion',
            'estado_anterior',
            'estado_anterior_display',
            'estado_nuevo',
            'estado_nuevo_display',
            'usuario',
            'usuario_nombre',
            'fecha_cambio',
            'fecha_cambio_formatted',
            'accion',
            'accion_display',
            'motivo',
            'observaciones',
            'datos_adicionales',
            # No exponemos ip_address ni hash_verificacion por seguridad
        ]
        read_only_fields = fields  # Historial es inmutable
    
    def get_usuario_nombre(self, obj):
        """Nombre del usuario que realizó el cambio."""
        if obj.usuario:
            return obj.usuario.get_full_name() or obj.usuario.username
        return 'Sistema'
    
    def get_accion_display(self, obj):
        """Nombre legible de la acción."""
        acciones_dict = dict(RequisicionHistorialEstados.ACCIONES_FLUJO)
        return acciones_dict.get(obj.accion, obj.accion)
    
    def get_estado_anterior_display(self, obj):
        """Nombre legible del estado anterior."""
        from .constants import ESTADOS_REQUISICION
        estados_dict = dict(ESTADOS_REQUISICION)
        return estados_dict.get(obj.estado_anterior, obj.estado_anterior) if obj.estado_anterior else '-'
    
    def get_estado_nuevo_display(self, obj):
        """Nombre legible del estado nuevo."""
        from .constants import ESTADOS_REQUISICION
        estados_dict = dict(ESTADOS_REQUISICION)
        return estados_dict.get(obj.estado_nuevo, obj.estado_nuevo)
    
    def get_fecha_cambio_formatted(self, obj):
        """Fecha formateada para display."""
        if obj.fecha_cambio:
            return obj.fecha_cambio.strftime('%d/%m/%Y %H:%M')
        return None


# DETALLE REQUISICION SERIALIZER
# =============================================================================

class DetalleRequisicionSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_unidad = serializers.CharField(source='producto.unidad_medida', read_only=True)
    producto_presentacion = serializers.CharField(source='producto.presentacion', read_only=True, allow_null=True)
    lote_numero = serializers.CharField(source='lote.numero_lote', read_only=True, allow_null=True)
    # ISS-DB: Alias para compatibilidad con frontend
    producto_clave = serializers.CharField(source='producto.clave', read_only=True, allow_null=True)
    producto_descripcion = serializers.CharField(source='producto.nombre', read_only=True)  # Alias de producto_nombre
    lote_caducidad = serializers.DateField(source='lote.fecha_caducidad', read_only=True, allow_null=True)
    lote_stock = serializers.IntegerField(source='lote.cantidad_actual', read_only=True, allow_null=True)
    stock_disponible = serializers.SerializerMethodField()  # ISS-FIX: Usar método para calcular stock real
    stock_centro = serializers.SerializerMethodField()  # Stock del producto/lote en el centro destino
    # cantidad_surtida tiene default 0 en BD
    cantidad_surtida = serializers.IntegerField(required=False, default=0, allow_null=True)
    # MEJORA FLUJO 3: Campo para explicar ajustes de cantidad
    motivo_ajuste = serializers.CharField(required=False, allow_null=True, allow_blank=True, max_length=255)
    
    class Meta:
        model = DetalleRequisicion
        fields = [
            'id', 'producto', 'lote', 
            'producto_nombre', 'producto_clave', 'producto_descripcion', 'producto_unidad', 'producto_presentacion',
            'lote_numero', 'lote_caducidad', 'lote_stock', 'stock_disponible', 'stock_centro',
            'cantidad_solicitada', 'cantidad_autorizada', 
            'cantidad_surtida', 'cantidad_recibida', 'notas', 'motivo_ajuste',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'lote': {'required': False, 'allow_null': True},  # ISS-FIX: Lote puede ser null
            'notas': {'required': False, 'allow_null': True, 'allow_blank': True},
            'cantidad_autorizada': {'required': False, 'allow_null': True},
            'cantidad_recibida': {'required': False, 'allow_null': True},
        }
    
    def validate_cantidad_solicitada(self, value):
        if value <= 0:
            raise serializers.ValidationError('La cantidad debe ser mayor a 0')
        # Validar que sea número entero (sin decimales)
        if not isinstance(value, int) or value != int(value):
            raise serializers.ValidationError(
                'La cantidad debe ser un número entero (sin decimales). '
                f'Valor recibido: {value}'
            )
        return int(value)
    
    def get_stock_disponible(self, obj):
        """
        ISS-FIX: Calcula el stock disponible priorizando:
        1. Stock del lote asignado si existe
        2. Stock total del producto en farmacia central si no hay lote
        """
        # Si hay lote asignado, usar su cantidad_actual
        if obj.lote and obj.lote.cantidad_actual is not None:
            return obj.lote.cantidad_actual
        
        # Si no hay lote, calcular stock total del producto en farmacia central
        if obj.producto:
            # Stock total de lotes activos del producto (en farmacia = sin centro)
            from django.db.models import Sum
            stock_total = obj.producto.lotes.filter(
                activo=True,
                cantidad_actual__gt=0,
                centro__isnull=True  # Lotes de farmacia central
            ).aggregate(total=Sum('cantidad_actual'))['total']
            return stock_total or 0
        
        return 0
    
    def get_stock_centro(self, obj):
        """
        Calcula el stock del producto/lote en el centro ORIGEN de la requisición.
        Esto permite a Farmacia ver cuánto tiene el centro que hace la solicitud.
        
        CORREGIDO: Antes usaba centro_destino (que es NULL cuando centro pide a farmacia).
        Ahora usa centro_origen (el centro que hace la requisición).
        """
        # Obtener el centro origen de la requisición (el centro que hace el pedido)
        centro_origen = None
        if hasattr(obj, 'requisicion') and obj.requisicion:
            centro_origen = obj.requisicion.centro_origen
        
        if not centro_origen or not obj.producto:
            return 0
        
        from django.db.models import Sum
        
        # Si hay lote específico, buscar ese lote en el centro
        if obj.lote:
            lote_centro = obj.producto.lotes.filter(
                numero_lote=obj.lote.numero_lote,
                centro=centro_origen,
                activo=True
            ).first()
            return lote_centro.cantidad_actual if lote_centro else 0
        
        # Si no hay lote, calcular stock total del producto en el centro origen
        stock_total = obj.producto.lotes.filter(
            activo=True,
            cantidad_actual__gt=0,
            centro=centro_origen
        ).aggregate(total=Sum('cantidad_actual'))['total']
        return stock_total or 0
    
    def validate(self, data):
        """
        MEJORA FLUJO 3: Si cantidad_autorizada < cantidad_solicitada,
        se requiere motivo_ajuste obligatorio.
        """
        cantidad_solicitada = data.get('cantidad_solicitada') or (self.instance.cantidad_solicitada if self.instance else None)
        cantidad_autorizada = data.get('cantidad_autorizada')
        motivo_ajuste = data.get('motivo_ajuste', '').strip() if data.get('motivo_ajuste') else ''
        
        # Solo validar si se está autorizando menos de lo solicitado
        if cantidad_autorizada is not None and cantidad_solicitada is not None:
            if cantidad_autorizada < cantidad_solicitada:
                if not motivo_ajuste or len(motivo_ajuste) < 10:
                    raise serializers.ValidationError({
                        'motivo_ajuste': 'Debe indicar el motivo del ajuste (mínimo 10 caracteres) cuando autoriza menos cantidad de la solicitada.'
                    })
        
        return data


# =============================================================================
# REQUISICION SERIALIZERS
# =============================================================================

class RequisicionListSerializer(serializers.ModelSerializer):
    """
    Serializer LIGERO para listado de requisiciones.
    OPTIMIZACIÓN: Evita SerializerMethodField y nested serializers costosos.
    Usa campos anotados desde el queryset para evitar N+1 queries.
    """
    # Campos básicos con source directo (sin método)
    folio = serializers.CharField(source='numero', read_only=True)
    centro_nombre = serializers.CharField(source='centro_origen.nombre', read_only=True, allow_null=True)
    centro = serializers.IntegerField(source='centro_origen_id', read_only=True, allow_null=True)
    solicitante_nombre = serializers.SerializerMethodField()
    usuario_solicita_nombre = serializers.SerializerMethodField()  # Alias para frontend
    # AUDITORÍA: Quién autorizó, surtió o rechazó (para trazabilidad visual en lista)
    usuario_autoriza_nombre = serializers.SerializerMethodField()
    surtidor_nombre = serializers.SerializerMethodField()
    rechazado_por_nombre = serializers.SerializerMethodField()

    # Campos anotados desde el queryset (evitan N+1)
    total_productos = serializers.IntegerField(read_only=True)
    total_items = serializers.IntegerField(source='total_productos', read_only=True)
    
    class Meta:
        model = Requisicion
        fields = [
            'id', 'numero', 'folio', 'centro', 'centro_nombre', 'centro_origen_id',
            'solicitante_nombre', 'usuario_solicita_nombre', 'fecha_solicitud', 'estado', 'tipo', 'prioridad',
            'es_urgente', 'total_productos', 'total_items',
            'fecha_autorizacion', 'fecha_surtido', 'fecha_entrega',
            # AUDITORÍA: actores del flujo
            'usuario_autoriza_nombre', 'surtidor_nombre', 'rechazado_por_nombre', 'motivo_rechazo',
        ]
        read_only_fields = fields
    
    def get_solicitante_nombre(self, obj):
        if obj.solicitante:
            return obj.solicitante.get_full_name() or obj.solicitante.username
        return None
    
    def get_usuario_solicita_nombre(self, obj):
        """Alias de solicitante_nombre para compatibilidad con frontend."""
        return self.get_solicitante_nombre(obj)

    def get_usuario_autoriza_nombre(self, obj):
        """Quien autorizó (autorizador_farmacia → autorizador director → autorizador_admin → autorizador)."""
        for campo in ('autorizador_farmacia', 'director_centro', 'administrador_centro', 'autorizador'):
            actor = getattr(obj, campo, None)
            if actor:
                return actor.get_full_name() or actor.username
        return None

    def get_surtidor_nombre(self, obj):
        """Quien surtió la requisición."""
        actor = getattr(obj, 'surtidor', None)
        if actor:
            return actor.get_full_name() or actor.username
        return None

    def get_rechazado_por_nombre(self, obj):
        """Quien rechazó la requisición (usa historial o campo rechazado_por si existe)."""
        actor = getattr(obj, 'rechazado_por', None)
        if actor:
            return actor.get_full_name() or actor.username
        return None


class RequisicionSerializer(serializers.ModelSerializer):
    # NOTA: Para creación se usa 'items' o 'detalles' en request.data, procesado manualmente en ViewSet
    detalles = DetalleRequisicionSerializer(many=True, required=False)
    # Usar campos reales de la BD
    centro_origen_nombre = serializers.CharField(source='centro_origen.nombre', read_only=True, allow_null=True)
    centro_destino_nombre = serializers.CharField(source='centro_destino.nombre', read_only=True, allow_null=True)
    solicitante_nombre = serializers.SerializerMethodField()
    solicitante_id = serializers.IntegerField(read_only=True)  # ISS-FIX: Campo explícito para comparación en frontend
    autorizador_nombre = serializers.SerializerMethodField()
    total_productos = serializers.SerializerMethodField()
    
    # ISS-DB: Alias para compatibilidad con frontend (campos calculados/read_only)
    folio = serializers.CharField(source='numero', read_only=True)  # Alias de numero
    # ISS-FIX-CENTRO: 'centro_nombre' debe mostrar centro_origen (el centro que SOLICITA)
    centro_nombre = serializers.CharField(source='centro_origen.nombre', read_only=True, allow_null=True)
    usuario_solicita_nombre = serializers.SerializerMethodField()  # Alias de solicitante_nombre
    usuario_autoriza_nombre = serializers.SerializerMethodField()  # Alias de autorizador_nombre
    observaciones = serializers.CharField(source='notas', read_only=True, allow_null=True)  # Alias de notas
    # motivo_rechazo es ahora un campo real en la BD (FLUJO V2), no un alias
    total_items = serializers.SerializerMethodField()  # Alias de total_productos
    
    # ISS-FIX-CENTRO: Campo 'centro' para compatibilidad con frontend
    # Representa el centro que SOLICITA la requisición (centro_origen)
    # NOTA: Se usa SerializerMethodField para lectura y se sobreescribe en create/update para escritura
    centro = serializers.SerializerMethodField(read_only=True)  # Para lectura (devuelve centro_origen_id)
    centro_write = serializers.PrimaryKeyRelatedField(
        source='centro_origen', queryset=Centro.objects.all(), 
        required=False, allow_null=True, write_only=True
    )
    # Campo 'comentario' para compatibilidad con frontend (alias de notas)
    comentario = serializers.SerializerMethodField(read_only=True)  # Para lectura (devuelve notas)
    comentario_write = serializers.CharField(source='notas', required=False, allow_blank=True, allow_null=True, write_only=True)
    
    # ========== CAMPOS URGENCIA ==========
    fecha_entrega_solicitada = serializers.DateField(required=False, allow_null=True)
    es_urgente = serializers.BooleanField(required=False, default=False)
    motivo_urgencia = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    
    # ========== FLUJO V2: CAMPOS DE TRAZABILIDAD TEMPORAL ==========
    fecha_envio_admin = serializers.DateTimeField(read_only=True)
    fecha_autorizacion_admin = serializers.DateTimeField(read_only=True)
    fecha_envio_director = serializers.DateTimeField(read_only=True)
    fecha_autorizacion_director = serializers.DateTimeField(read_only=True)
    fecha_envio_farmacia = serializers.DateTimeField(read_only=True)
    fecha_recepcion_farmacia = serializers.DateTimeField(read_only=True)
    fecha_autorizacion_farmacia = serializers.DateTimeField(read_only=True)
    fecha_recoleccion_limite = serializers.DateTimeField(required=False, allow_null=True)
    fecha_vencimiento = serializers.DateTimeField(read_only=True)
    
    # ========== FLUJO V2: ACTORES (READ-ONLY PARA TRAZABILIDAD) ==========
    administrador_centro_nombre = serializers.SerializerMethodField()
    director_centro_nombre = serializers.SerializerMethodField()
    receptor_farmacia_nombre = serializers.SerializerMethodField()
    autorizador_farmacia_nombre = serializers.SerializerMethodField()
    surtidor_nombre = serializers.SerializerMethodField()
    
    # ========== FLUJO V2: MOTIVOS (motivo_rechazo ya existe como alias) ==========
    motivo_devolucion = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    motivo_vencimiento = serializers.CharField(read_only=True)
    observaciones_farmacia = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    
    class Meta:
        model = Requisicion
        fields = [
            'id', 'numero', 'folio', 'centro', 'centro_write', 'comentario', 'comentario_write',
            'centro_origen', 'centro_origen_nombre', 
            'centro_destino', 'centro_destino_nombre', 'centro_nombre',
            'solicitante', 'solicitante_id', 'solicitante_nombre', 'usuario_solicita_nombre',
            'autorizador', 'autorizador_nombre', 'usuario_autoriza_nombre',
            'fecha_solicitud', 'fecha_autorizacion', 'fecha_surtido', 'fecha_entrega',
            'estado', 'tipo', 'prioridad', 'notas', 'observaciones', 'motivo_rechazo', 'lugar_entrega',
            'foto_firma_surtido', 'foto_firma_recepcion',
            'usuario_firma_surtido', 'usuario_firma_recepcion',
            'fecha_firma_surtido', 'fecha_firma_recepcion',
            # Campos para formato de requisicion del centro (firmas)
            'firma_solicitante', 'nombre_solicitante', 'cargo_solicitante',
            'firma_jefe_area', 'nombre_jefe_area', 'cargo_jefe_area',
            'firma_director', 'nombre_director', 'cargo_director',
            # Campos urgencia
            'fecha_entrega_solicitada', 'es_urgente', 'motivo_urgencia',
            # ========== FLUJO V2: CAMPOS DE TRAZABILIDAD ==========
            # Fechas del flujo jerárquico
            'fecha_envio_admin', 'fecha_autorizacion_admin',
            'fecha_envio_director', 'fecha_autorizacion_director',
            'fecha_envio_farmacia', 'fecha_recepcion_farmacia', 'fecha_autorizacion_farmacia',
            'fecha_recoleccion_limite', 'fecha_vencimiento',
            # Actores (IDs y nombres)
            'administrador_centro', 'administrador_centro_nombre',
            'director_centro', 'director_centro_nombre',
            'receptor_farmacia', 'receptor_farmacia_nombre',
            'autorizador_farmacia', 'autorizador_farmacia_nombre',
            'surtidor', 'surtidor_nombre',
            # Motivos
            'motivo_devolucion', 'motivo_vencimiento', 'observaciones_farmacia',
            # Fin FLUJO V2
            'detalles', 'total_productos', 'total_items', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'numero', 'folio', 'fecha_solicitud', 'created_at', 'updated_at',
            # FLUJO V2: Campos de trazabilidad son read-only (se setean por lógica de negocio)
            'fecha_envio_admin', 'fecha_autorizacion_admin',
            'fecha_envio_director', 'fecha_autorizacion_director',
            'fecha_envio_farmacia', 'fecha_recepcion_farmacia', 'fecha_autorizacion_farmacia',
            'fecha_vencimiento', 'motivo_vencimiento',
            # FLUJO V2: Estado solo se modifica por endpoints de transición
            'estado',
            # FLUJO V2: Actores del flujo (se asignan automáticamente)
            'administrador_centro', 'director_centro',
            'receptor_farmacia', 'autorizador_farmacia', 'surtidor',
        ]
        extra_kwargs = {
            # Campos con defaults en BD
            'estado': {'required': False, 'default': 'borrador'},
            'tipo': {'required': False, 'default': 'normal'},
            'prioridad': {'required': False, 'default': 'normal'},
            # Campos nullable
            'notas': {'required': False, 'allow_null': True, 'allow_blank': True},
            'lugar_entrega': {'required': False, 'allow_null': True, 'allow_blank': True},
            'centro_origen': {'required': False, 'allow_null': True},
            'centro_destino': {'required': False, 'allow_null': True},
            'solicitante': {'required': False, 'allow_null': True},
            'autorizador': {'required': False, 'allow_null': True},
            # Campos de firmas para formato (todos opcionales)
            'firma_solicitante': {'required': False, 'allow_null': True, 'allow_blank': True},
            'nombre_solicitante': {'required': False, 'allow_null': True, 'allow_blank': True},
            'cargo_solicitante': {'required': False, 'allow_null': True, 'allow_blank': True},
            'firma_jefe_area': {'required': False, 'allow_null': True, 'allow_blank': True},
            'nombre_jefe_area': {'required': False, 'allow_null': True, 'allow_blank': True},
            'cargo_jefe_area': {'required': False, 'allow_null': True, 'allow_blank': True},
            'firma_director': {'required': False, 'allow_null': True, 'allow_blank': True},
            'nombre_director': {'required': False, 'allow_null': True, 'allow_blank': True},
            'cargo_director': {'required': False, 'allow_null': True, 'allow_blank': True},
        }
    
    def get_solicitante_nombre(self, obj):
        if obj.solicitante:
            return obj.solicitante.get_full_name() or obj.solicitante.username
        return None
    
    def get_usuario_solicita_nombre(self, obj):
        """Alias de solicitante_nombre para compatibilidad con frontend."""
        return self.get_solicitante_nombre(obj)
    
    def get_autorizador_nombre(self, obj):
        if obj.autorizador:
            return obj.autorizador.get_full_name() or obj.autorizador.username
        return None
    
    def get_centro(self, obj):
        """ISS-FIX-CENTRO: Devuelve centro_origen_id (el centro que SOLICITA).
        FALLBACK: si centro_origen es NULL (datos viejos), usar centro_destino."""
        return obj.centro_origen_id or obj.centro_destino_id
    
    def get_comentario(self, obj):
        """Alias de notas para compatibilidad con frontend (lectura)."""
        return obj.notas
    
    def get_usuario_autoriza_nombre(self, obj):
        """Alias de autorizador_nombre para compatibilidad con frontend."""
        return self.get_autorizador_nombre(obj)
    
    def get_total_productos(self, obj):
        return obj.detalles.count()
    
    def get_total_items(self, obj):
        """Alias de total_productos para compatibilidad con frontend."""
        return self.get_total_productos(obj)
    
    # ========== FLUJO V2: MÉTODOS GET PARA NOMBRES DE ACTORES ==========
    def get_administrador_centro_nombre(self, obj):
        """Nombre del administrador del centro que autorizó."""
        if obj.administrador_centro:
            return obj.administrador_centro.get_full_name() or obj.administrador_centro.username
        return None
    
    def get_director_centro_nombre(self, obj):
        """Nombre del director del centro que autorizó."""
        if obj.director_centro:
            return obj.director_centro.get_full_name() or obj.director_centro.username
        return None
    
    def get_receptor_farmacia_nombre(self, obj):
        """Nombre del usuario de farmacia que recibió la requisición."""
        if obj.receptor_farmacia:
            return obj.receptor_farmacia.get_full_name() or obj.receptor_farmacia.username
        return None
    
    def get_autorizador_farmacia_nombre(self, obj):
        """Nombre del usuario de farmacia que autorizó."""
        if obj.autorizador_farmacia:
            return obj.autorizador_farmacia.get_full_name() or obj.autorizador_farmacia.username
        return None
    
    def get_surtidor_nombre(self, obj):
        """Nombre del usuario que surtió la requisición."""
        if obj.surtidor:
            return obj.surtidor.get_full_name() or obj.surtidor.username
        return None
    
    def to_internal_value(self, data):
        """
        Mapea campos del frontend a campos internos antes de validación.
        ISS-FIX-CENTRO: El frontend envía 'centro' que representa el centro
        que SOLICITA la requisición, mapeamos a 'centro_origen'.
        """
        # Crear copia mutable de los datos
        data = data.copy() if hasattr(data, 'copy') else dict(data)
        
        # ISS-FIX-CENTRO: Mapear 'centro' → 'centro_write' (que tiene source='centro_origen')
        if 'centro' in data and 'centro_write' not in data:
            data['centro_write'] = data.pop('centro')
        
        # Mapear 'comentario' → 'comentario_write' (que tiene source='notas')
        if 'comentario' in data and 'comentario_write' not in data:
            data['comentario_write'] = data.pop('comentario')
        
        return super().to_internal_value(data)
    
    def validate(self, data):
        """Validaciones de requisicion con campos de urgencia."""
        # Validar que notas/observaciones no esten vacias al enviar
        estado = data.get('estado', getattr(self.instance, 'estado', 'borrador') if self.instance else 'borrador')
        notas = data.get('notas', getattr(self.instance, 'notas', None) if self.instance else None)
        
        # Si esta enviando la requisicion (cambiando de borrador a enviada)
        if estado == 'enviada' and not notas:
            raise serializers.ValidationError({
                'notas': 'Las observaciones son obligatorias al enviar una requisicion.'
            })
        
        # Validar urgencia
        es_urgente = data.get('es_urgente', False)
        motivo_urgencia = data.get('motivo_urgencia', '')
        fecha_entrega_solicitada = data.get('fecha_entrega_solicitada')
        
        if es_urgente and not motivo_urgencia:
            raise serializers.ValidationError({
                'motivo_urgencia': 'El motivo de urgencia es obligatorio cuando se marca como urgente.'
            })
        
        # Auto-marcar como urgente si fecha_entrega_solicitada < hoy + 2 dias
        if fecha_entrega_solicitada:
            from datetime import date, timedelta
            limite_urgencia = date.today() + timedelta(days=2)
            if fecha_entrega_solicitada < limite_urgencia:
                data['es_urgente'] = True
                if not data.get('motivo_urgencia'):
                    data['motivo_urgencia'] = 'Fecha de entrega proxima (menos de 2 dias)'
        
        return data
    
    def create(self, validated_data):
        detalles_data = validated_data.pop('detalles', [])
        # Generar numero automatico si no viene
        if 'numero' not in validated_data or not validated_data.get('numero'):
            from django.utils import timezone
            import random
            validated_data['numero'] = f"REQ-{timezone.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        requisicion = Requisicion.objects.create(**validated_data)
        for detalle_data in detalles_data:
            DetalleRequisicion.objects.create(requisicion=requisicion, **detalle_data)
        return requisicion
    
    def update(self, instance, validated_data):
        detalles_data = validated_data.pop('detalles', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if detalles_data is not None:
            instance.detalles.all().delete()
            for detalle_data in detalles_data:
                DetalleRequisicion.objects.create(requisicion=instance, **detalle_data)
        return instance


# =============================================================================
# MOVIMIENTO SERIALIZER
# =============================================================================

# Subtipos válidos para salidas (MEJORA FLUJO 5)
SUBTIPOS_SALIDA_VALIDOS = ['receta', 'consumo_interno', 'merma', 'caducidad', 'transferencia', 'otro']

class MovimientoSerializer(serializers.ModelSerializer):
    lote_numero = serializers.CharField(source='lote.numero_lote', read_only=True, allow_null=True)
    numero_lote = serializers.CharField(source='lote.numero_lote', read_only=True, allow_null=True)  # Alias para frontend
    lote_codigo = serializers.CharField(source='lote.numero_lote', read_only=True, allow_null=True)  # Alias para frontend
    producto_nombre = serializers.SerializerMethodField()
    producto_clave = serializers.CharField(source='lote.producto.clave', read_only=True, allow_null=True)  # Campo para frontend
    producto_descripcion = serializers.CharField(source='lote.producto.nombre', read_only=True, allow_null=True)  # Campo para frontend
    centro_origen_nombre = serializers.CharField(source='centro_origen.nombre', read_only=True, allow_null=True)
    centro_destino_nombre = serializers.CharField(source='centro_destino.nombre', read_only=True, allow_null=True)
    centro_nombre = serializers.SerializerMethodField()  # Alias unificado para frontend
    usuario_nombre = serializers.SerializerMethodField()
    observaciones = serializers.CharField(source='motivo', read_only=True, allow_null=True)  # Alias para lectura frontend
    requisicion_folio = serializers.CharField(source='requisicion.numero', read_only=True, allow_null=True)  # Folio de requisición
    fecha_movimiento = serializers.DateTimeField(source='fecha', read_only=True)  # Alias para frontend
    # MEJORA FLUJO 5: Nuevos campos para trazabilidad de pacientes
    subtipo_salida = serializers.CharField(required=False, allow_null=True, allow_blank=True, max_length=30)
    numero_expediente = serializers.CharField(required=False, allow_null=True, allow_blank=True, max_length=50)
    # FORMATO OFICIAL B: Folio/número de documento de entrada/salida
    folio_documento = serializers.CharField(required=False, allow_null=True, allow_blank=True, max_length=100)
    # Fecha de salida física (puede diferir de la fecha de registro en el sistema)
    fecha_salida = serializers.DateTimeField(required=False, allow_null=True)
    
    # ========== FIX: Campos para escritura desde frontend ==========
    # El frontend envía 'centro' y 'observaciones', pero el modelo tiene 'centro_destino' y 'motivo'
    # Usamos to_internal_value para mapear estos campos correctamente
    
    class Meta:
        model = Movimiento
        fields = [
            'id', 'tipo', 'producto', 'producto_nombre', 'producto_clave', 'producto_descripcion',
            'lote', 'lote_numero', 'numero_lote', 'lote_codigo',
            'centro_origen', 'centro_origen_nombre', 'centro_destino', 'centro_destino_nombre', 'centro_nombre',
            'cantidad', 'usuario', 'usuario_nombre', 'requisicion', 'requisicion_folio',
            'motivo', 'observaciones', 'referencia', 'subtipo_salida', 'numero_expediente', 'folio_documento',
            'fecha_salida', 'fecha', 'fecha_movimiento', 'created_at'
        ]
        read_only_fields = ['fecha', 'created_at']
        extra_kwargs = {
            'motivo': {'required': True, 'allow_null': False, 'allow_blank': False},  # ISS-FIX: Observaciones obligatorias
            'referencia': {'required': False, 'allow_null': True, 'allow_blank': True},
            'folio_documento': {'required': False, 'allow_null': True, 'allow_blank': True},
            'lote': {'required': False, 'allow_null': True},
            'centro_origen': {'required': False, 'allow_null': True},
            'centro_destino': {'required': False, 'allow_null': True},
            'requisicion': {'required': False, 'allow_null': True},
            'usuario': {'required': False, 'allow_null': True},
        }
    
    def to_internal_value(self, data):
        """
        FIX: Mapear campos del frontend a campos del modelo.
        - 'centro' -> se guarda en validated_data['centro'] para que ViewSet lo use
        - 'observaciones' -> se mapea a 'motivo' para el modelo
        - ISS-MEDICO FIX v2: Inferir 'producto' del 'lote' si no se envía
        """
        from .models import Lote
        data = data.copy() if hasattr(data, 'copy') else dict(data)
        
        # Mapear 'observaciones' del frontend a 'motivo' del modelo
        if 'observaciones' in data and 'motivo' not in data:
            data['motivo'] = data.pop('observaciones')
        
        # ISS-MEDICO FIX v2: Si no viene 'producto' pero viene 'lote', inferir producto del lote
        if 'producto' not in data and 'lote' in data:
            try:
                lote = Lote.objects.select_related('producto').get(pk=data['lote'])
                data['producto'] = lote.producto_id
            except Lote.DoesNotExist:
                pass  # Se manejará en la validación normal
        
        result = super().to_internal_value(data)
        
        # Preservar 'centro' para que ViewSet lo pueda usar (no es un campo del modelo directamente)
        # El ViewSet usa este valor para la función registrar_movimiento_stock
        if 'centro' in data:
            result['centro'] = data['centro']
        
        return result
    
    def get_producto_nombre(self, obj):
        if obj.producto:
            return obj.producto.nombre
        if obj.lote and obj.lote.producto:
            return obj.lote.producto.nombre
        return None
    
    def get_usuario_nombre(self, obj):
        if obj.usuario:
            return obj.usuario.get_full_name() or obj.usuario.username
        return None
    
    def get_centro_nombre(self, obj):
        """
        Retorna el nombre del centro relevante según el tipo de movimiento:
        - ENTRADA: centro donde ENTRA la mercancía (centro_destino o lote.centro)
        - SALIDA: centro de donde SALE la mercancía (centro_origen o lote.centro)
        
        ISS-FIX: Para requisiciones, las entradas deben mostrar el centro destino
        y las salidas deben mostrar el origen (Almacén Central).
        """
        tipo = (obj.tipo or '').lower()
        
        if tipo == 'entrada':
            # Para entradas: mostrar dónde ENTRA (centro_destino o lote.centro)
            if obj.centro_destino:
                return obj.centro_destino.nombre
            if obj.lote and obj.lote.centro:
                return obj.lote.centro.nombre
            return 'Almacén Central'
        elif tipo == 'salida':
            # Para salidas: mostrar de dónde SALE (centro_origen o lote.centro original)
            if obj.centro_origen:
                return obj.centro_origen.nombre
            # Si el lote es de farmacia central (centro=null), mostrar "Almacén Central"
            if obj.lote:
                if obj.lote.centro:
                    return obj.lote.centro.nombre
                return 'Almacén Central'
            return 'Almacén Central'
        else:
            # Otros tipos (ajuste): usar cualquier centro disponible
            if obj.centro_destino:
                return obj.centro_destino.nombre
            if obj.centro_origen:
                return obj.centro_origen.nombre
            if obj.lote and obj.lote.centro:
                return obj.lote.centro.nombre
            return 'Almacén Central'
    
    def validate_subtipo_salida(self, value):
        """Validar que el subtipo de salida sea válido."""
        if value and value.lower() not in SUBTIPOS_SALIDA_VALIDOS:
            raise serializers.ValidationError(
                f'Subtipo de salida inválido. Valores permitidos: {", ".join(SUBTIPOS_SALIDA_VALIDOS)}'
            )
        return value.lower() if value else None
    
    def validate(self, data):
        """
        MEJORA FLUJO 5: Si el tipo es 'salida' y subtipo_salida es 'receta',
        el numero_expediente es obligatorio para trazabilidad médica.
        """
        tipo = (data.get('tipo') or '').lower()
        subtipo = (data.get('subtipo_salida') or '').lower()
        expediente = (data.get('numero_expediente') or '').strip()
        
        if tipo == 'salida' and subtipo == 'receta':
            if not expediente:
                raise serializers.ValidationError({
                    'numero_expediente': 'El número de expediente es obligatorio para salidas por receta médica.'
                })
            # Validar formato básico del expediente (alfanumérico, mínimo 3 caracteres)
            if len(expediente) < 3:
                raise serializers.ValidationError({
                    'numero_expediente': 'El número de expediente debe tener al menos 3 caracteres.'
                })
        else:
            # ISS-DB-003: Si no es receta, asegurar que numero_expediente sea NULL, no ""
            if 'numero_expediente' in data and not data['numero_expediente']:
                data['numero_expediente'] = None
        
        # ISS-DB-003: Limpiar subtipo_salida vacío
        if 'subtipo_salida' in data and not data['subtipo_salida']:
            data['subtipo_salida'] = None
        
        # MOV-FECHA: Validar que fecha_salida no sea futura
        fecha_salida = data.get('fecha_salida')
        if fecha_salida:
            from django.utils import timezone as tz
            ahora = tz.now()
            if fecha_salida > ahora:
                raise serializers.ValidationError({
                    'fecha_salida': 'La fecha de salida no puede ser una fecha futura.'
                })
        
        return data


# =============================================================================
# NOTIFICACION SERIALIZER
# =============================================================================

class NotificacionSerializer(serializers.ModelSerializer):
    fecha_creacion = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = Notificacion
        fields = ['id', 'titulo', 'mensaje', 'tipo', 'leida', 'fecha_creacion', 'url', 'datos']
        read_only_fields = ['fecha_creacion']


# =============================================================================
# AUDITORIA LOG SERIALIZER - Panel SUPER ADMIN
# =============================================================================

class AuditoriaLogSerializer(serializers.ModelSerializer):
    """
    Serializer para logs de auditoría.
    Incluye campos extendidos para Panel SUPER ADMIN.
    """
    usuario_nombre = serializers.SerializerMethodField()
    usuario_username = serializers.CharField(source='usuario.username', read_only=True, default=None)
    centro_nombre = serializers.CharField(source='centro.nombre', read_only=True, default=None)
    fecha = serializers.DateTimeField(source='timestamp', read_only=True)
    
    class Meta:
        model = AuditoriaLogs
        fields = [
            'id', 
            'usuario', 'usuario_nombre', 'usuario_username',
            'rol_usuario',
            'centro', 'centro_nombre',
            'accion', 'modelo', 'objeto_id',
            'resultado', 'status_code', 'metodo_http',
            'endpoint', 'request_id', 'idempotency_key',
            'ip_address', 'user_agent', 
            'datos_anteriores', 'datos_nuevos', 'detalles', 
            'fecha'
        ]
        read_only_fields = fields
    
    def get_usuario_nombre(self, obj):
        if obj.usuario:
            nombre = obj.usuario.get_full_name()
            return nombre if nombre.strip() else obj.usuario.username
        return 'Sistema'


class AuditoriaLogDetalleSerializer(AuditoriaLogSerializer):
    """
    Serializer detallado para vista de evento individual.
    Incluye datos before/after completos.
    """
    cambios_resumen = serializers.SerializerMethodField()
    
    class Meta(AuditoriaLogSerializer.Meta):
        fields = AuditoriaLogSerializer.Meta.fields + ['cambios_resumen']
    
    def get_cambios_resumen(self, obj):
        """Genera un resumen de los cambios realizados."""
        if not obj.datos_anteriores and not obj.datos_nuevos:
            return None
        
        cambios = []
        antes = obj.datos_anteriores or {}
        despues = obj.datos_nuevos or {}
        
        # Encontrar campos modificados
        todos_campos = set(antes.keys()) | set(despues.keys())
        
        for campo in todos_campos:
            valor_antes = antes.get(campo)
            valor_despues = despues.get(campo)
            
            if valor_antes != valor_despues:
                cambios.append({
                    'campo': campo,
                    'antes': valor_antes,
                    'despues': valor_despues,
                })
        
        return cambios if cambios else None


# =============================================================================
# IMPORTACION LOG SERIALIZER
# =============================================================================

class ImportacionLogSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source='usuario.username', read_only=True, default=None)
    
    class Meta:
        model = ImportacionLogs
        fields = [
            'id', 'archivo', 'tipo_importacion', 'registros_totales',
            'registros_exitosos', 'registros_fallidos', 'estado',
            'errores', 'fecha_inicio', 'fecha_fin', 'usuario_nombre'
        ]
        read_only_fields = fields


# =============================================================================
# USER ME SERIALIZER
# =============================================================================

class UserMeSerializer(serializers.ModelSerializer):
    # ISS-PERMS FIX: Serializar centro como objeto {id, nombre} para que el frontend lo lea correctamente
    centro = CentroNestedSerializer(read_only=True)
    centro_nombre = serializers.CharField(source='centro.nombre', read_only=True, default='')
    permisos = serializers.SerializerMethodField()
    telefono = serializers.SerializerMethodField()
    # ISS-PERMS FIX: Incluir rol_efectivo para que el frontend sepa el rol real
    rol_efectivo = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'rol', 'rol_efectivo', 'centro', 'centro_nombre', 'adscripcion', 'permisos',
            'is_superuser', 'is_staff', 'telefono',
        ]
        read_only_fields = ['username', 'rol', 'centro', 'is_superuser', 'is_staff']

    def get_permisos(self, obj):
        return build_perm_map(obj)
    
    def get_rol_efectivo(self, obj):
        """ISS-PERMS FIX: Devuelve el rol real usado para permisos (inferido si campo vacío)"""
        return _resolve_rol(obj)

    def get_telefono(self, obj):
        """Obtener teléfono desde UserProfile si existe."""
        profile = getattr(obj, 'profile', None)
        return profile.telefono if profile else None

    def update(self, instance, validated_data):
        # ISS-SEC: Solo administradores pueden modificar información del perfil
        # Usuarios de FARMACIA y CENTRO no pueden cambiar ningún dato para evitar malas prácticas
        rol_usuario = _resolve_rol(instance)
        es_admin = rol_usuario == 'ADMIN'
        
        # Campos restringidos para usuarios no-ADMIN
        campos_restringidos = ['email', 'first_name', 'last_name']
        
        if not es_admin:
            # Silenciosamente ignorar cambios para usuarios no-ADMIN
            from django.utils import timezone
            import logging
            logger = logging.getLogger(__name__)
            
            for campo in campos_restringidos:
                if campo in validated_data:
                    logger.warning(
                        f"[ISS-SEC] Usuario {instance.username} (rol={rol_usuario}) intentó modificar {campo}. "
                        f"Ignorando cambio. Timestamp: {timezone.now()}"
                    )
                    del validated_data[campo]
        
        # Extraer telefono de los datos (viene en request.data pero no en validated_data)
        telefono = self.initial_data.get('telefono')
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Actualizar teléfono en UserProfile si se proporcionó (solo si es admin)
        if telefono is not None and es_admin:
            profile = getattr(instance, 'profile', None)
            if profile:
                profile.telefono = telefono
                profile.save(update_fields=['telefono', 'updated_at'])
        elif telefono is not None and not es_admin:
            from django.utils import timezone
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"[ISS-SEC] Usuario {instance.username} (rol={rol_usuario}) intentó modificar telefono. "
                f"Ignorando cambio. Timestamp: {timezone.now()}"
            )
        
        return instance


# =============================================================================
# CONFIGURACION SISTEMA SERIALIZER
# =============================================================================

class ConfiguracionSistemaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionSistema
        fields = ['id', 'clave', 'valor', 'descripcion', 'tipo', 'es_publica', 'updated_at']
        read_only_fields = ['updated_at']
        extra_kwargs = {
            'tipo': {'required': False, 'default': 'string'},
            'es_publica': {'required': False, 'default': False},
            'descripcion': {'required': False, 'allow_null': True, 'allow_blank': True},
        }


# =============================================================================
# TEMA GLOBAL SERIALIZER
# =============================================================================

class TemaGlobalSerializer(serializers.ModelSerializer):
    """
    Serializer para TemaGlobal - Configuración del tema visual.
    Todos los campos de color son opcionales con defaults en BD.
    """
    css_variables = serializers.SerializerMethodField()
    
    class Meta:
        model = TemaGlobal
        fields = [
            'id', 'nombre', 'es_activo', 
            'logo_url', 'logo_width', 'logo_height', 'favicon_url',
            'titulo_sistema', 'subtitulo_sistema',
            'color_primario', 'color_primario_hover',
            'color_secundario', 'color_secundario_hover',
            'color_exito', 'color_exito_hover',
            'color_alerta', 'color_alerta_hover',
            'color_error', 'color_error_hover',
            'color_info', 'color_info_hover',
            'color_fondo_principal', 'color_fondo_sidebar', 'color_fondo_header',
            'color_texto_principal', 'color_texto_sidebar', 'color_texto_header',
            'color_texto_links', 'color_borde_inputs', 'color_borde_focus',
            'reporte_color_encabezado', 'reporte_color_texto',
            # Campos adicionales de la BD
            'reporte_color_filas_alternas', 'reporte_pie_pagina', 'reporte_ano_visible',
            'fuente_principal', 'fuente_titulos',
            'css_variables', 'created_at', 'updated_at'
        ]
        read_only_fields = ['css_variables', 'created_at', 'updated_at']
        extra_kwargs = {
            'es_activo': {'required': False, 'default': False},
            'logo_url': {'required': False, 'allow_null': True, 'allow_blank': True},
            'logo_width': {'required': False, 'default': 160},
            'logo_height': {'required': False, 'default': 60},
            'favicon_url': {'required': False, 'allow_null': True, 'allow_blank': True},
            'titulo_sistema': {'required': False, 'allow_null': True},
            'subtitulo_sistema': {'required': False, 'allow_null': True},
            # Nuevos campos
            'reporte_color_filas_alternas': {'required': False, 'allow_null': True},
            'reporte_pie_pagina': {'required': False, 'allow_null': True, 'allow_blank': True},
            'reporte_ano_visible': {'required': False, 'allow_null': True},
            'fuente_principal': {'required': False, 'allow_null': True},
            'fuente_titulos': {'required': False, 'allow_null': True},
        }

    def get_css_variables(self, obj):
        """Genera las variables CSS para el frontend."""
        return {
            '--color-primary': obj.color_primario or '#9F2241',
            '--color-primary-hover': obj.color_primario_hover or '#6B1839',
            '--color-primary-light': f'rgba({self._hex_to_rgb(obj.color_primario or "#9F2241")}, 0.2)',
            '--color-secondary': obj.color_secundario or '#424242',
            '--color-success': obj.color_exito or '#4CAF50',
            '--color-warning': obj.color_alerta or '#FF9800',
            '--color-error': obj.color_error or '#F44336',
            '--color-info': obj.color_info or '#2196F3',
            '--color-background': obj.color_fondo_principal or '#F5F5F5',
            '--color-sidebar-bg': obj.color_fondo_sidebar or '#9F2241',
            '--color-header-bg': obj.color_fondo_header or '#9F2241',
            '--color-text': obj.color_texto_principal or '#212121',
            '--color-text-secondary': obj.color_texto_principal or '#757575',
            '--color-sidebar-text': obj.color_texto_sidebar or '#FFFFFF',
            '--color-header-text': obj.color_texto_header or '#FFFFFF',
            '--color-border': obj.color_borde_inputs or '#E0E0E0',
            '--font-family-principal': "'Montserrat', sans-serif",
        }

    def _hex_to_rgb(self, hex_color):
        """Convierte color hex a RGB para rgba()."""
        try:
            hex_color = hex_color.lstrip('#')
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return f'{r}, {g}, {b}'
        except Exception:
            return '159, 34, 65'


class TemaGlobalPublicoSerializer(serializers.ModelSerializer):
    """
    Serializer público para TemaGlobal - Solo campos necesarios para el frontend.
    Usado en endpoints públicos como login.
    """
    css_variables = serializers.SerializerMethodField()
    
    class Meta:
        model = TemaGlobal
        fields = [
            'id', 'nombre', 'logo_url', 'logo_width', 'logo_height', 'favicon_url',
            'titulo_sistema', 'subtitulo_sistema',
            'color_primario', 'color_primario_hover',
            'color_secundario', 'color_secundario_hover',
            'color_exito', 'color_alerta', 'color_error', 'color_info',
            'color_fondo_principal', 'color_fondo_sidebar', 'color_fondo_header',
            'color_texto_principal', 'color_texto_sidebar', 'color_texto_header',
            'color_texto_links', 'color_borde_inputs', 'color_borde_focus',
            'css_variables', 'updated_at',
        ]
        read_only_fields = fields

    def get_css_variables(self, obj):
        """Genera las variables CSS para el frontend."""
        return {
            '--color-primary': obj.color_primario or '#9F2241',
            '--color-primary-hover': obj.color_primario_hover or '#6B1839',
            '--color-primary-light': f'rgba({self._hex_to_rgb(obj.color_primario or "#9F2241")}, 0.2)',
            '--color-secondary': obj.color_secundario or '#424242',
            '--color-success': obj.color_exito or '#4CAF50',
            '--color-warning': obj.color_alerta or '#FF9800',
            '--color-error': obj.color_error or '#F44336',
            '--color-info': obj.color_info or '#2196F3',
            '--color-background': obj.color_fondo_principal or '#F5F5F5',
            '--color-sidebar-bg': obj.color_fondo_sidebar or '#9F2241',
            '--color-header-bg': obj.color_fondo_header or '#9F2241',
            '--color-text': obj.color_texto_principal or '#212121',
            '--color-text-secondary': obj.color_texto_principal or '#757575',
            '--color-sidebar-text': obj.color_texto_sidebar or '#FFFFFF',
            '--color-header-text': obj.color_texto_header or '#FFFFFF',
            '--color-border': obj.color_borde_inputs or '#E0E0E0',
            '--font-family-principal': "'Montserrat', sans-serif",
        }

    def _hex_to_rgb(self, hex_color):
        """Convierte color hex a RGB para rgba()."""
        try:
            hex_color = hex_color.lstrip('#')
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return f'{r}, {g}, {b}'
        except Exception:
            return '159, 34, 65'


# =============================================================================
# HOJA RECOLECCION SERIALIZER
# =============================================================================

class DetalleHojaRecoleccionSerializer(serializers.ModelSerializer):
    """
    Serializer para DetalleHojaRecoleccion.
    ISS-FIX: Actualizado para usar campos reales del modelo según crear_bd_desarrollo.sql:
    hoja_recoleccion_id, requisicion_id, orden, recolectado, fecha_recoleccion, notas
    """
    requisicion_folio = serializers.CharField(source='requisicion.folio', read_only=True, allow_null=True)
    
    class Meta:
        model = DetalleHojaRecoleccion
        fields = [
            'id', 'hoja', 'requisicion', 'requisicion_folio',
            'orden', 'recolectado', 'fecha_recoleccion',
            'notas', 'created_at'
        ]
        read_only_fields = ['created_at']
        extra_kwargs = {
            'orden': {'required': False, 'default': 0},
            'recolectado': {'required': False, 'default': False},
            'notas': {'required': False, 'allow_null': True, 'allow_blank': True},
            'fecha_recoleccion': {'required': False, 'allow_null': True},
        }


class HojaRecoleccionSerializer(serializers.ModelSerializer):
    """
    Serializer para HojaRecoleccion.
    """
    detalles = DetalleHojaRecoleccionSerializer(many=True, required=False)
    centro_nombre = serializers.CharField(source='centro.nombre', read_only=True, allow_null=True)
    responsable_nombre = serializers.SerializerMethodField()
    
    class Meta:
        model = HojaRecoleccion
        fields = [
            'id', 'numero', 'centro', 'centro_nombre', 
            'responsable', 'responsable_nombre',
            'estado', 'fecha_programada', 'fecha_recoleccion',
            'notas', 'detalles', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'estado': {'required': False, 'default': 'pendiente'},
            'notas': {'required': False, 'allow_null': True, 'allow_blank': True},
            'centro': {'required': False, 'allow_null': True},
            'responsable': {'required': False, 'allow_null': True},
            'fecha_recoleccion': {'required': False, 'allow_null': True},
        }
    
    def get_responsable_nombre(self, obj):
        if obj.responsable:
            return obj.responsable.get_full_name() or obj.responsable.username
        return None


# =============================================================================
# USER PROFILE SERIALIZER
# =============================================================================

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer para UserProfile - Perfil de usuario adicional.
    """
    usuario_username = serializers.CharField(source='usuario.username', read_only=True)
    centro_nombre = serializers.CharField(source='centro.nombre', read_only=True, allow_null=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'usuario', 'usuario_username', 'rol', 'telefono',
            'centro', 'centro_nombre', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'rol': {'required': False, 'default': 'visualizador'},
            'telefono': {'required': False, 'allow_null': True, 'allow_blank': True},
            'centro': {'required': False, 'allow_null': True},
        }


# =============================================================================
# PRODUCTO IMAGEN SERIALIZER
# =============================================================================

class ProductoImagenSerializer(serializers.ModelSerializer):
    """
    Serializer para imagenes de productos.
    Permite gestionar galeria de fotos por producto.
    """
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    
    class Meta:
        model = ProductoImagen
        fields = [
            'id', 'producto', 'producto_nombre', 'imagen', 
            'es_principal', 'orden', 'descripcion', 'created_at'
        ]
        read_only_fields = ['created_at']
        extra_kwargs = {
            'es_principal': {'required': False, 'default': False},
            'orden': {'required': False, 'default': 0},
            'descripcion': {'required': False, 'allow_null': True, 'allow_blank': True},
        }


# =============================================================================
# LOTE DOCUMENTO SERIALIZER
# =============================================================================

class LoteDocumentoSerializer(serializers.ModelSerializer):
    """
    Serializer para documentos de lotes (facturas, contratos).
    """
    lote_numero = serializers.CharField(source='lote.numero_lote', read_only=True)
    producto_nombre = serializers.CharField(source='lote.producto.nombre', read_only=True)
    created_by_nombre = serializers.SerializerMethodField()
    tipo_documento_display = serializers.CharField(source='get_tipo_documento_display', read_only=True)
    
    class Meta:
        model = LoteDocumento
        fields = [
            'id', 'lote', 'lote_numero', 'producto_nombre',
            'tipo_documento', 'tipo_documento_display', 'numero_documento',
            'archivo', 'nombre_archivo', 'fecha_documento', 'notas',
            'created_at', 'created_by', 'created_by_nombre'
        ]
        read_only_fields = ['created_at']
        extra_kwargs = {
            'tipo_documento': {'required': True},
            'archivo': {'required': True},
            'numero_documento': {'required': False, 'allow_null': True, 'allow_blank': True},
            'nombre_archivo': {'required': False, 'allow_null': True, 'allow_blank': True},
            'fecha_documento': {'required': False, 'allow_null': True},
            'notas': {'required': False, 'allow_null': True, 'allow_blank': True},
            'created_by': {'required': False, 'allow_null': True},
        }
    
    def get_created_by_nombre(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None
    
    def validate_tipo_documento(self, value):
        """Validar que el tipo de documento sea valido."""
        tipos_validos = ['factura', 'contrato', 'remision', 'otro']
        if value not in tipos_validos:
            raise serializers.ValidationError(
                f"Tipo de documento invalido. Valores permitidos: {', '.join(tipos_validos)}"
            )
        return value


# =============================================================================
# DONACION SERIALIZERS (ALMACEN SEPARADO - NO AFECTA INVENTARIO PRINCIPAL)
# =============================================================================

class ProductoDonacionSerializer(serializers.ModelSerializer):
    """
    Serializer para el catálogo independiente de productos de donaciones.
    Este catálogo es COMPLETAMENTE SEPARADO del catálogo principal de productos.
    """
    class Meta:
        model = ProductoDonacion
        fields = [
            'id', 'clave', 'nombre', 'descripcion', 'unidad_medida',
            'presentacion', 'activo', 'notas', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'clave': {'required': True},
            'nombre': {'required': True},
            'descripcion': {'required': False, 'allow_null': True, 'allow_blank': True},
            'unidad_medida': {'required': False, 'default': 'PIEZA'},
            'presentacion': {'required': False, 'allow_null': True, 'allow_blank': True},
            'activo': {'required': False, 'default': True},
            'notas': {'required': False, 'allow_null': True, 'allow_blank': True},
        }
    
    def validate_clave(self, value):
        """Validar que la clave sea única (case insensitive)"""
        clave_upper = value.upper().strip()
        qs = ProductoDonacion.objects.filter(clave__iexact=clave_upper)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe un producto de donación con esta clave.")
        return clave_upper


class DetalleDonacionSerializer(serializers.ModelSerializer):
    """
    Serializer para detalle de donaciones - ALMACEN COMPLETAMENTE SEPARADO.
    Usa el catálogo independiente de ProductoDonacion.
    Las donaciones no afectan el inventario principal ni generan movimientos auditados.
    """
    # Campos del nuevo catálogo de donaciones
    producto_donacion_nombre = serializers.CharField(source='producto_donacion.nombre', read_only=True)
    producto_donacion_codigo = serializers.CharField(source='producto_donacion.clave', read_only=True)
    # Campos legacy (compatibilidad con datos antiguos)
    producto_nombre = serializers.SerializerMethodField()
    producto_codigo = serializers.SerializerMethodField()
    estado_producto_display = serializers.CharField(source='get_estado_producto_display', read_only=True)
    donacion_numero = serializers.CharField(source='donacion.numero', read_only=True)
    
    class Meta:
        model = DetalleDonacion
        fields = [
            'id', 'donacion', 'donacion_numero',
            # Nuevo catálogo de donaciones (preferido)
            'producto_donacion', 'producto_donacion_nombre', 'producto_donacion_codigo',
            # Legacy (compatibilidad)
            'producto', 'producto_nombre', 'producto_codigo',
            'numero_lote', 'cantidad', 'cantidad_disponible',
            'fecha_caducidad', 'estado_producto', 'estado_producto_display',
            'notas', 'created_at'
        ]
        read_only_fields = ['created_at', 'cantidad_disponible']
        extra_kwargs = {
            'donacion': {'required': False},  # Se asigna al crear desde DonacionSerializer
            'producto_donacion': {'required': False, 'allow_null': True},  # Nuevo catálogo
            'producto': {'required': False, 'allow_null': True},  # Legacy, ahora opcional
            'cantidad': {'required': True},
            'numero_lote': {'required': True, 'allow_blank': False},  # Obligatorio para trazabilidad
            'fecha_caducidad': {'required': True},  # Obligatorio para control de inventario
            'estado_producto': {'required': False, 'default': 'bueno'},
            'notas': {'required': False, 'allow_null': True, 'allow_blank': True},
        }
    
    def get_producto_nombre(self, obj):
        """Retorna nombre del producto (donación o legacy)"""
        if obj.producto_donacion:
            return obj.producto_donacion.nombre
        elif obj.producto:
            return obj.producto.nombre
        return 'Sin producto'
    
    def get_producto_codigo(self, obj):
        """Retorna clave del producto (donación o legacy)"""
        if obj.producto_donacion:
            return obj.producto_donacion.clave
        elif obj.producto:
            return obj.producto.clave
        return ''
    
    def validate_cantidad(self, value):
        if value <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor a 0.")
        return value
    
    def validate(self, attrs):
        """Validar que se proporcione al menos un producto (donación o legacy)"""
        producto_donacion = attrs.get('producto_donacion')
        producto = attrs.get('producto')
        
        if not producto_donacion and not producto:
            raise serializers.ValidationError({
                'producto_donacion': 'Debe especificar un producto del catálogo de donaciones.'
            })
        return attrs


class DonacionSerializer(serializers.ModelSerializer):
    """
    Serializer para donaciones.
    """
    detalles = DetalleDonacionSerializer(many=True, required=False)
    centro_destino_nombre = serializers.CharField(source='centro_destino.nombre', read_only=True, allow_null=True)
    recibido_por_nombre = serializers.SerializerMethodField()
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    donante_tipo_display = serializers.CharField(source='get_donante_tipo_display', read_only=True)
    total_productos = serializers.SerializerMethodField()
    total_unidades = serializers.SerializerMethodField()
    folio = serializers.SerializerMethodField()
    
    class Meta:
        model = Donacion
        fields = [
            'id', 'numero', 'folio',
            'donante_nombre', 'donante_tipo', 'donante_tipo_display',
            'donante_rfc', 'donante_direccion', 'donante_contacto',
            'fecha_donacion', 'fecha_recepcion',
            'centro_destino', 'centro_destino_nombre',
            'recibido_por', 'recibido_por_nombre',
            'estado', 'estado_display', 'notas', 'documento_donacion',
            'detalles', 'total_productos', 'total_unidades',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['numero', 'folio', 'fecha_recepcion', 'created_at', 'updated_at']
        extra_kwargs = {
            'donante_nombre': {'required': True},
            'fecha_donacion': {'required': True},
            'donante_tipo': {'required': False, 'default': 'otro'},
            'donante_rfc': {'required': False, 'allow_null': True, 'allow_blank': True},
            'donante_direccion': {'required': False, 'allow_null': True, 'allow_blank': True},
            'donante_contacto': {'required': False, 'allow_null': True, 'allow_blank': True},
            'centro_destino': {'required': False, 'allow_null': True},
            'recibido_por': {'required': False, 'allow_null': True},
            'estado': {'required': False, 'default': 'pendiente'},
            'notas': {'required': False, 'allow_null': True, 'allow_blank': True},
            'documento_donacion': {'required': False, 'allow_null': True, 'allow_blank': True},
        }
    
    def get_recibido_por_nombre(self, obj):
        if obj.recibido_por:
            return obj.recibido_por.get_full_name() or obj.recibido_por.username
        return None
    
    def get_total_productos(self, obj):
        return obj.detalles.count()
    
    def get_total_unidades(self, obj):
        total = obj.detalles.aggregate(total=Sum('cantidad'))['total']
        return total or 0
    
    def get_folio(self, obj):
        return f"DON-{obj.numero}"
    
    def validate(self, data):
        """
        Validación personalizada: no se puede guardar una donación sin productos.
        """
        detalles = data.get('detalles', [])
        
        # En creación, los detalles deben existir
        if not self.instance and not detalles:
            raise serializers.ValidationError({
                'detalles': 'Debe agregar al menos un producto a la donación.'
            })
        
        return data
    
    def create(self, validated_data):
        detalles_data = validated_data.pop('detalles', [])
        
        # Validación adicional en creación
        if not detalles_data:
            raise serializers.ValidationError({
                'detalles': 'Debe agregar al menos un producto a la donación.'
            })
        
        # Generar numero automatico
        if 'numero' not in validated_data or not validated_data.get('numero'):
            import random
            validated_data['numero'] = f"{timezone.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        
        donacion = Donacion.objects.create(**validated_data)
        
        for detalle_data in detalles_data:
            DetalleDonacion.objects.create(donacion=donacion, **detalle_data)
        
        return donacion
    
    def update(self, instance, validated_data):
        detalles_data = validated_data.pop('detalles', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if detalles_data is not None:
            # Validar que no se quede sin productos (si se envían detalles vacíos)
            if len(detalles_data) == 0:
                raise serializers.ValidationError({
                    'detalles': 'No se puede actualizar una donación dejándola sin productos.'
                })
            
            # Eliminar detalles existentes y crear nuevos
            instance.detalles.all().delete()
            for detalle_data in detalles_data:
                DetalleDonacion.objects.create(donacion=instance, **detalle_data)
        
        return instance


class SalidaDonacionSerializer(serializers.ModelSerializer):
    """
    Serializer para salidas/entregas del almacen de donaciones.
    Control interno sin afectar movimientos principales.
    
    ISS-DB-ALIGN: Incluye campos de trazabilidad:
    - centro_destino: Centro penitenciario destino
    - finalizado: Si la entrega fue confirmada
    - fecha_finalizado: Timestamp de finalización
    - finalizado_por: Usuario que finalizó
    """
    detalle_donacion_info = serializers.SerializerMethodField()
    entregado_por_nombre = serializers.SerializerMethodField()
    producto_nombre = serializers.SerializerMethodField()
    producto_clave = serializers.SerializerMethodField()
    numero_lote = serializers.SerializerMethodField()
    centro_destino_nombre = serializers.CharField(source='centro_destino.nombre', read_only=True, allow_null=True)
    finalizado_por_nombre = serializers.SerializerMethodField()
    estado_entrega = serializers.CharField(read_only=True)  # Property del modelo
    
    class Meta:
        model = SalidaDonacion
        fields = [
            'id', 'detalle_donacion', 'detalle_donacion_info',
            'cantidad', 'destinatario', 'motivo',
            'entregado_por', 'entregado_por_nombre',
            'producto_nombre', 'producto_clave', 'numero_lote',
            'fecha_entrega', 'notas', 'created_at',
            # ISS-DB-ALIGN: Campos de trazabilidad
            'centro_destino', 'centro_destino_nombre',
            'finalizado', 'fecha_finalizado',
            'finalizado_por', 'finalizado_por_nombre',
            'estado_entrega'
        ]
        read_only_fields = ['created_at', 'fecha_entrega', 'entregado_por', 'fecha_finalizado', 'finalizado_por']
        extra_kwargs = {
            'detalle_donacion': {'required': True},
            'cantidad': {'required': True},
            'destinatario': {'required': True},
            'motivo': {'required': False, 'allow_null': True, 'allow_blank': True},
            'notas': {'required': False, 'allow_null': True, 'allow_blank': True},
            'centro_destino': {'required': False, 'allow_null': True},
            'finalizado': {'required': False, 'default': False},
        }
    
    def get_detalle_donacion_info(self, obj):
        if obj.detalle_donacion:
            return {
                'id': obj.detalle_donacion.id,
                'donacion_numero': obj.detalle_donacion.donacion.numero,
                'cantidad_original': obj.detalle_donacion.cantidad,
                'cantidad_disponible': obj.detalle_donacion.cantidad_disponible,
            }
        return None
    
    def get_entregado_por_nombre(self, obj):
        if obj.entregado_por:
            return f"{obj.entregado_por.first_name} {obj.entregado_por.last_name}".strip() or obj.entregado_por.username
        return None
    
    def get_finalizado_por_nombre(self, obj):
        """ISS-DB-ALIGN: Nombre del usuario que finalizó la entrega"""
        if obj.finalizado_por:
            return f"{obj.finalizado_por.first_name} {obj.finalizado_por.last_name}".strip() or obj.finalizado_por.username
        return None
    
    def get_producto_nombre(self, obj):
        """Obtener nombre del producto desde detalle_donacion.
        DetalleDonacion tiene dos campos: producto_donacion (nuevo) y producto (legacy).
        """
        if obj.detalle_donacion:
            # Usar la property nombre_producto que maneja ambos casos
            return obj.detalle_donacion.nombre_producto
        return None
    
    def get_producto_clave(self, obj):
        """Obtener clave del producto desde detalle_donacion."""
        if obj.detalle_donacion:
            # Intentar producto_donacion primero, luego producto legacy
            if obj.detalle_donacion.producto_donacion:
                return obj.detalle_donacion.producto_donacion.clave
            elif obj.detalle_donacion.producto:
                return obj.detalle_donacion.producto.clave
        return None
    
    def get_numero_lote(self, obj):
        """Obtener número de lote desde detalle_donacion."""
        if obj.detalle_donacion and obj.detalle_donacion.numero_lote:
            return obj.detalle_donacion.numero_lote
        return None
    
    def validate_cantidad(self, value):
        if value <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor a 0.")
        return value
    
    def validate(self, attrs):
        detalle = attrs.get('detalle_donacion')
        cantidad = attrs.get('cantidad')
        
        if detalle and cantidad:
            if cantidad > detalle.cantidad_disponible:
                raise serializers.ValidationError({
                    'cantidad': f"Stock insuficiente. Disponible: {detalle.cantidad_disponible}"
                })
        
        return attrs
    
    def create(self, validated_data):
        # Asignar usuario actual
        request = self.context.get('request')
        if request and request.user:
            validated_data['entregado_por'] = request.user
        
        # NOTA: El descuento de stock lo hace el modelo SalidaDonacion.save()
        # No duplicar el descuento aquí
        
        return super().create(validated_data)


# =============================================================================
# MÓDULO DE DISPENSACIÓN A PACIENTES (FORMATO C)
# =============================================================================

from .models import Paciente, Dispensacion, DetalleDispensacion, HistorialDispensacion


class PacienteSerializer(serializers.ModelSerializer):
    """
    Serializer para el catálogo de Pacientes/Internos.
    """
    nombre_completo = serializers.CharField(read_only=True)
    edad = serializers.IntegerField(read_only=True)
    ubicacion_completa = serializers.CharField(read_only=True)
    centro_nombre = serializers.SerializerMethodField()
    created_by_nombre = serializers.SerializerMethodField()
    total_dispensaciones = serializers.SerializerMethodField()
    
    class Meta:
        model = Paciente
        fields = [
            'id', 'numero_expediente', 'nombre', 'apellido_paterno', 'apellido_materno',
            'nombre_completo', 'curp', 'fecha_nacimiento', 'edad', 'sexo',
            'centro', 'centro_nombre', 'dormitorio', 'celda', 'ubicacion_completa',
            'tipo_sangre', 'alergias', 'enfermedades_cronicas', 'observaciones_medicas',
            'activo', 'fecha_ingreso', 'fecha_egreso', 'motivo_egreso',
            'created_at', 'updated_at', 'created_by', 'created_by_nombre',
            'total_dispensaciones'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']
    
    def get_centro_nombre(self, obj):
        return obj.centro.nombre if obj.centro else None
    
    def get_created_by_nombre(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.username
        return None
    
    def get_total_dispensaciones(self, obj):
        return obj.dispensaciones.count()
    
    def validate_numero_expediente(self, value):
        """Validar que el número de expediente sea único"""
        instance = self.instance
        if Paciente.objects.exclude(pk=instance.pk if instance else None).filter(numero_expediente=value).exists():
            raise serializers.ValidationError("Ya existe un paciente con este número de expediente.")
        return value
    
    def validate_curp(self, value):
        """Validar formato de CURP si se proporciona"""
        if value:
            value = value.upper().strip()
            if len(value) != 18:
                raise serializers.ValidationError("El CURP debe tener 18 caracteres.")
            # Validación básica de formato CURP
            import re
            patron_curp = r'^[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d$'
            if not re.match(patron_curp, value):
                raise serializers.ValidationError("Formato de CURP inválido.")
        return value
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user:
            validated_data['created_by'] = request.user
        return super().create(validated_data)


class PacienteSimpleSerializer(serializers.ModelSerializer):
    """Serializer simplificado para selects y autocompletado"""
    nombre_completo = serializers.CharField(read_only=True)
    ubicacion_completa = serializers.CharField(read_only=True)
    
    class Meta:
        model = Paciente
        fields = ['id', 'numero_expediente', 'nombre_completo', 'ubicacion_completa', 'centro']


class DetalleDispensacionSerializer(serializers.ModelSerializer):
    """
    Serializer para detalles de dispensación.
    """
    producto_nombre = serializers.SerializerMethodField()
    producto_clave = serializers.SerializerMethodField()
    lote_numero = serializers.SerializerMethodField()
    lote_caducidad = serializers.SerializerMethodField()
    completo = serializers.BooleanField(read_only=True)
    producto_sustituto_nombre = serializers.SerializerMethodField()
    
    class Meta:
        model = DetalleDispensacion
        fields = [
            'id', 'dispensacion', 'producto', 'producto_nombre', 'producto_clave',
            'lote', 'lote_numero', 'lote_caducidad',
            'cantidad_prescrita', 'cantidad_dispensada', 'completo',
            'dosis', 'frecuencia', 'duracion_tratamiento', 'via_administracion', 'horarios',
            'estado', 'producto_sustituto', 'producto_sustituto_nombre', 'motivo_sustitucion',
            'notas', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_producto_nombre(self, obj):
        return obj.producto.nombre if obj.producto else None
    
    def get_producto_clave(self, obj):
        return obj.producto.clave if obj.producto else None
    
    def get_lote_numero(self, obj):
        return obj.lote.numero_lote if obj.lote else None
    
    def get_lote_caducidad(self, obj):
        return obj.lote.fecha_caducidad if obj.lote else None
    
    def get_producto_sustituto_nombre(self, obj):
        return obj.producto_sustituto.nombre if obj.producto_sustituto else None
    
    def validate_cantidad_prescrita(self, value):
        if value <= 0:
            raise serializers.ValidationError("La cantidad prescrita debe ser mayor a 0.")
        return value
    
    def validate_cantidad_dispensada(self, value):
        if value < 0:
            raise serializers.ValidationError("La cantidad dispensada no puede ser negativa.")
        return value


class DispensacionSerializer(serializers.ModelSerializer):
    """
    Serializer principal para Dispensaciones.
    """
    paciente_nombre = serializers.SerializerMethodField()
    paciente_expediente = serializers.SerializerMethodField()
    paciente_ubicacion = serializers.SerializerMethodField()
    centro_nombre = serializers.SerializerMethodField()
    dispensado_por_nombre = serializers.SerializerMethodField()
    autorizado_por_nombre = serializers.SerializerMethodField()
    created_by_nombre = serializers.SerializerMethodField()
    detalles = DetalleDispensacionSerializer(many=True, read_only=True)
    total_items = serializers.SerializerMethodField()
    total_dispensado = serializers.SerializerMethodField()
    total_prescrito = serializers.SerializerMethodField()
    porcentaje_completado = serializers.FloatField(read_only=True)
    tipo_dispensacion_display = serializers.SerializerMethodField()
    estado_display = serializers.SerializerMethodField()
    # Validación: médico prescriptor es obligatorio
    medico_prescriptor = serializers.CharField(required=True, allow_blank=False, max_length=200)
    
    class Meta:
        model = Dispensacion
        fields = [
            'id', 'folio', 'paciente', 'paciente_nombre', 'paciente_expediente', 'paciente_ubicacion',
            'centro', 'centro_nombre', 'fecha_dispensacion',
            'tipo_dispensacion', 'tipo_dispensacion_display',
            'diagnostico', 'indicaciones', 'medico_prescriptor', 'cedula_medico',
            'estado', 'estado_display',
            'dispensado_por', 'dispensado_por_nombre',
            'autorizado_por', 'autorizado_por_nombre',
            'firma_paciente', 'firma_dispensador',
            'observaciones', 'motivo_cancelacion',
            'created_at', 'updated_at', 'created_by', 'created_by_nombre',
            'detalles', 'total_items', 'total_dispensado', 'total_prescrito', 'porcentaje_completado'
        ]
        read_only_fields = ['id', 'folio', 'created_at', 'updated_at', 'created_by', 'fecha_dispensacion']
    
    def get_paciente_nombre(self, obj):
        return obj.paciente.nombre_completo if obj.paciente else None
    
    def get_paciente_expediente(self, obj):
        return obj.paciente.numero_expediente if obj.paciente else None
    
    def get_paciente_ubicacion(self, obj):
        return obj.paciente.ubicacion_completa if obj.paciente else None
    
    def get_centro_nombre(self, obj):
        return obj.centro.nombre if obj.centro else None
    
    def get_dispensado_por_nombre(self, obj):
        if obj.dispensado_por:
            return f"{obj.dispensado_por.first_name} {obj.dispensado_por.last_name}".strip() or obj.dispensado_por.username
        return None
    
    def get_autorizado_por_nombre(self, obj):
        if obj.autorizado_por:
            return f"{obj.autorizado_por.first_name} {obj.autorizado_por.last_name}".strip() or obj.autorizado_por.username
        return None
    
    def get_created_by_nombre(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.username
        return None
    
    def get_total_items(self, obj):
        return obj.get_total_items()
    
    def get_total_dispensado(self, obj):
        return obj.get_total_dispensado()
    
    def get_total_prescrito(self, obj):
        return obj.get_total_prescrito()
    
    def get_tipo_dispensacion_display(self, obj):
        return obj.get_tipo_dispensacion_display()
    
    def get_estado_display(self, obj):
        return obj.get_estado_display()
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user:
            validated_data['created_by'] = request.user
            # Asignar centro del usuario si no se especifica
            if not validated_data.get('centro') and request.user.centro:
                validated_data['centro'] = request.user.centro
        return super().create(validated_data)


class DispensacionListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listados de dispensaciones"""
    paciente_nombre = serializers.SerializerMethodField()
    paciente_expediente = serializers.SerializerMethodField()
    centro_nombre = serializers.SerializerMethodField()
    created_by_nombre = serializers.SerializerMethodField()
    total_items = serializers.SerializerMethodField()
    tipo_dispensacion_display = serializers.SerializerMethodField()
    estado_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Dispensacion
        fields = [
            'id', 'folio', 'paciente', 'paciente_nombre', 'paciente_expediente',
            'centro', 'centro_nombre', 'fecha_dispensacion',
            'tipo_dispensacion', 'tipo_dispensacion_display',
            'estado', 'estado_display', 'total_items',
            'created_by', 'created_by_nombre'
        ]
    
    def get_paciente_nombre(self, obj):
        return obj.paciente.nombre_completo if obj.paciente else None
    
    def get_paciente_expediente(self, obj):
        return obj.paciente.numero_expediente if obj.paciente else None
    
    def get_centro_nombre(self, obj):
        return obj.centro.nombre if obj.centro else None
    
    def get_created_by_nombre(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.username
        return None
    
    def get_total_items(self, obj):
        return obj.get_total_items()
    
    def get_tipo_dispensacion_display(self, obj):
        return obj.get_tipo_dispensacion_display()
    
    def get_estado_display(self, obj):
        return obj.get_estado_display()


class HistorialDispensacionSerializer(serializers.ModelSerializer):
    """Serializer para historial de dispensaciones"""
    usuario_nombre = serializers.SerializerMethodField()
    accion_display = serializers.SerializerMethodField()
    
    class Meta:
        model = HistorialDispensacion
        fields = [
            'id', 'dispensacion', 'accion', 'accion_display',
            'estado_anterior', 'estado_nuevo',
            'usuario', 'usuario_nombre', 'detalles', 'ip_address', 'created_at'
        ]
    
    def get_usuario_nombre(self, obj):
        if obj.usuario:
            return f"{obj.usuario.first_name} {obj.usuario.last_name}".strip() or obj.usuario.username
        return None
    
    def get_accion_display(self, obj):
        return obj.get_accion_display()


# =====================================================
# SERIALIZERS: COMPRAS DE CAJA CHICA
# =====================================================

class DetalleCompraCajaChicaSerializer(serializers.ModelSerializer):
    """Serializer para detalles de compra de caja chica"""
    producto_nombre = serializers.SerializerMethodField()
    producto_clave = serializers.SerializerMethodField()
    
    class Meta:
        model = DetalleCompraCajaChica
        fields = [
            'id', 'compra', 'producto', 'producto_nombre', 'producto_clave',
            'descripcion_producto', 'cantidad_solicitada', 'cantidad_comprada',
            'cantidad_recibida', 'numero_lote', 'fecha_caducidad',
            'precio_unitario', 'importe', 'unidad_medida', 'notas', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'importe']
    
    def get_producto_nombre(self, obj):
        return obj.producto.nombre if obj.producto else None
    
    def get_producto_clave(self, obj):
        return obj.producto.clave if obj.producto else None
    
    def validate_cantidad_solicitada(self, value):
        if value <= 0:
            raise serializers.ValidationError("La cantidad solicitada debe ser mayor a 0")
        return value
    
    def validate_precio_unitario(self, value):
        if value < 0:
            raise serializers.ValidationError("El precio unitario no puede ser negativo")
        return value


class DetalleCompraCajaChicaWriteSerializer(serializers.Serializer):
    """Serializer para escribir detalles de compra (creación anidada)"""
    producto = serializers.IntegerField(required=False, allow_null=True)
    descripcion_producto = serializers.CharField(max_length=500)
    cantidad = serializers.IntegerField(min_value=1)
    unidad = serializers.CharField(max_length=50, required=False, allow_blank=True)
    precio_unitario = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    numero_lote = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    fecha_caducidad = serializers.DateField(required=False, allow_null=True)


class CompraCajaChicaSerializer(serializers.ModelSerializer):
    """
    Serializer principal para compras de caja chica.
    
    FLUJO CON VERIFICACIÓN DE FARMACIA:
    1. Centro crea solicitud con detalles
    2. Centro envía a Farmacia para verificar disponibilidad
    3. Farmacia confirma que NO tiene stock (o rechaza si tiene)
    4. Centro envía a Admin para autorización
    5. Admin autoriza y envía a Director
    6. Director autoriza
    7. Centro realiza compra
    8. Centro recibe productos
    """
    centro_nombre = serializers.SerializerMethodField()
    solicitante_nombre = serializers.SerializerMethodField()
    autorizado_por_nombre = serializers.SerializerMethodField()
    recibido_por_nombre = serializers.SerializerMethodField()
    # Campos para flujo farmacia
    verificado_por_farmacia_nombre = serializers.SerializerMethodField()
    # Campos para flujo multinivel
    administrador_centro_nombre = serializers.SerializerMethodField()
    director_centro_nombre = serializers.SerializerMethodField()
    rechazado_por_nombre = serializers.SerializerMethodField()
    detalles = DetalleCompraCajaChicaSerializer(many=True, read_only=True)
    detalles_write = DetalleCompraCajaChicaWriteSerializer(many=True, write_only=True, required=False)
    estado_display = serializers.SerializerMethodField()
    total_productos = serializers.SerializerMethodField()
    requisicion_origen_numero = serializers.SerializerMethodField()
    # Acciones disponibles según estado y rol
    acciones_disponibles = serializers.SerializerMethodField()
    
    class Meta:
        model = CompraCajaChica
        fields = [
            'id', 'folio', 'centro', 'centro_nombre',
            'requisicion_origen', 'requisicion_origen_numero',
            'proveedor_nombre', 'proveedor_rfc', 'proveedor_direccion', 'proveedor_telefono', 'proveedor_contacto',
            'fecha_solicitud', 'fecha_compra', 'fecha_recepcion',
            # Flujo farmacia: fechas y datos
            'fecha_envio_farmacia', 'fecha_respuesta_farmacia',
            'verificado_por_farmacia', 'verificado_por_farmacia_nombre',
            'respuesta_farmacia', 'stock_farmacia_verificado',
            # Flujo multinivel: fechas
            'fecha_envio_admin', 'fecha_autorizacion_admin',
            'fecha_envio_director', 'fecha_autorizacion_director',
            'numero_factura', 'documento_respaldo',
            'subtotal', 'iva', 'total',
            'motivo_compra', 'estado', 'estado_display',
            # Usuarios del flujo
            'solicitante', 'solicitante_nombre',
            'administrador_centro', 'administrador_centro_nombre',
            'director_centro', 'director_centro_nombre',
            'autorizado_por', 'autorizado_por_nombre',
            'recibido_por', 'recibido_por_nombre',
            'rechazado_por', 'rechazado_por_nombre',
            'observaciones', 'motivo_cancelacion', 'motivo_rechazo',
            'created_at', 'updated_at',
            'detalles', 'detalles_write', 'total_productos',
            'acciones_disponibles'
        ]
        read_only_fields = ['id', 'folio', 'subtotal', 'iva', 'total', 'created_at', 'updated_at']
    
    def get_centro_nombre(self, obj):
        return obj.centro.nombre if obj.centro else None
    
    def get_solicitante_nombre(self, obj):
        if obj.solicitante:
            return f"{obj.solicitante.first_name} {obj.solicitante.last_name}".strip() or obj.solicitante.username
        return None
    
    def get_verificado_por_farmacia_nombre(self, obj):
        if hasattr(obj, 'verificado_por_farmacia') and obj.verificado_por_farmacia:
            return f"{obj.verificado_por_farmacia.first_name} {obj.verificado_por_farmacia.last_name}".strip() or obj.verificado_por_farmacia.username
        return None
    
    def get_administrador_centro_nombre(self, obj):
        if hasattr(obj, 'administrador_centro') and obj.administrador_centro:
            return f"{obj.administrador_centro.first_name} {obj.administrador_centro.last_name}".strip() or obj.administrador_centro.username
        return None
    
    def get_director_centro_nombre(self, obj):
        if hasattr(obj, 'director_centro') and obj.director_centro:
            return f"{obj.director_centro.first_name} {obj.director_centro.last_name}".strip() or obj.director_centro.username
        return None
    
    def get_autorizado_por_nombre(self, obj):
        if obj.autorizado_por:
            return f"{obj.autorizado_por.first_name} {obj.autorizado_por.last_name}".strip() or obj.autorizado_por.username
        return None
    
    def get_recibido_por_nombre(self, obj):
        if obj.recibido_por:
            return f"{obj.recibido_por.first_name} {obj.recibido_por.last_name}".strip() or obj.recibido_por.username
        return None
    
    def get_rechazado_por_nombre(self, obj):
        if hasattr(obj, 'rechazado_por') and obj.rechazado_por:
            return f"{obj.rechazado_por.first_name} {obj.rechazado_por.last_name}".strip() or obj.rechazado_por.username
        return None
    
    def get_estado_display(self, obj):
        return obj.get_estado_display()
    
    def get_total_productos(self, obj):
        return obj.detalles.count()
    
    def get_requisicion_origen_numero(self, obj):
        return obj.requisicion_origen.numero if obj.requisicion_origen else None
    
    def get_acciones_disponibles(self, obj):
        """Retorna las acciones disponibles según estado actual y rol del usuario"""
        request = self.context.get('request')
        if not request or not request.user:
            return []
        
        user = request.user
        rol = getattr(user, 'rol', '').lower()
        acciones = []
        
        # Determinar acciones según rol y estado
        if obj.estado == 'pendiente':
            if rol in ['medico', 'centro', 'administrador_centro', 'director_centro']:
                acciones.extend(['editar', 'enviar_farmacia', 'cancelar'])
        elif obj.estado == 'enviada_farmacia':
            if rol in ['farmacia', 'admin_farmacia', 'superuser'] or user.is_superuser:
                acciones.extend(['confirmar_sin_stock', 'rechazar_tiene_stock'])
            if rol in ['medico', 'centro']:
                acciones.append('cancelar')
        elif obj.estado == 'sin_stock_farmacia':
            if rol in ['medico', 'centro', 'administrador_centro']:
                acciones.extend(['enviar_admin', 'cancelar'])
        elif obj.estado == 'rechazada_farmacia':
            if rol in ['medico', 'centro']:
                acciones.extend(['editar', 'cancelar'])
        elif obj.estado == 'enviada_admin':
            if rol in ['administrador_centro', 'admin']:
                acciones.extend(['autorizar_admin', 'rechazar', 'devolver'])
        elif obj.estado == 'autorizada_admin':
            if rol in ['administrador_centro', 'admin']:
                acciones.extend(['enviar_director', 'cancelar'])
        elif obj.estado == 'enviada_director':
            if rol in ['director_centro', 'director']:
                acciones.extend(['autorizar_director', 'rechazar', 'devolver'])
        elif obj.estado == 'autorizada':
            if rol in ['medico', 'centro', 'administrador_centro', 'director_centro']:
                acciones.extend(['registrar_compra', 'cancelar'])
        elif obj.estado == 'comprada':
            if rol in ['medico', 'centro', 'administrador_centro']:
                acciones.extend(['registrar_recepcion', 'cancelar'])
        elif obj.estado == 'rechazada':
            if rol in ['medico', 'centro']:
                acciones.extend(['editar', 'reenviar'])
        
        # Ver detalle siempre disponible
        acciones.insert(0, 'ver')
        
        return acciones
    
    def validate(self, data):
        """Validaciones del formulario"""
        # Validar que haya detalles al crear
        if not self.instance:  # Es creación
            detalles = data.get('detalles_write', [])
            if not detalles:
                raise serializers.ValidationError({
                    'detalles_write': 'Debe agregar al menos un producto a la solicitud.'
                })
            # Validar cada detalle
            for i, detalle in enumerate(detalles):
                if not detalle.get('descripcion_producto'):
                    raise serializers.ValidationError({
                        'detalles_write': f'El producto {i+1} debe tener una descripción.'
                    })
                if not detalle.get('cantidad') or detalle.get('cantidad', 0) < 1:
                    raise serializers.ValidationError({
                        'detalles_write': f'El producto {i+1} debe tener una cantidad válida.'
                    })
        
        # Validar motivo de compra
        if not self.instance and not data.get('motivo_compra'):
            raise serializers.ValidationError({
                'motivo_compra': 'Debe especificar el motivo de la compra.'
            })
        
        return data
    
    def create(self, validated_data):
        # Extraer detalles antes de crear la compra
        detalles_data = validated_data.pop('detalles_write', [])
        
        request = self.context.get('request')
        if request and request.user:
            validated_data['solicitante'] = request.user
            # Asignar centro del usuario si no se especifica
            if not validated_data.get('centro') and hasattr(request.user, 'centro') and request.user.centro:
                validated_data['centro'] = request.user.centro
        
        # Crear la compra
        compra = super().create(validated_data)
        
        # Crear los detalles
        from .models import DetalleCompraCajaChica, Producto
        for detalle_data in detalles_data:
            producto_id = detalle_data.pop('producto', None)
            producto = None
            if producto_id:
                try:
                    producto = Producto.objects.get(id=producto_id)
                except Producto.DoesNotExist:
                    pass
            
            # Mapear campos del frontend a campos del modelo
            DetalleCompraCajaChica.objects.create(
                compra=compra,
                producto=producto,
                descripcion_producto=detalle_data.get('descripcion_producto', ''),
                cantidad_solicitada=detalle_data.get('cantidad', 1),
                unidad_medida=detalle_data.get('unidad') or 'PIEZA',
                precio_unitario=detalle_data.get('precio_unitario', 0),
                numero_lote=detalle_data.get('numero_lote') or None,
                fecha_caducidad=detalle_data.get('fecha_caducidad') or None,
            )
        
        # Recalcular totales
        compra.calcular_totales()
        
        return compra


class CompraCajaChicaListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listado de compras"""
    centro_nombre = serializers.SerializerMethodField()
    solicitante_nombre = serializers.SerializerMethodField()
    estado_display = serializers.SerializerMethodField()
    total_productos = serializers.SerializerMethodField()
    
    class Meta:
        model = CompraCajaChica
        fields = [
            'id', 'folio', 'centro', 'centro_nombre',
            'proveedor_nombre', 'fecha_solicitud', 'fecha_compra',
            'total', 'estado', 'estado_display', 'motivo_compra',
            'solicitante', 'solicitante_nombre', 'total_productos',
            'created_at'  # Para trazabilidad de captura
        ]
    
    def get_centro_nombre(self, obj):
        return obj.centro.nombre if obj.centro else None
    
    def get_solicitante_nombre(self, obj):
        if obj.solicitante:
            return f"{obj.solicitante.first_name} {obj.solicitante.last_name}".strip() or obj.solicitante.username
        return None
    
    def get_estado_display(self, obj):
        return obj.get_estado_display()
    
    def get_total_productos(self, obj):
        return obj.detalles.count()


class InventarioCajaChicaSerializer(serializers.ModelSerializer):
    """Serializer para inventario de caja chica"""
    centro_nombre = serializers.SerializerMethodField()
    producto_nombre = serializers.SerializerMethodField()
    producto_clave = serializers.SerializerMethodField()
    compra_folio = serializers.SerializerMethodField()
    estado = serializers.SerializerMethodField()
    valor_total = serializers.SerializerMethodField()
    
    class Meta:
        model = InventarioCajaChica
        fields = [
            'id', 'centro', 'centro_nombre',
            'producto', 'producto_nombre', 'producto_clave', 'descripcion_producto',
            'numero_lote', 'fecha_caducidad',
            'cantidad_inicial', 'cantidad_actual',
            'compra', 'compra_folio', 'detalle_compra',
            'precio_unitario', 'valor_total',
            'ubicacion', 'activo', 'estado',
            'created_at', 'updated_at'
        ]
        # ISS-SEC-005: cantidad_actual y cantidad_inicial son read_only.
        # Solo se modifican vía recepción de compra o movimientos de caja chica.
        read_only_fields = ['id', 'created_at', 'updated_at', 'cantidad_actual', 'cantidad_inicial']
    
    def get_centro_nombre(self, obj):
        return obj.centro.nombre if obj.centro else None
    
    def get_producto_nombre(self, obj):
        return obj.producto.nombre if obj.producto else None
    
    def get_producto_clave(self, obj):
        return obj.producto.clave if obj.producto else None
    
    def get_compra_folio(self, obj):
        return obj.compra.folio if obj.compra else None
    
    def get_estado(self, obj):
        return obj.estado
    
    def get_valor_total(self, obj):
        return obj.precio_unitario * obj.cantidad_actual


class MovimientoCajaChicaSerializer(serializers.ModelSerializer):
    """Serializer para movimientos de inventario de caja chica"""
    inventario_descripcion = serializers.SerializerMethodField()
    usuario_nombre = serializers.SerializerMethodField()
    tipo_display = serializers.SerializerMethodField()
    
    class Meta:
        model = MovimientoCajaChica
        fields = [
            'id', 'inventario', 'inventario_descripcion',
            'tipo', 'tipo_display', 'cantidad',
            'cantidad_anterior', 'cantidad_nueva',
            'referencia', 'motivo',
            'usuario', 'usuario_nombre', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'cantidad_anterior', 'cantidad_nueva']
    
    def get_inventario_descripcion(self, obj):
        return obj.inventario.descripcion_producto if obj.inventario else None
    
    def get_usuario_nombre(self, obj):
        if obj.usuario:
            return f"{obj.usuario.first_name} {obj.usuario.last_name}".strip() or obj.usuario.username
        return None
    
    def get_tipo_display(self, obj):
        return obj.get_tipo_display()


class HistorialCompraCajaChicaSerializer(serializers.ModelSerializer):
    """Serializer para historial de compras de caja chica"""
    compra_folio = serializers.SerializerMethodField()
    usuario_nombre = serializers.SerializerMethodField()
    
    class Meta:
        model = HistorialCompraCajaChica
        fields = [
            'id', 'compra', 'compra_folio',
            'estado_anterior', 'estado_nuevo',
            'usuario', 'usuario_nombre',
            'accion', 'observaciones', 'ip_address', 'created_at'
        ]
    
    def get_compra_folio(self, obj):
        return obj.compra.folio if obj.compra else None
    
    def get_usuario_nombre(self, obj):
        if obj.usuario:
            return f"{obj.usuario.first_name} {obj.usuario.last_name}".strip() or obj.usuario.username
        return None
