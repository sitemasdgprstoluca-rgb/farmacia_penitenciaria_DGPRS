"""
Modelos Django para la aplicación core de farmacia penitenciaria.

ISS-005 FIX (audit5): DOCUMENTACIÓN SOBRE managed=False
=========================================================

TODOS los modelos en este archivo usan `managed = False` porque las tablas 
ya existen en la base de datos Supabase/PostgreSQL. Esto tiene las siguientes
implicaciones importantes:

1. MIGRACIONES:
   - Django NO creará ni modificará las tablas automáticamente
   - Cualquier cambio de esquema debe hacerse directamente en Supabase
   - Usar archivos SQL en docs/SQL_MIGRATIONS.md para cambios de esquema

2. CONSTRAINTS Y VALIDACIONES:
   - Django NO aplica constraints de BD (unique, foreign key, check)
   - Las constraints se gestionan directamente en Supabase
   - Se DEBE validar en el código Python (forms, serializers, servicios)
   
3. FOREIGN KEYS:
   - on_delete NO tiene efecto en BD (solo en cascadas Django)
   - Triggers de Supabase manejan la integridad referencial real
   
4. CAMPO 'estado' EN LOTES:
   - Es una PROPIEDAD CALCULADA (@property), NO un campo de BD
   - Se calcula desde: activo + cantidad_actual + fecha_caducidad
   - NUNCA usar `estado__in` en querysets (causará FieldError)
   
5. RECOMENDACIONES:
   - Verificar existencia de campos en Supabase antes de agregar al modelo
   - Usar transaction.atomic() con select_for_update() para operaciones críticas
   - Agregar validaciones explícitas en servicios/serializers

Ver también: docs/SQL_MIGRATIONS.md, ARQUITECTURA.md
"""

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
    ESTADOS_LOTE_DISPONIBLES,  # ISS-001 FIX (audit11)
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
    """Validador específico para logos (max 500KB)"""
    validate_image_max_size(value, max_size_kb=500)


def validate_image_size(value):
    """
    ISS-002 FIX: Valida que la imagen no exceda 2MB.
    
    Corrige bug donde no se verificaba si value es None antes de
    acceder a value.size, causando AttributeError en campos opcionales.
    """
    if not value:
        return  # ISS-002 FIX: Retornar temprano si valor es None/vacío
    max_size = 2 * 1024 * 1024  # 2 MB
    if value.size > max_size:
        raise ValidationError(f'La imagen no puede exceder 2MB. Tamaño actual: {value.size/1024/1024:.1f}MB')


def producto_imagen_path(instance, filename):
    """Genera ruta para imÃ¡genes de productos"""
    ext = filename.split('.')[-1]
    return f'productos/{instance.clave}.{ext}'


def requisicion_firma_path(instance, filename):
    """
    ISS-006 FIX: Genera ruta SEGURA para fotos de firma de requisiciones.
    
    Sanitiza el nombre de archivo para prevenir:
    - Path traversal (../)
    - Caracteres peligrosos
    - Extensiones no permitidas
    """
    import uuid
    from django.utils import timezone
    
    # ISS-006: Extensiones de imagen permitidas
    EXTENSIONES_PERMITIDAS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    
    # Sanitizar extensión
    ext = os.path.splitext(filename)[1].lower()
    if ext not in EXTENSIONES_PERMITIDAS:
        ext = '.jpg'  # Default seguro
    
    # Generar nombre único (evita colisiones y path traversal)
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    unique_id = uuid.uuid4().hex[:8]
    folio = getattr(instance, 'folio', 'REQ') or 'REQ'
    
    # Sanitizar folio (solo alfanuméricos y guiones)
    safe_folio = ''.join(c for c in str(folio) if c.isalnum() or c in '-_')[:50]
    
    return f'requisiciones/firmas/{safe_folio}_{timestamp}_{unique_id}{ext}'


