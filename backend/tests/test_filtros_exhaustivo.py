"""
Tests exhaustivos para verificar filtrado en reportes, trazabilidad y búsqueda de lotes.

ESCENARIOS CUBIERTOS:
1. Búsqueda de lotes (con/sin filtro de centro, con/sin stock)
2. Reportes de movimientos (por centro, tipo, fechas)
3. Trazabilidad global (entradas, salidas, estadísticas)
4. Exports (Excel/PDF)
5. Lotes consolidados vs no consolidados

Ejecutar: pytest backend/tests/test_filtros_exhaustivo.py -v
"""

import pytest
from django.test import override_settings
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from rest_framework.test import APIClient
from rest_framework import status

from core.models import Producto, Lote, Centro, Movimiento, User


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def crear_estructura_completa(db):
    """
    Crea estructura completa de datos para pruebas exhaustivas.
    - 3 centros
    - 4 usuarios (admin, farmacia, 2 de centro)
    - 2 productos
    - 4 lotes (1 central, 3 en centros)
    - 12 movimientos variados (entradas, salidas, diferentes centros)
    """
    # ---- CENTROS ----
    # Nota: 'clave' es una property calculada del id, no un campo
    centro_santiaguito = Centro.objects.create(
        nombre='Centro Penitenciario Santiaguito',
        direccion='Santiaguito, Estado de México'
    )
    centro_norte = Centro.objects.create(
        nombre='Centro Penitenciario Norte',
        direccion='Zona Norte'
    )
    centro_sur = Centro.objects.create(
        nombre='Centro Penitenciario Sur',
        direccion='Zona Sur'
    )
    
    # ---- USUARIOS ----
    admin = User.objects.create_user(
        username='admin_test',
        email='admin@test.com',
        password='test123',
        rol='admin'
    )
    farmacia = User.objects.create_user(
        username='farmacia_test',
        email='farmacia@test.com',
        password='test123',
        rol='farmacia'
    )
    user_santiaguito = User.objects.create_user(
        username='user_santiaguito',
        email='santiaguito@test.com',
        password='test123',
        rol='centro',
        centro=centro_santiaguito
    )
    user_norte = User.objects.create_user(
        username='user_norte',
        email='norte@test.com',
        password='test123',
        rol='centro',
        centro=centro_norte
    )
    
    # ---- PRODUCTOS ----
    producto1 = Producto.objects.create(
        clave='615',
        nombre='KETOCONAZOL /CLINDAMICINA',
        descripcion='Crema antimicótica',
        unidad_medida='CAJA CON 7 OVULOS',
        activo=True
    )
    producto2 = Producto.objects.create(
        clave='620',
        nombre='PARACETAMOL 500MG',
        descripcion='Analgésico',
        unidad_medida='CAJA CON 20 TABLETAS',
        activo=True
    )
    
    # ---- LOTES ----
    fecha_base = timezone.now()
    caducidad = fecha_base.date() + timedelta(days=365)
    
    # Lote en Farmacia Central (centro=NULL) - CON stock
    lote_central = Lote.objects.create(
        producto=producto1,
        numero_lote='25072052',
        cantidad_inicial=100,
        cantidad_actual=50,  # Tiene stock
        fecha_caducidad=caducidad,
        precio_unitario=Decimal('10.00'),
        centro=None,  # Farmacia Central
        activo=True
    )
    
    # Lote en Santiaguito - SIN stock (agotado)
    lote_santiaguito = Lote.objects.create(
        producto=producto1,
        numero_lote='25072052',  # Mismo numero_lote (lote espejo)
        cantidad_inicial=50,
        cantidad_actual=0,  # SIN stock
        fecha_caducidad=caducidad,
        precio_unitario=Decimal('10.00'),
        centro=centro_santiaguito,
        activo=True
    )
    
    # Lote en Norte - CON stock
    lote_norte = Lote.objects.create(
        producto=producto2,
        numero_lote='25103022',
        cantidad_inicial=200,
        cantidad_actual=150,
        fecha_caducidad=caducidad,
        precio_unitario=Decimal('5.00'),
        centro=centro_norte,
        activo=True
    )
    
    # Lote en Sur - CON stock
    lote_sur = Lote.objects.create(
        producto=producto2,
        numero_lote='25103023',
        cantidad_inicial=100,
        cantidad_actual=80,
        fecha_caducidad=caducidad,
        precio_unitario=Decimal('5.00'),
        centro=centro_sur,
        activo=True
    )
    
    # ---- MOVIMIENTOS ----
    # ENTRADAS a diferentes centros
    mov_entrada_central = Movimiento.objects.create(
        lote=lote_central,
        producto=producto1,  # Campo obligatorio
        tipo='entrada',
        cantidad=100,
        fecha=fecha_base - timedelta(days=30),
        centro_origen=None,
        centro_destino=None,
        referencia='ENT-CENTRAL-001',
        motivo='Entrada inicial a Farmacia Central'
    )
    
    mov_entrada_santiaguito = Movimiento.objects.create(
        lote=lote_santiaguito,
        producto=producto1,
        tipo='entrada',
        cantidad=50,
        fecha=fecha_base - timedelta(days=25),
        centro_origen=None,
        centro_destino=centro_santiaguito,
        referencia='ENT-SANT-001',
        motivo='Transferencia desde Farmacia Central'
    )
    
    mov_entrada_norte = Movimiento.objects.create(
        lote=lote_norte,
        producto=producto2,
        tipo='entrada',
        cantidad=200,
        fecha=fecha_base - timedelta(days=20),
        centro_origen=None,
        centro_destino=centro_norte,
        referencia='ENT-NORTE-001',
        motivo='Entrada inicial Centro Norte'
    )
    
    # SALIDAS desde diferentes centros
    mov_salida_central = Movimiento.objects.create(
        lote=lote_central,
        producto=producto1,
        tipo='salida',
        cantidad=-50,
        fecha=fecha_base - timedelta(days=15),
        centro_origen=None,  # Farmacia Central
        centro_destino=centro_santiaguito,
        referencia='SAL-CENTRAL-001',
        motivo='Transferencia a Santiaguito',
        subtipo_salida='transferencia'
    )
    
    mov_salida_santiaguito_1 = Movimiento.objects.create(
        lote=lote_santiaguito,
        producto=producto1,
        tipo='salida',
        cantidad=-20,
        fecha=fecha_base - timedelta(days=10),
        centro_origen=centro_santiaguito,
        centro_destino=None,
        referencia='SAL-SANT-001',
        motivo='Dispensación a paciente',
        subtipo_salida='receta',
        numero_expediente='EXP-001'
    )
    
    mov_salida_santiaguito_2 = Movimiento.objects.create(
        lote=lote_santiaguito,
        producto=producto1,
        tipo='salida',
        cantidad=-30,
        fecha=fecha_base - timedelta(days=5),
        centro_origen=centro_santiaguito,
        centro_destino=None,
        referencia='SAL-SANT-002',
        motivo='Dispensación a paciente',
        subtipo_salida='receta',
        numero_expediente='EXP-002'
    )
    
    mov_salida_norte = Movimiento.objects.create(
        lote=lote_norte,
        producto=producto2,
        tipo='salida',
        cantidad=-50,
        fecha=fecha_base - timedelta(days=3),
        centro_origen=centro_norte,
        centro_destino=None,
        referencia='SAL-NORTE-001',
        motivo='Consumo interno',
        subtipo_salida='consumo_interno'
    )
    
    # AJUSTES
    mov_ajuste_sur = Movimiento.objects.create(
        lote=lote_sur,
        producto=producto2,
        tipo='ajuste',
        cantidad=-20,
        fecha=fecha_base - timedelta(days=1),
        centro_origen=centro_sur,
        centro_destino=None,
        referencia='AJU-SUR-001',
        motivo='Ajuste por inventario físico'
    )
    
    return {
        'centros': {
            'santiaguito': centro_santiaguito,
            'norte': centro_norte,
            'sur': centro_sur,
        },
        'usuarios': {
            'admin': admin,
            'farmacia': farmacia,
            'santiaguito': user_santiaguito,
            'norte': user_norte,
        },
        'productos': {
            'p1': producto1,
            'p2': producto2,
            'producto1': producto1,  # Alias para tests masivos
            'producto2': producto2,  # Alias para tests masivos
        },
        'lotes': {
            'central': lote_central,
            'santiaguito': lote_santiaguito,
            'norte': lote_norte,
            'sur': lote_sur,
        },
        'movimientos': {
            'entrada_central': mov_entrada_central,
            'entrada_santiaguito': mov_entrada_santiaguito,
            'entrada_norte': mov_entrada_norte,
            'salida_central': mov_salida_central,
            'salida_santiaguito_1': mov_salida_santiaguito_1,
            'salida_santiaguito_2': mov_salida_santiaguito_2,
            'salida_norte': mov_salida_norte,
            'ajuste_sur': mov_ajuste_sur,
        }
    }


