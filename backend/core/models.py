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
    Modelo de Producto Farmacéutico
    Adaptado a la estructura de base de datos existente
    
    Campos reales en BD: id, clave, descripcion, unidad_medida, precio_unitario, 
    stock_minimo, activo, created_at, updated_at, created_by_id, codigo_barras_producto
    """
    clave = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    unidad_medida = models.CharField(max_length=50)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    stock_minimo = models.IntegerField(default=0)
    activo = models.BooleanField(default=True)
    codigo_barras_producto = models.CharField(max_length=100, blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='productos_creados')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'productos'
        ordering = ['clave']
        managed = False  # La tabla ya existe en la BD

    def __str__(self):
        return f"{self.clave} - {self.descripcion or 'Sin descripción'}"
    
    # Propiedades para compatibilidad con código existente
    @property
    def nombre(self):
        return self.descripcion or self.clave
    
    @property
    def codigo_barras(self):
        return self.codigo_barras_producto
    
    def get_stock_actual(self, centro=None):
        """Calcula el stock actual sumando lotes disponibles."""
        from django.db.models import Sum
        
        filtros = {'deleted_at__isnull': True, 'cantidad_actual__gt': 0}
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
    Modelo de Lote de Producto
    Adaptado a la estructura de base de datos existente
    """
    numero_lote = models.CharField(max_length=100)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='lotes')
    cantidad_inicial = models.IntegerField(default=0)
    cantidad_actual = models.IntegerField(default=0)
    fecha_fabricacion = models.DateField(null=True, blank=True, db_column='fecha_entrada')
    fecha_caducidad = models.DateField()
    estado = models.CharField(max_length=50, default='disponible')
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='precio_compra')
    numero_contrato = models.CharField(max_length=100, blank=True, null=True)
    marca = models.CharField(max_length=100, blank=True, null=True)
    proveedor = models.CharField(max_length=200, blank=True, null=True)
    factura = models.CharField(max_length=100, blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    codigo_barras = models.CharField(max_length=100, blank=True, null=True)
    centro = models.ForeignKey('Centro', on_delete=models.SET_NULL, null=True, blank=True, related_name='lotes_centro')
    lote_origen = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='lotes_derivados')
    contrato = models.IntegerField(null=True, blank=True, db_column='contrato_id')  # FK a tabla contratos si existe
    documento_nombre = models.CharField(max_length=255, blank=True, null=True)
    documento_pdf = models.TextField(blank=True, null=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='lotes_creados')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='lotes_actualizados')

    class Meta:
        db_table = 'lotes'
        ordering = ['-created_at']
        managed = False  # La tabla ya existe en la BD

    def __str__(self):
        return f"{self.numero_lote} - {self.producto.nombre if self.producto else 'N/A'}"
    
    @property
    def estado_calculado(self):
        """Calcula el estado basado en cantidad y caducidad (alternativo al campo estado)"""
        from django.utils import timezone
        if self.cantidad_actual <= 0:
            return 'agotado'
        if self.fecha_caducidad and self.fecha_caducidad < timezone.now().date():
            return 'caducado'
        return 'disponible'
    
    # Alias para compatibilidad
    @property
    def activo(self):
        return self.deleted_at is None
    
    @property
    def ubicacion(self):
        """Alias de compatibilidad - retorna el nombre del centro"""
        return self.centro.nombre if self.centro else None
    
    # Alias para serializer
    @property
    def precio_compra(self):
        return self.precio_unitario
    
    @property
    def fecha_entrada(self):
        return self.fecha_fabricacion
    
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
        elif dias <= 7:
            return 'critico'
        elif dias <= 30:
            return 'proximo'
        return 'normal'


