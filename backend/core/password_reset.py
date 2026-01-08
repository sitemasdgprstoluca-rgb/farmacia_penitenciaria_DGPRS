"""
Views para recuperación de contraseña.
Usa Resend en producción para envío confiable de emails.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
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
    Envía el correo de recuperación de contraseña.
    Usa Resend si está configurado, sino fallback a Django mail.
    """
    frontend_url = getattr(settings, 'FRONTEND_URL', 'https://farmacia-penitenciaria-front.onrender.com')
    reset_url = f"{frontend_url}/restablecer-password?uid={uid}&token={token}"
    
    # Intentar usar Resend primero (servicio de producción)
    resend_api_key = getattr(settings, 'RESEND_API_KEY', '')
    
    if resend_api_key:
        try:
            import resend
            resend.api_key = resend_api_key
            
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'Sistema Farmacia <onboarding@resend.dev>')
            
            # Email HTML profesional
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #632842 0%, #8B3A5C 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .button {{ display: inline-block; background: #632842; color: white !important; padding: 15px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; font-weight: bold; }}
                    .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🏥 Sistema de Farmacia Penitenciaria</h1>
                    </div>
                    <div class="content">
                        <h2>Recuperación de Contraseña</h2>
                        <p>Hola <strong>{user.first_name or user.username}</strong>,</p>
                        <p>Has solicitado restablecer tu contraseña. Haz clic en el siguiente botón para crear una nueva:</p>
                        <p style="text-align: center;">
                            <a href="{reset_url}" class="button">Restablecer Contraseña</a>
                        </p>
                        <p>O copia y pega este enlace en tu navegador:</p>
                        <p style="word-break: break-all; color: #666; font-size: 12px;">{reset_url}</p>
                        <p><strong>⚠️ Este enlace expirará en 24 horas.</strong></p>
                        <p>Si no solicitaste este cambio, puedes ignorar este mensaje.</p>
                    </div>
                    <div class="footer">
                        <p>Este es un mensaje automático. Por favor no respondas a este correo.</p>
                        <p>Sistema de Farmacia Penitenciaria - Estado de México</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            params = {
                "from": from_email,
                "to": [user.email],
                "subject": "Recuperación de contraseña - Sistema de Farmacia Penitenciaria",
                "html": html_content,
            }
            
            resend.Emails.send(params)
            logger.info(f"Email de reset enviado via Resend para usuario ID {user.pk}")
            return True
            
        except Exception as e:
            logger.error(f"Error enviando email via Resend para usuario ID {user.pk}: {type(e).__name__}")
            # No hacer fallback a SMTP, retornar False
            return False
    
    # Fallback a Django mail (para desarrollo o si no hay Resend)
    try:
        from django.core.mail import send_mail
        
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
        
        send_mail(
            subject='Recuperación de contraseña - Sistema de Farmacia Penitenciaria',
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Error enviando email de reset para usuario ID {user.pk}: {type(e).__name__}")
        return False


class PasswordResetRequestView(APIView):
    """
    Solicita un reset de contraseña.
    Envía un email con un token de recuperación usando Resend.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        
        if not email:
            return Response(
                {'error': 'Email requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        response_data = {
            'message': 'Si el email está registrado, recibirás instrucciones para restablecer tu contraseña.'
        }
        
        try:
            user = User.objects.get(email=email)
            
            # Generar token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Verificar si hay servicio de email configurado
            resend_key = getattr(settings, 'RESEND_API_KEY', '')
            email_host = getattr(settings, 'EMAIL_HOST_USER', '')
            
            if resend_key or email_host:
                # Producción: enviar email via Resend o SMTP
                email_sent = send_password_reset_email(user, uid, token)
                if email_sent:
                    logger.info(f"Password reset: email enviado para usuario ID {user.pk}")
                else:
                    logger.warning(f"Password reset: fallo envío email para usuario ID {user.pk}")
            else:
                # Desarrollo sin email configurado: mostrar link directo
                frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
                reset_url = f"{frontend_url}/restablecer-password?uid={uid}&token={token}"
                response_data['debug_mode'] = True
                response_data['debug_url'] = reset_url
                response_data['debug_token'] = token
                response_data['debug_uid'] = uid
                logger.info(f"Password reset (sin email config): URL generada para usuario ID {user.pk}")
            
        except User.DoesNotExist:
            # No revelar si el usuario existe o no (log sin email completo)
            logger.debug("Password reset solicitado para email no registrado")
        
        return Response(response_data)


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
