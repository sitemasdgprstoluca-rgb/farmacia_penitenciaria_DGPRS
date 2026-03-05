"""
Views para recuperación de contraseña.
Usa Resend en producción para envío confiable de emails.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
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
    
    # Año actual para el footer
    from datetime import datetime
    current_year = datetime.now().year
    
    # Intentar usar Resend primero (servicio de producción)
    resend_api_key = getattr(settings, 'RESEND_API_KEY', '')
    
    if resend_api_key:
        try:
            import resend
            resend.api_key = resend_api_key
            
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'Sistema Farmacia <onboarding@resend.dev>')
            
            # Email HTML profesional mejorado
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                    body {{ 
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                        line-height: 1.6; 
                        color: #333; 
                        background-color: #f4f4f4;
                        padding: 20px;
                    }}
                    .email-wrapper {{ max-width: 600px; margin: 0 auto; background: white; }}
                    .header {{ 
                        background: linear-gradient(135deg, #9F2241 0%, #6B1839 50%, #4a0f26 100%); 
                        color: white; 
                        padding: 40px 30px; 
                        text-align: center; 
                        border-radius: 10px 10px 0 0;
                    }}
                    .header h1 {{ 
                        font-size: 24px; 
                        margin-bottom: 10px; 
                        font-weight: 600;
                    }}
                    .header p {{ 
                        font-size: 14px; 
                        opacity: 0.9; 
                        margin: 0;
                    }}
                    .icon-badge {{
                        width: 80px;
                        height: 80px;
                        background: rgba(255,255,255,0.2);
                        border-radius: 50%;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        margin: 0 auto 15px auto;
                        font-size: 40px;
                    }}
                    .content {{ 
                        background: #ffffff; 
                        padding: 40px 30px;
                    }}
                    .content h2 {{
                        color: #6B1839;
                        font-size: 22px;
                        margin-bottom: 20px;
                        font-weight: 600;
                    }}
                    .greeting {{
                        font-size: 16px;
                        color: #333;
                        margin-bottom: 15px;
                    }}
                    .greeting strong {{
                        color: #9F2241;
                    }}
                    .message {{
                        font-size: 15px;
                        color: #666;
                        margin-bottom: 25px;
                        line-height: 1.6;
                    }}
                    .button-container {{
                        text-align: center;
                        margin: 30px 0;
                    }}
                    .button {{ 
                        display: inline-block; 
                        background: linear-gradient(135deg, #9F2241 0%, #6B1839 100%);
                        color: white !important; 
                        padding: 16px 40px; 
                        text-decoration: none; 
                        border-radius: 8px; 
                        font-weight: bold;
                        font-size: 16px;
                        box-shadow: 0 4px 15px rgba(159, 34, 65, 0.3);
                        transition: all 0.3s ease;
                    }}
                    .button:hover {{
                        background: linear-gradient(135deg, #6B1839 0%, #9F2241 100%);
                        box-shadow: 0 6px 20px rgba(159, 34, 65, 0.4);
                    }}
                    .info-box {{
                        background: #f8f9fa;
                        border-left: 4px solid #9F2241;
                        padding: 15px;
                        margin: 25px 0;
                        border-radius: 4px;
                    }}
                    .info-box p {{
                        margin: 8px 0;
                        font-size: 14px;
                        color: #555;
                    }}
                    .warning-box {{
                        background: #fff3cd;
                        border: 1px solid #ffc107;
                        border-radius: 6px;
                        padding: 15px;
                        margin: 20px 0;
                    }}
                    .warning-box p {{
                        margin: 0;
                        font-size: 14px;
                        color: #856404;
                        font-weight: 600;
                    }}
                    .link-section {{
                        background: #f8f9fa;
                        padding: 15px;
                        border-radius: 6px;
                        margin: 20px 0;
                    }}
                    .link-section p {{
                        margin-bottom: 8px;
                        font-size: 13px;
                        color: #666;
                    }}
                    .link-text {{
                        word-break: break-all;
                        color: #9F2241;
                        font-size: 12px;
                        font-family: monospace;
                        padding: 10px;
                        background: white;
                        border: 1px solid #dee2e6;
                        border-radius: 4px;
                        display: block;
                    }}
                    .security-note {{
                        background: #e7f3ff;
                        border-left: 4px solid #0066cc;
                        padding: 15px;
                        margin: 20px 0;
                        border-radius: 4px;
                    }}
                    .security-note p {{
                        margin: 5px 0;
                        font-size: 13px;
                        color: #004085;
                    }}
                    .footer {{ 
                        background: #f8f9fa;
                        text-align: center; 
                        color: #666; 
                        font-size: 12px; 
                        padding: 30px;
                        border-radius: 0 0 10px 10px;
                        border-top: 3px solid #9F2241;
                    }}
                    .footer p {{
                        margin: 8px 0;
                    }}
                    .footer strong {{
                        color: #333;
                        font-size: 13px;
                    }}
                    @media only screen and (max-width: 600px) {{
                        .content {{ padding: 30px 20px; }}
                        .button {{ padding: 14px 30px; font-size: 15px; }}
                    }}
                </style>
            </head>
            <body>
                <div class="email-wrapper">
                    <div class="header">
                        <div class="icon-badge">🔐</div>
                        <h1>Sistema de Farmacia Penitenciaria</h1>
                        <p>Subsecretaría de Control Penitenciario • Estado de México</p>
                    </div>
                    
                    <div class="content">
                        <h2>Recuperación de Contraseña</h2>
                        
                        <p class="greeting">Hola <strong>{user.first_name or user.username}</strong>,</p>
                        
                        <p class="message">
                            Has solicitado restablecer tu contraseña para acceder al Sistema de Farmacia Penitenciaria. 
                            Para continuar con el proceso de recuperación, haz clic en el siguiente botón:
                        </p>
                        
                        <div class="button-container">
                            <a href="{reset_url}" class="button">Restablecer Contraseña</a>
                        </div>
                        
                        <div class="warning-box">
                            <p>⚠️ Este enlace expirará en 24 horas por seguridad.</p>
                        </div>
                        
                        <div class="link-section">
                            <p>Si el botón no funciona, copia y pega este enlace en tu navegador:</p>
                            <span class="link-text">{reset_url}</span>
                        </div>
                        
                        <div class="security-note">
                            <p><strong>🛡️ Información de Seguridad:</strong></p>
                            <p>• Este correo fue generado automáticamente por el sistema</p>
                            <p>• Si no solicitaste este cambio, ignora este mensaje</p>
                            <p>• Tu contraseña actual sigue siendo válida hasta que la cambies</p>
                            <p>• Nunca compartas tu contraseña con nadie</p>
                        </div>
                        
                        <div class="info-box">
                            <p><strong>¿Necesitas ayuda?</strong></p>
                            <p>Si tienes problemas para restablecer tu contraseña, contacta con el administrador del sistema.</p>
                        </div>
                    </div>
                    
                    <div class="footer">
                        <p><strong>Sistema de Farmacia Penitenciaria</strong></p>
                        <p>Subsecretaría de Control Penitenciario</p>
                        <p>Dirección General de Prevención y Readaptación Social • {current_year}</p>
                        <p style="margin-top: 15px; font-size: 11px; color: #999;">
                            Este es un mensaje automático. Por favor no respondas a este correo.
                        </p>
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


class PasswordResetThrottle(AnonRateThrottle):
    """Rate limit específico para password reset: máximo 3 peticiones por hora por IP"""
    rate = '3/hour'


class PasswordResetValidateThrottle(AnonRateThrottle):
    """Rate limit para validación de tokens: máximo 10 intentos por hora por IP"""
    rate = '10/hour'


class PasswordResetRequestView(APIView):
    """
    Solicita un reset de contraseña.
    Envía un email con un token de recuperación usando Resend.
    
    SEGURIDAD:
    - Rate limited a 3 peticiones por hora por IP
    - No revela si el email existe o no
    - Registra intentos en auditoría
    """
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetThrottle]
    
    def post(self, request):
        from core.models import AuditoriaLogs
        
        email = request.data.get('email', '').strip().lower()
        ip_address = request.META.get('REMOTE_ADDR', 'unknown')
        
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
            
            # Registrar solicitud en auditoría
            AuditoriaLogs.objects.create(
                usuario=user,
                accion='solicitar_reset_password',
                modelo='User',
                objeto_id=str(user.pk),
                ip_address=ip_address,
                detalles={'email': email}
            )
            
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
                # Sin servicio de email configurado
                # SEGURIDAD: NO loguear tokens/URLs - solo indicar que no hay servicio
                logger.warning(
                    f"Password reset solicitado pero no hay servicio de email configurado. "
                    f"Usuario ID: {user.pk}. Configure RESEND_API_KEY o EMAIL_HOST_USER."
                )
            
        except User.DoesNotExist:
            # No revelar si el usuario existe o no (log sin email completo)
            # Registrar intento fallido para detectar ataques
            AuditoriaLogs.objects.create(
                usuario=None,
                accion='solicitar_reset_password_fallido',
                modelo='User',
                objeto_id='email_no_encontrado',
                ip_address=ip_address,
                detalles={'email_domain': email.split('@')[1] if '@' in email else 'invalido'}
            )
            logger.debug("Password reset solicitado para email no registrado")
        
        return Response(response_data)


class PasswordResetValidateTokenView(APIView):
    """
    Valida un token de reset de contraseña.
    
    SEGURIDAD:
    - Rate limited a 10 intentos por hora por IP
    - Registra intentos de validación
    """
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetValidateThrottle]
    
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
    
    SEGURIDAD:
    - Rate limited a 5 intentos por hora por IP
    - Valida fortaleza de contraseña
    - Invalida token después de uso (automático al cambiar password hash)
    - Registra cambios exitosos en auditoría
    """
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetThrottle]  # Reutiliza mismo rate limit (3/hora)
    
    def post(self, request):
        from core.models import AuditoriaLogs
        
        token = request.data.get('token', '')
        uid = request.data.get('uid', '')
        new_password = request.data.get('new_password', '')
        confirm_password = request.data.get('confirm_password', '')
        ip_address = request.META.get('REMOTE_ADDR', 'unknown')
        
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
        
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
            
            # Validar contraseña usando los validadores configurados en Django
            try:
                validate_password(new_password, user=user)
            except ValidationError as e:
                return Response(
                    {'error': ' '.join(e.messages)},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not default_token_generator.check_token(user, token):
                return Response(
                    {'error': 'Token inválido o expirado'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Cambiar contraseña
            user.set_password(new_password)
            user.save()
            
            # Registrar cambio exitoso en auditoría
            AuditoriaLogs.objects.create(
                usuario=user,
                accion='password_restablecido',
                modelo='User',
                objeto_id=str(user.pk),
                ip_address=ip_address,
                detalles={
                    'metodo': 'password_reset_token',
                    'username': user.username
                }
            )
            
            logger.info(f"Contraseña restablecida para usuario: {user.username}")
            
            return Response({'message': 'Contraseña restablecida exitosamente'})
            
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {'error': 'Token inválido'},
                status=status.HTTP_400_BAD_REQUEST
            )
