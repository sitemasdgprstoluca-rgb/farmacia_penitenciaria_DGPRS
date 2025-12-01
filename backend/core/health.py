"""
Health check endpoints para load balancers y monitoreo.
"""
from django.http import JsonResponse
from django.db import connection


def health_check(request):
    """
    Health check básico - verifica que el servidor responda.
    Usado por load balancers para verificar disponibilidad.
    """
    return JsonResponse({
        'status': 'healthy',
        'service': 'farmacia-api'
    })


def readiness_check(request):
    """
    Readiness check - verifica que la aplicación esté lista para recibir tráfico.
    Incluye verificación de base de datos.
    """
    try:
        # Verificar conexión a base de datos
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        
        return JsonResponse({
            'status': 'ready',
            'database': 'connected'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'not_ready',
            'database': 'disconnected',
            'error': str(e)
        }, status=503)


def liveness_check(request):
    """
    Liveness check - verifica que el proceso esté vivo.
    Si falla, el orquestador debería reiniciar el contenedor.
    """
    return JsonResponse({
        'status': 'alive'
    })
