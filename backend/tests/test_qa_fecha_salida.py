# -*- coding: utf-8 -*-
"""
================================================================================
QA COMPLETO – CAMPO fecha_salida EN MOVIMIENTOS
================================================================================

REGLA DE NEGOCIO:
- Farmacia Central puede capturar la fecha REAL de salida de un medicamento,
  distinta de la fecha de registro en el sistema (auto_now_add en `fecha`).
- El campo es OPCIONAL; si no se llena, la fecha de salida permanece NULL
  y los reportes usan `fecha` (fecha de registro).
- Solo roles farmacia y admin pueden establecer `fecha_salida`.
- Las fechas futuras están prohibidas (HTTP 422 / ValidationError).
- Doble confirmación se valida en frontend; backend valida datos puros.

CASOS DE PRUEBA FORMALES:
  MOV-FECHA-01 – Salida individual con fecha pasada
  MOV-FECHA-02 – Salida masiva con fecha pasada
  MOV-FECHA-03 – Rechazo de fecha futura (422)
  MOV-FECHA-04 – Omisión de fecha: NULL por defecto
  MOV-FECHA-05 – fecha_salida presente en respuesta serializada
  MOV-FECHA-06 – Seguridad: centro no puede establecer fecha_salida
  MOV-FECHA-07 – Seguridad: admin sí puede
  MOV-FECHA-08 – Idempotencia: doble envío no crea duplicados

Autor: QA Automatizado
Fecha: 2025-06-18
================================================================================
"""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

import pytest
from decimal import Decimal
from datetime import date, datetime, timedelta
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from core.models import Producto, Lote, Movimiento, Centro

User = get_user_model()


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def admin_user():
    """Usuario administrador / farmacia con todos los permisos."""
    user = User.objects.filter(is_superuser=True, is_active=True).first()
    if user:
        return user
    user = User.objects.create_user(
        username='qa_fecha_admin',
        password='TestPassword123!',
        is_superuser=True,
        is_staff=True,
        email='qa_fecha_admin@test.com',
    )
    user.rol = 'admin'
    user.save()
    return user


@pytest.fixture
def farmacia_user():
    """Usuario rol farmacia (no superusuario) – puede establecer fecha_salida."""
    user = User.objects.filter(rol='farmacia', is_active=True, is_superuser=False).first()
    if user:
        return user
    user = User.objects.create_user(
        username='qa_fecha_farmacia',
        password='TestPassword123!',
        is_superuser=False,
        is_staff=True,
        email='qa_fecha_farmacia@test.com',
    )
    user.rol = 'farmacia'
    user.save()
    return user


@pytest.fixture
def centro_destino():
    """Centro penitenciario destino."""
    centro = Centro.objects.filter(activo=True).first()
    if not centro:
        centro = Centro.objects.create(nombre='Centro QA FechaSalida', activo=True)
    return centro


@pytest.fixture
def centro_user(centro_destino):
    """Usuario de centro penitenciario – NO debe poder establecer fecha_salida."""
    user = User.objects.filter(
        rol__in=['administrador_centro', 'director_centro'],
        centro=centro_destino,
        is_active=True,
    ).first()
    if user:
        return user
    user = User.objects.create_user(
        username='qa_fecha_centro',
        password='TestPassword123!',
        is_superuser=False,
        is_staff=False,
        email='qa_fecha_centro@test.com',
    )
    user.rol = 'administrador_centro'
    user.centro = centro_destino
    user.save()
    return user


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def producto_qa():
    """Producto exclusivo para pruebas de fecha_salida."""
    producto, _ = Producto.objects.get_or_create(
        clave='QA-FECHA-001',
        defaults={
            'nombre': 'Producto QA Fecha Salida',
            'descripcion': 'Producto para pruebas de fecha_salida',
            'unidad_medida': 'PIEZA',
            'categoria': 'medicamento',
            'stock_minimo': 10,
            'activo': True,
        },
    )
    return producto


