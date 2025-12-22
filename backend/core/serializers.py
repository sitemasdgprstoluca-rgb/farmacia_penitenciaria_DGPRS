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
    RequisicionHistorialEstados  # FLUJO V2
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
        
        logger.info(f"UserSerializer.create - validated_data: {validated_data}, centro_id: {centro_id}")
        logger.info(f"UserSerializer.create - password received: {'YES (length=' + str(len(password)) + ')' if password else 'NO'}")
        
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
        
        logger.info(f"UserSerializer.update - validated_data: {validated_data}, centro_id: {centro_id}")
        
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
        # Centro puede ser origen o destino de requisiciones
        from django.db.models import Q
        return Requisicion.objects.filter(
            Q(centro_origen=obj) | Q(centro_destino=obj)
        ).count()
    
    def get_total_usuarios(self, obj):
        return obj.usuarios.filter(is_active=True).count()


# =============================================================================
# PRODUCTO SERIALIZER
# =============================================================================

class ProductoSerializer(serializers.ModelSerializer):
    stock_actual = serializers.SerializerMethodField()
    lotes_activos = serializers.SerializerMethodField()
    
    class Meta:
        model = Producto
        fields = [
            'id', 'clave', 'nombre', 'descripcion', 'unidad_medida',
            'categoria', 'sustancia_activa', 'presentacion', 'concentracion',
            'via_administracion', 'requiere_receta', 'es_controlado',
            'stock_minimo', 'stock_actual', 'activo', 'imagen',
            'lotes_activos', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'stock_actual']
        extra_kwargs = {
            'clave': {'required': True},
            'nombre': {'required': True},
            'descripcion': {'required': False, 'allow_null': True, 'allow_blank': True},
            'presentacion': {'required': True},  # ISS-FIX: Presentación obligatoria
        }
    
    def get_stock_actual(self, obj):
        # Priorizar stock_calculado (anotación) sobre el campo
        return getattr(obj, 'stock_calculado', None) or obj.stock_actual or 0
    
    def get_lotes_activos(self, obj):
        # ISS-FIX: Priorizar lotes_centro_count (anotación por centro) sobre conteo global
        # Esto asegura que usuarios de centro vean solo SUS lotes
        lotes_centro = getattr(obj, 'lotes_centro_count', None)
        if lotes_centro is not None:
            return lotes_centro
        # Fallback: conteo global (para casos donde no hay anotación)
        return obj.lotes.filter(activo=True, cantidad_actual__gt=0).count()
    
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
    
    def validate_stock_minimo(self, value):
        """Stock mínimo debe ser un número no negativo."""
        if value is None:
            return 0  # Default
        if value < 0:
            raise serializers.ValidationError('El stock mínimo no puede ser negativo')
        return value
    
    def validate_presentacion(self, value):
        """ISS-FIX: Presentación es obligatoria."""
        if not value or str(value).strip() == '':
            raise serializers.ValidationError('La presentación es obligatoria')
        return str(value).strip()
    
    def validate(self, attrs):
        return attrs


# =============================================================================
# LOTE SERIALIZER
# =============================================================================

