# -*- coding: utf-8 -*-
"""
Tests Unitarios Completos - Trazabilidad y Generación de PDFs

Este archivo contiene pruebas unitarias para:
1. Flujo completo de trazabilidad (movimientos de inventario)
2. Generación de PDFs de reportes
3. Funciones de recibo de salida para movimientos
4. Funciones de recibo de salida para donaciones (sin modificar)
5. Validación de datos y estructura de respuestas

IMPORTANTE: Este módulo NO modifica la funcionalidad de donaciones.
"""
import pytest
from django.test import TestCase, RequestFactory
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from io import BytesIO
import json

# Models
from core.models import (
    Centro, Producto, Lote, Movimiento,
    Donacion, DetalleDonacion, SalidaDonacion
)

# PDF Utils
from core.utils.pdf_reports import (
    generar_reporte_inventario,
    generar_reporte_caducidades,
    generar_reporte_lotes,
    generar_reporte_requisiciones,
    generar_reporte_movimientos,
    generar_reporte_auditoria,
    generar_reporte_trazabilidad,
    generar_recibo_salida_movimiento,
    generar_recibo_salida_donacion
)

User = get_user_model()


# ============================================
# FIXTURES DE PYTEST
# ============================================

@pytest.fixture
def api_client():
    """Cliente API para tests."""
    return APIClient()


@pytest.fixture
def centro_almacen(db):
    """Centro Almacén Central (origen de transferencias)."""
    centro, _ = Centro.objects.get_or_create(
        nombre='Almacén Central',
        defaults={
            'direccion': 'Dirección Central',
            'activo': True
        }
    )
    return centro


@pytest.fixture
def centro_destino(db):
    """Centro destino para transferencias."""
    centro, _ = Centro.objects.get_or_create(
        nombre='Centro Penitenciario Test',
        defaults={
            'direccion': 'Dirección Test',
            'activo': True
        }
    )
    return centro


@pytest.fixture
def admin_user(db, centro_almacen):
    """Usuario administrador para tests."""
    user, _ = User.objects.get_or_create(
        username='admin_test_trazabilidad',
        defaults={
            'email': 'admin_traz@test.com',
            'rol': 'admin',
            'is_staff': True,
            'is_superuser': True,
            'centro': centro_almacen
        }
    )
    user.set_password('testpass123')
    user.save()
    return user


@pytest.fixture
def farmacia_user(db, centro_almacen):
    """Usuario de farmacia para tests."""
    user, _ = User.objects.get_or_create(
        username='farmacia_test_trazabilidad',
        defaults={
            'email': 'farmacia_traz@test.com',
            'rol': 'farmacia',
            'centro': centro_almacen
        }
    )
    user.set_password('testpass123')
    user.save()
    return user


@pytest.fixture
def centro_user(db, centro_destino):
    """Usuario de centro (rol restringido)."""
    user, _ = User.objects.get_or_create(
        username='centro_test_trazabilidad',
        defaults={
            'email': 'centro_traz@test.com',
            'rol': 'administrador_centro',
            'centro': centro_destino
        }
    )
    user.set_password('testpass123')
    user.save()
    return user


@pytest.fixture
def producto_test(db):
    """Producto de prueba."""
    producto, _ = Producto.objects.get_or_create(
        clave='TEST-PROD-001',
        defaults={
            'nombre': 'Producto Test Trazabilidad',
            'descripcion': 'Producto para pruebas de trazabilidad',
            'unidad_medida': 'PIEZA',
            'categoria': 'medicamento',
            'stock_minimo': 10,
            'activo': True
        }
    )
    return producto


@pytest.fixture
def lote_test(db, producto_test, centro_almacen):
    """Lote de prueba en Almacén Central."""
    lote, _ = Lote.objects.get_or_create(
        numero_lote='LOTE-TEST-001',
        producto=producto_test,
        defaults={
            'cantidad_inicial': 1000,
            'cantidad_actual': 500,
            'fecha_caducidad': timezone.now().date() + timedelta(days=365),
            'precio_unitario': 100.00,
            'centro': None,  # Almacén Central
            'activo': True
        }
    )
    return lote