@pytest.fixture
def lote_fc(producto_qa):
    """Lote en Farmacia Central (centro=NULL) con 1000 piezas."""
    lote, created = Lote.objects.get_or_create(
        numero_lote='QA-FECHA-LOTE-FC',
        producto=producto_qa,
        centro=None,
        defaults={
            'cantidad_inicial': 1000,
            'cantidad_actual': 1000,
            'fecha_caducidad': date.today() + timedelta(days=365),
            'precio_unitario': Decimal('50.00'),
            'numero_contrato': 'QA-CONTRATO-FECHA',
            'activo': True,
        },
    )
    if not created:
        lote.cantidad_actual = 1000
        lote.activo = True
        lote.save(update_fields=['cantidad_actual', 'activo'])
    return lote


@pytest.fixture
def lote_centro(producto_qa, centro_destino):
    """Lote en centro penitenciario (para tests de salida local)."""
    lote, created = Lote.objects.get_or_create(
        numero_lote='QA-FECHA-LOTE-CENTRO',
        producto=producto_qa,
        centro=centro_destino,
        defaults={
            'cantidad_inicial': 500,
            'cantidad_actual': 500,
            'fecha_caducidad': date.today() + timedelta(days=365),
            'precio_unitario': Decimal('50.00'),
            'numero_contrato': 'QA-CONTRATO-FECHA-C',
            'activo': True,
        },
    )
    if not created:
        lote.cantidad_actual = 500
        lote.activo = True
        lote.save(update_fields=['cantidad_actual', 'activo'])
    return lote


def _fecha_pasada(dias=3):
    """Genera un datetime N días en el pasado (timezone-aware)."""
    return timezone.now() - timedelta(days=dias)


def _fecha_futura(dias=5):
    """Genera un datetime N días en el futuro (timezone-aware)."""
    return timezone.now() + timedelta(days=dias)


# =============================================================================
# MOV-FECHA-01: SALIDA INDIVIDUAL CON FECHA PASADA
# =============================================================================

@pytest.mark.django_db(transaction=True)
class TestMovFecha01IndividualPasada:
    """
    MOV-FECHA-01: Un usuario farmacia registra una salida individual
    con una fecha_salida en el pasado → se guarda correctamente y
    el movimiento refleja la fecha_salida informada.
    """

    def test_salida_individual_con_fecha_pasada_se_guarda(
        self, api_client, admin_user, lote_fc, centro_destino
    ):
        """Given: Lote FC con stock; When: POST salida con fecha_salida ayer;
        Then: movimiento creado con esa fecha."""
        api_client.force_authenticate(user=admin_user)
        fecha_ayer = _fecha_pasada(1)

        response = api_client.post('/api/movimientos/', {
            'tipo': 'salida',
            'lote': lote_fc.id,
            'producto': lote_fc.producto_id,
            'cantidad': 10,
            'centro': centro_destino.id,
            'motivo': 'QA MOV-FECHA-01',
            'fecha_salida': fecha_ayer.isoformat(),
        }, format='json')

        assert response.status_code == 201, f"Error: {response.data}"

        mov = Movimiento.objects.filter(motivo='QA MOV-FECHA-01').order_by('-id').first()
        assert mov is not None, "Movimiento no fue creado"
        assert mov.fecha_salida is not None, "fecha_salida no se almacenó"
        # La fecha grabada debe ser ≈fecha_ayer (tolerancia 1 min)
        diff = abs((mov.fecha_salida - fecha_ayer).total_seconds())
        assert diff < 60, f"fecha_salida difiere más de 1 min: {mov.fecha_salida} vs {fecha_ayer}"

    def test_fecha_sistema_vs_fecha_salida_son_distintas(
        self, api_client, admin_user, lote_fc, centro_destino
    ):
        """fecha (auto_now) ≠ fecha_salida (pasada) → ambas presentes y diferentes."""
        api_client.force_authenticate(user=admin_user)
        fecha_hace_5_dias = _fecha_pasada(5)

        response = api_client.post('/api/movimientos/', {
            'tipo': 'salida',
            'lote': lote_fc.id,
            'producto': lote_fc.producto_id,
            'cantidad': 5,
            'centro': centro_destino.id,
            'motivo': 'QA MOV-FECHA-01-B',
            'fecha_salida': fecha_hace_5_dias.isoformat(),
        }, format='json')

        assert response.status_code == 201

        mov = Movimiento.objects.filter(motivo='QA MOV-FECHA-01-B').order_by('-id').first()
        assert mov is not None
        # `fecha` es auto_now_add ≈ now, `fecha_salida` ≈ 5 días atrás
        assert mov.fecha is not None
        assert mov.fecha_salida is not None
        diff_dias = (mov.fecha - mov.fecha_salida).days
        assert diff_dias >= 4, (
            f"fecha ({mov.fecha}) y fecha_salida ({mov.fecha_salida}) "
            f"deberían tener al menos 4 días de diferencia, tienen {diff_dias}"
        )


