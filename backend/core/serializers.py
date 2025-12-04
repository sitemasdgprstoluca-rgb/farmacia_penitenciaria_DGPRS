from rest_framework import serializers
from django.db.models import Sum
from django.utils import timezone
from .models import User, Centro, Producto, Lote, Requisicion, DetalleRequisicion, Movimiento, AuditoriaLog, ImportacionLog, Notificacion, UserProfile, ConfiguracionSistema, HojaRecoleccion, DetalleHojaRecoleccion
from .constants import (
    UNIDADES_MEDIDA,
    ESTADOS_LOTE,
    ESTADOS_REQUISICION,
    TIPOS_MOVIMIENTO,
    ROLES_USUARIO,
    EXTRA_PERMISSIONS,
    PRODUCTO_CLAVE_MIN_LENGTH,
    PRODUCTO_CLAVE_MAX_LENGTH,
    PRODUCTO_DESCRIPCION_MIN_LENGTH,
    PRODUCTO_DESCRIPCION_MAX_LENGTH,
    PRODUCTO_PRECIO_MAX_DIGITS,
    PRODUCTO_PRECIO_DECIMAL_PLACES,
    LOTE_NUMERO_MIN_LENGTH,
    LOTE_NUMERO_MAX_LENGTH,
)
import logging

