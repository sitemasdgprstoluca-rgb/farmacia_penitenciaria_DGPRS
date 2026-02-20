# -*- coding: utf-8 -*-
"""
Tests de regresión para la regla CCG (Contrato Global) — cobertura completa.

Requisito de negocio:
    Para cualquier combinación (producto, numero_contrato), la suma de
    cantidad_inicial de todos los lotes NO puede exceder cantidad_contrato_global.

Cubre:
    A) Casos normales (crear/mover dentro del límite)
    B) Separación por contrato (límites independientes)
    C) Update / PATCH (cantidad_inicial inmutable)
    D) Importación masiva Excel (hard-block pre-creación)
    E) Concurrencia (race condition con SELECT FOR UPDATE)
    F) ccg=NULL (no aplica bloqueo)

Ejecutar:
    cd backend && python -m pytest tests/test_ccg_hard_block.py -v
"""
import pytest
import threading
from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework import serializers as drf_serializers


# ─── helpers ────────────────────────────────────────────────────────────────

def _make_producto(clave, nombre='Test CCG'):
    from core.models import Producto
    obj, _ = Producto.objects.get_or_create(
        clave=clave,
        defaults={
            'nombre': nombre,
            'unidad_medida': 'TABLETA',
            'categoria': 'medicamento',
            'activo': True,
        }
    )
    return obj


def _make_lote(producto, numero_lote, cantidad_inicial, numero_contrato=None,
               cantidad_contrato_global=None, cantidad_contrato=None, activo=True):
    from core.models import Lote
    return Lote.objects.create(
        producto=producto,
        numero_lote=numero_lote,
        cantidad_inicial=cantidad_inicial,
        cantidad_actual=cantidad_inicial,
        fecha_caducidad=date(2030, 12, 31),
        precio_unitario=Decimal('1.00'),
        numero_contrato=numero_contrato,
        cantidad_contrato_global=cantidad_contrato_global,
        cantidad_contrato=cantidad_contrato,
        activo=activo,
    )


def _make_admin(username='admin_ccg_test'):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        return User.objects.create_superuser(
            username=username, email=f'{username}@test.com', password='test123'
        )


# ============================================================================
# A) CASOS NORMALES
# ============================================================================

@pytest.mark.django_db
def test_a1_crear_lote_dentro_del_limite():
    """CCG=100, crear lote cantidad_inicial=60 → OK."""
    from core.serializers import LoteSerializer
    prod = _make_producto('CCG-A1')
    data = {
        'numero_lote': 'LA1-001',
        'producto': prod.pk,
        'cantidad_inicial': 60,
        'fecha_caducidad': '2030-12-31',
        'precio_unitario': '1.00',
        'numero_contrato': 'CONT-A1',
        'centro': None,
        'cantidad_contrato_global': 100,
    }
    ser = LoteSerializer(data=data)
    assert ser.is_valid(), ser.errors


@pytest.mark.django_db
def test_a2_crear_lote_exactamente_en_el_limite():
    """CCG=100, existente=0, nuevo=100 → OK (exactamente en el límite)."""
    from core.serializers import LoteSerializer
    prod = _make_producto('CCG-A2')
    data = {
        'numero_lote': 'LA2-001',
        'producto': prod.pk,
        'cantidad_inicial': 100,
        'fecha_caducidad': '2030-12-31',
        'precio_unitario': '1.00',
        'numero_contrato': 'CONT-A2',
        'centro': None,
        'cantidad_contrato_global': 100,
    }
    ser = LoteSerializer(data=data)
    assert ser.is_valid(), ser.errors


