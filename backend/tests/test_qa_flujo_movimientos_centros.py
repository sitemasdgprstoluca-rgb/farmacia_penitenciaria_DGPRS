# -*- coding: utf-8 -*-
"""
================================================================================
QA COMPLETO - FLUJO DE MOVIMIENTOS HACIA CENTROS PENITENCIARIOS
================================================================================

REGLA DE NEGOCIO ACTUALIZADA:
- La farmacia central descuenta inventario de inmediato
- El centro recibe stock en custodia y gestiona la salida manual posteriormente
- NO existe dispensación automática al recibir mercancía

ESCENARIOS CUBIERTOS:
- A: Salida individual a centro
- B: Salida masiva a centro  
- C: Salida manual del centro
- D: Validación de no doble descuento
- E: Cancelación/reverso de movimientos

Autor: QA Automatizado
Fecha: 2026-02-10
================================================================================
"""
import os
import sys

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.db import transaction
from django.db.models import Sum
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from core.models import Producto, Lote, Movimiento, Centro

User = get_user_model()


# =============================================================================
# FIXTURES Y UTILIDADES
# =============================================================================

@pytest.fixture
def admin_user():
    """Usuario administrador/farmacia para pruebas."""
    # Buscar usuario admin existente primero
    user = User.objects.filter(is_superuser=True, is_active=True).first()
    if user:
        return user
    
    # Si no existe, crear uno con password
    user = User.objects.create_user(
        username='qa_admin_test',
        password='TestPassword123!',
        is_superuser=True,
        is_staff=True,
        email='qa_admin@test.com'
    )
    user.rol = 'admin'
    user.save()
    return user


@pytest.fixture
def centro_user(centro_destino):
    """Usuario de centro para pruebas de salida manual."""
    # Buscar usuario de centro existente primero
    user = User.objects.filter(
        rol__in=['administrador_centro', 'director_centro'],
        centro=centro_destino,
        is_active=True
    ).first()
    if user:
        return user
    
    # Si no existe, crear uno con password
    user = User.objects.create_user(
        username='qa_centro_test',
        password='TestPassword123!',
        is_superuser=False,
        is_staff=False,
        email='qa_centro@test.com'
    )
    user.rol = 'administrador_centro'
    user.centro = centro_destino
    user.save()
    return user


@pytest.fixture
def api_client():
    """Cliente API para pruebas."""
    return APIClient()


@pytest.fixture
def producto_qa():
    """Producto exclusivo para pruebas QA."""
    producto, _ = Producto.objects.get_or_create(
        clave='QA-TEST-001',
        defaults={
            'nombre': 'Producto QA Test Movimientos',
            'descripcion': 'Producto exclusivo para pruebas QA de movimientos',
            'unidad_medida': 'PIEZA',
            'categoria': 'medicamento',
            'stock_minimo': 10,
            'activo': True
        }
    )
    return producto


@pytest.fixture
def lote_farmacia_central(producto_qa):
    """Lote en Farmacia Central (centro=NULL) con stock suficiente."""
    lote, created = Lote.objects.get_or_create(
        numero_lote='QA-LOTE-FC-001',
        producto=producto_qa,
        centro=None,  # Farmacia Central
        defaults={
            'cantidad_inicial': 1000,
            'cantidad_actual': 1000,
            'fecha_caducidad': date.today() + timedelta(days=365),
            'precio_unitario': Decimal('100.00'),
            'numero_contrato': 'QA-CONTRATO-001',
            'activo': True
        }
    )
    if not created:
        # Resetear stock para pruebas limpias
        lote.cantidad_actual = 1000
        lote.activo = True
        lote.save(update_fields=['cantidad_actual', 'activo'])
    return lote


@pytest.fixture
def centro_destino():
    """Centro destino para transferencias."""
    centro = Centro.objects.filter(activo=True).first()
    if not centro:
        centro = Centro.objects.create(
            nombre='Centro QA Test',
            activo=True
        )
    return centro


@pytest.fixture
def centro_destino_2():
    """Segundo centro para pruebas masivas."""
    centros = Centro.objects.filter(activo=True)[:2]
    if centros.count() >= 2:
        return centros[1]
    return Centro.objects.create(
        nombre='Centro QA Test 2',
        activo=True
    )


def limpiar_lotes_centro(producto, centro):
    """Elimina lotes de prueba en un centro específico."""
    Lote.objects.filter(
        producto=producto,
        centro=centro,
        numero_lote__startswith='QA-'
    ).delete()


def obtener_stock_centro(producto, centro):
    """Obtiene el stock total de un producto en un centro."""
    return Lote.objects.filter(
        producto=producto,
        centro=centro,
        activo=True
    ).aggregate(total=Sum('cantidad_actual'))['total'] or 0


def contar_movimientos_salida_centro(lote_centro):
    """Cuenta movimientos de salida registrados para un lote de centro."""
    return Movimiento.objects.filter(
        lote=lote_centro,
        tipo='salida'
    ).count()


