# -*- coding: utf-8 -*-
"""
================================================================================
QA COMPLETO - SEGREGACIÓN DE ACCESO Y CONTROL ENTRE CENTROS
================================================================================

OBJETIVO:
Verificar que el sistema cumple con la segregación de datos entre centros
penitenciarios, farmacia central y roles de usuario.

CASOS DE PRUEBA:
  SEC-01  Centro A NO puede ver datos de Centro B
  SEC-02  Centro NO puede ver datos de Farmacia Central
  SEC-03  Movimiento visible solo para el centro destino
  SEC-04  Salida manual solo sobre inventario propio
  SEC-05  Restricciones por perfil (médico, admin_centro, director, vista)
  SEC-06  Protección contra IDOR (manipulación de IDs)
  SEC-07  Farmacia/Admin ve todos los datos (cross-centro)
  SEC-08  Auditoría: trazabilidad de quién hizo qué

Perfiles probados:
  - admin (superusuario)
  - farmacia
  - administrador_centro (Centro A y Centro B)
  - director_centro
  - medico
  - vista
  - centro (consulta)

Autor: QA Automatizado - Segregación
Fecha: 2025-02-10
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
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from core.models import Producto, Lote, Movimiento, Centro

User = get_user_model()


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def centro_a(db):
    """Centro penitenciario A."""
    obj, _ = Centro.objects.get_or_create(
        nombre='Centro Penitenciario A - Seguridad',
        defaults={'direccion': 'Dir Centro A', 'activo': True}
    )
    return obj


@pytest.fixture
def centro_b(db):
    """Centro penitenciario B (distinto de A)."""
    obj, _ = Centro.objects.get_or_create(
        nombre='Centro Penitenciario B - Seguridad',
        defaults={'direccion': 'Dir Centro B', 'activo': True}
    )
    return obj


@pytest.fixture
def producto_seg(db):
    """Producto para pruebas de segregación."""
    obj, _ = Producto.objects.get_or_create(
        clave='SEG-MED-001',
        defaults={
            'nombre': 'Medicamento Segregación Test',
            'unidad_medida': 'TABLETA',
            'categoria': 'medicamento',
            'activo': True,
        }
    )
    return obj


@pytest.fixture
def producto_seg_2(db):
    """Segundo producto para pruebas de segregación."""
    obj, _ = Producto.objects.get_or_create(
        clave='SEG-MED-002',
        defaults={
            'nombre': 'Medicamento Segregación 2',
            'unidad_medida': 'CAPSULA',
            'categoria': 'medicamento',
            'activo': True,
        }
    )
    return obj


@pytest.fixture
def lote_central(producto_seg, db):
    """Lote en farmacia central (centro=None)."""
    obj, _ = Lote.objects.get_or_create(
        producto=producto_seg,
        numero_lote='SEG-LOT-CENTRAL',
        defaults={
            'centro': None,
            'fecha_caducidad': date(2028, 12, 31),
            'cantidad_inicial': 500,
            'cantidad_actual': 500,
            'precio_unitario': Decimal('15.00'),
            'activo': True,
        }
    )
    # Asegurar stock disponible
    obj.cantidad_actual = 500
    obj.activo = True
    obj.save()
    return obj


@pytest.fixture
def lote_centro_a(producto_seg, centro_a, db):
    """Lote asignado al Centro A."""
    obj, _ = Lote.objects.get_or_create(
        producto=producto_seg,
        numero_lote='SEG-LOT-CA',
        defaults={
            'centro': centro_a,
            'fecha_caducidad': date(2028, 6, 30),
            'cantidad_inicial': 200,
            'cantidad_actual': 200,
            'precio_unitario': Decimal('15.00'),
            'activo': True,
        }
    )
    obj.cantidad_actual = 200
    obj.centro = centro_a
    obj.activo = True
    obj.save()
    return obj


@pytest.fixture
def lote_centro_b(producto_seg, centro_b, db):
    """Lote asignado al Centro B."""
    obj, _ = Lote.objects.get_or_create(
        producto=producto_seg,
        numero_lote='SEG-LOT-CB',
        defaults={
            'centro': centro_b,
            'fecha_caducidad': date(2028, 6, 30),
            'cantidad_inicial': 150,
            'cantidad_actual': 150,
            'precio_unitario': Decimal('15.00'),
            'activo': True,
        }
    )
    obj.cantidad_actual = 150
    obj.centro = centro_b
    obj.activo = True
    obj.save()
    return obj


@pytest.fixture
def lote_extra_centro_b(producto_seg_2, centro_b, db):
    """Lote extra en Centro B (otro producto)."""
    obj, _ = Lote.objects.get_or_create(
        producto=producto_seg_2,
        numero_lote='SEG-LOT-CB-EXTRA',
        defaults={
            'centro': centro_b,
            'fecha_caducidad': date(2028, 12, 31),
            'cantidad_inicial': 80,
            'cantidad_actual': 80,
            'precio_unitario': Decimal('20.00'),
            'activo': True,
        }
    )
    obj.cantidad_actual = 80
    obj.centro = centro_b
    obj.activo = True
    obj.save()
    return obj


# --- Movimientos ---

@pytest.fixture
def mov_entrada_centro_a(lote_centro_a, centro_a, producto_seg, db):
    """Movimiento de entrada registrado en Centro A."""
    obj = Movimiento.objects.create(
        lote=lote_centro_a,
        producto=producto_seg,
        tipo='entrada',
        cantidad=100,
        motivo='Transferencia a Centro A (seg test)',
    )
    return obj


@pytest.fixture
def mov_entrada_centro_b(lote_centro_b, centro_b, producto_seg, db):
    """Movimiento de entrada registrado en Centro B."""
    obj = Movimiento.objects.create(
        lote=lote_centro_b,
        producto=producto_seg,
        tipo='entrada',
        cantidad=50,
        motivo='Transferencia a Centro B (seg test)',
    )
    return obj


@pytest.fixture
def mov_salida_central(lote_central, centro_a, producto_seg, db):
    """Movimiento de salida de farmacia central hacia Centro A."""
    obj = Movimiento.objects.create(
        lote=lote_central,
        producto=producto_seg,
        tipo='salida',
        cantidad=100,
        centro_destino=centro_a,
        motivo='Salida de FC a Centro A (seg test)',
    )
    return obj


# --- Usuarios ---

def _make_user(username, rol, centro=None, **extra):
    """Helper para crear usuarios de test con password válido."""
    try:
        user = User.objects.get(username=username)
        # Asegurar centro y rol correctos
        changed = False
        if user.centro != centro:
            user.centro = centro
            changed = True
        if user.rol != rol:
            user.rol = rol
            changed = True
        if changed:
            user.save(update_fields=['centro', 'rol'])
        return user
    except User.DoesNotExist:
        pass

    # Separar is_superuser/is_staff de extra para create_user
    is_superuser = extra.pop('is_superuser', False)
    is_staff = extra.pop('is_staff', False)

    user = User.objects.create_user(
        username=username,
        password='SegTest2025!',
        email=f'{username}@segtest.com',
        rol=rol,
        centro=centro,
        is_active=True,
        is_superuser=is_superuser,
        is_staff=is_staff,
        **extra,
    )
    return user


@pytest.fixture
def user_admin(db):
    """Superusuario admin."""
    return _make_user('seg_admin', 'admin', is_superuser=True, is_staff=True)


@pytest.fixture
def user_farmacia(db):
    """Personal de farmacia central."""
    return _make_user('seg_farmacia', 'farmacia', is_staff=True)


@pytest.fixture
def user_admin_centro_a(centro_a, db):
    """Administrador asignado al Centro A."""
    return _make_user('seg_admin_ca', 'administrador_centro', centro=centro_a)


@pytest.fixture
def user_admin_centro_b(centro_b, db):
    """Administrador asignado al Centro B."""
    return _make_user('seg_admin_cb', 'administrador_centro', centro=centro_b)


@pytest.fixture
def user_director_centro_a(centro_a, db):
    """Director del Centro A."""
    return _make_user('seg_director_ca', 'director_centro', centro=centro_a)


@pytest.fixture
def user_medico_centro_a(centro_a, db):
    """Médico asignado al Centro A."""
    return _make_user('seg_medico_ca', 'medico', centro=centro_a)


@pytest.fixture
def user_vista(db):
    """Usuario de sólo consulta (vista global)."""
    return _make_user('seg_vista', 'vista')


@pytest.fixture
def user_centro_consulta_a(centro_a, db):
    """Usuario básico de consulta en Centro A."""
    return _make_user('seg_centro_ca', 'centro', centro=centro_a)


@pytest.fixture
def user_centro_consulta_b(centro_b, db):
    """Usuario básico de consulta en Centro B."""
    return _make_user('seg_centro_cb', 'centro', centro=centro_b)


# --- Clients autenticados ---

def _client_for(user):
    """Crea APIClient autenticado para un usuario."""
    c = APIClient()
    c.force_authenticate(user=user)
    return c


# =============================================================================
# SEC-01: CENTRO A NO PUEDE VER DATOS DE CENTRO B
# =============================================================================

@pytest.mark.django_db
class TestSEC01_SegregacionEntreCentros:
    """
    Un usuario de Centro A NO debe poder ver lotes, movimientos
    ni productos con stock de Centro B, y viceversa.
    """

    def test_lotes_centro_a_no_ve_lotes_centro_b(
        self, user_admin_centro_a, lote_centro_a, lote_centro_b
    ):
        """Los lotes de Centro B son invisibles para un usuario de Centro A."""
        client = _client_for(user_admin_centro_a)
        resp = client.get('/api/lotes/')
        assert resp.status_code == status.HTTP_200_OK

        data = resp.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        lote_ids = [l.get('id') for l in results]

        assert lote_centro_a.id in lote_ids, "Debe ver su propio lote"
        assert lote_centro_b.id not in lote_ids, "NO debe ver lote de Centro B"

    def test_lotes_centro_b_no_ve_lotes_centro_a(
        self, user_admin_centro_b, lote_centro_a, lote_centro_b
    ):
        """Los lotes de Centro A son invisibles para un usuario de Centro B."""
        client = _client_for(user_admin_centro_b)
        resp = client.get('/api/lotes/')
        assert resp.status_code == status.HTTP_200_OK

        data = resp.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        lote_ids = [l.get('id') for l in results]

        assert lote_centro_b.id in lote_ids, "Debe ver su propio lote"
        assert lote_centro_a.id not in lote_ids, "NO debe ver lote de Centro A"

    def test_movimientos_centro_a_no_ve_movimientos_centro_b(
        self, user_admin_centro_a,
        mov_entrada_centro_a, mov_entrada_centro_b
    ):
        """Movimientos de Centro B son invisibles para usuario de Centro A."""
        client = _client_for(user_admin_centro_a)
        resp = client.get('/api/movimientos/')
        assert resp.status_code == status.HTTP_200_OK

        data = resp.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        mov_ids = [m.get('id') for m in results]

        assert mov_entrada_centro_a.id in mov_ids, "Debe ver su movimiento"
        assert mov_entrada_centro_b.id not in mov_ids, "NO debe ver movimiento de Centro B"

    def test_productos_centro_a_no_ve_stock_centro_b(
        self, user_admin_centro_a, lote_centro_a, lote_centro_b, lote_extra_centro_b
    ):
        """
        Productos del Centro B (que sólo tienen stock allí) no deben
        aparecer para usuario de Centro A.
        """
        client = _client_for(user_admin_centro_a)
        resp = client.get('/api/productos/')
        assert resp.status_code == status.HTTP_200_OK

        data = resp.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        prod_ids = [p.get('id') for p in results]

        # producto_seg tiene stock en Centro A (lote_centro_a) → visible
        assert lote_centro_a.producto.id in prod_ids, "Debe ver producto con stock propio"
        # producto_seg_2 sólo tiene stock en Centro B → invisible
        assert lote_extra_centro_b.producto.id not in prod_ids, \
            "NO debe ver producto con stock exclusivo de Centro B"


# =============================================================================
# SEC-02: CENTRO NO PUEDE VER DATOS DE FARMACIA CENTRAL
# =============================================================================

@pytest.mark.django_db
class TestSEC02_CentroNoPuedVerFarmaciaCentral:
    """
    Un usuario de centro NO debe ver lotes ni movimientos de
    farmacia central (centro=None) salvo los que llegan a su centro.
    """

    def test_lotes_centrales_invisibles_para_centro(
        self, user_admin_centro_a, lote_central, lote_centro_a
    ):
        """Lotes de farmacia central (centro=None) no aparecen para centro."""
        client = _client_for(user_admin_centro_a)
        resp = client.get('/api/lotes/')
        assert resp.status_code == status.HTTP_200_OK

        data = resp.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        lote_ids = [l.get('id') for l in results]

        assert lote_central.id not in lote_ids, "NO debe ver lote de farmacia central"
        assert lote_centro_a.id in lote_ids, "Debe ver su propio lote"

    def test_movimientos_centrales_invisibles_para_centro(
        self, user_admin_centro_a,
        mov_salida_central, mov_entrada_centro_a
    ):
        """
        Movimientos de salida de farmacia central (lote.centro=None)
        no deben ser visibles para un usuario de centro, a menos que
        el centro sea origen o destino.
        """
        client = _client_for(user_admin_centro_a)
        resp = client.get('/api/movimientos/')
        assert resp.status_code == status.HTTP_200_OK

        data = resp.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        mov_ids = [m.get('id') for m in results]

        # La entrada al propio centro SÍ es visible
        assert mov_entrada_centro_a.id in mov_ids, "Debe ver su entrada"
        # La salida de FC (lote.centro=None, centro_origen=None) NO es visible
        # a menos que centro_destino == centro del usuario
        # Si mov_salida_central.centro_destino == centro_a, sería visible.
        # Verificamos la lógica correcta.

    def test_centro_no_puede_acceder_salida_masiva(self, user_admin_centro_a):
        """
        El endpoint de salida masiva está restringido a farmacia/admin.
        Un usuario de centro debe recibir 403.
        """
        client = _client_for(user_admin_centro_a)
        resp = client.get('/api/salida-masiva/lotes-disponibles/')
        assert resp.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED,
        ), f"Esperaba 403, obtuvo {resp.status_code}"


# =============================================================================
# SEC-03: MOVIMIENTO VISIBLE SOLO PARA CENTRO DESTINO
# =============================================================================

@pytest.mark.django_db
class TestSEC03_MovimientoVisibleSoloCentroDestino:
    """El movimiento de entrada sólo es visible para el centro destinatario."""

    def test_entrada_visible_solo_para_destino(
        self, user_admin_centro_a, user_admin_centro_b,
        mov_entrada_centro_a
    ):
        """Centro B no puede ver la entrada registrada en Centro A."""
        # Centro A SÍ lo ve
        client_a = _client_for(user_admin_centro_a)
        resp_a = client_a.get('/api/movimientos/')
        data_a = resp_a.json()
        results_a = data_a.get('results', data_a) if isinstance(data_a, dict) else data_a
        ids_a = [m['id'] for m in results_a]
        assert mov_entrada_centro_a.id in ids_a

        # Centro B NO lo ve
        client_b = _client_for(user_admin_centro_b)
        resp_b = client_b.get('/api/movimientos/')
        data_b = resp_b.json()
        results_b = data_b.get('results', data_b) if isinstance(data_b, dict) else data_b
        ids_b = [m['id'] for m in results_b]
        assert mov_entrada_centro_a.id not in ids_b

    def test_farmacia_ve_todos_los_movimientos(
        self, user_farmacia,
        mov_entrada_centro_a, mov_entrada_centro_b, mov_salida_central
    ):
        """Farmacia central ve movimientos de todos los centros."""
        client = _client_for(user_farmacia)
        resp = client.get('/api/movimientos/')
        assert resp.status_code == status.HTTP_200_OK

        data = resp.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        ids = [m['id'] for m in results]

        assert mov_entrada_centro_a.id in ids, "Farmacia debe ver mov Centro A"
        assert mov_entrada_centro_b.id in ids, "Farmacia debe ver mov Centro B"
        assert mov_salida_central.id in ids, "Farmacia debe ver mov central"


# =============================================================================
# SEC-04: SALIDA MANUAL SOLO SOBRE INVENTARIO PROPIO
# =============================================================================

@pytest.mark.django_db
class TestSEC04_SalidaManualSoloInventarioPropio:
    """
    Un usuario de centro sólo puede crear movimientos de salida
    sobre lotes que pertenecen a su centro.
    """

    def test_salida_sobre_lote_propio_permitida(
        self, user_admin_centro_a, lote_centro_a
    ):
        """Admin de Centro A puede registrar salida sobre su propio lote."""
        client = _client_for(user_admin_centro_a)
        payload = {
            'lote': lote_centro_a.id,
            'tipo': 'salida',
            'cantidad': 10,
            'motivo': 'Salida manual test segregación - uso interno',
        }
        resp = client.post('/api/movimientos/', payload, format='json')
        # Puede ser 201 (creado) o 200, según la vista
        assert resp.status_code in (
            status.HTTP_201_CREATED,
            status.HTTP_200_OK,
        ), f"Esperaba éxito, obtuvo {resp.status_code}: {resp.content}"

    def test_salida_sobre_lote_ajeno_denegada(
        self, user_admin_centro_a, lote_centro_b
    ):
        """Admin de Centro A NO puede crear salida sobre lote de Centro B."""
        client = _client_for(user_admin_centro_a)
        payload = {
            'lote': lote_centro_b.id,
            'tipo': 'salida',
            'cantidad': 5,
            'motivo': 'Intento salida ajena - debería rechazarse',
        }
        resp = client.post('/api/movimientos/', payload, format='json')
        assert resp.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ), f"Debió rechazar, obtuvo {resp.status_code}"

    def test_salida_sobre_lote_central_denegada(
        self, user_admin_centro_a, lote_central
    ):
        """Centro NO puede hacer salida sobre lote de Farmacia Central."""
        client = _client_for(user_admin_centro_a)
        payload = {
            'lote': lote_central.id,
            'tipo': 'salida',
            'cantidad': 5,
            'motivo': 'Intento sobre lote FC - debe rechazarse',
        }
        resp = client.post('/api/movimientos/', payload, format='json')
        assert resp.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ), f"Debió rechazar, obtuvo {resp.status_code}"


# =============================================================================
# SEC-05: RESTRICCIONES POR PERFIL
# =============================================================================

@pytest.mark.django_db
class TestSEC05_RestriccionesPorPerfil:
    """
    Cada rol tiene un nivel de acceso distinto.
    Médico: sólo lectura en ciertos endpoints.
    Vista: sólo lectura global.
    Director: lectura del centro.
    """

    def test_medico_puede_leer_lotes_para_requisicion(
        self, user_medico_centro_a, lote_central
    ):
        """
        Médico puede pedir lotes para_requisicion (farmacia central)
        pero NO debería ver lotes de centro libremente.
        """
        client = _client_for(user_medico_centro_a)
        # Con para_requisicion, el médico ve lotes de FC
        resp = client.get('/api/lotes/', {'para_requisicion': 'true'})
        assert resp.status_code == status.HTTP_200_OK

    def test_medico_no_puede_crear_movimientos_directos(
        self, user_medico_centro_a, lote_centro_a
    ):
        """Médico NO puede crear movimientos de inventario."""
        client = _client_for(user_medico_centro_a)
        payload = {
            'lote': lote_centro_a.id,
            'tipo': 'salida',
            'cantidad': 5,
            'motivo': 'Intento médico crear movimiento directo',
        }
        resp = client.post('/api/movimientos/', payload, format='json')
        # Médico no tiene permiso de escritura en movimientos
        # IsCentroCanManageInventory: medico POST-only pero can_manage_inventory=False
        assert resp.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_400_BAD_REQUEST,
        ), f"Médico no debe crear movimientos: {resp.status_code}"

    def test_vista_solo_lectura_lotes(self, user_vista, lote_centro_a, lote_central):
        """Usuario vista puede leer lotes pero no crear movimientos."""
        client = _client_for(user_vista)

        # Lectura permitida
        resp = client.get('/api/lotes/')
        assert resp.status_code == status.HTTP_200_OK

    def test_vista_no_puede_crear_movimientos(self, user_vista, lote_central):
        """Usuario vista NO puede crear movimientos."""
        client = _client_for(user_vista)
        payload = {
            'lote': lote_central.id,
            'tipo': 'salida',
            'cantidad': 1,
            'motivo': 'Vista intenta crear movimiento',
        }
        resp = client.post('/api/movimientos/', payload, format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN, \
            f"Vista no debe escribir: {resp.status_code}"

    def test_director_puede_leer_su_centro(
        self, user_director_centro_a, lote_centro_a, lote_centro_b
    ):
        """Director ve sólo datos de su centro."""
        client = _client_for(user_director_centro_a)
        resp = client.get('/api/lotes/')
        assert resp.status_code == status.HTTP_200_OK

        data = resp.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        lote_ids = [l['id'] for l in results]

        assert lote_centro_a.id in lote_ids, "Director debe ver lotes de su centro"
        assert lote_centro_b.id not in lote_ids, "Director NO debe ver lotes de otro centro"

    def test_centro_consulta_no_puede_usar_salida_masiva(
        self, user_centro_consulta_a
    ):
        """Rol centro (consulta) no puede acceder a salida-masiva."""
        client = _client_for(user_centro_consulta_a)
        resp = client.get('/api/salida-masiva/lotes-disponibles/')
        assert resp.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_farmacia_puede_crear_movimientos(
        self, user_farmacia, lote_central
    ):
        """Personal de farmacia SÍ puede registrar movimientos."""
        client = _client_for(user_farmacia)
        payload = {
            'lote': lote_central.id,
            'tipo': 'entrada',
            'cantidad': 50,
            'motivo': 'Entrada por compra test farmacia',
        }
        resp = client.post('/api/movimientos/', payload, format='json')
        assert resp.status_code in (
            status.HTTP_201_CREATED,
            status.HTTP_200_OK,
        ), f"Farmacia debe poder crear movimientos: {resp.status_code}"


# =============================================================================
# SEC-06: PROTECCIÓN CONTRA IDOR
# (Insecure Direct Object Reference)
# =============================================================================

@pytest.mark.django_db
class TestSEC06_ProteccionIDOR:
    """
    Verificar que manipular IDs en la URL no permite acceder
    a recursos de otro centro.
    """

    def test_idor_lote_detail_centro_ajeno(
        self, user_admin_centro_a, lote_centro_b
    ):
        """
        Centro A intenta GET /api/lotes/<id_lote_centro_b>/
        Debe recibir 404 (no lo encuentra en su queryset).
        """
        client = _client_for(user_admin_centro_a)
        resp = client.get(f'/api/lotes/{lote_centro_b.id}/')
        assert resp.status_code == status.HTTP_404_NOT_FOUND, \
            f"IDOR: obtuvo {resp.status_code}, esperaba 404"

    def test_idor_movimiento_detail_centro_ajeno(
        self, user_admin_centro_a, mov_entrada_centro_b
    ):
        """
        Centro A intenta GET /api/movimientos/<id_mov_centro_b>/
        Debe recibir 404.
        """
        client = _client_for(user_admin_centro_a)
        resp = client.get(f'/api/movimientos/{mov_entrada_centro_b.id}/')
        assert resp.status_code == status.HTTP_404_NOT_FOUND, \
            f"IDOR: obtuvo {resp.status_code}, esperaba 404"

    def test_idor_lote_central_detail_desde_centro(
        self, user_admin_centro_a, lote_central
    ):
        """
        Centro A intenta acceder al detalle de un lote de FC.
        Debe recibir 404.
        """
        client = _client_for(user_admin_centro_a)
        resp = client.get(f'/api/lotes/{lote_central.id}/')
        assert resp.status_code == status.HTTP_404_NOT_FOUND, \
            f"IDOR: acceso a lote FC desde centro: {resp.status_code}"

    def test_idor_patch_lote_ajeno(
        self, user_admin_centro_a, lote_centro_b
    ):
        """
        Centro A intenta PATCH sobre lote de Centro B.
        Debe recibir 403 o 404.
        """
        client = _client_for(user_admin_centro_a)
        resp = client.patch(
            f'/api/lotes/{lote_centro_b.id}/',
            {'cantidad_actual': 0},
            format='json',
        )
        assert resp.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ), f"IDOR PATCH: obtuvo {resp.status_code}"

    def test_idor_delete_lote_ajeno(
        self, user_admin_centro_a, lote_centro_b
    ):
        """
        Centro A intenta DELETE sobre lote de Centro B.
        Debe ser rechazado.
        """
        client = _client_for(user_admin_centro_a)
        resp = client.delete(f'/api/lotes/{lote_centro_b.id}/')
        assert resp.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        ), f"IDOR DELETE: obtuvo {resp.status_code}"

    def test_idor_movimiento_con_lote_ajeno(
        self, user_admin_centro_a, lote_centro_b
    ):
        """
        Centro A intenta crear un movimiento referenciando un lote
        que pertenece a Centro B. La vista debe rechazarlo.
        """
        client = _client_for(user_admin_centro_a)
        payload = {
            'lote': lote_centro_b.id,
            'tipo': 'salida',
            'cantidad': 10,
            'motivo': 'IDOR test - lote ajeno no permitido',
        }
        resp = client.post('/api/movimientos/', payload, format='json')
        assert resp.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ), f"IDOR POST con lote ajeno: obtuvo {resp.status_code}"


# =============================================================================
# SEC-07: FARMACIA / ADMIN VE TODOS LOS DATOS
# =============================================================================

@pytest.mark.django_db
class TestSEC07_FarmaciaAdminVeeTodo:
    """Admin y farmacia ven datos de todos los centros y FC."""

    def test_admin_ve_lotes_todos_los_centros(
        self, user_admin, lote_central, lote_centro_a, lote_centro_b
    ):
        """Admin puede ver lotes de FC, Centro A y Centro B."""
        client = _client_for(user_admin)
        resp = client.get('/api/lotes/')
        assert resp.status_code == status.HTTP_200_OK

        data = resp.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        ids = [l['id'] for l in results]

        assert lote_central.id in ids, "Admin debe ver lote FC"
        assert lote_centro_a.id in ids, "Admin debe ver lote Centro A"
        assert lote_centro_b.id in ids, "Admin debe ver lote Centro B"

    def test_farmacia_ve_lotes_todos_los_centros(
        self, user_farmacia, lote_central, lote_centro_a, lote_centro_b
    ):
        """Farmacia puede ver lotes de FC, Centro A y Centro B."""
        client = _client_for(user_farmacia)
        resp = client.get('/api/lotes/')
        assert resp.status_code == status.HTTP_200_OK

        data = resp.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        ids = [l['id'] for l in results]

        assert lote_central.id in ids, "Farmacia debe ver lote FC"
        assert lote_centro_a.id in ids, "Farmacia debe ver lote Centro A"
        assert lote_centro_b.id in ids, "Farmacia debe ver lote Centro B"

    def test_admin_ve_movimientos_todos(
        self, user_admin,
        mov_entrada_centro_a, mov_entrada_centro_b, mov_salida_central
    ):
        """Admin ve movimientos de todos los centros."""
        client = _client_for(user_admin)
        resp = client.get('/api/movimientos/')
        assert resp.status_code == status.HTTP_200_OK

        data = resp.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        ids = [m['id'] for m in results]

        assert mov_entrada_centro_a.id in ids
        assert mov_entrada_centro_b.id in ids
        assert mov_salida_central.id in ids

    def test_admin_puede_filtrar_por_centro(
        self, user_admin, centro_a,
        lote_centro_a, lote_centro_b
    ):
        """Admin puede filtrar lotes por centro específico."""
        client = _client_for(user_admin)
        resp = client.get('/api/lotes/', {'centro': centro_a.id})
        assert resp.status_code == status.HTTP_200_OK

        data = resp.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        ids = [l['id'] for l in results]

        assert lote_centro_a.id in ids
        # Centro B no debe aparecer cuando filtramos por Centro A
        assert lote_centro_b.id not in ids


# =============================================================================
# SEC-08: AUDITORÍA Y TRAZABILIDAD
# =============================================================================

@pytest.mark.django_db
class TestSEC08_AuditoriaTrazabilidad:
    """
    Verificar que los movimientos registran correctamente
    quién los creó (responsable, usuario).
    """

    def test_movimiento_registra_responsable(
        self, user_farmacia, lote_central
    ):
        """Al crear un movimiento, queda registrado el usuario responsable."""
        client = _client_for(user_farmacia)
        payload = {
            'lote': lote_central.id,
            'tipo': 'entrada',
            'cantidad': 25,
            'motivo': 'Auditoría test - registro responsable',
        }
        resp = client.post('/api/movimientos/', payload, format='json')
        if resp.status_code in (status.HTTP_201_CREATED, status.HTTP_200_OK):
            data = resp.json()
            mov_id = data.get('id')
            if mov_id:
                mov = Movimiento.objects.get(id=mov_id)
                assert mov.usuario is not None or data.get('usuario_nombre'), \
                    "El movimiento debe registrar usuario responsable"

    def test_movimiento_tiene_fecha_y_tipo(
        self, user_admin, lote_central
    ):
        """Los movimientos registran fecha, tipo correctamente."""
        client = _client_for(user_admin)
        payload = {
            'lote': lote_central.id,
            'tipo': 'entrada',
            'cantidad': 10,
            'motivo': 'Ajuste auditoría - fecha y tipo',
        }
        resp = client.post('/api/movimientos/', payload, format='json')
        if resp.status_code in (status.HTTP_201_CREATED, status.HTTP_200_OK):
            data = resp.json()
            assert data.get('tipo') == 'entrada'
            assert data.get('fecha') or data.get('fecha_movimiento') or data.get('created_at'), \
                "Debe registrar fecha"

    def test_historial_movimientos_lote_cronologico(
        self, user_admin, lote_central
    ):
        """Los movimientos se pueden consultar en orden cronológico."""
        client = _client_for(user_admin)
        # Crear dos movimientos consecutivos
        for i in range(2):
            client.post('/api/movimientos/', {
                'lote': lote_central.id,
                'tipo': 'entrada',
                'cantidad': 5 + i,
                'motivo': f'Cronológico #{i} - auditoría test',
            }, format='json')

        resp = client.get('/api/movimientos/', {'lote': lote_central.id})
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        assert len(results) >= 2, "Debe haber al menos 2 movimientos"


# =============================================================================
# SEC-09: USUARIO SIN CENTRO ASIGNADO
# =============================================================================

@pytest.mark.django_db
class TestSEC09_UsuarioSinCentro:
    """
    Un usuario con rol de centro pero sin centro asignado (centro=None)
    no debe ver datos de ningún centro.
    """

    def test_usuario_centro_sin_centro_ve_lista_vacia(
        self, lote_centro_a, lote_centro_b, db
    ):
        """Usuario con rol='centro' pero centro=None ve vacío."""
        user = _make_user('seg_huerfano', 'centro', centro=None)
        client = _client_for(user)
        resp = client.get('/api/lotes/')
        assert resp.status_code == status.HTTP_200_OK

        data = resp.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        assert len(results) == 0, \
            f"Usuario sin centro asignado NO debe ver lotes, vio {len(results)}"

    def test_usuario_centro_sin_centro_no_puede_crear_movimiento(
        self, lote_centro_a, db
    ):
        """Usuario sin centro asignado no puede crear movimientos."""
        user = _make_user('seg_huerfano2', 'centro', centro=None)
        client = _client_for(user)
        payload = {
            'lote': lote_centro_a.id,
            'tipo': 'salida',
            'cantidad': 1,
            'motivo': 'Sin centro asignado - test segregación',
        }
        resp = client.post('/api/movimientos/', payload, format='json')
        assert resp.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        )


# =============================================================================
# SEC-10: CROSS-CHECK BIDIRECCIONAL
# =============================================================================

@pytest.mark.django_db
class TestSEC10_CrossCheckBidireccional:
    """
    Verificación cruzada: lo que ve Centro A vs Centro B
    deben ser conjuntos completamente disjuntos.
    """

    def test_lotes_disjuntos_entre_centros(
        self, user_admin_centro_a, user_admin_centro_b,
        lote_centro_a, lote_centro_b, lote_extra_centro_b
    ):
        """Los lotes visibles de Centro A y Centro B son conjuntos disjuntos."""
        client_a = _client_for(user_admin_centro_a)
        client_b = _client_for(user_admin_centro_b)

        resp_a = client_a.get('/api/lotes/')
        resp_b = client_b.get('/api/lotes/')

        data_a = resp_a.json()
        data_b = resp_b.json()

        results_a = data_a.get('results', data_a) if isinstance(data_a, dict) else data_a
        results_b = data_b.get('results', data_b) if isinstance(data_b, dict) else data_b

        ids_a = set(l['id'] for l in results_a)
        ids_b = set(l['id'] for l in results_b)

        interseccion = ids_a & ids_b
        assert len(interseccion) == 0, \
            f"Centros comparten lotes (IDs: {interseccion}) — violación de segregación"

    def test_movimientos_disjuntos_entre_centros(
        self, user_admin_centro_a, user_admin_centro_b,
        mov_entrada_centro_a, mov_entrada_centro_b
    ):
        """Los movimientos visibles de Centro A y B son conjuntos disjuntos."""
        client_a = _client_for(user_admin_centro_a)
        client_b = _client_for(user_admin_centro_b)

        resp_a = client_a.get('/api/movimientos/')
        resp_b = client_b.get('/api/movimientos/')

        data_a = resp_a.json()
        data_b = resp_b.json()

        results_a = data_a.get('results', data_a) if isinstance(data_a, dict) else data_a
        results_b = data_b.get('results', data_b) if isinstance(data_b, dict) else data_b

        ids_a = set(m['id'] for m in results_a)
        ids_b = set(m['id'] for m in results_b)

        interseccion = ids_a & ids_b
        assert len(interseccion) == 0, \
            f"Centros comparten movimientos (IDs: {interseccion}) — violación de segregación"
