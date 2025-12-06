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
    Adaptado a la estructura de base de datos existente
    
    Campos reales en BD: id, clave, nombre, tipo, direccion, telefono, 
    responsable, activo, created_at, updated_at
    """
    clave = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=50, blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    responsable = models.CharField(max_length=200, blank=True, null=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'centros'
        ordering = ['nombre']
        managed = False  # La tabla ya existe en la BD

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    """
    Modelo de Producto Farmacéutico - Supabase
    
    Campos en Supabase: id, clave, descripcion, unidad_medida, precio_unitario,
    stock_minimo, stock_maximo, activo, codigo_barras, imagen, created_at, updated_at
    """
    clave = models.CharField(max_length=50, unique=True)
    descripcion = models.CharField(max_length=500)
    unidad_medida = models.CharField(max_length=20, default='pieza')
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    stock_minimo = models.IntegerField(default=0)
    stock_maximo = models.IntegerField(default=0)
    activo = models.BooleanField(default=True)
    codigo_barras = models.CharField(max_length=50, blank=True, null=True)
    imagen = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'productos'
        ordering = ['clave']
        managed = False  # Tabla en Supabase

    def __str__(self):
        return f"{self.clave} - {self.descripcion}"
    
    # Alias para compatibilidad con código que usa 'nombre'
    @property
    def nombre(self):
        return self.descripcion
    
    def get_stock_actual(self, centro=None):
        """Calcula el stock actual sumando lotes disponibles."""
        from django.db.models import Sum
        
        filtros = {'estado': 'disponible', 'cantidad_actual__gt': 0}
        if centro and centro != 'todos':
            filtros['centro'] = centro
        
        return self.lotes.filter(**filtros).aggregate(
            total=Sum('cantidad_actual')
        )['total'] or 0
    
    def get_nivel_stock(self):
        """Retorna el nivel de stock basado en stock actual vs stock mínimo."""
        stock_actual = self.get_stock_actual()
        stock_minimo = self.stock_minimo or 0
        
        if stock_actual == 0:
            return 'sin_stock'
        elif stock_minimo > 0:
            porcentaje = (stock_actual / stock_minimo) * 100
            if porcentaje <= 25:
                return 'critico'
            elif porcentaje <= 50:
                return 'bajo'
            elif porcentaje <= 150:
                return 'normal'
            else:
                return 'alto'
        return 'normal'


class Lote(models.Model):
    """
    Modelo de Lote de Producto - Supabase
    
    Campos en Supabase: id, producto_id, centro_id, numero_lote, fecha_caducidad,
    fecha_entrada, cantidad_inicial, cantidad_actual, precio_compra, estado,
    ubicacion, observaciones, documento_soporte, created_at, updated_at
    """
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='lotes')
    centro = models.ForeignKey('Centro', on_delete=models.SET_NULL, null=True, blank=True, related_name='lotes_centro')
    numero_lote = models.CharField(max_length=100)
    fecha_caducidad = models.DateField()
    fecha_entrada = models.DateField()
    cantidad_inicial = models.IntegerField(default=0)
    cantidad_actual = models.IntegerField(default=0)
    precio_compra = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado = models.CharField(max_length=20, default='disponible')
    ubicacion = models.CharField(max_length=100, blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    documento_soporte = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'lotes'
        ordering = ['-created_at']
        managed = False  # Tabla en Supabase

    def __str__(self):
        return f"{self.numero_lote} - {self.producto.nombre if self.producto else 'N/A'}"
    
    # Alias para compatibilidad
    @property
    def precio_unitario(self):
        return self.precio_compra
    
    @property
    def activo(self):
        return self.estado == 'disponible'
    
    def dias_para_caducar(self):
        """Calcula días restantes para caducidad"""
        from django.utils import timezone
        if not self.fecha_caducidad:
            return None
        delta = self.fecha_caducidad - timezone.now().date()
        return delta.days
    
    def esta_caducado(self):
        """Indica si el lote está vencido"""
        from django.utils import timezone
        if not self.fecha_caducidad:
            return False
        return self.fecha_caducidad < timezone.now().date()
    
    def alerta_caducidad(self):
        """Nivel de alerta: vencido, critico, proximo, normal"""
        dias = self.dias_para_caducar()
        if dias is None:
            return 'normal'
        if dias < 0:
            return 'vencido'
        elif dias <= 90:
            return 'critico'
        elif dias <= 180:
            return 'proximo'
        return 'normal'


class Movimiento(models.Model):
    """
    Modelo de Movimiento de inventario - Supabase
    
    Campos en Supabase: id, tipo, producto_id, lote_id, cantidad, centro_origen_id,
    centro_destino_id, requisicion_id, usuario_id, motivo, referencia, fecha, created_at
    """
    tipo = models.CharField(max_length=20)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='movimientos')
    lote = models.ForeignKey(Lote, on_delete=models.PROTECT, null=True, blank=True, related_name='movimientos')
    cantidad = models.IntegerField()
    centro_origen = models.ForeignKey('Centro', on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos_origen')
    centro_destino = models.ForeignKey('Centro', on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos_destino')
    requisicion = models.ForeignKey('Requisicion', on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    motivo = models.TextField(blank=True, null=True)
    referencia = models.CharField(max_length=100, blank=True, null=True)
    fecha = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'movimientos'
        ordering = ['-fecha']
        managed = False  # Tabla en Supabase

    def __str__(self):
        return f"{self.tipo} - {self.cantidad} - {self.fecha}"
    
    # Alias para compatibilidad
    @property
    def centro(self):
        return self.centro_origen or self.centro_destino
    
    @property
    def observaciones(self):
        return self.motivo


class Requisicion(models.Model):
    """
    Modelo de Requisicion - Supabase
    
    Campos en Supabase: id, numero, centro_origen_id, centro_destino_id, solicitante_id,
    autorizador_id, estado, tipo, prioridad, notas, lugar_entrega, fecha_solicitud,
    fecha_autorizacion, fecha_surtido, fecha_entrega, foto_firma_surtido, foto_firma_recepcion,
    usuario_firma_surtido_id, usuario_firma_recepcion_id, fecha_firma_surtido, fecha_firma_recepcion,
    created_at, updated_at
    """
    numero = models.CharField(max_length=50, unique=True)
    centro_origen = models.ForeignKey('Centro', on_delete=models.SET_NULL, null=True, blank=True, related_name='requisiciones_origen')
    centro_destino = models.ForeignKey('Centro', on_delete=models.SET_NULL, null=True, blank=True, related_name='requisiciones_destino')
    solicitante = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='requisiciones_solicitadas')
    autorizador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='requisiciones_autorizadas')
    estado = models.CharField(max_length=20, default='borrador')
    tipo = models.CharField(max_length=50, default='normal')
    prioridad = models.CharField(max_length=20, default='normal')
    notas = models.TextField(blank=True, null=True)
    lugar_entrega = models.CharField(max_length=200, blank=True, null=True)
    fecha_solicitud = models.DateTimeField()
    fecha_autorizacion = models.DateTimeField(null=True, blank=True)
    fecha_surtido = models.DateTimeField(null=True, blank=True)
    fecha_entrega = models.DateTimeField(null=True, blank=True)
    foto_firma_surtido = models.CharField(max_length=255, blank=True, null=True)
    foto_firma_recepcion = models.CharField(max_length=255, blank=True, null=True)
    usuario_firma_surtido = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='firmas_surtido')
    usuario_firma_recepcion = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='firmas_recepcion')
    fecha_firma_surtido = models.DateTimeField(null=True, blank=True)
    fecha_firma_recepcion = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'requisiciones'
        ordering = ['-fecha_solicitud']
        managed = False  # Tabla en Supabase

    def __str__(self):
        return f"REQ-{self.numero}"
    
    # Aliases para compatibilidad con código existente
    @property
    def folio(self):
        return self.numero
    
    @property
    def centro(self):
        return self.centro_destino or self.centro_origen
    
    @property
    def observaciones(self):
        return self.notas


class DetalleRequisicion(models.Model):
    """
    Detalle de Requisicion - Supabase
    
    Campos en Supabase: id, requisicion_id, producto_id, lote_id, cantidad_solicitada,
    cantidad_autorizada, cantidad_surtida, cantidad_recibida, notas, created_at, updated_at
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
        managed = False  # Tabla en Supabase

    def __str__(self):
        return f"{self.requisicion.numero} - {self.producto.nombre}"


