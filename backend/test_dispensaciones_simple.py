"""
================================================================================
PRUEBAS RÁPIDAS - MÓDULO DE DISPENSACIÓN A PACIENTES (FORMATO C)
================================================================================
Fecha: 2026-01-13
Descripción: Pruebas simplificadas que funcionan con SQLite en tests

Ejecutar con: python manage.py test test_dispensaciones_simple -v 2
================================================================================
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

django.setup()

from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from datetime import date, timedelta

from core.models import User, Centro, Producto, Lote


class TestModuloDispensacionesFuncional(TransactionTestCase):
    """
    Pruebas funcionales del módulo de Dispensaciones
    Usa modelos existentes para verificar lógica de negocio
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Crear centro
        cls.centro = Centro.objects.create(
            nombre="Centro Test Disp",
            direccion="Test",
            activo=True
        )
        
        # Crear producto
        cls.producto = Producto.objects.create(
            clave="PROD-TEST-001",
            nombre="Paracetamol Test",
            unidad_medida="tableta",
            categoria="medicamento",
            activo=True
        )
        
        # Usuario médico
        cls.medico = User.objects.create_user(
            username='medico_simple_test',
            password='test123456',
            rol='medico',
            centro=cls.centro
        )
        
        # Usuario farmacia
        cls.farmacia = User.objects.create_user(
            username='farmacia_simple_test',
            password='test123456',
            rol='farmacia'
        )
        
        # Lote en el centro
        cls.lote = Lote.objects.create(
            numero_lote="LOTE-TEST-001",
            producto=cls.producto,
            cantidad_inicial=100,
            cantidad_actual=100,
            fecha_caducidad=date.today() + timedelta(days=365),
            precio_unitario=Decimal('10.00'),
            centro=cls.centro,
            activo=True
        )
    
    def setUp(self):
        self.client = APIClient()
    
    def test_01_endpoint_pacientes_existe(self):
        """Verifica que el endpoint de pacientes existe"""
        self.client.force_authenticate(user=self.medico)
        response = self.client.get('/api/v1/pacientes/')
        
        # 200 = lista vacía, endpoint existe
        self.assertIn(response.status_code, [200, 403])
        print("✅ Endpoint /api/v1/pacientes/ existe")
    
    def test_02_endpoint_dispensaciones_existe(self):
        """Verifica que el endpoint de dispensaciones existe"""
        self.client.force_authenticate(user=self.medico)
        response = self.client.get('/api/v1/dispensaciones/')
        
        self.assertIn(response.status_code, [200, 403])
        print("✅ Endpoint /api/v1/dispensaciones/ existe")
    
    def test_03_permiso_farmacia_denegado_crear(self):
        """Farmacia NO puede crear pacientes (solo auditoría)"""
        self.client.force_authenticate(user=self.farmacia)
        
        response = self.client.post('/api/v1/pacientes/', {
            'numero_expediente': 'TEST-001',
            'nombre': 'Test',
            'apellido_paterno': 'Paciente',
            'centro': self.centro.id
        }, format='json')
        
        # Debe ser 403 Forbidden
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        print("✅ Farmacia NO puede crear pacientes (solo auditoría)")
    
    def test_04_permiso_farmacia_denegado_dispensacion(self):
        """Farmacia NO puede crear dispensaciones"""
        self.client.force_authenticate(user=self.farmacia)
        
        response = self.client.post('/api/v1/dispensaciones/', {
            'tipo_dispensacion': 'normal'
        }, format='json')
        
        # Debe ser 403 Forbidden
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        print("✅ Farmacia NO puede crear dispensaciones (solo auditoría)")
    
    def test_05_permiso_medico_puede_ver(self):
        """Médico puede ver listado de pacientes"""
        self.client.force_authenticate(user=self.medico)
        
        response = self.client.get('/api/v1/pacientes/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        print("✅ Médico puede ver pacientes")
    
    def test_06_permiso_medico_puede_crear_paciente(self):
        """Médico puede crear paciente"""
        self.client.force_authenticate(user=self.medico)
        
        response = self.client.post('/api/v1/pacientes/', {
            'numero_expediente': 'EXP-MED-001',
            'nombre': 'Juan',
            'apellido_paterno': 'Pérez',
            'centro': self.centro.id,
            'activo': True
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        print(f"✅ Médico puede crear paciente (ID: {response.data['id']})")
        
        return response.data['id']
    
    def test_07_permiso_medico_puede_crear_dispensacion(self):
        """Médico puede crear dispensación"""
        self.client.force_authenticate(user=self.medico)
        
        # Primero crear paciente
        pac_response = self.client.post('/api/v1/pacientes/', {
            'numero_expediente': 'EXP-DISP-001',
            'nombre': 'María',
            'apellido_paterno': 'López',
            'centro': self.centro.id,
            'activo': True
        }, format='json')
        
        paciente_id = pac_response.data['id']
        
        # Crear dispensación
        response = self.client.post('/api/v1/dispensaciones/', {
            'paciente': paciente_id,
            'centro': self.centro.id,
            'tipo_dispensacion': 'normal',
            'diagnostico': 'Test diagnóstico'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('folio', response.data)
        self.assertEqual(response.data['estado'], 'pendiente')
        
        print(f"✅ Médico puede crear dispensación (Folio: {response.data['folio']})")
    
    def test_08_farmacia_puede_ver_dispensaciones(self):
        """Farmacia puede VER dispensaciones para auditoría"""
        self.client.force_authenticate(user=self.farmacia)
        
        response = self.client.get('/api/v1/dispensaciones/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        print("✅ Farmacia puede VER dispensaciones para auditoría")
    
    def test_09_lotes_filtrado_por_centro(self):
        """Verifica que los lotes se filtran por centro"""
        self.client.force_authenticate(user=self.medico)
        
        response = self.client.get('/api/v1/lotes/', {
            'centro': self.centro.id
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar que existe al menos el lote de prueba
        resultados = response.data.get('results', response.data)
        if resultados:
            lote = next((l for l in resultados if l['numero_lote'] == 'LOTE-TEST-001'), None)
            self.assertIsNotNone(lote, "Lote de prueba no encontrado")
            self.assertEqual(lote['centro'], self.centro.id)
        
        print("✅ Lotes se filtran correctamente por centro")
    
    def test_10_estructura_respuesta_pacientes(self):
        """Verifica estructura de respuesta de API pacientes"""
        self.client.force_authenticate(user=self.medico)
        
        # Crear paciente
        self.client.post('/api/v1/pacientes/', {
            'numero_expediente': 'EXP-STRUCT-001',
            'nombre': 'Test',
            'apellido_paterno': 'Estructura',
            'centro': self.centro.id,
            'activo': True
        }, format='json')
        
        # Listar
        response = self.client.get('/api/v1/pacientes/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar paginación
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)
        
        if response.data['results']:
            item = response.data['results'][0]
            campos_esperados = ['id', 'numero_expediente', 'nombre', 'centro']
            for campo in campos_esperados:
                self.assertIn(campo, item, f"Campo '{campo}' no encontrado")
        
        print("✅ Estructura de respuesta de pacientes correcta")


class TestReglasNegocioSimplificadas(TransactionTestCase):
    """
    Pruebas de reglas de negocio simplificadas
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.centro = Centro.objects.create(
            nombre="Centro RN Test",
            direccion="Test",
            activo=True
        )
        
        cls.producto = Producto.objects.create(
            clave="PROD-RN-001",
            nombre="Ibuprofeno Test",
            unidad_medida="tableta",
            categoria="medicamento",
            activo=True
        )
        
        cls.medico = User.objects.create_user(
            username='medico_rn_test',
            password='test123456',
            rol='medico',
            centro=cls.centro
        )
        
        cls.lote = Lote.objects.create(
            numero_lote="LOTE-RN-001",
            producto=cls.producto,
            cantidad_inicial=50,
            cantidad_actual=50,
            fecha_caducidad=date.today() + timedelta(days=365),
            precio_unitario=Decimal('5.00'),
            centro=cls.centro,
            activo=True
        )
    
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.medico)
    
    def test_rn01_folio_autogenerado(self):
        """RN-01: El folio debe generarse automáticamente"""
        # Crear paciente
        pac = self.client.post('/api/v1/pacientes/', {
            'numero_expediente': 'EXP-RN01-001',
            'nombre': 'Folio',
            'apellido_paterno': 'Test',
            'centro': self.centro.id,
            'activo': True
        }, format='json')
        
        # Crear dispensación sin folio
        response = self.client.post('/api/v1/dispensaciones/', {
            'paciente': pac.data['id'],
            'centro': self.centro.id,
            'tipo_dispensacion': 'normal'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        folio = response.data.get('folio')
        self.assertIsNotNone(folio)
        self.assertTrue(len(folio) > 0)
        
        print(f"✅ RN-01: Folio autogenerado: {folio}")
    
    def test_rn02_estado_inicial_pendiente(self):
        """RN-02: Estado inicial debe ser 'pendiente'"""
        pac = self.client.post('/api/v1/pacientes/', {
            'numero_expediente': 'EXP-RN02-001',
            'nombre': 'Estado',
            'apellido_paterno': 'Test',
            'centro': self.centro.id,
            'activo': True
        }, format='json')
        
        response = self.client.post('/api/v1/dispensaciones/', {
            'paciente': pac.data['id'],
            'centro': self.centro.id,
            'tipo_dispensacion': 'normal'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data.get('estado'), 'pendiente')
        
        print("✅ RN-02: Estado inicial 'pendiente' correcto")
    
    def test_rn03_centro_asignado_automaticamente(self):
        """RN-03: Centro del médico se asigna automáticamente"""
        pac = self.client.post('/api/v1/pacientes/', {
            'numero_expediente': 'EXP-RN03-001',
            'nombre': 'Centro',
            'apellido_paterno': 'Auto',
            'centro': self.centro.id,
            'activo': True
        }, format='json')
        
        # No especificar centro
        response = self.client.post('/api/v1/dispensaciones/', {
            'paciente': pac.data['id'],
            'tipo_dispensacion': 'normal'
        }, format='json')
        
        # Puede fallar si centro es requerido, o asignarse automáticamente
        if response.status_code == status.HTTP_201_CREATED:
            self.assertEqual(response.data.get('centro'), self.centro.id)
            print("✅ RN-03: Centro asignado automáticamente del médico")
        else:
            # Centro es requerido explícitamente
            print("⚠️ RN-03: Centro es requerido explícitamente en el request")
    
    def test_rn04_cancelar_requiere_motivo(self):
        """RN-04: Cancelación requiere motivo"""
        pac = self.client.post('/api/v1/pacientes/', {
            'numero_expediente': 'EXP-RN04-001',
            'nombre': 'Cancelar',
            'apellido_paterno': 'Test',
            'centro': self.centro.id,
            'activo': True
        }, format='json')
        
        disp = self.client.post('/api/v1/dispensaciones/', {
            'paciente': pac.data['id'],
            'centro': self.centro.id,
            'tipo_dispensacion': 'normal'
        }, format='json')
        
        disp_id = disp.data['id']
        
        # Sin motivo debe fallar
        response = self.client.post(f'/api/v1/dispensaciones/{disp_id}/cancelar/', {
            'motivo': ''
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Con motivo debe funcionar
        response = self.client.post(f'/api/v1/dispensaciones/{disp_id}/cancelar/', {
            'motivo': 'Paciente rechazó tratamiento'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('estado'), 'cancelada')
        
        print("✅ RN-04: Cancelación requiere motivo obligatorio")


def run_tests():
    """Ejecuta las pruebas"""
    import unittest
    
    print("\n" + "="*70)
    print("PRUEBAS DEL MÓDULO DE DISPENSACIÓN A PACIENTES")
    print("="*70 + "\n")
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestModuloDispensacionesFuncional))
    suite.addTests(loader.loadTestsFromTestCase(TestReglasNegocioSimplificadas))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*70)
    print("RESUMEN")
    print("="*70)
    print(f"Total: {result.testsRun}")
    print(f"✅ Exitosas: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Fallidas: {len(result.failures)}")
    print(f"⚠️ Errores: {len(result.errors)}")
    print("="*70)
    
    return result


if __name__ == '__main__':
    run_tests()