# =============================================================================
# SECCIÓN 1: QA DE NEGOCIO - VALIDACIÓN DE REGLAS
# =============================================================================

@pytest.mark.django_db(transaction=True)
class TestReglasNegocio:
    """
    Validar que el nuevo flujo de movimientos hacia centros cumpla con 
    la regla de negocio actualizada.
    """

    def test_regla_001_farmacia_central_descuenta_inmediato(
        self, api_client, admin_user, lote_farmacia_central, centro_destino
    ):
        """
        REGLA: El inventario SÍ se descuenta inmediatamente de la farmacia central.
        """
        api_client.force_authenticate(user=admin_user)
        stock_inicial_fc = lote_farmacia_central.cantidad_actual
        cantidad_a_enviar = 50

        # Ejecutar salida masiva (auto_confirmar=True por defecto)
        response = api_client.post('/api/salida-masiva/', {
            'centro_destino_id': centro_destino.id,
            'observaciones': 'QA Test - Regla 001',
            'auto_confirmar': True,
            'items': [{'lote_id': lote_farmacia_central.id, 'cantidad': cantidad_a_enviar}]
        }, format='json')

        assert response.status_code == 201, f"Error: {response.data}"
        
        # Verificar descuento inmediato en farmacia central
        lote_farmacia_central.refresh_from_db()
        stock_final_fc = lote_farmacia_central.cantidad_actual
        
        assert stock_final_fc == stock_inicial_fc - cantidad_a_enviar, \
            f"Farmacia Central debió descontar {cantidad_a_enviar}. " \
            f"Inicial: {stock_inicial_fc}, Final: {stock_final_fc}"

    def test_regla_002_centro_no_descuenta_automatico(
        self, api_client, admin_user, lote_farmacia_central, centro_destino, producto_qa
    ):
        """
        REGLA: El inventario NO se descuenta automáticamente en el centro.
        El centro mantiene inventario disponible hasta acción manual.
        """
        api_client.force_authenticate(user=admin_user)
        cantidad_a_enviar = 30

        # Limpiar lotes previos del centro
        limpiar_lotes_centro(producto_qa, centro_destino)

        # Ejecutar transferencia
        response = api_client.post('/api/salida-masiva/', {
            'centro_destino_id': centro_destino.id,
            'observaciones': 'QA Test - Regla 002',
            'auto_confirmar': True,
            'items': [{'lote_id': lote_farmacia_central.id, 'cantidad': cantidad_a_enviar}]
        }, format='json')

        assert response.status_code == 201

        # Verificar que el centro recibió el stock COMPLETO (sin descuento)
        stock_centro = obtener_stock_centro(producto_qa, centro_destino)
        
        assert stock_centro == cantidad_a_enviar, \
            f"Centro debe tener {cantidad_a_enviar} disponibles. Tiene: {stock_centro}"

    def test_regla_003_no_movimiento_salida_automatico_centro(
        self, api_client, admin_user, lote_farmacia_central, centro_destino, producto_qa
    ):
        """
        REGLA: No debe registrarse salida automática en el centro.
        Solo debe existir movimiento de ENTRADA, no de SALIDA automática.
        """
        api_client.force_authenticate(user=admin_user)
        cantidad_a_enviar = 25

        # Obtener grupo de salida para rastrear
        response = api_client.post('/api/salida-masiva/', {
            'centro_destino_id': centro_destino.id,
            'observaciones': 'QA Test - Regla 003',
            'auto_confirmar': True,
            'items': [{'lote_id': lote_farmacia_central.id, 'cantidad': cantidad_a_enviar}]
        }, format='json')

        assert response.status_code == 201
        grupo_salida = response.data.get('grupo_salida')

        # Buscar movimientos de este grupo
        movimientos = Movimiento.objects.filter(
            referencia=grupo_salida
        ).values_list('tipo', flat=True)

        tipos = list(movimientos)
        
        # Debe haber exactamente: 1 salida (de FC) + 1 entrada (al centro)
        assert tipos.count('salida') == 1, \
            f"Debe haber exactamente 1 salida (de FC). Encontradas: {tipos.count('salida')}"
        assert tipos.count('entrada') == 1, \
            f"Debe haber exactamente 1 entrada (al centro). Encontradas: {tipos.count('entrada')}"
        
        # NO debe haber movimientos de dispensación automática
        mov_dispensacion = Movimiento.objects.filter(
            referencia=grupo_salida,
            subtipo_salida='dispensacion'
        ).count()
        
        assert mov_dispensacion == 0, \
            f"NO debe existir dispensación automática. Encontradas: {mov_dispensacion}"

    def test_regla_004_trazabilidad_completa(
        self, api_client, admin_user, lote_farmacia_central, centro_destino
    ):
        """
        REGLA: Debe existir trazabilidad clara entre:
        - Movimiento de salida desde farmacia central
        - Inventario asignado al centro
        """
        api_client.force_authenticate(user=admin_user)
        cantidad = 40

        response = api_client.post('/api/salida-masiva/', {
            'centro_destino_id': centro_destino.id,
            'observaciones': 'QA Test - Trazabilidad',
            'auto_confirmar': True,
            'items': [{'lote_id': lote_farmacia_central.id, 'cantidad': cantidad}]
        }, format='json')

        assert response.status_code == 201
        grupo_salida = response.data.get('grupo_salida')

        # Verificar movimiento de SALIDA desde FC
        mov_salida = Movimiento.objects.filter(
            referencia=grupo_salida,
            tipo='salida',
            centro_origen__isnull=True  # Farmacia Central
        ).first()

        assert mov_salida is not None, "Debe existir movimiento de salida desde FC"
        assert mov_salida.centro_destino == centro_destino, "Destino debe ser el centro"
        assert mov_salida.cantidad == cantidad, "Cantidad debe coincidir"

        # Verificar movimiento de ENTRADA al centro
        mov_entrada = Movimiento.objects.filter(
            referencia=grupo_salida,
            tipo='entrada',
            centro_destino=centro_destino
        ).first()

        assert mov_entrada is not None, "Debe existir movimiento de entrada al centro"
        assert mov_entrada.cantidad == cantidad, "Cantidad de entrada debe coincidir"

        # Verificar que ambos movimientos comparten referencia (trazabilidad)
        assert mov_salida.referencia == mov_entrada.referencia, \
            "Ambos movimientos deben compartir la misma referencia"


