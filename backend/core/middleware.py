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
