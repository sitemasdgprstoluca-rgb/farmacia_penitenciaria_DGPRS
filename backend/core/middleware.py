"""
Middleware para capturar IP y User-Agent en auditoría
"""
import threading

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
