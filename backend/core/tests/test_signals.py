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
        req = Requisicion.objects.create(usuario_solicita=self.usuario, centro=self.centro, estado='enviada')

        req.estado = 'autorizada'
        req.usuario_autoriza = self.usuario
        req.save()

        notif = Notificacion.objects.filter(usuario=self.usuario, requisicion=req).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.tipo, 'success')

    def test_notificacion_creada_al_rechazar(self):
        req = Requisicion.objects.create(usuario_solicita=self.usuario, centro=self.centro, estado='enviada')

        req.estado = 'rechazada'
        req.motivo_rechazo = 'Stock insuficiente'
        req.usuario_autoriza = self.usuario
        req.save()

        notif = Notificacion.objects.filter(usuario=self.usuario, requisicion=req).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.tipo, 'warning')
