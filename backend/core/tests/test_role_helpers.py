"""
Tests para RoleHelper - ISS-004 FIX (audit16)

Estos tests verifican el sistema centralizado de validación de roles
para garantizar consistencia en todas las operaciones del sistema.
"""
import pytest
from unittest.mock import Mock, MagicMock
from django.contrib.auth import get_user_model
from core.permissions import RoleHelper


class TestRoleHelper:
    """Tests para RoleHelper centralizado."""
    
    def _create_mock_user(self, rol=None, is_superuser=False, groups=None, centro=None):
        """Crea un mock de usuario para tests."""
        user = Mock()
        user.is_authenticated = True
        user.is_superuser = is_superuser
        user.rol = rol
        user.centro = centro
        
        if groups:
            mock_groups = []
            for g in groups:
                mock_group = Mock()
                mock_group.name = g
                mock_groups.append(mock_group)
            user.groups.all.return_value = mock_groups
        else:
            user.groups.all.return_value = []
        
        return user
    
    def test_superuser_tiene_todos_los_roles(self):
        """Superuser debe tener acceso a todos los roles."""
        user = self._create_mock_user(is_superuser=True)
        
        assert RoleHelper.has_role(user, ['admin']) is True
        assert RoleHelper.has_role(user, ['farmacia']) is True
        assert RoleHelper.has_role(user, ['centro']) is True
        assert RoleHelper.has_role(user, ['vista']) is True
    
    def test_usuario_no_autenticado_sin_roles(self):
        """Usuario no autenticado no debe tener roles."""
        user = Mock()
        user.is_authenticated = False
        
        assert RoleHelper.has_role(user, ['admin']) is False
        assert RoleHelper.has_role(user, ['farmacia']) is False
        assert RoleHelper.is_farmacia_or_admin(user) is False
        assert RoleHelper.get_user_centro(user) is None
    
    def test_usuario_none_sin_roles(self):
        """None como usuario no debe tener roles."""
        assert RoleHelper.has_role(None, ['admin']) is False
        assert RoleHelper.is_farmacia_or_admin(None) is False
        assert RoleHelper.get_user_centro(None) is None
    
    def test_rol_farmacia_por_campo(self):
        """Usuario con rol='farmacia' debe ser detectado."""
        user = self._create_mock_user(rol='farmacia')
        
        assert RoleHelper.has_role(user, ['farmacia']) is True
        assert RoleHelper.is_farmacia(user) is True
        assert RoleHelper.is_farmacia_or_admin(user) is True
        assert RoleHelper.can_surtir(user) is True
        assert RoleHelper.can_autorizar(user) is True
    
    def test_rol_farmacia_por_grupo(self):
        """Usuario con grupo FARMACIA_ADMIN debe tener permisos de farmacia."""
        user = self._create_mock_user(groups=['FARMACIA_ADMIN'])
        
        assert RoleHelper.has_role(user, ['farmacia']) is True
        assert RoleHelper.is_farmacia(user) is True
    
    def test_rol_farmaceutico_por_grupo(self):
        """Usuario con grupo FARMACEUTICO debe tener permisos de farmacia."""
        user = self._create_mock_user(groups=['FARMACEUTICO'])
        
        assert RoleHelper.has_role(user, ['farmacia']) is True
        assert RoleHelper.can_surtir(user) is True
    
    def test_rol_centro_por_campo(self):
        """Usuario con rol='centro' debe ser detectado."""
        user = self._create_mock_user(rol='centro')
        
        assert RoleHelper.has_role(user, ['centro']) is True
        assert RoleHelper.is_centro(user) is True
        assert RoleHelper.is_farmacia(user) is False
        assert RoleHelper.can_surtir(user) is False
    
    def test_rol_centro_por_grupo(self):
        """Usuario con grupo CENTRO_USER debe tener permisos de centro."""
        user = self._create_mock_user(groups=['CENTRO_USER'])
        
        assert RoleHelper.has_role(user, ['centro']) is True
    
    def test_rol_solicitante_alias_centro(self):
        """Usuario con rol='solicitante' debe tener permisos de centro."""
        user = self._create_mock_user(rol='solicitante')
        
        assert RoleHelper.has_role(user, ['centro']) is True
    
    def test_rol_vista_no_puede_surtir(self):
        """Usuario con rol='vista' no debe poder surtir."""
        user = self._create_mock_user(rol='vista')
        
        assert RoleHelper.is_vista(user) is True
        assert RoleHelper.can_surtir(user) is False
        assert RoleHelper.can_autorizar(user) is False
        assert RoleHelper.can_cancelar(user) is False
    
    def test_get_user_centro(self):
        """get_user_centro debe retornar el centro del usuario."""
        centro_mock = Mock()
        centro_mock.nombre = "Centro Test"
        
        user = self._create_mock_user(centro=centro_mock)
        
        assert RoleHelper.get_user_centro(user) == centro_mock
    
    def test_get_user_centro_none(self):
        """get_user_centro debe retornar None si no tiene centro."""
        user = self._create_mock_user(centro=None)
        
        assert RoleHelper.get_user_centro(user) is None
    
    def test_validate_centro_access_admin_siempre_accede(self):
        """Admin debe poder acceder a cualquier requisición."""
        user = self._create_mock_user(is_superuser=True)
        requisicion = Mock()
        requisicion.centro_destino = Mock()
        
        assert RoleHelper.validate_centro_access(user, requisicion) is True
    
    def test_validate_centro_access_farmacia_siempre_accede(self):
        """Farmacia debe poder acceder a cualquier requisición."""
        user = self._create_mock_user(rol='farmacia')
        requisicion = Mock()
        requisicion.centro_destino = Mock()
        
        assert RoleHelper.validate_centro_access(user, requisicion) is True
    
    def test_validate_centro_access_centro_propio(self):
        """Centro debe poder acceder solo a sus propias requisiciones."""
        centro = Mock()
        user = self._create_mock_user(rol='centro', centro=centro)
        
        requisicion = Mock()
        requisicion.centro_destino = centro
        requisicion.centro_origen = None
        requisicion.centro = None
        requisicion.solicitante = None
        
        assert RoleHelper.validate_centro_access(user, requisicion) is True
    
    def test_validate_centro_access_centro_ajeno_denegado(self):
        """Centro no debe poder acceder a requisiciones de otros centros."""
        centro_usuario = Mock()
        centro_otro = Mock()
        
        user = self._create_mock_user(rol='centro', centro=centro_usuario)
        
        requisicion = Mock()
        requisicion.centro_destino = centro_otro
        requisicion.centro_origen = None
        requisicion.centro = None
        requisicion.solicitante = None
        
        assert RoleHelper.validate_centro_access(user, requisicion) is False
    
    def test_validate_centro_access_por_solicitante(self):
        """Centro debe poder acceder si es el centro del solicitante."""
        centro = Mock()
        user = self._create_mock_user(rol='centro', centro=centro)
        
        solicitante = Mock()
        solicitante.centro = centro
        
        requisicion = Mock()
        requisicion.centro_destino = None
        requisicion.centro_origen = None
        requisicion.centro = None
        requisicion.solicitante = solicitante
        
        assert RoleHelper.validate_centro_access(user, requisicion) is True
    
    def test_usuario_sin_centro_no_accede(self):
        """Usuario sin centro asignado no debe poder acceder."""
        user = self._create_mock_user(rol='centro', centro=None)
        
        requisicion = Mock()
        requisicion.centro_destino = Mock()
        
        assert RoleHelper.validate_centro_access(user, requisicion) is False