def validate_firma_path(value):
    r"""
    ISS-006 FIX: Valida que una ruta de firma sea segura.
    
    Previene:
    - Path traversal (../, ..\)
    - Rutas absolutas
    - Caracteres peligrosos
    - Extensiones no permitidas
    
    Args:
        value: Ruta a validar (string)
        
    Raises:
        ValidationError si la ruta es insegura
    """
    if not value:
        return
    
    # ISS-006: Extensiones de imagen permitidas
    EXTENSIONES_PERMITIDAS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    
    # Caracteres peligrosos
    CARACTERES_PELIGROSOS = ['..', '\\', '//', '<', '>', ':', '"', '|', '?', '*', '\x00']
    
    value_str = str(value)
    
    # Detectar path traversal
    for peligroso in CARACTERES_PELIGROSOS:
        if peligroso in value_str:
            raise ValidationError(
                f'ISS-006: Ruta de archivo inválida. Caracteres no permitidos detectados.'
            )
    
    # No permitir rutas absolutas
    if value_str.startswith('/') or (len(value_str) > 1 and value_str[1] == ':'):
        raise ValidationError(
            f'ISS-006: No se permiten rutas absolutas para archivos de firma.'
        )
    
    # Validar extensión
    ext = os.path.splitext(value_str)[1].lower()
    if ext and ext not in EXTENSIONES_PERMITIDAS:
        raise ValidationError(
            f'ISS-006: Extensión de archivo no permitida: {ext}. '
            f'Extensiones válidas: {", ".join(EXTENSIONES_PERMITIDAS)}'
        )


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
            # Permisos flujo V2 - CENTRO NO CONFIRMA NADA (automático al surtir)
            'perm_crear_requisicion': True, 'perm_autorizar_admin': False,
            'perm_autorizar_director': False, 'perm_recibir_farmacia': False,
            'perm_autorizar_farmacia': False, 'perm_surtir': False, 'perm_confirmar_entrega': False,
        },
        'administrador_centro': {
            'perm_dashboard': True, 'perm_productos': True, 'perm_lotes': False,
            'perm_requisiciones': True, 'perm_centros': False, 'perm_usuarios': False,
            'perm_reportes': False, 'perm_trazabilidad': False, 'perm_auditoria': False,  # ISS-FIX: Centro NO ve reportes/trazabilidad
            'perm_notificaciones': True, 'perm_movimientos': False, 'perm_donaciones': False,
            # Permisos flujo V2 - CENTRO NO CONFIRMA NADA (automático al surtir)
            'perm_crear_requisicion': False, 'perm_autorizar_admin': True,
            'perm_autorizar_director': False, 'perm_recibir_farmacia': False,
            'perm_autorizar_farmacia': False, 'perm_surtir': False, 'perm_confirmar_entrega': False,
        },
        'director_centro': {
            'perm_dashboard': True, 'perm_productos': True, 'perm_lotes': False,
            'perm_requisiciones': True, 'perm_centros': False, 'perm_usuarios': False,
            'perm_reportes': False, 'perm_trazabilidad': False, 'perm_auditoria': False,  # ISS-FIX: Centro NO ve reportes/trazabilidad
            'perm_notificaciones': True, 'perm_movimientos': False, 'perm_donaciones': False,
            # Permisos flujo V2 - CENTRO NO CONFIRMA NADA (automático al surtir)
            'perm_crear_requisicion': False, 'perm_autorizar_admin': False,
            'perm_autorizar_director': True, 'perm_recibir_farmacia': False,
            'perm_autorizar_farmacia': False, 'perm_surtir': False, 'perm_confirmar_entrega': False,
        },
        'centro': {
            'perm_dashboard': True, 'perm_productos': True, 'perm_lotes': True,
            'perm_requisiciones': True, 'perm_centros': False, 'perm_usuarios': False,
            'perm_reportes': False, 'perm_trazabilidad': False, 'perm_auditoria': False,  # ISS-FIX: Centro NO ve reportes/trazabilidad
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
            'perm_reportes': False, 'perm_trazabilidad': False, 'perm_auditoria': False,  # ISS-FIX: Centro NO ve reportes/trazabilidad
            'perm_notificaciones': True, 'perm_movimientos': True, 'perm_donaciones': True,
            # CENTRO NO CONFIRMA NADA (automático al surtir por farmacia)
            'perm_crear_requisicion': True, 'perm_autorizar_admin': False,
            'perm_autorizar_director': False, 'perm_recibir_farmacia': False,
            'perm_autorizar_farmacia': False, 'perm_surtir': False, 'perm_confirmar_entrega': False,
        },
        'usuario_normal': {
            'perm_dashboard': True, 'perm_productos': True, 'perm_lotes': False,
            'perm_requisiciones': True, 'perm_centros': False, 'perm_usuarios': False,
            'perm_reportes': False, 'perm_trazabilidad': False, 'perm_auditoria': False,
            'perm_notificaciones': True, 'perm_movimientos': False, 'perm_donaciones': False,
            # CENTRO NO CONFIRMA NADA (automático al surtir por farmacia)
            'perm_crear_requisicion': True, 'perm_autorizar_admin': False,
            'perm_autorizar_director': False, 'perm_recibir_farmacia': False,
            'perm_autorizar_farmacia': False, 'perm_surtir': False, 'perm_confirmar_entrega': False,
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
    # Campo 'activo' requerido para compatibilidad con tabla usuarios en BD
    activo = models.BooleanField(default=True, help_text="Usuario activo (compatibilidad con BD)")
    
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

    def save(self, *args, **kwargs):
        """
        ISS-001 FIX (audit13): Forzar validación de permisos al guardar.
        
        IMPORTANTE: Como managed=False, no hay constraints de BD.
        Este save() garantiza que clean() SIEMPRE se ejecute, previniendo
        escalada de privilegios vía ORM o scripts.
        
        Args:
            skip_validation: bool - Solo permitido en DEBUG, con warning.
        """
        skip_validation = kwargs.pop('skip_validation', False)
        
        if skip_validation:
            from django.conf import settings
            import traceback
            if not getattr(settings, 'DEBUG', False):
                logger.warning(
                    f"ISS-001: skip_validation ignorado en producción para User {self.username}"
                )
                skip_validation = False
            else:
                logger.warning(
                    f"ISS-001: skip_validation usado en DEBUG para User {self.username}. "
                    f"Stack trace: {''.join(traceback.format_stack()[-3:-1])}"
                )
        
        if not skip_validation:
            # Ejecutar full_clean() que incluye clean() con validación de permisos
            try:
                self.full_clean()
            except ValidationError as e:
                logger.error(
                    f"ISS-001: Validación fallida para User {self.username}: {e.message_dict if hasattr(e, 'message_dict') else e}"
                )
                raise
        
        super().save(*args, **kwargs)

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
    nombre_comercial = models.CharField(max_length=200, blank=True, null=True)  # Nombre comercial del producto (ej: Tylenol, Aspirina)
    descripcion = models.TextField(blank=True, null=True)
    # ISS-FIX: max_length ampliado para soportar textos como "CAJA CON 7 OVULOS"
    unidad_medida = models.CharField(max_length=100, default='PIEZA')
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
    
    def get_stock_actual(self, centro=None, use_cache=False, cache_timeout=60):
        """
        ISS-001 FIX (audit11): Calcula el stock actual sumando lotes disponibles.
        ISS-007 FIX (audit11): Soporte para caching opcional.
        ISS-004 FIX (audit19): Maneja fecha_caducidad null (lotes sin caducidad).
        
        SOLO cuenta lotes con estado 'disponible', activos y no vencidos.
        Excluye lotes bloqueados, retirados, vencidos o agotados.
        Lotes SIN fecha de caducidad se consideran vigentes (según regla de negocio).
        
        Args:
            centro: Filtrar por centro específico (None = todos)
            use_cache: Si True, usa cache de Django (default False para transacciones)
            cache_timeout: Tiempo de cache en segundos (default 60)
        """
        from django.db.models import Sum, Q
        from django.utils import timezone
        from django.core.cache import cache
        
        # ISS-007 FIX (audit11): Caching opcional para reportes/vistas
        if use_cache:
            centro_key = centro.id if hasattr(centro, 'id') else (centro or 'all')
            cache_key = f'stock_producto_{self.id}_{centro_key}'
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        hoy = timezone.now().date()
        
        # ISS-004 FIX (audit19): Usar Q objects para manejar caducidad null
        # Lotes sin fecha_caducidad se consideran vigentes
        filtro_caducidad = Q(fecha_caducidad__gte=hoy) | Q(fecha_caducidad__isnull=True)
        
        filtros = Q(activo=True) & Q(cantidad_actual__gt=0) & filtro_caducidad
        
        if centro and centro != 'todos':
            filtros &= Q(centro=centro)
        
        result = self.lotes.filter(filtros).aggregate(
            total=Sum('cantidad_actual')
        )['total'] or 0
        
        # ISS-007 FIX: Guardar en cache si se solicitó
        if use_cache:
            cache.set(cache_key, result, cache_timeout)
        
        return result
    
    def get_stock_farmacia_central(self, solo_vigentes=True, use_cache=False, cache_timeout=60):
        """
        ISS-001 FIX (audit11): Calcula stock disponible en farmacia central.
        ISS-007 FIX (audit11): Soporte para caching opcional.
        ISS-004 FIX (audit19): Maneja fecha_caducidad null.
        
        SOLO cuenta lotes con estado 'disponible', activos y no vencidos.
        Excluye lotes bloqueados, retirados, vencidos o agotados.
        Lotes SIN fecha de caducidad se consideran vigentes.
        
        Args:
            solo_vigentes: Si True, excluye lotes vencidos (default True)
            use_cache: Si True, usa cache de Django (default False)
            cache_timeout: Tiempo de cache en segundos (default 60)
            
        Returns:
            int: Stock disponible
        """
        from django.db.models import Sum, Q
        from django.utils import timezone
        from django.core.cache import cache
        
        # ISS-007 FIX (audit11): Caching opcional
        if use_cache:
            cache_key = f'stock_farmacia_central_{self.id}_{solo_vigentes}'
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        hoy = timezone.now().date()
        
        # ISS-004 FIX (audit19): Usar Q objects para filtros complejos
        filtros = Q(activo=True) & Q(centro__isnull=True) & Q(cantidad_actual__gt=0)
        
        if solo_vigentes:
            # Lotes sin fecha_caducidad se consideran vigentes
            filtros &= Q(fecha_caducidad__gte=hoy) | Q(fecha_caducidad__isnull=True)
        
        result = self.lotes.filter(filtros).aggregate(
            total=Sum('cantidad_actual')
        )['total'] or 0
        
        if use_cache:
            cache.set(cache_key, result, cache_timeout)
        
        return result
    
    def get_stock_centro(self, centro, solo_vigentes=True, use_cache=False, cache_timeout=60):
        """
        ISS-001 FIX (audit11): Calcula stock disponible en un centro específico.
        ISS-007 FIX (audit11): Soporte para caching opcional.
        ISS-004 FIX (audit19): Maneja fecha_caducidad null.
        
        SOLO cuenta lotes con estado 'disponible', activos y no vencidos.
        Excluye lotes bloqueados, retirados, vencidos o agotados.
        Lotes SIN fecha de caducidad se consideran vigentes.
        
        Args:
            centro: Instancia o ID del centro
            solo_vigentes: Si True, excluye lotes vencidos (default True)
            use_cache: Si True, usa cache de Django (default False)
            cache_timeout: Tiempo de cache en segundos (default 60)
            
        Returns:
            int: Stock disponible
        """
        from django.db.models import Sum, Q
        from django.utils import timezone
        from django.core.cache import cache
        
        centro_id = centro.id if hasattr(centro, 'id') else centro
        
        # ISS-007 FIX (audit11): Caching opcional
        if use_cache:
            cache_key = f'stock_centro_{self.id}_{centro_id}_{solo_vigentes}'
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        hoy = timezone.now().date()
        
        # ISS-004 FIX (audit19): Usar Q objects para filtros complejos
        filtros = Q(activo=True) & Q(centro_id=centro_id) & Q(cantidad_actual__gt=0)
        
        if solo_vigentes:
            # Lotes sin fecha_caducidad se consideran vigentes
            filtros &= Q(fecha_caducidad__gte=hoy) | Q(fecha_caducidad__isnull=True)
        
        result = self.lotes.filter(filtros).aggregate(
            total=Sum('cantidad_actual')
        )['total'] or 0
        
        if use_cache:
            cache.set(cache_key, result, cache_timeout)
        
        return result
    
    def get_lotes_disponibles_farmacia(self):
        """
        ISS-001 FIX (audit11): Retorna lotes disponibles para surtido en farmacia central.
        Ordenados por fecha de caducidad (FEFO - First Expired, First Out).
        
        SOLO retorna lotes con estado 'disponible', activos y no vencidos.
        """
        from django.utils import timezone
        
        return self.lotes.filter(
            activo=True,
            centro__isnull=True,
            cantidad_actual__gt=0,
            fecha_caducidad__gte=timezone.now().date(),
            # ISS-004 FIX (audit14): No usar estado__in, campo no existe en BD
        ).order_by('fecha_caducidad')
    
    def get_stock_global(self, solo_vigentes=True, use_cache=False, cache_timeout=60):
        """
        ISS-002/ISS-004 FIX: Calcula stock total de todos los lotes (farmacia + centros).
        
        Útil para reportes globales de inventario, pero NO debe usarse
        para validar disponibilidad de requisiciones (usar get_stock_farmacia_central).
        
        Args:
            solo_vigentes: Si True, excluye lotes vencidos (default True)
            use_cache: Si True, usa cache de Django (default False)
            cache_timeout: Tiempo de cache en segundos (default 60)
            
        Returns:
            int: Stock total disponible
        """
        from django.db.models import Sum
        from django.utils import timezone
        from django.core.cache import cache
        
        if use_cache:
            cache_key = f'stock_global_{self.id}_{solo_vigentes}'
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        filtros = {
            'activo': True,
            'cantidad_actual__gt': 0,
        }
        
        if solo_vigentes:
            filtros['fecha_caducidad__gte'] = timezone.now().date()
        
        result = self.lotes.filter(**filtros).aggregate(
            total=Sum('cantidad_actual')
        )['total'] or 0
        
        if use_cache:
            cache.set(cache_key, result, cache_timeout)
        
        return result
    
    def get_nivel_stock(self, centro=None):
        """
        ISS-004 FIX: Retorna el nivel de stock: critico, bajo, normal, alto.
        
        Args:
            centro: Centro específico para calcular nivel (None = farmacia central)
            
        Returns:
            str: 'critico', 'bajo', 'normal', o 'alto'
        """
        if centro:
            stock = self.get_stock_centro(centro)
        else:
            stock = self.get_stock_farmacia_central()
        
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
    
    ISS-001: Validaciones de negocio implementadas:
    - fecha_caducidad debe ser posterior a fecha_fabricacion
    - cantidad_inicial y cantidad_actual deben ser >= 0
    - fecha_caducidad no puede ser anterior a la fecha actual para lotes nuevos
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
        # ISS-FIX: Incluir centro en unique_together para permitir mismo lote en diferentes centros
        unique_together = [['numero_lote', 'producto', 'centro']]

    def __str__(self):
        return f"{self.numero_lote} - {self.producto}"
    
    def clean(self):
        """
        ISS-001: Validaciones de negocio para lotes.
        Se ejecutan en save() y en serializers con full_clean().
        """
        from django.core.exceptions import ValidationError
        from django.utils import timezone
        
        errors = {}
        
        # Validar cantidad_inicial no negativa
        if self.cantidad_inicial is not None and self.cantidad_inicial < 0:
            errors['cantidad_inicial'] = 'La cantidad inicial no puede ser negativa.'
        
        # Validar cantidad_actual no negativa
        if self.cantidad_actual is not None and self.cantidad_actual < 0:
            errors['cantidad_actual'] = 'La cantidad actual no puede ser negativa.'
        
        # Validar que fecha_caducidad sea posterior a fecha_fabricacion
        if self.fecha_fabricacion and self.fecha_caducidad:
            if self.fecha_caducidad <= self.fecha_fabricacion:
                errors['fecha_caducidad'] = 'La fecha de caducidad debe ser posterior a la fecha de fabricación.'
        
        # Validar que lotes nuevos no estén ya vencidos (solo en creación)
        if not self.pk and self.fecha_caducidad:  # Solo para nuevos registros
            hoy = timezone.now().date()
            if self.fecha_caducidad < hoy:
                errors['fecha_caducidad'] = f'No se puede registrar un lote ya vencido (caducidad: {self.fecha_caducidad}, hoy: {hoy}).'
        
        # Validar precio unitario no negativo
        if self.precio_unitario is not None and self.precio_unitario < 0:
            errors['precio_unitario'] = 'El precio unitario no puede ser negativo.'
        
        # ISS-006: Advertencia si no tiene contrato (solo warning, no bloquea)
        # La validación estricta de contrato se hace en el serializer donde podemos
        # acceder a reglas de negocio más complejas
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """
        ISS-001/ISS-002 FIX (audit12): Ejecutar validaciones antes de guardar.
        
        El parámetro skip_validation SOLO debe usarse en:
        - Migraciones de datos controladas
        - Scripts de mantenimiento con supervisión
        
        NUNCA en producción para operaciones regulares.
        """
        from django.conf import settings
        
        skip_validation = kwargs.pop('skip_validation', False)
        
        # ISS-002 FIX (audit12): Registrar uso de skip_validation
        # ISS-001 FIX (audit19): Usar campos reales, no property 'estado' 
        if skip_validation:
            if not getattr(settings, 'DEBUG', False):
                logger = logging.getLogger(__name__)
                logger.critical(
                    f"ISS-002 ALERTA: skip_validation usado en PRODUCCIÓN para Lote. "
                    f"ID: {self.pk}, Producto: {self.producto_id}, Activo: {self.activo}, "
                    f"Cantidad: {self.cantidad_actual}. Revisar trazabilidad."
                )
        
        if not skip_validation:
            self.full_clean()
        super().save(*args, **kwargs)
    
    def validar_contrato(self, cantidad_a_ingresar=None, strict=False, es_entrada_formal=False):
        """
        ISS-003 FIX (audit15): Valida reglas de contrato para el lote.
        
        Args:
            cantidad_a_ingresar: Cantidad adicional que se pretende ingresar
            strict: Si True, convierte advertencias críticas en errores bloqueantes
            es_entrada_formal: Si True, exige número de contrato
            
        Returns:
            dict: {valido: bool, errores: list, advertencias: list, bloqueante: bool}
        """
        from core.lote_helpers import ContratoValidator
        
        # Delegar a ContratoValidator para validación completa
        resultado = ContratoValidator.validar_entrada_contrato(
            lote=self,
            cantidad_a_ingresar=cantidad_a_ingresar or 0,
            contrato=None,  # Se buscaría por numero_contrato si existiera modelo Contrato
            es_entrada_formal=es_entrada_formal,
            strict=strict,
        )
        
        return {
            'valido': resultado['valido'],
            'errores': resultado['errores'],
            'advertencias': resultado['advertencias'],
            'bloqueante': resultado.get('bloqueante', False),
        }
    
    def esta_vencido(self):
        """ISS-001: Verifica si el lote ya venció."""
        from django.utils import timezone
        if not self.fecha_caducidad:
            return False
        return self.fecha_caducidad < timezone.now().date()
    
    def esta_disponible_para_surtido(self):
        """
        ISS-001: Verifica si el lote puede usarse para surtir.
        Debe estar activo, con stock disponible y no vencido.
        """
        return (
            self.activo and 
            self.cantidad_actual > 0 and 
            not self.esta_vencido()
        )
    
    @property
    def precio_compra(self):
        return self.precio_unitario
    
    @property
    def estado(self):
        """
        ISS-003 FIX: Propiedad calculada que determina el estado real del lote.
        
        Considera:
        - activo: Si el lote está activo en el sistema
        - fecha_caducidad: Si el lote está vencido
        - cantidad_actual: Si el lote tiene existencias
        
        Estados posibles:
        - 'vencido': Fecha de caducidad pasada
        - 'agotado': cantidad_actual <= 0 o activo=False
        - 'disponible': Activo, con stock y no vencido
        """
        from django.utils import timezone
        
        # Primero verificar si está inactivo
        if not self.activo:
            return 'agotado'
        
        # Verificar si está vencido
        if self.fecha_caducidad:
            hoy = timezone.now().date()
            if self.fecha_caducidad < hoy:
                return 'vencido'
        
        # Verificar si está agotado
        if self.cantidad_actual is None or self.cantidad_actual <= 0:
            return 'agotado'
        
        # Si pasa todas las validaciones, está disponible
        return 'disponible'

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
        Alineado con clasificación SIFP y Serializer:
        
        Retorna:
            - 'vencido': Ya caducó (< 0 días)
            - 'critico': Caduca en menos de 3 meses (< 90 días)
            - 'proximo': Caduca en 3-6 meses (90-180 días)
            - 'normal': Más de 6 meses para caducar (> 180 días)
        """
        dias = self.dias_para_caducar()
        if dias < 0:
            return 'vencido'
        elif dias < 90:
            return 'critico'
        elif dias < 180:
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
    
    ISS-002: Validaciones de negocio implementadas:
    - Validar signo de cantidad según tipo de movimiento
    - Validar stock suficiente antes de restar (salidas, mermas, etc.)
    - Exigir lote para tipos que lo requieren
    - Verificar que lotes no estén vencidos para salidas
    """
    
    # Tipos que RESTAN stock (cantidad debe ser positiva, se resta del inventario)
    # ISS-FIX: Agregar 'ajuste' genérico que se usa en salidas manuales
    TIPOS_RESTA_STOCK = ['salida', 'ajuste', 'ajuste_negativo', 'merma', 'caducidad', 'transferencia']
    # Tipos que SUMAN stock (cantidad debe ser positiva, se suma al inventario)
    TIPOS_SUMA_STOCK = ['entrada', 'ajuste_positivo', 'devolucion']
    # Tipos que REQUIEREN lote obligatorio
    TIPOS_REQUIERE_LOTE = ['salida', 'ajuste', 'merma', 'caducidad', 'transferencia']
    # Tipos válidos
    # ISS-FIX: Agregar 'ajuste' genérico para compatibilidad con registrar_movimiento_stock
    TIPOS_VALIDOS = ['entrada', 'salida', 'ajuste', 'transferencia', 'ajuste_positivo', 'ajuste_negativo', 'devolucion', 'merma', 'caducidad']
    
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
    # FORMATO OFICIAL B: Folio/número de documento de entrada/salida para trazabilidad oficial
    folio_documento = models.CharField(max_length=100, blank=True, null=True, db_column='folio_documento')
    fecha = models.DateTimeField(auto_now_add=True)  # BD default: now()
    created_at = models.DateTimeField(auto_now_add=True)  # BD default: now()

    class Meta:
        db_table = 'movimientos'
        ordering = ['-fecha']
        managed = False  # La tabla ya existe en la BD

    def __str__(self):
        return f"{self.tipo} - {self.cantidad} - {self.fecha}"
    
    def clean(self):
        """
        ISS-002: Validaciones de negocio para movimientos.
        """
        from django.core.exceptions import ValidationError
        
        errors = {}
        tipo = (self.tipo or '').lower()
        
        # Validar tipo de movimiento válido
        if tipo and tipo not in self.TIPOS_VALIDOS:
            errors['tipo'] = f'Tipo de movimiento inválido: {tipo}. Tipos válidos: {", ".join(self.TIPOS_VALIDOS)}'
        
        # ISS-MEDICO FIX v2: La cantidad se almacena con signo según el tipo de movimiento
        # - Salidas se almacenan como negativos (representan reducción de stock)
        # - Entradas se almacenan como positivos (representan aumento de stock)
        # La validación debe verificar coherencia entre tipo y signo, no exigir siempre positivo
        if self.cantidad is not None and self.cantidad == 0:
            errors['cantidad'] = 'La cantidad no puede ser cero.'
        
        # Validar coherencia tipo-signo
        if self.cantidad is not None and tipo in self.TIPOS_RESTA_STOCK:
            # Para tipos que restan, la cantidad debe ser negativa o se convertirá
            pass  # registrar_movimiento_stock maneja la conversión
        elif self.cantidad is not None and tipo in self.TIPOS_SUMA_STOCK:
            # Para tipos que suman, la cantidad debe ser positiva
            if self.cantidad < 0:
                errors['cantidad'] = f'Las {tipo}s deben tener cantidad positiva.'
        
        # Validar lote obligatorio para tipos que lo requieren
        if tipo in self.TIPOS_REQUIERE_LOTE and not self.lote_id:
            errors['lote'] = f'El tipo de movimiento "{tipo}" requiere especificar un lote.'
        
        # Validar que el lote no esté vencido para salidas
        if self.lote and tipo in self.TIPOS_RESTA_STOCK:
            if hasattr(self.lote, 'esta_vencido') and self.lote.esta_vencido():
                errors['lote'] = f'No se puede usar el lote {self.lote.numero_lote} porque está vencido.'
        
        # Validar stock suficiente para tipos que restan
        # ISS-001 FIX (audit20): Validar stock considerando el centro
        # ISS-FIX: Si _stock_pre_movimiento está definido, usar ese valor en lugar de
        # lote.cantidad_actual, porque el stock ya fue descontado por RequisicionService
        if tipo in self.TIPOS_RESTA_STOCK and self.lote and self.cantidad:
            stock_a_validar = getattr(self, '_stock_pre_movimiento', None)
            if stock_a_validar is None:
                stock_a_validar = self.lote.cantidad_actual
            if stock_a_validar < self.cantidad:
                errors['cantidad'] = (
                    f'Stock insuficiente en lote {self.lote.numero_lote}. '
                    f'Disponible: {stock_a_validar}, Solicitado: {self.cantidad}'
                )
            # ISS-001 FIX (audit20): Validar que el lote esté en el centro origen para salidas
            if tipo == 'salida' and self.centro_origen_id and self.lote.centro_id:
                if self.lote.centro_id != self.centro_origen_id:
                    errors['lote'] = (
                        f'El lote {self.lote.numero_lote} no está en el centro de origen. '
                        f'Lote en centro ID: {self.lote.centro_id}, Origen: {self.centro_origen_id}'
                    )
        
        # Validar expediente obligatorio para salidas por receta
        if self.subtipo_salida == 'receta' and not self.numero_expediente:
            errors['numero_expediente'] = 'El número de expediente es obligatorio para salidas por receta médica.'
        
        # Validar que transferencias tengan centro origen y destino
        if tipo == 'transferencia':
            if not self.centro_origen_id:
                errors['centro_origen'] = 'Las transferencias requieren un centro de origen.'
            if not self.centro_destino_id:
                errors['centro_destino'] = 'Las transferencias requieren un centro de destino.'
            if self.centro_origen_id and self.centro_destino_id and self.centro_origen_id == self.centro_destino_id:
                errors['centro_destino'] = 'El centro de destino debe ser diferente al centro de origen.'
            
            # ISS-004 FIX (audit14): Validar lote activo y con stock para transferencias
            # NOTA: La BD no tiene campo 'estado' en lotes, usar activo + cantidad + fecha
            if self.lote:
                if not self.lote.activo:
                    errors['lote'] = (
                        f'No se puede transferir del lote {self.lote.numero_lote} '
                        f'porque está inactivo.'
                    )
                
                from django.utils import timezone
                if self.lote.fecha_caducidad and self.lote.fecha_caducidad < timezone.now().date():
                    errors['lote'] = (
                        f'No se puede transferir del lote {self.lote.numero_lote} '
                        f'porque está vencido (caducidad: {self.lote.fecha_caducidad}).'
                    )
                
                # ISS-004 FIX (audit12): Validar que el lote pertenezca al centro origen
                if self.lote.centro_id and self.centro_origen_id:
                    if self.lote.centro_id != self.centro_origen_id:
                        errors['lote'] = (
                            f'El lote {self.lote.numero_lote} no pertenece al centro de origen. '
                            f'Lote en centro: {self.lote.centro_id}, Origen indicado: {self.centro_origen_id}'
                        )
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """
        ISS-002 FIX (audit12): Ejecutar validaciones antes de guardar.
        
        NOTA: Para operaciones atómicas con actualización de stock,
        usar RequisicionService que maneja transacciones completas.
        
        El parámetro skip_validation SOLO debe usarse en:
        - Migraciones de datos controladas
        - Scripts de mantenimiento con supervisión
        - Tests con datos ficticios
        
        NUNCA en producción para operaciones regulares.
        """
        from django.conf import settings
        
        skip_validation = kwargs.pop('skip_validation', False)
        
        # ISS-002 FIX (audit12): Restringir skip_validation a DEBUG o forzar log de alerta
        if skip_validation:
            if not getattr(settings, 'DEBUG', False):
                # En producción: registrar alerta CRÍTICA pero permitir (para migraciones)
                logger = logging.getLogger(__name__)
                logger.critical(
                    f"ISS-002 ALERTA: skip_validation usado en PRODUCCIÓN para Movimiento. "
                    f"Lote: {self.lote_id}, Tipo: {self.tipo}, Cantidad: {self.cantidad}, "
                    f"Centro: {self.centro_id}. Revisar trazabilidad."
                )
            else:
                # En desarrollo: solo warning
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"ISS-002: skip_validation usado para Movimiento "
                    f"(lote={self.lote_id}, tipo={self.tipo})"
                )
        
        if not skip_validation:
            self.full_clean()
        super().save(*args, **kwargs)
    
    def aplicar_movimiento_a_lote(self, revalidar_stock=True):
        """
        ISS-001 FIX (audit14): Aplica el efecto del movimiento al stock del lote.
        
        IMPORTANTE: Esta operación DEBE ejecutarse dentro de una transacción atómica
        con select_for_update() aplicado al lote.
        
        ISS-001: Revalida stock justo antes de modificar para evitar race conditions.
        Si otro proceso modificó el stock entre clean() y este método, se detectará.
        
        Args:
            revalidar_stock: Si True, revalida que haya stock suficiente (default True).
                            Solo pasar False en migraciones controladas.
        
        Raises:
            ValidationError: Si no hay stock suficiente al revalidar
        """
        from django.core.exceptions import ValidationError
        from django.db import transaction
        
        if not self.lote:
            return
        
        tipo = (self.tipo or '').lower()
        
        # ISS-001 FIX: Usar select_for_update para bloqueo real
        # Esto evita que otra transacción modifique el lote simultáneamente
        with transaction.atomic():
            # Re-obtener lote con lock exclusivo
            lote_bloqueado = Lote.objects.select_for_update().get(pk=self.lote.pk)
            
            # ISS-001 FIX: Revalidar stock DESPUÉS de obtener el lock
            # Esto detecta cambios concurrentes que ocurrieron entre clean() y ahora
            if revalidar_stock and tipo in self.TIPOS_RESTA_STOCK:
                if lote_bloqueado.cantidad_actual < self.cantidad:
                    raise ValidationError({
                        'cantidad': (
                            f'ISS-001: Stock insuficiente al aplicar movimiento. '
                            f'Lote {lote_bloqueado.numero_lote}: '
                            f'disponible={lote_bloqueado.cantidad_actual}, '
                            f'requerido={self.cantidad}. '
                            f'Posible modificación concurrente detectada.'
                        )
                    })
            
            # HALLAZGO #4: Aplicar el cambio de stock de forma atómica usando F()
            # Esto previene race conditions en operaciones concurrentes
            from django.db.models import F
            
            if tipo in self.TIPOS_RESTA_STOCK:
                Lote.objects.filter(pk=lote_bloqueado.pk).update(
                    cantidad_actual=F('cantidad_actual') - self.cantidad
                )
            elif tipo in self.TIPOS_SUMA_STOCK:
                Lote.objects.filter(pk=lote_bloqueado.pk).update(
                    cantidad_actual=F('cantidad_actual') + self.cantidad
                )
            
            # Refrescar instancia para obtener el valor actualizado
            lote_bloqueado.refresh_from_db(fields=['cantidad_actual'])
            
            # ISS-001 FIX: Validar que no quede negativo (doble check)
            if lote_bloqueado.cantidad_actual < 0:
                raise ValidationError({
                    'cantidad': (
                        f'ISS-001: Operación resultaría en stock negativo. '
                        f'Lote {lote_bloqueado.numero_lote}: resultado={lote_bloqueado.cantidad_actual}. '
                        f'Transacción cancelada.'
                    )
                })
            
            # Guardar sin re-ejecutar validaciones completas del lote
            lote_bloqueado.save(update_fields=['cantidad_actual', 'updated_at'])
            
            # Actualizar referencia local
            self.lote = lote_bloqueado
    
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
    
    ISS-001/002/003 FIX (audit8): Estados y transiciones importados desde
    core.constants como FUENTE ÚNICA DE VERDAD.
    """
    
    # ========== FLUJO V2: IMPORTAR DE CONSTANTS (FUENTE ÚNICA DE VERDAD) ==========
    # ISS-001/002/003 FIX (audit8): NO duplicar definiciones, importar desde constants
    from core.constants import (
        TRANSICIONES_REQUISICION as _TRANSICIONES,
        ESTADOS_SURTIBLES as _ESTADOS_SURTIBLES,
        ESTADOS_EDITABLES as _ESTADOS_EDITABLES,
        ESTADOS_TERMINALES as _ESTADOS_TERMINALES,
        ESTADOS_REQUIEREN_SERVICIO as _ESTADOS_REQUIEREN_SERVICIO,
    )
    
    # Exponer como atributos de clase para compatibilidad
    TRANSICIONES_VALIDAS = _TRANSICIONES
    ESTADOS_SURTIBLES = _ESTADOS_SURTIBLES
    ESTADOS_EDITABLES = _ESTADOS_EDITABLES
    ESTADOS_TERMINALES = _ESTADOS_TERMINALES
    
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
        """
        ISS-FIX: Devuelve centro_origen (el centro que HACE la requisición).
        
        IMPORTANTE: Anteriormente devolvía centro_destino que es NULL para
        requisiciones a farmacia central, causando errores de permisos.
        
        El "centro de la requisición" semánticamente es el centro que la origina.
        """
        return self.centro_origen
    
    @property
    def centro_id(self):
        """
        ISS-FIX: Alias para centro_origen_id (compatibilidad).
        
        CAMBIO: Antes devolvía centro_destino_id, ahora centro_origen_id.
        """
        return self.centro_origen_id
    
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
    
    # ========== ISS-003 FIX (audit19): Campo updated_by en memoria ==========
    # ADVERTENCIA: Este campo NO existe en la BD (managed=False).
    # Los writes a este campo NO SE PERSISTEN.
    # 
    # Se mantiene para compatibilidad con código existente que espera este campo,
    # pero se DEBE migrar a:
    # - cambiar_estado_con_historial() para cambios de estado persistidos
    # - Campos de actores específicos (surtidor, autorizador, receptor_farmacia)
    # 
    # ALTERNATIVA PERSISTIDA: Usar get_ultimo_actor_modificacion() para obtener
    # el último usuario que modificó la requisición desde el historial.
    # 
    # TODO: Deprecar en próxima versión mayor
    _updated_by = None
    
    def get_ultimo_actor_modificacion(self):
        """
        ISS-003 FIX (audit19): Obtiene el último usuario que modificó la requisición.
        
        Este método LEE desde RequisicionHistorialEstados, por lo que SÍ es persistido.
        Use este método en lugar de updated_by para auditoría confiable.
        
        Returns:
            User | None: Último usuario que modificó la requisición
        """
        ultimo_cambio = self.historial_estados.order_by('-fecha_cambio').first()
        if ultimo_cambio:
            return ultimo_cambio.usuario
        return self.solicitante  # Fallback al creador
    
    @property
    def updated_by(self):
        """
        ISS-004 FIX (audit6): Usuario que realizó la última modificación.
        
        ⚠️ ADVERTENCIA: Este campo NO se persiste en BD.
        
        Para trazabilidad que SÍ se persiste, use:
        1. cambiar_estado_con_historial() - registra en RequisicionHistorialEstados
        2. Campos de actores: surtidor, autorizador, receptor_farmacia, usuario_firma_*
        3. El servicio RequisicionService que establece campos correctamente
        
        Returns:
            User | None: Usuario en memoria (no persistido)
        """
        import warnings
        warnings.warn(
            "ISS-004: updated_by no se persiste en BD. Use campos de actores específicos.",
            DeprecationWarning,
            stacklevel=2
        )
        return self._updated_by
    
    @updated_by.setter
    def updated_by(self, value):
        """
        ISS-004 FIX (audit6): Registra el usuario que modifica (solo en memoria).
        
        ⚠️ ADVERTENCIA: Este valor NO se guardará en la BD.
        Para auditoría persistente, use los métodos del servicio RequisicionService.
        """
        import warnings
        warnings.warn(
            "ISS-004: updated_by no se persiste en BD. El valor se perderá al refrescar el objeto.",
            DeprecationWarning,
            stacklevel=2
        )
        self._updated_by = value
        # ISS-004: Log de auditoría cuando se asigna updated_by
        if value:
            logger.warning(
                f"ISS-004 AUDIT: Requisicion {self.numero} - updated_by asignado a "
                f"usuario ID={getattr(value, 'id', 'N/A')} ({getattr(value, 'username', 'N/A')}). "
                f"NOTA: Este valor NO se persistirá en BD."
            )
    
    # ========== ISS-003: MÉTODOS DE MÁQUINA DE ESTADOS ==========
    
    def puede_transicionar_a(self, nuevo_estado: str) -> bool:
        """
        ISS-003: Verifica si la transición es válida sin ejecutarla.
        
        Args:
            nuevo_estado: Estado destino
            
        Returns:
            bool: True si la transición es válida
        """
        estado_actual = (self.estado or 'borrador').lower()
        nuevo_estado = nuevo_estado.lower()
        transiciones_permitidas = self.TRANSICIONES_VALIDAS.get(estado_actual, [])
        return nuevo_estado in transiciones_permitidas
    
    def get_transiciones_disponibles(self) -> list:
        """
        ISS-003: Retorna las transiciones disponibles desde el estado actual.
        """
        estado_actual = (self.estado or 'borrador').lower()
        return self.TRANSICIONES_VALIDAS.get(estado_actual, [])
    
    def es_estado_terminal(self) -> bool:
        """ISS-003: Verifica si el estado actual es terminal."""
        estado_actual = (self.estado or 'borrador').lower()
        return estado_actual in self.ESTADOS_TERMINALES
    
    def es_editable(self) -> bool:
        """ISS-003: Verifica si la requisición puede editarse."""
        estado_actual = (self.estado or 'borrador').lower()
        return estado_actual in self.ESTADOS_EDITABLES
    
    def es_surtible(self) -> bool:
        """ISS-003: Verifica si la requisición puede surtirse."""
        estado_actual = (self.estado or 'borrador').lower()
        return estado_actual in self.ESTADOS_SURTIBLES
    
    def validar_transicion(self, nuevo_estado: str, motivo: str = None) -> list:
        """
        ISS-003: Valida una transición incluyendo reglas de negocio.
        
        Args:
            nuevo_estado: Estado destino
            motivo: Motivo (requerido para rechazos/devoluciones)
            
        Returns:
            list: Lista de errores (vacía si es válida)
        """
        from django.utils import timezone
        
        errores = []
        nuevo_estado = nuevo_estado.lower()
        estado_actual = (self.estado or 'borrador').lower()
        
        # Validar que la transición esté permitida
        if not self.puede_transicionar_a(nuevo_estado):
            transiciones = self.get_transiciones_disponibles()
            errores.append(
                f"Transición de '{estado_actual}' a '{nuevo_estado}' no permitida. "
                f"Transiciones válidas: {', '.join(transiciones) or 'ninguna'}"
            )
            return errores  # No continuar validando si la transición no es válida
        
        # Validar motivo para rechazos
        if nuevo_estado == 'rechazada':
            if not motivo or not motivo.strip():
                errores.append("Se requiere un motivo para rechazar la requisición.")
        
        # Validar motivo para devoluciones
        if nuevo_estado == 'devuelta':
            if not motivo or not motivo.strip():
                errores.append("Se requiere un motivo para devolver la requisición.")
        
        # Validar que no esté vencida antes de entregar
        if nuevo_estado == 'entregada':
            if self.fecha_recoleccion_limite:
                if timezone.now() > self.fecha_recoleccion_limite:
                    errores.append(
                        f"La fecha límite de recolección ({self.fecha_recoleccion_limite.strftime('%d/%m/%Y %H:%M')}) "
                        "ha expirado. La requisición debe marcarse como vencida."
                    )
        
        # Validar que tenga detalles antes de enviar
        if nuevo_estado in ['pendiente_admin', 'enviada']:
            if hasattr(self, 'detalles') and not self.detalles.exists():
                errores.append("La requisición debe tener al menos un producto.")
            
            # ISS-005 FIX (audit20): Validación temprana de stock al enviar
            # Esto advierte sobre posibles problemas antes de que llegue a farmacia
            if hasattr(self, 'detalles') and self.detalles.exists():
                productos_sin_stock = []
                for detalle in self.detalles.all():
                    if hasattr(detalle.producto, 'get_stock_farmacia_central'):
                        stock_disponible = detalle.producto.get_stock_farmacia_central()
                        if stock_disponible < detalle.cantidad_solicitada:
                            productos_sin_stock.append(
                                f"{detalle.producto.nombre} (disponible: {stock_disponible}, solicitado: {detalle.cantidad_solicitada})"
                            )
                
                if productos_sin_stock:
                    # Solo advertencia, no bloquea (el farmacéutico puede ajustar)
                    logger.warning(
                        f"ISS-005: Requisición {self.numero} enviada con stock insuficiente en: "
                        f"{', '.join(productos_sin_stock[:3])}{'...' if len(productos_sin_stock) > 3 else ''}"
                    )
        
        return errores
    
    # ISS-002 FIX (audit7): Estados que requieren pasar por el servicio transaccional
    # Estos estados involucran operaciones de inventario que deben ser atómicas
    ESTADOS_REQUIEREN_SERVICIO = {
        'en_surtido',  # Inicia reserva de stock
        'surtida',     # Confirma descuento de inventario
        'parcial',     # Surtido parcial con movimientos
        'entregada',   # Confirmación de entrega
    }
    
    def cambiar_estado(self, nuevo_estado: str, usuario=None, motivo: str = None, 
                       validar: bool = True, forzar_modelo: bool = False):
        """
        ISS-002 FIX (audit7): Cambia el estado de la requisición con validaciones.
        
        IMPORTANTE: Las transiciones a estados de inventario (en_surtido, surtida, parcial, 
        entregada) DEBEN usar el servicio transaccional RequisicionService para garantizar
        atomicidad y validación de stock. Este método bloqueará dichos cambios a menos 
        que se use forzar_modelo=True (solo para migraciones/scripts administrativos).
        
        Args:
            nuevo_estado: Estado destino
            usuario: Usuario que realiza la transición
            motivo: Motivo (para rechazos/devoluciones)
            validar: Si se deben ejecutar las validaciones básicas
            forzar_modelo: Si True, permite cambios directos (solo admin/scripts)
            
        Raises:
            ValidationError: Si la transición no es válida o requiere servicio
        """
        from django.core.exceptions import ValidationError
        from django.utils import timezone
        
        nuevo_estado = nuevo_estado.lower()
        
        # ISS-002 FIX: Bloquear cambios a estados de inventario desde el modelo
        if nuevo_estado in self.ESTADOS_REQUIEREN_SERVICIO and not forzar_modelo:
            raise ValidationError({
                'estado': [
                    f"La transición a '{nuevo_estado}' requiere operaciones de inventario. "
                    f"Use el servicio transaccional RequisicionService en lugar de cambiar "
                    f"el estado directamente en el modelo. Esto garantiza validación de stock, "
                    f"atomicidad y trazabilidad completa."
                ]
            })
        
        # Validar transición básica
        if validar:
            errores = self.validar_transicion(nuevo_estado, motivo)
            if errores:
                raise ValidationError({'estado': errores})
        
        estado_anterior = self.estado
        self.estado = nuevo_estado
        
        # Registrar campos según el nuevo estado
        if nuevo_estado == 'rechazada' and motivo:
            self.motivo_rechazo = motivo
        elif nuevo_estado == 'devuelta' and motivo:
            self.motivo_devolucion = motivo
        elif nuevo_estado == 'vencida':
            self.fecha_vencimiento = timezone.now()
            if motivo:
                self.motivo_vencimiento = motivo
        
        # Registrar timestamp de la transición
        if nuevo_estado == 'pendiente_admin':
            self.fecha_envio_admin = timezone.now()
        elif nuevo_estado == 'pendiente_director':
            self.fecha_autorizacion_admin = timezone.now()
            self.fecha_envio_director = timezone.now()
            if usuario:
                self.administrador_centro = usuario
        elif nuevo_estado == 'enviada':
            self.fecha_autorizacion_director = timezone.now()
            self.fecha_envio_farmacia = timezone.now()
            if usuario:
                self.director_centro = usuario
        elif nuevo_estado == 'en_revision':
            self.fecha_recepcion_farmacia = timezone.now()
            if usuario:
                self.receptor_farmacia = usuario
        elif nuevo_estado == 'autorizada':
            self.fecha_autorizacion_farmacia = timezone.now()
            self.fecha_autorizacion = timezone.now()
            if usuario:
                self.autorizador_farmacia = usuario
                self.autorizador = usuario
        elif nuevo_estado == 'surtida':
            self.fecha_surtido = timezone.now()
            if usuario:
                self.surtidor = usuario
        elif nuevo_estado == 'entregada':
            self.fecha_entrega = timezone.now()
            self.fecha_firma_recepcion = timezone.now()
            if usuario:
                self.usuario_firma_recepcion = usuario
        
        return estado_anterior
    
    def registrar_cambio_estado(self, estado_anterior: str, estado_nuevo: str, 
                                 usuario=None, accion: str = None, motivo: str = None,
                                 ip_address: str = None, datos_adicionales: dict = None):
        """
        ISS-007: Registra un cambio de estado en el historial de la requisición.
        
        Args:
            estado_anterior: Estado antes del cambio
            estado_nuevo: Estado después del cambio
            usuario: Usuario que realizó el cambio
            accion: Tipo de acción (autorizar, rechazar, etc.)
            motivo: Razón del cambio
            ip_address: IP desde donde se realizó
            datos_adicionales: Contexto extra (JSON)
        """
        from django.utils import timezone
        
        # Importar modelo de historial
        try:
            RequisicionHistorialEstados.objects.create(
                requisicion=self,
                estado_anterior=estado_anterior,
                estado_nuevo=estado_nuevo,
                usuario=usuario,
                accion=accion or f"{estado_anterior}_a_{estado_nuevo}",
                motivo=motivo or '',
                ip_address=ip_address or '',
                datos_adicionales=datos_adicionales or {},
                fecha_cambio=timezone.now()
            )
        except Exception as e:
            # Log error pero no fallar la operación principal
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error registrando historial de requisición {self.numero}: {e}")
    
    def cambiar_estado_con_historial(self, nuevo_estado: str, usuario=None, 
                                      motivo: str = None, ip_address: str = None,
                                      datos_adicionales: dict = None, validar: bool = True):
        """
        ISS-007: Cambia el estado y registra en historial automáticamente.
        
        Args:
            nuevo_estado: Estado destino
            usuario: Usuario que realiza la transición
            motivo: Motivo del cambio
            ip_address: IP de la solicitud
            datos_adicionales: Datos extra para auditoría
            validar: Si se deben ejecutar las validaciones
            
        Returns:
            str: Estado anterior
            
        Raises:
            ValidationError: Si la transición no es válida
        """
        estado_anterior = self.estado
        
        # Ejecutar cambio de estado con validaciones
        self.cambiar_estado(nuevo_estado, usuario, motivo, validar)
        
        # Determinar acción según el estado nuevo
        acciones_map = {
            'pendiente_admin': 'enviar_admin',
            'pendiente_director': 'autorizar_admin',
            'enviada': 'autorizar_director',
            'en_revision': 'recibir_farmacia',
            'autorizada': 'autorizar_farmacia',
            'en_surtido': 'iniciar_surtido',
            'surtida': 'surtir',
            'entregada': 'entregar',
            'rechazada': 'rechazar',
            'devuelta': 'devolver',
            'vencida': 'marcar_vencida',
            'cancelada': 'cancelar',
        }
        accion = acciones_map.get(nuevo_estado, f"cambiar_a_{nuevo_estado}")
        
        # Registrar en historial
        self.registrar_cambio_estado(
            estado_anterior=estado_anterior,
            estado_nuevo=nuevo_estado,
            usuario=usuario,
            accion=accion,
            motivo=motivo,
            ip_address=ip_address,
            datos_adicionales=datos_adicionales
        )
        
        return estado_anterior

    def clean(self):
        """
        ISS-003 FIX (audit14): Validaciones de negocio para requisiciones.
        ISS-006 FIX: Validación de rutas de archivos de firma.
        
        Valida:
        - Estado válido según máquina de estados
        - Campos obligatorios por estado
        - Coherencia de fechas
        - Rutas de archivos de firma seguras
        """
        from django.core.exceptions import ValidationError
        from django.utils import timezone
        
        errors = {}
        estado = (self.estado or 'borrador').lower()
        
        # Lista de estados válidos
        estados_validos = list(self.TRANSICIONES_VALIDAS.keys()) + list(self.ESTADOS_TERMINALES)
        if estado not in estados_validos:
            errors['estado'] = f'Estado "{estado}" no es válido. Estados válidos: {", ".join(estados_validos)}'
        
        # Validar campos obligatorios según estado
        if estado not in ['borrador', 'devuelta']:
            if not self.centro_destino_id and not self.centro_origen_id:
                errors['centro_origen'] = 'La requisición debe tener al menos un centro asignado.'
        
        # Validar solicitante para estados avanzados
        if estado not in ['borrador']:
            if not self.solicitante_id:
                errors['solicitante'] = 'La requisición debe tener un solicitante asignado.'
        
        # Validar autorizador para estado autorizada
        if estado == 'autorizada' and not self.autorizador_id:
            errors['autorizador'] = 'Las requisiciones autorizadas deben tener un autorizador asignado.'
        
        # Validar que requisiciones terminales tengan fecha de término
        if estado in ['surtida', 'entregada'] and not self.fecha_surtido:
            errors['fecha_surtido'] = f'Las requisiciones en estado "{estado}" deben tener fecha de surtido.'
        
        # Validar coherencia de fechas
        if self.fecha_autorizacion and self.fecha_solicitud:
            if self.fecha_autorizacion < self.fecha_solicitud:
                errors['fecha_autorizacion'] = 'La fecha de autorización no puede ser anterior a la fecha de solicitud.'
        
        if self.fecha_surtido and self.fecha_autorizacion:
            if self.fecha_surtido < self.fecha_autorizacion:
                errors['fecha_surtido'] = 'La fecha de surtido no puede ser anterior a la fecha de autorización.'
        
        # ========== ISS-009 FIX (audit7): Validar coherencia de campos de firma ==========
        # Pares usuario/fecha deben estar completos para estados terminales
        if estado in ['surtida', 'parcial']:
            # Surtido requiere usuario Y fecha
            if self.usuario_firma_surtido and not self.fecha_firma_surtido:
                errors['fecha_firma_surtido'] = 'Falta fecha de firma de surtido.'
            if self.fecha_firma_surtido and not self.usuario_firma_surtido:
                errors['usuario_firma_surtido'] = 'Falta usuario de firma de surtido.'
        
        if estado == 'entregada':
            # Entrega requiere usuario Y fecha de recepción
            if self.usuario_firma_recepcion and not self.fecha_firma_recepcion:
                errors['fecha_firma_recepcion'] = 'Falta fecha de firma de recepción.'
            if self.fecha_firma_recepcion and not self.usuario_firma_recepcion:
                errors['usuario_firma_recepcion'] = 'Falta usuario de firma de recepción.'
            
            # ISS-009 FIX: Advertir si no hay evidencia de surtido en entrega
            if not self.usuario_firma_surtido:
                logger.warning(
                    f"ISS-009 AUDIT: Requisición {self.numero} en estado 'entregada' "
                    f"sin usuario de surtido registrado. Posible problema de trazabilidad."
                )
        
        # ========== ISS-006 FIX: Validar rutas de archivos de firma ==========
        # Campos de ruta de firma que deben ser validados
        campos_firma = [
            ('foto_firma_surtido', self.foto_firma_surtido),
            ('foto_firma_recepcion', self.foto_firma_recepcion),
            ('firma_solicitante', self.firma_solicitante),
            ('firma_jefe_area', self.firma_jefe_area),
            ('firma_director', self.firma_director),
        ]
        
        for campo_nombre, valor in campos_firma:
            if valor:
                try:
                    validate_firma_path(valor)
                except ValidationError as e:
                    errors[campo_nombre] = str(e.message if hasattr(e, 'message') else e)
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """
        ISS-003 FIX (audit14): Ejecutar validaciones antes de guardar.
        
        IMPORTANTE: Para cambios de estado, usar los métodos:
        - cambiar_estado() para transiciones simples
        - cambiar_estado_con_historial() para trazabilidad completa
        - RequisicionService para operaciones de inventario
        
        El parámetro skip_validation permite omitir validaciones solo en:
        - Migraciones de datos
        - Scripts de mantenimiento supervisados
        - Tests
        """
        from django.conf import settings
        
        skip_validation = kwargs.pop('skip_validation', False)
        
        # ISS-003 FIX: Restringir skip_validation en producción
        if skip_validation:
            if not getattr(settings, 'DEBUG', False):
                logger.warning(
                    f"ISS-003: skip_validation usado en PRODUCCIÓN para Requisicion {self.numero}. "
                    f"Estado: {self.estado}. Revisar trazabilidad."
                )
            else:
                logger.debug(f"ISS-003: skip_validation usado para Requisicion {self.numero}")
        
        if not skip_validation:
            self.full_clean()
        
        super().save(*args, **kwargs)


class DetalleRequisicion(models.Model):
    """
    Detalle de Requisicion
    Adaptado a la estructura de base de datos existente
    
    MEJORA FLUJO 3: Campo motivo_ajuste para comunicar al Centro
    por qué Farmacia autorizó menos cantidad de la solicitada.
    
    ISS-003 FIX: Validaciones de negocio implementadas:
    - Cantidades no pueden ser negativas
    - Coherencia: solicitada >= autorizada >= surtida >= recibida
    - motivo_ajuste obligatorio cuando cantidad_autorizada < cantidad_solicitada
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
    
    def clean(self):
        """
        ISS-003 FIX: Validaciones de negocio para detalles de requisición.
        
        Valida:
        - Cantidades no negativas
        - Coherencia entre cantidades (solicitada >= autorizada >= surtida >= recibida)
        - Obligatoriedad de motivo_ajuste cuando se reduce cantidad autorizada
        """
        from django.core.exceptions import ValidationError
        
        errors = {}
        
        # ========== Validar cantidades no negativas ==========
        if self.cantidad_solicitada is not None and self.cantidad_solicitada < 0:
            errors['cantidad_solicitada'] = 'La cantidad solicitada no puede ser negativa.'
        
        if self.cantidad_autorizada is not None and self.cantidad_autorizada < 0:
            errors['cantidad_autorizada'] = 'La cantidad autorizada no puede ser negativa.'
        
        if self.cantidad_surtida is not None and self.cantidad_surtida < 0:
            errors['cantidad_surtida'] = 'La cantidad surtida no puede ser negativa.'
        
        if self.cantidad_recibida is not None and self.cantidad_recibida < 0:
            errors['cantidad_recibida'] = 'La cantidad recibida no puede ser negativa.'
        
        # ========== Validar coherencia de cantidades ==========
        # Solo validar coherencia si los valores están presentes
        
        # cantidad_autorizada no puede superar cantidad_solicitada
        if (self.cantidad_autorizada is not None and 
            self.cantidad_solicitada is not None and
            self.cantidad_autorizada > self.cantidad_solicitada):
            errors['cantidad_autorizada'] = (
                f'La cantidad autorizada ({self.cantidad_autorizada}) no puede '
                f'superar la cantidad solicitada ({self.cantidad_solicitada}).'
            )
        
        # cantidad_surtida no puede superar cantidad_autorizada
        if (self.cantidad_surtida is not None and 
            self.cantidad_autorizada is not None and
            self.cantidad_surtida > self.cantidad_autorizada):
            errors['cantidad_surtida'] = (
                f'La cantidad surtida ({self.cantidad_surtida}) no puede '
                f'superar la cantidad autorizada ({self.cantidad_autorizada}).'
            )
        
        # cantidad_recibida no puede superar cantidad_surtida
        if (self.cantidad_recibida is not None and 
            self.cantidad_surtida is not None and
            self.cantidad_recibida > self.cantidad_surtida):
            errors['cantidad_recibida'] = (
                f'La cantidad recibida ({self.cantidad_recibida}) no puede '
                f'superar la cantidad surtida ({self.cantidad_surtida}).'
            )
        
        # ========== ISS-003 FIX: Validar motivo_ajuste obligatorio ==========
        # Si cantidad_autorizada es menor que cantidad_solicitada, se requiere motivo
        if (self.cantidad_autorizada is not None and 
            self.cantidad_solicitada is not None and
            self.cantidad_autorizada < self.cantidad_solicitada):
            if not self.motivo_ajuste or not self.motivo_ajuste.strip():
                errors['motivo_ajuste'] = (
                    f'Se requiere un motivo de ajuste cuando la cantidad autorizada '
                    f'({self.cantidad_autorizada}) es menor que la solicitada '
                    f'({self.cantidad_solicitada}). Explique la razón del ajuste.'
                )
        
        # ========== Validar cantidad_solicitada > 0 ==========
        if self.cantidad_solicitada is not None and self.cantidad_solicitada <= 0:
            errors['cantidad_solicitada'] = 'La cantidad solicitada debe ser mayor a cero.'
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """
        ISS-003 FIX: Ejecutar validaciones antes de guardar.
        
        El parámetro skip_validation permite omitir validaciones solo en:
        - Migraciones de datos
        - Scripts de mantenimiento supervisados
        """
        from django.conf import settings
        
        skip_validation = kwargs.pop('skip_validation', False)
        
        if skip_validation:
            if not getattr(settings, 'DEBUG', False):
                logger.warning(
                    f"ISS-003: skip_validation usado en PRODUCCIÓN para DetalleRequisicion. "
                    f"Requisicion: {self.requisicion_id}, Producto: {self.producto_id}. "
                    f"Revisar trazabilidad."
                )
        
        if not skip_validation:
            self.full_clean()
        
        super().save(*args, **kwargs)


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
    Configuración del tema visual - Supabase
    
    Campos en Supabase: id, nombre, es_activo, logo_url, logo_width, logo_height,
    favicon_url, titulo_sistema, subtitulo_sistema, y muchos colores...
    """
    nombre = models.CharField(max_length=100, unique=True)
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
    
    # Propiedades para compatibilidad con pdf_reports.py
    @property
    def activo(self):
        return self.es_activo
    
    @property
    def color_fondo(self):
        return self.color_fondo_principal
    
    @property
    def color_texto(self):
        return self.color_texto_principal
    
    @property
    def color_texto_secundario(self):
        """Alias para color_texto_secundario (usa color_texto_sidebar como fallback)"""
        return getattr(self, '_color_texto_secundario', None) or '#6b7280'
    
    @property
    def color_advertencia(self):
        """Alias para color_advertencia (usa color_alerta)"""
        return self.color_alerta or '#FF9800'
    
    @property
    def reporte_color_texto_encabezado(self):
        """Color del texto en encabezados de tablas de reportes"""
        return getattr(self, '_reporte_color_texto_encabezado', None) or '#FFFFFF'
    
    @property
    def reporte_titulo_institucion(self):
        """Título de la institución para reportes"""
        return self.titulo_sistema or 'Sistema de Farmacia Penitenciaria'
    
    @property
    def reporte_subtitulo(self):
        """Subtítulo para reportes"""
        return self.subtitulo_sistema or 'Secretaría de Seguridad'
    
    @property
    def logo_reportes(self):
        """Logo para reportes (usa logo_url)"""
        return None  # No hay campo de archivo, retornar None
    
    @property
    def imagen_fondo_reportes(self):
        """Imagen de fondo para reportes"""
        return None  # No hay campo de archivo, retornar None
    
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

    @classmethod
    def get_tema_activo(cls):
        """
        Obtiene el tema activo del sistema.
        Retorna el primer tema con es_activo=True, o crea un tema por defecto.
        """
        try:
            tema = cls.objects.filter(es_activo=True).first()
            if tema:
                return tema
            # Retornar el primer tema existente si ninguno está activo
            tema = cls.objects.first()
            if tema:
                return tema
        except Exception:
            pass
        # Retornar un objeto con valores por defecto
        return cls(
            nombre='default',
            es_activo=True,
            color_primario='#632842',
            color_primario_hover='#8a3b5c',
            color_secundario='#424242',
            color_texto_principal='#1f2937',
            color_texto_secundario='#6b7280',
            reporte_color_encabezado='#632842',
            reporte_color_texto='#FFFFFF',
            reporte_color_filas_alternas='#F5F5F5',
            color_exito='#4CAF50',
            color_error='#F44336',
            color_alerta='#FF9800',
            color_info='#2196F3',
        )


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
    
    Campos en Supabase (según crear_bd_desarrollo.sql):
    id, hoja_recoleccion_id, requisicion_id, orden, recolectado, fecha_recoleccion, notas, created_at
    
    ISS-DB-ALIGN: Alineado con esquema real de BD
    """
    hoja = models.ForeignKey(HojaRecoleccion, on_delete=models.CASCADE, related_name='detalles', db_column='hoja_recoleccion_id')
    requisicion = models.ForeignKey('Requisicion', on_delete=models.CASCADE, related_name='detalles_hoja_recoleccion', db_column='requisicion_id', null=True, blank=True)
    orden = models.IntegerField(default=0)
    recolectado = models.BooleanField(default=False)
    fecha_recoleccion = models.DateTimeField(null=True, blank=True)
    notas = models.TextField(blank=True, null=True)
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


