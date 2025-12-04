from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date
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
        indexes = [
            models.Index(fields=['rol', 'activo']),
            models.Index(fields=['centro', 'activo']),
        ]

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
    """
    clave = models.CharField(
        max_length=50,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Z0-9\-]+$',
                message='La clave solo puede contener letras mayúsculas, números y guiones'
            )
        ]
    )
    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=100, blank=True)
    direccion = models.TextField(blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    responsable = models.CharField(max_length=200, blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'centros'
        ordering = ['clave']
        indexes = [
            models.Index(fields=['activo']),
            models.Index(fields=['clave']),
        ]

    def __str__(self):
        return f"{self.clave} - {self.nombre}"


class Producto(models.Model):
    """
    Modelo de Producto Farmacéutico
    Validaciones robustas para integridad de datos
    """
    clave = models.CharField(
        max_length=PRODUCTO_CLAVE_MAX_LENGTH,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Za-z0-9\-_]+$',
                message='La clave solo puede contener letras, números, guiones y guiones bajos'
            )
        ],
        help_text=f"Clave unica del producto ({PRODUCTO_CLAVE_MIN_LENGTH}-{PRODUCTO_CLAVE_MAX_LENGTH} caracteres alfanumericos)"
    )
    descripcion = models.TextField(
        help_text=f"Descripción del producto ({PRODUCTO_DESCRIPCION_MIN_LENGTH}-{PRODUCTO_DESCRIPCION_MAX_LENGTH} caracteres)"
    )
    unidad_medida = models.CharField(
        max_length=20,
        choices=UNIDADES_MEDIDA,
        help_text="Unidad de medida del producto"
    )
    precio_unitario = models.DecimalField(
        max_digits=PRODUCTO_PRECIO_MAX_DIGITS,
        decimal_places=PRODUCTO_PRECIO_DECIMAL_PLACES,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Precio unitario del producto"
    )
    stock_minimo = models.IntegerField(
        default=10,
        validators=[MinValueValidator(0)],
        help_text="Cantidad mínima en inventario antes de alerta"
    )
    activo = models.BooleanField(
        default=True,
        help_text="Indica si el producto está activo en el sistema"
    )
    codigo_barras_producto = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        help_text="Código de barras del producto (opcional)"
    )
    
    # Campos de auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='productos_creados'
    )

    class Meta:
        db_table = 'productos'
        ordering = ['clave']
        indexes = [
            models.Index(fields=['activo']),
            models.Index(fields=['clave']),
            models.Index(fields=['unidad_medida']),
            models.Index(fields=['-created_at']),
            # Índices compuestos para queries frecuentes
            models.Index(fields=['activo', 'stock_minimo'], name='idx_producto_activo_stock'),
            models.Index(fields=['clave', 'activo'], name='idx_producto_clave_activo'),
        ]

    def clean(self):
        """Validaciones personalizadas"""
        # Normalizar clave a mayúsculas
        if self.clave:
            self.clave = self.clave.upper().strip()
        
        # Normalizar unidad de medida a mayúsculas
        if self.unidad_medida:
            self.unidad_medida = self.unidad_medida.upper().strip()
            unidades_validas = [unidad[0] for unidad in UNIDADES_MEDIDA]
            if self.unidad_medida not in unidades_validas:
                raise ValidationError({
                    'unidad_medida': f'El valor "{self.unidad_medida}" no es una unidad válida.'
                })

        # Validar longitud de clave
        if self.clave and len(self.clave) < PRODUCTO_CLAVE_MIN_LENGTH:
            raise ValidationError({
                'clave': f'La clave debe tener al menos {PRODUCTO_CLAVE_MIN_LENGTH} caracteres'
            })
        
        # Validar descripción
        if self.descripcion:
            self.descripcion = self.descripcion.strip()
            if len(self.descripcion) < PRODUCTO_DESCRIPCION_MIN_LENGTH:
                raise ValidationError({
                    'descripcion': f'La descripción debe tener al menos {PRODUCTO_DESCRIPCION_MIN_LENGTH} caracteres'
                })
            if len(self.descripcion) > PRODUCTO_DESCRIPCION_MAX_LENGTH:
                raise ValidationError({
                    'descripcion': f'La descripción no puede exceder {PRODUCTO_DESCRIPCION_MAX_LENGTH} caracteres'
                })

    def save(self, *args, **kwargs):
        # ISS-001: Capturar estado ANTES de guardar para log correcto
        is_new = self.pk is None
        self.full_clean()
        super().save(*args, **kwargs)
        logger.info(f"Producto {self.clave} {'creado' if is_new else 'actualizado'}")

    def __str__(self):
        return f"{self.clave} - {self.descripcion[:50]}"
    
    def get_stock_actual(self, centro=None):
        """
        Calcula el stock actual sumando lotes disponibles.
        
        ISS-001 FIX: Ahora soporta filtrado por ubicación:
        - centro=None: Solo farmacia central (lotes sin centro asignado)
        - centro=objeto_centro: Solo lotes de ese centro específico
        - centro='todos': Todos los lotes (comportamiento legacy, NO RECOMENDADO)
        
        Excluye lotes con soft-delete (deleted_at) y lotes vencidos.
        
        Args:
            centro: Centro para filtrar, None para farmacia central, 'todos' para global
            
        Returns:
            int: Stock disponible
        """
        from django.utils import timezone
        from django.db.models import Sum
        
        today = timezone.now().date()
        
        filtros = {
            'estado': 'disponible',
            'deleted_at__isnull': True,
            'fecha_caducidad__gte': today,
        }
        
        # ISS-001: Filtrar por ubicación
        if centro == 'todos':
            # Comportamiento legacy - NO RECOMENDADO para validaciones
            pass
        elif centro is None:
            # Farmacia central: solo lotes sin centro asignado
            filtros['centro__isnull'] = True
        else:
            # Centro específico
            filtros['centro'] = centro
        
        return self.lotes.filter(**filtros).aggregate(
            total=Sum('cantidad_actual')
        )['total'] or 0
    
    def get_stock_farmacia_central(self):
        """
        ISS-001: Obtiene stock disponible SOLO en farmacia central.
        
        Este método debe usarse para validar requisiciones salientes,
        ya que representa el inventario real disponible para distribución.
        
        Returns:
            int: Stock en farmacia central
        """
        return self.get_stock_actual(centro=None)
    
    def get_stock_centro(self, centro):
        """
        ISS-001: Obtiene stock disponible en un centro específico.
        
        Args:
            centro: Instancia del modelo Centro
            
        Returns:
            int: Stock en el centro especificado
        """
        if centro is None:
            return self.get_stock_farmacia_central()
        return self.get_stock_actual(centro=centro)
    
    def get_stock_global(self):
        """
        ISS-001: Obtiene stock total en todo el sistema (farmacia + centros).
        
        ADVERTENCIA: No usar para validar requisiciones salientes.
        El stock en centros ya está comprometido/distribuido.
        
        Returns:
            int: Stock total en el sistema
        """
        return self.get_stock_actual(centro='todos')
    
    def get_nivel_stock(self, centro=None):
        """
        Retorna el nivel de stock: critico, bajo, normal, alto.
        
        ISS-001: Usa stock de farmacia central por defecto para indicadores.
        
        Args:
            centro: Centro para calcular nivel (None = farmacia central)
        """
        stock_actual = self.get_stock_actual(centro=centro)
        
        if stock_actual <= self.stock_minimo * NIVELES_STOCK['critico']:
            return 'critico'
        elif stock_actual <= self.stock_minimo * NIVELES_STOCK['bajo']:
            return 'bajo'
        elif stock_actual <= self.stock_minimo * NIVELES_STOCK['normal']:
            return 'normal'
        else:
            return 'alto'
    
    def get_stock_comprometido(self, centro=None):
        """
        ISS-008: Calcula stock comprometido por requisiciones pendientes.
        
        Stock comprometido = Cantidad autorizada en requisiciones que aún
        no han sido surtidas o recibidas.
        
        Estados que comprometen stock:
        - 'autorizada': Aprobada, pendiente de surtir
        - 'parcial': Parcialmente autorizada/surtida
        - 'surtida': Surtida pero no recibida
        
        Args:
            centro: Centro destino para filtrar (None = todas las requisiciones)
            
        Returns:
            int: Cantidad de stock comprometido
        """
        from django.db.models import Sum
        
        # Estados que comprometen stock (pendientes de surtir o confirmar recepción)
        ESTADOS_COMPROMETIDOS = ['autorizada', 'parcial', 'surtida']
        
        filtros = {
            'requisicion__estado__in': ESTADOS_COMPROMETIDOS,
            'producto': self,
        }
        
        # Filtrar por centro destino si se especifica
        if centro is not None:
            filtros['requisicion__centro'] = centro
        
        # Importar aquí para evitar import circular
        from core.models import DetalleRequisicion
        
        # Calcular: cantidad autorizada - cantidad ya surtida
        # Esto da el stock que aún está pendiente de entregar
        comprometido = DetalleRequisicion.objects.filter(
            **filtros
        ).aggregate(
            total=Sum('cantidad_autorizada')
        )['total'] or 0
        
        surtido = DetalleRequisicion.objects.filter(
            **filtros
        ).aggregate(
            total=Sum('cantidad_surtida')
        )['total'] or 0
        
        return max(0, comprometido - surtido)
    
    def get_stock_disponible_real(self, centro=None):
        """
        ISS-008: Calcula stock realmente disponible (actual - comprometido).
        
        Este es el stock que realmente puede ser usado para nuevas requisiciones.
        
        Args:
            centro: Centro para filtrar stock físico (None = farmacia central)
            
        Returns:
            int: Stock disponible para nuevas requisiciones
        """
        stock_actual = self.get_stock_actual(centro=centro)
        stock_comprometido = self.get_stock_comprometido()
        return max(0, stock_actual - stock_comprometido)
    
    def get_resumen_stock(self, centro=None):
        """
        ISS-008: Retorna resumen completo del estado del stock.
        
        Args:
            centro: Centro para filtrar (None = farmacia central)
            
        Returns:
            dict: Resumen con stock_actual, stock_comprometido, stock_disponible
        """
        stock_actual = self.get_stock_actual(centro=centro)
        stock_comprometido = self.get_stock_comprometido()
        stock_disponible = max(0, stock_actual - stock_comprometido)
        
        return {
            'stock_actual': stock_actual,
            'stock_comprometido': stock_comprometido,
            'stock_disponible': stock_disponible,
            'nivel_stock': self.get_nivel_stock(centro=centro),
            'tiene_comprometido': stock_comprometido > 0,
        }


class Lote(models.Model):
    """
    Modelo de Lote de Producto
    Controla inventario con número de lote, caducidad y cantidades
    
    IMPORTANTE: El campo único es 'numero_lote' (NO codigo_lote)
    """
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='lotes',
        help_text="Producto al que pertenece el lote"
    )
    centro = models.ForeignKey(
        'Centro',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lotes_centro',
        help_text="Centro asociado para inventario por sede"
    )
    numero_lote = models.CharField(
        max_length=LOTE_NUMERO_MAX_LENGTH,
        blank=False,
        null=False,
        validators=[
            RegexValidator(
                regex=r'^[A-Za-z0-9\-]+$',
                message='El número de lote solo puede contener letras, números y guiones'
            )
        ],
        help_text=f"Número de lote único por producto ({LOTE_NUMERO_MIN_LENGTH}-{LOTE_NUMERO_MAX_LENGTH} caracteres)"
    )
    fecha_caducidad = models.DateField(help_text="Fecha de caducidad del lote")
    cantidad_inicial = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Cantidad inicial del lote"
    )
    cantidad_actual = models.IntegerField(
        validators=[MinValueValidator(0)],
        help_text="Cantidad actual disponible"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS_LOTE,
        default='disponible',
        help_text="Estado actual del lote"
    )
    precio_compra = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Precio de compra del lote"
    )
    proveedor = models.CharField(max_length=200, blank=True)
    factura = models.CharField(max_length=100, blank=True)
    
    # CAMPOS DE TRAZABILIDAD DE CONTRATOS
    numero_contrato = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="Número de contrato de adquisición para trazabilidad"
    )
    marca = models.CharField(
        max_length=150,
        blank=True,
        help_text="Marca del medicamento/producto"
    )
    
    fecha_entrada = models.DateField(auto_now_add=True)
    observaciones = models.TextField(blank=True)
    codigo_barras = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        help_text="Código de barras del lote (RFC-45)"
    )
    
    # ISS-005: Documento PDF adjunto con validación de tipo/tamaño
    documento_pdf = models.FileField(
        upload_to=pdf_upload_path,
        validators=[validate_pdf_file],
        null=True,
        blank=True,
        help_text="Documento PDF de soporte (contrato, certificado, etc.) - Máximo 10MB"
    )
    documento_nombre = models.CharField(
        max_length=255,
        blank=True,
        help_text="Nombre original del documento"
    )
    
    # Soft delete
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    # VINCULACIÓN OBLIGATORIA: Lote origen en farmacia central
    # Todo lote en un centro DEBE estar vinculado a su lote origen en farmacia
    # Esto garantiza trazabilidad completa: farmacia → transferencia → centro
    lote_origen = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='lotes_derivados',
        help_text="Lote origen en farmacia central (NULL solo para lotes de farmacia)"
    )
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lotes_creados'
    )
    # ISS-007: Campo de auditoría para rastrear quién modifica lotes
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lotes_modificados',
        help_text="Usuario que realizó la última modificación"
    )

    class Meta:
        db_table = 'lotes'
        ordering = ['-fecha_entrada', 'fecha_caducidad']
        constraints = [
            # Constraint modificado: mismo lote puede existir en farmacia Y en centros
            # pero solo UNA vez por centro (o farmacia central)
            models.UniqueConstraint(
                fields=['producto', 'numero_lote', 'centro'],
                name='unique_lote_por_producto_centro'
            ),
            # ISS-019: Constraints de integridad
            models.CheckConstraint(
                check=models.Q(cantidad_actual__gte=0),
                name='ck_lote_cantidad_no_negativa',
                violation_error_message='La cantidad actual no puede ser negativa'
            ),
            models.CheckConstraint(
                check=models.Q(cantidad_inicial__gte=1),
                name='ck_lote_cantidad_inicial_positiva',
                violation_error_message='La cantidad inicial debe ser al menos 1'
            ),
            models.CheckConstraint(
                check=models.Q(cantidad_actual__lte=models.F('cantidad_inicial')),
                name='ck_lote_actual_no_excede_inicial',
                violation_error_message='La cantidad actual no puede exceder la cantidad inicial'
            ),
        ]
        indexes = [
            models.Index(fields=['estado']),
            models.Index(fields=['fecha_caducidad']),
            models.Index(fields=['producto', 'estado']),
            models.Index(fields=['deleted_at']),
            models.Index(fields=['centro']),
            models.Index(fields=['lote_origen']),
            # Índices compuestos para queries de stock y caducidades
            models.Index(fields=['producto', 'estado', 'fecha_caducidad'], name='idx_lote_stock_lookup'),
            models.Index(fields=['estado', 'fecha_caducidad', 'cantidad_actual'], name='idx_lote_disponible'),
            # Índice para trazabilidad de contratos
            models.Index(fields=['numero_contrato'], name='idx_lote_contrato'),
        ]

    def clean(self):
        """Validaciones personalizadas"""
        # Normalizar número de lote
        if self.numero_lote:
            self.numero_lote = self.numero_lote.upper().strip()
        
        # Validar número de lote
        if self.numero_lote and len(self.numero_lote) < LOTE_NUMERO_MIN_LENGTH:
            raise ValidationError({
                'numero_lote': f'El número de lote debe tener al menos {LOTE_NUMERO_MIN_LENGTH} caracteres'
            })

        if self.producto_id and self.numero_lote:
            qs = self.__class__.objects.filter(
                producto_id=self.producto_id,
                numero_lote=self.numero_lote,
                centro_id=self.centro_id,
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError({
                    'numero_lote': 'Ya existe un lote con este numero para este producto y centro'
                })
        
        # REGLA DE ORO: Vinculación obligatoria centro → farmacia
        # Lotes en farmacia (centro=NULL): NO deben tener lote_origen
        # Lotes en centros: DEBEN tener lote_origen apuntando a farmacia
        if self.centro is None:
            # Lote de farmacia central: no debe tener lote_origen
            if self.lote_origen is not None:
                raise ValidationError({
                    'lote_origen': 'Los lotes de farmacia central no deben tener lote origen'
                })
        else:
            # ISS-002: Lote de centro DEBE tener lote_origen para trazabilidad
            if self.lote_origen is None:
                raise ValidationError({
                    'lote_origen': 'Los lotes en centros deben tener un lote origen de farmacia central para garantizar trazabilidad'
                })
            # Validar que lote_origen sea del mismo producto
            if self.lote_origen.producto_id != self.producto_id:
                raise ValidationError({
                    'lote_origen': 'El lote origen debe ser del mismo producto'
                })
            # Validar que la fecha de caducidad coincida
            if self.lote_origen.fecha_caducidad != self.fecha_caducidad:
                raise ValidationError({
                    'fecha_caducidad': 'La fecha de caducidad debe coincidir con la del lote origen'
                })
        
        # Validar que lote_origen sea de farmacia central si está definido
        if self.lote_origen is not None:
            if self.lote_origen.centro is not None:
                raise ValidationError({
                    'lote_origen': 'El lote origen debe ser de farmacia central (centro=NULL)'
                })
            # Validar que coincidan producto, numero_lote y caducidad
            if self.producto_id != self.lote_origen.producto_id:
                raise ValidationError({
                    'producto': 'El producto debe coincidir con el lote origen'
                })
            if self.numero_lote != self.lote_origen.numero_lote:
                raise ValidationError({
                    'numero_lote': 'El número de lote debe coincidir con el lote origen'
                })
            if self.fecha_caducidad != self.lote_origen.fecha_caducidad:
                raise ValidationError({
                    'fecha_caducidad': 'La fecha de caducidad debe coincidir con el lote origen'
                })
        
        # Validar que cantidad actual no exceda inicial
        if self.cantidad_actual > self.cantidad_inicial:
            raise ValidationError({
                'cantidad_actual': 'La cantidad actual no puede ser mayor a la cantidad inicial'
            })
        
        # ISS-002 FIX: Validar fecha de caducidad con timezone-aware date
        from django.utils import timezone
        today = timezone.now().date()
        if self.fecha_caducidad and self.fecha_caducidad < today:
            self.estado = 'vencido'
            logger.warning(f"Lote {self.numero_lote} marcado como vencido automáticamente")
        
        # Marcar como agotado si cantidad es 0
        if self.cantidad_actual == 0 and self.estado == 'disponible':
            self.estado = 'agotado'
        
        # Validar precio_compra
        if self.precio_compra and self.precio_compra < 0:
            raise ValidationError({
                'precio_compra': 'El precio de compra no puede ser negativo'
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Lote {self.numero_lote} - {self.producto.clave}"
    
    def generar_codigo_barras(self):
        """
        Genera código de barras basado en producto_clave + lote_numero
        Formato: PRODUCTO:LOTE
        Ejemplo: MED001:LOT123
        
        Returns:
            str: Código de barras generado
        """
        if not self.codigo_barras:
            barcode = f"{self.producto.clave}:{self.numero_lote}"
            self.codigo_barras = barcode
            self.save(update_fields=['codigo_barras'])
        return self.codigo_barras
    
    def dias_para_caducar(self):
        """Calcula días restantes para caducidad usando timezone-aware date (ISS-002)"""
        from django.utils import timezone
        today = timezone.now().date()
        delta = self.fecha_caducidad - today
        return delta.days
    
    def esta_caducado(self):
        """Verifica si el lote está vencido usando timezone-aware date (ISS-002)"""
        from django.utils import timezone
        today = timezone.now().date()
        return self.fecha_caducidad < today
    
    def alerta_caducidad(self):
        """
        Retorna nivel de alerta por caducidad según especificación SIFP:
        - 🟢 'normal': > 6 meses (más de 180 días)
        - 🟡 'proximo': Entre 3 y 6 meses (90-180 días)
        - 🔴 'critico': < 3 meses (menos de 90 días)
        - 🔴 'vencido': Caducado (días < 0)
        
        Returns: 'vencido' | 'critico' | 'proximo' | 'normal'
        """
        dias = self.dias_para_caducar()
        
        if dias < 0:
            return 'vencido'
        elif dias < 90:  # Menos de 3 meses - crítico (rojo)
            return 'critico'
        elif dias < 180:  # Menos de 6 meses - próximo a vencer (amarillo)
            return 'proximo'
        else:  # Más de 6 meses - normal (verde)
            return 'normal'
    
    def soft_delete(self):
        """Marca lote como eliminado sin borrar de BD"""
        from django.utils import timezone
        if not self.deleted_at:
            self.deleted_at = timezone.now()
            # Cambiar estado a 'retirado' para indicar que ya no está disponible
            if self.estado in ['disponible', 'reservado']:
                self.estado = 'retirado'
            self.save(update_fields=['deleted_at', 'estado', 'updated_at'])
            logger.info(f"Lote {self.numero_lote} marcado como eliminado (soft delete)")
    
    @classmethod
    def active_only(cls):
        """Retorna solo lotes activos (no eliminados)"""
        return cls.objects.filter(deleted_at__isnull=True).exclude(estado='retirado')
    
    @classmethod
    def proximos_a_caducar(cls, dias=30):
        """
        Retorna lotes que caducarán en los próximos N días
        Por defecto 30 días
        """
        from django.utils import timezone
        hoy = timezone.now().date()
        fecha_limite = hoy + timedelta(days=dias)
        
        return cls.objects.filter(
            deleted_at__isnull=True,
            estado='disponible',
            fecha_caducidad__gte=hoy,
            fecha_caducidad__lte=fecha_limite,
            cantidad_actual__gt=0
        ).select_related('producto').order_by('fecha_caducidad')
    
    # ==========================================
    # ISS-010: Métodos de Control de Contratos
    # ==========================================
    
    def tiene_contrato(self):
        """
        ISS-010: Verifica si el lote tiene número de contrato asignado.
        
        Returns:
            bool: True si tiene contrato, False si no
        """
        return bool(self.numero_contrato and self.numero_contrato.strip())
    
    def get_info_contrato(self):
        """
        ISS-010: Retorna información completa del contrato del lote.
        
        Returns:
            dict: Información del contrato con:
                - tiene_contrato: bool
                - numero_contrato: str o None
                - proveedor: str
                - factura: str
                - marca: str
                - precio_compra: Decimal o None
        """
        return {
            'tiene_contrato': self.tiene_contrato(),
            'numero_contrato': self.numero_contrato if self.tiene_contrato() else None,
            'proveedor': self.proveedor or '',
            'factura': self.factura or '',
            'marca': self.marca or '',
            'precio_compra': self.precio_compra,
        }
    
    @classmethod
    def por_contrato(cls, numero_contrato, solo_disponibles=True):
        """
        ISS-010: Obtiene todos los lotes asociados a un número de contrato.
        
        Args:
            numero_contrato: Número de contrato a buscar
            solo_disponibles: Si True, excluye lotes eliminados/vencidos
            
        Returns:
            QuerySet: Lotes del contrato especificado
        """
        filtros = {
            'numero_contrato': numero_contrato,
        }
        
        if solo_disponibles:
            filtros['deleted_at__isnull'] = True
        
        return cls.objects.filter(**filtros).select_related('producto', 'centro')
    
    @classmethod
    def resumen_por_contrato(cls, numero_contrato):
        """
        ISS-010: Genera resumen estadístico de un contrato específico.
        
        Args:
            numero_contrato: Número de contrato a analizar
            
        Returns:
            dict: Resumen con:
                - total_lotes: int
                - total_cantidad_inicial: int
                - total_cantidad_actual: int
                - porcentaje_consumido: float
                - productos: list de productos únicos
                - estados: dict con conteo por estado
                - valor_total: Decimal (si hay precios)
        """
        from django.db.models import Sum, Count
        
        lotes = cls.por_contrato(numero_contrato, solo_disponibles=False)
        
        if not lotes.exists():
            return {
                'numero_contrato': numero_contrato,
                'total_lotes': 0,
                'total_cantidad_inicial': 0,
                'total_cantidad_actual': 0,
                'porcentaje_consumido': 0,
                'productos': [],
                'estados': {},
                'valor_total': Decimal('0.00'),
            }
        
        agregados = lotes.aggregate(
            total_lotes=Count('id'),
            total_inicial=Sum('cantidad_inicial'),
            total_actual=Sum('cantidad_actual'),
        )
        
        # Conteo por estado
        estados = {}
        for lote in lotes.values('estado').annotate(count=Count('id')):
            estados[lote['estado']] = lote['count']
        
        # Productos únicos
        productos = list(lotes.values_list('producto__clave', flat=True).distinct())
        
        # Valor total (si hay precios)
        valor_total = lotes.filter(precio_compra__isnull=False).aggregate(
            total=Sum(models.F('cantidad_inicial') * models.F('precio_compra'))
        )['total'] or Decimal('0.00')
        
        total_inicial = agregados['total_inicial'] or 0
        total_actual = agregados['total_actual'] or 0
        consumido = total_inicial - total_actual
        porcentaje = (consumido / total_inicial * 100) if total_inicial > 0 else 0
        
        return {
            'numero_contrato': numero_contrato,
            'total_lotes': agregados['total_lotes'],
            'total_cantidad_inicial': total_inicial,
            'total_cantidad_actual': total_actual,
            'cantidad_consumida': consumido,
            'porcentaje_consumido': round(porcentaje, 2),
            'productos': productos,
            'estados': estados,
            'valor_total': valor_total,
        }
    
    @classmethod
    def contratos_activos(cls):
        """
        ISS-010: Lista todos los números de contrato con lotes activos.
        
        Returns:
            list: Lista de números de contrato únicos con lotes disponibles
        """
        return list(
            cls.objects.filter(
                deleted_at__isnull=True,
                numero_contrato__isnull=False,
            ).exclude(
                numero_contrato=''
            ).values_list('numero_contrato', flat=True).distinct().order_by('numero_contrato')
        )


class Requisicion(models.Model):
    """
    Modelo de Requisición de medicamentos
    Flujo: Borrador -> Enviada -> Autorizada/Rechazada -> Surtida -> Recibida
    
    ISS-002: Máquina de Estados UNIFICADA (modelo y servicio usan la misma)
    
    Estados:
    - borrador: Estado inicial, puede ser editada
    - enviada: Enviada para revisión, pendiente de autorización
    - autorizada: Aprobada, lista para surtir
    - parcial: Parcialmente autorizada/surtida
    - rechazada: Rechazada, no se surtirá (permite reenvío a borrador)
    - surtida: Surtida por farmacia, pendiente de recepción
    - recibida: Recibida por el centro destino
    - cancelada: Cancelada por el usuario
    """
    # ISS-002: Definición CANÓNICA de transiciones válidas de estado
    # Esta es la fuente única de verdad para todo el sistema
    TRANSICIONES_VALIDAS = {
        'borrador': ['enviada', 'cancelada'],
        'enviada': ['autorizada', 'parcial', 'rechazada', 'cancelada'],
        'autorizada': ['surtida', 'parcial', 'cancelada'],
        'parcial': ['surtida', 'cancelada'],
        'rechazada': ['borrador'],  # ISS-002: Permite reenvío después de correcciones
        'surtida': ['recibida'],
        'recibida': [],   # Estado terminal
        'cancelada': [],  # Estado terminal
    }
    
    # Estados que permiten surtido
    ESTADOS_SURTIBLES = ['autorizada', 'parcial']
    
    # Estados terminales (no permiten más transiciones)
    ESTADOS_TERMINALES = ['recibida', 'cancelada']
    
    folio = models.CharField(max_length=50, unique=True)
    centro = models.ForeignKey(
        Centro,
        on_delete=models.PROTECT,
        related_name='requisiciones'
    )
    usuario_solicita = models.ForeignKey(settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='requisiciones_solicitadas'
    )
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS_REQUISICION,
        default='borrador'
    )
    observaciones = models.TextField(blank=True)
    usuario_autoriza = models.ForeignKey(settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requisiciones_autorizadas'
    )
    fecha_autorizacion = models.DateTimeField(null=True, blank=True)
    motivo_rechazo = models.TextField(blank=True)
    
    # Lugar de entrega (detalle de dónde se entrega: centro, servicio, área)
    lugar_entrega = models.CharField(
        max_length=300,
        blank=True,
        help_text="Detalle del lugar de entrega (centro, servicio, área, etc.)"
    )
    
    # Campos para marcar como recibida por el centro
    fecha_recibido = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha y hora en que el centro recibió la requisición"
    )
    usuario_recibe = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requisiciones_recibidas',
        help_text="Usuario del centro que recibió la requisición"
    )
    observaciones_recepcion = models.TextField(
        blank=True,
        help_text="Observaciones al momento de recibir la requisición"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # ISS-007: Campo de auditoría para rastrear modificaciones
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requisiciones_modificadas',
        help_text="Usuario que realizó la última modificación"
    )

    class Meta:
        db_table = 'requisiciones'
        ordering = ['-fecha_solicitud']
        indexes = [
            models.Index(fields=['estado']),
            models.Index(fields=['centro', 'estado']),
            models.Index(fields=['-fecha_solicitud']),
        ]

    def __str__(self):
        return f"{self.folio} - {self.centro.nombre}"
    
    def puede_transicionar_a(self, nuevo_estado):
        """
        Verifica si la transición de estado es válida.
        
        Args:
            nuevo_estado: El estado al que se quiere transicionar
            
        Returns:
            bool: True si la transición es válida, False en caso contrario
        """
        estado_actual = (self.estado or 'borrador').lower()
        nuevo_estado = (nuevo_estado or '').lower()
        
        transiciones_permitidas = self.TRANSICIONES_VALIDAS.get(estado_actual, [])
        return nuevo_estado in transiciones_permitidas
    
    def cambiar_estado(self, nuevo_estado, usuario=None, motivo=None):
        """
        Cambia el estado de la requisición validando la transición.
        
        Args:
            nuevo_estado: El nuevo estado
            usuario: Usuario que realiza el cambio (opcional)
            motivo: Motivo del cambio (requerido para rechazos)
            
        Returns:
            bool: True si el cambio fue exitoso
            
        Raises:
            ValidationError: Si la transición no es válida
        """
        from django.utils import timezone
        
        nuevo_estado = (nuevo_estado or '').lower()
        
        if not self.puede_transicionar_a(nuevo_estado):
            estado_actual = self.estado or 'borrador'
            transiciones_permitidas = self.TRANSICIONES_VALIDAS.get(estado_actual.lower(), [])
            raise ValidationError({
                'estado': f"Transición de '{estado_actual}' a '{nuevo_estado}' no permitida. "
                         f"Transiciones válidas: {', '.join(transiciones_permitidas) or 'ninguna'}"
            })
        
        # Validaciones específicas por tipo de transición
        if nuevo_estado == 'rechazada' and not motivo:
            raise ValidationError({
                'motivo_rechazo': 'Se requiere un motivo para rechazar la requisición'
            })
        
        if nuevo_estado == 'enviada' and not self.detalles.exists():
            raise ValidationError({
                'detalles': 'La requisición debe tener al menos un producto para ser enviada'
            })
        
        # Aplicar el cambio
        self.estado = nuevo_estado
        
        if nuevo_estado == 'rechazada' and motivo:
            self.motivo_rechazo = motivo
            self.observaciones = motivo
        
        if nuevo_estado in ['autorizada', 'parcial']:
            self.fecha_autorizacion = timezone.now()
            if usuario:
                self.usuario_autoriza = usuario
        
        logger.info(f"Requisición {self.folio}: estado cambiado a '{nuevo_estado}' por {usuario or 'sistema'}")
        return True
    
    def get_transiciones_disponibles(self):
        """
        Retorna las transiciones disponibles desde el estado actual.
        
        Returns:
            list: Lista de estados a los que se puede transicionar
        """
        estado_actual = (self.estado or 'borrador').lower()
        return self.TRANSICIONES_VALIDAS.get(estado_actual, [])
    
    def es_estado_terminal(self):
        """
        Verifica si el estado actual es terminal (no permite más transiciones).
        
        Returns:
            bool: True si es estado terminal
        """
        return len(self.get_transiciones_disponibles()) == 0
    
    def save(self, *args, **kwargs):
        """Auto-generar folio si no existe (ISS-010: con protección contra race conditions)"""
        if not self.folio:
            # Generar folio: REQ-CENTRO-YYYYMMDD-NNNN
            from django.utils import timezone
            from django.db import transaction
            
            today = timezone.now()
            fecha = today.strftime('%Y%m%d')
            centro_codigo = self.centro.clave[:3] if self.centro else 'GEN'
            prefijo = f'REQ-{centro_codigo}-{fecha}'
            
            # ISS-010: Usar transacción y select_for_update para evitar race conditions
            with transaction.atomic():
                # Bloquear filas existentes para este prefijo mientras calculamos
                ultima = Requisicion.objects.select_for_update().filter(
                    folio__startswith=prefijo
                ).order_by('-folio').first()
                
                if ultima:
                    # Extraer número y sumar 1
                    try:
                        ultimo_num = int(ultima.folio.split('-')[-1])
                        nuevo_num = ultimo_num + 1
                    except (ValueError, IndexError):
                        nuevo_num = 1
                else:
                    nuevo_num = 1
                
                self.folio = f'{prefijo}-{nuevo_num:04d}'
                logger.info(f"Folio generado automáticamente: {self.folio}")
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)


class DetalleRequisicion(models.Model):
    """
    Detalle de productos en una requisición.
    Cada detalle está asociado a un producto y opcionalmente a un lote específico
    para trazabilidad completa.
    """
    requisicion = models.ForeignKey(
        Requisicion,
        on_delete=models.PROTECT,
        related_name='detalles'
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT
    )
    lote = models.ForeignKey(
        'Lote',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='detalles_requisicion',
        help_text='Lote específico del que se solicita el producto'
    )
    cantidad_solicitada = models.IntegerField(
        validators=[MinValueValidator(1)]
    )
    cantidad_autorizada = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )
    cantidad_surtida = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = 'detalles_requisicion'
        unique_together = ['requisicion', 'producto', 'lote']
        indexes = [
            models.Index(fields=['requisicion', 'producto']),
            models.Index(fields=['lote']),
        ]
        # ISS-019: Constraints de integridad
        constraints = [
            models.CheckConstraint(
                check=models.Q(cantidad_solicitada__gte=1),
                name='ck_detalle_cantidad_solicitada_positiva',
                violation_error_message='La cantidad solicitada debe ser al menos 1'
            ),
        ]


class Movimiento(models.Model):
    """
    Modelo de trazabilidad de movimientos de inventario
    Registra toda entrada, salida y ajuste de productos
    """
    tipo = models.CharField(
        max_length=20,
        choices=TIPOS_MOVIMIENTO
    )
    lote = models.ForeignKey(
        Lote,
        on_delete=models.PROTECT,
        related_name='movimientos'
    )
    centro = models.ForeignKey(
        Centro,
        on_delete=models.PROTECT,
        related_name='movimientos',
        null=True,
        blank=True
    )
    cantidad = models.IntegerField()
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Usuario que registró el movimiento (opcional para movimientos automáticos)"
    )
    requisicion = models.ForeignKey(
        Requisicion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos'
    )
    documento_referencia = models.CharField(
        max_length=100,
        blank=True,
        help_text="Referencia del documento (factura, remito, etc.)"
    )
    lugar_entrega = models.CharField(
        max_length=300,
        blank=True,
        help_text="Detalle del lugar de entrega (centro, servicio, área, etc.)"
    )
    observaciones = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'movimientos'
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['tipo']),
            models.Index(fields=['lote', 'tipo']),
            models.Index(fields=['-fecha']),
            models.Index(fields=['centro', '-fecha']),
        ]

    def clean(self):
        """Validaciones de movimientos"""
        # Validar cantidad positiva para entradas
        if self.tipo == 'entrada' and self.cantidad <= 0:
            raise ValidationError({
                'cantidad': 'La cantidad de entrada debe ser positiva'
            })
        
        # Validar disponibilidad para salidas
        if self.tipo == 'salida':
            if self.cantidad >= 0:
                raise ValidationError({
                    'cantidad': 'La cantidad de salida debe ser negativa'
                })
            
            # Verificar stock disponible
            stock_disponible = getattr(self, '_stock_pre_movimiento', self.lote.cantidad_actual)
            if abs(self.cantidad) > stock_disponible:
                raise ValidationError({
                    'cantidad': f'Stock insuficiente. Disponible: {stock_disponible}'
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        
        # NOTA: La actualización del stock del lote se realiza en registrar_movimiento_stock
        # para evitar doble contabilización y garantizar atomicidad
        logger.info(
            f"Movimiento {self.tipo} registrado: "
            f"Lote {self.lote.numero_lote}, Cantidad: {self.cantidad}"
        )


class ImportacionLog(models.Model):
    """
    Modelo para registrar importaciones masivas en el sistema.
    """
    ESTADOS = [
        ('exitosa', 'Exitosa'),
        ('parcial', 'Parcialmente exitosa'),
        ('fallida', 'Fallida'),
    ]
    
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    archivo_nombre = models.CharField(max_length=255)
    modelo = models.CharField(max_length=50)
    fecha_importacion = models.DateTimeField(auto_now_add=True)
    total_registros = models.IntegerField(default=0)
    registros_exitosos = models.IntegerField(default=0)
    registros_fallidos = models.IntegerField(default=0)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='exitosa')
    resultado_procesamiento = models.JSONField(default=dict)
    
    class Meta:
        db_table = 'importacion_logs'
        ordering = ['-fecha_importacion']
    
    def __str__(self):
        return f"Importación {self.archivo_nombre} - {self.fecha_importacion}"


class UserProfile(models.Model):
    """
    Perfil extendido de usuario. El centro se toma directamente de User.centro.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='profile'
    )
    telefono = models.CharField(max_length=15, blank=True)
    cargo = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profiles'
    
    def __str__(self):
        return f"Perfil de {self.user.username}"


