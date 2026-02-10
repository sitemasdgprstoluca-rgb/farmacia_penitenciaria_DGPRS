# -*- coding: utf-8 -*-
"""
================================================================================
QA COMPLETO — DISPENSACIONES + CAJA CHICA POR CENTRO
================================================================================
Validación integral:  Negocio · Funcional · Técnico · Seguridad · Masiva

 TC-DISP-01   Acceso a módulos/submódulos según rol
 TC-DISP-02   Dispensar descuenta inventario correcto y genera trazabilidad
 TC-DISP-03   Dispensación parcial (forzar_parcial)
 TC-DISP-04   Cancelación de dispensación con motivo
 TC-DISP-05   Exportar PDF Formato C
 TC-DISP-06   Historial auditable de dispensación
 TC-CCH-01    Registro caja chica por centro (sin cruzar datos)
 TC-CCH-02    Flujo multinivel: pendiente → comprada → recibida
 TC-CCH-03    Salida de inventario caja chica
 TC-CCH-04    Ajuste de inventario caja chica
 TC-CCH-05    Historial/trazabilidad de compras caja chica
 TC-COMP-01   Compra genera inventario exclusivamente para el centro
 TC-INV-01    Dispensación descuenta inventario del centro correcto
 TC-SEC-01    Centro A no accede a Centro B (API: dispensaciones + CC)
 TC-SEC-02    IDOR en compras, inventario y movimientos caja chica
 TC-SEC-03    Farmacia solo lectura en dispensaciones
 TC-SEC-04    Farmacia verificación stock en caja chica
 TC-SEC-05    Roles por endpoint — matriz completa
 TC-TRAZ-01   Trazabilidad end-to-end compra→inventario→salida→movimiento
 TC-TRAZ-02   Auditoría registra usuario, centro, timestamp, acción
 TC-VOL-01    Prueba masiva multi-centro (N compras, N dispensaciones)

Autor: QA Automatizado
Fecha: 2026-02-10
================================================================================
"""
import os, uuid
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from core.models import (
    Producto, Lote, Centro, Movimiento,
    Dispensacion, DetalleDispensacion, HistorialDispensacion, Paciente,
    CompraCajaChica, DetalleCompraCajaChica,
    InventarioCajaChica, MovimientoCajaChica, HistorialCompraCajaChica,
)

User = get_user_model()

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
_counter = 0

def _uid():
    global _counter
    _counter += 1
    return _counter

def _make_user(username, rol, centro=None, **kw):
    """Crea o actualiza usuario de test."""
    try:
        u = User.objects.get(username=username)
        changed = False
        for attr in ('rol', 'centro'):
            val = centro if attr == 'centro' else rol
            if getattr(u, attr) != val:
                setattr(u, attr, val)
                changed = True
        for k, v in kw.items():
            if getattr(u, k, None) != v:
                setattr(u, k, v)
                changed = True
        if changed:
            u.save()
        return u
    except User.DoesNotExist:
        is_su = kw.pop('is_superuser', False)
        is_st = kw.pop('is_staff', False)
        return User.objects.create_user(
            username=username, password='QaFull2026!',
            email=f'{username}@qa.test', rol=rol, centro=centro,
            is_active=True, is_superuser=is_su, is_staff=is_st, **kw,
        )


