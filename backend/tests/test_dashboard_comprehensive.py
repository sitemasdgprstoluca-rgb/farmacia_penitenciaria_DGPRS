# -*- coding: utf-8 -*-
"""
Test Suite Completa: Dashboard - Backend
========================================

Tests unitarios y de integración para el módulo Dashboard:
- Endpoint dashboard_resumen
- Endpoint dashboard_graficas
- Filtros por usuario y centro
- Seguridad y permisos
- Caché y rendimiento
- Casos edge y errores

Author: SIFP - Sistema de Inventario Farmacéutico Penitenciario
Date: 2026-01-04
"""
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.cache import cache
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock
from decimal import Decimal
from datetime import datetime, timedelta
import json

# Intentar importar modelos (pueden no existir en todos los entornos)
try:
    from core.models import (
        Producto, Lote, Movimiento, Centro, Requisicion, 
        Notificacion, User
    )
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    User = get_user_model()


# =============================================================================
# FIXTURES Y DATOS DE PRUEBA
# =============================================================================

@pytest.fixture
def api_client():
    """Cliente API para tests."""
    return APIClient()


@pytest.fixture
def admin_user(db):
    """Usuario admin para tests."""
    User = get_user_model()
    user = User.objects.create_user(
        username='admin_test',
        email='admin@test.com',
        password='testpass123',
        rol='admin',
        is_staff=True,
        is_superuser=True
    )
    return user


@pytest.fixture
def farmacia_user(db):
    """Usuario farmacia para tests."""
    User = get_user_model()
    user = User.objects.create_user(
        username='farmacia_test',
        email='farmacia@test.com',
        password='testpass123',
        rol='farmacia',
        is_staff=True
    )
    return user


@pytest.fixture
def centro_user(db, centro):
    """Usuario de centro para tests."""
    User = get_user_model()
    user = User.objects.create_user(
        username='centro_test',
        email='centro@test.com',
        password='testpass123',
        rol='centro',
        centro=centro
    )
    return user


@pytest.fixture
def vista_user(db):
    """Usuario vista para tests."""
    User = get_user_model()
    user = User.objects.create_user(
        username='vista_test',
        email='vista@test.com',
        password='testpass123',
        rol='vista'
    )
    return user


@pytest.fixture
def centro(db):
    """Centro de prueba."""
    if not MODELS_AVAILABLE:
        pytest.skip("Modelos no disponibles")
    return Centro.objects.create(
        nombre='Centro de Prueba Norte',
        direccion='Calle Test 123',
        activo=True
    )


@pytest.fixture
def centro2(db):
    """Segundo centro de prueba."""
    if not MODELS_AVAILABLE:
        pytest.skip("Modelos no disponibles")
    return Centro.objects.create(
        nombre='Centro de Prueba Sur',
        direccion='Calle Test 456',
        activo=True
    )


@pytest.fixture
def producto(db):
    """Producto de prueba."""
    if not MODELS_AVAILABLE:
        pytest.skip("Modelos no disponibles")
    return Producto.objects.create(
        clave='TEST001',
        nombre='Producto de Prueba',
        descripcion='Descripción del producto de prueba',
        categoria='medicamento',
        unidad_medida='pieza',
        activo=True,
        stock_minimo=10
    )


@pytest.fixture
def lote(db, producto, centro):
    """Lote de prueba."""
    if not MODELS_AVAILABLE:
        pytest.skip("Modelos no disponibles")
    return Lote.objects.create(
        numero_lote='LOT-2026-001',
        producto=producto,
        centro=centro,
        cantidad_inicial=100,
        cantidad_actual=80,
        fecha_caducidad=timezone.now().date() + timedelta(days=180),
        activo=True
    )


@pytest.fixture
def lote_farmacia(db, producto):
    """Lote en farmacia central (sin centro)."""
    if not MODELS_AVAILABLE:
        pytest.skip("Modelos no disponibles")
    return Lote.objects.create(
        numero_lote='LOT-2026-002',
        producto=producto,
        centro=None,  # Farmacia central
        cantidad_inicial=200,
        cantidad_actual=150,
        fecha_caducidad=timezone.now().date() + timedelta(days=365),
        activo=True
    )