# =============================================================================
# SECCIÓN 2: QA FUNCIONAL - PRUEBAS DE ACEPTACIÓN (Given/When/Then)
# =============================================================================

@pytest.mark.django_db(transaction=True)
class TestEscenario1SalidaIndividual:
    """
    Escenario 1: Salida individual hacia centro
    
    Given un inventario disponible en farmacia central
    And un centro habilitado para recibir inventario
    When se realiza una salida individual hacia el centro
    Then el inventario de farmacia central debe descontarse inmediatamente
    And el inventario del centro debe incrementarse como disponible
    And no debe registrarse salida automática en el centro
    """

    def test_escenario_1_salida_individual(
        self, api_client, admin_user, lote_farmacia_central, centro_destino, producto_qa
    ):
        """Test completo del Escenario 1."""
        # GIVEN
        api_client.force_authenticate(user=admin_user)
        stock_fc_inicial = lote_farmacia_central.cantidad_actual
        limpiar_lotes_centro(producto_qa, centro_destino)
        stock_centro_inicial = obtener_stock_centro(producto_qa, centro_destino)
        cantidad = 50
        
        assert stock_fc_inicial >= cantidad, "Debe haber stock suficiente en FC"
        assert stock_centro_inicial == 0, "Centro debe iniciar sin stock del producto"

        # WHEN - Salida individual (usando salida_masiva con 1 item)
        response = api_client.post('/api/salida-masiva/', {
            'centro_destino_id': centro_destino.id,
            'observaciones': 'Escenario 1 - Salida individual',
            'auto_confirmar': True,
            'items': [{'lote_id': lote_farmacia_central.id, 'cantidad': cantidad}]
        }, format='json')

        assert response.status_code == 201

        # THEN - Verificaciones
        lote_farmacia_central.refresh_from_db()
        stock_fc_final = lote_farmacia_central.cantidad_actual
        stock_centro_final = obtener_stock_centro(producto_qa, centro_destino)
        grupo = response.data.get('grupo_salida')

        # FC descontado inmediatamente
        assert stock_fc_final == stock_fc_inicial - cantidad, \
            f"FC debe descontarse. Esperado: {stock_fc_inicial - cantidad}, Actual: {stock_fc_final}"

        # Centro incrementado como disponible
        assert stock_centro_final == cantidad, \
            f"Centro debe tener {cantidad} disponible. Actual: {stock_centro_final}"

        # No salida automática en centro
        salidas_auto = Movimiento.objects.filter(
            referencia=grupo,
            tipo='salida',
            lote__centro=centro_destino
        ).count()
        
        assert salidas_auto == 0, \
            f"No debe haber salidas automáticas en centro. Encontradas: {salidas_auto}"


