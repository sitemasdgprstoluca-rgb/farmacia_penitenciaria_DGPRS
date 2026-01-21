"""
Serializers y Views personalizados para JWT con manejo seguro de tokens.

Implementación de seguridad:
- Access Token: Se envía en la respuesta JSON (almacenado en memoria del cliente)
- Refresh Token: Se envía como cookie HttpOnly (no accesible desde JavaScript)

Esto previene ataques XSS ya que el refresh token nunca está expuesto al JavaScript.
"""
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from core.serializers import UserSerializer
from core.views import LoginThrottle
import logging

logger = logging.getLogger(__name__)

# Configuración de cookies seguras
REFRESH_TOKEN_COOKIE_NAME = 'refresh_token'
REFRESH_TOKEN_COOKIE_PATH = '/'  # Cambiado a / para compatibilidad cross-origin
REFRESH_TOKEN_COOKIE_SECURE = not settings.DEBUG  # True en producción (requerido para SameSite=None)
REFRESH_TOKEN_COOKIE_HTTPONLY = True
# SameSite=None permite cookies cross-origin (frontend en diferente dominio)
# En desarrollo usamos Lax para evitar problemas con localhost
REFRESH_TOKEN_COOKIE_SAMESITE = 'None' if not settings.DEBUG else 'Lax'
# Duración del refresh token (7 días por defecto, configurable)
REFRESH_TOKEN_COOKIE_MAX_AGE = settings.SIMPLE_JWT.get('REFRESH_TOKEN_LIFETIME').total_seconds()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Serializer personalizado que incluye datos del usuario en la respuesta"""
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Agregar información del usuario
        serializer = UserSerializer(self.user)
        data['user'] = serializer.data
        
        return data


class SecureTokenObtainPairView(TokenObtainPairView):
    """
    View de login seguro que:
    - Envía access token en JSON (para almacenar en memoria)
    - Envía refresh token como cookie HttpOnly (no accesible desde JS)
    """
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginThrottle]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])
        
        # Obtener tokens y datos del usuario
        data = serializer.validated_data
        access_token = data.pop('access')
        refresh_token = data.pop('refresh')
        user_data = data.get('user', {})
        
        # Crear respuesta con access token y datos del usuario
        # SEGURIDAD: El refresh token SOLO se envía en cookie HttpOnly
        # para prevenir exposición via XSS - nunca en el body JSON
        response_data = {
            'access': access_token,
            'user': user_data,
            'message': 'Login exitoso'
        }
        
        response = Response(response_data, status=status.HTTP_200_OK)
        
        # Configurar refresh token como cookie HttpOnly (respaldo)
        logger.info(f"[LOGIN] Configurando cookie: SameSite={REFRESH_TOKEN_COOKIE_SAMESITE}, Secure={REFRESH_TOKEN_COOKIE_SECURE}, Path={REFRESH_TOKEN_COOKIE_PATH}")
        response.set_cookie(
            key=REFRESH_TOKEN_COOKIE_NAME,
            value=refresh_token,
            max_age=int(REFRESH_TOKEN_COOKIE_MAX_AGE),
            path=REFRESH_TOKEN_COOKIE_PATH,
            secure=REFRESH_TOKEN_COOKIE_SECURE,
            httponly=REFRESH_TOKEN_COOKIE_HTTPONLY,
            samesite=REFRESH_TOKEN_COOKIE_SAMESITE,
        )
        
        logger.info(f"[LOGIN] Login exitoso para usuario: {user_data.get('username', 'unknown')}")
        return response


class SecureTokenRefreshView(APIView):
    """
    View de refresh seguro que:
    - Lee el refresh token desde la cookie HttpOnly
    - Retorna un nuevo access token en JSON
    - Opcionalmente rota el refresh token (nueva cookie)
    """
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        # DEBUG: Log de cookies recibidas
        logger.info(f"[REFRESH] Cookies recibidas: {list(request.COOKIES.keys())}")
        logger.info(f"[REFRESH] Origin: {request.headers.get('Origin', 'N/A')}")
        logger.info(f"[REFRESH] Cookie config: SameSite={REFRESH_TOKEN_COOKIE_SAMESITE}, Secure={REFRESH_TOKEN_COOKIE_SECURE}")
        
        # Obtener refresh token de la cookie
        refresh_token = request.COOKIES.get(REFRESH_TOKEN_COOKIE_NAME)
        
        if not refresh_token:
            # Fallback: intentar leer del body (para compatibilidad hacia atrás)
            refresh_token = request.data.get('refresh')
            if refresh_token:
                logger.info("[REFRESH] Token obtenido del body (fallback)")
        else:
            logger.info("[REFRESH] Token obtenido de cookie HttpOnly")
        
        if not refresh_token:
            logger.warning("[REFRESH] No se encontró refresh token en cookie ni body")
            return Response(
                {'error': 'No se encontró token de refresh'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            # Validar y refrescar el token
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)
            
            # Crear respuesta con nuevo access token
            response_data = {'access': access_token}
            
            # Si está habilitada la rotación de refresh tokens
            if settings.SIMPLE_JWT.get('ROTATE_REFRESH_TOKENS', False):
                # Blacklist el token anterior si está configurado
                if settings.SIMPLE_JWT.get('BLACKLIST_AFTER_ROTATION', False):
                    try:
                        refresh.blacklist()
                    except AttributeError:
                        pass  # Blacklist no está habilitado
                
                # Crear nuevo refresh token - obtener el usuario real
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user_id = refresh.access_token.payload.get('user_id')
                try:
                    user = User.objects.get(id=user_id)
                    new_refresh = RefreshToken.for_user(user)
                    new_refresh_str = str(new_refresh)
                    
                    # SEGURIDAD: El nuevo refresh token solo va en cookie HttpOnly
                    response = Response(response_data, status=status.HTTP_200_OK)
                    
                    # Actualizar cookie con nuevo refresh token (respaldo)
                    response.set_cookie(
                        key=REFRESH_TOKEN_COOKIE_NAME,
                        value=new_refresh_str,
                        max_age=int(REFRESH_TOKEN_COOKIE_MAX_AGE),
                        path=REFRESH_TOKEN_COOKIE_PATH,
                        secure=REFRESH_TOKEN_COOKIE_SECURE,
                        httponly=REFRESH_TOKEN_COOKIE_HTTPONLY,
                        samesite=REFRESH_TOKEN_COOKIE_SAMESITE,
                    )
                    return response
                except User.DoesNotExist:
                    logger.warning(f"Usuario {user_id} no encontrado para rotación de token")
            
            response = Response(response_data, status=status.HTTP_200_OK)
            return response
            
        except TokenError as e:
            logger.warning(f"Token refresh fallido: {str(e)}")
            return Response(
                {'error': 'Token de refresh inválido o expirado'},
                status=status.HTTP_401_UNAUTHORIZED
            )


class SecureLogoutView(APIView):
    """
    View de logout seguro que:
    - Invalida el refresh token (blacklist)
    - Elimina la cookie del refresh token
    """
    permission_classes = [AllowAny]  # Permitir logout sin auth
    
    def post(self, request, *args, **kwargs):
        # Obtener refresh token de la cookie
        refresh_token = request.COOKIES.get(REFRESH_TOKEN_COOKIE_NAME)
        
        if not refresh_token:
            # Fallback: intentar leer del body
            refresh_token = request.data.get('refresh')
        
        # Intentar blacklist del token si existe
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
                logger.info("Refresh token blacklisted exitosamente")
            except Exception as e:
                logger.warning(f"Error al blacklist token: {str(e)}")
        
        # Crear respuesta
        response = Response(
            {'message': 'Logout exitoso'},
            status=status.HTTP_200_OK
        )
        
        # Eliminar cookie del refresh token
        response.delete_cookie(
            key=REFRESH_TOKEN_COOKIE_NAME,
            path=REFRESH_TOKEN_COOKIE_PATH,
        )
        
        return response


# Mantener compatibilidad con el view anterior
class CustomTokenObtainPairView(SecureTokenObtainPairView):
    """Alias para mantener compatibilidad hacia atrás"""
    pass