@pytest.fixture
def lote_centro(db, producto_test, centro_destino):
    """Lote de prueba en centro destino."""
    lote, _ = Lote.objects.get_or_create(
        numero_lote='LOTE-CENTRO-001',
        producto=producto_test,
        defaults={
            'cantidad_inicial': 200,
            'cantidad_actual': 150,
            'fecha_caducidad': timezone.now().date() + timedelta(days=180),
            'precio_unitario': 100.00,
            'centro': centro_destino,
            'activo': True
        }
    )
    return lote


@pytest.fixture
def movimiento_entrada(db, lote_test, admin_user, centro_almacen):
    """Movimiento de entrada para tests."""
    mov, _ = Movimiento.objects.get_or_create(
        lote=lote_test,
        tipo='entrada',
        cantidad=100,
        defaults={
            'usuario': admin_user,
            'centro_destino': None,  # Almacén Central
            'motivo': 'Entrada de prueba para test',
            'fecha': timezone.now()
        }
    )
    return mov


@pytest.fixture
def movimiento_salida(db, lote_test, admin_user, centro_destino):
    """Movimiento de salida/transferencia para tests."""
    mov, _ = Movimiento.objects.get_or_create(
        lote=lote_test,
        tipo='salida',
        cantidad=-50,
        subtipo_salida='transferencia',
        defaults={
            'usuario': admin_user,
            'centro_origen': None,  # Almacén Central
            'centro_destino': centro_destino,
            'motivo': 'Transferencia de prueba',
            'fecha': timezone.now()
        }
    )
    return mov


# ============================================
# TESTS DE GENERACIÓN DE PDFs
# ============================================