@pytest.mark.django_db(transaction=True)
class TestEscenario2SalidaMasiva:
    """
    Escenario 2: Salida masiva hacia centros
    
    Given un inventario suficiente en farmacia central
    When se ejecuta una salida masiva hacia uno o varios centros
    Then el inventario de farmacia central debe descontarse correctamente
    And cada centro debe recibir inventario disponible
    And no debe existir descuento automático en ningún centro
    """

    def test_escenario_2_salida_masiva_multiples_items(
        self, api_client, admin_user, lote_farmacia_central, centro_destino, producto_qa
    ):
        """Salida masiva con múltiples items al mismo centro."""
        api_client.force_authenticate(user=admin_user)
        
        # Crear segundo lote en FC
        lote_2, _ = Lote.objects.get_or_create(
            numero_lote='QA-LOTE-FC-002',
            producto=producto_qa,
            centro=None,
            defaults={
                'cantidad_inicial': 500,
                'cantidad_actual': 500,
                'fecha_caducidad': date.today() + timedelta(days=365),
                'precio_unitario': Decimal('150.00'),
                'activo': True
            }
        )
        if lote_2.cantidad_actual < 100:
            lote_2.cantidad_actual = 500
            lote_2.save()

        stock_fc_1_inicial = lote_farmacia_central.cantidad_actual
        stock_fc_2_inicial = lote_2.cantidad_actual
        
        cantidad_1 = 30
        cantidad_2 = 20

        limpiar_lotes_centro(producto_qa, centro_destino)

        # WHEN
        response = api_client.post('/api/salida-masiva/', {
            'centro_destino_id': centro_destino.id,
            'observaciones': 'Escenario 2 - Masiva múltiples items',
            'auto_confirmar': True,
            'items': [
                {'lote_id': lote_farmacia_central.id, 'cantidad': cantidad_1},
                {'lote_id': lote_2.id, 'cantidad': cantidad_2}
            ]
        }, format='json')

        assert response.status_code == 201

        # THEN
        lote_farmacia_central.refresh_from_db()
        lote_2.refresh_from_db()

        # FC descontado correctamente
        assert lote_farmacia_central.cantidad_actual == stock_fc_1_inicial - cantidad_1
        assert lote_2.cantidad_actual == stock_fc_2_inicial - cantidad_2

        # Centro recibe todo disponible
        stock_centro = obtener_stock_centro(producto_qa, centro_destino)
        total_enviado = cantidad_1 + cantidad_2
        assert stock_centro == total_enviado, \
            f"Centro debe tener {total_enviado}. Tiene: {stock_centro}"

        # Sin descuentos automáticos
        grupo = response.data.get('grupo_salida')
        dispensaciones = Movimiento.objects.filter(
            referencia=grupo,
            subtipo_salida='dispensacion'
        ).count()
        assert dispensaciones == 0


@pytest.mark.django_db(transaction=True)
class TestEscenario3NoDobleDescuento:
    """
    Escenario 3: Validación de no doble descuento
    
    Given una salida registrada desde farmacia central hacia un centro
    When se consulta el inventario del centro
    Then el stock debe reflejarse como disponible
    And no debe existir consumo ni salida registrada automáticamente
    """

    def test_escenario_3_no_doble_descuento(
        self, api_client, admin_user, lote_farmacia_central, centro_destino, producto_qa
    ):
        """Verificar que no existe doble descuento."""
        api_client.force_authenticate(user=admin_user)
        cantidad = 60

        limpiar_lotes_centro(producto_qa, centro_destino)

        # Ejecutar transferencia
        response = api_client.post('/api/salida-masiva/', {
            'centro_destino_id': centro_destino.id,
            'observaciones': 'Escenario 3 - No doble descuento',
            'auto_confirmar': True,
            'items': [{'lote_id': lote_farmacia_central.id, 'cantidad': cantidad}]
        }, format='json')

        assert response.status_code == 201
        grupo = response.data.get('grupo_salida')

        # Consultar lote del centro
        lote_centro = Lote.objects.filter(
            producto=producto_qa,
            centro=centro_destino
        ).first()

        assert lote_centro is not None, "Debe existir lote en centro"
        
        # Stock debe estar COMPLETO (no descontado)
        assert lote_centro.cantidad_actual == cantidad, \
            f"Stock centro debe ser {cantidad}. Actual: {lote_centro.cantidad_actual}"

        # No debe haber salidas registradas para este lote del centro
        salidas_lote_centro = Movimiento.objects.filter(
            lote=lote_centro,
            tipo='salida'
        ).count()

        assert salidas_lote_centro == 0, \
            f"No debe haber salidas en lote centro. Encontradas: {salidas_lote_centro}"


