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

logger = logging.getLogger(__name__)


class User(AbstractUser):
    """
    Modelo de usuario extendido con roles y asignación de centro
    """
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
        self.full_clean()
        super().save(*args, **kwargs)
        logger.info(f"Producto {self.clave} {'creado' if self.pk is None else 'actualizado'}")

    def __str__(self):
        return f"{self.clave} - {self.descripcion[:50]}"
    
    def get_stock_actual(self):
        """Calcula el stock actual sumando todos los lotes disponibles"""
        return sum(
            lote.cantidad_actual
            for lote in self.lotes.filter(estado='disponible')
        )
    
    def get_nivel_stock(self):
        """Retorna el nivel de stock: critico, bajo, normal, alto"""
        stock_actual = self.get_stock_actual()
        
        if stock_actual <= self.stock_minimo * NIVELES_STOCK['critico']:
            return 'critico'
        elif stock_actual <= self.stock_minimo * NIVELES_STOCK['bajo']:
            return 'bajo'
        elif stock_actual <= self.stock_minimo * NIVELES_STOCK['normal']:
            return 'normal'
        else:
            return 'alto'


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
    
    # Documento PDF adjunto (contrato, certificado, soporte documental)
    documento_pdf = models.FileField(
        upload_to='lotes/documentos/%Y/%m/',
        null=True,
        blank=True,
        help_text="Documento PDF de soporte (contrato, certificado, etc.)"
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

    class Meta:
        db_table = 'lotes'
        ordering = ['-fecha_entrada', 'fecha_caducidad']
        constraints = [
            # Constraint modificado: mismo lote puede existir en farmacia Y en centros
            # pero solo UNA vez por centro (o farmacia central)
            models.UniqueConstraint(
                fields=['producto', 'numero_lote', 'centro'],
                name='unique_lote_por_producto_centro'
            )
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
            # Lote de centro: DEBE tener lote_origen (excepto en creación inicial vía surtido)
            # La validación de lote_origen se relaja aquí porque se asigna después del create
            pass
        
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
        
        # Validar fecha de caducidad
        if self.fecha_caducidad and self.fecha_caducidad < date.today():
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
        """Calcula días restantes para caducidad"""
        delta = self.fecha_caducidad - date.today()
        return delta.days
    
    def esta_caducado(self):
        """Verifica si el lote está vencido"""
        return self.fecha_caducidad < date.today()
    
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


class Requisicion(models.Model):
    """
    Modelo de Requisición de medicamentos
    Flujo: Borrador -> Enviada -> Autorizada/Rechazada -> Surtida -> Recibida
    
    Máquina de Estados:
    - borrador: Estado inicial, puede ser editada
    - enviada: Enviada para revisión, pendiente de autorización
    - autorizada: Aprobada, lista para surtir
    - parcial: Parcialmente autorizada
    - rechazada: Rechazada, no se surtirá
    - surtida: Surtida por farmacia, pendiente de recepción
    - recibida: Recibida por el centro destino
    - cancelada: Cancelada por el usuario
    """
    # Definición de transiciones válidas de estado
    TRANSICIONES_VALIDAS = {
        'borrador': ['enviada', 'cancelada'],
        'enviada': ['autorizada', 'parcial', 'rechazada', 'cancelada'],
        'autorizada': ['surtida', 'cancelada'],
        'parcial': ['surtida', 'cancelada'],
        'rechazada': [],  # Estado terminal
        'surtida': ['recibida'],  # Puede pasar a recibida
        'recibida': [],   # Estado terminal
        'cancelada': [],  # Estado terminal
    }
    
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
        """Auto-generar folio si no existe"""
        if not self.folio:
            # Generar folio: REQ-CENTRO-YYYYMMDD-NNNN
            from django.utils import timezone
            today = timezone.now()
            fecha = today.strftime('%Y%m%d')
            centro_codigo = self.centro.clave[:3] if self.centro else 'GEN'
            
            # Obtener último número del día
            ultima = Requisicion.objects.filter(
                folio__startswith=f'REQ-{centro_codigo}-{fecha}'
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
            
            self.folio = f'REQ-{centro_codigo}-{fecha}-{nuevo_num:04d}'
            logger.info(f"Folio generado automáticamente: {self.folio}")
        
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
        help_text="Logo para el header de la interfaz (PNG/JPG, max 500KB)"
    )
    
    # Logo/fondo para PDFs institucionales
    logo_pdf = models.ImageField(
        upload_to='configuracion/logos/',
        null=True,
        blank=True,
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
        default='#1976D2',
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
        default='#1565C0',
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
        default='#FF5722',
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
        default='#263238',
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
        default='#1976D2',
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
        default='#ECEFF1',
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
        ('default', 'Por Defecto (Azul)'),
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
                'color_primario': '#1976D2',
                'color_primario_hover': '#1565C0',
                'color_secundario': '#424242',
                'color_acento': '#FF5722',
                'color_fondo': '#F5F5F5',
                'color_fondo_sidebar': '#263238',
                'color_fondo_header': '#1976D2',
                'color_fondo_card': '#FFFFFF',
                'color_texto': '#212121',
                'color_texto_secundario': '#757575',
                'color_texto_sidebar': '#ECEFF1',
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
        """Auto-generar folio si no existe"""
        if not self.folio_hoja:
            from django.utils import timezone
            today = timezone.now()
            fecha = today.strftime('%Y%m%d')
            
            # Obtener último número del día
            ultima = HojaRecoleccion.objects.filter(
                folio_hoja__startswith=f'HR-{fecha}'
            ).order_by('-folio_hoja').first()
            
            if ultima:
                try:
                    ultimo_num = int(ultima.folio_hoja.split('-')[-1])
                    nuevo_num = ultimo_num + 1
                except (ValueError, IndexError):
                    nuevo_num = 1
            else:
                nuevo_num = 1
            
            self.folio_hoja = f'HR-{fecha}-{nuevo_num:04d}'
        
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