class Notificacion(models.Model):
    """Modelo para notificaciones del sistema."""
    TIPOS = [
        ('info', 'Información'),
        ('success', 'Éxito'),
        ('warning', 'Advertencia'),
        ('error', 'Error'),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='notificaciones'
    )
    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    tipo = models.CharField(max_length=20, choices=TIPOS, default='info')
    requisicion = models.ForeignKey(
        Requisicion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='notificaciones'
    )
    leida = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notificaciones'
        ordering = ['-fecha_creacion']
        # ISS-010: Índices para consultas frecuentes
        indexes = [
            models.Index(fields=['usuario', 'leida', '-fecha_creacion'], name='idx_notif_user_read'),
            models.Index(fields=['usuario', '-fecha_creacion'], name='idx_notif_user_date'),
        ]

    def __str__(self):
        return f"{self.titulo} - {self.usuario.username}"

class AuditoriaLog(models.Model):
    """
    Modelo de auditoría para rastrear todas las acciones del sistema
    """
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='acciones_auditoria'
    )
    accion = models.CharField(
        max_length=100,
        help_text="Tipo de acción: crear, editar, eliminar, autorizar, etc."
    )
    modelo = models.CharField(
        max_length=50,
        help_text="Modelo afectado: Producto, Requisicion, Lote, etc."
    )
    objeto_id = models.IntegerField(null=True, blank=True, help_text="ID del objeto afectado")
    objeto_repr = models.CharField(max_length=255, blank=True, default='', help_text="Representación del objeto")
    cambios = models.JSONField(
        default=dict,
        help_text="Detalles de los cambios realizados"
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'auditoria_logs'
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['usuario', '-fecha']),
            models.Index(fields=['modelo', 'objeto_id']),
            models.Index(fields=['-fecha']),
        ]
    
    def __str__(self):
        return f"{self.usuario} - {self.accion} - {self.modelo} #{self.objeto_id} - {self.fecha.strftime('%Y-%m-%d %H:%M')}"


