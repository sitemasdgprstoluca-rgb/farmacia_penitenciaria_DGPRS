"""
Exception handlers personalizados para respuestas consistentes.

Maneja excepciones de Django, DRF y Python nativas para retornar
respuestas JSON consistentes en lugar de errores 500.
"""
from rest_framework.views import exception_handler
from rest_framework.exceptions import (
    ValidationError, 
    PermissionDenied, 
    NotFound,
    NotAuthenticated,
    AuthenticationFailed,
)
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied as DjangoPermissionDenied
from django.db import IntegrityError, DatabaseError
from django.http import Http404
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Handler personalizado para manejar todas las excepciones.
    
    Convierte excepciones de Django/Python a respuestas HTTP apropiadas:
    - ObjectDoesNotExist, Http404 → 404 Not Found
    - ValueError, TypeError → 400 Bad Request  
    - IntegrityError → 409 Conflict
    - PermissionDenied → 403 Forbidden
    - Otras excepciones no manejadas → 500 Internal Server Error
    
    Retorna respuestas en formato JSON consistente.
    """
    # Obtener información del request para logging
    request = context.get('request')
    view = context.get('view')
    user_info = str(request.user) if request else 'Anónimo'
    view_info = view.__class__.__name__ if view else 'Unknown'
    
    # ═══════════════════════════════════════════════════════════════
    # PASO 1: Convertir excepciones de Django/Python a excepciones DRF
    # ═══════════════════════════════════════════════════════════════
    
    # ObjectDoesNotExist (Model.DoesNotExist) → 404
    if isinstance(exc, ObjectDoesNotExist):
        logger.warning(f"ObjectDoesNotExist en {view_info}: {exc}")
        return Response({
            'error': True,
            'status_code': 404,
            'message': 'Recurso no encontrado',
            'detail': str(exc) or 'El objeto solicitado no existe.',
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Http404 → 404
    if isinstance(exc, Http404):
        logger.warning(f"Http404 en {view_info}: {exc}")
        return Response({
            'error': True,
            'status_code': 404,
            'message': 'Recurso no encontrado',
            'detail': str(exc) or 'La página solicitada no existe.',
        }, status=status.HTTP_404_NOT_FOUND)
    
    # ValueError, TypeError → 400 Bad Request
    if isinstance(exc, (ValueError, TypeError)):
        logger.warning(f"{exc.__class__.__name__} en {view_info}: {exc}")
        return Response({
            'error': True,
            'status_code': 400,
            'message': 'Datos inválidos',
            'detail': str(exc),
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # IntegrityError (duplicados, FK violations) → 409 Conflict
    if isinstance(exc, IntegrityError):
        logger.error(f"IntegrityError en {view_info}: {exc}")
        # Intentar dar un mensaje más amigable
        error_msg = str(exc)
        if 'UNIQUE constraint' in error_msg or 'duplicate key' in error_msg.lower():
            detail = 'Ya existe un registro con estos datos.'
        elif 'FOREIGN KEY' in error_msg or 'foreign key' in error_msg.lower():
            detail = 'No se puede completar la operación: referencia a datos inexistentes.'
        elif 'NOT NULL' in error_msg:
            detail = 'Faltan campos obligatorios.'
        else:
            detail = 'Error de integridad de datos.'
        
        return Response({
            'error': True,
            'status_code': 409,
            'message': 'Conflicto de datos',
            'detail': detail,
        }, status=status.HTTP_409_CONFLICT)
    
    # DatabaseError genérico → 500 pero con mensaje controlado
    if isinstance(exc, DatabaseError):
        logger.error(f"DatabaseError en {view_info}: {exc}", exc_info=True)
        return Response({
            'error': True,
            'status_code': 500,
            'message': 'Error de base de datos',
            'detail': 'Ocurrió un error al acceder a la base de datos. Intente nuevamente.',
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Django PermissionDenied → 403
    if isinstance(exc, DjangoPermissionDenied):
        logger.warning(f"PermissionDenied en {view_info} por {user_info}: {exc}")
        return Response({
            'error': True,
            'status_code': 403,
            'message': 'Permiso denegado',
            'detail': str(exc) or 'No tiene permisos para realizar esta acción.',
        }, status=status.HTTP_403_FORBIDDEN)
    
    # ═══════════════════════════════════════════════════════════════
    # PASO 2: Llamar al handler por defecto de DRF
    # ═══════════════════════════════════════════════════════════════
    response = exception_handler(exc, context)
    
    # Si el handler por defecto no manejó la excepción → 500 genérico
    if response is None:
        logger.error(
            f"Excepción no manejada en {view_info}: {exc.__class__.__name__} - {exc}",
            exc_info=True
        )
        return Response({
            'error': True,
            'status_code': 500,
            'message': 'Error interno del servidor',
            'detail': 'Ocurrió un error inesperado. Contacte al administrador si persiste.',
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # ═══════════════════════════════════════════════════════════════
    # PASO 3: Personalizar respuesta según el tipo de error DRF
    # ═══════════════════════════════════════════════════════════════
    custom_response = {
        'error': True,
        'status_code': response.status_code,
    }
    
    # ValidationError (400)
    if isinstance(exc, ValidationError):
        custom_response['message'] = 'Error de validación'
        custom_response['errors'] = response.data
    
    # PermissionDenied (403)
    elif isinstance(exc, PermissionDenied):
        custom_response['message'] = 'Permiso denegado'
        custom_response['detail'] = str(exc.detail) if hasattr(exc, 'detail') else str(exc)
    
    # NotAuthenticated (401)
    elif isinstance(exc, NotAuthenticated):
        custom_response['message'] = 'Autenticación requerida'
        custom_response['detail'] = 'Debe iniciar sesión para acceder a este recurso.'
    
    # AuthenticationFailed (401)
    elif isinstance(exc, AuthenticationFailed):
        custom_response['message'] = 'Error de autenticación'
        custom_response['detail'] = str(exc.detail) if hasattr(exc, 'detail') else 'Credenciales inválidas.'
    
    # NotFound (404)
    elif isinstance(exc, NotFound):
        custom_response['message'] = 'Recurso no encontrado'
        custom_response['detail'] = str(exc.detail) if hasattr(exc, 'detail') else str(exc)
    
    # Otros errores DRF
    else:
        if isinstance(response.data, dict):
            custom_response['message'] = response.data.get('detail', 'Error en la solicitud')
            custom_response['errors'] = response.data
        else:
            custom_response['message'] = 'Error en la solicitud'
            custom_response['errors'] = response.data
    
    # Log para depuración
    log_level = logging.WARNING if response.status_code < 500 else logging.ERROR
    logger.log(
        log_level,
        f"{exc.__class__.__name__} en {view_info} - "
        f"Status: {response.status_code} - Usuario: {user_info}"
    )
    
    return Response(custom_response, status=response.status_code)
