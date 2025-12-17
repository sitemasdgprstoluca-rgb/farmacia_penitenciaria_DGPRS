from rest_framework import viewsets, status, serializers, permissions, mixins
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.core.paginator import InvalidPage
from django.core.cache import cache
from django.http import HttpResponse
from django.db import transaction
from django.db.models import Q, Sum, Count, F, IntegerField
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import Group
from datetime import datetime, timedelta, date
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
import os
import logging
import random  # ISS-FIX: Necesario para generar números de requisición
from io import BytesIO

# ISS-004 FIX (audit9): Pillow para validación profunda de imágenes
try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    Image = None

# ISS-011, ISS-021, ISS-030: Import de servicios transaccionales
from inventario.services import CentroPermissionMixin

logger = logging.getLogger(__name__)


# -----------------------------------------------------------
# VALIDADORES DE IMPORTACIÓN EXCEL
# -----------------------------------------------------------

# Magic bytes para formatos Excel válidos
# XLSX/XLSM son archivos ZIP (PK\x03\x04)
# XLS antiguo usa formato OLE2 (Compound File Binary Format)
# ISS-008 FIX (audit7): XLSM eliminado - archivos con macros NO permitidos
EXCEL_MAGIC_BYTES = {
    '.xlsx': b'PK\x03\x04',  # ZIP archive (Office Open XML)
    # '.xlsm': REMOVIDO - ISS-008 FIX: No permitir archivos con macros
    '.xls': b'\xD0\xCF\x11\xE0',  # OLE2 Compound Document
}

# ISS-008 FIX (audit7): Extensiones explícitamente prohibidas por seguridad
EXCEL_EXTENSIONS_BLOCKED = {'.xlsm', '.xlsb', '.xltm', '.xla', '.xlam'}  # Formatos con macros

# ISS-006: Magic bytes y MIME types para imágenes permitidas en firmas
IMAGE_MAGIC_BYTES = {
    '.jpg': [b'\xff\xd8\xff'],  # JPEG
    '.jpeg': [b'\xff\xd8\xff'],  # JPEG
    '.png': [b'\x89PNG\r\n\x1a\n'],  # PNG
    '.gif': [b'GIF87a', b'GIF89a'],  # GIF
    '.webp': [b'RIFF'],  # WebP (RIFF container)
}

ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
ALLOWED_IMAGE_MIMES = {
    'image/jpeg', 'image/png', 'image/gif', 'image/webp'
}

# ISS-005 FIX (audit7): Magic bytes para validación de PDF
PDF_MAGIC_BYTES = b'%PDF-'  # Todos los PDFs válidos empiezan con este header
PDF_MAX_SIZE_MB = 10  # Tamaño máximo en MB
PDF_MAX_SIZE_BYTES = PDF_MAX_SIZE_MB * 1024 * 1024

# ISS-002 FIX (audit9): Content-Types válidos para PDF (validación estricta)
PDF_VALID_CONTENT_TYPES = {'application/pdf', 'application/x-pdf'}

# ISS-001 FIX (audit9): Estado inicial SOLO borrador para TODOS los usuarios
# El flujo jerárquico OBLIGA: borrador → pendiente_admin → pendiente_director → enviada
# NUNCA se puede crear una requisición directamente en 'enviada'
ESTADO_INICIAL_UNICO = 'borrador'
# Mantener por compatibilidad pero DEPRECADO - usar ESTADO_INICIAL_UNICO
ESTADOS_INICIALES_VALIDOS = {'borrador'}  # ISS-001 FIX: Eliminado 'enviada'
ESTADO_INICIAL_CENTRO = 'borrador'
ESTADO_INICIAL_FARMACIA = 'borrador'


def validar_archivo_pdf(file, max_size_mb=PDF_MAX_SIZE_MB):
    """
    ISS-005 FIX (audit7): Valida archivo PDF antes de guardarlo.
    
    Validaciones:
    1. Archivo presente y con nombre válido
    2. Extensión .pdf
    3. Tamaño dentro de límites
    4. Magic bytes correctos (%PDF-)
    5. Content-Type MIME válido (si disponible)
    
    Retorna: (es_valido, mensaje_error)
    """
    # 1. Validar que hay archivo
    if not file:
        return False, 'No se recibió archivo PDF'
    
    # 2. Validar nombre obligatorio
    nombre = getattr(file, 'name', None)
    if not nombre or not nombre.strip():
        return False, 'El archivo debe tener un nombre válido'
    
    # 3. Validar extensión
    extension = ('.' + nombre.split('.')[-1].lower()) if '.' in nombre else ''
    if extension != '.pdf':
        return False, f'Solo se permiten archivos PDF (.pdf). Extensión recibida: {extension}'
    
    # 4. Validar tamaño
    max_size_bytes = max_size_mb * 1024 * 1024
    if hasattr(file, 'size') and file.size > max_size_bytes:
        return False, f'El archivo excede el tamaño máximo de {max_size_mb}MB ({file.size / 1024 / 1024:.2f}MB)'
    
    # 5. Validar magic bytes - leer primeros bytes con límite
    try:
        buffer_result, bytes_leidos = leer_archivo_con_limite(file, max_size_bytes + 1024)
        
        if buffer_result is None:
            return False, bytes_leidos  # bytes_leidos contiene el mensaje de error
        
        # Validar tamaño real
        if bytes_leidos > max_size_bytes:
            return False, f'El archivo excede el tamaño máximo de {max_size_mb}MB (tamaño real: {bytes_leidos / 1024 / 1024:.2f}MB)'
        
        # Verificar magic bytes de PDF
        header = buffer_result.read(8)
        buffer_result.seek(0)  # Restaurar posición
        
        if not header.startswith(PDF_MAGIC_BYTES):
            logger.warning(
                f"ISS-005: Archivo {nombre} rechazado - magic bytes incorrectos: {header[:8]!r}"
            )
            return False, 'El archivo no es un PDF válido (magic bytes incorrectos)'
        
    except Exception as e:
        logger.error(f"ISS-005: Error validando PDF {nombre}: {e}")
        return False, f'Error al validar el archivo PDF: {str(e)}'
    
    # 6. ISS-002 FIX (audit9): Validar Content-Type ESTRICTAMENTE
    # No solo advertir, BLOQUEAR archivos con Content-Type sospechoso
    content_type = getattr(file, 'content_type', None)
    if content_type:
        if content_type not in PDF_VALID_CONTENT_TYPES:
            logger.error(
                f"ISS-002: Archivo {nombre} BLOQUEADO - content-type inválido: {content_type}. "
                f"Solo se permiten: {PDF_VALID_CONTENT_TYPES}"
            )
            return False, (
                f'Content-Type inválido: {content_type}. '
                f'Solo se permiten archivos PDF (application/pdf)'
            )
    
    return True, None


def leer_archivo_con_limite(file, max_bytes):
    """
    ISS-001: Lee un archivo con límite estricto de bytes.
    
    Previene DoS por archivos enormes que no declaran tamaño correcto.
    Lee en chunks y aborta si se excede el límite.
    
    Args:
        file: Archivo a leer (UploadedFile o similar)
        max_bytes: Máximo de bytes permitidos
    
    Returns:
        tuple: (BytesIO con contenido, bytes_leidos) o (None, error_message)
    """
    CHUNK_SIZE = 64 * 1024  # 64KB chunks
    buffer = BytesIO()
    bytes_leidos = 0
    
    try:
        # Asegurar que estamos al inicio del archivo
        if hasattr(file, 'seek'):
            file.seek(0)
        
        while True:
            chunk = file.read(CHUNK_SIZE)
            if not chunk:
                break
            
            bytes_leidos += len(chunk)
            
            # ISS-001: Corte estricto si excede el límite
            if bytes_leidos > max_bytes:
                logger.warning(
                    f"Archivo rechazado: tamaño real ({bytes_leidos} bytes) "
                    f"excede límite ({max_bytes} bytes)"
                )
                return None, f'El archivo excede el tamaño máximo permitido ({max_bytes / 1024 / 1024:.1f}MB)'
            
            buffer.write(chunk)
        
        buffer.seek(0)
        return buffer, bytes_leidos
        
    except Exception as e:
        logger.error(f"Error leyendo archivo: {e}")
        return None, f'Error al leer el archivo: {str(e)}'


def validar_archivo_imagen(file, max_size_mb=2):
    """
    ISS-006: Valida archivo de imagen antes de guardarlo.
    
    Validaciones:
    1. Archivo presente y con nombre válido
    2. Extensión permitida (.jpg, .jpeg, .png, .gif, .webp)
    3. Tamaño dentro de límites (default 2MB)
    4. Magic bytes correctos (contenido real corresponde a imagen)
    5. Content-Type MIME válido (si disponible)
    
    Retorna: (es_valido, mensaje_error)
    """
    # 1. Validar que hay archivo
    if not file:
        return False, 'No se recibió archivo de imagen'
    
    # 2. Validar nombre obligatorio
    nombre = getattr(file, 'name', None)
    if not nombre or not nombre.strip():
        return False, 'El archivo debe tener un nombre válido'
    
    nombre_lower = nombre.lower().strip()
    ext = os.path.splitext(nombre_lower)[1]
    
    # 3. Validar extensión
    if not ext:
        return False, 'El archivo debe tener una extensión (.jpg, .png, etc.)'
    
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return False, f'Extensión no permitida: {ext}. Use: {", ".join(ALLOWED_IMAGE_EXTENSIONS)}'
    
    # 4. Validar tamaño
    max_size_bytes = max_size_mb * 1024 * 1024
    file_size = getattr(file, 'size', None)
    if file_size is not None and file_size > max_size_bytes:
        return False, f'Imagen demasiado grande: {file_size / 1024 / 1024:.1f}MB. Máximo: {max_size_mb}MB'
    
    # 5. Validar Content-Type MIME si está disponible
    content_type = getattr(file, 'content_type', None)
    if content_type and content_type.lower() not in ALLOWED_IMAGE_MIMES:
        logger.warning(
            f"Archivo rechazado: content_type {content_type} no permitido. "
            f"Nombre: {nombre}"
        )
        return False, f'Tipo de archivo no permitido: {content_type}. Use imágenes JPG, PNG, GIF o WebP'
    
    # 6. Validar magic bytes - contenido real del archivo
    try:
        pos = file.tell() if hasattr(file, 'tell') else 0
        header = file.read(16)  # Leer suficientes bytes
        
        if hasattr(file, 'seek'):
            file.seek(pos)
        
        if not header or len(header) < 4:
            return False, 'Archivo vacío o corrupto'
        
        # Verificar magic bytes según extensión
        expected_magics = IMAGE_MAGIC_BYTES.get(ext, [])
        if expected_magics:
            match = False
            for magic in expected_magics:
                if header.startswith(magic):
                    match = True
                    break
            
            if not match:
                logger.warning(
                    f"Archivo imagen rechazado: extensión {ext} pero magic bytes incorrectos. "
                    f"Header: {header[:8].hex()}, Nombre: {nombre}"
                )
                return False, f'El contenido del archivo no corresponde a una imagen {ext} válida'
    
    except Exception as e:
        logger.error(f"Error validando magic bytes de imagen: {e}")
        return False, 'Error al validar el contenido del archivo de imagen'
    
    # 7. ISS-004 FIX (audit9): Validación profunda con Pillow
    # Intenta abrir la imagen para detectar archivos corruptos o maliciosos
    if PILLOW_AVAILABLE and Image is not None:
        try:
            pos = file.tell() if hasattr(file, 'tell') else 0
            
            # Leer contenido completo para Pillow
            if hasattr(file, 'seek'):
                file.seek(0)
            content = file.read()
            
            # Restaurar posición
            if hasattr(file, 'seek'):
                file.seek(pos)
            
            # Intentar abrir con Pillow
            img_buffer = BytesIO(content)
            with Image.open(img_buffer) as img:
                # Verificar que realmente se puede decodificar
                img.verify()
                
                # Reabrir para validar dimensiones (verify() invalida el handle)
                img_buffer.seek(0)
                with Image.open(img_buffer) as img_check:
                    width, height = img_check.size
                    
                    # Límites de dimensiones para evitar DoS
                    MAX_IMAGE_DIMENSION = 4096  # 4K máximo
                    if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
                        logger.warning(
                            f"Imagen rechazada por dimensiones excesivas: {width}x{height}, "
                            f"máximo: {MAX_IMAGE_DIMENSION}x{MAX_IMAGE_DIMENSION}"
                        )
                        return False, f'Imagen demasiado grande: {width}x{height}. Máximo: {MAX_IMAGE_DIMENSION}x{MAX_IMAGE_DIMENSION} píxeles'
                    
                    # Verificar formato reportado por Pillow
                    pillow_format = img_check.format
                    expected_formats = {
                        '.jpg': ['JPEG'],
                        '.jpeg': ['JPEG'],
                        '.png': ['PNG'],
                        '.gif': ['GIF'],
                        '.webp': ['WEBP'],
                    }
                    
                    if ext in expected_formats and pillow_format not in expected_formats[ext]:
                        logger.warning(
                            f"Imagen rechazada: extensión {ext} pero Pillow detectó {pillow_format}. "
                            f"Nombre: {nombre}"
                        )
                        return False, f'El contenido del archivo ({pillow_format}) no corresponde a la extensión {ext}'
            
            # ISS-006 FIX (audit11): Asegurar que el stream quede en posición original
            if hasattr(file, 'seek'):
                file.seek(0)
                    
        except Exception as e:
            logger.warning(
                f"Imagen rechazada: Pillow no pudo abrir/verificar el archivo. "
                f"Error: {e}, Nombre: {nombre}"
            )
            return False, 'Imagen corrupta o formato no válido - no se puede procesar'
    else:
        # ISS-006 FIX (audit11): Rechazar imágenes si Pillow no está disponible
        # La validación solo con magic bytes no es suficiente para seguridad
        logger.error(
            "Pillow NO disponible - rechazando imagen por seguridad. "
            "Instale Pillow con: pip install Pillow"
        )
        return False, 'Validación de imágenes no disponible. Contacte al administrador.'
    
    # ISS-006 FIX (audit11): Asegurar stream en posición 0 para el caller
    if hasattr(file, 'seek'):
        file.seek(0)
    
    return True, None


def validar_archivo_excel(file):
    """
    ISS-008 FIX (audit7): Valida archivo Excel antes de procesarlo con múltiples capas de seguridad.
    
    Validaciones:
    1. Archivo presente y con nombre válido
    2. Extensión permitida (.xlsx, .xls) - NO xlsm ni otros con macros
    3. Tamaño dentro de límites
    4. Magic bytes correctos (contenido real coincide con extensión)
    
    ISS-008 FIX (audit7): Archivos con macros (.xlsm, .xlsb, etc) están BLOQUEADOS
    por seguridad. Solo se permiten formatos sin código ejecutable.
    
    Retorna: (es_valido, mensaje_error)
    """
    # 1. Validar que hay archivo
    if not file:
        return False, 'No se recibió archivo'
    
    # 2. ISS-001: Validar nombre obligatorio - rechazar archivos sin nombre
    nombre = getattr(file, 'name', None)
    if not nombre or not nombre.strip():
        return False, 'El archivo debe tener un nombre válido'
    
    nombre_lower = nombre.lower().strip()
    ext = os.path.splitext(nombre_lower)[1]
    
    # 3. Validar extensión
    if not ext:
        return False, 'El archivo debe tener una extensión (.xlsx o .xls)'
    
    # ISS-008 FIX (audit7): Bloquear extensiones con macros ANTES de cualquier otra validación
    if ext in EXCEL_EXTENSIONS_BLOCKED:
        logger.warning(
            f"ISS-008: Archivo rechazado por extensión con macros: {nombre}. "
            f"Extensiones bloqueadas: {EXCEL_EXTENSIONS_BLOCKED}"
        )
        return False, (
            f'Extensión {ext} no permitida por seguridad. '
            f'Los archivos con macros (.xlsm, .xlsb, etc.) están bloqueados. '
            f'Por favor convierta a .xlsx (sin macros) antes de importar.'
        )
    
    extensiones_permitidas = getattr(settings, 'IMPORT_ALLOWED_EXTENSIONS', ['.xlsx', '.xls'])
    if ext not in extensiones_permitidas:
        return False, f'Extensión no permitida: {ext}. Use: {", ".join(extensiones_permitidas)}'
    
    # 4. Validar tamaño declarado ANTES de leer contenido (primera línea de defensa)
    max_size_mb = getattr(settings, 'IMPORT_MAX_FILE_SIZE_MB', 10)
    max_size_bytes = max_size_mb * 1024 * 1024
    
    file_size = getattr(file, 'size', None)
    if file_size is not None and file_size > max_size_bytes:
        return False, f'Archivo demasiado grande: {file_size / 1024 / 1024:.1f}MB. Máximo: {max_size_mb}MB'
    
    # 5. ISS-001: Validar magic bytes - contenido real del archivo
    try:
        # Guardar posición actual y leer primeros bytes
        pos = file.tell() if hasattr(file, 'tell') else 0
        header = file.read(8)  # Leer suficientes bytes para identificar formato
        
        # Restaurar posición para que el archivo pueda ser procesado después
        if hasattr(file, 'seek'):
            file.seek(pos)
        
        if not header or len(header) < 4:
            return False, 'Archivo vacío o corrupto'
        
        # Verificar magic bytes según extensión
        expected_magic = EXCEL_MAGIC_BYTES.get(ext)
        if expected_magic:
            if not header.startswith(expected_magic):
                # El contenido no coincide con la extensión declarada
                logger.warning(
                    f"Archivo rechazado: extensión {ext} pero magic bytes incorrectos. "
                    f"Header: {header[:8].hex()}"
                )
                return False, f'El contenido del archivo no corresponde a un archivo {ext} válido'
    except Exception as e:
        logger.error(f"Error validando magic bytes: {e}")
        return False, 'Error al validar el contenido del archivo'
    
    return True, None


def cargar_workbook_seguro(file):
    """
    ISS-001: Carga un workbook Excel con límites de seguridad estrictos.
    
    1. Lee el archivo con límite real de bytes (no confía en file.size)
    2. Usa read_only=True para streaming y menor uso de memoria
    3. Usa data_only=True para ignorar fórmulas (previene ataques por fórmulas)
    
    Returns:
        tuple: (workbook, error_message) - workbook es None si hay error
    """
    max_size_mb = getattr(settings, 'IMPORT_MAX_FILE_SIZE_MB', 10)
    max_size_bytes = max_size_mb * 1024 * 1024
    
    # Leer archivo con límite estricto de bytes
    buffer, resultado = leer_archivo_con_limite(file, max_size_bytes)
    
    if buffer is None:
        # resultado contiene el mensaje de error
        return None, resultado
    
    try:
        # ISS-001: Usar read_only=True para streaming y data_only=True para ignorar fórmulas
        # Esto reduce significativamente el uso de memoria en archivos grandes
        wb = openpyxl.load_workbook(
            buffer, 
            read_only=True,  # Streaming mode - no carga todo en memoria
            data_only=True   # Ignora fórmulas - solo valores (previene ataques)
        )
        return wb, None
    except Exception as e:
        logger.error(f"Error cargando workbook: {e}")
        return None, f'Error al procesar el archivo Excel: {str(e)}'


def validar_filas_excel(ws):
    """
    Valida número de filas en worksheet con streaming y corte temprano.
    
    ISS-003: Optimizado para no recorrer archivos enormes innecesariamente.
    Se detiene al superar el límite máximo permitido.
    
    Retorna: (es_valido, mensaje_error, num_filas)
    """
    max_rows = getattr(settings, 'IMPORT_MAX_ROWS', 5000)
    # Margen adicional para detener el conteo (evitar contar millones de filas)
    cutoff = max_rows + 1
    
    num_filas = 0
    # ISS-003: Streaming con corte temprano - detenerse apenas superamos el límite
    for row in ws.iter_rows(min_row=2, values_only=True):
        # Solo contar filas que tienen al menos un valor no vacío
        if any(cell is not None and str(cell).strip() for cell in row):
            num_filas += 1
            if num_filas > max_rows:
                # Corte temprano: ya sabemos que excede el límite
                return False, f'El archivo excede el máximo de {max_rows} filas permitidas', num_filas
    
    return True, None, num_filas

from core.models import Producto, Lote, Movimiento, Centro, Requisicion, DetalleRequisicion, HojaRecoleccion, LoteDocumento
from core.serializers import (
    ProductoSerializer, LoteSerializer, MovimientoSerializer, 
    CentroSerializer, RequisicionSerializer, DetalleRequisicionSerializer,
    HojaRecoleccionSerializer, LoteDocumentoSerializer
)

from django.contrib.auth import get_user_model
from core.permissions import (
    IsAdminRole, IsFarmaciaRole, IsCentroRole, IsVistaRole,
    IsFarmaciaAdminOrReadOnly, CanAuthorizeRequisicion,
    IsCentroCanManageInventory, RoleHelper,  # ISS-MEDICO FIX
    IsFarmaciaAdminOrVistaReadOnly, IsCentroOwnResourcesOnly  # ISS-MEDICO FIX: permisos restrictivos
)
from core.constants import (
    ESTADOS_REQUISICION,
    PAGINATION_DEFAULT_PAGE_SIZE,
    PAGINATION_MAX_PAGE_SIZE,
    UNIDADES_MEDIDA,
    REQUISICION_GRUPOS_ESTADO,
    TRANSICIONES_REQUISICION,
    PERMISOS_FLUJO_REQUISICION,
)

User = get_user_model()


# ============================================================================
# HELPERS DE SEGURIDAD - Filtrado por centro para roles no-admin
# ISS-AUDIT FIX: Separación de funciones para claridad y seguridad
# ============================================================================

def is_farmacia_or_admin(user):
    """
    ISS-AUDIT FIX: Verifica si el usuario es farmacia o admin (roles de escritura).
    
    IMPORTANTE: Esta función NO incluye 'vista' - usar has_global_read_access()
    para operaciones de solo lectura que incluyan vista.
    
    Roles con acceso de escritura:
    - admin: admin_sistema, superusuario, administrador
    - farmacia: farmacia, admin_farmacia, farmaceutico, usuario_farmacia
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    
    rol = (getattr(user, 'rol', '') or '').lower()
    
    # ISS-AUDIT FIX: Solo roles admin y farmacia (NO vista)
    ROLES_ESCRITURA = {
        # Admin
        'admin', 'admin_sistema', 'superusuario', 'administrador',
        # Farmacia
        'farmacia', 'admin_farmacia', 'farmaceutico', 'usuario_farmacia',
    }
    
    if rol in ROLES_ESCRITURA:
        return True
    
    # Verificar grupos (por si el rol no esta en campo directo)
    group_names = {g.name.upper() for g in user.groups.all()}
    GRUPOS_ESCRITURA = {'FARMACIA_ADMIN', 'FARMACEUTICO'}
    
    return bool(group_names & GRUPOS_ESCRITURA)


def has_global_read_access(user):
    """
    ISS-AUDIT FIX: Verifica si el usuario puede leer datos globales (incluye vista).
    
    Usar esta función para operaciones de SOLO LECTURA donde el rol vista
    debe tener acceso.
    
    Roles con lectura global:
    - admin, farmacia (heredan de is_farmacia_or_admin)
    - vista: vista, usuario_vista (solo lectura)
    """
    # Admin y farmacia siempre tienen acceso de lectura
    if is_farmacia_or_admin(user):
        return True
    
    if not user or not user.is_authenticated:
        return False
    
    rol = (getattr(user, 'rol', '') or '').lower()
    
    # Roles de solo lectura global
    ROLES_VISTA = {'vista', 'usuario_vista'}
    
    if rol in ROLES_VISTA:
        return True
    
    # Verificar grupos
    group_names = {g.name.upper() for g in user.groups.all()}
    return 'VISTA_USER' in group_names


def get_user_centro(user):
    """Obtiene el centro asignado al usuario."""
    return getattr(user, 'centro', None) or getattr(getattr(user, 'profile', None), 'centro', None)


def _get_rol_efectivo(user):
    """
    ISS-DIRECTOR FIX: Obtiene el rol efectivo del usuario para validaciones de flujo.
    
    Esta función debe usarse en TODAS las validaciones de permisos del flujo
    para garantizar consistencia con lo que se envía al frontend.
    
    La lógica es idéntica a _resolve_rol en serializers.py pero devuelve
    el rol en minúsculas para usar con PERMISOS_FLUJO_REQUISICION.
    
    IMPORTANTE: Ahora infiere roles específicos (director_centro, administrador_centro, medico)
    basándose en los permisos personalizados del usuario cuando el campo rol está vacío.
    
    Returns:
        str: Rol normalizado en minúsculas (medico, administrador_centro, director_centro, etc.)
    """
    if not user:
        return 'sin_rol'
    if user.is_superuser:
        return 'admin'
    
    # Obtener rol del campo usuario
    rol_campo = (getattr(user, 'rol', '') or '').lower().strip()
    
    # Si hay rol en el campo, usarlo directamente
    if rol_campo and rol_campo not in ['null', 'none', '']:
        return rol_campo
    
    # ISS-DIRECTOR FIX: Inferir rol si el campo está vacío
    # Esto evita que usuarios con rol vacío pierdan sus permisos específicos
    
    # Si es staff pero no superuser, es farmacia
    if getattr(user, 'is_staff', False):
        return 'farmacia'
    
    # ISS-DIRECTOR FIX: Inferir rol específico por permisos personalizados
    # Verificar permisos del flujo para roles de centro específicos
    if getattr(user, 'perm_autorizar_director', None) is True:
        return 'director_centro'
    
    if getattr(user, 'perm_autorizar_admin', None) is True:
        return 'administrador_centro'
    
    if getattr(user, 'perm_crear_requisicion', None) is True:
        # Usuario con permiso de crear requisiciones y centro = médico
        centro = getattr(user, 'centro', None) or getattr(user, 'centro_id', None)
        if centro:
            return 'medico'
    
    # Si tiene centro asignado sin permisos específicos, es usuario de centro genérico
    centro = getattr(user, 'centro', None) or getattr(user, 'centro_id', None)
    if centro:
        return 'centro'
    
    # Default: vista (más restrictivo)
    return 'vista'


def invalidar_cache_dashboard(centro_id=None):
    """
    ISS-005: Invalida el caché del dashboard cuando hay cambios en datos.
    
    Se llama automáticamente al registrar movimientos, crear requisiciones, etc.
    
    Args:
        centro_id: ID del centro afectado (opcional). Si es None, invalida solo el global.
                   Si se pasa, invalida tanto el del centro como el global.
    """
    try:
        # Siempre invalidar el global
        cache.delete('dashboard_resumen_global')
        cache.delete('dashboard_graficas_global')
        
        # Si hay un centro específico, invalidar también ese
        if centro_id:
            cache.delete(f'dashboard_resumen_{centro_id}')
            cache.delete(f'dashboard_graficas_{centro_id}')
    except Exception as e:
        # No fallar si hay problemas con el caché
        logger.warning(f'Error al invalidar caché del dashboard: {e}')


def registrar_movimiento_stock(*, lote, tipo, cantidad, usuario=None, centro=None, requisicion=None, observaciones='', skip_centro_check=False, subtipo_salida=None, numero_expediente=None):
    """
    Helper central para registrar un movimiento y actualizar cantidad_actual del lote.
    
    ISS-002: Incluye validación de pertenencia de centro para prevenir manipulación
    de inventario entre centros.
    
    ISS-003 FIX: Los ajustes negativos requieren observaciones obligatorias con
    longitud mínima para auditoría y prevención de robo hormiga.
    
    MEJORA FLUJO 5: Soporte para subtipo_salida y numero_expediente para
    trazabilidad de pacientes en salidas por receta médica.
    
    Args:
        lote: Instancia del Lote a modificar
        tipo: 'entrada', 'salida' o 'ajuste'
        cantidad: Cantidad a mover (positivo)
        usuario: Usuario que realiza la operación (opcional)
        centro: Centro donde se registra el movimiento (opcional)
        requisicion: Requisición asociada (opcional)
        observaciones: Texto descriptivo (obligatorio para ajustes negativos)
        skip_centro_check: Si True, omite validación de pertenencia (solo para operaciones
                          de sistema/admin que ya validaron permisos)
        subtipo_salida: Tipo de salida (receta, consumo_interno, merma, etc.)
        numero_expediente: Número de expediente del paciente (para recetas)
    
    Raises:
        ValidationError: Si los datos son inválidos o hay problemas de autorización
    
    Returns:
        tuple: (movimiento_creado, lote_actualizado)
    """
    tipo_normalizado = (tipo or '').lower()
    if tipo_normalizado not in ('entrada', 'salida', 'ajuste'):
        raise serializers.ValidationError({'tipo': 'Tipo de movimiento no valido'})
    if cantidad is None:
        raise serializers.ValidationError({'cantidad': 'Cantidad requerida'})
    try:
        cantidad_int = int(cantidad)
    except (TypeError, ValueError):
        raise serializers.ValidationError({'cantidad': 'La cantidad debe ser un numero entero'})

    # =========================================================================
    # ISS-003 FIX: Validación de observaciones para ajustes negativos
    # =========================================================================
    # Los ajustes que reducen stock (negativos) requieren justificación obligatoria
    # para prevenir robo hormiga y asegurar trazabilidad de pérdidas
    LONGITUD_MINIMA_OBSERVACION = 10
    es_ajuste_negativo = tipo_normalizado == 'ajuste' and cantidad_int < 0
    
    if es_ajuste_negativo:
        if not observaciones or len(observaciones.strip()) < LONGITUD_MINIMA_OBSERVACION:
            raise serializers.ValidationError({
                'observaciones': f'Los ajustes negativos requieren una justificación de al menos {LONGITUD_MINIMA_OBSERVACION} caracteres. '
                                 f'Explique el motivo del ajuste (merma, caducidad, rotura, etc.)'
            })

    # =========================================================================
    # ISS-002: Validación de pertenencia de centro
    # =========================================================================
    # Si se pasa un centro explícito, verificar que el lote pertenezca a ese centro
    # Esto previene que usuarios de un centro manipulen stock de otros centros
    if not skip_centro_check and centro is not None:
        lote_centro = getattr(lote, 'centro', None)
        if lote_centro is not None and lote_centro.pk != centro.pk:
            logger.warning(
                f"Intento de operación de stock rechazado: "
                f"usuario={getattr(usuario, 'username', 'N/A')}, "
                f"lote_centro={lote_centro.pk}, centro_solicitado={centro.pk}"
            )
            raise serializers.ValidationError({
                'centro': 'El lote no pertenece al centro especificado. Operación no autorizada.'
            })
    
    # Si el usuario no es admin/farmacia, verificar que tenga acceso al centro del lote
    if not skip_centro_check and usuario is not None and hasattr(usuario, 'is_authenticated') and usuario.is_authenticated:
        if not is_farmacia_or_admin(usuario):
            user_centro = get_user_centro(usuario)
            lote_centro = getattr(lote, 'centro', None)
            if lote_centro is not None and user_centro is not None:
                if user_centro.pk != lote_centro.pk:
                    logger.warning(
                        f"Acceso no autorizado a lote de otro centro: "
                        f"usuario={usuario.username}, user_centro={user_centro.pk}, "
                        f"lote_centro={lote_centro.pk}"
                    )
                    raise serializers.ValidationError({
                        'lote': 'No tiene permiso para operar sobre lotes de otros centros.'
                    })

    delta = cantidad_int
    if tipo_normalizado == 'salida' and delta > 0:
        delta = -delta
    if tipo_normalizado == 'entrada' and delta < 0:
        delta = abs(delta)

    with transaction.atomic():
        lote_ref = Lote.objects.select_for_update().get(pk=lote.pk)
        stock_disponible = lote_ref.cantidad_actual

        if delta < 0 and abs(delta) > stock_disponible:
            raise serializers.ValidationError({
                'cantidad': f'Stock insuficiente en el lote (disponible {stock_disponible}).'
            })

        nuevo_stock = stock_disponible + delta
        if nuevo_stock < 0:
            raise serializers.ValidationError({'cantidad': 'La operacion dejaria el lote con stock negativo'})

        # Actualizar stock y estado de disponibilidad
        lote_ref.cantidad_actual = nuevo_stock
        
        # Para entradas, tambien actualizar cantidad_inicial si es necesario
        # Esto permite recibir stock adicional en lotes existentes
        update_fields = ['cantidad_actual', 'activo', 'updated_at']
        if tipo_normalizado == 'entrada' and nuevo_stock > lote_ref.cantidad_inicial:
            lote_ref.cantidad_inicial = nuevo_stock
            update_fields.append('cantidad_inicial')
        
        if nuevo_stock == 0:
            lote_ref.activo = False
        elif not lote_ref.activo:
            lote_ref.activo = True
        lote_ref.save(update_fields=update_fields)

        # Crear movimiento con campos correctos de la BD
        # ISS-MEDICO FIX v2: La cantidad siempre se guarda como positiva en BD
        # (hay un CHECK constraint chk_movimiento_cantidad_positiva)
        # El tipo (entrada/salida/ajuste) indica si suma o resta
        movimiento = Movimiento(
            tipo=tipo_normalizado,
            producto=lote_ref.producto,
            lote=lote_ref,
            centro_destino=centro if tipo_normalizado == 'entrada' else None,
            centro_origen=centro if tipo_normalizado != 'entrada' else None,
            requisicion=requisicion,
            usuario=usuario if usuario and getattr(usuario, 'is_authenticated', False) else None,
            cantidad=abs(cantidad_int),  # Siempre positivo, el tipo indica la operación
            motivo=observaciones or '',
            # MEJORA FLUJO 5: Campos de trazabilidad para pacientes
            subtipo_salida=subtipo_salida if tipo_normalizado == 'salida' else None,
            numero_expediente=numero_expediente if tipo_normalizado == 'salida' and subtipo_salida == 'receta' else None
        )
        # Guardar stock previo para evitar fallos de validacion al crear el movimiento
        movimiento._stock_pre_movimiento = stock_disponible
        movimiento.save()
        
        # ISS-005: Invalidar caché del dashboard al registrar movimientos
        centro_afectado = centro.id if centro else (lote_ref.centro.id if lote_ref.centro else None)
        invalidar_cache_dashboard(centro_afectado)

    return movimiento, lote_ref


class CustomPagination(PageNumberPagination):
    """Paginacin unificada para todos los listados del API."""
    page_size = PAGINATION_DEFAULT_PAGE_SIZE
    page_size_query_param = 'page_size'
    max_page_size = PAGINATION_MAX_PAGE_SIZE

    def paginate_queryset(self, queryset, request, view=None):
        try:
            return super().paginate_queryset(queryset, request, view=view)
        except InvalidPage:
            # Si la pgina solicitada no existe, devolver la ltima disponible sin 404
            self.page = self.paginator.page(self.paginator.num_pages or 1)
            self.request = request
            return list(self.page)

# ISS-002: UserSerializer eliminado - usar el de core.serializers
# from core.serializers import UserSerializer (si se necesita)

# NOTA: UserViewSet está en core/views.py - importar desde allí

class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.prefetch_related('lotes').all()  # HALLAZGO #8 FIX
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get_permissions(self):
        """
        Permisos personalizados por accion:
        - list, retrieve: IsAuthenticated
        - create, update, destroy, toggle_activo, importar_excel, exportar_excel, auditoria: IsFarmaciaRole
        """
        acciones_farmacia = [
            'create', 'update', 'partial_update', 'destroy', 
            'toggle_activo', 'importar_excel', 'exportar_excel', 'auditoria'
        ]
        if self.action in acciones_farmacia:
            from core.permissions import IsFarmaciaRole
            return [IsAuthenticated(), IsFarmaciaRole()]
        return [IsAuthenticated()]
    
    def get_object(self):
        """
        HALLAZGO #7 FIX: Validar acceso por centro en operaciones de escritura.
        Usuarios de centro solo pueden modificar productos si tienen permisos explícitos.
        """
        obj = super().get_object()
        
        # Solo validar en operaciones de escritura (create/update/delete)
        if self.action in ['update', 'partial_update', 'destroy']:
            user = self.request.user
            if not is_farmacia_or_admin(user) and not user.is_superuser:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied(
                    'Solo usuarios con rol farmacia/admin pueden modificar productos.'
                )
        
        return obj

    def get_queryset(self):
        queryset = Producto.objects.all()
        user = self.request.user
        
        # ISS-FIX: Determinar el centro para filtrar stock
        # Usuarios CENTRO solo ven productos con stock en SU centro (lo que farmacia les ha surtido)
        # Admin/Farmacia/Vista ven stock de farmacia central por defecto
        centro_param = self.request.query_params.get('centro')
        
        # ISS-FIX: Flag para determinar si el usuario es de centro
        es_usuario_centro = not is_farmacia_or_admin(user) and not user.is_superuser
        
        if es_usuario_centro:
            # Usuario de centro - filtrar stock solo por su centro
            user_centro = get_user_centro(user)
            if user_centro:
                # Anotar stock_calculado basado SOLO en lotes de su centro
                queryset = queryset.annotate(
                    stock_calculado=Coalesce(
                        Sum(
                            'lotes__cantidad_actual',
                            filter=Q(
                                lotes__activo=True,
                                lotes__cantidad_actual__gt=0,
                                lotes__centro=user_centro
                            )
                        ),
                        0
                    ),
                    # ISS-FIX: Contar lotes del centro específico del usuario
                    lotes_centro_count=Count(
                        'lotes',
                        filter=Q(
                            lotes__activo=True,
                            lotes__cantidad_actual__gt=0,
                            lotes__centro=user_centro
                        )
                    )
                )
                # ISS-FIX: Usuarios de centro SOLO ven productos con stock > 0 en su centro
                # Ya no ven todos los 76 productos con stock = 0
                queryset = queryset.filter(stock_calculado__gt=0)
            else:
                # Usuario sin centro asignado - no ve ningún producto
                queryset = queryset.annotate(
                    stock_calculado=Coalesce(Sum('lotes__cantidad_actual', filter=Q(pk__isnull=True)), 0),
                    lotes_centro_count=Count('lotes', filter=Q(pk__isnull=True))
                ).filter(stock_calculado__gt=0)  # Filtro imposible = 0 resultados
        else:
            # Admin/Farmacia/Vista - pueden ver stock global o por centro específico
            if centro_param:
                if centro_param == 'central':
                    # Solo stock de farmacia central (centro=NULL)
                    queryset = queryset.annotate(
                        stock_calculado=Coalesce(
                            Sum(
                                'lotes__cantidad_actual',
                                filter=Q(
                                    lotes__activo=True,
                                    lotes__cantidad_actual__gt=0,
                                    lotes__centro__isnull=True
                                )
                            ),
                            0
                        ),
                        lotes_centro_count=Count(
                            'lotes',
                            filter=Q(
                                lotes__activo=True,
                                lotes__cantidad_actual__gt=0,
                                lotes__centro__isnull=True
                            )
                        )
                    )
                else:
                    # Stock de un centro específico
                    queryset = queryset.annotate(
                        stock_calculado=Coalesce(
                            Sum(
                                'lotes__cantidad_actual',
                                filter=Q(
                                    lotes__activo=True,
                                    lotes__cantidad_actual__gt=0,
                                    lotes__centro_id=centro_param
                                )
                            ),
                            0
                        ),
                        lotes_centro_count=Count(
                            'lotes',
                            filter=Q(
                                lotes__activo=True,
                                lotes__cantidad_actual__gt=0,
                                lotes__centro_id=centro_param
                            )
                        )
                    )
            else:
                # Por defecto: stock de farmacia central (donde está el inventario principal)
                queryset = queryset.annotate(
                    stock_calculado=Coalesce(
                        Sum(
                            'lotes__cantidad_actual',
                            filter=Q(
                                lotes__activo=True,
                                lotes__cantidad_actual__gt=0,
                                lotes__centro__isnull=True
                            )
                        ),
                        0
                    ),
                    lotes_centro_count=Count(
                        'lotes',
                        filter=Q(
                            lotes__activo=True,
                            lotes__cantidad_actual__gt=0,
                            lotes__centro__isnull=True
                        )
                    )
                )
        
        activo = self.request.query_params.get('activo')
        if activo == 'true':
            queryset = queryset.filter(activo=True)
        elif activo == 'false':
            queryset = queryset.filter(activo=False)
        
        unidad = self.request.query_params.get('unidad_medida')
        if unidad and unidad != '':
            queryset = queryset.filter(unidad_medida=unidad)
        
        search = self.request.query_params.get('search')
        if search and search.strip():
            queryset = queryset.filter(
                Q(clave__icontains=search) | 
                Q(nombre__icontains=search)
            )

        stock_status = self.request.query_params.get('stock_status')
        if stock_status:
            # ISS-FIX: Usar stock_calculado ya anotado (respeta el centro del usuario)
            # Ya no es necesario crear stock_total_calc separado
            status_val = stock_status.lower()
            if status_val == 'sin_stock':
                queryset = queryset.filter(stock_calculado__lte=0)
            elif status_val == 'critico':
                queryset = queryset.filter(
                    stock_calculado__gt=0,
                    stock_minimo__gt=0,
                    stock_calculado__lt=F('stock_minimo') * 0.5
                )
            elif status_val == 'bajo':
                queryset = queryset.filter(
                    Q(
                        stock_minimo__gt=0,
                        stock_calculado__gte=F('stock_minimo') * 0.5,
                        stock_calculado__lt=F('stock_minimo')
                    ) | Q(
                        stock_minimo__lte=0,
                        stock_calculado__gt=0,
                        stock_calculado__lt=25
                    )
                )
            elif status_val == 'normal':
                queryset = queryset.filter(
                    Q(
                        stock_minimo__gt=0,
                        stock_calculado__gte=F('stock_minimo'),
                        stock_calculado__lte=F('stock_minimo') * 2
                    ) | Q(
                        stock_minimo__lte=0,
                        stock_calculado__gte=25,
                        stock_calculado__lt=100
                    )
                )
            elif status_val == 'alto':
                queryset = queryset.filter(
                    Q(
                        stock_minimo__gt=0,
                        stock_calculado__gt=F('stock_minimo') * 2
                    ) | Q(
                        stock_minimo__lte=0,
                        stock_calculado__gte=100
                    )
                )
        
        return queryset.order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        """
        Crea un nuevo producto.
        
        Validaciones:
        - Clave unica
        - Campos requeridos
        - Formato correcto
        """
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            
            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data, 
                status=status.HTTP_201_CREATED, 
                headers=headers
            )
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            logger.error(f"Error al crear producto: {str(e)}", exc_info=True)
            return Response({'error': 'Error al crear producto. Verifique los datos ingresados.'}, status=status.HTTP_400_BAD_REQUEST)
    
    def update(self, request, *args, **kwargs):
        """
        Actualiza un producto existente.
        
        Validaciones:
        - Clave unica (si se modifica)
        - Datos validos
        """
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            
            return Response(serializer.data)
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            logger.error(f"Error al actualizar producto: {str(e)}", exc_info=True)
            return Response({'error': 'Error al actualizar producto. Verifique los datos ingresados.'}, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, *args, **kwargs):
        """
        Elimina un producto.
        
        Validaciones:
        - No puede eliminarse si tiene lotes asociados
        - Confirmacion de eliminacion
        """
        instance = self.get_object()
        
        try:
            if instance.lotes.exists():
                return Response({
                    'error': 'No se puede eliminar el producto',
                    'razon': 'Tiene lotes asociados',
                    'sugerencia': 'Elimine primero los lotes o marque el producto como inactivo'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            instance.delete()
            return Response({'mensaje': 'Producto eliminado exitosamente'}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            logger.error(f"Error al eliminar producto: {str(e)}", exc_info=True)
            return Response({'error': 'Error al eliminar producto'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], url_path='toggle-activo')
    def toggle_activo(self, request, pk=None):
        """
        Activa o desactiva un producto.
        POST /api/productos/{id}/toggle-activo/
        
        Reglas:
        - No se puede desactivar un producto con stock disponible > 0
        - Usa update() directo para evitar validacion de otros campos
        """
        try:
            producto = self.get_object()
            nuevo_estado = not producto.activo
            
            # Si se va a desactivar, verificar que no tenga stock disponible
            if not nuevo_estado:  # Desactivando
                stock_disponible = producto.lotes.filter(
                    activo=True,
                    cantidad_actual__gt=0
                ).aggregate(total=Sum('cantidad_actual'))['total'] or 0
                
                if stock_disponible > 0:
                    return Response({
                        'error': 'No se puede desactivar el producto',
                        'razon': f'Tiene {stock_disponible} unidades en stock disponible',
                        'sugerencia': 'Transfiera o agote el inventario antes de desactivar'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Usar update() directo para evitar validacion de otros campos
            Producto.objects.filter(pk=producto.pk).update(activo=nuevo_estado)
            
            estado = 'activado' if nuevo_estado else 'desactivado'
            return Response({
                'mensaje': f'Producto {estado} exitosamente',
                'activo': nuevo_estado,
                'id': producto.id
            }, status=status.HTTP_200_OK)
        except Producto.DoesNotExist:
            return Response({'error': 'Producto no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error en toggle_activo: {str(e)}", exc_info=True)
            return Response({'error': f'Error interno: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'], url_path='auditoria')
    def auditoria(self, request, pk=None):
        """
        Obtiene el historial de cambios de un producto.
        GET /api/productos/{id}/auditoria/
        """
        try:
            from core.models import AuditoriaLogs
            producto = self.get_object()
            
            # Buscar logs de auditoria relacionados con este producto
            logs = AuditoriaLogs.objects.filter(
                Q(modelo='producto') | Q(modelo='core_producto') | Q(modelo='Producto'),
                objeto_id=str(producto.id)
            ).order_by('-timestamp')[:50]
            
            historial = []
            for log in logs:
                historial.append({
                    'id': log.id,
                    'fecha': log.timestamp.isoformat() if log.timestamp else None,
                    'usuario': log.usuario.get_full_name() or log.usuario.username if log.usuario else 'Sistema',
                    'accion': log.accion,
                    'cambios': log.datos_nuevos if log.datos_nuevos else None,
                    'ip': log.ip_address if log.ip_address else None,
                })
            
            return Response({
                'producto': {
                    'id': producto.id,
                    'clave': producto.clave,
                    'nombre': producto.nombre,
                },
                'historial': historial,
                'total': len(historial)
            })
        except Producto.DoesNotExist:
            return Response({'error': 'Producto no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error en auditoria: {str(e)}", exc_info=True)
            return Response({'error': 'Error al obtener auditoría'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'], url_path='lotes')
    def lotes(self, request, pk=None):
        """
        Obtiene los lotes de un producto específico con información de caducidad.
        GET /api/productos/{id}/lotes/
        
        ISS-FIX (lotes-centro): Mejorado para diagnóstico de problemas de lotes por centro.
        
        Retorna:
        - Lista de lotes con cantidad, número de lote, fecha de caducidad y semáforo de alerta
        """
        from datetime import date, timedelta
        try:
            producto = self.get_object()
            user = request.user
            
            # ISS-FIX: Logging para diagnóstico
            logger.info(
                f"ISS-LOTES-PROD: Consultando lotes de producto {producto.clave} (ID: {producto.pk}). "
                f"Usuario: {user.username}, Rol: {getattr(user, 'rol', 'N/A')}"
            )
            
            # Obtener lotes del producto
            lotes_queryset = producto.lotes.filter(
                activo=True,
                cantidad_actual__gt=0
            )
            
            # ISS-FIX: Si es usuario de centro, filtrar solo lotes de su centro
            if not is_farmacia_or_admin(user) and not user.is_superuser:
                user_centro = get_user_centro(user)
                if user_centro:
                    # ISS-FIX: Log del filtro aplicado
                    lotes_antes = lotes_queryset.count()
                    lotes_queryset = lotes_queryset.filter(centro=user_centro)
                    lotes_despues = lotes_queryset.count()
                    logger.info(
                        f"ISS-LOTES-PROD: Filtrado por centro {user_centro.nombre} (ID: {user_centro.pk}). "
                        f"Lotes antes: {lotes_antes}, después: {lotes_despues}"
                    )
                else:
                    logger.warning(
                        f"ISS-LOTES-PROD: Usuario {user.username} sin centro asignado. "
                        f"Retornando 0 lotes."
                    )
                    lotes_queryset = lotes_queryset.none()
            else:
                # ISS-FIX: Admin/farmacia ven todos los lotes
                logger.info(
                    f"ISS-LOTES-PROD: Usuario admin/farmacia, mostrando todos los lotes. "
                    f"Total: {lotes_queryset.count()}"
                )
            
            # Ordenar por fecha de caducidad (más próximos a vencer primero)
            lotes_queryset = lotes_queryset.order_by('fecha_caducidad')
            
            hoy = date.today()
            lotes_data = []
            
            for lote in lotes_queryset:
                dias_para_caducar = (lote.fecha_caducidad - hoy).days if lote.fecha_caducidad else None
                
                # Determinar semáforo de caducidad
                if dias_para_caducar is None:
                    alerta_caducidad = 'sin_fecha'
                elif dias_para_caducar < 0:
                    alerta_caducidad = 'vencido'
                elif dias_para_caducar <= 30:
                    alerta_caducidad = 'critico'
                elif dias_para_caducar <= 90:
                    alerta_caducidad = 'proximo'
                else:
                    alerta_caducidad = 'normal'
                
                lotes_data.append({
                    'id': lote.id,
                    'numero_lote': lote.numero_lote,
                    'cantidad_actual': lote.cantidad_actual,
                    'fecha_caducidad': lote.fecha_caducidad.isoformat() if lote.fecha_caducidad else None,
                    'dias_para_caducar': dias_para_caducar,
                    'alerta_caducidad': alerta_caducidad,
                    'centro_id': lote.centro_id,
                    'centro_nombre': lote.centro.nombre if lote.centro else 'Farmacia Central',
                })
                
                # ISS-FIX: Log detallado de cada lote
                logger.debug(
                    f"ISS-LOTES-PROD: Lote ID={lote.id}, NumLote={lote.numero_lote}, "
                    f"Cantidad={lote.cantidad_actual}, Centro={lote.centro_id}"
                )
            
            # ISS-FIX: Log del resultado final
            logger.info(
                f"ISS-LOTES-PROD: Retornando {len(lotes_data)} lotes para producto {producto.clave}. "
                f"Stock total: {sum(l['cantidad_actual'] for l in lotes_data)}"
            )
            
            return Response({
                'producto': {
                    'id': producto.id,
                    'clave': producto.clave,
                    'nombre': producto.nombre,
                    'unidad_medida': producto.unidad_medida,
                },
                'lotes': lotes_data,
                'total_lotes': len(lotes_data),
                'total_stock': sum(l['cantidad_actual'] for l in lotes_data),
            })
        except Producto.DoesNotExist:
            return Response({'error': 'Producto no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error en lotes: {str(e)}", exc_info=True)
            return Response({'error': 'Error al obtener lotes'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'], url_path='lotes-diagnostico')
    def lotes_diagnostico(self, request, pk=None):
        """
        ISS-FIX (lotes-centro): Endpoint de diagnóstico para problemas de lotes.
        GET /api/productos/{id}/lotes-diagnostico/
        
        Solo accesible para admin/farmacia. Muestra TODOS los lotes del producto
        sin filtros de centro para diagnóstico.
        """
        from datetime import date
        
        # Solo admin/farmacia puede usar este endpoint
        if not is_farmacia_or_admin(request.user) and not request.user.is_superuser:
            return Response({
                'error': 'Este endpoint solo está disponible para administradores'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            producto = self.get_object()
            
            # Obtener TODOS los lotes del producto (incluyendo inactivos y sin stock)
            todos_lotes = producto.lotes.all().order_by('centro_id', 'numero_lote')
            
            hoy = date.today()
            lotes_data = []
            
            for lote in todos_lotes:
                lotes_data.append({
                    'id': lote.id,
                    'numero_lote': lote.numero_lote,
                    'cantidad_inicial': lote.cantidad_inicial,
                    'cantidad_actual': lote.cantidad_actual,
                    'fecha_caducidad': lote.fecha_caducidad.isoformat() if lote.fecha_caducidad else None,
                    'activo': lote.activo,
                    'centro_id': lote.centro_id,
                    'centro_nombre': lote.centro.nombre if lote.centro else 'Farmacia Central (NULL)',
                    'created_at': lote.created_at.isoformat() if lote.created_at else None,
                    'updated_at': lote.updated_at.isoformat() if lote.updated_at else None,
                })
            
            # Agrupar por centro
            lotes_por_centro = {}
            for lote in lotes_data:
                centro_key = lote['centro_nombre']
                if centro_key not in lotes_por_centro:
                    lotes_por_centro[centro_key] = {
                        'centro_id': lote['centro_id'],
                        'lotes': [],
                        'total_stock': 0,
                        'total_lotes': 0,
                    }
                lotes_por_centro[centro_key]['lotes'].append(lote)
                lotes_por_centro[centro_key]['total_stock'] += lote['cantidad_actual']
                lotes_por_centro[centro_key]['total_lotes'] += 1
            
            return Response({
                'producto': {
                    'id': producto.id,
                    'clave': producto.clave,
                    'nombre': producto.nombre,
                },
                'diagnostico': {
                    'total_lotes_bd': len(lotes_data),
                    'total_stock_global': sum(l['cantidad_actual'] for l in lotes_data),
                    'lotes_activos': sum(1 for l in lotes_data if l['activo']),
                    'lotes_con_stock': sum(1 for l in lotes_data if l['cantidad_actual'] > 0),
                },
                'lotes_por_centro': lotes_por_centro,
                'todos_los_lotes': lotes_data,
            })
            
        except Producto.DoesNotExist:
            return Response({'error': 'Producto no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error en lotes_diagnostico: {str(e)}", exc_info=True)
            return Response({'error': f'Error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='exportar-excel')
    def exportar_excel(self, request):
        """
        Exporta todos los productos a un archivo Excel.
        
        Columnas alineadas con schema real de productos:
        - #, Codigo Barras, Nombre, Categoria, Unidad, Stock Minimo, Stock Actual, 
          Sustancia Activa, Presentacion, Requiere Receta, Controlado, Lotes, Estado
        """
        try:
            productos = self.get_queryset()
            
            # Crear libro de Excel
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Productos'
            
            # Encabezados alineados con schema de Supabase
            headers = ['#', 'Clave', 'Nombre', 'Categoria', 'Unidad Medida', 
                       'Stock Minimo', 'Stock Actual', 'Sustancia Activa', 'Presentacion',
                       'Concentracion', 'Via Admin', 'Requiere Receta', 'Controlado', 
                       'Lotes Activos', 'Estado']
            ws.append(headers)
            
            # Estilo de encabezados
            header_fill = PatternFill(start_color='632842', end_color='632842', fill_type='solid')
            header_font = Font(bold=True, color='FFFFFF', size=12)
            
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Datos de productos
            for idx, producto in enumerate(productos, start=1):
                stock_actual = producto.lotes.filter(activo=True).aggregate(total=Sum('cantidad_actual'))['total'] or 0
                lotes_activos = producto.lotes.filter(activo=True, cantidad_actual__gt=0).count()
                
                ws.append([
                    idx,
                    producto.clave or '',
                    producto.nombre,
                    producto.categoria or '',
                    producto.unidad_medida,
                    producto.stock_minimo,
                    stock_actual,
                    producto.sustancia_activa or '',
                    producto.presentacion or '',
                    producto.concentracion or '',
                    producto.via_administracion or '',
                    'Sí' if producto.requiere_receta else 'No',
                    'Sí' if producto.es_controlado else 'No',
                    lotes_activos,
                    'Activo' if producto.activo else 'Inactivo'
                ])
                
                # Colorear fila si el stock esta por debajo del minimo
                if stock_actual < producto.stock_minimo:
                    for col in range(1, 16):
                        ws.cell(row=idx+1, column=col).fill = PatternFill(
                            start_color='FFF4E6', 
                            end_color='FFF4E6', 
                            fill_type='solid'
                        )
            
            # Ajustar anchos de columna
            ws.column_dimensions['A'].width = 6
            ws.column_dimensions['B'].width = 18
            ws.column_dimensions['C'].width = 40
            ws.column_dimensions['D'].width = 18
            ws.column_dimensions['E'].width = 14
            ws.column_dimensions['F'].width = 12
            ws.column_dimensions['G'].width = 12
            ws.column_dimensions['H'].width = 20
            ws.column_dimensions['I'].width = 14
            ws.column_dimensions['J'].width = 14
            ws.column_dimensions['K'].width = 14
            ws.column_dimensions['L'].width = 14
            ws.column_dimensions['M'].width = 12
            ws.column_dimensions['N'].width = 12
            ws.column_dimensions['O'].width = 10
            
            # Generar respuesta
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename=Productos_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            wb.save(response)
            
            return response
            
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            return Response({
                'error': 'Error al exportar productos',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], url_path='importar-excel')
    def importar_excel(self, request):
        """
        Importa productos desde archivo Excel con detección automática de columnas.
        
        Columnas reconocidas (flexibles, no importa el orden):
        - Clave (requerido): código único del producto
        - Nombre (requerido): nombre del producto
        - Unidad (requerido): unidad de medida (CAJA, PIEZA, etc.)
        - Stock Minimo (opcional): cantidad mínima en inventario
        - Categoria (opcional): medicamento, material_curacion, insumo
        - Sustancia Activa, Presentacion, Concentracion, Via Admin (opcionales)
        - Requiere Receta, Controlado (opcionales): Si/No
        - Estado/Activo (opcional): Activo/Inactivo
        
        Limites de seguridad:
        - Tamano maximo: 10MB
        - Filas maximas: 5000
        - Extensiones: .xlsx, .xls
        """
        file = request.FILES.get('file')
        
        # HALLAZGO #13 FIX: Validar archivo CON magic bytes
        es_valido, error_msg = validar_archivo_excel(file)
        if not es_valido:
            logger.warning(f"HALLAZGO #13: Archivo Excel rechazado en importar_excel: {error_msg}")
            return Response({
                'error': 'Archivo invalido',
                'mensaje': error_msg
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # ISS-001: Usar carga segura con limite real de bytes
            wb, error_carga = cargar_workbook_seguro(file)
            if wb is None:
                return Response({
                    'error': 'Error al procesar archivo',
                    'mensaje': error_carga
                }, status=status.HTTP_400_BAD_REQUEST)
            
            ws = wb.active
            
            # Validar numero de filas
            filas_validas, error_filas, num_filas = validar_filas_excel(ws)
            if not filas_validas:
                wb.close()
                return Response({
                    'error': 'Archivo demasiado grande',
                    'mensaje': error_filas
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # ISS-FIX: Detectar fila de encabezados automáticamente
            COLUMN_ALIASES = {
                'clave': ['clave', 'codigo', 'código', 'clave producto', 'cod', 'id producto'],
                'nombre': ['nombre', 'nombre producto', 'descripcion', 'descripción', 'producto'],
                'unidad_medida': ['unidad', 'unidad medida', 'um', 'unidad de medida', 'medida'],
                'stock_minimo': ['stock minimo', 'stock mínimo', 'stock min', 'minimo', 'mínimo'],
                'categoria': ['categoria', 'categoría', 'tipo', 'clasificacion'],
                'sustancia_activa': ['sustancia activa', 'sustancia', 'principio activo', 'activo'],
                'presentacion': ['presentacion', 'presentación', 'forma'],
                'concentracion': ['concentracion', 'concentración', 'dosis'],
                'via_administracion': ['via admin', 'via administracion', 'vía admin', 'administracion', 'via'],
                'requiere_receta': ['requiere receta', 'receta', 'req receta'],
                'es_controlado': ['controlado', 'es controlado', 'control'],
                'estado': ['estado', 'activo', 'status'],
            }
            
            def normalizar_header(val):
                if not val:
                    return ''
                return str(val).lower().strip().replace('_', ' ').replace('-', ' ')
            
            # Buscar fila con encabezados (primeras 5 filas)
            header_row_idx = 1
            col_map = {}
            
            for row_num in range(1, min(6, ws.max_row + 1)):
                row_values = [cell.value for cell in ws[row_num]]
                headers_encontrados = 0
                temp_map = {}
                
                for col_idx, val in enumerate(row_values):
                    header_norm = normalizar_header(val)
                    if not header_norm:
                        continue
                    
                    for field, aliases in COLUMN_ALIASES.items():
                        if header_norm in aliases or any(alias in header_norm for alias in aliases):
                            if field not in temp_map:
                                temp_map[field] = col_idx
                                headers_encontrados += 1
                            break
                
                # Si encontramos al menos 2 columnas clave (clave, nombre), es la fila de headers
                if headers_encontrados >= 2 and ('clave' in temp_map or 'nombre' in temp_map):
                    header_row_idx = row_num
                    col_map = temp_map
                    break
            
            # Si no hay mapa, usar orden por defecto
            if not col_map:
                col_map = {
                    'clave': 0, 'nombre': 1, 'unidad_medida': 2, 'stock_minimo': 3,
                    'categoria': 4, 'sustancia_activa': 5, 'presentacion': 6,
                    'concentracion': 7, 'via_administracion': 8, 'requiere_receta': 9,
                    'es_controlado': 10, 'estado': 11
                }
            
            def get_val(row, field, default=None):
                if field not in col_map:
                    return default
                idx = col_map[field]
                if idx < len(row):
                    val = row[idx]
                    return val if val not in [None, '', 'None'] else default
                return default
            
            creados = 0
            actualizados = 0
            errores = []
            exitos = []
            
            # ISS-019: Envolver en transacción atómica
            with transaction.atomic():
                for row_idx, row in enumerate(ws.iter_rows(min_row=header_row_idx + 1, values_only=True), start=header_row_idx + 1):
                    try:
                        # Saltar filas vacías
                        if not row or all(cell is None or str(cell).strip() == '' for cell in row):
                            continue
                        
                        # Extraer valores usando el mapa de columnas
                        clave = get_val(row, 'clave')
                        nombre = get_val(row, 'nombre')
                        unidad_medida = get_val(row, 'unidad_medida')
                        stock_minimo = get_val(row, 'stock_minimo')
                        categoria = get_val(row, 'categoria')
                        sustancia_activa = get_val(row, 'sustancia_activa')
                        presentacion = get_val(row, 'presentacion')
                        concentracion = get_val(row, 'concentracion')
                        via_administracion = get_val(row, 'via_administracion')
                        requiere_receta = get_val(row, 'requiere_receta')
                        es_controlado = get_val(row, 'es_controlado')
                        estado = get_val(row, 'estado')
                        
                        # Validar campos requeridos
                        if not clave:
                            errores.append({'fila': row_idx, 'error': 'Clave es obligatoria'})
                            continue
                        if not nombre:
                            errores.append({'fila': row_idx, 'error': 'Nombre es obligatorio'})
                            continue
                        
                        # ISS-FIX: Permitir texto libre en unidad de medida para mejor manejo de farmacia
                        # Ejemplos: "CAJA CON 7 OVULOS", "GOTERO CON 15 MILILITROS"
                        unidad_limpia = str(unidad_medida).strip().upper() if unidad_medida else 'PIEZA'

                        try:
                            stock_min = int(float(stock_minimo)) if stock_minimo not in [None, ''] else 10
                            if stock_min < 0:
                                stock_min = 0
                        except Exception:
                            stock_min = 10  # Default

                        # Parsear campos booleanos
                        def parse_bool(val):
                            if val is None:
                                return False
                            return str(val).lower() in ['sí', 'si', 'true', '1', 'yes', 's', 'x', 'activo']

                        # Validar y normalizar categoría
                        from core.constants import CATEGORIAS_VALIDAS
                        categoria_limpia = str(categoria).strip().lower().replace(' ', '_') if categoria else 'medicamento'
                        if categoria_limpia not in CATEGORIAS_VALIDAS:
                            categoria_limpia = 'medicamento'

                        # Preparar datos
                        datos = {
                            'nombre': str(nombre).strip()[:500],
                            'unidad_medida': unidad_limpia,
                            'stock_minimo': stock_min,
                            'categoria': categoria_limpia,
                            'sustancia_activa': str(sustancia_activa).strip()[:200] if sustancia_activa else '',
                            'presentacion': str(presentacion).strip()[:200] if presentacion else '',
                            'concentracion': str(concentracion).strip()[:100] if concentracion else '',
                            'via_administracion': str(via_administracion).strip()[:50] if via_administracion else '',
                            'requiere_receta': parse_bool(requiere_receta),
                            'es_controlado': parse_bool(es_controlado),
                            'activo': str(estado).lower() in ['activo', 'sí', 'si', 'true', '1', 'yes', 's'] if estado else True
                        }
                        
                        # Ya no es necesario guardar en presentación porque unidad_medida acepta texto completo
                        
                        # Crear o actualizar producto
                        clave_limpia = str(clave).strip()[:50].upper()
                        
                        producto, created = Producto.objects.update_or_create(
                            clave=clave_limpia,
                            defaults=datos
                        )
                        
                        if created:
                            creados += 1
                        else:
                            actualizados += 1
                        exitos.append({'fila': row_idx, 'producto_id': producto.id, 'clave': producto.clave})
                            
                    except Exception as e:
                        errores.append({'fila': row_idx, 'error': str(e)})
            
            return Response({
                'mensaje': 'Importacion completada',
                'resumen': {
                    'creados': creados,
                    'actualizados': actualizados,
                    'total_procesados': creados + actualizados,
                    'total_errores': len(errores)
                },
                'exitos': exitos,
                'errores': errores,
                'exito': len(errores) == 0
            }, status=status.HTTP_200_OK if len(errores) == 0 else status.HTTP_207_MULTI_STATUS)
            
        except Exception as e:
            return Response({
                'error': 'Error al procesar archivo',
                'mensaje': str(e),
                'sugerencia': 'Verifique que el archivo tenga formato Excel válido con columnas: Clave, Nombre, Unidad, etc.'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='plantilla')
    def plantilla_productos(self, request):
        """
        Descarga plantilla Excel para importación de productos.
        
        Columnas:
        - Clave (REQUERIDO, único) - Código identificador del producto
        - Nombre (REQUERIDO) - Nombre del medicamento o insumo
        - Unidad (opcional) - Unidad de medida (PIEZA, CAJA, FRASCO, SOBRE, AMPOLLETA, TABLETA, CAPSULA, ML, GR)
        - Stock Minimo (opcional, default: 10) - Cantidad mínima de alerta
        - Categoria (opcional) - medicamento, material_curacion, insumo, equipo, otro
        - Sustancia Activa (opcional) - Principio activo
        - Presentacion (opcional) - Forma farmacéutica
        - Concentracion (opcional) - Dosis del principio activo
        - Via Admin (opcional) - Vía de administración
        - Requiere Receta (opcional) - Sí/No
        - Controlado (opcional) - Sí/No
        - Estado (opcional, default: Activo) - Activo/Inactivo
        """
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Productos'
        
        # Headers que coinciden con importar_excel
        headers = [
            'Clave', 'Nombre', 'Unidad', 'Stock Minimo', 'Categoria',
            'Sustancia Activa', 'Presentacion', 'Concentracion', 
            'Via Admin', 'Requiere Receta', 'Controlado', 'Estado'
        ]
        ws.append(headers)
        
        # ============================================================
        # FILAS DE EJEMPLO - ELIMINAR ANTES DE USAR CON DATOS REALES
        # Estas filas son solo para mostrar el formato correcto.
        # ============================================================
        ws.append([
            'PRUEBA001', '[EJEMPLO] Paracetamol 500mg - ELIMINAR', 'CAJA', 50, 'medicamento',
            'Paracetamol', 'Tableta', '500 mg',
            'oral', 'No', 'No', 'Activo'
        ])
        ws.append([
            'PRUEBA002', '[EJEMPLO] Ibuprofeno 400mg - ELIMINAR', 'FRASCO', 30, 'medicamento',
            'Ibuprofeno', 'Cápsula', '400 mg',
            'oral', 'No', 'No', 'Activo'
        ])
        ws.append([
            'PRUEBA003', '[EJEMPLO] Jeringa 10ml - ELIMINAR', 'PIEZA', 100, 'material_curacion',
            '', '', '',
            '', 'No', 'No', 'Activo'
        ])
        
        # Aplicar formato a headers
        from openpyxl.styles import Font, PatternFill, Alignment
        header_font = Font(bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='9F2241', end_color='9F2241', fill_type='solid')
        for col in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col)
            cell.font = header_font
            cell.fill = header_fill
        
        # Estilo para filas de ejemplo (gris, itálica - sin fondo de color)
        example_font = Font(italic=True, color='888888')
        for row_num in range(2, 5):  # Filas 2, 3, 4 (ejemplos)
            for col in range(1, len(headers) + 1):
                cell = ws.cell(row=row_num, column=col)
                cell.font = example_font
        
        # Ajustar ancho de columnas
        column_widths = {
            'A': 15,  # Clave
            'B': 45,  # Nombre (más ancho para ver el texto de ejemplo)
            'C': 12,  # Unidad
            'D': 14,  # Stock Minimo
            'E': 18,  # Categoria
            'F': 20,  # Sustancia Activa
            'G': 15,  # Presentacion
            'H': 15,  # Concentracion
            'I': 12,  # Via Admin
            'J': 15,  # Requiere Receta
            'K': 12,  # Controlado
            'L': 10,  # Estado
        }
        for col_letter, width in column_widths.items():
            ws.column_dimensions[col_letter].width = width
        
        # ============================================================
        # HOJA DE INSTRUCCIONES
        # ============================================================
        ws_instrucciones = wb.create_sheet(title='INSTRUCCIONES')
        
        instrucciones = [
            ['╔════════════════════════════════════════════════════════════════════╗'],
            ['║    INSTRUCCIONES PARA IMPORTACIÓN DE PRODUCTOS                    ║'],
            ['╚════════════════════════════════════════════════════════════════════╝'],
            [''],
            ['⚠️  IMPORTANTE: Las filas amarillas en la hoja "Productos" son EJEMPLOS.'],
            ['    ELIMÍNELAS antes de cargar sus datos reales.'],
            [''],
            ['────────────────────────────────────────────────────────────────────────'],
            ['COLUMNAS REQUERIDAS (obligatorias):'],
            ['────────────────────────────────────────────────────────────────────────'],
            ['• Clave      - Código único del producto (ej: 001, MED001, ABC123)'],
            ['• Nombre     - Nombre completo del producto'],
            [''],
            ['────────────────────────────────────────────────────────────────────────'],
            ['COLUMNAS OPCIONALES:'],
            ['────────────────────────────────────────────────────────────────────────'],
            ['• Unidad         - CAJA, PIEZA, FRASCO, SOBRE, TABLETA, etc. (default: PIEZA)'],
            ['• Stock Minimo   - Cantidad mínima para alertas (default: 10)'],
            ['• Categoria      - medicamento, material_curacion, insumo (default: medicamento)'],
            ['• Sustancia Activa - Principio activo del medicamento'],
            ['• Presentacion   - Forma farmacéutica (tableta, cápsula, jarabe, etc.)'],
            ['• Concentracion  - Dosis (ej: 500 mg, 10 ml)'],
            ['• Via Admin      - oral, intravenosa, tópica, etc.'],
            ['• Requiere Receta - Sí / No (default: No)'],
            ['• Controlado     - Sí / No (default: No)'],
            ['• Estado         - Activo / Inactivo (default: Activo)'],
            [''],
            ['────────────────────────────────────────────────────────────────────────'],
            ['NOTAS:'],
            ['────────────────────────────────────────────────────────────────────────'],
            ['• Si la CLAVE ya existe, el producto se ACTUALIZARÁ con los nuevos datos.'],
            ['• Si la CLAVE no existe, se CREARÁ un nuevo producto.'],
            ['• Máximo 5000 productos por archivo.'],
            ['• Tamaño máximo de archivo: 10 MB.'],
            ['• Formatos aceptados: .xlsx, .xls'],
            [''],
        ]
        
        for row in instrucciones:
            ws_instrucciones.append(row)
        
        # Formato de instrucciones
        ws_instrucciones.column_dimensions['A'].width = 80
        for row in ws_instrucciones.iter_rows():
            for cell in row:
                cell.alignment = Alignment(wrap_text=False)
        
        # Poner hoja de Productos como activa
        wb.active = ws
        
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=Plantilla_Productos.xlsx'
        wb.save(response)
        return response


class CentroViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar centros penitenciarios.
    
    Funcionalidades:
    - CRUD completo
    - Busqueda por clave, nombre y direccion
    - Filtrado por estado activo/inactivo
    - Exportar a Excel con formato profesional
    - Importar desde Excel con validaciones
    - Obtener requisiciones por centro
    
    ISS-MEDICO FIX: Roles de centro (medico, etc.) reciben 403 en GET.
    Solo admin/farmacia/vista pueden ver el catálogo de centros.
    """
    queryset = Centro.objects.all()
    serializer_class = CentroSerializer
    # ISS-MEDICO FIX: Bloquear acceso a roles de centro (incluyendo médico)
    permission_classes = [IsFarmaciaAdminOrVistaReadOnly]
    pagination_class = CustomPagination

    def _user_centro(self, user):
        return getattr(user, 'centro', None) or getattr(getattr(user, 'profile', None), 'centro', None)

    def get_queryset(self):
        """Filtra centros segun parametros"""
        queryset = Centro.objects.all()
        user = getattr(self.request, 'user', None)
        
        # Admin, Farmacia y Superusuarios pueden ver todos los centros
        # Otros usuarios solo ven su propio centro
        if user and not user.is_superuser and not is_farmacia_or_admin(user):
            user_centro = self._user_centro(user)
            if user_centro:
                queryset = queryset.filter(id=user_centro.id)
            else:
                return Centro.objects.none()
        
        # Filtro por busqueda
        search = self.request.query_params.get('search')
        if search and search.strip():
            queryset = queryset.filter(
                Q(nombre__icontains=search) | 
                Q(direccion__icontains=search) |
                Q(email__icontains=search) |
                Q(telefono__icontains=search)
            )
        
        # Filtro por estado activo
        activo = self.request.query_params.get('activo')
        if activo == 'true':
            queryset = queryset.filter(activo=True)
        elif activo == 'false':
            queryset = queryset.filter(activo=False)
        
        # Ordenamiento (respeta parámetro del frontend)
        ordering = self.request.query_params.get('ordering', '-created_at')
        valid_orderings = ['nombre', '-nombre', 'created_at', '-created_at', 'activo', '-activo']
        if ordering in valid_orderings:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by('-created_at')
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Crea un nuevo centro"""
        try:
            logger.debug(f"CREAR CENTRO - Body: {request.data}")
            
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            centro = serializer.save()
            
            logger.info(f"Centro creado: {centro.clave} - {centro.nombre}")
            
            return Response({
                'mensaje': 'Centro creado exitosamente',
                'centro': CentroSerializer(centro).data
            }, status=status.HTTP_201_CREATED)
            
        except serializers.ValidationError as e:
            logger.warning(f"Error de validación al crear centro: {e.detail}")
            return Response({
                'error': 'Error de validacion',
                'detalles': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.exception(f"Error inesperado al crear centro: {e}")
            # traceback removido por seguridad (ISS-008)
            return Response({
                'error': 'Error al crear centro',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        """Actualiza un centro existente"""
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            
            return Response({
                'mensaje': 'Centro actualizado exitosamente',
                'centro': serializer.data
            })
        except serializers.ValidationError as e:
            return Response(
                {'error': 'Error de validacion', 'detalles': e.detail},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            return Response(
                {'error': 'Error al actualizar centro', 'mensaje': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, *args, **kwargs):
        """
        Elimina un centro.
        
        Validaciones:
        - No puede eliminarse si tiene requisiciones asociadas (como origen o destino)
        - No puede eliminarse si tiene usuarios asignados
        """
        instance = self.get_object()
        
        try:
            # Verificar requisiciones (como origen O destino)
            has_req_origen = hasattr(instance, 'requisiciones_origen') and instance.requisiciones_origen.exists()
            has_req_destino = hasattr(instance, 'requisiciones_destino') and instance.requisiciones_destino.exists()
            
            if has_req_origen or has_req_destino:
                total_origen = instance.requisiciones_origen.count() if has_req_origen else 0
                total_destino = instance.requisiciones_destino.count() if has_req_destino else 0
                total_requisiciones = total_origen + total_destino
                
                # Contar requisiciones activas
                activas_origen = instance.requisiciones_origen.exclude(
                    estado__in=['CANCELADA', 'SURTIDA']
                ).count() if has_req_origen else 0
                activas_destino = instance.requisiciones_destino.exclude(
                    estado__in=['CANCELADA', 'SURTIDA']
                ).count() if has_req_destino else 0
                requisiciones_activas = activas_origen + activas_destino
                
                return Response({
                    'error': 'No se puede eliminar el centro',
                    'razon': 'Tiene requisiciones asociadas',
                    'total_requisiciones': total_requisiciones,
                    'como_origen': total_origen,
                    'como_destino': total_destino,
                    'requisiciones_activas': requisiciones_activas,
                    'sugerencia': 'Marque el centro como inactivo en lugar de eliminarlo'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Verificar usuarios asignados (solo activos, consistente con serializer)
            if hasattr(instance, 'usuarios'):
                usuarios_activos = instance.usuarios.filter(is_active=True)
                if usuarios_activos.exists():
                    total_usuarios = usuarios_activos.count()
                    
                    return Response({
                        'error': 'No se puede eliminar el centro',
                        'razon': 'Tiene usuarios activos asignados',
                        'total_usuarios': total_usuarios,
                        'sugerencia': 'Reasigne los usuarios a otro centro o marque el centro como inactivo'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Verificar lotes con stock activo
            if hasattr(instance, 'lotes'):
                lotes_con_stock = instance.lotes.filter(activo=True, cantidad_actual__gt=0).count()
                if lotes_con_stock > 0:
                    return Response({
                        'error': 'No se puede eliminar el centro',
                        'razon': 'Tiene lotes con stock disponible',
                        'lotes_con_stock': lotes_con_stock,
                        'sugerencia': 'Transfiera el inventario a otro centro o marque el centro como inactivo'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Si no tiene relaciones, se puede eliminar
            clave_eliminada = instance.clave
            nombre_eliminado = instance.nombre
            instance.delete()
            
            return Response({
                'mensaje': 'Centro eliminado exitosamente',
                'centro_eliminado': f"{clave_eliminada} - {nombre_eliminado}"
            }, status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            return Response({
                'error': 'Error al eliminar centro',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='toggle-activo')
    def toggle_activo(self, request, pk=None):
        """
        Activa o desactiva un centro.
        POST /api/centros/{id}/toggle-activo/
        
        Usa update() directo para evitar validacion de otros campos.
        """
        try:
            centro = self.get_object()
            nuevo_estado = not centro.activo
            
            # Usar update() directo para evitar validacion de otros campos
            Centro.objects.filter(pk=centro.pk).update(activo=nuevo_estado)
            
            estado = 'activado' if nuevo_estado else 'desactivado'
            return Response({
                'mensaje': f'Centro {estado} exitosamente',
                'activo': nuevo_estado,
                'id': centro.id,
                'clave': centro.clave,
                'nombre': centro.nombre
            }, status=status.HTTP_200_OK)
        except Centro.DoesNotExist:
            return Response({'error': 'Centro no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error en toggle_activo centro: {str(e)}", exc_info=True)
            return Response({'error': f'Error interno: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def inventario(self, request, pk=None):
        """Devuelve inventario resumido del centro a partir de lotes asociados a movimientos del centro."""
        centro = self.get_object()
        user_centro = self._user_centro(request.user)
        if not request.user.is_superuser:
            if not user_centro or user_centro.id != centro.id:
                return Response({'error': 'Solo puedes ver inventario de tu centro'}, status=status.HTTP_403_FORBIDDEN)

        # Lotes que han tenido movimientos en este centro
        lote_ids = Movimiento.objects.filter(
            Q(centro_origen=centro) | Q(centro_destino=centro)
        ).values_list('lote_id', flat=True)
        lotes = Lote.objects.filter(
            Q(id__in=lote_ids) | Q(centro=centro),
            activo=True,
            cantidad_actual__gt=0
        ).select_related('producto')

        inventario_dict = {}
        for lote in lotes:
            prod = lote.producto
            item = inventario_dict.setdefault(prod.id, {
                'producto_id': prod.id,
                'clave': prod.clave,
                'producto': prod.nombre,
                'cantidad_disponible': 0,
                'lote_proximo_caducar': None,
                'fecha_caducidad': None,
            })
            item['cantidad_disponible'] += lote.cantidad_actual
            if lote.fecha_caducidad:
                fecha_actual = item['fecha_caducidad']
                if fecha_actual is None or lote.fecha_caducidad < fecha_actual:
                    item['lote_proximo_caducar'] = lote.numero_lote
                    item['fecha_caducidad'] = lote.fecha_caducidad

        # Si no hay lotes asociados, caer al agregado por movimientos para no dejar vacio
        inventario = list(inventario_dict.values())
        if not inventario:
            movimientos = Movimiento.objects.filter(
                Q(centro_origen=centro) | Q(centro_destino=centro)
            )
            agregados = movimientos.values('lote__producto').annotate(cantidad=Coalesce(Sum('cantidad'), 0))
            for item in agregados:
                producto = Producto.objects.filter(id=item['lote__producto']).first()
                if not producto:
                    continue
                inventario.append({
                    'producto_id': producto.id,
                    'clave': producto.clave,
                    'producto': producto.nombre,
                    'cantidad_disponible': max(0, item['cantidad']),
                    'lote_proximo_caducar': None,
                    'fecha_caducidad': None,
                })

        return Response({
            'centro': centro.nombre,
            'centro_id': centro.id,
            'total_productos': len(inventario),
            'inventario': inventario
        })
    
    @action(detail=False, methods=['get'], url_path='exportar-excel')
    def exportar_excel(self, request):
        """
        Exporta todos los centros a Excel con formato profesional.
        
        Columnas (alineadas con BD):
        - #, Nombre, Direccion, Telefono, Email, Total Requisiciones, Estado
        """
        try:
            centros = self.get_queryset()
            
            # Crear libro de Excel
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Centros Penitenciarios'
            
            # Titulo del reporte
            ws.merge_cells('A1:G1')
            titulo_cell = ws['A1']
            titulo_cell.value = 'REPORTE DE CENTROS PENITENCIARIOS'
            titulo_cell.font = Font(bold=True, size=14, color='632842')
            titulo_cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Fecha de generacion
            ws.merge_cells('A2:G2')
            fecha_cell = ws['A2']
            fecha_cell.value = f'Generado el {timezone.now().strftime("%d/%m/%Y %H:%M")}'

            fecha_cell.font = Font(size=10, italic=True)
            fecha_cell.alignment = Alignment(horizontal='center')
            
            # Espacio
            ws.append([])
            
            # Encabezados (sin Clave - campo no existe en BD)
            headers = ['#', 'Nombre', 'Direccion', 'Telefono', 'Email', 'Total Requisiciones', 'Estado']
            ws.append(headers)
            
            # Estilo de encabezados
            header_fill = PatternFill(start_color='632842', end_color='632842', fill_type='solid')
            header_font = Font(bold=True, color='FFFFFF', size=11)
            header_alignment = Alignment(horizontal='center', vertical='center')
            
            for col_num, cell in enumerate(ws[4], 1):
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = header_alignment
            
            # Datos de centros
            for idx, centro in enumerate(centros, start=1):
                # Calcular total de requisiciones (origen + destino, consistente con serializer)
                total_requisiciones = 0
                if hasattr(centro, 'requisiciones_origen'):
                    total_requisiciones += centro.requisiciones_origen.count()
                if hasattr(centro, 'requisiciones_destino'):
                    total_requisiciones += centro.requisiciones_destino.count()
                
                ws.append([
                    idx,
                    centro.nombre,
                    centro.direccion or '',
                    centro.telefono or '',
                    getattr(centro, 'email', '') or '',
                    total_requisiciones,
                    'Activo' if centro.activo else 'Inactivo'
                ])
                
                # Estilo para filas
                row_num = idx + 4
                for cell in ws[row_num]:
                    cell.alignment = Alignment(vertical='center')
                    
                # Colorear estado
                estado_cell = ws.cell(row=row_num, column=7)
                if centro.activo:
                    estado_cell.fill = PatternFill(start_color='D4EDDA', end_color='D4EDDA', fill_type='solid')
                    estado_cell.font = Font(color='155724', bold=True)
                else:
                    estado_cell.fill = PatternFill(start_color='F8D7DA', end_color='F8D7DA', fill_type='solid')
                    estado_cell.font = Font(color='721C24', bold=True)
            
            # Ajustar anchos de columna
            ws.column_dimensions['A'].width = 8
            ws.column_dimensions['B'].width = 50
            ws.column_dimensions['C'].width = 40
            ws.column_dimensions['D'].width = 18
            ws.column_dimensions['E'].width = 15
            ws.column_dimensions['F'].width = 20
            ws.column_dimensions['G'].width = 12
            
            # Agregar bordes
            from openpyxl.styles import Border, Side
            thin_border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
            
            for row in ws.iter_rows(min_row=4, max_row=ws.max_row, min_col=1, max_col=7):
                for cell in row:
                    cell.border = thin_border
            
            # Resumen al final
            ws.append([])
            resumen_row = ws.max_row + 1
            ws.merge_cells(f'A{resumen_row}:C{resumen_row}')
            resumen_cell = ws[f'A{resumen_row}']
            resumen_cell.value = f'TOTAL DE CENTROS: {centros.count()}'
            resumen_cell.font = Font(bold=True, size=11)
            resumen_cell.alignment = Alignment(horizontal='left')
            
            # Generar respuesta
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename=Centros_Penitenciarios_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            wb.save(response)
            
            return response
            
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            return Response({
                'error': 'Error al exportar centros',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], url_path='importar')
    def importar_excel(self, request):
        """
        Importa centros desde Excel.
        
        Formato esperado (columnas en orden):
        1. Nombre (REQUERIDO, único) - Nombre del centro penitenciario
        2. Direccion (opcional) - Dirección física
        3. Telefono (opcional) - Número de teléfono
        4. Email (opcional) - Correo electrónico
        5. Estado (opcional, default: Activo) - 'Activo' o 'Inactivo'
        
        Limites de seguridad:
        - Tamano maximo: configurado en IMPORT_MAX_FILE_SIZE_MB (default 10MB)
        - Filas maximas: configurado en IMPORT_MAX_ROWS (default 5000)
        - Extensiones: .xlsx, .xls
        
        Nota: Si el nombre ya existe, se actualizan los demás campos.
        """
        file = request.FILES.get('file')
        
        # HALLAZGO #13 FIX: Validar archivo CON magic bytes
        es_valido, error_msg = validar_archivo_excel(file)
        if not es_valido:
            logger.warning(f"HALLAZGO #13: Archivo Excel rechazado en importar_excel (CentroViewSet): {error_msg}")
            return Response({
                'error': 'Archivo invalido',
                'mensaje': error_msg
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # ISS-001: Usar carga segura con limite real de bytes
            wb, error_carga = cargar_workbook_seguro(file)
            if wb is None:
                return Response({
                    'error': 'Error al procesar archivo',
                    'mensaje': error_carga
                }, status=status.HTTP_400_BAD_REQUEST)
            
            ws = wb.active
            
            # Validar numero de filas
            filas_validas, error_filas, num_filas = validar_filas_excel(ws)
            if not filas_validas:
                wb.close()  # Liberar recursos en modo read_only
                return Response({
                    'error': 'Archivo demasiado grande',
                    'mensaje': error_filas
                }, status=status.HTTP_400_BAD_REQUEST)
            
            creados = 0
            actualizados = 0
            errores = []
            
            # Procesar filas
            for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                try:
                    # Saltar filas vacías
                    if not row or all(cell is None or str(cell).strip() == '' for cell in row):
                        continue
                    
                    # Extraer datos - Formato: Nombre, Direccion, Telefono, Email, Estado
                    # (mínimo 1 columna: nombre)
                    nombre = row[0] if len(row) > 0 else None
                    direccion = row[1] if len(row) > 1 else None
                    telefono = row[2] if len(row) > 2 else None
                    email = row[3] if len(row) > 3 else None
                    estado = row[4] if len(row) > 4 else 'Activo'
                    
                    # Validar requeridos
                    if not nombre or str(nombre).strip() == '':
                        errores.append({'fila': row_idx, 'error': 'Nombre es requerido'})
                        continue
                    
                    nombre_limpio = str(nombre).strip()
                    
                    # Preparar datos
                    datos = {
                        'direccion': str(direccion).strip() if direccion else '',
                        'telefono': str(telefono).strip() if telefono else '',
                        'email': str(email).strip() if email else '',
                        'activo': str(estado).lower() in ['activo', 'si', 'sí', 'true', '1', 'yes'] if estado else True
                    }
                    
                    # Crear o actualizar usando nombre como identificador único
                    centro, created = Centro.objects.update_or_create(
                        nombre=nombre_limpio,
                        defaults=datos
                    )
                    
                    if created:
                        creados += 1
                    else:
                        actualizados += 1
                        
                except Exception as e:
                    errores.append(f'Fila {row_idx}: {str(e)}')
            
            return Response({
                'mensaje': 'Importacion completada',
                'resumen': {
                    'creados': creados,
                    'actualizados': actualizados,
                    'total_procesados': creados + actualizados,
                    'errores_encontrados': len(errores)
                },
                'errores': errores[:10] if errores else [],  # Maximo 10 errores
                'tiene_mas_errores': len(errores) > 10,
                'exito': len(errores) == 0
            }, status=status.HTTP_200_OK if len(errores) == 0 else status.HTTP_207_MULTI_STATUS)
            
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            logger.exception(f'Error en importacion de centros: {str(e)}')
            return Response({
                'error': 'Error al procesar el archivo',
                'mensaje': str(e),
                'sugerencia': 'Verifique que el archivo tenga el formato correcto: Nombre, Direccion, Telefono, Email, Estado'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def requisiciones(self, request, pk=None):
        """Obtiene todas las requisiciones de un centro"""
        try:
            centro = self.get_object()
            
            if not hasattr(centro, 'requisiciones'):
                return Response({
                    'centro': {
                        'id': centro.id,
                        'clave': centro.clave,
                        'nombre': centro.nombre
                    },
                    'requisiciones': [],
                    'total': 0,
                    'mensaje': 'No hay requisiciones disponibles'
                })
            
            requisiciones = centro.requisiciones_destino.all().order_by('-fecha_solicitud')
            
            # Agrupar por estado
            por_estado = {}
            for req in requisiciones:
                estado = req.estado
                if estado not in por_estado:
                    por_estado[estado] = 0
                por_estado[estado] += 1
            
            requisiciones_data = []
            for req in requisiciones:
                requisiciones_data.append({
                    'id': req.id,
                    'folio': req.folio,
                    'estado': req.estado,
                    'fecha_solicitud': req.fecha_solicitud,
                    'total_items': req.items.count() if hasattr(req, 'items') else 0
                })
            
            return Response({
                'centro': {
                    'id': centro.id,
                    'clave': centro.clave,
                    'nombre': centro.nombre
                },
                'estadisticas': {
                    'total': requisiciones.count(),
                    'por_estado': por_estado
                },
                'requisiciones': requisiciones_data
            })
            
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            return Response({
                'error': 'Error al obtener requisiciones',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], url_path='plantilla')
    def plantilla_centros(self, request):
        """Descarga plantilla de Excel para importación de centros."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Centros'
        
        # Headers que coinciden con el modelo Centro
        headers = ['Nombre', 'Direccion', 'Telefono', 'Email', 'Estado']
        ws.append(headers)
        
        # Fila de ejemplo
        ws.append(['CENTRO PENITENCIARIO EJEMPLO', 'Av. Principal 123, Ciudad', '(555) 123-4567', 'centro@ejemplo.gob.mx', 'Activo'])
        
        # Aplicar formato a headers
        from openpyxl.styles import Font, PatternFill
        header_font = Font(bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='9F2241', end_color='9F2241', fill_type='solid')
        for col in range(1, 6):
            cell = ws.cell(row=1, column=col)
            cell.font = header_font
            cell.fill = header_fill
        
        # Ajustar ancho de columnas
        ws.column_dimensions['A'].width = 45  # Nombre
        ws.column_dimensions['B'].width = 40  # Direccion
        ws.column_dimensions['C'].width = 18  # Telefono
        ws.column_dimensions['D'].width = 30  # Email
        ws.column_dimensions['E'].width = 12  # Estado
        
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=Plantilla_Centros.xlsx'
        wb.save(response)
        return response


class LoteViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar lotes.
    
    Funcionalidades:
    - CRUD completo
    - Filtrado por producto
    - Filtrado por estado de caducidad
    - Busqueda por numero de lote
    - Validaciones de integridad
    
    ISS-MEDICO FIX: Médicos pueden ver lotes (para crear requisiciones)
    pero NO pueden crear/editar/eliminar lotes.
    """
    queryset = Lote.objects.select_related('producto').all()
    serializer_class = LoteSerializer
    # ISS-MEDICO FIX: Médico puede leer pero NO escribir
    permission_classes = [IsCentroOwnResourcesOnly]
    pagination_class = CustomPagination

    def get_queryset(self):
        """
        Filtra lotes segun parametros.
        
        Parametros:
        - producto: ID del producto
        - activo: true/false
        - caducidad: vencido/critico/proximo/normal
        - search: busqueda por numero de lote
        - centro: ID del centro o 'central' para farmacia (solo admin/farmacia/vista)
        
        Seguridad: Usuarios de centro solo ven lotes de su centro.
        Admin/farmacia por defecto ven solo Farmacia Central, pueden filtrar con ?centro=.
        """
        queryset = Lote.objects.select_related('producto', 'centro').all()
        
        # SEGURIDAD: Filtrar por centro segun rol
        user = self.request.user
        
        # ISS-FIX: Usuarios de centro pueden ver lotes de farmacia central
        # cuando están creando requisiciones (para_requisicion=true)
        para_requisicion = self.request.query_params.get('para_requisicion', '').lower() == 'true'
        
        if not is_farmacia_or_admin(user):
            # Usuario de centro
            user_centro = get_user_centro(user)
            if not user_centro:
                return Lote.objects.none()
            
            if para_requisicion:
                # ISS-FIX: Para crear requisiciones, mostrar lotes de FARMACIA CENTRAL
                # porque las requisiciones se surten desde farmacia central
                queryset = queryset.filter(centro__isnull=True)
            else:
                # Por defecto: solo lotes de SU centro
                queryset = queryset.filter(centro=user_centro)
        else:
            # Admin/farmacia/vista: por defecto solo Farmacia Central
            # ISS-FIX: Evitar mostrar lotes duplicados de centros en vista de Farmacia
            centro_param = self.request.query_params.get('centro')
            if centro_param:
                if centro_param == 'central':
                    # Filtrar solo farmacia central (centro=NULL)
                    queryset = queryset.filter(centro__isnull=True)
                elif centro_param == 'todos':
                    # Mostrar todos los lotes (solo si se pide explícitamente)
                    pass  # No filtrar
                else:
                    # Filtrar por centro específico
                    queryset = queryset.filter(centro_id=centro_param)
            else:
                # Por defecto: solo lotes de Farmacia Central (centro=NULL)
                queryset = queryset.filter(centro__isnull=True)
        
        # Filtrar por producto
        producto = self.request.query_params.get('producto')
        if producto:
            queryset = queryset.filter(producto_id=producto)
        
        # Filtrar por activo (el campo real en la BD)
        activo = self.request.query_params.get('activo')
        if activo is not None:
            if activo.lower() in ['true', '1', 'si']:
                queryset = queryset.filter(activo=True)
            elif activo.lower() in ['false', '0', 'no']:
                queryset = queryset.filter(activo=False)
        
        # Busqueda por numero de lote, clave o nombre producto (ISS-003)
        search = self.request.query_params.get('search')
        if search and search.strip():
            search_term = search.strip()
            queryset = queryset.filter(
                Q(numero_lote__icontains=search_term) |
                Q(producto__clave__icontains=search_term) |
                Q(producto__nombre__icontains=search_term)
            )
        
        # Filtrar por estado de caducidad segun especificacion SIFP:
        # Normal: > 6 meses (180 dias)
        # Proximo: 3-6 meses (90-180 dias)
        # Critico: < 3 meses (90 dias)
        # Vencido: < 0 dias
        caducidad = self.request.query_params.get('caducidad')
        if caducidad:
            from datetime import date, timedelta
            hoy = date.today()
            
            if caducidad == 'vencido':
                queryset = queryset.filter(fecha_caducidad__lt=hoy)
            elif caducidad == 'critico':
                # Menos de 3 meses (< 90 dias) pero no vencido
                queryset = queryset.filter(
                    fecha_caducidad__gte=hoy,
                    fecha_caducidad__lt=hoy + timedelta(days=90)
                )
            elif caducidad == 'proximo':
                # Entre 3 y 6 meses (90-180 dias)
                queryset = queryset.filter(
                    fecha_caducidad__gte=hoy + timedelta(days=90),
                    fecha_caducidad__lt=hoy + timedelta(days=180)
                )
            elif caducidad == 'normal':
                # Mas de 6 meses (> 180 dias)
                queryset = queryset.filter(fecha_caducidad__gte=hoy + timedelta(days=180))
        
        # Filtrar por stock minimo (para catalogo de requisiciones)
        stock_min = self.request.query_params.get('stock_min')
        if stock_min:
            try:
                queryset = queryset.filter(cantidad_actual__gte=int(stock_min))
            except (ValueError, TypeError):
                pass
        
        # Filtrar por existencia de stock (con_stock/sin_stock)
        con_stock = self.request.query_params.get('con_stock')
        if con_stock == 'con_stock':
            queryset = queryset.filter(cantidad_actual__gt=0)
        elif con_stock == 'sin_stock':
            queryset = queryset.filter(cantidad_actual=0)
        
        # Filtrar solo lotes disponibles (no vencidos) para el catalogo
        solo_disponibles = self.request.query_params.get('solo_disponibles')
        if solo_disponibles == 'true':
            from datetime import date
            queryset = queryset.filter(
                activo=True,
                fecha_caducidad__gt=date.today()
            )
        
        return queryset.order_by('-created_at')
    
    @transaction.atomic  # HALLAZGO #10 FIX: Garantizar atomicidad
    def create(self, request, *args, **kwargs):
        """Crea un nuevo lote con validaciones"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            
            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data, 
                status=status.HTTP_201_CREATED, 
                headers=headers
            )
        except serializers.ValidationError as e:
            return Response(
                {'error': 'Error de validacion', 'detalles': e.detail}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # HALLAZGO #12 FIX: No exponer stack trace completo
            logger.error(f"Error al crear lote: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Error al crear lote. Contacte al administrador.'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        """Actualiza un lote existente.
        
        ISS-010 FIX: Validación explícita de permisos para evitar IDOR.
        Solo admin/farmacia pueden modificar lotes de farmacia central.
        Usuarios de centro solo pueden modificar lotes de SU centro.
        """
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            
            # ISS-010: Validar permisos de escritura sobre este lote específico
            user = request.user
            if not is_farmacia_or_admin(user):
                user_centro = get_user_centro(user)
                lote_centro = instance.centro
                
                # Si el lote es de farmacia central o de otro centro, denegar
                if lote_centro is None or (user_centro and lote_centro.pk != user_centro.pk):
                    logger.warning(
                        f"ISS-010: Intento de modificación no autorizada de lote. "
                        f"Usuario={user.username}, lote={instance.numero_lote}, "
                        f"lote_centro={lote_centro}, user_centro={user_centro}"
                    )
                    return Response(
                        {'error': 'No tiene permisos para modificar este lote'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            
            return Response(serializer.data)
        except serializers.ValidationError as e:
            return Response(
                {'error': 'Error de validacion', 'detalles': e.detail}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            return Response(
                {'error': 'Error al actualizar lote', 'mensaje': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, *args, **kwargs):
        """
        Elimina un lote.
        
        ISS-010 FIX: Validación explícita de permisos para evitar IDOR.
        
        Validaciones:
        - Permisos de escritura sobre el lote
        - No puede eliminarse si tiene movimientos asociados
        """
        instance = self.get_object()
        
        # ISS-010: Validar permisos de escritura sobre este lote específico
        user = request.user
        if not is_farmacia_or_admin(user):
            user_centro = get_user_centro(user)
            lote_centro = instance.centro
            
            # Si el lote es de farmacia central o de otro centro, denegar
            if lote_centro is None or (user_centro and lote_centro.pk != user_centro.pk):
                logger.warning(
                    f"ISS-010: Intento de eliminación no autorizada de lote. "
                    f"Usuario={user.username}, lote={instance.numero_lote}, "
                    f"lote_centro={lote_centro}, user_centro={user_centro}"
                )
                return Response(
                    {'error': 'No tiene permisos para eliminar este lote'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        try:
            # Verificar si tiene movimientos
            if Movimiento.objects.filter(lote=instance).exists():
                total_movimientos = Movimiento.objects.filter(lote=instance).count()
                
                return Response({
                    'error': 'No se puede eliminar el lote',
                    'razon': 'Tiene movimientos asociados',
                    'total_movimientos': total_movimientos,
                    'sugerencia': 'Marque el lote como inactivo en lugar de eliminarlo'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Si no tiene movimientos, se puede eliminar
            numero_lote = instance.numero_lote
            producto_clave = instance.producto.clave
            instance.delete()
            
            return Response({
                'mensaje': 'Lote eliminado exitosamente',
                'lote_eliminado': numero_lote,
                'producto': producto_clave
            }, status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            return Response({
                'error': 'Error al eliminar lote',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='exportar-pdf')
    def exportar_pdf(self, request):
        """
        Genera PDF de inventario de lotes con filtros opcionales.
        
        Usa los mismos filtros que get_queryset para consistencia:
        - producto: ID del producto
        - activo: true/false
        - search: búsqueda en número de lote o producto
        - caducidad: vencido/critico/proximo/normal
        - con_stock: con_stock/sin_stock
        - centro: ID del centro o 'central'
        
        Respeta permisos de usuario:
        - Usuarios de centro solo ven lotes de su centro
        - Admin/Farmacia/Vista ven todo
        """
        from core.utils.pdf_reports import generar_reporte_lotes
        
        try:
            # Usar get_queryset que ya aplica filtros y permisos
            queryset = self.get_queryset()
            
            # Limitar a 500 lotes para PDF
            lotes = queryset[:500]
            
            # Preparar datos para el PDF
            lotes_data = []
            for lote in lotes:
                lotes_data.append({
                    'producto_clave': getattr(lote.producto, 'clave', '') if lote.producto else '',
                    'producto_nombre': getattr(lote.producto, 'nombre', '') if lote.producto else '',
                    'numero_lote': lote.numero_lote or '',
                    'fecha_fabricacion': lote.fecha_fabricacion.strftime('%Y-%m-%d') if lote.fecha_fabricacion else '',
                    'fecha_caducidad': lote.fecha_caducidad.strftime('%Y-%m-%d') if lote.fecha_caducidad else '',
                    'fecha_caducidad_raw': lote.fecha_caducidad,
                    'cantidad_inicial': lote.cantidad_inicial,
                    'cantidad_actual': lote.cantidad_actual,
                    'centro_nombre': getattr(lote.centro, 'nombre', 'Farmacia Central') if lote.centro else 'Farmacia Central',
                    'activo': lote.activo,
                })
            
            # Preparar filtros para mostrar en el PDF
            filtros = {}
            if request.query_params.get('producto'):
                try:
                    producto = Producto.objects.get(pk=request.query_params.get('producto'))
                    filtros['producto'] = f"{producto.clave} - {producto.nombre}"
                except Producto.DoesNotExist:
                    pass
            if request.query_params.get('centro'):
                centro_param = request.query_params.get('centro')
                if centro_param == 'central':
                    filtros['centro'] = 'Farmacia Central'
                else:
                    try:
                        centro = Centro.objects.get(pk=centro_param)
                        filtros['centro'] = centro.nombre
                    except Centro.DoesNotExist:
                        pass
            if request.query_params.get('caducidad'):
                filtros['caducidad'] = request.query_params.get('caducidad')
            if request.query_params.get('con_stock'):
                filtros['con_stock'] = request.query_params.get('con_stock')
            if request.query_params.get('activo'):
                filtros['activo'] = request.query_params.get('activo')
            if request.query_params.get('search'):
                filtros['busqueda'] = request.query_params.get('search')
            
            pdf_buffer = generar_reporte_lotes(lotes_data, filtros)
            
            response = HttpResponse(
                pdf_buffer.getvalue(),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'attachment; filename="Inventario_Lotes_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
            
            return response
            
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            return Response({
                'error': 'Error al generar PDF de lotes',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='exportar-excel')
    def exportar_excel(self, request):
        """
        Exporta lotes aplicando los mismos filtros de listado.
        
        ISS-DB: Incluye todos los campos de la tabla lotes de Supabase:
        - clave (de producto)
        - numero_lote, fecha_fabricacion, fecha_caducidad
        - cantidad_inicial, cantidad_actual
        - precio_unitario, numero_contrato, marca, ubicacion
        - centro (nombre), activo
        """
        try:
            lotes = self.get_queryset()
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Lotes'

            ws.merge_cells('A1:L1')
            ws['A1'] = 'REPORTE DE LOTES - SISTEMA DE INVENTARIO FARMACEUTICO PENITENCIARIO'
            ws['A1'].font = Font(bold=True, size=14, color='632842')
            ws['A1'].alignment = Alignment(horizontal='center', vertical='center')

            ws.append([])
            # ISS-DB: Headers alineados con esquema real de Supabase
            headers = [
                '#', 'Clave', 'Nombre Producto', 'Número Lote',
                'Fecha Fabricación', 'Fecha Caducidad',
                'Cantidad Inicial', 'Cantidad Actual',
                'Precio Unitario', 'Número Contrato', 'Marca', 'Ubicación',
                'Centro', 'Activo'
            ]
            ws.append(headers)
            header_fill = PatternFill(start_color='632842', end_color='632842', fill_type='solid')
            header_font = Font(bold=True, color='FFFFFF', size=11)
            for cell in ws[3]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')

            for idx, lote in enumerate(lotes, 1):
                ws.append([
                    idx,
                    getattr(lote.producto, 'clave', '') or '',
                    getattr(lote.producto, 'nombre', '') or '',
                    lote.numero_lote or '',
                    lote.fecha_fabricacion.strftime('%Y-%m-%d') if lote.fecha_fabricacion else '',
                    lote.fecha_caducidad.strftime('%Y-%m-%d') if lote.fecha_caducidad else '',
                    lote.cantidad_inicial,
                    lote.cantidad_actual,
                    float(lote.precio_unitario) if lote.precio_unitario else 0.00,
                    lote.numero_contrato or '',
                    lote.marca or '',
                    lote.ubicacion or '',
                    getattr(lote.centro, 'nombre', 'Farmacia Central') if lote.centro else 'Farmacia Central',
                    'Sí' if lote.activo else 'No'
                ])

            # Ajustar anchos de columna
            column_widths = [6, 15, 25, 15, 14, 14, 12, 12, 12, 18, 15, 15, 18, 8]
            for col_idx, width in enumerate(column_widths, 1):
                ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = width

            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename=Lotes_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            wb.save(response)
            return response
        except Exception as exc:
            # traceback removido por seguridad (ISS-008)
            return Response({'error': 'Error al exportar lotes', 'mensaje': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='importar-excel')
    def importar_excel(self, request):
        """
        Importa lotes desde Excel con detección automática de columnas.
        
        Columnas reconocidas (flexibles, no importa el orden):
        - Producto/Clave (requerido): clave o nombre del producto
        - Numero Lote/Lote (requerido): identificador del lote
        - Fecha Caducidad (requerido): fecha de vencimiento
        - Cantidad Inicial/Cantidad (requerido): cantidad recibida
        - Cantidad Actual (opcional): default = cantidad inicial
        - Fecha Fabricacion (opcional)
        - Precio Unitario/Precio (opcional): default = 0
        - Numero Contrato/Contrato (opcional)
        - Marca (opcional)
        - Ubicacion (opcional)
        - Centro/Centro ID (opcional): ID o nombre del centro
        
        Limites de seguridad:
        - Tamano maximo: 10MB
        - Filas maximas: 5000
        - Extensiones: .xlsx, .xls
        """
        file = request.FILES.get('file')
        
        # HALLAZGO #13 FIX: Validar archivo CON magic bytes
        es_valido, error_msg = validar_archivo_excel(file)
        if not es_valido:
            logger.warning(f"HALLAZGO #13: Archivo Excel rechazado en importar_excel (LoteViewSet): {error_msg}")
            return Response({
                'error': 'Archivo invalido',
                'mensaje': error_msg
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # ISS-001: Usar carga segura con limite real de bytes
            wb, error_carga = cargar_workbook_seguro(file)
            if wb is None:
                return Response({
                    'error': 'Error al procesar archivo',
                    'mensaje': error_carga
                }, status=status.HTTP_400_BAD_REQUEST)
            
            ws = wb.active
            
            # Validar numero de filas
            filas_validas, error_filas, num_filas = validar_filas_excel(ws)
            if not filas_validas:
                wb.close()
                return Response({
                    'error': 'Archivo demasiado grande',
                    'mensaje': error_filas
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # ISS-FIX: Detectar fila de encabezados automáticamente
            # Buscar fila que contenga palabras clave como "lote", "producto", "cantidad"
            header_row_idx = 1
            col_map = {}
            
            # Mapeo de nombres de columna a campos internos
            COLUMN_ALIASES = {
                'producto': ['producto', 'clave', 'clave producto', 'codigo', 'código'],
                'nombre_producto': ['nombre producto', 'nombre', 'descripcion', 'descripción'],
                'numero_lote': ['numero lote', 'número lote', 'lote', 'no. lote', 'no lote', 'num lote'],
                'fecha_caducidad': ['fecha caducidad', 'caducidad', 'vencimiento', 'fecha vencimiento', 'expira', 'fecha expiracion'],
                'cantidad_inicial': ['cantidad inicial', 'cantidad', 'cant inicial', 'cant', 'qty'],
                'cantidad_actual': ['cantidad actual', 'cant actual', 'stock', 'existencia'],
                'fecha_fabricacion': ['fecha fabricacion', 'fecha fabricación', 'fabricacion', 'fabricación', 'manufactura'],
                'precio_unitario': ['precio unitario', 'precio', 'costo', 'valor', 'precio unit'],
                'numero_contrato': ['numero contrato', 'número contrato', 'contrato', 'no. contrato', 'no contrato'],
                'marca': ['marca', 'laboratorio', 'fabricante'],
                'ubicacion': ['ubicacion', 'ubicación', 'almacen', 'almacén', 'bodega'],
                'centro': ['centro', 'centro id', 'centro_id', 'destino'],
                'activo': ['activo', 'estado', 'status'],
            }
            
            def normalizar_header(val):
                if not val:
                    return ''
                return str(val).lower().strip().replace('_', ' ').replace('-', ' ')
            
            # Buscar fila con encabezados (primeras 5 filas)
            for row_num in range(1, min(6, ws.max_row + 1)):
                row_values = [cell.value for cell in ws[row_num]]
                headers_encontrados = 0
                temp_map = {}
                
                for col_idx, val in enumerate(row_values):
                    header_norm = normalizar_header(val)
                    if not header_norm:
                        continue
                    
                    for field, aliases in COLUMN_ALIASES.items():
                        if header_norm in aliases or any(alias in header_norm for alias in aliases):
                            if field not in temp_map:
                                temp_map[field] = col_idx
                                headers_encontrados += 1
                            break
                
                # Si encontramos al menos 3 columnas relevantes, es la fila de headers
                if headers_encontrados >= 3:
                    header_row_idx = row_num
                    col_map = temp_map
                    break
            
            # Si no hay mapa, usar orden por defecto
            if not col_map:
                col_map = {
                    'producto': 0, 'numero_lote': 1, 'fecha_caducidad': 2,
                    'cantidad_inicial': 3, 'cantidad_actual': 4, 'fecha_fabricacion': 5,
                    'precio_unitario': 6, 'numero_contrato': 7, 'marca': 8,
                    'ubicacion': 9, 'centro': 10
                }
            
            def get_val(row, field, default=None):
                if field not in col_map:
                    return default
                idx = col_map[field]
                if idx < len(row):
                    val = row[idx]
                    return val if val not in [None, '', 'None'] else default
                return default
            
            exitos = []
            errores = []

            for row_idx, row in enumerate(ws.iter_rows(min_row=header_row_idx + 1, values_only=True), start=header_row_idx + 1):
                try:
                    # Saltar filas vacías
                    if not row or all(cell is None or str(cell).strip() == '' for cell in row):
                        continue
                    
                    # Extraer valores usando el mapa de columnas
                    producto_ref = get_val(row, 'producto') or get_val(row, 'nombre_producto')
                    numero_lote = get_val(row, 'numero_lote')
                    fecha_cad = get_val(row, 'fecha_caducidad')
                    cantidad_inicial = get_val(row, 'cantidad_inicial')
                    cantidad_actual = get_val(row, 'cantidad_actual')
                    fecha_fab = get_val(row, 'fecha_fabricacion')
                    precio_unitario = get_val(row, 'precio_unitario')
                    numero_contrato = get_val(row, 'numero_contrato')
                    marca = get_val(row, 'marca')
                    ubicacion = get_val(row, 'ubicacion')
                    centro_ref = get_val(row, 'centro')

                    if not producto_ref or not numero_lote:
                        errores.append({'fila': row_idx, 'error': 'Producto y numero de lote son obligatorios'})
                        continue

                    # ISS-FIX: Buscar producto por clave o nombre (flexible)
                    producto_busqueda = str(producto_ref).strip()
                    producto = Producto.objects.filter(
                        Q(clave__iexact=producto_busqueda) |
                        Q(nombre__icontains=producto_busqueda)
                    ).first()
                    if not producto:
                        errores.append({'fila': row_idx, 'error': f'Producto no encontrado: {producto_ref}'})
                        continue

                    # Parsear fecha de caducidad (varios formatos)
                    try:
                        fecha_cad_val = None
                        if fecha_cad:
                            if isinstance(fecha_cad, (datetime, date)):
                                fecha_cad_val = fecha_cad.date() if hasattr(fecha_cad, 'date') else fecha_cad
                            else:
                                fecha_str = str(fecha_cad).strip()
                                # Intentar varios formatos
                                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d']:
                                    try:
                                        fecha_cad_val = datetime.strptime(fecha_str.split()[0], fmt).date()
                                        break
                                    except:
                                        continue
                        if not fecha_cad_val:
                            raise ValueError("No se pudo parsear fecha")
                    except Exception:
                        errores.append({'fila': row_idx, 'error': f'Fecha de caducidad invalida: {fecha_cad}'})
                        continue

                    # Parsear fecha de fabricacion (opcional)
                    fecha_fab_val = None
                    if fecha_fab:
                        try:
                            if isinstance(fecha_fab, (datetime, date)):
                                fecha_fab_val = fecha_fab.date() if hasattr(fecha_fab, 'date') else fecha_fab
                            else:
                                fecha_str = str(fecha_fab).strip()
                                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d']:
                                    try:
                                        fecha_fab_val = datetime.strptime(fecha_str.split()[0], fmt).date()
                                        break
                                    except:
                                        continue
                        except Exception:
                            pass  # Ignorar fecha fabricacion invalida

                    # Parsear cantidades (más flexible)
                    try:
                        cant_ini = int(float(cantidad_inicial)) if cantidad_inicial not in [None, ''] else 0
                        cant_act = int(float(cantidad_actual)) if cantidad_actual not in [None, ''] else cant_ini
                        if cant_ini <= 0:
                            cant_ini = 1  # Minimo 1
                        if cant_act < 0:
                            cant_act = 0
                    except Exception:
                        errores.append({'fila': row_idx, 'error': f'Cantidades invalidas: inicial={cantidad_inicial}, actual={cantidad_actual}'})
                        continue

                    # Parsear precio unitario (opcional)
                    precio_val = 0
                    if precio_unitario not in [None, '']:
                        try:
                            precio_val = float(str(precio_unitario).replace(',', '.'))
                            if precio_val < 0:
                                precio_val = 0
                        except Exception:
                            pass  # Usar 0 si no es valido

                    # Preparar defaults para update_or_create
                    defaults = {
                        'fecha_caducidad': fecha_cad_val or date.today(),
                        'cantidad_inicial': cant_ini,
                        'cantidad_actual': cant_act,
                        'precio_unitario': precio_val,
                        'numero_contrato': str(numero_contrato).strip()[:100] if numero_contrato else '',
                        'marca': str(marca).strip()[:100] if marca else '',
                        'ubicacion': str(ubicacion).strip()[:100] if ubicacion else '',
                    }
                    
                    if fecha_fab_val:
                        defaults['fecha_fabricacion'] = fecha_fab_val
                    
                    # ISS-FIX: Asignar centro si se proporciona (por ID o nombre)
                    if centro_ref:
                        try:
                            centro_str = str(centro_ref).strip()
                            # Intentar por ID numerico primero
                            if centro_str.isdigit():
                                centro = Centro.objects.get(pk=int(centro_str))
                            else:
                                # Buscar por nombre
                                centro = Centro.objects.filter(nombre__icontains=centro_str).first()
                            if centro:
                                defaults['centro'] = centro
                        except (Centro.DoesNotExist, ValueError):
                            pass  # Ignorar centro invalido

                    lote, created = Lote.objects.update_or_create(
                        producto=producto,
                        numero_lote=str(numero_lote).strip().upper(),
                        defaults=defaults
                    )
                    exitos.append({'fila': row_idx, 'lote_id': lote.id, 'numero_lote': lote.numero_lote, 'created': created})
                except Exception as exc:
                    errores.append({'fila': row_idx, 'error': str(exc)})

            status_code = status.HTTP_200_OK if not errores else status.HTTP_207_MULTI_STATUS
            return Response({
                'mensaje': 'Importacion de lotes completada',
                'resumen': {
                    'exitos': len(exitos),
                    'errores': len(errores),
                    'total': len(exitos) + len(errores)
                },
                'exitos': exitos,
                'errores': errores
            }, status=status_code)
        except Exception as exc:
            # traceback removido por seguridad (ISS-008)
            return Response({'error': 'Error al procesar archivo', 'mensaje': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='plantilla')
    def plantilla_lotes(self, request):
        """
        Descarga plantilla Excel para importación de lotes.
        
        Columnas (en orden):
        1. Producto (REQUERIDO) - Clave o nombre del producto
        2. Numero Lote (REQUERIDO) - Identificador único del lote
        3. Fecha Caducidad (REQUERIDO, YYYY-MM-DD)
        4. Cantidad Inicial (REQUERIDO) - Cantidad recibida
        5. Cantidad Actual (opcional, default = Cantidad Inicial)
        6. Fecha Fabricacion (opcional, YYYY-MM-DD)
        7. Precio Unitario (opcional, default = 0)
        8. Numero Contrato (opcional)
        9. Marca (opcional)
        10. Ubicacion (opcional)
        11. Centro ID (opcional) - ID numérico del centro
        """
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Lotes'
        
        # Headers que coinciden con importar_excel
        headers = [
            'Producto', 'Numero Lote', 'Fecha Caducidad', 'Cantidad Inicial',
            'Cantidad Actual', 'Fecha Fabricacion', 'Precio Unitario',
            'Numero Contrato', 'Marca', 'Ubicacion', 'Centro ID'
        ]
        ws.append(headers)
        
        # ============================================================
        # FILAS DE EJEMPLO - ELIMINAR ANTES DE USAR CON DATOS REALES
        # Estas filas son solo para mostrar el formato correcto.
        # ============================================================
        from datetime import date, timedelta
        fecha_cad_ejemplo = (date.today() + timedelta(days=365)).strftime('%Y-%m-%d')
        fecha_fab_ejemplo = date.today().strftime('%Y-%m-%d')
        
        ws.append([
            'PRUEBA001', 'LOTE-PRUEBA-001', fecha_cad_ejemplo, 100,
            100, fecha_fab_ejemplo, 25.50,
            'CONT-PRUEBA-001', '[EJEMPLO] Laboratorio - ELIMINAR', 'Almacén A', ''
        ])
        ws.append([
            'PRUEBA002', 'LOTE-PRUEBA-002', fecha_cad_ejemplo, 50,
            50, fecha_fab_ejemplo, 18.75,
            'CONT-PRUEBA-002', '[EJEMPLO] Farmacéutica - ELIMINAR', 'Almacén B', ''
        ])
        ws.append([
            'PRUEBA003', 'LOTE-PRUEBA-003', fecha_cad_ejemplo, 200,
            200, '', 5.00,
            '', '[EJEMPLO] Material - ELIMINAR', '', ''
        ])
        
        # Aplicar formato a headers
        from openpyxl.styles import Font, PatternFill, Alignment
        header_font = Font(bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='9F2241', end_color='9F2241', fill_type='solid')
        for col in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col)
            cell.font = header_font
            cell.fill = header_fill
        
        # Estilo para filas de ejemplo (gris, itálica - sin fondo de color)
        example_font = Font(italic=True, color='888888')
        for row_num in range(2, 5):  # Filas 2, 3, 4 (ejemplos)
            for col in range(1, len(headers) + 1):
                cell = ws.cell(row=row_num, column=col)
                cell.font = example_font
        
        # Ajustar ancho de columnas
        column_widths = {
            'A': 15,  # Producto
            'B': 20,  # Numero Lote
            'C': 16,  # Fecha Caducidad
            'D': 16,  # Cantidad Inicial
            'E': 16,  # Cantidad Actual
            'F': 18,  # Fecha Fabricacion
            'G': 15,  # Precio Unitario
            'H': 18,  # Numero Contrato
            'I': 35,  # Marca (más ancho para ver el texto de ejemplo)
            'J': 15,  # Ubicacion
            'K': 12,  # Centro ID
        }
        for col_letter, width in column_widths.items():
            ws.column_dimensions[col_letter].width = width
        
        # ============================================================
        # HOJA DE INSTRUCCIONES
        # ============================================================
        ws_instrucciones = wb.create_sheet(title='INSTRUCCIONES')
        
        instrucciones = [
            ['╔════════════════════════════════════════════════════════════════════╗'],
            ['║    INSTRUCCIONES PARA IMPORTACIÓN DE LOTES                        ║'],
            ['╚════════════════════════════════════════════════════════════════════╝'],
            [''],
            ['⚠️  IMPORTANTE: Las filas amarillas en la hoja "Lotes" son EJEMPLOS.'],
            ['    ELIMÍNELAS antes de cargar sus datos reales.'],
            [''],
            ['────────────────────────────────────────────────────────────────────────'],
            ['COLUMNAS REQUERIDAS (obligatorias):'],
            ['────────────────────────────────────────────────────────────────────────'],
            ['• Producto       - Clave del producto (debe existir en el sistema)'],
            ['• Numero Lote    - Identificador único del lote'],
            ['• Fecha Caducidad - Formato: YYYY-MM-DD (ej: 2026-12-31)'],
            ['• Cantidad Inicial - Cantidad de unidades recibidas'],
            [''],
            ['────────────────────────────────────────────────────────────────────────'],
            ['COLUMNAS OPCIONALES:'],
            ['────────────────────────────────────────────────────────────────────────'],
            ['• Cantidad Actual  - Stock actual (default: igual a Cantidad Inicial)'],
            ['• Fecha Fabricacion - Formato: YYYY-MM-DD'],
            ['• Precio Unitario  - Precio por unidad (default: 0)'],
            ['• Numero Contrato  - Referencia del contrato de adquisición'],
            ['• Marca            - Laboratorio o fabricante'],
            ['• Ubicacion        - Ubicación física en el almacén'],
            ['• Centro ID        - ID numérico del centro (vacío = Farmacia Central)'],
            [''],
            ['────────────────────────────────────────────────────────────────────────'],
            ['NOTAS:'],
            ['────────────────────────────────────────────────────────────────────────'],
            ['• El PRODUCTO debe existir antes de importar lotes.'],
            ['• Si el lote ya existe (mismo producto + número de lote), se ACTUALIZA.'],
            ['• La cantidad_actual se inicializa igual a cantidad_inicial.'],
            ['• Fechas aceptadas: YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY'],
            ['• Máximo 5000 lotes por archivo.'],
            ['• Tamaño máximo de archivo: 10 MB.'],
            [''],
        ]
        
        for row in instrucciones:
            ws_instrucciones.append(row)
        
        # Formato de instrucciones
        ws_instrucciones.column_dimensions['A'].width = 80
        for row in ws_instrucciones.iter_rows():
            for cell in row:
                cell.alignment = Alignment(wrap_text=False)
        
        # Poner hoja de Lotes como activa
        wb.active = ws
        
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=Plantilla_Lotes.xlsx'
        wb.save(response)
        return response
    
    @action(detail=False, methods=['get'])
    def por_vencer(self, request):
        """
        Obtiene lotes proximos a vencer.
        
        Parametros:
        - dias: numero de dias (default: 30)
        """
        try:
            from datetime import date, timedelta
            
            dias = int(request.query_params.get('dias', 30))
            fecha_limite = date.today() + timedelta(days=dias)
            
            lotes = Lote.objects.select_related('producto').filter(
                activo=True,
                cantidad_actual__gt=0,
                fecha_caducidad__lte=fecha_limite
            ).order_by('fecha_caducidad')
            
            serializer = self.get_serializer(lotes, many=True)
            
            return Response({
                'total': lotes.count(),
                'dias_configurados': dias,
                'fecha_limite': fecha_limite,
                'lotes': serializer.data
            })
            
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            return Response({
                'error': 'Error al obtener lotes por vencer',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='por-caducar')
    def por_caducar(self, request):
        """Alias compatible para el frontend: lotes proximos a vencer."""
        try:
            from datetime import date, timedelta

            dias = int(request.query_params.get('dias', 90))
            hoy = date.today()
            fecha_limite = hoy + timedelta(days=dias)
            lotes = Lote.objects.select_related('producto').filter(
                cantidad_actual__gt=0,
                fecha_caducidad__gt=hoy,
                fecha_caducidad__lte=fecha_limite
            ).order_by('fecha_caducidad')

            page = self.paginate_queryset(lotes)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(lotes, many=True)
            return Response(serializer.data)
        except Exception as exc:
            # traceback removido por seguridad (ISS-008)
            return Response({'error': 'Error al obtener lotes por caducar', 'mensaje': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def vencidos(self, request):
        """Lotes con caducidad vencida y stock disponible."""
        try:
            from datetime import date

            hoy = date.today()
            lotes = Lote.objects.select_related('producto').filter(
                cantidad_actual__gt=0,
                fecha_caducidad__lt=hoy
            ).order_by('fecha_caducidad')

            page = self.paginate_queryset(lotes)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(lotes, many=True)
            return Response(serializer.data)
        except Exception as exc:
            # traceback removido por seguridad (ISS-008)
            return Response({'error': 'Error al obtener lotes vencidos', 'mensaje': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def historial(self, request, pk=None):
        """Obtiene el historial de movimientos de un lote"""
        try:
            lote = self.get_object()
            
            movimientos = Movimiento.objects.filter(lote=lote).select_related(
                'lote__producto'
            ).order_by('-fecha')
            
            from django.db.models import Sum
            
            total_entradas = movimientos.filter(tipo='entrada').aggregate(
                total=Sum('cantidad')
            )['total'] or 0
            
            total_salidas = movimientos.filter(tipo='salida').aggregate(
                total=Sum('cantidad')
            )['total'] or 0
            
            movimientos_data = []
            for mov in movimientos:
                movimientos_data.append({
                    'id': mov.id,
                    'tipo': mov.tipo,
                    'cantidad': mov.cantidad,
                    'fecha': mov.fecha,
                    'observaciones': mov.observaciones or ''
                })
            
            return Response({
                'lote': {
                    'id': lote.id,
                    'numero_lote': lote.numero_lote,
                    'producto': lote.producto.clave,
                    'cantidad_actual': lote.cantidad_actual
                },
                'estadisticas': {
                    'total_entradas': total_entradas,
                    'total_salidas': total_salidas,
                    'diferencia': total_entradas - total_salidas
                },
                'movimientos': movimientos_data,
                'total_movimientos': len(movimientos_data)
            })
            
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            return Response({
                'error': 'Error al obtener historial',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def ajustar_stock(self, request, pk=None):
        """
        Ajusta stock del lote y crea movimiento asociado (entrada/salida/ajuste).
        """
        lote = self.get_object()
        tipo = request.data.get('tipo', 'ajuste')
        cantidad = request.data.get('cantidad')
        observaciones = request.data.get('observaciones', '')

        try:
            movimiento, lote_actualizado = registrar_movimiento_stock(
                lote=lote,
                tipo=tipo,
                cantidad=cantidad,
                usuario=request.user if request.user.is_authenticated else None,
                centro=None,
                requisicion=None,
                observaciones=observaciones
            )
            return Response({
                'mensaje': 'Stock ajustado correctamente',
                'lote': self.get_serializer(lote_actualizado).data,
                'movimiento_id': movimiento.id
            })
        except serializers.ValidationError as exc:
            return Response({'error': 'Error de validacion', 'detalles': exc.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            # traceback removido por seguridad (ISS-008)
            return Response({'error': 'Error al ajustar stock', 'mensaje': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='lotes-derivados')
    def lotes_derivados(self, request, pk=None):
        """
        Obtiene los lotes derivados de un lote de farmacia (vinculados a centros).
        
        Solo aplica para lotes de farmacia central (centro=NULL).
        Muestra todos los centros que tienen stock de este lote.
        """
        try:
            lote = self.get_object()
            
            # Verificar que es un lote de farmacia
            if lote.centro is not None:
                return Response({
                    'error': 'Solo los lotes de farmacia central tienen lotes derivados',
                    'lote_id': lote.id,
                    'centro': lote.centro.nombre if lote.centro else None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Nota: En Supabase no hay lote_origen, se simplifica
            # Los lotes derivados se manejan diferente
            derivados = Lote.objects.none()
            
            # Calcular totales
            from django.db.models import Sum
            total_derivados = 0
            stock_total_centros = 0
            
            derivados_data = []
            # Código original removido - lote_origen no existe en Supabase
            
            return Response({
                'lote_farmacia': {
                    'id': lote.id,
                    'numero_lote': lote.numero_lote,
                    'producto_clave': lote.producto.clave,
                    'producto_nombre': lote.producto.nombre,
                    'cantidad_actual': lote.cantidad_actual,
                    'fecha_caducidad': lote.fecha_caducidad
                },
                'resumen': {
                    'total_centros_con_stock': total_derivados,
                    'stock_total_en_centros': stock_total_centros,
                    'stock_farmacia': lote.cantidad_actual,
                    'stock_total_sistema': lote.cantidad_actual + stock_total_centros
                },
                'lotes_derivados': derivados_data
            })
            
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            return Response({
                'error': 'Error al obtener lotes derivados',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='trazabilidad')
    def trazabilidad_lote(self, request, pk=None):
        """
        Obtiene la trazabilidad completa de un lote:
        - Si es lote de farmacia: muestra derivados en centros
        - Si es lote de centro: muestra origen en farmacia
        """
        try:
            lote = self.get_object()
            
            result = {
                'lote': {
                    'id': lote.id,
                    'numero_lote': lote.numero_lote,
                    'producto_clave': lote.producto.clave,
                    'producto_descripcion': lote.producto.descripcion,
                    'cantidad_actual': lote.cantidad_actual,
                    'fecha_caducidad': lote.fecha_caducidad,
                    'es_lote_farmacia': lote.centro is None,
                    'ubicacion': lote.centro.nombre if lote.centro else 'Farmacia Central'
                },
                'origen': None,
                'derivados': []
            }
            
            # En Supabase no hay lote_origen - trazabilidad simplificada
            # Los lotes de cada centro son independientes
            
            # Movimientos relacionados
            movimientos = Movimiento.objects.filter(
                lote=lote
            ).select_related('requisicion', 'usuario', 'centro_origen', 'centro_destino').order_by('-fecha')[:20]
            
            result['movimientos'] = [{
                'id': m.id,
                'tipo': m.tipo,
                'cantidad': m.cantidad,
                'fecha': m.fecha,
                'requisicion_folio': m.requisicion.folio if m.requisicion else None,
                'observaciones': m.observaciones
            } for m in movimientos]
            
            return Response(result)
            
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            return Response({
                'error': 'Error al obtener trazabilidad',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # =========================================================================
    # ACCIONES DE DOCUMENTOS (facturas, contratos, remisiones)
    # =========================================================================
    
    @action(detail=True, methods=['get'], url_path='documentos')
    def listar_documentos(self, request, pk=None):
        """
        Lista todos los documentos asociados a un lote.
        """
        try:
            lote = self.get_object()
            documentos = LoteDocumento.objects.filter(lote=lote).order_by('-created_at')
            serializer = LoteDocumentoSerializer(documentos, many=True)
            return Response({
                'lote_id': lote.id,
                'numero_lote': lote.numero_lote,
                'total_documentos': documentos.count(),
                'documentos': serializer.data
            })
        except Exception as e:
            return Response({
                'error': 'Error al obtener documentos',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='subir-documento')
    def subir_documento(self, request, pk=None):
        """
        Sube un documento (PDF) asociado al lote.
        
        Campos requeridos:
        - documento: archivo PDF (multipart)
        - tipo_documento: factura/contrato/remision/otro
        
        Campos opcionales:
        - numero_documento: número del documento
        - fecha_documento: fecha del documento (YYYY-MM-DD)
        - notas: notas adicionales
        """
        try:
            lote = self.get_object()
            
            # Validar permisos de escritura
            user = request.user
            if not is_farmacia_or_admin(user):
                user_centro = get_user_centro(user)
                lote_centro = lote.centro
                if lote_centro is None or (user_centro and lote_centro.pk != user_centro.pk):
                    return Response(
                        {'error': 'No tiene permisos para subir documentos a este lote'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # ISS-005 FIX (audit7): Validar archivo PDF con función centralizada
            archivo = request.FILES.get('documento')
            if not archivo:
                return Response(
                    {'error': 'Debe proporcionar un archivo'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Usar validador centralizado que verifica extensión, tamaño Y magic bytes
            es_valido, error_msg = validar_archivo_pdf(archivo)
            if not es_valido:
                return Response(
                    {'error': error_msg},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validar tipo de documento
            tipo_documento = request.data.get('tipo_documento', 'otro')
            tipos_validos = ['factura', 'contrato', 'remision', 'otro']
            if tipo_documento not in tipos_validos:
                return Response(
                    {'error': f'Tipo de documento inválido. Valores permitidos: {tipos_validos}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Generar path único para el archivo
            import uuid
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            unique_name = f"{tipo_documento}_{timestamp}_{uuid.uuid4().hex[:8]}.pdf"
            archivo_path = f"lotes/documentos/{lote.id}/{unique_name}"
            
            # ISS-001 FIX: Subir archivo al almacenamiento ANTES de crear registro
            from inventario.services.storage_service import get_storage_service, StorageError
            
            storage = get_storage_service()
            upload_result = storage.upload_file(
                file_content=archivo,
                file_path=archivo_path,
                content_type='application/pdf',
                metadata={
                    'lote_id': lote.id,
                    'tipo_documento': tipo_documento,
                    'uploaded_by': user.username if user.is_authenticated else 'anonymous'
                }
            )
            
            # ISS-001 FIX: Si falla la subida, NO crear registro (rollback)
            if not upload_result.get('success'):
                logger.error(
                    f"ISS-001: Fallo subida documento lote {lote.id}: {upload_result.get('error')}"
                )
                return Response({
                    'error': 'Error al guardar archivo en almacenamiento',
                    'detalle': upload_result.get('error', 'Error desconocido')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Parsear fecha si viene
            fecha_documento = None
            if request.data.get('fecha_documento'):
                try:
                    fecha_documento = datetime.strptime(
                        request.data.get('fecha_documento'), '%Y-%m-%d'
                    ).date()
                except ValueError:
                    pass
            
            # ISS-001 FIX: Solo crear registro si la subida fue exitosa
            try:
                documento = LoteDocumento.objects.create(
                    lote=lote,
                    tipo_documento=tipo_documento,
                    numero_documento=request.data.get('numero_documento', ''),
                    archivo=archivo_path,
                    nombre_archivo=nombre_archivo,
                    fecha_documento=fecha_documento,
                    notas=request.data.get('notas', ''),
                    created_by=user if user.is_authenticated else None
                )
            except Exception as db_error:
                # ISS-001 FIX: Si falla crear registro, eliminar archivo subido (rollback)
                logger.error(f"ISS-001: Error BD, revirtiendo subida: {db_error}")
                storage.delete_file(archivo_path)
                raise
            
            logger.info(
                f"ISS-001: Documento subido exitosamente - Lote: {lote.id}, "
                f"Path: {archivo_path}, Storage: {upload_result.get('storage')}"
            )
            
            serializer = LoteDocumentoSerializer(documento)
            return Response({
                'mensaje': 'Documento subido correctamente',
                'documento': serializer.data,
                'storage_info': {
                    'path': archivo_path,
                    'url': upload_result.get('url'),
                    'storage_type': upload_result.get('storage')
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': 'Error al subir documento',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['delete'], url_path='eliminar-documento/(?P<doc_id>[0-9]+)')
    def eliminar_documento(self, request, pk=None, doc_id=None):
        """
        Elimina un documento específico del lote.
        """
        try:
            lote = self.get_object()
            
            # Validar permisos de escritura
            user = request.user
            if not is_farmacia_or_admin(user):
                user_centro = get_user_centro(user)
                lote_centro = lote.centro
                if lote_centro is None or (user_centro and lote_centro.pk != user_centro.pk):
                    return Response(
                        {'error': 'No tiene permisos para eliminar documentos de este lote'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Buscar documento
            try:
                documento = LoteDocumento.objects.get(id=doc_id, lote=lote)
            except LoteDocumento.DoesNotExist:
                return Response(
                    {'error': 'Documento no encontrado'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # ISS-002 FIX: Eliminar archivo del almacenamiento ANTES de borrar registro
            from inventario.services.storage_service import get_storage_service
            
            archivo_path = documento.archivo
            nombre = documento.nombre_archivo
            
            storage = get_storage_service()
            delete_result = storage.delete_file(archivo_path)
            
            # ISS-002 FIX: Registrar resultado de eliminación de storage
            if not delete_result.get('success'):
                logger.warning(
                    f"ISS-002: No se pudo eliminar archivo '{archivo_path}' del storage: "
                    f"{delete_result.get('error')}. Se eliminará el registro de BD igualmente."
                )
            else:
                logger.info(
                    f"ISS-002: Archivo eliminado de storage: {archivo_path}"
                )
            
            # Eliminar registro de BD
            documento.delete()
            
            logger.info(
                f"ISS-002: Documento eliminado - Lote: {lote.id}, "
                f"Archivo: {nombre}, Path: {archivo_path}"
            )
            
            return Response({
                'mensaje': 'Documento eliminado correctamente',
                'documento_eliminado': nombre,
                'storage_cleanup': delete_result.get('success', False)
            })
            
        except Exception as e:
            return Response({
                'error': 'Error al eliminar documento',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MovimientoViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet
):
    """
    ViewSet para gestionar movimientos de inventario.
    
    PERMISOS:
    - Admin/Farmacia: acceso completo a todos los movimientos
    - Centro (administrador_centro, director_centro): puede VER y CREAR movimientos
    - Medico: NO puede crear movimientos (ISS-MEDICO FIX)
    - Vista: solo lectura
    
    FILTROS (alineados con exportacin):
    - tipo: entrada/salida/ajuste
    - centro: ID del centro
    - producto: ID del producto
    - lote: ID del lote
    - fecha_inicio: YYYY-MM-DD
    - fecha_fin: YYYY-MM-DD
    - search: bsqueda en observaciones, nmero de lote, producto
    
    Esto permite auditora completa de consumos en cada centro.
    """
    queryset = Movimiento.objects.select_related('lote__producto', 'centro_origen', 'centro_destino', 'usuario').all()
    serializer_class = MovimientoSerializer
    # ISS-MEDICO FIX: Usar permiso que excluye médico de operaciones de escritura
    permission_classes = [IsCentroCanManageInventory]
    pagination_class = CustomPagination
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        """
        Filtra movimientos segun parametros.
        
        Parametros (alineados con exportacin):
        - tipo: entrada/salida/ajuste
        - centro: ID del centro (solo admin/farmacia/vista)
        - producto: ID del producto
        - lote: ID del lote
        - fecha_inicio: fecha mnima (YYYY-MM-DD)
        - fecha_fin: fecha mxima (YYYY-MM-DD)
        - search: bsqueda en observaciones, lote, producto
        
        Seguridad: Usuarios de centro solo ven movimientos de su centro.
        Admin/farmacia/vista ven todo por defecto, pueden filtrar con ?centro=.
        """
        queryset = Movimiento.objects.select_related('lote__producto', 'centro_origen', 'centro_destino', 'usuario')
        
        # ISS-019 FIX: Filtrar por centro según rol usando has_global_read_access
        # que incluye admin, farmacia Y vista para lectura global
        user = self.request.user
        if not has_global_read_access(user):
            # Usuario de centro: forzado a su centro
            # ISS-CENTRO FIX: Incluir movimientos donde el centro es origen, destino O el lote pertenece al centro
            user_centro = get_user_centro(user)
            if user_centro:
                queryset = queryset.filter(
                    Q(lote__centro=user_centro) | 
                    Q(centro_origen=user_centro) | 
                    Q(centro_destino=user_centro)
                )
            else:
                return Movimiento.objects.none()
        else:
            # Admin/farmacia/vista: pueden filtrar por centro especifico
            centro_param = self.request.query_params.get('centro')
            if centro_param:
                # ISS-CENTRO FIX: Filtrar por centro origen, destino O lote
                queryset = queryset.filter(
                    Q(lote__centro_id=centro_param) | 
                    Q(centro_origen_id=centro_param) | 
                    Q(centro_destino_id=centro_param)
                )
        
        # Filtro por tipo
        tipo = self.request.query_params.get('tipo')
        if tipo:
            queryset = queryset.filter(tipo=tipo.lower())
        
        # Filtro por producto
        producto = self.request.query_params.get('producto')
        if producto:
            queryset = queryset.filter(lote__producto_id=producto)
        
        # Filtro por lote (acepta ID numérico o número de lote como texto)
        lote = self.request.query_params.get('lote')
        if lote:
            if lote.isdigit():
                # Si es un número, buscar por ID
                queryset = queryset.filter(lote_id=lote)
            else:
                # Si es texto, buscar por número de lote (coincidencia parcial)
                queryset = queryset.filter(lote__numero_lote__icontains=lote)
        
        # Filtro por subtipo de salida (receta, consumo_interno, merma, etc.)
        subtipo_salida = self.request.query_params.get('subtipo_salida')
        if subtipo_salida:
            queryset = queryset.filter(subtipo_salida__iexact=subtipo_salida)
        
        # Filtro por rango de fechas
        fecha_inicio = self.request.query_params.get('fecha_inicio')
        if fecha_inicio:
            queryset = queryset.filter(fecha__date__gte=fecha_inicio)
        
        fecha_fin = self.request.query_params.get('fecha_fin')
        if fecha_fin:
            queryset = queryset.filter(fecha__date__lte=fecha_fin)
        
        # Busqueda en motivo, lote y producto
        search = self.request.query_params.get('search')
        if search and search.strip():
            search_term = search.strip()
            queryset = queryset.filter(
                Q(motivo__icontains=search_term) |
                Q(lote__numero_lote__icontains=search_term) |
                Q(lote__producto__clave__icontains=search_term) |
                Q(lote__producto__descripcion__icontains=search_term) |
                Q(numero_expediente__icontains=search_term)
            )
        
        return queryset.order_by('-fecha')

    def perform_create(self, serializer):
        """
        Crea un movimiento validando permisos por centro.
        
        SEGURIDAD:
        - Admin/farmacia: pueden crear cualquier movimiento en cualquier lote
        - Usuario de centro (administrador/director): pueden crear movimientos en lotes de su centro
          y solo ciertos tipos: 'salida' (consumo), 'ajuste' (inventario físico)
        - Médico: Solo puede crear movimientos de SALIDA (para dispensación a pacientes)
        - Usuario de centro NO puede crear 'entrada' (solo vía surtido de requisición)
        """
        user = self.request.user
        lote = serializer.validated_data.get('lote')
        tipo = serializer.validated_data.get('tipo', '').lower()
        motivo = serializer.validated_data.get('motivo', '').strip()
        
        # ISS-MEDICO FIX v2: Médicos SOLO pueden crear SALIDAS (para dispensación a pacientes)
        if RoleHelper.is_medico(user):
            if tipo != 'salida':
                raise serializers.ValidationError({
                    'tipo': 'Los médicos solo pueden registrar movimientos de SALIDA para dispensación a pacientes.'
                })
            # Observaciones/motivo son OBLIGATORIAS para médicos
            if not motivo:
                raise serializers.ValidationError({
                    'motivo': 'Las observaciones son obligatorias. Indique el motivo de la salida (ej: dispensación a paciente, nombre del paciente, etc.).'
                })
        
        # Validar que usuario de centro solo opere con sus lotes
        if not is_farmacia_or_admin(user):
            user_centro = get_user_centro(user)
            
            # Validar que el lote pertenece al centro del usuario
            if lote and lote.centro != user_centro:
                raise serializers.ValidationError({
                    'lote': 'Solo puedes registrar movimientos en lotes de tu centro'
                })
            
            # Validar tipos de movimiento permitidos para centros
            # Centros pueden: salida (consumo), ajuste (inventario fsico)
            # Centros NO pueden: entrada (solo va surtido automtico)
            tipos_permitidos_centro = ['salida', 'ajuste']
            if tipo not in tipos_permitidos_centro:
                raise serializers.ValidationError({
                    'tipo': f'Los centros solo pueden registrar: {", ".join(tipos_permitidos_centro)}. Las entradas se generan automticamente al surtir requisiciones.'
                })
        
        # MEJORA FLUJO 5: Extraer campos de trazabilidad
        subtipo_salida = serializer.validated_data.get('subtipo_salida')
        numero_expediente = serializer.validated_data.get('numero_expediente')
        
        movimiento, _ = registrar_movimiento_stock(
            lote=lote,
            tipo=serializer.validated_data.get('tipo'),
            cantidad=serializer.validated_data.get('cantidad'),
            usuario=user,
            centro=serializer.validated_data.get('centro') or (lote.centro if lote else None),
            requisicion=serializer.validated_data.get('requisicion'),
            # FIX: El serializer mapea 'observaciones' del frontend a 'motivo' via to_internal_value
            observaciones=serializer.validated_data.get('motivo', ''),
            subtipo_salida=subtipo_salida,
            numero_expediente=numero_expediente
        )
        # Dejar instancia lista para serializer.data
        serializer.instance = movimiento

    @action(detail=False, methods=['get'], url_path='trazabilidad-pdf')
    def trazabilidad_pdf(self, request):
        """
        Genera PDF de trazabilidad de un producto.
        Parmetros: ?producto_clave=XXX
        
        SEGURIDAD: Filtra por centro del usuario si no es admin/farmacia.
        """
        from core.utils.pdf_reports import generar_reporte_trazabilidad
        
        # SEGURIDAD: Verificar permisos y determinar filtro de centro
        user = request.user
        filtrar_por_centro = not is_farmacia_or_admin(user)
        user_centro = get_user_centro(user) if filtrar_por_centro else None
        
        clave = request.query_params.get('producto_clave')
        if not clave:
            return Response({'error': 'Se requiere producto_clave'}, status=status.HTTP_400_BAD_REQUEST)
        
        producto = Producto.objects.filter(
            Q(clave__iexact=clave) | Q(descripcion__iexact=clave)
        ).first()
        if not producto:
            return Response({'error': 'Producto no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            # Obtener movimientos del producto
            movimientos = Movimiento.objects.filter(
                lote__producto=producto
            ).select_related('lote', 'centro_origen', 'centro_destino', 'usuario')
            
            # Aplicar filtro de centro si corresponde
            if filtrar_por_centro and user_centro:
                movimientos = movimientos.filter(
                    Q(centro_origen=user_centro) | Q(centro_destino=user_centro) | Q(lote__centro=user_centro)
                )
            
            movimientos = movimientos.order_by('-fecha')[:100]
            
            trazabilidad_data = []
            for mov in movimientos:
                trazabilidad_data.append({
                    'fecha': mov.fecha.strftime('%d/%m/%Y %H:%M') if mov.fecha else 'N/A',
                    'tipo': mov.tipo.upper(),
                    'lote': mov.lote.numero_lote if mov.lote else 'N/A',
                    'cantidad': mov.cantidad,
                    'centro': mov.centro_destino.nombre if mov.centro_destino else (mov.centro_origen.nombre if mov.centro_origen else 'Farmacia Central'),
                    'usuario': mov.usuario.get_full_name() if mov.usuario else 'Sistema',
                    'observaciones': mov.motivo or ''
                })
            
            producto_info = {
                'clave': producto.clave,
                'descripcion': producto.nombre,  # Usar nombre como descripción principal
                'unidad_medida': producto.unidad_medida,
                'stock_actual': producto.get_stock_actual() if hasattr(producto, 'get_stock_actual') else 0,
                'stock_minimo': producto.stock_minimo,
                'precio_unitario': 0,  # precio_unitario está en Lote, no en Producto
            }
            
            pdf_buffer = generar_reporte_trazabilidad(trazabilidad_data, producto_info=producto_info)
            
            response = HttpResponse(
                pdf_buffer.getvalue(),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'attachment; filename="Trazabilidad_{clave}_{timezone.now().strftime("%Y%m%d")}.pdf"'
            
            return response
            
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            return Response({
                'error': 'Error al generar PDF de trazabilidad',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='trazabilidad-lote-pdf')
    def trazabilidad_lote_pdf(self, request):
        """
        Genera PDF de trazabilidad de un lote especfico.
        Parmetros: ?numero_lote=XXX
        
        SEGURIDAD: Solo admin/farmacia pueden acceder.
        """
        from core.utils.pdf_reports import generar_reporte_trazabilidad
        
        # SEGURIDAD: Solo admin/farmacia pueden exportar trazabilidad de lotes
        if not is_farmacia_or_admin(request.user):
            return Response({'error': 'Solo administradores y farmacia pueden exportar trazabilidad de lotes'}, status=status.HTTP_403_FORBIDDEN)
        
        numero_lote = request.query_params.get('numero_lote')
        if not numero_lote:
            return Response({'error': 'Se requiere numero_lote'}, status=status.HTTP_400_BAD_REQUEST)
        
        lote = Lote.objects.filter(numero_lote__iexact=numero_lote).select_related('producto', 'centro').first()
        if not lote:
            return Response({'error': 'Lote no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            # Obtener movimientos del lote
            movimientos = Movimiento.objects.filter(
                lote=lote
            ).select_related('lote', 'centro_origen', 'centro_destino', 'usuario').order_by('-fecha')[:100]
            
            trazabilidad_data = []
            for mov in movimientos:
                trazabilidad_data.append({
                    'fecha': mov.fecha.strftime('%d/%m/%Y %H:%M') if mov.fecha else 'N/A',
                    'tipo': mov.tipo.upper(),
                    'lote': mov.lote.numero_lote if mov.lote else 'N/A',
                    'cantidad': mov.cantidad,
                    'centro': mov.centro_destino.nombre if mov.centro_destino else (mov.centro_origen.nombre if mov.centro_origen else 'Farmacia Central'),
                    'usuario': mov.usuario.get_full_name() if mov.usuario else 'Sistema',
                    'observaciones': mov.motivo or ''
                })
            
            producto_info = {
                'clave': lote.producto.clave if lote.producto else 'N/A',
                'descripcion': lote.producto.descripcion if lote.producto else 'N/A',
                'unidad_medida': lote.producto.unidad_medida if lote.producto else 'N/A',
                'stock_actual': lote.cantidad_actual,
                'stock_minimo': lote.producto.stock_minimo if lote.producto else 0,
                'numero_lote': lote.numero_lote,
                'fecha_caducidad': lote.fecha_caducidad.strftime('%d/%m/%Y') if lote.fecha_caducidad else 'N/A',
                'proveedor': lote.marca or 'No especificado',
            }
            
            pdf_buffer = generar_reporte_trazabilidad(trazabilidad_data, producto_info=producto_info)
            
            response = HttpResponse(
                pdf_buffer.getvalue(),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'attachment; filename="Trazabilidad_Lote_{numero_lote}_{timezone.now().strftime("%Y%m%d")}.pdf"'
            
            return response
            
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            return Response({
                'error': 'Error al generar PDF de trazabilidad del lote',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='exportar-pdf')
    def exportar_pdf(self, request):
        """
        Genera PDF de movimientos con filtros opcionales.
        Filtros soportados: tipo, fecha_inicio, fecha_fin, producto, centro, lote, subtipo_salida, search
        """
        from core.utils.pdf_reports import generar_reporte_movimientos
        
        try:
            # Aplicar filtros (get_queryset ya aplica filtros base, aquí se duplican por consistencia explícita)
            queryset = self.get_queryset()
            
            tipo = request.query_params.get('tipo')
            if tipo:
                queryset = queryset.filter(tipo=tipo.lower())
            
            fecha_inicio = request.query_params.get('fecha_inicio')
            if fecha_inicio:
                queryset = queryset.filter(fecha__gte=fecha_inicio)
            
            fecha_fin = request.query_params.get('fecha_fin')
            if fecha_fin:
                queryset = queryset.filter(fecha__lte=fecha_fin)
            
            # FIX: Agregar filtros faltantes para consistencia total
            producto = request.query_params.get('producto')
            if producto:
                queryset = queryset.filter(lote__producto_id=producto)
            
            centro = request.query_params.get('centro')
            if centro:
                queryset = queryset.filter(Q(centro_origen_id=centro) | Q(centro_destino_id=centro) | Q(lote__centro_id=centro))
            
            lote = request.query_params.get('lote')
            if lote:
                if lote.isdigit():
                    queryset = queryset.filter(lote_id=lote)
                else:
                    queryset = queryset.filter(lote__numero_lote__icontains=lote)
            
            subtipo_salida = request.query_params.get('subtipo_salida')
            if subtipo_salida:
                queryset = queryset.filter(subtipo_salida__iexact=subtipo_salida)
            
            search = request.query_params.get('search')
            if search:
                queryset = queryset.filter(
                    Q(lote__numero_lote__icontains=search) |
                    Q(lote__producto__nombre__icontains=search) |
                    Q(lote__producto__descripcion__icontains=search) |
                    Q(motivo__icontains=search) |
                    Q(numero_expediente__icontains=search)
                )
            
            movimientos = queryset[:200]  # Limitar para PDF
            
            # Agrupar movimientos por referencia/transacción para PDF
            transacciones = {}
            total_entradas = 0
            total_salidas = 0
            
            for mov in movimientos:
                amount = abs(mov.cantidad) if mov.tipo == 'salida' else mov.cantidad
                ref = mov.referencia or f"MOV-{mov.id}"
                
                if ref not in transacciones:
                    transacciones[ref] = {
                        'referencia': ref,
                        'fecha': mov.fecha.strftime('%d/%m/%Y %H:%M') if mov.fecha else 'N/A',
                        'tipo': mov.tipo.upper(),
                        'centro_origen': mov.centro_origen.nombre if mov.centro_origen else 'Farmacia Central',
                        'centro_destino': mov.centro_destino.nombre if mov.centro_destino else 'Farmacia Central',
                        'total_productos': 0,
                        'total_cantidad': 0,
                        'detalles': []
                    }
                
                transacciones[ref]['detalles'].append({
                    'producto': f"{mov.lote.producto.clave if mov.lote and mov.lote.producto else 'N/A'} - {getattr(mov.lote.producto, 'descripcion', '')[:40] if mov.lote and mov.lote.producto else ''}",
                    'lote': mov.lote.numero_lote if mov.lote else 'N/A',
                    'cantidad': amount
                })
                transacciones[ref]['total_productos'] += 1
                transacciones[ref]['total_cantidad'] += amount
                
                if mov.tipo == 'entrada':
                    total_entradas += amount
                else:
                    total_salidas += amount
            
            movimientos_data = list(transacciones.values())
            resumen_data = {
                'total_transacciones': len(movimientos_data),
                'total_movimientos': sum(t['total_productos'] for t in movimientos_data),
                'total_entradas': total_entradas,
                'total_salidas': total_salidas,
                'diferencia': total_entradas - total_salidas
            }
            
            pdf_buffer = generar_reporte_movimientos(movimientos_data, resumen=resumen_data)
            
            response = HttpResponse(
                pdf_buffer.getvalue(),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'attachment; filename="Movimientos_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
            
            return response
            
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            return Response({
                'error': 'Error al generar PDF de movimientos',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='exportar-excel')
    def exportar_excel(self, request):
        """
        Genera Excel de movimientos con filtros opcionales.
        Filtros soportados: tipo, fecha_inicio, fecha_fin, producto, centro, lote, subtipo_salida, search
        """
        try:
            # Aplicar filtros (get_queryset ya aplica filtros base, aquí se duplican por consistencia explícita)
            queryset = self.get_queryset()
            
            tipo = request.query_params.get('tipo')
            if tipo:
                queryset = queryset.filter(tipo=tipo.lower())
            
            fecha_inicio = request.query_params.get('fecha_inicio')
            if fecha_inicio:
                queryset = queryset.filter(fecha__gte=fecha_inicio)
            
            fecha_fin = request.query_params.get('fecha_fin')
            if fecha_fin:
                queryset = queryset.filter(fecha__lte=fecha_fin)
            
            producto = request.query_params.get('producto')
            if producto:
                queryset = queryset.filter(lote__producto_id=producto)
            
            centro = request.query_params.get('centro')
            if centro:
                queryset = queryset.filter(Q(centro_origen_id=centro) | Q(centro_destino_id=centro) | Q(lote__centro_id=centro))
            
            # FIX: Agregar filtros faltantes para consistencia total
            lote = request.query_params.get('lote')
            if lote:
                if lote.isdigit():
                    queryset = queryset.filter(lote_id=lote)
                else:
                    queryset = queryset.filter(lote__numero_lote__icontains=lote)
            
            subtipo_salida = request.query_params.get('subtipo_salida')
            if subtipo_salida:
                queryset = queryset.filter(subtipo_salida__iexact=subtipo_salida)
            
            search = request.query_params.get('search')
            if search:
                queryset = queryset.filter(
                    Q(lote__numero_lote__icontains=search) |
                    Q(lote__producto__nombre__icontains=search) |
                    Q(lote__producto__descripcion__icontains=search) |
                    Q(motivo__icontains=search) |
                    Q(numero_expediente__icontains=search)
                )
            
            movimientos = queryset[:1000]  # Limitar para Excel
            
            # Crear libro de Excel
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Movimientos'
            
            # Título - MEJORA FLUJO 5: Extender a 11 columnas (K)
            ws.merge_cells('A1:K1')
            ws['A1'] = 'REPORTE DE MOVIMIENTOS'
            ws['A1'].font = Font(bold=True, size=14, color='632842')
            ws['A1'].alignment = Alignment(horizontal='center')
            
            # Fecha
            ws.merge_cells('A2:K2')
            ws['A2'] = f'Generado el {timezone.now().strftime("%d/%m/%Y %H:%M")}'
            ws['A2'].alignment = Alignment(horizontal='center')
            
            # Encabezados - MEJORA FLUJO 5: Incluir subtipo y expediente
            headers = ['#', 'Fecha', 'Tipo', 'Subtipo', 'Producto', 'Lote', 'Cantidad', 'Centro', 'Usuario', 'No. Expediente', 'Observaciones']
            ws.append([])
            ws.append(headers)
            
            header_fill = PatternFill(start_color='632842', end_color='632842', fill_type='solid')
            header_font = Font(bold=True, color='FFFFFF')
            for cell in ws[4]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center')
            
            # Datos - MEJORA FLUJO 5: Incluir campos de trazabilidad
            for idx, mov in enumerate(movimientos, 1):
                ws.append([
                    idx,
                    mov.fecha.strftime('%d/%m/%Y %H:%M') if mov.fecha else 'N/A',
                    mov.tipo.upper(),
                    (mov.subtipo_salida or '').upper() if mov.tipo == 'salida' else '',
                    mov.lote.producto.descripcion[:50] if mov.lote and mov.lote.producto else 'N/A',
                    mov.lote.numero_lote if mov.lote else 'N/A',
                    mov.cantidad,
                    mov.centro_destino.nombre if mov.centro_destino else (mov.centro_origen.nombre if mov.centro_origen else 'Farmacia Central'),
                    mov.usuario.get_full_name() or mov.usuario.username if mov.usuario else 'Sistema',
                    mov.numero_expediente or '',
                    (mov.motivo or '')[:100],
                ])
            
            # Ajustar anchos - actualizado para 11 columnas
            column_widths = [8, 18, 12, 15, 45, 15, 10, 25, 20, 18, 30]
            for i, width in enumerate(column_widths, 1):
                ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = width
            
            # Respuesta
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="Movimientos_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
            wb.save(response)
            return response
            
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            return Response({
                'error': 'Error al generar Excel de movimientos',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RequisicionViewSet(CentroPermissionMixin, viewsets.ModelViewSet):
    """
    ISS-030: CRUD y flujo de requisiciones con control de acceso por centro.
    
    Estados en minúsculas:
    (borrador -> enviada -> autorizada/parcial -> surtida o rechazada/cancelada)
    
    ISS-011, ISS-021: El método surtir() usa RequisicionService para transacciones atómicas.
    ISS-014: Bloqueo optimista de lotes durante el surtido.
    ISS-030: Validación de acceso por centro en todas las operaciones.
    """
    queryset = Requisicion.objects.select_related('centro_origen', 'centro_destino', 'solicitante', 'autorizador').prefetch_related('detalles__producto').all()
    serializer_class = RequisicionSerializer
    permission_classes = [IsCentroRole]
    pagination_class = CustomPagination

    def _user_centro(self, user):
        return getattr(user, 'centro', None) or getattr(getattr(user, 'profile', None), 'centro', None)

    def _validar_stock_items(self, items, centro=None, validar_farmacia_central=True, modo='informativo'):
        """
        ISS-001, ISS-004, ISS-005 FIX: Valida stock disponible con lógica clara por ubicación.
        
        ISS-004 FIX (audit17): Optimizado para evitar N+1 queries.
        Usa agregación en bloque en lugar de consultas individuales por producto.
        
        ISS-005 FIX: Dos modos de validación:
        - 'informativo': Solo reporta problemas sin bloquear (para creación)
        - 'estricto': Bloquea si no hay stock suficiente (para autorización/surtido)
        
        LÓGICA DE VALIDACIÓN:
        - Para requisiciones (validar_farmacia_central=True): 
          Valida contra stock de FARMACIA CENTRAL, ya que las requisiciones
          solicitan medicamentos que serán surtidos desde farmacia.
          ISS-004: Solo considera lotes vigentes (no vencidos).
        
        - Para operaciones internas de centro (validar_farmacia_central=False):
          Valida contra stock del centro específico.
        
        Args:
            items: Lista de items con producto y cantidad
            centro: Centro para contexto (usado para info, no para validación de requisiciones)
            validar_farmacia_central: Si True, valida contra farmacia central
            modo: 'informativo' (default) o 'estricto'
            
        Returns:
            list: Lista de errores/advertencias de stock
        """
        from django.utils import timezone
        from django.db.models import Sum
        from core.models import Lote
        
        errores = []
        today = timezone.now().date()
        
        # ISS-004 FIX: Recopilar todos los producto_ids primero
        producto_ids = []
        items_validos = []
        
        for item_data in items:
            producto_id = item_data.get('producto')
            if not producto_id:
                continue
            try:
                cantidad = int(item_data.get('cantidad_autorizada') or item_data.get('cantidad_solicitada') or 0)
            except (TypeError, ValueError):
                continue
            
            if cantidad <= 0:
                continue
            
            producto_ids.append(producto_id)
            items_validos.append({
                'producto_id': producto_id,
                'cantidad': cantidad,
                'item_data': item_data
            })
        
        if not producto_ids:
            return errores
        
        # ISS-004 FIX: Prefetch de productos en una sola consulta
        productos = {p.id: p for p in Producto.objects.filter(id__in=producto_ids)}
        
        # ISS-004 FIX: Calcular stock en bloque usando agregación
        # Filtro base para lotes vigentes
        lotes_filter = {
            'activo': True,
            'fecha_caducidad__gte': today,
            'producto_id__in': producto_ids,
        }
        
        if validar_farmacia_central:
            # Stock de farmacia central = lotes sin centro
            lotes_filter['centro__isnull'] = True
        elif centro:
            # Stock de centro específico
            lotes_filter['centro'] = centro
        else:
            # Fallback a farmacia central
            lotes_filter['centro__isnull'] = True
        
        # Agregar stock por producto en una sola consulta
        stock_por_producto = dict(
            Lote.objects.filter(**lotes_filter)
            .values('producto_id')
            .annotate(total=Sum('cantidad_actual'))
            .values_list('producto_id', 'total')
        )
        
        # Validar cada item
        for item in items_validos:
            producto_id = item['producto_id']
            cantidad = item['cantidad']
            producto = productos.get(producto_id)
            
            if not producto:
                continue
            
            disponible = stock_por_producto.get(producto_id, 0) or 0
            
            if cantidad > disponible:
                error_item = {
                    'producto': producto.clave,
                    'descripcion': producto.descripcion[:50] if producto.descripcion else '',
                    'disponible': disponible,
                    'solicitado': cantidad,
                    'deficit': cantidad - disponible,
                    'ubicacion': 'farmacia_central' if validar_farmacia_central else (
                        centro.nombre if centro else 'farmacia_central'
                    ),
                    'nota': 'Solo se considera stock de lotes vigentes (no vencidos)',
                    # ISS-005: Indicar tipo de error según modo
                    'tipo': 'advertencia' if modo == 'informativo' else 'error',
                    'bloquea': modo == 'estricto'
                }
                errores.append(error_item)
        
        return errores

    def get_queryset(self):
        """
        FLUJO V2: Filtros de seguridad a nivel de fila (Row Level Security lógica).
        
        Cada rol ve solo las requisiciones que le corresponden según su posición
        en el flujo jerárquico.
        
        ISS-006 FIX (audit17): Registro de auditoría para accesos privilegiados.
        ISS-DIRECTOR FIX: Usa _get_rol_efectivo para consistencia.
        """
        from core.validators import AuditLogger
        
        queryset = Requisicion.objects.select_related(
            'centro_origen', 'centro_destino', 'solicitante', 'autorizador',
            # FLUJO V2: Actores del flujo
            'administrador_centro', 'director_centro', 
            'receptor_farmacia', 'autorizador_farmacia', 'surtidor'
        ).prefetch_related('detalles__producto')
        
        user = getattr(self.request, 'user', None)
        if not user or not user.is_authenticated:
            return Requisicion.objects.none()
        
        filter_applied = False  # ISS-006: Rastrear si se aplica filtro de centro
        
        # ISS-DIRECTOR FIX: Usar rol efectivo para consistencia con frontend
        rol = _get_rol_efectivo(user)
        
        # 1. Superusuario o Admin Global: Ve todo
        if user.is_superuser or rol == 'admin':
            # ISS-006 FIX: Registrar acceso privilegiado sin filtro
            AuditLogger.log_privileged_access(
                user, 
                'requisicion', 
                action='list_all',
                details={'sin_filtro_centro': True}
            )
            pass  # Sin filtro de centro
        
        # 2. Personal de Farmacia Central: Ve solo lo que ha sido enviado
        elif rol == 'farmacia':
            # Farmacia NO debe ver borradores ni pendientes internos del centro
            queryset = queryset.exclude(estado__in=['borrador', 'pendiente_admin', 'pendiente_director'])
            filter_applied = True
        
        # ISS-019 FIX: 2.5 Rol Vista (Auditoría/Control): Lectura global para trazabilidad
        elif rol == 'vista':
            # Vista puede ver todo para auditoría, sin requerir centro asignado
            # Excluir borradores (no son documentos oficiales aún)
            queryset = queryset.exclude(estado='borrador')
            AuditLogger.log_privileged_access(
                user,
                'requisicion',
                action='list_audit',
                details={'rol': 'vista', 'acceso_global': True}
            )
            filter_applied = True  # Marca como filtrado (excluyó borradores)
        
        # 3. Usuarios de Centros Penitenciarios
        else:
            user_centro = self._user_centro(user)
            if not user_centro:
                # ISS-DIRECTOR FIX: Marcar que no hay centro para validación posterior
                # El método list() validará esto y retornará 403
                self._missing_centro = True
                return Requisicion.objects.none()
            
            # Filtrar por centro del usuario
            queryset = queryset.filter(
                Q(centro_origen=user_centro) | Q(centro_destino=user_centro)
            )
            
            # 3.1 Médico: Solo sus propias requisiciones (las que creó)
            if rol == 'medico':
                queryset = queryset.filter(solicitante=user)
            
            # 3.2 Administrador Centro: Ve desde pendiente_admin en adelante
            # FLUJO V2: Admin NO ve borradores de otros ni pendiente_director (eso es del director)
            # ISS-ROL-FIX: Incluir alias 'admin_centro' para compatibilidad
            elif rol in ['administrador_centro', 'admin_centro']:
                # Puede ver: pendiente_admin (para autorizar) + todo lo que ya pasó esa etapa
                # NO ve: borradores de otros
                queryset = queryset.exclude(
                    Q(estado='borrador') & ~Q(solicitante=user)
                )
            
            # 3.3 Director Centro: Ve SOLO desde pendiente_director en adelante
            # FLUJO V2: Director NO debe ver pendiente_admin (eso es del Admin)
            # ISS-ROL-FIX: Incluir alias 'director' para compatibilidad
            elif rol in ['director_centro', 'director']:
                # Estados que el director puede ver:
                # - pendiente_director: para autorizar
                # - enviada, autorizada, parcial, surtida, entregada: ya autorizados
                # - rechazada, cancelada, vencida: finalizados
                # NO ve: borrador, pendiente_admin (aún no llegó a su etapa)
                queryset = queryset.exclude(estado__in=['borrador', 'pendiente_admin'])
                queryset = queryset.exclude(estado__in=['borrador', 'pendiente_admin'])
            
            # 3.4 Centro genérico: Ve todo del centro (lectura)
            # else: ya está filtrado por centro
            filter_applied = True
        
        # Aplicar filtros adicionales de query params
        # ISS-019 FIX: Admin/farmacia/vista pueden filtrar por centro específico
        if user.is_superuser or rol in ['admin', 'farmacia', 'vista']:
            centro_param = self.request.query_params.get('centro')
            if centro_param:
                queryset = queryset.filter(
                    Q(centro_origen_id=centro_param) | Q(centro_destino_id=centro_param)
                )
                filter_applied = True  # ISS-006: Ya filtraron por centro

        estado = self.request.query_params.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado.lower())

        grupo = self.request.query_params.get('grupo_estado')
        if grupo and grupo in REQUISICION_GRUPOS_ESTADO:
            queryset = queryset.filter(estado__in=REQUISICION_GRUPOS_ESTADO[grupo])

        search = self.request.query_params.get('search')
        if search and search.strip():
            queryset = queryset.filter(numero__icontains=search.strip())

        # Filtros de fecha
        fecha_desde = self.request.query_params.get('fecha_desde')
        if fecha_desde:
            queryset = queryset.filter(fecha_solicitud__date__gte=fecha_desde)
        
        fecha_hasta = self.request.query_params.get('fecha_hasta')
        if fecha_hasta:
            queryset = queryset.filter(fecha_solicitud__date__lte=fecha_hasta)

        # ISS-006 FIX: Registrar consultas globales sin filtro de centro
        if not filter_applied:
            AuditLogger.log_global_query(user, queryset, filter_applied=False)

        return queryset.order_by('-fecha_solicitud')
    
    def list(self, request, *args, **kwargs):
        """
        ISS-DIRECTOR FIX: Override de list para retornar 403 explícito
        cuando un usuario de centro no tiene centro asignado.
        
        Esto evita que se devuelva lista vacía silenciosa, lo que puede
        ocultar errores de configuración o intentos de acceso indebido.
        """
        # Resetear flag
        self._missing_centro = False
        
        # Llamar get_queryset que puede setear _missing_centro
        queryset = self.filter_queryset(self.get_queryset())
        
        # Verificar si falta centro
        if getattr(self, '_missing_centro', False):
            rol = _get_rol_efectivo(request.user)
            logger.warning(
                f"ISS-DIRECTOR: Usuario {request.user.username} (rol={rol}) "
                f"intentó listar requisiciones sin centro asignado"
            )
            return Response({
                'error': 'Usuario de centro sin centro asignado',
                'detail': 'Su cuenta está configurada como usuario de centro pero no tiene un centro asignado. Contacte al administrador.',
                'rol': rol
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Continuar con el list normal
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @transaction.atomic  # HALLAZGO #10 FIX: Garantizar atomicidad requisición + detalles
    def create(self, request, *args, **kwargs):
        """
        ISS-001 FIX: Crea requisicion SIEMPRE en estado borrador.
        
        SEGURIDAD:
        - El estado enviado por el cliente es IGNORADO
        - Usuarios de centro: siempre 'borrador'
        - Farmacia/Admin: siempre 'borrador' (deben usar acción 'enviar' para cambiar)
        - Se valida contra máquina de estados antes de persistir
        """
        try:
            data = request.data.copy()
            fecha = timezone.now()
            numero = f"REQ-{fecha.strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
            while Requisicion.objects.filter(numero=numero).exists():
                numero = f"REQ-{fecha.strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

            # ISS-001 FIX: IGNORAR estado enviado por cliente - siempre borrador
            # El cliente NO puede crear requisiciones en estados avanzados
            estado_solicitado = str(data.get('estado', '')).lower()
            if estado_solicitado and estado_solicitado != 'borrador':
                logger.warning(
                    f"ISS-001: Intento de crear requisición en estado '{estado_solicitado}' "
                    f"por usuario {request.user.username}. Forzando a 'borrador'."
                )
            data['estado'] = ESTADO_INICIAL_CENTRO  # Siempre 'borrador'
            data['numero'] = numero

            solicitante = request.user if request.user.is_authenticated else None
            es_privilegiado = False
            
            # ISS-FIX-CENTRO: Corregir semántica de centros
            # centro_origen = centro del usuario que SOLICITA (de donde sale la requisición)
            # centro_destino = farmacia central (NULL) - a donde va la requisición
            # El frontend envía 'centro' que es el centro del solicitante → debe ir en centro_origen
            if 'centro' in data:
                # El centro del frontend es el centro ORIGEN (quien solicita)
                data['centro_origen'] = data.pop('centro')
            
            # ISS-FIX: Mapear 'comentario' del frontend a 'notas' para consistencia
            if 'comentario' in data and 'notas' not in data:
                data['notas'] = data.pop('comentario')
            
            if solicitante:
                data['solicitante'] = getattr(solicitante, 'id', None)
                centro_user = self._user_centro(solicitante)
                es_privilegiado = is_farmacia_or_admin(solicitante)
                if centro_user and not es_privilegiado:
                    # Validar que el centro enviado sea el del usuario
                    if data.get('centro_origen') and int(data.get('centro_origen')) != centro_user.id and not solicitante.is_superuser:
                        return Response({'error': 'No puedes crear requisiciones para otro centro'}, status=status.HTTP_403_FORBIDDEN)
                    # Asignar centro_origen = centro del usuario solicitante
                    data['centro_origen'] = centro_user.id
                    # centro_destino = NULL (farmacia central, no tiene centro)
                    data['centro_destino'] = None
                elif not centro_user and not es_privilegiado and not solicitante.is_superuser:
                    return Response({'error': 'El usuario no tiene centro asignado'}, status=status.HTTP_403_FORBIDDEN)
                elif not data.get('centro_origen') and centro_user:
                    data['centro_origen'] = centro_user.id
                    data['centro_destino'] = None

            items_data = request.data.get('items', []) or request.data.get('detalles', []) or []
            # ISS-FIX-CENTRO: Usar centro_origen para obtener info del centro solicitante
            centro_origen = Centro.objects.filter(id=data.get('centro_origen')).first() if data.get('centro_origen') else None
            if not centro_origen and solicitante and not solicitante.is_superuser and not es_privilegiado:
                return Response({'error': 'No se encontró el centro origen para la requisición'}, status=status.HTTP_400_BAD_REQUEST)
            
            # ISS-001, ISS-004, ISS-005 FIX: Validación INFORMATIVA de stock en creación
            # Las requisiciones solicitan medicamentos que serán surtidos desde farmacia central
            # En creación solo advertimos, no bloqueamos (modo='informativo')
            advertencias_stock = self._validar_stock_items(
                items_data, 
                centro=centro_origen,  # Pasamos centro_origen para referencia
                validar_farmacia_central=True,
                modo='informativo'  # ISS-005: Solo advertir en creación
            )

            # Agregar detalles a data para que el serializer los procese
            data['detalles'] = items_data
            
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            requisicion = serializer.save()

            response_data = {
                'mensaje': 'Requisicion creada exitosamente',
                'requisicion': RequisicionSerializer(requisicion).data
            }
            
            # ISS-005: Incluir advertencias de stock si las hay
            if advertencias_stock:
                response_data['advertencias_stock'] = advertencias_stock
                response_data['nota'] = (
                    'Hay productos con stock insuficiente en farmacia central. '
                    'La requisición se creó pero puede ser rechazada en autorización.'
                )

            return Response(response_data, status=status.HTTP_201_CREATED)
        except serializers.ValidationError as exc:
            logger.error(f"[RequisicionViewSet.create] ValidationError: {exc.detail}")
            return Response({'error': 'Error de validacion', 'detalles': exc.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            # ISS-FIX: Log completo del error para diagnóstico
            import traceback
            logger.error(f"[RequisicionViewSet.create] Exception: {str(exc)}")
            logger.error(f"[RequisicionViewSet.create] Traceback: {traceback.format_exc()}")
            return Response({'error': 'Error al crear requisicion', 'mensaje': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def update(self, request, *args, **kwargs):
        """Solo permite editar si sigue en borrador."""
        requisicion = self.get_object()
        if (requisicion.estado or '').lower() != 'borrador':
            return Response({'error': 'Solo se pueden editar requisiciones en estado BORRADOR', 'estado_actual': requisicion.estado}, status=status.HTTP_400_BAD_REQUEST)

        centro_user = self._user_centro(request.user)
        if not request.user.is_superuser and centro_user and requisicion.centro_id != centro_user.id:
            return Response({'error': 'No puedes editar requisiciones de otro centro'}, status=status.HTTP_403_FORBIDDEN)

        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(requisicion, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        requisicion = serializer.save()

        items_data = request.data.get('items') or request.data.get('detalles') or []
        if items_data:
            # ISS-001, ISS-004, ISS-005: Validar stock en modo informativo (solo advertir)
            advertencias_stock = self._validar_stock_items(
                items_data, 
                centro=requisicion.centro,
                validar_farmacia_central=True,
                modo='informativo'  # ISS-005: Solo advertir en edición
            )
            requisicion.detalles.all().delete()
            for item_data in items_data:
                producto_id = item_data.get('producto')
                cant = item_data.get('cantidad_solicitada')
                if not producto_id or cant in [None, '']:
                    continue
                # ISS-FIX-LOTE: Incluir el lote específico si viene en el request
                lote_id = item_data.get('lote') or item_data.get('lote_id')
                DetalleRequisicion.objects.create(
                    requisicion=requisicion,
                    producto_id=producto_id,
                    lote_id=lote_id,  # ISS-FIX-LOTE: Guardar lote específico
                    cantidad_solicitada=int(cant),
                    cantidad_autorizada=int(item_data.get('cantidad_autorizada') or 0),
                    observaciones=item_data.get('observaciones', '')
                )
            
            # ISS-005: Devolver resultado con advertencias si las hay
            response_data = {'mensaje': 'Requisicion actualizada exitosamente', 'requisicion': RequisicionSerializer(requisicion).data}
            if advertencias_stock:
                response_data['advertencias_stock'] = advertencias_stock
            return Response(response_data)

        return Response({'mensaje': 'Requisicion actualizada exitosamente', 'requisicion': RequisicionSerializer(requisicion).data})
    
    def destroy(self, request, *args, **kwargs):
        requisicion = self.get_object()
        if (requisicion.estado or '').lower() != 'borrador':
            return Response({'error': 'Solo se pueden eliminar requisiciones en estado BORRADOR', 'estado_actual': requisicion.estado}, status=status.HTTP_400_BAD_REQUEST)
        centro_user = self._user_centro(request.user)
        if not request.user.is_superuser:
            if not centro_user or requisicion.centro_id != centro_user.id:
                return Response({'error': 'No puedes eliminar requisiciones de otro centro'}, status=status.HTTP_403_FORBIDDEN)
        folio = requisicion.folio
        requisicion.delete()
        return Response({'mensaje': 'Requisicion eliminada', 'folio_eliminado': folio}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def enviar(self, request, pk=None):
        """
        ISS-002/ISS-007 FIX (audit17): Envía requisición con revalidación de stock.
        
        Antes de enviar, se revalida el stock disponible en farmacia central.
        Si hay productos sin stock suficiente, se advierte pero permite enviar
        (el bloqueo ocurre en autorización/surtido).
        """
        requisicion = self.get_object()
        if (requisicion.estado or '').lower() != 'borrador':
            return Response({'error': 'Solo se pueden enviar requisiciones en estado BORRADOR', 'estado_actual': requisicion.estado}, status=status.HTTP_400_BAD_REQUEST)
        centro_user = self._user_centro(request.user)
        es_privilegiado = is_farmacia_or_admin(request.user)
        if not request.user.is_superuser and not es_privilegiado:
            if not centro_user or requisicion.centro_id != centro_user.id:
                return Response({'error': 'No puedes enviar requisiciones de otro centro'}, status=status.HTTP_403_FORBIDDEN)
        if not requisicion.detalles.exists():
            return Response({'error': 'La requisicion debe tener al menos un producto'}, status=status.HTTP_400_BAD_REQUEST)
        
        # ISS-002/ISS-007 FIX: Revalidar stock antes de enviar (modo informativo)
        # ISS-FIX-CENTRO: usar centro_origen (el centro que solicita)
        items_para_validar = [
            {'producto': d.producto_id, 'cantidad_solicitada': d.cantidad_solicitada}
            for d in requisicion.detalles.all()
        ]
        advertencias_stock = self._validar_stock_items(
            items_para_validar,
            centro=requisicion.centro_origen,
            validar_farmacia_central=True,
            modo='informativo'
        )
        
        # ISS-DB-002: Usar 'enviada' (valor en BD Supabase)
        requisicion.estado = 'enviada'
        requisicion.save(update_fields=['estado'])
        
        response_data = {
            'mensaje': 'Requisicion enviada', 
            'requisicion': RequisicionSerializer(requisicion).data
        }
        
        # ISS-002: Incluir advertencias de stock si las hay
        if advertencias_stock:
            response_data['advertencias_stock'] = advertencias_stock
            response_data['nota'] = (
                'Algunos productos tienen stock insuficiente en farmacia central. '
                'La requisición puede ser ajustada o rechazada en autorización.'
            )
        
        return Response(response_data)

    @action(detail=True, methods=['post'])
    def autorizar(self, request, pk=None):
        """
        ISS-004 FIX (audit18): Autorizar requisición con bloqueo para prevenir race conditions.
        
        Usa transaction.atomic() y select_for_update() para evitar que múltiples
        usuarios autoricen la misma requisición simultáneamente.
        """
        from django.db import transaction
        
        requisicion = self.get_object()
        # ISS-DB-002: Usar 'enviada' (valor en BD Supabase)
        if (requisicion.estado or '').lower() != 'enviada':
            return Response({'error': 'Solo se pueden autorizar requisiciones en estado ENVIADA', 'estado_actual': requisicion.estado}, status=status.HTTP_400_BAD_REQUEST)

        centro_user = self._user_centro(request.user)
        es_privilegiado = is_farmacia_or_admin(request.user)
        if not request.user.is_superuser and not es_privilegiado:
            if not centro_user:
                return Response({'error': 'El usuario no tiene centro asignado'}, status=status.HTTP_403_FORBIDDEN)
            if requisicion.centro_id != centro_user.id:
                return Response({'error': 'No puedes autorizar requisiciones de otro centro'}, status=status.HTTP_403_FORBIDDEN)
        # ISS-DIRECTOR FIX: Usar rol efectivo en lugar de rol campo directo
        rol_efectivo = _get_rol_efectivo(request.user)
        if not request.user.is_superuser and rol_efectivo.lower() not in ['admin_sistema', 'farmacia', 'admin_farmacia', 'superusuario'] and not request.user.is_staff:
            return Response({'error': 'No tienes permiso para autorizar requisiciones', 'rol_actual': rol_efectivo}, status=status.HTTP_403_FORBIDDEN)

        items_data = request.data.get('items') or request.data.get('detalles') or []
        
        # ISS-004 FIX (audit18): Ejecutar autorización dentro de transacción atómica
        try:
            with transaction.atomic():
                # Bloquear requisición para evitar modificaciones concurrentes
                requisicion_bloqueada = Requisicion.objects.select_for_update(nowait=False).get(pk=requisicion.pk)
                
                # ISS-004: Re-verificar estado después del bloqueo (pudo cambiar)
                if (requisicion_bloqueada.estado or '').lower() != 'enviada':
                    return Response({
                        'error': 'La requisición ya no está en estado ENVIADA (modificada concurrentemente)',
                        'estado_actual': requisicion_bloqueada.estado
                    }, status=status.HTTP_409_CONFLICT)
                
                return self._autorizar_con_bloqueo(request, requisicion_bloqueada, items_data)
                
        except Exception as e:
            logger.error(f"ISS-004: Error en autorización atómica: {e}")
            return Response({
                'error': f'Error al autorizar: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _autorizar_con_bloqueo(self, request, requisicion, items_data):
        """
        ISS-004 FIX (audit18): Lógica de autorización ejecutada dentro de transacción.
        
        Este método se llama desde autorizar() dentro de un bloque transaction.atomic()
        con la requisición ya bloqueada via select_for_update().
        """
        # ISS-003: Revalidar stock disponible en FARMACIA CENTRAL antes de autorizar
        # El stock pudo haber cambiado desde que se creó/envió la requisición
        errores_stock = []
        advertencias_stock = []
        
        # ISS-004 FIX: Bloquear detalles también para evitar modificaciones
        detalles_bloqueados = DetalleRequisicion.objects.select_for_update().filter(
            requisicion=requisicion
        ).select_related('producto')
        
        # Crear mapa de detalles por ID para acceso rápido
        detalles_map = {d.id: d for d in detalles_bloqueados}
        
        for item_data in items_data:
            item_id = item_data.get('id')
            cant_autorizada = item_data.get('cantidad_autorizada')
            if item_id is None or cant_autorizada is None:
                continue
            
            # ISS-004 FIX: Usar detalle bloqueado del mapa
            item = detalles_map.get(item_id)
            if item is None:
                continue
            
            cant_autorizada = max(0, int(cant_autorizada))
            if cant_autorizada > 0:
                # ISS-001: Usar stock de FARMACIA CENTRAL (no global)
                stock_farmacia = item.producto.get_stock_farmacia_central()
                
                if stock_farmacia < cant_autorizada:
                    if stock_farmacia == 0:
                        errores_stock.append({
                            'producto': item.producto.clave,
                            'descripcion': item.producto.descripcion[:50],
                            'solicitado': cant_autorizada,
                            'disponible_farmacia': stock_farmacia,
                            'mensaje': 'Sin stock en farmacia central'
                        })
                    else:
                        advertencias_stock.append({
                            'producto': item.producto.clave,
                            'descripcion': item.producto.descripcion[:50],
                            'solicitado': cant_autorizada,
                            'disponible_farmacia': stock_farmacia,
                            'sugerido': stock_farmacia,
                            'mensaje': f'Stock insuficiente, disponible: {stock_farmacia}'
                        })
            
            item.cantidad_autorizada = cant_autorizada
            
            # MEJORA FLUJO 3: Guardar motivo_ajuste si se autoriza menos de lo solicitado
            if cant_autorizada < item.cantidad_solicitada:
                motivo_ajuste = (item_data.get('motivo_ajuste') or '').strip()
                if len(motivo_ajuste) < 10:
                    return Response({
                        'error': f'Debe indicar el motivo del ajuste (mínimo 10 caracteres) para {item.producto.clave}',
                        'producto': item.producto.clave,
                        'cantidad_solicitada': item.cantidad_solicitada,
                        'cantidad_autorizada': cant_autorizada
                    }, status=status.HTTP_400_BAD_REQUEST)
                item.motivo_ajuste = motivo_ajuste
            else:
                item.motivo_ajuste = None
            
            item.save()
        
        # ISS-003: Si hay productos sin stock, rechazar autorización o advertir
        if errores_stock:
            # Productos con 0 stock - no permitir autorización
            return Response({
                'error': 'No se puede autorizar: productos sin stock en farmacia central',
                'detalles': errores_stock,
                'advertencias': advertencias_stock
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Determinar estado final
        # Si todas las cantidades autorizadas son 0 o menores a lo solicitado -> parcial
        # IMPORTANTE: Usar consulta directa a DB para ver valores actualizados (evitar cache de QuerySet)
        from django.db.models import Sum
        totales = DetalleRequisicion.objects.filter(
            requisicion=requisicion
        ).aggregate(
            total_sol=Sum('cantidad_solicitada'),
            total_aut=Sum('cantidad_autorizada')
        )
        total_solicitado = totales['total_sol'] or 0
        total_autorizado = totales['total_aut'] or 0
        
        if total_autorizado == 0:
            return Response({
                'error': 'Debe autorizar al menos un producto',
                'total_solicitado': total_solicitado,
                'total_autorizado': total_autorizado
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # ISS-DB-002: Usar 'parcial' para autorización parcial (valor en BD Supabase)
        nuevo_estado = 'autorizada' if total_autorizado >= total_solicitado else 'parcial'
        
        requisicion.estado = nuevo_estado
        requisicion.fecha_autorizacion = timezone.now()
        if request.user and request.user.is_authenticated:
            requisicion.autorizador = request.user
        requisicion.save(update_fields=['estado', 'fecha_autorizacion', 'autorizador_id'])

        response_data = {
            'mensaje': f'Requisicion {nuevo_estado}',
            'requisicion': RequisicionSerializer(requisicion).data
        }
        
        # ISS-003: Incluir advertencias si hay stock parcial
        if advertencias_stock:
            response_data['advertencias'] = advertencias_stock
            response_data['mensaje'] += ' (con advertencias de stock)'
        
        return Response(response_data)

    @action(detail=True, methods=['post'])
    def rechazar(self, request, pk=None):
        requisicion = self.get_object()
        # ISS-DB-002: Usar 'enviada' (valor en BD Supabase)
        if (requisicion.estado or '').lower() != 'enviada':
            return Response({'error': 'Solo se pueden rechazar requisiciones en estado ENVIADA', 'estado_actual': requisicion.estado}, status=status.HTTP_400_BAD_REQUEST)
        centro_user = self._user_centro(request.user)
        es_privilegiado = is_farmacia_or_admin(request.user)
        if not request.user.is_superuser and not es_privilegiado:
            if not centro_user or requisicion.centro_id != centro_user.id:
                return Response({'error': 'No puedes rechazar requisiciones de otro centro'}, status=status.HTTP_403_FORBIDDEN)
        motivo = request.data.get('observaciones') or request.data.get('comentario') or ''
        if not motivo.strip():
            return Response({'error': 'Debe proporcionar un motivo de rechazo'}, status=status.HTTP_400_BAD_REQUEST)
        requisicion.estado = 'rechazada'
        requisicion.notas = motivo
        requisicion.save(update_fields=['estado', 'notas'])
        return Response({'mensaje': 'Requisicion rechazada', 'requisicion': RequisicionSerializer(requisicion).data})

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """
        ISS-RES-002 FIX (audit-final): Cancelar requisición con transacción atómica.
        
        Usa transaction.atomic() y select_for_update() para prevenir
        modificaciones concurrentes durante la cancelación.
        """
        from django.db import transaction
        
        try:
            with transaction.atomic():
                # ISS-RES-002: Bloquear requisición para evitar modificaciones concurrentes
                requisicion = Requisicion.objects.select_for_update(nowait=False).get(pk=pk)
                
                estado_actual = (requisicion.estado or '').lower()
                
                # Verificar estado después del bloqueo (pudo cambiar)
                if estado_actual in ['surtida', 'cancelada', 'rechazada', 'entregada']:
                    return Response({
                        'error': f'No se puede cancelar una requisición en estado {requisicion.estado}',
                        'estado_actual': requisicion.estado
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Validar permisos de centro
                centro_user = self._user_centro(request.user)
                if not request.user.is_superuser:
                    if not centro_user or requisicion.centro_id != centro_user.id:
                        return Response({
                            'error': 'No puedes cancelar requisiciones de otro centro'
                        }, status=status.HTTP_403_FORBIDDEN)
                
                # ISS-RES-002: Usar cambiar_estado para validaciones
                motivo = request.data.get('observaciones') or request.data.get('comentario') or 'Cancelada por usuario'
                
                try:
                    requisicion.cambiar_estado(
                        'cancelada',
                        usuario=request.user,
                        motivo=motivo,
                        validar=True
                    )
                    requisicion.save(update_fields=['estado', 'notas', 'updated_at'])
                except ValidationError as e:
                    return Response({
                        'error': str(e.message_dict if hasattr(e, 'message_dict') else e)
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Log de auditoría
                logger.info(
                    f"ISS-RES-002: Requisición {requisicion.numero} cancelada por "
                    f"usuario {request.user.username}. Motivo: {motivo}"
                )
                
                return Response({
                    'mensaje': 'Requisición cancelada',
                    'requisicion': RequisicionSerializer(requisicion).data
                })
                
        except Requisicion.DoesNotExist:
            return Response({
                'error': 'Requisición no encontrada'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"ISS-RES-002: Error cancelando requisición {pk}: {e}")
            return Response({
                'error': f'Error al cancelar: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='diagnostico-surtido')
    def diagnostico_surtido(self, request, pk=None):
        """
        ISS-DEBUG: Endpoint de diagnóstico para verificar si una requisición puede ser surtida.
        
        Retorna información detallada sobre:
        - Estado de la requisición
        - Detalles y sus productos
        - Stock disponible en farmacia central
        - Problemas detectados
        
        Este endpoint es de solo lectura, no modifica datos.
        """
        from django.utils import timezone
        from django.db.models import Sum
        
        hoy = timezone.now().date()
        
        try:
            requisicion = self.get_object()
        except Exception as e:
            return Response({
                'error': f'No se pudo obtener la requisición: {str(e)}'
            }, status=status.HTTP_404_NOT_FOUND)
        
        ESTADOS_SURTIBLES = {'autorizada', 'autorizada_farmacia', 'en_surtido', 'parcial'}
        estado_actual = (requisicion.estado or '').lower()
        
        diagnostico = {
            'requisicion': {
                'id': requisicion.pk,
                'numero': requisicion.numero,
                'folio': getattr(requisicion, 'folio', requisicion.numero),
                'estado': requisicion.estado,
                'centro': requisicion.centro.nombre if requisicion.centro else None,
                'centro_id': requisicion.centro_id,
                'solicitante': requisicion.solicitante.username if requisicion.solicitante else None,
                'fecha_creacion': requisicion.created_at.isoformat() if requisicion.created_at else None,
            },
            'estado_surtible': estado_actual in ESTADOS_SURTIBLES,
            'estados_validos': list(ESTADOS_SURTIBLES),
            'detalles': [],
            'errores': [],
            'advertencias': [],
            'puede_surtirse': True,
        }
        
        if estado_actual not in ESTADOS_SURTIBLES:
            diagnostico['errores'].append(
                f"Estado '{requisicion.estado}' no es surtible. Estados válidos: {ESTADOS_SURTIBLES}"
            )
            diagnostico['puede_surtirse'] = False
        
        detalles = requisicion.detalles.select_related('producto', 'lote').all()
        
        if not detalles:
            diagnostico['errores'].append("La requisición no tiene detalles")
            diagnostico['puede_surtirse'] = False
            return Response(diagnostico)
        
        for det in detalles:
            detalle_info = {
                'id': det.pk,
                'producto_id': det.producto_id,
                'producto_clave': det.producto.clave if det.producto else None,
                'producto_nombre': (det.producto.nombre[:50] + '...') if det.producto and len(det.producto.nombre) > 50 else (det.producto.nombre if det.producto else None),
                'cantidad_solicitada': det.cantidad_solicitada,
                'cantidad_autorizada': det.cantidad_autorizada,
                'cantidad_surtida': det.cantidad_surtida,
                'pendiente': 0,
                'lote_especifico': None,
                'stock_farmacia': 0,
                'lotes_disponibles': [],
                'puede_surtirse': True,
                'errores': [],
            }
            
            if not det.producto_id:
                detalle_info['errores'].append("Sin producto asignado")
                detalle_info['puede_surtirse'] = False
                diagnostico['puede_surtirse'] = False
                diagnostico['detalles'].append(detalle_info)
                continue
            
            # Calcular pendiente
            pendiente = (det.cantidad_autorizada or det.cantidad_solicitada or 0) - (det.cantidad_surtida or 0)
            detalle_info['pendiente'] = pendiente
            
            if pendiente <= 0:
                detalle_info['puede_surtirse'] = True  # Ya surtido
                diagnostico['detalles'].append(detalle_info)
                continue
            
            # Verificar cantidad autorizada
            if det.cantidad_autorizada is None or det.cantidad_autorizada == 0:
                diagnostico['advertencias'].append(
                    f"Detalle {det.pk} ({det.producto.clave}): cantidad_autorizada es NULL/0, "
                    f"se usará cantidad_solicitada={det.cantidad_solicitada}"
                )
            
            # Verificar lote específico vs FEFO
            if det.lote_id is not None:
                lote = det.lote
                detalle_info['lote_especifico'] = {
                    'id': lote.pk if lote else det.lote_id,
                    'numero': lote.numero_lote if lote else 'N/A',
                    'stock': lote.cantidad_actual if lote else 0,
                    'activo': lote.activo if lote else False,
                    'caducidad': str(lote.fecha_caducidad) if lote and lote.fecha_caducidad else None,
                    'centro': lote.centro.nombre if lote and lote.centro else 'Farmacia Central',
                }
                
                if not lote:
                    detalle_info['errores'].append(f"Lote referenciado {det.lote_id} no existe")
                    detalle_info['puede_surtirse'] = False
                elif not lote.activo:
                    detalle_info['errores'].append(f"Lote {lote.numero_lote} está inactivo")
                    detalle_info['puede_surtirse'] = False
                elif lote.cantidad_actual < pendiente:
                    detalle_info['errores'].append(
                        f"Stock insuficiente en lote {lote.numero_lote}: "
                        f"disponible={lote.cantidad_actual}, requerido={pendiente}"
                    )
                    detalle_info['puede_surtirse'] = False
                elif lote.fecha_caducidad and lote.fecha_caducidad < hoy:
                    detalle_info['errores'].append(f"Lote {lote.numero_lote} está vencido")
                    detalle_info['puede_surtirse'] = False
            else:
                # FEFO automático - buscar lotes en farmacia central
                lotes_disponibles = Lote.objects.filter(
                    centro__isnull=True,  # Farmacia central
                    producto=det.producto,
                    activo=True,
                    cantidad_actual__gt=0,
                    fecha_caducidad__gte=hoy
                ).order_by('fecha_caducidad')[:5]  # Limitar a 5 para respuesta
                
                stock_total = Lote.objects.filter(
                    centro__isnull=True,
                    producto=det.producto,
                    activo=True,
                    cantidad_actual__gt=0,
                    fecha_caducidad__gte=hoy
                ).aggregate(total=Sum('cantidad_actual'))['total'] or 0
                
                detalle_info['stock_farmacia'] = stock_total
                detalle_info['lotes_disponibles'] = [
                    {
                        'id': l.pk,
                        'numero': l.numero_lote,
                        'stock': l.cantidad_actual,
                        'caducidad': str(l.fecha_caducidad) if l.fecha_caducidad else None,
                    }
                    for l in lotes_disponibles
                ]
                
                if stock_total < pendiente:
                    detalle_info['errores'].append(
                        f"Stock insuficiente en farmacia: disponible={stock_total}, requerido={pendiente}"
                    )
                    detalle_info['puede_surtirse'] = False
            
            if not detalle_info['puede_surtirse']:
                diagnostico['puede_surtirse'] = False
            
            diagnostico['detalles'].append(detalle_info)
        
        # Resumen
        total_detalles = len(diagnostico['detalles'])
        detalles_ok = sum(1 for d in diagnostico['detalles'] if d['puede_surtirse'])
        diagnostico['resumen'] = {
            'total_detalles': total_detalles,
            'detalles_listos': detalles_ok,
            'detalles_con_problemas': total_detalles - detalles_ok,
        }
        
        return Response(diagnostico)

    @action(detail=True, methods=['post'])
    def surtir(self, request, pk=None):
        """
        ISS-011, ISS-021: Surte una requisición autorizada de forma ATÓMICA.
        
        Usa RequisicionService para garantizar:
        - Transacción atómica con rollback completo si falla cualquier paso
        - Bloqueo optimista de lotes (select_for_update)
        - Validación de permisos por centro
        
        PERMISOS:
        - Superuser: puede surtir cualquier requisición
        - Farmacia (admin_farmacia, farmacia): puede surtir cualquier requisición
        - Centro: solo puede surtir requisiciones de su propio centro
        
        LÓGICA DE STOCK:
        - Primero usa lotes de farmacia central (centro=NULL) → crea entrada en centro destino
        - Si no hay en farmacia central, usa lotes del centro solicitante (salida interna)
        
        NUEVO: Soporta foto de firma de surtido vía multipart/form-data
        """
        import traceback
        from inventario.services import (
            RequisicionService,
            StockInsuficienteError,
            EstadoInvalidoError,
            PermisoRequisicionError
        )
        
        # DEBUG: Log inicio de surtido
        logger.info(f"SURTIR: Iniciando surtido para requisición pk={pk}, usuario={request.user.username}")
        
        try:
            requisicion = self.get_object()
            logger.info(f"SURTIR: Requisición obtenida: {requisicion.folio}, estado={requisicion.estado}")
        except Exception as e:
            logger.exception(f"SURTIR: Error al obtener requisición: {e}")
            return Response({
                'error': 'No se pudo obtener la requisición',
                'detalle': str(e),
                'tipo_error': type(e).__name__
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # ISS-FIX-FECHA-VENCIDA: Verificación adicional de fecha límite antes de surtir
        # Si la fecha ya venció, marcar como vencida y retornar error
        fecha_limite = getattr(requisicion, 'fecha_recoleccion_limite', None)
        if fecha_limite and timezone.now() > fecha_limite:
            logger.warning(
                f"SURTIR: Requisición {requisicion.folio} tiene fecha límite vencida: {fecha_limite}"
            )
            # Marcar como vencida
            estado_anterior = requisicion.estado
            requisicion.estado = 'vencida'
            requisicion.fecha_vencimiento = timezone.now()
            requisicion.motivo_vencimiento = (
                f"Fecha límite de recolección vencida: {fecha_limite.strftime('%Y-%m-%d %H:%M')}"
            )
            requisicion.save(update_fields=['estado', 'fecha_vencimiento', 'motivo_vencimiento', 'updated_at'])
            
            # Registrar en historial
            self._registrar_historial(
                requisicion, estado_anterior, 'vencida',
                request.user, 'vencer_automatico', request,
                datos_adicionales={'motivo': requisicion.motivo_vencimiento}
            )
            
            return Response({
                'error': 'No se puede surtir: La fecha límite de recolección ya venció',
                'fecha_limite': fecha_limite.isoformat(),
                'estado_actual': 'vencida',
                'mensaje': 'La requisición ha sido marcada como vencida automáticamente'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # ISS-FIX-SURTIR: Auto-asignación de cantidad_autorizada movida al servicio
        # para que ocurra dentro de la transacción atómica
        
        try:
            # ISS-011, ISS-021: Usar servicio transaccional
            logger.info(f"SURTIR: Creando servicio para {requisicion.folio}")
            service = RequisicionService(requisicion, request.user)
            
            logger.info(f"SURTIR: Llamando service.surtir() para {requisicion.folio}")
            resultado = service.surtir(
                is_farmacia_or_admin_fn=is_farmacia_or_admin,
                get_user_centro_fn=get_user_centro
            )
            logger.info(f"SURTIR: Surtido exitoso para {requisicion.folio}")
            
            # Refrescar requisición para serializer
            requisicion.refresh_from_db()
            
            # ISS-004 FIX (audit21): Validar imagen completa (MIME, magic bytes, extensión)
            foto_firma = request.FILES.get('foto_firma_surtido') or request.FILES.get('foto_firma')
            if foto_firma:
                es_valido, error_msg = validar_archivo_imagen(foto_firma, max_size_mb=2)
                if es_valido:
                    requisicion.foto_firma_surtido = foto_firma
                    requisicion.fecha_firma_surtido = timezone.now()
                    requisicion.usuario_firma_surtido = request.user
                    requisicion.save(update_fields=['foto_firma_surtido', 'fecha_firma_surtido', 'usuario_firma_surtido'])
                else:
                    logger.warning(f"ISS-004: Firma rechazada en surtir {requisicion.folio}: {error_msg}")
            
            return Response({
                'mensaje': 'Requisición surtida exitosamente',
                'requisicion': RequisicionSerializer(requisicion, context={'request': request}).data,
                'detalles_surtido': resultado
            })
            
        except EstadoInvalidoError as e:
            return Response({
                'error': str(e),
                'codigo': e.code,
                'estado_actual': e.estado_actual
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except PermisoRequisicionError as e:
            return Response({
                'error': str(e),
                'codigo': e.code
            }, status=status.HTTP_403_FORBIDDEN)
            
        except StockInsuficienteError as e:
            return Response({
                'error': str(e),
                'codigo': e.code,
                'detalles': e.detalles_stock
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.exception(f"Error inesperado al surtir requisición {requisicion.folio}: {e}")
            # ISS-DEBUG: Retornar error detallado para diagnóstico
            import traceback
            error_detalle = traceback.format_exc()
            return Response({
                'error': 'Error interno al procesar el surtido. Por favor intente nuevamente.',
                'codigo': 'error_interno',
                'detalle': str(e),
                'tipo_error': type(e).__name__
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='marcar-recibida')
    def marcar_recibida(self, request, pk=None):
        """
        ISS-002 FIX: Marca una requisición surtida como recibida con CONCILIACIÓN.
        
        PERMISOS:
        - Solo usuarios del centro receptor pueden marcar como recibida
        - Solo requisiciones en estado 'surtida' o 'parcial' pueden marcarse
        
        DATOS REQUERIDOS:
        - lugar_entrega: Lugar donde se recibió
        - items_recibidos: Lista de {detalle_id, cantidad_recibida} para conciliación
        - observaciones_recepcion: Observaciones de la recepción (opcional)
        
        CONCILIACIÓN (ISS-002):
        - Valida cantidades recibidas vs surtidas
        - Registra divergencias (faltantes/daños)
        - Crea movimientos de recepción para trazabilidad
        """
        from django.utils import timezone
        from django.db import transaction
        
        requisicion = self.get_object()
        estado_actual = (requisicion.estado or '').lower()
        
        # ISS-002: También permitir 'parcial'
        if estado_actual not in ['surtida', 'parcial']:
            return Response({
                'error': 'Solo se pueden marcar como recibidas las requisiciones surtidas o parciales',
                'estado_actual': requisicion.estado
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # PERMISOS: Solo usuarios del centro receptor pueden confirmar recepción
        user = request.user
        if not user.is_superuser:
            centro_user = self._user_centro(user)
            if not centro_user or requisicion.centro_id != centro_user.id:
                return Response({
                    'error': 'Solo el centro receptor puede confirmar la recepción'
                }, status=status.HTTP_403_FORBIDDEN)
        
        # Obtener datos del request
        lugar_entrega = request.data.get('lugar_entrega', '')
        observaciones_recepcion = request.data.get('observaciones_recepcion', '')
        items_recibidos = request.data.get('items_recibidos', [])
        
        if not lugar_entrega:
            return Response({
                'error': 'El lugar de entrega es requerido'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # ISS-002 FIX: Conciliación de cantidades recibidas vs surtidas
        divergencias = []
        detalles_conciliados = []
        
        with transaction.atomic():
            for detalle in requisicion.detalles.select_related('producto'):
                cantidad_surtida = detalle.cantidad_surtida or 0
                
                # Buscar item recibido correspondiente
                item_recibido = next(
                    (i for i in items_recibidos if str(i.get('detalle_id')) == str(detalle.id)),
                    None
                )
                
                if item_recibido:
                    try:
                        cantidad_recibida = int(item_recibido.get('cantidad_recibida', cantidad_surtida))
                    except (ValueError, TypeError):
                        cantidad_recibida = cantidad_surtida
                    
                    observacion_item = item_recibido.get('observaciones', '')
                else:
                    # Si no se especifica, asumir que recibió lo surtido
                    cantidad_recibida = cantidad_surtida
                    observacion_item = ''
                
                # Detectar divergencia
                diferencia = cantidad_surtida - cantidad_recibida
                if diferencia != 0:
                    divergencias.append({
                        'producto': detalle.producto.clave,
                        'producto_nombre': (detalle.producto.nombre or '')[:50],
                        'cantidad_surtida': cantidad_surtida,
                        'cantidad_recibida': cantidad_recibida,
                        'diferencia': diferencia,
                        'tipo': 'faltante' if diferencia > 0 else 'excedente',
                        'observaciones': observacion_item
                    })
                    
                    # ISS-002: Registrar movimiento de ajuste por divergencia
                    # ISS-FIX: Usar centro_origen (quien hizo la requisición), no centro (alias de centro_destino)
                    if diferencia > 0 and requisicion.centro_origen:
                        # Faltante: registrar ajuste negativo en centro
                        lotes_centro = Lote.objects.filter(
                            producto=detalle.producto,
                            centro=requisicion.centro_origen,
                            activo=True,
                            cantidad_actual__gt=0
                        ).order_by('fecha_caducidad')
                        
                        faltante_pendiente = diferencia
                        for lote in lotes_centro:
                            if faltante_pendiente <= 0:
                                break
                            
                            ajustar = min(faltante_pendiente, lote.cantidad_actual)
                            registrar_movimiento_stock(
                                lote=lote,
                                tipo='ajuste',
                                cantidad=-ajustar,
                                usuario=user,
                                centro=requisicion.centro_origen,
                                requisicion=requisicion,
                                observaciones=f'AJUSTE_RECEPCION: Faltante en recepción REQ-{requisicion.numero}. {observacion_item}',
                                skip_centro_check=True
                            )
                            faltante_pendiente -= ajustar
                
                # Guardar cantidad recibida en detalle
                detalle.cantidad_recibida = cantidad_recibida
                detalle.save(update_fields=['cantidad_recibida'])
                
                detalles_conciliados.append({
                    'detalle_id': detalle.id,
                    'producto': detalle.producto.clave,
                    'surtida': cantidad_surtida,
                    'recibida': cantidad_recibida
                })
            
            # Actualizar la requisición
            requisicion.estado = 'entregada'
            requisicion.fecha_entrega = timezone.now()
            requisicion.lugar_entrega = lugar_entrega
            requisicion.usuario_firma_recepcion = user
            requisicion.fecha_firma_recepcion = timezone.now()
            
            # ISS-002: Registrar divergencias y responsable en notas
            notas_recepcion = f"[Recepción {timezone.now().strftime('%Y-%m-%d %H:%M')}] "
            notas_recepcion += f"Recibido por: {user.username}. "
            if observaciones_recepcion:
                notas_recepcion += f"Obs: {observaciones_recepcion}. "
            if divergencias:
                notas_recepcion += f"DIVERGENCIAS: {len(divergencias)} productos con diferencias. "
            
            notas_actual = requisicion.notas or ''
            requisicion.notas = f"{notas_actual}\n{notas_recepcion}".strip()
            
            # Validar foto de firma si se incluye
            foto_firma = request.FILES.get('foto_firma_recepcion') or request.FILES.get('foto_firma')
            if foto_firma:
                # ISS-006: Validar imagen antes de guardar
                es_valido, error_msg = validar_archivo_imagen(foto_firma, max_size_mb=2)
                if not es_valido:
                    return Response({
                        'error': f'Error en foto de firma: {error_msg}'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                requisicion.foto_firma_recepcion = foto_firma
            
            update_fields = [
                'estado', 'fecha_entrega', 'lugar_entrega', 'notas',
                'usuario_firma_recepcion_id', 'fecha_firma_recepcion'
            ]
            if foto_firma:
                update_fields.append('foto_firma_recepcion')
            
            requisicion.save(update_fields=update_fields)
        
        response_data = {
            'mensaje': 'Requisición marcada como recibida',
            'requisicion': RequisicionSerializer(requisicion, context={'request': request}).data,
            'conciliacion': {
                'detalles': detalles_conciliados,
                'total_items': len(detalles_conciliados)
            }
        }
        
        # ISS-002: Incluir divergencias si las hay
        if divergencias:
            response_data['divergencias'] = divergencias
            response_data['mensaje'] += f' (con {len(divergencias)} divergencias registradas)'
        
        return Response(response_data)

    @action(detail=True, methods=['post'], url_path='subir-firma-surtido')
    def subir_firma_surtido(self, request, pk=None):
        """
        ISS-006 FIX: Sube la foto de firma de surtido con validación de imagen.
        
        ISS-DB-002: 'recibida' -> 'entregada' para alinearse con BD Supabase.
        Solo disponible para requisiciones en estado 'surtida' o 'entregada'.
        Solo usuarios de farmacia/admin pueden subir esta firma.
        
        Validaciones de seguridad (ISS-006):
        - Extensión permitida (.jpg, .jpeg, .png, .gif, .webp)
        - MIME type correcto
        - Magic bytes válidos (contenido real = imagen)
        - Tamaño máximo 2MB
        """
        from django.utils import timezone
        
        requisicion = self.get_object()
        estado_actual = (requisicion.estado or '').lower()
        
        # ISS-DB-002: 'recibida' -> 'entregada'
        if estado_actual not in ['surtida', 'entregada']:
            return Response({
                'error': 'Solo se puede subir firma de surtido para requisiciones surtidas o entregadas',
                'estado_actual': requisicion.estado
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # PERMISOS: Solo farmacia/admin puede subir firma de surtido
        user = request.user
        if not user.is_superuser and not is_farmacia_or_admin(user):
            return Response({
                'error': 'Solo farmacia o administradores pueden subir la firma de surtido'
            }, status=status.HTTP_403_FORBIDDEN)
        
        foto_firma = request.FILES.get('foto_firma_surtido') or request.FILES.get('foto_firma')
        if not foto_firma:
            return Response({
                'error': 'No se proporcionó la foto de firma'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # ISS-006 FIX: Validar imagen con magic bytes, MIME y extensión
        es_valido, error_msg = validar_archivo_imagen(foto_firma, max_size_mb=2)
        if not es_valido:
            return Response({
                'error': f'Error en foto de firma: {error_msg}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        requisicion.foto_firma_surtido = foto_firma
        requisicion.fecha_firma_surtido = timezone.now()
        requisicion.usuario_firma_surtido = user
        requisicion.save(update_fields=['foto_firma_surtido', 'fecha_firma_surtido', 'usuario_firma_surtido'])
        
        return Response({
            'mensaje': 'Firma de surtido subida correctamente',
            'requisicion': RequisicionSerializer(requisicion, context={'request': request}).data
        })

    @action(detail=True, methods=['post'], url_path='subir-firma-recepcion')
    def subir_firma_recepcion(self, request, pk=None):
        """
        ISS-006 FIX: Sube la foto de firma de recepción con validación de imagen.
        
        ISS-DB-002: 'recibida' -> 'entregada' para alinearse con BD Supabase.
        Solo disponible para requisiciones en estado 'entregada'.
        Solo usuarios del centro receptor pueden subir esta firma.
        
        Validaciones de seguridad (ISS-006):
        - Extensión permitida (.jpg, .jpeg, .png, .gif, .webp)
        - MIME type correcto
        - Magic bytes válidos (contenido real = imagen)
        - Tamaño máximo 2MB
        """
        from django.utils import timezone
        
        requisicion = self.get_object()
        estado_actual = (requisicion.estado or '').lower()
        
        # ISS-DB-002: 'recibida' -> 'entregada'
        if estado_actual != 'entregada':
            return Response({
                'error': 'Solo se puede subir firma de recepción para requisiciones entregadas',
                'estado_actual': requisicion.estado
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # PERMISOS: Solo usuarios del centro receptor pueden subir firma de recepción
        user = request.user
        if not user.is_superuser:
            centro_user = self._user_centro(user)
            if not centro_user or requisicion.centro_id != centro_user.id:
                return Response({
                    'error': 'Solo el centro receptor puede subir la firma de recepción'
                }, status=status.HTTP_403_FORBIDDEN)
        
        foto_firma = request.FILES.get('foto_firma_recepcion') or request.FILES.get('foto_firma')
        if not foto_firma:
            return Response({
                'error': 'No se proporcionó la foto de firma'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # ISS-006 FIX: Validar imagen con magic bytes, MIME y extensión
        es_valido, error_msg = validar_archivo_imagen(foto_firma, max_size_mb=2)
        if not es_valido:
            return Response({
                'error': f'Error en foto de firma: {error_msg}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        requisicion.foto_firma_recepcion = foto_firma
        requisicion.fecha_firma_recepcion = timezone.now()
        requisicion.usuario_firma_recepcion = user
        requisicion.save(update_fields=['foto_firma_recepcion', 'fecha_firma_recepcion', 'usuario_firma_recepcion'])
        
        return Response({
            'mensaje': 'Firma de recepción subida correctamente',
            'requisicion': RequisicionSerializer(requisicion, context={'request': request}).data
        })
        
        return Response({
            'mensaje': 'Firma de recepción subida correctamente',
            'requisicion': RequisicionSerializer(requisicion, context={'request': request}).data
        })

    @action(detail=True, methods=['get'], url_path='hoja-recoleccion')
    def hoja_recoleccion(self, request, pk=None):
        """
        Genera y descarga el PDF de la hoja de recolección para una requisición.
        ISS-DB-002: Estados alineados con BD Supabase.
        Solo disponible para requisiciones autorizadas, en_surtido, parcial o surtidas.
        """
        from core.utils.pdf_generator import generar_hoja_recoleccion
        
        requisicion = self.get_object()
        estado = (requisicion.estado or '').lower()
        
        # ISS-DB-002: Validar estados de BD Supabase
        if estado not in ['autorizada', 'en_surtido', 'parcial', 'surtida']:
            return Response({
                'error': 'Solo se pueden generar hojas para requisiciones autorizadas, en surtido, parciales o surtidas',
                'estado_actual': requisicion.estado
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Generar el PDF
            pdf_buffer = generar_hoja_recoleccion(requisicion)
            
            # Crear respuesta HTTP con el PDF
            response = HttpResponse(
                pdf_buffer.getvalue(),
                content_type='application/pdf'
            )
            folio_safe = (requisicion.folio or f'REQ-{requisicion.id}').replace('/', '-')
            response['Content-Disposition'] = f'attachment; filename="Hoja_Recoleccion_{folio_safe}.pdf"'
            
            return response
            
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            return Response({
                'error': 'Error al generar la hoja de recolección',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='hoja-consulta')
    def hoja_consulta(self, request, pk=None):
        """
        Genera y descarga el PDF de hoja de consulta simplificada para centros.
        Esta versión tiene un sello "SURTIDA" y NO muestra firmas completas.
        Solo disponible para requisiciones surtidas o entregadas.
        Para uso exclusivo de roles de centro (médico, usuario_centro, etc.)
        """
        from core.utils.pdf_generator import generar_hoja_consulta
        
        requisicion = self.get_object()
        estado = (requisicion.estado or '').lower()
        
        # Solo para estados surtida o entregada
        if estado not in ['surtida', 'entregada']:
            return Response({
                'error': 'La hoja de consulta solo está disponible para requisiciones surtidas o entregadas',
                'estado_actual': requisicion.estado
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Generar el PDF de consulta con sello SURTIDA
            pdf_buffer = generar_hoja_consulta(requisicion)
            
            # Crear respuesta HTTP con el PDF
            response = HttpResponse(
                pdf_buffer.getvalue(),
                content_type='application/pdf'
            )
            folio_safe = (requisicion.folio or f'REQ-{requisicion.id}').replace('/', '-')
            response['Content-Disposition'] = f'attachment; filename="Consulta_Requisicion_{folio_safe}.pdf"'
            
            return response
            
        except Exception as e:
            import traceback
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error generando hoja consulta req {pk}: {str(e)}")
            logger.error(traceback.format_exc())
            return Response({
                'error': 'Error al generar la hoja de consulta',
                'mensaje': str(e),
                'detalle': traceback.format_exc()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='pdf-rechazo')
    def pdf_rechazo(self, request, pk=None):
        """
        Genera y descarga el PDF de rechazo para una requisicin rechazada.
        """
        from core.utils.pdf_generator import generar_pdf_rechazo
        
        requisicion = self.get_object()
        estado = (requisicion.estado or '').lower()
        
        if estado != 'rechazada':
            return Response({
                'error': 'Solo se pueden generar PDFs de rechazo para requisiciones rechazadas',
                'estado_actual': requisicion.estado
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            pdf_buffer = generar_pdf_rechazo(requisicion)
            
            response = HttpResponse(
                pdf_buffer.getvalue(),
                content_type='application/pdf'
            )
            folio_safe = (requisicion.folio or f'REQ-{requisicion.id}').replace('/', '-')
            response['Content-Disposition'] = f'attachment; filename="Requisicion_Rechazada_{folio_safe}.pdf"'
            
            return response
            
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            return Response({
                'error': 'Error al generar el PDF de rechazo',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ==========================================================================
    # FLUJO V2: ENDPOINTS DE TRANSICIÓN DE ESTADOS JERÁRQUICOS
    # ==========================================================================
    
    def _get_client_ip(self, request):
        """Obtiene la IP del cliente para auditoría."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')
    
    def _registrar_historial(self, requisicion, estado_anterior, estado_nuevo, 
                              usuario, accion, request, motivo=None, datos_adicionales=None):
        """
        Registra un cambio de estado en el historial inmutable.
        """
        from core.models import RequisicionHistorialEstados
        
        try:
            RequisicionHistorialEstados.objects.create(
                requisicion=requisicion,
                estado_anterior=estado_anterior,
                estado_nuevo=estado_nuevo,
                usuario=usuario,
                accion=accion,
                motivo=motivo,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500] if request else None,
                datos_adicionales=datos_adicionales
            )
        except Exception as e:
            logger.warning(f"No se pudo registrar historial: {e}")
    
    def _validar_transicion(self, estado_actual, estado_nuevo):
        """Valida que la transición de estado sea permitida."""
        transiciones_validas = TRANSICIONES_REQUISICION.get(estado_actual, [])
        return estado_nuevo in transiciones_validas
    
    def _validar_permiso_flujo(self, user, accion):
        """
        Valida que el usuario tenga permiso para ejecutar una acción del flujo.
        
        ISS-DIRECTOR FIX: Usa _get_rol_efectivo para consistencia con frontend.
        Antes usaba user.rol directamente, lo que fallaba si el campo estaba vacío.
        
        Args:
            user: Usuario que intenta ejecutar la acción
            accion: Clave del permiso (ej: 'puede_autorizar_admin')
            
        Returns:
            bool: True si tiene permiso
        """
        if user.is_superuser:
            return True
        
        # ISS-DIRECTOR FIX: Usar rol efectivo en lugar de user.rol directo
        # Esto garantiza que si el campo rol está vacío, se infiera correctamente
        rol = _get_rol_efectivo(user)
        permisos_rol = PERMISOS_FLUJO_REQUISICION.get(rol, {})
        
        tiene_permiso = permisos_rol.get(accion, False)
        
        # Log para debugging si falla
        if not tiene_permiso:
            logger.debug(
                f"_validar_permiso_flujo: Usuario {user.username} (rol={rol}, "
                f"rol_campo={getattr(user, 'rol', 'vacío')}) no tiene permiso '{accion}'"
            )
        
        return tiene_permiso

    @action(detail=True, methods=['post'], url_path='enviar-admin')
    @transaction.atomic
    def enviar_admin(self, request, pk=None):
        """
        FLUJO V2: Médico envía requisición al Administrador del Centro.
        
        Transición: borrador → pendiente_admin
        Permiso requerido: puede_enviar_admin (rol: medico)
        """
        try:
            requisicion = self.get_object()
            estado_actual = (requisicion.estado or '').lower()
            
            # Validar estado
            if estado_actual != 'borrador':
                return Response({
                    'error': 'Solo se pueden enviar a administrador las requisiciones en BORRADOR',
                    'estado_actual': requisicion.estado
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validar transición
            if not self._validar_transicion(estado_actual, 'pendiente_admin'):
                return Response({
                    'error': 'Transición de estado no permitida',
                    'estado_actual': estado_actual,
                    'estado_destino': 'pendiente_admin'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validar permiso
            if not self._validar_permiso_flujo(request.user, 'puede_enviar_admin'):
                # ISS-DIRECTOR FIX: Mostrar rol efectivo en mensaje de error
                rol_efectivo = _get_rol_efectivo(request.user)
                return Response({
                    'error': 'No tiene permiso para enviar requisiciones al administrador',
                    'rol_actual': rol_efectivo,
                    'detalle': f'El rol "{rol_efectivo}" no tiene el permiso puede_enviar_admin'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Validar que tenga detalles
            if not requisicion.detalles.exists():
                return Response({
                    'error': 'La requisición debe tener al menos un producto'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validar centro - ISS-FIX-CENTRO: usar centro_origen (el centro que solicita)
            # FALLBACK: si centro_origen es NULL (datos viejos), usar centro_destino
            centro_user = self._user_centro(request.user)
            requisicion_centro_id = requisicion.centro_origen_id or requisicion.centro_destino_id
            if not request.user.is_superuser and centro_user:
                if requisicion_centro_id != centro_user.id:
                    return Response({
                        'error': 'No puede enviar requisiciones de otro centro'
                    }, status=status.HTTP_403_FORBIDDEN)
            
            # Ejecutar transición
            estado_anterior = requisicion.estado
            requisicion.estado = 'pendiente_admin'
            requisicion.fecha_envio_admin = timezone.now()
            requisicion.save(update_fields=['estado', 'fecha_envio_admin', 'updated_at'])
            
            # Registrar en historial (no crítico, no debe fallar la transición)
            try:
                self._registrar_historial(
                    requisicion, estado_anterior, 'pendiente_admin',
                    request.user, 'enviar_a_administrador', request,
                    datos_adicionales={'centro_id': centro_user.id if centro_user else None}
                )
            except Exception as hist_err:
                logger.warning(f"Error registrando historial (no crítico): {hist_err}")
            
            return Response({
                'mensaje': 'Requisición enviada al administrador',
                'requisicion': RequisicionSerializer(requisicion, context={'request': request}).data
            })
        except Exception as e:
            import traceback
            logger.error(f"[enviar_admin] Error: {str(e)}")
            logger.error(f"[enviar_admin] Traceback: {traceback.format_exc()}")
            return Response({
                'error': 'Error al enviar requisición',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='autorizar-admin')
    @transaction.atomic
    def autorizar_admin(self, request, pk=None):
        """
        FLUJO V2: Administrador del Centro autoriza la requisición.
        
        Transición: pendiente_admin → pendiente_director
        Permiso requerido: puede_autorizar_admin (rol: administrador_centro)
        """
        requisicion = self.get_object()
        estado_actual = (requisicion.estado or '').lower()
        
        if estado_actual != 'pendiente_admin':
            return Response({
                'error': 'Solo se pueden autorizar requisiciones en PENDIENTE_ADMIN',
                'estado_actual': requisicion.estado
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not self._validar_transicion(estado_actual, 'pendiente_director'):
            return Response({
                'error': 'Transición de estado no permitida'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not self._validar_permiso_flujo(request.user, 'puede_autorizar_admin'):
            # ISS-DIRECTOR FIX: Mostrar rol efectivo en mensaje de error
            rol_efectivo = _get_rol_efectivo(request.user)
            return Response({
                'error': 'No tiene permiso para autorizar como administrador del centro',
                'rol_actual': rol_efectivo,
                'detalle': f'El rol "{rol_efectivo}" no tiene el permiso puede_autorizar_admin'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Validar centro - ISS-FIX-CENTRO: usar centro_origen (el centro que solicita)
        # FALLBACK: si centro_origen es NULL (datos viejos), usar centro_destino
        centro_user = self._user_centro(request.user)
        requisicion_centro_id = requisicion.centro_origen_id or requisicion.centro_destino_id
        if not request.user.is_superuser and centro_user:
            if requisicion_centro_id != centro_user.id:
                return Response({
                    'error': 'No puede autorizar requisiciones de otro centro'
                }, status=status.HTTP_403_FORBIDDEN)
        
        observaciones = request.data.get('observaciones', '')
        
        estado_anterior = requisicion.estado
        requisicion.estado = 'pendiente_director'
        requisicion.fecha_autorizacion_admin = timezone.now()
        requisicion.administrador_centro = request.user
        if observaciones:
            requisicion.notas = f"{requisicion.notas or ''}\n[Admin] {observaciones}".strip()
        requisicion.save(update_fields=['estado', 'fecha_autorizacion_admin', 'administrador_centro', 'notas'])
        
        self._registrar_historial(
            requisicion, estado_anterior, 'pendiente_director',
            request.user, 'autorizar_administrador', request,
            datos_adicionales={'observaciones': observaciones}
        )
        
        return Response({
            'mensaje': 'Requisición autorizada por administrador, pendiente de director',
            'requisicion': RequisicionSerializer(requisicion, context={'request': request}).data
        })

    @action(detail=True, methods=['post'], url_path='autorizar-director')
    @transaction.atomic
    def autorizar_director(self, request, pk=None):
        """
        FLUJO V2: Director del Centro autoriza la requisición.
        
        Transición: pendiente_director → enviada (a farmacia central)
        Permiso requerido: puede_autorizar_director (rol: director_centro)
        """
        requisicion = self.get_object()
        estado_actual = (requisicion.estado or '').lower()
        
        if estado_actual != 'pendiente_director':
            return Response({
                'error': 'Solo se pueden autorizar requisiciones en PENDIENTE_DIRECTOR',
                'estado_actual': requisicion.estado
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not self._validar_transicion(estado_actual, 'enviada'):
            return Response({
                'error': 'Transición de estado no permitida'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not self._validar_permiso_flujo(request.user, 'puede_autorizar_director'):
            # ISS-DIRECTOR FIX: Mostrar rol efectivo en mensaje de error
            rol_efectivo = _get_rol_efectivo(request.user)
            return Response({
                'error': 'No tiene permiso para autorizar como director del centro',
                'rol_actual': rol_efectivo,
                'rol_campo': getattr(request.user, 'rol', '') or '(vacío)',
                'detalle': f'El rol "{rol_efectivo}" no tiene el permiso puede_autorizar_director'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # ISS-FIX-CENTRO: usar centro_origen (el centro que solicita)
        # FALLBACK: si centro_origen es NULL (datos viejos), usar centro_destino
        centro_user = self._user_centro(request.user)
        requisicion_centro_id = requisicion.centro_origen_id or requisicion.centro_destino_id
        if not request.user.is_superuser and centro_user:
            if requisicion_centro_id != centro_user.id:
                return Response({
                    'error': 'No puede autorizar requisiciones de otro centro'
                }, status=status.HTTP_403_FORBIDDEN)
        
        observaciones = request.data.get('observaciones', '')
        
        estado_anterior = requisicion.estado
        requisicion.estado = 'enviada'
        requisicion.fecha_autorizacion_director = timezone.now()
        requisicion.fecha_envio_farmacia = timezone.now()
        requisicion.director_centro = request.user
        if observaciones:
            requisicion.notas = f"{requisicion.notas or ''}\n[Director] {observaciones}".strip()
        requisicion.save(update_fields=[
            'estado', 'fecha_autorizacion_director', 'fecha_envio_farmacia', 
            'director_centro', 'notas'
        ])
        
        self._registrar_historial(
            requisicion, estado_anterior, 'enviada',
            request.user, 'autorizar_director', request,
            datos_adicionales={'observaciones': observaciones}
        )
        
        return Response({
            'mensaje': 'Requisición autorizada por director, enviada a farmacia central',
            'requisicion': RequisicionSerializer(requisicion, context={'request': request}).data
        })

    @action(detail=True, methods=['post'], url_path='recibir-farmacia')
    @transaction.atomic
    def recibir_farmacia(self, request, pk=None):
        """
        FLUJO V2: Farmacia Central recibe la requisición para revisión.
        
        Transición: enviada → en_revision
        Permiso requerido: puede_recibir_farmacia (rol: farmacia)
        """
        requisicion = self.get_object()
        estado_actual = (requisicion.estado or '').lower()
        
        if estado_actual != 'enviada':
            return Response({
                'error': 'Solo se pueden recibir requisiciones en estado ENVIADA',
                'estado_actual': requisicion.estado
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not self._validar_transicion(estado_actual, 'en_revision'):
            return Response({
                'error': 'Transición de estado no permitida'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not self._validar_permiso_flujo(request.user, 'puede_recibir_farmacia'):
            if not is_farmacia_or_admin(request.user):
                # ISS-DIRECTOR FIX: Mostrar rol efectivo en mensaje de error
                rol_efectivo = _get_rol_efectivo(request.user)
                return Response({
                    'error': 'Solo personal de farmacia puede recibir requisiciones',
                    'rol_actual': rol_efectivo,
                    'detalle': f'El rol "{rol_efectivo}" no tiene el permiso puede_recibir_farmacia'
                }, status=status.HTTP_403_FORBIDDEN)
        
        observaciones = request.data.get('observaciones', '')
        
        estado_anterior = requisicion.estado
        requisicion.estado = 'en_revision'
        requisicion.fecha_recepcion_farmacia = timezone.now()
        requisicion.receptor_farmacia = request.user
        if observaciones:
            requisicion.observaciones_farmacia = observaciones
        requisicion.save(update_fields=[
            'estado', 'fecha_recepcion_farmacia', 'receptor_farmacia', 'observaciones_farmacia'
        ])
        
        self._registrar_historial(
            requisicion, estado_anterior, 'en_revision',
            request.user, 'recibir_farmacia', request,
            datos_adicionales={'observaciones': observaciones}
        )
        
        return Response({
            'mensaje': 'Requisición recibida en farmacia, en revisión',
            'requisicion': RequisicionSerializer(requisicion, context={'request': request}).data
        })

    @action(detail=True, methods=['post'], url_path='autorizar-farmacia')
    @transaction.atomic
    def autorizar_farmacia(self, request, pk=None):
        """
        FLUJO V2: Farmacia Central autoriza la requisición y asigna fecha límite de recolección.
        
        Transición: en_revision → autorizada (o enviada → autorizada)
        Permiso requerido: puede_autorizar_farmacia (rol: farmacia)
        
        IMPORTANTE: Debe incluir 'fecha_recoleccion_limite' en el request.
        """
        requisicion = self.get_object()
        estado_actual = (requisicion.estado or '').lower()
        
        if estado_actual not in ['en_revision', 'enviada']:
            return Response({
                'error': 'Solo se pueden autorizar requisiciones en EN_REVISION o ENVIADA',
                'estado_actual': requisicion.estado
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not self._validar_transicion(estado_actual, 'autorizada'):
            return Response({
                'error': 'Transición de estado no permitida'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not self._validar_permiso_flujo(request.user, 'puede_autorizar_farmacia'):
            if not is_farmacia_or_admin(request.user):
                # ISS-DIRECTOR FIX: Mostrar rol efectivo en mensaje de error
                rol_efectivo = _get_rol_efectivo(request.user)
                return Response({
                    'error': 'Solo personal de farmacia puede autorizar requisiciones',
                    'rol_actual': rol_efectivo,
                    'detalle': f'El rol "{rol_efectivo}" no tiene el permiso puede_autorizar_farmacia'
                }, status=status.HTTP_403_FORBIDDEN)
        
        # CRÍTICO: Validar fecha límite de recolección
        fecha_recoleccion_str = request.data.get('fecha_recoleccion_limite')
        if not fecha_recoleccion_str:
            return Response({
                'error': 'Debe especificar la fecha límite de recolección',
                'campo_requerido': 'fecha_recoleccion_limite'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from django.utils.dateparse import parse_datetime, parse_date
            fecha_recoleccion = parse_datetime(fecha_recoleccion_str)
            if not fecha_recoleccion:
                fecha_date = parse_date(fecha_recoleccion_str)
                if fecha_date:
                    # Si solo es fecha, agregar hora 17:00
                    from datetime import time
                    fecha_recoleccion = timezone.make_aware(
                        datetime.combine(fecha_date, time(17, 0, 0))
                    )
            # ISS-FIX: Asegurar que la fecha siempre sea timezone-aware
            elif timezone.is_naive(fecha_recoleccion):
                fecha_recoleccion = timezone.make_aware(fecha_recoleccion)
        except Exception:
            return Response({
                'error': 'Formato de fecha inválido. Use YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not fecha_recoleccion:
            return Response({
                'error': 'No se pudo parsear la fecha límite de recolección'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar que la fecha sea futura
        if fecha_recoleccion <= timezone.now():
            return Response({
                'error': 'La fecha límite de recolección debe ser futura'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        observaciones = request.data.get('observaciones', '')
        
        # Procesar ajustes de cantidades si se envían
        items_data = request.data.get('items') or request.data.get('detalles') or []
        items_procesados = set()
        
        for item_data in items_data:
            item_id = item_data.get('id')
            cant_autorizada = item_data.get('cantidad_autorizada')
            if item_id is None or cant_autorizada is None:
                continue
            try:
                item = requisicion.detalles.get(id=item_id)
                item.cantidad_autorizada = max(0, int(cant_autorizada))
                motivo_ajuste = item_data.get('motivo_ajuste', '')
                if item.cantidad_autorizada < item.cantidad_solicitada and not motivo_ajuste:
                    return Response({
                        'error': f'Debe indicar motivo de ajuste para {item.producto.clave}',
                        'producto': item.producto.clave
                    }, status=status.HTTP_400_BAD_REQUEST)
                item.motivo_ajuste = motivo_ajuste
                item.save()
                items_procesados.add(item_id)
            except DetalleRequisicion.DoesNotExist:
                continue
        
        # ISS-SURTIR-FIX: Si NO se enviaron items explícitos, autorizar TODOS los detalles
        # con cantidad_autorizada = cantidad_solicitada (aprobación total)
        if not items_procesados:
            logger.info(f"autorizar_farmacia: No se enviaron items, autorizando todos los detalles con cantidad solicitada")
            for detalle in requisicion.detalles.all():
                if detalle.cantidad_autorizada is None or detalle.cantidad_autorizada == 0:
                    detalle.cantidad_autorizada = detalle.cantidad_solicitada
                    detalle.save()
                    logger.info(f"  - Detalle {detalle.id}: autorizado {detalle.cantidad_autorizada} unidades de {detalle.producto.clave}")
        
        estado_anterior = requisicion.estado
        requisicion.estado = 'autorizada'
        
        # ISS-FIX: Asignar campos directamente sin try/except individual
        # Los campos existen en el modelo y en la BD según el schema
        requisicion.fecha_autorizacion_farmacia = timezone.now()
        requisicion.fecha_autorizacion = timezone.now()  # Campo legacy
        requisicion.fecha_recoleccion_limite = fecha_recoleccion
        requisicion.autorizador_farmacia = request.user
        requisicion.autorizador = request.user  # Campo legacy
        
        if observaciones:
            requisicion.observaciones_farmacia = f"{requisicion.observaciones_farmacia or ''}\n{observaciones}".strip()
        
        # ISS-FIX: Guardar SIN update_fields para evitar problemas con managed=False
        # Django manejará qué campos actualizar basándose en los cambios detectados
        try:
            requisicion.save()
            logger.info(f"Requisición {requisicion.folio} guardada exitosamente con fecha_recoleccion_limite={fecha_recoleccion}")
        except Exception as save_error:
            logger.error(f"Error al guardar requisición autorizada: {save_error}")
            # Si falla, intentar guardar con update() directo incluyendo TODOS los campos importantes
            try:
                Requisicion.objects.filter(pk=requisicion.pk).update(
                    estado='autorizada',
                    fecha_autorizacion=timezone.now(),
                    fecha_autorizacion_farmacia=timezone.now(),
                    fecha_recoleccion_limite=fecha_recoleccion,
                    autorizador_farmacia=request.user,
                    autorizador=request.user
                )
                requisicion.refresh_from_db()
                logger.info(f"Guardado exitoso via update() directo con fecha_recoleccion_limite={fecha_recoleccion}")
            except Exception as fallback_error:
                logger.error(f"Error en fallback update: {fallback_error}")
                raise
        
        self._registrar_historial(
            requisicion, estado_anterior, 'autorizada',
            request.user, 'autorizar_farmacia', request,
            datos_adicionales={
                'fecha_recoleccion_limite': fecha_recoleccion.isoformat(),
                'observaciones': observaciones
            }
        )
        
        return Response({
            'mensaje': f'Requisición autorizada. Fecha límite de recolección: {fecha_recoleccion.strftime("%Y-%m-%d %H:%M")}',
            'requisicion': RequisicionSerializer(requisicion, context={'request': request}).data,
            'fecha_recoleccion_limite': fecha_recoleccion.isoformat()
        })

    @action(detail=True, methods=['post'], url_path='devolver')
    @transaction.atomic
    def devolver(self, request, pk=None):
        """
        FLUJO V2: Devuelve una requisición al centro para correcciones.
        
        Transiciones permitidas:
        - pendiente_admin → devuelta (por administrador)
        - pendiente_director → devuelta (por director)
        - en_revision → devuelta (por farmacia)
        
        Requiere motivo obligatorio.
        """
        requisicion = self.get_object()
        estado_actual = (requisicion.estado or '').lower()
        
        estados_devolvibles = ['pendiente_admin', 'pendiente_director', 'en_revision']
        if estado_actual not in estados_devolvibles:
            return Response({
                'error': f'Solo se pueden devolver requisiciones en: {", ".join(estados_devolvibles)}',
                'estado_actual': requisicion.estado
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not self._validar_transicion(estado_actual, 'devuelta'):
            return Response({
                'error': 'Transición de estado no permitida'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        motivo = request.data.get('motivo') or request.data.get('observaciones', '')
        if not motivo or len(motivo.strip()) < 10:
            return Response({
                'error': 'Debe proporcionar un motivo de devolución (mínimo 10 caracteres)'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar permisos según estado
        tiene_permiso = False
        if estado_actual == 'pendiente_admin':
            tiene_permiso = self._validar_permiso_flujo(request.user, 'puede_autorizar_admin')
        elif estado_actual == 'pendiente_director':
            tiene_permiso = self._validar_permiso_flujo(request.user, 'puede_autorizar_director')
        elif estado_actual == 'en_revision':
            tiene_permiso = is_farmacia_or_admin(request.user)
        
        if not request.user.is_superuser and not tiene_permiso:
            return Response({
                'error': 'No tiene permiso para devolver esta requisición',
                'estado_actual': estado_actual
            }, status=status.HTTP_403_FORBIDDEN)
        
        estado_anterior = requisicion.estado
        requisicion.estado = 'devuelta'
        requisicion.motivo_devolucion = motivo.strip()
        requisicion.save(update_fields=['estado', 'motivo_devolucion'])
        
        self._registrar_historial(
            requisicion, estado_anterior, 'devuelta',
            request.user, 'devolver_centro', request,
            motivo=motivo.strip()
        )
        
        return Response({
            'mensaje': 'Requisición devuelta al centro para correcciones',
            'requisicion': RequisicionSerializer(requisicion, context={'request': request}).data,
            'motivo_devolucion': motivo.strip()
        })

    @action(detail=True, methods=['post'], url_path='reenviar')
    @transaction.atomic
    def reenviar(self, request, pk=None):
        """
        FLUJO V2: Reenvía una requisición devuelta al proceso de autorización.
        
        Transición: devuelta → pendiente_admin
        Permiso: médico del centro (creador original)
        """
        requisicion = self.get_object()
        estado_actual = (requisicion.estado or '').lower()
        
        if estado_actual != 'devuelta':
            return Response({
                'error': 'Solo se pueden reenviar requisiciones en estado DEVUELTA',
                'estado_actual': requisicion.estado
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not self._validar_transicion(estado_actual, 'pendiente_admin'):
            return Response({
                'error': 'Transición de estado no permitida'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar que sea el solicitante original o admin
        # ISS-FIX-CENTRO: usar centro_origen (el centro que solicita)
        # FALLBACK: si centro_origen es NULL (datos viejos), usar centro_destino
        if not request.user.is_superuser:
            if requisicion.solicitante_id != request.user.id:
                centro_user = self._user_centro(request.user)
                requisicion_centro_id = requisicion.centro_origen_id or requisicion.centro_destino_id
                if not centro_user or requisicion_centro_id != centro_user.id:
                    return Response({
                        'error': 'Solo el solicitante original puede reenviar la requisición'
                    }, status=status.HTTP_403_FORBIDDEN)
        
        observaciones = request.data.get('observaciones', '')
        
        estado_anterior = requisicion.estado
        requisicion.estado = 'pendiente_admin'
        requisicion.fecha_envio_admin = timezone.now()
        requisicion.motivo_devolucion = None  # Limpiar motivo anterior
        if observaciones:
            requisicion.notas = f"{requisicion.notas or ''}\n[Reenvío] {observaciones}".strip()
        requisicion.save(update_fields=['estado', 'fecha_envio_admin', 'motivo_devolucion', 'notas'])
        
        self._registrar_historial(
            requisicion, estado_anterior, 'pendiente_admin',
            request.user, 'enviar_a_administrador', request,
            datos_adicionales={'es_reenvio': True, 'observaciones': observaciones}
        )
        
        return Response({
            'mensaje': 'Requisición reenviada para autorización',
            'requisicion': RequisicionSerializer(requisicion, context={'request': request}).data
        })

    @action(detail=True, methods=['post'], url_path='confirmar-entrega')
    @transaction.atomic
    def confirmar_entrega(self, request, pk=None):
        """
        FLUJO V2: Farmacia confirma la entrega de los medicamentos al centro.
        
        Transición: surtida → entregada
        Permiso: Solo FARMACIA puede confirmar (ellos entregan físicamente)
        
        IMPORTANTE: Debe confirmar antes de fecha_recoleccion_limite
        """
        requisicion = self.get_object()
        estado_actual = (requisicion.estado or '').lower()
        
        if estado_actual != 'surtida':
            return Response({
                'error': 'Solo se pueden confirmar entregas de requisiciones SURTIDAS',
                'estado_actual': requisicion.estado
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not self._validar_transicion(estado_actual, 'entregada'):
            return Response({
                'error': 'Transición de estado no permitida'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # ISS-FIX: Solo FARMACIA puede confirmar entrega (ellos entregan físicamente al centro)
        user_rol = getattr(request.user, 'rol', '') or ''
        roles_permitidos = ['farmacia', 'admin', 'admin_sistema', 'superusuario']
        if user_rol.lower() not in roles_permitidos and not request.user.is_superuser:
            return Response({
                'error': 'Solo el personal de Farmacia puede confirmar la entrega de medicamentos',
                'detalle': 'El centro recibirá los medicamentos cuando Farmacia confirme la entrega'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Verificar fecha límite
        if requisicion.fecha_recoleccion_limite:
            if timezone.now() > requisicion.fecha_recoleccion_limite:
                return Response({
                    'error': 'La fecha límite de recolección ha expirado. La requisición será marcada como vencida.',
                    'fecha_limite': requisicion.fecha_recoleccion_limite.isoformat()
                }, status=status.HTTP_400_BAD_REQUEST)
        
        lugar_entrega = request.data.get('lugar_entrega', '')
        observaciones = request.data.get('observaciones', '')
        
        if not lugar_entrega:
            return Response({
                'error': 'Debe especificar el lugar de entrega'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        estado_anterior = requisicion.estado
        requisicion.estado = 'entregada'
        requisicion.fecha_entrega = timezone.now()
        requisicion.lugar_entrega = lugar_entrega
        if observaciones:
            requisicion.notas = f"{requisicion.notas or ''}\n[Recepción] {observaciones}".strip()
        
        # ISS-004 FIX (audit21): Validar imagen completa (MIME, magic bytes, extensión)
        foto_firma = request.FILES.get('foto_firma_recepcion') or request.FILES.get('foto_firma')
        update_fields = ['estado', 'fecha_entrega', 'lugar_entrega', 'notas']
        
        if foto_firma:
            es_valido, error_msg = validar_archivo_imagen(foto_firma, max_size_mb=2)
            if es_valido:
                requisicion.foto_firma_recepcion = foto_firma
                requisicion.fecha_firma_recepcion = timezone.now()
                requisicion.usuario_firma_recepcion = request.user
                update_fields.extend(['foto_firma_recepcion', 'fecha_firma_recepcion', 'usuario_firma_recepcion'])
            else:
                logger.warning(f"ISS-004: Firma rechazada en confirmar_entrega {requisicion.folio}: {error_msg}")
        
        requisicion.save(update_fields=update_fields)
        
        self._registrar_historial(
            requisicion, estado_anterior, 'entregada',
            request.user, 'confirmar_entrega', request,
            datos_adicionales={
                'lugar_entrega': lugar_entrega,
                'observaciones': observaciones
            }
        )
        
        return Response({
            'mensaje': 'Entrega confirmada exitosamente',
            'requisicion': RequisicionSerializer(requisicion, context={'request': request}).data
        })

    @action(detail=True, methods=['post'], url_path='marcar-vencida')
    @transaction.atomic
    def marcar_vencida(self, request, pk=None):
        """
        FLUJO V2: Marca una requisición como vencida (manualmente por admin).
        
        Transición: surtida → vencida
        Permiso: Solo admin/superuser
        
        NOTA: Normalmente esto lo hace un cron automáticamente.
        """
        requisicion = self.get_object()
        estado_actual = (requisicion.estado or '').lower()
        
        if estado_actual != 'surtida':
            return Response({
                'error': 'Solo se pueden marcar como vencidas requisiciones SURTIDAS',
                'estado_actual': requisicion.estado
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not request.user.is_superuser and not is_farmacia_or_admin(request.user):
            return Response({
                'error': 'Solo administradores pueden marcar requisiciones como vencidas'
            }, status=status.HTTP_403_FORBIDDEN)
        
        motivo = request.data.get('motivo', 'Vencimiento manual por administrador')
        
        estado_anterior = requisicion.estado
        requisicion.estado = 'vencida'
        requisicion.fecha_vencimiento = timezone.now()
        requisicion.motivo_vencimiento = motivo
        requisicion.save(update_fields=['estado', 'fecha_vencimiento', 'motivo_vencimiento'])
        
        self._registrar_historial(
            requisicion, estado_anterior, 'vencida',
            request.user, 'vencer', request,
            motivo=motivo
        )
        
        return Response({
            'mensaje': 'Requisición marcada como vencida',
            'requisicion': RequisicionSerializer(requisicion, context={'request': request}).data
        })

    @action(detail=True, methods=['get'], url_path='historial')
    def historial_estados(self, request, pk=None):
        """
        FLUJO V2: Obtiene el historial de cambios de estado de una requisición.
        
        Retorna lista ordenada de todos los cambios para auditoría.
        """
        from core.models import RequisicionHistorialEstados
        from core.serializers import RequisicionHistorialEstadosSerializer
        
        requisicion = self.get_object()
        
        # Validar acceso - ISS-FIX-CENTRO: usar centro_origen (el centro que solicita)
        # FALLBACK: si centro_origen es NULL (datos viejos), usar centro_destino
        if not request.user.is_superuser and not is_farmacia_or_admin(request.user):
            centro_user = self._user_centro(request.user)
            requisicion_centro_id = requisicion.centro_origen_id or requisicion.centro_destino_id
            if not centro_user or requisicion_centro_id != centro_user.id:
                return Response({
                    'error': 'No tiene acceso al historial de esta requisición'
                }, status=status.HTTP_403_FORBIDDEN)
        
        historial = RequisicionHistorialEstados.objects.filter(
            requisicion=requisicion
        ).select_related('usuario').order_by('fecha_cambio')
        
        # Usar el serializer formal para consistencia
        serializer = RequisicionHistorialEstadosSerializer(historial, many=True)
        
        return Response({
            'requisicion_id': requisicion.id,
            'folio': requisicion.folio,
            'estado_actual': requisicion.estado,
            'total_cambios': historial.count(),
            'historial': serializer.data
        })

    @action(detail=False, methods=['post'], url_path='verificar-vencidas')
    def verificar_vencidas(self, request):
        """
        FLUJO V2: Verifica y marca como vencidas las requisiciones que superaron 
        su fecha límite de recolección.
        
        Este endpoint simula lo que haría el cron diario.
        Solo disponible para admin/superuser.
        """
        if not request.user.is_superuser and not is_farmacia_or_admin(request.user):
            return Response({
                'error': 'Solo administradores pueden ejecutar esta operación'
            }, status=status.HTTP_403_FORBIDDEN)
        
        from core.models import RequisicionHistorialEstados
        
        ahora = timezone.now()
        requisiciones_vencidas = Requisicion.objects.filter(
            estado='surtida',
            fecha_recoleccion_limite__lt=ahora
        )
        
        vencidas = []
        for req in requisiciones_vencidas:
            estado_anterior = req.estado
            req.estado = 'vencida'
            req.fecha_vencimiento = ahora
            req.motivo_vencimiento = f'Vencimiento automático. Fecha límite: {req.fecha_recoleccion_limite.strftime("%Y-%m-%d %H:%M")}'
            req.save(update_fields=['estado', 'fecha_vencimiento', 'motivo_vencimiento'])
            
            # Registrar en historial
            try:
                RequisicionHistorialEstados.objects.create(
                    requisicion=req,
                    estado_anterior=estado_anterior,
                    estado_nuevo='vencida',
                    usuario=request.user,
                    accion='vencer_automatico',
                    motivo=req.motivo_vencimiento,
                    ip_address=self._get_client_ip(request)
                )
            except Exception as e:
                logger.warning(f"No se pudo registrar historial para REQ-{req.numero}: {e}")
            
            vencidas.append({
                'id': req.id,
                'folio': req.folio,
                'centro': req.centro_destino.nombre if req.centro_destino else None,
                'fecha_limite': req.fecha_recoleccion_limite.isoformat()
            })
        
        return Response({
            'mensaje': f'Se marcaron {len(vencidas)} requisiciones como vencidas',
            'total_vencidas': len(vencidas),
            'requisiciones': vencidas
        })

    @action(detail=False, methods=['get'], url_path='transiciones-disponibles')
    def transiciones_disponibles(self, request):
        """
        FLUJO V2: Retorna las transiciones de estado disponibles según el rol del usuario.
        
        Útil para que el frontend sepa qué acciones mostrar.
        """
        user = request.user
        rol = (getattr(user, 'rol', '') or '').lower()
        permisos_rol = PERMISOS_FLUJO_REQUISICION.get(rol, {})
        
        if user.is_superuser:
            permisos_rol = {k: True for k in [
                'puede_crear', 'puede_enviar_admin', 'puede_autorizar_admin',
                'puede_autorizar_director', 'puede_recibir_farmacia',
                'puede_autorizar_farmacia', 'puede_surtir', 'puede_confirmar_entrega'
            ]}
        
        acciones_disponibles = []
        
        if permisos_rol.get('puede_crear'):
            acciones_disponibles.append({
                'accion': 'crear',
                'endpoint': '/api/requisiciones/',
                'metodo': 'POST',
                'descripcion': 'Crear nueva requisición'
            })
        
        if permisos_rol.get('puede_enviar_admin'):
            acciones_disponibles.append({
                'accion': 'enviar_admin',
                'endpoint': '/api/requisiciones/{id}/enviar-admin/',
                'metodo': 'POST',
                'estado_requerido': 'borrador',
                'estado_resultante': 'pendiente_admin',
                'descripcion': 'Enviar a administrador del centro'
            })
        
        if permisos_rol.get('puede_autorizar_admin'):
            acciones_disponibles.append({
                'accion': 'autorizar_admin',
                'endpoint': '/api/requisiciones/{id}/autorizar-admin/',
                'metodo': 'POST',
                'estado_requerido': 'pendiente_admin',
                'estado_resultante': 'pendiente_director',
                'descripcion': 'Autorizar como administrador'
            })
        
        if permisos_rol.get('puede_autorizar_director'):
            acciones_disponibles.append({
                'accion': 'autorizar_director',
                'endpoint': '/api/requisiciones/{id}/autorizar-director/',
                'metodo': 'POST',
                'estado_requerido': 'pendiente_director',
                'estado_resultante': 'enviada',
                'descripcion': 'Autorizar como director'
            })
        
        if permisos_rol.get('puede_recibir_farmacia'):
            acciones_disponibles.append({
                'accion': 'recibir_farmacia',
                'endpoint': '/api/requisiciones/{id}/recibir-farmacia/',
                'metodo': 'POST',
                'estado_requerido': 'enviada',
                'estado_resultante': 'en_revision',
                'descripcion': 'Recibir en farmacia para revisión'
            })
        
        if permisos_rol.get('puede_autorizar_farmacia'):
            acciones_disponibles.append({
                'accion': 'autorizar_farmacia',
                'endpoint': '/api/requisiciones/{id}/autorizar-farmacia/',
                'metodo': 'POST',
                'estado_requerido': ['en_revision', 'enviada'],
                'estado_resultante': 'autorizada',
                'descripcion': 'Autorizar y asignar fecha de recolección',
                'campos_requeridos': ['fecha_recoleccion_limite']
            })
        
        if permisos_rol.get('puede_surtir'):
            acciones_disponibles.append({
                'accion': 'surtir',
                'endpoint': '/api/requisiciones/{id}/surtir/',
                'metodo': 'POST',
                'estado_requerido': 'autorizada',
                'estado_resultante': 'surtida',
                'descripcion': 'Surtir requisición'
            })
        
        if permisos_rol.get('puede_confirmar_entrega'):
            acciones_disponibles.append({
                'accion': 'confirmar_entrega',
                'endpoint': '/api/requisiciones/{id}/confirmar-entrega/',
                'metodo': 'POST',
                'estado_requerido': 'surtida',
                'estado_resultante': 'entregada',
                'descripcion': 'Confirmar recepción de medicamentos',
                'campos_requeridos': ['lugar_entrega']
            })
        
        return Response({
            'usuario': user.username,
            'rol': rol,
            'es_superuser': user.is_superuser,
            'es_farmacia': is_farmacia_or_admin(user),
            'acciones_disponibles': acciones_disponibles,
            'transiciones': TRANSICIONES_REQUISICION
        })

    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """Estadsticas de requisiciones filtradas por centro si aplica."""
        try:
            # SEGURIDAD: Filtrar por centro del usuario si no es admin/farmacia
            user = request.user
            base_queryset = Requisicion.objects.all()
            
            if not is_farmacia_or_admin(user):
                user_centro = get_user_centro(user)
                if user_centro:
                    base_queryset = base_queryset.filter(centro_destino=user_centro)
                else:
                    base_queryset = Requisicion.objects.none()
            
            total = base_queryset.count()
            por_estado = {estado: base_queryset.filter(estado=estado).count() for estado, _ in ESTADOS_REQUISICION}
            
            # Top centros solo para admin/farmacia
            por_centro = []
            if is_farmacia_or_admin(user):
                # Usar requisiciones_destino (related_name correcto del FK centro_destino)
                centros = Centro.objects.annotate(total_requisiciones=Count('requisiciones_destino')).filter(total_requisiciones__gt=0).order_by('-total_requisiciones')[:10]
                for centro in centros:
                    por_centro.append({'centro': centro.nombre, 'total': centro.total_requisiciones})
            
            return Response({'total': total, 'por_estado': por_estado, 'top_centros': por_centro})
        except Exception as exc:
            # traceback removido por seguridad (ISS-008)
            return Response({'error': 'Error al obtener estadisticas', 'mensaje': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='resumen_estados')
    def resumen_estados(self, request):
        """
        Resumen de conteos por estado y por grupo lógico.
        
        FIX: Ahora aplica TODOS los filtros del frontend para que los contadores
        de las tabs reflejen correctamente los datos filtrados.
        
        Filtros soportados: centro, estado, grupo_estado, search, fecha_desde, fecha_hasta
        """
        try:
            user = request.user
            base_queryset = Requisicion.objects.all()
            
            # SEGURIDAD: Filtrar por centro del usuario si no es admin/farmacia
            if not is_farmacia_or_admin(user):
                user_centro = get_user_centro(user)
                if user_centro:
                    base_queryset = base_queryset.filter(
                        Q(centro_origen=user_centro) | Q(centro_destino=user_centro)
                    )
                else:
                    base_queryset = Requisicion.objects.none()
            else:
                # Admin/farmacia pueden filtrar por centro específico
                centro_param = request.query_params.get('centro')
                if centro_param and centro_param not in ['', 'null', 'undefined', 'todos', 'PENDING']:
                    try:
                        centro_id = int(centro_param)
                        base_queryset = base_queryset.filter(
                            Q(centro_origen_id=centro_id) | Q(centro_destino_id=centro_id)
                        )
                    except (ValueError, TypeError):
                        pass
            
            # FIX: Aplicar filtro de búsqueda (search)
            # ISS-FIX-CENTRO: buscar en centro_origen (datos nuevos) y centro_destino (datos viejos)
            search = request.query_params.get('search', '').strip()
            if search:
                base_queryset = base_queryset.filter(
                    Q(numero__icontains=search) |
                    Q(solicitante__first_name__icontains=search) |
                    Q(solicitante__last_name__icontains=search) |
                    Q(centro_origen__nombre__icontains=search) |
                    Q(centro_destino__nombre__icontains=search)
                )
            
            # FIX: Aplicar filtro de fechas
            fecha_desde = request.query_params.get('fecha_desde')
            if fecha_desde:
                base_queryset = base_queryset.filter(fecha_solicitud__date__gte=fecha_desde)
            
            fecha_hasta = request.query_params.get('fecha_hasta')
            if fecha_hasta:
                base_queryset = base_queryset.filter(fecha_solicitud__date__lte=fecha_hasta)
            
            # Calcular conteos por estado y por grupo
            por_estado = {estado.upper(): base_queryset.filter(estado=estado).count() for estado, _ in ESTADOS_REQUISICION}
            por_grupo = {}
            for nombre, estados in REQUISICION_GRUPOS_ESTADO.items():
                por_grupo[nombre] = base_queryset.filter(estado__in=estados).count()
            
            return Response({'por_estado': por_estado, 'por_grupo': por_grupo})
        except Exception as exc:
            # traceback removido por seguridad (ISS-008)
            return Response({'error': 'Error al obtener resumen de estados', 'mensaje': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_resumen(request):
    """
    ISS-005: Resumen del dashboard con KPIs y últimos movimientos.
    Implementa caché para mejorar rendimiento.
    
    SEGURIDAD:
    - Usuarios de centro: solo ven datos de su centro
    - Admin/farmacia/vista: ven datos globales por defecto
    - Admin/farmacia/vista pueden usar ?centro=ID para filtrar por centro específico
    """
    try:
        # SEGURIDAD: Filtrar por centro si el usuario no es admin/farmacia/vista
        user = request.user
        filtrar_por_centro = not is_farmacia_or_admin(user)
        user_centro = get_user_centro(user) if filtrar_por_centro else None
        
        # Admin/farmacia/vista puede filtrar por centro especfico
        centro_param = request.query_params.get('centro')
        if centro_param and centro_param not in ['', 'null', 'undefined', 'todos']:
            if is_farmacia_or_admin(user):
                try:
                    user_centro = Centro.objects.get(pk=int(centro_param))
                    filtrar_por_centro = True
                except (Centro.DoesNotExist, ValueError, TypeError):
                    pass
        
        # ISS-005: Generar clave de caché única por usuario/centro
        centro_id = user_centro.id if user_centro else 'global'
        cache_key = f'dashboard_resumen_{centro_id}'
        
        # ISS-005: Intentar obtener del caché (excepto últimos movimientos que son dinámicos)
        cached_kpi = cache.get(cache_key)
        
        if cached_kpi is None:
            # === PRODUCTOS ===
            # ISS-FIX: Para usuarios de centro, contar solo productos que tienen lotes en SU centro
            if filtrar_por_centro and user_centro:
                # Contar productos distintos que tienen lotes activos con stock en el centro
                total_productos = Producto.objects.filter(
                    activo=True,
                    lotes__centro=user_centro,
                    lotes__activo=True,
                    lotes__cantidad_actual__gt=0
                ).distinct().count()
            else:
                total_productos = Producto.objects.filter(activo=True).count()
            
            # === LOTES ===
            lotes_query = Lote.objects.filter(
                activo=True,
                cantidad_actual__gt=0
            )
            
            if filtrar_por_centro and user_centro:
                lotes_query = lotes_query.filter(centro=user_centro)
            
            stock_total = lotes_query.aggregate(
                total=Coalesce(Sum('cantidad_actual'), 0, output_field=IntegerField())
            )['total']
            lotes_activos = lotes_query.count()

            # === MOVIMIENTOS DEL MES ===
            inicio_mes = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            movimientos_base = Movimiento.objects.all()
            if filtrar_por_centro and user_centro:
                movimientos_base = movimientos_base.filter(
                    Q(centro_origen=user_centro) | Q(centro_destino=user_centro) | Q(lote__centro=user_centro)
                )
            
            # Contar movimientos del mes actual
            movimientos_mes = movimientos_base.filter(fecha__gte=inicio_mes).count()
            
            # Si no hay movimientos este mes, mostrar total general como referencia
            total_movimientos = movimientos_base.count() if movimientos_mes == 0 else movimientos_mes
            
            cached_kpi = {
                'total_productos': total_productos,
                'stock_total': max(0, stock_total),
                'lotes_activos': lotes_activos,
                'movimientos_mes': total_movimientos
            }
            
            # ISS-005: Guardar en caché con TTL configurable
            cache_ttl = getattr(settings, 'CACHE_TTL_DASHBOARD', 60)
            cache.set(cache_key, cached_kpi, cache_ttl)
        
        # === ÚLTIMOS MOVIMIENTOS (siempre frescos, no cacheados) ===
        movimientos_base = Movimiento.objects.all()
        if filtrar_por_centro and user_centro:
            movimientos_base = movimientos_base.filter(
                Q(centro_origen=user_centro) | Q(centro_destino=user_centro) | Q(lote__centro=user_centro)
            )
        
        ultimos_movimientos = movimientos_base.select_related(
            'lote__producto', 'lote__centro', 'centro_origen', 'centro_destino', 'requisicion', 'usuario'
        ).order_by('-fecha')[:10]
        
        movimientos_data = []
        for mov in ultimos_movimientos:
            lote = mov.lote
            producto_desc = 'N/A'
            producto_clave = 'N/A'
            lote_numero = 'N/A'
            
            if lote:
                lote_numero = lote.numero_lote or 'N/A'
                if lote.producto:
                    producto_desc = lote.producto.descripcion or 'N/A'
                    producto_clave = lote.producto.clave or 'N/A'
            
            # Determinar origen/destino
            lote_centro = lote.centro if lote else None
            mov_centro = mov.centro_destino
            
            if mov.tipo == 'entrada':
                origen = mov.referencia or 'Proveedor'
                destino = lote_centro.nombre if lote_centro else 'Farmacia Central'
            else:
                origen = lote_centro.nombre if lote_centro else 'Farmacia Central'
                destino = mov_centro.nombre if mov_centro else 'Consumo/Ajuste'
            
            movimientos_data.append({
                'id': mov.id,
                'tipo_movimiento': mov.tipo.upper(),
                'producto__descripcion': producto_desc,
                'producto__clave': producto_clave,
                'lote__codigo_lote': lote_numero,
                'cantidad': abs(mov.cantidad),
                'fecha_movimiento': mov.fecha.isoformat() if mov.fecha else None,
                'observaciones': mov.motivo or '',
                'origen': origen,
                'destino': destino,
                'requisicion_folio': mov.requisicion.folio if mov.requisicion else None,
                'referencia': mov.referencia or None,
                'usuario': (mov.usuario.get_full_name() or mov.usuario.username) if mov.usuario else 'Sistema',
            })

        return Response({
            'kpi': cached_kpi,
            'ultimos_movimientos': movimientos_data
        })
        
    except Exception as exc:
        # traceback removido por seguridad (ISS-008)
        logger.exception('Error en dashboard_resumen')
        return Response({
            'kpi': {'total_productos': 0, 'stock_total': 0, 'lotes_activos': 0, 'movimientos_mes': 0},
            'ultimos_movimientos': [],
            'error': 'Error interno del servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_graficas(request):
    """
    ISS-005: Datos para gráficas del dashboard con caché.
    Retorna consumo_mensual, stock_por_centro y requisiciones_por_estado.
    
    SEGURIDAD: Filtra por centro del usuario si no es admin/farmacia.
    Admin/farmacia puede usar ?centro=ID para filtrar por centro específico.
    """
    try:
        from dateutil.relativedelta import relativedelta
        
        # SEGURIDAD: Determinar filtro de centro
        user = request.user
        filtrar_por_centro = not is_farmacia_or_admin(user)
        user_centro = get_user_centro(user) if filtrar_por_centro else None
        
        # Admin/farmacia puede filtrar por centro específico
        centro_param = request.query_params.get('centro')
        if centro_param and centro_param not in ['', 'null', 'undefined', 'todos']:
            if is_farmacia_or_admin(user):
                try:
                    user_centro = Centro.objects.get(pk=int(centro_param))
                    filtrar_por_centro = True
                except (Centro.DoesNotExist, ValueError, TypeError):
                    pass
        
        # ISS-005: Generar clave de caché única por centro
        centro_id = user_centro.id if user_centro else 'global'
        cache_key = f'dashboard_graficas_{centro_id}'
        
        # ISS-005: Intentar obtener del caché
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)
        
        hoy = timezone.now().date()
        
        # =========================================
        # 1. CONSUMO MENSUAL (LTIMOS 6 MESES)
        # =========================================
        consumo_mensual = []
        
        for i in range(6):
            # Calcular el mes (hace 5, 4, 3, 2, 1, 0 meses)
            fecha_mes = hoy - relativedelta(months=5-i)
            mes_inicio = fecha_mes.replace(day=1)
            
            # Calcular fin del mes
            if fecha_mes.month == 12:
                mes_fin = fecha_mes.replace(year=fecha_mes.year + 1, month=1, day=1)
            else:
                mes_fin = fecha_mes.replace(month=fecha_mes.month + 1, day=1)
            
            # Base query
            mov_mes = Movimiento.objects.filter(
                fecha__date__gte=mes_inicio,
                fecha__date__lt=mes_fin
            )
            
            if filtrar_por_centro and user_centro:
                mov_mes = mov_mes.filter(
                    Q(centro_origen=user_centro) | Q(centro_destino=user_centro) | Q(lote__centro=user_centro)
                )
            
            # Calcular entradas y salidas
            entradas = mov_mes.filter(tipo='entrada').aggregate(
                total=Coalesce(Sum('cantidad'), 0, output_field=IntegerField())
            )['total']
            
            salidas = mov_mes.filter(tipo='salida').aggregate(
                total=Coalesce(Sum('cantidad'), 0, output_field=IntegerField())
            )['total']
            
            consumo_mensual.append({
                'mes': mes_inicio.strftime('%b'),
                'entradas': max(0, abs(entradas)),
                'salidas': max(0, abs(salidas)),
            })
        
        # =========================================
        # 2. STOCK POR CENTRO (TODOS LOS CENTROS CON STOCK > 0)
        # =========================================
        stock_por_centro = []
        
        if not filtrar_por_centro:
            # Farmacia Central (lotes sin centro asignado)
            stock_farmacia = Lote.objects.filter(
                centro__isnull=True,
                activo=True,
                cantidad_actual__gt=0
            ).aggregate(
                total=Coalesce(Sum('cantidad_actual'), 0, output_field=IntegerField())
            )['total']
            
            # Solo agregar Farmacia Central si tiene stock
            if stock_farmacia > 0:
                stock_por_centro.append({
                    'centro': 'Farmacia Central',
                    'stock': stock_farmacia
                })
            
            # Todos los centros activos CON STOCK
            for centro in Centro.objects.filter(activo=True).order_by('nombre'):
                stock = Lote.objects.filter(
                    centro=centro,
                    activo=True,
                    cantidad_actual__gt=0
                ).aggregate(
                    total=Coalesce(Sum('cantidad_actual'), 0, output_field=IntegerField())
                )['total']
                
                # Solo agregar centros con stock > 0
                if stock > 0:
                    # Truncar nombre largo
                    nombre = centro.nombre
                    if len(nombre) > 20:
                        nombre = nombre[:17] + '...'
                    
                    stock_por_centro.append({
                        'centro': nombre,
                        'stock': stock
                    })
        else:
            # Usuario de centro: solo su stock
            if user_centro:
                stock = Lote.objects.filter(
                    centro=user_centro,
                    activo=True,
                    cantidad_actual__gt=0
                ).aggregate(
                    total=Coalesce(Sum('cantidad_actual'), 0, output_field=IntegerField())
                )['total']
                
                stock_por_centro.append({
                    'centro': user_centro.nombre,
                    'stock': max(0, stock)
                })
        
        # =========================================
        # 3. REQUISICIONES POR ESTADO
        # =========================================
        requisiciones_qs = Requisicion.objects.all()
        if filtrar_por_centro and user_centro:
            requisiciones_qs = requisiciones_qs.filter(centro_destino=user_centro)
        
        estados_agg = requisiciones_qs.values('estado').annotate(
            cantidad=Count('id')
        ).order_by('estado')
        
        requisiciones_por_estado = []
        for item in estados_agg:
            if item['cantidad'] > 0:
                requisiciones_por_estado.append({
                    'estado': item['estado'].upper(),
                    'cantidad': item['cantidad']
                })
        
        # ISS-005: Preparar respuesta y guardar en caché
        response_data = {
            'consumo_mensual': consumo_mensual,
            'stock_por_centro': stock_por_centro,
            'requisiciones_por_estado': requisiciones_por_estado
        }
        
        # Guardar en caché con TTL de estadísticas (5 minutos por defecto)
        cache_ttl = getattr(settings, 'CACHE_TTL_ESTADISTICAS', 300)
        cache.set(cache_key, response_data, cache_ttl)
        
        return Response(response_data)
        
    except Exception as exc:
        # traceback removido por seguridad (ISS-008)
        logger.exception('Error en dashboard_graficas')
        return Response({
            'consumo_mensual': [],
            'stock_por_centro': [],
            'requisiciones_por_estado': [],
            'error': 'Error interno del servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def trazabilidad_producto(request, clave):
    """
    Trazabilidad de un producto identificado por clave (case-insensitive).
    Retorna lotes, movimientos y alertas de stock/caducidad.
    
    SEGURIDAD: Filtra por centro del usuario si no es admin/farmacia.
    """
    try:
        # SEGURIDAD: Determinar filtro de centro
        user = request.user
        if not user or not user.is_authenticated:
            return Response({'error': 'Autenticacion requerida'}, status=status.HTTP_403_FORBIDDEN)
        rol_usuario = (getattr(user, 'rol', '') or '').lower()
        if rol_usuario == 'vista':
            return Response({'error': 'No tienes permiso para trazabilidad'}, status=status.HTTP_403_FORBIDDEN)
        filtrar_por_centro = not is_farmacia_or_admin(user)
        user_centro = get_user_centro(user) if filtrar_por_centro else None
        
        centro_param = request.query_params.get('centro')
        if centro_param and is_farmacia_or_admin(user):
            try:
                user_centro = Centro.objects.get(pk=centro_param)
                filtrar_por_centro = True
            except Centro.DoesNotExist:
                pass
        
        producto = Producto.objects.filter(
            Q(clave__iexact=clave) | Q(descripcion__iexact=clave)
        ).first()
        if not producto:
            return Response({'error': 'Producto no encontrado', 'clave_buscada': clave}, status=status.HTTP_404_NOT_FOUND)

        lotes = Lote.objects.filter(producto=producto, activo=True)
        
        # Aplicar filtro de centro
        if filtrar_por_centro and user_centro:
            lotes = lotes.filter(centro=user_centro)
        
        lotes = lotes.order_by('-created_at')
        lotes_data = []
        from datetime import date, timedelta

        for lote in lotes:
            dias_caducidad = (lote.fecha_caducidad - date.today()).days if lote.fecha_caducidad else None
            if dias_caducidad is None:
                estado_caducidad = 'DESCONOCIDO'
            elif dias_caducidad < 0:
                estado_caducidad = 'VENCIDO'
            elif dias_caducidad <= 7:
                estado_caducidad = 'CRITICO'
            elif dias_caducidad <= 30:
                estado_caducidad = 'PROXIMO'
            else:
                estado_caducidad = 'NORMAL'

            movimientos_lote = Movimiento.objects.filter(lote=lote)
            total_entradas = movimientos_lote.filter(tipo='entrada').aggregate(total=Sum('cantidad'))['total'] or 0
            total_salidas = movimientos_lote.filter(tipo='salida').aggregate(total=Sum('cantidad'))['total'] or 0

            lotes_data.append({
                'id': lote.id,
                'numero_lote': lote.numero_lote,
                'fecha_caducidad': lote.fecha_caducidad.isoformat() if lote.fecha_caducidad else None,
                'dias_para_caducar': dias_caducidad,
                'estado_caducidad': estado_caducidad,
                'cantidad_actual': lote.cantidad_actual,
                'cantidad_inicial': lote.cantidad_inicial,
                'total_entradas': total_entradas,
                'total_salidas': total_salidas,
                'marca': lote.marca or 'N/A',
                'precio_unitario': str(lote.precio_unitario) if lote.precio_unitario else None,
                # Campos de trazabilidad de contratos (solo para ADMIN/FARMACIA)
                'numero_contrato': (lote.numero_contrato or '') if is_farmacia_or_admin(user) else None,
                'activo': getattr(lote, 'activo', True),
                'created_at': lote.created_at.isoformat()
            })

        movimientos = Movimiento.objects.filter(lote__producto=producto).select_related('lote', 'centro_origen', 'centro_destino')
        
        # Aplicar filtro de centro a movimientos
        if filtrar_por_centro and user_centro:
            movimientos = movimientos.filter(
                Q(centro_origen=user_centro) | Q(centro_destino=user_centro) | Q(lote__centro=user_centro)
            )
        
        movimientos = movimientos.order_by('-fecha')[:100]
        movimientos_data = []
        for mov in movimientos:
            movimientos_data.append({
                'id': mov.id,
                'tipo_movimiento': mov.tipo.upper(),
                'tipo': mov.tipo.upper(),
                'lote': mov.lote.numero_lote if mov.lote else 'N/A',
                'cantidad': mov.cantidad,
                'fecha_movimiento': mov.fecha.isoformat(),
                'observaciones': mov.motivo or ''
            })

        stock_total = lotes.filter(activo=True).aggregate(total=Sum('cantidad_actual'))['total'] or 0
        lotes_activos = lotes.filter(activo=True, cantidad_actual__gt=0).count()
        total_lotes = lotes.count()
        
        # Totales de entradas/salidas filtrados por centro si aplica
        mov_query = Movimiento.objects.filter(lote__producto=producto)
        if filtrar_por_centro and user_centro:
            mov_query = mov_query.filter(lote__centro=user_centro)
        total_entradas_prod = mov_query.filter(tipo='entrada').aggregate(total=Sum('cantidad'))['total'] or 0
        total_salidas_prod = mov_query.filter(tipo='salida').aggregate(total=Sum('cantidad'))['total'] or 0

        fecha_limite = date.today() + timedelta(days=30)
        lotes_proximos_vencer = lotes.filter(cantidad_actual__gt=0, fecha_caducidad__lte=fecha_limite, fecha_caducidad__gte=date.today()).count()
        lotes_vencidos = lotes.filter(cantidad_actual__gt=0, fecha_caducidad__lt=date.today()).count()

        alertas = []
        if stock_total < producto.stock_minimo:
            alertas.append({'tipo': 'STOCK_BAJO', 'mensaje': f'Stock actual ({stock_total}) por debajo del minimo ({producto.stock_minimo})', 'nivel': 'CRITICO'})
        if lotes_vencidos > 0:
            alertas.append({'tipo': 'LOTES_VENCIDOS', 'mensaje': f'{lotes_vencidos} lote(s) vencido(s) con stock', 'nivel': 'CRITICO'})
        if lotes_proximos_vencer > 0:
            alertas.append({'tipo': 'PROXIMOS_VENCER', 'mensaje': f'{lotes_proximos_vencer} lote(s) proximo(s) a vencer (30 dias)', 'nivel': 'ADVERTENCIA'})

        return Response({
            'codigo': producto.clave,
            'producto': {
                'id': producto.id,
                'clave': producto.clave,
                'descripcion': producto.nombre,  # Usar nombre como descripción principal
                'unidad_medida': producto.unidad_medida,
                'stock_minimo': producto.stock_minimo,
                'precio_unitario': None,  # precio_unitario está en Lote, no en Producto
                'activo': producto.activo
            },
            'estadisticas': {
                'stock_total': stock_total,
                'total_lotes': total_lotes,
                'lotes_activos': lotes_activos,
                'total_entradas': total_entradas_prod,
                'total_salidas': total_salidas_prod,
                'diferencia': total_entradas_prod - total_salidas_prod,
                'lotes_proximos_vencer': lotes_proximos_vencer,
                'lotes_vencidos': lotes_vencidos,
                'bajo_minimo': stock_total < producto.stock_minimo
            },
            'lotes': lotes_data,
            'movimientos': movimientos_data,
            'total_movimientos': Movimiento.objects.filter(lote__producto=producto).count(),
            'alertas': alertas
        })
    except Exception as exc:
        # traceback removido por seguridad (ISS-008)
        return Response({'error': 'Error al obtener trazabilidad del producto', 'mensaje': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def trazabilidad_lote(request, codigo):
    """
    Trazabilidad completa de un lote por su numero.
    
    SEGURIDAD: Filtra por centro del usuario si no es admin/farmacia.
    """
    try:
        if not request.user or not request.user.is_authenticated or not is_farmacia_or_admin(request.user):
            return Response({'error': 'Solo usuarios de farmacia o administradores pueden acceder a reportes'}, status=status.HTTP_403_FORBIDDEN)

        # SEGURIDAD: Determinar filtro de centro
        user = request.user
        filtrar_por_centro = not is_farmacia_or_admin(user)
        user_centro = get_user_centro(user) if filtrar_por_centro else None
        
        lote_query = Lote.objects.select_related('producto').filter(numero_lote__iexact=codigo)
        
        # Aplicar filtro de centro
        if filtrar_por_centro and user_centro:
            lote_query = lote_query.filter(centro=user_centro)
        
        lote = lote_query.first()
        if not lote:
            return Response({'error': 'Lote no encontrado', 'codigo_buscado': codigo}, status=status.HTTP_404_NOT_FOUND)

        movimientos = Movimiento.objects.select_related('centro_origen', 'centro_destino', 'usuario').filter(lote=lote).order_by('fecha')
        historial = []
        saldo = 0
        for mov in movimientos:
            saldo += mov.cantidad
            historial.append({
                'id': mov.id,
                'fecha': mov.fecha.isoformat(),
                'tipo': mov.tipo.upper(),
                'cantidad': mov.cantidad,
                'saldo': saldo,
                'centro': mov.centro_destino.nombre if mov.centro_destino else (mov.centro_origen.nombre if mov.centro_origen else 'Farmacia Central'),
                'usuario': mov.usuario.username if mov.usuario else '-',
                'lote': mov.lote.numero_lote if mov.lote else '-',
                'observaciones': mov.motivo or ''
            })

        total_entradas = movimientos.filter(tipo='entrada').aggregate(total=Sum('cantidad'))['total'] or 0
        total_salidas = movimientos.filter(tipo='salida').aggregate(total=Sum('cantidad'))['total'] or 0

        from datetime import date
        dias_caducidad = (lote.fecha_caducidad - date.today()).days if lote.fecha_caducidad else None
        if dias_caducidad is None:
            estado_caducidad = 'DESCONOCIDO'
        elif dias_caducidad < 0:
            estado_caducidad = 'VENCIDO'
        elif dias_caducidad <= 7:
            estado_caducidad = 'CRITICO'
        elif dias_caducidad <= 30:
            estado_caducidad = 'PROXIMO'
        else:
            estado_caducidad = 'NORMAL'

        alertas = []
        if dias_caducidad is not None:
            if dias_caducidad < 0:
                alertas.append({'tipo': 'VENCIDO', 'mensaje': f'Lote vencido hace {abs(dias_caducidad)} dias', 'nivel': 'CRITICO'})
            elif dias_caducidad <= 7:
                alertas.append({'tipo': 'CRITICO', 'mensaje': f'Caduca en {dias_caducidad} dias', 'nivel': 'CRITICO'})
            elif dias_caducidad <= 30:
                alertas.append({'tipo': 'PROXIMO', 'mensaje': f'Caduca en {dias_caducidad} dias', 'nivel': 'ADVERTENCIA'})

        return Response({
            'id': lote.id,
            'numero_lote': lote.numero_lote,
            'producto': lote.producto.clave,
            'lote': {
                'id': lote.id,
                'numero_lote': lote.numero_lote,
                'producto': lote.producto.clave,
                'producto_nombre': lote.producto.nombre,  # Campo para frontend
                'producto_descripcion': lote.producto.descripcion or lote.producto.nombre,
                'cantidad_actual': lote.cantidad_actual,
                'cantidad_inicial': lote.cantidad_inicial,
                'activo': lote.activo,
                'fecha_caducidad': lote.fecha_caducidad.isoformat() if lote.fecha_caducidad else None,
                'dias_para_caducar': dias_caducidad,
                'estado_caducidad': estado_caducidad,
                'marca': lote.marca,
                'proveedor': None,  # Campo no existe en modelo, dejarlo null
                # ISS-FIX: Agregar centro (nombre o 'Farmacia Central' si es null)
                'centro': lote.centro.nombre if lote.centro else 'Farmacia Central',
                'centro_id': lote.centro.id if lote.centro else None,
                # Campos de trazabilidad de contratos (solo para ADMIN/FARMACIA)
                'numero_contrato': lote.numero_contrato if is_farmacia_or_admin(user) else None,
            },
            'estadisticas': {
                'total_entradas': total_entradas,
                'total_salidas': total_salidas,
                'diferencia': total_entradas - total_salidas,
                'cantidad_actual': lote.cantidad_actual,
                'saldo_calculado': saldo,
                'diferencia_stock': saldo - lote.cantidad_actual,
                'consistente': saldo == lote.cantidad_actual
            },
            'movimientos': historial,
            'historial': historial,  # compatibilidad hacia atr?s
            'total_movimientos': movimientos.count(),
            'alertas': alertas
        })
    except Exception as exc:
        # traceback removido por seguridad (ISS-008)
        return Response({'error': 'Error al obtener trazabilidad del lote', 'mensaje': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def reporte_inventario(request):
    """
    Genera reporte de inventario actual.
    Por defecto devuelve JSON. Con ?formato=excel devuelve Excel.
    
    SEGURIDAD: Filtra por centro del usuario si no es admin/farmacia.
    Admin/farmacia puede usar ?centro=ID para filtrar.
    
    Parmetros:
    - centro: ID del centro o 'central' para farmacia central
    - nivel_stock: alto, bajo, normal, sin_stock
    - formato: json (default), excel, pdf
    """
    try:
        if not request.user or not request.user.is_authenticated or not is_farmacia_or_admin(request.user):
            return Response({'error': 'Solo usuarios de farmacia o administradores pueden acceder a reportes'}, status=status.HTTP_403_FORBIDDEN)
        # SEGURIDAD: Determinar filtro de centro
        user = request.user
        
        # Por defecto: admin/farmacia ven solo Farmacia Central
        # Usuarios de centro ven solo su centro
        filtrar_por_centro = True  # Siempre filtrar
        user_centro = None  # NULL = Farmacia Central por defecto
        
        if not is_farmacia_or_admin(user):
            # Usuario de centro: filtrar por su centro
            user_centro = get_user_centro(user)
        
        # Admin/farmacia puede filtrar por centro específico
        centro_param = request.query_params.get('centro')
        if centro_param and is_farmacia_or_admin(user):
            if centro_param == 'central':
                # Filtrar solo farmacia central (ya es el default)
                user_centro = None
            elif centro_param == 'todos':
                # Ver todo (sin filtro de centro)
                filtrar_por_centro = False
            else:
                try:
                    user_centro = Centro.objects.get(pk=centro_param)
                except Centro.DoesNotExist:
                    pass
        
        formato = request.query_params.get('formato', 'json')
        nivel_stock_filtro = request.query_params.get('nivel_stock', '').lower().strip()
        productos = Producto.objects.filter(activo=True).order_by('clave')
        
        # Construir datos
        datos = []
        total_productos = 0
        total_stock = 0
        productos_bajo_minimo = 0
        productos_sin_stock = 0
        
        for idx, producto in enumerate(productos, 1):
            # Aplicar filtro de centro si corresponde
            lotes_query = producto.lotes.filter(
                activo=True
            )
            if filtrar_por_centro:
                if user_centro:
                    lotes_query = lotes_query.filter(centro=user_centro)
                else:
                    # centro=NULL significa farmacia central
                    lotes_query = lotes_query.filter(centro__isnull=True)
            
            stock_total = lotes_query.aggregate(total=Sum('cantidad_actual'))['total'] or 0
            lotes_activos = lotes_query.filter(cantidad_actual__gt=0).count()
            
            # Calcular precio promedio desde lotes (precio_unitario está en Lote, no en Producto)
            from django.db.models import Avg
            precio_promedio = lotes_query.filter(cantidad_actual__gt=0).aggregate(avg=Avg('precio_unitario'))['avg'] or 0.0

            nivel = 'alto'
            if stock_total == 0:
                nivel = 'sin_stock'
                productos_sin_stock += 1
            elif stock_total < producto.stock_minimo:
                nivel = 'bajo'
                productos_bajo_minimo += 1
            elif stock_total < producto.stock_minimo * 1.5:
                nivel = 'normal'
            
            # Filtrar por nivel_stock si se especific
            if nivel_stock_filtro and nivel != nivel_stock_filtro:
                continue

            # Se incluye 'nivel_stock' para compatibilidad con el frontend
            # Usar 'nombre' del producto como descripción principal
            datos.append({
                '#': idx,
                'clave': producto.clave,
                'descripcion': producto.nombre,  # nombre es el campo principal del producto
                'unidad': producto.unidad_medida,
                'unidad_medida': producto.unidad_medida,  # alias esperado por frontend
                'stock_minimo': producto.stock_minimo,
                'stock_actual': stock_total,
                'lotes_activos': lotes_activos,
                'nivel': nivel,
                'nivel_stock': nivel,
                'precio_unitario': float(precio_promedio),
            })
            total_productos += 1
            total_stock += stock_total
        
        resumen = {
            'total_productos': total_productos,
            'total_stock': total_stock,
            'stock_total': total_stock,  # alias para compatibilidad frontend
            'productos_bajo_minimo': productos_bajo_minimo,
            'productos_sin_stock': productos_sin_stock,
        }
        
        # Si formato es JSON, devolver datos
        if formato == 'json':
            return Response({
                'datos': datos,
                'resumen': resumen
            })
        
        # Formato PDF
        if formato == 'pdf':
            from core.utils.pdf_reports import generar_reporte_inventario
            
            # Preparar datos para el generador PDF
            productos_data = []
            for item in datos:
                productos_data.append({
                    'clave': item['clave'],
                    'descripcion': item['descripcion'],
                    'unidad_medida': item['unidad'],
                    'stock_minimo': item['stock_minimo'],
                    'stock_actual': item['stock_actual'],
                    'lotes_activos': item['lotes_activos'],
                    'nivel': item['nivel'],
                    'precio_unitario': item['precio_unitario']
                })
            
            filtros = {
                'fecha_generacion': timezone.now().strftime('%d/%m/%Y %H:%M')
            }
            if filtrar_por_centro and user_centro:
                filtros['centro'] = user_centro.nombre
            
            pdf_buffer = generar_reporte_inventario(productos_data, formato='pdf', filtros=filtros)
            
            response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f"attachment; filename=Inventario_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            return response
        
        # Formato Excel
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Inventario'

        ws.merge_cells('A1:I1')
        titulo = ws['A1']
        titulo.value = 'REPORTE DE INVENTARIO ACTUAL'
        titulo.font = Font(bold=True, size=14, color='632842')
        titulo.alignment = Alignment(horizontal='center', vertical='center')

        ws.merge_cells('A2:I2')
        subtitulo = ws['A2']
        subtitulo.value = f"Generado el {timezone.now().strftime('%d/%m/%Y %H:%M:%S')}"
        subtitulo.alignment = Alignment(horizontal='center')
        subtitulo.font = Font(size=10, italic=True)

        ws.append([])
        headers = ['#', 'Clave', 'Descripcin', 'Unidad', 'Stock Mn.', 'Stock Actual', 'Lotes', 'Nivel', 'Precio']
        ws.append(headers)

        header_fill = PatternFill(start_color='632842', end_color='632842', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF', size=11)
        for cell in ws[4]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')

        for item in datos:
            ws.append([
                item['#'],
                item['clave'],
                item['descripcion'][:70],
                item['unidad'],
                item['stock_minimo'],
                item['stock_actual'],
                item['lotes_activos'],
                item['nivel'].upper(),
                item['precio_unitario']
            ])

        ws.append([])
        resumen_row = ws.max_row + 1
        ws[f'B{resumen_row}'] = 'Total de Productos'
        ws[f'C{resumen_row}'] = resumen['total_productos']
        ws[f'B{resumen_row + 1}'] = 'Stock Total'
        ws[f'C{resumen_row + 1}'] = resumen['total_stock']
        ws[f'B{resumen_row + 2}'] = 'Productos bajo mnimo'
        ws[f'C{resumen_row + 2}'] = resumen['productos_bajo_minimo']

        for col, width in zip(['A','B','C','D','E','F','G','H','I'], [8,14,45,10,14,14,10,12,12]):
            ws.column_dimensions[col].width = width

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f"attachment; filename=Inventario_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        wb.save(response)
        return response

    except Exception as e:
        # traceback removido por seguridad (ISS-008)
        return Response({'error': 'Error al generar reporte', 'mensaje': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
@api_view(['GET'])
def reporte_movimientos(request):
    """
    Genera reporte de movimientos con filtros.
    
    SEGURIDAD: Filtra por centro del usuario si no es admin/farmacia.
    Admin/farmacia puede usar ?centro=ID para filtrar.
    
    Parametros:
    - fecha_inicio: Fecha inicial (YYYY-MM-DD)
    - fecha_fin: Fecha final (YYYY-MM-DD)
    - tipo: ENTRADA o SALIDA
    - centro: ID del centro (solo admin/farmacia)
    - formato: excel o pdf
    """
    try:
        logger.info(f"Generando reporte de movimientos. Params: {dict(request.query_params)}")
        
        # SEGURIDAD: Determinar filtro de centro
        user = request.user
        filtrar_por_centro = not is_farmacia_or_admin(user)
        user_centro = get_user_centro(user) if filtrar_por_centro else None
        
        # Admin/farmacia puede filtrar por centro específico
        centro_param = request.query_params.get('centro')
        # Ignorar 'todos' como parámetro de centro
        if centro_param and centro_param.lower() == 'todos':
            centro_param = None
        if centro_param and is_farmacia_or_admin(user):
            try:
                user_centro = Centro.objects.get(pk=centro_param)
                filtrar_por_centro = True
            except Centro.DoesNotExist:
                pass
        
        # Obtener parametros
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin')
        tipo = request.query_params.get('tipo')
        formato = request.query_params.get('formato', 'excel')
        
        # Filtrar movimientos
        movimientos = Movimiento.objects.select_related('lote__producto', 'centro_origen', 'centro_destino').all()
        
        # Aplicar filtro de centro
        if filtrar_por_centro and user_centro:
            movimientos = movimientos.filter(
                Q(centro_origen=user_centro) | Q(centro_destino=user_centro) | Q(lote__centro=user_centro)
            )
        
        if fecha_inicio:
            movimientos = movimientos.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            movimientos = movimientos.filter(fecha__lte=fecha_fin)
        if tipo:
            movimientos = movimientos.filter(tipo=tipo.lower())
        
        movimientos = movimientos.order_by('-fecha')
        
        # Agrupar movimientos por referencia/transacción
        transacciones = {}
        total_entradas = 0
        total_salidas = 0
        
        for mov in movimientos:
            amount = abs(mov.cantidad) if mov.tipo == 'salida' else mov.cantidad
            ref = mov.referencia or f"MOV-{mov.id}"
            
            if ref not in transacciones:
                # Crear nueva transacción agrupada
                transacciones[ref] = {
                    'referencia': ref,
                    'fecha': mov.fecha.strftime('%d/%m/%Y %H:%M'),
                    'fecha_raw': mov.fecha,
                    'tipo': mov.tipo.upper(),
                    'centro_origen': mov.centro_origen.nombre if mov.centro_origen else 'Farmacia Central',
                    'centro_destino': mov.centro_destino.nombre if mov.centro_destino else 'Farmacia Central',
                    'total_productos': 0,
                    'total_cantidad': 0,
                    'observaciones': mov.motivo or '',
                    'detalles': []
                }
            
            # Agregar detalle a la transacción
            producto_info = 'N/A'
            if mov.lote and mov.lote.producto:
                producto_info = f"{mov.lote.producto.clave} - {(mov.lote.producto.descripcion or '')[:50]}"
            
            transacciones[ref]['detalles'].append({
                'producto': producto_info,
                'lote': mov.lote.numero_lote if mov.lote else 'N/A',
                'cantidad': amount
            })
            transacciones[ref]['total_productos'] += 1
            transacciones[ref]['total_cantidad'] += amount
            
            if mov.tipo == 'entrada':
                total_entradas += amount
            else:
                total_salidas += amount
        
        # Convertir a lista ordenada por fecha
        datos = list(transacciones.values())
        datos.sort(key=lambda x: x['fecha_raw'], reverse=True)
        
        # Limpiar fecha_raw antes de enviar
        for item in datos:
            del item['fecha_raw']
        
        resumen = {
            'total_transacciones': len(datos),
            'total_movimientos': sum(t['total_productos'] for t in datos),
            'total_entradas': total_entradas,
            'total_salidas': total_salidas,
            'diferencia': total_entradas - total_salidas
        }
        
        # Formato JSON
        if formato == 'json':
            return Response({
                'datos': datos,
                'resumen': resumen
            })
        
        # Formato PDF
        if formato == 'pdf':
            from core.utils.pdf_reports import generar_reporte_movimientos
            
            # Los datos ya están agrupados por transacción, pasarlos directamente
            filtros = {
                'fecha_generacion': timezone.now().strftime('%d/%m/%Y %H:%M')
            }
            if fecha_inicio:
                filtros['fecha_inicio'] = fecha_inicio
            if fecha_fin:
                filtros['fecha_fin'] = fecha_fin
            if tipo:
                filtros['tipo'] = tipo
            if filtrar_por_centro and user_centro:
                filtros['centro'] = user_centro.nombre
            
            # Pasar resumen y datos agrupados al generador PDF
            pdf_buffer = generar_reporte_movimientos(datos, filtros=filtros, resumen=resumen)
            
            response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f"attachment; filename=Movimientos_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            return response
        
        if formato == 'excel':
            # Generar Excel con formato agrupado por transacciones
            wb = openpyxl.Workbook()
            
            # === HOJA 1: RESUMEN DE TRANSACCIONES ===
            ws = wb.active
            ws.title = 'Transacciones'
            
            # Titulo
            ws.merge_cells('A1:H1')
            titulo_cell = ws['A1']
            titulo_cell.value = 'REPORTE DE MOVIMIENTOS - TRANSACCIONES'
            titulo_cell.font = Font(bold=True, size=14, color='632842')
            titulo_cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Filtros aplicados
            filtros_text = []
            if fecha_inicio:
                filtros_text.append(f'Desde: {fecha_inicio}')
            if fecha_fin:
                filtros_text.append(f'Hasta: {fecha_fin}')
            if tipo:
                filtros_text.append(f'Tipo: {tipo}')
            
            ws.merge_cells('A2:H2')
            filtros_cell = ws['A2']
            filtros_cell.value = ' | '.join(filtros_text) if filtros_text else 'Sin filtros'
            filtros_cell.font = Font(size=10, italic=True)
            filtros_cell.alignment = Alignment(horizontal='center')
            
            # Resumen
            ws['A3'] = f"Total Transacciones: {resumen['total_transacciones']}"
            ws['C3'] = f"Total Entradas: {resumen['total_entradas']}"
            ws['E3'] = f"Total Salidas: {resumen['total_salidas']}"
            ws['G3'] = f"Diferencia: {resumen['diferencia']}"
            for col in ['A', 'C', 'E', 'G']:
                ws[f'{col}3'].font = Font(bold=True, size=10)
            
            ws.append([])  # Linea en blanco
            
            # Encabezados de transacciones
            headers = ['#', 'Referencia', 'Fecha', 'Tipo', 'Centro Origen', 'Centro Destino', 'Productos', 'Cantidad Total']
            ws.append(headers)
            
            # Estilo encabezados
            header_fill = PatternFill(start_color='632842', end_color='632842', fill_type='solid')
            header_font = Font(bold=True, color='FFFFFF', size=11)
            
            for cell in ws[5]:  # Fila 5 tiene los encabezados
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Datos de transacciones
            for idx, trans in enumerate(datos, 1):
                ws.append([
                    idx,
                    trans['referencia'],
                    trans['fecha'],
                    trans['tipo'],
                    trans['centro_origen'],
                    trans['centro_destino'],
                    trans['total_productos'],
                    trans['total_cantidad']
                ])
                
                # Colorear por tipo
                row_num = idx + 5
                tipo_cell = ws.cell(row=row_num, column=4)
                if trans['tipo'].upper() == 'ENTRADA':
                    tipo_cell.fill = PatternFill(start_color='D4EDDA', end_color='D4EDDA', fill_type='solid')
                    tipo_cell.font = Font(color='155724', bold=True)
                else:
                    tipo_cell.fill = PatternFill(start_color='F8D7DA', end_color='F8D7DA', fill_type='solid')
                    tipo_cell.font = Font(color='721C24', bold=True)
            
            # Ajustar anchos
            ws.column_dimensions['A'].width = 6
            ws.column_dimensions['B'].width = 25
            ws.column_dimensions['C'].width = 18
            ws.column_dimensions['D'].width = 12
            ws.column_dimensions['E'].width = 22
            ws.column_dimensions['F'].width = 22
            ws.column_dimensions['G'].width = 12
            ws.column_dimensions['H'].width = 15
            
            # === HOJA 2: DETALLE DE PRODUCTOS ===
            ws2 = wb.create_sheet('Detalle Productos')
            
            ws2.merge_cells('A1:F1')
            ws2['A1'].value = 'DETALLE DE PRODUCTOS POR TRANSACCIÓN'
            ws2['A1'].font = Font(bold=True, size=14, color='632842')
            ws2['A1'].alignment = Alignment(horizontal='center')
            
            ws2.append([])
            
            # Encabezados detalle
            detail_headers = ['Referencia', 'Tipo', '#', 'Producto', 'Lote', 'Cantidad']
            ws2.append(detail_headers)
            
            for cell in ws2[3]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Agregar detalles de cada transacción
            for trans in datos:
                for det_idx, det in enumerate(trans.get('detalles', []), 1):
                    ws2.append([
                        trans['referencia'],
                        trans['tipo'],
                        det_idx,
                        det['producto'],
                        det['lote'],
                        det['cantidad']
                    ])
            
            # Ajustar anchos
            ws2.column_dimensions['A'].width = 25
            ws2.column_dimensions['B'].width = 12
            ws2.column_dimensions['C'].width = 6
            ws2.column_dimensions['D'].width = 50
            ws2.column_dimensions['E'].width = 18
            ws2.column_dimensions['F'].width = 12
            
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename=Movimientos_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            wb.save(response)
            
            logger.info(f"Reporte Excel generado: {len(datos)} transacciones")
            
            return response
            
        # Formato no soportado
        return Response({
            'error': 'Formato no soportado',
            'formatos_disponibles': ['json', 'pdf', 'excel']
        }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error generando reporte: {str(e)}")
        # traceback removido por seguridad (ISS-008)
        return Response({
            'error': 'Error al generar reporte de movimientos',
            'mensaje': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def reporte_caducidades(request):
    """
    Genera reporte de lotes proximos a caducar.
    Por defecto devuelve JSON. Con ?formato=excel devuelve Excel.
    
    SEGURIDAD: Filtra por centro del usuario si no es admin/farmacia.
    Admin/farmacia puede usar ?centro=ID para filtrar.
    
    Parmetros:
    - dias: Nmero de das de anticipacin (default: 30)
    - centro: ID del centro o 'central' para farmacia central
    - estado: vencido, critico, proximo (filtra por estado especfico)
    - formato: json (default), excel, pdf
    """
    try:
        # SEGURIDAD: Determinar filtro de centro
        user = request.user
        filtrar_por_centro = not is_farmacia_or_admin(user)
        user_centro = get_user_centro(user) if filtrar_por_centro else None
        
        # Admin/farmacia puede filtrar por centro específico
        centro_param = request.query_params.get('centro')
        if centro_param and is_farmacia_or_admin(user):
            if centro_param == 'central':
                filtrar_por_centro = True
                user_centro = None
            else:
                try:
                    user_centro = Centro.objects.get(pk=centro_param)
                    filtrar_por_centro = True
                except Centro.DoesNotExist:
                    pass
        
        dias = int(request.query_params.get('dias', 30))
        formato = request.query_params.get('formato', 'json')
        estado_filtro = request.query_params.get('estado', '').lower().strip()
        
        fecha_limite = date.today() + timedelta(days=dias)
        
        # Obtener lotes proximos a vencer (solo lotes activos)
        lotes = Lote.objects.filter(
            activo=True,
            cantidad_actual__gt=0,
            fecha_caducidad__lte=fecha_limite
        ).select_related('producto')
        
        # Aplicar filtro de centro
        if filtrar_por_centro:
            if user_centro:
                lotes = lotes.filter(centro=user_centro)
            else:
                lotes = lotes.filter(centro__isnull=True)
        
        lotes = lotes.order_by('fecha_caducidad')
        
        # Construir datos
        datos = []
        vencidos = 0
        criticos = 0
        proximos = 0
        
        for lote in lotes:
            dias_restantes = (lote.fecha_caducidad - date.today()).days
            
            if dias_restantes < 0:
                estado = 'vencido'
            elif dias_restantes <= 7:
                estado = 'critico'
            else:
                estado = 'proximo'
            
            # Filtrar por estado si se especificó
            if estado_filtro and estado != estado_filtro:
                continue
            
            # Contadores DESPUÉS del filtro para reflejar datos reales
            if estado == 'vencido':
                vencidos += 1
            elif estado == 'critico':
                criticos += 1
            else:
                proximos += 1
            
            datos.append({
                'producto': f"{lote.producto.clave} - {lote.producto.nombre}",
                'lote': lote.numero_lote,
                'caducidad': lote.fecha_caducidad.isoformat(),
                'dias_restantes': dias_restantes,
                'stock': lote.cantidad_actual,
                'estado': estado,
            })
        
        resumen = {
            'total': len(datos),
            'vencidos': vencidos,
            'criticos': criticos,
            'proximos': proximos,
            'dias_filtro': dias,
        }
        
        # Si formato es JSON, devolver datos
        if formato == 'json':
            return Response({
                'datos': datos,
                'resumen': resumen
            })
        
        # Formato PDF
        if formato == 'pdf':
            from core.utils.pdf_reports import generar_reporte_caducidades
            
            # Preparar datos para el generador PDF
            lotes_data = []
            for item in datos:
                lotes_data.append({
                    'producto': item['producto'],
                    'numero_lote': item['lote'],
                    'fecha_caducidad': item['caducidad'],
                    'dias_restantes': item['dias_restantes'],
                    'cantidad_actual': item['stock'],
                    'estado': item['estado']
                })
            
            filtros = {
                'dias_anticipacion': dias,
                'fecha_generacion': timezone.now().strftime('%d/%m/%Y %H:%M')
            }
            if filtrar_por_centro and user_centro:
                filtros['centro'] = user_centro.nombre
            
            pdf_buffer = generar_reporte_caducidades(lotes_data, dias=dias, filtros=filtros)
            
            response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f"attachment; filename=Caducidades_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            return response
        
        # Generar Excel
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Caducidades'
        
        ws.merge_cells('A1:G1')
        titulo_cell = ws['A1']
        titulo_cell.value = f'REPORTE DE LOTES PROXIMOS A CADUCAR ({dias} DIAS)'
        titulo_cell.font = Font(bold=True, size=14, color='632842')
        titulo_cell.alignment = Alignment(horizontal='center', vertical='center')
        
        ws.merge_cells('A2:G2')
        fecha_cell = ws['A2']
        fecha_cell.value = f'Generado el {timezone.now().strftime("%d/%m/%Y %H:%M")}'
        fecha_cell.font = Font(size=10, italic=True)
        fecha_cell.alignment = Alignment(horizontal='center')
        
        ws.append([])
        
        headers = ['#', 'Producto', 'Lote', 'Caducidad', 'Das Restantes', 'Stock', 'Estado']
        ws.append(headers)
        
        header_fill = PatternFill(start_color='632842', end_color='632842', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF', size=11)
        
        for cell in ws[4]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        for idx, item in enumerate(datos, 1):
            ws.append([
                idx,
                item['producto'][:50],
                item['lote'],
                item['caducidad'],
                item['dias_restantes'],
                item['stock'],
                item['estado'].upper()
            ])
        
        ws.append([])
        resumen_row = ws.max_row + 1
        ws[f'B{resumen_row}'] = 'Total:'
        ws[f'C{resumen_row}'] = resumen['total']
        ws[f'B{resumen_row + 1}'] = 'Vencidos:'
        ws[f'C{resumen_row + 1}'] = resumen['vencidos']
        ws[f'B{resumen_row + 2}'] = 'Crticos:'
        ws[f'C{resumen_row + 2}'] = resumen['criticos']
        ws[f'B{resumen_row + 3}'] = 'Prximos:'
        ws[f'C{resumen_row + 3}'] = resumen['proximos']
        
        for col, width in zip(['A','B','C','D','E','F','G'], [8,50,20,15,15,12,12]):
            ws.column_dimensions[col].width = width
        
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=Caducidades_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        wb.save(response)
        
        return response
        
    except Exception as e:
        # traceback removido por seguridad (ISS-008)
        return Response({
            'error': 'Error al generar reporte de caducidades',
            'mensaje': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def reporte_requisiciones(request):
    """
    Genera reporte de requisiciones con filtros.
    Por defecto devuelve JSON. Con ?formato=excel devuelve Excel.
    
    SEGURIDAD: Filtra por centro del usuario si no es admin/farmacia.
    Admin/farmacia puede usar ?centro=ID para filtrar.
    
    Parametros:
    - fecha_inicio: Fecha inicial (YYYY-MM-DD)
    - fecha_fin: Fecha final (YYYY-MM-DD)
    - estado: Estado de la requisicion
    - centro: ID del centro (solo admin/farmacia)
    - formato: json/excel
    """
    try:
        # SEGURIDAD: Determinar filtro de centro
        user = request.user
        filtrar_por_centro = not is_farmacia_or_admin(user)
        user_centro = get_user_centro(user) if filtrar_por_centro else None
        
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin')
        estado = request.query_params.get('estado')
        centro_param = request.query_params.get('centro') or request.query_params.get('centro_id')
        # Ignorar 'todos' como parámetro de centro
        if centro_param and centro_param.lower() == 'todos':
            centro_param = None
        formato = request.query_params.get('formato', 'json')
        
        requisiciones = Requisicion.objects.select_related('centro_origen', 'centro_destino', 'solicitante').all()
        
        # Aplicar filtro de centro obligatorio para usuarios de centro
        if filtrar_por_centro and user_centro:
            requisiciones = requisiciones.filter(Q(centro_origen=user_centro) | Q(centro_destino=user_centro))
        elif centro_param and is_farmacia_or_admin(user):
            requisiciones = requisiciones.filter(Q(centro_origen_id=centro_param) | Q(centro_destino_id=centro_param))
        
        if fecha_inicio:
            requisiciones = requisiciones.filter(fecha_solicitud__gte=fecha_inicio)
        if fecha_fin:
            requisiciones = requisiciones.filter(fecha_solicitud__lte=fecha_fin)
        if estado:
            requisiciones = requisiciones.filter(estado__iexact=estado)
        
        requisiciones = requisiciones.order_by('-fecha_solicitud')
        
        # Construir datos
        datos = []
        estados_count = {}
        
        for req in requisiciones:
            estado_req = req.estado.upper()
            estados_count[estado_req] = estados_count.get(estado_req, 0) + 1
            
            # Determinar centro (preferir destino, luego origen)
            centro_nombre = 'N/A'
            if req.centro_destino:
                centro_nombre = req.centro_destino.nombre
            elif req.centro_origen:
                centro_nombre = req.centro_origen.nombre
            
            # Obtener detalle de productos
            detalles_productos = []
            for detalle in req.detalles.select_related('producto').all():
                detalles_productos.append({
                    'clave': detalle.producto.clave if detalle.producto else 'N/A',
                    'nombre': detalle.producto.nombre if detalle.producto else 'N/A',
                    'cantidad_solicitada': detalle.cantidad_solicitada or 0,
                    'cantidad_autorizada': detalle.cantidad_autorizada or 0,
                    'cantidad_surtida': detalle.cantidad_surtida or 0,
                })
            
            datos.append({
                'id': req.id,
                'folio': req.folio or f'REQ-{req.id}',
                'centro': centro_nombre,
                'estado': estado_req,
                'fecha_solicitud': req.fecha_solicitud.isoformat() if req.fecha_solicitud else None,
                'total_productos': req.detalles.count(),
                'solicitante': req.solicitante.get_full_name() if req.solicitante else 'N/A',
                'productos': detalles_productos,  # Agregar detalle de productos
            })
        
        resumen = {
            'total': len(datos),
            'por_estado': estados_count,
        }
        
        # Si formato es JSON, devolver datos
        if formato == 'json':
            return Response({
                'datos': datos,
                'resumen': resumen
            })
        
        # Formato PDF
        if formato == 'pdf':
            from core.utils.pdf_reports import generar_reporte_requisiciones
            
            # Preparar datos para el generador PDF - INCLUIR PRODUCTOS
            requisiciones_data = []
            for item in datos:
                requisiciones_data.append({
                    'folio': item['folio'],
                    'centro': item['centro'],
                    'estado': item['estado'],
                    'fecha_solicitud': item['fecha_solicitud'],
                    'total_productos': item['total_productos'],
                    'solicitante': item['solicitante'],
                    'productos': item.get('productos', []),  # INCLUIR detalle de productos
                })
            
            filtros = {
                'fecha_generacion': timezone.now().strftime('%d/%m/%Y %H:%M')
            }
            if fecha_inicio:
                filtros['fecha_inicio'] = fecha_inicio
            if fecha_fin:
                filtros['fecha_fin'] = fecha_fin
            if estado:
                filtros['estado'] = estado
            if filtrar_por_centro and user_centro:
                filtros['centro'] = user_centro.nombre
            
            pdf_buffer = generar_reporte_requisiciones(requisiciones_data, filtros=filtros)
            
            response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f"attachment; filename=Requisiciones_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            return response
        
        # Generar Excel
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Requisiciones'
        
        ws.merge_cells('A1:G1')
        titulo_cell = ws['A1']
        titulo_cell.value = 'REPORTE DE REQUISICIONES'
        titulo_cell.font = Font(bold=True, size=14, color='632842')
        titulo_cell.alignment = Alignment(horizontal='center', vertical='center')
        
        ws.merge_cells('A2:G2')
        fecha_cell = ws['A2']
        fecha_cell.value = f'Generado el {timezone.now().strftime("%d/%m/%Y %H:%M")}'
        fecha_cell.font = Font(size=10, italic=True)
        fecha_cell.alignment = Alignment(horizontal='center')
        
        ws.append([])
        
        headers = ['#', 'Folio', 'Centro', 'Fecha', 'Estado', 'Solicitante', 'Productos']
        ws.append(headers)
        
        header_fill = PatternFill(start_color='632842', end_color='632842', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF', size=11)
        
        for cell in ws[4]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        for idx, item in enumerate(datos, 1):
            ws.append([
                idx,
                item['folio'],
                item['centro'],
                item['fecha_solicitud'][:10] if item['fecha_solicitud'] else 'N/A',
                item['estado'],
                item['solicitante'],
                item['total_productos']
            ])
        
        for col, width in zip(['A','B','C','D','E','F','G'], [6,18,25,12,15,25,10]):
            ws.column_dimensions[col].width = width
        
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=Requisiciones_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        wb.save(response)
        
        return response
        
    except Exception as e:
        # traceback removido por seguridad (ISS-008)
        return Response({
            'error': 'Error al generar reporte de requisiciones',
            'mensaje': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def reporte_medicamentos_por_caducar(request):
    """Resumen JSON de productos con lotes proximos a caducar.
    
    SEGURIDAD: Filtra por centro del usuario si no es admin/farmacia.
    """
    try:
        # SEGURIDAD: Determinar filtro de centro
        user = request.user
        filtrar_por_centro = not is_farmacia_or_admin(user)
        user_centro = get_user_centro(user) if filtrar_por_centro else None
        
        centro_param = request.query_params.get('centro')
        if centro_param and is_farmacia_or_admin(user):
            try:
                user_centro = Centro.objects.get(pk=centro_param)
                filtrar_por_centro = True
            except Centro.DoesNotExist:
                pass
        
        dias = int(request.query_params.get('dias', 30))
        hoy = date.today()
        limite = hoy + timedelta(days=dias)
        lotes = Lote.objects.filter(
            cantidad_actual__gt=0,
            fecha_caducidad__gt=hoy,
            fecha_caducidad__lte=limite
        ).select_related('producto')
        
        # Aplicar filtro de centro
        if filtrar_por_centro and user_centro:
            lotes = lotes.filter(centro=user_centro)

        agregados = {}
        for lote in lotes:
            prod = lote.producto
            key = prod.id
            entry = agregados.setdefault(key, {
                'producto_id': prod.id,
                'clave': prod.clave,
                'descripcion': prod.descripcion,
                'stock_total': 0,
                'lotes': 0,
                'primer_vencimiento': None,
            })
            entry['lotes'] += 1
            entry['stock_total'] += lote.cantidad_actual
            fecha = lote.fecha_caducidad
            if entry['primer_vencimiento'] is None or fecha < entry['primer_vencimiento']:
                entry['primer_vencimiento'] = fecha

        resultados = sorted(
            agregados.values(),
            key=lambda x: x.get('primer_vencimiento') or limite
        )
        for res in resultados:
            fv = res['primer_vencimiento']
            res['primer_vencimiento'] = fv.isoformat() if fv else None

        return Response({
            'total_productos': len(resultados),
            'total_lotes': lotes.count(),
            'dias_configurados': dias,
            'resultados': resultados
        })
    except Exception as exc:
        # traceback removido por seguridad (ISS-008)
        return Response({'error': 'Error al obtener medicamentos por caducar', 'mensaje': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def reporte_bajo_stock(request):
    """Productos con stock por debajo del minimo.
    
    SEGURIDAD: Filtra por centro del usuario si no es admin/farmacia.
    """
    try:
        # SEGURIDAD: Determinar filtro de centro
        user = request.user
        filtrar_por_centro = not is_farmacia_or_admin(user)
        user_centro = get_user_centro(user) if filtrar_por_centro else None
        
        centro_param = request.query_params.get('centro')
        if centro_param and is_farmacia_or_admin(user):
            try:
                user_centro = Centro.objects.get(pk=centro_param)
                filtrar_por_centro = True
            except Centro.DoesNotExist:
                pass
        
        productos = Producto.objects.filter(activo=True)
        resultados = []
        for prod in productos:
            lotes_query = prod.lotes.filter(
                activo=True
            )
            # Aplicar filtro de centro
            if filtrar_por_centro and user_centro:
                lotes_query = lotes_query.filter(centro=user_centro)
            
            stock = lotes_query.aggregate(total=Sum('cantidad_actual'))['total'] or 0
            if stock < prod.stock_minimo:
                resultados.append({
                    'producto_id': prod.id,
                    'clave': prod.clave,
                    'descripcion': prod.descripcion,
                    'stock_actual': stock,
                    'stock_minimo': prod.stock_minimo,
                    'diferencia': prod.stock_minimo - stock
                })
        resultados = sorted(resultados, key=lambda x: x['diferencia'], reverse=True)
        return Response({'total': len(resultados), 'resultados': resultados})
    except Exception as exc:
        # traceback removido por seguridad (ISS-008)
        return Response({'error': 'Error al obtener productos en bajo stock', 'mensaje': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def reporte_consumo(request):
    """
    Consumo (salidas) por producto en un rango de fechas.
    
    SEGURIDAD: Filtra por centro del usuario si no es admin/farmacia.
    """
    try:
        # SEGURIDAD: Determinar filtro de centro
        user = request.user
        filtrar_por_centro = not is_farmacia_or_admin(user)
        user_centro = get_user_centro(user) if filtrar_por_centro else None
        
        centro_param = request.query_params.get('centro')
        if centro_param and is_farmacia_or_admin(user):
            try:
                user_centro = Centro.objects.get(pk=centro_param)
                filtrar_por_centro = True
            except Centro.DoesNotExist:
                pass
        
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin')
        movimientos = Movimiento.objects.select_related('lote__producto', 'centro_origen', 'centro_destino').filter(tipo='salida')
        
        # Aplicar filtro de centro
        if filtrar_por_centro and user_centro:
            movimientos = movimientos.filter(
                Q(centro_origen=user_centro) | Q(centro_destino=user_centro) | Q(lote__centro=user_centro)
            )
        
        if fecha_inicio:
            movimientos = movimientos.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            movimientos = movimientos.filter(fecha__lte=fecha_fin)

        agregados = {}
        for mov in movimientos:
            prod = getattr(mov.lote, 'producto', None)
            if not prod:
                continue
            key = prod.id
            entry = agregados.setdefault(key, {
                'producto_id': prod.id,
                'clave': prod.clave,
                'descripcion': prod.descripcion,
                'total_salidas': 0
            })
            entry['total_salidas'] += abs(mov.cantidad or 0)

        resultados = sorted(agregados.values(), key=lambda x: x['total_salidas'], reverse=True)
        return Response({'total_productos': len(resultados), 'resultados': resultados})
    except Exception as exc:
        # traceback removido por seguridad (ISS-008)
        return Response({'error': 'Error al obtener consumo', 'mensaje': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def reportes_precarga(request):
    """
    Obtiene datos para precargar formularios de reportes.
    
    SEGURIDAD: Filtra centros y lotes segn el rol del usuario.
    - Admin/farmacia: ven todos los centros
    - Usuario de centro: solo ve su centro
    
    Retorna:
    - Lista de productos activos
    - Lista de centros activos (filtrada segn rol)
    - Tipos de movimiento disponibles
    """
    try:
        # SEGURIDAD: Determinar filtro de centro
        user = request.user
        es_admin_farmacia = is_farmacia_or_admin(user)
        user_centro = get_user_centro(user) if not es_admin_farmacia else None
        
        # Usar clave como identificador principal del producto
        productos_qs = Producto.objects.filter(activo=True).values('id', 'clave', 'descripcion').order_by('clave')
        productos = [{'id': p['id'], 'clave': p['clave'], 'descripcion': p['descripcion']} for p in productos_qs]
        
        # Filtrar centros segun rol
        if es_admin_farmacia:
            # Centro no tiene campo 'clave', usar id como identificador
            centros = list(Centro.objects.filter(activo=True).values('id', 'nombre').order_by('nombre'))
            # Agregar 'clave' basado en id para compatibilidad con frontend
            for c in centros:
                c['clave'] = str(c['id'])
        elif user_centro:
            centros = [{'id': user_centro.id, 'clave': user_centro.clave, 'nombre': user_centro.nombre}]
        else:
            centros = []
        
        # Filtrar lotes segun rol
        lotes_query = Lote.objects.filter(activo=True)
        if not es_admin_farmacia and user_centro:
            lotes_query = lotes_query.filter(centro=user_centro)
        lotes = list(lotes_query.values('id', 'numero_lote', 'producto_id'))
        
        return Response({
            'productos': productos,
            'centros': centros,
            'lotes': lotes,
            'tipos_movimiento': ['ENTRADA', 'SALIDA']
        })
        
    except Exception as e:
        # traceback removido por seguridad (ISS-008)
        return Response({
            'error': 'Error al obtener datos de precarga',
            'mensaje': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HojaRecoleccionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet de solo lectura para Hojas de Recoleccion.
    Las hojas se generan automaticamente al autorizar requisiciones.
    """
    queryset = HojaRecoleccion.objects.select_related(
        'centro', 'responsable'
    ).prefetch_related('detalles')
    serializer_class = HojaRecoleccionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get_queryset(self):
        """Filtra por centro si el usuario no es admin/farmacia."""
        queryset = super().get_queryset().order_by('-created_at')
        user = self.request.user
        if not user or not user.is_authenticated:
            return HojaRecoleccion.objects.none()
        if user.is_superuser:
            return queryset
        rol = getattr(user, 'rol', '').lower()
        if rol in ('admin', 'farmacia', 'administrador', 'usuario_farmacia'):
            return queryset
        # Filtrar por centro del usuario
        user_centro = getattr(user, 'centro', None)
        if user_centro:
            return queryset.filter(centro=user_centro)
        return HojaRecoleccion.objects.none()

    @action(detail=True, methods=['get'])
    def verificar_integridad(self, request, pk=None):
        """Verifica que el hash de la hoja coincida con su contenido."""
        import hashlib
        import json
        hoja = self.get_object()
        contenido = json.dumps(hoja.contenido_json, sort_keys=True, ensure_ascii=False)
        hash_calculado = hashlib.sha256(contenido.encode('utf-8')).hexdigest()
        return Response({
            'folio': hoja.numero,
            'hash_almacenado': hoja.hash_contenido,
            'hash_calculado': hash_calculado,
            'integridad_ok': hash_calculado == hoja.hash_contenido
        })

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """Genera y descarga el PDF de la hoja de recolección."""
        from core.utils.pdf_generator import generar_hoja_recoleccion
        
        hoja = self.get_object()
        requisicion = hoja.requisicion
        
        try:
            pdf_buffer = generar_hoja_recoleccion(requisicion)
            
            response = HttpResponse(
                pdf_buffer.getvalue(),
                content_type='application/pdf'
            )
            folio_safe = (hoja.numero or f'HOJA-{hoja.id}').replace('/', '-')
            response['Content-Disposition'] = f'attachment; filename="Hoja_Recoleccion_{folio_safe}.pdf"'
            
            return response
            
        except Exception as e:
            # traceback removido por seguridad (ISS-008)
            return Response({
                'error': 'Error al generar PDF',
                'mensaje': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='por-requisicion/(?P<requisicion_id>[^/.]+)')
    def por_requisicion(self, request, requisicion_id=None):
        """
        Obtiene la hoja de recolección asociada a una requisición específica.
        """
        try:
            hoja = self.get_queryset().filter(requisicion_id=requisicion_id).first()
            if hoja:
                return Response({
                    'existe': True,
                    'hoja': HojaRecoleccionSerializer(hoja, context={'request': request}).data
                })
            return Response({
                'existe': False,
                'hoja': None
            })
        except Exception as e:
            logger.error(f"Error obteniendo hoja por requisición {requisicion_id}: {e}")
            return Response({
                'existe': False,
                'error': str(e)
            }, status=status.HTTP_200_OK)  # No es error crítico







