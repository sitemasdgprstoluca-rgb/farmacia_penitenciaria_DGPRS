# -*- coding: utf-8 -*-
"""
================================================================================
QA COMPLETO — FILTROS DE MOVIMIENTOS + BÚSQUEDA POR PRODUCTO/LOTE
================================================================================

Cubre:
  MOV-FILT-01  Filtrar solo requisiciones
  MOV-FILT-02  Filtrar solo salidas individuales
  MOV-FILT-03  Filtrar solo salidas masivas
  MOV-SRCH-01  Buscar por producto (nombre, clave)
  MOV-SRCH-02  Buscar por lote (numero_lote)
  MOV-SRCH-03  Combinación tipo + producto
  MOV-SRCH-04  Combinación tipo + lote
  MOV-SRCH-05  Sin resultados (UX correcta)
  MOV-SEC-01   Segregación por centro/perfil al buscar
  MOV-PERF-01  Performance / paginación sin pérdida / sin duplicados

Autor: QA Automatizado
Fecha: 2026-02-10
================================================================================
"""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.db.models import Q
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status as http_status

from core.models import Producto, Lote, Movimiento, Centro, Requisicion

User = get_user_model()


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def admin_user():
    """Admin / farmacia."""
    user = User.objects.filter(is_superuser=True, is_active=True).first()
    if user:
        return user
    user = User.objects.create_user(
        username='qa_filt_admin',
        password='TestPassword123!',
        is_superuser=True,
        is_staff=True,
        email='qa_filt_admin@test.com',
    )
    user.rol = 'admin'
    user.save()
    return user


@pytest.fixture
def centro_a():
    """Centro A."""
    c, _ = Centro.objects.get_or_create(nombre='Centro QA-FiltA', defaults={'activo': True})
    return c


@pytest.fixture
def centro_b():
    """Centro B."""
    c, _ = Centro.objects.get_or_create(nombre='Centro QA-FiltB', defaults={'activo': True})
    return c


@pytest.fixture
def user_centro_a(centro_a):
    """Usuario restringido a Centro A."""
    user = User.objects.filter(username='qa_centro_a_filt').first()
    if user:
        user.centro = centro_a
        user.save()
        return user
    user = User.objects.create_user(
        username='qa_centro_a_filt',
        password='TestPassword123!',
        is_superuser=False,
        is_staff=False,
        email='qa_centro_a_filt@test.com',
    )
    user.rol = 'administrador_centro'
    user.centro = centro_a
    user.save()
    return user


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def producto_alpha():
    """Producto Alpha — nombre y clave buscables."""
    p, _ = Producto.objects.get_or_create(
        clave='QA-ALPHA-001',
        defaults={
            'nombre': 'Paracetamol Alpha QA',
            'descripcion': 'Tabletas Paracetamol 500mg',
            'unidad_medida': 'PIEZA',
            'categoria': 'medicamento',
            'stock_minimo': 5,
            'activo': True,
        },
    )
    return p


@pytest.fixture
def producto_beta():
    """Producto Beta — diferente."""
    p, _ = Producto.objects.get_or_create(
        clave='QA-BETA-002',
        defaults={
            'nombre': 'Ibuprofeno Beta QA',
            'descripcion': 'Tabletas Ibuprofeno 400mg',
            'unidad_medida': 'PIEZA',
            'categoria': 'medicamento',
            'stock_minimo': 5,
            'activo': True,
        },
    )
    return p


def _get_or_create_lote(numero, producto, centro=None, qty=500):
    """Helper: crea lote con stock."""
    lote, created = Lote.objects.get_or_create(
        numero_lote=numero,
        producto=producto,
        centro=centro,
        defaults={
            'cantidad_inicial': qty,
            'cantidad_actual': qty,
            'fecha_caducidad': date.today() + timedelta(days=365),
            'precio_unitario': Decimal('10.00'),
            'numero_contrato': 'QA-CONT',
            'activo': True,
        },
    )
    if not created:
        lote.cantidad_actual = qty
        lote.activo = True
        lote.save(update_fields=['cantidad_actual', 'activo'])
    return lote


@pytest.fixture
def lote_alpha(producto_alpha):
    return _get_or_create_lote('QA-LOTE-ALPHA-01', producto_alpha)


@pytest.fixture
def lote_beta(producto_beta):
    return _get_or_create_lote('QA-LOTE-BETA-01', producto_beta)


@pytest.fixture
def lote_alpha_centro_a(producto_alpha, centro_a):
    """Lote de Alpha en Centro A."""
    return _get_or_create_lote('QA-LOTE-ALPHA-CA', producto_alpha, centro=centro_a, qty=200)


