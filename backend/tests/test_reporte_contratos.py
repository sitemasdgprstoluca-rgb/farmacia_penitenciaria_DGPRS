# -*- coding: utf-8 -*-
"""
Pruebas unitarias y de integración para el Reporte de Contratos.

Este módulo prueba:
1. Acceso por roles (solo admin/farmacia)
2. Agrupación correcta por número de contrato
3. Cálculo de cantidades iniciales, actuales y consumidas
4. Seguimiento de movimientos (entradas y salidas)
5. Estados del contrato (disponible, consumo_medio, por_agotar, agotado)
6. Exportación a JSON, Excel y PDF
7. Filtrado por número de contrato específico
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status as http_status

from core.models import User, Centro, Producto, Lote


@pytest.fixture
def api_client():
    """Cliente de API para pruebas."""
    return APIClient()


@pytest.fixture
def usuario_admin(db):
    """Crea un usuario administrador."""
    user = User.objects.create_user(
        username='admin_test',
        email='admin@test.com',
        password='TestPass123!',
        rol='admin',
        is_active=True
    )
    return user


@pytest.fixture
def usuario_farmacia(db):
    """Crea un usuario de farmacia."""
    user = User.objects.create_user(
        username='farmacia_test',
        email='farmacia@test.com',
        password='TestPass123!',
        rol='farmacia',
        is_active=True
    )
    return user


@pytest.fixture
def centro_test(db):
    """Crea un centro de prueba usando ORM."""
    # Temporalmente cambiar managed a True para crear via ORM
    original_managed = Centro._meta.managed
    Centro._meta.managed = True
    try:
        centro = Centro.objects.create(
            nombre='Centro Test Contratos',
            activo=True
        )
        return centro
    finally:
        Centro._meta.managed = original_managed


@pytest.fixture
def usuario_centro(db, centro_test):
    """Crea un usuario de centro (no debería tener acceso al reporte de contratos)."""
    user = User.objects.create_user(
        username='centro_test',
        email='centro@test.com',
        password='TestPass123!',
        rol='centro',
        centro=centro_test,
        is_active=True
    )
    return user


@pytest.fixture
def producto_prueba(db):
    """Crea un producto de prueba usando ORM."""
    original_managed = Producto._meta.managed
    Producto._meta.managed = True
    try:
        producto = Producto.objects.create(
            clave='MED-CONT-001',
            nombre='Paracetamol 500mg Test',
            descripcion='Analgésico para pruebas',
            presentacion='Caja c/20 tabletas',
            unidad_medida='CAJA',
            stock_minimo=10,
            activo=True
        )
        return producto
    finally:
        Producto._meta.managed = original_managed


@pytest.fixture
def producto_prueba_2(db):
    """Crea un segundo producto de prueba."""
    original_managed = Producto._meta.managed
    Producto._meta.managed = True
    try:
        producto = Producto.objects.create(
            clave='MED-CONT-002',
            nombre='Ibuprofeno 400mg Test',
            descripcion='Antiinflamatorio para pruebas',
            presentacion='Frasco c/30 tabletas',
            unidad_medida='FRASCO',
            stock_minimo=5,
            activo=True
        )
        return producto
    finally:
        Producto._meta.managed = original_managed


@pytest.fixture
def lotes_contrato_a(db, producto_prueba, producto_prueba_2):
    """Crea lotes para el contrato A con diferentes estados."""
    original_managed = Lote._meta.managed
    Lote._meta.managed = True
    lotes = []
    
    try:
        # Lote 1: Disponible (poco consumido)
        lote1 = Lote.objects.create(
            numero_lote='LOT-CONT-A-001',
            producto=producto_prueba,
            cantidad_inicial=100,
            cantidad_actual=90,  # 10% consumido
            fecha_caducidad=date.today() + timedelta(days=365),
            precio_unitario=Decimal('25.50'),
            numero_contrato='CONT-2025-A',
            marca='Bayer',
            activo=True
        )
        lotes.append(lote1)
        
        # Lote 2: Consumo medio (50% consumido)
        lote2 = Lote.objects.create(
            numero_lote='LOT-CONT-A-002',
            producto=producto_prueba,
            cantidad_inicial=200,
            cantidad_actual=100,  # 50% consumido
            fecha_caducidad=date.today() + timedelta(days=180),
            precio_unitario=Decimal('25.50'),
            numero_contrato='CONT-2025-A',
            marca='Bayer',
            activo=True
        )
        lotes.append(lote2)
        
        # Lote 3: Otro producto, mismo contrato
        lote3 = Lote.objects.create(
            numero_lote='LOT-CONT-A-003',
            producto=producto_prueba_2,
            cantidad_inicial=50,
            cantidad_actual=40,  # 20% consumido
            fecha_caducidad=date.today() + timedelta(days=270),
            precio_unitario=Decimal('35.00'),
            numero_contrato='CONT-2025-A',
            marca='Pfizer',
            activo=True
        )
        lotes.append(lote3)
        
        return lotes
    finally:
        Lote._meta.managed = original_managed


@pytest.fixture
def lotes_contrato_b(db, producto_prueba):
    """Crea lotes para el contrato B (agotado)."""
    original_managed = Lote._meta.managed
    Lote._meta.managed = True
    try:
        lote = Lote.objects.create(
            numero_lote='LOT-CONT-B-001',
            producto=producto_prueba,
            cantidad_inicial=50,
            cantidad_actual=0,  # 100% consumido = agotado
            fecha_caducidad=date.today() + timedelta(days=90),
            precio_unitario=Decimal('30.00'),
            numero_contrato='CONT-2025-B',
            marca='Genérico',
            activo=True
        )
        return [lote]
    finally:
        Lote._meta.managed = original_managed


class TestReporteContratosAcceso:
    """Pruebas de acceso por roles al reporte de contratos."""
    
    @pytest.mark.django_db
    def test_admin_puede_acceder(self, api_client, usuario_admin, lotes_contrato_a):
        """Admin debe poder acceder al reporte."""
        api_client.force_authenticate(user=usuario_admin)
        response = api_client.get('/api/reportes/contratos/')
        assert response.status_code == http_status.HTTP_200_OK
        assert 'datos' in response.data
        assert 'resumen' in response.data
    
    @pytest.mark.django_db
    def test_farmacia_puede_acceder(self, api_client, usuario_farmacia, lotes_contrato_a):
        """Farmacia debe poder acceder al reporte."""
        api_client.force_authenticate(user=usuario_farmacia)
        response = api_client.get('/api/reportes/contratos/')
        assert response.status_code == http_status.HTTP_200_OK
        assert 'datos' in response.data
    
    @pytest.mark.django_db
    def test_centro_no_puede_acceder(self, api_client, usuario_centro, lotes_contrato_a):
        """Usuario de centro NO debe poder acceder al reporte."""
        api_client.force_authenticate(user=usuario_centro)
        response = api_client.get('/api/reportes/contratos/')
        assert response.status_code == http_status.HTTP_403_FORBIDDEN
    
    @pytest.mark.django_db
    def test_usuario_anonimo_no_puede_acceder(self, api_client, lotes_contrato_a):
        """Usuario anónimo NO debe poder acceder."""
        response = api_client.get('/api/reportes/contratos/')
        assert response.status_code in [http_status.HTTP_401_UNAUTHORIZED, http_status.HTTP_403_FORBIDDEN]


class TestReporteContratosAgrupacion:
    """Pruebas de agrupación correcta por contrato."""
    
    @pytest.mark.django_db
    def test_agrupa_lotes_por_contrato(self, api_client, usuario_admin, lotes_contrato_a, lotes_contrato_b):
        """Debe agrupar correctamente los lotes por número de contrato."""
        api_client.force_authenticate(user=usuario_admin)
        response = api_client.get('/api/reportes/contratos/')
        
        assert response.status_code == http_status.HTTP_200_OK
        datos = response.data['datos']
        
        # Debe haber 2 contratos (A y B)
        assert len(datos) == 2
        
        # Buscar contrato A
        contrato_a = next((c for c in datos if 'A' in c['numero_contrato'].upper()), None)
        assert contrato_a is not None
        assert contrato_a['total_lotes'] == 3  # 3 lotes en contrato A
        assert contrato_a['total_productos'] == 2  # 2 productos únicos
        
        # Buscar contrato B
        contrato_b = next((c for c in datos if 'B' in c['numero_contrato'].upper()), None)
        assert contrato_b is not None
        assert contrato_b['total_lotes'] == 1
        assert contrato_b['total_productos'] == 1
    
    @pytest.mark.django_db
    def test_calculo_cantidades(self, api_client, usuario_admin, lotes_contrato_a):
        """Debe calcular correctamente cantidades iniciales, actuales y consumidas."""
        api_client.force_authenticate(user=usuario_admin)
        response = api_client.get('/api/reportes/contratos/')
        
        datos = response.data['datos']
        contrato_a = next((c for c in datos if 'A' in c['numero_contrato'].upper()), None)
        
        # Cantidades esperadas del contrato A:
        # Lote 1: 100 inicial, 90 actual
        # Lote 2: 200 inicial, 100 actual
        # Lote 3: 50 inicial, 40 actual
        # Total: 350 inicial, 230 actual, 120 consumido
        assert contrato_a['cantidad_inicial'] == 350
        assert contrato_a['cantidad_actual'] == 230
        assert contrato_a['cantidad_consumida'] == 120
    
    @pytest.mark.django_db
    def test_calculo_porcentaje_uso(self, api_client, usuario_admin, lotes_contrato_a, lotes_contrato_b):
        """Debe calcular correctamente el porcentaje de uso."""
        api_client.force_authenticate(user=usuario_admin)
        response = api_client.get('/api/reportes/contratos/')
        
        datos = response.data['datos']
        
        # Contrato B está agotado (100% uso)
        contrato_b = next((c for c in datos if 'B' in c['numero_contrato'].upper()), None)
        assert contrato_b['porcentaje_uso'] == 100.0
        
        # Contrato A tiene uso parcial
        contrato_a = next((c for c in datos if 'A' in c['numero_contrato'].upper()), None)
        # 120 consumido de 350 = 34.29%
        assert 30 < contrato_a['porcentaje_uso'] < 40


class TestReporteContratosEstados:
    """Pruebas de determinación de estados."""
    
    @pytest.mark.django_db
    def test_estado_agotado(self, api_client, usuario_admin, lotes_contrato_b):
        """Contrato con cantidad_actual=0 debe tener estado 'agotado'."""
        api_client.force_authenticate(user=usuario_admin)
        response = api_client.get('/api/reportes/contratos/')
        
        datos = response.data['datos']
        contrato_b = next((c for c in datos if 'B' in c['numero_contrato'].upper()), None)
        
        assert contrato_b['estado'] == 'agotado'
    
    @pytest.mark.django_db
    def test_estado_disponible(self, api_client, usuario_admin, lotes_contrato_a):
        """Contrato con <50% uso debe tener estado 'disponible'."""
        api_client.force_authenticate(user=usuario_admin)
        response = api_client.get('/api/reportes/contratos/')
        
        datos = response.data['datos']
        contrato_a = next((c for c in datos if 'A' in c['numero_contrato'].upper()), None)
        
        # 34% consumido = disponible (< 50%)
        assert contrato_a['estado'] == 'disponible'
    
    @pytest.mark.django_db
    def test_estado_por_agotar(self, api_client, usuario_admin, producto_prueba):
        """Contrato con >80% uso debe tener estado 'por_agotar'."""
        original_managed = Lote._meta.managed
        Lote._meta.managed = True
        try:
            # Crear lote casi agotado (85% consumido)
            Lote.objects.create(
                numero_lote='LOT-CONT-C-001',
                producto=producto_prueba,
                cantidad_inicial=100,
                cantidad_actual=15,  # 85% consumido
                fecha_caducidad=date.today() + timedelta(days=365),
                precio_unitario=Decimal('20.00'),
                numero_contrato='CONT-2025-C',
                activo=True
            )
        finally:
            Lote._meta.managed = original_managed
        
        api_client.force_authenticate(user=usuario_admin)
        response = api_client.get('/api/reportes/contratos/')
        
        datos = response.data['datos']
        contrato_c = next((c for c in datos if 'C' in c['numero_contrato'].upper()), None)
        
        assert contrato_c['estado'] == 'por_agotar'


class TestReporteContratosFiltros:
    """Pruebas de filtrado."""
    
    @pytest.mark.django_db
    def test_filtrar_por_contrato(self, api_client, usuario_admin, lotes_contrato_a, lotes_contrato_b):
        """Debe filtrar correctamente por número de contrato."""
        api_client.force_authenticate(user=usuario_admin)
        
        # Filtrar solo contrato A
        response = api_client.get('/api/reportes/contratos/?numero_contrato=A')
        
        assert response.status_code == http_status.HTTP_200_OK
        datos = response.data['datos']
        
        # Solo debe haber 1 contrato (A)
        assert len(datos) == 1
        assert 'A' in datos[0]['numero_contrato'].upper()
    
    @pytest.mark.django_db
    def test_filtro_case_insensitive(self, api_client, usuario_admin, lotes_contrato_a):
        """El filtro debe ser case-insensitive."""
        api_client.force_authenticate(user=usuario_admin)
        
        # Filtrar con minúsculas
        response = api_client.get('/api/reportes/contratos/?numero_contrato=cont-2025')
        
        assert response.status_code == http_status.HTTP_200_OK
        assert len(response.data['datos']) > 0


class TestReporteContratosExportacion:
    """Pruebas de exportación a diferentes formatos."""
    
    @pytest.mark.django_db
    def test_exportar_excel(self, api_client, usuario_admin, lotes_contrato_a):
        """Debe exportar correctamente a Excel."""
        api_client.force_authenticate(user=usuario_admin)
        response = api_client.get('/api/reportes/contratos/?formato=excel')
        
        assert response.status_code == http_status.HTTP_200_OK
        assert 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in response['Content-Type']
        assert 'attachment' in response['Content-Disposition']
        assert 'Contratos' in response['Content-Disposition']
    
    @pytest.mark.django_db
    def test_exportar_pdf(self, api_client, usuario_admin, lotes_contrato_a):
        """Debe exportar correctamente a PDF."""
        api_client.force_authenticate(user=usuario_admin)
        response = api_client.get('/api/reportes/contratos/?formato=pdf')
        
        assert response.status_code == http_status.HTTP_200_OK
        assert 'application/pdf' in response['Content-Type']
        assert 'attachment' in response['Content-Disposition']


class TestReporteContratosResumen:
    """Pruebas del resumen global."""
    
    @pytest.mark.django_db
    def test_resumen_totales(self, api_client, usuario_admin, lotes_contrato_a, lotes_contrato_b):
        """El resumen debe contener totales correctos."""
        api_client.force_authenticate(user=usuario_admin)
        response = api_client.get('/api/reportes/contratos/')
        
        resumen = response.data['resumen']
        
        assert 'total_contratos' in resumen
        assert resumen['total_contratos'] == 2
        
        assert 'total_lotes' in resumen
        assert resumen['total_lotes'] == 4  # 3 de A + 1 de B
        
        assert 'cantidad_inicial_global' in resumen
        assert 'cantidad_actual_global' in resumen
        assert 'valor_total_global' in resumen


class TestReporteContratosCasosEspeciales:
    """Pruebas de casos especiales y edge cases."""
    
    @pytest.mark.django_db
    def test_sin_lotes_con_contrato(self, api_client, usuario_admin, producto_prueba):
        """Sin lotes con número de contrato, debe retornar lista vacía para filtro específico."""
        original_managed = Lote._meta.managed
        Lote._meta.managed = True
        try:
            # Crear lote SIN número de contrato
            Lote.objects.create(
                numero_lote='LOT-SIN-CONTRATO-X',
                producto=producto_prueba,
                cantidad_inicial=100,
                cantidad_actual=100,
                fecha_caducidad=date.today() + timedelta(days=365),
                precio_unitario=Decimal('10.00'),
                numero_contrato='',  # Sin contrato
                activo=True
            )
        finally:
            Lote._meta.managed = original_managed
        
        api_client.force_authenticate(user=usuario_admin)
        # Buscar específicamente contratos sin datos
        response = api_client.get('/api/reportes/contratos/?numero_contrato=NO-EXISTE')
        
        assert response.status_code == http_status.HTTP_200_OK
        assert len(response.data['datos']) == 0
    
    @pytest.mark.django_db
    def test_lotes_inactivos_excluidos(self, api_client, usuario_admin, producto_prueba):
        """Los lotes inactivos deben ser excluidos del reporte."""
        original_managed = Lote._meta.managed
        Lote._meta.managed = True
        try:
            # Crear lote inactivo
            Lote.objects.create(
                numero_lote='LOT-INACTIVO-X',
                producto=producto_prueba,
                cantidad_inicial=100,
                cantidad_actual=100,
                fecha_caducidad=date.today() + timedelta(days=365),
                precio_unitario=Decimal('10.00'),
                numero_contrato='CONT-INACTIVO-X',
                activo=False  # Inactivo
            )
        finally:
            Lote._meta.managed = original_managed
        
        api_client.force_authenticate(user=usuario_admin)
        response = api_client.get('/api/reportes/contratos/')
        
        # No debe aparecer el contrato con lote inactivo
        datos = response.data['datos']
        contrato_inactivo = next((c for c in datos if 'INACTIVO-X' in c['numero_contrato'].upper()), None)
        assert contrato_inactivo is None
    
    @pytest.mark.django_db
    def test_valor_total_calculado_correctamente(self, api_client, usuario_admin, lotes_contrato_a):
        """El valor total debe calcularse como precio_unitario * cantidad_inicial."""
        api_client.force_authenticate(user=usuario_admin)
        response = api_client.get('/api/reportes/contratos/')
        
        datos = response.data['datos']
        contrato_a = next((c for c in datos if 'A' in c['numero_contrato'].upper()), None)
        
        # Valor esperado:
        # Lote 1: 25.50 * 100 = 2550
        # Lote 2: 25.50 * 200 = 5100
        # Lote 3: 35.00 * 50 = 1750
        # Total: 9400
        assert contrato_a['valor_total'] == 9400.00


# ============================================================================
# PRUEBAS DE INTEGRACIÓN MASIVAS
# ============================================================================

class TestReporteContratosMasivo:
    """Pruebas con volúmenes masivos de datos."""
    
    @pytest.mark.django_db
    def test_multiples_contratos(self, api_client, usuario_admin, producto_prueba):
        """Debe manejar múltiples contratos sin problemas."""
        original_managed = Lote._meta.managed
        Lote._meta.managed = True
        
        try:
            # Crear 10 contratos con 5 lotes cada uno
            for i in range(10):
                for j in range(5):
                    Lote.objects.create(
                        numero_lote=f'LOT-MASIVO-{i:02d}-{j:02d}',
                        producto=producto_prueba,
                        cantidad_inicial=100 + (i * 10),
                        cantidad_actual=50 + (j * 5),
                        fecha_caducidad=date.today() + timedelta(days=365 - i*30),
                        precio_unitario=Decimal(f'{20 + i}.00'),
                        numero_contrato=f'CONT-MASIVO-{i:03d}',
                        activo=True
                    )
        finally:
            Lote._meta.managed = original_managed
        
        api_client.force_authenticate(user=usuario_admin)
        response = api_client.get('/api/reportes/contratos/')
        
        assert response.status_code == http_status.HTTP_200_OK
        datos = response.data['datos']
        
        # Debe haber 10 contratos
        assert len(datos) == 10
        
        # Cada contrato debe tener 5 lotes
        for contrato in datos:
            assert contrato['total_lotes'] == 5
        
        # El resumen debe tener 50 lotes totales
        assert response.data['resumen']['total_lotes'] == 50
    
    @pytest.mark.django_db
    def test_exportar_excel_masivo(self, api_client, usuario_admin, producto_prueba):
        """Debe exportar a Excel con muchos registros."""
        original_managed = Lote._meta.managed
        Lote._meta.managed = True
        
        try:
            # Crear 20 contratos
            for i in range(20):
                Lote.objects.create(
                    numero_lote=f'LOT-EXCEL-{i:03d}',
                    producto=producto_prueba,
                    cantidad_inicial=100,
                    cantidad_actual=50,
                    fecha_caducidad=date.today() + timedelta(days=365),
                    precio_unitario=Decimal('25.00'),
                    numero_contrato=f'CONT-EXCEL-{i:03d}',
                    activo=True
                )
        finally:
            Lote._meta.managed = original_managed
        
        api_client.force_authenticate(user=usuario_admin)
        response = api_client.get('/api/reportes/contratos/?formato=excel')
        
        assert response.status_code == http_status.HTTP_200_OK
        # Verificar que el archivo tiene tamaño razonable
        assert len(response.content) > 1000  # Al menos 1KB
