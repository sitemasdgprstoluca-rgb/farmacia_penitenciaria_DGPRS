"""
Health check endpoints para load balancers y monitoreo.
"""
from django.http import JsonResponse
from django.db import connection
from django.conf import settings
import time


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
    Incluye verificación de base de datos con diagnóstico detallado.
    """
    start_time = time.time()
    db_info = {}
    
    try:
        # Obtener información de configuración de la BD
        db_config = settings.DATABASES.get('default', {})
        db_info['engine'] = db_config.get('ENGINE', 'unknown')
        db_info['host'] = db_config.get('HOST', 'unknown')[:30] + '...' if db_config.get('HOST', '') else 'localhost'
        
        # Verificar conexión a base de datos
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            result = cursor.fetchone()
        
        elapsed = round((time.time() - start_time) * 1000, 2)
        
        return JsonResponse({
            'status': 'ready',
            'database': 'connected',
            'db_response_ms': elapsed,
            'db_info': db_info
        })
    except Exception as e:
        elapsed = round((time.time() - start_time) * 1000, 2)
        error_type = type(e).__name__
        error_msg = str(e)[:200]  # Limitar mensaje de error
        
        return JsonResponse({
            'status': 'not_ready',
            'database': 'disconnected',
            'error_type': error_type,
            'error': error_msg,
            'elapsed_ms': elapsed,
            'db_info': db_info,
            'hint': 'Verifica que Supabase esté activo y DATABASE_URL sea correcto'
        }, status=503)


def liveness_check(request):
    """
    Liveness check - verifica que el proceso esté vivo.
    Si falla, el orquestador debería reiniciar el contenedor.
    """
    return JsonResponse({
        'status': 'alive'
    })