@pytest.fixture
def lote_beta_centro_b(producto_beta, centro_b):
    """Lote de Beta en Centro B."""
    return _get_or_create_lote('QA-LOTE-BETA-CB', producto_beta, centro=centro_b, qty=200)


@pytest.fixture
def requisicion_qa(admin_user, centro_a):
    """Requisición de referencia."""
    from django.utils import timezone
    now = timezone.now()
    req, _ = Requisicion.objects.get_or_create(
        numero='REQ-QA-FILT-001',
        defaults={
            'centro_origen': centro_a,
            'solicitante': admin_user,
            'estado': 'surtida',
            'tipo': 'normal',
            'prioridad': 'normal',
            'fecha_surtido': now,
        },
    )
    return req


# ---------- Movimientos de prueba -----------

@pytest.fixture
def movimientos_mixtos(
    admin_user, producto_alpha, producto_beta,
    lote_alpha, lote_beta,
    lote_alpha_centro_a, lote_beta_centro_b,
    centro_a, centro_b,
    requisicion_qa,
):
    """
    Crea escenario mixto con los 3 orígenes + entradas:
        - 2 mov tipo requisición  (producto_alpha, producto_beta)
        - 2 mov tipo salida masiva (producto_alpha, producto_beta)
        - 2 mov tipo salida individual (producto_alpha, producto_beta)
        - 2 mov tipo entrada (producto_alpha en centro_a, producto_beta en centro_b)
    """
    # Limpiar movimientos QA anteriores
    Movimiento.objects.filter(motivo__icontains='[QA-FILT]').delete()

    movs = {}

    # --- Requisición ---
    movs['req_alpha'] = Movimiento.objects.create(
        tipo='salida',
        producto=producto_alpha,
        lote=lote_alpha,
        cantidad=10,
        usuario=admin_user,
        motivo='SALIDA_POR_REQUISICION REQ-QA-FILT-001 [QA-FILT]',
        referencia='REQ-QA-FILT-001',
        requisicion=requisicion_qa,
        centro_destino=centro_a,
        subtipo_salida='transferencia',
    )
    movs['req_beta'] = Movimiento.objects.create(
        tipo='salida',
        producto=producto_beta,
        lote=lote_beta,
        cantidad=5,
        usuario=admin_user,
        motivo='SALIDA_POR_REQUISICION REQ-QA-FILT-001 [QA-FILT]',
        referencia='REQ-QA-FILT-001',
        requisicion=requisicion_qa,
        centro_destino=centro_a,
        subtipo_salida='transferencia',
    )

    # --- Salida masiva ---
    movs['masiva_alpha'] = Movimiento.objects.create(
        tipo='salida',
        producto=producto_alpha,
        lote=lote_alpha,
        cantidad=20,
        usuario=admin_user,
        motivo='Salida masiva a Centro A [SAL-QA-FILT-001] [QA-FILT]',
        referencia='SAL-QA-FILT-001',
        centro_destino=centro_a,
        subtipo_salida='transferencia',
    )
    movs['masiva_beta'] = Movimiento.objects.create(
        tipo='salida',
        producto=producto_beta,
        lote=lote_beta,
        cantidad=15,
        usuario=admin_user,
        motivo='Salida masiva a Centro B [SAL-QA-FILT-002] [QA-FILT]',
        referencia='SAL-QA-FILT-002',
        centro_destino=centro_b,
        subtipo_salida='transferencia',
    )

    # --- Salida individual ---
    movs['indiv_alpha'] = Movimiento.objects.create(
        tipo='salida',
        producto=producto_alpha,
        lote=lote_alpha,
        cantidad=3,
        usuario=admin_user,
        motivo='Dispensación individual receta [QA-FILT]',
        subtipo_salida='receta',
        numero_expediente='EXP-QA-001',
        centro_origen=centro_a,
    )
    movs['indiv_beta'] = Movimiento.objects.create(
        tipo='salida',
        producto=producto_beta,
        lote=lote_beta,
        cantidad=2,
        usuario=admin_user,
        motivo='Consumo interno individual [QA-FILT]',
        subtipo_salida='consumo_interno',
    )

    # --- Entradas ---
    movs['entrada_alpha'] = Movimiento.objects.create(
        tipo='entrada',
        producto=producto_alpha,
        lote=lote_alpha_centro_a,
        cantidad=50,
        usuario=admin_user,
        motivo='Entrada de stock al centro A [QA-FILT]',
        centro_destino=centro_a,
    )
    movs['entrada_beta'] = Movimiento.objects.create(
        tipo='entrada',
        producto=producto_beta,
        lote=lote_beta_centro_b,
        cantidad=30,
        usuario=admin_user,
        motivo='Entrada de stock al centro B [QA-FILT]',
        centro_destino=centro_b,
    )

    return movs


