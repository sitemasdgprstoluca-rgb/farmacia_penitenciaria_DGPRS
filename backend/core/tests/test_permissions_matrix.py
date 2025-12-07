"""Tests basicos de permisos por roles."""

from decimal import Decimal
from datetime import timedelta
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone

from core.models import Centro, Requisicion, Producto, DetalleRequisicion, Lote

User = get_user_model()


class PermissionsMatrixTest(APITestCase):
    def setUp(self):
        self.centro_1 = Centro.objects.create(clave='CTR001', nombre='Centro 1')
        self.centro_2 = Centro.objects.create(clave='CTR002', nombre='Centro 2')

        self.superuser = User.objects.create_superuser(username='super', email='super@test.com', password='test123')
        self.user_centro1 = User.objects.create_user(username='user1', password='test123', centro=self.centro_1)
        self.user_centro2 = User.objects.create_user(username='user2', password='test123', centro=self.centro_2)

        self.client = APIClient()

    def test_user_no_ve_requisicion_de_otro_centro(self):
        # Usar campos reales: numero, solicitante, centro_destino
        req = Requisicion.objects.create(numero='PERM-001', solicitante=self.user_centro2, centro_destino=self.centro_2)
        self.client.force_authenticate(user=self.user_centro1)
        resp = self.client.get(f'/api/requisiciones/{req.id}/')
        self.assertNotEqual(resp.status_code, status.HTTP_200_OK)

    def test_superuser_si_ve_requisicion_ajena(self):
        req = Requisicion.objects.create(numero='PERM-002', solicitante=self.user_centro2, centro_destino=self.centro_2)
        self.client.force_authenticate(user=self.superuser)
        resp = self.client.get(f'/api/requisiciones/{req.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_autorizar_requiere_superuser(self):
        # Crear producto para el detalle
        producto = Producto.objects.create(
            clave='PROD001',
            descripcion='Producto Test',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('100.00')
        )
        
        req = Requisicion.objects.create(
            numero='PERM-003',
            solicitante=self.user_centro1,
            centro_destino=self.centro_1,
            estado='enviada'
        )
        
        # Agregar detalle a la requisición
        detalle = DetalleRequisicion.objects.create(
            requisicion=req,
            producto=producto,
            cantidad_solicitada=10
        )
        
        # ISS-003: Crear lote en farmacia central para que haya stock
        Lote.objects.create(
            producto=producto,
            centro=None,  # Farmacia central
            numero_lote="PERM-001",
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
        
        # IMPORTANTE: Limpiar autenticación y autenticar como user normal
        self.client.force_authenticate(user=None)
        self.client.force_authenticate(user=self.user_centro1)
        
        # user normal NO DEBE poder autorizar
        resp = self.client.post(f'/api/requisiciones/{req.id}/autorizar/', {
            'items': [{'id': detalle.id, 'cantidad_autorizada': 10}]
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN,
                        f"Usuario normal recibió {resp.status_code} en lugar de 403. Data: {resp.data}")

        # Limpiar y autenticar como superuser
        self.client.force_authenticate(user=None)
        self.client.force_authenticate(user=self.superuser)
        
        # ISS-003: superuser SÍ DEBE poder autorizar (ahora requiere enviar items)
        resp = self.client.post(f'/api/requisiciones/{req.id}/autorizar/', {
            'items': [{'id': detalle.id, 'cantidad_autorizada': 10}]
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK,
                        f"Superuser recibió {resp.status_code} en lugar de 200. Data: {resp.data}")