logger = logging.getLogger(__name__)

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
        'configurarTema': True,  # Solo Admin puede personalizar tema
        # Permisos granulares de requisiciones
        'crearRequisicion': True,
        'editarRequisicion': True,
        'eliminarRequisicion': True,
        'enviarRequisicion': True,
        'autorizarRequisicion': True,
        'rechazarRequisicion': True,
        'surtirRequisicion': True,
        'cancelarRequisicion': True,
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
        'verAuditoria': False,  # Solo admin/superuser
        'verNotificaciones': True,
        'verPerfil': True,
        'verMovimientos': True,
        'configurarTema': False,  # Farmacia NO puede personalizar tema
        # Permisos granulares de requisiciones
        'crearRequisicion': True,
        'editarRequisicion': True,
        'eliminarRequisicion': True,
        'enviarRequisicion': True,
        'autorizarRequisicion': True,
        'rechazarRequisicion': True,
        'surtirRequisicion': True,
        'cancelarRequisicion': True,
        'descargarHojaRecoleccion': True,
    },
    'CENTRO': {
        'verDashboard': True,
        'verProductos': False,
        'verLotes': False,
        'verRequisiciones': True,
        'verCentros': False,
        'verUsuarios': False,
        'verReportes': False,  # Centro NO debe ver Reportes - solo admin/farmacia
        'verTrazabilidad': False,
        'verAuditoria': False,
        'verNotificaciones': True,
        'verPerfil': True,
        'verMovimientos': False,
        'configurarTema': False,  # Centro no puede personalizar tema
        # Permisos granulares de requisiciones - Centro solo crea y envía
        'crearRequisicion': True,
        'editarRequisicion': True,  # Solo sus propios borradores
        'eliminarRequisicion': True,  # Solo sus propios borradores
        'enviarRequisicion': True,
        'autorizarRequisicion': False,  # No puede autorizar
        'rechazarRequisicion': False,  # No puede rechazar
        'surtirRequisicion': False,  # No puede surtir
        'cancelarRequisicion': True,  # Puede cancelar las suyas
        'descargarHojaRecoleccion': True,  # Puede descargar para recoger
    },
    'VISTA': {
        'verDashboard': True,
        'verProductos': True,
        'verLotes': True,
        'verRequisiciones': True,
        'verCentros': True,
        'verUsuarios': True,
        'verReportes': True,
        'verTrazabilidad': False,  # Restringido: datos sensibles
        'verAuditoria': False,  # Restringido: datos sensibles
        'verNotificaciones': True,
        'verPerfil': True,
        'verMovimientos': True,
        'configurarTema': False,  # Vista no puede personalizar tema
        # Vista no puede modificar requisiciones
        'crearRequisicion': False,
        'editarRequisicion': False,
        'eliminarRequisicion': False,
        'enviarRequisicion': False,
        'autorizarRequisicion': False,
        'rechazarRequisicion': False,
        'surtirRequisicion': False,
        'cancelarRequisicion': False,
        'descargarHojaRecoleccion': True,  # Puede descargar para consulta
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
    """
    Construye el mapa de permisos del usuario.
    Primero usa los permisos del rol, luego sobrescribe con permisos personalizados si existen.
    """
    rol = _resolve_rol(user)
    base = PERMISOS_POR_ROL.get(rol, PERMISOS_POR_ROL['SIN_ROL']).copy()
    
    if user and user.is_superuser:
        for key in base.keys():
            base[key] = True
    
    # Aplicar permisos personalizados si el usuario los tiene configurados
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
            if custom_value is not None:  # Solo sobrescribe si está explícitamente configurado
                base[perm_key] = custom_value
    
    return base


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer para Usuario con validaciones robustas
    """
    centro_nombre = serializers.CharField(source='centro.nombre', read_only=True)
    password = serializers.CharField(write_only=True, required=False, style={'input_type': 'password'})
    grupos = serializers.SerializerMethodField()
    extra_permisos = serializers.SerializerMethodField()
    permisos = serializers.SerializerMethodField()
    permisos_personalizados = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'rol', 'centro', 'centro_nombre', 'activo', 'password', 
            'adscripcion',  # Campo de adscripción
            'grupos', 'extra_permisos', 'permisos', 'permisos_personalizados',
            'is_active', 'is_superuser',
            'perm_dashboard', 'perm_productos', 'perm_lotes', 'perm_requisiciones',
            'perm_centros', 'perm_usuarios', 'perm_reportes', 'perm_trazabilidad',
            'perm_auditoria', 'perm_notificaciones', 'perm_movimientos',
            'date_joined', 'last_login'
        ]
        read_only_fields = ['date_joined', 'last_login']
        extra_kwargs = {
            'password': {'write_only': True, 'required': False}
        }

    def get_grupos(self, obj):
        return [g.name for g in obj.groups.all()]
    
    def get_extra_permisos(self, obj):
        from core.constants import EXTRA_PERMISSIONS
        group_names = set(g.name for g in obj.groups.all())
        return [perm for perm in EXTRA_PERMISSIONS if perm in group_names]
    
    def get_permisos(self, obj):
        """Retorna los permisos efectivos del usuario (rol + personalizados)"""
        return build_perm_map(obj)
    
    def get_permisos_personalizados(self, obj):
        """Retorna solo los permisos que han sido personalizados (no null)"""
        return {
            'perm_dashboard': obj.perm_dashboard,
            'perm_productos': obj.perm_productos,
            'perm_lotes': obj.perm_lotes,
            'perm_requisiciones': obj.perm_requisiciones,
            'perm_centros': obj.perm_centros,
            'perm_usuarios': obj.perm_usuarios,
            'perm_reportes': obj.perm_reportes,
            'perm_trazabilidad': obj.perm_trazabilidad,
            'perm_auditoria': obj.perm_auditoria,
            'perm_notificaciones': obj.perm_notificaciones,
            'perm_movimientos': obj.perm_movimientos,
        }
    
    def validate_username(self, value):
        """
        Valida username: alfanumérico, mín 3 caracteres, único
        """
        if not value or len(value) < 3:
            raise serializers.ValidationError('El username debe tener al menos 3 caracteres')
        
        if not value.replace('_', '').replace('.', '').isalnum():
            raise serializers.ValidationError('Solo se permiten letras, números, puntos y guiones bajos')
        
        # Validar unicidad (excluyendo instancia actual en updates)
        instance_id = self.instance.id if self.instance else None
        if User.objects.filter(username__iexact=value).exclude(id=instance_id).exists():
            raise serializers.ValidationError(f'El username "{value}" ya está en uso')
        
        return value.lower()
    
    def validate_email(self, value):
        """Valida email único"""
        if value:
            instance_id = self.instance.id if self.instance else None
            if User.objects.filter(email__iexact=value).exclude(id=instance_id).exists():
                raise serializers.ValidationError(f'El email "{value}" ya está en uso')
        
        return value.lower() if value else value
    
    def validate_password(self, value):
        """
        Valida contraseña: mín 8 caracteres, mayúscula, número
        """
        if value:
            if len(value) < 8:
                raise serializers.ValidationError('La contraseña debe tener al menos 8 caracteres')
            
            if not any(c.isupper() for c in value):
                raise serializers.ValidationError('La contraseña debe contener al menos una mayúscula')
            
            if not any(c.isdigit() for c in value):
                raise serializers.ValidationError('La contraseña debe contener al menos un número')
        
        return value
    
    def create(self, validated_data):
        """Crea usuario con contraseña hasheada"""
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        
        user.save()
        logger.info(f"Usuario {user.username} creado con rol {user.rol}")
        return user
    
    def update(self, instance, validated_data):
        """Actualiza usuario, hashea contraseña si se proporciona"""
        password = validated_data.pop('password', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
        
        instance.save()
        logger.info(f"Usuario {instance.username} actualizado")
        return instance


class CentroSerializer(serializers.ModelSerializer):
    """
    Serializer para Centro Penitenciario con validaciones robustas
    """
    total_requisiciones = serializers.SerializerMethodField()
    total_usuarios = serializers.SerializerMethodField()
    
    class Meta:
        model = Centro
        fields = [
            'id', 'clave', 'nombre', 'tipo', 'direccion', 'telefono', 
            'responsable', 'activo', 'total_requisiciones', 'total_usuarios',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_total_requisiciones(self, obj):
        """
        Cuenta requisiciones reales del centro
        ✅ CORREGIDO: Ya no retorna 0 hardcodeado
        """
        return obj.requisiciones.count()
    
    def get_total_usuarios(self, obj):
        """Cuenta usuarios activos asignados al centro"""
        return obj.usuarios.filter(activo=True).count()
    
    def validate_clave(self, value):
        """
        Valida clave: normaliza, verifica unicidad y longitud
        """
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError(
                'La clave debe tener al menos 2 caracteres'
            )
        
        # Normalizar a mayúsculas
        value = value.upper().strip()
        
        # Validar unicidad (excluyendo instancia actual en updates)
        instance_id = self.instance.id if self.instance else None
        if Centro.objects.filter(clave__iexact=value).exclude(id=instance_id).exists():
            raise serializers.ValidationError(
                f'Ya existe un centro con la clave "{value}"'
            )
        
        return value
    
    def validate_nombre(self, value):
        """Valida nombre: longitud mínima"""
        if not value or len(value.strip()) < 5:
            raise serializers.ValidationError(
                'El nombre debe tener al menos 5 caracteres'
            )
        
        return value.strip()
    
    def validate_telefono(self, value):
        """Valida formato de teléfono"""
        if value:
            import re
            # Permitir solo números, guiones, espacios, paréntesis y +
            if not re.match(r'^[\d\s\-\+\(\)]+$', value):
                raise serializers.ValidationError(
                    'Formato de teléfono inválido. Solo números, espacios, guiones, + y paréntesis'
                )
        
        return value
    
    def validate(self, data):
        """Validaciones cruzadas"""
        # Validación adicional si es necesario
        return data

class ProductoSerializer(serializers.ModelSerializer):
    """
    Serializer robusto para Producto con validaciones completas
    """
    stock_actual = serializers.SerializerMethodField(
        help_text="Stock actual calculado de lotes disponibles"
    )
    nivel_stock = serializers.SerializerMethodField(
        help_text="Nivel de stock: critico, bajo, normal, alto"
    )
    lotes_activos = serializers.SerializerMethodField(
        help_text="Cantidad de lotes disponibles"
    )
    valor_inventario = serializers.SerializerMethodField(
        help_text="Valor total del inventario (stock * precio)"
    )
    creado_por = serializers.SerializerMethodField(
        help_text="Usuario que creó el producto"
    )
    
    class Meta:
        model = Producto
        fields = [
            'id', 'clave', 'descripcion', 'unidad_medida', 'precio_unitario',
            'stock_minimo', 'activo', 'stock_actual', 'nivel_stock',
            'lotes_activos', 'valor_inventario', 'created_at', 'updated_at',
            'creado_por'
        ]
        read_only_fields = ['created_at', 'updated_at', 'creado_por']
    
    def get_stock_actual(self, obj):
        """Calcula stock actual de lotes disponibles"""
        return obj.get_stock_actual()
    
    def get_nivel_stock(self, obj):
        """Retorna nivel de stock calculado"""
        return obj.get_nivel_stock()
    
    def get_lotes_activos(self, obj):
        """Cuenta lotes en estado disponible"""
        return obj.lotes.filter(estado='disponible').count()
    
    def get_valor_inventario(self, obj):
        """Calcula valor total del inventario"""
        stock = self.get_stock_actual(obj)
        return float(stock * obj.precio_unitario)
    
    def get_creado_por(self, obj):
        """Retorna el nombre/email del usuario que creó el producto"""
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None
    
    def validate_clave(self, value):
        """
        Valida clave: normaliza a mayúsculas, verifica unicidad y formato
        """
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError(
                'La clave debe tener al menos 3 caracteres'
            )
        
        # Normalizar a mayúsculas
        value = value.upper().strip()
        
        # Validar formato alfanumérico con guiones y guiones bajos
        import re
        if not re.match(r'^[A-Z0-9\-_]+$', value):
            raise serializers.ValidationError(
                'La clave solo puede contener letras, números, guiones y guiones bajos'
            )
        
        # Validar unicidad (excluyendo instancia actual en updates)
        instance_id = self.instance.id if self.instance else None
        if Producto.objects.filter(clave__iexact=value).exclude(id=instance_id).exists():
            raise serializers.ValidationError(
                f'Ya existe un producto con la clave "{value}"'
            )
        
        return value
    
    def validate(self, data):
        """
        Validaciones cross-field complejas
        """
        # Validar coherencia stock_minimo vs stock_actual
        if 'stock_minimo' in data:
            stock_min = data['stock_minimo']
            # Si se está creando, no hay stock actual aún
            if self.instance:
                stock_actual = self.instance.get_stock_actual()
                if stock_min > stock_actual and stock_actual > 0:
                    logger.warning(
                        f"Producto {self.instance.clave}: stock_minimo ({stock_min}) "
                        f"mayor que stock_actual ({stock_actual})"
                    )
        
        # Validar descripción no duplicada (warning, no error)
        if 'descripcion' in data:
            desc = data['descripcion']
            queryset = Producto.objects.filter(descripcion__iexact=desc)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                logger.warning(
                    f"Ya existe producto con descripción similar: {desc}"
                )
        
        # Validar que no se desactive un producto con stock si se proporciona activo=False
        if 'activo' in data and not data['activo'] and self.instance:
            stock_actual = self.instance.get_stock_actual()
            if stock_actual > 0:
                raise serializers.ValidationError({
                    'activo': f'No se puede desactivar un producto con {stock_actual} unidades en stock. Ajuste primero el inventario.'
                })
        
        return data
    
    def validate_descripcion(self, value):
        """Valida descripción: longitud y contenido"""
        value = value.strip()
        
        if len(value) < PRODUCTO_DESCRIPCION_MIN_LENGTH:
            raise serializers.ValidationError(
                f"La descripción debe tener al menos {PRODUCTO_DESCRIPCION_MIN_LENGTH} caracteres"
            )
        
        if len(value) > PRODUCTO_DESCRIPCION_MAX_LENGTH:
            raise serializers.ValidationError(
                f"La descripción no puede exceder {PRODUCTO_DESCRIPCION_MAX_LENGTH} caracteres"
            )
        
        return value
    
    def validate_precio_unitario(self, value):
        """Valida precio: debe ser positivo y con máximo 2 decimales"""
        from decimal import Decimal, InvalidOperation
        
        # ISS-006: Validar None explícitamente antes de conversión
        if value is None:
            raise serializers.ValidationError("El precio es requerido")
        
        # Convertir a Decimal si es float o string (ISS-006)
        if not isinstance(value, Decimal):
            try:
                value = Decimal(str(value))
            except (InvalidOperation, ValueError, TypeError):
                raise serializers.ValidationError("El precio debe ser un número válido")
        
        if value <= 0:
            raise serializers.ValidationError("El precio debe ser mayor a 0")
        
        # Validar máximo decimales permitidos
        if value.as_tuple().exponent < -PRODUCTO_PRECIO_DECIMAL_PLACES:
            raise serializers.ValidationError(
                f"El precio solo puede tener {PRODUCTO_PRECIO_DECIMAL_PLACES} decimales"
            )
        
        return value
    
    def validate_stock_minimo(self, value):
        """Valida stock mínimo: entero no negativo"""
        if value < 0:
            raise serializers.ValidationError("El stock mínimo no puede ser negativo")
        
        return value
    
    def validate_unidad_medida(self, value):
        """Valida que la unidad esté en las opciones permitidas"""
        unidades_validas = [u[0] for u in UNIDADES_MEDIDA]
        if value not in unidades_validas:
            raise serializers.ValidationError(
                f"Unidad inválida. Opciones: {', '.join(unidades_validas)}"
            )
        
        return value


class LoteSerializer(serializers.ModelSerializer):
    """
    Serializer para Lote con validaciones y campos calculados.
    Incluye información de vinculación farmacia -> centro.
    """
    # Campos del producto (read-only)
    producto_clave = serializers.CharField(source='producto.clave', read_only=True)
    producto_descripcion = serializers.CharField(source='producto.descripcion', read_only=True)
    producto_unidad = serializers.CharField(source='producto.unidad_medida', read_only=True)
    
    # Campos del centro (read-only)
    centro_id = serializers.IntegerField(source='centro.id', read_only=True, allow_null=True)
    centro_nombre = serializers.CharField(source='centro.nombre', read_only=True, allow_null=True)
    centro_clave = serializers.CharField(source='centro.clave', read_only=True, allow_null=True)
    
    # Campos de vinculación (lote_origen - trazabilidad farmacia->centro)
    lote_origen_id = serializers.IntegerField(source='lote_origen.id', read_only=True, allow_null=True)
    lote_origen_numero = serializers.CharField(source='lote_origen.numero_lote', read_only=True, allow_null=True)
    es_lote_farmacia = serializers.SerializerMethodField()
    tiene_derivados = serializers.SerializerMethodField()
    cantidad_derivados = serializers.SerializerMethodField()
    
    # Campos calculados (SerializerMethodField)
    dias_para_caducar = serializers.SerializerMethodField()
    porcentaje_consumido = serializers.SerializerMethodField()
    alerta_caducidad = serializers.SerializerMethodField()
    esta_caducado = serializers.SerializerMethodField()
    estado_visual = serializers.SerializerMethodField()
    stock_actual = serializers.IntegerField(source='cantidad_actual', read_only=True)
    ubicacion = serializers.SerializerMethodField()
    
    # Campo de documento PDF
    documento_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Lote
        fields = [
            'id', 'producto', 'producto_clave', 'producto_descripcion', 'producto_unidad',
            'numero_lote', 'fecha_caducidad', 'cantidad_inicial', 'cantidad_actual', 'stock_actual',
            'estado', 'precio_compra', 'proveedor', 'factura', 'fecha_entrada', 
            # Campos de trazabilidad de contratos
            'numero_contrato', 'marca',
            'observaciones', 'dias_para_caducar', 'porcentaje_consumido', 
            'alerta_caducidad', 'esta_caducado', 'estado_visual',
            # Campos de ubicación y vinculación
            'centro', 'centro_id', 'centro_nombre', 'centro_clave', 'ubicacion',
            'lote_origen', 'lote_origen_id', 'lote_origen_numero',
            'es_lote_farmacia', 'tiene_derivados', 'cantidad_derivados',
            # Campos de documento adjunto
            'documento_pdf', 'documento_nombre', 'documento_url',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'fecha_entrada']
    
    def get_dias_para_caducar(self, obj):
        """Calcula días restantes para caducidad"""
        return obj.dias_para_caducar()
    
    def get_porcentaje_consumido(self, obj):
        """Calcula porcentaje consumido del lote"""
        if obj.cantidad_inicial == 0:
            return 0
        return round(((obj.cantidad_inicial - obj.cantidad_actual) / obj.cantidad_inicial) * 100, 2)
    
    def get_alerta_caducidad(self, obj):
        """Nivel de alerta: vencido, critico, proximo, normal"""
        return obj.alerta_caducidad()
    
    def get_esta_caducado(self, obj):
        """Indica si el lote está vencido"""
        return obj.esta_caducado()
    
    def get_estado_visual(self, obj):
        """
        Estado visual combinado (caducidad + stock)
        Returns: {'tipo': 'danger|warning|success', 'mensaje': '...'}
        """
        if obj.esta_caducado():
            return {'tipo': 'danger', 'mensaje': 'VENCIDO'}
        
        alerta = obj.alerta_caducidad()
        if alerta == 'critico':
            return {'tipo': 'danger', 'mensaje': 'CADUCA EN 7 DÍAS'}
        elif alerta == 'proximo':
            return {'tipo': 'warning', 'mensaje': 'CADUCA EN 30 DÍAS'}
        
        if obj.cantidad_actual == 0:
            return {'tipo': 'warning', 'mensaje': 'AGOTADO'}
        elif obj.cantidad_actual <= obj.cantidad_inicial * 0.2:
            return {'tipo': 'warning', 'mensaje': 'STOCK BAJO'}
        
        return {'tipo': 'success', 'mensaje': 'VIGENTE'}
    
    def get_ubicacion(self, obj):
        """Indica si el lote está en farmacia central o en un centro"""
        if obj.centro:
            return {'tipo': 'centro', 'nombre': obj.centro.nombre, 'clave': obj.centro.clave}
        return {'tipo': 'farmacia', 'nombre': 'Farmacia Central', 'clave': 'CENTRAL'}
    
    def get_es_lote_farmacia(self, obj):
        """Indica si este es un lote de farmacia central (origen)"""
        return obj.centro is None
    
    def get_tiene_derivados(self, obj):
        """Indica si este lote de farmacia tiene lotes derivados en centros"""
        if obj.centro is None:  # Solo lotes de farmacia pueden tener derivados
            return obj.lotes_derivados.filter(deleted_at__isnull=True).exists()
        return False
    
    def get_cantidad_derivados(self, obj):
        """Cantidad de lotes derivados en centros (solo para lotes de farmacia)"""
        if obj.centro is None:
            return obj.lotes_derivados.filter(deleted_at__isnull=True).count()
        return 0
    
    def get_documento_url(self, obj):
        """Retorna la URL del documento PDF si existe"""
        if obj.documento_pdf:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.documento_pdf.url)
            return obj.documento_pdf.url
        return None
    
    def validate_numero_lote(self, value):
        """
        Valida número de lote: normaliza y verifica longitud
        """
        if not value or len(value.strip()) < LOTE_NUMERO_MIN_LENGTH:
            raise serializers.ValidationError(
                f'El número de lote debe tener al menos {LOTE_NUMERO_MIN_LENGTH} caracteres'
            )
        
        return value.strip().upper()
    
    def validate_fecha_caducidad(self, value):
        """Valida que la fecha de caducidad sea futura"""
        from datetime import date
        if value and value < date.today():
            raise serializers.ValidationError(
                "La fecha de caducidad no puede ser anterior a hoy"
            )
        
        return value
    
    def validate_cantidad_inicial(self, value):
        """Valida cantidad inicial positiva"""
        if value < 1:
            raise serializers.ValidationError("La cantidad inicial debe ser al menos 1")
        return value
    
    def validate_cantidad_actual(self, value):
        """Valida cantidad actual no negativa"""
        if value < 0:
            raise serializers.ValidationError("La cantidad actual no puede ser negativa")
        return value
    
    def validate_precio_compra(self, value):
        """Valida precio de compra no negativo"""
        if value and value < 0:
            raise serializers.ValidationError("El precio de compra no puede ser negativo")
        return value
    
    def validate(self, data):
        """Validaciones cruzadas"""
        # Validar cantidad actual <= cantidad inicial
        cantidad_inicial = data.get('cantidad_inicial') or (
            self.instance.cantidad_inicial if self.instance else 0
        )
        cantidad_actual = data.get('cantidad_actual')
        
        if cantidad_actual and cantidad_actual > cantidad_inicial:
            raise serializers.ValidationError({
                'cantidad_actual': 'La cantidad actual no puede ser mayor a la inicial'
            })
        
        # Validar unicidad de número de lote por producto Y centro
        # La constraint es: (producto, numero_lote, centro) debe ser único
        producto = data.get('producto') or (self.instance.producto if self.instance else None)
        numero_lote = data.get('numero_lote')
        centro = data.get('centro')  # None = farmacia central
        
        if producto and numero_lote:
            queryset = Lote.objects.filter(
                producto=producto, 
                numero_lote__iexact=numero_lote,
                centro=centro,  # Mismo centro (o farmacia si None)
                deleted_at__isnull=True  # Excluir eliminados
            )
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                ubicacion = centro.nombre if centro else 'Farmacia Central'
                raise serializers.ValidationError({
                    'numero_lote': f'Ya existe el lote {numero_lote} para este producto en {ubicacion}'
                })
        
        return data

    def to_representation(self, instance):
        """
        Filtra campos de contrato según rol del usuario.
        Solo ADMIN y FARMACIA pueden ver numero_contrato y marca.
        """
        data = super().to_representation(instance)
        
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            user = request.user
            # Superuser o staff siempre ven todo
            if user.is_superuser or user.is_staff:
                return data
            
            # Verificar rol del usuario
            rol = getattr(user, 'rol', None)
            if rol not in ['ADMIN', 'FARMACIA']:
                # Ocultar campos de contrato para roles sin permisos
                data.pop('numero_contrato', None)
                data.pop('marca', None)
        else:
            # Usuario no autenticado o sin request, ocultar campos sensibles
            data.pop('numero_contrato', None)
            data.pop('marca', None)
        
        return data
class DetalleRequisicionSerializer(serializers.ModelSerializer):
    """
    Serializer para detalle de requisición con validaciones.
    Cada detalle está asociado a un producto y un lote específico.
    """
    producto_clave = serializers.CharField(source='producto.clave', read_only=True)
    producto_descripcion = serializers.CharField(source='producto.descripcion', read_only=True)
    producto_unidad = serializers.CharField(source='producto.unidad_medida', read_only=True)
    # Información del lote asociado
    lote_numero = serializers.CharField(source='lote.numero_lote', read_only=True, allow_null=True)
    lote_caducidad = serializers.SerializerMethodField()
    lote_stock = serializers.SerializerMethodField()
    stock_disponible = serializers.SerializerMethodField()
    
    class Meta:
        model = DetalleRequisicion
        fields = [
            'id', 'producto', 'lote', 'producto_clave', 'producto_descripcion', 'producto_unidad',
            'lote_numero', 'lote_caducidad', 'lote_stock',
            'cantidad_solicitada', 'cantidad_autorizada', 'cantidad_surtida', 
            'observaciones', 'stock_disponible'
        ]
    
    def get_stock_disponible(self, obj):
        """Calcula stock disponible del producto (total de todos los lotes)"""
        return obj.producto.get_stock_actual()
    
    def get_lote_caducidad(self, obj):
        """Fecha de caducidad del lote asociado"""
        if obj.lote and obj.lote.fecha_caducidad:
            return obj.lote.fecha_caducidad.strftime('%d/%m/%Y')
        return None
    
    def get_lote_stock(self, obj):
        """Stock disponible del lote específico"""
        if obj.lote:
            return obj.lote.cantidad_actual
        return None
    
    def validate_cantidad_solicitada(self, value):
        """Valida cantidad solicitada > 0"""
        if value <= 0:
            raise serializers.ValidationError('La cantidad solicitada debe ser mayor a 0')
        
        return value
    
    def validate_cantidad_autorizada(self, value):
        """Valida cantidad autorizada"""
        if value is not None and value < 0:
            raise serializers.ValidationError('La cantidad autorizada no puede ser negativa')
        
        return value
    
    def validate(self, data):
        """Validaciones cruzadas"""
        cantidad_solicitada = data.get('cantidad_solicitada')
        cantidad_autorizada = data.get('cantidad_autorizada', 0)
        producto = data.get('producto') or (self.instance.producto if self.instance else None)
        lote = data.get('lote') or (self.instance.lote if self.instance else None)
        
        # Validar que el producto esté activo
        if producto and not producto.activo:
            raise serializers.ValidationError({
                'producto': f'El producto {producto.clave} está inactivo y no puede ser solicitado'
            })
        
        # Validar que el lote pertenezca al producto
        if lote and producto and lote.producto_id != producto.id:
            raise serializers.ValidationError({
                'lote': 'El lote no corresponde al producto seleccionado'
            })
        
        # Validar que autorizada no exceda solicitada
        if cantidad_autorizada and cantidad_autorizada > cantidad_solicitada:
            raise serializers.ValidationError({
                'cantidad_autorizada': 'No puede exceder la cantidad solicitada'
            })
        
        # Validar que no exceda el stock del lote
        if lote and cantidad_solicitada:
            if cantidad_solicitada > lote.cantidad_actual:
                raise serializers.ValidationError({
                    'cantidad_solicitada': f'No puede exceder el stock del lote ({lote.cantidad_actual} disponibles)'
                })
        
        # Validar stock disponible (solo en autorización)
        if cantidad_autorizada and cantidad_autorizada > 0:
            producto = data.get('producto') or (self.instance.producto if self.instance else None)
            if producto:
                stock = producto.get_stock_actual()
                if cantidad_autorizada > stock:
                    raise serializers.ValidationError({
                        'cantidad_autorizada': f'Stock insuficiente. Disponible: {stock}'
                    })
        
        return data


class RequisicionSerializer(serializers.ModelSerializer):
    """
    Serializer para Requisición con validaciones de flujo
    ✅ CORREGIDO: Ahora permite editar detalles
    """
    detalles = DetalleRequisicionSerializer(many=True, required=False)
    centro_nombre = serializers.CharField(source='centro.nombre', read_only=True)
    usuario_solicita_nombre = serializers.CharField(source='usuario_solicita.get_full_name', read_only=True)
    usuario_autoriza_nombre = serializers.CharField(source='usuario_autoriza.get_full_name', read_only=True)
    usuario_recibe_nombre = serializers.CharField(source='usuario_recibe.get_full_name', read_only=True, allow_null=True)
    total_productos = serializers.SerializerMethodField()
    puede_editar = serializers.SerializerMethodField()
    
    # Transiciones válidas de estado
    TRANSICIONES_VALIDAS = {
        'borrador': ['enviada', 'cancelada'],
        'enviada': ['autorizada', 'parcial', 'rechazada', 'cancelada'],
        'autorizada': ['surtida', 'cancelada'],
        'parcial': ['autorizada', 'surtida', 'cancelada'],
        'rechazada': ['cancelada'],
        'surtida': ['recibida'],
        'recibida': [],
        'cancelada': []
    }
    
    class Meta:
        model = Requisicion
        fields = [
            'id', 'folio', 'centro', 'centro_nombre', 'usuario_solicita', 
            'usuario_solicita_nombre', 'fecha_solicitud', 'estado', 'observaciones',
            'usuario_autoriza', 'usuario_autoriza_nombre', 'fecha_autorizacion',
            'motivo_rechazo', 'detalles', 'total_productos', 'puede_editar',
            # Campos de recepción
            'lugar_entrega', 'fecha_recibido', 'usuario_recibe', 'usuario_recibe_nombre',
            'observaciones_recepcion',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['folio', 'fecha_solicitud', 'created_at', 'updated_at']
    
    def get_total_productos(self, obj):
        """Cuenta productos en la requisición"""
        return obj.detalles.count()
    
    def get_puede_editar(self, obj):
        """Indica si la requisición puede editarse"""
        return obj.estado in ['borrador', 'enviada']
    
    def validate_estado(self, value):
        """Valida transiciones de estado"""
        if self.instance:
            estado_actual = self.instance.estado
            if value not in self.TRANSICIONES_VALIDAS.get(estado_actual, []):
                raise serializers.ValidationError(
                    f'No se puede cambiar de {estado_actual} a {value}. '
                    f'Transiciones válidas: {", ".join(self.TRANSICIONES_VALIDAS[estado_actual])}'
                )
        
        return value
    
    def create(self, validated_data):
        """
        Crea requisición con detalles.
        NOTA: El folio se genera automáticamente en el modelo Requisicion.save()
        con formato REQ-CENTRO-YYYYMMDD-NNNN para evitar duplicados.
        """
        detalles_data = validated_data.pop('detalles', [])
        
        # NO generar folio aquí - el modelo lo hace en save() con transacción segura
        # El modelo genera: REQ-{centro}-{fecha}-{numero}
        
        requisicion = Requisicion.objects.create(**validated_data)
        
        # Crear detalles
        for detalle_data in detalles_data:
            DetalleRequisicion.objects.create(requisicion=requisicion, **detalle_data)
        
        logger.info(f"Requisición {requisicion.folio} creada con {len(detalles_data)} productos")
        return requisicion
    
    def update(self, instance, validated_data):
        """
        Actualiza requisición y detalles
        ✅ CORREGIDO: Ahora permite actualizar detalles
        """
        detalles_data = validated_data.pop('detalles', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Actualizar detalles si se proporcionan
        if detalles_data is not None:
            # Eliminar detalles existentes
            instance.detalles.all().delete()
            
            
            # Crear nuevos detalles
            for detalle_data in detalles_data:
                DetalleRequisicion.objects.create(requisicion=instance, **detalle_data)
        
        logger.info(f"Requisición {instance.folio} actualizada")
        return instance

class MovimientoSerializer(serializers.ModelSerializer):
    lote_numero = serializers.CharField(source='lote.numero_lote', read_only=True)
    producto_clave = serializers.CharField(source='lote.producto.clave', read_only=True)
    producto_descripcion = serializers.CharField(source='lote.producto.descripcion', read_only=True)
    centro_nombre = serializers.CharField(source='centro.nombre', read_only=True)
    usuario_nombre = serializers.CharField(source='usuario.get_full_name', read_only=True)
    requisicion_folio = serializers.CharField(source='requisicion.folio', read_only=True)
    
    class Meta:
        model = Movimiento
        fields = ['id', 'tipo', 'lote', 'lote_numero', 'producto_clave', 'producto_descripcion',
                  'centro', 'centro_nombre', 'cantidad', 'usuario', 'usuario_nombre',
                  'requisicion', 'requisicion_folio', 'documento_referencia', 'observaciones', 
                  'lugar_entrega', 'fecha']
        read_only_fields = ['fecha']


class NotificacionSerializer(serializers.ModelSerializer):
    requisicion_folio = serializers.CharField(source='requisicion.folio', read_only=True)

    class Meta:
        model = Notificacion
        fields = ['id', 'titulo', 'mensaje', 'tipo', 'leida', 'fecha_creacion', 'requisicion', 'requisicion_folio']
        read_only_fields = ['fecha_creacion']

class AuditoriaLogSerializer(serializers.ModelSerializer):
    """Serializer para logs de auditoría"""
    usuario_nombre = serializers.SerializerMethodField()
    descripcion = serializers.SerializerMethodField()
    ip_address = serializers.CharField(read_only=True, allow_null=True)
    
    class Meta:
        model = AuditoriaLog
        fields = [
            'id', 'usuario', 'usuario_nombre', 'accion', 'modelo', 
            'objeto_id', 'objeto_repr', 'descripcion', 'cambios', 'ip_address', 'fecha'
        ]
        read_only_fields = fields
    
    def get_usuario_nombre(self, obj):
        """Obtiene el nombre del usuario o 'Sistema' si es nulo"""
        if obj.usuario:
            nombre = obj.usuario.get_full_name()
            return nombre if nombre else obj.usuario.username
        return 'Sistema'
    
    def get_descripcion(self, obj):
        """Genera una descripción legible de la acción"""
        accion_dict = {
            'CREATE': 'creó',
            'UPDATE': 'actualizó',
            'DELETE': 'eliminó',
            'LOGIN': 'inició sesión',
            'LOGOUT': 'cerró sesión'
        }
        accion_texto = accion_dict.get(obj.accion, obj.accion)
        
        if obj.accion in ['LOGIN', 'LOGOUT']:
            return f"{accion_texto} en el sistema"
        
        return f"{accion_texto} {obj.modelo}: {obj.objeto_repr}"


class ImportacionLogSerializer(serializers.ModelSerializer):
    """Serializer liviano para auditoría de importaciones."""
    usuario_nombre = serializers.CharField(source='usuario.username', read_only=True, default=None)
    
    class Meta:
        model = ImportacionLog
        fields = [
            'id', 'archivo_nombre', 'modelo', 'total_registros',
            'registros_exitosos', 'registros_fallidos', 'estado',
            'resultado_procesamiento', 'fecha_importacion', 'usuario_nombre'
        ]
        read_only_fields = fields


class UserMeSerializer(serializers.ModelSerializer):
    """Serializer especializado para /usuarios/me/ (lectura/edición)."""
    centro_nombre = serializers.CharField(source='centro.nombre', read_only=True)
    grupos = serializers.SerializerMethodField()
    extra_permisos = serializers.SerializerMethodField()
    permisos = serializers.SerializerMethodField()
    telefono = serializers.CharField(source='profile.telefono', allow_blank=True, required=False)
    cargo = serializers.CharField(source='profile.cargo', allow_blank=True, required=False)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'rol', 'centro', 'centro_nombre', 'telefono', 'cargo',
            'adscripcion',  # Campo de adscripción
            'grupos', 'extra_permisos', 'permisos',
            'is_superuser', 'is_staff',  # Importante para el frontend
        ]
        read_only_fields = ['username', 'rol', 'centro', 'is_superuser', 'is_staff']

    def get_grupos(self, obj):
        return [g.name for g in obj.groups.all()]

    def get_extra_permisos(self, obj):
        group_names = set(g.name for g in obj.groups.all())
        return [perm for perm in EXTRA_PERMISSIONS if perm in group_names]

    def get_permisos(self, obj):
        return build_perm_map(obj)

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if profile_data:
            profile, _ = UserProfile.objects.get_or_create(user=instance)
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()

        return instance


class ConfiguracionSistemaSerializer(serializers.ModelSerializer):
    """
    Serializer para la configuración global del sistema.
    Solo superusuarios pueden modificar.
    """
    css_variables = serializers.SerializerMethodField(
        help_text="Variables CSS para aplicar directamente en el frontend"
    )
    updated_by_nombre = serializers.CharField(
        source='updated_by.get_full_name', 
        read_only=True
    )
    temas_disponibles = serializers.SerializerMethodField()
    logo_header_url = serializers.SerializerMethodField()
    logo_pdf_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ConfiguracionSistema
        fields = [
            'id', 'nombre_sistema', 'logo_url', 'tema_activo',
            # Campos de identidad institucional
            'nombre_institucion', 'subtitulo_institucion',
            'logo_header', 'logo_header_url', 'logo_pdf', 'logo_pdf_url',
            # Colores principales
            'color_primario', 'color_primario_hover', 'color_secundario', 'color_acento',
            # Colores de fondo
            'color_fondo', 'color_fondo_sidebar', 'color_fondo_header', 'color_fondo_card',
            # Colores de texto
            'color_texto', 'color_texto_secundario', 'color_texto_sidebar', 'color_texto_header',
            # Colores de estados
            'color_exito', 'color_advertencia', 'color_error', 'color_info',
            # Meta
            'css_variables', 'temas_disponibles',
            'updated_at', 'updated_by', 'updated_by_nombre',
        ]
        read_only_fields = ['id', 'updated_at', 'css_variables', 'temas_disponibles', 'logo_header_url', 'logo_pdf_url']
    
    def get_css_variables(self, obj):
        """Retorna las variables CSS para inyectar en el frontend"""
        return obj.to_css_variables()
    
    def get_temas_disponibles(self, obj):
        """Retorna la lista de temas predefinidos disponibles"""
        return [
            {'id': tema[0], 'nombre': tema[1]} 
            for tema in ConfiguracionSistema.TEMAS_PREDEFINIDOS
        ]
    
    def get_logo_header_url(self, obj):
        """Retorna la URL del logo del header si existe"""
        if obj.logo_header:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo_header.url)
            return obj.logo_header.url
        return None
    
    def get_logo_pdf_url(self, obj):
        """Retorna la URL del logo para PDF si existe"""
        if obj.logo_pdf:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo_pdf.url)
            return obj.logo_pdf.url
        return None
    
    def validate_tema_activo(self, value):
        """Valida que el tema sea válido"""
        temas_validos = [t[0] for t in ConfiguracionSistema.TEMAS_PREDEFINIDOS]
        if value not in temas_validos:
            raise serializers.ValidationError(
                f"Tema inválido. Opciones: {', '.join(temas_validos)}"
            )
        return value
    
    def update(self, instance, validated_data):
        """
        Actualiza la configuración.
        Si se cambia tema_activo a uno predefinido, aplica los colores del tema.
        """
        tema_nuevo = validated_data.get('tema_activo')
        
        # Si se selecciona un tema predefinido (no 'custom'), aplicar sus colores
        if tema_nuevo and tema_nuevo != 'custom' and tema_nuevo != instance.tema_activo:
            ConfiguracionSistema.aplicar_tema_predefinido(tema_nuevo)
            # Recargar la instancia
            instance.refresh_from_db()
            # Ahora aplicar cualquier otro campo que se haya enviado
            for attr, value in validated_data.items():
                if attr != 'tema_activo':  # Ya aplicamos el tema
                    setattr(instance, attr, value)
            instance.save()
        else:
            # Actualización normal
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            # Si se modifican colores manualmente, cambiar a 'custom'
            campos_color = [f for f in validated_data.keys() if f.startswith('color_')]
            if campos_color and validated_data.get('tema_activo') != 'custom':
                instance.tema_activo = 'custom'
            instance.save()
        
        return instance


class DetalleHojaRecoleccionSerializer(serializers.ModelSerializer):
    """Serializer para detalle de hoja de recolección"""
    producto_clave = serializers.CharField(source='producto.clave', read_only=True)
    producto_descripcion = serializers.CharField(source='producto.descripcion', read_only=True)
    producto_unidad = serializers.CharField(source='producto.unidad_medida', read_only=True)
    lote_numero = serializers.CharField(source='lote_asignado.numero_lote', read_only=True, default=None)
    
    class Meta:
        model = DetalleHojaRecoleccion
        fields = [
            'id', 'producto', 'producto_clave', 'producto_descripcion', 'producto_unidad',
            'cantidad_autorizada', 'cantidad_entregada', 'lote_asignado', 'lote_numero',
            'observaciones'
        ]


class HojaRecoleccionSerializer(serializers.ModelSerializer):
    """
    Serializer para Hoja de Recolección.
    Incluye información de seguridad y verificación.
    """
    detalles = DetalleHojaRecoleccionSerializer(many=True, read_only=True)
    requisicion_folio = serializers.CharField(source='requisicion.folio', read_only=True)
    centro_nombre = serializers.CharField(source='requisicion.centro.nombre', read_only=True)
    centro_clave = serializers.CharField(source='requisicion.centro.clave', read_only=True)
    generado_por_nombre = serializers.CharField(source='generado_por.get_full_name', read_only=True)
    verificado_por_nombre = serializers.CharField(source='verificado_por.get_full_name', read_only=True)
    integridad_valida = serializers.SerializerMethodField()
    productos_resumen = serializers.SerializerMethodField()
    
    class Meta:
        model = HojaRecoleccion
        fields = [
            'id', 'folio_hoja', 'requisicion', 'requisicion_folio',
            'centro_nombre', 'centro_clave', 'estado', 'hash_contenido',
            'contenido_json', 'fecha_generacion', 'fecha_impresion', 'fecha_verificacion',
            'generado_por', 'generado_por_nombre', 'verificado_por', 'verificado_por_nombre',
            'veces_impresa', 'veces_descargada', 'observaciones',
            'integridad_valida', 'productos_resumen', 'detalles'
        ]
        read_only_fields = [
            'folio_hoja', 'hash_contenido', 'fecha_generacion', 
            'veces_impresa', 'veces_descargada'
        ]
    
    def get_integridad_valida(self, obj):
        """Verifica si el contenido no ha sido alterado"""
        return obj.verificar_integridad()
    
    def get_productos_resumen(self, obj):
        """Resumen de productos de la hoja"""
        if not obj.contenido_json or 'detalles' not in obj.contenido_json:
            return []
        return obj.contenido_json.get('detalles', [])


# ============================================================================
# SERIALIZERS PARA TEMA GLOBAL
# ============================================================================
from .models import TemaGlobal


class TemaGlobalSerializer(serializers.ModelSerializer):
    """
    Serializer completo para TemaGlobal.
    Incluye URLs de imagenes y configuracion JSON para el frontend.
    """
    logo_header_url = serializers.SerializerMethodField()
    logo_login_url = serializers.SerializerMethodField()
    logo_reportes_url = serializers.SerializerMethodField()
    favicon_url = serializers.SerializerMethodField()
    imagen_fondo_login_url = serializers.SerializerMethodField()
    imagen_fondo_reportes_url = serializers.SerializerMethodField()
    
    css_variables = serializers.SerializerMethodField()
    config_completa = serializers.SerializerMethodField()
    
    creado_por_nombre = serializers.CharField(source='creado_por.get_full_name', read_only=True)
    modificado_por_nombre = serializers.CharField(source='modificado_por.get_full_name', read_only=True)
    
    class Meta:
        model = TemaGlobal
        fields = [
            'id', 'nombre', 'descripcion', 'activo', 'es_tema_institucional',
            # Logos
            'logo_header', 'logo_header_url',
            'logo_login', 'logo_login_url',
            'logo_reportes', 'logo_reportes_url',
            'favicon', 'favicon_url',
            'imagen_fondo_login', 'imagen_fondo_login_url',
            'imagen_fondo_reportes', 'imagen_fondo_reportes_url',
            # Colores principales
            'color_primario', 'color_primario_hover',
            'color_secundario', 'color_secundario_hover',
            # Colores de estado
            'color_exito', 'color_error', 'color_advertencia', 'color_info',
            # Colores de fondo
            'color_fondo_principal', 'color_fondo_tarjetas',
            'color_fondo_sidebar', 'color_fondo_header',
            # Colores de texto
            'color_texto_principal', 'color_texto_secundario',
            'color_texto_invertido', 'color_texto_links',
            # Colores de bordes
            'color_borde', 'color_borde_focus',
            # Tipografia
            'fuente_principal', 'fuente_titulos',
            'tamano_h1', 'tamano_h2', 'tamano_h3',
            'tamano_texto_base', 'tamano_texto_pequeno',
            'tamano_etiquetas', 'tamano_botones',
            'peso_titulos', 'peso_texto_normal', 'peso_botones',
            # Reportes
            'reporte_ano_visible', 'reporte_titulo_institucion',
            'reporte_subtitulo', 'reporte_pie_pagina',
            'reporte_color_encabezado', 'reporte_color_texto_encabezado',
            'reporte_color_filas_alternas',
            # Estilos
            'border_radius_base', 'border_radius_botones', 'shadow_base',
            # Computed
            'css_variables', 'config_completa',
            # Auditoria
            'creado_por', 'creado_por_nombre',
            'modificado_por', 'modificado_por_nombre',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['es_tema_institucional', 'created_at', 'updated_at']
    
    def get_logo_header_url(self, obj):
        if obj.logo_header:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo_header.url)
            return obj.logo_header.url
        return None
    
    def get_logo_login_url(self, obj):
        if obj.logo_login:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo_login.url)
            return obj.logo_login.url
        return None
    
    def get_logo_reportes_url(self, obj):
        if obj.logo_reportes:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo_reportes.url)
            return obj.logo_reportes.url
        return None
    
    def get_favicon_url(self, obj):
        if obj.favicon:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.favicon.url)
            return obj.favicon.url
        return None
    
    def get_imagen_fondo_login_url(self, obj):
        if obj.imagen_fondo_login:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.imagen_fondo_login.url)
            return obj.imagen_fondo_login.url
        return None
    
    def get_imagen_fondo_reportes_url(self, obj):
        if obj.imagen_fondo_reportes:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.imagen_fondo_reportes.url)
            return obj.imagen_fondo_reportes.url
        return None
    
    def get_css_variables(self, obj):
        return obj.to_css_variables()
    
    def get_config_completa(self, obj):
        return obj.to_json_config()


class TemaGlobalPublicoSerializer(serializers.ModelSerializer):
    """
    Serializer publico para TemaGlobal (sin campos de auditoria).
    Usado para el endpoint publico que cualquier usuario puede consultar.
    """
    logo_header_url = serializers.SerializerMethodField()
    logo_login_url = serializers.SerializerMethodField()
    logo_reportes_url = serializers.SerializerMethodField()
    favicon_url = serializers.SerializerMethodField()
    imagen_fondo_login_url = serializers.SerializerMethodField()
    
    css_variables = serializers.SerializerMethodField()
    
    class Meta:
        model = TemaGlobal
        fields = [
            'id', 'nombre',
            # URLs de imagenes
            'logo_header_url', 'logo_login_url', 'logo_reportes_url',
            'favicon_url', 'imagen_fondo_login_url',
            # Colores
            'color_primario', 'color_primario_hover',
            'color_secundario', 'color_secundario_hover',
            'color_exito', 'color_error', 'color_advertencia', 'color_info',
            'color_fondo_principal', 'color_fondo_tarjetas',
            'color_fondo_sidebar', 'color_fondo_header',
            'color_texto_principal', 'color_texto_secundario',
            'color_texto_invertido', 'color_texto_links',
            'color_borde', 'color_borde_focus',
            # Tipografia
            'fuente_principal', 'fuente_titulos',
            'tamano_h1', 'tamano_h2', 'tamano_h3',
            'tamano_texto_base', 'tamano_texto_pequeno',
            'tamano_etiquetas', 'tamano_botones',
            'peso_titulos', 'peso_texto_normal', 'peso_botones',
            # Reportes (solo lo necesario para UI)
            'reporte_ano_visible', 'reporte_titulo_institucion',
            # Estilos
            'border_radius_base', 'border_radius_botones', 'shadow_base',
            # CSS variables
            'css_variables',
            'updated_at',
        ]
    
    def get_logo_header_url(self, obj):
        if obj.logo_header:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo_header.url)
            return obj.logo_header.url
        return None
    
    def get_logo_login_url(self, obj):
        if obj.logo_login:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo_login.url)
            return obj.logo_login.url
        return None
    
    def get_logo_reportes_url(self, obj):
        if obj.logo_reportes:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo_reportes.url)
            return obj.logo_reportes.url
        return None
    
    def get_favicon_url(self, obj):
        if obj.favicon:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.favicon.url)
            return obj.favicon.url
        return None
    
    def get_imagen_fondo_login_url(self, obj):
        if obj.imagen_fondo_login:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.imagen_fondo_login.url)
            return obj.imagen_fondo_login.url
        return None
    
    def get_css_variables(self, obj):
        return obj.to_css_variables()