# ============================================================================
# CATÁLOGO INDEPENDIENTE DE PRODUCTOS PARA DONACIONES
# ============================================================================
class ProductoDonacion(models.Model):
    """
    Catálogo de productos EXCLUSIVO para donaciones.
    Completamente independiente del catálogo de productos principal.
    Las donaciones pueden tener productos con claves y nombres diferentes.
    """
    clave = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, null=True)
    unidad_medida = models.CharField(max_length=50, default='PIEZA')
    presentacion = models.CharField(max_length=100, blank=True, null=True)
    activo = models.BooleanField(default=True)
    notas = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'productos_donacion'
        managed = False  # Tabla en Supabase
        ordering = ['nombre']
        verbose_name = 'Producto de Donación'
        verbose_name_plural = 'Productos de Donación'

    def __str__(self):
        return f"{self.clave} - {self.nombre}"


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
    Detalle de productos en una donacion - ALMACEN COMPLETAMENTE SEPARADO.
    Usa ProductoDonacion (catálogo independiente) en lugar del catálogo principal.
    NO afecta el inventario principal ni genera movimientos auditados.
    """
    donacion = models.ForeignKey(
        Donacion, 
        on_delete=models.CASCADE, 
        related_name='detalles',
        db_column='donacion_id'
    )
    # USA CATÁLOGO INDEPENDIENTE DE DONACIONES - no el catálogo principal
    producto_donacion = models.ForeignKey(
        ProductoDonacion, 
        on_delete=models.PROTECT, 
        related_name='detalles_donacion',
        db_column='producto_donacion_id',
        null=True,  # Permitir null temporalmente para migración
        blank=True
    )
    # Campos legacy para compatibilidad con datos existentes
    producto = models.ForeignKey(
        Producto, 
        on_delete=models.SET_NULL,  # Cambiado a SET_NULL para permitir desvinculación
        related_name='detalles_donacion_legacy',
        db_column='producto_id',
        null=True,  # Ahora es opcional
        blank=True
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
        # Usar producto_donacion si existe, sino producto legacy
        nombre_producto = 'Sin producto'
        if self.producto_donacion:
            nombre_producto = self.producto_donacion.nombre
        elif self.producto:
            nombre_producto = self.producto.nombre
        return f"{self.donacion.numero} - {nombre_producto} x {self.cantidad}"
    
    @property
    def nombre_producto(self):
        """Devuelve el nombre del producto (donación o legacy)"""
        if self.producto_donacion:
            return self.producto_donacion.nombre
        elif self.producto:
            return self.producto.nombre
        return 'Sin producto'
    
    @property
    def clave_producto(self):
        """Devuelve la clave del producto (donación o legacy)"""
        if self.producto_donacion:
            return self.producto_donacion.clave
        elif self.producto:
            return self.producto.clave
        return ''
    
    def save(self, *args, **kwargs):
        # Si es nuevo registro y NO se especificó cantidad_disponible explícitamente,
        # usar el valor de cantidad. Pero si se pasó 0, respetarlo (donación pendiente).
        if not self.pk and self.cantidad_disponible is None:
            self.cantidad_disponible = self.cantidad
        super().save(*args, **kwargs)


class SalidaDonacion(models.Model):
    """
    Registro de entregas/salidas del almacen de donaciones.
    Permite control interno sin afectar movimientos principales.
    
    ISS-DB-ALIGN: Campos agregados para coincidir con BD Supabase:
    - centro_destino_id: Centro penitenciario destino de la entrega
    - finalizado: Si la entrega fue confirmada/completada
    - fecha_finalizado: Timestamp de finalización
    - finalizado_por_id: Usuario que finalizó la entrega
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
    
    # ISS-DB-ALIGN: Campos nuevos para trazabilidad de entregas a centros
    centro_destino = models.ForeignKey(
        Centro,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='salidas_donaciones',
        db_column='centro_destino_id'
    )
    finalizado = models.BooleanField(default=False)
    fecha_finalizado = models.DateTimeField(null=True, blank=True)
    finalizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='entregas_finalizadas',
        db_column='finalizado_por_id'
    )

    class Meta:
        db_table = 'salidas_donaciones'
        managed = False  # Tabla en Supabase
        ordering = ['-fecha_entrega']

    def __str__(self):
        return f"Salida {self.id} - {self.destinatario} x {self.cantidad}"
    
    @property
    def estado_entrega(self):
        """Estado de la entrega para mostrar en frontend"""
        return 'entregado' if self.finalizado else 'pendiente'
    
    def save(self, *args, **kwargs):
        # El stock se descuenta AL CREAR para reservarlo inmediatamente
        # Esto evita que múltiples usuarios soliciten el mismo stock
        is_new = self.pk is None
        
        if is_new:  # Solo en creación
            if self.cantidad > self.detalle_donacion.cantidad_disponible:
                raise ValueError(
                    f"Stock insuficiente. Disponible: {self.detalle_donacion.cantidad_disponible}, "
                    f"Solicitado: {self.cantidad}"
                )
            # Descontar inmediatamente al crear (reservar stock)
            self.detalle_donacion.cantidad_disponible -= self.cantidad
            self.detalle_donacion.save(update_fields=['cantidad_disponible'])
        
        super().save(*args, **kwargs)
    
    def finalizar(self, usuario=None):
        """
        Finaliza la entrega (confirma que fue entregada físicamente).
        El stock ya fue descontado al crear, aquí solo se marca como completado.
        """
        from django.utils import timezone
        
        if self.finalizado:
            raise ValueError("Esta entrega ya fue finalizada")
        
        # Marcar como finalizado (el stock ya fue descontado al crear)
        self.finalizado = True
        self.fecha_finalizado = timezone.now()
        if usuario:
            self.finalizado_por = usuario
        self.save()


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
        ('devolver_centro', 'Devolver al Médico'),
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


