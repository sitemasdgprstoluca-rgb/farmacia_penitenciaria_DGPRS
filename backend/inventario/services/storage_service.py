"""
ISS-001/002 FIX: Servicio de almacenamiento de archivos.

Soporta:
- Supabase Storage (producción) - S3 compatible
- Almacenamiento local (desarrollo/fallback)

Uso:
    from inventario.services.storage_service import StorageService
    
    storage = StorageService()
    
    # Subir archivo
    result = storage.upload_file(file_content, 'lotes/documentos/123/factura.pdf')
    if result['success']:
        url = result['url']
    
    # Eliminar archivo
    result = storage.delete_file('lotes/documentos/123/factura.pdf')
    
    # Verificar existencia
    exists = storage.file_exists('lotes/documentos/123/factura.pdf')
"""
import os
import logging
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, BinaryIO, Union
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Error de operación de almacenamiento."""
    def __init__(self, message: str, operation: str = None, path: str = None):
        super().__init__(message)
        self.operation = operation
        self.path = path


class StorageService:
    """
    ISS-001/002 FIX: Servicio unificado de almacenamiento de archivos.
    
    En producción usa Supabase Storage (S3 compatible).
    En desarrollo usa almacenamiento local como fallback.
    """
    
    # Bucket por defecto para documentos
    DEFAULT_BUCKET = 'documentos'
    
    # Tipos MIME permitidos para documentos de lote
    ALLOWED_MIME_TYPES = {
        'application/pdf': '.pdf',
        'image/jpeg': '.jpg',
        'image/png': '.png',
    }
    
    # Tamaño máximo por defecto (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024
    
    def __init__(self, bucket: str = None):
        """
        Inicializa el servicio de almacenamiento.
        
        Args:
            bucket: Nombre del bucket (default: 'documentos')
        """
        self.bucket = bucket or self.DEFAULT_BUCKET
        self._client = None
        self._use_supabase = self._check_supabase_config()
        
        if self._use_supabase:
            self._init_supabase_client()
        else:
            logger.warning(
                "ISS-001: Supabase Storage no configurado. "
                "Usando almacenamiento local (NO recomendado para producción)."
            )
    
    def _check_supabase_config(self) -> bool:
        """Verifica si Supabase Storage está configurado."""
        return all([
            getattr(settings, 'SUPABASE_URL', None),
            getattr(settings, 'SUPABASE_KEY', None),
        ])
    
    def _init_supabase_client(self):
        """Inicializa el cliente de Supabase Storage."""
        try:
            from supabase import create_client

            url = settings.SUPABASE_URL
            key = settings.SUPABASE_KEY

            # Detectar tipo de key para logging
            key_type = 'service_role' if key and ('service_role' in key or len(key) > 200) else 'anon/unknown'
            logger.info(
                f"ISS-001: Inicializando Supabase Storage - "
                f"URL={url[:40]}... bucket='{self.bucket}' key_type={key_type}"
            )

            self._client = create_client(url, key)
            logger.info(f"ISS-001: Supabase Storage inicializado OK para bucket '{self.bucket}'")

        except ImportError:
            logger.error(
                "ISS-001: CRÍTICO - Paquete 'supabase' NO INSTALADO. "
                "Los archivos se guardarán localmente (NO persistente en Render). "
                "Instalar con: pip install supabase"
            )
            self._use_supabase = False
        except Exception as e:
            logger.error(f"ISS-001: Error inicializando Supabase: {e}", exc_info=True)
            self._use_supabase = False
    
    def upload_file(
        self,
        file_content: Union[bytes, BinaryIO],
        file_path: str,
        content_type: str = 'application/pdf',
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        ISS-001 FIX: Sube un archivo al almacenamiento.
        
        Args:
            file_content: Contenido del archivo (bytes o file-like object)
            file_path: Ruta destino (ej: 'lotes/documentos/123/factura.pdf')
            content_type: Tipo MIME del archivo
            metadata: Metadata adicional para el archivo
            
        Returns:
            dict: {
                'success': bool,
                'url': str (si éxito),
                'path': str,
                'size': int,
                'error': str (si falla)
            }
        """
        try:
            # Convertir a bytes si es file-like object
            if hasattr(file_content, 'read'):
                content = file_content.read()
                # Resetear posición si es posible
                if hasattr(file_content, 'seek'):
                    file_content.seek(0)
            else:
                content = file_content
            
            # Validar tamaño
            if len(content) > self.MAX_FILE_SIZE:
                return {
                    'success': False,
                    'error': f'Archivo excede tamaño máximo ({self.MAX_FILE_SIZE / 1024 / 1024}MB)',
                    'path': file_path
                }
            
            # Calcular hash para verificación
            file_hash = hashlib.md5(content).hexdigest()
            
            if self._use_supabase:
                return self._upload_supabase(content, file_path, content_type, metadata, file_hash)
            else:
                return self._upload_local(content, file_path, content_type, metadata, file_hash)
                
        except Exception as e:
            logger.error(f"ISS-001: Error subiendo archivo '{file_path}': {e}")
            return {
                'success': False,
                'error': str(e),
                'path': file_path
            }
    
    def _upload_supabase(
        self,
        content: bytes,
        file_path: str,
        content_type: str,
        metadata: Dict[str, Any],
        file_hash: str
    ) -> Dict[str, Any]:
        """Sube archivo a Supabase Storage."""
        try:
            if len(content) == 0:
                raise StorageError("El archivo está vacío (0 bytes)", operation='upload', path=file_path)

            logger.info(
                f"ISS-001: Subiendo a Supabase bucket='{self.bucket}' "
                f"path='{file_path}' size={len(content)} type='{content_type}' "
                f"use_supabase={self._use_supabase} client={'OK' if self._client else 'NONE'}"
            )

            if not self._client:
                raise StorageError(
                    "Cliente Supabase no inicializado. Verificar SUPABASE_URL y SUPABASE_KEY.",
                    operation='upload', path=file_path
                )

            # storage3 usa file_options como headers HTTP directamente
            # 'content-type' y 'x-upsert' son headers HTTP válidos
            response = self._client.storage.from_(self.bucket).upload(
                path=file_path,
                file=content,
                file_options={
                    'content-type': content_type,
                    'x-upsert': 'true',
                }
            )

            # Verificar respuesta - storage3 puede devolver dict, Response, o str
            logger.info(f"ISS-001: Upload response type={type(response).__name__}")

            # Si es un httpx.Response, verificar status code
            if hasattr(response, 'status_code'):
                if response.status_code >= 400:
                    error_text = response.text if hasattr(response, 'text') else str(response)
                    logger.error(f"ISS-001: Supabase HTTP {response.status_code}: {error_text}")
                    raise StorageError(
                        f"HTTP {response.status_code}: {error_text}",
                        operation='upload', path=file_path
                    )

            # Si tiene .json (httpx.Response o similar)
            if response and hasattr(response, 'json'):
                resp_data = response.json() if callable(response.json) else response.json
                if isinstance(resp_data, dict):
                    if resp_data.get('error'):
                        error_msg = resp_data.get('message', resp_data.get('error', 'Error desconocido'))
                        logger.error(f"ISS-001: Supabase upload error: {resp_data}")
                        raise StorageError(error_msg, operation='upload', path=file_path)
                    if resp_data.get('statusCode') and int(resp_data.get('statusCode', 200)) >= 400:
                        logger.error(f"ISS-001: Supabase upload error: {resp_data}")
                        raise StorageError(str(resp_data), operation='upload', path=file_path)

            # Obtener URL pública
            url_response = self._client.storage.from_(self.bucket).get_public_url(file_path)

            logger.info(f"ISS-001: Archivo subido exitosamente a Supabase: {file_path} -> {url_response}")

            return {
                'success': True,
                'url': url_response,
                'path': file_path,
                'size': len(content),
                'hash': file_hash,
                'storage': 'supabase'
            }

        except StorageError:
            raise
        except Exception as e:
            logger.error(f"ISS-001: Error Supabase upload: {e}", exc_info=True)
            raise StorageError(str(e), operation='upload', path=file_path)
    
    def _upload_local(
        self,
        content: bytes,
        file_path: str,
        content_type: str,
        metadata: Dict[str, Any],
        file_hash: str
    ) -> Dict[str, Any]:
        """Sube archivo a almacenamiento local (fallback). NO persistente en Render."""
        try:
            logger.warning(
                f"ISS-001: FALLBACK LOCAL - Guardando '{file_path}' localmente. "
                f"Esto NO es persistente en Render. Instalar paquete 'supabase' y configurar "
                f"SUPABASE_URL/SUPABASE_KEY para almacenamiento permanente."
            )
            # Usar Django's default_storage
            saved_path = default_storage.save(file_path, ContentFile(content))
            url = default_storage.url(saved_path)

            logger.info(f"ISS-001: Archivo guardado localmente: {saved_path} -> {url}")

            return {
                'success': True,
                'url': url,
                'path': saved_path,
                'size': len(content),
                'hash': file_hash,
                'storage': 'local'
            }
            
        except Exception as e:
            logger.error(f"ISS-001: Error local upload: {e}")
            raise StorageError(str(e), operation='upload', path=file_path)
    
    def delete_file(self, file_path: str) -> Dict[str, Any]:
        """
        ISS-002 FIX: Elimina un archivo del almacenamiento.
        
        Args:
            file_path: Ruta del archivo a eliminar
            
        Returns:
            dict: {
                'success': bool,
                'path': str,
                'error': str (si falla)
            }
        """
        try:
            if self._use_supabase:
                return self._delete_supabase(file_path)
            else:
                return self._delete_local(file_path)
                
        except Exception as e:
            logger.error(f"ISS-002: Error eliminando archivo '{file_path}': {e}")
            return {
                'success': False,
                'error': str(e),
                'path': file_path
            }
    
    def _delete_supabase(self, file_path: str) -> Dict[str, Any]:
        """Elimina archivo de Supabase Storage."""
        try:
            response = self._client.storage.from_(self.bucket).remove([file_path])
            
            logger.info(f"ISS-002: Archivo eliminado de Supabase: {file_path}")
            
            return {
                'success': True,
                'path': file_path,
                'storage': 'supabase'
            }
            
        except Exception as e:
            logger.error(f"ISS-002: Error Supabase delete: {e}")
            # No relanzar - documentar fallo pero permitir continuar
            return {
                'success': False,
                'error': str(e),
                'path': file_path,
                'storage': 'supabase'
            }
    
    def _delete_local(self, file_path: str) -> Dict[str, Any]:
        """Elimina archivo de almacenamiento local."""
        try:
            if default_storage.exists(file_path):
                default_storage.delete(file_path)
                logger.info(f"ISS-002: Archivo eliminado localmente: {file_path}")
                return {
                    'success': True,
                    'path': file_path,
                    'storage': 'local'
                }
            else:
                logger.warning(f"ISS-002: Archivo no existe para eliminar: {file_path}")
                return {
                    'success': True,  # No es error si ya no existe
                    'path': file_path,
                    'storage': 'local',
                    'warning': 'Archivo no existía'
                }
                
        except Exception as e:
            logger.error(f"ISS-002: Error local delete: {e}")
            return {
                'success': False,
                'error': str(e),
                'path': file_path,
                'storage': 'local'
            }
    
    def file_exists(self, file_path: str) -> bool:
        """
        Verifica si un archivo existe en el almacenamiento.
        
        Args:
            file_path: Ruta del archivo
            
        Returns:
            bool: True si existe
        """
        try:
            if self._use_supabase:
                # Intentar obtener metadata del archivo
                try:
                    self._client.storage.from_(self.bucket).get_public_url(file_path)
                    return True
                except:
                    return False
            else:
                return default_storage.exists(file_path)
                
        except Exception as e:
            logger.error(f"Error verificando existencia de '{file_path}': {e}")
            return False
    
    def download_file(self, file_path: str) -> Dict[str, Any]:
        """
        Descarga un archivo del almacenamiento.
        
        Args:
            file_path: Ruta del archivo a descargar
            
        Returns:
            dict: {
                'success': bool,
                'content': bytes (si éxito),
                'path': str,
                'size': int (si éxito),
                'error': str (si falla)
            }
        """
        try:
            if self._use_supabase:
                return self._download_supabase(file_path)
            else:
                return self._download_local(file_path)
                
        except Exception as e:
            logger.error(f"Error descargando archivo '{file_path}': {e}")
            return {
                'success': False,
                'error': str(e),
                'path': file_path
            }
    
    def _download_supabase(self, file_path: str) -> Dict[str, Any]:
        """Descarga archivo de Supabase Storage."""
        try:
            response = self._client.storage.from_(self.bucket).download(file_path)
            
            logger.info(f"Archivo descargado de Supabase: {file_path}")
            
            return {
                'success': True,
                'content': response,
                'path': file_path,
                'size': len(response) if response else 0,
                'storage': 'supabase'
            }
            
        except Exception as e:
            logger.error(f"Error Supabase download: {e}")
            return {
                'success': False,
                'error': str(e),
                'path': file_path,
                'storage': 'supabase'
            }
    
    def _download_local(self, file_path: str) -> Dict[str, Any]:
        """Descarga archivo de almacenamiento local."""
        try:
            if default_storage.exists(file_path):
                with default_storage.open(file_path, 'rb') as f:
                    content = f.read()
                
                logger.info(f"Archivo descargado localmente: {file_path}")
                
                return {
                    'success': True,
                    'content': content,
                    'path': file_path,
                    'size': len(content),
                    'storage': 'local'
                }
            else:
                logger.warning(f"Archivo no existe para descargar: {file_path}")
                return {
                    'success': False,
                    'error': 'Archivo no encontrado',
                    'path': file_path,
                    'storage': 'local'
                }
                
        except Exception as e:
            logger.error(f"Error local download: {e}")
            return {
                'success': False,
                'error': str(e),
                'path': file_path,
                'storage': 'local'
            }
    
    def get_url(self, file_path: str, expires_in: int = 3600) -> Optional[str]:
        """
        Obtiene URL de acceso a un archivo.
        
        Args:
            file_path: Ruta del archivo
            expires_in: Segundos de validez para URL firmada (Supabase)
            
        Returns:
            str: URL del archivo o None si no existe
        """
        try:
            if self._use_supabase:
                # URL pública o firmada según configuración del bucket
                return self._client.storage.from_(self.bucket).get_public_url(file_path)
            else:
                if default_storage.exists(file_path):
                    return default_storage.url(file_path)
                return None
                
        except Exception as e:
            logger.error(f"Error obteniendo URL de '{file_path}': {e}")
            return None


