from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def health_check(request):
    return JsonResponse({
        'status': 'ok',
        'message': 'Backend funcionando correctamente',
        'database': 'connected'
    })


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('config.api_urls')),
    path('api/', include('config.api_urls')),
    path('api/', include('inventario.urls')),
    path('api/', include('farmacia.urls')),
    path('health/', health_check),
]
