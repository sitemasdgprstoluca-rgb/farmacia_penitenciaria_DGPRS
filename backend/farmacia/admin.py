from django.contrib import admin
from core.models import Requisicion, DetalleRequisicion


class DetalleRequisicionInline(admin.TabularInline):
    model = DetalleRequisicion
    extra = 0
    readonly_fields = ['cantidad_solicitada']
    fields = ['producto', 'cantidad_solicitada', 'cantidad_autorizada', 'observaciones']


@admin.register(Requisicion)
class RequisicionAdmin(admin.ModelAdmin):
    """Admin ajustado al modelo Requisicion actual."""

    list_display = ['folio', 'centro', 'estado', 'usuario_solicita', 'fecha_solicitud', 'total_items']
    list_filter = ['estado', 'centro', 'fecha_solicitud']
    search_fields = ['folio', 'centro__nombre', 'usuario_solicita__username']
    readonly_fields = ['folio', 'fecha_solicitud', 'created_at', 'updated_at', 'fecha_autorizacion']
    inlines = [DetalleRequisicionInline]
    date_hierarchy = 'fecha_solicitud'

    fieldsets = (
        ('Información General', {
            'fields': ('folio', 'centro', 'usuario_solicita', 'estado', 'observaciones')
        }),
        ('Autorización', {
            'fields': ('usuario_autoriza', 'fecha_autorizacion', 'motivo_rechazo'),
            'classes': ('collapse',)
        }),
        ('Fechas', {
            'fields': ('fecha_solicitud', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def total_items(self, obj):
        return obj.detalles.count()
    total_items.short_description = 'Items'

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            instance.save()
        formset.save_m2m()