class Movimiento(models.Model):
    """
    Modelo de Movimiento de inventario
    Adaptado a la estructura de base de datos existente
    
    Campos reales en BD: id, tipo, cantidad, observaciones, fecha, centro_id, 
    lote_id, requisicion_id, documento_referencia, lugar_entrega, usuario_id
    """
    tipo = models.CharField(max_length=50)
    lote = models.ForeignKey(Lote, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos')
    cantidad = models.IntegerField()
    observaciones = models.TextField(blank=True, null=True)
    fecha = models.DateTimeField(auto_now_add=True)
    centro = models.ForeignKey('Centro', on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos')
    requisicion = models.ForeignKey('Requisicion', on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    documento_referencia = models.CharField(max_length=255, blank=True, null=True)
    lugar_entrega = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        db_table = 'movimientos'
        ordering = ['-fecha']
        managed = False  # La tabla ya existe en la BD

    def __str__(self):
        return f"{self.tipo} - {self.cantidad} - {self.fecha}"
    
    # Propiedades para compatibilidad con código que espera producto
    @property
    def producto(self):
        return self.lote.producto if self.lote else None


class Requisicion(models.Model):
    """
    Modelo de Requisicion
    Adaptado a la estructura de base de datos existente
    
    Campos reales en BD: id, folio, fecha_solicitud, estado, observaciones, 
    fecha_autorizacion, motivo_rechazo, created_at, updated_at, centro_id, 
    usuario_autoriza_id, usuario_solicita_id, fecha_recibido, lugar_entrega, 
    observaciones_recepcion, usuario_recibe_id, updated_by_id
    """
    folio = models.CharField(max_length=50, unique=True)
    centro = models.ForeignKey('Centro', on_delete=models.SET_NULL, null=True, blank=True, related_name='requisiciones')
    usuario_solicita = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='requisiciones_solicitadas')
    usuario_autoriza = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='requisiciones_autorizadas')
    usuario_recibe = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='requisiciones_recibidas')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='requisiciones_actualizadas')
    estado = models.CharField(max_length=50, default='borrador')
    observaciones = models.TextField(blank=True, null=True)
    observaciones_recepcion = models.TextField(blank=True, null=True)
    motivo_rechazo = models.TextField(blank=True, null=True)
    lugar_entrega = models.CharField(max_length=200, blank=True, null=True)
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_autorizacion = models.DateTimeField(null=True, blank=True)
    fecha_recibido = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'requisiciones'
        ordering = ['-fecha_solicitud']
        managed = False  # La tabla ya existe en la BD

    def __str__(self):
        return f"REQ-{self.folio}"
    
    # Propiedades para compatibilidad con código existente
    @property
    def numero(self):
        return self.folio
    
    @property
    def solicitante(self):
        return self.usuario_solicita
    
    @property
    def autorizador(self):
        return self.usuario_autoriza
    
    @property
    def notas(self):
        return self.observaciones


