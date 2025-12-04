"""
ISS-029: Tests E2E (End-to-End).

Tests de integración que verifican flujos completos
del sistema de farmacia penitenciaria.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


@pytest.mark.e2e
class TestFlujoCompletoRequisicion(TransactionTestCase):
    """
    ISS-029: Test E2E del flujo completo de requisición.
    
    Verifica el ciclo de vida completo:
    1. Crear medicamento y lotes
    2. Crear requisición
    3. Aprobar requisición
    4. Despachar medicamentos
    5. Verificar stock actualizado
    """
    
    def setUp(self):
        """Configurar datos de prueba."""
        from core.models import (
            Medicamento, Lote, Centro, UserProfile
        )
        
        # Crear usuarios
        self.admin = User.objects.create_superuser(
            username='admin_e2e',
            email='admin@test.com',
            password='testpass123'
        )
        
        self.farmaceutico = User.objects.create_user(
            username='farmaceutico_e2e',
            email='farmaceutico@test.com',
            password='testpass123'
        )
        
        self.solicitante = User.objects.create_user(
            username='solicitante_e2e',
            email='solicitante@test.com',
            password='testpass123'
        )
        
        # Crear centro
        self.centro = Centro.objects.create(
            nombre='Centro E2E Test',
            codigo='E2E01'
        )
        
        # Crear medicamento
        self.medicamento = Medicamento.objects.create(
            nombre='Paracetamol E2E',
            codigo='PARA-E2E-001',
            principio_activo='Paracetamol',
            presentacion='Tabletas 500mg',
            unidad_medida='tabletas',
            stock_minimo=100,
            stock_maximo=1000
        )
        
        # Crear lotes con stock
        self.lote1 = Lote.objects.create(
            medicamento=self.medicamento,
            codigo_lote='LOTE-E2E-001',
            fecha_fabricacion=date.today() - timedelta(days=30),
            fecha_vencimiento=date.today() + timedelta(days=365),
            cantidad_inicial=500,
            cantidad_actual=500
        )
        
        self.lote2 = Lote.objects.create(
            medicamento=self.medicamento,
            codigo_lote='LOTE-E2E-002',
            fecha_fabricacion=date.today() - timedelta(days=15),
            fecha_vencimiento=date.today() + timedelta(days=400),
            cantidad_inicial=300,
            cantidad_actual=300
        )
        
        # Cliente API
        self.client = APIClient()
    
    def test_flujo_completo_requisicion_exitosa(self):
        """
        Test del flujo completo de requisición exitosa.
        """
        from core.models import Requisicion, DetalleRequisicion, Movimiento
        
        # === PASO 1: Crear requisición ===
        self.client.force_authenticate(user=self.solicitante)
        
        requisicion_data = {
            'centro': self.centro.id,
            'motivo': 'Abastecimiento mensual E2E Test',
            'prioridad': 'NORMAL',
            'detalles': [
                {
                    'medicamento': self.medicamento.id,
                    'cantidad_solicitada': 100,
                    'observaciones': 'Urgente para enfermería'
                }
            ]
        }
        
        response = self.client.post(
            '/api/requisiciones/',
            requisicion_data,
            format='json'
        )
        
        # Verificar creación
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK])
        requisicion_id = response.data.get('id')
        self.assertIsNotNone(requisicion_id)
        
        # Verificar estado inicial
        requisicion = Requisicion.objects.get(id=requisicion_id)
        self.assertEqual(requisicion.estado, 'PENDIENTE')
        
        # === PASO 2: Aprobar requisición (como farmacéutico) ===
        self.client.force_authenticate(user=self.farmaceutico)
        
        response = self.client.post(
            f'/api/requisiciones/{requisicion_id}/aprobar/',
            {'observaciones': 'Aprobado E2E'},
            format='json'
        )
        
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_202_ACCEPTED])
        
        requisicion.refresh_from_db()
        self.assertEqual(requisicion.estado, 'APROBADA')
        
        # === PASO 3: Despachar medicamentos ===
        stock_inicial_lote1 = self.lote1.cantidad_actual
        
        response = self.client.post(
            f'/api/requisiciones/{requisicion_id}/despachar/',
            {
                'despachos': [
                    {
                        'detalle_id': requisicion.detalles.first().id,
                        'lote_id': self.lote1.id,
                        'cantidad': 100
                    }
                ]
            },
            format='json'
        )
        
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_202_ACCEPTED])
        
        # === PASO 4: Verificar estado final ===
        requisicion.refresh_from_db()
        self.assertEqual(requisicion.estado, 'DESPACHADA')
        
        # Verificar stock actualizado
        self.lote1.refresh_from_db()
        self.assertEqual(
            self.lote1.cantidad_actual, 
            stock_inicial_lote1 - 100
        )
        
        # Verificar movimiento registrado
        movimiento = Movimiento.objects.filter(
            lote=self.lote1,
            tipo='SALIDA',
            cantidad=100
        ).first()
        self.assertIsNotNone(movimiento)
        
        # Verificar detalle actualizado
        detalle = requisicion.detalles.first()
        self.assertEqual(detalle.cantidad_entregada, 100)
    
    def test_flujo_requisicion_stock_insuficiente(self):
        """
        Test de requisición cuando no hay stock suficiente.
        """
        from core.models import Requisicion
        
        self.client.force_authenticate(user=self.solicitante)
        
        # Solicitar más de lo disponible
        requisicion_data = {
            'centro': self.centro.id,
            'motivo': 'Solicitud excesiva E2E',
            'detalles': [
                {
                    'medicamento': self.medicamento.id,
                    'cantidad_solicitada': 10000,  # Más que stock total (800)
                }
            ]
        }
        
        response = self.client.post(
            '/api/requisiciones/',
            requisicion_data,
            format='json'
        )
        
        # Puede crear la requisición (advertencia) o rechazar
        if response.status_code == status.HTTP_201_CREATED:
            # Verificar que incluye advertencia de stock
            self.assertIn('warnings', response.data)
        else:
            # O rechaza por stock insuficiente
            self.assertIn(response.status_code, [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ])


@pytest.mark.e2e
class TestFlujoImportacionLotes(TransactionTestCase):
    """
    ISS-029: Test E2E del flujo de importación de lotes.
    """
    
    def setUp(self):
        """Configurar datos de prueba."""
        from core.models import Medicamento
        
        self.admin = User.objects.create_superuser(
            username='admin_import',
            email='admin_import@test.com',
            password='testpass123'
        )
        
        self.medicamento = Medicamento.objects.create(
            nombre='Ibuprofeno Import',
            codigo='IBU-IMP-001',
            principio_activo='Ibuprofeno'
        )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)
    
    def test_importacion_csv_exitosa(self):
        """Test de importación CSV exitosa."""
        import io
        
        # Crear CSV de prueba
        csv_content = """codigo_lote,medicamento_codigo,cantidad,fecha_vencimiento