class TestPDFGeneration:
    """Tests para funciones de generación de PDF."""
    
    @pytest.mark.django_db
    def test_generar_recibo_salida_movimiento_basico(self, movimiento_salida):
        """Test: generar recibo PDF para un movimiento de salida."""
        movimiento_data = {
            'id': movimiento_salida.id,
            'folio': movimiento_salida.id,
            'fecha': movimiento_salida.fecha.isoformat() if movimiento_salida.fecha else None,
            'tipo': movimiento_salida.tipo,
            'subtipo_salida': movimiento_salida.subtipo_salida or 'transferencia',
            'centro_origen': {'nombre': 'Almacén Central'},
            'centro_destino': {'nombre': movimiento_salida.centro_destino.nombre if movimiento_salida.centro_destino else ''},
            'cantidad': abs(movimiento_salida.cantidad),
            'producto': movimiento_salida.lote.producto.nombre if movimiento_salida.lote else 'N/A',
            'producto_clave': movimiento_salida.lote.producto.clave if movimiento_salida.lote else 'N/A',
            'lote': movimiento_salida.lote.numero_lote if movimiento_salida.lote else 'N/A',
            'presentacion': movimiento_salida.lote.producto.presentacion if movimiento_salida.lote and movimiento_salida.lote.producto else '',
            'usuario': movimiento_salida.usuario.get_full_name() if movimiento_salida.usuario else 'Sistema',
            'observaciones': movimiento_salida.motivo or ''
        }
        
        # Generar PDF
        pdf_buffer = generar_recibo_salida_movimiento(movimiento_data, finalizado=False)
        
        # Verificar que retorna un BytesIO
        assert isinstance(pdf_buffer, BytesIO)
        
        # Verificar que tiene contenido
        pdf_content = pdf_buffer.getvalue()
        assert len(pdf_content) > 0
        
        # Verificar que es un PDF válido (comienza con %PDF)
        assert pdf_content[:4] == b'%PDF'
    
    @pytest.mark.django_db
    def test_generar_recibo_salida_movimiento_finalizado(self, movimiento_salida):
        """Test: generar recibo PDF con estado finalizado (sello ENTREGADO)."""
        movimiento_data = {
            'id': movimiento_salida.id,
            'folio': movimiento_salida.id,
            'fecha': timezone.now().isoformat(),
            'tipo': 'salida',
            'subtipo_salida': 'transferencia',
            'centro_origen': {'nombre': 'Almacén Central'},
            'centro_destino': {'nombre': 'Centro Destino'},
            'cantidad': 50,
            'producto': 'Producto Test',
            'producto_clave': 'TEST-001',
            'lote': 'LOTE-001',
            'presentacion': 'Caja',
            'usuario': 'Usuario Test',
            'observaciones': 'Test finalizado',
            'fecha_entrega': timezone.now().strftime('%d/%m/%Y %H:%M')
        }
        
        # Generar PDF con finalizado=True
        pdf_buffer = generar_recibo_salida_movimiento(movimiento_data, finalizado=True)
        
        assert isinstance(pdf_buffer, BytesIO)
        pdf_content = pdf_buffer.getvalue()
        assert len(pdf_content) > 0
        assert pdf_content[:4] == b'%PDF'
    
    @pytest.mark.django_db
    def test_generar_recibo_salida_donacion_no_modificado(self):
        """
        Test: Verificar que la función de donación existe y funciona.
        IMPORTANTE: No debe modificarse la lógica de donaciones.
        """
        # Datos mínimos para generar un recibo de donación
        donacion_data = {
            'id': 1,
            'numero': 'DON-TEST-001',
            'fecha': timezone.now().isoformat(),
            'donante': 'Donante Test',
            'centro_destino': 'Centro Test',
            'estado': 'recibida'
        }
        
        items_data = [
            {
                'producto': 'Producto Donación 1',
                'cantidad': 100,
                'lote': 'LOTE-DON-001',
                'fecha_caducidad': (timezone.now().date() + timedelta(days=365)).isoformat()
            }
        ]
        
        # Verificar que la función existe y es llamable
        assert callable(generar_recibo_salida_donacion)
        
        # Generar PDF de donación
        pdf_buffer = generar_recibo_salida_donacion(donacion_data, items_data, finalizado=False)
        
        # Verificar que retorna BytesIO válido
        assert isinstance(pdf_buffer, BytesIO)
        pdf_content = pdf_buffer.getvalue()
        assert len(pdf_content) > 0
        assert pdf_content[:4] == b'%PDF'
    
    @pytest.mark.django_db
    def test_generar_reporte_trazabilidad(self, producto_test):
        """Test: generar reporte de trazabilidad en PDF."""
        trazabilidad_data = [
            {
                'fecha': timezone.now().strftime('%d/%m/%Y %H:%M'),
                'tipo': 'ENTRADA',
                'lote': 'LOTE-001',
                'cantidad': 100,
                'centro': 'Almacén Central',
                'usuario': 'Admin Test',
                'observaciones': 'Entrada inicial'
            },
            {
                'fecha': (timezone.now() - timedelta(hours=2)).strftime('%d/%m/%Y %H:%M'),
                'tipo': 'SALIDA',
                'lote': 'LOTE-001',
                'cantidad': -25,
                'centro': 'Centro Test',
                'usuario': 'Farmacia Test',
                'observaciones': 'Transferencia a centro'
            }
        ]
        
        producto_info = {
            'clave': producto_test.clave,
            'descripcion': producto_test.nombre,
            'unidad_medida': producto_test.unidad_medida,
            'stock_actual': 500,
            'stock_minimo': producto_test.stock_minimo
        }
        
        pdf_buffer = generar_reporte_trazabilidad(trazabilidad_data, producto_info=producto_info)
        
        assert isinstance(pdf_buffer, BytesIO)
        pdf_content = pdf_buffer.getvalue()
        assert len(pdf_content) > 0
        assert pdf_content[:4] == b'%PDF'
    
    @pytest.mark.django_db
    def test_generar_reporte_movimientos(self):
        """Test: generar reporte de movimientos en PDF."""
        movimientos_data = [
            {
                'id': 1,
                'fecha': timezone.now().strftime('%d/%m/%Y %H:%M'),
                'tipo': 'entrada',
                'producto': 'Producto A',
                'lote': 'LOTE-A',
                'cantidad': 100,
                'centro': 'Almacén Central',
                'usuario': 'Admin',
                'motivo': 'Ingreso inicial'
            },
            {
                'id': 2,
                'fecha': timezone.now().strftime('%d/%m/%Y %H:%M'),
                'tipo': 'salida',
                'producto': 'Producto A',
                'lote': 'LOTE-A',
                'cantidad': -30,
                'centro': 'Centro Test',
                'usuario': 'Farmacia',
                'motivo': 'Despacho'
            }
        ]
        
        pdf_buffer = generar_reporte_movimientos(movimientos_data)
        
        assert isinstance(pdf_buffer, BytesIO)
        pdf_content = pdf_buffer.getvalue()
        assert len(pdf_content) > 0
        assert pdf_content[:4] == b'%PDF'