# Cache de instancias por bucket
_storage_instances: Dict[str, StorageService] = {}


def get_storage_service(bucket: str = None) -> StorageService:
    """
    Obtiene instancia del servicio de almacenamiento para el bucket especificado.

    Args:
        bucket: Bucket a usar (default: StorageService.DEFAULT_BUCKET)

    Returns:
        StorageService: Instancia del servicio
    """
    global _storage_instances

    bucket_key = bucket or StorageService.DEFAULT_BUCKET

    if bucket_key not in _storage_instances:
        _storage_instances[bucket_key] = StorageService(bucket_key)

    return _storage_instances[bucket_key]


def extract_storage_path(url: str, bucket_name: str) -> str:
    """
    Extrae el path relativo de un archivo desde su URL completa de Supabase Storage.

    Ejemplo:
        URL: https://xxx.supabase.co/storage/v1/object/public/productos-imagenes/2026/03/img.jpg
        bucket_name: 'productos-imagenes'
        Retorna: '2026/03/img.jpg'

    Si la URL no contiene el bucket_name, retorna los últimos 3 segmentos como fallback.
    Si la URL ya es un path relativo (no empieza con http), la retorna tal cual.
    """
    if not url:
        return url

    # Si ya es un path relativo (no una URL completa), retornar tal cual
    if not url.startswith('http'):
        return url

    parts = url.split('/')
    try:
        bucket_idx = parts.index(bucket_name)
        return '/'.join(parts[bucket_idx + 1:])
    except ValueError:
        # Fallback: tomar los últimos 3 segmentos (año/mes/archivo)
        return '/'.join(parts[-3:]) if len(parts) >= 3 else '/'.join(parts[-2:])


