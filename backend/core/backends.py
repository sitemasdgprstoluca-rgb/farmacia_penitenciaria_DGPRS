"""
Backend de autenticación personalizado para el sistema.

Implementa autenticación case-insensitive para usernames, evitando
problemas donde el usuario escribe "Centro" pero el username guardado
es "centro".
"""
import logging
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


class CaseInsensitiveModelBackend(ModelBackend):
    """
    Backend de autenticación que hace matching case-insensitive del username.
    
    Esto resuelve el problema donde:
    - Usuario se registra como "centro" (el serializer convierte a minúsculas)
    - Usuario intenta login con "Centro" o "CENTRO"
    - La autenticación falla porque Django compara case-sensitive
    
    Con este backend, cualquier variación de mayúsculas/minúsculas funcionará.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        
        if username is None or password is None:
            return None
        
        # Buscar usuario de forma case-insensitive
        try:
            user = User.objects.get(**{f'{User.USERNAME_FIELD}__iexact': username})
        except User.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user (#20760).
            User().set_password(password)
            logger.warning(f"[AUTH] Login fallido: usuario '{username}' no existe")
            return None
        except User.MultipleObjectsReturned:
            # Esto no debería pasar si el username es único
            logger.error(f"[AUTH] Múltiples usuarios con username similar a '{username}'")
            return None
        
        # Verificar contraseña y que el usuario puede autenticarse
        if user.check_password(password) and self.user_can_authenticate(user):
            logger.info(f"[AUTH] Login exitoso: {user.username}")
            return user
        
        # Log de intento fallido (contraseña incorrecta o usuario inactivo)
        if not user.check_password(password):
            logger.warning(f"[AUTH] Login fallido: contraseña incorrecta para '{username}'")
        elif not user.is_active:
            logger.warning(f"[AUTH] Login fallido: usuario '{username}' está inactivo")
        
        return None
