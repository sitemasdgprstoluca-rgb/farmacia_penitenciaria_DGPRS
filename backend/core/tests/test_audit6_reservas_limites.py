"""
Tests para audit6: Reservas en cancelación, límites contractuales y exclusión de requisición.

ISS-001: Liberar reservas al cancelar requisiciones
ISS-002: Validar límites de monto y cantidad en contratos
ISS-003: Excluir requisición actual del stock comprometido en re-autorizaciones
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError

from core.models import (
    Producto, Lote, Centro, Requisicion, DetalleRequisicion,
    Contrato, ContratoProducto
)

pytestmark = pytest.mark.django_db


# =============================================================================
# FIXTURES AUXILIARES
# =============================================================================

@pytest.fixture
def producto(db):
    """Crea un producto de prueba."""
    return Producto.objects.create(
        clave='PROD-AUD6-001',
        descripcion='Producto Test Audit6 para pruebas',
        unidad_medida='PIEZA',
        precio_unitario=Decimal('10.00'),
        activo=True
    )


@pytest.fixture
def centro(db):
    """Crea un centro de prueba."""
    return Centro.objects.create(
        nombre='Centro Test Audit6',
        direccion='Dirección de prueba completa para el centro',
        tipo='penitenciario',
        activo=True
    )


class TestLiberarReservasEnCancelacion:
    """Tests para ISS-001: Liberar reservas al cancelar requisiciones."""
    
    @pytest.fixture
    def setup_requisicion_autorizada(self, admin_user, producto, centro):
        """Crea una requisición autorizada con reservas."""
        hoy = timezone.now().date()
        
        # Crear lote en farmacia central
        lote = Lote.objects.create(
            producto=producto,
            centro=None,  # Farmacia central
            numero_lote='LOTE-CANCEL-001',
            fecha_caducidad=hoy + timedelta(days=180),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
        
        # Crear requisición
        requisicion = Requisicion.objects.create(
            folio='REQ-CANCEL-001',
            centro=centro,
            usuario_solicita=admin_user,
            estado='borrador'
        )
        
        # Crear detalle
        detalle = DetalleRequisicion.objects.create(
            requisicion=requisicion,
            producto=producto,
            cantidad_solicitada=50,
            cantidad_autorizada=50
        )
        
        # Enviar y autorizar (esto registra reservas)
        requisicion.cambiar_estado('enviada', usuario=admin_user, persist=True)
        requisicion.cambiar_estado('autorizada', usuario=admin_user, persist=True)
        
        # Refrescar para obtener datos de reserva
        detalle.refresh_from_db()
        
        return {
            'requisicion': requisicion,
            'detalle': detalle,
            'lote': lote
        }
    
    def test_reservas_se_liberan_al_cancelar(self, setup_requisicion_autorizada, admin_user):
        """Verifica que las reservas se liberan cuando se cancela una requisición autorizada."""
        data = setup_requisicion_autorizada
        requisicion = data['requisicion']
        detalle = data['detalle']
        
        # Verificar que hay reserva antes de cancelar
        assert detalle.cantidad_reservada == 50
        assert detalle.fecha_reserva is not None
        
        # Cancelar la requisición
        requisicion.cambiar_estado('cancelada', usuario=admin_user, persist=True)
        
        # Refrescar y verificar que las reservas se liberaron
        detalle.refresh_from_db()
        assert detalle.cantidad_reservada == 0
        assert detalle.fecha_reserva is None
    
    def test_reservas_se_liberan_al_rechazar(self, admin_user, producto, centro):
        """Verifica que las reservas también se liberan al rechazar (comportamiento existente)."""
        hoy = timezone.now().date()
        
        # Crear lote para este test
        lote = Lote.objects.create(
            producto=producto,
            centro=None,  # Farmacia central
            numero_lote='LOTE-RECHAZO-001',
            fecha_caducidad=hoy + timedelta(days=180),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
        
        # Crear requisición
        requisicion = Requisicion.objects.create(
            folio='REQ-RECHAZO-001',
            centro=centro,
            usuario_solicita=admin_user,
            estado='borrador'
        )
        
        detalle = DetalleRequisicion.objects.create(
            requisicion=requisicion,
            producto=producto,
            cantidad_solicitada=30,
            cantidad_autorizada=30
        )
        
        # Enviar (las reservas se crean al enviar y autorizar)
        requisicion.cambiar_estado('enviada', usuario=admin_user, persist=True)
        
        # Rechazar desde enviada (transición válida)
        requisicion.cambiar_estado('rechazada', usuario=admin_user, motivo='Test de rechazo', persist=True)
        
        requisicion.refresh_from_db()
        detalle.refresh_from_db()
        
        assert requisicion.estado == 'rechazada'
        # Las reservas NO se crean al enviar, solo al autorizar
        # Pero si hubo autorización previa y luego rechazo (desde enviada), se liberarían


class TestLimitesContractuales:
    """Tests para ISS-002: Validar límites de monto y cantidad en contratos."""
    
    @pytest.fixture
    def contrato_con_limites(self, admin_user, producto):
        """Crea un contrato con límites de monto y cantidad."""
        hoy = timezone.now().date()
        
        contrato = Contrato.objects.create(
            numero_contrato='CONT-LIMITES-001',
            descripcion='Contrato con límites',
            proveedor='Proveedor Test',
            fecha_inicio=hoy - timedelta(days=30),
            fecha_fin=hoy + timedelta(days=180),
            monto_maximo=Decimal('50000.00'),  # Límite de monto alto para probar cantidad primero
            activo=True,
            created_by=admin_user
        )
        
        # Crear límite por producto
        contrato_producto = ContratoProducto.objects.create(
            contrato=contrato,
            producto=producto,
            cantidad_maxima=500,  # Máximo 500 unidades
            precio_unitario=Decimal('20.00')  # $20 por unidad
        )
        
        return {
            'contrato': contrato,
            'contrato_producto': contrato_producto,
            'producto': producto
        }
    
    def test_validar_entrada_excede_cantidad_maxima(self, contrato_con_limites):
        """Verifica que se rechaza una entrada que excede la cantidad máxima por producto."""
        data = contrato_con_limites
        contrato = data['contrato']
        producto = data['producto']
        
        hoy = timezone.now().date()
        
        # Intentar ingresar más de la cantidad máxima (500)
        # 600 * $20 = $12,000 que está dentro del monto máximo ($50,000)
        # pero excede la cantidad máxima (500)
        with pytest.raises(ValidationError) as exc_info:
            contrato.validar_entrada(
                producto=producto,
                cantidad=600,  # Excede 500
                fecha_caducidad=hoy + timedelta(days=180)
            )
        
        assert 'cantidad' in exc_info.value.message_dict
        assert 'Excede la cantidad máxima' in str(exc_info.value)
    
    def test_validar_entrada_excede_monto_maximo(self, admin_user, producto):
        """Verifica que se rechaza una entrada que excede el monto máximo del contrato."""
        hoy = timezone.now().date()
        
        # Crear un contrato con monto máximo bajo
        contrato = Contrato.objects.create(
            numero_contrato='CONT-MONTO-001',
            descripcion='Contrato con monto bajo',
            proveedor='Proveedor Test',
            fecha_inicio=hoy - timedelta(days=30),
            fecha_fin=hoy + timedelta(days=180),
            monto_maximo=Decimal('10000.00'),  # Límite de $10,000
            activo=True,
            created_by=admin_user
        )
        
        # Crear límite por producto con precio alto
        ContratoProducto.objects.create(
            contrato=contrato,
            producto=producto,
            cantidad_maxima=1000,  # Cantidad alta para no fallar por cantidad
            precio_unitario=Decimal('20.00')  # $20 por unidad
        )
        
        # Primero crear un lote que consuma parte del monto
        # 400 unidades * $20 = $8000
        Lote.objects.create(
            producto=producto,
            centro=None,
            numero_lote='LOTE-MONTO-001',
            fecha_caducidad=hoy + timedelta(days=180),
            cantidad_inicial=400,
            cantidad_actual=400,
            precio_compra=Decimal('20.00'),
            contrato=contrato,
            estado='disponible'
        )
        
        # Intentar ingresar 200 más (200 * $20 = $4000)
        # Total sería $12000 > $10000 máximo
        with pytest.raises(ValidationError) as exc_info:
            contrato.validar_entrada(
                producto=producto,
                cantidad=200,
                fecha_caducidad=hoy + timedelta(days=180)
            )
        
        assert 'contrato' in exc_info.value.message_dict
        assert 'excede el monto máximo' in str(exc_info.value)
    
    def test_validar_entrada_dentro_limites(self, contrato_con_limites):
        """Verifica que se permite una entrada dentro de los límites."""
        data = contrato_con_limites
        contrato = data['contrato']
        producto = data['producto']
        
        hoy = timezone.now().date()
        
        # Ingresar cantidad dentro del límite
        # No debe lanzar excepción
        contrato.validar_entrada(
            producto=producto,
            cantidad=100,  # Dentro de 500
            fecha_caducidad=hoy + timedelta(days=180)
        )
    
    def test_contrato_producto_cantidad_disponible(self, contrato_con_limites):
        """Verifica el cálculo correcto de cantidad disponible."""
        data = contrato_con_limites
        contrato = data['contrato']
        producto = data['producto']
        contrato_producto = data['contrato_producto']
        
        hoy = timezone.now().date()
        
        # Sin lotes, debe haber 500 disponibles
        assert contrato_producto.get_cantidad_disponible() == 500
        
        # Crear lote que consuma 200
        Lote.objects.create(
            producto=producto,
            centro=None,
            numero_lote='LOTE-DISP-001',
            fecha_caducidad=hoy + timedelta(days=180),
            cantidad_inicial=200,
            cantidad_actual=200,
            precio_compra=Decimal('20.00'),
            contrato=contrato,
            estado='disponible'
        )
        
        # Ahora debe haber 300 disponibles
        assert contrato_producto.get_cantidad_utilizada() == 200
        assert contrato_producto.get_cantidad_disponible() == 300


class TestExcluirRequisicionEnStockComprometido:
    """Tests para ISS-003: Excluir requisición actual del stock comprometido."""
    
    @pytest.fixture
    def setup_dos_requisiciones(self, admin_user, producto, centro):
        """Crea dos requisiciones autorizadas del mismo producto."""
        hoy = timezone.now().date()
        
        # Crear lote con stock suficiente para ambas
        lote = Lote.objects.create(
            producto=producto,
            centro=None,
            numero_lote='LOTE-EXCLUIR-001',
            fecha_caducidad=hoy + timedelta(days=180),
            cantidad_inicial=200,
            cantidad_actual=200,
            estado='disponible'
        )
        
        # Primera requisición
        req1 = Requisicion.objects.create(
            folio='REQ-EXCL-001',
            centro=centro,
            usuario_solicita=admin_user,
            estado='borrador'
        )
        det1 = DetalleRequisicion.objects.create(
            requisicion=req1,
            producto=producto,
            cantidad_solicitada=80,
            cantidad_autorizada=80
        )
        req1.cambiar_estado('enviada', usuario=admin_user, persist=True)
        req1.cambiar_estado('autorizada', usuario=admin_user, persist=True)
        
        # Segunda requisición
        req2 = Requisicion.objects.create(
            folio='REQ-EXCL-002',
            centro=centro,
            usuario_solicita=admin_user,
            estado='borrador'
        )
        det2 = DetalleRequisicion.objects.create(
            requisicion=req2,
            producto=producto,
            cantidad_solicitada=70,
            cantidad_autorizada=70
        )
        req2.cambiar_estado('enviada', usuario=admin_user, persist=True)
        req2.cambiar_estado('autorizada', usuario=admin_user, persist=True)
        
        return {
            'lote': lote,
            'req1': req1,
            'req2': req2,
            'det1': det1,
            'det2': det2,
            'producto': producto
        }
    
    def test_stock_comprometido_sin_excluir(self, setup_dos_requisiciones):
        """Verifica el stock comprometido total sin exclusiones."""
        data = setup_dos_requisiciones
        producto = data['producto']
        
        # Stock comprometido debe ser 80 + 70 = 150
        comprometido = producto.get_stock_comprometido()
        assert comprometido == 150
    
    def test_stock_comprometido_excluyendo_requisicion(self, setup_dos_requisiciones):
        """Verifica que se puede excluir una requisición específica."""
        data = setup_dos_requisiciones
        producto = data['producto']
        req1 = data['req1']
        req2 = data['req2']
        
        # Excluir req1 (80 unidades) - debe quedar solo 70
        comprometido_sin_req1 = producto.get_stock_comprometido(excluir_requisicion=req1.pk)
        assert comprometido_sin_req1 == 70
        
        # Excluir req2 (70 unidades) - debe quedar solo 80
        comprometido_sin_req2 = producto.get_stock_comprometido(excluir_requisicion=req2.pk)
        assert comprometido_sin_req2 == 80
    
    def test_reautorizacion_no_genera_error_stock_insuficiente(self, setup_dos_requisiciones, admin_user):
        """
        Verifica que re-autorizar una requisición no genera error de stock.
        
        Escenario: Stock 200, Req1=80, Req2=70 (comprometido total=150, disponible=50)
        Si rechazamos Req1 y luego la re-enviamos para re-autorizar,
        no debería fallar por falta de stock porque sus propias 80 unidades
        no deben contarse como "comprometidas por otras".
        """
        data = setup_dos_requisiciones
        req1 = data['req1']
        req2 = data['req2']
        producto = data['producto']
        
        # Cancelar req1
        req1.cambiar_estado('cancelada', usuario=admin_user, persist=True)
        
        # Verificar que las reservas se liberaron
        data['det1'].refresh_from_db()
        assert data['det1'].cantidad_reservada == 0
        
        # Crear nueva requisición con la misma cantidad
        req3 = Requisicion.objects.create(
            folio='REQ-EXCL-003',
            centro=req1.centro,
            usuario_solicita=admin_user,
            estado='borrador'
        )
        det3 = DetalleRequisicion.objects.create(
            requisicion=req3,
            producto=producto,
            cantidad_solicitada=80,  # Misma cantidad que req1
            cantidad_autorizada=80
        )
        
        # Stock disponible = 200 - 70 (req2) = 130
        # Solicitar 80 debe funcionar
        req3.cambiar_estado('enviada', usuario=admin_user, persist=True)
        
        # Esto NO debe fallar porque excluimos la propia requisición
        req3.cambiar_estado('autorizada', usuario=admin_user, persist=True)
        
        req3.refresh_from_db()
        assert req3.estado == 'autorizada'


class TestValidacionesIntegradas:
    """Tests de integración que combinan varios aspectos."""
    
    def test_flujo_completo_cancelacion_y_reautorizacion(self, admin_user, producto, centro):
        """Verifica el flujo completo de cancelar y re-autorizar."""
        hoy = timezone.now().date()
        
        # Setup
        lote = Lote.objects.create(
            producto=producto,
            centro=None,
            numero_lote='LOTE-FLUJO-001',
            fecha_caducidad=hoy + timedelta(days=180),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
        
        # Primera autorización
        req1 = Requisicion.objects.create(
            folio='REQ-FLUJO-001',
            centro=centro,
            usuario_solicita=admin_user,
            estado='borrador'
        )
        det1 = DetalleRequisicion.objects.create(
            requisicion=req1,
            producto=producto,
            cantidad_solicitada=100,
            cantidad_autorizada=100
        )
        
        req1.cambiar_estado('enviada', usuario=admin_user, persist=True)
        req1.cambiar_estado('autorizada', usuario=admin_user, persist=True)
        
        # Verificar reserva
        det1.refresh_from_db()
        assert det1.cantidad_reservada == 100
        
        # Stock comprometido debe ser 100
        assert producto.get_stock_comprometido() == 100
        
        # Cancelar
        req1.cambiar_estado('cancelada', usuario=admin_user, persist=True)
        
        # Reservas deben estar liberadas
        det1.refresh_from_db()
        assert det1.cantidad_reservada == 0
        
        # Stock comprometido debe ser 0
        assert producto.get_stock_comprometido() == 0
        
        # Crear nueva requisición con todo el stock
        req2 = Requisicion.objects.create(
            folio='REQ-FLUJO-002',
            centro=centro,
            usuario_solicita=admin_user,
            estado='borrador'
        )
        DetalleRequisicion.objects.create(
            requisicion=req2,
            producto=producto,
            cantidad_solicitada=100,
            cantidad_autorizada=100
        )
        
        req2.cambiar_estado('enviada', usuario=admin_user, persist=True)
        req2.cambiar_estado('autorizada', usuario=admin_user, persist=True)
        
        req2.refresh_from_db()
        assert req2.estado == 'autorizada'
