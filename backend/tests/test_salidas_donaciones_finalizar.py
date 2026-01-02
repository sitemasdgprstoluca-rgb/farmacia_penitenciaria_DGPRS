"""
Tests Unitarios para el módulo de Salidas de Donaciones - Función Finalizar
===========================================================================

Estos tests verifican los siguientes cambios implementados:
1. El stock NO se descuenta al crear la salida (solo se reserva/valida)
2. El stock SÍ se descuenta al finalizar la entrega
3. No se puede finalizar una entrega ya finalizada
4. El centro_destino se guarda correctamente
5. Los campos finalizado, fecha_finalizado, finalizado_por funcionan

Ejecutar con: python manage.py test tests.test_salidas_donaciones_finalizar
O directamente: python -m pytest tests/test_salidas_donaciones_finalizar.py -v
"""
import os
import sys
import django
import pytest
from decimal import Decimal
from datetime import date, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory, TestCase
from django.utils import timezone
from rest_framework.test import force_authenticate, APIClient
from rest_framework import status as http_status
from core.models import (
    User, Centro, Producto, ProductoDonacion, 
    Donacion, DetalleDonacion, SalidaDonacion
)
from core.views import SalidaDonacionViewSet


class TestSalidaDonacionFinalizar:
    """Tests para la funcionalidad de finalizar entregas de donaciones."""
    
    @pytest.fixture(autouse=True)
    def setup(self, db):
        """Configurar datos de prueba."""
        self.factory = RequestFactory()
        
        # Crear usuario admin
        self.admin = User.objects.filter(is_superuser=True).first()
        if not self.admin:
            self.admin = User.objects.create_superuser(
                username='test_admin_donaciones',
                email='admin_donaciones@test.com',
                password='testpass123'
            )
        
        # Crear centro de prueba
        self.centro = Centro.objects.create(
            nombre='Centro de Prueba Finalizar',
            activo=True
        )
        
        # Crear producto de donación
        self.producto_donacion = ProductoDonacion.objects.create(
            clave='TEST-DON-FIN-001',
            nombre='Producto Test Finalizar',
            unidad_medida='PIEZA',
            activo=True
        )
        
        # Crear donación
        self.donacion = Donacion.objects.create(
            numero=f'DON-TEST-FIN-{timezone.now().strftime("%Y%m%d%H%M%S")}',
            donante_nombre='Donante Test Finalizar',
            donante_tipo='empresa',
            fecha_donacion=date.today(),
            estado='procesada'
        )
        
        # Crear detalle de donación con stock
        self.detalle = DetalleDonacion.objects.create(
            donacion=self.donacion,
            producto_donacion=self.producto_donacion,
            numero_lote='LOTE-FIN-TEST-001',
            cantidad=100,
            cantidad_disponible=100,
            fecha_caducidad=date.today() + timedelta(days=365),
            estado_producto='bueno'
        )
    
    def teardown_method(self, method):
        """Limpiar datos de prueba."""
        try:
            SalidaDonacion.objects.filter(
                detalle_donacion__donacion__numero__startswith='DON-TEST-FIN'
            ).delete()
            DetalleDonacion.objects.filter(
                donacion__numero__startswith='DON-TEST-FIN'
            ).delete()
            Donacion.objects.filter(numero__startswith='DON-TEST-FIN').delete()
            ProductoDonacion.objects.filter(clave__startswith='TEST-DON-FIN').delete()
            Centro.objects.filter(nombre='Centro de Prueba Finalizar').delete()
        except Exception as e:
            print(f"Error en limpieza: {e}")
    
    def test_crear_salida_no_descuenta_stock(self, db):
        """TEST 1: Al crear una salida, el stock NO debe descontarse."""
        stock_inicial = self.detalle.cantidad_disponible
        
        # Crear salida
        salida = SalidaDonacion.objects.create(
            detalle_donacion=self.detalle,
            cantidad=10,
            destinatario='Test Destinatario',
            motivo='Test motivo'
        )
        
        # Refrescar el detalle
        self.detalle.refresh_from_db()
        
        # El stock NO debe haber cambiado
        assert self.detalle.cantidad_disponible == stock_inicial, \
            f"El stock debería ser {stock_inicial} pero es {self.detalle.cantidad_disponible}"
        
        # La salida no debe estar finalizada
        assert salida.finalizado == False, "La salida no debe estar finalizada al crear"
        assert salida.fecha_finalizado is None, "No debe tener fecha de finalización"
        assert salida.finalizado_por is None, "No debe tener usuario finalizador"
        
        # Limpiar
        salida.delete()
        
        print("✅ TEST 1: Crear salida no descuenta stock - PASÓ")
    
    def test_finalizar_descuenta_stock(self, db):
        """TEST 2: Al finalizar, el stock SÍ debe descontarse."""
        stock_inicial = self.detalle.cantidad_disponible
        cantidad_salida = 15
        
        # Crear salida (no descuenta)
        salida = SalidaDonacion.objects.create(
            detalle_donacion=self.detalle,
            cantidad=cantidad_salida,
            destinatario='Test Destinatario Finalizar'
        )
        
        # Verificar que no se descontó
        self.detalle.refresh_from_db()
        assert self.detalle.cantidad_disponible == stock_inicial
        
        # Finalizar la salida
        salida.finalizar(usuario=self.admin)
        
        # Verificar que ahora sí se descontó
        self.detalle.refresh_from_db()
        stock_esperado = stock_inicial - cantidad_salida
        assert self.detalle.cantidad_disponible == stock_esperado, \
            f"Stock esperado: {stock_esperado}, actual: {self.detalle.cantidad_disponible}"
        
        # Verificar campos de finalización
        assert salida.finalizado == True
        assert salida.fecha_finalizado is not None
        assert salida.finalizado_por == self.admin
        
        # Limpiar
        salida.delete()
        
        print("✅ TEST 2: Finalizar descuenta stock - PASÓ")
    
    def test_no_puede_finalizar_dos_veces(self, db):
        """TEST 3: No se puede finalizar una entrega ya finalizada."""
        # Crear y finalizar
        salida = SalidaDonacion.objects.create(
            detalle_donacion=self.detalle,
            cantidad=10,
            destinatario='Test Doble Finalizar'
        )
        salida.finalizar(usuario=self.admin)
        
        # Intentar finalizar de nuevo
        with pytest.raises(ValueError) as excinfo:
            salida.finalizar(usuario=self.admin)
        
        assert "ya fue finalizada" in str(excinfo.value).lower()
        
        # Limpiar
        salida.delete()
        
        print("✅ TEST 3: No finalizar dos veces - PASÓ")
    
    def test_centro_destino_se_guarda(self, db):
        """TEST 4: El centro_destino se guarda correctamente."""
        salida = SalidaDonacion.objects.create(
            detalle_donacion=self.detalle,
            cantidad=5,
            destinatario='Test Centro Destino',
            centro_destino=self.centro
        )
        
        # Verificar que se guardó
        salida.refresh_from_db()
        assert salida.centro_destino == self.centro
        assert salida.centro_destino.nombre == 'Centro de Prueba Finalizar'
        
        # Limpiar
        salida.delete()
        
        print("✅ TEST 4: Centro destino se guarda - PASÓ")
    
    def test_validacion_stock_insuficiente_al_crear(self, db):
        """TEST 5: Validar que no se puede crear salida si no hay stock suficiente."""
        # Intentar crear salida con más de lo disponible
        with pytest.raises(ValueError) as excinfo:
            SalidaDonacion.objects.create(
                detalle_donacion=self.detalle,
                cantidad=self.detalle.cantidad_disponible + 100,  # Más de lo disponible
                destinatario='Test Sin Stock'
            )
        
        assert "insuficiente" in str(excinfo.value).lower()
        
        print("✅ TEST 5: Validación stock insuficiente al crear - PASÓ")
    
    def test_validacion_stock_insuficiente_al_finalizar(self, db):
        """TEST 6: Si el stock cambió entre crear y finalizar, debe validar."""
        stock_inicial = self.detalle.cantidad_disponible
        
        # Crear salida por casi todo el stock
        salida1 = SalidaDonacion.objects.create(
            detalle_donacion=self.detalle,
            cantidad=stock_inicial - 5,
            destinatario='Test Salida 1'
        )
        
        # Crear otra salida pequeña
        salida2 = SalidaDonacion.objects.create(
            detalle_donacion=self.detalle,
            cantidad=10,  # Esto excedería el stock después de finalizar salida1
            destinatario='Test Salida 2'
        )
        
        # Finalizar la primera (consume casi todo)
        salida1.finalizar(usuario=self.admin)
        
        # Intentar finalizar la segunda debería fallar
        with pytest.raises(ValueError) as excinfo:
            salida2.finalizar(usuario=self.admin)
        
        assert "insuficiente" in str(excinfo.value).lower()
        
        # Limpiar
        salida2.delete()
        salida1.delete()
        
        print("✅ TEST 6: Validación stock al finalizar - PASÓ")
    
    def test_estado_entrega_property(self, db):
        """TEST 7: La propiedad estado_entrega funciona correctamente."""
        salida = SalidaDonacion.objects.create(
            detalle_donacion=self.detalle,
            cantidad=5,
            destinatario='Test Estado'
        )
        
        # Antes de finalizar
        assert salida.estado_entrega == 'pendiente'
        
        # Después de finalizar
        salida.finalizar(usuario=self.admin)
        assert salida.estado_entrega == 'entregado'
        
        # Limpiar
        salida.delete()
        
        print("✅ TEST 7: Estado entrega property - PASÓ")


