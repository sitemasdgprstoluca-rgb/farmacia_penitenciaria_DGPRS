"""
Tests para el sistema de confirmación en 2 pasos (ISS-SEC)
Verifica que el backend valida correctamente la confirmación obligatoria
"""

import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from core.models import Centro, Producto, Lote
from core.mixins import ConfirmationRequiredMixin, require_confirmation
from rest_framework.views import APIView
from rest_framework.response import Response
from decimal import Decimal
from datetime import date, timedelta

User = get_user_model()


@pytest.fixture
def admin_user(db):
    """Crea un usuario admin para las pruebas"""
    return User.objects.create_user(
        username='admin_test',
        password='TestPass123!',
        email='admin@test.com',
        rol='admin',
        is_active=True
    )


@pytest.fixture
def farmacia_user(db):
    """Crea un usuario de farmacia para las pruebas"""
    return User.objects.create_user(
        username='farmacia_test',
        password='TestPass123!',
        email='farmacia@test.com',
        rol='farmacia',
        is_active=True
    )


@pytest.fixture
def centro(db):
    """Crea un centro para las pruebas"""
    return Centro.objects.create(
        nombre='Centro Test',
        direccion='Dirección Test',
        activo=True
    )


@pytest.fixture
def producto(db):
    """Crea un producto para las pruebas"""
    return Producto.objects.create(
        clave='PROD-001',
        nombre='Producto Test',
        descripcion='Descripción test',
        unidad='PIEZA',
        activo=True
    )


@pytest.fixture
def lote(db, producto):
    """Crea un lote para las pruebas"""
    return Lote.objects.create(
        producto=producto,
        numero_lote='LOTE-001',
        fecha_caducidad=date.today() + timedelta(days=365),
        stock_inicial=100,
        stock_actual=100
    )


@pytest.fixture
def api_client():
    """Cliente API para las pruebas"""
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, admin_user):
    """Cliente autenticado como admin"""
    api_client.force_authenticate(user=admin_user)
    return api_client


class TestConfirmationRequiredMixin:
    """Tests para el mixin ConfirmationRequiredMixin"""

    def test_delete_sin_confirmacion_retorna_409(self, authenticated_client, centro):
        """DELETE sin confirmed=true debe retornar 409 Conflict"""
        url = f'/api/centros/{centro.id}/'
        
        response = authenticated_client.delete(url)
        
        # Debe rechazar con 409 Conflict
        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data.get('code') == 'CONFIRMATION_REQUIRED'
        assert 'confirmación' in response.data.get('message', '').lower() or \
               'confirmation' in response.data.get('message', '').lower()

    def test_delete_con_confirmacion_query_param(self, authenticated_client, centro):
        """DELETE con ?confirmed=true debe proceder"""
        url = f'/api/centros/{centro.id}/?confirmed=true'
        
        response = authenticated_client.delete(url)
        
        # Puede ser 204 (éxito) o error de dependencias, pero NO 409
        assert response.status_code != status.HTTP_409_CONFLICT

    def test_delete_con_header_confirmacion(self, authenticated_client, centro):
        """DELETE con header X-Confirm-Action debe proceder"""
        url = f'/api/centros/{centro.id}/'
        
        response = authenticated_client.delete(
            url,
            HTTP_X_CONFIRM_ACTION='true'
        )
        
        # No debe ser 409
        assert response.status_code != status.HTTP_409_CONFLICT

    def test_delete_con_body_confirmacion(self, authenticated_client, centro):
        """DELETE con body {confirmed: true} debe proceder"""
        url = f'/api/centros/{centro.id}/'
        
        response = authenticated_client.delete(
            url,
            data={'confirmed': True},
            format='json'
        )
        
        # No debe ser 409
        assert response.status_code != status.HTTP_409_CONFLICT


