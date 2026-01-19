from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from core.health import health_check, readiness_check, liveness_check


def api_root(request):
    """Endpoint raíz con información de la API."""
    return JsonResponse({
        'name': 'Farmacia Penitenciaria API',
        'version': '1.0.0',
        'status': 'online',
        'endpoints': {
            'health': '/health/',
            'api': '/api/',
            'docs': '/api/docs/',
            'schema': '/api/schema/',
        }
    })


urlpatterns = [
    # Raíz - Info de la API
    path('', api_root, name='api-root'),
    
    # Health checks (sin autenticación para load balancers)
    # Disponible en raíz Y bajo /api/ para compatibilidad con frontend
    path('health/', health_check, name='health'),
    path('ready/', readiness_check, name='readiness'),
    path('alive/', liveness_check, name='liveness'),
    path('api/health/', health_check, name='api-health'),
    path('api/ready/', readiness_check, name='api-readiness'),
    path('api/alive/', liveness_check, name='api-liveness'),
    
    # Admin
    path('admin/', admin.site.urls),
    
    # API - Versión principal (usar esta)
    path('api/', include('config.api_urls')),
    # API v1 - DEPRECATED: Mantener por compatibilidad, migrar frontend a /api/
    # En producción, considerar remover esta ruta después de migración
    path('api/v1/', include('config.api_urls')),
    
    # Documentación API
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Media files
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
