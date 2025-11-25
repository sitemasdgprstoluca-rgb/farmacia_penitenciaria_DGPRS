"""
Serializers personalizados para JWT que incluyen información del usuario
"""
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from core.serializers import UserSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Serializer personalizado que incluye datos del usuario en la respuesta"""
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Agregar información del usuario
        serializer = UserSerializer(self.user)
        data['user'] = serializer.data
        
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    """View personalizado para login que retorna tokens + datos del usuario"""
    serializer_class = CustomTokenObtainPairSerializer
