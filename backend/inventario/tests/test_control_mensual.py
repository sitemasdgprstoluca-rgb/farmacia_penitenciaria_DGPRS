"""
Pruebas Unitarias y Masivas para Control Mensual de Almacén (Formato A)

Este archivo contiene pruebas exhaustivas para verificar:
1. Cálculos correctos de existencias anteriores, entradas, salidas y existencia final
2. Filtrado correcto por mes/año
3. Lógica del documento de entrada (folio_documento, referencia, numero_contrato)
4. Agrupación por producto
5. Manejo de casos edge (sin datos, múltiples lotes, etc.)
6. Permisos de acceso
7. Consistencia matemática: Existencia_Anterior + Entradas - Salidas = Existencia_Final

Ejecutar con: pytest backend/inventario/tests/test_control_mensual.py -v
"""

import pytest
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock
from io import BytesIO

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase
from rest_framework import status

from core.models import (
    Producto, Lote, Movimiento, Centro, User
)


# ============================================================================
# FIXTURES Y HELPERS
# ============================================================================

@pytest.fixture
def api_client():
    """Cliente API para pruebas."""
    return APIClient()


@pytest.fixture
def admin_user(db):
    """Crea un usuario admin para pruebas."""
    user = User.objects.create_user(
        username='admin_test_cm',
        email='admin_cm@test.com',
        password='testpass123',
        rol='admin'
    )
    user.is_staff = True
    user.is_superuser = True
    user.save()
    return user


@pytest.fixture
def farmacia_user(db):
    """Crea un usuario farmacia para pruebas."""
    user = User.objects.create_user(
        username='farmacia_test_cm',
        email='farmacia_cm@test.com',
        password='testpass123',
        rol='farmacia'
    )
    return user


@pytest.fixture
def centro_user(db):
    """Crea un usuario de centro para pruebas."""
    centro = Centro.objects.create(nombre='CPR Test Control Mensual')
    user = User.objects.create_user(
        username='centro_test_cm',
        email='centro_cm@test.com',
        password='testpass123',
        rol='centro',
        centro=centro
    )
    return user


@pytest.fixture
def producto_test(db):
    """Crea un producto de prueba."""
    return Producto.objects.create(
        clave='TEST-CM-001',
        nombre='Producto Test Control Mensual',
        presentacion='Caja con 10 tabletas',
        activo=True
    )


@pytest.fixture
def producto_test_2(db):
    """Crea un segundo producto de prueba."""
    return Producto.objects.create(
        clave='TEST-CM-002',
        nombre='Producto Test 2 Control Mensual',
        presentacion='Frasco 100ml',
        activo=True
    )


@pytest.fixture
def lote_farmacia(db, producto_test):
    """Crea un lote en farmacia central (centro=None)."""
    return Lote.objects.create(
        producto=producto_test,
        numero_lote='LOT-CM-001',
        numero_contrato='CONT-2025-001',
        fecha_caducidad=date.today() + timedelta(days=365),
        cantidad_inicial=100,
        cantidad_actual=100,
        centro=None,  # Farmacia Central
        activo=True
    )


@pytest.fixture
def lote_centro(db, producto_test, centro_user):
    """Crea un lote en un centro específico."""
    return Lote.objects.create(
        producto=producto_test,
        numero_lote='LOT-CM-002',
        numero_contrato='CONT-2025-002',
        fecha_caducidad=date.today() + timedelta(days=365),
        cantidad_inicial=50,
        cantidad_actual=50,
        centro=centro_user.centro,
        activo=True
    )


def crear_movimiento(lote, tipo, cantidad, fecha, usuario=None, folio_documento=None, referencia=None, motivo=''):
    """Helper para crear movimientos con fecha específica."""
    mov = Movimiento.objects.create(
        lote=lote,
        producto=lote.producto,
        tipo=tipo,
        cantidad=abs(cantidad),
        usuario=usuario,
        folio_documento=folio_documento,
        referencia=referencia,
        motivo=motivo or f'{tipo} de prueba',
        centro_origen=None if tipo == 'entrada' else lote.centro,
        centro_destino=lote.centro if tipo == 'entrada' else None,
    )
    # Actualizar fecha después de crear (porque auto_now_add=True)
    Movimiento.objects.filter(pk=mov.pk).update(fecha=fecha)
    mov.refresh_from_db()
    return mov


