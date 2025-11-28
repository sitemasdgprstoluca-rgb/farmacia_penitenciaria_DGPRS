# -*- coding: utf-8 -*-
"""
Sistema de Recuperacion de Contrasena por Email
================================================
Usa cache de Django para almacenar tokens (compatible con Redis en produccion).
Incluye rate limiting y validacion robusta.
"""
import secrets
import hashlib
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

# Prefijo para keys de cache
CACHE_PREFIX = 'pwd_reset_'
TOKEN_EXPIRY_SECONDS = 3600  # 1 hora


# =============================================================================
# THROTTLING ESPECIFICO PARA RESET
# =============================================================================
class PasswordResetThrottle(AnonRateThrottle):
    """Rate limit: 3 solicitudes por minuto por IP."""
    rate = '3/min'


class PasswordResetConfirmThrottle(AnonRateThrottle):
    """Rate limit: 5 intentos por minuto por IP."""
    rate = '5/min'


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================
def generate_reset_token():
    """Genera un token seguro de 32 bytes (43 caracteres URL-safe)"""
    return secrets.token_urlsafe(32)


def hash_token(token):
    """Hashea el token para almacenamiento seguro"""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def get_client_ip(request):
    """Obtiene la IP real del cliente"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def store_token(token_hash, user_id):
    """Almacena token en cache con expiracion automatica"""
    cache_key = f"{CACHE_PREFIX}{token_hash}"
    cache.set(cache_key, {
        'user_id': user_id,
        'created_at': timezone.now().isoformat(),
    }, TOKEN_EXPIRY_SECONDS)


def get_token_data(token_hash):
    """Recupera datos del token del cache"""
    cache_key = f"{CACHE_PREFIX}{token_hash}"
    return cache.get(cache_key)


def invalidate_token(token_hash):
    """Elimina token del cache"""
    cache_key = f"{CACHE_PREFIX}{token_hash}"
    cache.delete(cache_key)


def invalidate_user_tokens(user_id):
    """
    Invalida tokens anteriores de un usuario.
    Nota: Con cache simple esto no es posible eficientemente.
    Se recomienda usar Redis con patron de keys para produccion.
    """
    # Con cache local, no podemos iterar. Se maneja con expiracion automatica.
    pass


def send_reset_email(user, reset_url):
    """
    Envia email de reset. Retorna True si se envio correctamente.
    """
    subject = 'Restablecimiento de Contrasena - Sistema de Farmacia'
    nombre = user.first_name or user.username
    
    html_message = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"></head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #9F2241; margin: 0;">Sistema de Farmacia</h1>
            <p style="color: #666; margin: 5px 0;">Control de Abasto Penitenciario</p>
        </div>
        
        <div style="background: #f9f9f9; border-radius: 10px; padding: 25px; margin-bottom: 20px;">
            <h2 style="color: #333; margin-top: 0;">Hola, {nombre}</h2>
            <p>Recibimos una solicitud para restablecer la contrasena de tu cuenta.</p>
            <p>Haz clic en el siguiente boton para crear una nueva contrasena:</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_url}" 
                   style="background: linear-gradient(135deg, #9F2241 0%, #6B1839 100%);
                          color: white; padding: 15px 30px; text-decoration: none;
                          border-radius: 8px; font-weight: bold; display: inline-block;">
                    Restablecer Contrasena
                </a>
            </div>
            
            <p style="color: #666; font-size: 14px;">
                Este enlace expirara en <strong>1 hora</strong>.
            </p>
            <p style="color: #666; font-size: 14px;">
                Si no solicitaste este cambio, puedes ignorar este correo.
            </p>
        </div>
        
        <div style="text-align: center; color: #999; font-size: 12px; margin-top: 30px;">
            <p>Este es un correo automatico, por favor no respondas.</p>
            <p>Subsecretaria de Seguridad - Gobierno del Estado de Mexico</p>
        </div>
    </div>
</body>
</html>"""
    
    plain_message = f"""Hola {nombre},

Recibimos una solicitud para restablecer la contrasena de tu cuenta.

Para crear una nueva contrasena, visita el siguiente enlace:
{reset_url}

Este enlace expirara en 1 hora.

Si no solicitaste este cambio, puedes ignorar este correo.

Sistema de Farmacia - Subsecretaria de Seguridad"""
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False
        )
        return True
    except Exception as e:
        logger.error(f"Error enviando email de reset a {user.email}: {e}")
        return False


