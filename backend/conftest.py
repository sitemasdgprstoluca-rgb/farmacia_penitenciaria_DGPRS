"""
Pytest configuration for the backend tests.

Este archivo configura pytest para que funcione con modelos managed=False
que están diseñados para Supabase/PostgreSQL pero necesitan SQLite para tests.
"""
import pytest
from django.conf import settings


def pytest_configure():
    """Configure Django settings for pytest."""
    settings.DEBUG = False
    settings.TESTING = True


@pytest.fixture(scope='session')
def django_db_setup(django_db_blocker):
    """
    Configura la base de datos de tests creando tablas directamente desde modelos.
    
    Esta estrategia evita problemas con migraciones desincronizadas ya que:
    - Los modelos usan managed=False (BD real es Supabase)
    - Las migraciones pueden estar desactualizadas
    - SQLite se usa solo para tests
    
    Enfoque:
    1. Ejecutar solo migraciones de Django core (auth, sessions, etc)
    2. Crear tablas de la app 'core' directamente desde los modelos
    """
    from django.apps import apps
    from django.db import connection
    from django.core.management import call_command
    
    # Obtener todos los modelos de 'core' con managed=False
    core_models = []
    for app_config in apps.get_app_configs():
        if app_config.name == 'core':
            for model in app_config.get_models():
                core_models.append(model)
                # Cambiar temporalmente a managed=True
                model._meta.managed = True
    
    with django_db_blocker.unblock():
        # 1. Crear tablas de Django core (auth, sessions, contenttypes, etc)
        # Usamos fake para las de core ya que las crearemos manualmente
        call_command('migrate', 'contenttypes', verbosity=0, interactive=False)
        call_command('migrate', 'auth', verbosity=0, interactive=False)
        call_command('migrate', 'sessions', verbosity=0, interactive=False)
        call_command('migrate', 'admin', verbosity=0, interactive=False)
        
        # 2. Crear tablas de 'core' directamente desde los modelos
        # Esto evita problemas con migraciones desactualizadas
        with connection.schema_editor() as schema_editor:
            for model in core_models:
                try:
                    schema_editor.create_model(model)
                except Exception as e:
                    # La tabla puede ya existir o tener error
                    import sys
                    if 'already exists' not in str(e).lower():
                        print(f"[TEST] Error creando {model._meta.db_table}: {e}", file=sys.stderr)
    
    yield
    
    # Restaurar managed=False
    for model in core_models:
        model._meta.managed = False