@pytest.mark.django_db(transaction=True)
class TestEscenario4SalidaManualCentro:
    """
    Escenario 4: Salida manual desde el centro
    
    Given inventario disponible en un centro
    When el centro registra una salida manual
    Then el inventario del centro debe descontarse
    And no debe impactar el inventario de farmacia central
    """

    def test_escenario_4_salida_manual_centro(
        self, api_client, admin_user, centro_user, lote_farmacia_central, 
        centro_destino, producto_qa
    ):
        """Salida manual desde centro no afecta farmacia central."""
        # SETUP: Primero transferir stock al centro
        api_client.force_authenticate(user=admin_user)
        cantidad_inicial = 100

        limpiar_lotes_centro(producto_qa, centro_destino)

        response = api_client.post('/api/salida-masiva/', {
            'centro_destino_id': centro_destino.id,
            'observaciones': 'Setup Escenario 4',
            'auto_confirmar': True,
            'items': [{'lote_id': lote_farmacia_central.id, 'cantidad': cantidad_inicial}]
        }, format='json')
        assert response.status_code == 201

        # Obtener estados después de la transferencia
        lote_farmacia_central.refresh_from_db()
        stock_fc_antes_salida_manual = lote_farmacia_central.cantidad_actual

        lote_centro = Lote.objects.filter(
            producto=producto_qa,
            centro=centro_destino
        ).first()
        stock_centro_antes = lote_centro.cantidad_actual

        # GIVEN - Centro tiene inventario disponible
        assert stock_centro_antes == cantidad_inicial

        # WHEN - Centro registra salida manual
        api_client.force_authenticate(user=centro_user)
        cantidad_salida = 20

        response_salida = api_client.post('/api/movimientos/', {
            'lote': lote_centro.id,
            'tipo': 'salida',
            'cantidad': cantidad_salida,
            'observaciones': 'Salida manual - Escenario 4',
            'subtipo_salida': 'consumo_interno'
        }, format='json')

        assert response_salida.status_code == 201, f"Error: {response_salida.data}"

        # THEN
        lote_centro.refresh_from_db()
        lote_farmacia_central.refresh_from_db()

        # Centro descontado
        assert lote_centro.cantidad_actual == stock_centro_antes - cantidad_salida, \
            f"Centro debe descontar. Esperado: {stock_centro_antes - cantidad_salida}, " \
            f"Actual: {lote_centro.cantidad_actual}"

        # FC sin cambios
        assert lote_farmacia_central.cantidad_actual == stock_fc_antes_salida_manual, \
            f"FC NO debe cambiar. Antes: {stock_fc_antes_salida_manual}, " \
            f"Después: {lote_farmacia_central.cantidad_actual}"


@pytest.mark.django_db(transaction=True)
class TestEscenario5CancelacionReverso:
    """
    Escenario 5: Cancelación o reverso (si aplica)
    
    Given un movimiento hacia centro aún no consumido
    When se cancela o revierte el movimiento
    Then el inventario debe regresar a farmacia central
    And no debe existir afectación en el centro
    """

    def test_escenario_5_cancelacion_pendiente(
        self, api_client, admin_user, lote_farmacia_central, centro_destino, producto_qa
    ):
        """Cancelación de salida PENDIENTE devuelve stock a FC."""
        api_client.force_authenticate(user=admin_user)
        stock_fc_inicial = lote_farmacia_central.cantidad_actual
        cantidad = 35

        limpiar_lotes_centro(producto_qa, centro_destino)

        # Crear salida PENDIENTE (auto_confirmar=False)
        response = api_client.post('/api/salida-masiva/', {
            'centro_destino_id': centro_destino.id,
            'observaciones': 'Escenario 5 - Para cancelar',
            'auto_confirmar': False,  # PENDIENTE
            'items': [{'lote_id': lote_farmacia_central.id, 'cantidad': cantidad}]
        }, format='json')

        assert response.status_code == 201
        grupo = response.data.get('grupo_salida')

        # Stock FC no debe cambiar aún (está pendiente)
        lote_farmacia_central.refresh_from_db()
        assert lote_farmacia_central.cantidad_actual == stock_fc_inicial, \
            "En modo PENDIENTE, FC no debe descontar aún"

        # WHEN - Cancelar
        response_cancel = api_client.delete(f'/api/salida-masiva/cancelar/{grupo}/')
        
        # Si el endpoint existe, verificar que funciona
        if response_cancel.status_code == 200:
            lote_farmacia_central.refresh_from_db()
            assert lote_farmacia_central.cantidad_actual == stock_fc_inicial, \
                "Tras cancelar, FC debe mantener stock original"

            # Centro no debe tener stock
            stock_centro = obtener_stock_centro(producto_qa, centro_destino)
            assert stock_centro == 0, "Centro no debe tener stock tras cancelar"


# =============================================================================
# SECCIÓN 3: QA TÉCNICO - VALIDACIONES TÉCNICAS
# =============================================================================

