# -*- coding: utf-8 -*-
from rest_framework import serializers
from django.db.models import Sum
from django.utils import timezone
from .models import (
    User, Centro, Producto, Lote, Requisicion, DetalleRequisicion, 
    Movimiento, AuditoriaLog, ImportacionLog, Notificacion
)
from .constants import EXTRA_PERMISSIONS
import logging
import re

logger = logging.getLogger(__name__)

# =============================================================================
# PERMISOS POR ROL
# =============================================================================

PERMISOS_POR_ROL = {
    'ADMIN': {
        'verDashboard': True,
        'verProductos': True,
        'verLotes': True,
        'verRequisiciones': True,
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
    },
    'FARMACIA': {
        'verDashboard': True,
        'verProductos': True,
        'verLotes': True,
        'verRequisiciones': True,
        'verCentros': True,
        'verUsuarios': True,
        'verReportes': True,
        'verTrazabilidad': True,
        'verAuditoria': False,
        'verNotificaciones': True,
        'verPerfil': True,
        'verMovimientos': True,
        'configurarTema': False,
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
    },
    'CENTRO': {
        'verDashboard': True,
        'verProductos': True,
        'verLotes': True,
        'verRequisiciones': True,
        'verCentros': False,
        'verUsuarios': False,
        'verReportes': True,
        'verTrazabilidad': True,
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
        'confirmarRecepcion': True,
        'descargarHojaRecoleccion': True,
    },
    'VISTA': {
        'verDashboard': True,
        'verProductos': True,
        'verLotes': True,
        'verRequisiciones': True,
        'verCentros': True,
        'verUsuarios': True,
        'verReportes': True,
        'verTrazabilidad': True,
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
        'descargarHojaRecoleccion': True,
    },
    'SIN_ROL': {
        'verDashboard': False,
        'verProductos': False,
        'verLotes': False,
        'verRequisiciones': False,
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
        'descargarHojaRecoleccion': False,
    },
}


def _resolve_rol(user):
    if not user:
        return 'SIN_ROL'
    if user.is_superuser:
        return 'ADMIN'
    normalized = (user.rol or '').lower()
    if normalized in ['admin_sistema', 'superusuario']:
        return 'ADMIN'
    if normalized in ['farmacia', 'admin_farmacia']:
        return 'FARMACIA'
    if normalized in ['centro', 'usuario_normal', 'solicitante']:
        return 'CENTRO'
    if normalized in ['vista', 'usuario_vista']:
        return 'VISTA'
    return 'SIN_ROL'


def build_perm_map(user):
    rol = _resolve_rol(user)
    base = PERMISOS_POR_ROL.get(rol, PERMISOS_POR_ROL['SIN_ROL']).copy()
    if user and user.is_superuser:
        for key in base.keys():
            base[key] = True
    if user:
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
        }
        for field, perm_key in perm_fields.items():
            custom_value = getattr(user, field, None)
            if custom_value is not None:
                base[perm_key] = custom_value
    return base


# =============================================================================
# USER SERIALIZER
# =============================================================================

class UserSerializer(serializers.ModelSerializer):
    centro_nombre = serializers.CharField(source='centro.nombre', read_only=True)
    password = serializers.CharField(write_only=True, required=False)
    permisos = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'rol', 'centro', 'centro_nombre', 'activo', 'password', 
            'adscripcion', 'permisos', 'is_active', 'is_superuser',
            'date_joined', 'last_login'
        ]
        read_only_fields = ['date_joined', 'last_login']
        extra_kwargs = {'password': {'write_only': True, 'required': False}}

    def get_permisos(self, obj):
        return build_perm_map(obj)
    
    def validate_username(self, value):
        if not value or len(value) < 3:
            raise serializers.ValidationError('El username debe tener al menos 3 caracteres')
        instance_id = self.instance.id if self.instance else None
        if User.objects.filter(username__iexact=value).exclude(id=instance_id).exists():
            raise serializers.ValidationError('El username ya esta en uso')
        return value.lower()
    
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
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
            'id', 'nombre', 'direccion', 'telefono', 
            'activo', 'total_requisiciones', 'total_usuarios',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_total_requisiciones(self, obj):
        return obj.requisiciones.count()
    
    def get_total_usuarios(self, obj):
        return obj.usuarios.filter(activo=True).count()


# =============================================================================
# PRODUCTO SERIALIZER
# =============================================================================