@pytest.mark.django_db
def test_a3_crear_lote_excede_limite_es_rechazado():
    """CCG=100, existente=90, nuevo=15 → FALLO (total=105)."""
    prod = _make_producto('CCG-A3')
    _make_lote(prod, 'LA3-EXIST', 90, 'CONT-A3', 100)
    from core.serializers import LoteSerializer
    data = {
        'numero_lote': 'LA3-NUEVO',
        'producto': prod.pk,
        'cantidad_inicial': 15,
        'fecha_caducidad': '2030-12-31',
        'precio_unitario': '1.00',
        'numero_contrato': 'CONT-A3',
        'centro': None,
        'cantidad_contrato_global': 100,
    }
    ser = LoteSerializer(data=data)
    assert not ser.is_valid()
    assert 'cantidad_inicial' in str(ser.errors)


@pytest.mark.django_db
def test_a4_movimiento_entrada_excede_ccg_bloqueado():
    """Entrada vía movimiento que excedería CCG → ValidationError."""
    prod = _make_producto('CCG-A4')
    lote = _make_lote(prod, 'LA4-001', 90, 'CONT-A4', 100)
    admin = _make_admin('admin_a4')
    from inventario.views.base import registrar_movimiento_stock
    with pytest.raises(drf_serializers.ValidationError) as exc:
        registrar_movimiento_stock(
            lote=lote, tipo='entrada', cantidad=15,
            usuario=admin, centro=None
        )
    assert 'CONTRATO GLOBAL' in str(exc.value.detail)


@pytest.mark.django_db
def test_a5_movimiento_entrada_exactamente_en_limite():
    """Entrada vía movimiento que llega exactamente al CCG → OK."""
    prod = _make_producto('CCG-A5')
    lote = _make_lote(prod, 'LA5-001', 90, 'CONT-A5', 100)
    admin = _make_admin('admin_a5')
    from inventario.views.base import registrar_movimiento_stock
    mov = registrar_movimiento_stock(
        lote=lote, tipo='entrada', cantidad=10,
        usuario=admin, centro=None
    )
    lote.refresh_from_db()
    assert lote.cantidad_inicial == 100


# ============================================================================
# B) SEPARACIÓN POR CONTRATO
# ============================================================================

@pytest.mark.django_db
def test_b1_contratos_independientes():
    """Mismo producto, contratos distintos → sumatorias independientes."""
    prod = _make_producto('CCG-B1')
    _make_lote(prod, 'LB1-X', 90, 'CONT-X', 100)
    # Contrato Y con su propio CCG=50, no afectado por CONT-X
    from core.serializers import LoteSerializer
    data = {
        'numero_lote': 'LB1-Y',
        'producto': prod.pk,
        'cantidad_inicial': 50,
        'fecha_caducidad': '2030-12-31',
        'precio_unitario': '1.00',
        'numero_contrato': 'CONT-Y',
        'centro': None,
        'cantidad_contrato_global': 50,
    }
    ser = LoteSerializer(data=data)
    assert ser.is_valid(), ser.errors


@pytest.mark.django_db
def test_b2_productos_distintos_independientes():
    """Contratos del mismo número pero productos distintos → independientes."""
    prod1 = _make_producto('CCG-B2A')
    prod2 = _make_producto('CCG-B2B')
    _make_lote(prod1, 'LB2-P1', 95, 'CONT-SHARED', 100)
    # Producto 2 bajo el mismo numero_contrato: SUM independiente
    from core.serializers import LoteSerializer
    data = {
        'numero_lote': 'LB2-P2',
        'producto': prod2.pk,
        'cantidad_inicial': 95,
        'fecha_caducidad': '2030-12-31',
        'precio_unitario': '1.00',
        'numero_contrato': 'CONT-SHARED',
        'centro': None,
        'cantidad_contrato_global': 100,
    }
    ser = LoteSerializer(data=data)
    assert ser.is_valid(), ser.errors


# ============================================================================
# C) UPDATE — cantidad_inicial inmutable
# ============================================================================