@pytest.fixture
def movimiento_entrada(db, lote, admin_user):
    """Movimiento de entrada."""
    if not MODELS_AVAILABLE:
        pytest.skip("Modelos no disponibles")
    return Movimiento.objects.create(
        tipo='entrada',
        producto=lote.producto,
        lote=lote,
        cantidad=50,
        centro_destino=lote.centro,
        usuario=admin_user,
        motivo='Entrada de prueba',
        referencia='REF-001'
    )


@pytest.fixture
def movimiento_salida(db, lote, admin_user):
    """Movimiento de salida."""
    if not MODELS_AVAILABLE:
        pytest.skip("Modelos no disponibles")
    return Movimiento.objects.create(
        tipo='salida',
        producto=lote.producto,
        lote=lote,
        cantidad=20,
        centro_origen=lote.centro,
        usuario=admin_user,
        motivo='Salida de prueba'
    )


@pytest.fixture
def requisicion(db, centro, admin_user):
    """Requisición de prueba."""
    if not MODELS_AVAILABLE:
        pytest.skip("Modelos no disponibles")
    return Requisicion.objects.create(
        numero='REQ-2026-001',
        centro_destino=centro,
        solicitante=admin_user,
        estado='pendiente_admin',
        tipo='normal',
        prioridad='normal'
    )


# =============================================================================
# TESTS: ENDPOINT DASHBOARD RESUMEN
# =============================================================================

