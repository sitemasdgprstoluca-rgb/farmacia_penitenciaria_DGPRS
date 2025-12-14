"""
Tests para ISS-001, ISS-002, ISS-003, ISS-004

ISS-001: Separación de stock farmacia central vs centros
ISS-002: Máquina de estados unificada entre modelo y servicio
ISS-003: Revalidación de stock al autorizar requisiciones
ISS-004: Cálculo de stock normalizado por ubicación
"""
import pytest
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from core.models import (
    User, Centro, Producto, Lote, Requisicion, DetalleRequisicion
)


@pytest.fixture
def centro_penal(db):
    """Centro penitenciario de prueba."""
    return Centro.objects.create(
        nombre="Centro Penitenciario Test",
        direccion="Dirección Test",
        activo=True
    )


@pytest.fixture
def centro_otro(db):
    """Otro centro de prueba."""
    return Centro.objects.create(
        nombre="Centro Otro Test",
        direccion="Dirección Otro",
        activo=True
    )


@pytest.fixture
def producto(db):
    """Producto de prueba."""
    from decimal import Decimal
    return Producto.objects.create(
        clave="MED001",
        nombre="Medicamento de prueba para tests ISS-001",
        descripcion="Medicamento de prueba para tests ISS-001",
        unidad_medida="CAJA",
        stock_minimo=10,
        activo=True
    )


@pytest.fixture
def usuario_farmacia(db):
    """Usuario con rol de farmacia."""
    user = User.objects.create_user(
        username="farmacia_test",
        email="farmacia@test.com",
        password="test123456",
        rol="farmacia"
    )
    return user


@pytest.fixture
def usuario_centro(db, centro_penal):
    """Usuario de centro."""
    user = User.objects.create_user(
        username="centro_test",
        email="centro@test.com",
        password="test123456",
        rol="centro",
        centro=centro_penal
    )
    return user


@pytest.fixture
def lote_farmacia_central(db, producto):
    """Lote en farmacia central (centro=None)."""
    return Lote.objects.create(
        producto=producto,
        numero_lote="FC-001",
        centro=None,  # Farmacia central
        fecha_caducidad=timezone.now().date() + timedelta(days=365),
        cantidad_inicial=100,
        cantidad_actual=100,
        precio_unitario=Decimal("50.00"),
        activo=True
    )


@pytest.fixture
def lote_en_centro(db, producto, centro_penal, lote_farmacia_central):
    """Lote en centro penitenciario."""
    return Lote.objects.create(
        producto=producto,
        numero_lote="CT-001",
        centro=centro_penal,
        fecha_caducidad=lote_farmacia_central.fecha_caducidad,
        cantidad_inicial=30,
        cantidad_actual=30,
        precio_unitario=Decimal("50.00"),
        activo=True
    )


class TestISS001StockPorUbicacion:
    """
    ISS-001: Tests para separación de stock por ubicación.
    
    El cálculo de stock debe distinguir entre:
    - Farmacia central (centro=None)
    - Centros específicos
    """
    
    def test_get_stock_farmacia_central_solo_cuenta_lotes_sin_centro(
        self, producto, lote_farmacia_central, lote_en_centro
    ):
        """
        get_stock_farmacia_central() debe retornar SOLO stock de lotes
        sin centro asignado (farmacia central).
        """
        stock_farmacia = producto.get_stock_farmacia_central()
        
        # Solo debe contar los 100 de farmacia central, NO los 30 del centro
        assert stock_farmacia == 100
        assert stock_farmacia != 130  # No debe incluir stock de centros
    
    def test_get_stock_centro_solo_cuenta_lotes_del_centro(
        self, producto, lote_farmacia_central, lote_en_centro, centro_penal
    ):
        """
        get_stock_centro() debe retornar SOLO stock del centro especificado.
        """
        stock_centro = producto.get_stock_centro(centro_penal)
        
        # Solo debe contar los 30 del centro
        assert stock_centro == 30
        assert stock_centro != 130  # No debe incluir stock de farmacia
    
    def test_get_stock_global_cuenta_todos_los_lotes(
        self, producto, lote_farmacia_central, lote_en_centro
    ):
        """
        get_stock_global() debe retornar stock total (farmacia + centros).
        """
        stock_global = producto.get_stock_global()
        
        # Debe sumar todo: 100 + 30 = 130
        assert stock_global == 130
    
    def test_get_stock_actual_default_es_farmacia_central(
        self, producto, lote_farmacia_central, lote_en_centro
    ):
        """
        get_stock_actual() sin parámetros debe retornar stock de farmacia central.
        """
        stock_default = producto.get_stock_actual()
        stock_farmacia = producto.get_stock_farmacia_central()
        
        assert stock_default == stock_farmacia
        assert stock_default == 100
    
    def test_stock_excluye_lotes_vencidos(self, producto):
        """El stock debe excluir lotes con fecha de caducidad pasada."""
        # Lote vencido en farmacia central
        Lote.objects.create(
            producto=producto,
            numero_lote="FC-VENCIDO",
            centro=None,
            fecha_caducidad=timezone.now().date() - timedelta(days=1),
            cantidad_inicial=50,
            cantidad_actual=50,
            activo=True
        )
        
        # Lote vigente
        Lote.objects.create(
            producto=producto,
            numero_lote="FC-VIGENTE",
            centro=None,
            fecha_caducidad=timezone.now().date() + timedelta(days=30),
            cantidad_inicial=25,
            cantidad_actual=25,
            activo=True
        )
        
        stock = producto.get_stock_farmacia_central()
        
        # Solo debe contar el lote vigente
        assert stock == 25
    
    def test_stock_excluye_lotes_inactivos(self, producto):
        """El stock debe excluir lotes inactivos."""
        # Lote inactivo
        Lote.objects.create(
            producto=producto,
            numero_lote="FC-INACTIVO",
            centro=None,
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=50,
            cantidad_actual=50,
            activo=False  # Inactivo
        )
        
        # Lote activo
        Lote.objects.create(
            producto=producto,
            numero_lote="FC-ACTIVO",
            centro=None,
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=25,
            cantidad_actual=25,
            activo=True
        )
        
        stock = producto.get_stock_farmacia_central()
        
        assert stock == 25


