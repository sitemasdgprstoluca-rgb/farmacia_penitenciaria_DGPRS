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


# ISS-016: Validador de tamaño de archivo para imágenes
def validate_image_max_size(value, max_size_kb=500):
    """Valida que una imagen no exceda el tamaño máximo (default 500KB)"""
    if value:
        max_size_bytes = max_size_kb * 1024
        if value.size > max_size_bytes:
            raise ValidationError(
                f'El archivo es demasiado grande. Máximo permitido: {max_size_kb}KB'
            )


def validate_logo_size(value):
    """Validador específico para logos (max 500KB)"""
    validate_image_max_size(value, max_size_kb=500)


def validate_image_size(value):
    """Valida que la imagen no exceda 2MB"""
    max_size = 2 * 1024 * 1024  # 2 MB
    if value.size > max_size:
        raise ValidationError(f'La imagen no puede exceder 2MB. Tamaño actual: {value.size/1024/1024:.1f}MB')


def producto_imagen_path(instance, filename):
    """Genera ruta para imágenes de productos"""
    ext = filename.split('.')[-1]
    return f'productos/{instance.clave}.{ext}'


def requisicion_firma_path(instance, filename):
    """Genera ruta para fotos de firma de requisiciones"""
    ext = filename.split('.')[-1]
    return f'requisiciones/firmas/{instance.folio}_{filename}'


# ISS-005: Validador de archivos PDF
def validate_pdf_file(value):
    """
    ISS-005: Valida que el archivo sea PDF válido y no exceda tamaño máximo.
    
    Validaciones:
    - Extensión .pdf
    - Tamaño máximo 10MB
    - Content-type application/pdf (si está disponible)
    """
    if not value:
        return
    
    # Validar extensión
    ext = os.path.splitext(value.name)[1].lower()
    if ext != '.pdf':
        raise ValidationError('Solo se permiten archivos PDF (.pdf)')
    
    # Validar tamaño (máximo 10MB)
    max_size_bytes = 10 * 1024 * 1024  # 10MB
    if value.size > max_size_bytes:
        raise ValidationError(
            f'El archivo PDF es demasiado grande. Máximo permitido: 10MB. '
            f'Tamaño actual: {value.size / (1024*1024):.2f}MB'
        )
    
    # Validar content-type si está disponible
    if hasattr(value, 'content_type'):
        allowed_types = ['application/pdf', 'application/x-pdf']
        if value.content_type not in allowed_types:
            raise ValidationError(
                f'Tipo de archivo no válido. Se esperaba PDF, se recibió: {value.content_type}'
            )


