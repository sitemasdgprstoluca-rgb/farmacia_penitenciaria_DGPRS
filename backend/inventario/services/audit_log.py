"""
ISS-032: Audit log centralizado.

Sistema de auditoría que registra todas las operaciones
importantes del sistema de forma consistente.
"""
import logging
import json
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from functools import wraps

from django.db import models, transaction
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger('audit')


class AuditAction(Enum):
    """Tipos de acciones auditables."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    SOFT_DELETE = "soft_delete"
    RESTORE = "restore"
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGE = "password_change"
    PERMISSION_CHANGE = "permission_change"
    EXPORT = "export"
    IMPORT = "import"
    TRANSITION = "transition"  # Cambio de estado
    APPROVAL = "approval"
    REJECTION = "rejection"
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"
    ERROR = "error"


class AuditSeverity(Enum):
    """Severidad del evento para alertas."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEntry:
    """Entrada de auditoría."""
    timestamp: datetime
    action: AuditAction
    severity: AuditSeverity
    usuario_id: Optional[int]
    usuario_username: Optional[str]
    modelo: str
    objeto_id: Optional[int]
    objeto_repr: str
    descripcion: str
    datos_anteriores: Optional[Dict] = None
    datos_nuevos: Optional[Dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    duracion_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            'timestamp': self.timestamp.isoformat(),
            'action': self.action.value,
            'severity': self.severity.value,
            'usuario_id': self.usuario_id,
            'usuario_username': self.usuario_username,
            'modelo': self.modelo,
            'objeto_id': self.objeto_id,
            'objeto_repr': self.objeto_repr[:200],
            'descripcion': self.descripcion,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'request_id': self.request_id,
            'duracion_ms': self.duracion_ms,
        }
        
        if self.datos_anteriores:
            result['datos_anteriores'] = self._sanitize_data(self.datos_anteriores)
        if self.datos_nuevos:
            result['datos_nuevos'] = self._sanitize_data(self.datos_nuevos)
        if self.metadata:
            result['metadata'] = self.metadata
        
        return result
    
    def _sanitize_data(self, data: Dict) -> Dict:
        """Elimina datos sensibles del log."""
        sensitive_fields = {
            'password', 'token', 'secret', 'api_key', 'access_token',
            'refresh_token', 'private_key', 'credential'
        }
        
        sanitized = {}
        for key, value in data.items():
            if any(s in key.lower() for s in sensitive_fields):
                sanitized[key] = '***REDACTED***'
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_data(value)
            else:
                sanitized[key] = value
        
        return sanitized


