"""
Middleware para capturar IP y User-Agent en auditoría
"""
import re
import threading
from django.conf import settings

_thread_locals = threading.local()


def get_current_request():
    """Obtiene el request actual del thread local"""
    return getattr(_thread_locals, 'request', None)


def get_current_user():
    """Obtiene el usuario actual del request"""
    request = get_current_request()
    if request:
        return getattr(request, 'user', None)
    return None


class CurrentRequestMiddleware:
    """
    Middleware que guarda el request en thread local
    para acceder desde signals y otros lugares
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        _thread_locals.request = request
        response = self.get_response(request)
        return response


class SecurityHeadersMiddleware:
    """
    Middleware que añade headers de seguridad adicionales (CSP, etc.)
    Solo activo cuando CSP_ENABLED=True en settings.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Solo añadir CSP si está habilitado
        if getattr(settings, 'CSP_ENABLED', False):
            csp_parts = [
                "default-src " + getattr(settings, 'CSP_DEFAULT_SRC', "'self'"),
                "script-src " + getattr(settings, 'CSP_SCRIPT_SRC', "'self'"),
                "style-src " + getattr(settings, 'CSP_STYLE_SRC', "'self' 'unsafe-inline'"),
                "img-src " + getattr(settings, 'CSP_IMG_SRC', "'self' data: blob:"),
                "font-src " + getattr(settings, 'CSP_FONT_SRC', "'self'"),
                "connect-src " + getattr(settings, 'CSP_CONNECT_SRC', "'self'"),
                "frame-ancestors " + getattr(settings, 'CSP_FRAME_ANCESTORS', "'none'"),
            ]
            response['Content-Security-Policy'] = '; '.join(csp_parts)
        
        # Permissions-Policy (antes Feature-Policy)
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        return response


class RateLimitMiddleware:
    """
    Middleware de Rate Limiting para proteger contra ataques de fuerza bruta.
    
    Configuración en settings.py:
        RATE_LIMIT_ENABLED = True  # Activar/desactivar
        RATE_LIMIT_REQUESTS = 100  # Requests por ventana
        RATE_LIMIT_WINDOW = 60     # Ventana en segundos
        RATE_LIMIT_LOGIN_REQUESTS = 5   # Límite especial para login
        RATE_LIMIT_LOGIN_WINDOW = 300   # Ventana para login (5 min)
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Almacenamiento en memoria simple (en producción usar Redis/Memcached)
        self._request_counts = {}
    
    def __call__(self, request):
        if not getattr(settings, 'RATE_LIMIT_ENABLED', False):
            return self.get_response(request)
        
        # Obtener IP del cliente
        client_ip = self._get_client_ip(request)
        path = request.path
        
        # Verificar rate limit
        is_blocked, retry_after = self._check_rate_limit(client_ip, path)
        
        if is_blocked:
            from django.http import JsonResponse
            return JsonResponse(
                {
                    'error': 'Demasiadas solicitudes. Por favor, espera antes de intentar de nuevo.',
                    'retry_after': retry_after
                },
                status=429
            )
        
        response = self.get_response(request)
        return response
    
    def _get_client_ip(self, request):
        """Obtiene la IP real del cliente considerando proxies"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip
    
    def _check_rate_limit(self, client_ip, path):
        """
        Verifica si el cliente ha excedido el límite.
        Retorna (is_blocked, retry_after_seconds)
        """
        import time
        
        now = time.time()
        
        # Configuración diferente para endpoints de auth
        is_auth_endpoint = '/auth/' in path or '/token/' in path or '/login/' in path
        
        if is_auth_endpoint:
            max_requests = getattr(settings, 'RATE_LIMIT_LOGIN_REQUESTS', 5)
            window = getattr(settings, 'RATE_LIMIT_LOGIN_WINDOW', 300)
            key = f"auth:{client_ip}"
        else:
            max_requests = getattr(settings, 'RATE_LIMIT_REQUESTS', 100)
            window = getattr(settings, 'RATE_LIMIT_WINDOW', 60)
            key = f"api:{client_ip}"
        
        # Limpiar entradas antiguas
        self._cleanup_old_entries(now, window)
        
        # Obtener o crear registro
        if key not in self._request_counts:
            self._request_counts[key] = {'count': 0, 'window_start': now}
        
        record = self._request_counts[key]
        
        # Si la ventana expiró, reiniciar
        if now - record['window_start'] > window:
            record['count'] = 0
            record['window_start'] = now
        
        # Incrementar contador
        record['count'] += 1
        
        # Verificar límite
        if record['count'] > max_requests:
            retry_after = int(window - (now - record['window_start']))
            return True, max(1, retry_after)
        
        return False, 0
    
    def _cleanup_old_entries(self, now, window):
        """Limpia entradas antiguas para evitar memory leak"""
        # Cada 100 requests, limpiar
        if len(self._request_counts) > 1000:
            expired_keys = [
                k for k, v in self._request_counts.items()
                if now - v['window_start'] > window * 2
            ]
            for k in expired_keys:
                del self._request_counts[k]


