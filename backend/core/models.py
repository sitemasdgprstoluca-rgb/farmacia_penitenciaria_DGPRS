from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date, timedelta
from .constants import (
    UNIDADES_MEDIDA,
    ESTADOS_LOTE,
    ESTADOS_REQUISICION,
    TIPOS_MOVIMIENTO,
    ROLES_USUARIO,
    PRODUCTO_CLAVE_MIN_LENGTH,
    PRODUCTO_CLAVE_MAX_LENGTH,
    PRODUCTO_DESCRIPCION_MIN_LENGTH,
    PRODUCTO_DESCRIPCION_MAX_LENGTH,
    PRODUCTO_PRECIO_MAX_DIGITS,
    PRODUCTO_PRECIO_DECIMAL_PLACES,
    LOTE_NUMERO_MIN_LENGTH,
    LOTE_NUMERO_MAX_LENGTH,
    NIVELES_STOCK,
)
import logging
import os


# ISS-016: Validador de tamaÃ±o de archivo para imÃ¡genes
def validate_image_max_size(value, max_size_kb=500):
    """Valida que una imagen no exceda el tamaÃ±o mÃ¡ximo (default 500KB)"""
    if value:
        max_size_bytes = max_size_kb * 1024
        if value.size > max_size_bytes:
            raise ValidationError(
                f'El archivo es demasiado grande. MÃ¡ximo permitido: {max_size_kb}KB'
            )


def validate_logo_size(value):
    """Validador especÃ­fico para logos (max 500KB)"""
    validate_image_max_size(value, max_size_kb=500)


def validate_image_size(value):
    """Valida que la imagen no exceda 2MB"""
    max_size = 2 * 1024 * 1024  # 2 MB
    if value.size > max_size:
        raise ValidationError(f'La imagen no puede exceder 2MB. TamaÃ±o actual: {value.size/1024/1024:.1f}MB')


def producto_imagen_path(instance, filename):
    """Genera ruta para imÃ¡genes de productos"""
    ext = filename.split('.')[-1]
    return f'productos/{instance.clave}.{ext}'


def requisicion_firma_path(instance, filename):
    """Genera ruta para fotos de firma de requisiciones"""
    ext = filename.split('.')[-1]
    return f'requisiciones/firmas/{instance.folio}_{filename}'


# ISS-005: Validador de archivos PDF
def validate_pdf_file(value):
    """
    ISS-005: Valida que el archivo sea PDF vÃ¡lido y no exceda tamaÃ±o mÃ¡ximo.
    
    Validaciones:
    - ExtensiÃ³n .pdf
    - TamaÃ±o mÃ¡ximo 10MB
    - Content-type application/pdf (si estÃ¡ disponible)
    """
    if not value:
        return
    
    # Validar extensiÃ³n
    ext = os.path.splitext(value.name)[1].lower()
    if ext != '.pdf':
        raise ValidationError('Solo se permiten archivos PDF (.pdf)')
    
    # Validar tamaÃ±o (mÃ¡ximo 10MB)
    max_size_bytes = 10 * 1024 * 1024  # 10MB
    if value.size > max_size_bytes:
        raise ValidationError(
            f'El archivo PDF es demasiado grande. MÃ¡ximo permitido: 10MB. '
            f'TamaÃ±o actual: {value.size / (1024*1024):.2f}MB'
        )
    
    # Validar content-type si estÃ¡ disponible
    if hasattr(value, 'content_type'):
        allowed_types = ['application/pdf', 'application/x-pdf']
        if value.content_type not in allowed_types:
            raise ValidationError(
                f'Tipo de archivo no vÃ¡lido. Se esperaba PDF, se recibiÃ³: {value.content_type}'
            )


# ISS-005: FunciÃ³n para generar nombre seguro de archivo PDF
def pdf_upload_path(instance, filename):
    """
    ISS-005: Genera ruta segura para archivos PDF.
    
    Formato: lotes/documentos/YYYY/MM/producto_lote_timestamp.pdf
    """
    import uuid
    from django.utils import timezone
    
    # Sanitizar nombre (remover caracteres peligrosos)
    safe_name = "".join(c for c in filename if c.isalnum() or c in '._-')
    
    # Generar nombre Ãºnico
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    unique_id = uuid.uuid4().hex[:8]
    
    # Obtener info del lote si estÃ¡ disponible
    producto_clave = getattr(instance, 'producto', None)
    if producto_clave and hasattr(producto_clave, 'clave'):
        producto_clave = producto_clave.clave[:20]
    else:
        producto_clave = 'doc'
    
    numero_lote = getattr(instance, 'numero_lote', 'lote')[:20] if instance else 'lote'
    
    # Formato final: lotes/documentos/2024/12/PROD123_LOT456_20241204_123456_abc12345.pdf
    new_filename = f"{producto_clave}_{numero_lote}_{timestamp}_{unique_id}.pdf"
    
    year = timezone.now().strftime('%Y')
    month = timezone.now().strftime('%m')
    
    return f"lotes/documentos/{year}/{month}/{new_filename}"

logger = logging.getLogger(__name__)


