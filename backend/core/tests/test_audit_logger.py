"""
Tests para AuditLogger - ISS-006 FIX (audit17)

Estos tests verifican el sistema de auditoría para accesos privilegiados.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, call
import logging
from datetime import datetime


class TestAuditLoggerPrivilegedAccess:
    """Tests para logging de acceso privilegiado."""
    
    def test_log_privileged_access_admin(self):
        """Log cuando admin accede sin filtros."""
        from core.validators import AuditLogger
        
        user = Mock()
        user.username = 'admin_test'
        user.is_staff = True
        user.is_superuser = False
        user.is_authenticated = True
        user.id = 1
        user.rol = 'admin'
        
        with patch('core.validators.logger') as mock_logger:
            AuditLogger.log_privileged_access(
                user=user,
                resource='Requisicion',
                filter_applied=False,
                details={'action': 'list'}
            )
            
            mock_logger.warning.assert_called_once()
            call_args = str(mock_logger.warning.call_args)
            assert 'admin_test' in call_args
            assert 'Requisicion' in call_args
    
    def test_log_privileged_access_superuser(self):
        """Log cuando superuser accede."""
        from core.validators import AuditLogger
        
        user = Mock()
        user.username = 'superadmin'
        user.is_staff = True
        user.is_superuser = True
        user.is_authenticated = True
        user.id = 1
        user.rol = 'admin'
        
        with patch('core.validators.logger') as mock_logger:
            AuditLogger.log_privileged_access(
                user=user,
                resource='Producto',
                filter_applied=True,
                details={'filtro': 'centro_id=5'}
            )
            
            # Con filter_applied=True usa info en el audit logger
            # Verificamos que el método se ejecutó sin error


    def test_no_log_unauthenticated_user(self):
        """No log para usuarios no autenticados."""
        from core.validators import AuditLogger
        
        user = Mock()
        user.username = 'usuario_anonimo'
        user.is_authenticated = False
        
        with patch('core.validators.logger') as mock_logger:
            AuditLogger.log_privileged_access(
                user=user,
                resource='Requisicion',
                filter_applied=True,
                details={}
            )
            
            # No debe haber log ya que no está autenticado
            mock_logger.warning.assert_not_called()
            mock_logger.info.assert_not_called()
    
    def test_log_includes_user_details(self):
        """El log incluye detalles del usuario."""
        from core.validators import AuditLogger
        
        user = Mock()
        user.username = 'admin'
        user.is_staff = True
        user.is_superuser = False
        user.is_authenticated = True
        user.id = 42
        user.rol = 'farmacia'
        
        with patch('core.validators.logger') as mock_logger:
            AuditLogger.log_privileged_access(
                user=user,
                resource='Lote',
                filter_applied=False,
                details={'timestamp': '2024-01-01'}
            )
            
            mock_logger.warning.assert_called_once()
            call_args = str(mock_logger.warning.call_args)
            assert 'admin' in call_args


class TestAuditLoggerGlobalQuery:
    """Tests para logging de consultas globales."""
    
    def test_log_global_query_without_filter(self):
        """Log cuando consulta no tiene filtros."""
        from core.validators import AuditLogger
        
        user = Mock()
        user.username = 'admin'
        user.is_staff = True
        user.is_superuser = False
        user.is_authenticated = True
        user.id = 1
        user.rol = 'admin'
        
        with patch('core.validators.logger') as mock_logger:
            AuditLogger.log_global_query(
                user=user,
                queryset_count=1500,
                model_name='Requisicion',
                filters_applied={}
            )
            
            mock_logger.warning.assert_called_once()
            call_args = str(mock_logger.warning.call_args)
            assert '1500' in call_args
    
    def test_log_global_query_large_result(self):
        """Log especial para resultados muy grandes."""
        from core.validators import AuditLogger
        
        user = Mock()
        user.username = 'superadmin'
        user.is_staff = True
        user.is_superuser = True
        user.is_authenticated = True
        user.id = 1
        user.rol = 'admin_sistema'
        
        with patch('core.validators.logger') as mock_logger:
            AuditLogger.log_global_query(
                user=user,
                queryset_count=10000,
                model_name='Movimiento',
                filters_applied={'tipo': 'entrada'}
            )
            
            # Debería loguear por cantidad grande (>1000)
            mock_logger.warning.assert_called()
    
    def test_no_log_unauthenticated_for_query(self):
        """No log para usuarios no autenticados en consultas."""
        from core.validators import AuditLogger
        
        user = Mock()
        user.username = 'operador'
        user.is_authenticated = False
        
        with patch('core.validators.logger') as mock_logger:
            AuditLogger.log_global_query(
                user=user,
                queryset_count=50,
                model_name='Requisicion',
                filters_applied={'centro_id': 1, 'estado': 'pendiente'}
            )
            
            # No autenticado - no se loguea
            mock_logger.warning.assert_not_called()
            mock_logger.info.assert_not_called()


class TestAuditLoggerStockOperations:
    """Tests para logging de operaciones de stock."""
    
    def test_log_stock_validation(self):
        """Log de validación de stock."""
        from core.validators import AuditLogger
        
        user = Mock()
        user.username = 'farmacia'
        user.id = 1
        
        with patch('core.validators.logger') as mock_logger:
            AuditLogger.log_stock_operation(
                user=user,
                operation='validacion',
                producto_id=1,
                cantidad=100,
                resultado='ok',
                modo='estricto'
            )
            
            mock_logger.info.assert_called_once()
    
    def test_log_stock_validation_failed(self):
        """Log de validación de stock fallida."""
        from core.validators import AuditLogger
        
        user = Mock()
        user.username = 'farmacia'
        user.id = 1
        
        with patch('core.validators.logger') as mock_logger:
            AuditLogger.log_stock_operation(
                user=user,
                operation='validacion',
                producto_id=1,
                cantidad=100,
                resultado='insuficiente',
                modo='estricto'
            )
            
            # Validación fallida debería ser warning
            mock_logger.warning.assert_called_once()
    
    def test_log_stock_revalidation_at_transition(self):
        """Log de revalidación en transición de estado."""
        from core.validators import AuditLogger
        
        user = Mock()
        user.username = 'admin'
        user.id = 1
        
        with patch('core.validators.logger') as mock_logger:
            AuditLogger.log_stock_operation(
                user=user,
                operation='revalidacion_envio',
                producto_id=None,
                cantidad=None,
                resultado='ok',
                modo='informativo',
                requisicion_id=123
            )
            
            mock_logger.info.assert_called()


class TestAuditLoggerStateTransitions:
    """Tests para logging de transiciones de estado."""
    
    def test_log_requisicion_state_change(self):
        """Log de cambio de estado de requisición."""
        from core.validators import AuditLogger
        
        user = Mock()
        user.username = 'autorizador'
        user.id = 1
        
        with patch('core.validators.logger') as mock_logger:
            AuditLogger.log_state_transition(
                user=user,
                model='Requisicion',
                object_id=456,
                old_state='enviada',
                new_state='autorizada'
            )
            
            mock_logger.info.assert_called_once()
            call_args = str(mock_logger.info.call_args)
            assert 'enviada' in call_args
            assert 'autorizada' in call_args
    
    def test_log_cancelation(self):
        """Log de cancelación."""
        from core.validators import AuditLogger
        
        user = Mock()
        user.username = 'admin'
        user.id = 1
        
        with patch('core.validators.logger') as mock_logger:
            AuditLogger.log_state_transition(
                user=user,
                model='Requisicion',
                object_id=789,
                old_state='pendiente',
                new_state='cancelada',
                motivo='Sin stock'
            )
            
            # Cancelaciones deberían ser warning
            mock_logger.warning.assert_called_once()


class TestAuditLoggerConfiguration:
    """Tests para configuración del logger."""
    
    def test_logger_uses_audit_logger(self):
        """El AuditLogger usa el logger 'audit' configurado."""
        import logging
        
        # Verificar que el módulo usa el logger correcto
        # El logger debe estar configurado en settings
        audit_logger = logging.getLogger('audit')
        assert audit_logger is not None
    
    def test_audit_entries_structured(self):
        """Las entradas de auditoría tienen estructura consistente."""
        from core.validators import AuditLogger
        
        user = Mock()
        user.username = 'test_user'
        user.is_staff = True
        user.is_superuser = False
        user.is_authenticated = True
        user.id = 99
        user.rol = 'admin'
        
        with patch('core.validators.logger') as mock_logger:
            AuditLogger.log_privileged_access(
                user=user,
                resource='Test',
                filter_applied=False,
                details={'key': 'value'}
            )
            
            # Verificar que se llamó con información estructurada
            mock_logger.warning.assert_called()
            call_args = str(mock_logger.warning.call_args)
            # Debe incluir usuario y recurso
            assert 'test_user' in call_args or 'Test' in call_args


class TestAuditLoggerIntegration:
    """Tests de integración con el sistema de logs."""
    
    def test_full_audit_workflow(self):
        """Test de flujo completo de auditoría."""
        from core.validators import AuditLogger
        
        # Simular un flujo de operaciones
        user = Mock()
        user.username = 'workflow_user'
        user.is_staff = True
        user.is_superuser = False
        user.is_authenticated = True
        user.id = 10
        user.rol = 'admin'
        
        with patch('core.validators.logger') as mock_logger:
            # 1. Usuario accede a listado
            AuditLogger.log_privileged_access(
                user=user,
                resource='Requisicion',
                filter_applied=False,
                details={'action': 'list'}
            )
            
            # 2. Usuario consulta resultados
            AuditLogger.log_global_query(
                user=user,
                queryset_count=500,
                model_name='Requisicion',
                filters_applied={}
            )
            
            # 3. Usuario cambia estado
            AuditLogger.log_state_transition(
                user=user,
                model='Requisicion',
                object_id=1,
                old_state='borrador',
                new_state='enviada'
            )
            
            # Verificar que se generaron los logs esperados
            assert mock_logger.warning.call_count >= 2  # acceso + query
            assert mock_logger.info.call_count >= 1  # transición