class Notificacion(models.Model):
    """
    Modelo de Notificacion - Supabase
    
    Campos en Supabase: id, usuario_id, tipo, titulo, mensaje, leida, datos, url, created_at
    """
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notificaciones')
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
        managed = False  # La tabla ya existe en Supabase

    def __str__(self):
        return f"{self.titulo} - {self.usuario.username}"


class TemaGlobal(models.Model):
    """
    Configuración del tema visual - Supabase
    
    Campos en Supabase: id, nombre, logo_url, color_primario, color_secundario,
    color_fondo, color_texto, activo, updated_at
    """
    nombre = models.CharField(max_length=100, default='Gobierno del Estado de México')
    logo_url = models.CharField(max_length=500, blank=True, null=True)
    color_primario = models.CharField(max_length=7, default='#6d1a36')
    color_secundario = models.CharField(max_length=7, default='#c9a227')
    color_fondo = models.CharField(max_length=7, default='#faf7f2')
    color_texto = models.CharField(max_length=7, default='#1a1a1a')
    activo = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tema_global'
        managed = False  # Tabla en Supabase

    def __str__(self):
        return self.nombre


class ConfiguracionSistema(models.Model):
    """
    Configuración del sistema - Supabase
    
    Campos en Supabase: id, clave, valor, descripcion, tipo, updated_at
    """
    clave = models.CharField(max_length=100, unique=True)
    valor = models.TextField(blank=True, null=True)
    descripcion = models.CharField(max_length=500, blank=True, null=True)
    tipo = models.CharField(max_length=20, default='texto')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'configuracion_sistema'
        managed = False  # Tabla en Supabase

    def __str__(self):
        return self.clave