class PdfInlineMiddleware:
    """
    Middleware que convierte Content-Disposition de 'attachment' a 'inline' para
    respuestas PDF, permitiendo que el navegador las abra en su visor nativo
    en lugar de forzar la descarga automática.

    También añade headers de seguridad y caché apropiados para PDFs:
    - Content-Length (si no está presente)
    - Cache-Control: no-store (datos sensibles)
    - X-Content-Type-Options: nosniff

    El usuario conserva la posibilidad de descargar o imprimir desde el visor.
    """

    _ATTACHMENT_RE = re.compile(r'\battachment\b', re.IGNORECASE)

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        content_type = response.get('Content-Type', '')
        if 'application/pdf' not in content_type:
            return response

        # Content-Disposition: attachment → inline
        disposition = response.get('Content-Disposition', '')
        if disposition and 'attachment' in disposition.lower():
            response['Content-Disposition'] = self._ATTACHMENT_RE.sub('inline', disposition)

        # Content-Length (si no está presente y el contenido es accesible)
        if not response.get('Content-Length'):
            try:
                if hasattr(response, 'content'):
                    response['Content-Length'] = str(len(response.content))
            except Exception:
                pass  # FileResponse streaming — Content-Length lo pone Django

        # Seguridad / caché para PDFs con datos sensibles
        if not response.get('Cache-Control'):
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
        response['X-Content-Type-Options'] = 'nosniff'

        return response


# ============================================================================
# MIDDLEWARE DE AUDITORÍA COMPLETA PARA SUPER ADMIN
# ============================================================================

import uuid
import json
import logging

audit_logger = logging.getLogger('audit')


