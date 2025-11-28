"""
Health check endpoint para monitoreo de producción.
"""
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
import time


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Endpoint de health check para monitoring y load balancers.
    
    Verifica:
    - Estado de la base de datos
    - Estado del cache
    - Tiempo de respuesta
    
    Retorna 200 si todo está OK, 503 si hay problemas.
    """
    start_time = time.time()
    status = {
        'status': 'healthy',
        'timestamp': int(time.time()),
        'checks': {}
    }
    
    http_status = 200
    
    # Check base de datos
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        status['checks']['database'] = 'OK'
    except Exception as e:
        status['checks']['database'] = f'ERROR: {str(e)}'
        status['status'] = 'unhealthy'
        http_status = 503
    
    # Check cache
    try:
        cache_key = 'health_check_test'
        cache.set(cache_key, 'test', 10)
        value = cache.get(cache_key)
        if value == 'test':
            status['checks']['cache'] = 'OK'
        else:
            status['checks']['cache'] = 'ERROR: Cache not working'
            status['status'] = 'degraded'
    except Exception as e:
        status['checks']['cache'] = f'ERROR: {str(e)}'
        # Cache no es crítico, no cambiar status a unhealthy
        status['checks']['cache_note'] = 'Cache is optional'
    
    # Tiempo de respuesta
    response_time = (time.time() - start_time) * 1000  # en ms
    status['response_time_ms'] = round(response_time, 2)
    
    if response_time > 1000:  # > 1 segundo
        status['status'] = 'slow'
        status['warning'] = 'Response time is high'
    
    return JsonResponse(status, status=http_status)


@api_view(['GET'])
@permission_classes([AllowAny])
def readiness_check(request):
    """
    Readiness check - verifica si la aplicación está lista para recibir tráfico.
    """
    try:
        # Verificar que podemos hacer queries a la BD
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM django_migrations")
            count = cursor.fetchone()[0]
            
        if count == 0:
            return JsonResponse({
                'ready': False,
                'reason': 'No migrations applied'
            }, status=503)
        
        return JsonResponse({
            'ready': True,
            'migrations_count': count
        })
    except Exception as e:
        return JsonResponse({
            'ready': False,
            'reason': str(e)
        }, status=503)


@api_view(['GET'])
@permission_classes([AllowAny])
def liveness_check(request):
    """
    Liveness check - verifica si la aplicación está viva (puede ser simple).
    """
    return JsonResponse({'alive': True})