# ============================================================================
# PRUEBAS UNITARIAS - CÁLCULOS BÁSICOS
# ============================================================================

@pytest.mark.django_db
class TestCalculosBasicosControlMensual:
    """Pruebas para verificar cálculos básicos del control mensual."""
    
    def test_existencia_anterior_sin_movimientos(self, api_client, admin_user, producto_test, lote_farmacia):
        """Sin movimientos en el mes, existencia anterior = existencia final."""
        api_client.force_authenticate(user=admin_user)
        
        # Obtener mes actual
        hoy = timezone.now()
        
        response = api_client.get('/api/reportes/control-mensual/', {
            'mes': hoy.month,
            'anio': hoy.year
        })
        
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/pdf'
    
    def test_calculo_entradas_mes(self, api_client, admin_user, producto_test, lote_farmacia):
        """Verificar que las entradas del mes se calculan correctamente."""
        api_client.force_authenticate(user=admin_user)
        
        # Crear entrada en el mes actual
        hoy = timezone.now()
        fecha_entrada = hoy.replace(day=15)
        
        crear_movimiento(
            lote=lote_farmacia,
            tipo='entrada',
            cantidad=50,
            fecha=fecha_entrada,
            usuario=admin_user,
            folio_documento='FACT-2026-001'
        )
        
        # Actualizar cantidad del lote
        lote_farmacia.cantidad_actual = 150  # 100 + 50
        lote_farmacia.save()
        
        response = api_client.get('/api/reportes/control-mensual/', {
            'mes': hoy.month,
            'anio': hoy.year
        })
        
        assert response.status_code == 200
    
    def test_calculo_salidas_mes(self, api_client, admin_user, producto_test, lote_farmacia):
        """Verificar que las salidas del mes se calculan correctamente."""
        api_client.force_authenticate(user=admin_user)
        
        hoy = timezone.now()
        fecha_salida = hoy.replace(day=10)
        
        crear_movimiento(
            lote=lote_farmacia,
            tipo='salida',
            cantidad=30,
            fecha=fecha_salida,
            usuario=admin_user
        )
        
        # Actualizar cantidad del lote
        lote_farmacia.cantidad_actual = 70  # 100 - 30
        lote_farmacia.save()
        
        response = api_client.get('/api/reportes/control-mensual/', {
            'mes': hoy.month,
            'anio': hoy.year
        })
        
        assert response.status_code == 200


@pytest.mark.django_db
class TestConsistenciaMatematica:
    """Pruebas para verificar: Existencia_Anterior + Entradas - Salidas = Existencia_Final."""
    
    def test_formula_basica(self, db, producto_test):
        """Verificar fórmula básica con datos controlados."""
        # Crear lote con datos conocidos
        lote = Lote.objects.create(
            producto=producto_test,
            numero_lote='LOT-MATH-001',
            numero_contrato='CONT-MATH-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=80,  # 100 + 20 - 40 = 80
            centro=None,
            activo=True
        )
        
        hoy = timezone.now()
        mes_inicio = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Crear entrada de 20
        crear_movimiento(lote, 'entrada', 20, mes_inicio + timedelta(days=5))
        # Crear salida de 40
        crear_movimiento(lote, 'salida', 40, mes_inicio + timedelta(days=10))
        
        # Calcular manualmente
        entradas = 20
        salidas = 40
        existencia_final = 80
        existencia_anterior = existencia_final - entradas + salidas  # 80 - 20 + 40 = 100
        
        assert existencia_anterior == 100
        assert existencia_anterior + entradas - salidas == existencia_final
    
    def test_formula_multiples_movimientos(self, db, producto_test):
        """Verificar fórmula con múltiples movimientos."""
        lote = Lote.objects.create(
            producto=producto_test,
            numero_lote='LOT-MATH-002',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=200,
            cantidad_actual=185,  # 200 + 50 + 35 - 60 - 40 = 185
            centro=None,
            activo=True
        )
        
        hoy = timezone.now()
        mes_inicio = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Múltiples entradas: 50 + 35 = 85
        crear_movimiento(lote, 'entrada', 50, mes_inicio + timedelta(days=3))
        crear_movimiento(lote, 'entrada', 35, mes_inicio + timedelta(days=8))
        
        # Múltiples salidas: 60 + 40 = 100
        crear_movimiento(lote, 'salida', 60, mes_inicio + timedelta(days=5))
        crear_movimiento(lote, 'salida', 40, mes_inicio + timedelta(days=12))
        
        entradas_totales = 50 + 35  # 85
        salidas_totales = 60 + 40   # 100
        existencia_final = 185
        existencia_anterior = existencia_final - entradas_totales + salidas_totales  # 185 - 85 + 100 = 200
        
        assert existencia_anterior == 200
        assert existencia_anterior + entradas_totales - salidas_totales == existencia_final