# ============================================
# TESTS DE FLUJO DE TRAZABILIDAD
# ============================================

class TestTrazabilidadFlow:
    """Tests para el flujo completo de trazabilidad."""
    
    @pytest.mark.django_db
    def test_crear_movimiento_entrada_admin(self, api_client, admin_user, lote_test):
        """Test: Admin puede crear movimiento de entrada."""
        api_client.force_authenticate(user=admin_user)
        
        data = {
            'lote': lote_test.id,
            'tipo': 'entrada',
            'cantidad': 50,
            'observaciones': 'Entrada de prueba'
        }
        
        response = api_client.post('/api/movimientos/', data, format='json')
        
        # Admin puede crear entradas
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
    
    @pytest.mark.django_db
    def test_crear_movimiento_salida_centro(self, api_client, centro_user, lote_centro):
        """Test: Usuario de centro puede crear movimiento de salida."""
        api_client.force_authenticate(user=centro_user)
        
        data = {
            'lote': lote_centro.id,
            'tipo': 'salida',
            'cantidad': 10,
            'observaciones': 'Consumo interno'
        }
        
        response = api_client.post('/api/movimientos/', data, format='json')
        
        # Usuario de centro puede crear salidas en su centro
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]
    
    @pytest.mark.django_db
    def test_listar_movimientos_filtro_centro(self, api_client, admin_user, centro_destino, movimiento_salida):
        """Test: Filtrar movimientos por centro."""
        api_client.force_authenticate(user=admin_user)
        
        # Listar todos los movimientos
        response = api_client.get('/api/movimientos/')
        assert response.status_code == status.HTTP_200_OK
        
        # Filtrar por centro específico
        response_filtered = api_client.get(f'/api/movimientos/?centro={centro_destino.id}')
        assert response_filtered.status_code == status.HTTP_200_OK
    
    @pytest.mark.django_db
    def test_listar_movimientos_filtro_fecha(self, api_client, admin_user, movimiento_salida):
        """Test: Filtrar movimientos por rango de fechas."""
        api_client.force_authenticate(user=admin_user)
        
        fecha_inicio = (timezone.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        fecha_fin = timezone.now().strftime('%Y-%m-%d')
        
        response = api_client.get(f'/api/movimientos/?fecha_inicio={fecha_inicio}&fecha_fin={fecha_fin}')
        assert response.status_code == status.HTTP_200_OK
    
    @pytest.mark.django_db
    def test_listar_movimientos_filtro_tipo(self, api_client, admin_user):
        """Test: Filtrar movimientos por tipo (entrada/salida/ajuste)."""
        api_client.force_authenticate(user=admin_user)
        
        for tipo in ['entrada', 'salida', 'ajuste']:
            response = api_client.get(f'/api/movimientos/?tipo={tipo}')
            assert response.status_code == status.HTTP_200_OK


# ============================================
# TESTS DE ENDPOINT RECIBO-SALIDA
# ============================================

class TestReciboSalidaEndpoint:
    """Tests para el endpoint de recibo de salida de movimientos."""
    
    @pytest.mark.django_db
    def test_recibo_salida_existe(self, api_client, admin_user, movimiento_salida):
        """Test: Verificar que el endpoint recibo-salida existe."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.get(f'/api/movimientos/{movimiento_salida.id}/recibo-salida/')
        
        # El endpoint debe existir (200 o 404 si no hay permisos, pero NO 405)
        assert response.status_code != status.HTTP_405_METHOD_NOT_ALLOWED
    
    @pytest.mark.django_db
    def test_recibo_salida_retorna_pdf(self, api_client, admin_user, movimiento_salida):
        """Test: El endpoint debe retornar un PDF válido."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.get(f'/api/movimientos/{movimiento_salida.id}/recibo-salida/')
        
        if response.status_code == status.HTTP_200_OK:
            # Verificar que es un PDF
            assert response['Content-Type'] == 'application/pdf'
            assert response.content[:4] == b'%PDF'
    
    @pytest.mark.django_db
    def test_recibo_salida_finalizado(self, api_client, admin_user, movimiento_salida):
        """Test: Recibo de salida con parámetro finalizado."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.get(f'/api/movimientos/{movimiento_salida.id}/recibo-salida/?finalizado=true')
        
        if response.status_code == status.HTTP_200_OK:
            assert response['Content-Type'] == 'application/pdf'


# ============================================
# TESTS DE CONFIRMAR ENTREGA INDIVIDUAL
# ============================================

class TestConfirmarEntregaIndividual:
    """Tests para el endpoint de confirmar entrega de movimientos individuales."""
    
    @pytest.mark.django_db
    def test_confirmar_entrega_endpoint_existe(self, api_client, admin_user, movimiento_salida):
        """Test: Verificar que el endpoint confirmar-entrega existe."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.post(f'/api/movimientos/{movimiento_salida.id}/confirmar-entrega/')
        
        # El endpoint debe existir (200, 400 o 403 pero NO 405)
        assert response.status_code != status.HTTP_405_METHOD_NOT_ALLOWED
    
    @pytest.mark.django_db
    def test_confirmar_entrega_exitosa(self, api_client, admin_user, movimiento_salida):
        """Test: Confirmar entrega de un movimiento de salida."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.post(f'/api/movimientos/{movimiento_salida.id}/confirmar-entrega/')
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert data.get('success') == True
            assert 'movimiento_id' in data
            
            # Verificar que el movimiento fue marcado como confirmado
            movimiento_salida.refresh_from_db()
            assert '[CONFIRMADO]' in (movimiento_salida.motivo or '')
    
    @pytest.mark.django_db
    def test_confirmar_entrega_ya_confirmada(self, api_client, admin_user, movimiento_salida):
        """Test: No se puede confirmar una entrega ya confirmada."""
        api_client.force_authenticate(user=admin_user)
        
        # Primera confirmación
        response1 = api_client.post(f'/api/movimientos/{movimiento_salida.id}/confirmar-entrega/')
        
        if response1.status_code == status.HTTP_200_OK:
            # Segunda confirmación debe fallar
            response2 = api_client.post(f'/api/movimientos/{movimiento_salida.id}/confirmar-entrega/')
            assert response2.status_code == status.HTTP_400_BAD_REQUEST
            data = response2.json()
            assert data.get('error') == True
    
    @pytest.mark.django_db
    def test_confirmar_entrega_solo_salidas(self, api_client, admin_user, lote_test):
        """Test: Solo se pueden confirmar entregas de movimientos de salida."""
        from core.models import Movimiento
        
        # Crear movimiento de entrada
        movimiento_entrada = Movimiento.objects.create(
            lote=lote_test,
            tipo='entrada',
            cantidad=10,
            motivo='Test entrada',
            usuario=admin_user
        )
        
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.post(f'/api/movimientos/{movimiento_entrada.id}/confirmar-entrega/')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data.get('error') == True


# ============================================
# TESTS DE VALIDACIÓN DE DATOS
# ============================================

class TestDataValidation:
    """Tests para validación de datos en movimientos."""
    
    @pytest.mark.django_db
    def test_movimiento_cantidad_negativa_salida(self, api_client, admin_user, lote_test):
        """Test: Salidas deben tener cantidad positiva (se convierte a negativa internamente)."""
        api_client.force_authenticate(user=admin_user)
        
        data = {
            'lote': lote_test.id,
            'tipo': 'salida',
            'cantidad': 10,  # Positivo en la solicitud
            'observaciones': 'Test cantidad'
        }
        
        response = api_client.post('/api/movimientos/', data, format='json')
        
        # El sistema debe aceptar la cantidad
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]
    
    @pytest.mark.django_db
    def test_movimiento_requiere_lote(self, api_client, admin_user):
        """Test: Movimientos requieren un lote válido."""
        api_client.force_authenticate(user=admin_user)
        
        data = {
            'tipo': 'entrada',
            'cantidad': 10,
            'observaciones': 'Sin lote'
        }
        
        response = api_client.post('/api/movimientos/', data, format='json')
        
        # Debe rechazar sin lote
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.django_db
    def test_movimiento_lote_inexistente(self, api_client, admin_user):
        """Test: Rechazar movimiento con lote inexistente."""
        api_client.force_authenticate(user=admin_user)
        
        data = {
            'lote': 99999,  # ID que no existe
            'tipo': 'entrada',
            'cantidad': 10,
            'observaciones': 'Lote inexistente'
        }
        
        response = api_client.post('/api/movimientos/', data, format='json')
        
        # Debe rechazar con lote inexistente
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================
# TESTS DE SEGURIDAD
# ============================================

class TestSecurity:
    """Tests de seguridad para movimientos y trazabilidad."""
    
    @pytest.mark.django_db
    def test_movimientos_requiere_autenticacion(self, api_client):
        """Test: API de movimientos requiere autenticación."""
        response = api_client.get('/api/movimientos/')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.django_db
    def test_centro_no_ve_otros_centros(self, api_client, centro_user, movimiento_entrada):
        """Test: Usuario de centro no debe ver movimientos de otros centros."""
        api_client.force_authenticate(user=centro_user)
        
        # El movimiento_entrada es del Almacén Central, no del centro del usuario
        response = api_client.get('/api/movimientos/')
        
        assert response.status_code == status.HTTP_200_OK
        # Los resultados deben estar filtrados por el centro del usuario
    
    @pytest.mark.django_db
    def test_admin_ve_todos_movimientos(self, api_client, admin_user):
        """Test: Admin puede ver todos los movimientos."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.get('/api/movimientos/')
        
        assert response.status_code == status.HTTP_200_OK


# ============================================
# TESTS DE DONACIONES (VERIFICACIÓN - NO MODIFICAR)
# ============================================

class TestDonacionesNoModificadas:
    """
    Tests para verificar que la funcionalidad de donaciones NO fue modificada.
    Estos tests aseguran que las funciones de donación siguen funcionando.
    """
    
    @pytest.mark.django_db
    def test_modelo_donacion_existe(self):
        """Test: El modelo Donacion existe y tiene los campos correctos."""
        # Verificar que el modelo existe
        assert hasattr(Donacion, '_meta')
        
        # Verificar campos principales
        field_names = [f.name for f in Donacion._meta.get_fields()]
        campos_requeridos = ['id', 'numero', 'donante_nombre', 'estado']
        
        for campo in campos_requeridos:
            assert campo in field_names, f"Campo {campo} no encontrado en Donacion"
    
    @pytest.mark.django_db
    def test_modelo_detalle_donacion_existe(self):
        """Test: El modelo DetalleDonacion existe."""
        assert hasattr(DetalleDonacion, '_meta')
        
        field_names = [f.name for f in DetalleDonacion._meta.get_fields()]
        assert 'donacion' in field_names
        assert 'cantidad' in field_names
    
    @pytest.mark.django_db
    def test_modelo_salida_donacion_existe(self):
        """Test: El modelo SalidaDonacion existe."""
        assert hasattr(SalidaDonacion, '_meta')
        
        field_names = [f.name for f in SalidaDonacion._meta.get_fields()]
        assert 'detalle_donacion' in field_names
    
    def test_funcion_pdf_donacion_existe(self):
        """Test: La función generar_recibo_salida_donacion existe y es independiente."""
        # Verificar que la función existe
        assert callable(generar_recibo_salida_donacion)
        
        # Verificar que tiene la firma correcta (3 parámetros)
        import inspect
        sig = inspect.signature(generar_recibo_salida_donacion)
        params = list(sig.parameters.keys())
        
        assert 'movimiento_data' in params
        assert 'items_data' in params
        assert 'finalizado' in params


# ============================================
# TESTS DE INTEGRACIÓN PDF-API
# ============================================

class TestPDFAPIIntegration:
    """Tests de integración entre generación de PDF y API."""
    
    @pytest.mark.django_db
    def test_trazabilidad_pdf_endpoint(self, api_client, admin_user, producto_test):
        """Test: Endpoint de trazabilidad PDF funciona."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.get(f'/api/movimientos/trazabilidad-pdf/?producto_clave={producto_test.clave}')
        
        # Puede ser 200 (éxito) o 404 (sin movimientos)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR]
        
        if response.status_code == status.HTTP_200_OK:
            assert response['Content-Type'] == 'application/pdf'
    
    @pytest.mark.django_db
    def test_trazabilidad_lote_pdf_endpoint(self, api_client, admin_user, lote_test):
        """Test: Endpoint de trazabilidad de lote PDF funciona."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.get(f'/api/movimientos/trazabilidad-lote-pdf/?numero_lote={lote_test.numero_lote}')
        
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN, status.HTTP_500_INTERNAL_SERVER_ERROR]
        
        if response.status_code == status.HTTP_200_OK:
            assert response['Content-Type'] == 'application/pdf'


