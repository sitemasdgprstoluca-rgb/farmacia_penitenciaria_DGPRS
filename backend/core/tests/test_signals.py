"""Tests para signals automáticos relacionados con requisiciones."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Centro, Requisicion, Notificacion

User = get_user_model()


class SignalsTest(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(username='testuser', password='test123')
        self.centro = Centro.objects.create(clave='CTR001', nombre='Centro Test')

    def test_notificacion_creada_al_autorizar(self):
        # Usar campos reales de la BD: solicitante, centro_destino, numero
        req = Requisicion.objects.create(
            numero='TEST-001',
            solicitante=self.usuario, 
            centro_destino=self.centro, 
            estado='enviada'
        )

        req.estado = 'autorizada'
        req.autorizador = self.usuario
        req.save()

        # Notificacion usa campo datos={requisicion_id: ...} en vez de requisicion=
        notif = Notificacion.objects.filter(usuario=self.usuario, datos__requisicion_id=req.id).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.tipo, 'success')

    def test_notificacion_creada_al_rechazar(self):
        req = Requisicion.objects.create(
            numero='TEST-002',
            solicitante=self.usuario, 
            centro_destino=self.centro, 
            estado='enviada'
        )

        req.estado = 'rechazada'
        req.notas = 'Stock insuficiente'  # Campo real es 'notas'
        req.autorizador = self.usuario
        req.save()

        notif = Notificacion.objects.filter(usuario=self.usuario, datos__requisicion_id=req.id).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.tipo, 'warning')
