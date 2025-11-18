# filepath: apps/inventario/serializers.py
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import Producto, Lote, Movimiento


class ProductoSerializer(serializers.ModelSerializer):
    stock_total = serializers.IntegerField(read_only=True)
    proximo_vencer = serializers.DateField(read_only=True)

    class Meta:
        model = Producto
        fields = [
            "id",
            "clave",
            "descripcion",
            "unidad_medida",
            "precio_unitario",
            "stock_minimo",
            "stock_total",
            "proximo_vencer",
        ]


class LoteSerializer(serializers.ModelSerializer):
    # mismos datos con dos nombres distintos para compatibilidad
    clave = serializers.CharField(source="producto.clave", read_only=True)
    descripcion = serializers.CharField(source="producto.descripcion", read_only=True)
    producto_clave = serializers.CharField(source="producto.clave", read_only=True)
    producto_descripcion = serializers.CharField(
        source="producto.descripcion", read_only=True
    )

    class Meta:
        model = Lote
        fields = [
            "id",
            "producto",  # id del producto
            "clave",
            "descripcion",
            "producto_clave",
            "producto_descripcion",
            "numero_lote",
            "fecha_caducidad",
            "existencias",
        ]

    # ✅ Validar fecha de caducidad (no permitir fechas pasadas)
    def validate_fecha_caducidad(self, value):
        if value is None:
            return value
        hoy = timezone.now().date()
        if value < hoy:
            raise serializers.ValidationError(
                "La fecha de caducidad no puede ser anterior a hoy."
            )
        return value


class MovimientoSerializer(serializers.ModelSerializer):
    # info del lote / producto
    clave = serializers.CharField(source="lote.producto.clave", read_only=True)
    descripcion = serializers.CharField(
        source="lote.producto.descripcion", read_only=True
    )
    numero_lote = serializers.CharField(source="lote.numero_lote", read_only=True)
    lote_id = serializers.IntegerField(source="lote.id", read_only=True)

    # fecha elegible por el usuario; si no viene, se usa ahora()
    fecha = serializers.DateTimeField(required=False, default=timezone.now)

    # quién hizo el movimiento (solo lectura)
    usuario_username = serializers.CharField(
        source="usuario.username", read_only=True
    )

    class Meta:
        model = Movimiento
        fields = [
            "id",
            "fecha",
            "tipo",
            "cantidad",
            "unidad_medica",
            "observaciones",
            "lote",
            "lote_id",
            "clave",
            "descripcion",
            "numero_lote",
            "usuario_username",
        ]
        read_only_fields = [
            "lote_id",
            "clave",
            "descripcion",
            "numero_lote",
            "usuario_username",
        ]

    # ---- Validaciones de negocio previas ----
    def validate(self, attrs):
        tipo = (attrs.get("tipo") or "").lower()
        cantidad = attrs.get("cantidad")
        lote = attrs.get("lote")
        fecha = attrs.get("fecha") or timezone.now()

        # cantidad > 0
        if cantidad is not None and cantidad <= 0:
            raise serializers.ValidationError(
                {"cantidad": "La cantidad debe ser mayor a cero."}
            )

        # ajuste no negativo
        if tipo == "ajuste" and cantidad is not None and cantidad < 0:
            raise serializers.ValidationError(
                {"cantidad": "El ajuste no puede ser negativo."}
            )

        # chequeo rápido de existencias para salida
        if tipo == "salida" and lote is not None and cantidad is not None:
            exist = lote.existencias or 0
            if cantidad > exist:
                raise serializers.ValidationError(
                    {
                        "cantidad": (
                            "No hay existencias suficientes para la salida. "
                            f"Disponibles actualmente: {exist}."
                        )
                    }
                )

        # ✅ validar que la fecha del movimiento no sea posterior a la caducidad
        if lote and lote.fecha_caducidad:
            if fecha.date() > lote.fecha_caducidad:
                raise serializers.ValidationError(
                    {
                        "fecha": (
                            "La fecha del movimiento no puede ser posterior a la "
                            f"fecha de caducidad del lote "
                            f"({lote.fecha_caducidad:%d/%m/%Y})."
                        )
                    }
                )

        return attrs

    # ---- Crear movimiento + actualizar existencias de forma atómica ----
    def create(self, validated_data):
        tipo = (validated_data.get("tipo") or "").lower()
        cantidad = validated_data["cantidad"]
        lote = validated_data["lote"]

        # asignar usuario que hizo el movimiento (si está autenticado)
        request = self.context.get("request")
        usuario = getattr(request, "user", None) if request else None
        if usuario and usuario.is_authenticated:
            validated_data["usuario"] = usuario

        # la fecha ya viene en validated_data (del request o default)
        with transaction.atomic():
            # bloquea el lote mientras calculamos el nuevo stock
            lote = Lote.objects.select_for_update().get(pk=lote.pk)
            exist = lote.existencias or 0

            if tipo == "entrada":
                nuevo_stock = exist + cantidad

            elif tipo == "salida":
                if cantidad > exist:
                    # chequeo definitivo dentro de la transacción
                    raise ValidationError(
                        {
                            "cantidad": [
                                "No hay existencias suficientes para la salida. "
                                f"Disponibles actualmente: {exist}."
                            ]
                        }
                    )
                nuevo_stock = exist - cantidad

            elif tipo == "ajuste":
                if cantidad < 0:
                    raise ValidationError(
                        {"cantidad": ["El ajuste no puede ser negativo."]}
                    )
                # ajuste = dejar el lote exactamente en 'cantidad'
                nuevo_stock = cantidad

            else:
                raise ValidationError({"tipo": ["Tipo de movimiento inválido."]})

            lote.existencias = nuevo_stock
            lote.save()

            # usamos el lote bloqueado
            validated_data["lote"] = lote
            movimiento = Movimiento.objects.create(**validated_data)

        return movimiento

    # ---- Salida coherente para el frontend ----
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # aseguramos minúsculas en tipo
        data["tipo"] = (instance.tipo or "").lower()
        data["lote_id"] = instance.lote_id
        data["numero_lote"] = instance.lote.numero_lote
        data["clave"] = instance.lote.producto.clave
        data["descripcion"] = instance.lote.producto.descripcion
        data["usuario_username"] = (
            instance.usuario.username if getattr(instance, "usuario", None) else None
        )
        return data