# =============================================================================
# VISTAS API
# =============================================================================
class PasswordResetRequestView(APIView):
    """
    POST /api/password-reset/request/
    Solicita restablecimiento de contrasena enviando email.
    """
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetThrottle]
    
    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        
        if not email:
            return Response({
                'error': 'Debe proporcionar un correo electronico'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Mensaje generico para no revelar si el email existe
        success_message = {
            'message': 'Si el correo esta registrado, recibiras un enlace para restablecer tu contrasena.',
            'info': 'Revisa tu bandeja de entrada y spam.'
        }
        
        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            logger.info(f"Solicitud de reset para email no registrado: {email}")
            return Response(success_message, status=status.HTTP_200_OK)
        
        # Generar nuevo token
        token = generate_reset_token()
        token_hash = hash_token(token)
        
        # Guardar en cache
        store_token(token_hash, user.id)
        
        # Construir URL de reset
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
        reset_url = f"{frontend_url}/restablecer-password?token={token}"
        
        # Intentar enviar email
        email_sent = send_reset_email(user, reset_url)
        
        if not email_sent:
            invalidate_token(token_hash)
            logger.warning(f"Fallo envio de email de reset para {email}")
            
            if settings.DEBUG:
                return Response({
                    'message': success_message['message'],
                    'debug_token': token,
                    'debug_url': reset_url,
                    'warning': 'Email no configurado. Token mostrado solo en modo DEBUG.'
                }, status=status.HTTP_200_OK)
        else:
            logger.info(f"Email de reset enviado a {email}")
        
        return Response(success_message, status=status.HTTP_200_OK)


class PasswordResetValidateTokenView(APIView):
    """
    POST /api/password-reset/validate/
    Valida si un token es valido (sin usarlo).
    """
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetConfirmThrottle]
    
    def post(self, request):
        token = request.data.get('token', '').strip()
        
        if not token:
            return Response({
                'valid': False,
                'error': 'Token requerido'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        token_hash = hash_token(token)
        token_data = get_token_data(token_hash)
        
        if not token_data:
            return Response({
                'valid': False,
                'error': 'Enlace invalido o expirado'
            })
        
        return Response({
            'valid': True,
            'message': 'Token valido'
        })


class PasswordResetConfirmView(APIView):
    """
    POST /api/password-reset/confirm/
    Confirma el restablecimiento con el token y nueva contrasena.
    """
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetConfirmThrottle]
    
    def post(self, request):
        token = request.data.get('token', '').strip()
        new_password = request.data.get('new_password', '')
        confirm_password = request.data.get('confirm_password', '')
        
        if not all([token, new_password, confirm_password]):
            return Response({
                'error': 'Debe proporcionar token, new_password y confirm_password'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if new_password != confirm_password:
            return Response({
                'error': 'Las contrasenas no coinciden'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # ✅ Validaciones de complejidad (unificadas con cambio de contraseña)
        if len(new_password) < 8:
            return Response({
                'error': 'La contrasena debe tener al menos 8 caracteres'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not any(c.isupper() for c in new_password):
            return Response({
                'error': 'La contrasena debe tener al menos una mayuscula'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not any(c.isdigit() for c in new_password):
            return Response({
                'error': 'La contrasena debe tener al menos un numero'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        token_hash = hash_token(token)
        token_data = get_token_data(token_hash)
        
        if not token_data:
            return Response({
                'error': 'El enlace no es valido o ha expirado'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(id=token_data['user_id'])
            user.set_password(new_password)
            user.save()
            
            # Invalidar token usado
            invalidate_token(token_hash)
            
            logger.info(f"Contrasena restablecida para usuario {user.username}")
            
            return Response({
                'message': 'Contrasena restablecida exitosamente. Ya puedes iniciar sesion.'
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            invalidate_token(token_hash)
            return Response({
                'error': 'Usuario no encontrado'
            }, status=status.HTTP_400_BAD_REQUEST)