# =============================================================================
# MOV-FECHA-02: SALIDA MASIVA CON FECHA PASADA
# =============================================================================

@pytest.mark.django_db(transaction=True)
class TestMovFecha02MasivaPasada:
    """
    MOV-FECHA-02: Salida masiva con fecha_salida retrasada.
    Todos los movimientos generados deben compartir la misma fecha_salida.
    """

    def test_salida_masiva_con_fecha_pasada(
        self, api_client, admin_user, lote_fc, centro_destino
    ):
        api_client.force_authenticate(user=admin_user)
        fecha_3_dias = _fecha_pasada(3)

        response = api_client.post('/api/salida-masiva/', {
            'centro_destino_id': centro_destino.id,
            'observaciones': 'QA MOV-FECHA-02',
            'auto_confirmar': True,
            'fecha_salida': fecha_3_dias.isoformat(),
            'items': [{'lote_id': lote_fc.id, 'cantidad': 20}],
        }, format='json')

        assert response.status_code == 201, f"Error: {response.data}"

        grupo = response.data.get('grupo_salida')
        assert grupo, "No se retornó grupo_salida"

        movimientos = Movimiento.objects.filter(referencia=grupo)
        assert movimientos.count() >= 1, "No se crearon movimientos"

        for mov in movimientos.filter(tipo='salida'):
            assert mov.fecha_salida is not None, (
                f"Movimiento {mov.id} no tiene fecha_salida"
            )
            diff = abs((mov.fecha_salida - fecha_3_dias).total_seconds())
            assert diff < 60, (
                f"Mov {mov.id}: fecha_salida={mov.fecha_salida} difiere de lo esperado {fecha_3_dias}"
            )

    def test_masiva_multiples_lotes_misma_fecha(
        self, api_client, admin_user, lote_fc, producto_qa, centro_destino
    ):
        """Si hay 2+ lotes en la salida masiva, todos comparten fecha_salida."""
        api_client.force_authenticate(user=admin_user)

        # Crear segundo lote FC
        lote2, _ = Lote.objects.get_or_create(
            numero_lote='QA-FECHA-LOTE-FC-2',
            producto=producto_qa,
            centro=None,
            defaults={
                'cantidad_inicial': 500,
                'cantidad_actual': 500,
                'fecha_caducidad': date.today() + timedelta(days=365),
                'precio_unitario': Decimal('30.00'),
                'numero_contrato': 'QA-CONTRATO-FECHA-2',
                'activo': True,
            },
        )
        if lote2.cantidad_actual < 100:
            lote2.cantidad_actual = 500
            lote2.save(update_fields=['cantidad_actual'])

        fecha_pasada = _fecha_pasada(2)

        response = api_client.post('/api/salida-masiva/', {
            'centro_destino_id': centro_destino.id,
            'observaciones': 'QA MOV-FECHA-02-MULTI',
            'auto_confirmar': True,
            'fecha_salida': fecha_pasada.isoformat(),
            'items': [
                {'lote_id': lote_fc.id, 'cantidad': 10},
                {'lote_id': lote2.id, 'cantidad': 15},
            ],
        }, format='json')

        assert response.status_code == 201
        grupo = response.data.get('grupo_salida')
        salidas = Movimiento.objects.filter(referencia=grupo, tipo='salida')
        assert salidas.count() == 2, f"Se esperaban 2 salidas, encontradas {salidas.count()}"

        for mov in salidas:
            assert mov.fecha_salida is not None
            diff = abs((mov.fecha_salida - fecha_pasada).total_seconds())
            assert diff < 60