@pytest.mark.django_db
def test_c1_patch_cantidad_inicial_rechazado():
    """PATCH con cantidad_inicial diferente → ValidationError."""
    from core.serializers import LoteSerializer
    prod = _make_producto('CCG-C1')
    lote = _make_lote(prod, 'LC1-001', 50, 'CONT-C1', 100)
    data = {'cantidad_inicial': 9999}
    ser = LoteSerializer(instance=lote, data=data, partial=True)
    assert not ser.is_valid()
    assert 'cantidad_inicial' in str(ser.errors)


@pytest.mark.django_db
def test_c2_patch_otro_campo_no_cambia_ccg():
    """PATCH de un campo no relacionado con CCG → OK, cantidad_inicial no cambia."""
    from core.serializers import LoteSerializer
    prod = _make_producto('CCG-C2')
    lote = _make_lote(prod, 'LC2-001', 50, 'CONT-C2', 100)
    data = {'ubicacion': 'Estante B'}
    ser = LoteSerializer(instance=lote, data=data, partial=True)
    assert ser.is_valid(), ser.errors
    ser.save()
    lote.refresh_from_db()
    assert lote.cantidad_inicial == 50


# ============================================================================
# D) IMPORTACIÓN MASIVA
# ============================================================================

@pytest.mark.django_db
def test_d1_excel_import_excede_ccg_rechazado():
    """importar_lotes_desde_excel con cantidad que excedería CCG → ValueError."""
    from core.models import Producto
    prod = _make_producto('CCG-D1')
    _make_lote(prod, 'LD1-EXIST', 90, 'CONT-D1', 100)

    # Simular filas consolidadas que exceden el límite
    from core.utils.excel_importer import _validar_ccg_antes_de_importar
    filas = [{
        'producto_id': prod.pk,
        'numero_contrato': 'CONT-D1',
        'centro': None,
        'cantidad_contrato_global': 100,
        'cantidad_inicial': 15,  # 90 existente + 15 = 105 > 100
    }]
    with pytest.raises(ValueError) as exc:
        _validar_ccg_antes_de_importar(filas, centro=None)
    assert 'contrato global' in str(exc.value).lower()


@pytest.mark.django_db
def test_d2_excel_import_dentro_de_limite():
    """importar con cantidad que cabe exactamente → no lanza."""
    from core.utils.excel_importer import _validar_ccg_antes_de_importar
    prod = _make_producto('CCG-D2')
    _make_lote(prod, 'LD2-EXIST', 90, 'CONT-D2', 100)
    filas = [{
        'producto_id': prod.pk,
        'numero_contrato': 'CONT-D2',
        'centro': None,
        'cantidad_contrato_global': 100,
        'cantidad_inicial': 10,  # exactamente en el límite
    }]
    # No debe lanzar
    _validar_ccg_antes_de_importar(filas, centro=None)


@pytest.mark.django_db
def test_d3_excel_import_sin_ccg_no_bloquea():
    """Filas sin cantidad_contrato_global → no se verifica nada."""
    from core.utils.excel_importer import _validar_ccg_antes_de_importar
    prod = _make_producto('CCG-D3')
    filas = [{
        'producto_id': prod.pk,
        'numero_contrato': 'CONT-D3',
        'centro': None,
        'cantidad_contrato_global': None,   # sin CCG
        'cantidad_inicial': 99999,
    }]
    # No debe lanzar
    _validar_ccg_antes_de_importar(filas, centro=None)


# ============================================================================
# E) CONCURRENCIA
# ============================================================================