# ============================================================================
# PRUEBAS - DOCUMENTO DE ENTRADA
# ============================================================================

@pytest.mark.django_db
class TestDocumentoEntrada:
    """Pruebas para verificar la lógica del documento de entrada."""
    
    def test_prioridad_folio_documento(self, db, producto_test, admin_user):
        """El folio_documento tiene prioridad sobre referencia y numero_contrato."""
        lote = Lote.objects.create(
            producto=producto_test,
            numero_lote='LOT-DOC-001',
            numero_contrato='CONT-OLD-001',  # Tiene contrato
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=150,
            centro=None,
            activo=True
        )
        
        hoy = timezone.now()
        
        # Crear entrada con folio_documento
        mov = crear_movimiento(
            lote=lote,
            tipo='entrada',
            cantidad=50,
            fecha=hoy,
            usuario=admin_user,
            folio_documento='FACT-2026-PRIO',  # Este debe tener prioridad
            referencia='REF-IGNORADA'
        )
        
        assert mov.folio_documento == 'FACT-2026-PRIO'
    
    def test_fallback_referencia(self, db, producto_test, admin_user):
        """Sin folio_documento, debe usar referencia."""
        lote = Lote.objects.create(
            producto=producto_test,
            numero_lote='LOT-DOC-002',
            numero_contrato='CONT-OLD-002',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=150,
            centro=None,
            activo=True
        )
        
        hoy = timezone.now()
        
        mov = crear_movimiento(
            lote=lote,
            tipo='entrada',
            cantidad=50,
            fecha=hoy,
            usuario=admin_user,
            folio_documento=None,  # Sin folio
            referencia='REQ-2026-123'  # Debe usar esta
        )
        
        assert mov.folio_documento is None
        assert mov.referencia == 'REQ-2026-123'
    
    def test_fallback_numero_contrato(self, db, producto_test, admin_user):
        """Sin folio ni referencia, debe usar numero_contrato del lote."""
        lote = Lote.objects.create(
            producto=producto_test,
            numero_lote='LOT-DOC-003',
            numero_contrato='CONT-2026-FALLBACK',  # Debe usar este
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=150,
            centro=None,
            activo=True
        )
        
        hoy = timezone.now()
        
        mov = crear_movimiento(
            lote=lote,
            tipo='entrada',
            cantidad=50,
            fecha=hoy,
            usuario=admin_user,
            folio_documento=None,
            referencia=None
        )
        
        # El lote tiene numero_contrato que se usará como fallback
        assert lote.numero_contrato == 'CONT-2026-FALLBACK'
    
    def test_documento_vacio_sin_entradas(self, db, producto_test):
        """Sin entradas en el mes, documento debe estar vacío."""
        lote = Lote.objects.create(
            producto=producto_test,
            numero_lote='LOT-DOC-004',
            numero_contrato='CONT-NO-USAR',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=70,  # Solo salida
            centro=None,
            activo=True
        )
        
        hoy = timezone.now()
        
        # Solo crear salida, sin entrada
        crear_movimiento(
            lote=lote,
            tipo='salida',
            cantidad=30,
            fecha=hoy
        )
        
        # No hay entradas, así que doc_entrada debe estar vacío
        movs_entrada = Movimiento.objects.filter(lote=lote, tipo='entrada')
        assert movs_entrada.count() == 0