@pytest.mark.django_db
class TestConfirmationOnDeleteEndpoints:
    """Tests de confirmación en endpoints DELETE específicos"""

    def test_delete_producto_requiere_confirmacion(self, authenticated_client, producto):
        """DELETE /api/productos/{id}/ sin confirmación debe fallar"""
        url = f'/api/productos/{producto.id}/'
        
        response = authenticated_client.delete(url)
        
        # Verificar que requiere confirmación o tiene otra protección
        # (puede ser 409 o 400 dependiendo de la implementación)
        assert response.status_code in [
            status.HTTP_409_CONFLICT, 
            status.HTTP_400_BAD_REQUEST
        ] or 'confirm' in str(response.data).lower()

    def test_delete_lote_requiere_confirmacion(self, authenticated_client, lote):
        """DELETE /api/lotes/{id}/ sin confirmación debe fallar"""
        url = f'/api/lotes/{lote.id}/'
        
        response = authenticated_client.delete(url)
        
        # Verificar que requiere confirmación
        assert response.status_code in [
            status.HTTP_409_CONFLICT,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN  # También válido si hay protección adicional
        ]

    def test_delete_usuario_requiere_confirmacion(self, authenticated_client, farmacia_user):
        """DELETE /api/usuarios/{id}/ sin confirmación debe fallar"""
        url = f'/api/usuarios/{farmacia_user.id}/'
        
        response = authenticated_client.delete(url)
        
        # Verificar que requiere confirmación
        assert response.status_code in [
            status.HTTP_409_CONFLICT,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN
        ]


@pytest.mark.django_db  
class TestConfirmationResponses:
    """Tests para verificar la estructura de respuestas de confirmación"""

    def test_response_409_incluye_codigo(self, authenticated_client, centro):
        """La respuesta 409 debe incluir código CONFIRMATION_REQUIRED"""
        url = f'/api/centros/{centro.id}/'
        
        response = authenticated_client.delete(url)
        
        if response.status_code == status.HTTP_409_CONFLICT:
            assert 'code' in response.data
            assert response.data['code'] == 'CONFIRMATION_REQUIRED'

    def test_response_409_incluye_mensaje(self, authenticated_client, centro):
        """La respuesta 409 debe incluir mensaje descriptivo"""
        url = f'/api/centros/{centro.id}/'
        
        response = authenticated_client.delete(url)
        
        if response.status_code == status.HTTP_409_CONFLICT:
            assert 'message' in response.data or 'detail' in response.data

    def test_response_409_incluye_requires_confirmation(self, authenticated_client, centro):
        """La respuesta 409 debe indicar que requiere confirmación"""
        url = f'/api/centros/{centro.id}/'
        
        response = authenticated_client.delete(url)
        
        if response.status_code == status.HTTP_409_CONFLICT:
            assert response.data.get('requires_confirmation') == True or \
                   response.data.get('code') == 'CONFIRMATION_REQUIRED'


@pytest.mark.django_db
class TestConfirmationSecurityEdgeCases:
    """Tests de casos límite de seguridad"""

    def test_confirmed_false_no_permite_eliminar(self, authenticated_client, centro):
        """confirmed=false no debe permitir eliminar"""
        url = f'/api/centros/{centro.id}/?confirmed=false'
        
        response = authenticated_client.delete(url)
        
        # Debe rechazar - confirmed=false es lo mismo que sin confirmar
        assert response.status_code == status.HTTP_409_CONFLICT or \
               Centro.objects.filter(id=centro.id).exists()

    def test_confirmed_string_invalido(self, authenticated_client, centro):
        """confirmed=invalid no debe permitir eliminar"""
        url = f'/api/centros/{centro.id}/?confirmed=maybe'
        
        response = authenticated_client.delete(url)
        
        # Debe rechazar - valor inválido
        assert response.status_code == status.HTTP_409_CONFLICT or \
               Centro.objects.filter(id=centro.id).exists()

    def test_multiple_confirmaciones_validas(self, authenticated_client, centro):
        """Múltiples métodos de confirmación deben funcionar"""
        url = f'/api/centros/{centro.id}/?confirmed=true'
        
        response = authenticated_client.delete(
            url,
            HTTP_X_CONFIRM_ACTION='true',
            data={'confirmed': True},
            format='json'
        )
        
        # Debe permitir con confirmación redundante
        assert response.status_code != status.HTTP_409_CONFLICT

    def test_no_bypass_sin_autenticacion(self, api_client, centro):
        """Usuario no autenticado no puede eliminar aunque confirme"""
        url = f'/api/centros/{centro.id}/?confirmed=true'
        
        response = api_client.delete(url)
        
        # Debe rechazar por falta de autenticación (401 o 403)
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ]