class HojaRecoleccion(models.Model):
    """
    Hoja de Recolección - Supabase
    
    Campos en Supabase: id, requisicion_id, folio, estado, fecha_generacion,
    fecha_inicio, fecha_fin, usuario_recolector_id, observaciones
    """
    requisicion = models.ForeignKey(Requisicion, on_delete=models.CASCADE, related_name='hojas_recoleccion')
    folio = models.CharField(max_length=50, unique=True)
    estado = models.CharField(max_length=20, default='pendiente')
    fecha_generacion = models.DateTimeField()
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    usuario_recolector = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='hojas_recolector')
    observaciones = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'hojas_recoleccion'
        managed = False  # Tabla en Supabase

    def __str__(self):
        return f"HR-{self.folio}"


class DetalleHojaRecoleccion(models.Model):
    """
    Detalle de Hoja de Recolección - Supabase
    
    Campos en Supabase: id, hoja_recoleccion_id, detalle_requisicion_id, lote_id,
    cantidad_recolectada, ubicacion, recolectado, orden
    """
    hoja_recoleccion = models.ForeignKey(HojaRecoleccion, on_delete=models.CASCADE, related_name='detalles')
    detalle_requisicion = models.ForeignKey(DetalleRequisicion, on_delete=models.CASCADE)
    lote = models.ForeignKey(Lote, on_delete=models.SET_NULL, null=True, blank=True)
    cantidad_recolectada = models.IntegerField(default=0)
    ubicacion = models.CharField(max_length=100, blank=True, null=True)
    recolectado = models.BooleanField(default=False)
    orden = models.IntegerField(default=0)

    class Meta:
        db_table = 'detalles_hoja_recoleccion'
        managed = False  # Tabla en Supabase


class ImportacionLog(models.Model):
    """
    Log de Importaciones - Supabase
    
    Campos en Supabase: id, usuario_id, archivo_nombre, tipo_importacion,
    registros_procesados, registros_exitosos, registros_fallidos, errores, created_at
    """
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    archivo_nombre = models.CharField(max_length=255)
    tipo_importacion = models.CharField(max_length=50)
    registros_procesados = models.IntegerField(default=0)
    registros_exitosos = models.IntegerField(default=0)
    registros_fallidos = models.IntegerField(default=0)
    errores = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'importacion_log'
        managed = False  # Tabla en Supabase


class AuditLog(models.Model):
    """
    Log de Auditoría - Supabase
    
    Campos en Supabase: id, usuario_id, accion, modelo, objeto_id,
    datos_antes, datos_despues, ip_address, user_agent, created_at
    """
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    accion = models.CharField(max_length=50)
    modelo = models.CharField(max_length=100)
    objeto_id = models.CharField(max_length=100, null=True, blank=True)
    datos_antes = models.JSONField(null=True, blank=True)
    datos_despues = models.JSONField(null=True, blank=True)
    ip_address = models.CharField(max_length=45, null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_log'
        managed = False  # Tabla en Supabase


# Alias para compatibilidad con código existente
AuditoriaLog = AuditLog


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


