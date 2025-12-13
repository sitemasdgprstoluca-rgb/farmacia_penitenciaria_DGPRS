"""
Tests para validar los fixes de la auditoría de seguridad Auth/RBAC.

ISS-AUDIT: Tests para:
- BUG-001: is_farmacia_or_admin() no incluye 'vista'
- BUG-003: RoleHelper.ROLE_ALIASES como única fuente de verdad
"""
import pytest
from unittest.mock import Mock, MagicMock
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

# Importar funciones a testear
from core.permissions import RoleHelper, _has_role


User = get_user_model()


class TestIsFarmaciaOrAdminFix:
    """
    ISS-AUDIT BUG-001: Verificar que is_farmacia_or_admin() NO incluye 'vista'.
    
    El fix separa las funciones:
    - is_farmacia_or_admin(): Solo admin y farmacia (escritura)
    - has_global_read_access(): Admin, farmacia Y vista (lectura)
    """
    
    def test_admin_returns_true(self):
        """Admin debe retornar True en is_farmacia_or_admin()"""
        from inventario.views import is_farmacia_or_admin
        
        user = Mock()
        user.is_authenticated = True
        user.is_superuser = False
        user.rol = 'admin'
        user.groups.all.return_value = []
        
        assert is_farmacia_or_admin(user) is True
    
    def test_farmacia_returns_true(self):
        """Farmacia debe retornar True en is_farmacia_or_admin()"""
        from inventario.views import is_farmacia_or_admin
        
        user = Mock()
        user.is_authenticated = True
        user.is_superuser = False
        user.rol = 'farmacia'
        user.groups.all.return_value = []
        
        assert is_farmacia_or_admin(user) is True
    
    def test_vista_returns_false(self):
        """ISS-AUDIT FIX: Vista NO debe retornar True en is_farmacia_or_admin()"""
        from inventario.views import is_farmacia_or_admin
        
        user = Mock()
        user.is_authenticated = True
        user.is_superuser = False
        user.rol = 'vista'
        user.groups.all.return_value = []
        
        # Este es el fix principal - antes retornaba True incorrectamente
        assert is_farmacia_or_admin(user) is False
    
    def test_centro_returns_false(self):
        """Centro no debe tener acceso en is_farmacia_or_admin()"""
        from inventario.views import is_farmacia_or_admin
        
        user = Mock()
        user.is_authenticated = True
        user.is_superuser = False
        user.rol = 'centro'
        user.groups.all.return_value = []
        
        assert is_farmacia_or_admin(user) is False
    
    def test_administrador_centro_returns_false(self):
        """Administrador centro no debe tener acceso en is_farmacia_or_admin()"""
        from inventario.views import is_farmacia_or_admin
        
        user = Mock()
        user.is_authenticated = True
        user.is_superuser = False
        user.rol = 'administrador_centro'
        user.groups.all.return_value = []
        
        assert is_farmacia_or_admin(user) is False
    
    def test_superuser_returns_true(self):
        """Superusuario siempre retorna True"""
        from inventario.views import is_farmacia_or_admin
        
        user = Mock()
        user.is_authenticated = True
        user.is_superuser = True
        user.rol = ''
        user.groups.all.return_value = []
        
        assert is_farmacia_or_admin(user) is True


class TestHasGlobalReadAccess:
    """
    ISS-AUDIT BUG-001: Verificar que has_global_read_access() incluye 'vista'.
    """
    
    def test_vista_has_global_read_access(self):
        """Vista debe tener acceso de lectura global"""
        from inventario.views import has_global_read_access
        
        user = Mock()
        user.is_authenticated = True
        user.is_superuser = False
        user.rol = 'vista'
        user.groups.all.return_value = []
        
        assert has_global_read_access(user) is True
    
    def test_admin_has_global_read_access(self):
        """Admin debe tener acceso de lectura global (hereda de is_farmacia_or_admin)"""
        from inventario.views import has_global_read_access
        
        user = Mock()
        user.is_authenticated = True
        user.is_superuser = False
        user.rol = 'admin'
        user.groups.all.return_value = []
        
        assert has_global_read_access(user) is True
    
    def test_farmacia_has_global_read_access(self):
        """Farmacia debe tener acceso de lectura global"""
        from inventario.views import has_global_read_access
        
        user = Mock()
        user.is_authenticated = True
        user.is_superuser = False
        user.rol = 'farmacia'
        user.groups.all.return_value = []
        
        assert has_global_read_access(user) is True
    
    def test_centro_no_global_read_access(self):
        """Centro NO debe tener acceso de lectura global"""
        from inventario.views import has_global_read_access
        
        user = Mock()
        user.is_authenticated = True
        user.is_superuser = False
        user.rol = 'centro'
        user.groups.all.return_value = []
        
        assert has_global_read_access(user) is False