@pytest.mark.django_db
class TestRequireConfirmationDecorator:
    """Tests para el decorador require_confirmation"""

    def test_decorator_aplica_validacion(self):
        """El decorador debe aplicar validación de confirmación"""
        
        @require_confirmation
        def mock_delete_action(request):
            return Response({'status': 'deleted'})
        
        # Crear mock request sin confirmación
        from rest_framework.request import Request
        from django.test import RequestFactory
        
        factory = RequestFactory()
        django_request = factory.delete('/test/')
        request = Request(django_request)
        
        response = mock_delete_action(request)
        
        # Debe requerir confirmación
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_decorator_permite_con_confirmacion(self):
        """El decorador debe permitir con confirmación"""
        
        @require_confirmation
        def mock_delete_action(request):
            return Response({'status': 'deleted'})
        
        from rest_framework.request import Request
        from django.test import RequestFactory
        
        factory = RequestFactory()
        django_request = factory.delete('/test/?confirmed=true')
        request = Request(django_request)
        
        response = mock_delete_action(request)
        
        # Debe permitir la acción
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'deleted'


@pytest.mark.django_db
class TestIntegrationWithFrontend:
    """Tests de integración con el flujo del frontend"""

    def test_flujo_completo_delete_centro(self, authenticated_client, centro):
        """Simula el flujo completo de eliminación desde el frontend"""
        url = f'/api/centros/{centro.id}/'
        
        # Paso 1: Intento sin confirmación (frontend muestra modal)
        response1 = authenticated_client.delete(url)
        assert response1.status_code == status.HTTP_409_CONFLICT
        assert Centro.objects.filter(id=centro.id).exists()
        
        # Paso 2: Con confirmación del usuario (después del modal)
        response2 = authenticated_client.delete(
            url,
            HTTP_X_CONFIRM_ACTION='true'
        )
        
        # Puede ser éxito o error de dependencias, pero NO 409
        assert response2.status_code != status.HTTP_409_CONFLICT

    def test_flujo_cancelacion_no_elimina(self, authenticated_client, centro):
        """Si el usuario cancela el modal, el item no se elimina"""
        url = f'/api/centros/{centro.id}/'
        
        # Paso 1: Intento sin confirmación
        response = authenticated_client.delete(url)
        assert response.status_code == status.HTTP_409_CONFLICT
        
        # Usuario cancela - no hace segundo request
        # El centro debe seguir existiendo
        assert Centro.objects.filter(id=centro.id).exists()

    def test_header_x_confirm_action_case_insensitive(self, authenticated_client, centro):
        """El header X-Confirm-Action debe ser case-insensitive"""
        url = f'/api/centros/{centro.id}/'
        
        # Variantes del header
        for header_value in ['true', 'True', 'TRUE', '1', 'yes']:
            response = authenticated_client.delete(
                url,
                HTTP_X_CONFIRM_ACTION=header_value
            )
            
            # No debe ser 409 (la confirmación debe ser aceptada)
            # Puede ser otro error pero no por falta de confirmación
            if response.status_code == status.HTTP_409_CONFLICT:
                assert response.data.get('code') != 'CONFIRMATION_REQUIRED', \
                    f"Header value '{header_value}' no fue aceptado como confirmación"