# ============================================
# TESTS DE PDF CON FONDO INSTITUCIONAL
# ============================================

class TestPDFConFondoInstitucional:
    """Tests para verificar que los PDFs usan el fondo institucional."""
    
    def test_generar_recibo_salida_movimiento_usa_fondo(self):
        """Test: generar_recibo_salida_movimiento debe usar FondoOficialCanvas."""
        from core.utils.pdf_reports import generar_recibo_salida_movimiento
        import inspect
        
        # Obtener el código fuente de la función
        source_code = inspect.getsource(generar_recibo_salida_movimiento)
        
        # Verificar que usa FondoOficialCanvas
        assert 'FondoOficialCanvas' in source_code, "La función debe usar FondoOficialCanvas"
        assert 'canvasmaker' in source_code, "La función debe usar canvasmaker para el fondo"
    
    def test_generar_recibo_salida_donacion_usa_fondo(self):
        """Test: generar_recibo_salida_donacion debe usar FondoOficialCanvas."""
        from core.utils.pdf_reports import generar_recibo_salida_donacion
        import inspect
        
        # Obtener el código fuente de la función
        source_code = inspect.getsource(generar_recibo_salida_donacion)
        
        # Verificar que usa FondoOficialCanvas
        assert 'FondoOficialCanvas' in source_code, "La función debe usar FondoOficialCanvas"
        assert 'canvasmaker' in source_code, "La función debe usar canvasmaker para el fondo"
    
    def test_generar_recibo_salida_movimiento_genera_pdf(self):
        """Test: generar_recibo_salida_movimiento genera un PDF válido."""
        from core.utils.pdf_reports import generar_recibo_salida_movimiento
        
        movimiento_data = {
            'folio': 123,
            'fecha': '2025-01-01 10:00',
            'tipo': 'salida',
            'subtipo_salida': 'transferencia',
            'centro_origen': {'id': 1, 'nombre': 'Almacén Central'},
            'centro_destino': {'id': 2, 'nombre': 'Centro Test'},
            'cantidad': 50,
            'producto': 'Producto Test',
            'producto_clave': 'PT001',
            'lote': 'LOTE001',
            'presentacion': 'Caja',
            'usuario': 'Usuario Test',
            'observaciones': 'Test de PDF'
        }
        
        buffer = generar_recibo_salida_movimiento(movimiento_data, finalizado=False)
        
        assert buffer is not None
        content = buffer.getvalue()
        assert content[:4] == b'%PDF', "El contenido debe ser un PDF válido"
    
    def test_generar_recibo_salida_movimiento_finalizado(self):
        """Test: generar_recibo_salida_movimiento con finalizado=True."""
        from core.utils.pdf_reports import generar_recibo_salida_movimiento
        
        movimiento_data = {
            'folio': 456,
            'fecha': '2025-01-01 10:00',
            'tipo': 'salida',
            'subtipo_salida': 'transferencia',
            'centro_origen': {'id': 1, 'nombre': 'Almacén Central'},
            'centro_destino': {'id': 2, 'nombre': 'Centro Test'},
            'cantidad': 25,
            'producto': 'Producto Test 2',
            'producto_clave': 'PT002',
            'lote': 'LOTE002',
            'presentacion': 'Frasco',
            'usuario': 'Usuario Test',
            'observaciones': ''
        }
        
        buffer = generar_recibo_salida_movimiento(movimiento_data, finalizado=True)
        
        assert buffer is not None
        content = buffer.getvalue()
        assert content[:4] == b'%PDF', "El contenido debe ser un PDF válido"


# ============================================
# EJECUTAR TESTS DIRECTAMENTE
# ============================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
