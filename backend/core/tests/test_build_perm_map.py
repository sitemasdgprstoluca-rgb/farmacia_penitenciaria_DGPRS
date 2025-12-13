"""
Tests para verificar que build_perm_map genera permisos correctos por rol.

ISS-FIX: Verificar que roles de Centro NO reciben verReportes/verTrazabilidad,
alineando el comportamiento del serializer con la definición esperada.
"""

import pytest
from django.contrib.auth import get_user_model
from core.models import Centro
from core.serializers import build_perm_map, _resolve_rol, PERMISOS_POR_ROL

User = get_user_model()


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def centro():
    """Centro penitenciario de prueba."""
    return Centro.objects.create(clave='TST001', nombre='Centro Test')


@pytest.fixture
def user_administrador_centro(centro):
    """Usuario con rol administrador_centro."""
    user = User.objects.create_user(
        username='admin_centro_test',
        password='test123',
        rol='administrador_centro',
        centro=centro
    )
    return user


@pytest.fixture
def user_director_centro(centro):
    """Usuario con rol director_centro."""
    user = User.objects.create_user(
        username='director_centro_test',
        password='test123',
        rol='director_centro',
        centro=centro
    )
    return user


@pytest.fixture
def user_medico(centro):
    """Usuario con rol medico."""
    user = User.objects.create_user(
        username='medico_test',
        password='test123',
        rol='medico',
        centro=centro
    )
    return user


@pytest.fixture
def user_centro(centro):
    """Usuario con rol centro."""
    user = User.objects.create_user(
        username='centro_test',
        password='test123',
        rol='centro',
        centro=centro
    )
    return user


@pytest.fixture
def user_farmacia():
    """Usuario con rol farmacia."""
    user = User.objects.create_user(
        username='farmacia_test',
        password='test123',
        rol='farmacia',
        centro=None  # Farmacia no tiene centro
    )
    return user


@pytest.fixture
def user_admin():
    """Usuario superuser/admin."""
    user = User.objects.create_superuser(
        username='admin_test',
        password='test123',
        email='admin@test.com'
    )
    return user


# =============================================================================
# TESTS: Roles de Centro NO deben ver Reportes/Trazabilidad
# =============================================================================

@pytest.mark.django_db
class TestBuildPermMapCentroRoles:
    """
    Tests que verifican que los roles de Centro NO tienen permisos de
    Reportes y Trazabilidad.
    """
    
    def test_administrador_centro_no_ve_reportes(self, user_administrador_centro):
        """ISS-FIX: administrador_centro NO debe tener verReportes."""
        permisos = build_perm_map(user_administrador_centro)
        
        assert permisos['verReportes'] is False, \
            f"administrador_centro no debe tener verReportes, pero tiene: {permisos['verReportes']}"
    
    def test_administrador_centro_no_ve_trazabilidad(self, user_administrador_centro):
        """ISS-FIX: administrador_centro NO debe tener verTrazabilidad."""
        permisos = build_perm_map(user_administrador_centro)
        
        assert permisos['verTrazabilidad'] is False, \
            f"administrador_centro no debe tener verTrazabilidad, pero tiene: {permisos['verTrazabilidad']}"
    
    def test_director_centro_no_ve_reportes(self, user_director_centro):
        """ISS-FIX: director_centro NO debe tener verReportes."""
        permisos = build_perm_map(user_director_centro)
        
        assert permisos['verReportes'] is False, \
            f"director_centro no debe tener verReportes, pero tiene: {permisos['verReportes']}"
    
    def test_director_centro_no_ve_trazabilidad(self, user_director_centro):
        """ISS-FIX: director_centro NO debe tener verTrazabilidad."""
        permisos = build_perm_map(user_director_centro)
        
        assert permisos['verTrazabilidad'] is False, \
            f"director_centro no debe tener verTrazabilidad, pero tiene: {permisos['verTrazabilidad']}"
    
    def test_medico_no_ve_reportes(self, user_medico):
        """medico NO debe tener verReportes."""
        permisos = build_perm_map(user_medico)
        
        assert permisos['verReportes'] is False, \
            f"medico no debe tener verReportes, pero tiene: {permisos['verReportes']}"
    
    def test_medico_no_ve_trazabilidad(self, user_medico):
        """medico NO debe tener verTrazabilidad."""
        permisos = build_perm_map(user_medico)
        
        assert permisos['verTrazabilidad'] is False, \
            f"medico no debe tener verTrazabilidad, pero tiene: {permisos['verTrazabilidad']}"
    
    def test_centro_no_ve_reportes(self, user_centro):
        """ISS-FIX: centro NO debe tener verReportes."""
        permisos = build_perm_map(user_centro)
        
        assert permisos['verReportes'] is False, \
            f"centro no debe tener verReportes, pero tiene: {permisos['verReportes']}"
    
    def test_centro_no_ve_trazabilidad(self, user_centro):
        """ISS-FIX: centro NO debe tener verTrazabilidad."""
        permisos = build_perm_map(user_centro)
        
        assert permisos['verTrazabilidad'] is False, \
            f"centro no debe tener verTrazabilidad, pero tiene: {permisos['verTrazabilidad']}"


