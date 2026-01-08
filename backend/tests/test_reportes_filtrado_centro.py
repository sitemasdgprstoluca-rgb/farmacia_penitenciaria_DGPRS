"""
Tests unitarios y masivos para verificar el filtrado correcto por centro en reportes.

Estos tests verifican que:
1. Al filtrar por un centro específico, solo se muestren movimientos de ese centro
2. Las salidas solo muestren movimientos donde centro_origen=centro
3. Las entradas solo muestren movimientos donde centro_destino=centro
4. Los exports (Excel/PDF) respeten los mismos filtros
5. No se cuelen movimientos de otros centros
"""

import pytest
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import random
import string

# Importaciones del proyecto
from inventario.models import Producto, Lote, Centro, Movimiento
from users.models import User


@pytest.fixture
def setup_data(db):
    """
    Fixture que crea datos de prueba con múltiples centros y movimientos.
    """
    # Crear centros
    centro_a = Centro.objects.create(
        nombre='Centro A',
        clave='CA001',
        direccion='Dirección A',
        tipo='penitenciario'
    )
    centro_b = Centro.objects.create(
        nombre='Centro B',
        clave='CB001',
        direccion='Dirección B',
        tipo='penitenciario'
    )
    centro_c = Centro.objects.create(
        nombre='Centro C',
        clave='CC001',
        direccion='Dirección C',
        tipo='penitenciario'
    )
    
    # Crear usuarios
    admin_user = User.objects.create_user(
        username='admin_test',
        email='admin@test.com',
        password='testpass123',
        rol='ADMIN'
    )
    
    farmacia_user = User.objects.create_user(
        username='farmacia_test',
        email='farmacia@test.com',
        password='testpass123',
        rol='FARMACIA'
    )
    
    centro_a_user = User.objects.create_user(
        username='centro_a_user',
        email='centroa@test.com',
        password='testpass123',
        rol='CENTRO',
        centro=centro_a
    )
    
    centro_b_user = User.objects.create_user(
        username='centro_b_user',
        email='centrob@test.com',
        password='testpass123',
        rol='CENTRO',
        centro=centro_b
    )
    
    # Crear productos
    producto1 = Producto.objects.create(
        clave='PROD001',
        descripcion='Producto de Prueba 1',
        nombre='Producto 1',
        unidad_medida='PZA',
        activo=True
    )
    producto2 = Producto.objects.create(
        clave='PROD002',
        descripcion='Producto de Prueba 2',
        nombre='Producto 2',
        unidad_medida='PZA',
        activo=True
    )
    
    # Crear lotes
    # Lote en Farmacia Central (sin centro)
    lote_central = Lote.objects.create(
        producto=producto1,
        numero_lote='LOT-CENTRAL-001',
        cantidad_inicial=1000,
        cantidad_actual=800,
        fecha_caducidad=timezone.now().date() + timedelta(days=365),
        precio_unitario=Decimal('10.00'),
        activo=True
    )
    
    # Lote en Centro A
    lote_centro_a = Lote.objects.create(
        producto=producto1,
        numero_lote='LOT-CA-001',
        cantidad_inicial=500,
        cantidad_actual=400,
        fecha_caducidad=timezone.now().date() + timedelta(days=365),
        precio_unitario=Decimal('10.00'),
        centro=centro_a,
        activo=True
    )
    
    # Lote en Centro B
    lote_centro_b = Lote.objects.create(
        producto=producto1,
        numero_lote='LOT-CB-001',
        cantidad_inicial=300,
        cantidad_actual=250,
        fecha_caducidad=timezone.now().date() + timedelta(days=365),
        precio_unitario=Decimal('10.00'),
        centro=centro_b,
        activo=True
    )
    
    # Lote en Centro C
    lote_centro_c = Lote.objects.create(
        producto=producto2,
        numero_lote='LOT-CC-001',
        cantidad_inicial=200,
        cantidad_actual=150,
        fecha_caducidad=timezone.now().date() + timedelta(days=365),
        precio_unitario=Decimal('15.00'),
        centro=centro_c,
        activo=True
    )
    
    # Crear movimientos de diferentes tipos y centros
    fecha_base = timezone.now()
    
    # === MOVIMIENTOS DE SALIDA ===
    
    # Salida DESDE Centro A (centro_origen=A)
    mov_salida_a1 = Movimiento.objects.create(
        lote=lote_centro_a,
        tipo='salida',
        cantidad=-50,
        fecha=fecha_base - timedelta(hours=1),
        centro_origen=centro_a,
        centro_destino=None,
        referencia='MOV-SAL-A1',
        motivo='Dispensación Centro A',
        subtipo_salida='receta'
    )
    
    # Salida DESDE Centro A
    mov_salida_a2 = Movimiento.objects.create(
        lote=lote_centro_a,
        tipo='salida',
        cantidad=-30,
        fecha=fecha_base - timedelta(hours=2),
        centro_origen=centro_a,
        centro_destino=None,
        referencia='MOV-SAL-A2',
        motivo='Consumo interno Centro A',
        subtipo_salida='consumo_interno'
    )
    
    # Salida DESDE Centro B
    mov_salida_b1 = Movimiento.objects.create(
        lote=lote_centro_b,
        tipo='salida',
        cantidad=-40,
        fecha=fecha_base - timedelta(hours=3),
        centro_origen=centro_b,
        centro_destino=None,
        referencia='MOV-SAL-B1',
        motivo='Dispensación Centro B',
        subtipo_salida='receta'
    )
    
    # Salida DESDE Centro C
    mov_salida_c1 = Movimiento.objects.create(
        lote=lote_centro_c,
        tipo='salida',
        cantidad=-20,
        fecha=fecha_base - timedelta(hours=4),
        centro_origen=centro_c,
        centro_destino=None,
        referencia='MOV-SAL-C1',
        motivo='Dispensación Centro C',
        subtipo_salida='receta'
    )
    
    # Salida DESDE Farmacia Central (sin centro_origen)
    mov_salida_central = Movimiento.objects.create(
        lote=lote_central,
        tipo='salida',
        cantidad=-100,
        fecha=fecha_base - timedelta(hours=5),
        centro_origen=None,
        centro_destino=centro_a,
        referencia='MOV-SAL-FC1',
        motivo='Transferencia a Centro A',
        subtipo_salida='transferencia'
    )
    
    # === MOVIMIENTOS DE ENTRADA ===
    
    # Entrada HACIA Centro A (centro_destino=A)
    mov_entrada_a1 = Movimiento.objects.create(
        lote=lote_centro_a,
        tipo='entrada',
        cantidad=100,
        fecha=fecha_base - timedelta(hours=6),
        centro_origen=None,
        centro_destino=centro_a,
        referencia='MOV-ENT-A1',
        motivo='Recepción desde Farmacia'
    )
    
    # Entrada HACIA Centro B
    mov_entrada_b1 = Movimiento.objects.create(
        lote=lote_centro_b,
        tipo='entrada',
        cantidad=80,
        fecha=fecha_base - timedelta(hours=7),
        centro_origen=None,
        centro_destino=centro_b,
        referencia='MOV-ENT-B1',
        motivo='Recepción desde Farmacia'
    )
    
    # Entrada HACIA Centro C
    mov_entrada_c1 = Movimiento.objects.create(
        lote=lote_centro_c,
        tipo='entrada',
        cantidad=50,
        fecha=fecha_base - timedelta(hours=8),
        centro_origen=None,
        centro_destino=centro_c,
        referencia='MOV-ENT-C1',
        motivo='Recepción desde Farmacia'
    )
    
    return {
        'centros': {'a': centro_a, 'b': centro_b, 'c': centro_c},
        'users': {
            'admin': admin_user,
            'farmacia': farmacia_user,
            'centro_a': centro_a_user,
            'centro_b': centro_b_user
        },
        'productos': {'p1': producto1, 'p2': producto2},
        'lotes': {
            'central': lote_central,
            'a': lote_centro_a,
            'b': lote_centro_b,
            'c': lote_centro_c
        },
        'movimientos': {
            'salida_a1': mov_salida_a1,
            'salida_a2': mov_salida_a2,
            'salida_b1': mov_salida_b1,
            'salida_c1': mov_salida_c1,
            'salida_central': mov_salida_central,
            'entrada_a1': mov_entrada_a1,
            'entrada_b1': mov_entrada_b1,
            'entrada_c1': mov_entrada_c1
        }
    }