class User(AbstractUser):
    """
    Modelo de usuario extendido con roles y asignación de centro.
    
    ISS-009: Incluye validación de coherencia entre rol y permisos personalizados.
    FLUJO V2: Permisos granulares para flujo jerárquico de requisiciones.
    """
    
    # ISS-009: Definir permisos máximos permitidos por rol
    # True = puede tener el permiso, False = nunca puede tenerlo
    # FLUJO V2: Actualizado con nuevos roles y permisos del flujo
    PERMISOS_POR_ROL = {
        # Roles de Farmacia Central
        'admin': {
            'perm_dashboard': True, 'perm_productos': True, 'perm_lotes': True,
            'perm_requisiciones': True, 'perm_centros': True, 'perm_usuarios': True,
            'perm_reportes': True, 'perm_trazabilidad': True, 'perm_auditoria': True,
            'perm_notificaciones': True, 'perm_movimientos': True, 'perm_donaciones': True,
            # Permisos flujo V2
            'perm_crear_requisicion': True, 'perm_autorizar_admin': True,
            'perm_autorizar_director': True, 'perm_recibir_farmacia': True,
            'perm_autorizar_farmacia': True, 'perm_surtir': True, 'perm_confirmar_entrega': True,
        },
        'admin_sistema': {  # Legacy alias
            'perm_dashboard': True, 'perm_productos': True, 'perm_lotes': True,
            'perm_requisiciones': True, 'perm_centros': True, 'perm_usuarios': True,
            'perm_reportes': True, 'perm_trazabilidad': True, 'perm_auditoria': True,
            'perm_notificaciones': True, 'perm_movimientos': True, 'perm_donaciones': True,
            'perm_crear_requisicion': True, 'perm_autorizar_admin': True,
            'perm_autorizar_director': True, 'perm_recibir_farmacia': True,
            'perm_autorizar_farmacia': True, 'perm_surtir': True, 'perm_confirmar_entrega': True,
        },
        'farmacia': {
            'perm_dashboard': True, 'perm_productos': True, 'perm_lotes': True,
            'perm_requisiciones': True, 'perm_centros': False, 'perm_usuarios': False,
            'perm_reportes': True, 'perm_trazabilidad': True, 'perm_auditoria': False,
            'perm_notificaciones': True, 'perm_movimientos': True, 'perm_donaciones': True,
            # Permisos flujo V2
            'perm_crear_requisicion': False, 'perm_autorizar_admin': False,
            'perm_autorizar_director': False, 'perm_recibir_farmacia': True,
            'perm_autorizar_farmacia': True, 'perm_surtir': True, 'perm_confirmar_entrega': False,
        },
        'vista': {
            'perm_dashboard': True, 'perm_productos': True, 'perm_lotes': True,
            'perm_requisiciones': True, 'perm_centros': False, 'perm_usuarios': False,
            'perm_reportes': True, 'perm_trazabilidad': True, 'perm_auditoria': False,
            'perm_notificaciones': True, 'perm_movimientos': True, 'perm_donaciones': True,
            # Permisos flujo V2 - Solo consulta
            'perm_crear_requisicion': False, 'perm_autorizar_admin': False,
            'perm_autorizar_director': False, 'perm_recibir_farmacia': False,
            'perm_autorizar_farmacia': False, 'perm_surtir': False, 'perm_confirmar_entrega': False,
        },
        
        # Roles de Centro Penitenciario (FLUJO V2)
        'medico': {
            'perm_dashboard': True, 'perm_productos': True, 'perm_lotes': False,
            'perm_requisiciones': True, 'perm_centros': False, 'perm_usuarios': False,
            'perm_reportes': False, 'perm_trazabilidad': False, 'perm_auditoria': False,
            'perm_notificaciones': True, 'perm_movimientos': False, 'perm_donaciones': False,
            # Permisos flujo V2
            'perm_crear_requisicion': True, 'perm_autorizar_admin': False,
            'perm_autorizar_director': False, 'perm_recibir_farmacia': False,
            'perm_autorizar_farmacia': False, 'perm_surtir': False, 'perm_confirmar_entrega': True,
        },
        'administrador_centro': {
            'perm_dashboard': True, 'perm_productos': True, 'perm_lotes': False,
            'perm_requisiciones': True, 'perm_centros': False, 'perm_usuarios': False,
            'perm_reportes': True, 'perm_trazabilidad': True, 'perm_auditoria': False,
            'perm_notificaciones': True, 'perm_movimientos': False, 'perm_donaciones': False,
            # Permisos flujo V2
            'perm_crear_requisicion': False, 'perm_autorizar_admin': True,
            'perm_autorizar_director': False, 'perm_recibir_farmacia': False,
            'perm_autorizar_farmacia': False, 'perm_surtir': False, 'perm_confirmar_entrega': True,
        },
        'director_centro': {
            'perm_dashboard': True, 'perm_productos': True, 'perm_lotes': False,
            'perm_requisiciones': True, 'perm_centros': False, 'perm_usuarios': False,
            'perm_reportes': True, 'perm_trazabilidad': True, 'perm_auditoria': False,
            'perm_notificaciones': True, 'perm_movimientos': False, 'perm_donaciones': False,
            # Permisos flujo V2
            'perm_crear_requisicion': False, 'perm_autorizar_admin': False,
            'perm_autorizar_director': True, 'perm_recibir_farmacia': False,
            'perm_autorizar_farmacia': False, 'perm_surtir': False, 'perm_confirmar_entrega': True,
        },
        'centro': {
            'perm_dashboard': True, 'perm_productos': True, 'perm_lotes': True,
            'perm_requisiciones': True, 'perm_centros': False, 'perm_usuarios': False,
            'perm_reportes': True, 'perm_trazabilidad': True, 'perm_auditoria': False,
            'perm_notificaciones': True, 'perm_movimientos': True, 'perm_donaciones': True,
            # Permisos flujo V2 - Solo consulta
            'perm_crear_requisicion': False, 'perm_autorizar_admin': False,
            'perm_autorizar_director': False, 'perm_recibir_farmacia': False,
            'perm_autorizar_farmacia': False, 'perm_surtir': False, 'perm_confirmar_entrega': False,
        },
        
        # Legacy roles (compatibilidad)
        'usuario_centro': {
            'perm_dashboard': True, 'perm_productos': True, 'perm_lotes': True,
            'perm_requisiciones': True, 'perm_centros': False, 'perm_usuarios': False,
            'perm_reportes': True, 'perm_trazabilidad': True, 'perm_auditoria': False,
            'perm_notificaciones': True, 'perm_movimientos': True, 'perm_donaciones': True,
            'perm_crear_requisicion': True, 'perm_autorizar_admin': False,
            'perm_autorizar_director': False, 'perm_recibir_farmacia': False,
            'perm_autorizar_farmacia': False, 'perm_surtir': False, 'perm_confirmar_entrega': True,
        },
        'usuario_normal': {
            'perm_dashboard': True, 'perm_productos': True, 'perm_lotes': False,
            'perm_requisiciones': True, 'perm_centros': False, 'perm_usuarios': False,
            'perm_reportes': False, 'perm_trazabilidad': False, 'perm_auditoria': False,
            'perm_notificaciones': True, 'perm_movimientos': False, 'perm_donaciones': False,
            'perm_crear_requisicion': True, 'perm_autorizar_admin': False,
            'perm_autorizar_director': False, 'perm_recibir_farmacia': False,
            'perm_autorizar_farmacia': False, 'perm_surtir': False, 'perm_confirmar_entrega': True,
        },
    }
    
    rol = models.CharField(
        max_length=20,
        choices=ROLES_USUARIO,
        default='centro',
        help_text="Rol del usuario en el sistema"
    )
    centro = models.ForeignKey(
        'Centro',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios',
        db_column='centro_id',
        help_text="Centro asignado al usuario"
    )
    adscripcion = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text="Adscripción del usuario (centro/área/unidad de dependencia)"
    )
    # Campo 'activo' eliminado - usar is_active de AbstractUser
    
    # Permisos personalizados por módulo (null = usar permisos del rol por defecto)
    perm_dashboard = models.BooleanField(null=True, blank=True, help_text="Permiso para ver Dashboard")
    perm_productos = models.BooleanField(null=True, blank=True, help_text="Permiso para ver Productos")
    perm_lotes = models.BooleanField(null=True, blank=True, help_text="Permiso para ver Lotes")
    perm_requisiciones = models.BooleanField(null=True, blank=True, help_text="Permiso para ver Requisiciones")
    perm_centros = models.BooleanField(null=True, blank=True, help_text="Permiso para ver Centros")
    perm_usuarios = models.BooleanField(null=True, blank=True, help_text="Permiso para ver Usuarios")
    perm_reportes = models.BooleanField(null=True, blank=True, help_text="Permiso para ver Reportes")
    perm_trazabilidad = models.BooleanField(null=True, blank=True, help_text="Permiso para ver Trazabilidad")
    perm_auditoria = models.BooleanField(null=True, blank=True, help_text="Permiso para ver Auditoría")
    perm_notificaciones = models.BooleanField(null=True, blank=True, help_text="Permiso para ver Notificaciones")
    perm_movimientos = models.BooleanField(null=True, blank=True, help_text="Permiso para ver Movimientos")
    perm_donaciones = models.BooleanField(null=True, blank=True, help_text="Permiso para ver Donaciones (almacen separado)")
    
    # ========== FLUJO V2: PERMISOS GRANULARES DEL FLUJO DE REQUISICIONES ==========
    perm_crear_requisicion = models.BooleanField(null=True, blank=True, db_column='perm_crear_requisicion',
        help_text="Permiso para crear requisiciones (médicos)")
    perm_autorizar_admin = models.BooleanField(null=True, blank=True, db_column='perm_autorizar_admin',
        help_text="Permiso para autorizar como Administrador del Centro")
    perm_autorizar_director = models.BooleanField(null=True, blank=True, db_column='perm_autorizar_director',
        help_text="Permiso para autorizar como Director del Centro")
    perm_recibir_farmacia = models.BooleanField(null=True, blank=True, db_column='perm_recibir_farmacia',
        help_text="Permiso para recibir requisiciones en Farmacia Central")
    perm_autorizar_farmacia = models.BooleanField(null=True, blank=True, db_column='perm_autorizar_farmacia',
        help_text="Permiso para autorizar requisiciones en Farmacia Central")
    perm_surtir = models.BooleanField(null=True, blank=True, db_column='perm_surtir',
        help_text="Permiso para surtir requisiciones")
    perm_confirmar_entrega = models.BooleanField(null=True, blank=True, db_column='perm_confirmar_entrega',
        help_text="Permiso para confirmar entrega/recepción")
    
    class Meta:
        db_table = 'usuarios'
        managed = False  # La tabla ya existe en la BD

    def clean(self):
        """
        ISS-009: Valida coherencia entre rol y permisos personalizados.
        FLUJO V2: Incluye validación de permisos del flujo de requisiciones.
        
        Evita que un usuario tenga permisos que excedan su rol.
        """
        super().clean()
        
        # Superusers pueden tener cualquier permiso
        if self.is_superuser:
            return
        
        # Obtener permisos permitidos para este rol
        permisos_rol = self.PERMISOS_POR_ROL.get(self.rol, {})
        
        # Lista de campos de permisos (incluye flujo V2)
        campos_permisos = [
            'perm_dashboard', 'perm_productos', 'perm_lotes', 'perm_requisiciones',
            'perm_centros', 'perm_usuarios', 'perm_reportes', 'perm_trazabilidad',
            'perm_auditoria', 'perm_notificaciones', 'perm_movimientos', 'perm_donaciones',
            # FLUJO V2
            'perm_crear_requisicion', 'perm_autorizar_admin', 'perm_autorizar_director',
            'perm_recibir_farmacia', 'perm_autorizar_farmacia', 'perm_surtir', 'perm_confirmar_entrega'
        ]
        
        errores = {}
        for campo in campos_permisos:
            valor_actual = getattr(self, campo, None)
            permitido = permisos_rol.get(campo, False)
            
            # Si el permiso está explícitamente en True pero el rol no lo permite
            if valor_actual is True and not permitido:
                nombre_legible = campo.replace('perm_', '').replace('_', ' ').title()
                errores[campo] = (
                    f'El rol "{self.get_rol_display()}" no permite el permiso "{nombre_legible}". '
                    f'Cambie el rol a uno superior o desactive este permiso.'
                )
        
        if errores:
            raise ValidationError(errores)
    
    def get_permisos_efectivos(self):
        """
        ISS-009: Retorna los permisos efectivos del usuario.
        FLUJO V2: Incluye permisos del flujo de requisiciones.
        
        Combina permisos del rol base con personalizaciones, 
        respetando los límites del rol.
        """
        permisos_rol = self.PERMISOS_POR_ROL.get(self.rol, {})
        efectivos = {}
        
        # Lista de campos de permisos (incluye flujo V2)
        campos_permisos = [
            'perm_dashboard', 'perm_productos', 'perm_lotes', 'perm_requisiciones',
            'perm_centros', 'perm_usuarios', 'perm_reportes', 'perm_trazabilidad',
            'perm_auditoria', 'perm_notificaciones', 'perm_movimientos', 'perm_donaciones',
            # FLUJO V2
            'perm_crear_requisicion', 'perm_autorizar_admin', 'perm_autorizar_director',
            'perm_recibir_farmacia', 'perm_autorizar_farmacia', 'perm_surtir', 'perm_confirmar_entrega'
        ]
        
        for campo in campos_permisos:
            valor_personalizado = getattr(self, campo, None)
            maximo_rol = permisos_rol.get(campo, False)
            
            if self.is_superuser:
                # Superuser tiene todos los permisos
                efectivos[campo] = True
            elif valor_personalizado is not None:
                # Personalización: solo si está dentro del límite del rol
                efectivos[campo] = valor_personalizado and maximo_rol
            else:
                # Sin personalización: usar default del rol
                efectivos[campo] = maximo_rol
        
        return efectivos
    
    def puede_ejecutar_accion_flujo(self, accion):
        """
        FLUJO V2: Verifica si el usuario puede ejecutar una acción del flujo.
        
        Args:
            accion: Una de las acciones definidas en PERMISOS_FLUJO_REQUISICION
            
        Returns:
            bool: True si puede ejecutar la acción
        """
        from .constants import PERMISOS_FLUJO_REQUISICION
        
        if self.is_superuser:
            return True
        
        permisos_flujo = PERMISOS_FLUJO_REQUISICION.get(self.rol, {})
        return permisos_flujo.get(accion, False)

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_rol_display()})"