class TestSalidaDonacionAPI:
    """Tests para la API de Salidas de Donaciones."""
    
    @pytest.fixture(autouse=True)
    def setup(self, db):
        """Configurar datos de prueba."""
        self.factory = RequestFactory()
        self.client = APIClient()
        
        # Crear usuario admin
        self.admin = User.objects.filter(is_superuser=True).first()
        if not self.admin:
            self.admin = User.objects.create_superuser(
                username='test_admin_api_don',
                email='admin_api_don@test.com',
                password='testpass123'
            )
        
        # Autenticar
        self.client.force_authenticate(user=self.admin)
        
        # Crear centro
        self.centro = Centro.objects.create(
            nombre='Centro API Test',
            activo=True
        )
        
        # Crear producto de donación
        self.producto_donacion = ProductoDonacion.objects.create(
            clave='TEST-API-DON-001',
            nombre='Producto API Test',
            unidad_medida='PIEZA',
            activo=True
        )
        
        # Crear donación
        self.donacion = Donacion.objects.create(
            numero=f'DON-API-TEST-{timezone.now().strftime("%Y%m%d%H%M%S")}',
            donante_nombre='Donante API Test',
            fecha_donacion=date.today(),
            estado='procesada'
        )
        
        # Crear detalle
        self.detalle = DetalleDonacion.objects.create(
            donacion=self.donacion,
            producto_donacion=self.producto_donacion,
            numero_lote='LOTE-API-TEST',
            cantidad=200,
            cantidad_disponible=200,
            fecha_caducidad=date.today() + timedelta(days=365)
        )
    
    def teardown_method(self, method):
        """Limpiar datos de prueba."""
        try:
            SalidaDonacion.objects.filter(
                detalle_donacion__donacion__numero__startswith='DON-API-TEST'
            ).delete()
            DetalleDonacion.objects.filter(
                donacion__numero__startswith='DON-API-TEST'
            ).delete()
            Donacion.objects.filter(numero__startswith='DON-API-TEST').delete()
            ProductoDonacion.objects.filter(clave__startswith='TEST-API-DON').delete()
            Centro.objects.filter(nombre='Centro API Test').delete()
        except Exception as e:
            print(f"Error en limpieza: {e}")
    
    def test_api_finalizar_endpoint(self, db):
        """TEST API 1: El endpoint /finalizar/ funciona correctamente."""
        # Crear salida primero
        salida = SalidaDonacion.objects.create(
            detalle_donacion=self.detalle,
            cantidad=20,
            destinatario='Test API Finalizar',
            centro_destino=self.centro
        )
        
        stock_inicial = self.detalle.cantidad_disponible
        
        # Llamar endpoint finalizar
        view = SalidaDonacionViewSet.as_view({'post': 'finalizar'})
        request = self.factory.post(f'/api/salidas-donaciones/{salida.id}/finalizar/')
        force_authenticate(request, user=self.admin)
        response = view(request, pk=salida.id)
        
        assert response.status_code == 200, f"Error: {response.data}"
        
        # Verificar que se descuenta el stock
        self.detalle.refresh_from_db()
        assert self.detalle.cantidad_disponible == stock_inicial - 20
        
        # Verificar respuesta
        assert 'mensaje' in response.data
        assert 'salida' in response.data
        assert response.data['salida']['finalizado'] == True
        
        # Limpiar
        salida.delete()
        
        print("✅ TEST API 1: Endpoint finalizar - PASÓ")
    
    def test_api_finalizar_ya_finalizada(self, db):
        """TEST API 2: Finalizar algo ya finalizado retorna error 400."""
        salida = SalidaDonacion.objects.create(
            detalle_donacion=self.detalle,
            cantidad=10,
            destinatario='Test Ya Finalizada'
        )
        salida.finalizar(usuario=self.admin)
        
        # Intentar finalizar de nuevo via API
        view = SalidaDonacionViewSet.as_view({'post': 'finalizar'})
        request = self.factory.post(f'/api/salidas-donaciones/{salida.id}/finalizar/')
        force_authenticate(request, user=self.admin)
        response = view(request, pk=salida.id)
        
        assert response.status_code == 400
        assert 'error' in response.data
        assert 'ya fue finalizada' in response.data['error'].lower()
        
        # Limpiar
        salida.delete()
        
        print("✅ TEST API 2: Error al finalizar dos veces - PASÓ")
    
    def test_api_crear_con_centro_destino(self, db):
        """TEST API 3: Crear salida con centro_destino funciona."""
        import json
        
        salida_data = {
            'detalle_donacion': self.detalle.id,
            'cantidad': 15,
            'destinatario': 'Test Centro Destino API',
            'centro_destino': self.centro.id
        }
        
        view = SalidaDonacionViewSet.as_view({'post': 'create'})
        request = self.factory.post(
            '/api/salidas-donaciones/',
            data=json.dumps(salida_data),
            content_type='application/json'
        )
        force_authenticate(request, user=self.admin)
        response = view(request)
        
        assert response.status_code == 201, f"Error: {response.data}"
        assert response.data['centro_destino'] == self.centro.id
        assert response.data['centro_destino_nombre'] == 'Centro API Test'
        assert response.data['finalizado'] == False
        
        # Limpiar
        SalidaDonacion.objects.filter(id=response.data['id']).delete()
        
        print("✅ TEST API 3: Crear con centro_destino - PASÓ")
    
    def test_api_filtrar_por_finalizado(self, db):
        """TEST API 4: El filtro por finalizado funciona."""
        # Crear dos salidas, una finalizada y otra no
        salida1 = SalidaDonacion.objects.create(
            detalle_donacion=self.detalle,
            cantidad=5,
            destinatario='Test Filtro 1'
        )
        salida2 = SalidaDonacion.objects.create(
            detalle_donacion=self.detalle,
            cantidad=5,
            destinatario='Test Filtro 2'
        )
        salida2.finalizar(usuario=self.admin)
        
        # Filtrar por no finalizadas
        view = SalidaDonacionViewSet.as_view({'get': 'list'})
        request = self.factory.get('/api/salidas-donaciones/', {'finalizado': 'false'})
        force_authenticate(request, user=self.admin)
        response = view(request)
        
        assert response.status_code == 200
        results = response.data.get('results', response.data)
        no_finalizadas = [s for s in results if s['id'] == salida1.id]
        assert len(no_finalizadas) >= 1
        
        # Filtrar por finalizadas
        request = self.factory.get('/api/salidas-donaciones/', {'finalizado': 'true'})
        force_authenticate(request, user=self.admin)
        response = view(request)
        
        results = response.data.get('results', response.data)
        finalizadas = [s for s in results if s['id'] == salida2.id]
        assert len(finalizadas) >= 1
        
        # Limpiar
        salida1.delete()
        salida2.delete()
        
        print("✅ TEST API 4: Filtrar por finalizado - PASÓ")