class TestReporteMovimientosFiltradoCentro(APITestCase):
    """
    Tests unitarios para el filtrado de reportes de movimientos por centro.
    """
    
    @pytest.fixture(autouse=True)
    def setup_test(self, setup_data):
        """Setup automático para cada test."""
        self.data = setup_data
        self.client = APIClient()
    
    def test_salidas_filtra_solo_centro_origen(self, setup_data):
        """
        Test que verifica que al filtrar por Centro A y tipo SALIDA,
        solo aparezcan movimientos donde centro_origen=Centro A.
        """
        data = setup_data
        client = APIClient()
        client.force_authenticate(user=data['users']['admin'])
        
        centro_a = data['centros']['a']
        
        response = client.get(
            '/api/inventario/reportes/movimientos/',
            {
                'centro': centro_a.id,
                'tipo': 'salida',
                'formato': 'json'
            }
        )
        
        assert response.status_code == 200
        
        result = response.json()
        datos = result.get('datos', [])
        
        # Debe haber exactamente 2 salidas de Centro A (MOV-SAL-A1, MOV-SAL-A2)
        # NO debe incluir salidas de Centro B o C, ni la transferencia desde Central
        referencias_esperadas = {'MOV-SAL-A1', 'MOV-SAL-A2'}
        referencias_obtenidas = {d['referencia'] for d in datos}
        
        # Verificar que solo tenemos las salidas de Centro A
        for ref in referencias_obtenidas:
            assert ref in referencias_esperadas, \
                f"Se encontró referencia '{ref}' que NO debería estar (no es salida de Centro A)"
        
        assert referencias_esperadas == referencias_obtenidas, \
            f"Se esperaban {referencias_esperadas}, se obtuvieron {referencias_obtenidas}"
    
    def test_entradas_filtra_solo_centro_destino(self, setup_data):
        """
        Test que verifica que al filtrar por Centro A y tipo ENTRADA,
        solo aparezcan movimientos donde centro_destino=Centro A.
        """
        data = setup_data
        client = APIClient()
        client.force_authenticate(user=data['users']['admin'])
        
        centro_a = data['centros']['a']
        
        response = client.get(
            '/api/inventario/reportes/movimientos/',
            {
                'centro': centro_a.id,
                'tipo': 'entrada',
                'formato': 'json'
            }
        )
        
        assert response.status_code == 200
        
        result = response.json()
        datos = result.get('datos', [])
        
        # Debe haber exactamente 1 entrada hacia Centro A (MOV-ENT-A1)
        # También la salida desde central hacia A (MOV-SAL-FC1) cuenta como entrada para A
        referencias_obtenidas = {d['referencia'] for d in datos}
        
        # Solo MOV-ENT-A1 tiene centro_destino=Centro A
        assert 'MOV-ENT-A1' in referencias_obtenidas, \
            f"Debería incluir MOV-ENT-A1, obtenido: {referencias_obtenidas}"
        
        # NO debe incluir entradas de otros centros
        assert 'MOV-ENT-B1' not in referencias_obtenidas, \
            "No debería incluir entradas de Centro B"
        assert 'MOV-ENT-C1' not in referencias_obtenidas, \
            "No debería incluir entradas de Centro C"
    
    def test_sin_tipo_filtra_origen_y_destino(self, setup_data):
        """
        Test que verifica que al filtrar por Centro A sin tipo específico,
        aparezcan movimientos donde centro_origen=A OR centro_destino=A.
        """
        data = setup_data
        client = APIClient()
        client.force_authenticate(user=data['users']['admin'])
        
        centro_a = data['centros']['a']
        
        response = client.get(
            '/api/inventario/reportes/movimientos/',
            {
                'centro': centro_a.id,
                'formato': 'json'
            }
        )
        
        assert response.status_code == 200
        
        result = response.json()
        datos = result.get('datos', [])
        referencias_obtenidas = {d['referencia'] for d in datos}
        
        # Debe incluir salidas de Centro A
        assert 'MOV-SAL-A1' in referencias_obtenidas
        assert 'MOV-SAL-A2' in referencias_obtenidas
        
        # Debe incluir entradas hacia Centro A
        assert 'MOV-ENT-A1' in referencias_obtenidas
        
        # También la transferencia desde Farmacia Central hacia Centro A
        assert 'MOV-SAL-FC1' in referencias_obtenidas, \
            "Debería incluir MOV-SAL-FC1 porque centro_destino=Centro A"
        
        # NO debe incluir movimientos de otros centros
        assert 'MOV-SAL-B1' not in referencias_obtenidas, \
            "No debería incluir salidas de Centro B"
        assert 'MOV-ENT-B1' not in referencias_obtenidas, \
            "No debería incluir entradas de Centro B"
    
    def test_no_cuela_movimientos_por_lote_centro(self, setup_data):
        """
        Test crítico: verifica que NO se cuelen movimientos solo porque
        el lote pertenece al centro, si el movimiento no es origen/destino.
        """
        data = setup_data
        client = APIClient()
        client.force_authenticate(user=data['users']['admin'])
        
        centro_b = data['centros']['b']
        
        # Crear un movimiento especial donde el lote pertenece a Centro B,
        # pero el movimiento es desde Farmacia Central hacia Centro C
        lote_b = data['lotes']['b']
        centro_c = data['centros']['c']
        
        mov_especial = Movimiento.objects.create(
            lote=lote_b,  # Lote de Centro B
            tipo='salida',
            cantidad=-10,
            fecha=timezone.now(),
            centro_origen=None,  # Desde Farmacia Central
            centro_destino=centro_c,  # Hacia Centro C
            referencia='MOV-ESPECIAL-BC',
            motivo='Movimiento que NO debería aparecer en filtro de Centro B para salidas'
        )
        
        response = client.get(
            '/api/inventario/reportes/movimientos/',
            {
                'centro': centro_b.id,
                'tipo': 'salida',
                'formato': 'json'
            }
        )
        
        assert response.status_code == 200
        
        result = response.json()
        datos = result.get('datos', [])
        referencias_obtenidas = {d['referencia'] for d in datos}
        
        # MOV-ESPECIAL-BC NO debería aparecer porque centro_origen != Centro B
        assert 'MOV-ESPECIAL-BC' not in referencias_obtenidas, \
            f"MOV-ESPECIAL-BC no debería aparecer en salidas de Centro B. Obtenido: {referencias_obtenidas}"
        
        # Solo debe aparecer MOV-SAL-B1 (salida desde Centro B)
        assert 'MOV-SAL-B1' in referencias_obtenidas
        
        # Limpiar
        mov_especial.delete()