class Centro(models.Model):
    """
    Modelo de Centro Penitenciario
    
    Campos en BD: id, nombre, direccion, telefono, email, activo, created_at, updated_at
    """
    nombre = models.CharField(max_length=200, unique=True)
    direccion = models.TextField(blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=254, blank=True, null=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'centros'
        ordering = ['nombre']
        managed = False  # La tabla ya existe en la BD

    def __str__(self):
        return self.nombre
    
    # Propiedad para compatibilidad con cÃ³digo que usa 'clave'
    @property
    def clave(self):
        return str(self.id)


class Producto(models.Model):
    """
    Modelo de Producto Farmacéutico
    Adaptado a la estructura de base de datos existente.
    
    Columnas en BD:
    - clave (antes codigo_barras) - identificador único del producto
    - nombre - nombre del producto  
    - descripcion - descripción adicional (opcional)
    - categoria, sustancia_activa, presentacion, concentracion, via_administracion, etc.
    """
    # Campo principal: clave (mapea a columna 'clave' después del rename de codigo_barras)
    clave = models.CharField(max_length=50, unique=True, db_column='clave')
    nombre = models.CharField(max_length=500, db_column='nombre')
    descripcion = models.TextField(blank=True, null=True)
    unidad_medida = models.CharField(max_length=20, default='pieza')
    categoria = models.CharField(max_length=50, default='medicamento')
    stock_minimo = models.IntegerField(default=0)
    stock_actual = models.IntegerField(default=0)
    sustancia_activa = models.CharField(max_length=200, blank=True, null=True)
    presentacion = models.CharField(max_length=200, blank=True, null=True)
    concentracion = models.CharField(max_length=100, blank=True, null=True)
    via_administracion = models.CharField(max_length=50, blank=True, null=True)
    requiere_receta = models.BooleanField(default=False)
    es_controlado = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    imagen = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'productos'
        ordering = ['nombre']
        managed = False  # La tabla ya existe en la BD

    def __str__(self):
        return f"{self.clave} - {self.nombre}"
    
    def get_stock_actual(self, centro=None):
        """Calcula el stock actual sumando lotes disponibles."""
        from django.db.models import Sum
        
        filtros = {'activo': True}
        if centro and centro != 'todos':
            filtros['centro'] = centro
        
        return self.lotes.filter(**filtros).aggregate(
            total=Sum('cantidad_actual')
        )['total'] or 0
    
    def get_nivel_stock(self):
        """Retorna el nivel de stock: critico, bajo, normal, alto"""
        stock = self.get_stock_actual()
        if stock == 0:
            return 'critico'
        if self.stock_minimo > 0:
            ratio = stock / self.stock_minimo
            if ratio < 0.5:
                return 'critico'
            if ratio < 1:
                return 'bajo'
            if ratio > 2:
                return 'alto'
        return 'normal'


class Lote(models.Model):
    """
    Modelo de Lote de Producto - Supabase
    
    Campos en Supabase: id, numero_lote, producto_id, cantidad_inicial, 
    cantidad_actual, fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo, created_at, updated_at
    
    Constraints: lote_producto_unique (numero_lote, producto_id)
    """
    numero_lote = models.CharField(max_length=100)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='lotes', db_column='producto_id')
    cantidad_inicial = models.IntegerField()
    cantidad_actual = models.IntegerField(default=0)
    fecha_fabricacion = models.DateField(null=True, blank=True)
    fecha_caducidad = models.DateField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    numero_contrato = models.CharField(max_length=100, blank=True, null=True)
    marca = models.CharField(max_length=100, blank=True, null=True)
    ubicacion = models.CharField(max_length=100, blank=True, null=True)
    centro = models.ForeignKey('Centro', on_delete=models.SET_NULL, null=True, blank=True, related_name='lotes', db_column='centro_id')
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'lotes'
        managed = False  # Tabla en Supabase
        unique_together = [['numero_lote', 'producto']]  # lote_producto_unique constraint

    def __str__(self):
        return f"{self.numero_lote} - {self.producto}"
    
    @property
    def precio_compra(self):
        return self.precio_unitario
    
    @property
    def estado(self):
        """Calculated field since 'estado' column is gone"""
        return 'disponible' if self.activo else 'agotado' # Simplification

    def dias_para_caducar(self):
        """Calcula días restantes para caducidad (número entero)"""
        from django.utils import timezone
        if not self.fecha_caducidad:
            return 999  # Sin fecha de caducidad
        hoy = timezone.now().date()
        delta = (self.fecha_caducidad - hoy).days
        return delta
    
    def alerta_caducidad(self):
        """
        Clasifica el lote según su proximidad a caducar.
        
        Retorna:
            - 'vencido': Ya caducó
            - 'critico': Caduca en 30 días o menos
            - 'proximo': Caduca en 90 días o menos
            - 'normal': Más de 90 días para caducar
        """
        dias = self.dias_para_caducar()
        if dias < 0:
            return 'vencido'
        elif dias <= 30:
            return 'critico'
        elif dias <= 90:
            return 'proximo'
        else:
            return 'normal'