class AuditLogger:
    """
    ISS-032: Logger de auditoría centralizado.
    
    Registra eventos en múltiples destinos:
    - Log de Python (estructurado)
    - Base de datos (opcional)
    - Sistema externo (opcional)
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.db_enabled = getattr(settings, 'AUDIT_DB_ENABLED', True)
        self.log_reads = getattr(settings, 'AUDIT_LOG_READS', False)
        self.retention_days = getattr(settings, 'AUDIT_RETENTION_DAYS', 365)
    
    def log(
        self,
        action: AuditAction,
        modelo: str,
        objeto_id: Optional[int] = None,
        objeto_repr: str = "",
        descripcion: str = "",
        usuario=None,
        datos_anteriores: Dict = None,
        datos_nuevos: Dict = None,
        severity: AuditSeverity = AuditSeverity.INFO,
        request=None,
        metadata: Dict = None,
        duracion_ms: float = None
    ):
        """
        ISS-032: Registra un evento de auditoría.
        
        Args:
            action: Tipo de acción
            modelo: Nombre del modelo/entidad
            objeto_id: ID del objeto afectado
            objeto_repr: Representación string del objeto
            descripcion: Descripción del evento
            usuario: Usuario que realizó la acción
            datos_anteriores: Estado anterior (para updates)
            datos_nuevos: Estado nuevo
            severity: Severidad del evento
            request: Request HTTP (para extraer IP, user-agent)
            metadata: Datos adicionales
            duracion_ms: Duración de la operación
        """
        # Skip reads si no está habilitado
        if action == AuditAction.READ and not self.log_reads:
            return
        
        # Extraer info del request
        ip_address = None
        user_agent = None
        request_id = None
        
        if request:
            ip_address = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:200]
            request_id = request.META.get('HTTP_X_REQUEST_ID')
        
        # Crear entrada
        entry = AuditEntry(
            timestamp=timezone.now(),
            action=action,
            severity=severity,
            usuario_id=usuario.id if usuario else None,
            usuario_username=usuario.username if usuario else None,
            modelo=modelo,
            objeto_id=objeto_id,
            objeto_repr=objeto_repr[:200] if objeto_repr else "",
            descripcion=descripcion,
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            duracion_ms=duracion_ms,
            metadata=metadata or {}
        )
        
        # Log estructurado
        self._log_to_python(entry)
        
        # Log a base de datos
        if self.db_enabled:
            self._log_to_db(entry)
    
    def _log_to_python(self, entry: AuditEntry):
        """Log estructurado a Python logger."""
        log_data = entry.to_dict()
        
        # Determinar nivel de log
        level_map = {
            AuditSeverity.DEBUG: logging.DEBUG,
            AuditSeverity.INFO: logging.INFO,
            AuditSeverity.WARNING: logging.WARNING,
            AuditSeverity.ERROR: logging.ERROR,
            AuditSeverity.CRITICAL: logging.CRITICAL,
        }
        level = level_map.get(entry.severity, logging.INFO)
        
        # Formato estructurado
        message = (
            f"[AUDIT] {entry.action.value.upper()} {entry.modelo}"
            f"{'#' + str(entry.objeto_id) if entry.objeto_id else ''} "
            f"by {entry.usuario_username or 'system'}: {entry.descripcion}"
        )
        
        logger.log(level, message, extra={'audit_data': log_data})
    
    def _log_to_db(self, entry: AuditEntry):
        """Log a base de datos usando AuditoriaLog."""
        try:
            from core.models import AuditoriaLog
            
            # Mapear campos al modelo AuditoriaLog existente
            AuditoriaLog.objects.create(
                usuario_id=entry.usuario_id,
                accion=f"{entry.action.value}:{entry.severity.value}",
                modelo=entry.modelo,
                objeto_id=entry.objeto_id,
                objeto_repr=entry.objeto_repr,
                cambios={
                    'descripcion': entry.descripcion,
                    'datos_anteriores': entry.datos_anteriores,
                    'datos_nuevos': entry.datos_nuevos,
                    'metadata': entry.metadata,
                    'duracion_ms': entry.duracion_ms,
                    'request_id': entry.request_id,
                },
                ip_address=entry.ip_address,
                user_agent=entry.user_agent or '',
            )
        except Exception as e:
            # No fallar por errores de auditoría
            logger.error(f"Error guardando audit log en DB: {e}")
    
    def _get_client_ip(self, request) -> str:
        """Extrae IP del cliente considerando proxies."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')
    
    # === Métodos de conveniencia ===
    
    def log_create(self, modelo: str, objeto, usuario=None, request=None):
        """Log de creación."""
        self.log(
            action=AuditAction.CREATE,
            modelo=modelo,
            objeto_id=objeto.pk,
            objeto_repr=str(objeto),
            descripcion=f"Creado {modelo}",
            usuario=usuario,
            datos_nuevos=self._model_to_dict(objeto),
            request=request
        )
    
    def log_update(
        self,
        modelo: str,
        objeto,
        campos_cambiados: Dict,
        datos_anteriores: Dict,
        usuario=None,
        request=None
    ):
        """Log de actualización."""
        campos = ", ".join(campos_cambiados.keys())
        self.log(
            action=AuditAction.UPDATE,
            modelo=modelo,
            objeto_id=objeto.pk,
            objeto_repr=str(objeto),
            descripcion=f"Actualizado {modelo}: {campos}",
            usuario=usuario,
            datos_anteriores=datos_anteriores,
            datos_nuevos=campos_cambiados,
            request=request
        )
    
    def log_delete(self, modelo: str, objeto, usuario=None, request=None, soft=True):
        """Log de eliminación."""
        action = AuditAction.SOFT_DELETE if soft else AuditAction.DELETE
        severity = AuditSeverity.WARNING if not soft else AuditSeverity.INFO
        
        self.log(
            action=action,
            modelo=modelo,
            objeto_id=objeto.pk,
            objeto_repr=str(objeto),
            descripcion=f"{'Soft-delete' if soft else 'Eliminado'} {modelo}",
            usuario=usuario,
            datos_anteriores=self._model_to_dict(objeto),
            severity=severity,
            request=request
        )
    
    def log_login(self, usuario, request=None, exitoso=True):
        """Log de login."""
        action = AuditAction.LOGIN if exitoso else AuditAction.LOGIN_FAILED
        severity = AuditSeverity.INFO if exitoso else AuditSeverity.WARNING
        
        self.log(
            action=action,
            modelo="User",
            objeto_id=usuario.pk if exitoso else None,
            objeto_repr=usuario.username,
            descripcion=f"Login {'exitoso' if exitoso else 'fallido'}",
            usuario=usuario if exitoso else None,
            severity=severity,
            request=request
        )
    
    def log_transition(
        self,
        modelo: str,
        objeto,
        estado_anterior: str,
        estado_nuevo: str,
        usuario=None,
        request=None
    ):
        """Log de transición de estado."""
        self.log(
            action=AuditAction.TRANSITION,
            modelo=modelo,
            objeto_id=objeto.pk,
            objeto_repr=str(objeto),
            descripcion=f"Transición {estado_anterior} -> {estado_nuevo}",
            usuario=usuario,
            datos_anteriores={'estado': estado_anterior},
            datos_nuevos={'estado': estado_nuevo},
            request=request
        )
    
    def log_error(
        self,
        modelo: str,
        descripcion: str,
        exception: Exception = None,
        usuario=None,
        request=None,
        metadata: Dict = None
    ):
        """Log de error."""
        error_metadata = metadata or {}
        
        if exception:
            error_metadata['exception_type'] = type(exception).__name__
            error_metadata['exception_message'] = str(exception)
            error_metadata['traceback'] = traceback.format_exc()
        
        self.log(
            action=AuditAction.ERROR,
            modelo=modelo,
            descripcion=descripcion,
            usuario=usuario,
            severity=AuditSeverity.ERROR,
            request=request,
            metadata=error_metadata
        )
    
    def _model_to_dict(self, obj) -> Dict:
        """Convierte modelo a diccionario para auditoría."""
        if hasattr(obj, '__dict__'):
            result = {}
            for key, value in obj.__dict__.items():
                if not key.startswith('_'):
                    if isinstance(value, (str, int, float, bool, type(None))):
                        result[key] = value
                    elif isinstance(value, datetime):
                        result[key] = value.isoformat()
                    else:
                        result[key] = str(value)
            return result
        return {}