class ConfiguracionSistema(models.Model):
    """
    Modelo Singleton para configuración global del sistema.
    Solo debe existir un registro (id=1).
    Permite personalizar colores del tema de la interfaz.
    """
    # Nombre del sistema
    nombre_sistema = models.CharField(
        max_length=100,
        default='Sistema de Farmacia Penitenciaria',
        help_text="Nombre que aparece en el header del sistema"
    )
    
    # Logo URL (opcional - para URLs externas)
    logo_url = models.URLField(
        blank=True,
        null=True,
        help_text="URL del logo del sistema (opcional)"
    )
    
    # Logo archivo para header de la interfaz
    logo_header = models.ImageField(
        upload_to='configuracion/logos/',
        null=True,
        blank=True,
        validators=[validate_logo_size],  # ISS-016: Validar tamaño
        help_text="Logo para el header de la interfaz (PNG/JPG, max 500KB)"
    )
    
    # Logo/fondo para PDFs institucionales
    logo_pdf = models.ImageField(
        upload_to='configuracion/logos/',
        null=True,
        blank=True,
        validators=[validate_logo_size],  # ISS-016: Validar tamaño
        help_text="Logo o fondo institucional para PDFs (PNG, recomendado 800x1200px)"
    )
    
    # Institución para reportes
    nombre_institucion = models.CharField(
        max_length=200,
        default='Secretaría de Seguridad',
        help_text="Nombre de la institución para reportes"
    )
    
    subtitulo_institucion = models.CharField(
        max_length=200,
        default='Dirección General de Prevención y Reinserción Social',
        help_text="Subtítulo de la institución para reportes"
    )
    
    # === Colores del Tema ===
    # Colores principales
    color_primario = models.CharField(
        max_length=7,
        default='#9F2241',
        validators=[
            RegexValidator(
                regex=r'^#[0-9A-Fa-f]{6}$',
                message='El color debe estar en formato hexadecimal (#RRGGBB)'
            )
        ],
        help_text="Color primario del tema (botones principales, header)"
    )
    color_primario_hover = models.CharField(
        max_length=7,
        default='#6B1839',
        validators=[
            RegexValidator(
                regex=r'^#[0-9A-Fa-f]{6}$',
                message='El color debe estar en formato hexadecimal (#RRGGBB)'
            )
        ],
        help_text="Color primario al pasar el mouse"
    )
    
    color_secundario = models.CharField(
        max_length=7,
        default='#424242',
        validators=[
            RegexValidator(
                regex=r'^#[0-9A-Fa-f]{6}$',
                message='El color debe estar en formato hexadecimal (#RRGGBB)'
            )
        ],
        help_text="Color secundario del tema"
    )
    
    color_acento = models.CharField(
        max_length=7,
        default='#BC955C',
        validators=[
            RegexValidator(
                regex=r'^#[0-9A-Fa-f]{6}$',
                message='El color debe estar en formato hexadecimal (#RRGGBB)'
            )
        ],
        help_text="Color de acento para destacar elementos"
    )
    
    # Colores de fondo
    color_fondo = models.CharField(
        max_length=7,
        default='#F5F5F5',
        validators=[
            RegexValidator(
                regex=r'^#[0-9A-Fa-f]{6}$',
                message='El color debe estar en formato hexadecimal (#RRGGBB)'
            )
        ],
        help_text="Color de fondo general"
    )
    
    color_fondo_sidebar = models.CharField(
        max_length=7,
        default='#9F2241',
        validators=[
            RegexValidator(
                regex=r'^#[0-9A-Fa-f]{6}$',
                message='El color debe estar en formato hexadecimal (#RRGGBB)'
            )
        ],
        help_text="Color de fondo del menú lateral"
    )
    
    color_fondo_header = models.CharField(
        max_length=7,
        default='#9F2241',
        validators=[
            RegexValidator(
                regex=r'^#[0-9A-Fa-f]{6}$',
                message='El color debe estar en formato hexadecimal (#RRGGBB)'
            )
        ],
        help_text="Color de fondo del header"
    )
    
    color_fondo_card = models.CharField(
        max_length=7,
        default='#FFFFFF',
        validators=[
            RegexValidator(
                regex=r'^#[0-9A-Fa-f]{6}$',
                message='El color debe estar en formato hexadecimal (#RRGGBB)'
            )
        ],
        help_text="Color de fondo de tarjetas"
    )
    
    # Colores de texto
    color_texto = models.CharField(
        max_length=7,
        default='#212121',
        validators=[
            RegexValidator(
                regex=r'^#[0-9A-Fa-f]{6}$',
                message='El color debe estar en formato hexadecimal (#RRGGBB)'
            )
        ],
        help_text="Color de texto principal"
    )
    
    color_texto_secundario = models.CharField(
        max_length=7,
        default='#757575',
        validators=[
            RegexValidator(
                regex=r'^#[0-9A-Fa-f]{6}$',
                message='El color debe estar en formato hexadecimal (#RRGGBB)'
            )
        ],
        help_text="Color de texto secundario"
    )
    
    color_texto_sidebar = models.CharField(
        max_length=7,
        default='#FFFFFF',
        validators=[
            RegexValidator(
                regex=r'^#[0-9A-Fa-f]{6}$',
                message='El color debe estar en formato hexadecimal (#RRGGBB)'
            )
        ],
        help_text="Color de texto en el sidebar"
    )
    
    color_texto_header = models.CharField(
        max_length=7,
        default='#FFFFFF',
        validators=[
            RegexValidator(
                regex=r'^#[0-9A-Fa-f]{6}$',
                message='El color debe estar en formato hexadecimal (#RRGGBB)'
            )
        ],
        help_text="Color de texto en el header"
    )
    
    # Colores de estados
    color_exito = models.CharField(
        max_length=7,
        default='#4CAF50',
        validators=[
            RegexValidator(
                regex=r'^#[0-9A-Fa-f]{6}$',
                message='El color debe estar en formato hexadecimal (#RRGGBB)'
            )
        ],
        help_text="Color para estados de éxito"
    )
    
    color_advertencia = models.CharField(
        max_length=7,
        default='#FF9800',
        validators=[
            RegexValidator(
                regex=r'^#[0-9A-Fa-f]{6}$',
                message='El color debe estar en formato hexadecimal (#RRGGBB)'
            )
        ],
        help_text="Color para advertencias"
    )
    
    color_error = models.CharField(
        max_length=7,
        default='#F44336',
        validators=[
            RegexValidator(
                regex=r'^#[0-9A-Fa-f]{6}$',
                message='El color debe estar en formato hexadecimal (#RRGGBB)'
            )
        ],
        help_text="Color para errores"
    )
    
    color_info = models.CharField(
        max_length=7,
        default='#2196F3',
        validators=[
            RegexValidator(
                regex=r'^#[0-9A-Fa-f]{6}$',
                message='El color debe estar en formato hexadecimal (#RRGGBB)'
            )
        ],
        help_text="Color para información"
    )
    
    # Temas predefinidos (para facilitar la selección)
    TEMAS_PREDEFINIDOS = [
        ('default', 'Por Defecto (Institucional)'),
        ('dark', 'Oscuro'),
        ('green', 'Verde Institucional'),
        ('purple', 'Púrpura'),
        ('custom', 'Personalizado'),
    ]
    tema_activo = models.CharField(
        max_length=20,
        choices=TEMAS_PREDEFINIDOS,
        default='default',
        help_text="Tema predefinido o personalizado"
    )
    
    # Auditoría
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='configuraciones_actualizadas'
    )
    
    class Meta:
        db_table = 'configuracion_sistema'
        verbose_name = 'Configuración del Sistema'
        verbose_name_plural = 'Configuración del Sistema'
    
    def __str__(self):
        return f"Configuración del Sistema (Tema: {self.get_tema_activo_display()})"
    
    def save(self, *args, **kwargs):
        # Forzar que siempre sea el registro con id=1 (Singleton)
        self.pk = 1
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        # No permitir eliminar la configuración
        pass
    
    @classmethod
    def get_config(cls):
        """
        Obtiene la configuración del sistema (crea una por defecto si no existe).
        Siempre retorna un único objeto.
        """
        config, created = cls.objects.get_or_create(pk=1)
        if created:
            logger.info("Configuración del sistema creada con valores por defecto")
        return config
    
    @classmethod
    def aplicar_tema_predefinido(cls, tema):
        """
        Aplica un tema predefinido cambiando todos los colores.
        """
        config = cls.get_config()
        
        temas = {
            'default': {
                'color_primario': '#9F2241',
                'color_primario_hover': '#6B1839',
                'color_secundario': '#424242',
                'color_acento': '#BC955C',
                'color_fondo': '#F5F5F5',
                'color_fondo_sidebar': '#9F2241',
                'color_fondo_header': '#9F2241',
                'color_fondo_card': '#FFFFFF',
                'color_texto': '#212121',
                'color_texto_secundario': '#757575',
                'color_texto_sidebar': '#FFFFFF',
                'color_texto_header': '#FFFFFF',
                'color_exito': '#4CAF50',
                'color_advertencia': '#FF9800',
                'color_error': '#F44336',
                'color_info': '#2196F3',
            },
            'dark': {
                'color_primario': '#BB86FC',
                'color_primario_hover': '#9A67EA',
                'color_secundario': '#03DAC6',
                'color_acento': '#CF6679',
                'color_fondo': '#121212',
                'color_fondo_sidebar': '#1E1E1E',
                'color_fondo_header': '#1F1F1F',
                'color_fondo_card': '#2D2D2D',
                'color_texto': '#E1E1E1',
                'color_texto_secundario': '#A0A0A0',
                'color_texto_sidebar': '#E1E1E1',
                'color_texto_header': '#FFFFFF',
                'color_exito': '#4CAF50',
                'color_advertencia': '#FF9800',
                'color_error': '#CF6679',
                'color_info': '#64B5F6',
            },
            'green': {
                'color_primario': '#2E7D32',
                'color_primario_hover': '#1B5E20',
                'color_secundario': '#558B2F',
                'color_acento': '#FF6F00',
                'color_fondo': '#F1F8E9',
                'color_fondo_sidebar': '#1B5E20',
                'color_fondo_header': '#2E7D32',
                'color_fondo_card': '#FFFFFF',
                'color_texto': '#212121',
                'color_texto_secundario': '#616161',
                'color_texto_sidebar': '#E8F5E9',
                'color_texto_header': '#FFFFFF',
                'color_exito': '#43A047',
                'color_advertencia': '#FB8C00',
                'color_error': '#E53935',
                'color_info': '#039BE5',
            },
            'purple': {
                'color_primario': '#7B1FA2',
                'color_primario_hover': '#6A1B9A',
                'color_secundario': '#512DA8',
                'color_acento': '#FF4081',
                'color_fondo': '#F3E5F5',
                'color_fondo_sidebar': '#4A148C',
                'color_fondo_header': '#7B1FA2',
                'color_fondo_card': '#FFFFFF',
                'color_texto': '#212121',
                'color_texto_secundario': '#616161',
                'color_texto_sidebar': '#E1BEE7',
                'color_texto_header': '#FFFFFF',
                'color_exito': '#4CAF50',
                'color_advertencia': '#FF9800',
                'color_error': '#F44336',
                'color_info': '#2196F3',
            },
        }
        
        if tema in temas:
            for campo, valor in temas[tema].items():
                setattr(config, campo, valor)
            config.tema_activo = tema
            config.save()
            logger.info(f"Tema '{tema}' aplicado correctamente")
            return True
        return False
    
    def to_css_variables(self):
        """
        Retorna un diccionario con los colores para usar como CSS variables.
        """
        return {
            '--color-primary': self.color_primario,
            '--color-primary-hover': self.color_primario_hover,
            '--color-secondary': self.color_secundario,
            '--color-accent': self.color_acento,
            '--color-background': self.color_fondo,
            '--color-sidebar-bg': self.color_fondo_sidebar,
            '--color-header-bg': self.color_fondo_header,
            '--color-card-bg': self.color_fondo_card,
            '--color-text': self.color_texto,
            '--color-text-secondary': self.color_texto_secundario,
            '--color-sidebar-text': self.color_texto_sidebar,
            '--color-header-text': self.color_texto_header,
            '--color-success': self.color_exito,
            '--color-warning': self.color_advertencia,
            '--color-error': self.color_error,
            '--color-info': self.color_info,
        }


