# -*- coding: utf-8 -*-
"""
Tests para el fix ISS-FIX-500: Error 500 en movimientos de transferencia.

Verifica que:
1. Las transferencias desde Almacén Central a Centros funcionen correctamente
2. El centro_id se convierte correctamente a objeto Centro
3. skip_centro_check funciona para transferencias de admin/farmacia
"""
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal

from core.models import Centro, Producto, Lote

User = get_user_model()


class MovimientoTransferenciaTestCase(TestCase):
    """Tests para transferencias desde Almacén Central."""
    
    @classmethod
    def setUpTestData(cls):
        """Configuración inicial de datos de prueba."""
        # Crear usuario farmacia
        cls.user_farmacia = User.objects.create_user(
            username='test_farmacia',
            password='testpass123',
            email='farmacia@test.com',
            rol='farmacia',
            is_active=True
        )
        
        # Crear usuario admin
        cls.user_admin = User.objects.create_user(
            username='test_admin',
            password='testpass123',
            email='admin@test.com',
            rol='admin',
            is_superuser=True,
            is_active=True
        )
        
        # Crear centro destino
        cls.centro_destino = Centro.objects.create(
            nombre='Centro Penitenciario Test',
            direccion='Dirección de prueba',
            activo=True
        )
        
        # Crear producto
        cls.producto = Producto.objects.create(
            clave='TEST-001',
            nombre='Producto de Prueba',
            descripcion='Descripción de prueba',
            unidad_medida='pieza',
            categoria='medicamento',
            stock_minimo=10,
            activo=True
        )
        
        # Crear lote en Almacén Central (centro=None)
        cls.lote_almacen = Lote.objects.create(
            numero_lote='LOTE-TEST-001',
            producto=cls.producto,
            cantidad_inicial=1000,
            cantidad_actual=1000,
            fecha_caducidad='2027-12-31',
            precio_unitario=Decimal('10.00'),
            centro=None,  # Almacén Central
            activo=True
        )
    
    def setUp(self):
        """Configuración para cada test."""
        self.client = APIClient()
    
    def test_transferencia_farmacia_a_centro_con_id(self):
        """
        Test: Usuario farmacia puede transferir de Almacén Central a Centro
        usando centro_id (int).
        """
        self.client.force_authenticate(user=self.user_farmacia)
        
        data = {
            'tipo': 'salida',
            'lote': self.lote_almacen.id,
            'cantidad': 10,
            'centro': self.centro_destino.id,  # ID como int
            'observaciones': 'Transferencia de prueba a centro',
            'subtipo_salida': 'transferencia'
        }
        
        response = self.client.post('/api/movimientos/', data, format='json')
        
        # Debe ser exitoso (201) y no error 500
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED],
                      f"Esperado 200/201, recibido {response.status_code}: {response.data}")
        
        # Verificar que el stock se actualizó
        self.lote_almacen.refresh_from_db()
        self.assertEqual(self.lote_almacen.cantidad_actual, 990)
    
    def test_transferencia_admin_a_centro_con_id(self):
        """
        Test: Usuario admin puede transferir de Almacén Central a Centro.
        """
        self.client.force_authenticate(user=self.user_admin)
        
        data = {
            'tipo': 'salida',
            'lote': self.lote_almacen.id,
            'cantidad': 5,
            'centro': self.centro_destino.id,
            'observaciones': 'Transferencia admin de prueba',
            'subtipo_salida': 'transferencia'
        }
        
        response = self.client.post('/api/movimientos/', data, format='json')
        
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED],
                      f"Esperado 200/201, recibido {response.status_code}: {response.data}")
    
    def test_transferencia_con_centro_id_string(self):
        """
        Test: El centro_id como string también debe funcionar.
        """
        self.client.force_authenticate(user=self.user_farmacia)
        
        data = {
            'tipo': 'salida',
            'lote': self.lote_almacen.id,
            'cantidad': 3,
            'centro': str(self.centro_destino.id),  # ID como string
            'observaciones': 'Transferencia con centro string',
            'subtipo_salida': 'transferencia'
        }
        
        response = self.client.post('/api/movimientos/', data, format='json')
        
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED],
                      f"Esperado 200/201, recibido {response.status_code}: {response.data}")
    
    def test_transferencia_centro_inexistente(self):
        """
        Test: Transferencia a centro inexistente debe dar error 400, no 500.
        """
        self.client.force_authenticate(user=self.user_farmacia)
        
        data = {
            'tipo': 'salida',
            'lote': self.lote_almacen.id,
            'cantidad': 5,
            'centro': 99999,  # Centro que no existe
            'observaciones': 'Transferencia a centro inexistente',
            'subtipo_salida': 'transferencia'
        }
        
        response = self.client.post('/api/movimientos/', data, format='json')
        
        # Debe ser 400 (bad request), NO 500
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                        f"Esperado 400, recibido {response.status_code}")
        self.assertIn('centro', str(response.data).lower())
    
    def test_stock_insuficiente(self):
        """
        Test: Transferencia con stock insuficiente debe dar error 400.
        """
        self.client.force_authenticate(user=self.user_farmacia)
        
        data = {
            'tipo': 'salida',
            'lote': self.lote_almacen.id,
            'cantidad': 999999,  # Más del stock disponible
            'centro': self.centro_destino.id,
            'observaciones': 'Transferencia con stock insuficiente',
            'subtipo_salida': 'transferencia'
        }
        
        response = self.client.post('/api/movimientos/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class NombreAlmacenCentralTestCase(TestCase):
    """Tests para verificar que se usa 'Almacén Central' consistentemente."""
    
    def test_serializer_get_centro_nombre_almacen(self):
        """
        Test: get_centro_nombre debe retornar 'Almacén Central' cuando no hay centro.
        """
        from core.serializers import MovimientoSerializer
        from core.models import Movimiento
        
        # Crear datos mínimos
        producto = Producto.objects.create(
            clave='TEST-AC-001',
            nombre='Producto Almacén Central',
            unidad_medida='pieza',
            categoria='medicamento'
        )
        
        lote = Lote.objects.create(
            numero_lote='LOTE-AC-001',
            producto=producto,
            cantidad_inicial=100,
            cantidad_actual=100,
            fecha_caducidad='2027-12-31',
            precio_unitario=Decimal('5.00'),
            centro=None  # Almacén Central
        )
        
        mov = Movimiento.objects.create(
            tipo='entrada',
            producto=producto,
            lote=lote,
            cantidad=100,
            motivo='Ingreso inicial'
        )
        
        serializer = MovimientoSerializer(mov)
        centro_nombre = serializer.data.get('centro_nombre')
        
        self.assertEqual(centro_nombre, 'Almacén Central',
                        f"Esperado 'Almacén Central', recibido '{centro_nombre}'")
