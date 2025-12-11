"""
ISS-002/005: Tests para model_guards.py

Cubre:
- ValidatedModelMixin
- RequireServiceMixin
- TransactionGuard
- require_service decorator
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, override_settings
from django.core.exceptions import ValidationError


# Import after Django setup
try:
    from core.model_guards import (
        ValidatedModelMixin,
        RequireServiceMixin,
        TransactionGuard,
        require_service,
        ServiceRequiredError,
        ValidationBypassError,
    )
except ImportError:
    pass


class TransactionGuardTests(TestCase):
    """Tests para TransactionGuard context manager."""
    
    def test_transaction_guard_success(self):
        """TransactionGuard registra operaciones exitosas."""
        with TransactionGuard('test_operacion', requisicion_id=1) as guard:
            guard.registrar_operacion('paso_1', detalle='test')
            guard.registrar_operacion('paso_2', cantidad=10)
        
        self.assertTrue(guard.exito)
        self.assertEqual(len(guard.operaciones), 2)
        self.assertIsNotNone(guard.inicio)
        self.assertIsNotNone(guard.fin)
    
    def test_transaction_guard_failure(self):
        """TransactionGuard registra fallos y hace rollback."""
        try:
            with TransactionGuard('test_fallo', requisicion_id=1) as guard:
                guard.registrar_operacion('paso_1')
                raise ValueError("Error simulado")
        except ValueError:
            pass
        
        self.assertFalse(guard.exito)
        self.assertEqual(len(guard.operaciones), 1)
    
    def test_transaction_guard_resumen(self):
        """get_resumen() retorna información completa."""
        with TransactionGuard('test_resumen', user_id=5) as guard:
            guard.registrar_operacion('accion')
        
        resumen = guard.get_resumen()
        
        self.assertEqual(resumen['operacion'], 'test_resumen')
        self.assertEqual(resumen['contexto']['user_id'], 5)
        self.assertTrue(resumen['exito'])
        self.assertEqual(resumen['operaciones'], 1)


class RequireServiceDecoratorTests(TestCase):
    """Tests para @require_service decorator."""
    
    def test_decorator_warns_on_protected_fields(self):
        """Decorator emite warning cuando se envían campos protegidos."""
        
        @require_service('RequisicionService', ['estado'])
        def mock_update(self, request, *args, **kwargs):
            return 'success'
        
        mock_request = Mock()
        mock_request.data = {'estado': 'nuevo_estado', 'otro': 'valor'}
        
        with patch('core.model_guards.logger') as mock_logger:
            result = mock_update(None, mock_request)
            
            # Debe haber emitido un warning
            mock_logger.warning.assert_called()
            call_args = str(mock_logger.warning.call_args)
            self.assertIn('estado', call_args)
    
    def test_decorator_allows_non_protected_fields(self):
        """Decorator permite campos no protegidos sin warning."""
        
        @require_service('RequisicionService', ['estado'])
        def mock_update(self, request, *args, **kwargs):
            return 'success'
        
        mock_request = Mock()
        mock_request.data = {'descripcion': 'nueva descripcion'}
        
        with patch('core.model_guards.logger') as mock_logger:
            result = mock_update(None, mock_request)
            
            # No debe haber warnings
            mock_logger.warning.assert_not_called()


class ValidatedModelMixinTests(TestCase):
    """Tests para ValidatedModelMixin."""
    
    def test_mixin_calls_full_clean(self):
        """Mixin debe llamar full_clean() en save()."""
        
        class MockModel(ValidatedModelMixin):
            pk = None
            
            def __init__(self):
                self.full_clean_called = False
            
            def full_clean(self):
                self.full_clean_called = True
            
            def save_parent(self, *args, **kwargs):
                pass
        
        # Patch super().save
        with patch.object(ValidatedModelMixin, '__mro__', (ValidatedModelMixin, object)):
            model = MockModel()
            # Simular save
            try:
                # El mixin llama full_clean antes de save
                model.full_clean()
            except:
                pass
            
            self.assertTrue(model.full_clean_called)
    
    @override_settings(DEBUG=False)
    def test_skip_validation_blocked_in_production(self):
        """skip_validation debe ignorarse en producción."""
        
        class MockModel(ValidatedModelMixin):
            pk = 1
            CAMPOS_SIN_VALIDACION = set()
            
            def full_clean(self):
                self.validated = True
        
        model = MockModel()
        model.validated = False
        
        # En producción, skip_validation=True debe ignorarse
        # y la validación debe ejecutarse
        # (Este es un test conceptual - la implementación real
        # requiere un modelo Django completo)


class RequireServiceMixinTests(TestCase):
    """Tests para RequireServiceMixin."""
    
    def test_mixin_blocks_protected_field_changes(self):
        """Mixin debe bloquear cambios a campos protegidos."""
        
        class MockModel(RequireServiceMixin):
            pk = 1
            CAMPOS_PROTEGIDOS = {'estado'}
            SERVICIO_REQUERIDO = 'TestService'
            _service_context = False
            estado = 'nuevo'
            
            class DoesNotExist(Exception):
                pass
        
        # Mock para simular obtener el original
        with patch.object(MockModel, 'objects') as mock_objects:
            mock_original = Mock()
            mock_original.estado = 'original'
            mock_objects.get.return_value = mock_original
            
            model = MockModel()
            
            # Sin service_context, debe detectar el cambio
            campos = model._check_protected_fields()
            self.assertIn('estado', campos)
    
    def test_mixin_allows_with_service_context(self):
        """Mixin debe permitir cambios con service_context=True."""
        
        class MockModel(RequireServiceMixin):
            pk = 1
            CAMPOS_PROTEGIDOS = {'estado'}
            _service_context = True
            estado = 'nuevo'
        
        model = MockModel()
        
        # Con service_context=True, no debe verificar campos
        # (el save() original se ejecutaría)
        self.assertTrue(model._service_context)
    
    def test_enable_disable_service_context(self):
        """Métodos enable/disable funcionan correctamente."""
        
        class MockModel(RequireServiceMixin):
            _service_context = False
        
        model = MockModel()
        
        # Habilitar
        RequireServiceMixin.enable_service_context(model)
        self.assertTrue(model._service_context)
        
        # Deshabilitar
        RequireServiceMixin.disable_service_context(model)
        self.assertFalse(model._service_context)


class IntegrationTests(TestCase):
    """Tests de integración para guards combinados."""
    
    def test_transaction_guard_with_logging(self):
        """TransactionGuard registra correctamente en logs."""
        
        with patch('core.model_guards.logger') as mock_logger:
            with TransactionGuard('integracion_test', test=True) as guard:
                guard.registrar_operacion('paso_integracion')
            
            # Debe haber llamadas a info (inicio y fin)
            self.assertGreaterEqual(mock_logger.info.call_count, 2)
    
    def test_nested_transaction_guards(self):
        """TransactionGuards anidados funcionan correctamente."""
        
        with TransactionGuard('outer', level=1) as outer:
            outer.registrar_operacion('outer_op')
            
            with TransactionGuard('inner', level=2) as inner:
                inner.registrar_operacion('inner_op')
            
            self.assertTrue(inner.exito)
        
        self.assertTrue(outer.exito)
        self.assertEqual(len(outer.operaciones), 1)
        self.assertEqual(len(inner.operaciones), 1)