class TestRoleHelperSingleSource:
    """
    ISS-AUDIT BUG-003: Verificar que RoleHelper.ROLE_ALIASES es la única fuente de verdad.
    """
    
    def test_role_aliases_has_all_roles(self):
        """RoleHelper.ROLE_ALIASES debe contener todos los roles del sistema"""
        required_role_groups = ['admin', 'farmacia', 'centro', 'vista']
        
        for role_group in required_role_groups:
            assert role_group in RoleHelper.ROLE_ALIASES, f"Falta grupo de rol: {role_group}"
    
    def test_centro_roles_include_all_subroles(self):
        """El grupo 'centro' debe incluir todos los subroles del centro"""
        centro_subroles = {
            'centro', 'usuario_normal', 'solicitante', 
            'medico', 'administrador_centro', 'director_centro', 'usuario_centro'
        }
        
        assert centro_subroles.issubset(RoleHelper.ROLE_ALIASES['centro']), \
            f"Faltan subroles de centro: {centro_subroles - RoleHelper.ROLE_ALIASES['centro']}"
    
    def test_has_role_uses_role_helper(self):
        """_has_role debe usar RoleHelper.ROLE_ALIASES"""
        # Crear mock de usuario
        user = Mock()
        user.is_authenticated = True
        user.is_superuser = False
        user.rol = 'medico'  # Subrole de centro
        user.groups.all.return_value = []
        
        # medico está en el grupo 'centro' de RoleHelper.ROLE_ALIASES
        assert _has_role(user, ['centro']) is True
        assert _has_role(user, ['admin']) is False
        assert _has_role(user, ['farmacia']) is False


class TestRoleHelperMethods:
    """
    Tests para los métodos de RoleHelper.
    """
    
    def test_is_admin_with_admin_role(self):
        """is_admin debe retornar True para roles admin"""
        user = Mock()
        user.is_authenticated = True
        user.is_superuser = False
        user.rol = 'admin_sistema'
        user.groups.all.return_value = []
        
        assert RoleHelper.is_admin(user) is True
    
    def test_is_admin_with_superuser(self):
        """is_admin debe retornar True para superusuarios"""
        user = Mock()
        user.is_authenticated = True
        user.is_superuser = True
        user.rol = ''
        user.groups.all.return_value = []
        
        assert RoleHelper.is_admin(user) is True
    
    def test_is_farmacia_includes_admin(self):
        """is_farmacia debe incluir admin"""
        user = Mock()
        user.is_authenticated = True
        user.is_superuser = False
        user.rol = 'admin'
        user.groups.all.return_value = []
        
        assert RoleHelper.is_farmacia(user) is True
    
    def test_is_centro_with_medico(self):
        """is_centro debe retornar True para rol medico"""
        user = Mock()
        user.is_authenticated = True
        user.is_superuser = False
        user.rol = 'medico'
        user.groups.all.return_value = []
        
        assert RoleHelper.is_centro(user) is True
    
    def test_is_centro_with_administrador_centro(self):
        """is_centro debe retornar True para administrador_centro"""
        user = Mock()
        user.is_authenticated = True
        user.is_superuser = False
        user.rol = 'administrador_centro'
        user.groups.all.return_value = []
        
        assert RoleHelper.is_centro(user) is True
    
    def test_is_centro_with_director_centro(self):
        """is_centro debe retornar True para director_centro"""
        user = Mock()
        user.is_authenticated = True
        user.is_superuser = False
        user.rol = 'director_centro'
        user.groups.all.return_value = []
        
        assert RoleHelper.is_centro(user) is True


class TestPermissionsConsistency:
    """
    Tests para verificar consistencia entre models.py y serializers.py.
    """
    
    def test_centro_roles_no_reportes(self):
        """Roles de centro NO deben tener perm_reportes en models.py"""
        from core.models import User
        
        centro_roles = ['centro', 'medico', 'administrador_centro', 'director_centro', 'usuario_centro']
        
        for rol in centro_roles:
            if rol in User.PERMISOS_POR_ROL:
                perms = User.PERMISOS_POR_ROL[rol]
                assert perms.get('perm_reportes') is False, \
                    f"Rol {rol} tiene perm_reportes=True cuando debería ser False"
    
    def test_centro_roles_no_trazabilidad(self):
        """Roles de centro NO deben tener perm_trazabilidad en models.py"""
        from core.models import User
        
        centro_roles = ['centro', 'medico', 'administrador_centro', 'director_centro', 'usuario_centro']
        
        for rol in centro_roles:
            if rol in User.PERMISOS_POR_ROL:
                perms = User.PERMISOS_POR_ROL[rol]
                assert perms.get('perm_trazabilidad') is False, \
                    f"Rol {rol} tiene perm_trazabilidad=True cuando debería ser False"
    
    def test_admin_has_all_permissions(self):
        """Admin debe tener todos los permisos"""
        from core.models import User
        
        admin_perms = User.PERMISOS_POR_ROL.get('admin', {})
        
        critical_perms = [
            'perm_dashboard', 'perm_productos', 'perm_lotes', 
            'perm_requisiciones', 'perm_centros', 'perm_usuarios',
            'perm_reportes', 'perm_trazabilidad', 'perm_auditoria'
        ]
        
        for perm in critical_perms:
            assert admin_perms.get(perm) is True, f"Admin no tiene {perm}"


