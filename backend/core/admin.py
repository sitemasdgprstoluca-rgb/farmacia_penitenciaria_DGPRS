from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Centro, Producto, Lote, Requisicion, DetalleRequisicion, Movimiento


@admin.register(Centro)
class CentroAdmin(admin.ModelAdmin):
    """Admin para gestión de centros."""
    list_display = ['id', 'nombre', 'activo', 'created_at']
    list_filter = ['activo']
    search_fields = ['nombre', 'direccion']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin personalizado para el modelo User."""
    
    list_display = ['username', 'email', 'first_name', 'last_name', 'rol', 'is_staff', 'is_active']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'rol']
    search_fields = ['username', 'first_name', 'last_name', 'email']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Información Adicional', {'fields': ('rol', 'centro', 'adscripcion', 'activo')}),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Información Adicional', {'fields': ('rol', 'centro')}),
    )


@admin.register(Centro)
class CentroAdmin(admin.ModelAdmin):
    """Admin para Centros - Supabase"""
    list_display = ['id', 'clave', 'nombre', 'tipo', 'activo']
    list_filter = ['activo', 'tipo']
    search_fields = ['nombre', 'clave']


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    """
    Admin para Productos - Supabase
    
    Campos en Supabase: id, codigo_barras, nombre, descripcion, unidad_medida, categoria,
    stock_minimo, stock_actual, sustancia_activa, presentacion, concentracion,
    via_administracion, requiere_receta, es_controlado, activo, imagen, created_at, updated_at
    """
    list_display = ['id', 'nombre', 'codigo_barras', 'unidad_medida', 'stock_actual', 'activo']
    list_filter = ['activo', 'unidad_medida', 'categoria', 'requiere_receta', 'es_controlado']
    search_fields = ['nombre', 'codigo_barras', 'descripcion', 'sustancia_activa']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'descripcion', 'codigo_barras', 'unidad_medida', 'categoria', 'imagen')
        }),
        ('Información Farmacéutica', {
            'fields': ('sustancia_activa', 'presentacion', 'concentracion', 'via_administracion', 'requiere_receta', 'es_controlado')
        }),
        ('Stock', {
            'fields': ('stock_minimo', 'stock_actual')
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    """
    Admin para Lotes - Supabase
    
    Campos en Supabase: id, producto_id, centro_id, numero_lote, fecha_caducidad,
    fecha_entrada, cantidad_inicial, cantidad_actual, precio_compra, estado,
    ubicacion, observaciones, documento_soporte, created_at, updated_at
    """
    list_display = [
        'id',
        'numero_lote',
        'producto',
        'centro',
        'fecha_caducidad',
        'cantidad_actual',
        'cantidad_inicial',
        'estado',
    ]
    list_filter = [
        'estado',
        'fecha_caducidad',
        'centro',
    ]
    search_fields = [
        'numero_lote',
        'producto__clave',
        'producto__descripcion',
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
                'fecha_entrada',
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
                'documento_soporte',
            )
        }),
        ('Ubicación', {
            'fields': ('estado', 'centro', 'ubicacion', 'observaciones'),
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
    
    def get_queryset(self, request):
        """Incluye todos los lotes con relaciones"""
        return Lote.objects.select_related('producto', 'centro').all()


@admin.register(Requisicion)
class RequisicionAdmin(admin.ModelAdmin):
    """Admin para Requisiciones - Supabase"""
    list_display = ['id', 'folio', 'centro', 'estado', 'fecha_solicitud']
    list_filter = ['estado', 'prioridad']
    search_fields = ['folio']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(DetalleRequisicion)
class DetalleRequisicionAdmin(admin.ModelAdmin):
    """Admin para Detalles de Requisicion - Supabase"""
    list_display = ['id', 'requisicion', 'producto', 'cantidad_solicitada', 'cantidad_autorizada']
    list_filter = []
    search_fields = ['requisicion__folio', 'producto__clave']


@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    """Admin para Movimientos - Supabase"""
    list_display = ['id', 'tipo', 'lote', 'centro', 'cantidad', 'fecha']
    list_filter = ['tipo']
    search_fields = ['lote__numero_lote']
    readonly_fields = ['fecha']
