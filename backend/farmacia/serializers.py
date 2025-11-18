from rest_framework import serializers
from django.contrib.auth.models import User, Group
from django.db.models import Sum
from decimal import Decimal
import datetime
from core.models import (
    Centro, Producto, Lote, Movimiento, 
    Requisicion, DetalleRequisicion
)


class UserSerializer(serializers.ModelSerializer):
    grupos = serializers.SerializerMethodField()
    rol = serializers.SerializerMethodField()
    is_superuser = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                  'grupos', 'rol', 'is_superuser', 'is_staff', 'is_active']
        read_only_fields = ['id']

    def get_grupos(self, obj):
        return [g.name for g in obj.groups.all()]

    def get_rol(self, obj):
        if obj.is_superuser:
            return 'SUPERUSER'
        grupos = obj.groups.values_list('name', flat=True)
        if 'FARMACIA_ADMIN' in grupos:
            return 'FARMACIA_ADMIN'
        if 'CENTRO_USER' in grupos:
            return 'CENTRO_USER'
        if 'VISTA_USER' in grupos:
            return 'VISTA_USER'
        return 'NONE'


class CentroSerializer(serializers.ModelSerializer):
    total_requisiciones = serializers.SerializerMethodField()

    class Meta:
        model = Centro
        fields = ['id', 'clave', 'nombre', 'direccion', 'telefono', 'activo', 'total_requisiciones', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_total_requisiciones(self, obj):
        return 0  # Por ahora retornar 0

    def validate_clave(self, value):
        instance_id = self.instance.id if self.instance else None
        if Centro.objects.filter(clave=value.upper()).exclude(id=instance_id).exists():
            raise serializers.ValidationError('Ya existe un centro con esta clave.')
        return value.upper()

    def validate_nombre(self, value):
        if not value or len(value.strip()) < 5:
            raise serializers.ValidationError('El nombre debe tener al menos 5 caracteres.')
        return value.strip()


class ProductoSerializer(serializers.ModelSerializer):
    stock_total = serializers.SerializerMethodField()
    lotes_activos = serializers.SerializerMethodField()
    alerta_stock = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

    def get_stock_total(self, obj):
        stock = obj.lotes.filter(
            estado='disponible',
            deleted_at__isnull=True
        ).aggregate(
            total=Sum('cantidad_actual')
        )['total']
        return float(stock) if stock else 0.0

    def get_lotes_activos(self, obj):
        return obj.lotes.filter(
            estado='disponible',
            deleted_at__isnull=True,
            cantidad_actual__gt=0
        ).count()

    def get_alerta_stock(self, obj):
        stock = self.get_stock_total(obj)
        if stock == 0:
            return 'CRITICO'
        elif stock < 10:
            return 'BAJO'
        return 'NORMAL'

    def validate_clave(self, value):
        instance_id = self.instance.id if self.instance else None
        if Producto.objects.filter(clave=value).exclude(id=instance_id).exists():
            raise serializers.ValidationError('Ya existe un producto con esta clave')
        return value.upper()


class LoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lote
        fields = [
            'id',
            'producto',
            'numero_lote',  # Asegúrate de que este campo exista en el modelo
            'fecha_caducidad',
            'cantidad_actual',
            'precio_compra',
            'proveedor',
            'activo',
        ]

    def validate_numero_lote(self, value):
        if not value:
            raise serializers.ValidationError("El número de lote es requerido.")
        if len(value) < 3:
            raise serializers.ValidationError("El número de lote debe tener al menos 3 caracteres.")
        return value

    def get_dias_para_caducar(self, obj):
        if obj.caducidad < datetime.date.today():
            return 0
        return (obj.caducidad - datetime.date.today()).days

    def get_alerta_caducidad(self, obj):
        if obj.caducidad < datetime.date.today():
            return 'VENCIDO'
        dias = self.get_dias_para_caducar(obj)
        if dias <= 7:
            return 'CRITICO'
        elif dias <= 30:
            return 'PROXIMO'
        return 'NORMAL'

    def get_esta_caducado(self, obj):
        return obj.caducidad < datetime.date.today()

    def validate(self, data):
        # Validar que la fecha de caducidad sea futura
        if 'caducidad' in data and data['caducidad'] < datetime.date.today():
            raise serializers.ValidationError({
                'caducidad': 'La fecha de caducidad debe ser futura'
            })
        
        # Validar existencia
        if 'existencia_actual' in data and data['existencia_actual'] < 0:
            raise serializers.ValidationError({
                'existencia_actual': 'La existencia no puede ser negativa'
            })
        
        # Validar código de lote único por producto
        producto = data.get('producto', self.instance.producto if self.instance else None)
        codigo_lote = data.get('codigo_lote', self.instance.codigo_lote if self.instance else None)
        
        if producto and codigo_lote:
            instance_id = self.instance.id if self.instance else None
            if Lote.objects.filter(
                producto=producto, 
                codigo_lote=codigo_lote
            ).exclude(id=instance_id).exists():
                raise serializers.ValidationError({
                    'codigo_lote': 'Ya existe un lote con este código para este producto'
                })
        
        return data


class MovimientoSerializer(serializers.ModelSerializer):
    producto_detalle = ProductoSerializer(source='producto', read_only=True)
    lote_detalle = LoteSerializer(source='lote', read_only=True)
    centro_detalle = CentroSerializer(source='centro', read_only=True)
    usuario_nombre = serializers.CharField(source='usuario.get_full_name', read_only=True)

    class Meta:
        model = Movimiento
        fields = '__all__'
        read_only_fields = ['fecha', 'usuario']

    def validate(self, data):
        # Validar stock suficiente para salidas
        if data.get('tipo') == 'SALIDA' and data.get('lote'):
            if data['lote'].existencia_actual < data['cantidad']:
                raise serializers.ValidationError({
                    'cantidad': f"Stock insuficiente. Disponible: {data['lote'].existencia_actual}"
                })
        
        # Validar que salidas tengan lote
        if data.get('tipo') in ['SALIDA', 'AJUSTE'] and not data.get('lote'):
            raise serializers.ValidationError({
                'lote': 'Las salidas y ajustes deben especificar un lote'
            })
        
        return data


class DetalleRequisicionSerializer(serializers.ModelSerializer):
    producto_detalle = ProductoSerializer(source='producto', read_only=True)
    diferencia = serializers.SerializerMethodField()

    class Meta:
        model = DetalleRequisicion
        fields = '__all__'
        read_only_fields = ['requisicion']

    def get_diferencia(self, obj):
        if obj.cantidad_autorizada is not None:
            return float(obj.cantidad_autorizada - obj.cantidad_solicitada)
        return None


class RequisicionSerializer(serializers.ModelSerializer):
    items = DetalleRequisicionSerializer(many=True, read_only=True)
    centro_detalle = CentroSerializer(source='centro', read_only=True)
    solicitante_nombre = serializers.CharField(source='solicitante.get_full_name', read_only=True)
    autorizada_por_nombre = serializers.CharField(source='autorizada_por.get_full_name', read_only=True)
    surtida_por_nombre = serializers.CharField(source='surtida_por.get_full_name', read_only=True)
    total_items = serializers.SerializerMethodField()
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = Requisicion
        fields = '__all__'
        read_only_fields = [
            'folio', 'created_at', 'updated_at', 
            'autorizada_por', 'fecha_autorizacion',
            'surtida_por', 'fecha_surtido'
        ]

    def get_total_items(self, obj):
        return obj.items.count()
