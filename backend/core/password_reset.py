"""
Views para recuperación de contraseña.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


def send_password_reset_email(user, uid, token):
    """
    Envía el correo de recuperación de contraseña de forma segura.
    ISS-003: Los tokens NUNCA deben aparecer en logs.
    """
    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
    reset_url = f"{frontend_url}/reset-password?uid={uid}&token={token}"
    
    subject = 'Recuperación de contraseña - Sistema de Farmacia Penitenciaria'
    message = f"""
    Hola {user.first_name or user.username},
    
    Has solicitado restablecer tu contraseña.
    
    Haz clic en el siguiente enlace para crear una nueva contraseña:
    {reset_url}
    
    Este enlace expirará en 24 horas.
    
    Si no solicitaste este cambio, ignora este mensaje.
    
    Atentamente,
    Sistema de Farmacia Penitenciaria
    """
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        # ISS-003: NO loguear detalles sensibles, solo el tipo de error
        logger.error(f"Error enviando email de reset para usuario ID {user.pk}: {type(e).__name__}")
        return False


class PasswordResetRequestView(APIView):
    """
    Solicita un reset de contraseña.
    Envía un email con un token de recuperación.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        
        if not email:
            return Response(
                {'error': 'Email requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email=email)
            
            # Generar token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # ISS-003: Enviar email de forma segura (sin loguear tokens)
            email_sent = send_password_reset_email(user, uid, token)
            
            # Log seguro: solo indica que se procesó, sin datos sensibles
            logger.info(f"Password reset procesado para usuario ID {user.pk}, email_sent={email_sent}")
            
        except User.DoesNotExist:
            # No revelar si el usuario existe o no (log sin email completo)
            logger.debug("Password reset solicitado para email no registrado")
        
        # Siempre retornar éxito para no revelar información
        return Response({
            'message': 'Si el email está registrado, recibirás instrucciones para restablecer tu contraseña.'
        })


class PasswordResetValidateTokenView(APIView):
    """
    Valida un token de reset de contraseña.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        token = request.data.get('token', '')
        uid = request.data.get('uid', '')
        
        if not token or not uid:
            return Response(
                {'valid': False, 'error': 'Token y UID requeridos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
            
            if default_token_generator.check_token(user, token):
                return Response({'valid': True})
            else:
                return Response({'valid': False, 'error': 'Token inválido o expirado'})
                
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({'valid': False, 'error': 'Token inválido'})


class PasswordResetConfirmView(APIView):
    """
    Confirma el reset de contraseña con el token.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        token = request.data.get('token', '')
        uid = request.data.get('uid', '')
        new_password = request.data.get('new_password', '')
        confirm_password = request.data.get('confirm_password', '')
        
        if not all([token, uid, new_password]):
            return Response(
                {'error': 'Token, UID y nueva contraseña requeridos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if new_password != confirm_password:
            return Response(
                {'error': 'Las contraseñas no coinciden'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(new_password) < 8:
            return Response(
                {'error': 'La contraseña debe tener al menos 8 caracteres'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
            
            if not default_token_generator.check_token(user, token):
                return Response(
                    {'error': 'Token inválido o expirado'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Cambiar contraseña
            user.set_password(new_password)
            user.save()
            
            logger.info(f"Contraseña restablecida para usuario: {user.username}")
            
            return Response({'message': 'Contraseña restablecida exitosamente'})
            
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {'error': 'Token inválido'},
                status=status.HTTP_400_BAD_REQUEST
            )