class AuditMiddleware:
    """
    Middleware de auditoría completa para el panel SUPER ADMIN.
    
    Registra automáticamente todas las operaciones de escritura (POST, PUT, PATCH, DELETE)
    en los endpoints de la API, con trazabilidad completa:
    
    - Quién: usuario_id, rol, centro_id (al momento de la acción)
    - Qué: acción/método, modelo/módulo afectado
    - A qué: entidad (tipo + id)
    - Cuándo: timestamp
    - Resultado: success/fail + status_code
    - Contexto: ip, user_agent, endpoint, request_id, idempotency_key
    - Before/After: datos_anteriores/datos_nuevos (cuando aplica)
    
    Configuración en settings.py:
        AUDIT_ENABLED = True                    # Activar/desactivar
        AUDIT_LOG_READS = False                 # También loguear GETs (no recomendado)
        AUDIT_EXCLUDE_PATHS = ['/health/', '/metrics/']  # Paths a excluir
        AUDIT_SENSITIVE_FIELDS = ['password', 'token']   # Campos a redactar
    """
    
    # Métodos HTTP que generan cambios (auditables por defecto)
    WRITE_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}
    
    # Patrones de URL a excluir de auditoría
    DEFAULT_EXCLUDE_PATTERNS = [
        '/api/auth/token/refresh/',
        '/api/health/',
        '/api/metrics/',
        '/media/',
        '/static/',
        '/favicon.ico',
        '/__debug__/',
    ]
    
    # Campos sensibles a redactar
    SENSITIVE_FIELDS = {
        'password', 'token', 'secret', 'api_key', 'access_token', 
        'refresh_token', 'private_key', 'credential', 'authorization',
        'cookie', 'session', 'csrf',
    }
    
    # Mapeo de endpoints a módulos para auditoría
    MODULE_MAP = {
        '/api/productos/': 'PRODUCTOS',
        '/api/lotes/': 'LOTES',
        '/api/requisiciones/': 'REQUISICIONES',
        '/api/movimientos/': 'MOVIMIENTOS',
        '/api/donaciones/': 'DONACIONES',
        '/api/pacientes/': 'PACIENTES',
        '/api/dispensaciones/': 'DISPENSACIONES',
        '/api/compras-caja-chica/': 'CAJA_CHICA',
        '/api/centros/': 'CENTROS',
        '/api/usuarios/': 'USUARIOS',
        '/api/configuracion/': 'CONFIGURACION',
        '/api/auth/': 'AUTH',
        '/api/notificaciones/': 'NOTIFICACIONES',
        '/api/tema-global/': 'TEMA',
        '/api/importar/': 'IMPORTACION',
        '/api/exportar/': 'EXPORTACION',
        '/api/reportes/': 'REPORTES',
    }
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.audit_enabled = getattr(settings, 'AUDIT_ENABLED', True)
        self.log_reads = getattr(settings, 'AUDIT_LOG_READS', False)
        self.exclude_patterns = getattr(
            settings, 
            'AUDIT_EXCLUDE_PATHS', 
            self.DEFAULT_EXCLUDE_PATTERNS
        )
    
    def __call__(self, request):
        # Skip si auditoría deshabilitada
        if not self.audit_enabled:
            return self.get_response(request)
        
        # Skip rutas excluidas
        if self._should_skip(request):
            return self.get_response(request)
        
        # Skip GETs si no está habilitado log_reads
        if request.method == 'GET' and not self.log_reads:
            return self.get_response(request)
        
        # Generar request_id si no existe
        request_id = request.META.get('HTTP_X_REQUEST_ID')
        if not request_id:
            request_id = str(uuid.uuid4())
            request.META['HTTP_X_REQUEST_ID'] = request_id
        
        # Guardar el request_id en thread local para acceso en signals
        _thread_locals.request_id = request_id
        
        # Obtener idempotency_key si existe
        idempotency_key = request.META.get('HTTP_X_IDEMPOTENCY_KEY')
        
        # Capturar body antes de procesar (para before/after)
        request_body = self._get_request_body(request)
        
        # Procesar request
        response = self.get_response(request)
        
        # Registrar auditoría después de procesar
        try:
            self._log_audit(request, response, request_body, request_id, idempotency_key)
        except Exception as e:
            # No fallar por errores de auditoría
            audit_logger.error(f"Error en middleware de auditoría: {e}")
        
        # Agregar request_id a headers de respuesta
        response['X-Request-ID'] = request_id
        
        return response
    
    def _should_skip(self, request) -> bool:
        """Verifica si el request debe ser excluido de auditoría."""
        path = request.path
        
        # Verificar patrones de exclusión
        for pattern in self.exclude_patterns:
            if path.startswith(pattern):
                return True
        
        # Solo auditar endpoints de API
        if not path.startswith('/api/'):
            return True
        
        return False
    
    def _get_request_body(self, request) -> dict:
        """Extrae y sanitiza el body del request."""
        try:
            if request.content_type == 'application/json':
                body = json.loads(request.body.decode('utf-8')) if request.body else {}
                return self._sanitize_data(body)
            return {}
        except Exception:
            return {}
    
    def _sanitize_data(self, data) -> dict:
        """Elimina datos sensibles del log."""
        if not isinstance(data, dict):
            return data
        
        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(s in key_lower for s in self.SENSITIVE_FIELDS):
                sanitized[key] = '***REDACTED***'
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_data(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _get_module(self, path: str) -> str:
        """Obtiene el módulo basado en el path."""
        for pattern, module in self.MODULE_MAP.items():
            if path.startswith(pattern):
                return module
        return 'OTRO'
    
    def _get_action(self, method: str, path: str) -> str:
        """Determina la acción basada en método y path."""
        # Mapeo de métodos a acciones
        method_actions = {
            'POST': 'CREAR',
            'PUT': 'ACTUALIZAR',
            'PATCH': 'MODIFICAR',
            'DELETE': 'ELIMINAR',
            'GET': 'CONSULTAR',
        }
        
        action = method_actions.get(method, method)
        
        # Detectar acciones especiales por path
        path_lower = path.lower()
        if '/aprobar/' in path_lower or '/autorizar/' in path_lower:
            action = 'APROBAR'
        elif '/rechazar/' in path_lower:
            action = 'RECHAZAR'
        elif '/cancelar/' in path_lower:
            action = 'CANCELAR'
        elif '/recibir/' in path_lower or '/recepcion/' in path_lower:
            action = 'RECIBIR'
        elif '/surtir/' in path_lower or '/despachar/' in path_lower:
            action = 'SURTIR'
        elif '/enviar/' in path_lower:
            action = 'ENVIAR'
        elif '/importar/' in path_lower:
            action = 'IMPORTAR'
        elif '/exportar/' in path_lower:
            action = 'EXPORTAR'
        elif '/login/' in path_lower or '/token/' in path_lower:
            if method == 'POST':
                action = 'LOGIN'
        elif '/logout/' in path_lower:
            action = 'LOGOUT'
        elif '/password/' in path_lower or '/reset/' in path_lower:
            action = 'CAMBIO_PASSWORD'
        
        return action
    
    def _extract_object_id(self, path: str) -> str:
        """Extrae el ID del objeto del path si existe."""
        import re
        # Buscar patrones como /api/productos/123/ o /api/requisiciones/REQ-001/
        match = re.search(r'/api/\w+/([^/]+)/?$', path)
        if match:
            obj_id = match.group(1)
            # No devolver si es una acción como 'exportar', 'importar', etc.
            if not obj_id.startswith(('exportar', 'importar', 'bulk', 'stats', 'me')):
                return obj_id[:50]  # Limitar a 50 chars como en BD
        return None
    
    def _get_result(self, status_code: int) -> str:
        """Determina el resultado basado en el status code."""
        if 200 <= status_code < 300:
            return 'success'
        elif 400 <= status_code < 500:
            return 'fail'
        elif status_code >= 500:
            return 'error'
        else:
            return 'warning'
    
    def _get_client_ip(self, request) -> str:
        """Obtiene la IP real del cliente."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()[:45]
        return request.META.get('REMOTE_ADDR', '')[:45]
    
    def _log_audit(
        self, 
        request, 
        response, 
        request_body: dict,
        request_id: str,
        idempotency_key: str = None
    ):
        """Registra el evento de auditoría en la base de datos."""
        from .models import AuditoriaLogs
        
        user = getattr(request, 'user', None)
        
        # Determinar información del usuario
        usuario_id = None
        rol_usuario = None
        centro_id = None
        
        if user and user.is_authenticated:
            usuario_id = user.id
            rol_usuario = getattr(user, 'rol', None) or ('admin' if user.is_superuser else None)
            centro = getattr(user, 'centro', None)
            centro_id = centro.id if centro else None
        
        # Construir datos del evento
        path = request.path
        method = request.method
        status_code = response.status_code
        
        # Extraer response data para datos_nuevos (solo en creación/actualización exitosa)
        datos_nuevos = None
        if status_code in (200, 201) and hasattr(response, 'data'):
            try:
                response_data = response.data
                if isinstance(response_data, dict):
                    datos_nuevos = self._sanitize_data(response_data)
            except Exception:
                pass
        
        # Construir detalles
        detalles = {
            'path_completo': path,
            'query_params': dict(request.GET) if request.GET else None,
            'content_type': request.content_type,
            'response_size': len(response.content) if hasattr(response, 'content') else None,
        }
        
        # Filtrar None values
        detalles = {k: v for k, v in detalles.items() if v is not None}
        
        try:
            AuditoriaLogs.objects.create(
                usuario_id=usuario_id,
                accion=self._get_action(method, path),
                modelo=self._get_module(path),
                objeto_id=self._extract_object_id(path),
                datos_anteriores=request_body if method in ('PUT', 'PATCH', 'DELETE') else None,
                datos_nuevos=datos_nuevos,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                detalles=detalles,
                # Campos nuevos (requieren migración SQL)
                resultado=self._get_result(status_code),
                status_code=status_code,
                endpoint=path[:255],
                request_id=request_id[:100] if request_id else None,
                idempotency_key=idempotency_key[:255] if idempotency_key else None,
                rol_usuario=rol_usuario[:50] if rol_usuario else None,
                centro_id=centro_id,
                metodo_http=method[:10],
            )
        except Exception as e:
            # Fallback: intentar sin campos nuevos si la migración no se ha ejecutado
            audit_logger.warning(f"Auditoría con campos nuevos falló, usando fallback: {e}")
            try:
                AuditoriaLogs.objects.create(
                    usuario_id=usuario_id,
                    accion=self._get_action(method, path),
                    modelo=self._get_module(path),
                    objeto_id=self._extract_object_id(path),
                    datos_anteriores=request_body if method in ('PUT', 'PATCH', 'DELETE') else None,
                    datos_nuevos=datos_nuevos,
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                    detalles={
                        **detalles,
                        'resultado': self._get_result(status_code),
                        'status_code': status_code,
                        'request_id': request_id,
                        'idempotency_key': idempotency_key,
                        'rol_usuario': rol_usuario,
                        'centro_id': centro_id,
                        'metodo_http': method,
                    },
                )
            except Exception as e2:
                audit_logger.error(f"Error crítico en auditoría (fallback): {e2}")
