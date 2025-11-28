"""
Middleware para capturar IP y User-Agent en auditoría
"""
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
