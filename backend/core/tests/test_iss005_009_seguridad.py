"""
Tests para ISS-005, ISS-006, ISS-007, ISS-009

ISS-005: Validación de archivos PDF
ISS-006: Caducidad automática de lotes
ISS-007: Campos de auditoría updated_by
ISS-009: Coherencia rol-permisos en usuarios
"""
from decimal import Decimal
from datetime import timedelta
from io import BytesIO
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from django.contrib.auth import get_user_model

from core.models import (
    Centro, Producto, Lote, Requisicion, DetalleRequisicion,
    validate_pdf_file, pdf_upload_path
)

User = get_user_model()


class ISS005PDFValidationTest(TestCase):
    """ISS-005: Tests de validación de archivos PDF"""
    
    def test_pdf_extension_valido(self):
        """PDFs con extensión .pdf deben pasar"""
        pdf_content = b'%PDF-1.4 fake pdf content'
        pdf_file = SimpleUploadedFile(
            name='documento.pdf',
            content=pdf_content,
            content_type='application/pdf'
        )
        # No debe lanzar excepción
        validate_pdf_file(pdf_file)
    
    def test_extension_no_pdf_rechazada(self):
        """Archivos sin extensión .pdf deben ser rechazados"""
        fake_file = SimpleUploadedFile(
            name='documento.exe',
            content=b'fake content',
            content_type='application/octet-stream'
        )
        with self.assertRaises(ValidationError) as ctx:
            validate_pdf_file(fake_file)
        self.assertIn('Solo se permiten archivos PDF', str(ctx.exception))
    
    def test_archivo_muy_grande_rechazado(self):
        """Archivos > 10MB deben ser rechazados"""
        # Crear archivo de 11MB
        large_content = b'x' * (11 * 1024 * 1024)
        large_file = SimpleUploadedFile(
            name='documento_grande.pdf',
            content=large_content,
            content_type='application/pdf'
        )
        with self.assertRaises(ValidationError) as ctx:
            validate_pdf_file(large_file)
        self.assertIn('demasiado grande', str(ctx.exception))
    
    def test_pdf_upload_path_genera_nombre_seguro(self):
        """La función pdf_upload_path genera nombres seguros"""
        # Crear instancia mock
        class MockLote:
            producto = type('obj', (object,), {'clave': 'MED-001'})()
            numero_lote = 'LOT-2024-001'
        
        path = pdf_upload_path(MockLote(), 'documento<>peligroso.pdf')
        
        # Verificar formato
        self.assertTrue(path.startswith('lotes/documentos/'))
        self.assertTrue(path.endswith('.pdf'))
        # No debe contener caracteres peligrosos
        self.assertNotIn('<', path)
        self.assertNotIn('>', path)
    
    def test_archivo_none_no_lanza_error(self):
        """validate_pdf_file con None no debe lanzar error"""
        validate_pdf_file(None)  # No debe lanzar