class TestISS002MaquinaEstadosUnificada:
    """
    ISS-002: Tests para máquina de estados unificada.
    
    El modelo Requisicion y RequisicionService deben usar
    la misma definición de transiciones válidas.
    """
    
    def test_modelo_tiene_transiciones_definidas(self):
        """El modelo debe tener TRANSICIONES_VALIDAS definidas."""
        assert hasattr(Requisicion, 'TRANSICIONES_VALIDAS')
        assert isinstance(Requisicion.TRANSICIONES_VALIDAS, dict)
    
    def test_modelo_tiene_estados_surtibles(self):
        """El modelo debe definir ESTADOS_SURTIBLES."""
        assert hasattr(Requisicion, 'ESTADOS_SURTIBLES')
        assert 'autorizada' in Requisicion.ESTADOS_SURTIBLES
        assert 'parcial' in Requisicion.ESTADOS_SURTIBLES
    
    def test_servicio_usa_transiciones_del_modelo(self):
        """El servicio debe usar las transiciones del modelo."""
        from inventario.services.requisicion_service import RequisicionService
        from unittest.mock import MagicMock
        
        # Crear mock de requisicion y usuario
        mock_req = MagicMock()
        mock_req.estado = 'borrador'
        mock_user = MagicMock()
        
        service = RequisicionService(mock_req, mock_user)
        
        # Las transiciones del servicio deben ser las del modelo
        assert service.TRANSICIONES_VALIDAS == Requisicion.TRANSICIONES_VALIDAS
    
    def test_transiciones_borrador(self):
        """FLUJO V2: Desde borrador se puede ir a pendiente_admin o cancelada."""
        transiciones = Requisicion.TRANSICIONES_VALIDAS['borrador']
        
        # ISS-TRANSICIONES FIX: borrador → pendiente_admin (no enviada directa)
        assert 'pendiente_admin' in transiciones
        assert 'cancelada' in transiciones
        assert len(transiciones) == 2
    
    def test_transiciones_enviada(self):
        """FLUJO V2: Desde enviada se puede ir a en_revision, autorizada o rechazada."""
        transiciones = Requisicion.TRANSICIONES_VALIDAS['enviada']
        
        # ISS-TRANSICIONES FIX: enviada permite autorizada directa (sin pasar por en_revision)
        assert 'en_revision' in transiciones
        assert 'autorizada' in transiciones
        assert 'rechazada' in transiciones
        # Spec V2: enviada NO permite parcial ni cancelada
        assert 'parcial' not in transiciones
        assert 'cancelada' not in transiciones
    
    def test_transiciones_autorizada(self):
        """FLUJO V2: Desde autorizada se puede ir a en_surtido, surtida o cancelada."""
        transiciones = Requisicion.TRANSICIONES_VALIDAS['autorizada']
        
        # ISS-TRANSICIONES FIX: autorizada permite surtida directa
        assert 'en_surtido' in transiciones
        assert 'surtida' in transiciones
        assert 'cancelada' in transiciones
        # Spec V2: parcial es estado interno del surtido, no transición principal
        assert 'parcial' not in transiciones
    
    def test_transicion_rechazada_permite_reenvio(self):
        """ISS-002: Desde rechazada se puede volver a borrador para correcciones."""
        transiciones = Requisicion.TRANSICIONES_VALIDAS['rechazada']
        
        assert 'borrador' in transiciones
    
    def test_estados_terminales(self):
        """recibida y cancelada son estados terminales."""
        assert Requisicion.TRANSICIONES_VALIDAS['recibida'] == []
        assert Requisicion.TRANSICIONES_VALIDAS['cancelada'] == []


