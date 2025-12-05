from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Centro, Producto, Lote, Requisicion, DetalleRequisicion, Movimiento, ImportacionLog

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin personalizado para el modelo User."""
    
    # Campos a mostrar en la lista
    list_display = ['username', 'email', 'first_name', 'last_name', 'rol', 'is_staff', 'is_active']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'rol']
    search_fields = ['username', 'first_name', 'last_name', 'email']
    
    # Agregar campos personalizados al formulario de edición
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Información Adicional', {'fields': ('rol', 'centro', 'adscripcion', 'activo')}),
    )
    
    # Agregar campos personalizados al formulario de creación
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Información Adicional', {'fields': ('rol', 'centro')}),
    )

@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    """
    Admin para gestión de lotes
    Adaptado a la estructura de BD existente
    """
    list_display = [
        'id',
        'numero_lote',
        'producto',
        'fecha_caducidad',
        'cantidad_actual',
        'cantidad_inicial',
        'estado_display',
        'activo',
    ]
    list_filter = [
        'activo',
        'fecha_caducidad',
        'producto',
    ]
    search_fields = [
        'numero_lote',
        'producto__nombre',
        'marca',
    ]
    readonly_fields = [
        'created_at',
        'updated_at',
    ]
    fieldsets = (
        ('Información Básica', {
            'fields': (
                'producto',
                'numero_lote',
                'fecha_caducidad',
                'fecha_fabricacion',
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
                'precio_unitario',
                'numero_contrato',
                'marca',
                'ubicacion',
            )
        }),
        ('Estado', {
            'fields': ('activo', 'centro'),
        }),
        ('Auditoría', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'fecha_caducidad'
    ordering = ['-created_at', 'fecha_caducidad']
    
    def estado_display(self, obj):
        """Muestra el estado calculado del lote"""
        estado = obj.estado
        iconos = {
            'disponible': '🟢',
            'agotado': '⚫',
            'caducado': '🔴',
        }
        return f"{iconos.get(estado, '❓')} {estado.upper()}"
    estado_display.short_description = "Estado"
    
    def get_queryset(self, request):
        """Incluye todos los lotes"""
        return Lote.objects.select_related('producto', 'centro').all()