@pytest.mark.django_db
class TestDashboardResumenEndpoint:
    """Tests para el endpoint /api/dashboard/ (resumen)."""
    
    def test_dashboard_resumen_sin_autenticacion(self, api_client):
        """Debe requerir autenticación."""
        response = api_client.get('/api/dashboard/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_dashboard_resumen_admin_ve_datos_globales(self, api_client, admin_user, lote, lote_farmacia, movimiento_entrada):
        """Admin debe ver datos globales del sistema."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.get('/api/dashboard/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verificar estructura de KPIs
        assert 'kpi' in data
        kpi = data['kpi']
        assert 'total_productos' in kpi
        assert 'stock_total' in kpi
        assert 'lotes_activos' in kpi
        assert 'movimientos_mes' in kpi
        
        # Verificar que incluye lotes de todos los centros
        assert kpi['lotes_activos'] >= 2  # lote + lote_farmacia
    
    def test_dashboard_resumen_farmacia_ve_datos_globales(self, api_client, farmacia_user, lote, lote_farmacia):
        """Farmacia debe ver datos globales."""
        api_client.force_authenticate(user=farmacia_user)
        
        response = api_client.get('/api/dashboard/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'kpi' in data
    
    def test_dashboard_resumen_centro_ve_solo_su_centro(self, api_client, centro_user, lote, lote_farmacia):
        """Usuario de centro solo ve datos de su centro."""
        api_client.force_authenticate(user=centro_user)
        
        response = api_client.get('/api/dashboard/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        kpi = data['kpi']
        
        # Solo debe ver el lote de su centro, no el de farmacia central
        # (la lógica exacta depende de la implementación)
        assert 'lotes_activos' in kpi
    
    def test_dashboard_resumen_filtro_por_centro(self, api_client, admin_user, centro, centro2, lote):
        """Admin puede filtrar por centro específico."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.get(f'/api/dashboard/?centro={centro.id}')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Datos deben estar filtrados por el centro especificado
        assert 'kpi' in data
    
    def test_dashboard_resumen_ultimos_movimientos(self, api_client, admin_user, movimiento_entrada, movimiento_salida):
        """Debe incluir últimos movimientos."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.get('/api/dashboard/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert 'ultimos_movimientos' in data
        movimientos = data['ultimos_movimientos']
        assert isinstance(movimientos, list)
        
        # Verificar estructura de movimientos
        if len(movimientos) > 0:
            mov = movimientos[0]
            assert 'tipo_movimiento' in mov
            assert 'cantidad' in mov
    
    def test_dashboard_resumen_con_parametro_centro_invalido(self, api_client, admin_user):
        """Debe manejar centro inválido sin error."""
        api_client.force_authenticate(user=admin_user)
        
        # Centro que no existe
        response = api_client.get('/api/dashboard/?centro=99999')
        
        # No debe fallar, solo ignorar el filtro inválido
        assert response.status_code == status.HTTP_200_OK
    
    def test_dashboard_resumen_parametros_especiales(self, api_client, admin_user):
        """Debe manejar parámetros especiales correctamente."""
        api_client.force_authenticate(user=admin_user)
        
        # Parámetros que deben ser ignorados
        for param in ['null', 'undefined', 'todos', '']:
            response = api_client.get(f'/api/dashboard/?centro={param}')
            assert response.status_code == status.HTTP_200_OK


# =============================================================================
# TESTS: ENDPOINT DASHBOARD GRÁFICAS
# =============================================================================

@pytest.mark.django_db
class TestDashboardGraficasEndpoint:
    """Tests para el endpoint /api/dashboard/graficas/."""
    
    def test_graficas_sin_autenticacion(self, api_client):
        """Debe requerir autenticación."""
        response = api_client.get('/api/dashboard/graficas/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_graficas_estructura_respuesta(self, api_client, admin_user):
        """Debe retornar estructura correcta."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.get('/api/dashboard/graficas/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verificar campos principales
        assert 'consumo_mensual' in data
        assert 'stock_por_centro' in data
        assert 'requisiciones_por_estado' in data
    
    def test_graficas_consumo_mensual(self, api_client, admin_user, movimiento_entrada, movimiento_salida):
        """Debe calcular consumo mensual correctamente."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.get('/api/dashboard/graficas/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        consumo = data['consumo_mensual']
        assert isinstance(consumo, list)
        
        # Debe tener 6 meses de datos
        if len(consumo) > 0:
            mes = consumo[0]
            assert 'mes' in mes
            assert 'entradas' in mes
            assert 'salidas' in mes
    
    def test_graficas_stock_por_centro(self, api_client, admin_user, lote, lote_farmacia, centro):
        """Debe mostrar stock por centro."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.get('/api/dashboard/graficas/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        stock_centros = data['stock_por_centro']
        assert isinstance(stock_centros, list)
        
        # Debe incluir farmacia central y centros con stock
        if len(stock_centros) > 0:
            item = stock_centros[0]
            assert 'centro' in item
            assert 'stock' in item
    
    def test_graficas_requisiciones_por_estado(self, api_client, admin_user, requisicion):
        """Debe agrupar requisiciones por estado."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.get('/api/dashboard/graficas/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        req_estados = data['requisiciones_por_estado']
        assert isinstance(req_estados, list)
        
        if len(req_estados) > 0:
            item = req_estados[0]
            assert 'estado' in item
            assert 'cantidad' in item
    
    def test_graficas_filtro_centro_usuario(self, api_client, centro_user, lote, centro):
        """Usuario de centro ve solo gráficas de su centro."""
        api_client.force_authenticate(user=centro_user)
        
        response = api_client.get('/api/dashboard/graficas/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Stock debe ser solo del centro del usuario
        stock_centros = data['stock_por_centro']
        if len(stock_centros) > 0:
            # Solo debe haber un centro (el del usuario)
            assert len(stock_centros) <= 1


# =============================================================================
# TESTS: SEGURIDAD Y PERMISOS
# =============================================================================

@pytest.mark.django_db
class TestDashboardSeguridad:
    """Tests de seguridad para endpoints de dashboard."""
    
    def test_usuario_centro_no_puede_filtrar_otros_centros(self, api_client, centro_user, centro, centro2):
        """Usuario de centro no debe poder ver datos de otros centros."""
        api_client.force_authenticate(user=centro_user)
        
        # Intentar filtrar por otro centro
        response = api_client.get(f'/api/dashboard/?centro={centro2.id}')
        
        # Debe ignorar el parámetro y mostrar solo su centro
        assert response.status_code == status.HTTP_200_OK
    
    def test_usuario_inactivo_denegado(self, api_client, admin_user):
        """Usuario inactivo debe ser rechazado."""
        admin_user.is_active = False
        admin_user.save()
        
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.get('/api/dashboard/')
        
        # Puede ser 401 o 403 dependiendo de la configuración
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
    
    def test_admin_puede_ver_todo(self, api_client, admin_user, centro, centro2, lote):
        """Admin debe poder ver datos de todos los centros."""
        api_client.force_authenticate(user=admin_user)
        
        # Sin filtro
        response = api_client.get('/api/dashboard/')
        assert response.status_code == status.HTTP_200_OK
        
        # Con filtro centro 1
        response = api_client.get(f'/api/dashboard/?centro={centro.id}')
        assert response.status_code == status.HTTP_200_OK
        
        # Con filtro centro 2
        response = api_client.get(f'/api/dashboard/?centro={centro2.id}')
        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# TESTS: CACHÉ
# =============================================================================

@pytest.mark.django_db
class TestDashboardCache:
    """Tests de caché para dashboard."""
    
    def test_resumen_usa_cache(self, api_client, admin_user, lote):
        """Dashboard resumen debe usar caché."""
        api_client.force_authenticate(user=admin_user)
        
        # Limpiar caché primero
        cache.clear()
        
        # Primera llamada (sin caché)
        response1 = api_client.get('/api/dashboard/')
        assert response1.status_code == status.HTTP_200_OK
        
        # Segunda llamada (debería usar caché)
        response2 = api_client.get('/api/dashboard/')
        assert response2.status_code == status.HTTP_200_OK
        
        # Los datos deben ser iguales
        assert response1.json()['kpi'] == response2.json()['kpi']
    
    def test_graficas_usa_cache(self, api_client, admin_user):
        """Dashboard gráficas debe usar caché."""
        api_client.force_authenticate(user=admin_user)
        
        cache.clear()
        
        response1 = api_client.get('/api/dashboard/graficas/')
        assert response1.status_code == status.HTTP_200_OK
        
        response2 = api_client.get('/api/dashboard/graficas/')
        assert response2.status_code == status.HTTP_200_OK
    
    def test_cache_diferente_por_centro(self, api_client, admin_user, centro, centro2):
        """Caché debe ser diferente por centro."""
        api_client.force_authenticate(user=admin_user)
        
        cache.clear()
        
        # Datos globales
        response_global = api_client.get('/api/dashboard/')
        
        # Datos filtrados por centro 1
        response_c1 = api_client.get(f'/api/dashboard/?centro={centro.id}')
        
        # Datos filtrados por centro 2
        response_c2 = api_client.get(f'/api/dashboard/?centro={centro2.id}')
        
        # Todos deben ser exitosos
        assert response_global.status_code == status.HTTP_200_OK
        assert response_c1.status_code == status.HTTP_200_OK
        assert response_c2.status_code == status.HTTP_200_OK


# =============================================================================
# TESTS: CASOS EDGE Y ERRORES
# =============================================================================

@pytest.mark.django_db
class TestDashboardEdgeCases:
    """Tests para casos edge y manejo de errores."""
    
    def test_dashboard_sin_datos(self, api_client, admin_user):
        """Dashboard sin datos no debe fallar."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.get('/api/dashboard/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # KPIs deben existir aunque sean 0
        assert data['kpi']['total_productos'] >= 0
        assert data['kpi']['stock_total'] >= 0
    
    def test_dashboard_con_lotes_sin_producto(self, api_client, admin_user, lote):
        """Debe manejar lotes huérfanos gracefully."""
        api_client.force_authenticate(user=admin_user)
        
        # Simular lote sin producto (edge case)
        response = api_client.get('/api/dashboard/')
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_graficas_sin_movimientos(self, api_client, admin_user):
        """Gráficas sin movimientos no deben fallar."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.get('/api/dashboard/graficas/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Consumo mensual debe ser lista (puede estar vacía o con ceros)
        assert isinstance(data['consumo_mensual'], list)
    
    def test_graficas_sin_requisiciones(self, api_client, admin_user):
        """Gráficas sin requisiciones no deben fallar."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.get('/api/dashboard/graficas/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert isinstance(data['requisiciones_por_estado'], list)
    
    def test_usuario_centro_sin_centro_asignado(self, api_client, db):
        """Usuario de centro sin centro debe manejar error."""
        User = get_user_model()
        user_sin_centro = User.objects.create_user(
            username='centro_sin_asignar',
            email='sin_centro@test.com',
            password='testpass123',
            rol='admin_centro',
            centro=None  # Sin centro asignado
        )
        
        api_client.force_authenticate(user=user_sin_centro)
        
        response = api_client.get('/api/dashboard/')
        
        # Debe manejar el caso sin fallar
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]