@pytest.mark.django_db(transaction=True)
class TestValidacionesTecnicas:
    """
    Validaciones técnicas clave para el flujo de movimientos.
    """

    def test_tecnico_001_tipo_movimiento_correcto(
        self, api_client, admin_user, lote_farmacia_central, centro_destino
    ):
        """
        Validar que el movimiento crea un registro de transferencia 
        y no una salida final.
        """
        api_client.force_authenticate(user=admin_user)

        response = api_client.post('/api/salida-masiva/', {
            'centro_destino_id': centro_destino.id,
            'observaciones': 'Test técnico 001',
            'auto_confirmar': True,
            'items': [{'lote_id': lote_farmacia_central.id, 'cantidad': 15}]
        }, format='json')

        assert response.status_code == 201
        grupo = response.data.get('grupo_salida')

        # El movimiento de salida debe ser de tipo 'transferencia'
        mov_salida = Movimiento.objects.filter(
            referencia=grupo,
            tipo='salida'
        ).first()

        assert mov_salida.subtipo_salida == 'transferencia', \
            f"Subtipo debe ser 'transferencia'. Actual: {mov_salida.subtipo_salida}"

    def test_tecnico_002_lote_centro_estado_activo(
        self, api_client, admin_user, lote_farmacia_central, centro_destino, producto_qa
    ):
        """
        Validar que el inventario del centro se registre con estado activo/disponible.
        """
        api_client.force_authenticate(user=admin_user)
        cantidad = 45

        limpiar_lotes_centro(producto_qa, centro_destino)

        response = api_client.post('/api/salida-masiva/', {
            'centro_destino_id': centro_destino.id,
            'observaciones': 'Test técnico 002',
            'auto_confirmar': True,
            'items': [{'lote_id': lote_farmacia_central.id, 'cantidad': cantidad}]
        }, format='json')

        assert response.status_code == 201

        lote_centro = Lote.objects.filter(
            producto=producto_qa,
            centro=centro_destino
        ).first()

        assert lote_centro.activo == True, "Lote centro debe estar activo"
        assert lote_centro.cantidad_actual == cantidad, \
            f"Cantidad debe ser {cantidad}. Actual: {lote_centro.cantidad_actual}"

    def test_tecnico_003_no_triggers_automaticos(
        self, api_client, admin_user, lote_farmacia_central, centro_destino, producto_qa
    ):
        """
        Asegurar que no existan procesos legacy que descuenten al centro.
        Verificar que no hay movimientos de salida automáticos.
        """
        api_client.force_authenticate(user=admin_user)

        limpiar_lotes_centro(producto_qa, centro_destino)

        response = api_client.post('/api/salida-masiva/', {
            'centro_destino_id': centro_destino.id,
            'observaciones': 'Test técnico 003',
            'auto_confirmar': True,
            'items': [{'lote_id': lote_farmacia_central.id, 'cantidad': 25}]
        }, format='json')

        assert response.status_code == 201
        grupo = response.data.get('grupo_salida')

        # Buscar cualquier movimiento de salida que NO sea la transferencia original
        salidas_no_transferencia = Movimiento.objects.filter(
            referencia=grupo,
            tipo='salida'
        ).exclude(
            subtipo_salida='transferencia'
        ).count()

        assert salidas_no_transferencia == 0, \
            f"No debe haber salidas automáticas. Encontradas: {salidas_no_transferencia}"

    def test_tecnico_004_misma_logica_individual_masiva(
        self, api_client, admin_user, lote_farmacia_central, centro_destino, producto_qa
    ):
        """
        Verificar que el flujo masivo use la misma lógica que el individual.
        Ambos deben crear exactamente 2 movimientos: 1 salida + 1 entrada.
        """
        api_client.force_authenticate(user=admin_user)

        # Crear segundo lote para prueba
        lote_2, _ = Lote.objects.get_or_create(
            numero_lote='QA-LOTE-FC-003',
            producto=producto_qa,
            centro=None,
            defaults={
                'cantidad_inicial': 300,
                'cantidad_actual': 300,
                'fecha_caducidad': date.today() + timedelta(days=365),
                'precio_unitario': Decimal('120.00'),
                'activo': True
            }
        )

        # Prueba 1: Salida "individual" (1 item)
        response_1 = api_client.post('/api/salida-masiva/', {
            'centro_destino_id': centro_destino.id,
            'observaciones': 'Test individual',
            'auto_confirmar': True,
            'items': [{'lote_id': lote_farmacia_central.id, 'cantidad': 10}]
        }, format='json')
        grupo_1 = response_1.data.get('grupo_salida')

        # Prueba 2: Salida masiva (2 items)
        response_2 = api_client.post('/api/salida-masiva/', {
            'centro_destino_id': centro_destino.id,
            'observaciones': 'Test masiva',
            'auto_confirmar': True,
            'items': [
                {'lote_id': lote_farmacia_central.id, 'cantidad': 10},
                {'lote_id': lote_2.id, 'cantidad': 10}
            ]
        }, format='json')
        grupo_2 = response_2.data.get('grupo_salida')

        # Verificar estructura de movimientos
        # Individual: 2 movimientos (1 salida + 1 entrada)
        movs_individual = Movimiento.objects.filter(referencia=grupo_1)
        assert movs_individual.count() == 2, \
            f"Individual debe tener 2 movs. Tiene: {movs_individual.count()}"

        # Masiva con 2 items: 4 movimientos (2 salidas + 2 entradas)
        movs_masiva = Movimiento.objects.filter(referencia=grupo_2)
        assert movs_masiva.count() == 4, \
            f"Masiva 2 items debe tener 4 movs. Tiene: {movs_masiva.count()}"

        # Verificar proporción correcta
        for grupo in [grupo_1, grupo_2]:
            movs = Movimiento.objects.filter(referencia=grupo)
            salidas = movs.filter(tipo='salida').count()
            entradas = movs.filter(tipo='entrada').count()
            assert salidas == entradas, \
                f"Grupo {grupo}: Salidas ({salidas}) debe = Entradas ({entradas})"