@pytest.mark.django_db(transaction=True)
def test_e1_concurrencia_dos_entradas_mismo_contrato():
    """
    Dos threads intentan superar el CCG simultáneamente.
    Solo uno debe pasar; la BD nunca debe quedar excedida.
    """
    prod = _make_producto('CCG-E1')
    # Lote A y lote B comparten contrato CONT-E1, CCG=100
    lote_a = _make_lote(prod, 'LE1-A', 50, 'CONT-E1', 100)
    lote_b = _make_lote(prod, 'LE1-B', 40, 'CONT-E1', 100)
    admin = _make_admin('admin_e1')

    errors = []
    successes = []

    from inventario.views.base import registrar_movimiento_stock

    def intentar_entrada(lote, cantidad):
        try:
            registrar_movimiento_stock(
                lote=lote, tipo='entrada', cantidad=cantidad,
                usuario=admin, centro=None
            )
            successes.append(cantidad)
        except (drf_serializers.ValidationError, Exception) as e:
            errors.append(str(e))

    # Ambos intentan agregar 15 unidades (90+15=105 > 100)
    t1 = threading.Thread(target=intentar_entrada, args=(lote_a, 15))
    t2 = threading.Thread(target=intentar_entrada, args=(lote_b, 15))
    t1.start(); t2.start()
    t1.join(); t2.join()

    from django.db.models import Sum
    from core.models import Lote
    total = Lote.objects.filter(
        producto=prod, numero_contrato='CONT-E1'
    ).aggregate(s=Sum('cantidad_inicial'))['s'] or 0

    assert total <= 100, (
        f'¡Race condition: total={total} excede CCG=100! '
        f'successes={successes}, errors={errors}'
    )
    # Exactamente uno pasa o ninguno (si ambos leen 90+15=105 > 100)
    assert len(successes) <= 1


@pytest.mark.django_db(transaction=True)
def test_e2_concurrencia_crear_lotes_mismo_contrato():
    """
    Dos threads crean lotes simultáneamente bajo el mismo contrato.
    Al menos uno debe fallar si la suma superaría el CCG.
    """
    prod = _make_producto('CCG-E2')
    # Existente: 90
    _make_lote(prod, 'LE2-EXIST', 90, 'CONT-E2', 100)

    from core.serializers import LoteSerializer
    successes = []
    errors = []

    def crear_lote(numero_lote):
        data = {
            'numero_lote': numero_lote,
            'producto': prod.pk,
            'cantidad_inicial': 15,      # 90+15 = 105 > 100
            'fecha_caducidad': '2030-12-31',
            'precio_unitario': '1.00',
            'numero_contrato': 'CONT-E2',
        'centro': None,
            'cantidad_contrato_global': 100,
        }
        ser = LoteSerializer(data=data)
        if ser.is_valid():
            try:
                ser.save()
                successes.append(numero_lote)
            except Exception as e:
                errors.append(str(e))
        else:
            errors.append(str(ser.errors))

    t1 = threading.Thread(target=crear_lote, args=('LE2-T1',))
    t2 = threading.Thread(target=crear_lote, args=('LE2-T2',))
    t1.start(); t2.start()
    t1.join(); t2.join()

    from django.db.models import Sum
    from core.models import Lote
    total = Lote.objects.filter(
        producto=prod, numero_contrato='CONT-E2'
    ).aggregate(s=Sum('cantidad_inicial'))['s'] or 0

    assert total <= 100, (
        f'¡Race condition en CREATE: total={total} excede CCG=100! '
        f'successes={successes}, errors={errors}'
    )


# ============================================================================
# F) ccg=NULL (sin bloqueo)
# ============================================================================

@pytest.mark.django_db
def test_f1_sin_ccg_no_aplica_bloqueo():
    """Lotes sin cantidad_contrato_global → no hay restricción de CCG."""
    prod = _make_producto('CCG-F1')
    # Lote existente SIN ccg
    _make_lote(prod, 'LF1-EXIST', 9999, 'CONT-F1', cantidad_contrato_global=None)
    from core.serializers import LoteSerializer
    data = {
        'numero_lote': 'LF1-NUEVO',
        'producto': prod.pk,
        'cantidad_inicial': 9999,
        'fecha_caducidad': '2030-12-31',
        'precio_unitario': '1.00',
        'numero_contrato': 'CONT-F1',
        'centro': None,
        # sin cantidad_contrato_global
    }
    ser = LoteSerializer(data=data)
    assert ser.is_valid(), ser.errors