# =============================================================================
# MOV-FILT-01  Filtrar solo requisiciones
# =============================================================================
@pytest.mark.django_db
class TestMOVFILT01:
    """Filtrar por origen=requisicion devuelve SOLO movimientos de requisición."""

    def test_origen_requisicion_solo_requisiciones(self, api_client, admin_user, movimientos_mixtos):
        api_client.force_authenticate(admin_user)
        resp = api_client.get('/api/movimientos/', {'origen': 'requisicion', 'search': '[QA-FILT]'})
        assert resp.status_code == http_status.HTTP_200_OK
        results = resp.data.get('results', resp.data)
        ids = {m['id'] for m in results}

        # DEBE incluir los de requisición
        assert movimientos_mixtos['req_alpha'].id in ids
        assert movimientos_mixtos['req_beta'].id in ids

        # NO DEBE incluir masivas ni individuales
        assert movimientos_mixtos['masiva_alpha'].id not in ids
        assert movimientos_mixtos['masiva_beta'].id not in ids
        assert movimientos_mixtos['indiv_alpha'].id not in ids
        assert movimientos_mixtos['indiv_beta'].id not in ids

    def test_origen_requisicion_no_entradas(self, api_client, admin_user, movimientos_mixtos):
        """Las entradas no tienen referencia REQ- ni requisicion FK, deben excluirse."""
        api_client.force_authenticate(admin_user)
        resp = api_client.get('/api/movimientos/', {'origen': 'requisicion', 'search': '[QA-FILT]'})
        results = resp.data.get('results', resp.data)
        ids = {m['id'] for m in results}
        assert movimientos_mixtos['entrada_alpha'].id not in ids
        assert movimientos_mixtos['entrada_beta'].id not in ids


# =============================================================================
# MOV-FILT-02  Filtrar solo salidas individuales
# =============================================================================
@pytest.mark.django_db
class TestMOVFILT02:
    """Filtrar por origen=individual devuelve SOLO movimientos individuales."""

    def test_origen_individual_solo_individuales(self, api_client, admin_user, movimientos_mixtos):
        api_client.force_authenticate(admin_user)
        resp = api_client.get('/api/movimientos/', {'origen': 'individual', 'search': '[QA-FILT]'})
        assert resp.status_code == http_status.HTTP_200_OK
        results = resp.data.get('results', resp.data)
        ids = {m['id'] for m in results}

        # DEBE incluir individuales
        assert movimientos_mixtos['indiv_alpha'].id in ids
        assert movimientos_mixtos['indiv_beta'].id in ids

        # NO DEBE incluir requisiciones
        assert movimientos_mixtos['req_alpha'].id not in ids
        assert movimientos_mixtos['req_beta'].id not in ids

        # NO DEBE incluir masivas
        assert movimientos_mixtos['masiva_alpha'].id not in ids
        assert movimientos_mixtos['masiva_beta'].id not in ids

    def test_origen_individual_incluye_entradas_sin_grupo(self, api_client, admin_user, movimientos_mixtos):
        """Entradas sin referencia REQ/SAL son 'individuales'."""
        api_client.force_authenticate(admin_user)
        resp = api_client.get('/api/movimientos/', {'origen': 'individual', 'search': '[QA-FILT]'})
        results = resp.data.get('results', resp.data)
        ids = {m['id'] for m in results}
        # Entradas sin referencia deben estar en individual
        assert movimientos_mixtos['entrada_alpha'].id in ids
        assert movimientos_mixtos['entrada_beta'].id in ids