# =============================================================================
# MÓDULO DE DISPENSACIÓN A PACIENTES (FORMATO C)
# =============================================================================

SEXO_CHOICES = [
    ('M', 'Masculino'),
    ('F', 'Femenino'),
]

TIPOS_DISPENSACION = [
    ('normal', 'Normal'),
    ('urgente', 'Urgente'),
    ('tratamiento_cronico', 'Tratamiento Crónico'),
    ('dosis_unica', 'Dosis Única'),
]

ESTADOS_DISPENSACION = [
    ('pendiente', 'Pendiente'),
    ('dispensada', 'Dispensada'),
    ('parcial', 'Parcialmente Dispensada'),
    ('cancelada', 'Cancelada'),
]

ESTADOS_DETALLE_DISPENSACION = [
    ('pendiente', 'Pendiente'),
    ('dispensado', 'Dispensado'),
    ('sin_stock', 'Sin Stock'),
    ('sustituido', 'Sustituido'),
]


class Paciente(models.Model):
    """
    Catálogo de Pacientes/Internos para el módulo de dispensación.
    
    Cada paciente está asociado a un centro penitenciario y tiene
    un número de expediente único para trazabilidad de dispensaciones.
    """
    # Identificación
    numero_expediente = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=100)
    apellido_paterno = models.CharField(max_length=100)
    apellido_materno = models.CharField(max_length=100, blank=True, null=True)
    curp = models.CharField(max_length=18, blank=True, null=True)
    fecha_nacimiento = models.DateField(blank=True, null=True)
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES, blank=True, null=True)
    
    # Ubicación en el centro
    centro = models.ForeignKey(
        Centro,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pacientes',
        db_column='centro_id'
    )
    dormitorio = models.CharField(max_length=50, blank=True, null=True)
    celda = models.CharField(max_length=50, blank=True, null=True)
    
    # Información médica
    tipo_sangre = models.CharField(max_length=10, blank=True, null=True)
    alergias = models.TextField(blank=True, null=True)
    enfermedades_cronicas = models.TextField(blank=True, null=True)
    observaciones_medicas = models.TextField(blank=True, null=True)
    
    # Control
    activo = models.BooleanField(default=True)
    fecha_ingreso = models.DateField(blank=True, null=True)
    fecha_egreso = models.DateField(blank=True, null=True)
    motivo_egreso = models.CharField(max_length=100, blank=True, null=True)
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pacientes_creados',
        db_column='created_by_id'
    )

    class Meta:
        db_table = 'pacientes'
        managed = False  # Tabla en Supabase
        ordering = ['apellido_paterno', 'apellido_materno', 'nombre']
        verbose_name = 'Paciente'
        verbose_name_plural = 'Pacientes'

    def __str__(self):
        return f"{self.numero_expediente} - {self.nombre_completo}"
    
    @property
    def nombre_completo(self):
        """Retorna el nombre completo del paciente"""
        partes = [self.nombre, self.apellido_paterno]
        if self.apellido_materno:
            partes.append(self.apellido_materno)
        return ' '.join(partes)
    
    @property
    def edad(self):
        """Calcula la edad del paciente"""
        if not self.fecha_nacimiento:
            return None
        from datetime import date
        hoy = date.today()
        edad = hoy.year - self.fecha_nacimiento.year
        if (hoy.month, hoy.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day):
            edad -= 1
        return edad
    
    @property
    def ubicacion_completa(self):
        """Retorna la ubicación completa (dormitorio/celda)"""
        partes = []
        if self.dormitorio:
            partes.append(f"Dorm. {self.dormitorio}")
        if self.celda:
            partes.append(f"Celda {self.celda}")
        return ' / '.join(partes) if partes else 'Sin ubicación'