class HojaRecoleccion(models.Model):
    """
    Modelo para almacenar las hojas de recolección generadas.
    
    Flujo de seguridad:
    1. Farmacia revisa y ajusta cantidades en la requisición
    2. Al autorizar, se genera automáticamente la HojaRecoleccion con hash de seguridad
    3. El centro puede ver/imprimir la hoja
    4. Farmacia puede verificar que la hoja impresa coincide con lo autorizado
    
    El hash SHA256 garantiza que el contenido no ha sido alterado.
    """
    ESTADOS_HOJA = [
        ('generada', 'Generada'),
        ('impresa', 'Impresa'),
        ('verificada', 'Verificada'),
        ('completada', 'Completada'),
    ]
    
    requisicion = models.OneToOneField(
        'Requisicion',
        on_delete=models.PROTECT,
        related_name='hoja_recoleccion',
        help_text="Requisición asociada a esta hoja"
    )
    
    # Número de folio único para la hoja
    folio_hoja = models.CharField(
        max_length=50,
        unique=True,
        help_text="Folio único de la hoja de recolección"
    )
    
    # Hash de seguridad del contenido
    hash_contenido = models.CharField(
        max_length=64,
        help_text="Hash SHA256 del contenido para verificar integridad"
    )
    
    # Contenido JSON serializado (para reconstruir PDF idéntico)
    contenido_json = models.JSONField(
        default=dict,
        help_text="Contenido serializado de la hoja para reconstrucción"
    )
    
    # Estado de la hoja
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS_HOJA,
        default='generada'
    )
    
    # Fechas importantes
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    fecha_impresion = models.DateTimeField(null=True, blank=True)
    fecha_verificacion = models.DateTimeField(null=True, blank=True)
    
    # Usuarios involucrados
    generado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hojas_generadas',
        help_text="Usuario de farmacia que generó la hoja"
    )
    verificado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hojas_verificadas',
        help_text="Usuario de farmacia que verificó la hoja"
    )
    
    # Contador de impresiones (para detectar múltiples impresiones)
    veces_impresa = models.PositiveIntegerField(default=0)
    veces_descargada = models.PositiveIntegerField(default=0)
    
    # Observaciones
    observaciones = models.TextField(blank=True)
    
    class Meta:
        db_table = 'hojas_recoleccion'
        ordering = ['-fecha_generacion']
        verbose_name = 'Hoja de Recolección'
        verbose_name_plural = 'Hojas de Recolección'
        indexes = [
            models.Index(fields=['requisicion']),
            models.Index(fields=['folio_hoja']),
            models.Index(fields=['estado']),
            models.Index(fields=['-fecha_generacion']),
        ]
    
    def __str__(self):
        return f"Hoja {self.folio_hoja} - {self.requisicion.folio}"
    
    def save(self, *args, **kwargs):
        """Auto-generar folio si no existe (ISS-010: con protección contra race conditions)"""
        if not self.folio_hoja:
            from django.utils import timezone
            from django.db import transaction
            
            today = timezone.now()
            fecha = today.strftime('%Y%m%d')
            prefijo = f'HR-{fecha}'
            
            # ISS-010: Usar transacción y select_for_update para evitar race conditions
            with transaction.atomic():
                ultima = HojaRecoleccion.objects.select_for_update().filter(
                    folio_hoja__startswith=prefijo
                ).order_by('-folio_hoja').first()
                
                if ultima:
                    try:
                        ultimo_num = int(ultima.folio_hoja.split('-')[-1])
                        nuevo_num = ultimo_num + 1
                    except (ValueError, IndexError):
                        nuevo_num = 1
                else:
                    nuevo_num = 1
                
                self.folio_hoja = f'{prefijo}-{nuevo_num:04d}'
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)
    
    @classmethod
    def generar_hash(cls, contenido_dict):
        """
        Genera hash SHA256 del contenido para verificar integridad.
        """
        import hashlib
        import json
        
        # Serializar el contenido de forma determinista
        contenido_str = json.dumps(contenido_dict, sort_keys=True, default=str)
        return hashlib.sha256(contenido_str.encode('utf-8')).hexdigest()
    
    def verificar_integridad(self):
        """
        Verifica que el hash del contenido coincida con el almacenado.
        Returns True si el contenido no ha sido alterado.
        """
        hash_calculado = self.generar_hash(self.contenido_json)
        return hash_calculado == self.hash_contenido
    
    def registrar_impresion(self, usuario=None):
        """Registra una impresión de la hoja"""
        from django.utils import timezone
        self.veces_impresa += 1
        if not self.fecha_impresion:
            self.fecha_impresion = timezone.now()
            self.estado = 'impresa'
        self.save(update_fields=['veces_impresa', 'fecha_impresion', 'estado'])
    
    def registrar_descarga(self):
        """Registra una descarga del PDF"""
        self.veces_descargada += 1
        self.save(update_fields=['veces_descargada'])
    
    def marcar_verificada(self, usuario):
        """Marca la hoja como verificada por farmacia"""
        from django.utils import timezone
        self.estado = 'verificada'
        self.fecha_verificacion = timezone.now()
        self.verificado_por = usuario
        self.save(update_fields=['estado', 'fecha_verificacion', 'verificado_por'])
    
    @classmethod
    def crear_desde_requisicion(cls, requisicion, usuario=None):
        """
        Crea una HojaRecoleccion a partir de una requisición autorizada.
        """
        import json
        
        # Construir contenido para la hoja
        detalles_data = []
        for detalle in requisicion.detalles.select_related('producto').all():
            detalles_data.append({
                'producto_id': detalle.producto.id,
                'producto_clave': detalle.producto.clave,
                'producto_descripcion': detalle.producto.descripcion,
                'cantidad_solicitada': detalle.cantidad_solicitada,
                'cantidad_autorizada': detalle.cantidad_autorizada or 0,
            })
        
        contenido = {
            'requisicion_id': requisicion.id,
            'requisicion_folio': requisicion.folio,
            'centro_id': requisicion.centro.id if requisicion.centro else None,
            'centro_nombre': requisicion.centro.nombre if requisicion.centro else 'N/A',
            'centro_clave': requisicion.centro.clave if requisicion.centro else 'N/A',
            'fecha_solicitud': str(requisicion.fecha_solicitud),
            'fecha_autorizacion': str(requisicion.fecha_autorizacion) if requisicion.fecha_autorizacion else None,
            'solicitante': requisicion.usuario_solicita.get_full_name() if requisicion.usuario_solicita else 'N/A',
            'autorizador': requisicion.usuario_autoriza.get_full_name() if requisicion.usuario_autoriza else 'N/A',
            'detalles': detalles_data,
        }
        
        # Generar hash del contenido
        hash_contenido = cls.generar_hash(contenido)
        
        # Crear la hoja
        hoja = cls.objects.create(
            requisicion=requisicion,
            contenido_json=contenido,
            hash_contenido=hash_contenido,
            generado_por=usuario,
        )
        
        logger.info(f"Hoja de recolección {hoja.folio_hoja} generada para requisición {requisicion.folio}")
        return hoja