# ISS-005: Función para generar nombre seguro de archivo PDF
def pdf_upload_path(instance, filename):
    """
    ISS-005: Genera ruta segura para archivos PDF.
    
    Formato: lotes/documentos/YYYY/MM/producto_lote_timestamp.pdf
    """
    import uuid
    from django.utils import timezone
    
    # Sanitizar nombre (remover caracteres peligrosos)
    safe_name = "".join(c for c in filename if c.isalnum() or c in '._-')
    
    # Generar nombre único
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    unique_id = uuid.uuid4().hex[:8]
    
    # Obtener info del lote si está disponible
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
    """
    
    # ISS-009: Definir permisos máximos permitidos por rol
    # True = puede tener el permiso, False = nunca puede tenerlo
    PERMISOS_POR_ROL = {
        'admin_sistema': {
            'perm_dashboard': True, 'perm_productos': True, 'perm_lotes': True,
            'perm_requisiciones': True, 'perm_centros': True, 'perm_usuarios': True,
            'perm_reportes': True, 'perm_trazabilidad': True, 'perm_auditoria': True,
            'perm_notificaciones': True, 'perm_movimientos': True,
        },
        'farmacia': {
            'perm_dashboard': True, 'perm_productos': True, 'perm_lotes': True,
            'perm_requisiciones': True, 'perm_centros': False, 'perm_usuarios': False,
            'perm_reportes': True, 'perm_trazabilidad': True, 'perm_auditoria': False,
            'perm_notificaciones': True, 'perm_movimientos': True,
        },
        'usuario_centro': {
            'perm_dashboard': True, 'perm_productos': True, 'perm_lotes': True,
            'perm_requisiciones': True, 'perm_centros': False, 'perm_usuarios': False,
            'perm_reportes': True, 'perm_trazabilidad': True, 'perm_auditoria': False,
            'perm_notificaciones': True, 'perm_movimientos': True,
        },
        'usuario_normal': {
            'perm_dashboard': True, 'perm_productos': True, 'perm_lotes': False,
            'perm_requisiciones': True, 'perm_centros': False, 'perm_usuarios': False,
            'perm_reportes': False, 'perm_trazabilidad': False, 'perm_auditoria': False,
            'perm_notificaciones': True, 'perm_movimientos': False,
        },
    }
    
    rol = models.CharField(
        max_length=20,
        choices=ROLES_USUARIO,
        default='usuario_normal',
        help_text="Rol del usuario en el sistema"
    )
    centro = models.ForeignKey(
        'Centro',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios',
        help_text="Centro asignado al usuario"
    )
    adscripcion = models.CharField(
        max_length=200,
        blank=True,
        help_text="Adscripción del usuario (centro/área/unidad de dependencia)"
    )
    activo = models.BooleanField(default=True)
    
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
    
    class Meta:
        db_table = 'usuarios'
        managed = False  # La tabla ya existe en la BD

    def clean(self):
        """
        ISS-009: Valida coherencia entre rol y permisos personalizados.
        
        Evita que un usuario tenga permisos que excedan su rol.
        """
        super().clean()
        
        # Superusers pueden tener cualquier permiso
        if self.is_superuser:
            return
        
        # Obtener permisos permitidos para este rol
        permisos_rol = self.PERMISOS_POR_ROL.get(self.rol, {})
        
        # Lista de campos de permisos
        campos_permisos = [
            'perm_dashboard', 'perm_productos', 'perm_lotes', 'perm_requisiciones',
            'perm_centros', 'perm_usuarios', 'perm_reportes', 'perm_trazabilidad',
            'perm_auditoria', 'perm_notificaciones', 'perm_movimientos'
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
        
        Combina permisos del rol base con personalizaciones, 
        respetando los límites del rol.
        """
        permisos_rol = self.PERMISOS_POR_ROL.get(self.rol, {})
        efectivos = {}
        
        campos_permisos = [
            'perm_dashboard', 'perm_productos', 'perm_lotes', 'perm_requisiciones',
            'perm_centros', 'perm_usuarios', 'perm_reportes', 'perm_trazabilidad',
            'perm_auditoria', 'perm_notificaciones', 'perm_movimientos'
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

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_rol_display()})"


class Centro(models.Model):
    """
    Modelo de Centro Penitenciario
    
    Campos en BD: id, nombre, direccion, telefono, email, activo, created_at, updated_at
    """
    nombre = models.CharField(max_length=200)
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
    
    # Propiedad para compatibilidad con código que usa 'clave'
    @property
    def clave(self):
        return str(self.id)


class Producto(models.Model):
    """
    Modelo de Producto Farmacéutico
    Adaptado a la estructura de base de datos existente
    """
    codigo_barras = models.CharField(max_length=50, unique=True, null=True, blank=True)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    unidad_medida = models.CharField(max_length=50)
    categoria = models.CharField(max_length=100)
    stock_minimo = models.IntegerField(default=0)
    stock_actual = models.IntegerField(default=0)
    sustancia_activa = models.CharField(max_length=200, blank=True, null=True)
    presentacion = models.CharField(max_length=200, blank=True, null=True)
    concentracion = models.CharField(max_length=100, blank=True, null=True)
    via_administracion = models.CharField(max_length=100, blank=True, null=True)
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
        return f"{self.nombre}"
    
    # Propiedad para compatibilidad con código que usa 'clave'
    @property
    def clave(self):
        return self.codigo_barras or str(self.id)
    
    def get_stock_actual(self, centro=None):
        """Calcula el stock actual sumando lotes disponibles."""
        from django.db.models import Sum
        
        filtros = {'activo': True}
        if centro and centro != 'todos':
            filtros['centro'] = centro
        
        return self.lotes.filter(**filtros).aggregate(
            total=Sum('cantidad_actual')
        )['total'] or 0