def run_all_tests():
    """Ejecutar todos los tests manualmente."""
    print("=" * 70)
    print("TESTS UNITARIOS - SALIDAS DONACIONES FINALIZAR")
    print("=" * 70)
    
    # Tests del modelo
    print("\n--- Tests del Modelo SalidaDonacion ---")
    test_model = TestSalidaDonacionFinalizar()
    
    # Simular db fixture
    class MockDB:
        pass
    
    try:
        test_model.setup(MockDB())
        
        test_model.test_crear_salida_no_descuenta_stock(MockDB())
        test_model.test_finalizar_descuenta_stock(MockDB())
        test_model.test_no_puede_finalizar_dos_veces(MockDB())
        test_model.test_centro_destino_se_guarda(MockDB())
        test_model.test_validacion_stock_insuficiente_al_crear(MockDB())
        test_model.test_validacion_stock_insuficiente_al_finalizar(MockDB())
        test_model.test_estado_entrega_property(MockDB())
        
        test_model.teardown_method(None)
        
    except Exception as e:
        print(f"❌ Error en tests de modelo: {e}")
        import traceback
        traceback.print_exc()
    
    # Tests de la API
    print("\n--- Tests de la API SalidaDonacionViewSet ---")
    test_api = TestSalidaDonacionAPI()
    
    try:
        test_api.setup(MockDB())
        
        test_api.test_api_finalizar_endpoint(MockDB())
        test_api.test_api_finalizar_ya_finalizada(MockDB())
        test_api.test_api_crear_con_centro_destino(MockDB())
        test_api.test_api_filtrar_por_finalizado(MockDB())
        
        test_api.teardown_method(None)
        
    except Exception as e:
        print(f"❌ Error en tests de API: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("TESTS COMPLETADOS")
    print("=" * 70)


if __name__ == '__main__':
    run_all_tests()