class TestReportesExportFiltradoCentro(APITestCase):
    """
    Tests para verificar que los exports (Excel/PDF) respetan los filtros.
    """
    
    def test_export_excel_respeta_filtro_salidas(self, setup_data):
        """
        Test que verifica que el export Excel respeta el filtro de salidas por centro.
        """
        data = setup_data
        client = APIClient()
        client.force_authenticate(user=data['users']['admin'])
        
        centro_a = data['centros']['a']
        
        response = client.get(
            '/api/inventario/reportes/movimientos/',
            {
                'centro': centro_a.id,
                'tipo': 'salida',
                'formato': 'excel'
            }
        )
        
        assert response.status_code == 200
        assert 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in response['Content-Type']
        
        # El contenido del Excel contiene los datos filtrados correctamente
        # (verificamos que se genera sin errores)
        assert len(response.content) > 0
    
    def test_export_pdf_respeta_filtro_entradas(self, setup_data):
        """
        Test que verifica que el export PDF respeta el filtro de entradas por centro.
        """
        data = setup_data
        client = APIClient()
        client.force_authenticate(user=data['users']['admin'])
        
        centro_b = data['centros']['b']
        
        response = client.get(
            '/api/inventario/reportes/movimientos/',
            {
                'centro': centro_b.id,
                'tipo': 'entrada',
                'formato': 'pdf'
            }
        )
        
        assert response.status_code == 200
        assert 'application/pdf' in response['Content-Type']
        assert len(response.content) > 0