# =============================================================================
# MOV-FILT-03  Filtrar solo salidas masivas
# =============================================================================
@pytest.mark.django_db
class TestMOVFILT03:
    """Filtrar por origen=masiva devuelve SOLO movimientos de salida masiva."""

    def test_origen_masiva_solo_masivas(self, api_client, admin_user, movimientos_mixtos):
        api_client.force_authenticate(admin_user)
        resp = api_client.get('/api/movimientos/', {'origen': 'masiva', 'search': '[QA-FILT]'})
        assert resp.status_code == http_status.HTTP_200_OK
        results = resp.data.get('results', resp.data)
        ids = {m['id'] for m in results}

        assert movimientos_mixtos['masiva_alpha'].id in ids
        assert movimientos_mixtos['masiva_beta'].id in ids

        assert movimientos_mixtos['req_alpha'].id not in ids
        assert movimientos_mixtos['req_beta'].id not in ids
        assert movimientos_mixtos['indiv_alpha'].id not in ids
        assert movimientos_mixtos['indiv_beta'].id not in ids

    def test_origen_masiva_no_entradas(self, api_client, admin_user, movimientos_mixtos):
        api_client.force_authenticate(admin_user)
        resp = api_client.get('/api/movimientos/', {'origen': 'masiva', 'search': '[QA-FILT]'})
        results = resp.data.get('results', resp.data)
        ids = {m['id'] for m in results}
        assert movimientos_mixtos['entrada_alpha'].id not in ids
        assert movimientos_mixtos['entrada_beta'].id not in ids


# =============================================================================
# MOV-FILT-04  Suma de orígenes = total
# =============================================================================
@pytest.mark.django_db
class TestMOVFILT04:
    """La unión de los tres filtros de origen cubre todos los movimientos (sin pérdida ni duplicados)."""

    def test_union_origenes_es_total(self, api_client, admin_user, movimientos_mixtos):
        api_client.force_authenticate(admin_user)

        # Total sin filtro de origen
        resp_all = api_client.get('/api/movimientos/', {'search': '[QA-FILT]', 'page_size': 100})
        all_ids = {m['id'] for m in resp_all.data.get('results', resp_all.data)}

        ids_union = set()
        for origen in ('requisicion', 'masiva', 'individual'):
            resp = api_client.get('/api/movimientos/', {'origen': origen, 'search': '[QA-FILT]', 'page_size': 100})
            for m in resp.data.get('results', resp.data):
                ids_union.add(m['id'])

        assert ids_union == all_ids, \
            f"La unión de los 3 orígenes ({len(ids_union)}) no coincide con el total ({len(all_ids)})"

    def test_origenes_mutuamente_excluyentes(self, api_client, admin_user, movimientos_mixtos):
        """Ningún movimiento de QA-FILT debe aparecer en dos orígenes."""
        api_client.force_authenticate(admin_user)

        sets = {}
        for origen in ('requisicion', 'masiva', 'individual'):
            resp = api_client.get('/api/movimientos/', {'origen': origen, 'search': '[QA-FILT]', 'page_size': 100})
            sets[origen] = {m['id'] for m in resp.data.get('results', resp.data)}

        assert sets['requisicion'] & sets['masiva'] == set(), "Requisiciones y masivas se solapan"
        assert sets['requisicion'] & sets['individual'] == set(), "Requisiciones e individuales se solapan"
        assert sets['masiva'] & sets['individual'] == set(), "Masivas e individuales se solapan"


# =============================================================================
# MOV-SRCH-01  Búsqueda por producto
# =============================================================================
@pytest.mark.django_db
class TestMOVSRCH01:
    """Buscar por nombre de producto, clave o descripción."""

    def test_buscar_por_nombre_producto(self, api_client, admin_user, movimientos_mixtos):
        api_client.force_authenticate(admin_user)
        resp = api_client.get('/api/movimientos/', {'search': 'Paracetamol Alpha QA'})
        assert resp.status_code == http_status.HTTP_200_OK
        results = resp.data.get('results', resp.data)
        assert len(results) >= 1
        # Solo movimientos de producto_alpha
        for m in results:
            lote_data = m.get('lote_info') or m.get('lote_detalle') or {}
            prod = lote_data.get('producto_nombre', '') or ''
            clave = lote_data.get('producto_clave', '') or ''
            # El movimiento debe estar relacionado con Alpha
            assert m['id'] in {
                movimientos_mixtos['req_alpha'].id,
                movimientos_mixtos['masiva_alpha'].id,
                movimientos_mixtos['indiv_alpha'].id,
                movimientos_mixtos['entrada_alpha'].id,
            } or 'Paracetamol' in prod or 'ALPHA' in clave.upper()

    def test_buscar_por_clave_producto(self, api_client, admin_user, movimientos_mixtos):
        api_client.force_authenticate(admin_user)
        resp = api_client.get('/api/movimientos/', {'search': 'QA-ALPHA-001'})
        results = resp.data.get('results', resp.data)
        ids = {m['id'] for m in results}
        # Todos los movimientos de Alpha deben aparecer
        assert movimientos_mixtos['req_alpha'].id in ids
        assert movimientos_mixtos['masiva_alpha'].id in ids
        assert movimientos_mixtos['indiv_alpha'].id in ids
        assert movimientos_mixtos['entrada_alpha'].id in ids
        # Ningún movimiento de Beta
        assert movimientos_mixtos['req_beta'].id not in ids
        assert movimientos_mixtos['masiva_beta'].id not in ids

    def test_buscar_por_descripcion_producto(self, api_client, admin_user, movimientos_mixtos):
        api_client.force_authenticate(admin_user)
        resp = api_client.get('/api/movimientos/', {'search': 'Tabletas Paracetamol 500mg'})
        results = resp.data.get('results', resp.data)
        ids = {m['id'] for m in results}
        assert movimientos_mixtos['req_alpha'].id in ids

    def test_filtro_producto_por_id(self, api_client, admin_user, movimientos_mixtos, producto_alpha):
        """Filtrar con el select de producto (envía ID del producto)."""
        api_client.force_authenticate(admin_user)
        resp = api_client.get('/api/movimientos/', {'producto': producto_alpha.id, 'search': '[QA-FILT]'})
        results = resp.data.get('results', resp.data)
        ids = {m['id'] for m in results}
        assert movimientos_mixtos['req_alpha'].id in ids
        assert movimientos_mixtos['masiva_alpha'].id in ids
        assert movimientos_mixtos['indiv_alpha'].id in ids
        assert movimientos_mixtos['entrada_alpha'].id in ids
        # Beta no
        assert movimientos_mixtos['req_beta'].id not in ids