# Singleton global
audit_logger = AuditLogger()


# === Decoradores de auditoría ===

def audit_action(
    action: AuditAction,
    modelo: str,
    descripcion: str = None,
    include_result: bool = False
):
    """
    ISS-032: Decorador para auditar funciones/métodos.
    
    Uso:
        @audit_action(AuditAction.EXPORT, "Reporte", "Exportación de reportes")
        def exportar_reporte(request, ...):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time
            inicio = time.time()
            
            # Intentar extraer request y usuario
            request = kwargs.get('request') or (args[0] if args else None)
            usuario = None
            if hasattr(request, 'user') and request.user.is_authenticated:
                usuario = request.user
            
            try:
                result = func(*args, **kwargs)
                
                duracion = (time.time() - inicio) * 1000
                
                metadata = {}
                if include_result and result:
                    if isinstance(result, dict):
                        metadata['result_keys'] = list(result.keys())
                    elif hasattr(result, 'pk'):
                        metadata['result_id'] = result.pk
                
                audit_logger.log(
                    action=action,
                    modelo=modelo,
                    descripcion=descripcion or f"{action.value} en {modelo}",
                    usuario=usuario,
                    request=request if hasattr(request, 'META') else None,
                    duracion_ms=duracion,
                    metadata=metadata
                )
                
                return result
                
            except Exception as e:
                duracion = (time.time() - inicio) * 1000
                
                audit_logger.log(
                    action=AuditAction.ERROR,
                    modelo=modelo,
                    descripcion=f"Error en {action.value}: {str(e)}",
                    usuario=usuario,
                    severity=AuditSeverity.ERROR,
                    request=request if hasattr(request, 'META') else None,
                    duracion_ms=duracion,
                    metadata={'exception': str(e)}
                )
                raise
        
        return wrapper
    return decorator


def audit_model_changes(modelo_class):
    """
    ISS-032: Decorador de clase para auditar cambios en modelos.
    
    Uso:
        @audit_model_changes
        class MiModelo(models.Model):
            ...
    """
    original_save = modelo_class.save
    original_delete = modelo_class.delete
    
    def audited_save(self, *args, **kwargs):
        is_new = self.pk is None
        
        # Capturar estado anterior si es update
        datos_anteriores = None
        if not is_new:
            try:
                old_instance = modelo_class.objects.get(pk=self.pk)
                datos_anteriores = audit_logger._model_to_dict(old_instance)
            except modelo_class.DoesNotExist:
                pass
        
        # Ejecutar save
        result = original_save(self, *args, **kwargs)
        
        # Auditar
        if is_new:
            audit_logger.log_create(
                modelo=modelo_class.__name__,
                objeto=self
            )
        else:
            datos_nuevos = audit_logger._model_to_dict(self)
            campos_cambiados = {
                k: v for k, v in datos_nuevos.items()
                if datos_anteriores and datos_anteriores.get(k) != v
            }
            if campos_cambiados:
                audit_logger.log_update(
                    modelo=modelo_class.__name__,
                    objeto=self,
                    campos_cambiados=campos_cambiados,
                    datos_anteriores=datos_anteriores
                )
        
        return result
    
    def audited_delete(self, *args, **kwargs):
        audit_logger.log_delete(
            modelo=modelo_class.__name__,
            objeto=self,
            soft=False
        )
        return original_delete(self, *args, **kwargs)
    
    modelo_class.save = audited_save
    modelo_class.delete = audited_delete
    
    return modelo_class