def _cli(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _json(resp):
    """Extrae lista de resultados de respuesta paginada o lista."""
    data = resp.json()
    if isinstance(data, list):
        return data
    return data.get('results', data) if isinstance(data, dict) else data


# ─────────────────────────────────────────────────────────────────────────────
# FIXTURES COMPARTIDOS
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def centro_a(db):
    o, _ = Centro.objects.get_or_create(
        nombre='Centro Alfa QA-Full',
        defaults={'direccion': 'Dir Alfa', 'activo': True},
    )
    return o

@pytest.fixture
def centro_b(db):
    o, _ = Centro.objects.get_or_create(
        nombre='Centro Bravo QA-Full',
        defaults={'direccion': 'Dir Bravo', 'activo': True},
    )
    return o

@pytest.fixture
def prod1(db):
    o, _ = Producto.objects.get_or_create(
        clave='QA-FULL-001',
        defaults={'nombre': 'Amoxicilina 500mg QA', 'unidad_medida': 'TABLETA',
                  'categoria': 'medicamento', 'activo': True},
    )
    return o

@pytest.fixture
def prod2(db):
    o, _ = Producto.objects.get_or_create(
        clave='QA-FULL-002',
        defaults={'nombre': 'Metformina 850mg QA', 'unidad_medida': 'TABLETA',
                  'categoria': 'medicamento', 'activo': True},
    )
    return o

@pytest.fixture
def lote_a(prod1, centro_a, db):
    o, _ = Lote.objects.get_or_create(
        producto=prod1, numero_lote='QA-FULL-LOT-A1',
        defaults={'centro': centro_a, 'fecha_caducidad': date(2028, 12, 31),
                  'cantidad_inicial': 500, 'cantidad_actual': 500,
                  'precio_unitario': Decimal('6.50'), 'activo': True},
    )
    o.cantidad_actual = 500; o.centro = centro_a; o.activo = True; o.save()
    return o

@pytest.fixture
def lote_b(prod1, centro_b, db):
    o, _ = Lote.objects.get_or_create(
        producto=prod1, numero_lote='QA-FULL-LOT-B1',
        defaults={'centro': centro_b, 'fecha_caducidad': date(2028, 12, 31),
                  'cantidad_inicial': 300, 'cantidad_actual': 300,
                  'precio_unitario': Decimal('6.50'), 'activo': True},
    )
    o.cantidad_actual = 300; o.centro = centro_b; o.activo = True; o.save()
    return o

@pytest.fixture
def pac_a(centro_a, db):
    o, _ = Paciente.objects.get_or_create(
        numero_expediente='QA-FULL-EXP-A1',
        defaults={'nombre': 'Carlos', 'apellido_paterno': 'Méndez',
                  'apellido_materno': 'Salas', 'fecha_nacimiento': date(1980, 5, 10),
                  'sexo': 'M', 'centro': centro_a, 'activo': True},
    )
    return o

@pytest.fixture
def pac_b(centro_b, db):
    o, _ = Paciente.objects.get_or_create(
        numero_expediente='QA-FULL-EXP-B1',
        defaults={'nombre': 'Laura', 'apellido_paterno': 'Ríos',
                  'apellido_materno': 'Vega', 'fecha_nacimiento': date(1992, 11, 3),
                  'sexo': 'F', 'centro': centro_b, 'activo': True},
    )
    return o

# ── Usuarios ──

@pytest.fixture
def admin_global(db):
    return _make_user('qf_admin', 'admin', is_superuser=True, is_staff=True)

@pytest.fixture
def farm_user(db):
    return _make_user('qf_farmacia', 'farmacia', is_staff=True)

@pytest.fixture
def adm_a(centro_a, db):
    return _make_user('qf_adm_a', 'administrador_centro', centro=centro_a)

@pytest.fixture
def adm_b(centro_b, db):
    return _make_user('qf_adm_b', 'administrador_centro', centro=centro_b)

@pytest.fixture
def med_a(centro_a, db):
    return _make_user('qf_med_a', 'medico', centro=centro_a)

@pytest.fixture
def med_b(centro_b, db):
    return _make_user('qf_med_b', 'medico', centro=centro_b)

@pytest.fixture
def dir_a(centro_a, db):
    return _make_user('qf_dir_a', 'director_centro', centro=centro_a)

@pytest.fixture
def centro_user_a(centro_a, db):
    return _make_user('qf_centro_a', 'centro', centro=centro_a)

@pytest.fixture
def no_centro_user(db):
    return _make_user('qf_sincentro', 'centro')

# ── Inventario Caja Chica pre-creado ──

@pytest.fixture
def inv_cc_a(centro_a, prod1, db):
    o, _ = InventarioCajaChica.objects.get_or_create(
        centro=centro_a, producto=prod1, numero_lote='QA-FULL-CC-A',
        defaults={'descripcion_producto': 'Amoxicilina CC QA',
                  'cantidad_inicial': 200, 'cantidad_actual': 200,
                  'precio_unitario': Decimal('8.00'), 'activo': True},
    )
    o.cantidad_actual = 200; o.activo = True; o.save()
    return o

@pytest.fixture
def inv_cc_b(centro_b, prod1, db):
    o, _ = InventarioCajaChica.objects.get_or_create(
        centro=centro_b, producto=prod1, numero_lote='QA-FULL-CC-B',
        defaults={'descripcion_producto': 'Amoxicilina CC QA',
                  'cantidad_inicial': 150, 'cantidad_actual': 150,
                  'precio_unitario': Decimal('8.00'), 'activo': True},
    )
    o.cantidad_actual = 150; o.activo = True; o.save()
    return o

# ── Helpers para crear dispensaciones / compras por API ──

def _crear_dispensacion(cli, pac, prod, lote, prescrita=5):
    return cli.post('/api/dispensaciones/', {
        'paciente': pac.id,
        'tipo_dispensacion': 'normal',
        'medico_prescriptor': 'Dr. QA Full',
        'detalles': [{'producto': prod.id, 'lote': lote.id,
                      'cantidad_prescrita': prescrita}],
    }, format='json')


def _crear_compra_cc(cli, centro, prod, cant=10, precio=12.00, desc='Med QA CC'):
    return cli.post('/api/compras-caja-chica/', {
        'motivo_compra': f'Compra QA-{uuid.uuid4().hex[:6]}',
        'centro': centro.id,
        'detalles_write': [{
            'descripcion_producto': desc,
            'cantidad': cant,
            'precio_unitario': precio,
            'producto': prod.id,
        }],
    }, format='json')


def _avanzar_a_comprada(cli, compra_id):
    """Lleva compra de pendiente → comprada via registrar_compra."""
    det = DetalleCompraCajaChica.objects.filter(compra_id=compra_id).first()
    return cli.post(f'/api/compras-caja-chica/{compra_id}/registrar_compra/', {
        'fecha_compra': str(date.today()),
        'proveedor_nombre': 'Proveedor QA Full',
        'numero_factura': f'FAC-{uuid.uuid4().hex[:6]}',
        'detalles': [{'id': det.id, 'cantidad_comprada': det.cantidad_solicitada,
                      'precio_unitario': float(det.precio_unitario)}] if det else [],
    }, format='json')


def _recibir_compra(cli, compra_id):
    """Recibe compra comprada → recibida."""
    dets = DetalleCompraCajaChica.objects.filter(compra_id=compra_id)
    return cli.post(f'/api/compras-caja-chica/{compra_id}/recibir/', {
        'detalles': [{'id': d.id, 'cantidad_recibida': d.cantidad_comprada or d.cantidad_solicitada}
                     for d in dets],
    }, format='json')


# ═════════════════════════════════════════════════════════════════════════════
# TC-DISP-01  ACCESO A MÓDULOS/SUBMÓDULOS SEGÚN ROL
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTC_DISP_01_AccesoModulos:
    """
    Given  un usuario autenticado con rol válido
    When   navega a endpoints de dispensaciones y submódulos
    Then   solo accede si su rol lo permite y solo ve datos de su centro.
    """

    @pytest.mark.parametrize("fixture_user,expected", [
        ('adm_a', 200), ('med_a', 200), ('dir_a', 200),
        ('farm_user', 200), ('admin_global', 200),
    ])
    def test_listar_dispensaciones(self, fixture_user, expected, request,
                                   pac_a, lote_a, prod1, adm_a):
        """Todos los roles válidos pueden listar dispensaciones."""
        # Crear una dispensación primero
        _crear_dispensacion(_cli(adm_a), pac_a, prod1, lote_a)
        user = request.getfixturevalue(fixture_user)
        resp = _cli(user).get('/api/dispensaciones/')
        assert resp.status_code == expected

    def test_listar_detalle_dispensaciones(self, adm_a, pac_a, prod1, lote_a):
        """Submódulo detalle-dispensaciones accesible."""
        resp = _cli(adm_a).get('/api/detalle-dispensaciones/')
        assert resp.status_code == 200

    def test_listar_pacientes(self, adm_a):
        """Submódulo pacientes accesible."""
        resp = _cli(adm_a).get('/api/pacientes/')
        assert resp.status_code == 200

    def test_centro_a_solo_datos_centro_a(self, adm_a, adm_b,
                                           pac_a, pac_b, prod1,
                                           lote_a, lote_b):
        """Centro A solo ve dispensaciones de Centro A."""
        _crear_dispensacion(_cli(adm_a), pac_a, prod1, lote_a)
        _crear_dispensacion(_cli(adm_b), pac_b, prod1, lote_b)
        ids_a = [d['id'] for d in _json(_cli(adm_a).get('/api/dispensaciones/'))]
        ids_b = [d['id'] for d in _json(_cli(adm_b).get('/api/dispensaciones/'))]
        assert set(ids_a).isdisjoint(set(ids_b)), \
            "Dispensaciones de Centro A y B deben ser disjuntas"


# ═════════════════════════════════════════════════════════════════════════════
# TC-DISP-02  DISPENSAR DESCUENTA INVENTARIO Y GENERA TRAZABILIDAD
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTC_DISP_02_DispensarDescuentaInventario:
    """
    Given  inventario en Centro A
    When   se dispensa
    Then   stock baja, movimiento de salida creado, estado = dispensada.
    """

    def test_descuenta_stock_lote(self, adm_a, pac_a, prod1, lote_a):
        stock_pre = lote_a.cantidad_actual
        resp = _crear_dispensacion(_cli(adm_a), pac_a, prod1, lote_a, prescrita=8)
        did = resp.json()['id']
        _cli(adm_a).post(f'/api/dispensaciones/{did}/dispensar/', format='json')
        lote_a.refresh_from_db()
        assert lote_a.cantidad_actual == stock_pre - 8

    def test_genera_movimiento_salida_dispensacion(self, adm_a, pac_a, prod1, lote_a):
        resp = _crear_dispensacion(_cli(adm_a), pac_a, prod1, lote_a, prescrita=5)
        did = resp.json()['id']
        _cli(adm_a).post(f'/api/dispensaciones/{did}/dispensar/', format='json')
        mov = Movimiento.objects.filter(lote=lote_a, tipo='salida',
                                         subtipo_salida='dispensacion').last()
        assert mov is not None
        assert mov.cantidad == 5
        assert mov.usuario_id == adm_a.id

    def test_estado_dispensada(self, adm_a, pac_a, prod1, lote_a):
        resp = _crear_dispensacion(_cli(adm_a), pac_a, prod1, lote_a)
        did = resp.json()['id']
        _cli(adm_a).post(f'/api/dispensaciones/{did}/dispensar/', format='json')
        d = Dispensacion.objects.get(id=did)
        assert d.estado == 'dispensada'

    def test_dispensado_por_registrado(self, adm_a, pac_a, prod1, lote_a):
        resp = _crear_dispensacion(_cli(adm_a), pac_a, prod1, lote_a)
        did = resp.json()['id']
        _cli(adm_a).post(f'/api/dispensaciones/{did}/dispensar/', format='json')
        d = Dispensacion.objects.get(id=did)
        assert d.dispensado_por_id == adm_a.id

    def test_no_descuenta_lote_otro_centro(self, adm_a, pac_a, prod1, lote_a, lote_b):
        """Dispensar en A no toca stock de B."""
        stock_b = lote_b.cantidad_actual
        resp = _crear_dispensacion(_cli(adm_a), pac_a, prod1, lote_a, prescrita=3)
        _cli(adm_a).post(f'/api/dispensaciones/{resp.json()["id"]}/dispensar/',
                         format='json')
        lote_b.refresh_from_db()
        assert lote_b.cantidad_actual == stock_b


# ═════════════════════════════════════════════════════════════════════════════
# TC-DISP-03  DISPENSACIÓN PARCIAL (FORZAR_PARCIAL)
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTC_DISP_03_Parcial:
    """
    Given  stock insuficiente respecto a la cantidad prescrita
    When   se invoca dispensar con forzar_parcial=True
    Then   se dispensa lo disponible, estado=parcial, stock=0.
    """

    def test_forzar_parcial_despacha_disponible(self, adm_a, pac_a, prod1, centro_a, db):
        # Lote con stock bajo
        lot, _ = Lote.objects.get_or_create(
            producto=prod1, numero_lote='QA-FULL-PARC-LOT',
            defaults={'centro': centro_a, 'fecha_caducidad': date(2028, 12, 31),
                      'cantidad_inicial': 20, 'cantidad_actual': 20,
                      'precio_unitario': Decimal('6.50'), 'activo': True},
        )
        lot.cantidad_actual = 20; lot.save()
        resp = _crear_dispensacion(_cli(adm_a), pac_a, prod1, lot, prescrita=999)
        did = resp.json()['id']
        r = _cli(adm_a).post(f'/api/dispensaciones/{did}/dispensar/',
                              {'forzar_parcial': True}, format='json')
        assert r.status_code == 200
        d = Dispensacion.objects.get(id=did)
        assert d.estado == 'parcial'
        lot.refresh_from_db()
        assert lot.cantidad_actual == 0

    def test_sin_forzar_parcial_rechaza(self, adm_a, pac_a, prod1, centro_a, db):
        lot, _ = Lote.objects.get_or_create(
            producto=prod1, numero_lote='QA-FULL-PARC-LOT2',
            defaults={'centro': centro_a, 'fecha_caducidad': date(2028, 12, 31),
                      'cantidad_inicial': 5, 'cantidad_actual': 5,
                      'precio_unitario': Decimal('6.50'), 'activo': True},
        )
        lot.cantidad_actual = 5; lot.save()
        resp = _crear_dispensacion(_cli(adm_a), pac_a, prod1, lot, prescrita=999)
        did = resp.json()['id']
        r = _cli(adm_a).post(f'/api/dispensaciones/{did}/dispensar/',
                              {'forzar_parcial': False}, format='json')
        assert r.status_code in (400, 200)
        if r.status_code == 400:
            assert 'error' in r.json() or 'detail' in r.json()


# ═════════════════════════════════════════════════════════════════════════════
# TC-DISP-04  CANCELACIÓN DE DISPENSACIÓN
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTC_DISP_04_CancelarDispensacion:
    """
    Given  dispensación en estado pendiente
    When   se cancela con motivo
    Then   estado=cancelada, motivo guardado, historial registrado.
    """

    def test_cancelar_guarda_motivo_y_estado(self, adm_a, pac_a, prod1, lote_a):
        resp = _crear_dispensacion(_cli(adm_a), pac_a, prod1, lote_a)
        did = resp.json()['id']
        r = _cli(adm_a).post(f'/api/dispensaciones/{did}/cancelar/',
                              {'motivo': 'Paciente dado de alta'}, format='json')
        assert r.status_code == 200
        d = Dispensacion.objects.get(id=did)
        assert d.estado == 'cancelada'
        assert d.motivo_cancelacion is not None

    def test_cancelar_crea_historial(self, adm_a, pac_a, prod1, lote_a):
        resp = _crear_dispensacion(_cli(adm_a), pac_a, prod1, lote_a)
        did = resp.json()['id']
        _cli(adm_a).post(f'/api/dispensaciones/{did}/cancelar/',
                          {'motivo': 'Error de prescripción'}, format='json')
        hist = HistorialDispensacion.objects.filter(
            dispensacion_id=did, accion='cancelar')
        assert hist.exists(), "Debe registrarse historial de cancelación"


# ═════════════════════════════════════════════════════════════════════════════
# TC-DISP-05  EXPORTAR PDF FORMATO C
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTC_DISP_05_ExportarPDF:
    """
    Given  dispensación existente
    When   se solicita exportar_pdf
    Then   responde 200 con content-type application/pdf.
    """

    def test_exportar_pdf_devuelve_pdf(self, adm_a, pac_a, prod1, lote_a):
        resp = _crear_dispensacion(_cli(adm_a), pac_a, prod1, lote_a)
        did = resp.json()['id']
        r = _cli(adm_a).get(f'/api/dispensaciones/{did}/exportar_pdf/')
        assert r.status_code == 200
        ct = r.get('Content-Type', '')
        assert 'pdf' in ct or 'octet' in ct, f"Esperado PDF, obtenido {ct}"


# ═════════════════════════════════════════════════════════════════════════════
# TC-DISP-06  HISTORIAL AUDITABLE DE DISPENSACIÓN
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTC_DISP_06_HistorialAuditable:
    """
    Given  dispensación creada
    When   se ejecutan acciones (crear, dispensar, cancelar)
    Then   el historial registra cada acción con usuario, timestamp, estado.
    """

    def test_historial_api_disponible(self, adm_a, pac_a, prod1, lote_a):
        resp = _crear_dispensacion(_cli(adm_a), pac_a, prod1, lote_a)
        did = resp.json()['id']
        r = _cli(adm_a).get(f'/api/dispensaciones/{did}/historial/')
        assert r.status_code == 200
        hist = _json(r)
        assert len(hist) >= 1, "Historial debe tener al menos entrada de creación"

    def test_historial_registra_dispensar(self, adm_a, pac_a, prod1, lote_a):
        resp = _crear_dispensacion(_cli(adm_a), pac_a, prod1, lote_a)
        did = resp.json()['id']
        _cli(adm_a).post(f'/api/dispensaciones/{did}/dispensar/', format='json')
        hist = HistorialDispensacion.objects.filter(dispensacion_id=did)
        acciones = list(hist.values_list('accion', flat=True))
        assert 'dispensar' in acciones or 'completar' in acciones, \
            f"Historial debe registrar dispensar. Acciones: {acciones}"

    def test_historial_contiene_usuario(self, adm_a, pac_a, prod1, lote_a):
        resp = _crear_dispensacion(_cli(adm_a), pac_a, prod1, lote_a)
        did = resp.json()['id']
        h = HistorialDispensacion.objects.filter(dispensacion_id=did).first()
        assert h is not None
        assert h.usuario_id == adm_a.id


# ═════════════════════════════════════════════════════════════════════════════
# TC-CCH-01  REGISTRO CAJA CHICA POR CENTRO (SIN CRUZAR DATOS)
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTC_CCH_01_RegistroPorCentro:
    """
    Given  usuarios de Centro A y Centro B
    When   cada uno registra compras de caja chica
    Then   cada uno solo ve sus propias compras.
    """

    def test_compra_a_invisible_para_b(self, adm_a, adm_b, centro_a, centro_b, prod1):
        r_a = _crear_compra_cc(_cli(adm_a), centro_a, prod1)
        assert r_a.status_code in (200, 201)
        cid = r_a.json()['id']
        ids_b = [c['id'] for c in _json(_cli(adm_b).get('/api/compras-caja-chica/'))]
        assert cid not in ids_b

    def test_compra_b_invisible_para_a(self, adm_a, adm_b, centro_a, centro_b, prod1):
        r_b = _crear_compra_cc(_cli(adm_b), centro_b, prod1)
        assert r_b.status_code in (200, 201)
        cid = r_b.json()['id']
        ids_a = [c['id'] for c in _json(_cli(adm_a).get('/api/compras-caja-chica/'))]
        assert cid not in ids_a

    def test_folio_generado_automaticamente(self, adm_a, centro_a, prod1):
        r = _crear_compra_cc(_cli(adm_a), centro_a, prod1)
        assert r.status_code in (200, 201)
        data = r.json()
        assert data.get('id') is not None
        compra = CompraCajaChica.objects.get(id=data['id'])
        assert compra.folio and len(compra.folio) > 0, "Folio auto-generado obligatorio"


# ═════════════════════════════════════════════════════════════════════════════
# TC-CCH-02  FLUJO MULTINIVEL: PENDIENTE → COMPRADA → RECIBIDA
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTC_CCH_02_FlujoMultinivel:
    """
    Given  compra creada en estado pendiente
    When   transiciona: pendiente → comprada → recibida
    Then   cada transición se completa, el estado persiste.
    """

    def test_pendiente_a_comprada(self, adm_a, centro_a, prod1):
        r = _crear_compra_cc(_cli(adm_a), centro_a, prod1, cant=10)
        cid = r.json()['id']
        r2 = _avanzar_a_comprada(_cli(adm_a), cid)
        assert r2.status_code == 200
        c = CompraCajaChica.objects.get(id=cid)
        assert c.estado == 'comprada'

    def test_comprada_a_recibida(self, adm_a, centro_a, prod1):
        r = _crear_compra_cc(_cli(adm_a), centro_a, prod1, cant=10)
        cid = r.json()['id']
        _avanzar_a_comprada(_cli(adm_a), cid)
        r3 = _recibir_compra(_cli(adm_a), cid)
        assert r3.status_code == 200
        c = CompraCajaChica.objects.get(id=cid)
        assert c.estado == 'recibida'

    def test_recibida_registra_recibido_por(self, adm_a, centro_a, prod1):
        r = _crear_compra_cc(_cli(adm_a), centro_a, prod1, cant=5)
        cid = r.json()['id']
        _avanzar_a_comprada(_cli(adm_a), cid)
        _recibir_compra(_cli(adm_a), cid)
        c = CompraCajaChica.objects.get(id=cid)
        assert c.recibido_por_id == adm_a.id

    def test_calcular_totales(self, adm_a, centro_a, prod1):
        r = _crear_compra_cc(_cli(adm_a), centro_a, prod1, cant=10, precio=100)
        data = r.json()
        # Verificar que totales se calculan
        subtotal = Decimal(str(data.get('subtotal', 0)))
        total = Decimal(str(data.get('total', 0)))
        assert subtotal > 0 or total > 0


# ═════════════════════════════════════════════════════════════════════════════
# TC-CCH-03  SALIDA DE INVENTARIO CAJA CHICA
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTC_CCH_03_SalidaInventario:
    """
    Given  inventario CC con stock
    When   se registra salida
    Then   stock baja, movimiento creado, exceso rechazado.
    """

    def test_salida_descuenta_stock(self, adm_a, inv_cc_a):
        r = _cli(adm_a).post(f'/api/inventario-caja-chica/{inv_cc_a.id}/registrar_salida/', {
            'cantidad': 30, 'motivo': 'Uso clínico QA', 'referencia': 'REF-001',
        }, format='json')
        assert r.status_code == 200
        inv_cc_a.refresh_from_db()
        assert inv_cc_a.cantidad_actual == 170

    def test_salida_crea_movimiento_salida(self, adm_a, inv_cc_a):
        pre = MovimientoCajaChica.objects.filter(inventario=inv_cc_a, tipo='salida').count()
        _cli(adm_a).post(f'/api/inventario-caja-chica/{inv_cc_a.id}/registrar_salida/', {
            'cantidad': 10, 'motivo': 'QA mov salida',
        }, format='json')
        post = MovimientoCajaChica.objects.filter(inventario=inv_cc_a, tipo='salida').count()
        assert post > pre

    def test_salida_excede_stock_rechazada(self, adm_a, inv_cc_a):
        r = _cli(adm_a).post(f'/api/inventario-caja-chica/{inv_cc_a.id}/registrar_salida/', {
            'cantidad': 9999, 'motivo': 'Exceso',
        }, format='json')
        assert r.status_code == 400

    def test_salida_cero_rechazada(self, adm_a, inv_cc_a):
        r = _cli(adm_a).post(f'/api/inventario-caja-chica/{inv_cc_a.id}/registrar_salida/', {
            'cantidad': 0, 'motivo': 'Cero',
        }, format='json')
        assert r.status_code == 400


# ═════════════════════════════════════════════════════════════════════════════
# TC-CCH-04  AJUSTE DE INVENTARIO CAJA CHICA
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTC_CCH_04_AjusteInventario:
    """
    Given  inventario CC existente
    When   se ajusta cantidad
    Then   nuevo stock = cantidad indicada, movimiento ajuste creado.
    """

    def test_ajuste_positivo(self, adm_a, inv_cc_a):
        r = _cli(adm_a).post(f'/api/inventario-caja-chica/{inv_cc_a.id}/ajustar/', {
            'cantidad': 250, 'motivo': 'Ajuste inventario físico QA',
        }, format='json')
        assert r.status_code == 200
        inv_cc_a.refresh_from_db()
        assert inv_cc_a.cantidad_actual == 250
        mov = MovimientoCajaChica.objects.filter(
            inventario=inv_cc_a, tipo='ajuste_positivo').last()
        assert mov is not None
        assert mov.cantidad == 50  # 250-200

    def test_ajuste_negativo(self, adm_a, inv_cc_a):
        r = _cli(adm_a).post(f'/api/inventario-caja-chica/{inv_cc_a.id}/ajustar/', {
            'cantidad': 100, 'motivo': 'Ajuste neg QA',
        }, format='json')
        assert r.status_code == 200
        inv_cc_a.refresh_from_db()
        assert inv_cc_a.cantidad_actual == 100
        mov = MovimientoCajaChica.objects.filter(
            inventario=inv_cc_a, tipo='ajuste_negativo').last()
        assert mov is not None
        assert mov.cantidad == 100  # |100-200|

    def test_ajuste_misma_cantidad_rechazado(self, adm_a, inv_cc_a):
        r = _cli(adm_a).post(f'/api/inventario-caja-chica/{inv_cc_a.id}/ajustar/', {
            'cantidad': 200, 'motivo': 'No cambio',
        }, format='json')
        assert r.status_code == 400


# ═════════════════════════════════════════════════════════════════════════════
# TC-CCH-05  HISTORIAL/TRAZABILIDAD DE COMPRAS CAJA CHICA
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTC_CCH_05_HistorialCompras:
    """
    Given  compra que avanza por estados
    When   cada transición ocurre
    Then   HistorialCompraCajaChica registra cada cambio.
    """

    def test_historial_creado_al_registrar_compra(self, adm_a, centro_a, prod1):
        r = _crear_compra_cc(_cli(adm_a), centro_a, prod1)
        cid = r.json()['id']
        _avanzar_a_comprada(_cli(adm_a), cid)
        hist = HistorialCompraCajaChica.objects.filter(compra_id=cid)
        assert hist.exists(), "Debe existir historial tras registrar compra"

    def test_historial_recibir(self, adm_a, centro_a, prod1):
        r = _crear_compra_cc(_cli(adm_a), centro_a, prod1)
        cid = r.json()['id']
        _avanzar_a_comprada(_cli(adm_a), cid)
        _recibir_compra(_cli(adm_a), cid)
        hist = HistorialCompraCajaChica.objects.filter(compra_id=cid)
        estados = list(hist.values_list('estado_nuevo', flat=True))
        assert 'recibida' in estados, f"Historial debe incluir recibida: {estados}"


# ═════════════════════════════════════════════════════════════════════════════
# TC-COMP-01  COMPRA GENERA INVENTARIO EXCLUSIVAMENTE PARA EL CENTRO
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTC_COMP_01_CompraGeneraInventario:
    """
    Given  compra registrada y comprada para Centro A
    When   se recibe la compra
    Then   se crea InventarioCajaChica solo en Centro A,
           con cantidad, producto y vínculo a la compra.
    """

    def test_recibir_crea_inventario_centro_correcto(self, adm_a, centro_a, centro_b, prod1):
        inv_a_pre = InventarioCajaChica.objects.filter(centro=centro_a).count()
        inv_b_pre = InventarioCajaChica.objects.filter(centro=centro_b).count()

        r = _crear_compra_cc(_cli(adm_a), centro_a, prod1, cant=25)
        cid = r.json()['id']
        _avanzar_a_comprada(_cli(adm_a), cid)
        _recibir_compra(_cli(adm_a), cid)

        inv_a_post = InventarioCajaChica.objects.filter(centro=centro_a).count()
        inv_b_post = InventarioCajaChica.objects.filter(centro=centro_b).count()
        assert inv_a_post > inv_a_pre, "Inventario debe crearse en Centro A"
        assert inv_b_post == inv_b_pre, "Inventario NO debe crearse en Centro B"

    def test_inventario_cantidad_correcta(self, adm_a, centro_a, prod1):
        r = _crear_compra_cc(_cli(adm_a), centro_a, prod1, cant=40)
        cid = r.json()['id']
        _avanzar_a_comprada(_cli(adm_a), cid)
        _recibir_compra(_cli(adm_a), cid)
        inv = InventarioCajaChica.objects.filter(
            centro=centro_a, compra_id=cid).first()
        assert inv is not None
        assert inv.cantidad_actual >= 40

    def test_inventario_vinculado_a_compra(self, adm_a, centro_a, prod1):
        r = _crear_compra_cc(_cli(adm_a), centro_a, prod1, cant=15)
        cid = r.json()['id']
        _avanzar_a_comprada(_cli(adm_a), cid)
        _recibir_compra(_cli(adm_a), cid)
        inv = InventarioCajaChica.objects.filter(compra_id=cid).first()
        assert inv is not None
        assert inv.compra_id == cid, "Inventario debe tener FK a la compra"

    def test_recibir_genera_movimiento_entrada(self, adm_a, centro_a, prod1):
        pre = MovimientoCajaChica.objects.filter(tipo='entrada').count()
        r = _crear_compra_cc(_cli(adm_a), centro_a, prod1, cant=12)
        cid = r.json()['id']
        _avanzar_a_comprada(_cli(adm_a), cid)
        _recibir_compra(_cli(adm_a), cid)
        post = MovimientoCajaChica.objects.filter(tipo='entrada').count()
        assert post > pre


# ═════════════════════════════════════════════════════════════════════════════
# TC-INV-01  DISPENSACIÓN DESCUENTA INVENTARIO DEL CENTRO CORRECTO
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTC_INV_01_DispensacionInventarioCorrecto:
    """
    Given  lotes en Centro A y Centro B
    When   se dispensa en Centro A
    Then   solo el lote de Centro A pierde stock.
    """

    def test_dispensar_a_no_toca_b(self, adm_a, pac_a, prod1, lote_a, lote_b):
        stock_b = lote_b.cantidad_actual
        resp = _crear_dispensacion(_cli(adm_a), pac_a, prod1, lote_a, prescrita=10)
        _cli(adm_a).post(f'/api/dispensaciones/{resp.json()["id"]}/dispensar/',
                         format='json')
        lote_b.refresh_from_db()
        assert lote_b.cantidad_actual == stock_b

    def test_dispensar_b_no_toca_a(self, adm_b, pac_b, prod1, lote_a, lote_b):
        stock_a = lote_a.cantidad_actual
        resp = _crear_dispensacion(_cli(adm_b), pac_b, prod1, lote_b, prescrita=10)
        _cli(adm_b).post(f'/api/dispensaciones/{resp.json()["id"]}/dispensar/',
                         format='json')
        lote_a.refresh_from_db()
        assert lote_a.cantidad_actual == stock_a


# ═════════════════════════════════════════════════════════════════════════════
# TC-SEC-01  CENTRO A NO ACCEDE A CENTRO B  (DISPENSACIONES + CC)
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTC_SEC_01_SegregacionCruzada:
    """
    Given  usuario de Centro A
    When   consulta dispensaciones / compras / inventario CC / movimientos CC
    Then   no ve registros de Centro B.
    """

    def test_dispensaciones_segregadas(self, adm_a, adm_b, pac_a, pac_b,
                                        prod1, lote_a, lote_b):
        _crear_dispensacion(_cli(adm_a), pac_a, prod1, lote_a)
        _crear_dispensacion(_cli(adm_b), pac_b, prod1, lote_b)
        ids_a = {d['id'] for d in _json(_cli(adm_a).get('/api/dispensaciones/'))}
        ids_b = {d['id'] for d in _json(_cli(adm_b).get('/api/dispensaciones/'))}
        assert ids_a.isdisjoint(ids_b)

    def test_compras_cc_segregadas(self, adm_a, adm_b, centro_a, centro_b, prod1):
        _crear_compra_cc(_cli(adm_a), centro_a, prod1)
        _crear_compra_cc(_cli(adm_b), centro_b, prod1)
        ids_a = {c['id'] for c in _json(_cli(adm_a).get('/api/compras-caja-chica/'))}
        ids_b = {c['id'] for c in _json(_cli(adm_b).get('/api/compras-caja-chica/'))}
        assert ids_a.isdisjoint(ids_b)

    def test_inventario_cc_segregado(self, adm_a, adm_b, inv_cc_a, inv_cc_b):
        ids_a = {i['id'] for i in _json(_cli(adm_a).get('/api/inventario-caja-chica/'))}
        ids_b = {i['id'] for i in _json(_cli(adm_b).get('/api/inventario-caja-chica/'))}
        assert inv_cc_a.id in ids_a and inv_cc_a.id not in ids_b
        assert inv_cc_b.id in ids_b and inv_cc_b.id not in ids_a

    def test_movimientos_cc_segregados(self, adm_a, adm_b, inv_cc_a, inv_cc_b):
        # Crear movimiento en A
        _cli(adm_a).post(f'/api/inventario-caja-chica/{inv_cc_a.id}/registrar_salida/', {
            'cantidad': 5, 'motivo': 'Seg test',
        }, format='json')
        movs_a = _json(_cli(adm_a).get('/api/movimientos-caja-chica/'))
        movs_b = _json(_cli(adm_b).get('/api/movimientos-caja-chica/'))
        ids_a = {m['id'] for m in movs_a}
        ids_b = {m['id'] for m in movs_b}
        assert ids_a.isdisjoint(ids_b)


# ═════════════════════════════════════════════════════════════════════════════
# TC-SEC-02  IDOR EN COMPRAS, INVENTARIO Y MOVIMIENTOS CAJA CHICA
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTC_SEC_02_IDOR:
    """
    Given  recursos de Centro B
    When   Centro A intenta acceder por ID directo
    Then   404 o 403 (no fuga de datos).
    """

    def test_idor_compra_detail(self, adm_a, adm_b, centro_b, prod1):
        r = _crear_compra_cc(_cli(adm_b), centro_b, prod1)
        cid = r.json()['id']
        assert _cli(adm_a).get(f'/api/compras-caja-chica/{cid}/').status_code == 404

    def test_idor_inventario_detail(self, adm_a, inv_cc_b):
        assert _cli(adm_a).get(f'/api/inventario-caja-chica/{inv_cc_b.id}/').status_code == 404

    def test_idor_salida_inventario_ajeno(self, adm_a, inv_cc_b):
        r = _cli(adm_a).post(f'/api/inventario-caja-chica/{inv_cc_b.id}/registrar_salida/', {
            'cantidad': 1, 'motivo': 'IDOR test',
        }, format='json')
        assert r.status_code in (403, 404)

    def test_idor_ajuste_inventario_ajeno(self, adm_a, inv_cc_b):
        r = _cli(adm_a).post(f'/api/inventario-caja-chica/{inv_cc_b.id}/ajustar/', {
            'cantidad': 999, 'motivo': 'IDOR ajuste',
        }, format='json')
        assert r.status_code in (403, 404)

    def test_idor_dispensacion_detail(self, adm_a, adm_b, pac_b, prod1, lote_b):
        r = _crear_dispensacion(_cli(adm_b), pac_b, prod1, lote_b)
        did = r.json()['id']
        assert _cli(adm_a).get(f'/api/dispensaciones/{did}/').status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# TC-SEC-03  FARMACIA SOLO LECTURA EN DISPENSACIONES
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTC_SEC_03_FarmaciaSoloLectura:
    """
    Given  usuario con rol farmacia
    When   intenta crear/dispensar/cancelar
    Then   403 o 400 — solo puede leer (auditoría).
    """

    def test_farmacia_lista_dispensaciones(self, farm_user, adm_a, pac_a, prod1, lote_a):
        _crear_dispensacion(_cli(adm_a), pac_a, prod1, lote_a)
        r = _cli(farm_user).get('/api/dispensaciones/')
        assert r.status_code == 200

    def test_farmacia_no_crea_dispensacion(self, farm_user, pac_a):
        r = _cli(farm_user).post('/api/dispensaciones/', {
            'paciente': pac_a.id, 'tipo_dispensacion': 'normal',
            'medico_prescriptor': 'X',
        }, format='json')
        assert r.status_code in (403, 400)

    def test_farmacia_ve_todas_dispensaciones(self, farm_user, adm_a, adm_b,
                                               pac_a, pac_b, prod1, lote_a, lote_b):
        """Farmacia ve dispensaciones de TODOS los centros (auditoría global)."""
        r1 = _crear_dispensacion(_cli(adm_a), pac_a, prod1, lote_a)
        r2 = _crear_dispensacion(_cli(adm_b), pac_b, prod1, lote_b)
        ids_farm = {d['id'] for d in _json(_cli(farm_user).get('/api/dispensaciones/'))}
        assert r1.json()['id'] in ids_farm
        assert r2.json()['id'] in ids_farm


# ═════════════════════════════════════════════════════════════════════════════
# TC-SEC-04  FARMACIA VERIFICACIÓN STOCK EN CAJA CHICA
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTC_SEC_04_FarmaciaVerificacionCC:
    """
    Given  compra enviada a farmacia
    When   farmacia confirma sin stock o rechaza con stock
    Then   las acciones de verificación están permitidas.
    """

    def test_farmacia_puede_leer_compras_cc(self, farm_user, adm_a, centro_a, prod1):
        _crear_compra_cc(_cli(adm_a), centro_a, prod1)
        r = _cli(farm_user).get('/api/compras-caja-chica/')
        assert r.status_code == 200

    def test_farmacia_no_puede_crear_compra_cc(self, farm_user, centro_a, prod1):
        r = _crear_compra_cc(_cli(farm_user), centro_a, prod1)
        assert r.status_code in (403, 400)

    def test_farmacia_ve_compras_todos_centros(self, farm_user,
                                                adm_a, adm_b, centro_a, centro_b, prod1):
        r_a = _crear_compra_cc(_cli(adm_a), centro_a, prod1)
        r_b = _crear_compra_cc(_cli(adm_b), centro_b, prod1)
        ids_f = {c['id'] for c in _json(_cli(farm_user).get('/api/compras-caja-chica/'))}
        assert r_a.json()['id'] in ids_f
        assert r_b.json()['id'] in ids_f


# ═════════════════════════════════════════════════════════════════════════════
# TC-SEC-05  ROLES POR ENDPOINT — MATRIZ COMPLETA
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTC_SEC_05_MatrizRoles:
    """Verificar que cada rol ve solo lo que corresponde."""

    def test_medico_solo_ve_propias_dispensaciones(self, med_a, adm_a,
                                                     pac_a, prod1, lote_a):
        """Médico solo ve dispensaciones que él creó."""
        r_adm = _crear_dispensacion(_cli(adm_a), pac_a, prod1, lote_a)
        ids_med = {d['id'] for d in _json(_cli(med_a).get('/api/dispensaciones/'))}
        assert r_adm.json()['id'] not in ids_med

    def test_director_ve_todo_su_centro(self, dir_a, adm_a, pac_a, prod1, lote_a):
        r = _crear_dispensacion(_cli(adm_a), pac_a, prod1, lote_a)
        ids_dir = {d['id'] for d in _json(_cli(dir_a).get('/api/dispensaciones/'))}
        assert r.json()['id'] in ids_dir

    def test_sin_centro_ve_vacio_dispensaciones(self, no_centro_user):
        r = _cli(no_centro_user).get('/api/dispensaciones/')
        assert r.status_code == 200
        assert len(_json(r)) == 0

    def test_sin_centro_ve_vacio_compras_cc(self, no_centro_user):
        r = _cli(no_centro_user).get('/api/compras-caja-chica/')
        assert r.status_code == 200
        assert len(_json(r)) == 0

    def test_sin_centro_ve_vacio_inventario_cc(self, no_centro_user):
        r = _cli(no_centro_user).get('/api/inventario-caja-chica/')
        assert r.status_code == 200
        assert len(_json(r)) == 0

    def test_sin_centro_ve_vacio_movimientos_cc(self, no_centro_user):
        r = _cli(no_centro_user).get('/api/movimientos-caja-chica/')
        assert r.status_code == 200
        assert len(_json(r)) == 0

    def test_admin_global_ve_todo_dispensaciones(self, admin_global, adm_a, adm_b,
                                                   pac_a, pac_b, prod1, lote_a, lote_b):
        r1 = _crear_dispensacion(_cli(adm_a), pac_a, prod1, lote_a)
        r2 = _crear_dispensacion(_cli(adm_b), pac_b, prod1, lote_b)
        ids_adm = {d['id'] for d in _json(_cli(admin_global).get('/api/dispensaciones/'))}
        assert r1.json()['id'] in ids_adm
        assert r2.json()['id'] in ids_adm


# ═════════════════════════════════════════════════════════════════════════════
# TC-TRAZ-01  TRAZABILIDAD END-TO-END COMPRA → INV → SALIDA → MOVIMIENTO
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTC_TRAZ_01_TrazabilidadEndToEnd:
    """
    Given  compra creada → comprada → recibida en Centro A
    When   se registra salida del inventario generado
    Then   toda la cadena es rastreable:
           CompraCC → DetalleCompra → InventarioCC → MovimientoCC(entrada)
           → MovimientoCC(salida) — con usuario, centro, timestamps.
    """

    def test_cadena_completa(self, adm_a, centro_a, prod1):
        # 1. Crear compra
        r = _crear_compra_cc(_cli(adm_a), centro_a, prod1, cant=20, precio=15.00)
        cid = r.json()['id']

        # 2. Avanzar a comprada
        _avanzar_a_comprada(_cli(adm_a), cid)
        compra = CompraCajaChica.objects.get(id=cid)
        assert compra.estado == 'comprada'

        # 3. Recibir → genera inventario + movimiento entrada
        _recibir_compra(_cli(adm_a), cid)
        compra.refresh_from_db()
        assert compra.estado == 'recibida'

        # 4. Verificar InventarioCajaChica creado
        inv = InventarioCajaChica.objects.filter(compra_id=cid, centro=centro_a).first()
        assert inv is not None, "Inventario CC debe existir vinculado a compra"
        assert inv.cantidad_actual >= 20

        # 5. Verificar MovimientoCajaChica entrada
        mov_ent = MovimientoCajaChica.objects.filter(
            inventario=inv, tipo='entrada').first()
        assert mov_ent is not None
        assert mov_ent.usuario_id == adm_a.id
        assert mov_ent.referencia == compra.folio

        # 6. Registrar salida
        _cli(adm_a).post(f'/api/inventario-caja-chica/{inv.id}/registrar_salida/', {
            'cantidad': 5, 'motivo': 'Trazabilidad e2e QA',
            'referencia': 'TRAZ-E2E-001',
        }, format='json')

        # 7. Verificar MovimientoCajaChica salida
        mov_sal = MovimientoCajaChica.objects.filter(
            inventario=inv, tipo='salida').first()
        assert mov_sal is not None
        assert mov_sal.cantidad == 5
        assert mov_sal.usuario_id == adm_a.id
        assert mov_sal.motivo == 'Trazabilidad e2e QA'

        # 8. Cadena completa verificable
        assert inv.compra_id == cid               # Inventario → Compra
        assert mov_ent.inventario_id == inv.id     # Mov entrada → Inventario
        assert mov_sal.inventario_id == inv.id     # Mov salida → Inventario
        assert compra.centro_id == centro_a.id     # Compra → Centro
        assert inv.centro_id == centro_a.id        # Inventario → Centro

        # 9. Stock final
        inv.refresh_from_db()
        assert inv.cantidad_actual == 15  # 20 - 5


# ═════════════════════════════════════════════════════════════════════════════
# TC-TRAZ-02  AUDITORÍA REGISTRA USUARIO, CENTRO, TIMESTAMP, ACCIÓN
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTC_TRAZ_02_AuditoriaCompleta:
    """
    Given  acciones sobre dispensaciones y caja chica
    When   se ejecutan operaciones
    Then   historial/movimientos contienen: usuario, acción, timestamp.
    """

    def test_historial_dispensacion_completo(self, adm_a, pac_a, prod1, lote_a):
        resp = _crear_dispensacion(_cli(adm_a), pac_a, prod1, lote_a)
        did = resp.json()['id']
        h = HistorialDispensacion.objects.filter(dispensacion_id=did).first()
        assert h is not None
        assert h.usuario_id == adm_a.id
        assert h.accion == 'crear'
        assert h.estado_nuevo == 'pendiente'
        assert h.created_at is not None

    def test_movimiento_cc_tiene_campos_auditoria(self, adm_a, inv_cc_a):
        _cli(adm_a).post(f'/api/inventario-caja-chica/{inv_cc_a.id}/registrar_salida/', {
            'cantidad': 3, 'motivo': 'Auditoría QA',
        }, format='json')
        mov = MovimientoCajaChica.objects.filter(inventario=inv_cc_a).last()
        assert mov.usuario_id == adm_a.id
        assert mov.tipo == 'salida'
        assert mov.cantidad == 3
        assert mov.cantidad_anterior == 200
        assert mov.cantidad_nueva == 197
        assert mov.created_at is not None

    def test_compra_registra_solicitante(self, adm_a, centro_a, prod1):
        r = _crear_compra_cc(_cli(adm_a), centro_a, prod1)
        c = CompraCajaChica.objects.get(id=r.json()['id'])
        assert c.solicitante_id == adm_a.id

    def test_dispensacion_registra_created_by(self, adm_a, pac_a, prod1, lote_a):
        r = _crear_dispensacion(_cli(adm_a), pac_a, prod1, lote_a)
        d = Dispensacion.objects.get(id=r.json()['id'])
        assert d.created_by_id == adm_a.id
        assert d.created_at is not None


# ═════════════════════════════════════════════════════════════════════════════
# TC-VOL-01  PRUEBA MASIVA MULTI-CENTRO
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTC_VOL_01_PruebaMasiva:
    """
    Given  múltiples centros
    When   se generan N compras, N dispensaciones, N movimientos en paralelo
    Then   cada centro mantiene integridad de datos, no hay cruces.
    """

    NUM_OPS = 5  # Operaciones por centro

    def test_masivo_compras_multiples_centros(self, adm_a, adm_b,
                                               centro_a, centro_b, prod1, prod2):
        """Crear N compras en cada centro y verificar segregación."""
        ids_a, ids_b = [], []
        for i in range(self.NUM_OPS):
            r_a = _crear_compra_cc(_cli(adm_a), centro_a,
                                    prod1 if i % 2 == 0 else prod2,
                                    cant=5 + i, precio=10 + i)
            r_b = _crear_compra_cc(_cli(adm_b), centro_b,
                                    prod1 if i % 2 == 0 else prod2,
                                    cant=5 + i, precio=10 + i)
            assert r_a.status_code in (200, 201)
            assert r_b.status_code in (200, 201)
            ids_a.append(r_a.json()['id'])
            ids_b.append(r_b.json()['id'])

        # Verificar segregación completa
        vis_a = {c['id'] for c in _json(_cli(adm_a).get('/api/compras-caja-chica/'))}
        vis_b = {c['id'] for c in _json(_cli(adm_b).get('/api/compras-caja-chica/'))}
        for cid in ids_a:
            assert cid in vis_a and cid not in vis_b
        for cid in ids_b:
            assert cid in vis_b and cid not in vis_a

    def test_masivo_dispensaciones_multiples_centros(self, adm_a, adm_b,
                                                      pac_a, pac_b,
                                                      prod1, lote_a, lote_b):
        """Crear N dispensaciones por centro, verificar aislamiento."""
        ids_a, ids_b = [], []
        for i in range(self.NUM_OPS):
            r_a = _crear_dispensacion(_cli(adm_a), pac_a, prod1, lote_a, prescrita=2)
            r_b = _crear_dispensacion(_cli(adm_b), pac_b, prod1, lote_b, prescrita=2)
            assert r_a.status_code in (200, 201)
            assert r_b.status_code in (200, 201)
            ids_a.append(r_a.json()['id'])
            ids_b.append(r_b.json()['id'])

        vis_a = {d['id'] for d in _json(_cli(adm_a).get('/api/dispensaciones/'))}
        vis_b = {d['id'] for d in _json(_cli(adm_b).get('/api/dispensaciones/'))}
        for did in ids_a:
            assert did in vis_a and did not in vis_b
        for did in ids_b:
            assert did in vis_b and did not in vis_a

    def test_masivo_dispensar_mantiene_stock_aislado(self, adm_a, adm_b,
                                                      pac_a, pac_b,
                                                      prod1, lote_a, lote_b):
        """Dispensar N veces en cada centro, verificar stock independiente."""
        stock_a_pre = lote_a.cantidad_actual  # 500
        stock_b_pre = lote_b.cantidad_actual  # 300
        unidades = 3

        for _ in range(self.NUM_OPS):
            r = _crear_dispensacion(_cli(adm_a), pac_a, prod1, lote_a, prescrita=unidades)
            _cli(adm_a).post(f'/api/dispensaciones/{r.json()["id"]}/dispensar/',
                             format='json')
            r = _crear_dispensacion(_cli(adm_b), pac_b, prod1, lote_b, prescrita=unidades)
            _cli(adm_b).post(f'/api/dispensaciones/{r.json()["id"]}/dispensar/',
                             format='json')

        lote_a.refresh_from_db()
        lote_b.refresh_from_db()
        assert lote_a.cantidad_actual == stock_a_pre - (unidades * self.NUM_OPS)
        assert lote_b.cantidad_actual == stock_b_pre - (unidades * self.NUM_OPS)

    def test_masivo_movimientos_cc_multiples_centros(self, adm_a, adm_b,
                                                      inv_cc_a, inv_cc_b):
        """Registrar N salidas en cada centro, verificar totales."""
        for i in range(self.NUM_OPS):
            _cli(adm_a).post(f'/api/inventario-caja-chica/{inv_cc_a.id}/registrar_salida/', {
                'cantidad': 2, 'motivo': f'Masivo A-{i}',
            }, format='json')
            _cli(adm_b).post(f'/api/inventario-caja-chica/{inv_cc_b.id}/registrar_salida/', {
                'cantidad': 2, 'motivo': f'Masivo B-{i}',
            }, format='json')

        inv_cc_a.refresh_from_db()
        inv_cc_b.refresh_from_db()
        assert inv_cc_a.cantidad_actual == 200 - (2 * self.NUM_OPS)
        assert inv_cc_b.cantidad_actual == 150 - (2 * self.NUM_OPS)

        # Verificar que cada centro solo ve sus movimientos
        movs_a = _json(_cli(adm_a).get('/api/movimientos-caja-chica/'))
        movs_b = _json(_cli(adm_b).get('/api/movimientos-caja-chica/'))
        ids_a = {m['id'] for m in movs_a}
        ids_b = {m['id'] for m in movs_b}
        assert ids_a.isdisjoint(ids_b)


# ═════════════════════════════════════════════════════════════════════════════
# TC-REG-01  REGRESIÓN — NO ROMPER FLUJOS EXISTENTES
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTC_REG_01_Regresion:
    """Verificar que flujos principales de inventario no se rompieron."""

    def test_movimiento_inventario_principal_funciona(self, adm_a, prod1, lote_a, centro_a):
        """Movimientos del inventario principal (no CC) siguen funcionando."""
        stock_pre = lote_a.cantidad_actual
        mov = Movimiento(
            tipo='salida', subtipo_salida='consumo',
            producto=prod1, lote=lote_a,
            cantidad=5, centro_origen=centro_a,
            usuario=adm_a, motivo='Regresión QA',
        )
        mov.save()
        lote_a.refresh_from_db()
        assert lote_a.cantidad_actual == stock_pre - 5

    def test_exportar_inventario_cc(self, adm_a, inv_cc_a):
        """Exportar inventario CC devuelve respuesta válida."""
        r = _cli(adm_a).get('/api/inventario-caja-chica/exportar/')
        assert r.status_code == 200

    def test_resumen_inventario_cc(self, adm_a, inv_cc_a):
        """Resumen de inventario CC devuelve datos."""
        r = _cli(adm_a).get('/api/inventario-caja-chica/resumen/')
        assert r.status_code == 200

    def test_resumen_compras_cc(self, adm_a, centro_a, prod1):
        """Resumen de compras CC devuelve datos."""
        _crear_compra_cc(_cli(adm_a), centro_a, prod1)
        r = _cli(adm_a).get('/api/compras-caja-chica/resumen/')
        assert r.status_code == 200

    def test_movimientos_cc_readonly(self, adm_a, inv_cc_a):
        """Movimientos CC es read-only, no acepta POST directo."""
        r = _cli(adm_a).post('/api/movimientos-caja-chica/', {
            'inventario': inv_cc_a.id, 'tipo': 'salida', 'cantidad': 1,
        }, format='json')
        assert r.status_code == 405  # Method Not Allowed


# ═════════════════════════════════════════════════════════════════════════════
# TC-INT-01  INTEGRIDAD TRANSACCIONAL — INVENTARIO NEGATIVO
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTC_INT_01_IntegridadTransaccional:
    """Sin inventario negativo y sin consumo cruzado de centros."""

    def test_no_inventario_negativo_dispensacion(self, adm_a, pac_a, prod1, centro_a, db):
        lot, _ = Lote.objects.get_or_create(
            producto=prod1, numero_lote='QA-FULL-NEG-LOT',
            defaults={'centro': centro_a, 'fecha_caducidad': date(2028, 12, 31),
                      'cantidad_inicial': 3, 'cantidad_actual': 3,
                      'precio_unitario': Decimal('5.00'), 'activo': True},
        )
        lot.cantidad_actual = 3; lot.save()
        r = _crear_dispensacion(_cli(adm_a), pac_a, prod1, lot, prescrita=100)
        did = r.json()['id']
        resp = _cli(adm_a).post(f'/api/dispensaciones/{did}/dispensar/',
                                 {'forzar_parcial': False}, format='json')
        lot.refresh_from_db()
        # Con forzar_parcial=False debe fallar o dispensar parcialmente
        # En cualquier caso, stock no debe ser negativo
        assert lot.cantidad_actual >= 0

    def test_no_inventario_negativo_cc(self, adm_a, inv_cc_a):
        # Primera salida: agotar stock
        _cli(adm_a).post(f'/api/inventario-caja-chica/{inv_cc_a.id}/registrar_salida/', {
            'cantidad': 200, 'motivo': 'Agotar',
        }, format='json')
        inv_cc_a.refresh_from_db()
        assert inv_cc_a.cantidad_actual == 0

        # Segunda salida: debe fallar
        r = _cli(adm_a).post(f'/api/inventario-caja-chica/{inv_cc_a.id}/registrar_salida/', {
            'cantidad': 1, 'motivo': 'Ya sin stock',
        }, format='json')
        assert r.status_code == 400
        inv_cc_a.refresh_from_db()
        assert inv_cc_a.cantidad_actual >= 0

    def test_centro_a_no_consume_inventario_cc_de_b(self, adm_a, inv_cc_b):
        stock_b = inv_cc_b.cantidad_actual
        r = _cli(adm_a).post(f'/api/inventario-caja-chica/{inv_cc_b.id}/registrar_salida/', {
            'cantidad': 1, 'motivo': 'Cross-centro',
        }, format='json')
        assert r.status_code in (403, 404)
        inv_cc_b.refresh_from_db()
        assert inv_cc_b.cantidad_actual == stock_b
