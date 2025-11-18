from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date
from .constants import *
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
    activo = models.BooleanField(default=True)
    
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
        help_text="Clave única del producto (3-50 caracteres alfanuméricos)"
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
    
    # Campos de auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
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
    fecha_entrada = models.DateField(auto_now_add=True)
    observaciones = models.TextField(blank=True)
    
    # Soft delete
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lotes_creados'
    )

    class Meta:
        db_table = 'lotes'
        ordering = ['-fecha_entrada', 'fecha_caducidad']
        constraints = [
            models.UniqueConstraint(
                fields=['producto', 'numero_lote'],
                name='unique_numero_lote_por_producto'
            )
        ]
        indexes = [
            models.Index(fields=['estado']),
            models.Index(fields=['fecha_caducidad']),
            models.Index(fields=['producto', 'estado']),
            models.Index(fields=['deleted_at']),
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
    
    def dias_para_caducar(self):
        """Calcula días restantes para caducidad"""
        delta = self.fecha_caducidad - date.today()
        return delta.days
    
    def esta_caducado(self):
        """Verifica si el lote está vencido"""
        return self.fecha_caducidad < date.today()
    
    def alerta_caducidad(self):
        """
        Retorna nivel de alerta por caducidad
        Returns: 'critico' | 'proximo' | 'normal' | 'vencido'
        """
        dias = self.dias_para_caducar()
        
        if dias < 0:
            return 'vencido'
        elif dias <= 7:
            return 'critico'
        elif dias <= 30:
            return 'proximo'
        else:
            return 'normal'
    
    def soft_delete(self):
        """Marca lote como eliminado sin borrar de BD"""
        from django.utils import timezone
        self.deleted_at = timezone.now()
        self.activo = False
        self.save()
    
    @classmethod
    def active_only(cls):
        """Retorna solo lotes activos (no eliminados)"""
        return cls.objects.filter(deleted_at__isnull=True)


class Requisicion(models.Model):
    """
    Modelo de Requisición de medicamentos
    Flujo: Borrador -> Enviada -> Autorizada/Rechazada -> Surtida
    """
    folio = models.CharField(max_length=50, unique=True)
    centro = models.ForeignKey(
        Centro,
        on_delete=models.PROTECT,
        related_name='requisiciones'
    )
    usuario_solicita = models.ForeignKey(
        User,
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
    usuario_autoriza = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requisiciones_autorizadas'
    )
    fecha_autorizacion = models.DateTimeField(null=True, blank=True)
    motivo_rechazo = models.TextField(blank=True)
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


class DetalleRequisicion(models.Model):
    """
    Detalle de productos en una requisición
    """
    requisicion = models.ForeignKey(
        Requisicion,
        on_delete=models.CASCADE,
        related_name='detalles'
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT
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
        unique_together = ['requisicion', 'producto']
        indexes = [
            models.Index(fields=['requisicion', 'producto']),
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
        User,
        on_delete=models.PROTECT
    )
    requisicion = models.ForeignKey(
        Requisicion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos'
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
            if abs(self.cantidad) > self.lote.cantidad_actual:
                raise ValidationError({
                    'cantidad': f'Stock insuficiente. Disponible: {self.lote.cantidad_actual}'
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        
        # Actualizar cantidad en lote
        if self.tipo in ['entrada', 'salida', 'ajuste']:
            self.lote.cantidad_actual += self.cantidad
            self.lote.save()
            
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
    
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
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
    Perfil extendido de usuario para asociar con centros
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    centro = models.ForeignKey(
        Centro,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios_perfil',
        help_text="Centro asignado al usuario"
    )
    telefono = models.CharField(max_length=15, blank=True)
    cargo = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profiles'
    
    def __str__(self):
        return f"Perfil de {self.user.username}"


class AuditoriaLog(models.Model):
    """
    Modelo de auditoría para rastrear todas las acciones del sistema
    """
    usuario = models.ForeignKey(
        User,
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
    objeto_id = models.IntegerField(help_text="ID del objeto afectado")
    objeto_repr = models.CharField(max_length=255, help_text="Representación del objeto")
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
