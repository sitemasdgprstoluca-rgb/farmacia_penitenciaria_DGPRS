"""Tests para notificaciones."""

from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

from core.models import Centro, Requisicion, Notificacion

User = get_user_model()


class NotificacionModelTest(TestCase):
    """Tests de modelo Notificacion."""

    def setUp(self):
        self.usuario = User.objects.create_user(username='testuser', password='test123')
        self.centro = Centro.objects.create(clave='CTR001', nombre='Centro Test')
        self.requisicion = Requisicion.objects.create(usuario_solicita=self.usuario, centro=self.centro)

    def test_crear_notificacion(self):
        notif = Notificacion.objects.create(
            usuario=self.usuario,
            titulo='Test',
            mensaje='Mensaje test',
            tipo='success'
        )
        self.assertEqual(notif.usuario, self.usuario)
        self.assertFalse(notif.leida)

    def test_notificacion_con_requisicion(self):
        notif = Notificacion.objects.create(
            usuario=self.usuario,
            titulo='Requisicion aprobada',
            mensaje='Tu requisicion fue aprobada',
            requisicion=self.requisicion,
            tipo='success'
        )
        self.assertEqual(notif.requisicion, self.requisicion)

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

        response = self.client.post(f'/api/notificaciones/{notif.id}/marcar_leida/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notif.refresh_from_db()
        self.assertTrue(notif.leida)

    def test_contar_no_leidas(self):
        Notificacion.objects.create(usuario=self.usuario, titulo='No leida 1', mensaje='Test', leida=False)
        Notificacion.objects.create(usuario=self.usuario, titulo='Leida', mensaje='Test', leida=True)
        Notificacion.objects.create(usuario=self.usuario, titulo='No leida 2', mensaje='Test', leida=False)

        response = self.client.get('/api/notificaciones/no_leidas_count/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('no_leidas'), 2)

    def test_notificacion_sin_autenticacion(self):
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/notificaciones/')
        # Acepta tanto 401 (UNAUTHORIZED) como 403 (FORBIDDEN)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