class TestRoleHelperAliases:
    """Tests para verificar aliases de roles."""
    
    def _create_mock_user(self, rol=None, is_superuser=False, groups=None):
        user = Mock()
        user.is_authenticated = True
        user.is_superuser = is_superuser
        user.rol = rol
        user.groups.all.return_value = []
        return user
    
    def test_alias_admin_sistema(self):
        """admin_sistema debe ser reconocido como admin."""
        user = self._create_mock_user(rol='admin_sistema')
        assert RoleHelper.is_admin(user) is True
    
    def test_alias_superusuario(self):
        """superusuario debe ser reconocido como admin."""
        user = self._create_mock_user(rol='superusuario')
        assert RoleHelper.is_admin(user) is True
    
    def test_alias_admin_farmacia(self):
        """admin_farmacia debe ser reconocido como farmacia."""
        user = self._create_mock_user(rol='admin_farmacia')
        assert RoleHelper.is_farmacia(user) is True
    
    def test_alias_farmaceutico(self):
        """farmaceutico debe ser reconocido como farmacia."""
        user = self._create_mock_user(rol='farmaceutico')
        assert RoleHelper.is_farmacia(user) is True
    
    def test_alias_usuario_normal(self):
        """usuario_normal debe ser reconocido como centro."""
        user = self._create_mock_user(rol='usuario_normal')
        assert RoleHelper.is_centro(user) is True
    
    def test_alias_usuario_vista(self):
        """usuario_vista debe ser reconocido como vista."""
        user = self._create_mock_user(rol='usuario_vista')
        assert RoleHelper.is_vista(user) is True


class TestRoleHelperGetters:
    """Tests para funciones getter del RoleHelper."""
    
    def test_get_user_role_normalizado(self):
        """get_user_role debe retornar el rol normalizado en minúsculas."""
        user = Mock()
        user.is_authenticated = True
        user.is_superuser = False
        user.rol = 'FARMACIA'
        
        assert RoleHelper.get_user_role(user) == 'farmacia'
    
    def test_get_user_role_superuser(self):
        """get_user_role de superuser debe retornar 'admin'."""
        user = Mock()
        user.is_authenticated = True
        user.is_superuser = True
        user.rol = None
        
        assert RoleHelper.get_user_role(user) == 'admin'
    
    def test_get_user_groups(self):
        """get_user_groups debe retornar set de nombres en mayúsculas."""
        user = Mock()
        user.is_authenticated = True
        
        group1 = Mock()
        group1.name = 'farmacia_admin'
        group2 = Mock()
        group2.name = 'can_view'
        user.groups.all.return_value = [group1, group2]
        
        groups = RoleHelper.get_user_groups(user)
        assert 'FARMACIA_ADMIN' in groups
        assert 'CAN_VIEW' in groups