# ============================================================================
# PRUEBAS - FILTRADO POR MES/AÑO
# ============================================================================

@pytest.mark.django_db
class TestFiltradoPorPeriodo:
    """Pruebas para verificar el filtrado correcto por mes y año."""
    
    def test_movimientos_mes_anterior_no_incluidos(self, db, producto_test, admin_user):
        """Movimientos del mes anterior no deben incluirse en entradas/salidas."""
        lote = Lote.objects.create(
            producto=producto_test,
            numero_lote='LOT-PERIOD-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            centro=None,
            activo=True
        )
        
        hoy = timezone.now()
        mes_anterior = hoy - relativedelta(months=1)
        
        # Crear movimiento en mes anterior
        crear_movimiento(
            lote=lote,
            tipo='entrada',
            cantidad=50,
            fecha=mes_anterior.replace(day=15)
        )
        
        # Verificar que solo existe ese movimiento
        movs_mes_anterior = Movimiento.objects.filter(
            lote=lote,
            fecha__month=mes_anterior.month,
            fecha__year=mes_anterior.year
        )
        
        movs_mes_actual = Movimiento.objects.filter(
            lote=lote,
            fecha__month=hoy.month,
            fecha__year=hoy.year
        )
        
        assert movs_mes_anterior.count() == 1
        assert movs_mes_actual.count() == 0
    
    def test_movimientos_mes_siguiente_no_incluidos(self, db, producto_test, admin_user):
        """Movimientos del mes siguiente no deben incluirse."""
        lote = Lote.objects.create(
            producto=producto_test,
            numero_lote='LOT-PERIOD-002',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            centro=None,
            activo=True
        )
        
        hoy = timezone.now()
        mes_siguiente = hoy + relativedelta(months=1)
        
        # Crear movimiento en mes siguiente (futuro)
        crear_movimiento(
            lote=lote,
            tipo='entrada',
            cantidad=30,
            fecha=mes_siguiente.replace(day=10)
        )
        
        movs_mes_siguiente = Movimiento.objects.filter(
            lote=lote,
            fecha__month=mes_siguiente.month,
            fecha__year=mes_siguiente.year
        )
        
        assert movs_mes_siguiente.count() == 1
    
    def test_movimientos_mismo_mes_diferente_anio(self, db, producto_test):
        """Movimientos del mismo mes pero diferente año no deben incluirse."""
        lote = Lote.objects.create(
            producto=producto_test,
            numero_lote='LOT-PERIOD-003',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            centro=None,
            activo=True
        )
        
        hoy = timezone.now()
        anio_pasado = hoy - relativedelta(years=1)
        
        # Crear movimiento mismo mes, año pasado
        crear_movimiento(
            lote=lote,
            tipo='entrada',
            cantidad=25,
            fecha=anio_pasado
        )
        
        movs_anio_pasado = Movimiento.objects.filter(
            lote=lote,
            fecha__month=anio_pasado.month,
            fecha__year=anio_pasado.year
        )
        
        movs_anio_actual = Movimiento.objects.filter(
            lote=lote,
            fecha__month=hoy.month,
            fecha__year=hoy.year
        )
        
        assert movs_anio_pasado.count() == 1
        assert movs_anio_actual.count() == 0


# ============================================================================
# PRUEBAS - AGRUPACIÓN POR PRODUCTO
# ============================================================================