@pytest.mark.django_db
def test_f2_movimiento_sin_ccg_no_bloquea():
    """Entrada a lote sin ccg → no bloqueo."""
    prod = _make_producto('CCG-F2')
    lote = _make_lote(prod, 'LF2-001', 100, 'CONT-F2', cantidad_contrato_global=None)
    admin = _make_admin('admin_f2')
    from inventario.views.base import registrar_movimiento_stock
    registrar_movimiento_stock(
        lote=lote, tipo='entrada', cantidad=9999,
        usuario=admin, centro=None
    )
    lote.refresh_from_db()
    assert lote.cantidad_inicial == 10099


# ============================================================================
# G) LOTES INACTIVOS — contabilizan para CCG
# ============================================================================

@pytest.mark.django_db
def test_g1_lote_inactivo_cuenta_para_ccg():
    """
    Un lote inactivo (activo=False) igual consume contrato.
    Intentar crear nuevo lote que supere el límite → FALLO.
    El bug original usaba activo=True excluyendo estos lotes.
    """
    prod = _make_producto('CCG-G1')
    # Lote inactivo que ya consumió 90 unidades del contrato
    _make_lote(prod, 'LG1-INACT', 90, 'CONT-G1', 100, activo=False)
    from core.serializers import LoteSerializer
    data = {
        'numero_lote': 'LG1-NUEVO',
        'producto': prod.pk,
        'cantidad_inicial': 15,  # 90+15 = 105 > 100
        'fecha_caducidad': '2030-12-31',
        'precio_unitario': '1.00',
        'numero_contrato': 'CONT-G1',
        'centro': None,
        'cantidad_contrato_global': 100,
    }
    ser = LoteSerializer(data=data)
    assert not ser.is_valid(), (
        'Bug activo=True regresó: lotes inactivos no contabilizan para CCG'
    )
    assert 'cantidad_inicial' in str(ser.errors)


@pytest.mark.django_db
def test_g2_movimiento_lote_inactivo_cuenta_para_ccg():
    """
    Entrada vía movimiento; existen lotes inactivos que ya consumieron el contrato.
    El hard-block en base.py no usa activo=True → debe bloquear.
    """
    prod = _make_producto('CCG-G2')
    _make_lote(prod, 'LG2-INACT', 90, 'CONT-G2', 100, activo=False)
    lote_act = _make_lote(prod, 'LG2-ACT', 5, 'CONT-G2', 100)
    admin = _make_admin('admin_g2')
    from inventario.views.base import registrar_movimiento_stock
    with pytest.raises(drf_serializers.ValidationError) as exc:
        registrar_movimiento_stock(
            lote=lote_act, tipo='entrada', cantidad=10,  # 90+5+10 = 105 > 100
            usuario=admin, centro=None
        )
    assert 'CONTRATO GLOBAL' in str(exc.value.detail)


# ============================================================================
# H) HERENCIA DE ccg (lote sin ccg en la petición hereda del existente)
# ============================================================================

@pytest.mark.django_db
def test_h1_herencia_ccg():
    """Crear lote sin ccg explícito; se hereda de lotes existentes con mismo contrato."""
    prod = _make_producto('CCG-H1')
    _make_lote(prod, 'LH1-BASE', 95, 'CONT-H1', 100)  # ccg=100 en BD
    from core.serializers import LoteSerializer
    data = {
        'numero_lote': 'LH1-NUEVO',
        'producto': prod.pk,
        'cantidad_inicial': 10,   # 95+10=105 > 100 → debe rechazar
        'fecha_caducidad': '2030-12-31',
        'precio_unitario': '1.00',
        'numero_contrato': 'CONT-H1',
        'centro': None,
        # sin cantidad_contrato_global → lo hereda
    }
    ser = LoteSerializer(data=data)
    assert not ser.is_valid(), 'Herencia de CCG no funciona: debería bloquear'
    assert 'cantidad_inicial' in str(ser.errors)