class Movimiento(models.Model):
    """
    Modelo de Movimiento de inventario
    Adaptado a la estructura de base de datos existente
    
    Campos en BD: id, tipo, producto_id (NOT NULL), lote_id, cantidad, 
    centro_origen_id, centro_destino_id, requisicion_id, usuario_id, 
    motivo, referencia, fecha, created_at
    
    MEJORA FLUJO 5: Campos subtipo_salida y numero_expediente para
    trazabilidad de pacientes en salidas por receta médica.
    """
    tipo = models.CharField(max_length=30)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='movimientos', db_column='producto_id')
    lote = models.ForeignKey(Lote, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos', db_column='lote_id')
    cantidad = models.IntegerField()
    centro_origen = models.ForeignKey('Centro', on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos_salida', db_column='centro_origen_id')
    centro_destino = models.ForeignKey('Centro', on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos_entrada', db_column='centro_destino_id')
    requisicion = models.ForeignKey('Requisicion', on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos', db_column='requisicion_id')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos', db_column='usuario_id')
    motivo = models.TextField(blank=True, null=True)
    referencia = models.CharField(max_length=100, blank=True, null=True)
    # MEJORA FLUJO 5: Subtipo de salida (receta, consumo_interno, merma, etc.)
    subtipo_salida = models.CharField(max_length=30, blank=True, null=True, db_column='subtipo_salida')
    # MEJORA FLUJO 5: Número de expediente del paciente (obligatorio si subtipo='receta')
    numero_expediente = models.CharField(max_length=50, blank=True, null=True, db_column='numero_expediente')
    fecha = models.DateTimeField(auto_now_add=True)  # BD default: now()
    created_at = models.DateTimeField(auto_now_add=True)  # BD default: now()

    class Meta:
        db_table = 'movimientos'
        ordering = ['-fecha']
        managed = False  # La tabla ya existe en la BD

    def __str__(self):
        return f"{self.tipo} - {self.cantidad} - {self.fecha}"
    
    # Propiedades para compatibilidad
    @property
    def centro(self):
        return self.centro_destino or self.centro_origen
    
    @property
    def observaciones(self):
        return self.motivo
    
    @property
    def documento_referencia(self):
        return self.referencia


class Requisicion(models.Model):
    """
    Modelo de Requisicion
    Adaptado a la estructura de base de datos existente
    
    FLUJO V2: Campos para flujo jerárquico con trazabilidad completa
    - Médico → Administrador → Director → Farmacia Central
    - Fechas de cada paso del flujo
    - Fecha límite de recolección (vencimiento automático)
    """
    numero = models.CharField(max_length=50, unique=True, db_column='numero')
    centro_origen = models.ForeignKey('Centro', on_delete=models.SET_NULL, null=True, blank=True, related_name='requisiciones_origen', db_column='centro_origen_id')
    centro_destino = models.ForeignKey('Centro', on_delete=models.SET_NULL, null=True, blank=True, related_name='requisiciones_destino', db_column='centro_destino_id')
    solicitante = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='requisiciones_solicitadas', db_column='solicitante_id')
    autorizador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='requisiciones_autorizadas', db_column='autorizador_id')
    estado = models.CharField(max_length=30, default='borrador')
    tipo = models.CharField(max_length=30, default='normal')
    prioridad = models.CharField(max_length=20, default='normal')
    notas = models.TextField(blank=True, null=True)
    lugar_entrega = models.CharField(max_length=255, blank=True, null=True)
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_autorizacion = models.DateTimeField(null=True, blank=True)
    fecha_surtido = models.DateTimeField(null=True, blank=True)
    fecha_entrega = models.DateTimeField(null=True, blank=True)
    foto_firma_surtido = models.CharField(max_length=255, blank=True, null=True)
    foto_firma_recepcion = models.CharField(max_length=255, blank=True, null=True)
    usuario_firma_surtido = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='firmas_surtido', db_column='usuario_firma_surtido_id')
    usuario_firma_recepcion = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='firmas_recepcion', db_column='usuario_firma_recepcion_id')
    fecha_firma_surtido = models.DateTimeField(null=True, blank=True)
    fecha_firma_recepcion = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # ========== CAMPOS PARA FORMATO DE REQUISICION DEL CENTRO (FIRMAS) ==========
    firma_solicitante = models.CharField(max_length=255, blank=True, null=True, db_column='firma_solicitante')
    nombre_solicitante = models.CharField(max_length=255, blank=True, null=True, db_column='nombre_solicitante')
    cargo_solicitante = models.CharField(max_length=100, blank=True, null=True, db_column='cargo_solicitante')
    firma_jefe_area = models.CharField(max_length=255, blank=True, null=True, db_column='firma_jefe_area')
    nombre_jefe_area = models.CharField(max_length=255, blank=True, null=True, db_column='nombre_jefe_area')
    cargo_jefe_area = models.CharField(max_length=100, blank=True, null=True, db_column='cargo_jefe_area')
    firma_director = models.CharField(max_length=255, blank=True, null=True, db_column='firma_director')
    nombre_director = models.CharField(max_length=255, blank=True, null=True, db_column='nombre_director')
    cargo_director = models.CharField(max_length=100, blank=True, null=True, db_column='cargo_director')
    
    # ========== CAMPOS URGENCIA Y FECHA ENTREGA SOLICITADA ==========
    fecha_entrega_solicitada = models.DateField(null=True, blank=True, db_column='fecha_entrega_solicitada')
    es_urgente = models.BooleanField(default=False, db_column='es_urgente')
    motivo_urgencia = models.TextField(blank=True, null=True, db_column='motivo_urgencia')
    
    # ========== FLUJO V2: CAMPOS DE TRAZABILIDAD TEMPORAL ==========
    # Fechas del flujo jerárquico
    fecha_envio_admin = models.DateTimeField(null=True, blank=True, db_column='fecha_envio_admin')
    fecha_autorizacion_admin = models.DateTimeField(null=True, blank=True, db_column='fecha_autorizacion_admin')
    fecha_envio_director = models.DateTimeField(null=True, blank=True, db_column='fecha_envio_director')
    fecha_autorizacion_director = models.DateTimeField(null=True, blank=True, db_column='fecha_autorizacion_director')
    fecha_envio_farmacia = models.DateTimeField(null=True, blank=True, db_column='fecha_envio_farmacia')
    fecha_recepcion_farmacia = models.DateTimeField(null=True, blank=True, db_column='fecha_recepcion_farmacia')
    fecha_autorizacion_farmacia = models.DateTimeField(null=True, blank=True, db_column='fecha_autorizacion_farmacia')
    fecha_recoleccion_limite = models.DateTimeField(null=True, blank=True, db_column='fecha_recoleccion_limite')
    fecha_vencimiento = models.DateTimeField(null=True, blank=True, db_column='fecha_vencimiento')
    
    # ========== FLUJO V2: ACTORES DEL FLUJO (TRAZABILIDAD ANTI-FRAUDE) ==========
    administrador_centro = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
        null=True, blank=True, related_name='requisiciones_autorizadas_admin',
        db_column='administrador_centro_id'
    )
    director_centro = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='requisiciones_autorizadas_director',
        db_column='director_centro_id'
    )
    receptor_farmacia = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='requisiciones_recibidas',
        db_column='receptor_farmacia_id'
    )
    autorizador_farmacia = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='requisiciones_autorizadas_farmacia',
        db_column='autorizador_farmacia_id'
    )
    surtidor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='requisiciones_surtidas',
        db_column='surtidor_id'
    )
    
    # ========== FLUJO V2: MOTIVOS DE RECHAZO/DEVOLUCIÓN ==========
    motivo_rechazo = models.TextField(blank=True, null=True, db_column='motivo_rechazo')
    motivo_devolucion = models.TextField(blank=True, null=True, db_column='motivo_devolucion')
    motivo_vencimiento = models.TextField(blank=True, null=True, db_column='motivo_vencimiento')
    observaciones_farmacia = models.TextField(blank=True, null=True, db_column='observaciones_farmacia')

    class Meta:
        db_table = 'requisiciones'
        ordering = ['-fecha_solicitud']
        managed = False  # La tabla ya existe en la BD

    def __str__(self):
        return f"REQ-{self.numero}"
    
    # Propiedades para compatibilidad con codigo existente
    @property
    def folio(self):
        return self.numero
    
    @property
    def centro(self):
        return self.centro_destino
    
    @property
    def centro_id(self):
        """Alias para centro_destino_id (compatibilidad)"""
        return self.centro_destino_id
    
    @property
    def usuario_solicita(self):
        return self.solicitante
    
    @property
    def usuario_solicita_id(self):
        """Alias para solicitante_id (compatibilidad)"""
        return self.solicitante_id
    
    @property
    def usuario_autoriza(self):
        return self.autorizador
    
    @property
    def usuario_autoriza_id(self):
        """Alias para autorizador_id (compatibilidad)"""
        return self.autorizador_id
    
    @property
    def comentario(self):
        return self.notas
    
    @property
    def observaciones(self):
        return self.notas
    
    @observaciones.setter
    def observaciones(self, value):
        self.notas = value
    
    # NOTA: motivo_rechazo ya es un campo real del modelo (línea ~715)
    # Se eliminó la property que sobrescribía el campo y causaba errores
    
    # Alias para campos de recepcion (compatibilidad con codigo existente)
    @property
    def usuario_recibe(self):
        """Alias para usuario_firma_recepcion"""
        return self.usuario_firma_recepcion
    
    @usuario_recibe.setter
    def usuario_recibe(self, value):
        self.usuario_firma_recepcion = value
    
    @property
    def fecha_recibido(self):
        """Alias para fecha_firma_recepcion"""
        return self.fecha_firma_recepcion
    
    @fecha_recibido.setter
    def fecha_recibido(self, value):
        self.fecha_firma_recepcion = value
    
    # updated_by no existe en la BD, se ignora silenciosamente
    @property
    def updated_by(self):
        return None
    
    @updated_by.setter
    def updated_by(self, value):
        pass  # Campo no existe en BD, se ignora