# =============================================================================
# MOV-SRCH-02  Búsqueda por lote
# =============================================================================
@pytest.mark.django_db
class TestMOVSRCH02:
    """Buscar por lote (ID o número de lote)."""

    def test_buscar_por_numero_lote_texto(self, api_client, admin_user, movimientos_mixtos):
        api_client.force_authenticate(admin_user)
        resp = api_client.get('/api/movimientos/', {'search': 'QA-LOTE-ALPHA-01'})
        results = resp.data.get('results', resp.data)
        ids = {m['id'] for m in results}
        # Los 3 movimientos de Alpha que usan ese lote
        assert movimientos_mixtos['req_alpha'].id in ids
        assert movimientos_mixtos['masiva_alpha'].id in ids
        assert movimientos_mixtos['indiv_alpha'].id in ids

    def test_filtrar_por_lote_id(self, api_client, admin_user, movimientos_mixtos, lote_alpha):
        """Filtrar con el select de lote (envía ID numérico)."""
        api_client.force_authenticate(admin_user)
        resp = api_client.get('/api/movimientos/', {'lote': str(lote_alpha.id)})
        results = resp.data.get('results', resp.data)
        ids = {m['id'] for m in results}
        assert movimientos_mixtos['req_alpha'].id in ids
        assert movimientos_mixtos['masiva_alpha'].id in ids
        assert movimientos_mixtos['indiv_alpha'].id in ids
        # Movimientos con lote_alpha_centro_a (diferente lote) no
        assert movimientos_mixtos['entrada_alpha'].id not in ids

    def test_detalle_muestra_lote(self, api_client, admin_user, movimientos_mixtos, lote_alpha):
        """El detalle de un movimiento incluye la relación con el lote."""
        api_client.force_authenticate(admin_user)
        mov_id = movimientos_mixtos['req_alpha'].id
        resp = api_client.get(f'/api/movimientos/{mov_id}/')
        assert resp.status_code == http_status.HTTP_200_OK
        data = resp.data
        # Debe tener lote_info o lote_id
        assert data.get('lote') == lote_alpha.id or data.get('lote_info', {}).get('id') == lote_alpha.id


# =============================================================================
# MOV-SRCH-03  Combinación tipo/origen + producto
# =============================================================================
@pytest.mark.django_db
class TestMOVSRCH03:
    """Combinar filtro de origen con búsqueda por producto."""

    def test_masiva_mas_producto_alpha(self, api_client, admin_user, movimientos_mixtos, producto_alpha):
        """origen=masiva + producto=Alpha → solo masiva_alpha."""
        api_client.force_authenticate(admin_user)
        resp = api_client.get('/api/movimientos/', {
            'origen': 'masiva',
            'producto': producto_alpha.id,
            'search': '[QA-FILT]',
        })
        results = resp.data.get('results', resp.data)
        ids = {m['id'] for m in results}
        assert movimientos_mixtos['masiva_alpha'].id in ids
        # masiva_beta no porque es producto_beta
        assert movimientos_mixtos['masiva_beta'].id not in ids
        # requisiciones/individuales tampoco
        assert movimientos_mixtos['req_alpha'].id not in ids
        assert movimientos_mixtos['indiv_alpha'].id not in ids

    def test_requisicion_mas_producto_beta(self, api_client, admin_user, movimientos_mixtos, producto_beta):
        """origen=requisicion + producto=Beta → solo req_beta."""
        api_client.force_authenticate(admin_user)
        resp = api_client.get('/api/movimientos/', {
            'origen': 'requisicion',
            'producto': producto_beta.id,
            'search': '[QA-FILT]',
        })
        results = resp.data.get('results', resp.data)
        ids = {m['id'] for m in results}
        assert movimientos_mixtos['req_beta'].id in ids
        assert movimientos_mixtos['req_alpha'].id not in ids
        assert movimientos_mixtos['masiva_beta'].id not in ids