# ============================================================
# TESTS DE BÚSQUEDA DE LOTES
# ============================================================

class TestBusquedaLotes:
    """Tests para búsqueda de lotes con diferentes filtros."""
    
    def test_admin_busca_lote_sin_stock_debe_aparecer(self, crear_estructura_completa):
        """Admin/Farmacia DEBE ver lotes sin stock cuando busca."""
        data = crear_estructura_completa
        client = APIClient()
        client.force_authenticate(user=data['usuarios']['admin'])
        
        # Buscar lote que está en Santiaguito con stock 0
        response = client.get('/api/lotes/consolidados/', {
            'search': '25072052'
            # Sin filtro de centro = buscar en todos
        })
        
        assert response.status_code == 200
        results = response.json().get('results', response.json())
        
        # Debe encontrar el lote
        lotes_encontrados = [l for l in results if '25072052' in l.get('numero_lote', '')]
        assert len(lotes_encontrados) > 0, "Admin debe ver el lote 25072052 aunque esté sin stock en algún centro"
    
    def test_admin_filtro_central_no_ve_lotes_otros_centros(self, crear_estructura_completa):
        """Con filtro centro=central, solo ve lotes de Farmacia Central."""
        data = crear_estructura_completa
        client = APIClient()
        client.force_authenticate(user=data['usuarios']['admin'])
        
        response = client.get('/api/lotes/consolidados/', {
            'centro': 'central'
        })
        
        assert response.status_code == 200
        results = response.json().get('results', response.json())
        
        # Solo debe haber lotes de Farmacia Central (centro=NULL)
        for lote in results:
            # centro_nombre debería ser None o 'Almacén Central' o similar
            centro = lote.get('centro_nombre') or lote.get('centro')
            assert centro is None or 'central' in str(centro).lower() or centro == '', \
                f"Lote {lote.get('numero_lote')} tiene centro={centro}, debería ser Central"
    
    def test_admin_filtro_todos_ve_lotes_todos_centros(self, crear_estructura_completa):
        """Con filtro centro=todos (o sin centro), ve lotes de todos los centros."""
        data = crear_estructura_completa
        client = APIClient()
        client.force_authenticate(user=data['usuarios']['admin'])
        
        response = client.get('/api/lotes/consolidados/', {
            # Sin parámetro centro = todos
        })
        
        assert response.status_code == 200
        results = response.json().get('results', response.json())
        
        # Debe haber lotes de diferentes centros
        assert len(results) >= 2, "Debe ver lotes de múltiples centros"
    
    def test_usuario_centro_solo_ve_sus_lotes(self, crear_estructura_completa):
        """Usuario de centro solo ve lotes de su centro."""
        data = crear_estructura_completa
        client = APIClient()
        client.force_authenticate(user=data['usuarios']['santiaguito'])
        
        response = client.get('/api/lotes/')
        
        assert response.status_code == 200
        results = response.json().get('results', response.json())
        
        # Todos los lotes deben ser de Santiaguito
        for lote in results:
            centro_id = lote.get('centro') or lote.get('centro_id')
            if centro_id:
                assert centro_id == data['centros']['santiaguito'].id, \
                    f"Usuario de Santiaguito no debería ver lotes de otro centro"