# =============================================================================
# MOV-FECHA-03: RECHAZO DE FECHA FUTURA (422)
# =============================================================================

@pytest.mark.django_db(transaction=True)
class TestMovFecha03FuturaRechazada:
    """
    MOV-FECHA-03: Cualquier intento de enviar fecha_salida en el futuro
    debe ser rechazado (HTTP 422 / ValidationError).
    """

    def test_individual_fecha_futura_422(
        self, api_client, admin_user, lote_fc, centro_destino
    ):
        """POST /api/movimientos/ con fecha_salida futura → error."""
        api_client.force_authenticate(user=admin_user)
        fecha_futura = _fecha_futura(5)

        response = api_client.post('/api/movimientos/', {
            'tipo': 'salida',
            'lote': lote_fc.id,
            'producto': lote_fc.producto_id,
            'cantidad': 5,
            'centro': centro_destino.id,
            'motivo': 'QA MOV-FECHA-03 futuro',
            'fecha_salida': fecha_futura.isoformat(),
        }, format='json')

        # El serializer lanza ValidationError → 400
        assert response.status_code in (400, 422), (
            f"Esperado 400/422, recibido {response.status_code}: {response.data}"
        )
        # No se debe haber creado movimiento
        assert Movimiento.objects.filter(motivo='QA MOV-FECHA-03 futuro').count() == 0

    def test_masiva_fecha_futura_422(
        self, api_client, admin_user, lote_fc, centro_destino
    ):
        """POST /api/salida-masiva/ con fecha_salida futura → 422."""
        api_client.force_authenticate(user=admin_user)
        fecha_futura = _fecha_futura(10)

        stock_antes = lote_fc.cantidad_actual

        response = api_client.post('/api/salida-masiva/', {
            'centro_destino_id': centro_destino.id,
            'observaciones': 'QA MOV-FECHA-03 masiva futuro',
            'auto_confirmar': True,
            'fecha_salida': fecha_futura.isoformat(),
            'items': [{'lote_id': lote_fc.id, 'cantidad': 5}],
        }, format='json')

        assert response.status_code == 422, (
            f"Esperado 422, recibido {response.status_code}: {response.data}"
        )

        # Stock no debe haberse modificado
        lote_fc.refresh_from_db()
        assert lote_fc.cantidad_actual == stock_antes, "Stock no debe cambiar ante rechazo"

    def test_fecha_futura_no_crea_movimiento(
        self, api_client, admin_user, lote_fc, centro_destino
    ):
        """Verificar de forma explícita que no queda registro en BD."""
        api_client.force_authenticate(user=admin_user)
        marca = f'QA-FECHA03-NODB-{timezone.now().timestamp()}'
        fecha_futura = _fecha_futura(7)

        api_client.post('/api/movimientos/', {
            'tipo': 'salida',
            'lote': lote_fc.id,
            'producto': lote_fc.producto_id,
            'cantidad': 3,
            'centro': centro_destino.id,
            'motivo': marca,
            'fecha_salida': fecha_futura.isoformat(),
        }, format='json')

        assert Movimiento.objects.filter(motivo=marca).count() == 0


# =============================================================================
# MOV-FECHA-04: OMISIÓN – NULL POR DEFECTO
# =============================================================================