# =============================================================================
# MOV-SRCH-04  Combinación tipo/origen + lote
# =============================================================================
@pytest.mark.django_db
class TestMOVSRCH04:
    """Combinar filtro de origen con filtro por lote."""

    def test_individual_mas_lote_alpha(self, api_client, admin_user, movimientos_mixtos, lote_alpha):
        """origen=individual + lote=lote_alpha → solo indiv_alpha."""
        api_client.force_authenticate(admin_user)
        resp = api_client.get('/api/movimientos/', {
            'origen': 'individual',
            'lote': str(lote_alpha.id),
        })
        results = resp.data.get('results', resp.data)
        ids = {m['id'] for m in results}
        assert movimientos_mixtos['indiv_alpha'].id in ids
        # requisiciones y masivas usan el mismo lote pero tienen diferente origen
        assert movimientos_mixtos['req_alpha'].id not in ids
        assert movimientos_mixtos['masiva_alpha'].id not in ids


# =============================================================================
# MOV-SRCH-05  Sin resultados (UX correcta)
# =============================================================================
@pytest.mark.django_db
class TestMOVSRCH05:
    """Buscar con criterios sin coincidencias debe devolver lista vacía, no error."""

    def test_lote_inexistente(self, api_client, admin_user):
        api_client.force_authenticate(admin_user)
        resp = api_client.get('/api/movimientos/', {'search': 'LOTE-INEXISTENTE-L999-XYZ'})
        assert resp.status_code == http_status.HTTP_200_OK
        results = resp.data.get('results', resp.data)
        assert len(results) == 0

    def test_producto_inexistente(self, api_client, admin_user):
        api_client.force_authenticate(admin_user)
        resp = api_client.get('/api/movimientos/', {'search': 'ProductoQueNoExisteNunca'})
        assert resp.status_code == http_status.HTTP_200_OK
        results = resp.data.get('results', resp.data)
        assert len(results) == 0

    def test_combinacion_imposible(self, api_client, admin_user, movimientos_mixtos, producto_alpha):
        """origen=masiva + producto_alpha con lote de beta → 0 resultados."""
        api_client.force_authenticate(admin_user)
        resp = api_client.get('/api/movimientos/', {
            'origen': 'masiva',
            'producto': producto_alpha.id,
            'search': 'QA-LOTE-BETA',  # Lote de beta, producto alpha
        })
        assert resp.status_code == http_status.HTTP_200_OK
        results = resp.data.get('results', resp.data)
        assert len(results) == 0