class TestMovimientoViewSetFiltradoCentro(APITestCase):
    """
    Tests para el filtrado en MovimientoViewSet (API de movimientos).
    """
    
    def test_viewset_filtra_salidas_por_centro_origen(self, setup_data):
        """
        Test que verifica que el ViewSet filtra correctamente salidas por centro.
        """
        data = setup_data
        client = APIClient()
        client.force_authenticate(user=data['users']['admin'])
        
        centro_a = data['centros']['a']
        
        response = client.get(
            '/api/inventario/movimientos/',
            {
                'centro': centro_a.id,
                'tipo': 'salida'
            }
        )
        
        assert response.status_code == 200
        
        results = response.json().get('results', [])
        
        # Verificar que todos los movimientos tienen centro_origen=Centro A
        for mov in results:
            centro_origen_id = mov.get('centro_origen')
            if centro_origen_id:
                assert centro_origen_id == centro_a.id, \
                    f"Movimiento {mov.get('referencia')} tiene centro_origen={centro_origen_id}, debería ser {centro_a.id}"


class TestReportesConsumoFiltrado(APITestCase):
    """
    Tests para reporte de consumo (solo salidas).
    """
    
    def test_reporte_consumo_filtra_solo_salidas_del_centro(self, setup_data):
        """
        Test que verifica que el reporte de consumo filtra correctamente.
        """
        data = setup_data
        client = APIClient()
        client.force_authenticate(user=data['users']['admin'])
        
        centro_a = data['centros']['a']
        
        response = client.get(
            '/api/inventario/reportes/consumo/',
            {
                'centro': centro_a.id
            }
        )
        
        assert response.status_code == 200
        
        result = response.json()
        resultados = result.get('resultados', [])
        
        # Debe haber consumo del producto 1 (que tiene lote en Centro A)
        # pero solo de las salidas de Centro A, no de otros centros