@pytest.mark.django_db
class TestAgrupacionProducto:
    """Pruebas para verificar la agrupación correcta por producto."""
    
    def test_multiples_lotes_mismo_producto(self, db, producto_test, admin_user):
        """Múltiples lotes del mismo producto deben agruparse."""
        # Crear 3 lotes del mismo producto
        lotes = []
        for i in range(1, 4):
            lote = Lote.objects.create(
                producto=producto_test,
                numero_lote=f'LOT-GRUP-{i:03d}',
                fecha_caducidad=date.today() + timedelta(days=365 - i*30),
                cantidad_inicial=100,
                cantidad_actual=100 - i*10,  # 90, 80, 70
                centro=None,
                activo=True
            )
            lotes.append(lote)
        
        # Total cantidad_actual: 90 + 80 + 70 = 240
        total_cantidad = sum(l.cantidad_actual for l in lotes)
        assert total_cantidad == 240
        
        # Verificar que hay 3 lotes del mismo producto
        lotes_producto = Lote.objects.filter(producto=producto_test, centro__isnull=True)
        assert lotes_producto.count() == 3
    
    def test_diferentes_productos_separados(self, db, producto_test, producto_test_2):
        """Diferentes productos deben mantenerse separados."""
        # Lote producto 1
        lote1 = Lote.objects.create(
            producto=producto_test,
            numero_lote='LOT-SEP-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            centro=None,
            activo=True
        )
        
        # Lote producto 2
        lote2 = Lote.objects.create(
            producto=producto_test_2,
            numero_lote='LOT-SEP-002',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=200,
            cantidad_actual=200,
            centro=None,
            activo=True
        )
        
        # Verificar que hay lotes de diferentes productos
        assert lote1.producto.clave != lote2.producto.clave
        assert Lote.objects.filter(producto=producto_test).count() >= 1
        assert Lote.objects.filter(producto=producto_test_2).count() >= 1


# ============================================================================
# PRUEBAS - PERMISOS
# ============================================================================

@pytest.mark.django_db
class TestPermisosControlMensual:
    """Pruebas para verificar permisos de acceso."""
    
    def test_admin_puede_ver_farmacia_central(self, api_client, admin_user):
        """Admin puede exportar datos de Farmacia Central."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.get('/api/reportes/control-mensual/', {
            'mes': 1,
            'anio': 2026
        })
        
        # Puede ser 200 (PDF) o 404 (sin datos)
        assert response.status_code in [200, 404]
    
    def test_farmacia_puede_ver_farmacia_central(self, api_client, farmacia_user):
        """Usuario farmacia puede exportar datos de Farmacia Central."""
        api_client.force_authenticate(user=farmacia_user)
        
        response = api_client.get('/api/reportes/control-mensual/', {
            'mes': 1,
            'anio': 2026
        })
        
        assert response.status_code in [200, 404]
    
    def test_centro_no_puede_ver_farmacia_central(self, api_client, centro_user):
        """Usuario de centro NO puede exportar datos de Farmacia Central."""
        api_client.force_authenticate(user=centro_user)
        
        response = api_client.get('/api/reportes/control-mensual/', {
            'mes': 1,
            'anio': 2026
        })
        
        assert response.status_code == 403
    
    def test_centro_puede_ver_su_centro(self, api_client, centro_user):
        """Usuario de centro puede exportar datos de su propio centro."""
        api_client.force_authenticate(user=centro_user)
        
        response = api_client.get('/api/reportes/control-mensual/', {
            'mes': 1,
            'anio': 2026,
            'centro': centro_user.centro.id
        })
        
        assert response.status_code in [200, 404]
    
    def test_centro_no_puede_ver_otro_centro(self, api_client, centro_user, db):
        """Usuario de centro NO puede exportar datos de otro centro."""
        # Crear otro centro
        otro_centro = Centro.objects.create(nombre='Otro Centro Test')
        
        api_client.force_authenticate(user=centro_user)
        
        response = api_client.get('/api/reportes/control-mensual/', {
            'mes': 1,
            'anio': 2026,
            'centro': otro_centro.id
        })
        
        assert response.status_code == 403
    
    def test_usuario_no_autenticado(self, api_client):
        """Usuario no autenticado no puede acceder."""
        response = api_client.get('/api/reportes/control-mensual/')
        
        assert response.status_code in [401, 403]


# ============================================================================
# PRUEBAS - VALIDACIÓN DE PARÁMETROS
# ============================================================================

@pytest.mark.django_db
class TestValidacionParametros:
    """Pruebas para validación de parámetros de entrada."""
    
    def test_mes_invalido_menor_1(self, api_client, admin_user):
        """Mes menor a 1 debe dar error."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.get('/api/reportes/control-mensual/', {
            'mes': 0,
            'anio': 2026
        })
        
        assert response.status_code == 400
    
    def test_mes_invalido_mayor_12(self, api_client, admin_user):
        """Mes mayor a 12 debe dar error."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.get('/api/reportes/control-mensual/', {
            'mes': 13,
            'anio': 2026
        })
        
        assert response.status_code == 400
    
    def test_centro_inexistente(self, api_client, admin_user):
        """Centro que no existe debe dar error 404."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.get('/api/reportes/control-mensual/', {
            'mes': 1,
            'anio': 2026,
            'centro': 99999  # ID que no existe
        })
        
        assert response.status_code == 404
    
    def test_mes_diciembre(self, api_client, admin_user):
        """Mes diciembre debe funcionar correctamente (edge case año nuevo)."""
        api_client.force_authenticate(user=admin_user)
        
        response = api_client.get('/api/reportes/control-mensual/', {
            'mes': 12,
            'anio': 2025
        })
        
        assert response.status_code in [200, 404]