class TestMedicoPermissions:
    """
    ISS-AUDIT: Tests específicos para el rol médico.
    
    El médico debe poder:
    - Crear requisiciones
    - Enviar a administrador de centro
    - Confirmar entrega
    
    El médico NO debe poder:
    - Ver reportes ni trazabilidad
    - Autorizar requisiciones
    - Surtir requisiciones
    """
    
    def test_medico_puede_crear_requisicion(self):
        """Médico debe poder crear requisiciones"""
        from core.models import User
        
        medico_perms = User.PERMISOS_POR_ROL.get('medico', {})
        assert medico_perms.get('perm_crear_requisicion') is True
    
    def test_medico_puede_confirmar_entrega(self):
        """Médico debe poder confirmar entrega"""
        from core.models import User
        
        medico_perms = User.PERMISOS_POR_ROL.get('medico', {})
        assert medico_perms.get('perm_confirmar_entrega') is True
    
    def test_medico_no_ve_reportes(self):
        """Médico NO debe ver reportes"""
        from core.models import User
        
        medico_perms = User.PERMISOS_POR_ROL.get('medico', {})
        assert medico_perms.get('perm_reportes') is False
    
    def test_medico_no_ve_trazabilidad(self):
        """Médico NO debe ver trazabilidad"""
        from core.models import User
        
        medico_perms = User.PERMISOS_POR_ROL.get('medico', {})
        assert medico_perms.get('perm_trazabilidad') is False
    
    def test_medico_no_autoriza(self):
        """Médico NO puede autorizar como admin ni director"""
        from core.models import User
        
        medico_perms = User.PERMISOS_POR_ROL.get('medico', {})
        assert medico_perms.get('perm_autorizar_admin') is False
        assert medico_perms.get('perm_autorizar_director') is False
    
    def test_medico_no_surte(self):
        """Médico NO puede surtir requisiciones"""
        from core.models import User
        
        medico_perms = User.PERMISOS_POR_ROL.get('medico', {})
        assert medico_perms.get('perm_surtir') is False
    
    def test_medico_ve_productos_y_requisiciones(self):
        """Médico debe ver productos y requisiciones"""
        from core.models import User
        
        medico_perms = User.PERMISOS_POR_ROL.get('medico', {})
        assert medico_perms.get('perm_dashboard') is True
        assert medico_perms.get('perm_productos') is True
        assert medico_perms.get('perm_requisiciones') is True
        assert medico_perms.get('perm_notificaciones') is True


class TestBuildPermMapForMedico:
    """Tests para verificar que build_perm_map devuelve los permisos correctos para médico"""
    
    def test_build_perm_map_medico(self):
        """build_perm_map debe devolver permisos correctos para médico"""
        from core.serializers import build_perm_map
        
        user = Mock()
        user.is_superuser = False
        user.rol = 'medico'
        user.centro = Mock()
        user.perm_dashboard = None  # Sin override
        user.perm_productos = None
        user.perm_lotes = None
        user.perm_requisiciones = None
        user.perm_centros = None
        user.perm_usuarios = None
        user.perm_reportes = None
        user.perm_trazabilidad = None
        user.perm_auditoria = None
        user.perm_notificaciones = None
        user.perm_movimientos = None
        user.perm_donaciones = None
        user.perm_crear_requisicion = None
        user.perm_autorizar_admin = None
        user.perm_autorizar_director = None
        user.perm_recibir_farmacia = None
        user.perm_autorizar_farmacia = None
        user.perm_surtir = None
        user.perm_confirmar_entrega = None
        
        permisos = build_perm_map(user)
        
        # Permisos que debe tener
        assert permisos.get('verDashboard') is True
        assert permisos.get('verProductos') is True
        assert permisos.get('verRequisiciones') is True
        assert permisos.get('crearRequisicion') is True
        assert permisos.get('confirmarRecepcion') is True
        
        # Permisos que NO debe tener
        assert permisos.get('verReportes') is False
        assert permisos.get('verTrazabilidad') is False
        assert permisos.get('autorizarAdmin') is False
        assert permisos.get('surtirRequisicion') is False