# =============================================================================
# SECCIÓN 4: CASOS DE PRUEBA FORMALES
# =============================================================================

@pytest.mark.django_db(transaction=True)
class TestCasosPruebaFormales:
    """
    Casos de prueba formales documentados.
    """

    def test_caso_101_salida_individual_a_centro(
        self, api_client, admin_user, lote_farmacia_central, centro_destino, producto_qa
    ):
        """
        Caso 101 – Salida individual a centro
        Entrada: Salida de 50 unidades
        Resultado esperado:
        - Central –50
        - Centro +50 (sin consumo)
        """
        api_client.force_authenticate(user=admin_user)
        
        stock_fc_inicial = lote_farmacia_central.cantidad_actual
        limpiar_lotes_centro(producto_qa, centro_destino)
        
        cantidad = 50

        response = api_client.post('/api/salida-masiva/', {
            'centro_destino_id': centro_destino.id,
            'observaciones': 'Caso 101',
            'auto_confirmar': True,
            'items': [{'lote_id': lote_farmacia_central.id, 'cantidad': cantidad}]
        }, format='json')

        assert response.status_code == 201

        lote_farmacia_central.refresh_from_db()
        stock_centro = obtener_stock_centro(producto_qa, centro_destino)

        # Central –50
        assert lote_farmacia_central.cantidad_actual == stock_fc_inicial - cantidad
        # Centro +50
        assert stock_centro == cantidad

    def test_caso_102_salida_masiva_multiples_centros(
        self, api_client, admin_user, lote_farmacia_central, 
        centro_destino, centro_destino_2, producto_qa
    ):
        """
        Caso 102 – Salida masiva a múltiples destinos (simulado con 2 llamadas)
        Entrada: Salida a 2 centros
        Resultado esperado:
        - Central –total enviado
        - Centros +stock disponible
        """
        api_client.force_authenticate(user=admin_user)
        
        stock_fc_inicial = lote_farmacia_central.cantidad_actual
        limpiar_lotes_centro(producto_qa, centro_destino)
        limpiar_lotes_centro(producto_qa, centro_destino_2)
        
        cantidad_c1 = 30
        cantidad_c2 = 20

        # Envío a centro 1
        response_1 = api_client.post('/api/salida-masiva/', {
            'centro_destino_id': centro_destino.id,
            'observaciones': 'Caso 102 - Centro 1',
            'auto_confirmar': True,
            'items': [{'lote_id': lote_farmacia_central.id, 'cantidad': cantidad_c1}]
        }, format='json')
        assert response_1.status_code == 201

        # Envío a centro 2
        response_2 = api_client.post('/api/salida-masiva/', {
            'centro_destino_id': centro_destino_2.id,
            'observaciones': 'Caso 102 - Centro 2',
            'auto_confirmar': True,
            'items': [{'lote_id': lote_farmacia_central.id, 'cantidad': cantidad_c2}]
        }, format='json')
        assert response_2.status_code == 201

        lote_farmacia_central.refresh_from_db()
        stock_c1 = obtener_stock_centro(producto_qa, centro_destino)
        stock_c2 = obtener_stock_centro(producto_qa, centro_destino_2)

        total_enviado = cantidad_c1 + cantidad_c2

        # Central –total
        assert lote_farmacia_central.cantidad_actual == stock_fc_inicial - total_enviado
        # Centros con stock disponible
        assert stock_c1 == cantidad_c1
        assert stock_c2 == cantidad_c2

    def test_caso_103_consumo_manual_centro(
        self, api_client, admin_user, centro_user, lote_farmacia_central,
        centro_destino, producto_qa
    ):
        """
        Caso 103 – Consumo manual centro
        Entrada: Salida manual centro
        Resultado esperado:
        - Centro –cantidad
        - Central sin cambios
        """
        # Setup: Transferir al centro
        api_client.force_authenticate(user=admin_user)
        limpiar_lotes_centro(producto_qa, centro_destino)

        response = api_client.post('/api/salida-masiva/', {
            'centro_destino_id': centro_destino.id,
            'observaciones': 'Setup Caso 103',
            'auto_confirmar': True,
            'items': [{'lote_id': lote_farmacia_central.id, 'cantidad': 80}]
        }, format='json')
        assert response.status_code == 201

        lote_farmacia_central.refresh_from_db()
        stock_fc_antes_consumo = lote_farmacia_central.cantidad_actual

        lote_centro = Lote.objects.filter(
            producto=producto_qa,
            centro=centro_destino
        ).first()
        stock_centro_antes = lote_centro.cantidad_actual

        # Consumo manual
        api_client.force_authenticate(user=centro_user)
        cantidad_consumo = 25

        response_consumo = api_client.post('/api/movimientos/', {
            'lote': lote_centro.id,
            'tipo': 'salida',
            'cantidad': cantidad_consumo,
            'observaciones': 'Caso 103 - Consumo manual',
            'subtipo_salida': 'consumo_interno'
        }, format='json')

        assert response_consumo.status_code == 201

        lote_centro.refresh_from_db()
        lote_farmacia_central.refresh_from_db()

        # Centro –cantidad
        assert lote_centro.cantidad_actual == stock_centro_antes - cantidad_consumo
        # Central sin cambios
        assert lote_farmacia_central.cantidad_actual == stock_fc_antes_consumo

    def test_caso_104_bloqueo_doble_descuento(
        self, api_client, admin_user, lote_farmacia_central, centro_destino, producto_qa
    ):
        """
        Caso 104 – Doble salida (error)
        Entrada: Intento de consumo automático
        Resultado esperado:
        - Bloqueo o validación
        - No debe existir movimiento de dispensación automática
        """
        api_client.force_authenticate(user=admin_user)
        limpiar_lotes_centro(producto_qa, centro_destino)

        response = api_client.post('/api/salida-masiva/', {
            'centro_destino_id': centro_destino.id,
            'observaciones': 'Caso 104',
            'auto_confirmar': True,
            'items': [{'lote_id': lote_farmacia_central.id, 'cantidad': 40}]
        }, format='json')

        assert response.status_code == 201
        grupo = response.data.get('grupo_salida')

        # Verificar que NO existe dispensación automática
        dispensaciones = Movimiento.objects.filter(
            referencia=grupo,
            subtipo_salida='dispensacion'
        )

        assert dispensaciones.count() == 0, \
            f"No debe existir dispensación automática. Encontradas: {dispensaciones.count()}"

        # Verificar stock íntegro en centro
        lote_centro = Lote.objects.filter(
            producto=producto_qa,
            centro=centro_destino
        ).first()

        assert lote_centro.cantidad_actual == 40, \
            f"Stock centro debe ser 40 (sin descuento). Actual: {lote_centro.cantidad_actual}"