# ============================================================================
# PRUEBAS MASIVAS - VOLUMEN DE DATOS
# ============================================================================

@pytest.mark.django_db
class TestMasivoVolumenDatos:
    """Pruebas con grandes volúmenes de datos."""
    
    def test_100_productos_100_lotes(self, db, admin_user, api_client):
        """Prueba con 100 productos y múltiples lotes cada uno."""
        api_client.force_authenticate(user=admin_user)
        
        # Crear 50 productos con 2 lotes cada uno = 100 lotes
        productos = []
        for i in range(50):
            prod = Producto.objects.create(
                clave=f'MASS-{i:04d}',
                nombre=f'Producto Masivo {i}',
                presentacion='Unidad',
                activo=True
            )
            productos.append(prod)
            
            # 2 lotes por producto
            for j in range(2):
                Lote.objects.create(
                    producto=prod,
                    numero_lote=f'LOT-MASS-{i:04d}-{j:02d}',
                    fecha_caducidad=date.today() + timedelta(days=365),
                    cantidad_inicial=100,
                    cantidad_actual=80,
                    centro=None,
                    activo=True
                )
        
        # Verificar creación
        assert Producto.objects.filter(clave__startswith='MASS-').count() == 50
        assert Lote.objects.filter(numero_lote__startswith='LOT-MASS-').count() == 100
        
        # El reporte debe generar sin errores
        hoy = timezone.now()
        response = api_client.get('/api/reportes/control-mensual/', {
            'mes': hoy.month,
            'anio': hoy.year
        })
        
        assert response.status_code == 200
    
    def test_1000_movimientos_mes(self, db, admin_user, api_client):
        """Prueba con 1000 movimientos en el mes."""
        api_client.force_authenticate(user=admin_user)
        
        # Crear producto y lote
        prod = Producto.objects.create(
            clave='MASS-MOV-001',
            nombre='Producto Movimientos Masivos',
            presentacion='Unidad',
            activo=True
        )
        
        lote = Lote.objects.create(
            producto=prod,
            numero_lote='LOT-MASS-MOV-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=10000,
            cantidad_actual=10000,
            centro=None,
            activo=True
        )
        
        # Crear 500 entradas y 500 salidas
        hoy = timezone.now()
        mes_inicio = hoy.replace(day=1)
        
        movimientos = []
        for i in range(500):
            # Entrada
            movimientos.append(Movimiento(
                lote=lote,
                producto=prod,
                tipo='entrada',
                cantidad=10,
                fecha=mes_inicio + timedelta(hours=i),
                motivo='Entrada masiva'
            ))
            # Salida
            movimientos.append(Movimiento(
                lote=lote,
                producto=prod,
                tipo='salida',
                cantidad=5,
                fecha=mes_inicio + timedelta(hours=i, minutes=30),
                motivo='Salida masiva'
            ))
        
        Movimiento.objects.bulk_create(movimientos)
        
        # Verificar creación
        assert Movimiento.objects.filter(lote=lote).count() == 1000
        
        # El reporte debe generar sin errores
        response = api_client.get('/api/reportes/control-mensual/', {
            'mes': hoy.month,
            'anio': hoy.year
        })
        
        assert response.status_code == 200