class ISS006CaducidadTest(TestCase):
    """ISS-006: Tests de caducidad automática"""
    
    @classmethod
    def setUpTestData(cls):
        cls.producto = Producto.objects.create(
            clave='MED-CAD-001',
            descripcion='Medicamento para test de caducidad',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('50.00')
        )
    
    def test_lote_vencido_puede_marcarse_vencido(self):
        """Lotes con fecha pasada pueden tener estado 'vencido'"""
        lote = Lote.objects.create(
            producto=self.producto,
            numero_lote='CAD-001',
            fecha_caducidad=timezone.now().date() - timedelta(days=30),
            cantidad_inicial=100,
            cantidad_actual=50,
            estado='vencido'  # Estado correcto para lote vencido
        )
        lote.refresh_from_db()
        self.assertEqual(lote.estado, 'vencido')
    
    def test_lote_disponible_con_fecha_futura(self):
        """Lotes con fecha futura pueden estar disponibles"""
        lote = Lote.objects.create(
            producto=self.producto,
            numero_lote='CAD-002',
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
        lote.refresh_from_db()
        self.assertEqual(lote.estado, 'disponible')


class ISS007AuditoriaTest(TestCase):
    """ISS-007: Tests de campos de auditoría"""
    
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(
            username='auditor1',
            email='auditor1@test.com',
            password='Test123!'
        )
        cls.user2 = User.objects.create_user(
            username='auditor2',
            email='auditor2@test.com',
            password='Test123!'
        )
        cls.producto = Producto.objects.create(
            clave='AUD-001',
            descripcion='Producto para auditoría',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00')
        )
    
    def test_lote_registra_created_by(self):
        """Lote debe registrar quién lo creó"""
        lote = Lote.objects.create(
            producto=self.producto,
            numero_lote='AUD-LOT-001',
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=50,
            cantidad_actual=50,
            created_by=self.user1
        )
        self.assertEqual(lote.created_by, self.user1)
    
    def test_lote_registra_updated_by(self):
        """Lote debe registrar quién lo modificó"""
        lote = Lote.objects.create(
            producto=self.producto,
            numero_lote='AUD-LOT-002',
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=50,
            cantidad_actual=50,
            created_by=self.user1
        )
        
        # Modificar con otro usuario
        lote.cantidad_actual = 40
        lote.updated_by = self.user2
        lote.save()
        
        lote.refresh_from_db()
        self.assertEqual(lote.updated_by, self.user2)
    
    def test_requisicion_registra_updated_by(self):
        """Requisición debe registrar quién la modificó"""
        centro = Centro.objects.create(clave='AUD-CTR', nombre='Centro Auditoría')
        
        req = Requisicion.objects.create(
            centro=centro,
            usuario_solicita=self.user1,
            estado='borrador'
        )
        
        # Modificar
        req.observaciones = 'Modificación de prueba'
        req.updated_by = self.user2
        req.save()
        
        req.refresh_from_db()
        self.assertEqual(req.updated_by, self.user2)


class ISS009PermisoRolTest(TestCase):
    """ISS-009: Tests de coherencia rol-permisos"""
    
    def test_usuario_normal_no_puede_tener_perm_usuarios(self):
        """Usuario normal no puede tener permiso de usuarios"""
        user = User(
            username='test_normal',
            email='test@test.com',
            rol='usuario_normal',
            perm_usuarios=True  # Intenta tener permiso no permitido
        )
        
        with self.assertRaises(ValidationError) as ctx:
            user.full_clean()
        
        self.assertIn('perm_usuarios', str(ctx.exception))
    
    def test_usuario_normal_no_puede_tener_perm_auditoria(self):
        """Usuario normal no puede tener permiso de auditoría"""
        user = User(
            username='test_normal2',
            email='test2@test.com',
            rol='usuario_normal',
            perm_auditoria=True
        )
        
        with self.assertRaises(ValidationError) as ctx:
            user.full_clean()
        
        self.assertIn('perm_auditoria', str(ctx.exception))
    
    def test_admin_puede_tener_todos_los_permisos(self):
        """Admin puede tener todos los permisos"""
        user = User(
            username='test_admin',
            email='admin@test.com',
            password='hashedpassword123',  # Required
            rol='admin_sistema',
            perm_usuarios=True,
            perm_auditoria=True,
            perm_centros=True
        )
        # No debe lanzar excepción de permisos
        user.clean()  # Solo validar clean(), no full_clean()
    
    def test_farmacia_puede_tener_permisos_limitados(self):
        """Farmacia puede tener sus permisos pero no de admin"""
        user = User(
            username='test_farmacia',
            email='farmacia@test.com',
            password='hashedpassword123',  # Required
            rol='farmacia',
            perm_productos=True,
            perm_lotes=True,
            perm_reportes=True
        )
        # No debe lanzar excepción de permisos
        user.clean()  # Solo validar clean()
    
    def test_farmacia_no_puede_tener_perm_centros(self):
        """Farmacia no puede tener permiso de centros"""
        user = User(
            username='test_farmacia2',
            email='farmacia2@test.com',
            rol='farmacia',
            perm_centros=True  # No permitido para farmacia
        )
        
        with self.assertRaises(ValidationError) as ctx:
            user.full_clean()
        
        self.assertIn('perm_centros', str(ctx.exception))
    
    def test_superuser_ignora_validacion_permisos(self):
        """Superuser puede tener cualquier configuración"""
        user = User(
            username='test_super',
            email='super@test.com',
            password='hashedpassword123',  # Required
            rol='usuario_normal',  # Rol bajo
            is_superuser=True,  # Pero es superuser
            perm_usuarios=True,  # Normalmente no permitido
            perm_auditoria=True
        )
        # No debe lanzar excepción porque es superuser
        user.clean()  # Solo validar clean()
    
    def test_get_permisos_efectivos_respeta_rol(self):
        """get_permisos_efectivos respeta límites del rol"""
        user = User(
            username='test_efectivos',
            email='efectivos@test.com',
            rol='usuario_normal',
            perm_dashboard=True,  # Permitido
            perm_productos=True,  # Permitido
        )
        
        permisos = user.get_permisos_efectivos()
        
        # Permisos permitidos deben estar activos
        self.assertTrue(permisos['perm_dashboard'])
        self.assertTrue(permisos['perm_productos'])
        # Permisos no permitidos por rol deben estar inactivos
        self.assertFalse(permisos['perm_usuarios'])
        self.assertFalse(permisos['perm_auditoria'])
    
    def test_get_permisos_efectivos_superuser(self):
        """Superuser tiene todos los permisos efectivos"""
        user = User(
            username='test_super_efectivos',
            email='super_efe@test.com',
            rol='usuario_normal',
            is_superuser=True
        )
        
        permisos = user.get_permisos_efectivos()
        
        # Superuser tiene todo
        self.assertTrue(all(permisos.values()))


class ISS019ConstraintsTest(TestCase):
    """ISS-019: Tests de constraints de BD"""
    
    @classmethod
    def setUpTestData(cls):
        cls.producto = Producto.objects.create(
            clave='CONS-001',
            descripcion='Producto para constraints',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('25.00')
        )
        cls.centro = Centro.objects.create(
            clave='CONS-CTR',
            nombre='Centro Constraints'
        )
        cls.user = User.objects.create_user(
            username='cons_user',
            email='cons@test.com',
            password='Test123!'
        )
    
    def test_lote_cantidad_negativa_rechazada(self):
        """Lote con cantidad_actual < 0 debe fallar por validador"""
        # El validador MinValueValidator(0) en el modelo previene esto
        with self.assertRaises(ValidationError):
            lote = Lote(
                producto=self.producto,
                numero_lote='CONS-LOT-001',
                fecha_caducidad=timezone.now().date() + timedelta(days=365),
                cantidad_inicial=100,
                cantidad_actual=-10  # Negativo
            )
            lote.full_clean()
    
    def test_lote_cantidad_inicial_cero_rechazada(self):
        """Lote con cantidad_inicial = 0 debe fallar por validador"""
        # El validador MinValueValidator(1) en el modelo previene esto
        with self.assertRaises(ValidationError):
            lote = Lote(
                producto=self.producto,
                numero_lote='CONS-LOT-002',
                fecha_caducidad=timezone.now().date() + timedelta(days=365),
                cantidad_inicial=0,  # Cero no permitido
                cantidad_actual=0
            )
            lote.full_clean()
    
    def test_detalle_cantidad_cero_rechazada(self):
        """DetalleRequisicion con cantidad_solicitada = 0 debe fallar"""
        from django.db.utils import IntegrityError
        
        req = Requisicion.objects.create(
            centro=self.centro,
            usuario_solicita=self.user,
            estado='borrador'
        )
        
        with self.assertRaises(IntegrityError):
            DetalleRequisicion.objects.create(
                requisicion=req,
                producto=self.producto,
                cantidad_solicitada=0  # Cero no permitido
            )