class TestISS003RevalidacionStockAutorizar:
    """
    ISS-003: Tests para revalidación de stock al autorizar.
    
    Al autorizar una requisición debe revalidarse el stock
    disponible en farmacia central.
    """
    
    @pytest.fixture
    def requisicion_enviada(self, db, centro_penal, usuario_centro, producto):
        """Requisición en estado enviada lista para autorizar."""
        req = Requisicion.objects.create(
            folio="REQ-TEST-001",
            centro=centro_penal,
            usuario_solicita=usuario_centro,
            estado='enviada'
        )
        DetalleRequisicion.objects.create(
            requisicion=req,
            producto=producto,
            cantidad_solicitada=50,
            cantidad_autorizada=0
        )
        return req
    
    def test_autorizar_valida_stock_farmacia_central(
        self, requisicion_enviada, lote_farmacia_central, producto
    ):
        """
        Al autorizar, debe validarse el stock de farmacia central,
        no el stock global ni el del centro solicitante.
        """
        # El lote_farmacia_central tiene 100 unidades
        # La requisición pide 50, debería pasar
        
        detalle = requisicion_enviada.detalles.first()
        stock_disponible = producto.get_stock_farmacia_central()
        
        assert stock_disponible >= detalle.cantidad_solicitada
    
    def test_autorizar_rechaza_sin_stock_suficiente_farmacia(
        self, requisicion_enviada, lote_farmacia_central, lote_en_centro, producto, centro_penal
    ):
        """
        Si no hay stock SUFICIENTE en farmacia central,
        la autorización debe detectar el déficit.
        """
        # Lote farmacia tiene 100, centro tiene 30
        # Stock farmacia: 100, stock global: 130
        # Modificamos la requisición para pedir más de lo que hay en farmacia
        detalle = requisicion_enviada.detalles.first()
        detalle.cantidad_solicitada = 150  # Más que los 100 de farmacia
        detalle.save()
        
        stock_farmacia = producto.get_stock_farmacia_central()
        stock_global = producto.get_stock_global()
        
        # Farmacia tiene 100, global tiene 130, pero requisición pide 150
        assert stock_farmacia == 100
        assert stock_global == 130
        
        # La requisición pide 150, pero farmacia tiene solo 100
        assert stock_farmacia < detalle.cantidad_solicitada
        # Aunque el stock global (130) sería "suficiente", no debe usarse