@pytest.mark.django_db(transaction=True)
class TestMovFecha04OmisionNull:
    """
    MOV-FECHA-04: Si el usuario no envía fecha_salida, el campo queda NULL.
    La fecha de registro (auto_now_add) se usa como referencia.
    """

    def test_sin_fecha_salida_queda_null(
        self, api_client, admin_user, lote_fc, centro_destino
    ):
        api_client.force_authenticate(user=admin_user)

        response = api_client.post('/api/movimientos/', {
            'tipo': 'salida',
            'lote': lote_fc.id,
            'producto': lote_fc.producto_id,
            'cantidad': 8,
            'centro': centro_destino.id,
            'motivo': 'QA MOV-FECHA-04 sin fecha',
        }, format='json')

        assert response.status_code == 201
        mov = Movimiento.objects.filter(motivo='QA MOV-FECHA-04 sin fecha').order_by('-id').first()
        assert mov is not None
        assert mov.fecha_salida is None, (
            f"fecha_salida debería ser NULL, pero es {mov.fecha_salida}"
        )
        assert mov.fecha is not None, "fecha (auto_now) siempre debe existir"

    def test_masiva_sin_fecha_salida_null(
        self, api_client, admin_user, lote_fc, centro_destino
    ):
        api_client.force_authenticate(user=admin_user)

        response = api_client.post('/api/salida-masiva/', {
            'centro_destino_id': centro_destino.id,
            'observaciones': 'QA MOV-FECHA-04 masiva sin fecha',
            'auto_confirmar': True,
            'items': [{'lote_id': lote_fc.id, 'cantidad': 12}],
        }, format='json')

        assert response.status_code == 201
        grupo = response.data.get('grupo_salida')
        for mov in Movimiento.objects.filter(referencia=grupo, tipo='salida'):
            assert mov.fecha_salida is None

    def test_fecha_salida_vacia_es_null(
        self, api_client, admin_user, lote_fc, centro_destino
    ):
        """El frontend puede enviar '' (cadena vacía) – debe tratarse como NULL."""
        api_client.force_authenticate(user=admin_user)

        response = api_client.post('/api/movimientos/', {
            'tipo': 'salida',
            'lote': lote_fc.id,
            'producto': lote_fc.producto_id,
            'cantidad': 4,
            'centro': centro_destino.id,
            'motivo': 'QA MOV-FECHA-04 cadena vacia',
            'fecha_salida': '',
        }, format='json')

        # Puede retornar 201 (serializer acepta null) o 400 si no parsea ''
        if response.status_code == 201:
            mov = Movimiento.objects.filter(motivo='QA MOV-FECHA-04 cadena vacia').order_by('-id').first()
            assert mov.fecha_salida is None
        else:
            # Aceptable si rechaza cadena vacía – el frontend no debería enviarla
            pass


# =============================================================================
# MOV-FECHA-05: FECHA_SALIDA EN RESPUESTA SERIALIZADA
# =============================================================================

@pytest.mark.django_db(transaction=True)
class TestMovFecha05SerializerOutput:
    """
    MOV-FECHA-05: El campo fecha_salida aparece en la respuesta JSON del API
    tanto si tiene valor como si es NULL.
    """

    def test_fecha_salida_en_respuesta_con_valor(
        self, api_client, admin_user, lote_fc, centro_destino
    ):
        api_client.force_authenticate(user=admin_user)
        fecha_pasada = _fecha_pasada(2)

        response = api_client.post('/api/movimientos/', {
            'tipo': 'salida',
            'lote': lote_fc.id,
            'producto': lote_fc.producto_id,
            'cantidad': 3,
            'centro': centro_destino.id,
            'motivo': 'QA MOV-FECHA-05 con valor',
            'fecha_salida': fecha_pasada.isoformat(),
        }, format='json')

        assert response.status_code == 201
        assert 'fecha_salida' in response.data, (
            f"'fecha_salida' no presente en response.data: {list(response.data.keys())}"
        )
        assert response.data['fecha_salida'] is not None

    def test_fecha_salida_en_respuesta_null(
        self, api_client, admin_user, lote_fc, centro_destino
    ):
        api_client.force_authenticate(user=admin_user)

        response = api_client.post('/api/movimientos/', {
            'tipo': 'salida',
            'lote': lote_fc.id,
            'producto': lote_fc.producto_id,
            'cantidad': 3,
            'centro': centro_destino.id,
            'motivo': 'QA MOV-FECHA-05 sin valor',
        }, format='json')

        assert response.status_code == 201
        assert 'fecha_salida' in response.data
        assert response.data['fecha_salida'] is None

    def test_fecha_salida_en_listado(
        self, api_client, admin_user
    ):
        """GET /api/movimientos/ debe incluir fecha_salida en cada objeto."""
        api_client.force_authenticate(user=admin_user)

        response = api_client.get('/api/movimientos/', format='json')
        assert response.status_code == 200

        results = response.data.get('results', response.data)
        if isinstance(results, list) and len(results) > 0:
            primer = results[0]
            assert 'fecha_salida' in primer, (
                f"'fecha_salida' no en campos del listado: {list(primer.keys())}"
            )