def diagnostico_storage() -> Dict[str, Any]:
    """
    Diagnóstico completo del servicio de almacenamiento.
    Úsalo desde: GET /api/diagnostico-storage/
    """
    resultado = {
        'supabase_url_configurado': bool(getattr(settings, 'SUPABASE_URL', '')),
        'supabase_key_configurado': bool(getattr(settings, 'SUPABASE_KEY', '')),
        'supabase_url_preview': (getattr(settings, 'SUPABASE_URL', '') or '')[:50] + '...',
        'supabase_key_tipo': 'no configurado',
        'paquete_supabase_instalado': False,
        'paquete_storage3_instalado': False,
        'buckets_test': {},
    }

    # Verificar tipo de key
    key = getattr(settings, 'SUPABASE_KEY', '') or ''
    if 'service_role' in key:
        resultado['supabase_key_tipo'] = 'service_role (correcto para backend)'
    elif key.startswith('eyJ'):
        resultado['supabase_key_tipo'] = 'JWT (podría ser anon - verificar permisos de buckets)'
    elif key:
        resultado['supabase_key_tipo'] = f'desconocido (primeros 20 chars: {key[:20]}...)'

    # Verificar paquetes
    try:
        import supabase
        resultado['paquete_supabase_instalado'] = True
        resultado['supabase_version'] = getattr(supabase, '__version__', 'desconocida')
    except ImportError:
        resultado['paquete_supabase_instalado'] = False
        resultado['error_critico'] = 'Paquete supabase NO instalado. pip install supabase'

    try:
        import storage3
        resultado['paquete_storage3_instalado'] = True
        resultado['storage3_version'] = getattr(storage3, '__version__', 'desconocida')
    except ImportError:
        resultado['paquete_storage3_instalado'] = False

    # Test de upload por bucket
    buckets = ['productos-imagenes', 'lotes-documentos', 'requisiciones-firmadas', 'dispensaciones-firmadas']
    for bucket_name in buckets:
        try:
            service = StorageService(bucket_name)
            resultado['buckets_test'][bucket_name] = {
                'use_supabase': service._use_supabase,
                'client_ok': service._client is not None,
            }
            if service._use_supabase and service._client:
                # Intentar subir un archivo de prueba pequeño
                test_content = b'test-diagnostico'
                test_path = '_diagnostico/test.txt'
                try:
                    resp = service._client.storage.from_(bucket_name).upload(
                        path=test_path,
                        file=test_content,
                        file_options={
                            'content-type': 'text/plain',
                            'x-upsert': 'true',
                        }
                    )
                    resultado['buckets_test'][bucket_name]['upload_ok'] = True
                    resultado['buckets_test'][bucket_name]['upload_response_type'] = type(resp).__name__

                    # Verificar URL
                    url = service._client.storage.from_(bucket_name).get_public_url(test_path)
                    resultado['buckets_test'][bucket_name]['url_ejemplo'] = url

                    # Limpiar archivo de prueba
                    try:
                        service._client.storage.from_(bucket_name).remove([test_path])
                    except Exception:
                        pass

                except Exception as upload_err:
                    resultado['buckets_test'][bucket_name]['upload_ok'] = False
                    resultado['buckets_test'][bucket_name]['upload_error'] = str(upload_err)
        except Exception as e:
            resultado['buckets_test'][bucket_name] = {'error': str(e)}

    return resultado
