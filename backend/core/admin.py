from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Centro, Producto, Lote, Requisicion, DetalleRequisicion, Movimiento, ImportacionLog

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin personalizado para el modelo User."""
    
    # Campos a mostrar en la lista
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active']
    list_filter = ['is_staff', 'is_superuser', 'is_active']
    search_fields = ['username', 'first_name', 'last_name', 'email']
    
    # Agregar campos personalizados al formulario de edición
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Información Adicional', {'fields': ('telefono', 'centro')}),
    )
    
    # Agregar campos personalizados al formulario de creación
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Información Adicional', {'fields': ('telefono', 'centro')}),
    )

@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    """
    Admin para gestión de lotes
    CORREGIDO: Usa 'numero_lote' en lugar de 'codigo_lote'
    """
    list_display = [
        'id',
        'numero_lote',  # ✅ CORREGIDO (era codigo_lote)
        'producto',
        'fecha_caducidad',
        'cantidad_actual',
        'cantidad_inicial',
        'estado',
        'dias_restantes',
        'alerta',
        'deleted_at'
    ]
    list_filter = [
        'estado',
        'fecha_caducidad',
        'producto',
        'deleted_at',
        ('fecha_entrada', admin.DateFieldListFilter),
    ]
    search_fields = [
        'numero_lote',  # ✅ CORREGIDO
        'producto__clave',
        'producto__descripcion',
        'proveedor',
        'factura'
    ]
    readonly_fields = [
        'fecha_entrada',
        'created_at',
        'updated_at',
        'created_by',
        'dias_restantes',
        'alerta'
    ]
    fieldsets = (
        ('Información Básica', {
            'fields': (
                'producto',
                'numero_lote',  # ✅ CORREGIDO
                'fecha_caducidad',
                'estado'
            )
        }),
        ('Cantidades', {
            'fields': (
                'cantidad_inicial',
                'cantidad_actual',
            )
        }),
        ('Información de Compra', {
            'fields': (
                'precio_compra',
                'proveedor',
                'factura',
                'fecha_entrada'
            )
        }),
        ('Observaciones', {
            'fields': ('observaciones',),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': (
                'created_at',
                'updated_at',
                'created_by',
                'deleted_at'
            ),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'fecha_caducidad'
    ordering = ['-fecha_entrada', 'fecha_caducidad']
    
    def dias_restantes(self, obj):
        """Muestra días restantes para caducidad"""
        dias = obj.dias_para_caducar()
        if dias < 0:
            return f"❌ VENCIDO ({abs(dias)} días)"
        elif dias <= 7:
            return f"🔴 {dias} días"
        elif dias <= 30:
            return f"🟡 {dias} días"
        else:
            return f"🟢 {dias} días"
    dias_restantes.short_description = "Días para Caducar"
    
    def alerta(self, obj):
        """Muestra nivel de alerta"""
        nivel = obj.alerta_caducidad()
        iconos = {
            'vencido': '❌',
            'critico': '🔴',
            'proximo': '🟡',
            'normal': '🟢'
        }
        return f"{iconos.get(nivel, '❓')} {nivel.upper()}"
    alerta.short_description = "Alerta"
    
    def get_queryset(self, request):
        """Incluye lotes eliminados en admin"""
        return Lote.objects.select_related('producto', 'created_by').all()
    
    actions = ['marcar_vencidos', 'restaurar_eliminados']
    
    def marcar_vencidos(self, request, queryset):
        """Acción masiva: marcar lotes vencidos"""
        from datetime import date
        actualizados = queryset.filter(fecha_caducidad__lt=date.today()).update(estado='vencido')
        self.message_user(request, f"{actualizados} lotes marcados como vencidos")
    marcar_vencidos.short_description = "Marcar como vencidos"
    
    def restaurar_eliminados(self, request, queryset):
        """Acción masiva: restaurar lotes eliminados"""
        actualizados = queryset.filter(deleted_at__isnull=False).update(deleted_at=None)
        self.message_user(request, f"{actualizados} lotes restaurados")
    restaurar_eliminados.short_description = "Restaurar eliminados"