# =============================================================================
# SECCIÓN 5: PRUEBAS DE REGRESIÓN Y REPORTES
# =============================================================================

@pytest.mark.django_db(transaction=True)
class TestRegresionYReportes:
    """
    Pruebas de regresión para flujos existentes y reportes.
    """

    def test_regresion_001_flujo_existente_no_afectado(
        self, api_client, admin_user, lote_farmacia_central
    ):
        """
        Verificar que los flujos legacy (salidas directas internas)
        no fueron afectados por los cambios.
        """
        api_client.force_authenticate(user=admin_user)
        stock_inicial = lote_farmacia_central.cantidad_actual

        # Salida directa (merma) desde FC - NO es transferencia
        response = api_client.post('/api/movimientos/', {
            'lote': lote_farmacia_central.id,
            'tipo': 'salida',
            'cantidad': 5,
            'observaciones': 'Merma por daño - Test regresión',
            'subtipo_salida': 'merma'
        }, format='json')

        assert response.status_code == 201

        lote_farmacia_central.refresh_from_db()
        assert lote_farmacia_central.cantidad_actual == stock_inicial - 5

    def test_reporte_001_inventario_correcto(
        self, api_client, admin_user, lote_farmacia_central, centro_destino, producto_qa
    ):
        """
        Verificar que los reportes reflejen correctamente:
        - Inventario central
        - Inventario por centro
        """
        api_client.force_authenticate(user=admin_user)
        
        stock_fc_inicial = lote_farmacia_central.cantidad_actual
        limpiar_lotes_centro(producto_qa, centro_destino)
        cantidad = 55

        response = api_client.post('/api/salida-masiva/', {
            'centro_destino_id': centro_destino.id,
            'observaciones': 'Test reporte',
            'auto_confirmar': True,
            'items': [{'lote_id': lote_farmacia_central.id, 'cantidad': cantidad}]
        }, format='json')

        assert response.status_code == 201

        # Verificar datos para reportes
        lote_farmacia_central.refresh_from_db()
        
        # Stock FC (para reportes de inventario central)
        stock_fc_reportable = lote_farmacia_central.cantidad_actual
        assert stock_fc_reportable == stock_fc_inicial - cantidad

        # Stock Centro (para reportes por centro)
        stock_centro_reportable = obtener_stock_centro(producto_qa, centro_destino)
        assert stock_centro_reportable == cantidad

        # Total en sistema (debe ser consistente)
        total_sistema = stock_fc_reportable + stock_centro_reportable
        # El total debe ser igual al inicial de FC (nada se "perdió")
        assert total_sistema == stock_fc_inicial


# =============================================================================
# EJECUCIÓN DIRECTA
# =============================================================================

if __name__ == '__main__':
    print("=" * 80)
    print("QA COMPLETO - FLUJO DE MOVIMIENTOS HACIA CENTROS")
    print("=" * 80)
    print("\nEjecutando con pytest...\n")
    
    # Ejecutar con pytest
    import subprocess
    result = subprocess.run(
        ['pytest', __file__, '-v', '--tb=short', '-x'],
        capture_output=False
    )
    
    sys.exit(result.returncode)
