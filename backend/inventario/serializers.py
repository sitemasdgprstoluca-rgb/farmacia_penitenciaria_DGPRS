from rest_framework import serializers
from core.models import (
    Producto, Lote, Movimiento, Centro,
    Requisicion, DetalleRequisicion, AuditoriaLog
)
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()

class ProductoSerializer(serializers.ModelSerializer):
    stock_total = serializers.SerializerMethodField()
    lotes_activos = serializers.SerializerMethodField()
    alerta_stock = serializers.SerializerMethodField()
    nivel_stock = serializers.SerializerMethodField()
    creado_por = serializers.CharField(
        source='created_by.get_full_name',
        read_only=True,
        default=None
    )
    
    class Meta:
        model = Producto
        fields = [
            'id', 'clave', 'descripcion', 'unidad_medida',
            'precio_unitario', 'stock_minimo', 'activo',
            'stock_total', 'lotes_activos', 'alerta_stock', 'nivel_stock',
            'creado_por', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'stock_total', 'lotes_activos', 'alerta_stock', 'nivel_stock',
            'creado_por'
        ]
    
    def get_stock_total(self, obj):
        """Calcula el stock total considerando lotes disponibles"""
        from django.db.models import Sum
        total = obj.lotes.filter(
            deleted_at__isnull=True,
            cantidad_actual__gt=0
        ).aggregate(total=Sum('cantidad_actual'))['total']
        return float(total) if total else 0.0
    
    def get_lotes_activos(self, obj):
        """Cuenta lotes con existencias disponibles"""
        return obj.lotes.filter(
            deleted_at__isnull=True,
            cantidad_actual__gt=0
        ).count()
    
    def get_alerta_stock(self, obj):
        """Determina el estado del stock respecto al mínimo"""
        stock = self.get_stock_total(obj)
        if stock == 0:
            return 'CRITICO'
        if stock < obj.stock_minimo:
            return 'BAJO'
        return 'NORMAL'
    
    def get_nivel_stock(self, obj):
        """Alias requerido por el frontend"""
        return self.get_alerta_stock(obj)
    
    def validate_clave(self, value):
        """Valida que la clave sea única y en mayúsculas"""
        clave_upper = value.upper().strip()
        instance_id = self.instance.id if self.instance else None
        
        if Producto.objects.filter(clave__iexact=clave_upper).exclude(id=instance_id).exists():
            raise serializers.ValidationError('Ya existe un producto con esta clave.')
        
        return clave_upper
    
    def validate_precio_unitario(self, value):
        """Valida que el precio sea positivo"""
        if value is not None and value < 0:
            raise serializers.ValidationError('El precio no puede ser negativo.')
        return value
    
    def validate_stock_minimo(self, value):
        """Valida que el stock mínimo sea no negativo"""
        if value < 0:
            raise serializers.ValidationError('El stock mínimo no puede ser negativo.')
        return value
    
    def validate(self, data):
        """Validaciones a nivel de objeto"""
        descripcion = data.get('descripcion')
        if descripcion is not None and not descripcion.strip():
            raise serializers.ValidationError({'descripcion': 'La descripción no puede estar vacía.'})
        return data