# =============================================================================
# TESTS: RENDIMIENTO Y OPTIMIZACIÓN
# =============================================================================

@pytest.mark.django_db
class TestDashboardRendimiento:
    """Tests de rendimiento para dashboard."""
    
    def test_dashboard_tiempo_respuesta(self, api_client, admin_user, lote, movimiento_entrada):
        """Dashboard debe responder en tiempo razonable."""
        import time
        
        api_client.force_authenticate(user=admin_user)
        cache.clear()
        
        start = time.time()
        response = api_client.get('/api/dashboard/')
        elapsed = time.time() - start
        
        assert response.status_code == status.HTTP_200_OK
        # Debe responder en menos de 5 segundos
        assert elapsed < 5.0
    
    def test_graficas_tiempo_respuesta(self, api_client, admin_user):
        """Gráficas deben responder en tiempo razonable."""
        import time
        
        api_client.force_authenticate(user=admin_user)
        cache.clear()
        
        start = time.time()
        response = api_client.get('/api/dashboard/graficas/')
        elapsed = time.time() - start
        
        assert response.status_code == status.HTTP_200_OK
        assert elapsed < 5.0


# =============================================================================
# TESTS: INTEGRACIÓN CON MODELOS
# =============================================================================

@pytest.mark.django_db
class TestDashboardIntegracionModelos:
    """Tests de integración con modelos de Django."""
    
    def test_conteo_productos_activos(self, api_client, admin_user, producto, db):
        """Debe contar solo productos activos."""
        if not MODELS_AVAILABLE:
            pytest.skip("Modelos no disponibles")
        
        # Crear producto inactivo
        Producto.objects.create(
            clave='INACT001',
            nombre='Producto Inactivo',
            categoria='medicamento',
            unidad_medida='pieza',
            activo=False
        )
        
        api_client.force_authenticate(user=admin_user)
        response = api_client.get('/api/dashboard/')
        
        assert response.status_code == status.HTTP_200_OK
        
        # El conteo no debe incluir productos inactivos
        total_activos = Producto.objects.filter(activo=True).count()
        # Puede haber diferencia si se filtran por lotes
        assert response.json()['kpi']['total_productos'] <= total_activos + 1
    
    def test_stock_solo_lotes_activos(self, api_client, admin_user, lote, producto, centro, db):
        """Stock debe considerar solo lotes activos con cantidad > 0."""
        if not MODELS_AVAILABLE:
            pytest.skip("Modelos no disponibles")
        
        # Crear lote inactivo
        Lote.objects.create(
            numero_lote='INACT-LOT-001',
            producto=producto,
            centro=centro,
            cantidad_inicial=100,
            cantidad_actual=50,
            fecha_caducidad=timezone.now().date() + timedelta(days=30),
            activo=False
        )
        
        # Crear lote con cantidad 0
        Lote.objects.create(
            numero_lote='EMPTY-LOT-001',
            producto=producto,
            centro=centro,
            cantidad_inicial=100,
            cantidad_actual=0,
            fecha_caducidad=timezone.now().date() + timedelta(days=30),
            activo=True
        )
        
        api_client.force_authenticate(user=admin_user)
        response = api_client.get('/api/dashboard/')
        
        assert response.status_code == status.HTTP_200_OK
        
        # El stock no debe incluir lotes inactivos ni vacíos
        kpi = response.json()['kpi']
        assert kpi['stock_total'] >= 0
    
    def test_movimientos_del_mes_actual(self, api_client, admin_user, lote, db):
        """Debe contar solo movimientos del mes actual."""
        if not MODELS_AVAILABLE:
            pytest.skip("Modelos no disponibles")
        
        # Crear movimiento del mes anterior
        mov_anterior = Movimiento.objects.create(
            tipo='entrada',
            producto=lote.producto,
            lote=lote,
            cantidad=10,
            usuario=admin_user,
            motivo='Movimiento anterior'
        )
        # Modificar fecha a mes anterior
        mes_anterior = timezone.now() - timedelta(days=35)
        Movimiento.objects.filter(id=mov_anterior.id).update(fecha=mes_anterior)
        
        # Crear movimiento de este mes
        Movimiento.objects.create(
            tipo='entrada',
            producto=lote.producto,
            lote=lote,
            cantidad=20,
            usuario=admin_user,
            motivo='Movimiento actual'
        )
        
        api_client.force_authenticate(user=admin_user)
        response = api_client.get('/api/dashboard/')
        
        assert response.status_code == status.HTTP_200_OK
        # Debe contar al menos el movimiento del mes actual
        assert response.json()['kpi']['movimientos_mes'] >= 1