class LoteSerializer(serializers.ModelSerializer):
    # ISS-DB: Campos alineados con schema de productos (clave, nombre)
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_clave = serializers.CharField(source='producto.clave', read_only=True)
    producto_descripcion = serializers.CharField(source='producto.nombre', read_only=True)  # Alias para compatibilidad
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
    
    class Meta:
        model = Lote
        fields = [
            'id', 'producto', 'producto_nombre', 'producto_clave', 'producto_descripcion',
            'centro', 'centro_nombre',
            'numero_lote', 'fecha_caducidad', 'fecha_fabricacion',
            'cantidad_inicial', 'cantidad_actual', 'precio_unitario', 'precio_compra',
            'numero_contrato', 'marca', 'ubicacion', 'activo', 'estado',
            'dias_para_caducar', 'alerta_caducidad', 'porcentaje_consumido',
            'documentos', 'tiene_documentos',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'estado', 'documentos', 'tiene_documentos']
        extra_kwargs = {
            'cantidad_actual': {'required': False, 'default': 0},
            'numero_contrato': {'required': False, 'allow_null': True, 'allow_blank': True},
            'marca': {'required': False, 'allow_null': True, 'allow_blank': True},
            'ubicacion': {'required': False, 'allow_null': True, 'allow_blank': True},
        }
    
    def to_internal_value(self, data):
        # Si viene 'precio_compra' pero no 'precio_unitario', mapear automáticamente
        if 'precio_compra' in data and 'precio_unitario' not in data:
            data = data.copy()
            data['precio_unitario'] = data.pop('precio_compra')
        return super().to_internal_value(data)
    
    def validate_fecha_caducidad(self, value):
        """ISS-DB-004: Validar que fecha_caducidad esté presente (NOT NULL en BD)."""
        if value is None:
            raise serializers.ValidationError(
                'La fecha de caducidad es obligatoria. Use 2099-12-31 para insumos sin caducidad.'
            )
        return value
    
    def validate_numero_lote(self, value):
        """Número de lote es requerido y no puede estar vacío."""
        if not value or value.strip() == '':
            raise serializers.ValidationError('El número de lote es requerido')
        return value.strip()
    
    def validate_cantidad_inicial(self, value):
        """Cantidad inicial debe ser un número positivo."""
        if value is None:
            raise serializers.ValidationError('La cantidad inicial es requerida')
        if value < 0:
            raise serializers.ValidationError('La cantidad inicial no puede ser negativa')
        return value
    
    def validate_precio_unitario(self, value):
        """Precio unitario debe ser no negativo."""
        if value is not None and value < 0:
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
        """
        from django.core.exceptions import ValidationError as DjangoValidationError
        from .models import Contrato
        
        numero_contrato = attrs.get('numero_contrato')
        producto = attrs.get('producto')
        cantidad = attrs.get('cantidad_inicial', 0)
        fecha_caducidad = attrs.get('fecha_caducidad')
        
        # ISS-007: Si hay numero_contrato, buscar y validar el Contrato
        if numero_contrato and producto and cantidad > 0:
            try:
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
                
            except DjangoValidationError as e:
                # Convertir ValidationError de Django a DRF
                if hasattr(e, 'message_dict'):
                    raise serializers.ValidationError(e.message_dict)
                raise serializers.ValidationError({'numero_contrato': str(e)})
        
        return super().validate(attrs)
    
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
    lote_numero = serializers.CharField(source='lote.numero_lote', read_only=True, allow_null=True)
    # ISS-DB: Alias para compatibilidad con frontend
    producto_clave = serializers.CharField(source='producto.clave', read_only=True, allow_null=True)
    producto_descripcion = serializers.CharField(source='producto.nombre', read_only=True)  # Alias de producto_nombre
    lote_caducidad = serializers.DateField(source='lote.fecha_caducidad', read_only=True, allow_null=True)
    lote_stock = serializers.IntegerField(source='lote.cantidad_actual', read_only=True, allow_null=True)
    stock_disponible = serializers.IntegerField(source='lote.cantidad_actual', read_only=True, allow_null=True)
    # cantidad_surtida tiene default 0 en BD
    cantidad_surtida = serializers.IntegerField(required=False, default=0, allow_null=True)
    # MEJORA FLUJO 3: Campo para explicar ajustes de cantidad
    motivo_ajuste = serializers.CharField(required=False, allow_null=True, allow_blank=True, max_length=255)
    
    class Meta:
        model = DetalleRequisicion
        fields = [
            'id', 'producto', 'lote', 
            'producto_nombre', 'producto_clave', 'producto_descripcion', 'producto_unidad',
            'lote_numero', 'lote_caducidad', 'lote_stock', 'stock_disponible',
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
        return value
    
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
# REQUISICION SERIALIZER
# =============================================================================

class RequisicionSerializer(serializers.ModelSerializer):
    detalles = DetalleRequisicionSerializer(many=True, required=False)
    # Usar campos reales de la BD
    centro_origen_nombre = serializers.CharField(source='centro_origen.nombre', read_only=True, allow_null=True)
    centro_destino_nombre = serializers.CharField(source='centro_destino.nombre', read_only=True, allow_null=True)
    solicitante_nombre = serializers.SerializerMethodField()
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
            'solicitante', 'solicitante_nombre', 'usuario_solicita_nombre',
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
            'motivo', 'observaciones', 'referencia', 'subtipo_salida', 'numero_expediente',
            'fecha', 'fecha_movimiento', 'created_at'
        ]
        read_only_fields = ['fecha', 'created_at']
        extra_kwargs = {
            'motivo': {'required': False, 'allow_null': True, 'allow_blank': True},
            'referencia': {'required': False, 'allow_null': True, 'allow_blank': True},
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
        """Retorna el nombre del centro (destino para entradas, origen para salidas)."""
        if obj.centro_destino:
            return obj.centro_destino.nombre
        if obj.centro_origen:
            return obj.centro_origen.nombre
        if obj.lote and obj.lote.centro:
            return obj.lote.centro.nombre
        return 'Farmacia Central'
    
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
# AUDITORIA LOG SERIALIZER
# =============================================================================

class AuditoriaLogSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.SerializerMethodField()
    fecha = serializers.DateTimeField(source='timestamp', read_only=True)
    
    class Meta:
        model = AuditoriaLogs
        fields = [
            'id', 'usuario', 'usuario_nombre', 'accion', 'modelo', 
            'objeto_id', 'ip_address', 'user_agent', 'detalles', 'fecha'
        ]
        read_only_fields = fields
    
    def get_usuario_nombre(self, obj):
        if obj.usuario:
            return obj.usuario.get_full_name() or obj.usuario.username
        return 'Sistema'


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
        # Extraer telefono de los datos (viene en request.data pero no en validated_data)
        telefono = self.initial_data.get('telefono')
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Actualizar teléfono en UserProfile si se proporcionó
        if telefono is not None:
            profile = getattr(instance, 'profile', None)
            if profile:
                profile.telefono = telefono
                profile.save(update_fields=['telefono', 'updated_at'])
        
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
    """
    lote_numero = serializers.CharField(source='lote.numero_lote', read_only=True)
    producto_nombre = serializers.CharField(source='lote.producto.nombre', read_only=True)
    
    class Meta:
        model = DetalleHojaRecoleccion
        fields = [
            'id', 'lote', 'lote_numero', 'producto_nombre',
            'cantidad_recolectar', 'cantidad_recolectada',
            'motivo', 'observaciones', 'created_at'
        ]
        read_only_fields = ['created_at']
        extra_kwargs = {
            'cantidad_recolectada': {'required': False, 'default': 0, 'allow_null': True},
            'motivo': {'required': False, 'default': 'caducidad'},
            'observaciones': {'required': False, 'allow_null': True, 'allow_blank': True},
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
    
    Si no se proporciona clave, se genera automáticamente con formato DON-YYYYMMDD-XXXX
    """
    class Meta:
        model = ProductoDonacion
        fields = [
            'id', 'clave', 'nombre', 'descripcion', 'unidad_medida',
            'presentacion', 'activo', 'notas', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'clave': {'required': False, 'allow_blank': True},  # Ahora es opcional
            'nombre': {'required': True},
            'descripcion': {'required': False, 'allow_null': True, 'allow_blank': True},
            'unidad_medida': {'required': False, 'default': 'PIEZA'},
            'presentacion': {'required': False, 'allow_null': True, 'allow_blank': True},
            'activo': {'required': False, 'default': True},
            'notas': {'required': False, 'allow_null': True, 'allow_blank': True},
        }
    
    def _generar_clave_automatica(self):
        """
        Genera una clave única automática con formato DON-YYYYMMDD-XXXX
        Ejemplo: DON-20251219-0001
        """
        from datetime import date
        import random
        
        hoy = date.today().strftime('%Y%m%d')
        prefix = f"DON-{hoy}-"
        
        # Encontrar el siguiente número disponible
        existentes = ProductoDonacion.objects.filter(clave__startswith=prefix).order_by('-clave')
        if existentes.exists():
            ultima_clave = existentes.first().clave
            try:
                ultimo_numero = int(ultima_clave.split('-')[-1])
                siguiente = ultimo_numero + 1
            except (ValueError, IndexError):
                siguiente = random.randint(1, 9999)
        else:
            siguiente = 1
        
        return f"{prefix}{siguiente:04d}"
    
    def validate_clave(self, value):
        """Validar que la clave sea única (case insensitive), o generar automáticamente si está vacía"""
        # Si está vacía, se generará automáticamente en create()
        if not value or not value.strip():
            return None
        
        clave_upper = value.upper().strip()
        qs = ProductoDonacion.objects.filter(clave__iexact=clave_upper)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe un producto de donación con esta clave.")
        return clave_upper
    
    def create(self, validated_data):
        """Si no se proporciona clave, genera una automática"""
        if not validated_data.get('clave'):
            validated_data['clave'] = self._generar_clave_automatica()
        return super().create(validated_data)


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
            'numero_lote': {'required': False, 'allow_null': True, 'allow_blank': True},
            'fecha_caducidad': {'required': False, 'allow_null': True},
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
    
    def create(self, validated_data):
        detalles_data = validated_data.pop('detalles', [])
        
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
            # Eliminar detalles existentes y crear nuevos
            instance.detalles.all().delete()
            for detalle_data in detalles_data:
                DetalleDonacion.objects.create(donacion=instance, **detalle_data)
        
        return instance


class SalidaDonacionSerializer(serializers.ModelSerializer):
    """
    Serializer para salidas/entregas del almacen de donaciones.
    Control interno sin afectar movimientos principales.
    """
    detalle_donacion_info = serializers.SerializerMethodField()
    entregado_por_nombre = serializers.SerializerMethodField()
    producto_nombre = serializers.SerializerMethodField()
    finalizado_por_nombre = serializers.SerializerMethodField()
    
    class Meta:
        model = SalidaDonacion
        fields = [
            'id', 'detalle_donacion', 'detalle_donacion_info',
            'cantidad', 'destinatario', 'motivo',
            'entregado_por', 'entregado_por_nombre',
            'producto_nombre',
            'fecha_entrega', 'notas', 'created_at',
            'finalizado', 'fecha_finalizado', 'finalizado_por', 'finalizado_por_nombre'
        ]
        read_only_fields = ['created_at', 'fecha_entrega', 'entregado_por', 'fecha_finalizado', 'finalizado_por']
        extra_kwargs = {
            'detalle_donacion': {'required': True},
            'cantidad': {'required': True},
            'destinatario': {'required': True},
            'motivo': {'required': False, 'allow_null': True, 'allow_blank': True},
            'notas': {'required': False, 'allow_null': True, 'allow_blank': True},
            'finalizado': {'required': False},
        }
    
    def get_finalizado_por_nombre(self, obj):
        if hasattr(obj, 'finalizado_por') and obj.finalizado_por:
            return f"{obj.finalizado_por.first_name} {obj.finalizado_por.last_name}".strip() or obj.finalizado_por.username
        return None
    
    def get_detalle_donacion_info(self, obj):
        if obj.detalle_donacion:
            # Obtener nombre y código del producto (donación o legacy)
            producto_nombre = None
            producto_codigo = None
            if obj.detalle_donacion.producto_donacion:
                producto_nombre = obj.detalle_donacion.producto_donacion.nombre
                producto_codigo = obj.detalle_donacion.producto_donacion.clave
            elif obj.detalle_donacion.producto:
                producto_nombre = obj.detalle_donacion.producto.nombre
                producto_codigo = obj.detalle_donacion.producto.clave
            
            return {
                'id': obj.detalle_donacion.id,
                'donacion_numero': obj.detalle_donacion.donacion.numero,
                'producto_nombre': producto_nombre,
                'producto_codigo': producto_codigo,
                'numero_lote': obj.detalle_donacion.numero_lote,
                'cantidad_original': obj.detalle_donacion.cantidad,
                'cantidad_disponible': obj.detalle_donacion.cantidad_disponible,
            }
        return None
    
    def get_entregado_por_nombre(self, obj):
        if obj.entregado_por:
            return f"{obj.entregado_por.first_name} {obj.entregado_por.last_name}".strip() or obj.entregado_por.username
        return None
    
    def get_producto_nombre(self, obj):
        """Retorna el nombre del producto (donación o legacy)"""
        if obj.detalle_donacion:
            # Primero intentar con el nuevo catálogo de donaciones
            if obj.detalle_donacion.producto_donacion:
                return obj.detalle_donacion.producto_donacion.nombre
            # Fallback al catálogo legacy
            if obj.detalle_donacion.producto:
                return obj.detalle_donacion.producto.nombre
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