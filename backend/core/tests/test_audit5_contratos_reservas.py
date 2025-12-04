"""
Tests para fixes de auditoría 5: ISS-001 a ISS-007

ISS-001/003: Configuración de contrato obligatorio y caducidad (ya parametrizable)
ISS-002: Reservas de stock al autorizar
ISS-005: Modelo Contrato con límites
ISS-006: Trazabilidad de recepción por lotes
"""
from django.test import TestCase, override_settings
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal

from core.models import (
    Centro, Producto, Lote, Requisicion, DetalleRequisicion,
    Contrato, ContratoProducto, DetalleRecepcion, DetalleSurtido
)

User = get_user_model()


class ContratoModelTests(TestCase):
    """
    ISS-005: Tests para el modelo Contrato.
    """
    
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            username='admin_contrato',
            email='admin@contrato.test',
            password='Admin@123'
        )
        
        cls.producto = Producto.objects.create(
            clave='PROD-CONT-001',
            descripcion='Producto para test contrato',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            stock_minimo=10,
            activo=True
        )
    
    def test_crear_contrato_valido(self):
        """ISS-005: Crear contrato con datos válidos"""
        contrato = Contrato.objects.create(
            numero_contrato='CONT-2025-001',
            descripcion='Contrato de prueba',
            proveedor='Proveedor Test',
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=365),
            monto_maximo=Decimal('100000.00'),
            activo=True,
            created_by=self.admin
        )
        
        self.assertEqual(contrato.numero_contrato, 'CONT-2025-001')
        self.assertTrue(contrato.esta_vigente())
    
    def test_contrato_fecha_fin_antes_inicio_invalido(self):
        """ISS-005: Fecha fin no puede ser antes de inicio"""
        contrato = Contrato(
            numero_contrato='CONT-INVALID-001',
            proveedor='Proveedor',
            fecha_inicio=date.today(),
            fecha_fin=date.today() - timedelta(days=30)  # Antes de inicio
        )
        
        with self.assertRaises(ValidationError) as ctx:
            contrato.full_clean()
        
        self.assertIn('fecha_fin', ctx.exception.message_dict)
    
    def test_contrato_no_vigente_por_fecha(self):
        """ISS-005: Contrato fuera de vigencia no es válido para entradas"""
        # Contrato expirado
        contrato_expirado = Contrato.objects.create(
            numero_contrato='CONT-EXPIRADO',
            proveedor='Proveedor',
            fecha_inicio=date.today() - timedelta(days=365),
            fecha_fin=date.today() - timedelta(days=30)  # Ya expiró
        )
        
        self.assertFalse(contrato_expirado.esta_vigente())
    
    def test_contrato_no_vigente_por_inactivo(self):
        """ISS-005: Contrato inactivo no es vigente aunque fechas sean válidas"""
        contrato_inactivo = Contrato.objects.create(
            numero_contrato='CONT-INACTIVO',
            proveedor='Proveedor',
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=365),
            activo=False  # Inactivo
        )
        
        self.assertFalse(contrato_inactivo.esta_vigente())


class ContratoProductoLimiteTests(TestCase):
    """
    ISS-005: Tests para límites de producto por contrato.
    """
    
    @classmethod
    def setUpTestData(cls):
        cls.producto = Producto.objects.create(
            clave='PROD-LIMITE-001',
            descripcion='Producto para test límites',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('15.00'),
            stock_minimo=10,
            activo=True
        )
        
        cls.contrato = Contrato.objects.create(
            numero_contrato='CONT-LIMITE-001',
            proveedor='Proveedor Límites',
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=365),
            activo=True
        )
    
    def test_crear_limite_producto(self):
        """ISS-005: Crear límite de producto por contrato"""
        limite = ContratoProducto.objects.create(
            contrato=self.contrato,
            producto=self.producto,
            cantidad_maxima=1000,
            precio_unitario=Decimal('12.50')
        )
        
        self.assertEqual(limite.cantidad_maxima, 1000)
        self.assertEqual(limite.get_cantidad_disponible(), 1000)
    
    def test_cantidad_utilizada_con_lotes(self):
        """ISS-005: Calcular cantidad utilizada de un contrato"""
        # Crear límite
        limite = ContratoProducto.objects.create(
            contrato=self.contrato,
            producto=self.producto,
            cantidad_maxima=500,
            precio_unitario=Decimal('12.50')
        )
        
        # Crear lote asociado al contrato
        Lote.objects.create(
            producto=self.producto,
            centro=None,
            numero_lote='LOTE-CONT-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=200,
            cantidad_actual=200,
            estado='disponible',
            contrato=self.contrato
        )
        
        # Verificar cantidad utilizada
        self.assertEqual(limite.get_cantidad_utilizada(), 200)
        self.assertEqual(limite.get_cantidad_disponible(), 300)
        self.assertTrue(limite.puede_ingresar(300))
        self.assertFalse(limite.puede_ingresar(301))