# =============================================================================
# MOV-SEC-01  Segregación por centro/perfil al buscar
# =============================================================================
@pytest.mark.django_db
class TestMOVSEC01:
    """Usuarios de un centro NO ven movimientos de otro centro."""

    def test_user_centro_a_no_ve_centro_b(
        self, api_client, user_centro_a,
        movimientos_mixtos, lote_beta_centro_b,
    ):
        """User Centro A busca lote que pertenece a Centro B → no ve resultados de B."""
        api_client.force_authenticate(user_centro_a)
        resp = api_client.get('/api/movimientos/', {'search': 'QA-LOTE-BETA-CB'})
        assert resp.status_code == http_status.HTTP_200_OK
        results = resp.data.get('results', resp.data)
        ids = {m['id'] for m in results}
        # Entrada de Beta en Centro B no debe ser visible
        assert movimientos_mixtos['entrada_beta'].id not in ids

    def test_user_centro_a_ve_sus_movimientos(
        self, api_client, user_centro_a, movimientos_mixtos,
    ):
        """User Centro A puede ver movimientos de su centro."""
        api_client.force_authenticate(user_centro_a)
        resp = api_client.get('/api/movimientos/', {'search': '[QA-FILT]'})
        assert resp.status_code == http_status.HTTP_200_OK
        results = resp.data.get('results', resp.data)
        ids = {m['id'] for m in results}
        # La entrada de Alpha en Centro A sí debe ser visible
        assert movimientos_mixtos['entrada_alpha'].id in ids

    def test_admin_ve_todos_los_centros(self, api_client, admin_user, movimientos_mixtos):
        """Admin ve movimientos de todos los centros."""
        api_client.force_authenticate(admin_user)
        resp = api_client.get('/api/movimientos/', {'search': '[QA-FILT]', 'page_size': 100})
        results = resp.data.get('results', resp.data)
        ids = {m['id'] for m in results}
        assert movimientos_mixtos['entrada_alpha'].id in ids
        assert movimientos_mixtos['entrada_beta'].id in ids

    def test_filtro_centro_limita_resultados(self, api_client, admin_user, movimientos_mixtos, centro_a):
        """Admin filtrando por centro_a no ve movimientos de centro_b."""
        api_client.force_authenticate(admin_user)
        resp = api_client.get('/api/movimientos/', {
            'centro': centro_a.id,
            'search': '[QA-FILT]',
            'page_size': 100,
        })
        results = resp.data.get('results', resp.data)
        ids = {m['id'] for m in results}
        # Entrada de Beta en Centro B no
        assert movimientos_mixtos['entrada_beta'].id not in ids

    def test_user_sin_auth_rechazado(self, api_client):
        """Sin autenticar, se niega acceso."""
        resp = api_client.get('/api/movimientos/')
        assert resp.status_code in (
            http_status.HTTP_401_UNAUTHORIZED,
            http_status.HTTP_403_FORBIDDEN,
        )


# =============================================================================
# MOV-PERF-01  Performance, paginación y no duplicados
# =============================================================================
@pytest.mark.django_db
class TestMOVPERF01:
    """Volumen, paginación sin pérdida, y sin duplicados."""

    def test_sin_duplicados_con_filtro_origen(self, api_client, admin_user, movimientos_mixtos):
        """Aplicar filtro de origen no genera duplicados (distinct)."""
        api_client.force_authenticate(admin_user)
        for origen in ('requisicion', 'masiva', 'individual'):
            resp = api_client.get('/api/movimientos/', {
                'origen': origen,
                'search': '[QA-FILT]',
                'page_size': 100,
            })
            results = resp.data.get('results', resp.data)
            ids = [m['id'] for m in results]
            assert len(ids) == len(set(ids)), f"Duplicados detectados en origen={origen}: {ids}"

    def test_sin_duplicados_con_search_y_origen(self, api_client, admin_user, movimientos_mixtos):
        """Combinar search + origen no genera duplicados (Q-OR + Q-OR + JOINs)."""
        api_client.force_authenticate(admin_user)
        resp = api_client.get('/api/movimientos/', {
            'origen': 'requisicion',
            'search': 'Paracetamol',
            'page_size': 100,
        })
        results = resp.data.get('results', resp.data)
        ids = [m['id'] for m in results]
        assert len(ids) == len(set(ids)), f"Duplicados: {ids}"

    def test_paginacion_no_pierde_registros(self, api_client, admin_user, movimientos_mixtos):
        """Paginar de 2 en 2 recolecta todos los IDs sin pérdida."""
        api_client.force_authenticate(admin_user)

        # Obtener total
        resp_total = api_client.get('/api/movimientos/', {'search': '[QA-FILT]', 'page_size': 100})
        all_ids = {m['id'] for m in resp_total.data.get('results', resp_total.data)}
        total = len(all_ids)

        if total <= 2:
            return  # Con pocos movimientos no se puede probar paginación

        # Paginar de 2 en 2
        collected_ids = set()
        page = 1
        while True:
            resp = api_client.get('/api/movimientos/', {
                'search': '[QA-FILT]',
                'page_size': 2,
                'page': page,
            })
            results = resp.data.get('results', resp.data)
            if not results:
                break
            for m in results:
                collected_ids.add(m['id'])
            if not resp.data.get('next'):
                break
            page += 1

        assert collected_ids == all_ids, \
            f"Paginación perdió registros: esperados={len(all_ids)}, obtenidos={len(collected_ids)}"

    def test_volumen_alto_no_falla(self, api_client, admin_user, producto_alpha, lote_alpha):
        """Crear 50 movimientos y verificar que filtros funcionan sin error."""
        api_client.force_authenticate(admin_user)

        # Crear 50 movimientos individuales
        bulk = []
        for i in range(50):
            bulk.append(Movimiento(
                tipo='salida',
                producto=producto_alpha,
                lote=lote_alpha,
                cantidad=1,
                usuario=admin_user,
                motivo=f'Volumen test {i} [QA-PERF]',
                subtipo_salida='consumo_interno',
            ))
        Movimiento.objects.bulk_create(bulk)

        # Filtrar
        resp = api_client.get('/api/movimientos/', {
            'origen': 'individual',
            'search': '[QA-PERF]',
            'page_size': 100,
        })
        assert resp.status_code == http_status.HTTP_200_OK
        results = resp.data.get('results', resp.data)
        assert len(results) == 50

        # Limpiar
        Movimiento.objects.filter(motivo__icontains='[QA-PERF]').delete()