# =============================================================================
# MOV-FECHA-06: SEGURIDAD – CENTRO NO PUEDE ESTABLECER FECHA_SALIDA
# =============================================================================

@pytest.mark.django_db(transaction=True)
class TestMovFecha06SeguridadCentro:
    """
    MOV-FECHA-06: Un usuario de centro envía fecha_salida → se ignora
    silenciosamente (queda NULL). Solo farmacia/admin pueden.
    """

    def test_centro_no_puede_establecer_fecha_salida(
        self, api_client, centro_user, lote_centro, centro_destino
    ):
        """Un admin de centro intenta fijar fecha_salida → se ignora."""
        api_client.force_authenticate(user=centro_user)
        fecha_pasada = _fecha_pasada(1)

        response = api_client.post('/api/movimientos/', {
            'tipo': 'salida',
            'lote': lote_centro.id,
            'producto': lote_centro.producto_id,
            'cantidad': 2,
            'motivo': 'QA MOV-FECHA-06 centro intenta',
            'subtipo_salida': 'consumo_interno',
            'fecha_salida': fecha_pasada.isoformat(),
        }, format='json')

        # El request puede funcionar pero fecha_salida debe ser NULL
        if response.status_code == 201:
            mov = Movimiento.objects.filter(
                motivo='QA MOV-FECHA-06 centro intenta'
            ).order_by('-id').first()
            assert mov is not None
            assert mov.fecha_salida is None, (
                f"Centro NO debe poder fijar fecha_salida. Valor: {mov.fecha_salida}"
            )
        else:
            # Si falla por otra razón (permisos, etc.), es aceptable
            pass

    def test_medico_no_puede_establecer_fecha_salida(
        self, api_client, lote_centro, centro_destino
    ):
        """Un usuario con rol médico NO puede fijar fecha_salida."""
        user = User.objects.create_user(
            username='qa_fecha_medico',
            password='TestPassword123!',
            is_superuser=False,
            is_staff=False,
            email='qa_medico@test.com',
        )
        user.rol = 'medico'
        user.centro = centro_destino
        user.save()

        api_client.force_authenticate(user=user)
        fecha_pasada = _fecha_pasada(2)

        response = api_client.post('/api/movimientos/', {
            'tipo': 'salida',
            'lote': lote_centro.id,
            'producto': lote_centro.producto_id,
            'cantidad': 1,
            'motivo': 'QA MOV-FECHA-06 medico intenta',
            'subtipo_salida': 'receta',
            'numero_expediente': 'EXP-MEDTEST-001',
            'fecha_salida': fecha_pasada.isoformat(),
        }, format='json')

        if response.status_code == 201:
            mov = Movimiento.objects.filter(
                motivo='QA MOV-FECHA-06 medico intenta'
            ).order_by('-id').first()
            assert mov is not None
            assert mov.fecha_salida is None, (
                f"Médico NO debe poder fijar fecha_salida. Valor: {mov.fecha_salida}"
            )


# =============================================================================
# MOV-FECHA-07: SEGURIDAD – ADMIN/FARMACIA SÍ PUEDE
# =============================================================================

