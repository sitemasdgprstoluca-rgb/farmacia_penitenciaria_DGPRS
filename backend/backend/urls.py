from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def root_status(request):
    """Respuesta sencilla para la ruta raíz en producción."""
    return JsonResponse({
        'service': 'Farmacia Penitenciaria API',
        'status': 'ok'
    })


def health_check(request):
    return JsonResponse({
        'status': 'ok',
        'message': 'Backend funcionando correctamente',
        'database': 'connected'
    })


urlpatterns = [
    path('', root_status, name='api-root'),
    path('admin/', admin.site.urls),
    path('api/v1/', include('config.api_urls')),
    path('api/', include('config.api_urls')),
    path('api/', include('inventario.urls')),
    path('api/', include('farmacia.urls')),
    path('health/', health_check),
]
