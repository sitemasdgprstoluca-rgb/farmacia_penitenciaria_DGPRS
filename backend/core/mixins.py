# -*- coding: utf-8 -*-
"""
Módulo de mixins para confirmación en 2 pasos.

ISS-SEC: Proporciona validación de confirmación obligatoria para
operaciones destructivas (DELETE) y opcionalmente para operaciones
críticas de guardado (PUT/PATCH).

El frontend debe enviar el parámetro 'confirmed=true' para que la
acción se ejecute. Sin este parámetro, el backend responde 400/409.

Uso:
    from core.mixins import ConfirmationRequiredMixin
    
    class MiViewSet(ConfirmationRequiredMixin, viewsets.ModelViewSet):
        # Para eliminar, el frontend debe enviar ?confirmed=true
        require_delete_confirmation = True
        # Opcional: también requerir para actualizaciones críticas
        require_update_confirmation = False
"""
import logging
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


class ConfirmationRequiredMixin:
    """
    Mixin que requiere confirmación explícita para operaciones destructivas.
    
    Configuración en la clase que lo hereda:
    - require_delete_confirmation: bool (default: True)
    - require_update_confirmation: bool (default: False)
    - confirmation_param: str (default: 'confirmed')
    - confirmation_header: str (default: 'X-Confirm-Action')
    
    El cliente puede enviar la confirmación de dos formas:
    1. Query parameter: ?confirmed=true
    2. Header HTTP: X-Confirm-Action: true
    
    Respuestas de error:
    - 409 Conflict: Si falta la confirmación
    - Incluye instrucciones para el frontend
    """
    
    # Configuración por defecto
    require_delete_confirmation = True
    require_update_confirmation = False
    confirmation_param = 'confirmed'
    confirmation_header = 'X-Confirm-Action'
    
    def _is_confirmation_valid(self, request):
        """
        Verifica si la confirmación está presente y es válida.
        
        La confirmación puede venir como:
        - Query parameter: ?confirmed=true
        - Header HTTP: X-Confirm-Action: true
        - Body JSON: { "confirmed": true }
        
        Returns:
            bool: True si la confirmación es válida
        """
        # Verificar query parameter
        param_value = request.query_params.get(self.confirmation_param, '')
        if param_value.lower() in ('true', '1', 'yes', 'si'):
            return True
        
        # Verificar header HTTP
        header_value = request.headers.get(self.confirmation_header, '')
        if header_value.lower() in ('true', '1', 'yes', 'si'):
            return True
        
        # Verificar body (para PUT/PATCH con JSON)
        if hasattr(request, 'data') and isinstance(request.data, dict):
            body_value = request.data.get(self.confirmation_param, False)
            if body_value in (True, 'true', '1', 'yes', 'si'):
                return True
        
        return False
    
    def _get_confirmation_error_response(self, action_type='delete', instance=None):
        """
        Genera respuesta de error cuando falta la confirmación.
        
        Args:
            action_type: 'delete' o 'update'
            instance: Instancia del objeto (opcional, para info adicional)
        
        Returns:
            Response: Respuesta 409 con instrucciones
        """
        action_verb = 'eliminar' if action_type == 'delete' else 'actualizar'
        
        response_data = {
            'error': 'Confirmación requerida',
            'code': 'CONFIRMATION_REQUIRED',
            'message': f'Esta acción requiere confirmación explícita para {action_verb}.',
            'action_type': action_type,
            'instructions': {
                'query_param': f'Añada ?{self.confirmation_param}=true a la URL',
                'header': f'Añada el header {self.confirmation_header}: true',
                'body': f'Incluya "{self.confirmation_param}": true en el body JSON',
            },
        }
        
        # Añadir info del objeto si está disponible
        if instance:
            response_data['item'] = {
                'id': getattr(instance, 'pk', None),
                'str': str(instance)[:100],  # Limitar longitud
            }
        
        logger.info(
            f"ISS-SEC: Confirmación requerida para {action_type}. "
            f"Objeto: {instance}, User: {getattr(self, 'request', {}).user if hasattr(self, 'request') else 'N/A'}"
        )
        
        return Response(response_data, status=status.HTTP_409_CONFLICT)
    
    def destroy(self, request, *args, **kwargs):
        """
        Override de destroy para requerir confirmación.
        
        Si require_delete_confirmation es True y no hay confirmación,
        retorna 409 Conflict con instrucciones.
        """
        if self.require_delete_confirmation:
            if not self._is_confirmation_valid(request):
                # Obtener instancia para incluir en el mensaje
                try:
                    instance = self.get_object()
                except Exception:
                    instance = None
                
                return self._get_confirmation_error_response('delete', instance)
        
        # Confirmación válida, continuar con eliminación normal
        return super().destroy(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """
        Override de update para requerir confirmación (opcional).
        
        Si require_update_confirmation es True y no hay confirmación,
        retorna 409 Conflict con instrucciones.
        """
        if self.require_update_confirmation:
            if not self._is_confirmation_valid(request):
                try:
                    instance = self.get_object()
                except Exception:
                    instance = None
                
                return self._get_confirmation_error_response('update', instance)
        
        return super().update(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        """
        Override de partial_update para requerir confirmación (opcional).
        
        Sigue la misma lógica que update si require_update_confirmation es True.
        """
        if self.require_update_confirmation:
            if not self._is_confirmation_valid(request):
                try:
                    instance = self.get_object()
                except Exception:
                    instance = None
                
                return self._get_confirmation_error_response('update', instance)
        
        return super().partial_update(request, *args, **kwargs)


class CriticalActionMixin(ConfirmationRequiredMixin):
    """
    Versión más estricta que requiere confirmación para TODAS las
    operaciones de escritura (create, update, delete).
    
    Usar para recursos extremadamente sensibles.
    """
    require_delete_confirmation = True
    require_update_confirmation = True
    require_create_confirmation = True
    
    def create(self, request, *args, **kwargs):
        """
        Override de create para requerir confirmación.
        """
        if getattr(self, 'require_create_confirmation', False):
            if not self._is_confirmation_valid(request):
                return self._get_confirmation_error_response('create', None)
        
        return super().create(request, *args, **kwargs)


# Decorator alternativo para acciones específicas
def require_confirmation(action_type='delete'):
    """
    Decorator para requerir confirmación en una acción específica.
    
    Uso:
        @action(detail=True, methods=['delete'])
        @require_confirmation('delete')
        def mi_accion_destructiva(self, request, pk=None):
            # Esta acción requiere ?confirmed=true
            pass
    
    Args:
        action_type: 'delete', 'update', o 'create'
    """
    def decorator(func):
        def wrapper(self, request, *args, **kwargs):
            # Usar la lógica del mixin
            mixin = ConfirmationRequiredMixin()
            mixin.request = request
            
            if not mixin._is_confirmation_valid(request):
                return mixin._get_confirmation_error_response(action_type)
            
            return func(self, request, *args, **kwargs)
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator
