from rest_framework import serializers
from django.db.models import Sum
from .models import User, Centro, Producto, Lote, Requisicion, DetalleRequisicion, Movimiento, AuditoriaLog, ImportacionLog
from .constants import *
import logging

logger = logging.getLogger(__name__)


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer para Usuario con validaciones robustas
    """
    centro_nombre = serializers.CharField(source='centro.nombre', read_only=True)
    password = serializers.CharField(write_only=True, required=False, style={'input_type': 'password'})
    grupos = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'rol', 'centro', 'centro_nombre', 'activo', 'password', 
            'grupos',
            'date_joined', 'last_login'
        ]
        read_only_fields = ['date_joined', 'last_login']
        extra_kwargs = {
            'password': {'write_only': True, 'required': False}
        }

    def get_grupos(self, obj):
        return [g.name for g in obj.groups.all()]
    
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
    
    class Meta:
        model = Producto
        fields = [
            'id', 'clave', 'descripcion', 'unidad_medida', 'precio_unitario',
            'stock_minimo', 'activo', 'stock_actual', 'nivel_stock',
            'lotes_activos', 'valor_inventario', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
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
    
    def validate_clave(self, value):
        """
        Valida clave: normaliza a mayúsculas, verifica unicidad case-insensitive
        """
        value = value.upper().strip()
        
        # Validar longitud
        if len(value) < PRODUCTO_CLAVE_MIN_LENGTH:
            raise serializers.ValidationError(
                f"La clave debe tener al menos {PRODUCTO_CLAVE_MIN_LENGTH} caracteres"
            )
        
        # Validar unicidad case-insensitive (excluyendo instancia actual en updates)
        queryset = Producto.objects.filter(clave__iexact=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise serializers.ValidationError(
                f"Ya existe un producto con la clave '{value}'"
            )
        
        return value
    
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
        """Valida precio: debe ser positivo"""
        if value <= 0:
            raise serializers.ValidationError("El precio debe ser mayor a 0")
        
        # Validar máximo 2 decimales
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
    Serializer para Lote con validaciones y campos calculados
    """
    # Campos del producto (read-only)
    producto_clave = serializers.CharField(source='producto.clave', read_only=True)
    producto_descripcion = serializers.CharField(source='producto.descripcion', read_only=True)
    producto_unidad = serializers.CharField(source='producto.unidad_medida', read_only=True)
    
    # Campos calculados (SerializerMethodField)
    dias_para_caducar = serializers.SerializerMethodField()
    porcentaje_consumido = serializers.SerializerMethodField()
    alerta_caducidad = serializers.SerializerMethodField()
    esta_caducado = serializers.SerializerMethodField()
    estado_visual = serializers.SerializerMethodField()
    
    class Meta:
        model = Lote
        fields = [
            'id', 'producto', 'producto_clave', 'producto_descripcion', 'producto_unidad',
            'numero_lote', 'fecha_caducidad', 'cantidad_inicial', 'cantidad_actual',
            'estado', 'precio_compra', 'proveedor', 'factura', 'fecha_entrada', 
            'observaciones', 'dias_para_caducar', 'porcentaje_consumido', 
            'alerta_caducidad', 'esta_caducado', 'estado_visual',
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
        
        # Validar unicidad de número de lote por producto
        producto = data.get('producto') or (self.instance.producto if self.instance else None)
        numero_lote = data.get('numero_lote')
        
        if producto and numero_lote:
            queryset = Lote.objects.filter(
                producto=producto, 
                numero_lote__iexact=numero_lote,
                deleted_at__isnull=True  # Excluir eliminados
            )
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise serializers.ValidationError({
                    'numero_lote': f'Ya existe el lote {numero_lote} para este producto'
                })
        
        return data

class DetalleRequisicionSerializer(serializers.ModelSerializer):
    """
    Serializer para detalle de requisición con validaciones
    ✅ CORREGIDO: Ahora es editable (no READ_ONLY)
    """
    producto_clave = serializers.CharField(source='producto.clave', read_only=True)
    producto_descripcion = serializers.CharField(source='producto.descripcion', read_only=True)
    producto_unidad = serializers.CharField(source='producto.unidad_medida', read_only=True)
    stock_disponible = serializers.SerializerMethodField()
    
    class Meta:
        model = DetalleRequisicion
        fields = [
            'id', 'producto', 'producto_clave', 'producto_descripcion', 'producto_unidad',
            'cantidad_solicitada', 'cantidad_autorizada', 'cantidad_surtida', 
            'observaciones', 'stock_disponible'
        ]
    
    def get_stock_disponible(self, obj):
        """Calcula stock disponible del producto"""
        return obj.producto.get_stock_actual()
    
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
        
        # Validar que autorizada no exceda solicitada
        if cantidad_autorizada and cantidad_autorizada > cantidad_solicitada:
            raise serializers.ValidationError({
                'cantidad_autorizada': 'No puede exceder la cantidad solicitada'
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
    total_productos = serializers.SerializerMethodField()
    puede_editar = serializers.SerializerMethodField()
    
    # Transiciones válidas de estado
    TRANSICIONES_VALIDAS = {
        'borrador': ['enviada', 'cancelada'],
        'enviada': ['autorizada', 'parcial', 'rechazada', 'cancelada'],
        'autorizada': ['surtida', 'cancelada'],
        'parcial': ['autorizada', 'surtida', 'cancelada'],
        'rechazada': ['cancelada'],
        'surtida': [],
        'cancelada': []
    }
    
    class Meta:
        model = Requisicion
        fields = [
            'id', 'folio', 'centro', 'centro_nombre', 'usuario_solicita', 
            'usuario_solicita_nombre', 'fecha_solicitud', 'estado', 'observaciones',
            'usuario_autoriza', 'usuario_autoriza_nombre', 'fecha_autorizacion',
            'motivo_rechazo', 'detalles', 'total_productos', 'puede_editar',
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
        Crea requisición con detalles
        ✅ CORREGIDO: Ahora procesa detalles
        """
        detalles_data = validated_data.pop('detalles', [])
        
        # Generar folio automático
        ultimo_folio = Requisicion.objects.order_by('-id').first()
        if ultimo_folio:
            numero = int(ultimo_folio.folio.split('-')[1]) + 1
        else:
            numero = 1
        validated_data['folio'] = f"REQ-{numero:06d}"
        
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
                  'requisicion', 'requisicion_folio', 'observaciones', 'fecha']
        read_only_fields = ['fecha']

class AuditoriaLogSerializer(serializers.ModelSerializer):
    """Serializer para logs de auditoría"""
    usuario_nombre = serializers.CharField(source='usuario.get_full_name', read_only=True)
    descripcion = serializers.SerializerMethodField()
    
    class Meta:
        model = AuditoriaLog
        fields = [
            'id', 'usuario', 'usuario_nombre', 'accion', 'modelo', 
            'objeto_id', 'objeto_repr', 'descripcion', 'cambios', 'ip_address', 'fecha'
        ]
        read_only_fields = ['__all__']
    
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