class DetalleRequisicion(models.Model):
    """
    Detalle de Requisicion
    Adaptado a la estructura de base de datos existente
    
    MEJORA FLUJO 3: Campo motivo_ajuste para comunicar al Centro
    por qué Farmacia autorizó menos cantidad de la solicitada.
    """
    requisicion = models.ForeignKey(Requisicion, on_delete=models.CASCADE, related_name='detalles', db_column='requisicion_id')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='detalles_requisicion', db_column='producto_id')
    lote = models.ForeignKey(Lote, on_delete=models.SET_NULL, null=True, blank=True, related_name='detalles_requisicion', db_column='lote_id')
    cantidad_solicitada = models.IntegerField()
    cantidad_autorizada = models.IntegerField(null=True, blank=True)
    cantidad_surtida = models.IntegerField(default=0, null=True, blank=True)
    cantidad_recibida = models.IntegerField(null=True, blank=True)
    notas = models.TextField(blank=True, null=True)
    # MEJORA FLUJO 3: Motivo obligatorio si cantidad_autorizada < cantidad_solicitada
    motivo_ajuste = models.CharField(max_length=255, blank=True, null=True, db_column='motivo_ajuste')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'detalles_requisicion'
        managed = False  # La tabla ya existe en la BD

    def __str__(self):
        return f"{self.requisicion.numero} - {self.producto.nombre}"
    
    @property
    def observaciones(self):
        return self.notas


class Notificacion(models.Model):
    """
    Modelo de Notificacion
    Adaptado a la estructura de base de datos existente
    """
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notificaciones', db_column='usuario_id')
    tipo = models.CharField(max_length=50)
    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    leida = models.BooleanField(default=False)
    datos = models.JSONField(null=True, blank=True)
    url = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notificaciones'
        ordering = ['-created_at']
        managed = False  # La tabla ya existe en la BD

    def __str__(self):
        return f"{self.titulo} - {self.usuario.username}"