@pytest.mark.django_db
class TestBuildPermMapFarmaciaYAdmin:
    """
    Tests que verifican que Farmacia y Admin SÍ tienen permisos de
    Reportes y Trazabilidad.
    """
    
    def test_farmacia_si_ve_reportes(self, user_farmacia):
        """farmacia SÍ debe tener verReportes."""
        permisos = build_perm_map(user_farmacia)
        
        assert permisos['verReportes'] is True, \
            f"farmacia debe tener verReportes, pero tiene: {permisos['verReportes']}"
    
    def test_farmacia_si_ve_trazabilidad(self, user_farmacia):
        """farmacia SÍ debe tener verTrazabilidad."""
        permisos = build_perm_map(user_farmacia)
        
        assert permisos['verTrazabilidad'] is True, \
            f"farmacia debe tener verTrazabilidad, pero tiene: {permisos['verTrazabilidad']}"
    
    def test_superuser_si_ve_reportes(self, user_admin):
        """superuser SÍ debe tener verReportes."""
        permisos = build_perm_map(user_admin)
        
        assert permisos['verReportes'] is True, \
            f"superuser debe tener verReportes, pero tiene: {permisos['verReportes']}"
    
    def test_superuser_si_ve_trazabilidad(self, user_admin):
        """superuser SÍ debe tener verTrazabilidad."""
        permisos = build_perm_map(user_admin)
        
        assert permisos['verTrazabilidad'] is True, \
            f"superuser debe tener verTrazabilidad, pero tiene: {permisos['verTrazabilidad']}"


@pytest.mark.django_db
class TestBuildPermMapConOverridesBD:
    """
    Tests que verifican el comportamiento cuando hay valores en BD.
    ISS-FIX: Aunque en BD estuvieran True, el rol base debe prevalecer.
    
    NOTA: Actualmente build_perm_map respeta los valores de BD como override,
    por eso es importante que PERMISOS_POR_ROL tenga valores correctos
    y que los datos de BD estén sanitizados.
    """
    
    def test_administrador_centro_con_perm_reportes_true_en_bd(self, centro):
        """
        ISS-FIX: Si un admin_centro tiene perm_reportes=True en BD,
        build_perm_map lo devolverá así (por diseño de override).
        Este test documenta el comportamiento y la necesidad de sanitizar BD.
        """
        user = User.objects.create_user(
            username='admin_centro_override',
            password='test123',
            rol='administrador_centro',
            centro=centro,
            perm_reportes=True,  # Override incorrecto en BD
        )
        
        permisos = build_perm_map(user)
        
        # El override de BD prevalece - por eso es crucial sanitizar
        # Este test documenta el comportamiento actual
        assert permisos['verReportes'] is True, \
            "Override de BD debe prevalecer (necesita sanitización)"
    
    def test_administrador_centro_sin_override_usa_default(self, centro):
        """
        Si un admin_centro tiene perm_reportes=None (sin override),
        debe usar el default del rol que ahora es False.
        """
        user = User.objects.create_user(
            username='admin_centro_default',
            password='test123',
            rol='administrador_centro',
            centro=centro,
            perm_reportes=None,  # Sin override
        )
        
        permisos = build_perm_map(user)
        
        # Debe usar el default del rol (False después del fix)
        assert permisos['verReportes'] is False, \
            f"Sin override, debe usar default del rol (False), pero tiene: {permisos['verReportes']}"