class DetalleRequisicion(models.Model):
    """
    Detalle de Requisicion
    Adaptado a la estructura de base de datos existente
    
    Campos reales en BD: id, cantidad_solicitada, cantidad_autorizada, cantidad_surtida,
    observaciones, producto_id, requisicion_id, lote_id, cantidad_reservada, fecha_reserva
    """
    requisicion = models.ForeignKey(Requisicion, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    lote = models.ForeignKey(Lote, on_delete=models.SET_NULL, null=True, blank=True)
    cantidad_solicitada = models.IntegerField()
    cantidad_autorizada = models.IntegerField(null=True, blank=True)
    cantidad_surtida = models.IntegerField(null=True, blank=True)
    cantidad_reservada = models.IntegerField(null=True, blank=True)
    observaciones = models.TextField(blank=True, null=True)
    fecha_reserva = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'detalles_requisicion'
        managed = False  # La tabla ya existe en la BD

    def __str__(self):
        return f"{self.requisicion.folio} - {self.producto.clave}"
    
    @property
    def notas(self):
        return self.observaciones


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
    Configuración del tema visual
    Adaptado a la estructura de base de datos existente
    """
    nombre = models.CharField(max_length=100, default='Tema Default')
    es_activo = models.BooleanField(default=False, db_column='es_activo')
    logo_url = models.CharField(max_length=500, blank=True, null=True)
    logo_width = models.IntegerField(null=True, blank=True)
    logo_height = models.IntegerField(null=True, blank=True)
    favicon_url = models.CharField(max_length=500, blank=True, null=True)
    titulo_sistema = models.CharField(max_length=200, blank=True, null=True)
    subtitulo_sistema = models.CharField(max_length=200, blank=True, null=True)
    color_primario = models.CharField(max_length=20, blank=True, null=True)
    color_primario_hover = models.CharField(max_length=20, blank=True, null=True)
    color_secundario = models.CharField(max_length=20, blank=True, null=True)
    color_secundario_hover = models.CharField(max_length=20, blank=True, null=True)
    color_exito = models.CharField(max_length=20, blank=True, null=True)
    color_exito_hover = models.CharField(max_length=20, blank=True, null=True)
    color_alerta = models.CharField(max_length=20, blank=True, null=True)
    color_alerta_hover = models.CharField(max_length=20, blank=True, null=True)
    color_error = models.CharField(max_length=20, blank=True, null=True)
    color_error_hover = models.CharField(max_length=20, blank=True, null=True)
    color_info = models.CharField(max_length=20, blank=True, null=True)
    color_info_hover = models.CharField(max_length=20, blank=True, null=True)
    color_fondo_principal = models.CharField(max_length=20, blank=True, null=True)
    color_fondo_sidebar = models.CharField(max_length=20, blank=True, null=True)
    color_fondo_header = models.CharField(max_length=20, blank=True, null=True)
    color_texto_principal = models.CharField(max_length=20, blank=True, null=True)
    color_texto_sidebar = models.CharField(max_length=20, blank=True, null=True)
    color_texto_header = models.CharField(max_length=20, blank=True, null=True)
    color_texto_links = models.CharField(max_length=20, blank=True, null=True)
    color_borde_inputs = models.CharField(max_length=20, blank=True, null=True)
    color_borde_focus = models.CharField(max_length=20, blank=True, null=True)
    reporte_color_encabezado = models.CharField(max_length=20, blank=True, null=True)
    reporte_color_texto = models.CharField(max_length=20, blank=True, null=True)
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


class ConfiguracionSistema(models.Model):
    """
    Configuración del sistema
    Adaptado a la estructura de base de datos existente
    """
    clave = models.CharField(max_length=100, unique=True)
    valor = models.TextField()
    descripcion = models.TextField(blank=True, null=True)
    tipo = models.CharField(max_length=50, default='texto')
    es_publica = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'configuracion_sistema'
        managed = False  # La tabla ya existe en la BD

    def __str__(self):
        return self.clave


class HojaRecoleccion(models.Model):
    """
    Hoja de Recolección
    Adaptado a la estructura de base de datos existente
    """
    numero = models.CharField(max_length=50, unique=True)
    centro = models.ForeignKey('Centro', on_delete=models.SET_NULL, null=True, blank=True)
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='hojas_responsable')
    estado = models.CharField(max_length=50, default='pendiente')
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
    Detalle de Hoja de Recolección
    Adaptado a la estructura de base de datos existente
    """
    hoja = models.ForeignKey(HojaRecoleccion, on_delete=models.CASCADE, related_name='detalles', db_column='hoja_id')
    lote = models.ForeignKey(Lote, on_delete=models.PROTECT)
    cantidad_recolectar = models.IntegerField()
    cantidad_recolectada = models.IntegerField(null=True, blank=True)
    motivo = models.CharField(max_length=100)
    observaciones = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'detalle_hojas_recoleccion'
        managed = False  # La tabla ya existe en la BD


class ImportacionLog(models.Model):
    """
    Log de Importaciones
    Adaptado a la estructura de base de datos existente
    """
    archivo = models.CharField(max_length=255)
    tipo_importacion = models.CharField(max_length=50)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    registros_totales = models.IntegerField(default=0)
    registros_exitosos = models.IntegerField(default=0)
    registros_fallidos = models.IntegerField(default=0)
    errores = models.JSONField(null=True, blank=True)
    estado = models.CharField(max_length=50, default='pendiente')
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'importacion_logs'
        managed = False  # La tabla ya existe en la BD


class AuditLog(models.Model):
    """
    Log de Auditoría
    Adaptado a la estructura de base de datos existente
    """
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    accion = models.CharField(max_length=50)
    modelo = models.CharField(max_length=100)
    objeto_id = models.CharField(max_length=100, null=True, blank=True)
    datos_anteriores = models.JSONField(null=True, blank=True)
    datos_nuevos = models.JSONField(null=True, blank=True)
    ip_address = models.CharField(max_length=45, null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    detalles = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'auditoria_logs'
        managed = False  # La tabla ya existe en la BD


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