class TemaGlobal(models.Model):
    """
    ConfiguraciÃ³n del tema visual - Supabase
    
    Campos en Supabase: id, nombre, es_activo, logo_url, logo_width, logo_height,
    favicon_url, titulo_sistema, subtitulo_sistema, y muchos colores...
    """
    nombre = models.CharField(max_length=100, unique=True)
    es_activo = models.BooleanField(default=False)
    logo_url = models.CharField(max_length=500, blank=True, null=True)
    logo_width = models.IntegerField(default=160)
    logo_height = models.IntegerField(default=60)
    favicon_url = models.CharField(max_length=500, blank=True, null=True)
    titulo_sistema = models.CharField(max_length=100, default='Sistema de Inventario FarmacÃ©utico', null=True, blank=True)
    subtitulo_sistema = models.CharField(max_length=200, default='Gobierno del Estado', null=True, blank=True)
    
    # Colores
    color_primario = models.CharField(max_length=20, default='#9F2241', null=True, blank=True)
    color_primario_hover = models.CharField(max_length=20, default='#6B1839', null=True, blank=True)
    color_secundario = models.CharField(max_length=20, default='#424242', null=True, blank=True)
    color_secundario_hover = models.CharField(max_length=20, default='#2E2E2E', null=True, blank=True)
    color_exito = models.CharField(max_length=20, default='#4a7c4b', null=True, blank=True)
    color_exito_hover = models.CharField(max_length=20, default='#3d663e', null=True, blank=True)
    color_alerta = models.CharField(max_length=20, default='#d4a017', null=True, blank=True)
    color_alerta_hover = models.CharField(max_length=20, default='#b38b14', null=True, blank=True)
    color_error = models.CharField(max_length=20, default='#c53030', null=True, blank=True)
    color_error_hover = models.CharField(max_length=20, default='#a52828', null=True, blank=True)
    color_info = models.CharField(max_length=20, default='#3182ce', null=True, blank=True)
    color_info_hover = models.CharField(max_length=20, default='#2c6cb0', null=True, blank=True)
    color_fondo_principal = models.CharField(max_length=20, default='#f7f8fa', null=True, blank=True)
    color_fondo_sidebar = models.CharField(max_length=20, default='#9F2241', null=True, blank=True)
    color_fondo_header = models.CharField(max_length=20, default='#9F2241', null=True, blank=True)
    color_texto_principal = models.CharField(max_length=20, default='#1f2937', null=True, blank=True)
    color_texto_sidebar = models.CharField(max_length=20, default='#ffffff', null=True, blank=True)
    color_texto_header = models.CharField(max_length=20, default='#ffffff', null=True, blank=True)
    color_texto_links = models.CharField(max_length=20, default='#9F2241', null=True, blank=True)
    color_borde_inputs = models.CharField(max_length=20, default='#d1d5db', null=True, blank=True)
    color_borde_focus = models.CharField(max_length=20, default='#9F2241', null=True, blank=True)
    reporte_color_encabezado = models.CharField(max_length=20, default='#9F2241', null=True, blank=True)
    reporte_color_texto = models.CharField(max_length=20, default='#1f2937', null=True, blank=True)
    # Campos adicionales que existen en la BD
    reporte_color_filas_alternas = models.CharField(max_length=20, default='#f9fafb', null=True, blank=True)
    reporte_pie_pagina = models.TextField(blank=True, null=True)
    reporte_ano_visible = models.BooleanField(default=True, null=True, blank=True)
    fuente_principal = models.CharField(max_length=100, default='Inter', null=True, blank=True)
    fuente_titulos = models.CharField(max_length=100, default='Inter', null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tema_global'
        managed = False  # La tabla ya existe en la BD

    def __str__(self):
        return self.nombre
    
    # Propiedad para compatibilidad
    @property
    def activo(self):
        return self.es_activo
    
    @property
    def color_fondo(self):
        return self.color_fondo_principal
    
    @property
    def color_texto(self):
        return self.color_texto_principal
    
    def to_css_variables(self):
        """Genera diccionario de variables CSS"""
        return {
            '--color-primario': self.color_primario,
            '--color-primario-hover': self.color_primario_hover,
            '--color-secundario': self.color_secundario,
            '--color-secundario-hover': self.color_secundario_hover,
            '--color-exito': self.color_exito,
            '--color-exito-hover': self.color_exito_hover,
            '--color-alerta': self.color_alerta,
            '--color-alerta-hover': self.color_alerta_hover,
            '--color-error': self.color_error,
            '--color-error-hover': self.color_error_hover,
            '--color-info': self.color_info,
            '--color-info-hover': self.color_info_hover,
            '--color-fondo-principal': self.color_fondo_principal,
            '--color-fondo-sidebar': self.color_fondo_sidebar,
            '--color-fondo-header': self.color_fondo_header,
            '--color-texto-principal': self.color_texto_principal,
            '--color-texto-sidebar': self.color_texto_sidebar,
            '--color-texto-header': self.color_texto_header,
        }


class ConfiguracionSistema(models.Model):
    """
    ConfiguraciÃ³n del sistema - Supabase
    
    Campos en Supabase: id, clave, valor, descripcion, tipo, es_publica, updated_at
    """
    clave = models.CharField(max_length=100, unique=True)
    valor = models.TextField()  # Schema: NOT NULL
    descripcion = models.TextField(blank=True, null=True)
    tipo = models.CharField(max_length=20, default='string') # Schema says default 'string'
    es_publica = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'configuracion_sistema'
        managed = False  # La tabla ya existe en la BD

    def __str__(self):
        return self.clave


class HojaRecoleccion(models.Model):
    """
    Hoja de RecolecciÃ³n - Supabase
    
    Campos en Supabase: id, numero, centro_id, responsable_id, estado,
    fecha_programada, fecha_recoleccion, notas, created_at, updated_at
    """
    numero = models.CharField(max_length=50, unique=True)
    centro = models.ForeignKey(Centro, on_delete=models.SET_NULL, null=True, blank=True, related_name='hojas_recoleccion', db_column='centro_id')
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='hojas_recoleccion_responsable', db_column='responsable_id')
    estado = models.CharField(max_length=30, default='pendiente')
    fecha_programada = models.DateField()
    fecha_recoleccion = models.DateTimeField(null=True, blank=True)
    notas = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'hojas_recoleccion'
        managed = False  # La tabla ya existe en la BD

    def __str__(self):
        return f"HR-{self.numero}"

    @property
    def folio(self):
        return self.numero


class DetalleHojaRecoleccion(models.Model):
    """
    Detalle de Hoja de Recolección - Supabase
    
    Campos en Supabase: id, hoja_id, lote_id, cantidad_recolectar,
    cantidad_recolectada, motivo, observaciones, created_at
    """
    hoja = models.ForeignKey(HojaRecoleccion, on_delete=models.CASCADE, related_name='detalles', db_column='hoja_id')
    lote = models.ForeignKey(Lote, on_delete=models.CASCADE, related_name='detalles_recoleccion', db_column='lote_id')
    cantidad_recolectar = models.IntegerField()
    cantidad_recolectada = models.IntegerField(default=0, null=True, blank=True)  # BD: YES nulos, default 0
    motivo = models.CharField(max_length=50, default='caducidad')  # BD: NOT NULL, default 'caducidad'
    observaciones = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'detalle_hojas_recoleccion'
        managed = False  # Tabla en Supabase


class ImportacionLogs(models.Model):
    """
    Log de Importaciones - Supabase
    
    Campos en Supabase: id, archivo, tipo_importacion, usuario_id,
    registros_totales, registros_exitosos, registros_fallidos, errores, 
    estado, fecha_inicio, fecha_fin
    """
    archivo = models.CharField(max_length=255)
    tipo_importacion = models.CharField(max_length=50)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='importaciones', db_column='usuario_id')
    registros_totales = models.IntegerField(default=0)
    registros_exitosos = models.IntegerField(default=0)
    registros_fallidos = models.IntegerField(default=0)
    errores = models.JSONField(null=True, blank=True)
    estado = models.CharField(max_length=30, default='procesando')
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'importacion_logs'
        managed = False  # Tabla en Supabase

# Alias para compatibilidad
ImportacionLog = ImportacionLogs