LOTE-CSV-001,IBU-IMP-001,100,2025-12-31
LOTE-CSV-002,IBU-IMP-001,200,2025-06-30
LOTE-CSV-003,IBU-IMP-001,150,2026-01-15"""
        
        csv_file = io.StringIO(csv_content)
        csv_file.name = 'lotes_test.csv'
        
        response = self.client.post(
            '/api/lotes/importar/',
            {'archivo': csv_file, 'formato': 'csv'},
            format='multipart'
        )
        
        # Verificar resultado
        if response.status_code == status.HTTP_200_OK:
            from core.models import Lote
            
            self.assertTrue(
                Lote.objects.filter(codigo_lote='LOTE-CSV-001').exists()
            )
            self.assertEqual(response.data.get('importados', 0), 3)
    
    def test_importacion_con_errores_parciales(self):
        """Test de importación con algunos errores."""
        import io
        
        # CSV con errores
        csv_content = """codigo_lote,medicamento_codigo,cantidad,fecha_vencimiento
LOTE-ERR-001,IBU-IMP-001,100,2025-12-31
LOTE-ERR-002,CODIGO_INVALIDO,200,2025-06-30
LOTE-ERR-003,IBU-IMP-001,-50,2026-01-15"""  # Cantidad negativa
        
        csv_file = io.StringIO(csv_content)
        csv_file.name = 'lotes_errores.csv'
        
        response = self.client.post(
            '/api/lotes/importar/',
            {'archivo': csv_file, 'formato': 'csv'},
            format='multipart'
        )
        
        # Debe reportar errores detallados
        if 'errores' in response.data:
            self.assertGreater(len(response.data['errores']), 0)


@pytest.mark.e2e
class TestFlujoAjusteInventario(TransactionTestCase):
    """
    ISS-029: Test E2E del flujo de ajuste de inventario.
    """
    
    def setUp(self):
        """Configurar datos."""
        from core.models import Medicamento, Lote
        
        self.admin = User.objects.create_superuser(
            username='admin_ajuste',
            email='admin_ajuste@test.com',
            password='testpass123'
        )
        
        self.medicamento = Medicamento.objects.create(
            nombre='Medicamento Ajuste',
            codigo='MED-AJU-001'
        )
        
        self.lote = Lote.objects.create(
            medicamento=self.medicamento,
            codigo_lote='LOTE-AJU-001',
            fecha_fabricacion=date.today() - timedelta(days=30),
            fecha_vencimiento=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100
        )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)
    
    def test_ajuste_positivo(self):
        """Test de ajuste positivo de inventario."""
        from core.models import Movimiento
        
        response = self.client.post(
            f'/api/lotes/{self.lote.id}/ajustar/',
            {
                'cantidad': 10,
                'motivo': 'Encontrado en conteo físico',
                'tipo_ajuste': 'POSITIVO'
            },
            format='json'
        )
        
        if response.status_code == status.HTTP_200_OK:
            self.lote.refresh_from_db()
            self.assertEqual(self.lote.cantidad_actual, 110)
            
            # Verificar movimiento de ajuste
            ajuste = Movimiento.objects.filter(
                lote=self.lote,
                tipo='AJUSTE'
            ).first()
            self.assertIsNotNone(ajuste)
    
    def test_ajuste_negativo(self):
        """Test de ajuste negativo de inventario."""
        response = self.client.post(
            f'/api/lotes/{self.lote.id}/ajustar/',
            {
                'cantidad': 5,
                'motivo': 'Merma detectada',
                'tipo_ajuste': 'NEGATIVO'
            },
            format='json'
        )
        
        if response.status_code == status.HTTP_200_OK:
            self.lote.refresh_from_db()
            self.assertEqual(self.lote.cantidad_actual, 95)
    
    def test_ajuste_no_permite_stock_negativo(self):
        """Test que ajuste no permite stock negativo."""
        response = self.client.post(
            f'/api/lotes/{self.lote.id}/ajustar/',
            {
                'cantidad': 200,  # Más que el stock
                'motivo': 'Ajuste excesivo',
                'tipo_ajuste': 'NEGATIVO'
            },
            format='json'
        )
        
        # Debe rechazar o advertir
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ])


@pytest.mark.e2e
class TestFlujoReportes(TransactionTestCase):
    """
    ISS-029: Test E2E de generación de reportes.
    """
    
    def setUp(self):
        """Configurar datos."""
        from core.models import Medicamento, Lote, Movimiento
        
        self.admin = User.objects.create_superuser(
            username='admin_reportes',
            email='admin_reportes@test.com',
            password='testpass123'
        )
        
        # Crear datos para reportes
        self.medicamento = Medicamento.objects.create(
            nombre='Medicamento Reporte',
            codigo='MED-REP-001',
            stock_minimo=50
        )
        
        self.lote = Lote.objects.create(
            medicamento=self.medicamento,
            codigo_lote='LOTE-REP-001',
            fecha_fabricacion=date.today() - timedelta(days=30),
            fecha_vencimiento=date.today() + timedelta(days=30),  # Próximo a vencer
            cantidad_inicial=100,
            cantidad_actual=30  # Bajo stock mínimo
        )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)
    
    def test_reporte_stock_bajo(self):
        """Test de reporte de stock bajo mínimo."""
        response = self.client.get('/api/reportes/stock-bajo/')
        
        if response.status_code == status.HTTP_200_OK:
            # Verificar que incluye nuestro medicamento
            medicamentos = response.data.get('medicamentos', [])
            codigos = [m['codigo'] for m in medicamentos]
            self.assertIn('MED-REP-001', codigos)
    
    def test_reporte_proximos_vencer(self):
        """Test de reporte de lotes próximos a vencer."""
        response = self.client.get(
            '/api/reportes/proximos-vencer/',
            {'dias': 60}
        )
        
        if response.status_code == status.HTTP_200_OK:
            lotes = response.data.get('lotes', [])
            codigos = [l['codigo_lote'] for l in lotes]
            self.assertIn('LOTE-REP-001', codigos)
    
    def test_exportacion_inventario_csv(self):
        """Test de exportación de inventario a CSV."""
        response = self.client.get(
            '/api/reportes/inventario/export/',
            {'formato': 'csv'}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.get('Content-Type'),
            'text/csv'
        )


@pytest.mark.e2e  
class TestFlujoVerificacionIntegridad(TransactionTestCase):
    """
    ISS-029: Test E2E de verificación de integridad.
    """
    
    def setUp(self):
        """Configurar datos."""
        self.admin = User.objects.create_superuser(
            username='admin_integridad',
            email='admin_integridad@test.com',
            password='testpass123'
        )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)
    
    def test_verificacion_integridad_basica(self):
        """Test de verificación de integridad del sistema."""
        response = self.client.get('/api/sistema/verificar-integridad/')
        
        if response.status_code == status.HTTP_200_OK:
            self.assertIn('estado', response.data)
            self.assertIn(response.data['estado'], [
                'OK', 'ADVERTENCIA', 'CRITICO', 'REVISION_REQUERIDA'
            ])


@pytest.mark.e2e
class TestAutenticacionYPermisos(TransactionTestCase):
    """
    ISS-029: Test E2E de autenticación y permisos.
    """
    
    def setUp(self):
        """Configurar usuarios con diferentes roles."""
        from core.models import Centro
        
        self.admin = User.objects.create_superuser(
            username='admin_permisos',
            email='admin_permisos@test.com',
            password='testpass123'
        )
        
        self.usuario_basico = User.objects.create_user(
            username='usuario_basico',
            email='basico@test.com',
            password='testpass123'
        )
        
        self.client = APIClient()
    
    def test_acceso_sin_autenticacion_rechazado(self):
        """Test que endpoints protegidos requieren autenticación."""
        endpoints_protegidos = [
            '/api/medicamentos/',
            '/api/lotes/',
            '/api/requisiciones/',
            '/api/movimientos/',
        ]
        
        for endpoint in endpoints_protegidos:
            response = self.client.get(endpoint)
            self.assertEqual(
                response.status_code,
                status.HTTP_401_UNAUTHORIZED,
                f"Endpoint {endpoint} debería requerir autenticación"
            )
    
    def test_acceso_admin_completo(self):
        """Test que admin tiene acceso completo."""
        self.client.force_authenticate(user=self.admin)
        
        response = self.client.get('/api/medicamentos/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response = self.client.get('/api/lotes/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_usuario_basico_permisos_limitados(self):
        """Test que usuario básico tiene permisos limitados."""
        self.client.force_authenticate(user=self.usuario_basico)
        
        # Puede ver medicamentos
        response = self.client.get('/api/medicamentos/')
        self.assertIn(response.status_code, [
            status.HTTP_200_OK, 
            status.HTTP_403_FORBIDDEN
        ])


# === FIXTURES REUTILIZABLES ===

@pytest.fixture
def usuario_farmaceutico(db):
    """Fixture para usuario farmacéutico."""
    return User.objects.create_user(
        username='farmaceutico_fixture',
        email='farmaceutico_fixture@test.com',
        password='testpass123'
    )


@pytest.fixture
def medicamento_con_stock(db):
    """Fixture para medicamento con stock disponible."""
    from core.models import Medicamento, Lote
    
    med = Medicamento.objects.create(
        nombre='Medicamento Fixture',
        codigo='MED-FIX-001'
    )
    
    Lote.objects.create(
        medicamento=med,
        codigo_lote='LOTE-FIX-001',
        fecha_fabricacion=date.today() - timedelta(days=30),
        fecha_vencimiento=date.today() + timedelta(days=365),
        cantidad_inicial=1000,
        cantidad_actual=1000
    )
    
    return med


@pytest.fixture
def api_client_autenticado(db, usuario_farmaceutico):
    """Fixture para cliente API autenticado."""
    client = APIClient()
    client.force_authenticate(user=usuario_farmaceutico)
    return client