class DetalleHojaRecoleccion(models.Model):
    """
    Detalle de productos en la hoja de recolección.
    Almacena las cantidades oficiales al momento de la autorización.
    """
    hoja = models.ForeignKey(
        HojaRecoleccion,
        on_delete=models.CASCADE,
        related_name='detalles'
    )
    producto = models.ForeignKey(
        'Producto',
        on_delete=models.PROTECT
    )
    cantidad_autorizada = models.IntegerField(
        validators=[MinValueValidator(0)],
        help_text="Cantidad autorizada por farmacia"
    )
    cantidad_entregada = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Cantidad efectivamente entregada"
    )
    lote_asignado = models.ForeignKey(
        'Lote',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Lote del cual se surtió"
    )
    observaciones = models.TextField(blank=True)
    
    class Meta:
        db_table = 'detalle_hojas_recoleccion'
        unique_together = ['hoja', 'producto']
    
    def __str__(self):
        return f"{self.producto.clave} - {self.cantidad_autorizada} unidades"


# ============================================================================
# TEMA GLOBAL DEL SISTEMA
# ============================================================================

def tema_logo_path(instance, filename):
    """Genera ruta para logos del tema"""
    import os
    ext = filename.split('.')[-1]
    return f'tema/logos/{instance.tipo_logo}_{instance.id}.{ext}'