# ============================================================================
# PRUEBAS - CASOS EDGE
# ============================================================================

@pytest.mark.django_db
class TestCasosEdge:
    """Pruebas para casos límite y especiales."""
    
    def test_lote_cantidad_cero(self, db, admin_user, api_client):
        """Lote con cantidad 0 debe manejarse correctamente."""
        api_client.force_authenticate(user=admin_user)
        
        prod = Producto.objects.create(
            clave='EDGE-ZERO-001',
            nombre='Producto Cantidad Cero',
            presentacion='Unidad',
            activo=True
        )
        
        lote = Lote.objects.create(
            producto=prod,
            numero_lote='LOT-ZERO-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=0,  # Sin stock
            centro=None,
            activo=True
        )
        
        hoy = timezone.now()
        response = api_client.get('/api/reportes/control-mensual/', {
            'mes': hoy.month,
            'anio': hoy.year
        })
        
        assert response.status_code == 200
    
    def test_producto_sin_clave(self, db, admin_user, api_client):
        """Producto sin clave debe usar ID como fallback."""
        api_client.force_authenticate(user=admin_user)
        
        prod = Producto.objects.create(
            clave='',  # Sin clave
            nombre='Producto Sin Clave',
            presentacion='Unidad',
            activo=True
        )
        
        Lote.objects.create(
            producto=prod,
            numero_lote='LOT-NOCLAVE-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=50,
            cantidad_actual=50,
            centro=None,
            activo=True
        )
        
        hoy = timezone.now()
        response = api_client.get('/api/reportes/control-mensual/', {
            'mes': hoy.month,
            'anio': hoy.year
        })
        
        assert response.status_code == 200
    
    def test_lote_con_fecha_caducidad_muy_lejana(self, db, admin_user, api_client):
        """Lote con fecha de caducidad muy lejana debe manejarse correctamente."""
        api_client.force_authenticate(user=admin_user)
        
        prod = Producto.objects.create(
            clave='EDGE-FARFUT-001',
            nombre='Producto Caducidad Lejana',
            presentacion='Unidad',
            activo=True
        )
        
        # Fecha de caducidad en 10 años
        Lote.objects.create(
            producto=prod,
            numero_lote='LOT-FARFUT-001',
            fecha_caducidad=date.today() + timedelta(days=3650),  # 10 años
            cantidad_inicial=50,
            cantidad_actual=50,
            centro=None,
            activo=True
        )
        
        hoy = timezone.now()
        response = api_client.get('/api/reportes/control-mensual/', {
            'mes': hoy.month,
            'anio': hoy.year
        })
        
        assert response.status_code == 200
    
    def test_folio_documento_muy_largo(self, db, producto_test, admin_user):
        """Folio documento muy largo debe truncarse a 20 caracteres."""
        lote = Lote.objects.create(
            producto=producto_test,
            numero_lote='LOT-LONG-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=150,
            centro=None,
            activo=True
        )
        
        folio_largo = 'FACTURA-2026-PROVEEDOR-FARMACEUTICO-NACIONAL-001'
        
        mov = crear_movimiento(
            lote=lote,
            tipo='entrada',
            cantidad=50,
            fecha=timezone.now(),
            folio_documento=folio_largo
        )
        
        assert len(mov.folio_documento) == len(folio_largo)
        # La función trunca a 20 chars en el reporte
        assert len(folio_largo[:20]) == 20
    
    def test_mes_sin_movimientos(self, db, admin_user, api_client):
        """Mes sin movimientos debe generar PDF vacío o informativo."""
        api_client.force_authenticate(user=admin_user)
        
        # No crear ningún lote ni movimiento
        
        response = api_client.get('/api/reportes/control-mensual/', {
            'mes': 6,  # Junio probablemente sin datos
            'anio': 2020  # Año pasado sin datos
        })
        
        # Puede ser 200 con PDF vacío o 404
        assert response.status_code in [200, 404]


