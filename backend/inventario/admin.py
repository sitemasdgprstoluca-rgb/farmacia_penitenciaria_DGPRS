from django.contrib import admin
from core.models import DetalleRequisicion

# Nota: Producto, Lote, Movimiento, Centro, Requisicion están registrados en core/admin.py
# Solo registramos DetalleRequisicion aquí ya que es específica de este app

@admin.register(DetalleRequisicion)
class DetalleRequisicionAdmin(admin.ModelAdmin):
    list_display = ['requisicion', 'producto', 'cantidad_solicitada', 'cantidad_autorizada']