class AuditoriaLogs(models.Model):
    """
    Log de AuditorÃ­a - Supabase
    
    Campos en Supabase: id, usuario_id, accion, modelo, objeto_id,
    datos_anteriores, datos_nuevos, ip_address, user_agent, detalles, timestamp
    """
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='auditoria_logs', db_column='usuario_id')
    accion = models.CharField(max_length=50)
    modelo = models.CharField(max_length=100)
    objeto_id = models.CharField(max_length=50, null=True, blank=True)  # Schema says 50 chars
    datos_anteriores = models.JSONField(null=True, blank=True)
    datos_nuevos = models.JSONField(null=True, blank=True)
    ip_address = models.CharField(max_length=45, null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    detalles = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'auditoria_logs'
        managed = False  # Tabla en Supabase

# Alias para compatibilidad con cÃ³digo existente (si es necesario)
AuditLog = AuditoriaLogs
AuditoriaLog = AuditoriaLogs


class UserProfile(models.Model):
    """
    Modelo de perfil de usuario - Supabase
    
    Campos en BD: id, rol, telefono, centro_id, usuario_id, created_at, updated_at
    """
    rol = models.CharField(max_length=30, default='visualizador')
    telefono = models.CharField(max_length=20, blank=True, null=True)
    centro = models.ForeignKey(Centro, on_delete=models.SET_NULL, null=True, blank=True, related_name='perfiles_usuario', db_column='centro_id')
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='profile',
        db_column='usuario_id'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profiles'
        managed = False  # Tabla en Supabase
    
    def __str__(self):
        return f"Perfil de {self.usuario.username if self.usuario else 'N/A'}"


# ============================================================================
# MODELOS PARA MULTIPLES IMAGENES DE PRODUCTO
# ============================================================================
def producto_imagen_upload_path(instance, filename):
    """Genera ruta para imagenes de productos: productos/imagenes/{producto_id}/{filename}"""
    import uuid
    ext = filename.split('.')[-1].lower()
    unique_name = f"{uuid.uuid4().hex[:8]}.{ext}"
    return f"productos/imagenes/{instance.producto_id}/{unique_name}"


class ProductoImagen(models.Model):
    """
    Imagenes multiples para productos.
    Permite galeria de fotos por producto.
    """
    producto = models.ForeignKey(
        Producto, 
        on_delete=models.CASCADE, 
        related_name='imagenes',
        db_column='producto_id'
    )
    imagen = models.CharField(max_length=255)  # URL o path de la imagen
    es_principal = models.BooleanField(default=False)
    orden = models.IntegerField(default=0)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'producto_imagenes'
        managed = False  # Tabla en Supabase
        ordering = ['orden', '-es_principal']

    def __str__(self):
        return f"Imagen {self.id} - Producto {self.producto_id}"
    
    def save(self, *args, **kwargs):
        # Si esta imagen es principal, quitar es_principal de las demas
        if self.es_principal:
            ProductoImagen.objects.filter(
                producto_id=self.producto_id, 
                es_principal=True
            ).exclude(pk=self.pk).update(es_principal=False)
        super().save(*args, **kwargs)


# ============================================================================
# MODELOS PARA DOCUMENTOS DE LOTE (FACTURAS, CONTRATOS)
# ============================================================================
TIPOS_DOCUMENTO_LOTE = [
    ('factura', 'Factura'),
    ('contrato', 'Contrato'),
    ('remision', 'Remision'),
    ('otro', 'Otro'),
]


def lote_documento_upload_path(instance, filename):
    """Genera ruta para documentos de lote: lotes/documentos/{lote_id}/{filename}"""
    import uuid
    from django.utils import timezone
    ext = filename.split('.')[-1].lower()
    timestamp = timezone.now().strftime('%Y%m%d')
    unique_name = f"{instance.tipo_documento}_{timestamp}_{uuid.uuid4().hex[:8]}.{ext}"
    return f"lotes/documentos/{instance.lote_id}/{unique_name}"


class LoteDocumento(models.Model):
    """
    Documentos asociados a lotes (facturas, contratos, remisiones).
    Permite adjuntar PDFs e imagenes de documentacion.
    """
    lote = models.ForeignKey(
        Lote, 
        on_delete=models.CASCADE, 
        related_name='documentos',
        db_column='lote_id'
    )
    tipo_documento = models.CharField(
        max_length=50, 
        choices=TIPOS_DOCUMENTO_LOTE,
        default='otro'
    )
    numero_documento = models.CharField(max_length=100, blank=True, null=True)
    archivo = models.CharField(max_length=255)  # URL o path del archivo
    nombre_archivo = models.CharField(max_length=255, blank=True, null=True)
    fecha_documento = models.DateField(blank=True, null=True)
    notas = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documentos_lote_creados',
        db_column='created_by'
    )

    class Meta:
        db_table = 'lote_documentos'
        managed = False  # Tabla en Supabase
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_tipo_documento_display()} - Lote {self.lote_id}"


# ============================================================================
# MODELOS PARA DONACIONES
# ============================================================================
TIPOS_DONANTE = [
    ('empresa', 'Empresa'),
    ('gobierno', 'Gobierno'),
    ('ong', 'ONG'),
    ('particular', 'Particular'),
    ('otro', 'Otro'),
]

ESTADOS_DONACION = [
    ('pendiente', 'Pendiente'),
    ('recibida', 'Recibida'),
    ('procesada', 'Procesada'),
    ('rechazada', 'Rechazada'),
]

ESTADOS_PRODUCTO_DONACION = [
    ('bueno', 'Bueno'),
    ('regular', 'Regular'),
    ('malo', 'Malo'),
]


class Donacion(models.Model):
    """
    Registro de donaciones de medicamentos.
    Permite registrar entradas de inventario por donacion.
    """
    numero = models.CharField(max_length=50, unique=True)
    donante_nombre = models.CharField(max_length=255)
    donante_tipo = models.CharField(
        max_length=50, 
        choices=TIPOS_DONANTE,
        default='otro'
    )
    donante_rfc = models.CharField(max_length=20, blank=True, null=True)
    donante_direccion = models.TextField(blank=True, null=True)
    donante_contacto = models.CharField(max_length=100, blank=True, null=True)
    fecha_donacion = models.DateField()
    fecha_recepcion = models.DateTimeField(auto_now_add=True)
    centro_destino = models.ForeignKey(
        Centro,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='donaciones',
        db_column='centro_destino_id'
    )
    recibido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='donaciones_recibidas',
        db_column='recibido_por_id'
    )
    estado = models.CharField(
        max_length=30, 
        choices=ESTADOS_DONACION,
        default='pendiente'
    )
    notas = models.TextField(blank=True, null=True)
    documento_donacion = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'donaciones'
        managed = False  # Tabla en Supabase
        ordering = ['-fecha_recepcion']

    def __str__(self):
        return f"DON-{self.numero} - {self.donante_nombre}"
    
    @property
    def folio(self):
        return f"DON-{self.numero}"
    
    def get_total_productos(self):
        """Retorna el total de productos en la donacion"""
        return self.detalles.count()
    
    def get_total_unidades(self):
        """Retorna el total de unidades donadas"""
        from django.db.models import Sum
        return self.detalles.aggregate(total=Sum('cantidad'))['total'] or 0