class Dispensacion(models.Model):
    """
    Registro de dispensación de medicamentos a pacientes (Formato C).
    
    Representa una entrega de medicamentos a un paciente interno,
    con trazabilidad completa y generación de documento oficial.
    """
    # Identificación
    folio = models.CharField(max_length=50, unique=True)
    
    # Relaciones principales
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.PROTECT,
        related_name='dispensaciones',
        db_column='paciente_id'
    )
    centro = models.ForeignKey(
        Centro,
        on_delete=models.PROTECT,
        related_name='dispensaciones',
        db_column='centro_id'
    )
    
    # Información de la dispensación
    fecha_dispensacion = models.DateTimeField(auto_now_add=True)
    tipo_dispensacion = models.CharField(
        max_length=30,
        choices=TIPOS_DISPENSACION,
        default='normal'
    )
    
    # Prescripción médica
    diagnostico = models.TextField(blank=True, null=True)
    indicaciones = models.TextField(blank=True, null=True)
    medico_prescriptor = models.CharField(max_length=200, blank=True, null=True)
    cedula_medico = models.CharField(max_length=20, blank=True, null=True)
    
    # Estado
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS_DISPENSACION,
        default='pendiente'
    )
    
    # Responsables
    dispensado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dispensaciones_realizadas',
        db_column='dispensado_por_id'
    )
    autorizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dispensaciones_autorizadas',
        db_column='autorizado_por_id'
    )
    
    # Firmas digitales
    firma_paciente = models.CharField(max_length=255, blank=True, null=True)
    firma_dispensador = models.CharField(max_length=255, blank=True, null=True)
    
    # Observaciones
    observaciones = models.TextField(blank=True, null=True)
    motivo_cancelacion = models.TextField(blank=True, null=True)
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dispensaciones_creadas',
        db_column='created_by_id'
    )

    class Meta:
        db_table = 'dispensaciones'
        managed = False  # Tabla en Supabase
        ordering = ['-fecha_dispensacion']
        verbose_name = 'Dispensación'
        verbose_name_plural = 'Dispensaciones'

    def __str__(self):
        return f"{self.folio} - {self.paciente.nombre_completo}"
    
    def get_total_items(self):
        """Retorna el total de items en la dispensación"""
        return self.detalles.count()
    
    def get_total_dispensado(self):
        """Retorna el total de unidades dispensadas"""
        from django.db.models import Sum
        return self.detalles.aggregate(total=Sum('cantidad_dispensada'))['total'] or 0
    
    def get_total_prescrito(self):
        """Retorna el total de unidades prescritas"""
        from django.db.models import Sum
        return self.detalles.aggregate(total=Sum('cantidad_prescrita'))['total'] or 0
    
    @property
    def porcentaje_completado(self):
        """Calcula el porcentaje de dispensación completada"""
        total_prescrito = self.get_total_prescrito()
        if total_prescrito == 0:
            return 0
        return round((self.get_total_dispensado() / total_prescrito) * 100, 1)


