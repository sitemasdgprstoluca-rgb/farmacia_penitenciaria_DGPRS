# filepath: apps/inventario/models.py
from django.conf import settings
from django.db import models
from django.utils import timezone


class Producto(models.Model):
    clave = models.CharField(max_length=50, unique=True)
    descripcion = models.CharField(max_length=255)
    unidad_medida = models.CharField(max_length=50)
    precio_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    stock_minimo = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["clave"]

    def __str__(self):
        return f"{self.clave} - {self.descripcion}"


class Lote(models.Model):
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name="lotes",
    )
    numero_lote = models.CharField(max_length=100)
    fecha_caducidad = models.DateField(null=True, blank=True)
    existencias = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("producto", "numero_lote")
        ordering = ["fecha_caducidad", "numero_lote"]

    def __str__(self):
        return f"{self.producto.clave} | Lote {self.numero_lote} | {self.existencias} uds"


class Movimiento(models.Model):
    TIPO = (
        ("entrada", "Entrada"),
        ("salida", "Salida"),
        ("ajuste", "Ajuste"),
    )

    lote = models.ForeignKey(
        Lote,
        on_delete=models.PROTECT,
        related_name="movimientos",
    )
    tipo = models.CharField(max_length=10, choices=TIPO)
    cantidad = models.PositiveIntegerField()

    # la fecha la eliges desde el front; si no mandan, el serializer pone timezone.now()
    fecha = models.DateTimeField()

    unidad_medica = models.CharField(max_length=120, blank=True, default="")
    observaciones = models.TextField(blank=True, default="")

    # quién hizo el movimiento
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="movimientos",
        null=True,
        blank=True,
    )

    # 👉 borrado lógico
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        fecha_str = self.fecha.strftime("%Y-%m-%d %H:%M") if self.fecha else "—"
        return f"{self.tipo} {self.cantidad} de {self.lote} ({fecha_str})"