class DetalleDonacion(models.Model):
    """
    Detalle de productos en una donacion - ALMACEN SEPARADO.
    Cada linea representa un producto donado con su propio stock independiente.
    NO afecta el inventario principal ni genera movimientos auditados.
    """
    donacion = models.ForeignKey(
        Donacion, 
        on_delete=models.CASCADE, 
        related_name='detalles',
        db_column='donacion_id'
    )
    producto = models.ForeignKey(
        Producto, 
        on_delete=models.PROTECT, 
        related_name='detalles_donacion',
        db_column='producto_id'
    )
    # NO usa lote del inventario principal - tiene su propio numero de lote
    numero_lote = models.CharField(max_length=100, blank=True, null=True)
    cantidad = models.IntegerField()  # Cantidad recibida originalmente
    cantidad_disponible = models.IntegerField(default=0)  # Stock actual en almacen donaciones
    fecha_caducidad = models.DateField(blank=True, null=True)
    estado_producto = models.CharField(
        max_length=50, 
        choices=ESTADOS_PRODUCTO_DONACION,
        default='bueno'
    )
    notas = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'detalle_donaciones'
        managed = False  # Tabla en Supabase

    def __str__(self):
        return f"{self.donacion.numero} - {self.producto.nombre} x {self.cantidad}"
    
    def save(self, *args, **kwargs):
        # Si es nuevo registro, cantidad_disponible = cantidad
        if not self.pk and not self.cantidad_disponible:
            self.cantidad_disponible = self.cantidad
        super().save(*args, **kwargs)


class SalidaDonacion(models.Model):
    """
    Registro de entregas/salidas del almacen de donaciones.
    Permite control interno sin afectar movimientos principales.
    """
    detalle_donacion = models.ForeignKey(
        DetalleDonacion, 
        on_delete=models.PROTECT, 
        related_name='salidas',
        db_column='detalle_donacion_id'
    )
    cantidad = models.IntegerField()
    destinatario = models.CharField(max_length=255)  # Nombre del interno/paciente o area
    motivo = models.TextField(blank=True, null=True)
    entregado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='entregas_donaciones',
        db_column='entregado_por_id'
    )
    fecha_entrega = models.DateTimeField(auto_now_add=True)
    notas = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'salidas_donaciones'
        managed = False  # Tabla en Supabase
        ordering = ['-fecha_entrega']

    def __str__(self):
        return f"Salida {self.id} - {self.destinatario} x {self.cantidad}"
    
    def save(self, *args, **kwargs):
        # Validar que hay stock disponible
        if self.pk is None:  # Solo en creacion
            if self.cantidad > self.detalle_donacion.cantidad_disponible:
                raise ValueError(
                    f"Stock insuficiente. Disponible: {self.detalle_donacion.cantidad_disponible}, "
                    f"Solicitado: {self.cantidad}"
                )
            # Descontar del stock disponible
            self.detalle_donacion.cantidad_disponible -= self.cantidad
            self.detalle_donacion.save()
        super().save(*args, **kwargs)


# =============================================================================
# FLUJO V2: MODELOS DE AUDITORÍA Y TRAZABILIDAD DE REQUISICIONES
# =============================================================================

class RequisicionHistorialEstados(models.Model):
    """
    FLUJO V2: Historial inmutable de cambios de estado de requisiciones.
    
    Cada cambio de estado se registra con fecha, usuario responsable y contexto.
    Permite auditoría completa y detección de fraude.
    """
    ACCIONES_FLUJO = [
        ('crear', 'Crear requisición'),
        ('enviar_a_administrador', 'Enviar a Administrador'),
        ('autorizar_administrador', 'Autorizar por Administrador'),
        ('enviar_a_director', 'Enviar a Director'),
        ('autorizar_director', 'Autorizar por Director'),
        ('enviar_farmacia', 'Enviar a Farmacia'),
        ('recibir_farmacia', 'Recibir en Farmacia'),
        ('autorizar_farmacia', 'Autorizar en Farmacia'),
        ('iniciar_surtido', 'Iniciar surtido'),
        ('completar_surtido', 'Completar surtido'),
        ('confirmar_entrega', 'Confirmar entrega'),
        ('rechazar', 'Rechazar'),
        ('devolver_centro', 'Devolver al Centro'),
        ('vencer', 'Marcar como vencida'),
        ('vencer_automatico', 'Vencimiento automático'),
        ('cancelar', 'Cancelar'),
        ('cambio_estado', 'Cambio de estado'),
    ]
    
    requisicion = models.ForeignKey(
        Requisicion, 
        on_delete=models.CASCADE, 
        related_name='historial_estados',
        db_column='requisicion_id'
    )
    estado_anterior = models.CharField(max_length=50, blank=True, null=True)
    estado_nuevo = models.CharField(max_length=50)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='historial_requisiciones',
        db_column='usuario_id'
    )
    fecha_cambio = models.DateTimeField(auto_now_add=True)
    accion = models.CharField(max_length=100, choices=ACCIONES_FLUJO, default='cambio_estado')
    motivo = models.TextField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    ip_address = models.CharField(max_length=45, blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    datos_adicionales = models.JSONField(blank=True, null=True)
    hash_verificacion = models.CharField(max_length=64, blank=True, null=True)

    class Meta:
        db_table = 'requisicion_historial_estados'
        managed = False  # Tabla en Supabase
        ordering = ['-fecha_cambio']

    def __str__(self):
        return f"REQ-{self.requisicion.numero}: {self.estado_anterior} → {self.estado_nuevo}"
    
    @classmethod
    def registrar_cambio(cls, requisicion, estado_anterior, estado_nuevo, 
                         usuario=None, accion='cambio_estado', motivo=None,
                         ip_address=None, user_agent=None, datos_adicionales=None):
        """
        Método helper para registrar cambios de estado.
        """
        import hashlib
        import json
        from django.utils import timezone
        
        # Crear hash de verificación
        data_to_hash = f"{requisicion.id}|{estado_anterior}|{estado_nuevo}|{timezone.now().isoformat()}"
        hash_verificacion = hashlib.sha256(data_to_hash.encode()).hexdigest()
        
        return cls.objects.create(
            requisicion=requisicion,
            estado_anterior=estado_anterior,
            estado_nuevo=estado_nuevo,
            usuario=usuario,
            accion=accion,
            motivo=motivo,
            ip_address=ip_address,
            user_agent=user_agent,
            datos_adicionales=datos_adicionales,
            hash_verificacion=hash_verificacion
        )


class RequisicionAjusteCantidad(models.Model):
    """
    FLUJO V2: Registro de ajustes de cantidad realizados por Farmacia.
    
    Cuando Farmacia autoriza menos cantidad de la solicitada,
    debe registrar el motivo para auditoría.
    """
    TIPOS_AJUSTE = [
        ('sin_stock', 'Sin stock suficiente'),
        ('producto_agotado', 'Producto agotado'),
        ('sustitucion', 'Sustitución por otro producto'),
        ('correccion_cantidad', 'Corrección de cantidad'),
        ('lote_proximo_caducar', 'Lote próximo a caducar'),
    ]
    
    detalle_requisicion = models.ForeignKey(
        DetalleRequisicion,
        on_delete=models.CASCADE,
        related_name='ajustes',
        db_column='detalle_requisicion_id'
    )
    cantidad_original = models.IntegerField()
    cantidad_ajustada = models.IntegerField()
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='ajustes_cantidad',
        db_column='usuario_id'
    )
    fecha_ajuste = models.DateTimeField(auto_now_add=True)
    motivo_ajuste = models.TextField()
    tipo_ajuste = models.CharField(max_length=50, choices=TIPOS_AJUSTE)
    producto_sustituto = models.ForeignKey(
        Producto,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sustituciones',
        db_column='producto_sustituto_id'
    )
    ip_address = models.CharField(max_length=45, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'requisicion_ajustes_cantidad'
        managed = False  # Tabla en Supabase
        ordering = ['-fecha_ajuste']

    def __str__(self):
        return f"Ajuste {self.detalle_requisicion}: {self.cantidad_original} → {self.cantidad_ajustada}"