class CentroSerializer(serializers.ModelSerializer):
    total_requisiciones = serializers.SerializerMethodField()
    usuarios_asignados = serializers.SerializerMethodField()
    
    class Meta:
        model = Centro
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_total_requisiciones(self, obj):
        """Cuenta las requisiciones del centro"""
        if hasattr(obj, 'requisiciones'):
            return obj.requisiciones.count()
        return 0
    
    def get_usuarios_asignados(self, obj):
        """Cuenta los usuarios asignados al centro"""
        if hasattr(obj, 'usuarios'):
            return obj.usuarios.filter(is_active=True).count()
        return 0
    
    def validate_clave(self, value):
        """Valida clave única"""
        if not value or not value.strip():
            raise serializers.ValidationError('La clave no puede estar vacía.')
        
        clave_upper = value.upper().strip()
        instance_id = self.instance.id if self.instance else None
        
        if Centro.objects.filter(clave__iexact=clave_upper).exclude(id=instance_id).exists():
            raise serializers.ValidationError('Ya existe un centro con esta clave.')
        
        return clave_upper
    
    def validate_nombre(self, value):
        """Valida nombre"""
        if not value or not value.strip():
            raise serializers.ValidationError('El nombre no puede estar vacío.')
        
        if len(value.strip()) < 3:
            raise serializers.ValidationError('El nombre debe tener al menos 3 caracteres.')
        
        return value.strip()
    
    def validate_telefono(self, value):
        """Valida teléfono"""
        if value and value.strip():
            import re
            # Limpiar el teléfono
            telefono_limpio = re.sub(r'[\s\-\(\)]', '', value)
            
            # Validar que tenga entre 7 y 15 dígitos
            if not telefono_limpio.isdigit():
                raise serializers.ValidationError('El teléfono debe contener solo números.')
            
            if len(telefono_limpio) < 7 or len(telefono_limpio) > 15:
                raise serializers.ValidationError('El teléfono debe tener entre 7 y 15 dígitos.')
        
        return value.strip() if value else ''
    
    def validate(self, data):
        """Validaciones a nivel de objeto"""
        # Convertir clave a mayúsculas si existe
        if 'clave' in data:
            data['clave'] = data['clave'].upper().strip()
        
        # Limpiar espacios en blanco
        if 'nombre' in data:
            data['nombre'] = data['nombre'].strip()
        
        if 'direccion' in data and data['direccion']:
            data['direccion'] = data['direccion'].strip()
        
        return data
    
    def create(self, validated_data):
        """Crea el centro"""
        try:
            centro = Centro.objects.create(**validated_data)
            print(f"✅ Centro creado en serializer: {centro.clave}")
            return centro
        except Exception as e:
            print(f"❌ Error en serializer.create: {str(e)}")
            raise serializers.ValidationError(f'Error al crear centro: {str(e)}')
    
    def update(self, instance, validated_data):
        """Actualiza el centro"""
        try:
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            print(f"✅ Centro actualizado en serializer: {instance.clave}")
            return instance
        except Exception as e:
            print(f"❌ Error en serializer.update: {str(e)}")
            raise serializers.ValidationError(f'Error al actualizar centro: {str(e)}')

class LoteSerializer(serializers.ModelSerializer):
    producto_clave = serializers.CharField(source='producto.clave', read_only=True)
    producto_descripcion = serializers.CharField(source='producto.descripcion', read_only=True)
    dias_para_caducar = serializers.SerializerMethodField()
    estado_caducidad = serializers.SerializerMethodField()
    
    class Meta:
        model = Lote
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_dias_para_caducar(self, obj):
        """Calcula días restantes hasta la caducidad"""
        from datetime import date
        if obj.fecha_caducidad:
            dias = (obj.fecha_caducidad - date.today()).days
            return dias
        return None
    
    def get_estado_caducidad(self, obj):
        """Determina el estado de caducidad"""
        dias = self.get_dias_para_caducar(obj)
        if dias is None:
            return 'DESCONOCIDO'
        if dias < 0:
            return 'VENCIDO'
        elif dias <= 7:
            return 'CRITICO'
        elif dias <= 30:
            return 'PROXIMO'
        else:
            return 'NORMAL'
    
    def validate_numero_lote(self, value):
        """Valida que el número de lote sea único para el producto"""
        lote_upper = value.upper()
        instance_id = self.instance.id if self.instance else None
        producto_id = self.initial_data.get('producto')
        
        # Si estamos editando y el número de lote no cambió, está OK
        if self.instance and self.instance.numero_lote.upper() == lote_upper:
            return lote_upper
        
        # Verificar si existe el mismo número de lote para el mismo producto
        if producto_id:
            if Lote.objects.filter(
                producto_id=producto_id, 
                numero_lote__iexact=lote_upper
            ).exclude(id=instance_id).exists():
                raise serializers.ValidationError('Ya existe un lote con este número para el producto seleccionado.')
        
        return lote_upper
    
    def validate_fecha_caducidad(self, value):
        """Valida que la fecha de caducidad no sea muy antigua"""
        from datetime import date, timedelta
        
        if value < date.today() - timedelta(days=365):
            raise serializers.ValidationError('La fecha de caducidad es demasiado antigua.')
        
        return value
    
    def validate_cantidad_actual(self, value):
        """Valida que la cantidad sea no negativa"""
        if value < 0:
            raise serializers.ValidationError('La cantidad no puede ser negativa.')
        return value
    
    def validate_precio_compra(self, value):
        """Valida que el precio sea positivo si se proporciona"""
        if value is not None and value < 0:
            raise serializers.ValidationError('El precio no puede ser negativo.')
        return value