@pytest.fixture
def api_client():
    """Create a DRF API client for testing."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, django_user_model, db):
    """Create an authenticated API client."""
    user = django_user_model.objects.create_user(
        username='testuser',
        email='test@test.com',
        password='testpass123',
        rol='admin'  # Rol en minúsculas
    )
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def admin_user(django_user_model, db):
    """Create an admin user for testing."""
    return django_user_model.objects.create_superuser(
        username='admin',
        email='admin@test.com',
        password='adminpass123',
        rol='admin'  # Rol en minúsculas
    )


# ============================================================================
# FIXTURES PARA CENTRO
# ============================================================================

@pytest.fixture
def centro(db):
    """Centro penitenciario para tests"""
    from core.models import Centro
    centro_obj, _ = Centro.objects.get_or_create(
        nombre='Centro Penitenciario Test',
        defaults={'direccion': 'Dirección de prueba', 'activo': True}
    )
    return centro_obj


# ============================================================================
# FIXTURES PARA PRODUCTOS Y LOTES
# ============================================================================

@pytest.fixture
def producto(db):
    """Producto/medicamento para tests"""
    from core.models import Producto
    producto_obj, _ = Producto.objects.get_or_create(
        clave='MED-TEST-001',
        defaults={
            'nombre': 'Medicamento Test',
            'unidad_medida': 'TABLETA',
            'categoria': 'medicamento',
            'activo': True
        }
    )
    return producto_obj


@pytest.fixture
def lote(producto, centro, db):
    """Lote con stock disponible para tests"""
    from core.models import Lote
    from datetime import date
    from decimal import Decimal
    
    lote_obj, _ = Lote.objects.get_or_create(
        producto=producto,
        numero_lote='LOT-TEST-001',
        defaults={
            'centro': centro,
            'fecha_caducidad': date(2027, 12, 31),
            'cantidad_inicial': 1000,
            'cantidad_actual': 500,
            'precio_unitario': Decimal('10.00'),
            'activo': True
        }
    )
    return lote_obj


# ============================================================================
# FIXTURES PARA USUARIOS CON ROLES ESPECÍFICOS
# ============================================================================

@pytest.fixture
def usuario_farmacia(django_user_model, db):
    """Usuario con rol farmacia"""
    user, _ = django_user_model.objects.get_or_create(
        username='farmacia_test',
        defaults={
            'email': 'farmacia@test.com',
            'rol': 'farmacia',
            'is_staff': True
        }
    )
    user.set_password('testpass123')
    user.save()
    return user


@pytest.fixture
def usuario_centro(django_user_model, centro, db):
    """Usuario con rol centro"""
    user, _ = django_user_model.objects.get_or_create(
        username='centro_test',
        defaults={
            'email': 'centro@test.com',
            'rol': 'centro',
            'centro': centro
        }
    )
    user.set_password('testpass123')
    user.save()
    return user


# ============================================================================
# FIXTURES PARA PACIENTES
# ============================================================================

@pytest.fixture
def paciente(centro, db):
    """Paciente/PPL para tests"""
    from core.models import Paciente
    from datetime import date
    
    paciente_obj, _ = Paciente.objects.get_or_create(
        numero_expediente='EXP-TEST-001',
        defaults={
            'nombre': 'Juan',
            'apellido_paterno': 'Pérez',
            'apellido_materno': 'García',
            'curp': 'PEGJ800101HDFRRL09',
            'fecha_nacimiento': date(1980, 1, 1),
            'sexo': 'M',
            'centro': centro,
            'dormitorio': 'A-101',
            'activo': True
        }
    )
    return paciente_obj


# ============================================================================
# FIXTURES PARA DISPENSACIONES
# ============================================================================

@pytest.fixture
def dispensacion(paciente, centro, usuario_centro, db):
    """Dispensación básica para tests"""
    from core.models import Dispensacion
    
    dispensacion_obj = Dispensacion.objects.create(
        folio='DISP-TEST-001',
        paciente=paciente,
        centro=centro,
        tipo_dispensacion='normal',
        estado='pendiente',
        responsable_solicitud=usuario_centro
    )
    return dispensacion_obj


# ============================================================================
# FIXTURES PARA COMPRAS CAJA CHICA
# ============================================================================

@pytest.fixture
def compra_caja_chica(centro, usuario_centro, db):
    """Compra de caja chica para tests"""
    from core.models import CompraCajaChica
    from decimal import Decimal
    
    compra_obj = CompraCajaChica.objects.create(
        folio='CC-TEST-001',
        centro=centro,
        proveedor_nombre='Farmacia Local Test',
        proveedor_rfc='XAXX010101000',
        motivo_compra='Medicamento urgente no disponible',
        estado='pendiente',
        solicitante=usuario_centro,
        subtotal=Decimal('100.00'),
        iva=Decimal('16.00'),
        total=Decimal('116.00')
    )
    return compra_obj


# ============================================================================
# FIXTURES PARA INVENTARIO CAJA CHICA
# ============================================================================

@pytest.fixture
def inventario_caja_chica(centro, producto, compra_caja_chica, db):
    """Item de inventario de caja chica para tests"""
    from core.models import InventarioCajaChica
    from datetime import date
    from decimal import Decimal
    
    inventario_obj = InventarioCajaChica.objects.create(
        centro=centro,
        producto=producto,
        descripcion_producto='Medicamento CC Test',
        numero_lote='LOT-CC-TEST-001',
        fecha_caducidad=date(2027, 12, 31),
        cantidad_inicial=100,
        cantidad_actual=100,
        compra=compra_caja_chica,
        precio_unitario=Decimal('10.00'),
        activo=True
    )
    return inventario_obj
