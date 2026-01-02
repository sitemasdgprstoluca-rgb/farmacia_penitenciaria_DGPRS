"""Tests para notificaciones."""

from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

from core.models import Notificacion

User = get_user_model()


class NotificacionModelTest(TestCase):
    """Tests de modelo Notificacion."""

    def setUp(self):
        self.usuario = User.objects.create_user(username='testuser', password='test123')
        # NO crear Centro ni Requisicion porque sus modelos usan managed=False
        # y las migraciones de test no están sincronizadas con Supabase

    def test_crear_notificacion(self):
        notif = Notificacion.objects.create(
            usuario=self.usuario,
            titulo='Test',
            mensaje='Mensaje test',
            tipo='success'
        )
        self.assertEqual(notif.usuario, self.usuario)
        self.assertFalse(notif.leida)

    def test_notificacion_con_datos_requisicion(self):
        """Test notificación con datos de requisición en campo JSON 'datos'."""
        notif = Notificacion.objects.create(
            usuario=self.usuario,
            titulo='Requisicion aprobada',
            mensaje='Tu requisicion fue aprobada',
            datos={'requisicion_id': 123},  # Usar ID ficticio
            tipo='success'
        )
        self.assertEqual(notif.datos.get('requisicion_id'), 123)

    def test_marcar_leida(self):
        notif = Notificacion.objects.create(
            usuario=self.usuario,
            titulo='Test',
            mensaje='Test'
        )
        notif.leida = True
        notif.save()
        notif.refresh_from_db()
        self.assertTrue(notif.leida)

    def test_usuario_ve_solo_propias(self):
        otro_usuario = User.objects.create_user(username='otro', password='test123')

        Notificacion.objects.create(usuario=self.usuario, titulo='Para usuario 1', mensaje='Test')
        Notificacion.objects.create(usuario=otro_usuario, titulo='Para usuario 2', mensaje='Test')

        self.assertEqual(Notificacion.objects.filter(usuario=self.usuario).count(), 1)
        self.assertEqual(Notificacion.objects.filter(usuario=otro_usuario).count(), 1)


class NotificacionViewSetTest(APITestCase):
    """Tests de API para notificaciones."""

    def setUp(self):
        self.client = APIClient()
        self.usuario = User.objects.create_user(username='testuser', password='test123')
        self.otro_usuario = User.objects.create_user(username='otro', password='test123')
        self.client.force_authenticate(user=self.usuario)

    def test_listar_notificaciones_propias(self):
        Notificacion.objects.create(usuario=self.usuario, titulo='Para mi', mensaje='Test')
        Notificacion.objects.create(usuario=self.otro_usuario, titulo='Para otro', mensaje='Test')

        response = self.client.get('/api/notificaciones/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get('results', [])), 1)

    def test_marcar_leida_endpoint(self):
        notif = Notificacion.objects.create(usuario=self.usuario, titulo='Test', mensaje='Test', leida=False)

        response = self.client.post(f'/api/notificaciones/{notif.id}/marcar-leida/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notif.refresh_from_db()
        self.assertTrue(notif.leida)

    def test_contar_no_leidas(self):
        Notificacion.objects.create(usuario=self.usuario, titulo='No leida 1', mensaje='Test', leida=False)
        Notificacion.objects.create(usuario=self.usuario, titulo='Leida', mensaje='Test', leida=True)
        Notificacion.objects.create(usuario=self.usuario, titulo='No leida 2', mensaje='Test', leida=False)

        response = self.client.get('/api/notificaciones/no-leidas-count/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('no_leidas'), 2)

    def test_notificacion_sin_autenticacion(self):
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/notificaciones/')
        # Acepta tanto 401 (UNAUTHORIZED) como 403 (FORBIDDEN)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_marcar_todas_leidas(self):
        """Test del nuevo endpoint marcar-todas-leidas."""
        Notificacion.objects.create(usuario=self.usuario, titulo='No leida 1', mensaje='Test', leida=False)
        Notificacion.objects.create(usuario=self.usuario, titulo='No leida 2', mensaje='Test', leida=False)
        Notificacion.objects.create(usuario=self.usuario, titulo='No leida 3', mensaje='Test', leida=False)

        response = self.client.post('/api/notificaciones/marcar-todas-leidas/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('marcadas'), 3)
        
        # Verificar que todas están leídas
        no_leidas = Notificacion.objects.filter(usuario=self.usuario, leida=False).count()
        self.assertEqual(no_leidas, 0)

    def test_eliminar_notificacion_propia_permitido(self):
        """Test que el usuario puede eliminar sus propias notificaciones."""
        notif = Notificacion.objects.create(usuario=self.usuario, titulo='Para borrar', mensaje='Test')
        
        response = self.client.delete(f'/api/notificaciones/{notif.id}/')
        # DELETE de notificación propia devuelve 204 No Content
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # La notificación ya no debe existir
        self.assertFalse(Notificacion.objects.filter(id=notif.id).exists())

    def test_delete_notificacion_ajena_no_permitido(self):
        """Test que no se pueden eliminar notificaciones de otros usuarios."""
        notif = Notificacion.objects.create(usuario=self.otro_usuario, titulo='De otro', mensaje='Test')
        
        response = self.client.delete(f'/api/notificaciones/{notif.id}/')
        # La notificación de otro usuario no está en el queryset del usuario actual
        # El ViewSet maneja la excepción y devuelve 400 con un mensaje de error
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND])
        # La notificación del otro usuario debe seguir existiendo
        self.assertTrue(Notificacion.objects.filter(id=notif.id).exists())

    def test_no_puede_crear_notificacion(self):
        """Test que no se puede crear notificación vía API (read-only)."""
        data = {
            'titulo': 'Notificacion manual',
            'mensaje': 'No debería crearse',
            'tipo': 'info'
        }
        response = self.client.post('/api/notificaciones/', data)
        # ReadOnlyModelViewSet no tiene create
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_filtrar_por_tipo(self):
        """Test filtro por tipo de notificación."""
        Notificacion.objects.create(usuario=self.usuario, titulo='Info', mensaje='Test', tipo='info')
        Notificacion.objects.create(usuario=self.usuario, titulo='Warning', mensaje='Test', tipo='warning')
        Notificacion.objects.create(usuario=self.usuario, titulo='Error', mensaje='Test', tipo='error')

        response = self.client.get('/api/notificaciones/?tipo=warning')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get('results', [])), 1)

    def test_filtrar_por_leida(self):
        """Test filtro por estado leída."""
        Notificacion.objects.create(usuario=self.usuario, titulo='Leida', mensaje='Test', leida=True)
        Notificacion.objects.create(usuario=self.usuario, titulo='No leida', mensaje='Test', leida=False)

        response = self.client.get('/api/notificaciones/?leida=false')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get('results', [])), 1)
        self.assertEqual(response.data['results'][0]['titulo'], 'No leida')