def tema_imagen_path(instance, filename):
    """Genera ruta para imagenes del tema (fondos, etc)"""
    import os
    from django.utils import timezone
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    ext = filename.split('.')[-1]
    return f'tema/imagenes/{timestamp}.{ext}'


class TemaGlobal(models.Model):
    """
    Configuracion global del tema del sistema.
    Solo debe existir un registro activo a la vez (singleton pattern).
    
    Almacena:
    - Logos e imagenes
    - Paleta de colores
    - Tipografias
    - Configuracion de reportes
    - Ano visible en documentos
    """
    
    # -------------------------------------------------------------------------
    # METADATA
    # -------------------------------------------------------------------------
    nombre = models.CharField(
        max_length=100,
        default='Tema Institucional',
        help_text='Nombre descriptivo del tema'
    )
    descripcion = models.TextField(
        blank=True,
        help_text='Descripcion del tema'
    )
    activo = models.BooleanField(
        default=True,
        help_text='Solo un tema puede estar activo a la vez'
    )
    es_tema_institucional = models.BooleanField(
        default=False,
        help_text='Indica si es el tema institucional por defecto'
    )
    
    # -------------------------------------------------------------------------
    # LOGOS E IMAGENES
    # -------------------------------------------------------------------------
    logo_header = models.ImageField(
        upload_to='tema/logos/',
        null=True,
        blank=True,
        validators=[validate_logo_size],
        help_text='Logo principal mostrado en el header (max 500KB)'
    )
    logo_login = models.ImageField(
        upload_to='tema/logos/',
        null=True,
        blank=True,
        validators=[validate_logo_size],
        help_text='Logo para pantalla de login (max 500KB)'
    )
    logo_reportes = models.ImageField(
        upload_to='tema/logos/',
        null=True,
        blank=True,
        validators=[validate_logo_size],
        help_text='Logo para encabezado de reportes PDF (max 500KB)'
    )
    favicon = models.ImageField(
        upload_to='tema/logos/',
        null=True,
        blank=True,
        help_text='Favicon del sitio (ICO o PNG 32x32)'
    )
    imagen_fondo_login = models.ImageField(
        upload_to='tema/imagenes/',
        null=True,
        blank=True,
        help_text='Imagen de fondo para pantalla de login'
    )
    imagen_fondo_reportes = models.ImageField(
        upload_to='tema/imagenes/',
        null=True,
        blank=True,
        help_text='Imagen de fondo/marca de agua para reportes'
    )
    
    # -------------------------------------------------------------------------
    # COLORES - Paleta Principal
    # -------------------------------------------------------------------------
    color_primario = models.CharField(
        max_length=7,
        default='#1e3a5f',
        help_text='Color primario (hex). Usado en header, botones principales'
    )
    color_primario_hover = models.CharField(
        max_length=7,
        default='#15293f',
        help_text='Color primario en hover'
    )
    color_secundario = models.CharField(
        max_length=7,
        default='#3b82f6',
        help_text='Color secundario/acento'
    )
    color_secundario_hover = models.CharField(
        max_length=7,
        default='#2563eb',
        help_text='Color secundario en hover'
    )
    
    # Colores de estado
    color_exito = models.CharField(
        max_length=7,
        default='#10b981',
        help_text='Color para estados de exito (verde)'
    )
    color_error = models.CharField(
        max_length=7,
        default='#ef4444',
        help_text='Color para errores (rojo)'
    )
    color_advertencia = models.CharField(
        max_length=7,
        default='#f59e0b',
        help_text='Color para advertencias (amarillo/naranja)'
    )
    color_info = models.CharField(
        max_length=7,
        default='#3b82f6',
        help_text='Color para informacion (azul)'
    )
    
    # Colores de fondo
    color_fondo_principal = models.CharField(
        max_length=7,
        default='#f3f4f6',
        help_text='Color de fondo principal del layout'
    )
    color_fondo_tarjetas = models.CharField(
        max_length=7,
        default='#ffffff',
        help_text='Color de fondo de tarjetas y paneles'
    )
    color_fondo_sidebar = models.CharField(
        max_length=7,
        default='#1e3a5f',
        help_text='Color de fondo del sidebar/menu'
    )
    color_fondo_header = models.CharField(
        max_length=7,
        default='#1e3a5f',
        help_text='Color de fondo del header'
    )
    
    # Colores de texto
    color_texto_principal = models.CharField(
        max_length=7,
        default='#1f2937',
        help_text='Color de texto principal'
    )
    color_texto_secundario = models.CharField(
        max_length=7,
        default='#6b7280',
        help_text='Color de texto secundario/muted'
    )
    color_texto_invertido = models.CharField(
        max_length=7,
        default='#ffffff',
        help_text='Color de texto sobre fondos oscuros'
    )
    color_texto_links = models.CharField(
        max_length=7,
        default='#3b82f6',
        help_text='Color de enlaces'
    )
    
    # Colores de bordes y elementos
    color_borde = models.CharField(
        max_length=7,
        default='#e5e7eb',
        help_text='Color de bordes por defecto'
    )
    color_borde_focus = models.CharField(
        max_length=7,
        default='#3b82f6',
        help_text='Color de borde en focus'
    )
    
    # -------------------------------------------------------------------------
    # TIPOGRAFIA
    # -------------------------------------------------------------------------
    FUENTES_DISPONIBLES = [
        ('Inter', 'Inter (Sans-serif moderno)'),
        ('Roboto', 'Roboto (Sans-serif Google)'),
        ('Open Sans', 'Open Sans (Sans-serif legible)'),
        ('Lato', 'Lato (Sans-serif elegante)'),
        ('Montserrat', 'Montserrat (Sans-serif geometrico)'),
        ('Poppins', 'Poppins (Sans-serif redondeado)'),
        ('Source Sans Pro', 'Source Sans Pro (Adobe)'),
        ('Nunito', 'Nunito (Sans-serif suave)'),
        ('Arial', 'Arial (Sistema)'),
        ('Helvetica', 'Helvetica (Sistema)'),
    ]
    
    fuente_principal = models.CharField(
        max_length=50,
        default='Inter',
        choices=FUENTES_DISPONIBLES,
        help_text='Familia tipografica principal'
    )
    fuente_titulos = models.CharField(
        max_length=50,
        default='Inter',
        choices=FUENTES_DISPONIBLES,
        help_text='Familia tipografica para titulos'
    )
    
    # Tamanos de fuente (en rem para responsividad)
    tamano_h1 = models.CharField(
        max_length=10,
        default='2rem',
        help_text='Tamano de titulos H1'
    )
    tamano_h2 = models.CharField(
        max_length=10,
        default='1.5rem',
        help_text='Tamano de titulos H2'
    )
    tamano_h3 = models.CharField(
        max_length=10,
        default='1.25rem',
        help_text='Tamano de titulos H3'
    )
    tamano_texto_base = models.CharField(
        max_length=10,
        default='1rem',
        help_text='Tamano de texto base/parrafos'
    )
    tamano_texto_pequeno = models.CharField(
        max_length=10,
        default='0.875rem',
        help_text='Tamano de texto pequeno'
    )
    tamano_etiquetas = models.CharField(
        max_length=10,
        default='0.875rem',
        help_text='Tamano de etiquetas de formulario'
    )
    tamano_botones = models.CharField(
        max_length=10,
        default='0.875rem',
        help_text='Tamano de texto en botones'
    )
    
    # Pesos de fuente
    peso_titulos = models.CharField(
        max_length=10,
        default='700',
        help_text='Peso de fuente para titulos (400-900)'
    )
    peso_texto_normal = models.CharField(
        max_length=10,
        default='400',
        help_text='Peso de fuente para texto normal'
    )
    peso_botones = models.CharField(
        max_length=10,
        default='600',
        help_text='Peso de fuente para botones'
    )
    
    # -------------------------------------------------------------------------
    # CONFIGURACION DE REPORTES
    # -------------------------------------------------------------------------
    reporte_ano_visible = models.CharField(
        max_length=10,
        default='2025',
        help_text='Ano que aparece en los reportes'
    )
    reporte_titulo_institucion = models.CharField(
        max_length=200,
        default='Sistema de Farmacia Penitenciaria',
        help_text='Titulo de la institucion en reportes'
    )
    reporte_subtitulo = models.CharField(
        max_length=200,
        blank=True,
        default='Control de Inventario y Distribucion',
        help_text='Subtitulo en reportes'
    )
    reporte_pie_pagina = models.CharField(
        max_length=300,
        blank=True,
        default='Documento generado por el Sistema de Farmacia Penitenciaria',
        help_text='Texto del pie de pagina en reportes'
    )
    
    # Colores especificos de reportes
    reporte_color_encabezado = models.CharField(
        max_length=7,
        default='#1e3a5f',
        help_text='Color de fondo del encabezado de tablas en reportes'
    )
    reporte_color_texto_encabezado = models.CharField(
        max_length=7,
        default='#ffffff',
        help_text='Color de texto en encabezado de tablas'
    )
    reporte_color_filas_alternas = models.CharField(
        max_length=7,
        default='#f9fafb',
        help_text='Color de filas alternas en tablas'
    )
    
    # -------------------------------------------------------------------------
    # OTROS ESTILOS
    # -------------------------------------------------------------------------
    border_radius_base = models.CharField(
        max_length=10,
        default='0.5rem',
        help_text='Radio de borde base para elementos'
    )
    border_radius_botones = models.CharField(
        max_length=10,
        default='0.375rem',
        help_text='Radio de borde para botones'
    )
    shadow_base = models.CharField(
        max_length=100,
        default='0 1px 3px 0 rgba(0, 0, 0, 0.1)',
        help_text='Sombra base para tarjetas'
    )
    
    # -------------------------------------------------------------------------
    # AUDITORIA
    # -------------------------------------------------------------------------
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='temas_creados'
    )
    modificado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='temas_modificados'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tema_global'
        verbose_name = 'Tema Global'
        verbose_name_plural = 'Temas Globales'
    
    def __str__(self):
        estado = '(Activo)' if self.activo else ''
        return f"{self.nombre} {estado}"
    
    def save(self, *args, **kwargs):
        # Si este tema se activa, desactivar los demas
        if self.activo:
            TemaGlobal.objects.exclude(pk=self.pk).update(activo=False)
        super().save(*args, **kwargs)
    
    @classmethod
    def get_tema_activo(cls):
        """Obtiene el tema activo actual o crea el institucional si no existe"""
        tema = cls.objects.filter(activo=True).first()
        if not tema:
            tema = cls.crear_tema_institucional()
        return tema
    
    @classmethod
    def crear_tema_institucional(cls):
        """Crea el tema institucional por defecto"""
        tema, created = cls.objects.get_or_create(
            es_tema_institucional=True,
            defaults={
                'nombre': 'Tema Institucional',
                'descripcion': 'Tema oficial del Sistema de Farmacia Penitenciaria',
                'activo': True,
            }
        )
        if created:
            logger.info("Tema institucional creado")
        return tema
    
    def to_css_variables(self):
        """Convierte la configuracion a variables CSS compatibles con el frontend"""
        # Función helper para calcular color light con opacidad
        def hex_to_rgba_light(hex_color, opacity=0.2):
            hex_color = hex_color.lstrip('#')
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return f'rgba({r}, {g}, {b}, {opacity})'
        
        return {
            # Colores principales - nombres compatibles con frontend
            '--color-primary': self.color_primario,
            '--color-primary-hover': self.color_primario_hover,
            '--color-primary-light': hex_to_rgba_light(self.color_primario),
            '--color-secondary': self.color_secundario,
            '--color-secondary-hover': self.color_secundario_hover,
            '--color-accent': self.color_secundario,  # Alias para compatibilidad
            
            # Estados
            '--color-success': self.color_exito,
            '--color-error': self.color_error,
            '--color-warning': self.color_advertencia,
            '--color-info': self.color_info,
            '--color-danger': self.color_error,  # Alias para compatibilidad
            
            # Fondos - NOMBRES QUE USA EL FRONTEND
            '--color-background': self.color_fondo_principal,
            '--color-sidebar-bg': self.color_fondo_sidebar,
            '--color-header-bg': self.color_fondo_header,
            '--color-card-bg': self.color_fondo_tarjetas,
            # Aliases alternativos por compatibilidad
            '--color-bg-main': self.color_fondo_principal,
            '--color-bg-card': self.color_fondo_tarjetas,
            '--color-bg-sidebar': self.color_fondo_sidebar,
            '--color-bg-header': self.color_fondo_header,
            '--bg-primary': self.color_fondo_tarjetas,
            '--bg-secondary': self.color_fondo_principal,
            
            # Texto - NOMBRES QUE USA EL FRONTEND
            '--color-text': self.color_texto_principal,
            '--color-text-secondary': self.color_texto_secundario,
            '--color-sidebar-text': self.color_texto_invertido,
            '--color-header-text': self.color_texto_invertido,
            # Aliases alternativos por compatibilidad
            '--color-text-primary': self.color_texto_principal,
            '--color-text-inverted': self.color_texto_invertido,
            '--color-text-link': self.color_texto_links,
            '--text-primary': self.color_texto_principal,
            '--text-secondary': self.color_texto_secundario,
            
            # Bordes
            '--color-border': self.color_borde,
            '--color-border-focus': self.color_borde_focus,
            '--border-color': self.color_borde,
            
            # Tipografia - NOMBRES QUE USA EL FRONTEND
            '--font-family-principal': f"'{self.fuente_principal}', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif",
            '--font-family-titulos': f"'{self.fuente_titulos}', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
            # Aliases alternativos
            '--font-family-main': f"'{self.fuente_principal}', sans-serif",
            '--font-family-headings': f"'{self.fuente_titulos}', sans-serif",
            
            # Tamaños de fuente - NOMBRES QUE USA EL FRONTEND
            '--font-size-titulo': self.tamano_h1,
            '--font-size-subtitulo': self.tamano_h2,
            '--font-size-cuerpo': self.tamano_texto_base,
            '--font-size-pequeño': self.tamano_texto_pequeno,
            # Aliases alternativos
            '--font-size-h1': self.tamano_h1,
            '--font-size-h2': self.tamano_h2,
            '--font-size-h3': self.tamano_h3,
            '--font-size-base': self.tamano_texto_base,
            '--font-size-sm': self.tamano_texto_pequeno,
            '--font-size-label': self.tamano_etiquetas,
            '--font-size-button': self.tamano_botones,
            
            # Pesos de fuente
            '--font-weight-headings': self.peso_titulos,
            '--font-weight-normal': self.peso_texto_normal,
            '--font-weight-button': self.peso_botones,
            
            # Bordes y sombras
            '--border-radius-base': self.border_radius_base,
            '--border-radius-button': self.border_radius_botones,
            '--shadow-base': self.shadow_base,
            '--radius-sm': '4px',
            '--radius-md': '6px',
            '--radius-lg': self.border_radius_base,
            
            # Configuración de reportes (para frontend)
            '--color-reporte-encabezado': self.reporte_color_encabezado,
            '--color-reporte-texto-encabezado': self.reporte_color_texto_encabezado,
            '--color-reporte-filas-alternas': self.reporte_color_filas_alternas,
            '--tema-nombre-institucion': self.reporte_titulo_institucion,
            '--tema-subtitulo': self.reporte_subtitulo,
            '--tema-pie-pagina': self.reporte_pie_pagina,
            '--tema-ano-visible': str(self.reporte_ano_visible),
        }
    
    def to_json_config(self):
        """Exporta toda la configuracion como JSON para el frontend"""
        config = {
            'id': self.id,
            'nombre': self.nombre,
            'es_tema_institucional': self.es_tema_institucional,
            
            # URLs de imagenes
            'logos': {
                'header': self.logo_header.url if self.logo_header else None,
                'login': self.logo_login.url if self.logo_login else None,
                'reportes': self.logo_reportes.url if self.logo_reportes else None,
                'favicon': self.favicon.url if self.favicon else None,
            },
            'imagenes': {
                'fondo_login': self.imagen_fondo_login.url if self.imagen_fondo_login else None,
                'fondo_reportes': self.imagen_fondo_reportes.url if self.imagen_fondo_reportes else None,
            },
            
            # Colores
            'colores': {
                'primario': self.color_primario,
                'primario_hover': self.color_primario_hover,
                'secundario': self.color_secundario,
                'secundario_hover': self.color_secundario_hover,
                'exito': self.color_exito,
                'error': self.color_error,
                'advertencia': self.color_advertencia,
                'info': self.color_info,
                'fondo_principal': self.color_fondo_principal,
                'fondo_tarjetas': self.color_fondo_tarjetas,
                'fondo_sidebar': self.color_fondo_sidebar,
                'fondo_header': self.color_fondo_header,
                'texto_principal': self.color_texto_principal,
                'texto_secundario': self.color_texto_secundario,
                'texto_invertido': self.color_texto_invertido,
                'texto_links': self.color_texto_links,
                'borde': self.color_borde,
                'borde_focus': self.color_borde_focus,
            },
            
            # Tipografia
            'tipografia': {
                'fuente_principal': self.fuente_principal,
                'fuente_titulos': self.fuente_titulos,
                'tamanos': {
                    'h1': self.tamano_h1,
                    'h2': self.tamano_h2,
                    'h3': self.tamano_h3,
                    'base': self.tamano_texto_base,
                    'pequeno': self.tamano_texto_pequeno,
                    'etiquetas': self.tamano_etiquetas,
                    'botones': self.tamano_botones,
                },
                'pesos': {
                    'titulos': self.peso_titulos,
                    'normal': self.peso_texto_normal,
                    'botones': self.peso_botones,
                },
            },
            
            # Reportes
            'reportes': {
                'ano_visible': self.reporte_ano_visible,
                'titulo_institucion': self.reporte_titulo_institucion,
                'subtitulo': self.reporte_subtitulo,
                'pie_pagina': self.reporte_pie_pagina,
                'color_encabezado': self.reporte_color_encabezado,
                'color_texto_encabezado': self.reporte_color_texto_encabezado,
                'color_filas_alternas': self.reporte_color_filas_alternas,
            },
            
            # Estilos generales
            'estilos': {
                'border_radius_base': self.border_radius_base,
                'border_radius_botones': self.border_radius_botones,
                'shadow_base': self.shadow_base,
            },
            
            # Variables CSS listas para usar
            'css_variables': self.to_css_variables(),
            
            # Metadata
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        return config


class AuditLog(models.Model):
    """
    ISS-032: Modelo de log de auditoría centralizado.
    
    Registra todas las operaciones importantes del sistema
    para trazabilidad y cumplimiento.
    """
    
    ACTIONS = [
        ('create', 'Crear'),
        ('read', 'Leer'),
        ('update', 'Actualizar'),
        ('delete', 'Eliminar'),
        ('soft_delete', 'Eliminar (soft)'),
        ('restore', 'Restaurar'),
        ('login', 'Inicio de sesión'),
        ('logout', 'Cierre de sesión'),
        ('login_failed', 'Login fallido'),
        ('password_change', 'Cambio de contraseña'),
        ('permission_change', 'Cambio de permisos'),
        ('export', 'Exportación'),
        ('import', 'Importación'),
        ('transition', 'Transición de estado'),
        ('approval', 'Aprobación'),
        ('rejection', 'Rechazo'),
        ('transfer', 'Transferencia'),
        ('adjustment', 'Ajuste'),
        ('error', 'Error'),
    ]
    
    SEVERITIES = [
        ('debug', 'Debug'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]
    
    timestamp = models.DateTimeField(db_index=True)
    action = models.CharField(max_length=50, choices=ACTIONS, db_index=True)
    severity = models.CharField(max_length=20, choices=SEVERITIES, default='info')
    usuario_id = models.IntegerField(null=True, blank=True, db_index=True)
    modelo = models.CharField(max_length=100, db_index=True)
    objeto_id = models.IntegerField(null=True, blank=True)
    objeto_repr = models.CharField(max_length=200, blank=True)
    descripcion = models.TextField()
    datos_anteriores = models.JSONField(null=True, blank=True)
    datos_nuevos = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=200, blank=True)
    request_id = models.CharField(max_length=100, null=True, blank=True)
    duracion_ms = models.FloatField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp', 'action'], name='idx_audit_timestamp_action'),
            models.Index(fields=['usuario_id', 'timestamp'], name='idx_audit_usuario_timestamp'),
            models.Index(fields=['modelo', 'objeto_id'], name='idx_audit_modelo_objeto'),
            models.Index(fields=['severity', 'timestamp'], name='idx_audit_severity'),
        ]
    
    def __str__(self):
        return f"[{self.timestamp}] {self.action} {self.modelo}#{self.objeto_id}"