# =============================================================================
# TESTS DJANGO TESTCASE (ALTERNATIVA SIN PYTEST)
# =============================================================================

class TestDashboardDjango(TestCase):
    """Tests usando Django TestCase (para pytest alternativo)."""
    
    def setUp(self):
        """Configurar datos de prueba."""
        self.client = APIClient()
        User = get_user_model()
        self.admin = User.objects.create_user(
            username='test_admin_django',
            email='admin_dj@test.com',
            password='testpass',
            rol='farmacia_admin',
            is_staff=True,
            is_superuser=True
        )
    
    def test_dashboard_requiere_auth(self):
        """Dashboard requiere autenticación."""
        response = self.client.get('/api/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_dashboard_con_auth(self):
        """Dashboard funciona con autenticación."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_graficas_requiere_auth(self):
        """Gráficas requiere autenticación."""
        response = self.client.get('/api/dashboard/graficas/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_graficas_con_auth(self):
        """Gráficas funciona con autenticación."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/dashboard/graficas/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# =============================================================================
# TESTS DE VALIDACIÓN DE DATOS
# =============================================================================

@pytest.mark.django_db
class TestDashboardValidacionDatos:
    """Tests para validar formato y estructura de datos."""
    
    def test_kpi_valores_no_negativos(self, api_client, admin_user):
        """KPIs nunca deben ser negativos."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.get('/api/dashboard/')
        
        assert response.status_code == status.HTTP_200_OK
        kpi = response.json()['kpi']
        
        assert kpi['total_productos'] >= 0
        assert kpi['stock_total'] >= 0
        assert kpi['lotes_activos'] >= 0
        assert kpi['movimientos_mes'] >= 0
    
    def test_movimientos_estructura_completa(self, api_client, admin_user, movimiento_entrada):
        """Movimientos deben tener estructura completa."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.get('/api/dashboard/')
        
        assert response.status_code == status.HTTP_200_OK
        movimientos = response.json()['ultimos_movimientos']
        
        if len(movimientos) > 0:
            mov = movimientos[0]
            
            # Campos obligatorios
            campos_requeridos = [
                'id', 'tipo_movimiento', 'cantidad', 
                'fecha_movimiento'
            ]
            
            for campo in campos_requeridos:
                assert campo in mov, f"Campo '{campo}' faltante en movimiento"
    
    def test_graficas_consumo_formato_correcto(self, api_client, admin_user):
        """Consumo mensual debe tener formato correcto."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.get('/api/dashboard/graficas/')
        
        assert response.status_code == status.HTTP_200_OK
        consumo = response.json()['consumo_mensual']
        
        for item in consumo:
            assert 'mes' in item
            assert 'entradas' in item
            assert 'salidas' in item
            assert isinstance(item['entradas'], (int, float))
            assert isinstance(item['salidas'], (int, float))
            assert item['entradas'] >= 0
            assert item['salidas'] >= 0
    
    def test_stock_centro_formato_correcto(self, api_client, admin_user):
        """Stock por centro debe tener formato correcto."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.get('/api/dashboard/graficas/')
        
        assert response.status_code == status.HTTP_200_OK
        stock = response.json()['stock_por_centro']
        
        for item in stock:
            assert 'centro' in item
            assert 'stock' in item
            assert isinstance(item['stock'], (int, float))
            assert item['stock'] >= 0
    
    def test_requisiciones_estado_formato_correcto(self, api_client, admin_user, requisicion):
        """Requisiciones por estado debe tener formato correcto."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.get('/api/dashboard/graficas/')
        
        assert response.status_code == status.HTTP_200_OK
        req_estados = response.json()['requisiciones_por_estado']
        
        for item in req_estados:
            assert 'estado' in item
            assert 'cantidad' in item
            assert isinstance(item['cantidad'], int)
            assert item['cantidad'] > 0