# =============================================================================
# MOV-COMBO  Filtros adicionales de cobertura
# =============================================================================
@pytest.mark.django_db
class TestMOVCombo:
    """Validaciones adicionales de combinación de filtros."""

    def test_tipo_salida_mas_origen(self, api_client, admin_user, movimientos_mixtos):
        """tipo=salida + origen=masiva → solo salidas masivas."""
        api_client.force_authenticate(admin_user)
        resp = api_client.get('/api/movimientos/', {
            'tipo': 'salida',
            'origen': 'masiva',
            'search': '[QA-FILT]',
            'page_size': 100,
        })
        results = resp.data.get('results', resp.data)
        ids = {m['id'] for m in results}
        assert movimientos_mixtos['masiva_alpha'].id in ids
        assert movimientos_mixtos['masiva_beta'].id in ids
        # Entradas nunca aparecen con tipo=salida
        assert movimientos_mixtos['entrada_alpha'].id not in ids

    def test_tipo_entrada_ignora_origen(self, api_client, admin_user, movimientos_mixtos):
        """tipo=entrada + origen=masiva → probablemente vacío (las entradas no son masivas)."""
        api_client.force_authenticate(admin_user)
        resp = api_client.get('/api/movimientos/', {
            'tipo': 'entrada',
            'origen': 'masiva',
            'search': '[QA-FILT]',
            'page_size': 100,
        })
        results = resp.data.get('results', resp.data)
        # No hay entradas con referencia SAL-
        assert len(results) == 0

    def test_subtipo_salida_receta_con_origen_individual(self, api_client, admin_user, movimientos_mixtos):
        """subtipo_salida=receta + origen=individual → solo indiv_alpha (receta)."""
        api_client.force_authenticate(admin_user)
        resp = api_client.get('/api/movimientos/', {
            'subtipo_salida': 'receta',
            'origen': 'individual',
            'search': '[QA-FILT]',
            'page_size': 100,
        })
        results = resp.data.get('results', resp.data)
        ids = {m['id'] for m in results}
        assert movimientos_mixtos['indiv_alpha'].id in ids
        # consumo_interno no coincide con subtipo=receta
        assert movimientos_mixtos['indiv_beta'].id not in ids

    def test_origen_vacio_devuelve_todo(self, api_client, admin_user, movimientos_mixtos):
        """origen='' (vacío) → sin filtro, devuelve todo el QA-FILT."""
        api_client.force_authenticate(admin_user)
        resp = api_client.get('/api/movimientos/', {
            'origen': '',
            'search': '[QA-FILT]',
            'page_size': 100,
        })
        results = resp.data.get('results', resp.data)
        assert len(results) == 8  # 2 req + 2 masiva + 2 indiv + 2 entrada

    def test_agrupados_endpoint_soporta_origen(self, api_client, admin_user, movimientos_mixtos):
        """El endpoint agrupados también usa get_queryset → origen debe funcionar."""
        api_client.force_authenticate(admin_user)
        resp = api_client.get('/api/movimientos/agrupados/', {
            'origen': 'requisicion',
            'search': '[QA-FILT]',
        })
        assert resp.status_code == http_status.HTTP_200_OK
        # No debería tener grupos de tipo salida_masiva
        data = resp.data
        grupos = data.get('grupos', [])
        sin_grupo = data.get('sin_grupo', [])
        # Verificar que los movimientos devueltos son solo de requisición
        all_items = []
        for g in grupos:
            all_items.extend(g.get('items', []))
        all_items.extend(sin_grupo)
        for item in all_items:
            ref = item.get('referencia', '') or ''
            motivo = item.get('observaciones', '') or item.get('motivo', '') or ''
            # Si tiene referencia, debe ser REQ-
            if ref:
                assert ref.startswith('REQ-') or 'REQUISICION' in motivo.upper(), \
                    f"Item no-requisición en filtro origen=requisicion: ref={ref}, motivo={motivo}"
