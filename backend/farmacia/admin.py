from django.contrib import admin
from core.models import Requisicion, DetalleRequisicion


class DetalleRequisicionInline(admin.TabularInline):
    model = DetalleRequisicion
    extra = 0
    readonly_fields = ['cantidad_solicitada']
    fields = ['producto', 'cantidad_solicitada', 'cantidad_autorizada', 'observaciones']


@admin.register(Requisicion)
class RequisicionAdmin(admin.ModelAdmin):
    list_display = ['folio', 'centro', 'estado', 'solicitante', 'created_at', 'total_items']
    list_filter = ['estado', 'centro', 'created_at']
    search_fields = ['folio', 'centro__nombre', 'solicitante__username']
    readonly_fields = ['folio', 'created_at', 'updated_at', 'fecha_autorizacion', 'fecha_surtido']
    inlines = [DetalleRequisicionInline]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Información General', {
            'fields': ('folio', 'centro', 'solicitante', 'estado')
        }),
        ('Autorización', {
            'fields': ('autorizada_por', 'fecha_autorizacion', 'comentario_autorizacion'),
            'classes': ('collapse',)
        }),
        ('Surtido', {
            'fields': ('surtida_por', 'fecha_surtido'),
            'classes': ('collapse',)
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def total_items(self, obj):
        return obj.items.count()
    total_items.short_description = 'Items'
    
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            instance.save()
        formset.save_m2m()
