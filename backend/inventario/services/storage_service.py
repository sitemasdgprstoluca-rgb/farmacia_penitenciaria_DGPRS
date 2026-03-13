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
            
            self._client = create_client(url, key)
            logger.info(f"ISS-001: Supabase Storage inicializado para bucket '{self.bucket}'")
            
        except ImportError:
            logger.error(
                "ISS-001: Paquete 'supabase' no instalado. "
                "Instalar con: pip install supabase"
            )
            self._use_supabase = False
        except Exception as e:
            logger.error(f"ISS-001: Error inicializando Supabase: {e}")
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
            # Subir a Supabase Storage
            response = self._client.storage.from_(self.bucket).upload(
                path=file_path,
                file=content,
                file_options={
                    'content-type': content_type,
                    'x-upsert': 'true'  # Sobrescribir si existe
                }
            )
            
            # Obtener URL pública
            url_response = self._client.storage.from_(self.bucket).get_public_url(file_path)
            
            logger.info(f"ISS-001: Archivo subido a Supabase: {file_path}")
            
            return {
                'success': True,
                'url': url_response,
                'path': file_path,
                'size': len(content),
                'hash': file_hash,
                'storage': 'supabase'
            }
            
        except Exception as e:
            logger.error(f"ISS-001: Error Supabase upload: {e}")
            raise StorageError(str(e), operation='upload', path=file_path)
    
    def _upload_local(
        self,
        content: bytes,
        file_path: str,
        content_type: str,
        metadata: Dict[str, Any],
        file_hash: str
    ) -> Dict[str, Any]:
        """Sube archivo a almacenamiento local (fallback)."""
        try:
            # Usar Django's default_storage
            saved_path = default_storage.save(file_path, ContentFile(content))
            url = default_storage.url(saved_path)
            
            logger.info(f"ISS-001: Archivo guardado localmente: {saved_path}")
            
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


# Instancia singleton para uso en toda la aplicación
_storage_instance = None


def get_storage_service(bucket: str = None) -> StorageService:
    """
    Obtiene instancia del servicio de almacenamiento.
    
    Args:
        bucket: Bucket a usar (opcional)
        
    Returns:
        StorageService: Instancia del servicio
    """
    global _storage_instance
    
    if _storage_instance is None or (bucket and bucket != _storage_instance.bucket):
        _storage_instance = StorageService(bucket)
    
    return _storage_instance