class MovimientoSerializer(serializers.ModelSerializer):
    producto_clave = serializers.CharField(source='producto.clave', read_only=True)
    producto_descripcion = serializers.CharField(source='producto.descripcion', read_only=True)
    lote_numero = serializers.CharField(source='lote.numero_lote', read_only=True)
    
    class Meta:
        model = Movimiento
        fields = [
            'id', 
            'producto', 
            'producto_clave',
            'producto_descripcion',
            'lote', 
            'lote_numero',
            'tipo_movimiento', 
            'cantidad', 
            'fecha_movimiento', 
            'observaciones',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'producto_clave', 'producto_descripcion', 'lote_numero']

class UserSerializer(serializers.ModelSerializer):
    grupos = serializers.SerializerMethodField()
    rol = serializers.SerializerMethodField()
    centro_info = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'is_active', 'is_staff', 'is_superuser', 'grupos', 'rol', 
            'centro', 'centro_info', 'telefono', 'date_joined', 'password'
        ]
        read_only_fields = ['id', 'date_joined']
        extra_kwargs = {
            'password': {'write_only': True, 'required': False}
        }
    
    def get_grupos(self, obj):
        """Obtiene lista de grupos del usuario"""
        return [g.name for g in obj.groups.all()]
    
    def get_rol(self, obj):
        """Determina el rol principal del usuario"""
        if obj.is_superuser:
            return 'SUPERUSER'
        grupos = obj.groups.all()
        if grupos.exists():
            return grupos.first().name
        return 'USUARIO'
    
    def get_centro_info(self, obj):
        """Información del centro asignado"""
        if obj.centro:
            return {
                'id': obj.centro.id,
                'clave': obj.centro.clave,
                'nombre': obj.centro.nombre
            }
        return None
    
    def validate_username(self, value):
        """Valida username único"""
        if not value or not value.strip():
            raise serializers.ValidationError('El nombre de usuario no puede estar vacío.')
        
        username_lower = value.lower().strip()
        instance_id = self.instance.id if self.instance else None
        
        if User.objects.filter(username__iexact=username_lower).exclude(id=instance_id).exists():
            raise serializers.ValidationError('Este nombre de usuario ya existe.')
        
        if len(value.strip()) < 3:
            raise serializers.ValidationError('El nombre de usuario debe tener al menos 3 caracteres.')
        
        return value.strip()
    
    def validate_email(self, value):
        """Valida email único"""
        if value and value.strip():
            email_lower = value.lower().strip()
            instance_id = self.instance.id if self.instance else None
            
            if User.objects.filter(email__iexact=email_lower).exclude(id=instance_id).exists():
                raise serializers.ValidationError('Este email ya está registrado.')
        
        return value.strip() if value else ''
    
    def validate_password(self, value):
        """Valida contraseña"""
        if value:
            if len(value) < 6:
                raise serializers.ValidationError('La contraseña debe tener al menos 6 caracteres.')
        return value
    
    def create(self, validated_data):
        """Crea usuario con contraseña encriptada"""
        password = validated_data.pop('password', None)
        
        if not password:
            raise serializers.ValidationError({'password': 'La contraseña es requerida para crear un usuario.'})
        
        user = User.objects.create_user(
            username=validated_data.get('username'),
            email=validated_data.get('email', ''),
            password=password,
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            is_active=validated_data.get('is_active', True),
            is_staff=validated_data.get('is_staff', False),
            is_superuser=validated_data.get('is_superuser', False)
        )
        
        # Asignar centro si existe
        if 'centro' in validated_data and validated_data['centro']:
            user.centro = validated_data['centro']
        
        # Asignar teléfono si existe
        if 'telefono' in validated_data:
            user.telefono = validated_data.get('telefono', '')
        
        user.save()
        
        return user
    
    def update(self, instance, validated_data):
        """Actualiza usuario"""
        password = validated_data.pop('password', None)
        
        # Actualizar campos básicos
        instance.username = validated_data.get('username', instance.username)
        instance.email = validated_data.get('email', instance.email)
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.is_active = validated_data.get('is_active', instance.is_active)
        instance.is_staff = validated_data.get('is_staff', instance.is_staff)
        instance.is_superuser = validated_data.get('is_superuser', instance.is_superuser)
        
        # Actualizar centro
        if 'centro' in validated_data:
            instance.centro = validated_data['centro']
        
        # Actualizar teléfono
        if 'telefono' in validated_data:
            instance.telefono = validated_data.get('telefono', '')
        
        # Actualizar contraseña si se proporcionó
        if password:
            instance.set_password(password)
        
        instance.save()
        
        return instance

