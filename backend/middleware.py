# filepath: backend/middleware.py
from django.shortcuts import redirect
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)


class CORSErrorHandlingMiddleware:
    """
    ISS-FIX: Middleware para asegurar que los headers CORS se envíen
    incluso cuando hay errores 500. Sin esto, el navegador bloquea
    la respuesta de error y el frontend ve "CORS error" en lugar del error real.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        return response
    
    def process_exception(self, request, exception):
        """
        Captura excepciones no manejadas y devuelve una respuesta JSON
        con headers CORS apropiados.
        """
        from django.conf import settings
        
        # Solo manejar requests de API
        if not request.path.startswith('/api/'):
            return None
        
        # Log del error
        logger.error(
            f"Excepción no manejada en {request.method} {request.path}: {exception}",
            exc_info=True
        )
        
        # Crear respuesta de error
        error_response = JsonResponse(
            {
                'error': 'Error interno del servidor',
                'detail': str(exception) if settings.DEBUG else 'Contacte al administrador'
            },
            status=500
        )
        
        # Agregar headers CORS manualmente
        origin = request.META.get('HTTP_ORIGIN', '')
        allowed_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
        
        if origin in allowed_origins or '*' in allowed_origins:
            error_response['Access-Control-Allow-Origin'] = origin
            error_response['Access-Control-Allow-Credentials'] = 'true'
        
        return error_response


class RedirectNonSuperuserFromAdminMiddleware:
    """
    - Si es usuario autenticado NO superusuario y entra a /admin/,
      lo mandamos al front (post_login).
    - PERO dejamos pasar /admin/logout/ para que sí pueda cerrar sesión.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        if path.startswith("/admin/"):
            # 👇 SIEMPRE permitir el logout
            if path.startswith("/admin/logout"):
                return self.get_response(request)

            user = request.user

            # Usuario logueado y NO superusuario -> fuera del admin
            if user.is_authenticated and not user.is_superuser:
                return redirect("post_login")

        return self.get_response(request)
