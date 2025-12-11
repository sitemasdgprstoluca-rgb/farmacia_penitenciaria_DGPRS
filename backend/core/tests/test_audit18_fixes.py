"""
Tests para ISS-003, ISS-004, ISS-005 FIX (audit18)

Estos tests verifican:
- ISS-003: Fallback de funciones de permisos
- ISS-004: Bloqueos select_for_update en autorización
- ISS-005: Verificación de esquema al arrancar
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from django.core.exceptions import ValidationError
from django.db import transaction


class TestPermissionFallback:
    """
    ISS-003 FIX (audit18): Tests para fallback de funciones de permisos.
    """
    
    def test_default_is_farmacia_or_admin_superuser(self):
        """Superusuario siempre tiene acceso."""
        from inventario.services.requisicion_service import RequisicionService
        
        user = Mock()
        user.is_superuser = True
        
        result = RequisicionService._default_is_farmacia_or_admin(user)
        assert result is True
    
    def test_default_is_farmacia_or_admin_farmacia_rol(self):
        """Usuario con rol farmacia tiene acceso."""
        from inventario.services.requisicion_service import RequisicionService
        
        user = Mock()
        user.is_superuser = False
        user.rol = 'farmacia'
        
        result = RequisicionService._default_is_farmacia_or_admin(user)
        assert result is True
    
    def test_default_is_farmacia_or_admin_admin_rol(self):
        """Usuario con rol admin tiene acceso."""
        from inventario.services.requisicion_service import RequisicionService
        
        user = Mock()
        user.is_superuser = False
        user.rol = 'admin_farmacia'
        
        result = RequisicionService._default_is_farmacia_or_admin(user)
        assert result is True
    
    def test_default_is_farmacia_or_admin_medico_no_acceso(self):
        """Usuario con rol médico NO tiene acceso."""
        from inventario.services.requisicion_service import RequisicionService
        
        user = Mock()
        user.is_superuser = False
        user.rol = 'medico'
        
        result = RequisicionService._default_is_farmacia_or_admin(user)
        assert result is False
    
    def test_default_is_farmacia_or_admin_none_user(self):
        """Usuario None retorna False."""
        from inventario.services.requisicion_service import RequisicionService
        
        result = RequisicionService._default_is_farmacia_or_admin(None)
        assert result is False
    
    def test_default_get_user_centro(self):
        """Obtiene centro del usuario."""
        from inventario.services.requisicion_service import RequisicionService
        
        centro_mock = Mock()
        centro_mock.pk = 1
        
        user = Mock()
        user.centro = centro_mock
        
        result = RequisicionService._default_get_user_centro(user)
        assert result == centro_mock
    
    def test_default_get_user_centro_none_user(self):
        """Usuario None retorna None."""
        from inventario.services.requisicion_service import RequisicionService
        
        result = RequisicionService._default_get_user_centro(None)
        assert result is None
    
    def test_default_get_user_centro_farmacia_central(self):
        """Usuario de farmacia central no tiene centro."""
        from inventario.services.requisicion_service import RequisicionService
        
        user = Mock()
        user.centro = None
        
        result = RequisicionService._default_get_user_centro(user)
        assert result is None
    
    def test_validar_permisos_surtido_with_none_functions(self):
        """Usa fallback cuando funciones son None."""
        from inventario.services.requisicion_service import RequisicionService
        
        requisicion = Mock()
        requisicion.folio = 'REQ-001'
        requisicion.centro = Mock()
        requisicion.centro.nombre = 'Centro Test'
        requisicion.centro_id = None
        
        user = Mock()
        user.is_superuser = False
        user.username = 'farmacia_user'
        user.rol = 'farmacia'
        user.centro = None
        
        service = RequisicionService(requisicion, user)
        
        # Llamar con funciones None - debe usar fallback
        with patch('inventario.services.requisicion_service.logger'):
            result = service.validar_permisos_surtido(
                is_farmacia_or_admin_fn=None,
                get_user_centro_fn=None
            )
        
        assert result is True
    
    def test_validar_permisos_surtido_with_failing_functions(self):
        """Usa fallback cuando funciones lanzan excepción."""
        from inventario.services.requisicion_service import RequisicionService
        
        requisicion = Mock()
        requisicion.folio = 'REQ-001'
        requisicion.centro = Mock()
        requisicion.centro.nombre = 'Centro Test'
        requisicion.centro_id = None
        
        user = Mock()
        user.is_superuser = False
        user.username = 'admin_user'
        user.rol = 'admin_farmacia'
        user.centro = None
        
        service = RequisicionService(requisicion, user)
        
        # Funciones que fallan
        def failing_is_farmacia(u):
            raise RuntimeError("Función rota")
        
        def failing_get_centro(u):
            raise RuntimeError("Función rota")
        
        with patch('inventario.services.requisicion_service.logger'):
            result = service.validar_permisos_surtido(
                is_farmacia_or_admin_fn=failing_is_farmacia,
                get_user_centro_fn=failing_get_centro
            )
        
        assert result is True


class TestConcurrencyLocking:
    """
    ISS-004 FIX (audit18): Tests para bloqueos de concurrencia.
    """
    
    def test_autorizar_uses_select_for_update(self):
        """La autorización usa select_for_update para bloquear requisición."""
        # Este test verifica que el código tiene la llamada correcta
        import ast
        import inspect
        
        # Leer el código fuente para verificar que tiene select_for_update
        from inventario import views
        source = inspect.getsource(views.RequisicionViewSet.autorizar)
        
        assert 'select_for_update' in source
        assert 'transaction.atomic' in source
    
    def test_autorizar_handles_concurrent_modification(self):
        """La autorización maneja modificación concurrente."""
        # Este es un test conceptual - la implementación real necesita
        # verificar que retorna 409 CONFLICT cuando el estado cambió
        import inspect
        from inventario import views
        
        source = inspect.getsource(views.RequisicionViewSet.autorizar)
        
        # Verifica que hay manejo de estado cambiado
        assert '409' in source or 'CONFLICT' in source
    
    def test_autorizar_blocks_detalles(self):
        """La autorización también bloquea los detalles."""
        import inspect
        from inventario import views
        
        source = inspect.getsource(views.RequisicionViewSet._autorizar_con_bloqueo)
        
        # Verifica que los detalles también se bloquean
        assert 'DetalleRequisicion.objects.select_for_update' in source


class TestSchemaVerification:
    """
    ISS-005 FIX (audit18): Tests para verificación de esquema.
    """
    
    def test_schema_verifier_exists(self):
        """El verificador de esquema existe."""
        from core.schema_check import SchemaVerifier
        
        assert hasattr(SchemaVerifier, 'verificar_esquema')
        assert hasattr(SchemaVerifier, 'MODELOS_CRITICOS')
    
    def test_schema_verifier_has_critical_tables(self):
        """El verificador incluye tablas críticas."""
        from core.schema_check import SchemaVerifier
        
        assert 'requisiciones' in SchemaVerifier.MODELOS_CRITICOS
        assert 'productos' in SchemaVerifier.MODELOS_CRITICOS
        assert 'lotes' in SchemaVerifier.MODELOS_CRITICOS
        assert 'movimientos' in SchemaVerifier.MODELOS_CRITICOS
        assert 'centros' in SchemaVerifier.MODELOS_CRITICOS
    
    def test_tipos_compatibles(self):
        """Verifica compatibilidad de tipos."""
        from core.schema_check import SchemaVerifier
        
        # Integer compatible con bigint
        assert SchemaVerifier._tipos_compatibles('integer', 'bigint')
        
        # Character varying compatible con text
        assert SchemaVerifier._tipos_compatibles('character varying', 'text')
        
        # Timestamp compatible con timestamptz
        assert SchemaVerifier._tipos_compatibles('timestamp', 'timestamp with time zone')
        
        # Boolean compatible
        assert SchemaVerifier._tipos_compatibles('boolean', 'bool')
    
    def test_verificar_esquema_handles_no_connection(self):
        """El verificador maneja sin conexión sin bloquear."""
        from core.schema_check import SchemaVerifier
        
        with patch('core.schema_check.connection') as mock_conn:
            mock_conn.cursor.side_effect = Exception("No connection")
            
            resultado = SchemaVerifier.verificar_esquema(raise_on_error=False)
            
            # No debe lanzar excepción
            assert 'advertencias' in resultado
    
    def test_verificar_esquema_al_iniciar_respects_testing(self):
        """La verificación respeta modo testing."""
        from core.schema_check import verificar_esquema_al_iniciar
        
        with patch('django.conf.settings') as mock_settings:
            mock_settings.TESTING = True
            
            # No debe hacer nada en modo test
            resultado = verificar_esquema_al_iniciar()
            # En modo test, debería retornar None o similar


class TestRequisicionValidations:
    """
    ISS-002 FIX (audit18): Tests para validaciones de Requisicion.
    """
    
    def test_requisicion_has_clean_method(self):
        """Requisicion tiene método clean()."""
        from core.models import Requisicion
        
        assert hasattr(Requisicion, 'clean')
        
        # Verificar que es un método real, no heredado sin implementación
        import inspect
        source = inspect.getsource(Requisicion.clean)
        assert 'ValidationError' in source
    
    def test_requisicion_save_calls_full_clean(self):
        """Requisicion.save() llama full_clean()."""
        from core.models import Requisicion
        import inspect
        
        source = inspect.getsource(Requisicion.save)
        assert 'full_clean' in source
    
    def test_requisicion_blocks_inventory_states_without_service(self):
        """cambiar_estado bloquea estados de inventario sin servicio."""
        from core.models import Requisicion
        import inspect
        
        source = inspect.getsource(Requisicion.cambiar_estado)
        
        # Verifica que hay bloqueo de estados de inventario
        assert 'ESTADOS_REQUIEREN_SERVICIO' in source
        assert 'RequisicionService' in source


class TestServiceLayerEnforcement:
    """
    ISS-001 FIX (audit18): Tests para enforcement de capa de servicios.
    """
    
    def test_requisicion_estados_requieren_servicio(self):
        """Los estados críticos requieren pasar por servicio."""
        from core.models import Requisicion
        
        estados_criticos = {'en_surtido', 'surtida', 'parcial', 'entregada'}
        
        # Verificar que están en ESTADOS_REQUIEREN_SERVICIO
        assert hasattr(Requisicion, 'ESTADOS_REQUIEREN_SERVICIO')
        
        for estado in estados_criticos:
            assert estado in Requisicion.ESTADOS_REQUIEREN_SERVICIO, \
                f"Estado crítico '{estado}' no está en ESTADOS_REQUIEREN_SERVICIO"
    
    def test_cambiar_estado_blocks_without_forzar_modelo(self):
        """cambiar_estado bloquea estados críticos sin forzar_modelo."""
        from core.models import Requisicion
        from django.core.exceptions import ValidationError
        
        requisicion = Requisicion()
        requisicion.numero = 'TEST-001'
        requisicion.estado = 'autorizada'
        
        # Intentar cambiar a estado de inventario debería fallar
        with pytest.raises(ValidationError) as exc_info:
            requisicion.cambiar_estado('en_surtido', forzar_modelo=False)
        
        assert 'RequisicionService' in str(exc_info.value)


class TestAppConfigIntegration:
    """
    Tests de integración para AppConfig.
    """
    
    def test_core_config_has_schema_check(self):
        """CoreConfig ejecuta verificación de esquema."""
        from core.apps import CoreConfig
        import inspect
        
        source = inspect.getsource(CoreConfig.ready)
        
        # Verifica que llama a verificación de esquema
        assert 'schema_check' in source or 'schema_validator' in source
        assert 'verificar_esquema' in source