class DetalleRequisicionSerializer(serializers.ModelSerializer):
    producto_clave = serializers.CharField(source='producto.clave', read_only=True)
    producto_descripcion = serializers.CharField(source='producto.descripcion', read_only=True)
    producto_unidad = serializers.CharField(source='producto.unidad_medida', read_only=True)

    class Meta:
        model = DetalleRequisicion
        fields = '__all__'
        read_only_fields = ['id']
    
    def validate_cantidad_solicitada(self, value):
        """Valida cantidad solicitada"""
        if value <= 0:
            raise serializers.ValidationError('La cantidad debe ser mayor a 0.')
        return value
    
    def validate_cantidad_autorizada(self, value):
        """Valida cantidad autorizada"""
        if value is not None and value < 0:
            raise serializers.ValidationError('La cantidad autorizada no puede ser negativa.')
        return value
    
    def validate_cantidad_surtida(self, value):
        """Valida cantidad surtida"""
        if value is not None and value < 0:
            raise serializers.ValidationError('La cantidad surtida no puede ser negativa.')
        return value

class RequisicionSerializer(serializers.ModelSerializer):
    items = DetalleRequisicionSerializer(many=True, read_only=True)
    centro_nombre = serializers.CharField(source='centro.nombre', read_only=True)
    centro_clave = serializers.CharField(source='centro.clave', read_only=True)
    solicitante_nombre = serializers.CharField(source='solicitante.get_full_name', read_only=True)
    solicitante_username = serializers.CharField(source='solicitante.username', read_only=True)
    autorizado_por_nombre = serializers.CharField(source='autorizado_por.get_full_name', read_only=True)
    total_items = serializers.SerializerMethodField()
    total_solicitado = serializers.SerializerMethodField()
    total_autorizado = serializers.SerializerMethodField()
    puede_enviarse = serializers.SerializerMethodField()
    puede_autorizarse = serializers.SerializerMethodField()
    puede_cancelarse = serializers.SerializerMethodField()

    class Meta:
        model = Requisicion
        fields = '__all__'
        read_only_fields = ['id', 'folio', 'created_at', 'updated_at', 'fecha_solicitud', 'fecha_autorizacion', 'autorizado_por']
    
    def get_total_items(self, obj):
        """Cuenta total de items"""
        return obj.items.count()
    
    def get_total_solicitado(self, obj):
        """Suma total de cantidades solicitadas"""
        from django.db.models import Sum
        total = obj.items.aggregate(total=Sum('cantidad_solicitada'))['total']
        return total or 0
    
    def get_total_autorizado(self, obj):
        """Suma total de cantidades autorizadas"""
        from django.db.models import Sum
        total = obj.items.aggregate(total=Sum('cantidad_autorizada'))['total']
        return total or 0
    
    def get_puede_enviarse(self, obj):
        """Determina si puede enviarse"""
        return obj.estado == 'BORRADOR' and obj.items.exists()
    
    def get_puede_autorizarse(self, obj):
        """Determina si puede autorizarse"""
        return obj.estado == 'ENVIADA'
    
    def get_puede_cancelarse(self, obj):
        """Determina si puede cancelarse"""
        return obj.estado not in ['SURTIDA', 'CANCELADA']
    
    def validate_centro(self, value):
        """Valida que el centro esté activo"""
        if not value.activo:
            raise serializers.ValidationError('El centro seleccionado no está activo.')
        return value
    
    def validate(self, data):
        """Validaciones a nivel de objeto"""
        # Si es una creación, validar que tenga solicitante
        if not self.instance and 'solicitante' not in data:
            raise serializers.ValidationError({'solicitante': 'El solicitante es requerido.'})
        
        return data


class AuditoriaProductoSerializer(serializers.ModelSerializer):
    """Historial detallado de auditoría para productos"""
    usuario_nombre = serializers.CharField(
        source='usuario.get_full_name',
        read_only=True,
        default=''
    )
    modelo_display = serializers.SerializerMethodField()
    accion_display = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(source='fecha', read_only=True)
    
    class Meta:
        model = AuditoriaLog
        fields = [
            'id', 'usuario_nombre', 'accion', 'accion_display',
            'modelo', 'modelo_display', 'objeto_id', 'objeto_repr',
            'cambios', 'ip_address', 'user_agent', 'created_at'
        ]
        read_only_fields = fields
    
    def get_modelo_display(self, obj):
        return {
            'Producto': 'Producto',
            'Lote': 'Lote',
            'Requisicion': 'Requisición'
        }.get(obj.modelo, obj.modelo)
    
    def get_accion_display(self, obj):
        return {
            'crear': 'Creado',
            'actualizar': 'Actualizado',
            'eliminar': 'Eliminado',
            'importar': 'Importado'
        }.get(obj.accion, obj.accion.title())
