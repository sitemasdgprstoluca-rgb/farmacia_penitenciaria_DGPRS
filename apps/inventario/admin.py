from django.contrib import admin
from .models import Producto, Lote, Movimiento


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("clave", "descripcion", "unidad_medida", "stock_minimo")
    search_fields = ("clave", "descripcion")


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = ("producto", "numero_lote", "fecha_caducidad", "existencias")
    search_fields = ("producto__clave", "numero_lote")
    list_filter = ("fecha_caducidad",)


@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = ("tipo", "cantidad", "lote", "fecha", "unidad_medica")
    list_filter = ("tipo", "fecha")
    search_fields = ("lote__producto__clave", "unidad_medica")