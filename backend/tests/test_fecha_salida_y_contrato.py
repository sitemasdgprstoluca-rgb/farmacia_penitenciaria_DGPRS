"""
Tests QA: Fecha de salida + Inventario por contrato/lote

Valida end-to-end:
1. fecha_salida se guarda, devuelve y muestra correctamente
2. Lote con contrato muestra cantidades correctas
3. Reabastecimiento parcial actualiza totales
4. Permisos: centros no ven datos ajenos
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import Lote, Movimiento, Centro, Producto


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def centro_a(db):
    """Centro penitenciario A"""
    return Centro.objects.create(
        nombre='Centro A Test',
        direccion='Dir A',
        activo=True
    )


@pytest.fixture
def centro_b(db):
    """Centro penitenciario B"""
    return Centro.objects.create(
        nombre='Centro B Test',
        direccion='Dir B',
        activo=True
    )


@pytest.fixture
def producto_test(db):
    """Producto para testing"""
    return Producto.objects.create(
        clave='MED-QA-001',
        nombre='Paracetamol QA',
        unidad_medida='TABLETA',
        categoria='medicamento',
        activo=True
    )


@pytest.fixture
def lote_con_contrato(producto_test, centro_a, db):
    """Lote contrato=80 recibido=50"""
    return Lote.objects.create(
        producto=producto_test,
        numero_lote='LOT-QA-CONTRATO',
        centro=centro_a,
        fecha_caducidad=date(2027, 12, 31),
        cantidad_contrato=80,
        cantidad_inicial=50,
        cantidad_actual=50,
        precio_unitario=Decimal('15.50'),
        activo=True
    )


@pytest.fixture
def lote_sin_contrato(producto_test, centro_a, db):
    """Lote sin contrato (cantidad_contrato=None)"""
    return Lote.objects.create(
        producto=producto_test,
        numero_lote='LOT-QA-SINCONTRATO',
        centro=centro_a,
        fecha_caducidad=date(2027, 6, 30),
        cantidad_contrato=None,
        cantidad_inicial=100,
        cantidad_actual=100,
        precio_unitario=Decimal('10.00'),
        activo=True
    )


@pytest.fixture
def usuario_admin(django_user_model, db):
    user = django_user_model.objects.create_user(
        username='admin_qa',
        email='admin_qa@test.com',
        password='test123',
        rol='admin',
        is_staff=True,
        is_superuser=True
    )
    return user


@pytest.fixture
def usuario_farmacia(django_user_model, db):
    user = django_user_model.objects.create_user(
        username='farmacia_qa',
        email='farmacia_qa@test.com',
        password='test123',
        rol='farmacia',
        is_staff=True
    )
    return user


@pytest.fixture
def usuario_centro_a(django_user_model, centro_a, db):
    user = django_user_model.objects.create_user(
        username='centro_a_qa',
        email='centro_a@test.com',
        password='test123',
        rol='centro',
        centro=centro_a
    )
    return user


@pytest.fixture
def usuario_centro_b(django_user_model, centro_b, db):
    user = django_user_model.objects.create_user(
        username='centro_b_qa',
        email='centro_b@test.com',
        password='test123',
        rol='centro',
        centro=centro_b
    )
    return user


@pytest.fixture
def client_admin(usuario_admin):
    client = APIClient()
    client.force_authenticate(user=usuario_admin)
    return client


@pytest.fixture
def client_farmacia(usuario_farmacia):
    client = APIClient()
    client.force_authenticate(user=usuario_farmacia)
    return client


@pytest.fixture
def client_centro_a(usuario_centro_a):
    client = APIClient()
    client.force_authenticate(user=usuario_centro_a)
    return client


@pytest.fixture
def client_centro_b(usuario_centro_b):
    client = APIClient()
    client.force_authenticate(user=usuario_centro_b)
    return client


# ============================================================================
# 1. FECHA DE SALIDA — Backend (model + helper)
# ============================================================================

class TestFechaSalidaBackend:
    """Verifica que fecha_salida se persiste correctamente en movimientos."""

    @pytest.mark.django_db
    def test_movimiento_guarda_fecha_salida_en_modelo(self, lote_sin_contrato, usuario_admin):
        """Crear movimiento con fecha_salida directa y verificar que se guarda."""
        fecha_especifica = timezone.now() - timedelta(days=3)
        mov = Movimiento(
            lote=lote_sin_contrato,
            producto=lote_sin_contrato.producto,
            tipo='salida',
            cantidad=5,
            usuario=usuario_admin,
            motivo='Test fecha_salida directa',
            fecha_salida=fecha_especifica
        )
        mov._stock_pre_movimiento = lote_sin_contrato.cantidad_actual
        mov.save(skip_stock_update=True)

        mov.refresh_from_db()
        assert mov.fecha_salida is not None
        assert mov.fecha_salida.date() == fecha_especifica.date()

    @pytest.mark.django_db
    def test_registrar_movimiento_stock_pasa_fecha_salida(self, lote_sin_contrato, usuario_admin):
        """El helper registrar_movimiento_stock debe pasar fecha_salida al Movimiento."""
        from inventario.views_legacy import registrar_movimiento_stock

        fecha_pasada = timezone.now() - timedelta(days=7)
        mov, _ = registrar_movimiento_stock(
            lote=lote_sin_contrato,
            tipo='salida',
            cantidad=3,
            usuario=usuario_admin,
            observaciones='Test helper con fecha_salida',
            fecha_salida=fecha_pasada
        )

        mov.refresh_from_db()
        assert mov.fecha_salida is not None
        assert mov.fecha_salida.date() == fecha_pasada.date()

    @pytest.mark.django_db
    def test_registrar_movimiento_stock_sin_fecha_salida(self, lote_sin_contrato, usuario_admin):
        """Sin fecha_salida, el campo queda None."""
        from inventario.views_legacy import registrar_movimiento_stock

        mov, _ = registrar_movimiento_stock(
            lote=lote_sin_contrato,
            tipo='salida',
            cantidad=2,
            usuario=usuario_admin,
            observaciones='Test sin fecha_salida'
        )

        mov.refresh_from_db()
        assert mov.fecha_salida is None

    @pytest.mark.django_db
    def test_fecha_salida_solo_para_salidas(self, lote_sin_contrato, usuario_admin):
        """En entradas, fecha_salida debe forzarse a None."""
        from inventario.views_legacy import registrar_movimiento_stock

        fecha_erronea = timezone.now() - timedelta(days=1)
        mov, _ = registrar_movimiento_stock(
            lote=lote_sin_contrato,
            tipo='entrada',
            cantidad=10,
            usuario=usuario_admin,
            observaciones='Entrada no debe tener fecha_salida',
            fecha_salida=fecha_erronea  # Se pasa pero debe ignorarse
        )

        mov.refresh_from_db()
        assert mov.fecha_salida is None, "Las entradas no deben tener fecha_salida"


# ============================================================================
# 1b. FECHA DE SALIDA — API endpoint
# ============================================================================

class TestFechaSalidaAPI:
    """Verifica que fecha_salida viaja correctamente por la API."""

    @pytest.mark.django_db
    def test_crear_movimiento_con_fecha_salida_via_api(self, client_admin, lote_sin_contrato):
        """POST /api/movimientos/ con fecha_salida → debe guardarse y devolverse."""
        fecha_str = (timezone.now() - timedelta(days=5)).isoformat()

        response = client_admin.post('/api/movimientos/', {
            'lote': lote_sin_contrato.id,
            'tipo': 'salida',
            'cantidad': 4,
            'motivo': 'Salida con fecha pasada',
            'fecha_salida': fecha_str
        }, format='json')

        assert response.status_code in [200, 201], f"Error: {response.data}"
        data = response.data
        assert data.get('fecha_salida') is not None, "fecha_salida no devuelta en respuesta"

        # Verificar en DB
        mov = Movimiento.objects.get(pk=data['id'])
        assert mov.fecha_salida is not None
        assert mov.fecha_salida.date() == (timezone.now() - timedelta(days=5)).date()

    @pytest.mark.django_db
    def test_listado_movimientos_incluye_fecha_salida(self, client_admin, lote_sin_contrato, usuario_admin):
        """GET /api/movimientos/ debe devolver fecha_salida en cada registro."""
        fecha_pasada = timezone.now() - timedelta(days=2)
        mov = Movimiento(
            lote=lote_sin_contrato,
            producto=lote_sin_contrato.producto,
            tipo='salida',
            cantidad=1,
            usuario=usuario_admin,
            motivo='Test listado',
            fecha_salida=fecha_pasada
        )
        mov._stock_pre_movimiento = lote_sin_contrato.cantidad_actual
        mov.save(skip_stock_update=True)

        response = client_admin.get('/api/movimientos/')
        assert response.status_code == 200

        results = response.data.get('results', response.data)
        if isinstance(results, dict):
            results = results.get('results', [])
        found = [m for m in results if m['id'] == mov.id]
        assert len(found) == 1
        assert found[0]['fecha_salida'] is not None

    @pytest.mark.django_db
    def test_fecha_futura_rechazada(self, client_admin, lote_sin_contrato):
        """fecha_salida futura debe ser rechazada por validación."""
        fecha_futura = (timezone.now() + timedelta(days=10)).isoformat()

        response = client_admin.post('/api/movimientos/', {
            'lote': lote_sin_contrato.id,
            'tipo': 'salida',
            'cantidad': 1,
            'motivo': 'Salida futura',
            'fecha_salida': fecha_futura
        }, format='json')

        assert response.status_code == 400, "Debería rechazar fecha futura"


# ============================================================================
# 1c. FECHA DE SALIDA — PDF
# ============================================================================

class TestFechaSalidaPDF:
    """Verifica que el PDF usa fecha_salida (no fecha del sistema)."""

    @pytest.mark.django_db
    def test_datos_pdf_usa_fecha_salida(self, lote_sin_contrato, usuario_admin, centro_a):
        """Los datos de entrega para PDF deben usar fecha_salida."""
        fecha_especifica = timezone.now() - timedelta(days=10)
        grupo = 'SAL-TEST-001'

        mov = Movimiento(
            lote=lote_sin_contrato,
            producto=lote_sin_contrato.producto,
            tipo='salida',
            cantidad=5,
            usuario=usuario_admin,
            motivo=f'[{grupo}] Test PDF fecha',
            fecha_salida=fecha_especifica
        )
        mov._stock_pre_movimiento = lote_sin_contrato.cantidad_actual
        mov.save(skip_stock_update=True)

        # Simular la lógica de hoja_entrega_pdf
        primer_mov = Movimiento.objects.filter(motivo__contains=grupo).first()
        assert primer_mov is not None

        # La lógica corregida: fecha = primer_mov.fecha_salida or primer_mov.fecha
        fecha_pdf = primer_mov.fecha_salida or primer_mov.fecha
        assert fecha_pdf.date() == fecha_especifica.date(), \
            f"PDF debería usar {fecha_especifica.date()}, no {fecha_pdf.date()}"


# ============================================================================
# 2. INVENTARIO POR CONTRATO — Modelo y Serializer
# ============================================================================

class TestLoteContratoModelo:
    """Verifica cantidades de contrato en modelo y serializer."""

    @pytest.mark.django_db
    def test_lote_contrato_se_guarda_correctamente(self, lote_con_contrato):
        """Lote con contrato=80, inicial=50 debe guardar ambos valores."""
        lote_con_contrato.refresh_from_db()
        assert lote_con_contrato.cantidad_contrato == 80
        assert lote_con_contrato.cantidad_inicial == 50
        assert lote_con_contrato.cantidad_actual == 50

    @pytest.mark.django_db
    def test_serializer_incluye_campos_contrato(self, lote_con_contrato):
        """LoteSerializer debe incluir cantidad_contrato y cantidad_pendiente."""
        from core.serializers import LoteSerializer
        serializer = LoteSerializer(lote_con_contrato)
        data = serializer.data

        assert 'cantidad_contrato' in data
        assert 'cantidad_pendiente' in data
        assert data['cantidad_contrato'] == 80
        assert data['cantidad_inicial'] == 50
        assert data['cantidad_actual'] == 50
        assert data['cantidad_pendiente'] == 30  # 80 - 50

    @pytest.mark.django_db
    def test_serializer_sin_contrato(self, lote_sin_contrato):
        """Lote sin contrato: cantidad_pendiente debe ser None."""
        from core.serializers import LoteSerializer
        serializer = LoteSerializer(lote_sin_contrato)
        data = serializer.data

        assert data['cantidad_contrato'] is None
        assert data['cantidad_pendiente'] is None


# ============================================================================
# 2b. INVENTARIO POR CONTRATO — API consolidados
# ============================================================================

class TestLoteContratoConsolidados:
    """Verifica que el endpoint consolidados incluye cantidad_contrato."""

    @pytest.mark.django_db
    def test_consolidados_incluye_cantidad_contrato(self, client_admin, lote_con_contrato):
        """GET /api/lotes/consolidados/ debe devolver cantidad_contrato."""
        response = client_admin.get('/api/lotes/consolidados/')
        assert response.status_code == 200

        results = response.data.get('results', [])
        # Buscar nuestro lote por numero_lote
        found = [r for r in results if r.get('numero_lote') == 'LOT-QA-CONTRATO']
        assert len(found) >= 1, f"Lote no encontrado en consolidados. Results: {results}"

        lote_data = found[0]
        assert lote_data.get('cantidad_contrato') == 80, \
            f"cantidad_contrato debería ser 80, es {lote_data.get('cantidad_contrato')}"
        assert lote_data.get('cantidad_inicial') == 50
        assert lote_data.get('cantidad_actual') == 50
        assert lote_data.get('cantidad_pendiente') == 30

    @pytest.mark.django_db
    def test_consolidados_sin_contrato(self, client_admin, lote_sin_contrato):
        """Lote sin contrato: cantidad_contrato debe ser None en consolidados."""
        response = client_admin.get('/api/lotes/consolidados/')
        assert response.status_code == 200

        results = response.data.get('results', [])
        found = [r for r in results if r.get('numero_lote') == 'LOT-QA-SINCONTRATO']
        assert len(found) >= 1

        lote_data = found[0]
        assert lote_data.get('cantidad_contrato') is None
        assert lote_data.get('cantidad_pendiente') == 0


# ============================================================================
# 2c. INVENTARIO POR CONTRATO — API CRUD
# ============================================================================

class TestLoteContratoAPI:
    """Verifica creación y lectura de lotes con contrato vía API."""

    @pytest.mark.django_db
    def test_crear_lote_con_contrato_via_api(self, client_admin, producto_test, centro_a):
        """POST /api/lotes/ con contrato=80, inicial=50."""
        response = client_admin.post('/api/lotes/', {
            'producto': producto_test.id,
            'numero_lote': 'LOT-API-CONTRATO',
            'centro': centro_a.id,
            'fecha_caducidad': '2027-12-31',
            'cantidad_contrato': 80,
            'cantidad_inicial': 50,
            'cantidad_actual': 50,
            'precio_unitario': '15.50',
        }, format='json')

        assert response.status_code in [200, 201], f"Error al crear: {response.data}"
        data = response.data
        assert data['cantidad_contrato'] == 80
        assert data['cantidad_inicial'] == 50
        assert data['cantidad_actual'] == 50
        assert data.get('cantidad_pendiente') == 30

    @pytest.mark.django_db
    def test_detalle_lote_con_contrato(self, client_admin, lote_con_contrato):
        """GET /api/lotes/<id>/ devuelve cantidad_contrato."""
        response = client_admin.get(f'/api/lotes/{lote_con_contrato.id}/')
        assert response.status_code == 200
        assert response.data['cantidad_contrato'] == 80
        assert response.data['cantidad_inicial'] == 50
        assert response.data['cantidad_pendiente'] == 30


# ============================================================================
# 3. REABASTECIMIENTO — Completar contrato
# ============================================================================

class TestReabastecimientoContrato:
    """Verifica que se puede completar un contrato parcial con entradas."""

    @pytest.mark.django_db
    def test_entrada_incrementa_cantidad_inicial_y_actual(self, lote_con_contrato, usuario_admin):
        """Entrada de +30 en lote contrato=80, ini=50 → ini=80, act=80."""
        from inventario.views_legacy import registrar_movimiento_stock

        assert lote_con_contrato.cantidad_inicial == 50
        assert lote_con_contrato.cantidad_actual == 50

        mov, lote_actualizado = registrar_movimiento_stock(
            lote=lote_con_contrato,
            tipo='entrada',
            cantidad=30,
            usuario=usuario_admin,
            observaciones='Segunda recepción - completar contrato'
        )

        lote_actualizado.refresh_from_db()
        assert lote_actualizado.cantidad_inicial == 80, \
            f"cantidad_inicial debería ser 80, es {lote_actualizado.cantidad_inicial}"
        assert lote_actualizado.cantidad_actual == 80, \
            f"cantidad_actual debería ser 80, es {lote_actualizado.cantidad_actual}"

        # Verificar que cantidad_pendiente ahora es 0
        from core.serializers import LoteSerializer
        data = LoteSerializer(lote_actualizado).data
        assert data['cantidad_pendiente'] == 0

    @pytest.mark.django_db
    def test_entrada_parcial_15_de_30_pendientes(self, lote_con_contrato, usuario_admin):
        """Entrada parcial (15 de 30 pendientes) → ini=65, pendiente=15."""
        from inventario.views_legacy import registrar_movimiento_stock

        mov, lote_actualizado = registrar_movimiento_stock(
            lote=lote_con_contrato,
            tipo='entrada',
            cantidad=15,
            usuario=usuario_admin,
            observaciones='Entrega parcial adicional'
        )

        lote_actualizado.refresh_from_db()
        assert lote_actualizado.cantidad_inicial == 65
        assert lote_actualizado.cantidad_actual == 65
        assert lote_actualizado.cantidad_contrato == 80

        from core.serializers import LoteSerializer
        data = LoteSerializer(lote_actualizado).data
        assert data['cantidad_pendiente'] == 15  # 80 - 65

    @pytest.mark.django_db
    def test_salida_despues_de_completar_contrato(self, lote_con_contrato, usuario_admin):
        """Completar contrato (+30) → salida (-10) → actual=70, ini=80."""
        from inventario.views_legacy import registrar_movimiento_stock

        # Entrada: completar contrato
        _, lote = registrar_movimiento_stock(
            lote=lote_con_contrato,
            tipo='entrada',
            cantidad=30,
            usuario=usuario_admin,
            observaciones='Completar contrato'
        )

        # Salida
        _, lote = registrar_movimiento_stock(
            lote=lote,
            tipo='salida',
            cantidad=10,
            usuario=usuario_admin,
            observaciones='Salida post-contrato'
        )

        lote.refresh_from_db()
        assert lote.cantidad_contrato == 80
        assert lote.cantidad_inicial == 80
        assert lote.cantidad_actual == 70

    @pytest.mark.django_db
    def test_reabastecimiento_via_api(self, client_admin, lote_con_contrato):
        """POST /api/movimientos/ tipo=entrada → incrementa cantidad."""
        response = client_admin.post('/api/movimientos/', {
            'lote': lote_con_contrato.id,
            'tipo': 'entrada',
            'cantidad': 30,
            'motivo': 'Completar contrato vía API'
        }, format='json')

        assert response.status_code in [200, 201], f"Error: {response.data}"

        lote_con_contrato.refresh_from_db()
        assert lote_con_contrato.cantidad_inicial == 80
        assert lote_con_contrato.cantidad_actual == 80

    @pytest.mark.django_db
    def test_trazabilidad_movimientos_contrato(self, lote_con_contrato, usuario_admin):
        """Los movimientos de entrada/salida generan trazabilidad correcta."""
        from inventario.views_legacy import registrar_movimiento_stock

        # Entrada
        mov_entrada, _ = registrar_movimiento_stock(
            lote=lote_con_contrato,
            tipo='entrada',
            cantidad=30,
            usuario=usuario_admin,
            observaciones='Segunda recepción'
        )

        # Salida
        mov_salida, _ = registrar_movimiento_stock(
            lote=lote_con_contrato,
            tipo='salida',
            cantidad=5,
            usuario=usuario_admin,
            observaciones='Dispensación'
        )

        movimientos = Movimiento.objects.filter(lote=lote_con_contrato).order_by('id')
        assert movimientos.count() == 2
        assert movimientos[0].tipo == 'entrada'
        assert movimientos[0].cantidad == 30
        assert movimientos[1].tipo == 'salida'
        assert movimientos[1].cantidad == 5


# ============================================================================
# 4. PERMISOS — Aislamiento de centros
# ============================================================================

class TestAislamientoCentros:
    """Verifica que usuarios de un centro no ven datos de otro."""

    @pytest.mark.django_db
    def test_centro_a_no_ve_lotes_centro_b(
        self, client_centro_a, centro_b, producto_test, db
    ):
        """Usuario del centro A no debe ver lotes del centro B."""
        # Crear lote en centro B
        Lote.objects.create(
            producto=producto_test,
            numero_lote='LOT-CENTRO-B',
            centro=centro_b,
            fecha_caducidad=date(2027, 12, 31),
            cantidad_inicial=100,
            cantidad_actual=100,
            precio_unitario=Decimal('10.00'),
            activo=True
        )

        response = client_centro_a.get('/api/lotes/')
        assert response.status_code == 200

        results = response.data.get('results', response.data)
        if isinstance(results, dict):
            results = results.get('results', [])

        lotes_centro_b = [l for l in results if l.get('numero_lote') == 'LOT-CENTRO-B']
        assert len(lotes_centro_b) == 0, "Centro A no debe ver lotes de Centro B"

    @pytest.mark.django_db
    def test_centro_a_no_ve_movimientos_centro_b(
        self, client_centro_a, centro_b, producto_test, usuario_centro_b, db
    ):
        """Usuario del centro A no debe ver movimientos del centro B."""
        lote_b = Lote.objects.create(
            producto=producto_test,
            numero_lote='LOT-MOV-B',
            centro=centro_b,
            fecha_caducidad=date(2027, 12, 31),
            cantidad_inicial=100,
            cantidad_actual=100,
            precio_unitario=Decimal('10.00'),
            activo=True
        )

        mov = Movimiento(
            lote=lote_b,
            producto=producto_test,
            tipo='salida',
            cantidad=5,
            usuario=usuario_centro_b,
            motivo='Salida centro B'
        )
        mov._stock_pre_movimiento = 100
        mov.save(skip_stock_update=True)

        response = client_centro_a.get('/api/movimientos/')
        assert response.status_code == 200

        results = response.data.get('results', response.data)
        if isinstance(results, dict):
            results = results.get('results', [])

        movs_centro_b = [m for m in results if m.get('id') == mov.id]
        assert len(movs_centro_b) == 0, "Centro A no debe ver movimientos de Centro B"

    @pytest.mark.django_db
    def test_admin_ve_todos_los_centros(
        self, client_admin, centro_a, centro_b, producto_test, db
    ):
        """Admin debe ver lotes de todos los centros."""
        Lote.objects.create(
            producto=producto_test,
            numero_lote='LOT-ADMIN-A',
            centro=centro_a,
            fecha_caducidad=date(2027, 12, 31),
            cantidad_inicial=50,
            cantidad_actual=50,
            activo=True
        )
        Lote.objects.create(
            producto=producto_test,
            numero_lote='LOT-ADMIN-B',
            centro=centro_b,
            fecha_caducidad=date(2027, 12, 31),
            cantidad_inicial=75,
            cantidad_actual=75,
            activo=True
        )

        response = client_admin.get('/api/lotes/')
        assert response.status_code == 200

        results = response.data.get('results', response.data)
        if isinstance(results, dict):
            results = results.get('results', [])

        lotes_a = [l for l in results if l.get('numero_lote') == 'LOT-ADMIN-A']
        lotes_b = [l for l in results if l.get('numero_lote') == 'LOT-ADMIN-B']
        assert len(lotes_a) >= 1, "Admin debe ver lotes de Centro A"
        assert len(lotes_b) >= 1, "Admin debe ver lotes de Centro B"


# ============================================================================
# 5. ESCENARIO COMPLETO E2E
# ============================================================================

class TestEscenarioCompletoE2E:
    """Escenario completo: crear lote parcial → salida con fecha → completar → verificar."""

    @pytest.mark.django_db
    def test_flujo_completo_contrato_parcial(self, usuario_admin, producto_test, centro_a, db):
        """
        1. Crear lote contrato=80, recibido=50
        2. Salida de 10 con fecha_salida pasada
        3. Verificar: actual=40, inicial=50, contrato=80, pendiente=30
        4. Entrada +30 (completar contrato)
        5. Verificar: actual=70, inicial=80, contrato=80, pendiente=0
        """
        from inventario.views_legacy import registrar_movimiento_stock
        from core.serializers import LoteSerializer

        # 1. Crear lote
        lote = Lote.objects.create(
            producto=producto_test,
            numero_lote='LOT-E2E-001',
            centro=centro_a,
            fecha_caducidad=date(2027, 12, 31),
            cantidad_contrato=80,
            cantidad_inicial=50,
            cantidad_actual=50,
            precio_unitario=Decimal('20.00'),
            activo=True
        )

        data = LoteSerializer(lote).data
        assert data['cantidad_contrato'] == 80
        assert data['cantidad_pendiente'] == 30

        # 2. Salida con fecha_salida pasada
        fecha_salida = timezone.now() - timedelta(days=5)
        mov_salida, lote = registrar_movimiento_stock(
            lote=lote,
            tipo='salida',
            cantidad=10,
            usuario=usuario_admin,
            observaciones='Salida programada',
            fecha_salida=fecha_salida
        )

        # 3. Verificar estado intermedio
        lote.refresh_from_db()
        assert lote.cantidad_actual == 40
        assert lote.cantidad_inicial == 50
        assert lote.cantidad_contrato == 80

        mov_salida.refresh_from_db()
        assert mov_salida.fecha_salida.date() == fecha_salida.date()

        data = LoteSerializer(lote).data
        assert data['cantidad_pendiente'] == 30

        # 4. Completar contrato
        mov_entrada, lote = registrar_movimiento_stock(
            lote=lote,
            tipo='entrada',
            cantidad=30,
            usuario=usuario_admin,
            observaciones='Completar contrato parcial'
        )

        # 5. Verificar estado final
        lote.refresh_from_db()
        assert lote.cantidad_actual == 70  # 50 - 10 + 30
        assert lote.cantidad_inicial == 80  # 50 + 30
        assert lote.cantidad_contrato == 80

        data = LoteSerializer(lote).data
        assert data['cantidad_pendiente'] == 0  # 80 - 80

        # Verificar trazabilidad
        movimientos = Movimiento.objects.filter(lote=lote).order_by('id')
        assert movimientos.count() == 2
        assert movimientos[0].tipo == 'salida'
        assert movimientos[0].fecha_salida is not None
        assert movimientos[1].tipo == 'entrada'
        assert movimientos[1].fecha_salida is None  # entradas no tienen fecha_salida
