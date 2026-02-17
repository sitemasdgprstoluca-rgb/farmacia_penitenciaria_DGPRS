"""
TEST MASIVO DE LÓGICA DE NEGOCIO - CONTRATOS GLOBALES
======================================================

Autor: Sistema Farmacia Penitenciaria
Fecha: 2026-02-17

OBJETIVO:
Validar que el sistema calcula correctamente todos los campos relacionados con
contratos globales, especialmente la diferencia entre:
- cantidad_inicial (recibido total) → Afecta contratos
- cantidad_actual (disponible ahora) → NO afecta contratos

ESCENARIOS CRÍTICOS:
1. ✅ Contrato 500, recibido 200, salió 100 → Pendiente = 300 (NO 400)
2. ✅ Múltiples lotes del mismo contrato
3. ✅ Escenarios de exceso (recibido > contratado)
4. ✅ Inventario vs Recibido (cantidad_actual vs cantidad_inicial)
5. ✅ Endpoint /api/lotes/ incluye todos los campos
6. ✅ Endpoint /api/lotes/consolidados/ incluye todos los campos
"""

import os
import sys
import django
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from core.models import Producto, Lote, Centro
from datetime import date, datetime
import json

User = get_user_model()


class TestLogicaNegocioContratosGlobales(TransactionTestCase):
    """
    Test masivo de lógica de negocio para contratos globales.
    Usa TransactionTestCase para permitir reset de DB entre tests.
    """
    
    def setUp(self):
        """Setup inicial: crear usuario, centro, producto base"""
        self.user = User.objects.create_user(
            username='test_admin',
            password='test123',
            email='test@test.com',
            rol='admin'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Centro de prueba
        self.centro = Centro.objects.create(
            nombre='Centro Test',
            clave_centro='CT001',
            activo=True
        )
        
        # Producto de prueba
        self.producto = Producto.objects.create(
            clave_producto='TEST-001',
            nombre_producto='Producto Test',
            descripcion='Producto para pruebas de contratos',
            activo=True
        )
    
    def test_escenario_1_logica_basica_contrato(self):
        """
        ESCENARIO 1: Lógica básica de contrato
        - Contrato Global: 500
        - Lote creado: inicial=200, actual=200
        - Esperado: pendiente_global=300, inventario=200
        """
        print("\n" + "="*80)
        print("TEST 1: LÓGICA BÁSICA DE CONTRATO")
        print("="*80)
        
        lote = Lote.objects.create(
            producto=self.producto,
            centro=self.centro,
            numero_lote='L001',
            numero_contrato='CONT-001',
            cantidad_contrato_global=500,
            cantidad_inicial=200,
            cantidad_actual=200,
            fecha_recepcion=date.today(),
            fecha_caducidad=date(2027, 12, 31),
            activo=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Llamar al endpoint para obtener el lote con cálculos
        response = self.client.get(f'/api/lotes/{lote.id}/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        print(f"✓ Contrato Global: {data['cantidad_contrato_global']}")
        print(f"✓ Recibido (inicial): {data['cantidad_inicial']}")
        print(f"✓ Inventario (actual): {data['cantidad_actual']}")
        print(f"✓ Total Recibido Global: {data['cantidad_recibido_global']}")
        print(f"✓ Total Inventario Global: {data['total_inventario_global']}")
        print(f"✓ Pendiente Global: {data['cantidad_pendiente_global']}")
        
        # Validaciones
        self.assertEqual(data['cantidad_contrato_global'], 500)
        self.assertEqual(data['cantidad_inicial'], 200)
        self.assertEqual(data['cantidad_actual'], 200)
        self.assertEqual(data['cantidad_recibido_global'], 200)
        self.assertEqual(data['total_inventario_global'], 200)
        self.assertEqual(data['cantidad_pendiente_global'], 300)  # 500 - 200
        
        print("\n✅ TEST 1 PASADO: Lógica básica correcta\n")
    
    def test_escenario_2_salidas_no_afectan_contrato(self):
        """
        ESCENARIO 2: Las salidas NO afectan el cálculo del contrato
        - Contrato Global: 500
        - Recibido: 200 (cantidad_inicial)
        - Sale: 100 (cantidad_actual = 100)
        - Esperado: pendiente_global=300 (NO 400), inventario=100
        """
        print("\n" + "="*80)
        print("TEST 2: SALIDAS NO AFECTAN CONTRATO")
        print("="*80)
        
        lote = Lote.objects.create(
            producto=self.producto,
            centro=self.centro,
            numero_lote='L002',
            numero_contrato='CONT-002',
            cantidad_contrato_global=500,
            cantidad_inicial=200,  # Lo que se recibió
            cantidad_actual=100,   # Después de salir 100
            fecha_recepcion=date.today(),
            fecha_caducidad=date(2027, 12, 31),
            activo=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        response = self.client.get(f'/api/lotes/{lote.id}/')
        data = response.json()
        
        print(f"✓ Contrato Global: {data['cantidad_contrato_global']}")
        print(f"✓ Total Recibido Global (inicial): {data['cantidad_recibido_global']}")
        print(f"✓ Total Inventario Global (actual): {data['total_inventario_global']}")
        print(f"✓ Cantidad que salió: {200 - 100} = 100")
        print(f"✓ Pendiente Global: {data['cantidad_pendiente_global']}")
        
        # CRÍTICO: Las salidas NO afectan el contrato
        self.assertEqual(data['cantidad_recibido_global'], 200)  # Usa cantidad_inicial
        self.assertEqual(data['total_inventario_global'], 100)   # Usa cantidad_actual
        self.assertEqual(data['cantidad_pendiente_global'], 300)  # 500 - 200 (NO 500 - 100)
        
        print("\n✅ TEST 2 PASADO: Las salidas NO afectan el contrato (pendiente=300, NO 400)\n")
    
    def test_escenario_3_multiples_lotes_mismo_contrato(self):
        """
        ESCENARIO 3: Múltiples lotes del mismo contrato
        - Contrato Global: 1000
        - Lote 1: inicial=300, actual=250 (salió 50)
        - Lote 2: inicial=400, actual=400 (sin salidas)
        - Lote 3: inicial=200, actual=150 (salió 50)
        - Esperado: recibido=900, inventario=800, pendiente=100
        """
        print("\n" + "="*80)
        print("TEST 3: MÚLTIPLES LOTES DEL MISMO CONTRATO")
        print("="*80)
        
        lotes = [
            Lote.objects.create(
                producto=self.producto,
                centro=self.centro,
                numero_lote='L003-1',
                numero_contrato='CONT-003',
                cantidad_contrato_global=1000,
                cantidad_inicial=300,
                cantidad_actual=250,
                fecha_recepcion=date.today(),
                fecha_caducidad=date(2027, 12, 31),
                activo=True,
                created_by=self.user,
                updated_by=self.user
            ),
            Lote.objects.create(
                producto=self.producto,
                centro=self.centro,
                numero_lote='L003-2',
                numero_contrato='CONT-003',
                cantidad_contrato_global=1000,
                cantidad_inicial=400,
                cantidad_actual=400,
                fecha_recepcion=date.today(),
                fecha_caducidad=date(2027, 12, 31),
                activo=True,
                created_by=self.user,
                updated_by=self.user
            ),
            Lote.objects.create(
                producto=self.producto,
                centro=self.centro,
                numero_lote='L003-3',
                numero_contrato='CONT-003',
                cantidad_contrato_global=1000,
                cantidad_inicial=200,
                cantidad_actual=150,
                fecha_recepcion=date.today(),
                fecha_caducidad=date(2027, 12, 31),
                activo=True,
                created_by=self.user,
                updated_by=self.user
            )
        ]
        
        response = self.client.get(f'/api/lotes/{lotes[0].id}/')
        data = response.json()
        
        print(f"✓ Contrato Global: {data['cantidad_contrato_global']}")
        print(f"✓ Lote 1: inicial=300, actual=250")
        print(f"✓ Lote 2: inicial=400, actual=400")
        print(f"✓ Lote 3: inicial=200, actual=150")
        print(f"✓ Total Recibido Global: {data['cantidad_recibido_global']}")
        print(f"✓ Total Inventario Global: {data['total_inventario_global']}")
        print(f"✓ Pendiente Global: {data['cantidad_pendiente_global']}")
        
        self.assertEqual(data['cantidad_recibido_global'], 900)  # 300+400+200
        self.assertEqual(data['total_inventario_global'], 800)   # 250+400+150
        self.assertEqual(data['cantidad_pendiente_global'], 100)  # 1000-900
        
        print("\n✅ TEST 3 PASADO: Suma correcta de múltiples lotes\n")
    
    def test_escenario_4_exceso_de_recepcion(self):
        """
        ESCENARIO 4: Exceso (se recibió más de lo contratado)
        - Contrato Global: 300
        - Lote 1: inicial=200
        - Lote 2: inicial=250
        - Total recibido: 450
        - Esperado: pendiente=-150 (exceso)
        """
        print("\n" + "="*80)
        print("TEST 4: EXCESO DE RECEPCIÓN (RECIBIDO > CONTRATADO)")
        print("="*80)
        
        lotes = [
            Lote.objects.create(
                producto=self.producto,
                centro=self.centro,
                numero_lote='L004-1',
                numero_contrato='CONT-004',
                cantidad_contrato_global=300,
                cantidad_inicial=200,
                cantidad_actual=200,
                fecha_recepcion=date.today(),
                fecha_caducidad=date(2027, 12, 31),
                activo=True,
                created_by=self.user,
                updated_by=self.user
            ),
            Lote.objects.create(
                producto=self.producto,
                centro=self.centro,
                numero_lote='L004-2',
                numero_contrato='CONT-004',
                cantidad_contrato_global=300,
                cantidad_inicial=250,
                cantidad_actual=250,
                fecha_recepcion=date.today(),
                fecha_caducidad=date(2027, 12, 31),
                activo=True,
                created_by=self.user,
                updated_by=self.user
            )
        ]
        
        response = self.client.get(f'/api/lotes/{lotes[0].id}/')
        data = response.json()
        
        print(f"✓ Contrato Global: {data['cantidad_contrato_global']}")
        print(f"✓ Total Recibido: {data['cantidad_recibido_global']}")
        print(f"✓ Pendiente Global: {data['cantidad_pendiente_global']}")
        print(f"✓ Exceso: {abs(data['cantidad_pendiente_global'])}")
        
        self.assertEqual(data['cantidad_recibido_global'], 450)  # 200+250
        self.assertEqual(data['cantidad_pendiente_global'], -150)  # 300-450 (negativo = exceso)
        
        print("✓ El pendiente es NEGATIVO (exceso detectado)")
        print("\n✅ TEST 4 PASADO: Detección correcta de exceso\n")
    
    def test_escenario_5_endpoint_consolidados(self):
        """
        ESCENARIO 5: Validar que endpoint /api/lotes/consolidados/ incluye todos los campos
        """
        print("\n" + "="*80)
        print("TEST 5: ENDPOINT CONSOLIDADOS INCLUYE TODOS LOS CAMPOS")
        print("="*80)
        
        Lote.objects.create(
            producto=self.producto,
            centro=self.centro,
            numero_lote='L005',
            numero_contrato='CONT-005',
            cantidad_contrato_global=800,
            cantidad_inicial=300,
            cantidad_actual=250,
            fecha_recepcion=date.today(),
            fecha_caducidad=date(2027, 12, 31),
            activo=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        response = self.client.get('/api/lotes/consolidados/?page_size=100')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        if 'results' in data:
            lotes = data['results']
        else:
            lotes = data
        
        self.assertGreater(len(lotes), 0)
        lote = lotes[0]
        
        print(f"✓ Total lotes consolidados: {len(lotes)}")
        print(f"✓ Campos del primer lote:")
        print(f"  - cantidad_contrato_global: {lote.get('cantidad_contrato_global')}")
        print(f"  - cantidad_recibido_global: {lote.get('cantidad_recibido_global')}")
        print(f"  - total_inventario_global: {lote.get('total_inventario_global')}")
        print(f"  - cantidad_pendiente_global: {lote.get('cantidad_pendiente_global')}")
        
        # Validar que todos los campos existen
        self.assertIn('cantidad_contrato_global', lote)
        self.assertIn('cantidad_recibido_global', lote)
        self.assertIn('total_inventario_global', lote)
        self.assertIn('cantidad_pendiente_global', lote)
        
        print("\n✅ TEST 5 PASADO: Endpoint consolidados incluye todos los campos\n")
    
    def test_escenario_6_validacion_matematica_completa(self):
        """
        ESCENARIO 6: Validación matemática completa
        Caso real del usuario:
        - Contrato: 500
        - Recibido: 200 (cantidad_inicial)
        - Salió: 100 (cantidad_actual = 100)
        - Deben registrarse 300 (NO 400)
        """
        print("\n" + "="*80)
        print("TEST 6: VALIDACIÓN MATEMÁTICA COMPLETA (CASO REAL)")
        print("="*80)
        print("\nEscenario del usuario:")
        print("- Si del contrato de 500 se recibieron 200")
        print("- Y 100 fueron entregados a un centro")
        print("- Deben registrarse solo los 300 que faltan")
        print("- Los 200 recibidos se contabilizan a pesar de los 100 que salieron")
        print("")
        
        lote = Lote.objects.create(
            producto=self.producto,
            centro=self.centro,
            numero_lote='L006',
            numero_contrato='CONT-006',
            cantidad_contrato_global=500,
            cantidad_inicial=200,  # Lo que se RECIBIÓ
            cantidad_actual=100,   # Lo que QUEDA (salió 100)
            fecha_recepcion=date.today(),
            fecha_caducidad=date(2027, 12, 31),
            activo=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        response = self.client.get(f'/api/lotes/{lote.id}/')
        data = response.json()
        
        print("RESULTADOS:")
        print(f"✓ Contrato Global: {data['cantidad_contrato_global']}")
        print(f"✓ Total Recibido (cantidad_inicial): {data['cantidad_recibido_global']}")
        print(f"✓ Total Inventario (cantidad_actual): {data['total_inventario_global']}")
        print(f"✓ Cantidad que salió: {data['cantidad_inicial'] - data['cantidad_actual']}")
        print(f"✓ Pendiente por recibir: {data['cantidad_pendiente_global']}")
        print("")
        
        # Validaciones críticas
        self.assertEqual(data['cantidad_contrato_global'], 500, "El contrato debe ser 500")
        self.assertEqual(data['cantidad_recibido_global'], 200, "Se recibieron 200 (usa cantidad_inicial)")
        self.assertEqual(data['total_inventario_global'], 100, "Quedan 100 en inventario (usa cantidad_actual)")
        self.assertEqual(data['cantidad_pendiente_global'], 300, "Faltan 300 por recibir (500-200, NO 500-100)")
        
        print("VALIDACIÓN LÓGICA:")
        print(f"✓ Pendiente = Contrato - Recibido")
        print(f"✓ {data['cantidad_pendiente_global']} = {data['cantidad_contrato_global']} - {data['cantidad_recibido_global']}")
        print(f"✓ Las salidas NO afectan el pendiente del contrato")
        print(f"✓ El inventario actual es {data['total_inventario_global']} (para verificación)")
        
        print("\n✅ TEST 6 PASADO: Lógica correcta según requerimiento del usuario\n")


def run_all_tests():
    """Ejecutar todos los tests"""
    import unittest
    
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "TEST MASIVO DE LÓGICA DE NEGOCIO" + " "*26 + "║")
    print("║" + " "*25 + "CONTRATOS GLOBALES" + " "*35 + "║")
    print("╚" + "="*78 + "╝")
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestLogicaNegocioContratosGlobales)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*80)
    print("RESUMEN FINAL")
    print("="*80)
    print(f"Tests ejecutados: {result.testsRun}")
    print(f"✅ Pasados: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Fallidos: {len(result.failures)}")
    print(f"⚠️  Errores: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n" + "🎉 " * 20)
        print("TODOS LOS TESTS PASARON EXITOSAMENTE")
        print("La lógica de negocio es CORRECTA")
        print("🎉 " * 20)
        return True
    else:
        print("\n❌ ALGUNOS TESTS FALLARON - REVISAR LÓGICA")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