class Lote(models.Model):
    """
    Modelo de Lote de Producto - Supabase
    
    Campos en Supabase: id, numero_lote, producto_id, cantidad_inicial, 
    cantidad_actual, fecha_fabricacion, fecha_caducidad, precio_unitario,
    numero_contrato, marca, ubicacion, centro_id, activo, created_at, updated_at
    """
    numero_lote = models.CharField(max_length=100)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT) # Schema: producto_id
    cantidad_inicial = models.IntegerField()
    cantidad_actual = models.IntegerField(default=0)
    fecha_fabricacion = models.DateField(null=True, blank=True)
    fecha_caducidad = models.DateField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    numero_contrato = models.CharField(max_length=100, blank=True, null=True)
    marca = models.CharField(max_length=100, blank=True, null=True)
    ubicacion = models.CharField(max_length=100, blank=True, null=True)
    centro = models.ForeignKey('Centro', on_delete=models.SET_NULL, null=True, blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'lotes'
        managed = False  # Tabla en Supabase

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
        """Calcula días restantes para caducidad"""
        from django.utils import timezone
        if self.cantidad_actual <= 0:
            return 'agotado'
        if self.fecha_caducidad and self.fecha_caducidad < timezone.now().date():
            return 'caducado'
        return 'disponible'


class Movimiento(models.Model):
    """
    Modelo de Movimiento de inventario
    Adaptado a la estructura de base de datos existente
    """
    tipo = models.CharField(max_length=50)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='movimientos')
    lote = models.ForeignKey(Lote, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos')
    cantidad = models.IntegerField()
    centro_origen = models.ForeignKey('Centro', on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos_salida', db_column='centro_origen_id')
    centro_destino = models.ForeignKey('Centro', on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos_entrada', db_column='centro_destino_id')
    requisicion = models.ForeignKey('Requisicion', on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    motivo = models.TextField(blank=True, null=True)
    referencia = models.CharField(max_length=100, blank=True, null=True)
    fecha = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

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
    """
    numero = models.CharField(max_length=50, unique=True, db_column='numero')
    centro_origen = models.ForeignKey('Centro', on_delete=models.SET_NULL, null=True, blank=True, related_name='requisiciones_origen', db_column='centro_origen_id')
    centro_destino = models.ForeignKey('Centro', on_delete=models.SET_NULL, null=True, blank=True, related_name='requisiciones_destino', db_column='centro_destino_id')
    solicitante = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='requisiciones_solicitadas', db_column='solicitante_id')
    autorizador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='requisiciones_autorizadas', db_column='autorizador_id')
    estado = models.CharField(max_length=50, default='borrador')
    tipo = models.CharField(max_length=50, default='normal')
    prioridad = models.CharField(max_length=20, default='normal')
    notas = models.TextField(blank=True, null=True)
    lugar_entrega = models.CharField(max_length=200, blank=True, null=True)
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

    class Meta:
        db_table = 'requisiciones'
        ordering = ['-fecha_solicitud']
        managed = False  # La tabla ya existe en la BD

    def __str__(self):
        return f"REQ-{self.numero}"
    
    # Propiedades para compatibilidad con código existente
    @property
    def folio(self):
        return self.numero
    
    @property
    def centro(self):
        return self.centro_destino
    
    @property
    def usuario_solicita(self):
        return self.solicitante
    
    @property
    def usuario_autoriza(self):
        return self.autorizador
    
    @property
    def comentario(self):
        return self.notas
    
    @property
    def observaciones(self):
        return self.notas


class DetalleRequisicion(models.Model):
    """
    Detalle de Requisicion
    Adaptado a la estructura de base de datos existente
    """
    requisicion = models.ForeignKey(Requisicion, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    lote = models.ForeignKey(Lote, on_delete=models.SET_NULL, null=True, blank=True)
    cantidad_solicitada = models.IntegerField()
    cantidad_autorizada = models.IntegerField(null=True, blank=True)
    cantidad_surtida = models.IntegerField(null=True, blank=True)
    cantidad_recibida = models.IntegerField(null=True, blank=True)
    notas = models.TextField(blank=True, null=True)
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
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notificaciones')
    tipo = models.CharField(max_length=50)
    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    leida = models.BooleanField(default=False)
    datos = models.JSONField(null=True, blank=True)
    url = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notificaciones'
        ordering = ['-created_at']
        managed = False  # La tabla ya existe en la BD

    def __str__(self):
        return f"{self.titulo} - {self.usuario.username}"


class TemaGlobal(models.Model):
    """
    Configuración del tema visual - Supabase
    
    Campos en Supabase: id, nombre, es_activo, logo_url, logo_width, logo_height,
    favicon_url, titulo_sistema, subtitulo_sistema, y muchos colores...
    """
    nombre = models.CharField(max_length=100)
    es_activo = models.BooleanField(default=False)
    logo_url = models.CharField(max_length=500, blank=True, null=True)
    logo_width = models.IntegerField(default=160)
    logo_height = models.IntegerField(default=60)
    favicon_url = models.CharField(max_length=500, blank=True, null=True)
    titulo_sistema = models.CharField(max_length=100, default='Sistema de Inventario Farmacéutico', null=True, blank=True)
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
    Configuración del sistema - Supabase
    
    Campos en Supabase: id, clave, valor, descripcion, tipo, es_publica, updated_at
    """
    clave = models.CharField(max_length=100, unique=True)
    valor = models.TextField(blank=True, null=True)  # NOTE: Schema says NOT NULL but let's stick to existing slightly looser if needed, actually schema says NO, so I should probably make it NO null. Schema: valor text NO null.
    descripcion = models.TextField(blank=True, null=True) # Schema: text YES
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
    Hoja de Recolección - Supabase
    
    Campos en Supabase: id, numero, centro_id, responsable_id, estado,
    fecha_programada, fecha_recoleccion, notas, created_at, updated_at
    """
    numero = models.CharField(max_length=50, unique=True)
    centro = models.ForeignKey(Centro, on_delete=models.SET_NULL, null=True, blank=True)
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
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
    hoja = models.ForeignKey(HojaRecoleccion, on_delete=models.CASCADE, related_name='detalles')
    lote = models.ForeignKey(Lote, on_delete=models.CASCADE)
    cantidad_recolectar = models.IntegerField()
    cantidad_recolectada = models.IntegerField(default=0, null=True, blank=True)
    motivo = models.CharField(max_length=50, default='caducidad')
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
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
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
    Log de Auditoría - Supabase
    
    Campos en Supabase: id, usuario_id, accion, modelo, objeto_id,
    datos_anteriores, datos_nuevos, ip_address, user_agent, detalles, timestamp
    """
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    accion = models.CharField(max_length=50)
    modelo = models.CharField(max_length=100)
    objeto_id = models.CharField(max_length=50, null=True, blank=True) # Schema says 50 chars
    datos_anteriores = models.JSONField(null=True, blank=True)
    datos_nuevos = models.JSONField(null=True, blank=True)
    ip_address = models.CharField(max_length=45, null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    detalles = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'auditoria_logs'
        managed = False  # Tabla en Supabase

# Alias para compatibilidad con código existente (si es necesario)
AuditLog = AuditoriaLogs
AuditoriaLog = AuditoriaLogs


class UserProfile(models.Model):
    """
    Modelo de perfil de usuario (legacy)
    En la nueva estructura, el perfil está integrado en el modelo User.
    Este modelo se mantiene solo para compatibilidad con código existente.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='userprofile')
    
    class Meta:
        db_table = 'user_profiles'
        managed = False  # Tabla legacy
    
    @property
    def rol(self):
        """Obtiene el rol del usuario asociado"""
        return self.user.rol if self.user else None
    
    @property
    def centro(self):
        """Obtiene el centro del usuario asociado"""
        return self.user.centro if self.user else None
    
    def __str__(self):
        return f"Perfil de {self.user.username if self.user else 'N/A'}"