class DetalleDispensacion(models.Model):
    """
    Detalle de productos dispensados a pacientes.
    
    Cada línea representa un medicamento específico con su dosificación
    y la cantidad realmente entregada.
    """
    # Relación con dispensación
    dispensacion = models.ForeignKey(
        Dispensacion,
        on_delete=models.CASCADE,
        related_name='detalles',
        db_column='dispensacion_id'
    )
    
    # Producto dispensado
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='dispensaciones',
        db_column='producto_id'
    )
    lote = models.ForeignKey(
        Lote,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dispensaciones',
        db_column='lote_id'
    )
    
    # Cantidades
    cantidad_prescrita = models.IntegerField()
    cantidad_dispensada = models.IntegerField(default=0)
    
    # Información de dosificación
    dosis = models.CharField(max_length=100, blank=True, null=True)
    frecuencia = models.CharField(max_length=100, blank=True, null=True)
    duracion_tratamiento = models.CharField(max_length=100, blank=True, null=True)
    via_administracion = models.CharField(max_length=50, blank=True, null=True)
    horarios = models.TextField(blank=True, null=True)
    
    # Estado
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS_DETALLE_DISPENSACION,
        default='pendiente'
    )
    
    # Sustitución
    producto_sustituto = models.ForeignKey(
        Producto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sustituciones_dispensacion',
        db_column='producto_sustituto_id'
    )
    motivo_sustitucion = models.TextField(blank=True, null=True)
    
    # Observaciones
    notas = models.TextField(blank=True, null=True)
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'detalle_dispensaciones'
        managed = False  # Tabla en Supabase
        ordering = ['id']
        verbose_name = 'Detalle de Dispensación'
        verbose_name_plural = 'Detalles de Dispensación'

    def __str__(self):
        return f"{self.dispensacion.folio} - {self.producto.nombre} x {self.cantidad_dispensada}"
    
    @property
    def completo(self):
        """Indica si se dispensó la cantidad completa"""
        return self.cantidad_dispensada >= self.cantidad_prescrita