class ProductoSerializer(serializers.ModelSerializer):
    stock_actual = serializers.SerializerMethodField()
    lotes_activos = serializers.SerializerMethodField()
    
    class Meta:
        model = Producto
        fields = [
            'id', 'codigo_barras', 'nombre', 'descripcion', 'unidad_medida',
            'categoria', 'stock_minimo', 'stock_actual', 'sustancia_activa',
            'presentacion', 'concentracion', 'via_administracion',
            'requiere_receta', 'es_controlado', 'activo', 'imagen',
            'lotes_activos', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'stock_actual']
    
    def get_stock_actual(self, obj):
        return getattr(obj, 'stock_actual', 0) or 0
    
    def get_lotes_activos(self, obj):
        return obj.lotes.filter(estado='disponible').count()


# =============================================================================
# LOTE SERIALIZER
# =============================================================================

class LoteSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    centro_nombre = serializers.CharField(source='centro.nombre', read_only=True, allow_null=True)
    dias_para_caducar = serializers.SerializerMethodField()
    
    class Meta:
        model = Lote
        fields = [
            'id', 'producto', 'producto_nombre', 'centro', 'centro_nombre',
            'numero_lote', 'fecha_caducidad', 'fecha_entrada',
            'cantidad_inicial', 'cantidad_actual', 'precio_compra',
            'estado', 'ubicacion', 'observaciones', 'documento_soporte',
            'dias_para_caducar', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'fecha_entrada']
    
    def get_dias_para_caducar(self, obj):
        if obj.fecha_caducidad:
            delta = obj.fecha_caducidad - timezone.now().date()
            return delta.days
        return None


# =============================================================================
# DETALLE REQUISICION SERIALIZER
# =============================================================================

class DetalleRequisicionSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_unidad = serializers.CharField(source='producto.unidad_medida', read_only=True)
    lote_numero = serializers.CharField(source='lote.numero_lote', read_only=True, allow_null=True)
    
    class Meta:
        model = DetalleRequisicion
        fields = [
            'id', 'producto', 'lote', 'producto_nombre', 'producto_unidad',
            'lote_numero', 'cantidad_solicitada', 'cantidad_autorizada', 
            'cantidad_surtida', 'observaciones'
        ]
    
    def validate_cantidad_solicitada(self, value):
        if value <= 0:
            raise serializers.ValidationError('La cantidad debe ser mayor a 0')
        return value


# =============================================================================
# REQUISICION SERIALIZER
# =============================================================================

class RequisicionSerializer(serializers.ModelSerializer):
    detalles = DetalleRequisicionSerializer(many=True, required=False)
    centro_nombre = serializers.CharField(source='centro.nombre', read_only=True)
    usuario_solicita_nombre = serializers.SerializerMethodField()
    total_productos = serializers.SerializerMethodField()
    
    class Meta:
        model = Requisicion
        fields = [
            'id', 'folio', 'centro', 'centro_nombre', 'usuario_solicita', 
            'usuario_solicita_nombre', 'fecha_solicitud', 'estado', 'observaciones',
            'usuario_autoriza', 'fecha_autorizacion', 'motivo_rechazo', 
            'detalles', 'total_productos', 'created_at', 'updated_at'
        ]
        read_only_fields = ['folio', 'fecha_solicitud', 'created_at', 'updated_at']
    
    def get_usuario_solicita_nombre(self, obj):
        if obj.usuario_solicita:
            return obj.usuario_solicita.get_full_name() or obj.usuario_solicita.username
        return None
    
    def get_total_productos(self, obj):
        return obj.detalles.count()
    
    def create(self, validated_data):
        detalles_data = validated_data.pop('detalles', [])
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

class MovimientoSerializer(serializers.ModelSerializer):
    lote_numero = serializers.CharField(source='lote.numero_lote', read_only=True)
    producto_nombre = serializers.CharField(source='lote.producto.nombre', read_only=True)
    centro_nombre = serializers.CharField(source='centro.nombre', read_only=True, allow_null=True)
    
    class Meta:
        model = Movimiento
        fields = [
            'id', 'tipo', 'lote', 'lote_numero', 'producto_nombre',
            'centro', 'centro_nombre', 'cantidad', 'usuario',
            'requisicion', 'documento_referencia', 'observaciones', 'fecha'
        ]
        read_only_fields = ['fecha']


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
        model = AuditoriaLog
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
        model = ImportacionLog
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
    centro_nombre = serializers.CharField(source='centro.nombre', read_only=True, default='')
    permisos = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'rol', 'centro', 'centro_nombre', 'adscripcion', 'permisos',
            'is_superuser', 'is_staff',
        ]
        read_only_fields = ['username', 'rol', 'centro', 'is_superuser', 'is_staff']

    def get_permisos(self, obj):
        return build_perm_map(obj)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


