# -*- coding: utf-8 -*-
from rest_framework import serializers
from django.db.models import Sum
from django.utils import timezone
from .models import (
    User, Centro, Producto, Lote, Requisicion, DetalleRequisicion, 
    Movimiento, AuditoriaLogs, ImportacionLogs, Notificacion, ConfiguracionSistema,
    TemaGlobal, HojaRecoleccion, DetalleHojaRecoleccion, UserProfile
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
    centro_nombre = serializers.CharField(source='centro.nombre', read_only=True, allow_null=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    permisos = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'rol', 'centro', 'centro_nombre', 'activo', 'password', 
            'adscripcion', 'permisos', 'is_active', 'is_superuser',
            'date_joined', 'last_login',
            # Permisos personalizados
            'perm_dashboard', 'perm_productos', 'perm_lotes',
            'perm_requisiciones', 'perm_centros', 'perm_usuarios',
            'perm_reportes', 'perm_trazabilidad', 'perm_auditoria',
            'perm_notificaciones', 'perm_movimientos'
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
        return obj.usuarios.filter(activo=True).count()


# =============================================================================
# PRODUCTO SERIALIZER
# =============================================================================

class ProductoSerializer(serializers.ModelSerializer):
    stock_actual = serializers.SerializerMethodField()
    lotes_activos = serializers.SerializerMethodField()
    # Campo 'clave' para compatibilidad con frontend (mapea a codigo_barras)
    clave = serializers.CharField(source='codigo_barras', required=False, allow_null=True, allow_blank=True)
    
    class Meta:
        model = Producto
        fields = [
            'id', 'clave', 'codigo_barras', 'nombre', 'descripcion', 'unidad_medida',
            'categoria', 'stock_minimo', 'stock_actual', 'sustancia_activa',
            'presentacion', 'concentracion', 'via_administracion',
            'requiere_receta', 'es_controlado', 'activo', 'imagen',
            'lotes_activos', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'stock_actual']
        extra_kwargs = {
            'codigo_barras': {'required': False, 'allow_null': True, 'allow_blank': True},
            'nombre': {'required': False},  # Se puede generar desde descripcion
            'descripcion': {'required': False, 'allow_null': True, 'allow_blank': True},
        }
    
    def get_stock_actual(self, obj):
        return getattr(obj, 'stock_actual', 0) or 0
    
    def get_lotes_activos(self, obj):
        # Filtrar por activo=True, no por estado (que es propiedad calculada)
        return obj.lotes.filter(activo=True, cantidad_actual__gt=0).count()
    
    def to_internal_value(self, data):
        # Copiar datos para no mutar el original
        if hasattr(data, 'copy'):
            data = data.copy()
        else:
            data = dict(data)
        
        # Si viene 'clave' pero no 'codigo_barras', mapear automáticamente
        if 'clave' in data and 'codigo_barras' not in data:
            data['codigo_barras'] = data.pop('clave')
        
        # Si no viene 'nombre', generarlo desde descripcion o codigo_barras
        if 'nombre' not in data or not data.get('nombre'):
            nombre_candidato = data.get('descripcion') or data.get('codigo_barras') or 'Producto sin nombre'
            data['nombre'] = str(nombre_candidato)[:255]
        
        return super().to_internal_value(data)
    
    def validate(self, attrs):
        # Asegurar que nombre tenga valor
        if not attrs.get('nombre'):
            descripcion = attrs.get('descripcion') or attrs.get('codigo_barras') or 'Producto sin nombre'
            attrs['nombre'] = str(descripcion)[:255]
        return attrs


# =============================================================================
# LOTE SERIALIZER
# =============================================================================

class LoteSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    centro_nombre = serializers.CharField(source='centro.nombre', read_only=True, allow_null=True)
    dias_para_caducar = serializers.SerializerMethodField()
    estado = serializers.SerializerMethodField()
    # precio_unitario tiene precision 12, default 0 en BD
    precio_unitario = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    # Campo 'precio_compra' para compatibilidad con frontend (alias de precio_unitario)
    precio_compra = serializers.DecimalField(source='precio_unitario', max_digits=12, decimal_places=2, required=False, allow_null=True)
    
    class Meta:
        model = Lote
        fields = [
            'id', 'producto', 'producto_nombre', 'centro', 'centro_nombre',
            'numero_lote', 'fecha_caducidad', 'fecha_fabricacion',
            'cantidad_inicial', 'cantidad_actual', 'precio_unitario', 'precio_compra',
            'numero_contrato', 'marca', 'ubicacion', 'activo', 'estado',
            'dias_para_caducar', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'estado']
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


# =============================================================================
# DETALLE REQUISICION SERIALIZER
# =============================================================================

class DetalleRequisicionSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_unidad = serializers.CharField(source='producto.unidad_medida', read_only=True)
    lote_numero = serializers.CharField(source='lote.numero_lote', read_only=True, allow_null=True)
    # cantidad_surtida tiene default 0 en BD
    cantidad_surtida = serializers.IntegerField(required=False, default=0, allow_null=True)
    
    class Meta:
        model = DetalleRequisicion
        fields = [
            'id', 'producto', 'lote', 'producto_nombre', 'producto_unidad',
            'lote_numero', 'cantidad_solicitada', 'cantidad_autorizada', 
            'cantidad_surtida', 'cantidad_recibida', 'notas',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'notas': {'required': False, 'allow_null': True, 'allow_blank': True},
            'cantidad_autorizada': {'required': False, 'allow_null': True},
            'cantidad_recibida': {'required': False, 'allow_null': True},
        }
    
    def validate_cantidad_solicitada(self, value):
        if value <= 0:
            raise serializers.ValidationError('La cantidad debe ser mayor a 0')
        return value


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
    # Campo 'centro' para compatibilidad con frontend (alias de centro_destino)
    centro = serializers.PrimaryKeyRelatedField(
        source='centro_destino', queryset=Centro.objects.all(), 
        required=False, allow_null=True, write_only=True
    )
    # Campo 'comentario' para compatibilidad con frontend (alias de notas)
    comentario = serializers.CharField(source='notas', required=False, allow_blank=True, allow_null=True, write_only=True)
    
    class Meta:
        model = Requisicion
        fields = [
            'id', 'numero', 'centro', 'comentario', 'centro_origen', 'centro_origen_nombre', 
            'centro_destino', 'centro_destino_nombre',
            'solicitante', 'solicitante_nombre', 'autorizador', 'autorizador_nombre',
            'fecha_solicitud', 'fecha_autorizacion', 'fecha_surtido', 'fecha_entrega',
            'estado', 'tipo', 'prioridad', 'notas', 'lugar_entrega',
            'foto_firma_surtido', 'foto_firma_recepcion',
            'usuario_firma_surtido', 'usuario_firma_recepcion',
            'fecha_firma_surtido', 'fecha_firma_recepcion',
            'detalles', 'total_productos', 'created_at', 'updated_at'
        ]
        read_only_fields = ['numero', 'fecha_solicitud', 'created_at', 'updated_at']
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
        }
    
    def get_solicitante_nombre(self, obj):
        if obj.solicitante:
            return obj.solicitante.get_full_name() or obj.solicitante.username
        return None
    
    def get_autorizador_nombre(self, obj):
        if obj.autorizador:
            return obj.autorizador.get_full_name() or obj.autorizador.username
        return None
    
    def get_total_productos(self, obj):
        return obj.detalles.count()
    
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

class MovimientoSerializer(serializers.ModelSerializer):
    lote_numero = serializers.CharField(source='lote.numero_lote', read_only=True, allow_null=True)
    producto_nombre = serializers.SerializerMethodField()
    centro_origen_nombre = serializers.CharField(source='centro_origen.nombre', read_only=True, allow_null=True)
    centro_destino_nombre = serializers.CharField(source='centro_destino.nombre', read_only=True, allow_null=True)
    usuario_nombre = serializers.SerializerMethodField()
    
    class Meta:
        model = Movimiento
        fields = [
            'id', 'tipo', 'producto', 'producto_nombre', 'lote', 'lote_numero',
            'centro_origen', 'centro_origen_nombre', 'centro_destino', 'centro_destino_nombre',
            'cantidad', 'usuario', 'usuario_nombre', 'requisicion', 
            'motivo', 'referencia', 'fecha', 'created_at'
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
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'es_activo': {'required': False, 'default': False},
            'logo_url': {'required': False, 'allow_null': True, 'allow_blank': True},
            'logo_width': {'required': False, 'default': 160},
            'logo_height': {'required': False, 'default': 60},
            'favicon_url': {'required': False, 'allow_null': True, 'allow_blank': True},
            'titulo_sistema': {'required': False, 'allow_null': True},
            'subtitulo_sistema': {'required': False, 'allow_null': True},
        }


class TemaGlobalPublicoSerializer(serializers.ModelSerializer):
    """
    Serializer público para TemaGlobal - Solo campos necesarios para el frontend.
    Usado en endpoints públicos como login.
    """
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
        ]
        read_only_fields = fields


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