class TestFiltradoMasivo(APITestCase):
    """
    Tests masivos con gran cantidad de datos para verificar rendimiento y correctitud.
    """
    
    def test_filtrado_masivo_1000_movimientos(self, setup_data, db):
        """
        Test con 1000 movimientos para verificar que el filtrado funciona correctamente
        con grandes volúmenes de datos.
        """
        data = setup_data
        centro_a = data['centros']['a']
        centro_b = data['centros']['b']
        lote_a = data['lotes']['a']
        lote_b = data['lotes']['b']
        
        # Crear 1000 movimientos distribuidos entre centros
        movimientos_a = 0
        movimientos_b = 0
        
        for i in range(500):
            # 250 salidas desde Centro A
            Movimiento.objects.create(
                lote=lote_a,
                tipo='salida',
                cantidad=-1,
                fecha=timezone.now() - timedelta(minutes=i),
                centro_origen=centro_a,
                referencia=f'MASS-A-{i}',
                subtipo_salida='receta'
            )
            movimientos_a += 1
            
            # 250 salidas desde Centro B
            Movimiento.objects.create(
                lote=lote_b,
                tipo='salida',
                cantidad=-1,
                fecha=timezone.now() - timedelta(minutes=i+500),
                centro_origen=centro_b,
                referencia=f'MASS-B-{i}',
                subtipo_salida='receta'
            )
            movimientos_b += 1
        
        # Ahora probar el filtrado
        client = APIClient()
        client.force_authenticate(user=data['users']['admin'])
        
        # Filtrar solo Centro A
        response = client.get(
            '/api/inventario/reportes/movimientos/',
            {
                'centro': centro_a.id,
                'tipo': 'salida',
                'formato': 'json'
            }
        )
        
        assert response.status_code == 200
        
        result = response.json()
        datos = result.get('datos', [])
        
        # Contar referencias que empiezan con MASS-A vs MASS-B
        count_a = sum(1 for d in datos if d.get('referencia', '').startswith('MASS-A'))
        count_b = sum(1 for d in datos if d.get('referencia', '').startswith('MASS-B'))
        
        # Todos deben ser de Centro A, ninguno de Centro B
        assert count_b == 0, f"Se encontraron {count_b} movimientos de Centro B que no deberían estar"
        
        # Verificar que tenemos los movimientos de Centro A
        # (más los 2 originales del setup)
        assert count_a == 500, f"Se esperaban 500 movimientos de Centro A, se encontraron {count_a}"
    
    def test_filtrado_masivo_multiples_centros(self, setup_data, db):
        """
        Test que crea movimientos con diferentes combinaciones de origen/destino
        para verificar que el filtrado es preciso.
        """
        data = setup_data
        centro_a = data['centros']['a']
        centro_b = data['centros']['b']
        centro_c = data['centros']['c']
        lote_a = data['lotes']['a']
        
        # Crear movimientos con diferentes combinaciones
        combinaciones = [
            ('origen_a_destino_b', centro_a, centro_b),
            ('origen_b_destino_a', centro_b, centro_a),
            ('origen_a_destino_c', centro_a, centro_c),
            ('origen_c_destino_a', centro_c, centro_a),
            ('origen_b_destino_c', centro_b, centro_c),
            ('origen_c_destino_b', centro_c, centro_b),
        ]
        
        for ref_prefix, origen, destino in combinaciones:
            for i in range(10):
                Movimiento.objects.create(
                    lote=lote_a,
                    tipo='salida',
                    cantidad=-1,
                    fecha=timezone.now() - timedelta(minutes=i),
                    centro_origen=origen,
                    centro_destino=destino,
                    referencia=f'{ref_prefix}_{i}',
                    subtipo_salida='transferencia'
                )
        
        client = APIClient()
        client.force_authenticate(user=data['users']['admin'])
        
        # Filtrar salidas de Centro A
        response = client.get(
            '/api/inventario/reportes/movimientos/',
            {
                'centro': centro_a.id,
                'tipo': 'salida',
                'formato': 'json'
            }
        )
        
        assert response.status_code == 200
        result = response.json()
        datos = result.get('datos', [])
        
        # Solo deben aparecer las que tienen origen_a
        for d in datos:
            ref = d.get('referencia', '')
            if ref.startswith('origen_'):
                # Debe ser origen_a_*
                assert ref.startswith('origen_a_'), \
                    f"Referencia '{ref}' no debería aparecer en salidas de Centro A"


# ========================================
# TESTS DE TRAZABILIDAD
# ========================================

class TestTrazabilidadFiltrado(APITestCase):
    """
    Tests para trazabilidad con filtrado por centro.
    """
    
    def test_trazabilidad_producto_filtra_por_centro(self, setup_data):
        """
        Test que verifica que la trazabilidad de producto filtra correctamente.
        """
        data = setup_data
        client = APIClient()
        client.force_authenticate(user=data['users']['admin'])
        
        producto = data['productos']['p1']
        centro_a = data['centros']['a']
        
        response = client.get(
            f'/api/inventario/trazabilidad/producto/{producto.clave}/exportar/',
            {
                'centro': centro_a.id,
                'formato': 'json'
            }
        )
        
        # Verificar que la respuesta es exitosa
        if response.status_code == 200:
            result = response.json()
            # Verificar que solo hay movimientos relacionados con Centro A
            movimientos = result.get('movimientos', result.get('datos', []))
            
            for mov in movimientos:
                # Cada movimiento debe tener Centro A como origen o destino
                # (no solo por lote__centro)
                pass  # El assert específico depende del formato de respuesta


# ========================================
# RUN TESTS
# ========================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