class HistorialDispensacion(models.Model):
    """
    Historial de cambios en dispensaciones para auditoría.
    """
    ACCIONES = [
        ('crear', 'Creación'),
        ('agregar_item', 'Agregar Item'),
        ('dispensar', 'Dispensar'),
        ('completar', 'Completar'),
        ('cancelar', 'Cancelar'),
        ('modificar', 'Modificar'),
    ]
    
    dispensacion = models.ForeignKey(
        Dispensacion,
        on_delete=models.CASCADE,
        related_name='historial',
        db_column='dispensacion_id'
    )
    accion = models.CharField(max_length=50, choices=ACCIONES)
    estado_anterior = models.CharField(max_length=20, blank=True, null=True)
    estado_nuevo = models.CharField(max_length=20, blank=True, null=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historial_dispensaciones',
        db_column='usuario_id'
    )
    detalles = models.JSONField(blank=True, null=True)
    ip_address = models.CharField(max_length=45, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'historial_dispensaciones'
        managed = False  # Tabla en Supabase
        ordering = ['-created_at']
        verbose_name = 'Historial de Dispensación'
        verbose_name_plural = 'Historial de Dispensaciones'

    def __str__(self):
        return f"{self.dispensacion.folio} - {self.get_accion_display()}"


# =====================================================
# MÓDULO: COMPRAS DE CAJA CHICA DEL CENTRO
# =====================================================

class CompraCajaChica(models.Model):
    """
    Compras realizadas por el centro penitenciario con recursos de caja chica.
    
    FLUJO MULTINIVEL CON VERIFICACIÓN DE FARMACIA:
    1. Centro crea solicitud (pendiente)
    2. Centro envía a Farmacia para verificación (enviada_farmacia)
    3. Farmacia confirma NO disponibilidad (sin_stock_farmacia)
    4. Centro envía a Admin (enviada_admin)
    5. Admin autoriza (autorizada_admin)
    6. Admin envía a Director (enviada_director)
    7. Director autoriza (autorizada) - Lista para comprar
    8. Se realiza la compra (comprada)
    9. Se reciben productos (recibida)
    
    Si Farmacia tiene stock: rechaza indicando disponibilidad (rechazada_farmacia)
    
    PERMISOS:
    - Médico/Centro: Crea y envía solicitudes
    - Farmacia: Verifica disponibilidad
    - Admin: Autoriza y envía a Director
    - Director: Autorización final
    """
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('enviada_farmacia', 'Enviada a Farmacia'),
        ('sin_stock_farmacia', 'Sin Stock en Farmacia'),
        ('rechazada_farmacia', 'Hay Stock en Farmacia'),
        ('enviada_admin', 'Enviada a Admin'),
        ('autorizada_admin', 'Autorizada por Admin'),
        ('enviada_director', 'Enviada a Director'),
        ('autorizada', 'Autorizada'),
        ('comprada', 'Comprada'),
        ('recibida', 'Recibida'),
        ('cancelada', 'Cancelada'),
        ('rechazada', 'Rechazada'),
    ]
    
    # Transiciones válidas de estado
    TRANSICIONES_VALIDAS = {
        'pendiente': ['enviada_farmacia', 'cancelada'],
        'enviada_farmacia': ['sin_stock_farmacia', 'rechazada_farmacia', 'pendiente'],  # Farmacia verifica
        'sin_stock_farmacia': ['enviada_admin', 'cancelada'],  # Centro procede con compra
        'rechazada_farmacia': ['pendiente', 'cancelada'],  # Farmacia tiene stock, no procede compra
        'enviada_admin': ['autorizada_admin', 'rechazada', 'sin_stock_farmacia'],  # Admin puede devolver
        'autorizada_admin': ['enviada_director', 'cancelada'],
        'enviada_director': ['autorizada', 'rechazada', 'autorizada_admin'],  # Director puede devolver
        'autorizada': ['comprada', 'cancelada'],
        'comprada': ['recibida', 'cancelada'],
        'recibida': [],  # Estado terminal
        'cancelada': [],  # Estado terminal
        'rechazada': ['pendiente'],  # Puede volver a iniciar
    }
    
    folio = models.CharField(max_length=50, unique=True, blank=True)
    
    centro = models.ForeignKey(
        'Centro',
        on_delete=models.PROTECT,
        related_name='compras_caja_chica',
        db_column='centro_id'
    )
    
    # Requisición de origen (opcional)
    requisicion_origen = models.ForeignKey(
        'Requisicion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='compras_caja_chica',
        db_column='requisicion_origen_id'
    )
    
    # Datos del proveedor (opcional al crear, se llena cuando se realiza la compra)
    proveedor_nombre = models.CharField(max_length=200, blank=True, null=True)
    proveedor_rfc = models.CharField(max_length=20, blank=True, null=True)
    proveedor_direccion = models.TextField(blank=True, null=True)
    proveedor_telefono = models.CharField(max_length=50, blank=True, null=True)
    proveedor_contacto = models.CharField(max_length=200, blank=True, null=True)
    
    # Fechas base
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_compra = models.DateField(blank=True, null=True)
    fecha_recepcion = models.DateTimeField(blank=True, null=True)
    
    # ========== FLUJO FARMACIA: VERIFICACIÓN DE DISPONIBILIDAD ==========
    fecha_envio_farmacia = models.DateTimeField(blank=True, null=True)
    fecha_respuesta_farmacia = models.DateTimeField(blank=True, null=True)
    
    # ========== FLUJO MULTINIVEL: FECHAS DE TRAZABILIDAD ==========
    fecha_envio_admin = models.DateTimeField(blank=True, null=True)
    fecha_autorizacion_admin = models.DateTimeField(blank=True, null=True)
    fecha_envio_director = models.DateTimeField(blank=True, null=True)
    fecha_autorizacion_director = models.DateTimeField(blank=True, null=True)
    
    # Documento de respaldo
    numero_factura = models.CharField(max_length=100, blank=True, null=True)
    documento_respaldo = models.CharField(max_length=500, blank=True, null=True)
    
    # Montos
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    iva = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Justificación
    motivo_compra = models.TextField(help_text="Justificación de la compra por caja chica")
    
    # Estado
    estado = models.CharField(max_length=30, choices=ESTADOS, default='pendiente')
    
    # ========== USUARIOS DEL FLUJO ==========
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='compras_caja_solicitadas',
        db_column='solicitante_id'
    )
    # Admin que autoriza
    administrador_centro = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='compras_caja_autorizadas_admin',
        db_column='administrador_centro_id'
    )
    # Director que autoriza
    director_centro = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='compras_caja_autorizadas_director',
        db_column='director_centro_id'
    )
    # Compatibilidad: autorizado_por apunta al último autorizador
    autorizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='compras_caja_autorizadas',
        db_column='autorizado_por_id'
    )
    recibido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='compras_caja_recibidas',
        db_column='recibido_por_id'
    )
    # Usuario que rechazó
    rechazado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='compras_caja_rechazadas',
        db_column='rechazado_por_id'
    )
    
    # ========== FLUJO FARMACIA: VERIFICADOR ==========
    verificado_por_farmacia = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='compras_caja_verificadas',
        db_column='verificado_por_farmacia_id'
    )
    respuesta_farmacia = models.TextField(blank=True, null=True, help_text="Respuesta de farmacia sobre disponibilidad")
    stock_farmacia_verificado = models.IntegerField(blank=True, null=True, help_text="Stock encontrado en farmacia al momento de verificar")
    
    # Observaciones y motivos
    observaciones = models.TextField(blank=True, null=True)
    motivo_cancelacion = models.TextField(blank=True, null=True)
    motivo_rechazo = models.TextField(blank=True, null=True)
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'compras_caja_chica'
        managed = False
        ordering = ['-fecha_solicitud']
        verbose_name = 'Compra de Caja Chica'
        verbose_name_plural = 'Compras de Caja Chica'

    def __str__(self):
        return f"{self.folio} - {self.centro.nombre if self.centro else 'Sin centro'}"
    
    def calcular_totales(self):
        """Recalcula subtotal, IVA y total basado en los detalles"""
        from decimal import Decimal
        subtotal = Decimal('0')
        for detalle in self.detalles.all():
            subtotal += detalle.precio_unitario * detalle.cantidad_solicitada
        self.subtotal = subtotal
        self.iva = subtotal * Decimal('0.16')  # IVA 16%
        self.total = self.subtotal + self.iva
        self.save(update_fields=['subtotal', 'iva', 'total'])
    
    def puede_transicionar_a(self, nuevo_estado):
        """Verifica si la transición de estado es válida"""
        estados_permitidos = self.TRANSICIONES_VALIDAS.get(self.estado, [])
        return nuevo_estado in estados_permitidos