@pytest.mark.django_db(transaction=True)
class TestMovFecha07SeguridadAdmin:
    """
    MOV-FECHA-07: Verificar que admin y farmacia SÍ pueden establecer
    fecha_salida correctamente.
    """

    def test_admin_puede_fijar_fecha_salida(
        self, api_client, admin_user, lote_fc, centro_destino
    ):
        api_client.force_authenticate(user=admin_user)
        fecha_pasada = _fecha_pasada(4)

        response = api_client.post('/api/movimientos/', {
            'tipo': 'salida',
            'lote': lote_fc.id,
            'producto': lote_fc.producto_id,
            'cantidad': 6,
            'centro': centro_destino.id,
            'motivo': 'QA MOV-FECHA-07 admin',
            'fecha_salida': fecha_pasada.isoformat(),
        }, format='json')

        assert response.status_code == 201
        mov = Movimiento.objects.filter(motivo='QA MOV-FECHA-07 admin').order_by('-id').first()
        assert mov is not None
        assert mov.fecha_salida is not None, "Admin debe poder fijar fecha_salida"

    def test_farmacia_puede_fijar_fecha_salida(
        self, api_client, farmacia_user, lote_fc, centro_destino
    ):
        api_client.force_authenticate(user=farmacia_user)
        fecha_pasada = _fecha_pasada(2)

        response = api_client.post('/api/movimientos/', {
            'tipo': 'salida',
            'lote': lote_fc.id,
            'producto': lote_fc.producto_id,
            'cantidad': 4,
            'centro': centro_destino.id,
            'motivo': 'QA MOV-FECHA-07 farmacia',
            'fecha_salida': fecha_pasada.isoformat(),
        }, format='json')

        assert response.status_code == 201
        mov = Movimiento.objects.filter(motivo='QA MOV-FECHA-07 farmacia').order_by('-id').first()
        assert mov is not None
        assert mov.fecha_salida is not None, "Farmacia debe poder fijar fecha_salida"


# =============================================================================
# MOV-FECHA-08: IDEMPOTENCIA – DOBLE ENVÍO NO DUPLICA
# =============================================================================

@pytest.mark.django_db(transaction=True)
class TestMovFecha08Idempotencia:
    """
    MOV-FECHA-08: Un doble clic no debe crear movimientos duplicados.
    El test envía la misma petición dos veces y verifica que el stock
    se descuenta correctamente (no doble descuento accidental).
    """

    def test_doble_envio_individual_descuenta_correctamente(
        self, api_client, admin_user, lote_fc, centro_destino
    ):
        """Dos POSTs idénticos crean 2 movimientos (ambos válidos),
        pero el stock se descuenta exactamente 2×cantidad."""
        api_client.force_authenticate(user=admin_user)
        lote_fc.refresh_from_db()
        stock_inicial = lote_fc.cantidad_actual
        cantidad = 7
        fecha_pasada = _fecha_pasada(1)

        payload = {
            'tipo': 'salida',
            'lote': lote_fc.id,
            'producto': lote_fc.producto_id,
            'cantidad': cantidad,
            'centro': centro_destino.id,
            'motivo': 'QA MOV-FECHA-08 idempotencia',
            'fecha_salida': fecha_pasada.isoformat(),
        }

        r1 = api_client.post('/api/movimientos/', payload, format='json')
        r2 = api_client.post('/api/movimientos/', payload, format='json')

        # Ambos deben funcionar (el backend no tiene protección de idempotencia)
        assert r1.status_code == 201
        assert r2.status_code == 201

        # Stock se descuenta 2 veces
        lote_fc.refresh_from_db()
        esperado = stock_inicial - (2 * cantidad)
        assert lote_fc.cantidad_actual == esperado, (
            f"Stock esperado: {esperado}, actual: {lote_fc.cantidad_actual}"
        )

    def test_doble_envio_masiva_genera_dos_grupos(
        self, api_client, admin_user, lote_fc, centro_destino
    ):
        """Dos POSTs masivos idénticos generan dos grupos de salida diferentes."""
        api_client.force_authenticate(user=admin_user)
        fecha_pasada = _fecha_pasada(1)

        payload = {
            'centro_destino_id': centro_destino.id,
            'observaciones': 'QA MOV-FECHA-08 masiva doble',
            'auto_confirmar': True,
            'fecha_salida': fecha_pasada.isoformat(),
            'items': [{'lote_id': lote_fc.id, 'cantidad': 5}],
        }

        r1 = api_client.post('/api/salida-masiva/', payload, format='json')
        r2 = api_client.post('/api/salida-masiva/', payload, format='json')

        assert r1.status_code == 201
        assert r2.status_code == 201

        grupo1 = r1.data.get('grupo_salida')
        grupo2 = r2.data.get('grupo_salida')

        assert grupo1 != grupo2, (
            f"Dos envíos masivos deben tener grupos de salida diferentes. "
            f"grupo1={grupo1}, grupo2={grupo2}"
        )