@pytest.mark.django_db  
class TestResolveRol:
    """Tests para _resolve_rol que determina el rol efectivo."""
    
    def test_resolve_administrador_centro(self, user_administrador_centro):
        """administrador_centro se resuelve a ADMINISTRADOR_CENTRO."""
        rol = _resolve_rol(user_administrador_centro)
        assert rol == 'ADMINISTRADOR_CENTRO'
    
    def test_resolve_director_centro(self, user_director_centro):
        """director_centro se resuelve a DIRECTOR_CENTRO."""
        rol = _resolve_rol(user_director_centro)
        assert rol == 'DIRECTOR_CENTRO'
    
    def test_resolve_farmacia(self, user_farmacia):
        """farmacia se resuelve a FARMACIA."""
        rol = _resolve_rol(user_farmacia)
        assert rol == 'FARMACIA'
    
    def test_resolve_superuser(self, user_admin):
        """superuser se resuelve a ADMIN."""
        rol = _resolve_rol(user_admin)
        assert rol == 'ADMIN'


@pytest.mark.django_db
class TestPermisosFlujoCentro:
    """Tests de permisos específicos del flujo de requisiciones para roles de Centro."""
    
    def test_administrador_centro_puede_autorizar_admin(self, user_administrador_centro):
        """administrador_centro puede usar autorizarAdmin."""
        permisos = build_perm_map(user_administrador_centro)
        assert permisos['autorizarAdmin'] is True
        assert permisos['autorizarDirector'] is False
    
    def test_director_centro_puede_autorizar_director(self, user_director_centro):
        """director_centro puede usar autorizarDirector."""
        permisos = build_perm_map(user_director_centro)
        assert permisos['autorizarAdmin'] is False
        assert permisos['autorizarDirector'] is True
    
    def test_medico_puede_crear_requisicion(self, user_medico):
        """medico puede crear requisiciones."""
        permisos = build_perm_map(user_medico)
        assert permisos['crearRequisicion'] is True
        assert permisos['autorizarAdmin'] is False
        assert permisos['autorizarDirector'] is False


@pytest.mark.django_db
class TestPermisosSerializerVsModelAlineados:
    """
    Tests que verifican que PERMISOS_POR_ROL del serializer está alineado
    con la definición del modelo después del fix.
    """
    
    def test_serializer_centro_roles_no_tienen_reportes(self):
        """
        Verificar que PERMISOS_POR_ROL del serializer tiene verReportes=False
        para roles de Centro.
        """
        roles_centro = ['ADMINISTRADOR_CENTRO', 'DIRECTOR_CENTRO', 'CENTRO', 'MEDICO']
        
        for rol in roles_centro:
            assert PERMISOS_POR_ROL[rol]['verReportes'] is False, \
                f"{rol} en serializer debe tener verReportes=False"
    
    def test_serializer_centro_roles_no_tienen_trazabilidad(self):
        """
        Verificar que PERMISOS_POR_ROL del serializer tiene verTrazabilidad=False
        para roles de Centro.
        """
        roles_centro = ['ADMINISTRADOR_CENTRO', 'DIRECTOR_CENTRO', 'CENTRO', 'MEDICO']
        
        for rol in roles_centro:
            assert PERMISOS_POR_ROL[rol]['verTrazabilidad'] is False, \
                f"{rol} en serializer debe tener verTrazabilidad=False"
    
    def test_serializer_farmacia_tiene_reportes(self):
        """Verificar que FARMACIA tiene verReportes=True."""
        assert PERMISOS_POR_ROL['FARMACIA']['verReportes'] is True
    
    def test_serializer_farmacia_tiene_trazabilidad(self):
        """Verificar que FARMACIA tiene verTrazabilidad=True."""
        assert PERMISOS_POR_ROL['FARMACIA']['verTrazabilidad'] is True