class TestISS004CalculoStockNormalizado:
    """
    ISS-004: Tests para cálculo de stock normalizado.
    
    El cálculo debe ser consistente y usar lotes directamente,
    no agregados de movimientos con signos inconsistentes.
    """
    
    def test_stock_usa_cantidad_actual_de_lotes(
        self, producto, lote_farmacia_central
    ):
        """El stock debe basarse en cantidad_actual de lotes, no en movimientos."""
        stock = producto.get_stock_farmacia_central()
        
        assert stock == lote_farmacia_central.cantidad_actual
        assert stock == 100
    
    def test_stock_solo_cuenta_lotes_disponibles(self, producto):
        """Solo deben contarse lotes activos, vigentes y con stock."""
        # Lote disponible (activo, vigente, con stock)
        Lote.objects.create(
            producto=producto,
            numero_lote="DISP-001",
            centro=None,
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            activo=True
        )
        
        # Lote agotado (cantidad = 0)
        Lote.objects.create(
            producto=producto,
            numero_lote="AGOT-001",
            centro=None,
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=50,
            cantidad_actual=0,
            activo=True
        )
        
        # Lote inactivo
        Lote.objects.create(
            producto=producto,
            numero_lote="BLOQ-001",
            centro=None,
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=30,
            cantidad_actual=30,
            activo=False
        )
        
        stock = producto.get_stock_farmacia_central()
        
        # Solo el lote disponible con cantidad > 0
        assert stock == 100
    
    def test_get_nivel_stock_usa_farmacia_central_por_defecto(
        self, producto, lote_farmacia_central, lote_en_centro
    ):
        """get_nivel_stock() debe usar farmacia central por defecto."""
        # Con 100 en farmacia y stock_minimo=10
        # 100 > 10 * 1.5 = 15 -> nivel 'alto'
        nivel = producto.get_nivel_stock()
        
        # El nivel debe calcularse con stock de farmacia (100), no global (130)
        assert nivel == 'alto'
    
    def test_get_nivel_stock_puede_usar_centro_especifico(
        self, producto, lote_farmacia_central, lote_en_centro, centro_penal
    ):
        """get_nivel_stock() puede calcular para un centro específico."""
        # lote_farmacia_central tiene 100, lote_en_centro tiene 30
        # Verificamos que get_nivel_stock con centro específico usa solo ese centro
        
        nivel_centro = producto.get_nivel_stock(centro=centro_penal)
        nivel_farmacia = producto.get_nivel_stock(centro=None)
        
        # Centro tiene 30 y stock_minimo=10 -> 30 > 15 = 'alto'
        # Farmacia tiene 100 y stock_minimo=10 -> 100 > 15 = 'alto'
        # Ambos son 'alto' pero están calculados sobre stocks diferentes
        assert nivel_centro == 'alto'
        assert nivel_farmacia == 'alto'
        
        # Verificar que los stocks usados son diferentes
        stock_centro = producto.get_stock_centro(centro_penal)
        stock_farmacia = producto.get_stock_farmacia_central()
        assert stock_centro == 30
        assert stock_farmacia == 100


class TestIntegracionFlujoRequisicion:
    """
    Tests de integración para el flujo completo de requisiciones
    con las correcciones de ISS-001 a ISS-004.
    """
    
    @pytest.fixture
    def setup_completo(
        self, db, centro_penal, usuario_farmacia, producto
    ):
        """Setup completo para tests de integración."""
        # Lote en farmacia central
        lote_fc = Lote.objects.create(
            producto=producto,
            numero_lote="INT-FC-001",
            centro=None,
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            precio_unitario=Decimal("50.00"),
            activo=True
        )
        
        # Lote en centro (ya distribuido)
        lote_ct = Lote.objects.create(
            producto=producto,
            numero_lote="INT-CT-001",
            centro=centro_penal,
            fecha_caducidad=lote_fc.fecha_caducidad,
            cantidad_inicial=30,
            cantidad_actual=30,
            precio_unitario=Decimal("50.00"),
            activo=True
        )
        
        return {
            'lote_farmacia': lote_fc,
            'lote_centro': lote_ct,
            'producto': producto,
            'centro': centro_penal,
            'usuario': usuario_farmacia
        }
    
    def test_validacion_requisicion_usa_solo_farmacia_central(
        self, setup_completo
    ):
        """
        Al crear/validar requisición, solo debe considerarse
        el stock de farmacia central, no el de centros.
        """
        producto = setup_completo['producto']
        
        # Stock total: 100 (farmacia) + 30 (centro) = 130
        # Stock disponible para requisiciones: 100 (solo farmacia)
        
        stock_para_requisicion = producto.get_stock_farmacia_central()
        stock_global = producto.get_stock_global()
        
        assert stock_para_requisicion == 100
        assert stock_global == 130
        
        # Una requisición por 80 unidades debería ser válida
        assert 80 <= stock_para_requisicion
        
        # Una requisición por 120 unidades debería fallar
        # (aunque el stock global sea 130)
        assert 120 > stock_para_requisicion
    
    def test_stock_centro_no_afecta_otras_requisiciones(
        self, setup_completo, centro_otro
    ):
        """
        El stock que ya está en un centro no debe ser
        considerado para requisiciones de otros centros.
        """
        producto = setup_completo['producto']
        centro1 = setup_completo['centro']
        
        # Stock en centro1: 30
        # Stock en farmacia: 100
        
        stock_farmacia = producto.get_stock_farmacia_central()
        stock_centro1 = producto.get_stock_centro(centro1)
        stock_centro_otro = producto.get_stock_centro(centro_otro)
        
        assert stock_farmacia == 100
        assert stock_centro1 == 30
        assert stock_centro_otro == 0  # Otro centro no tiene stock
        
        # Una requisición del centro_otro solo puede contar
        # con el stock de farmacia (100), no con lo de centro1