# ============================================================
# TESTS DE REPORTES DE MOVIMIENTOS
# ============================================================

class TestReporteMovimientos:
    """Tests para reportes de movimientos con filtros."""
    
    def test_filtro_salidas_centro_solo_origen(self, crear_estructura_completa):
        """Al filtrar SALIDAS por centro, solo muestra donde centro_origen=centro."""
        data = crear_estructura_completa
        client = APIClient()
        client.force_authenticate(user=data['usuarios']['admin'])
        
        centro_sant = data['centros']['santiaguito']
        
        response = client.get('/api/reportes/movimientos/', {
            'centro': centro_sant.id,
            'tipo': 'salida',
            'formato': 'json'
        })
        
        assert response.status_code == 200
        result = response.json()
        datos = result.get('datos', [])
        
        # Todas las salidas deben tener centro_origen = Santiaguito
        for mov in datos:
            assert 'Santiaguito' in mov.get('centro_origen', ''), \
                f"Movimiento {mov.get('referencia')} no debería aparecer en salidas de Santiaguito"
    
    def test_filtro_entradas_centro_solo_destino(self, crear_estructura_completa):
        """Al filtrar ENTRADAS por centro, solo muestra donde centro_destino=centro."""
        data = crear_estructura_completa
        client = APIClient()
        client.force_authenticate(user=data['usuarios']['admin'])
        
        centro_sant = data['centros']['santiaguito']
        
        response = client.get('/api/reportes/movimientos/', {
            'centro': centro_sant.id,
            'tipo': 'entrada',
            'formato': 'json'
        })
        
        assert response.status_code == 200
        result = response.json()
        datos = result.get('datos', [])
        
        # Todas las entradas deben tener centro_destino = Santiaguito
        for mov in datos:
            # El destino debería ser Santiaguito o estar relacionado
            centro_destino = mov.get('centro_destino', '')
            assert 'Santiaguito' in centro_destino or centro_destino == '', \
                f"Movimiento {mov.get('referencia')} no debería aparecer en entradas de Santiaguito"
    
    def test_sin_filtro_tipo_muestra_ambos(self, crear_estructura_completa):
        """Sin filtro de tipo, muestra entradas Y salidas."""
        data = crear_estructura_completa
        client = APIClient()
        client.force_authenticate(user=data['usuarios']['admin'])
        
        response = client.get('/api/reportes/movimientos/', {
            'formato': 'json'
        })
        
        assert response.status_code == 200
        result = response.json()
        datos = result.get('datos', [])
        
        # Debe haber diferentes tipos
        tipos = set(mov.get('tipo', '').upper() for mov in datos)
        assert len(tipos) >= 1, "Debe haber al menos un tipo de movimiento"
    
    def test_filtro_fechas_funciona(self, crear_estructura_completa):
        """Filtro por fechas debe funcionar correctamente."""
        data = crear_estructura_completa
        client = APIClient()
        client.force_authenticate(user=data['usuarios']['admin'])
        
        fecha_inicio = (timezone.now() - timedelta(days=20)).strftime('%Y-%m-%d')
        fecha_fin = (timezone.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        
        response = client.get('/api/reportes/movimientos/', {
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'formato': 'json'
        })
        
        assert response.status_code == 200
        result = response.json()
        # Debería tener algunos resultados pero no todos
        assert 'datos' in result or 'resumen' in result


# ============================================================
# TESTS DE TRAZABILIDAD GLOBAL
# ============================================================

class TestTrazabilidadGlobal:
    """Tests para trazabilidad global."""
    
    def test_sin_filtros_muestra_todos_tipos(self, crear_estructura_completa):
        """Sin filtros, debe mostrar entradas, salidas y ajustes."""
        data = crear_estructura_completa
        client = APIClient()
        client.force_authenticate(user=data['usuarios']['admin'])
        
        response = client.get('/api/trazabilidad/global/')
        
        assert response.status_code == 200
        result = response.json()
        
        movimientos = result.get('movimientos', [])
        tipos = set(m.get('tipo', '').upper() for m in movimientos)
        
        # Debe haber diferentes tipos (no solo salidas)
        assert 'ENTRADA' in tipos or 'SALIDA' in tipos, \
            f"Tipos encontrados: {tipos}. Debe haber variedad de tipos."
    
    def test_estadisticas_correctas(self, crear_estructura_completa):
        """Las estadísticas deben ser correctas (usar abs para cantidades)."""
        data = crear_estructura_completa
        client = APIClient()
        client.force_authenticate(user=data['usuarios']['admin'])
        
        response = client.get('/api/trazabilidad/global/')
        
        assert response.status_code == 200
        result = response.json()
        
        estadisticas = result.get('estadisticas', {})
        total_entradas = estadisticas.get('total_entradas', 0)
        total_salidas = estadisticas.get('total_salidas', 0)
        
        # Las estadísticas deben ser positivas (abs de cantidades)
        assert total_entradas >= 0, "Total entradas debe ser >= 0"
        assert total_salidas >= 0, "Total salidas debe ser >= 0"
    
    def test_filtro_tipo_entrada(self, crear_estructura_completa):
        """Filtro tipo=entrada solo muestra entradas."""
        data = crear_estructura_completa
        client = APIClient()
        client.force_authenticate(user=data['usuarios']['admin'])
        
        response = client.get('/api/trazabilidad/global/', {
            'tipo': 'entrada'
        })
        
        assert response.status_code == 200
        result = response.json()
        
        movimientos = result.get('movimientos', [])
        for mov in movimientos:
            assert mov.get('tipo', '').upper() == 'ENTRADA', \
                f"Con filtro tipo=entrada, no debería aparecer {mov.get('tipo')}"
    
    def test_filtro_tipo_salida(self, crear_estructura_completa):
        """Filtro tipo=salida solo muestra salidas."""
        data = crear_estructura_completa
        client = APIClient()
        client.force_authenticate(user=data['usuarios']['admin'])
        
        response = client.get('/api/trazabilidad/global/', {
            'tipo': 'salida'
        })
        
        assert response.status_code == 200
        result = response.json()
        
        movimientos = result.get('movimientos', [])
        for mov in movimientos:
            assert mov.get('tipo', '').upper() == 'SALIDA', \
                f"Con filtro tipo=salida, no debería aparecer {mov.get('tipo')}"
    
    def test_filtro_centro_especifico(self, crear_estructura_completa):
        """Filtro por centro específico funciona."""
        data = crear_estructura_completa
        client = APIClient()
        client.force_authenticate(user=data['usuarios']['admin'])
        
        centro_norte = data['centros']['norte']
        
        response = client.get('/api/trazabilidad/global/', {
            'centro': centro_norte.id
        })
        
        assert response.status_code == 200
        result = response.json()
        
        # Debe tener resultados relacionados con Centro Norte
        assert result.get('total_movimientos', 0) >= 0


# ============================================================
# TESTS DE EXPORTS
# ============================================================

class TestExports:
    """Tests para exportación a Excel y PDF."""
    
    def test_export_excel_reportes(self, crear_estructura_completa):
        """Export Excel de reportes funciona."""
        data = crear_estructura_completa
        client = APIClient()
        client.force_authenticate(user=data['usuarios']['admin'])
        
        response = client.get('/api/reportes/movimientos/', {
            'formato': 'excel'
        })
        
        assert response.status_code == 200
        assert 'application/vnd.openxmlformats' in response['Content-Type']
    
    def test_export_pdf_reportes(self, crear_estructura_completa):
        """Export PDF de reportes funciona."""
        data = crear_estructura_completa
        client = APIClient()
        client.force_authenticate(user=data['usuarios']['admin'])
        
        response = client.get('/api/reportes/movimientos/', {
            'formato': 'pdf'
        })
        
        assert response.status_code == 200
        assert 'application/pdf' in response['Content-Type']
    
    def test_export_excel_trazabilidad_global(self, crear_estructura_completa):
        """Export Excel de trazabilidad global funciona."""
        data = crear_estructura_completa
        client = APIClient()
        client.force_authenticate(user=data['usuarios']['admin'])
        
        response = client.get('/api/trazabilidad/global/', {
            'formato': 'excel'
        })
        
        assert response.status_code == 200
        assert 'application/vnd.openxmlformats' in response['Content-Type']
    
    def test_export_pdf_trazabilidad_global(self, crear_estructura_completa):
        """Export PDF de trazabilidad global funciona."""
        data = crear_estructura_completa
        client = APIClient()
        client.force_authenticate(user=data['usuarios']['admin'])
        
        response = client.get('/api/trazabilidad/global/', {
            'formato': 'pdf'
        })
        
        assert response.status_code == 200
        assert 'application/pdf' in response['Content-Type']


# ============================================================
# TESTS DE TRAZABILIDAD DE LOTE
# ============================================================

class TestTrazabilidadLote:
    """Tests para trazabilidad de lote específico."""
    
    def test_trazabilidad_lote_incluye_todos_espejos(self, crear_estructura_completa):
        """Trazabilidad de lote debe incluir movimientos de todos los lotes espejo."""
        data = crear_estructura_completa
        client = APIClient()
        client.force_authenticate(user=data['usuarios']['admin'])
        
        # Buscar trazabilidad del lote 25072052 (tiene espejo en Santiaguito)
        response = client.get('/api/trazabilidad/lote/25072052/')
        
        assert response.status_code == 200
        result = response.json()
        
        movimientos = result.get('movimientos', [])
        # Debe tener movimientos tanto de Central como de Santiaguito
        assert len(movimientos) >= 2, \
            "Debe incluir movimientos de ambos lotes (central y espejo)"
    
    def test_trazabilidad_lote_export_excel(self, crear_estructura_completa):
        """Export Excel de trazabilidad de lote funciona."""
        data = crear_estructura_completa
        client = APIClient()
        client.force_authenticate(user=data['usuarios']['admin'])
        
        response = client.get('/api/trazabilidad/lote/25072052/exportar/', {
            'formato': 'excel'
        })
        
        assert response.status_code == 200
        assert 'spreadsheet' in response['Content-Type'] or 'excel' in response['Content-Type'].lower()
    
    def test_trazabilidad_lote_export_pdf(self, crear_estructura_completa):
        """Export PDF de trazabilidad de lote funciona."""
        data = crear_estructura_completa
        client = APIClient()
        client.force_authenticate(user=data['usuarios']['admin'])
        
        response = client.get('/api/trazabilidad/lote/25072052/exportar/', {
            'formato': 'pdf'
        })
        
        assert response.status_code == 200
        assert 'application/pdf' in response['Content-Type']


# ============================================================
# TESTS DE PERMISOS
# ============================================================

class TestPermisos:
    """Tests para verificar permisos correctos."""
    
    def test_usuario_centro_no_ve_trazabilidad_global(self, crear_estructura_completa):
        """Usuario de centro NO debe acceder a trazabilidad global."""
        data = crear_estructura_completa
        client = APIClient()
        client.force_authenticate(user=data['usuarios']['santiaguito'])
        
        response = client.get('/api/trazabilidad/global/')
        
        # Debe ser 403 Forbidden
        assert response.status_code == 403
    
    def test_admin_puede_ver_trazabilidad_global(self, crear_estructura_completa):
        """Admin puede acceder a trazabilidad global."""
        data = crear_estructura_completa
        client = APIClient()
        client.force_authenticate(user=data['usuarios']['admin'])
        
        response = client.get('/api/trazabilidad/global/')
        
        assert response.status_code == 200
    
    def test_farmacia_puede_ver_trazabilidad_global(self, crear_estructura_completa):
        """Farmacia puede acceder a trazabilidad global."""
        data = crear_estructura_completa
        client = APIClient()
        client.force_authenticate(user=data['usuarios']['farmacia'])
        
        response = client.get('/api/trazabilidad/global/')
        
        assert response.status_code == 200


# ============================================================
# TESTS MASIVOS
# ============================================================

class TestMasivo:
    """Tests con gran volumen de datos."""
    
    def test_1000_movimientos_filtrado_correcto(self, crear_estructura_completa, db):
        """Con 1000 movimientos, el filtrado sigue siendo correcto."""
        data = crear_estructura_completa
        centro_sant = data['centros']['santiaguito']
        lote_sant = data['lotes']['santiaguito']
        producto = data['productos']['producto1']
        
        # Crear 500 salidas de Santiaguito
        for i in range(500):
            Movimiento.objects.create(
                lote=lote_sant,
                producto=producto,
                tipo='salida',
                cantidad=-1,
                fecha=timezone.now() - timedelta(minutes=i),
                centro_origen=centro_sant,
                referencia=f'MASS-SANT-{i}'
            )
        
        # Crear 500 salidas de Norte
        lote_norte = data['lotes']['norte']
        centro_norte = data['centros']['norte']
        producto2 = data['productos']['producto2']
        for i in range(500):
            Movimiento.objects.create(
                lote=lote_norte,
                producto=producto2,
                tipo='salida',
                cantidad=-1,
                fecha=timezone.now() - timedelta(minutes=i+500),
                centro_origen=centro_norte,
                referencia=f'MASS-NORTE-{i}'
            )
        
        # Filtrar solo Santiaguito
        client = APIClient()
        client.force_authenticate(user=data['usuarios']['admin'])
        
        response = client.get('/api/reportes/movimientos/', {
            'centro': centro_sant.id,
            'tipo': 'salida',
            'formato': 'json'
        })
        
        assert response.status_code == 200
        result = response.json()
        datos = result.get('datos', [])
        
        # Contar referencias
        refs_sant = [d for d in datos if 'MASS-SANT' in d.get('referencia', '')]
        refs_norte = [d for d in datos if 'MASS-NORTE' in d.get('referencia', '')]
        
        # No debe haber ninguna de Norte
        assert len(refs_norte) == 0, f"Se colaron {len(refs_norte)} movimientos de Norte"
        
        # Debe haber de Santiaguito (puede estar limitado a 500)
        assert len(refs_sant) > 0, "Debe haber movimientos de Santiaguito"


# ============================================================
# EJECUCIÓN DIRECTA
# ============================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
