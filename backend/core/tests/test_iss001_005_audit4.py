"""
Tests para fixes de auditoría 4: ISS-001 a ISS-005

ISS-001: Stock comprometido debe filtrar por centro
ISS-002: Validación de contrato obligatorio (parametrizable)
ISS-003: Resumen de stock consistente por centro
ISS-004: Validación de caducidad mínima (parametrizable)
ISS-005: Stock comprometido considera lotes vencidos
"""
from django.test import TestCase, override_settings
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from decimal import Decimal

from core.models import Centro, Producto, Lote, Requisicion, DetalleRequisicion

User = get_user_model()


class StockComprometidoPorCentroTests(TestCase):
    """
    ISS-001/ISS-003: Tests para verificar que el stock comprometido
    se filtra correctamente por centro.
    """
    
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            username='admin_iss001',
            email='admin@iss001.test',
            password='Admin@123'
        )
        
        cls.centro_a = Centro.objects.create(
            clave='CENT-A-001',
            nombre='Centro A ISS001',
            direccion='Dir A',
            telefono='555-0001',
            activo=True
        )
        
        cls.centro_b = Centro.objects.create(
            clave='CENT-B-001',
            nombre='Centro B ISS001',
            direccion='Dir B',
            telefono='555-0002',
            activo=True
        )
        
        cls.producto = Producto.objects.create(
            clave='PROD-ISS001-001',
            descripcion='Producto para test ISS001',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            stock_minimo=10,
            activo=True
        )
        
        # Crear lote en farmacia central con 100 unidades
        cls.lote_farmacia = Lote.objects.create(
            producto=cls.producto,
            centro=None,  # Farmacia central
            numero_lote='LOTE-ISS001-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
    
    def test_stock_comprometido_aislado_por_centro(self):
        """ISS-001: El comprometido de un centro no afecta a otro"""
        # Crear requisición autorizada para Centro A (compromete 30)
        req_a = Requisicion.objects.create(
            folio='REQ-ISS001-A',
            centro=self.centro_a,
            usuario_solicita=self.admin,
            estado='autorizada'
        )
        DetalleRequisicion.objects.create(
            requisicion=req_a,
            producto=self.producto,
            cantidad_solicitada=30,
            cantidad_autorizada=30
        )
        
        # Crear requisición autorizada para Centro B (compromete 20)
        req_b = Requisicion.objects.create(
            folio='REQ-ISS001-B',
            centro=self.centro_b,
            usuario_solicita=self.admin,
            estado='autorizada'
        )
        DetalleRequisicion.objects.create(
            requisicion=req_b,
            producto=self.producto,
            cantidad_solicitada=20,
            cantidad_autorizada=20
        )
        
        # Comprometido global (farmacia central) = 50 (30 + 20)
        self.assertEqual(
            self.producto.get_stock_comprometido(centro=None),
            50,
            "Comprometido global debe sumar todas las requisiciones"
        )
        
        # Comprometido Centro A = 30 (solo su requisición)
        self.assertEqual(
            self.producto.get_stock_comprometido(centro=self.centro_a),
            30,
            "Comprometido Centro A debe ser solo de sus requisiciones"
        )
        
        # Comprometido Centro B = 20 (solo su requisición)
        self.assertEqual(
            self.producto.get_stock_comprometido(centro=self.centro_b),
            20,
            "Comprometido Centro B debe ser solo de sus requisiciones"
        )
    
    def test_stock_disponible_real_consistente_por_centro(self):
        """ISS-001: Stock disponible usa comprometido del mismo centro"""
        # Crear requisición autorizada para Centro A (compromete 40)
        req = Requisicion.objects.create(
            folio='REQ-ISS001-DISP',
            centro=self.centro_a,
            usuario_solicita=self.admin,
            estado='autorizada'
        )
        DetalleRequisicion.objects.create(
            requisicion=req,
            producto=self.producto,
            cantidad_solicitada=40,
            cantidad_autorizada=40
        )
        
        # Disponible en farmacia central = 100 - 40 = 60 (considerando comprometido global)
        disponible_farmacia = self.producto.get_stock_disponible_real(centro=None)
        self.assertEqual(disponible_farmacia, 60)
        
        # Disponible para Centro B (no tiene stock propio, pero el comprometido
        # de Centro A no debería afectar su cálculo si consultamos SU stock)
        # Nota: Centro B no tiene lotes propios, así que su stock actual es 0
        disponible_centro_b = self.producto.get_stock_disponible_real(centro=self.centro_b)
        self.assertEqual(disponible_centro_b, 0, "Centro B no tiene stock propio")
    
    def test_resumen_stock_incluye_indicador_centro(self):
        """ISS-003: Resumen incluye indicador de tipo de consulta"""
        resumen_farmacia = self.producto.get_resumen_stock(centro=None)
        self.assertTrue(resumen_farmacia['es_farmacia_central'])
        self.assertIsNone(resumen_farmacia['centro_id'])
        
        resumen_centro = self.producto.get_resumen_stock(centro=self.centro_a)
        self.assertFalse(resumen_centro['es_farmacia_central'])
        self.assertEqual(resumen_centro['centro_id'], self.centro_a.pk)


class StockComprometidoLotesVencidosTests(TestCase):
    """
    ISS-005: Tests para verificar que el stock comprometido
    considera la caducidad de los lotes.
    """
    
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            username='admin_iss005',
            email='admin@iss005.test',
            password='Admin@123'
        )
        
        cls.centro = Centro.objects.create(
            clave='CENT-ISS005',
            nombre='Centro ISS005',
            direccion='Dir',
            telefono='555-0005',
            activo=True
        )
        
        cls.producto = Producto.objects.create(
            clave='PROD-ISS005-001',
            descripcion='Producto para test ISS005',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            stock_minimo=10,
            activo=True
        )
    
    def test_comprometido_cero_si_no_hay_stock_vigente(self):
        """ISS-005: Si no hay lotes vigentes, comprometido debe ser 0"""
        # Crear lote VENCIDO en farmacia central
        Lote.objects.create(
            producto=self.producto,
            centro=None,
            numero_lote='LOTE-ISS005-VENCIDO',
            fecha_caducidad=date.today() - timedelta(days=30),  # Vencido
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='vencido'
        )
        
        # Crear requisición autorizada (compromete 50)
        req = Requisicion.objects.create(
            folio='REQ-ISS005-001',
            centro=self.centro,
            usuario_solicita=self.admin,
            estado='autorizada'
        )
        DetalleRequisicion.objects.create(
            requisicion=req,
            producto=self.producto,
            cantidad_solicitada=50,
            cantidad_autorizada=50
        )
        
        # El comprometido debe ser 0 porque no hay stock vigente
        comprometido = self.producto.get_stock_comprometido(excluir_lotes_vencidos=True)
        self.assertEqual(
            comprometido, 0,
            "Comprometido debe ser 0 si no hay lotes vigentes para cumplirlo"
        )
    
    def test_comprometido_normal_si_hay_stock_vigente(self):
        """ISS-005: Si hay lotes vigentes, comprometido se calcula normal"""
        # Crear lote VIGENTE en farmacia central
        Lote.objects.create(
            producto=self.producto,
            centro=None,
            numero_lote='LOTE-ISS005-VIGENTE',
            fecha_caducidad=date.today() + timedelta(days=365),  # Vigente
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
        
        # Crear requisición autorizada (compromete 30)
        req = Requisicion.objects.create(
            folio='REQ-ISS005-002',
            centro=self.centro,
            usuario_solicita=self.admin,
            estado='autorizada'
        )
        DetalleRequisicion.objects.create(
            requisicion=req,
            producto=self.producto,
            cantidad_solicitada=30,
            cantidad_autorizada=30
        )
        
        # El comprometido debe ser 30
        comprometido = self.producto.get_stock_comprometido(excluir_lotes_vencidos=True)
        self.assertEqual(comprometido, 30)


class ValidacionContratoTests(TestCase):
    """
    ISS-002: Tests para validación de contrato obligatorio.
    """
    
    @classmethod
    def setUpTestData(cls):
        cls.producto = Producto.objects.create(
            clave='PROD-ISS002-001',
            descripcion='Producto para test ISS002',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            stock_minimo=10,
            activo=True
        )
    
    @override_settings(LOTE_REQUIRE_CONTRATO=True)
    def test_lote_sin_contrato_rechazado_si_obligatorio(self):
        """ISS-002: Lote sin contrato es rechazado si REQUIRE_CONTRATO=True"""
        lote = Lote(
            producto=self.producto,
            centro=None,  # Farmacia central
            numero_lote='LOTE-ISS002-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible',
            numero_contrato=''  # Sin contrato
        )
        
        with self.assertRaises(ValidationError) as ctx:
            lote.full_clean()
        
        self.assertIn('numero_contrato', ctx.exception.message_dict)
    
    @override_settings(LOTE_REQUIRE_CONTRATO=False)
    def test_lote_sin_contrato_permitido_si_no_obligatorio(self):
        """ISS-002: Lote sin contrato es permitido si REQUIRE_CONTRATO=False"""
        lote = Lote(
            producto=self.producto,
            centro=None,  # Farmacia central
            numero_lote='LOTE-ISS002-002',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible',
            numero_contrato=''  # Sin contrato
        )
        
        # No debe lanzar excepción
        lote.full_clean()
        lote.save()
        self.assertTrue(lote.pk is not None)
    
    def test_lote_centro_no_requiere_contrato(self):
        """ISS-002: Lotes de centros no requieren contrato (heredan de lote_origen)"""
        # Crear lote origen en farmacia
        lote_origen = Lote.objects.create(
            producto=self.producto,
            centro=None,
            numero_lote='LOTE-ISS002-ORIGEN',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible',
            numero_contrato='CONT-001'
        )
        
        # Crear centro
        centro = Centro.objects.create(
            clave='CENT-ISS002',
            nombre='Centro ISS002',
            direccion='Dir',
            telefono='555-0002',
            activo=True
        )
        
        # Lote en centro (sin contrato propio) - debe permitirse
        lote_centro = Lote(
            producto=self.producto,
            centro=centro,
            numero_lote='LOTE-ISS002-ORIGEN',  # Mismo número
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=50,
            cantidad_actual=50,
            estado='disponible',
            numero_contrato='',  # Sin contrato
            lote_origen=lote_origen
        )
        
        # No debe lanzar excepción (no se valida contrato para centros)
        lote_centro.full_clean()
        lote_centro.save()
        self.assertTrue(lote_centro.pk is not None)


class ValidacionCaducidadMinimaTests(TestCase):
    """
    ISS-004: Tests para validación de caducidad mínima parametrizable.
    """
    
    @classmethod
    def setUpTestData(cls):
        cls.producto = Producto.objects.create(
            clave='PROD-ISS004-001',
            descripcion='Producto para test ISS004',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            stock_minimo=10,
            activo=True
        )
    
    @override_settings(LOTE_MIN_DIAS_CADUCIDAD=90, LOTE_BLOQUEAR_CADUCIDAD_CORTA=True)
    def test_lote_caducidad_corta_rechazado_si_bloqueo_activo(self):
        """ISS-004: Lote con caducidad < mínimo es rechazado si bloqueo activo"""
        lote = Lote(
            producto=self.producto,
            centro=None,  # Farmacia central
            numero_lote='LOTE-ISS004-001',
            fecha_caducidad=date.today() + timedelta(days=30),  # Solo 30 días
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
        
        with self.assertRaises(ValidationError) as ctx:
            lote.full_clean()
        
        self.assertIn('fecha_caducidad', ctx.exception.message_dict)
    
    @override_settings(LOTE_MIN_DIAS_CADUCIDAD=90, LOTE_BLOQUEAR_CADUCIDAD_CORTA=False)
    def test_lote_caducidad_corta_permitido_con_warning(self):
        """ISS-004: Lote con caducidad corta permitido si bloqueo inactivo (solo warning)"""
        lote = Lote(
            producto=self.producto,
            centro=None,  # Farmacia central
            numero_lote='LOTE-ISS004-002',
            fecha_caducidad=date.today() + timedelta(days=30),  # Solo 30 días
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
        
        # No debe lanzar excepción, solo warning en logs
        lote.full_clean()
        lote.save()
        self.assertTrue(lote.pk is not None)
    
    @override_settings(LOTE_MIN_DIAS_CADUCIDAD=30, LOTE_BLOQUEAR_CADUCIDAD_CORTA=True)
    def test_lote_caducidad_suficiente_permitido(self):
        """ISS-004: Lote con caducidad >= mínimo es permitido"""
        lote = Lote(
            producto=self.producto,
            centro=None,  # Farmacia central
            numero_lote='LOTE-ISS004-003',
            fecha_caducidad=date.today() + timedelta(days=60),  # 60 días >= 30 mínimo
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
        
        # No debe lanzar excepción
        lote.full_clean()
        lote.save()
        self.assertTrue(lote.pk is not None)


class IntegracionStockPorCentroTests(TestCase):
    """
    Tests de integración para flujo completo de stock por centro.
    """
    
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin_integ',
            email='admin@integ.test',
            password='Admin@123'
        )
        
        self.centro_norte = Centro.objects.create(
            clave='CENT-NORTE',
            nombre='Centro Norte',
            direccion='Norte',
            telefono='555-1111',
            activo=True
        )
        
        self.centro_sur = Centro.objects.create(
            clave='CENT-SUR',
            nombre='Centro Sur',
            direccion='Sur',
            telefono='555-2222',
            activo=True
        )
        
        self.producto = Producto.objects.create(
            clave='PROD-INTEG-001',
            descripcion='Producto integración',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            stock_minimo=10,
            activo=True
        )
        
        # Stock en farmacia central: 200
        self.lote_farmacia = Lote.objects.create(
            producto=self.producto,
            centro=None,
            numero_lote='LOTE-INTEG-FARM',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=200,
            cantidad_actual=200,
            estado='disponible'
        )
    
    def test_flujo_requisiciones_multiples_centros(self):
        """Test de flujo con requisiciones de múltiples centros"""
        # Centro Norte solicita 80
        req_norte = Requisicion.objects.create(
            folio='REQ-NORTE-001',
            centro=self.centro_norte,
            usuario_solicita=self.admin,
            estado='autorizada'
        )
        DetalleRequisicion.objects.create(
            requisicion=req_norte,
            producto=self.producto,
            cantidad_solicitada=80,
            cantidad_autorizada=80
        )
        
        # Centro Sur solicita 60
        req_sur = Requisicion.objects.create(
            folio='REQ-SUR-001',
            centro=self.centro_sur,
            usuario_solicita=self.admin,
            estado='autorizada'
        )
        DetalleRequisicion.objects.create(
            requisicion=req_sur,
            producto=self.producto,
            cantidad_solicitada=60,
            cantidad_autorizada=60
        )
        
        # Verificar resumen de farmacia central
        resumen_farmacia = self.producto.get_resumen_stock(centro=None)
        self.assertEqual(resumen_farmacia['stock_actual'], 200)
        self.assertEqual(resumen_farmacia['stock_comprometido'], 140)  # 80 + 60
        self.assertEqual(resumen_farmacia['stock_disponible'], 60)
        self.assertTrue(resumen_farmacia['es_farmacia_central'])
        
        # Resumen de Centro Norte (solo ve SU comprometido)
        resumen_norte = self.producto.get_resumen_stock(centro=self.centro_norte)
        self.assertEqual(resumen_norte['stock_actual'], 0)  # No tiene lotes propios
        self.assertEqual(resumen_norte['stock_comprometido'], 80)  # Solo su req
        self.assertFalse(resumen_norte['es_farmacia_central'])
        
        # Resumen de Centro Sur
        resumen_sur = self.producto.get_resumen_stock(centro=self.centro_sur)
        self.assertEqual(resumen_sur['stock_actual'], 0)
        self.assertEqual(resumen_sur['stock_comprometido'], 60)  # Solo su req