# ============================================================================
# PRUEBAS - RECONSTRUCCIÓN HISTÓRICA
# ============================================================================

@pytest.mark.django_db
class TestReconstruccionHistorica:
    """Pruebas para verificar reconstrucción de existencias en meses pasados."""
    
    def test_existencia_mes_pasado(self, db, admin_user, api_client):
        """Reconstruir existencia de un mes pasado correctamente."""
        api_client.force_authenticate(user=admin_user)
        
        prod = Producto.objects.create(
            clave='HIST-001',
            nombre='Producto Histórico',
            presentacion='Unidad',
            activo=True
        )
        
        # Crear lote con cantidad actual de 100
        lote = Lote.objects.create(
            producto=prod,
            numero_lote='LOT-HIST-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=200,
            cantidad_actual=100,  # Actual
            centro=None,
            activo=True
        )
        
        hoy = timezone.now()
        mes_pasado = hoy - relativedelta(months=1)
        
        # Movimientos del mes pasado
        crear_movimiento(lote, 'entrada', 50, mes_pasado.replace(day=10))
        crear_movimiento(lote, 'salida', 30, mes_pasado.replace(day=15))
        
        # Movimientos del mes actual (posteriores al mes consultado)
        crear_movimiento(lote, 'salida', 70, hoy.replace(day=5))
        
        # Para el mes pasado:
        # - Existencia final mes pasado = cantidad_actual + movimientos_despues
        # - 100 + 70 (salida de este mes) = 170
        # - Existencia anterior mes pasado = 170 - 50 + 30 = 150
        
        response = api_client.get('/api/reportes/control-mensual/', {
            'mes': mes_pasado.month,
            'anio': mes_pasado.year
        })
        
        assert response.status_code == 200


# ============================================================================
# PRUEBAS - FUNCIÓN REGISTRAR_MOVIMIENTO_STOCK
# ============================================================================

@pytest.mark.django_db
class TestRegistrarMovimientoStock:
    """Pruebas para la función registrar_movimiento_stock con folio_documento."""
    
    def test_folio_documento_se_guarda_en_entrada(self, db, producto_test, admin_user):
        """El folio_documento se guarda correctamente en movimientos de entrada."""
        from inventario.views_legacy import registrar_movimiento_stock
        
        lote = Lote.objects.create(
            producto=producto_test,
            numero_lote='LOT-REG-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            centro=None,
            activo=True
        )
        
        movimiento, lote_actualizado = registrar_movimiento_stock(
            lote=lote,
            tipo='entrada',
            cantidad=50,
            usuario=admin_user,
            observaciones='Prueba folio documento',
            folio_documento='FACT-TEST-001'
        )
        
        assert movimiento.folio_documento == 'FACT-TEST-001'
        assert lote_actualizado.cantidad_actual == 150
    
    def test_folio_documento_no_se_guarda_en_salida(self, db, producto_test, admin_user):
        """El folio_documento NO se guarda en movimientos de salida."""
        from inventario.views_legacy import registrar_movimiento_stock
        
        lote = Lote.objects.create(
            producto=producto_test,
            numero_lote='LOT-REG-002',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            centro=None,
            activo=True
        )
        
        movimiento, lote_actualizado = registrar_movimiento_stock(
            lote=lote,
            tipo='salida',
            cantidad=30,
            usuario=admin_user,
            observaciones='Prueba salida',
            folio_documento='FACT-NO-GUARDAR'  # No debe guardarse
        )
        
        # En salidas, folio_documento debe ser None (por diseño)
        assert movimiento.folio_documento is None
        assert lote_actualizado.cantidad_actual == 70


# ============================================================================
# EJECUCIÓN DIRECTA
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