class DetalleCompraCajaChica(models.Model):
    """
    Productos incluidos en cada compra de caja chica.
    """
    compra = models.ForeignKey(
        CompraCajaChica,
        on_delete=models.CASCADE,
        related_name='detalles',
        db_column='compra_id'
    )
    
    # Producto (puede ser del catálogo o descripción libre)
    producto = models.ForeignKey(
        'Producto',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='compras_caja_chica',
        db_column='producto_id'
    )
    descripcion_producto = models.CharField(max_length=500)
    
    # Cantidades
    cantidad_solicitada = models.IntegerField()
    cantidad_comprada = models.IntegerField(default=0)
    cantidad_recibida = models.IntegerField(default=0)
    
    # Datos del lote
    numero_lote = models.CharField(max_length=100, blank=True, null=True)
    fecha_caducidad = models.DateField(blank=True, null=True)
    
    # Precios
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    importe = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Unidad
    unidad_medida = models.CharField(max_length=50, default='PIEZA')
    
    # Notas
    notas = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'detalle_compras_caja_chica'
        managed = False
        ordering = ['id']
        verbose_name = 'Detalle de Compra Caja Chica'
        verbose_name_plural = 'Detalles de Compras Caja Chica'

    def __str__(self):
        return f"{self.compra.folio} - {self.descripcion_producto}"
    
    def save(self, *args, **kwargs):
        # Calcular importe
        self.importe = self.precio_unitario * self.cantidad_comprada
        super().save(*args, **kwargs)


class InventarioCajaChica(models.Model):
    """
    Inventario de productos comprados por caja chica.
    Este inventario es SEPARADO del inventario principal de farmacia.
    Pertenece al centro penitenciario.
    """
    centro = models.ForeignKey(
        'Centro',
        on_delete=models.PROTECT,
        related_name='inventario_caja_chica',
        db_column='centro_id'
    )
    
    # Producto
    producto = models.ForeignKey(
        'Producto',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventario_caja_chica',
        db_column='producto_id'
    )
    descripcion_producto = models.CharField(max_length=500)
    
    # Lote
    numero_lote = models.CharField(max_length=100, blank=True, null=True)
    fecha_caducidad = models.DateField(blank=True, null=True)
    
    # Cantidades
    cantidad_inicial = models.IntegerField(default=0)
    cantidad_actual = models.IntegerField(default=0)
    
    # Referencias
    compra = models.ForeignKey(
        CompraCajaChica,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='items_inventario',
        db_column='compra_id'
    )
    detalle_compra = models.ForeignKey(
        DetalleCompraCajaChica,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='items_inventario',
        db_column='detalle_compra_id'
    )
    
    # Precio
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Ubicación
    ubicacion = models.CharField(max_length=200, blank=True, null=True)
    
    # Estado
    activo = models.BooleanField(default=True)
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'inventario_caja_chica'
        managed = False
        ordering = ['-created_at']
        verbose_name = 'Inventario Caja Chica'
        verbose_name_plural = 'Inventario Caja Chica'
        unique_together = [['centro', 'producto', 'numero_lote']]

    def __str__(self):
        return f"{self.centro.nombre} - {self.descripcion_producto} ({self.cantidad_actual})"
    
    @property
    def estado(self):
        """Estado calculado del inventario"""
        if not self.activo:
            return 'inactivo'
        if self.cantidad_actual <= 0:
            return 'agotado'
        if self.fecha_caducidad and self.fecha_caducidad <= date.today():
            return 'caducado'
        if self.fecha_caducidad and self.fecha_caducidad <= date.today() + timedelta(days=90):
            return 'por_caducar'
        return 'disponible'


class MovimientoCajaChica(models.Model):
    """
    Registro de movimientos del inventario de caja chica.
    """
    TIPOS = [
        ('entrada', 'Entrada'),
        ('salida', 'Salida'),
        ('ajuste_positivo', 'Ajuste Positivo'),
        ('ajuste_negativo', 'Ajuste Negativo'),
        ('merma', 'Merma'),
        ('devolucion', 'Devolución'),
    ]
    
    inventario = models.ForeignKey(
        InventarioCajaChica,
        on_delete=models.CASCADE,
        related_name='movimientos',
        db_column='inventario_id'
    )
    
    tipo = models.CharField(max_length=30, choices=TIPOS)
    cantidad = models.IntegerField()
    cantidad_anterior = models.IntegerField()
    cantidad_nueva = models.IntegerField()
    
    # Referencia
    referencia = models.CharField(max_length=200, blank=True, null=True)
    motivo = models.TextField(blank=True, null=True)
    
    # Usuario
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_caja_chica',
        db_column='usuario_id'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'movimientos_caja_chica'
        managed = False
        ordering = ['-created_at']
        verbose_name = 'Movimiento Caja Chica'
        verbose_name_plural = 'Movimientos Caja Chica'

    def __str__(self):
        return f"{self.inventario.descripcion_producto} - {self.get_tipo_display()} x {self.cantidad}"


class HistorialCompraCajaChica(models.Model):
    """
    Historial de cambios en compras de caja chica para auditoría.
    """
    compra = models.ForeignKey(
        CompraCajaChica,
        on_delete=models.CASCADE,
        related_name='historial',
        db_column='compra_id'
    )
    
    estado_anterior = models.CharField(max_length=30, blank=True, null=True)
    estado_nuevo = models.CharField(max_length=30)
    
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historial_compras_caja',
        db_column='usuario_id'
    )
    
    accion = models.CharField(max_length=100)
    observaciones = models.TextField(blank=True, null=True)
    ip_address = models.CharField(max_length=45, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'historial_compras_caja_chica'
        managed = False
        ordering = ['-created_at']
        verbose_name = 'Historial Compra Caja Chica'
        verbose_name_plural = 'Historial Compras Caja Chica'

    def __str__(self):
        return f"{self.compra.folio} - {self.accion}"