class ReservaStockAutorizacionTests(TestCase):
    """
    ISS-002: Tests para reserva de stock al autorizar.
    """
    
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            username='admin_reserva',
            email='admin@reserva.test',
            password='Admin@123',
            rol='admin'
        )
        
        cls.centro = Centro.objects.create(
            clave='CENT-RESERVA',
            nombre='Centro Reserva',
            direccion='Dir',
            telefono='555-0001',
            activo=True
        )
        
        cls.producto = Producto.objects.create(
            clave='PROD-RESERVA-001',
            descripcion='Producto para test reserva',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            stock_minimo=10,
            activo=True
        )
        
        cls.lote = Lote.objects.create(
            producto=cls.producto,
            centro=None,
            numero_lote='LOTE-RESERVA-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
    
    def test_reserva_registrada_al_autorizar(self):
        """ISS-002: Al autorizar se registra la reserva en detalles"""
        requisicion = Requisicion.objects.create(
            folio='REQ-RESERVA-001',
            centro=self.centro,
            usuario_solicita=self.admin,
            estado='enviada'
        )
        detalle = DetalleRequisicion.objects.create(
            requisicion=requisicion,
            producto=self.producto,
            cantidad_solicitada=30,
            cantidad_autorizada=30
        )
        
        # Autorizar
        requisicion.cambiar_estado('autorizada', usuario=self.admin)
        
        # Verificar reserva
        detalle.refresh_from_db()
        self.assertEqual(detalle.cantidad_reservada, 30)
        self.assertIsNotNone(detalle.fecha_reserva)
    
    def test_reserva_liberada_al_rechazar(self):
        """ISS-002: Al rechazar se liberan las reservas"""
        requisicion = Requisicion.objects.create(
            folio='REQ-RESERVA-002',
            centro=self.centro,
            usuario_solicita=self.admin,
            estado='enviada'
        )
        detalle = DetalleRequisicion.objects.create(
            requisicion=requisicion,
            producto=self.producto,
            cantidad_solicitada=20,
            cantidad_autorizada=20
        )
        
        # Autorizar primero
        requisicion.cambiar_estado('autorizada', usuario=self.admin)
        detalle.refresh_from_db()
        self.assertEqual(detalle.cantidad_reservada, 20)
        
        # Ahora rechazar - necesitamos volver a enviada primero (o usar estado válido)
        # En el flujo normal, una vez autorizada no se puede rechazar directamente
        # Pero podemos verificar que _liberar_reservas funciona
        requisicion._liberar_reservas()
        detalle.refresh_from_db()
        self.assertEqual(detalle.cantidad_reservada, 0)
        self.assertIsNone(detalle.fecha_reserva)


class DetalleRecepcionTests(TestCase):
    """
    ISS-006: Tests para trazabilidad de recepción.
    """
    
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            username='admin_recepcion',
            email='admin@recepcion.test',
            password='Admin@123'
        )
        
        cls.centro = Centro.objects.create(
            clave='CENT-RECEP',
            nombre='Centro Recepción',
            direccion='Dir',
            telefono='555-0002',
            activo=True
        )
        
        cls.producto = Producto.objects.create(
            clave='PROD-RECEP-001',
            descripcion='Producto para test recepción',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            stock_minimo=10,
            activo=True
        )
        
        cls.lote_farmacia = Lote.objects.create(
            producto=cls.producto,
            centro=None,
            numero_lote='LOTE-RECEP-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
    
    def test_crear_detalle_recepcion(self):
        """ISS-006: Crear detalle de recepción para trazabilidad"""
        # Crear requisición y detalle
        requisicion = Requisicion.objects.create(
            folio='REQ-RECEP-001',
            centro=self.centro,
            usuario_solicita=self.admin,
            estado='surtida'
        )
        detalle_req = DetalleRequisicion.objects.create(
            requisicion=requisicion,
            producto=self.producto,
            cantidad_solicitada=50,
            cantidad_autorizada=50,
            cantidad_surtida=50
        )
        
        # Crear lote en centro (simulando recepción)
        lote_centro = Lote.objects.create(
            producto=self.producto,
            centro=self.centro,
            numero_lote='LOTE-RECEP-001',
            fecha_caducidad=self.lote_farmacia.fecha_caducidad,
            cantidad_inicial=50,
            cantidad_actual=50,
            estado='disponible',
            lote_origen=self.lote_farmacia
        )
        
        # Crear detalle de recepción
        recepcion = DetalleRecepcion.objects.create(
            detalle_requisicion=detalle_req,
            lote_centro=lote_centro,
            cantidad_recibida=50,
            cantidad_esperada=50,
            usuario=self.admin
        )
        
        self.assertEqual(recepcion.cantidad_recibida, 50)
        self.assertFalse(recepcion.tiene_discrepancia)
    
    def test_detectar_discrepancia_recepcion(self):
        """ISS-006: Detectar discrepancia entre surtido y recibido"""
        requisicion = Requisicion.objects.create(
            folio='REQ-RECEP-002',
            centro=self.centro,
            usuario_solicita=self.admin,
            estado='surtida'
        )
        detalle_req = DetalleRequisicion.objects.create(
            requisicion=requisicion,
            producto=self.producto,
            cantidad_solicitada=50,
            cantidad_autorizada=50,
            cantidad_surtida=50
        )
        
        lote_centro = Lote.objects.create(
            producto=self.producto,
            centro=self.centro,
            numero_lote='LOTE-RECEP-001',  # Debe coincidir con lote_origen
            fecha_caducidad=self.lote_farmacia.fecha_caducidad,
            cantidad_inicial=45,  # Recibió menos
            cantidad_actual=45,
            estado='disponible',
            lote_origen=self.lote_farmacia
        )
        
        # Crear recepción con discrepancia
        recepcion = DetalleRecepcion(
            detalle_requisicion=detalle_req,
            lote_centro=lote_centro,
            cantidad_recibida=45,  # Recibió 45
            cantidad_esperada=50,  # Esperaba 50
            observaciones='Faltaron 5 unidades'
        )
        recepcion.full_clean()  # Esto debe detectar discrepancia
        recepcion.save()
        
        self.assertTrue(recepcion.tiene_discrepancia)


class IntegracionContratoLoteTests(TestCase):
    """
    Tests de integración entre Contrato y Lote.
    """
    
    @classmethod
    def setUpTestData(cls):
        cls.producto = Producto.objects.create(
            clave='PROD-INTEG-CONT',
            descripcion='Producto integración contrato',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('20.00'),
            stock_minimo=10,
            activo=True
        )
        
        cls.contrato = Contrato.objects.create(
            numero_contrato='CONT-INTEG-001',
            proveedor='Proveedor Integración',
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=365),
            activo=True
        )
        
        ContratoProducto.objects.create(
            contrato=cls.contrato,
            producto=cls.producto,
            cantidad_maxima=500,
            precio_unitario=Decimal('18.00')
        )
    
    def test_lote_con_referencia_contrato(self):
        """ISS-005: Lote puede referenciar contrato para trazabilidad"""
        lote = Lote.objects.create(
            producto=self.producto,
            centro=None,
            numero_lote='LOTE-CONT-INTEG',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible',
            contrato=self.contrato,
            numero_contrato=self.contrato.numero_contrato
        )
        
        self.assertEqual(lote.contrato, self.contrato)
        self.assertEqual(lote.numero_contrato, 'CONT-INTEG-001')
    
    def test_validacion_entrada_contrato(self):
        """ISS-005: Validar entrada contra contrato"""
        # Entrada válida
        self.contrato.validar_entrada(
            producto=self.producto,
            cantidad=100,
            fecha_caducidad=date.today() + timedelta(days=365)
        )  # No debe lanzar excepción
        
        # Contrato inactivo
        contrato_inactivo = Contrato.objects.create(
            numero_contrato='CONT-INACTIVO-TEST',
            proveedor='Proveedor',
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=365),
            activo=False
        )
        
        with self.assertRaises(ValidationError):
            contrato_inactivo.validar_entrada(
                producto=self.producto,
                cantidad=50
            )
