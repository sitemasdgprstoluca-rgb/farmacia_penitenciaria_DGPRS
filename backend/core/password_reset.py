"""
Views para recuperación de contraseña.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


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
            
            # TODO: Implementar envío de email
            # Por ahora solo logueamos y retornamos éxito
            logger.info(f"Password reset solicitado para: {email}")
            logger.info(f"Token generado: uid={uid}, token={token}")
            
            # En producción, aquí enviarías el email
            # send_password_reset_email(user, uid, token)
            
        except User.DoesNotExist:
            # No revelar si el usuario existe o no
            logger.info(f"Password reset solicitado para email inexistente: {email}")
        
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