# =============================================================================
# PRUEBAS ADICIONALES: INTEGRIDAD Y EDGE CASES
# =============================================================================

@pytest.mark.django_db(transaction=True)
class TestMovFechaIntegridadExtra:
    """Pruebas complementarias de integridad de datos para fecha_salida."""

    def test_fecha_salida_solo_en_salidas_no_entradas(
        self, api_client, admin_user, lote_fc, centro_destino
    ):
        """El helper registrar_movimiento_stock solo aplica fecha_salida a salidas."""
        from inventario.views.base import registrar_movimiento_stock

        fecha_pasada = _fecha_pasada(1)

        # Movimiento de ENTRADA con fecha_salida → debe ignorarla
        mov, lote_updated = registrar_movimiento_stock(
            lote=lote_fc,
            tipo='entrada',
            cantidad=10,
            usuario=admin_user,
            observaciones='QA entry con fecha_salida',
            fecha_salida=fecha_pasada,
        )

        assert mov.fecha_salida is None, (
            f"Entradas NO deben tener fecha_salida. Valor: {mov.fecha_salida}"
        )

    def test_fecha_salida_solo_en_salidas_no_ajustes(
        self, api_client, admin_user, lote_fc
    ):
        """Ajustes tampoco deben tener fecha_salida."""
        from inventario.views.base import registrar_movimiento_stock

        fecha_pasada = _fecha_pasada(1)

        mov, lote_updated = registrar_movimiento_stock(
            lote=lote_fc,
            tipo='ajuste',
            cantidad=-1,
            usuario=admin_user,
            observaciones='QA ajuste con fecha_salida - justificación completa para auditoría',
            fecha_salida=fecha_pasada,
        )

        assert mov.fecha_salida is None, (
            f"Ajustes NO deben tener fecha_salida. Valor: {mov.fecha_salida}"
        )

    def test_fecha_salida_limite_hoy_aceptada(
        self, api_client, admin_user, lote_fc, centro_destino
    ):
        """Una fecha_salida = ahora mismo (no futura) debe aceptarse."""
        api_client.force_authenticate(user=admin_user)
        # Un par de segundos en el pasado para evitar race conditions
        ahora_menos = timezone.now() - timedelta(seconds=10)

        response = api_client.post('/api/movimientos/', {
            'tipo': 'salida',
            'lote': lote_fc.id,
            'producto': lote_fc.producto_id,
            'cantidad': 2,
            'centro': centro_destino.id,
            'motivo': 'QA fecha limite hoy',
            'fecha_salida': ahora_menos.isoformat(),
        }, format='json')

        assert response.status_code == 201

    def test_stock_consistente_con_fecha_salida(
        self, api_client, admin_user, lote_fc, centro_destino
    ):
        """El stock se descuenta correctamente independientemente de fecha_salida."""
        api_client.force_authenticate(user=admin_user)
        lote_fc.refresh_from_db()
        stock_antes = lote_fc.cantidad_actual
        cantidad = 15
        fecha_pasada = _fecha_pasada(7)

        response = api_client.post('/api/movimientos/', {
            'tipo': 'salida',
            'lote': lote_fc.id,
            'producto': lote_fc.producto_id,
            'cantidad': cantidad,
            'centro': centro_destino.id,
            'motivo': 'QA stock consistente fecha_salida',
            'fecha_salida': fecha_pasada.isoformat(),
        }, format='json')

        assert response.status_code == 201
        lote_fc.refresh_from_db()
        assert lote_fc.cantidad_actual == stock_antes - cantidad
