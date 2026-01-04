# -*- coding: utf-8 -*-
"""
Pruebas unitarias para el módulo de Movimientos por nivel de usuario.

Este archivo contiene tests exhaustivos que validan:
1. Acceso por rol (ADMIN, FARMACIA, CENTRO, MEDICO, VISTA)
2. Operaciones CRUD según permisos
3. Filtros y segmentación de datos por centro
4. Integración frontend-backend-base de datos

Estructura de la base de datos relevante:
- movimientos: tipo, producto_id, lote_id, cantidad, centro_origen_id, 
               centro_destino_id, subtipo_salida, numero_expediente
- usuarios: rol, centro_id
- lotes: producto_id, centro_id, cantidad_actual
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Producto, Lote, Movimiento, Centro

User = get_user_model()


@pytest.fixture
def api_client():
    """Cliente API sin autenticar."""
    return APIClient()


@pytest.fixture
def centro_farmacia(db):
    """Centro Farmacia Central (representa almacén central)."""
    # Farmacia Central no tiene un centro asociado en la BD
    # Los lotes de farmacia central tienen centro_id = NULL
    return None


@pytest.fixture
def centro_penitenciario(db):
    """Centro penitenciario de prueba."""
    return Centro.objects.create(
        nombre="CENTRO PENITENCIARIO TEST",
        direccion="Dirección de prueba",
        telefono="555-1234",
        activo=True
    )


@pytest.fixture
def centro_penitenciario_2(db):
    """Segundo centro penitenciario para pruebas de aislamiento."""
    return Centro.objects.create(
        nombre="CENTRO PENITENCIARIO 2",
        direccion="Dirección alternativa",
        telefono="555-5678",
        activo=True
    )


@pytest.fixture
def producto(db):
    """Producto de prueba."""
    return Producto.objects.create(
        clave="PROD001",
        nombre="Paracetamol 500mg",
        descripcion="Analgésico y antipirético",
        unidad_medida="CAJA",
        categoria="medicamento",
        stock_minimo=10,
        activo=True
    )


@pytest.fixture
def lote_farmacia_central(producto, db):
    """Lote en Almacén Central (centro=NULL)."""
    return Lote.objects.create(
        numero_lote="LOT-FC-001",
        producto=producto,
        cantidad_inicial=1000,
        cantidad_actual=1000,
        fecha_caducidad=date.today() + timedelta(days=365),
        precio_unitario=Decimal('10.00'),
        centro=None,  # NULL = Farmacia Central
        activo=True
    )


@pytest.fixture
def lote_centro(producto, centro_penitenciario, db):
    """Lote asignado a un centro penitenciario."""
    return Lote.objects.create(
        numero_lote="LOT-CP-001",
        producto=producto,
        cantidad_inicial=200,
        cantidad_actual=200,
        fecha_caducidad=date.today() + timedelta(days=365),
        precio_unitario=Decimal('10.00'),
        centro=centro_penitenciario,
        activo=True
    )


@pytest.fixture
def lote_centro_2(producto, centro_penitenciario_2, db):
    """Lote en el segundo centro (para aislamiento)."""
    return Lote.objects.create(
        numero_lote="LOT-CP2-001",
        producto=producto,
        cantidad_inicial=150,
        cantidad_actual=150,
        fecha_caducidad=date.today() + timedelta(days=365),
        precio_unitario=Decimal('10.00'),
        centro=centro_penitenciario_2,
        activo=True
    )


# ============================================================================
# USUARIOS POR ROL
# ============================================================================

@pytest.fixture
def usuario_admin(db):
    """Usuario con rol ADMIN - acceso total."""
    return User.objects.create_user(
        username="admin_test",
        email="admin@test.com",
        password="testpass123",
        rol="ADMIN",
        is_staff=True,
        is_superuser=True
    )


@pytest.fixture
def usuario_farmacia(db):
    """Usuario con rol FARMACIA - gestiona almacén central."""
    return User.objects.create_user(
        username="farmacia_test",
        email="farmacia@test.com",
        password="testpass123",
        rol="FARMACIA"
    )


@pytest.fixture
def usuario_centro_admin(centro_penitenciario, db):
    """Usuario con rol administrador_centro - gestiona su centro."""
    return User.objects.create_user(
        username="admin_centro_test",
        email="admin_centro@test.com",
        password="testpass123",
        rol="administrador_centro",
        centro=centro_penitenciario
    )


@pytest.fixture
def usuario_director(centro_penitenciario, db):
    """Usuario con rol director_centro - autoriza en su centro."""
    return User.objects.create_user(
        username="director_test",
        email="director@test.com",
        password="testpass123",
        rol="director_centro",
        centro=centro_penitenciario
    )


@pytest.fixture
def usuario_medico(centro_penitenciario, db):
    """Usuario con rol MEDICO - solo consultas y requisiciones."""
    return User.objects.create_user(
        username="medico_test",
        email="medico@test.com",
        password="testpass123",
        rol="MEDICO",
        centro=centro_penitenciario
    )


@pytest.fixture
def usuario_vista(db):
    """Usuario con rol VISTA - solo lectura."""
    return User.objects.create_user(
        username="vista_test",
        email="vista@test.com",
        password="testpass123",
        rol="VISTA"
    )


@pytest.fixture
def usuario_centro_otro(centro_penitenciario_2, db):
    """Usuario de otro centro (para pruebas de aislamiento)."""
    return User.objects.create_user(
        username="otro_centro_test",
        email="otro@test.com",
        password="testpass123",
        rol="administrador_centro",
        centro=centro_penitenciario_2
    )


# ============================================================================
# TESTS DE ACCESO POR ROL - LISTADO
# ============================================================================

@pytest.mark.django_db
class TestMovimientosListadoPorRol:
    """Tests para listar movimientos según rol de usuario."""

    def test_admin_ve_todos_los_movimientos(self, api_client, usuario_admin, 
                                             lote_farmacia_central, lote_centro):
        """ADMIN puede ver todos los movimientos de todos los centros."""
        # Crear movimientos en distintos lotes
        Movimiento.objects.create(
            tipo='entrada', cantidad=100, lote=lote_farmacia_central,
            motivo='Entrada inicial farmacia'
        )
        Movimiento.objects.create(
            tipo='salida', cantidad=10, lote=lote_centro,
            motivo='Salida centro'
        )
        
        api_client.force_authenticate(user=usuario_admin)
        response = api_client.get('/api/movimientos/')
        
        assert response.status_code == status.HTTP_200_OK
        # Debería ver ambos movimientos
        data = response.json()
        assert data['count'] >= 2

    def test_farmacia_ve_todos_los_movimientos(self, api_client, usuario_farmacia,
                                                lote_farmacia_central, lote_centro):
        """FARMACIA puede ver todos los movimientos."""
        Movimiento.objects.create(
            tipo='entrada', cantidad=50, lote=lote_farmacia_central,
            motivo='Entrada farmacia'
        )
        Movimiento.objects.create(
            tipo='salida', cantidad=5, lote=lote_centro,
            motivo='Salida centro'
        )
        
        api_client.force_authenticate(user=usuario_farmacia)
        response = api_client.get('/api/movimientos/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['count'] >= 2

    def test_centro_solo_ve_movimientos_de_su_centro(self, api_client, usuario_centro_admin,
                                                       lote_centro, lote_centro_2):
        """Usuario de centro solo ve movimientos de su centro."""
        # Movimiento en su centro
        Movimiento.objects.create(
            tipo='salida', cantidad=5, lote=lote_centro,
            motivo='Mi centro'
        )
        # Movimiento en otro centro (NO debe verlo)
        Movimiento.objects.create(
            tipo='salida', cantidad=3, lote=lote_centro_2,
            motivo='Otro centro'
        )
        
        api_client.force_authenticate(user=usuario_centro_admin)
        response = api_client.get('/api/movimientos/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Solo debería ver el de su centro
        for mov in data.get('results', []):
            # Verificar que no ve movimientos de otros centros
            assert 'Otro centro' not in mov.get('motivo', '')

    def test_medico_puede_listar_movimientos_de_su_centro(self, api_client, usuario_medico,
                                                           lote_centro):
        """MEDICO puede ver (pero no crear) movimientos de su centro."""
        Movimiento.objects.create(
            tipo='salida', cantidad=2, lote=lote_centro,
            motivo='Consumo centro', subtipo_salida='consumo_interno'
        )
        
        api_client.force_authenticate(user=usuario_medico)
        response = api_client.get('/api/movimientos/')
        
        assert response.status_code == status.HTTP_200_OK

    def test_vista_puede_listar_movimientos(self, api_client, usuario_vista,
                                             lote_farmacia_central):
        """Usuario VISTA puede listar movimientos (solo lectura)."""
        Movimiento.objects.create(
            tipo='entrada', cantidad=100, lote=lote_farmacia_central,
            motivo='Entrada test'
        )
        
        api_client.force_authenticate(user=usuario_vista)
        response = api_client.get('/api/movimientos/')
        
        assert response.status_code == status.HTTP_200_OK

    def test_usuario_no_autenticado_denegado(self, api_client):
        """Usuario sin autenticar no puede acceder."""
        response = api_client.get('/api/movimientos/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# TESTS DE CREACIÓN DE MOVIMIENTOS POR ROL
# ============================================================================

@pytest.mark.django_db
class TestMovimientosCreacionPorRol:
    """Tests para crear movimientos según rol de usuario."""

    def test_admin_puede_crear_entrada_farmacia_central(self, api_client, usuario_admin,
                                                         lote_farmacia_central):
        """ADMIN puede crear entrada en Almacén Central."""
        api_client.force_authenticate(user=usuario_admin)
        
        response = api_client.post('/api/movimientos/', {
            'lote': lote_farmacia_central.id,
            'tipo': 'entrada',
            'cantidad': 100,
            'observaciones': 'Entrada por compra'
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        # Verificar que el lote se actualizó
        lote_farmacia_central.refresh_from_db()
        assert lote_farmacia_central.cantidad_actual == 1100

    def test_farmacia_puede_crear_transferencia_a_centro(self, api_client, usuario_farmacia,
                                                          lote_farmacia_central, centro_penitenciario):
        """FARMACIA puede transferir de Almacén Central a Centro."""
        api_client.force_authenticate(user=usuario_farmacia)
        
        response = api_client.post('/api/movimientos/', {
            'lote': lote_farmacia_central.id,
            'tipo': 'salida',
            'cantidad': 50,
            'centro': centro_penitenciario.id,
            'subtipo_salida': 'transferencia',
            'observaciones': 'Transferencia a centro'
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        # Verificar stock se redujo
        lote_farmacia_central.refresh_from_db()
        assert lote_farmacia_central.cantidad_actual == 950

    def test_centro_admin_puede_crear_salida_consumo_interno(self, api_client, usuario_centro_admin,
                                                              lote_centro):
        """Administrador de centro puede crear salida por consumo interno."""
        api_client.force_authenticate(user=usuario_centro_admin)
        
        response = api_client.post('/api/movimientos/', {
            'lote': lote_centro.id,
            'tipo': 'salida',
            'cantidad': 10,
            'subtipo_salida': 'consumo_interno',
            'observaciones': 'Consumo interno centro'
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        lote_centro.refresh_from_db()
        assert lote_centro.cantidad_actual == 190

    def test_centro_admin_puede_crear_salida_receta(self, api_client, usuario_centro_admin,
                                                     lote_centro):
        """Administrador de centro puede crear salida por receta."""
        api_client.force_authenticate(user=usuario_centro_admin)
        
        response = api_client.post('/api/movimientos/', {
            'lote': lote_centro.id,
            'tipo': 'salida',
            'cantidad': 5,
            'subtipo_salida': 'receta',
            'numero_expediente': 'EXP-2025-001',
            'observaciones': 'Dispensación por receta'
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        # Verificar que se guardó el expediente
        mov = Movimiento.objects.get(numero_expediente='EXP-2025-001')
        assert mov.subtipo_salida == 'receta'

    def test_director_puede_crear_salida_en_su_centro(self, api_client, usuario_director,
                                                       lote_centro):
        """Director de centro puede crear movimientos en su centro."""
        api_client.force_authenticate(user=usuario_director)
        
        response = api_client.post('/api/movimientos/', {
            'lote': lote_centro.id,
            'tipo': 'salida',
            'cantidad': 3,
            'subtipo_salida': 'consumo_interno',
            'observaciones': 'Salida autorizada por director'
        })
        
        assert response.status_code == status.HTTP_201_CREATED

    def test_medico_no_puede_crear_movimientos(self, api_client, usuario_medico,
                                                lote_centro):
        """MEDICO NO puede crear movimientos - debe usar requisiciones."""
        api_client.force_authenticate(user=usuario_medico)
        
        response = api_client.post('/api/movimientos/', {
            'lote': lote_centro.id,
            'tipo': 'salida',
            'cantidad': 2,
            'subtipo_salida': 'receta',
            'observaciones': 'Intento de médico'
        })
        
        # Debe ser rechazado (403 Forbidden o 400 Bad Request)
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST]

    def test_vista_no_puede_crear_movimientos(self, api_client, usuario_vista,
                                               lote_farmacia_central):
        """Usuario VISTA no puede crear movimientos."""
        api_client.force_authenticate(user=usuario_vista)
        
        response = api_client.post('/api/movimientos/', {
            'lote': lote_farmacia_central.id,
            'tipo': 'entrada',
            'cantidad': 10,
            'observaciones': 'Intento de vista'
        })
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_centro_no_puede_crear_entrada(self, api_client, usuario_centro_admin,
                                            lote_centro):
        """Centro NO puede crear entradas - solo vía surtido de requisición."""
        api_client.force_authenticate(user=usuario_centro_admin)
        
        response = api_client.post('/api/movimientos/', {
            'lote': lote_centro.id,
            'tipo': 'entrada',
            'cantidad': 50,
            'observaciones': 'Intento de entrada'
        })
        
        # Debe ser rechazado
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_centro_no_puede_operar_lotes_de_otro_centro(self, api_client, usuario_centro_admin,
                                                          lote_centro_2):
        """Usuario de centro NO puede operar lotes de otro centro."""
        api_client.force_authenticate(user=usuario_centro_admin)
        
        response = api_client.post('/api/movimientos/', {
            'lote': lote_centro_2.id,  # Lote de otro centro
            'tipo': 'salida',
            'cantidad': 5,
            'subtipo_salida': 'consumo_interno',
            'observaciones': 'Intento cruzado'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================================
# TESTS DE VALIDACIONES DE NEGOCIO
# ============================================================================

@pytest.mark.django_db
class TestMovimientosValidaciones:
    """Tests para validaciones de negocio en movimientos."""

    def test_no_permite_salida_mayor_a_stock(self, api_client, usuario_farmacia,
                                              lote_farmacia_central):
        """No se puede sacar más de lo disponible."""
        api_client.force_authenticate(user=usuario_farmacia)
        
        response = api_client.post('/api/movimientos/', {
            'lote': lote_farmacia_central.id,
            'tipo': 'salida',
            'cantidad': 9999,  # Más de lo disponible
            'subtipo_salida': 'transferencia',
            'observaciones': 'Intento exceso'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cantidad_debe_ser_positiva(self, api_client, usuario_admin,
                                         lote_farmacia_central):
        """La cantidad debe ser un número positivo."""
        api_client.force_authenticate(user=usuario_admin)
        
        response = api_client.post('/api/movimientos/', {
            'lote': lote_farmacia_central.id,
            'tipo': 'entrada',
            'cantidad': -10,
            'observaciones': 'Cantidad negativa'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_lote_requerido(self, api_client, usuario_admin):
        """El lote es obligatorio."""
        api_client.force_authenticate(user=usuario_admin)
        
        response = api_client.post('/api/movimientos/', {
            'tipo': 'entrada',
            'cantidad': 10,
            'observaciones': 'Sin lote'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================================
# TESTS DE FILTROS
# ============================================================================

@pytest.mark.django_db
class TestMovimientosFiltros:
    """Tests para filtros en listado de movimientos."""

    def test_filtro_por_tipo(self, api_client, usuario_admin, lote_farmacia_central):
        """Filtrar movimientos por tipo (entrada/salida)."""
        Movimiento.objects.create(tipo='entrada', cantidad=100, lote=lote_farmacia_central)
        Movimiento.objects.create(tipo='salida', cantidad=10, lote=lote_farmacia_central)
        
        api_client.force_authenticate(user=usuario_admin)
        
        # Solo entradas
        response = api_client.get('/api/movimientos/', {'tipo': 'entrada'})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for mov in data.get('results', []):
            assert mov.get('tipo') == 'entrada'

    def test_filtro_por_rango_fechas(self, api_client, usuario_admin, lote_farmacia_central):
        """Filtrar por rango de fechas."""
        api_client.force_authenticate(user=usuario_admin)
        
        hoy = date.today().isoformat()
        response = api_client.get('/api/movimientos/', {
            'fecha_inicio': hoy,
            'fecha_fin': hoy
        })
        
        assert response.status_code == status.HTTP_200_OK

    def test_filtro_por_centro(self, api_client, usuario_admin, 
                               lote_centro, centro_penitenciario):
        """Admin puede filtrar por centro específico."""
        Movimiento.objects.create(tipo='salida', cantidad=5, lote=lote_centro)
        
        api_client.force_authenticate(user=usuario_admin)
        response = api_client.get('/api/movimientos/', {
            'centro': centro_penitenciario.id
        })
        
        assert response.status_code == status.HTTP_200_OK

    def test_filtro_por_subtipo_salida(self, api_client, usuario_admin, lote_farmacia_central):
        """Filtrar por subtipo de salida."""
        Movimiento.objects.create(
            tipo='salida', cantidad=10, lote=lote_farmacia_central,
            subtipo_salida='receta'
        )
        Movimiento.objects.create(
            tipo='salida', cantidad=5, lote=lote_farmacia_central,
            subtipo_salida='consumo_interno'
        )
        
        api_client.force_authenticate(user=usuario_admin)
        response = api_client.get('/api/movimientos/', {
            'subtipo_salida': 'receta'
        })
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for mov in data.get('results', []):
            if mov.get('tipo') == 'salida':
                assert mov.get('subtipo_salida') == 'receta'

    def test_busqueda_por_texto(self, api_client, usuario_admin, lote_farmacia_central):
        """Búsqueda por texto en motivo/observaciones."""
        Movimiento.objects.create(
            tipo='entrada', cantidad=50, lote=lote_farmacia_central,
            motivo='Donación Cruz Roja'
        )
        
        api_client.force_authenticate(user=usuario_admin)
        response = api_client.get('/api/movimientos/', {
            'search': 'Cruz Roja'
        })
        
        assert response.status_code == status.HTTP_200_OK


# ============================================================================
# TESTS DE INTEGRACIÓN FRONTEND-BACKEND
# ============================================================================

@pytest.mark.django_db
class TestMovimientosIntegracionFrontend:
    """Tests que simulan las llamadas del frontend."""

    def test_flujo_completo_farmacia_transferencia(self, api_client, usuario_farmacia,
                                                    producto, centro_penitenciario):
        """Flujo: Farmacia transfiere a Centro."""
        api_client.force_authenticate(user=usuario_farmacia)
        
        # 1. Crear lote en farmacia central
        lote = Lote.objects.create(
            numero_lote='LOT-FLUJO-001',
            producto=producto,
            cantidad_inicial=500,
            cantidad_actual=500,
            fecha_caducidad=date.today() + timedelta(days=180),
            precio_unitario=Decimal('15.00'),
            centro=None,  # Farmacia Central
            activo=True
        )
        
        # 2. Transferir a centro
        response = api_client.post('/api/movimientos/', {
            'lote': lote.id,
            'tipo': 'salida',
            'cantidad': 100,
            'centro': centro_penitenciario.id,
            'subtipo_salida': 'transferencia',
            'observaciones': 'Transferencia de prueba'
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # 3. Verificar stock actualizado
        lote.refresh_from_db()
        assert lote.cantidad_actual == 400

    def test_flujo_completo_centro_consumo(self, api_client, usuario_centro_admin,
                                           lote_centro):
        """Flujo: Centro registra consumo interno."""
        api_client.force_authenticate(user=usuario_centro_admin)
        
        stock_inicial = lote_centro.cantidad_actual
        
        # Registrar consumo
        response = api_client.post('/api/movimientos/', {
            'lote': lote_centro.id,
            'tipo': 'salida',
            'cantidad': 20,
            'subtipo_salida': 'consumo_interno',
            'observaciones': 'Consumo semanal enfermería'
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verificar stock
        lote_centro.refresh_from_db()
        assert lote_centro.cantidad_actual == stock_inicial - 20

    def test_flujo_centro_dispensacion_receta(self, api_client, usuario_centro_admin,
                                               lote_centro):
        """Flujo: Centro dispensa por receta con expediente."""
        api_client.force_authenticate(user=usuario_centro_admin)
        
        response = api_client.post('/api/movimientos/', {
            'lote': lote_centro.id,
            'tipo': 'salida',
            'cantidad': 10,
            'subtipo_salida': 'receta',
            'numero_expediente': 'EXP-FLUJO-001',
            'observaciones': 'Dispensación paciente Juan Pérez'
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verificar trazabilidad
        mov = Movimiento.objects.get(numero_expediente='EXP-FLUJO-001')
        assert mov.subtipo_salida == 'receta'
        assert mov.cantidad == 10


# ============================================================================
# TESTS DE RESPUESTA API (Formato esperado por frontend)
# ============================================================================

@pytest.mark.django_db
class TestMovimientosFormatoRespuesta:
    """Tests para validar formato de respuesta esperado por frontend."""

    def test_listado_incluye_campos_requeridos(self, api_client, usuario_admin,
                                                lote_farmacia_central, producto):
        """El listado debe incluir todos los campos que espera el frontend."""
        Movimiento.objects.create(
            tipo='entrada', cantidad=100, lote=lote_farmacia_central,
            motivo='Test formato'
        )
        
        api_client.force_authenticate(user=usuario_admin)
        response = api_client.get('/api/movimientos/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Estructura de paginación
        assert 'count' in data
        assert 'results' in data
        
        if data['results']:
            mov = data['results'][0]
            # Campos requeridos por frontend
            campos_requeridos = ['id', 'tipo', 'cantidad']
            for campo in campos_requeridos:
                assert campo in mov, f"Campo '{campo}' faltante en respuesta"

    def test_creacion_retorna_movimiento_creado(self, api_client, usuario_admin,
                                                 lote_farmacia_central):
        """La creación debe retornar el movimiento creado."""
        api_client.force_authenticate(user=usuario_admin)
        
        response = api_client.post('/api/movimientos/', {
            'lote': lote_farmacia_central.id,
            'tipo': 'entrada',
            'cantidad': 50,
            'observaciones': 'Test retorno'
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert 'id' in data
        assert data['cantidad'] == 50
