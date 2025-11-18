"""
Exception handlers personalizados para respuestas consistentes
"""
from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Handler personalizado para manejar todas las excepciones
    Retorna respuestas en formato JSON consistente
    """
    # Llamar al handler por defecto primero
    response = exception_handler(exc, context)
    
    # Si el handler por defecto no manejó la excepción
    if response is None:
        logger.error(f"Excepción no manejada: {str(exc)}")
        return Response({
            'error': 'Error interno del servidor',
            'detail': str(exc)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Personalizar respuesta según el tipo de error
    custom_response = {
        'error': True,
        'status_code': response.status_code,
    }
    
    # Manejar ValidationError
    if isinstance(exc, ValidationError):
        custom_response['message'] = 'Error de validación'
        custom_response['errors'] = response.data
    
    # Manejar PermissionDenied
    elif isinstance(exc, PermissionDenied):
        custom_response['message'] = 'Permiso denegado'
        custom_response['detail'] = str(exc)
    
    # Manejar NotFound
    elif isinstance(exc, NotFound):
        custom_response['message'] = 'Recurso no encontrado'
        custom_response['detail'] = str(exc)
    
    # Otros errores
    else:
        custom_response['message'] = response.data.get('detail', 'Error en la solicitud')
        custom_response['errors'] = response.data
    
    logger.warning(
        f"Excepción manejada: {exc.__class__.__name__} - "
        f"Status: {response.status_code} - "
        f"Usuario: {context['request'].user if context.get('request') else 'Anónimo'}"
    )
    
    return Response(custom_response, status=response.status_code)
