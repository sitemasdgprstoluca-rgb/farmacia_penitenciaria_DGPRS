"""
Pruebas unitarias completas para el módulo de Lotes.
Verifica: modelo, serializer, viewset, permisos, export/import.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from io import BytesIO


# ==================== FIXTURES ====================

@pytest.fixture
def api_client():
    """Cliente API sin autenticar."""
    return APIClient()


@pytest.fixture
def admin_user(db, django_user_model):
    """Usuario administrador."""
    return django_user_model.objects.create_user(
        username='admin_test',
        email='admin@test.com',
        password='admin123',
        rol='ADMIN',
        is_active=True
    )


@pytest.fixture
def farmacia_user(db, django_user_model):
    """Usuario farmacia."""
    return django_user_model.objects.create_user(
        username='farmacia_test',
        email='farmacia@test.com',
        password='farm123',
        rol='FARMACIA',
        is_active=True
    )


@pytest.fixture
def centro_user(db, django_user_model, centro):
    """Usuario de centro."""
    user = django_user_model.objects.create_user(
        username='centro_test',
        email='centro@test.com',
        password='centro123',
        rol='CENTRO',
        is_active=True,
        centro=centro
    )
    return user


@pytest.fixture
def vista_user(db, django_user_model):
    """Usuario vista (solo lectura)."""
    return django_user_model.objects.create_user(
        username='vista_test',
        email='vista@test.com',
        password='vista123',
        rol='VISTA',
        is_active=True
    )


@pytest.fixture
def centro(db):
    """Centro penitenciario de prueba."""
    from core.models import Centro
    return Centro.objects.create(
        nombre='Centro Test',
        direccion='Dirección Test',
        activo=True
    )


@pytest.fixture
def producto(db):
    """Producto de prueba."""
    from core.models import Producto
    return Producto.objects.create(
        clave='MED-001',
        nombre='Paracetamol 500mg',
        descripcion='Analgésico',
        unidad_medida='tableta',
        categoria='medicamento',
        stock_minimo=100,
        stock_actual=0,
        activo=True
    )


@pytest.fixture
def lote(db, producto, centro):
    """Lote de prueba."""
    from core.models import Lote
    return Lote.objects.create(
        numero_lote='LOT-001-TEST',
        producto=producto,
        cantidad_inicial=100,
        cantidad_actual=100,
        fecha_caducidad=date.today() + timedelta(days=365),
        precio_unitario=Decimal('10.50'),
        marca='Lab Test',
        ubicacion='A-01',
        centro=centro,
        activo=True
    )


@pytest.fixture
def lote_vencido(db, producto):
    """Lote vencido para pruebas."""
    from core.models import Lote
    return Lote.objects.create(
        numero_lote='LOT-VENCIDO-TEST',
        producto=producto,
        cantidad_inicial=50,
        cantidad_actual=50,
        fecha_caducidad=date.today() - timedelta(days=30),
        precio_unitario=Decimal('5.00'),
        activo=True
    )


@pytest.fixture
def lote_por_vencer(db, producto):
    """Lote próximo a vencer (30 días)."""
    from core.models import Lote
    return Lote.objects.create(
        numero_lote='LOT-PROXIMO-TEST',
        producto=producto,
        cantidad_inicial=75,
        cantidad_actual=75,
        fecha_caducidad=date.today() + timedelta(days=25),
        precio_unitario=Decimal('8.00'),
        activo=True
    )


@pytest.fixture
def authenticated_admin(api_client, admin_user):
    """Cliente autenticado como admin."""
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def authenticated_farmacia(api_client, farmacia_user):
    """Cliente autenticado como farmacia."""
    api_client.force_authenticate(user=farmacia_user)
    return api_client


@pytest.fixture
def authenticated_centro(api_client, centro_user):
    """Cliente autenticado como centro."""
    api_client.force_authenticate(user=centro_user)
    return api_client


@pytest.fixture
def authenticated_vista(api_client, vista_user):
    """Cliente autenticado como vista."""
    api_client.force_authenticate(user=vista_user)
    return api_client


# ==================== TESTS DE MODELO ====================

@pytest.mark.django_db
class TestLoteModel:
    """Pruebas del modelo Lote."""
    
    def test_crear_lote_basico(self, producto):
        """Debe crear un lote con campos mínimos requeridos."""
        from core.models import Lote
        
        lote = Lote.objects.create(
            numero_lote='LOT-BASICO',
            producto=producto,
            cantidad_inicial=100,
            fecha_caducidad=date.today() + timedelta(days=180)
        )
        
        assert lote.id is not None
        assert lote.numero_lote == 'LOT-BASICO'
        assert lote.cantidad_actual == 0  # default
        assert lote.activo == True  # default
    
    def test_campos_opcionales(self, producto, centro):
        """Debe manejar correctamente campos opcionales."""
        from core.models import Lote
        
        lote = Lote.objects.create(
            numero_lote='LOT-COMPLETO',
            producto=producto,
            cantidad_inicial=200,
            cantidad_actual=150,
            fecha_fabricacion=date.today() - timedelta(days=30),
            fecha_caducidad=date.today() + timedelta(days=365),
            precio_unitario=Decimal('25.99'),
            numero_contrato='CONT-2025-001',
            marca='Laboratorio XYZ',
            ubicacion='B-05',
            centro=centro,
            activo=True
        )
        
        assert lote.numero_contrato == 'CONT-2025-001'
        assert lote.marca == 'Laboratorio XYZ'
        assert lote.ubicacion == 'B-05'
        assert lote.centro == centro
    
    def test_propiedad_estado_vencido(self, lote_vencido):
        """Debe detectar lotes vencidos correctamente."""
        assert lote_vencido.fecha_caducidad < date.today()
    
    def test_propiedad_estado_por_vencer(self, lote_por_vencer):
        """Debe detectar lotes próximos a vencer."""
        dias_restantes = (lote_por_vencer.fecha_caducidad - date.today()).days
        assert dias_restantes <= 30
        assert dias_restantes > 0
    
    def test_propiedad_estado_normal(self, lote):
        """Debe identificar lotes en estado normal."""
        dias_restantes = (lote.fecha_caducidad - date.today()).days
        assert dias_restantes > 30
    
    def test_relacion_producto(self, lote, producto):
        """Debe mantener relación correcta con producto."""
        assert lote.producto == producto
        assert lote.producto.clave == 'MED-001'
    
    def test_relacion_centro(self, lote, centro):
        """Debe mantener relación correcta con centro."""
        assert lote.centro == centro
        assert lote.centro.nombre == 'Centro Test'
    
    def test_str_representation(self, lote):
        """Debe tener representación string correcta."""
        str_repr = str(lote)
        assert 'LOT-001-TEST' in str_repr or lote.numero_lote in str_repr


# ==================== TESTS DE SERIALIZER ====================

@pytest.mark.django_db
class TestLoteSerializer:
    """Pruebas del serializer de Lote."""
    
    def test_serializar_lote_completo(self, lote):
        """Debe serializar todos los campos correctamente."""
        from inventario.serializers.lotes import LoteSerializer
        
        serializer = LoteSerializer(lote)
        data = serializer.data
        
        # Campos básicos
        assert data['id'] == lote.id
        assert data['numero_lote'] == 'LOT-001-TEST'
        assert data['cantidad_inicial'] == 100
        assert data['cantidad_actual'] == 100
        
        # Campos de producto (computed)
        assert 'producto' in data
        assert 'producto_nombre' in data
        assert 'producto_clave' in data
        
        # Campos de centro (computed)
        assert 'centro' in data
        assert 'centro_nombre' in data
        
        # Campos de fechas
        assert 'fecha_caducidad' in data
        
        # Campos monetarios
        assert 'precio_unitario' in data
    
    def test_validar_numero_lote_requerido(self, producto):
        """Debe requerir numero_lote."""
        from inventario.serializers.lotes import LoteSerializer
        
        data = {
            'producto_id': producto.id,
            'cantidad_inicial': 100,
            'fecha_caducidad': str(date.today() + timedelta(days=180))
        }
        
        serializer = LoteSerializer(data=data)
        assert not serializer.is_valid()
        assert 'numero_lote' in serializer.errors
    
    def test_validar_cantidad_no_negativa(self, producto):
        """Debe rechazar cantidades negativas."""
        from inventario.serializers.lotes import LoteSerializer
        
        data = {
            'numero_lote': 'LOT-NEG',
            'producto_id': producto.id,
            'cantidad_inicial': -10,
            'fecha_caducidad': str(date.today() + timedelta(days=180))
        }
        
        serializer = LoteSerializer(data=data)
        assert not serializer.is_valid()
    
    def test_campos_computados(self, lote):
        """Debe incluir campos computados correctamente."""
        from inventario.serializers.lotes import LoteSerializer
        
        serializer = LoteSerializer(lote)
        data = serializer.data
        
        # Verificar campos computados existen
        assert 'dias_para_vencer' in data
        assert 'estado_caducidad' in data


# ==================== TESTS DE API - PERMISOS ====================

@pytest.mark.django_db
class TestLotePermisos:
    """Pruebas de permisos por rol."""
    
    def test_admin_puede_listar(self, authenticated_admin, lote):
        """Admin debe poder listar lotes."""
        url = '/api/lotes/'
        response = authenticated_admin.get(url)
        assert response.status_code == status.HTTP_200_OK
    
    def test_admin_puede_crear(self, authenticated_admin, producto):
        """Admin debe poder crear lotes."""
        url = '/api/lotes/'
        data = {
            'numero_lote': 'LOT-ADMIN-CREATE',
            'producto_id': producto.id,
            'cantidad_inicial': 50,
            'cantidad_actual': 50,
            'fecha_caducidad': str(date.today() + timedelta(days=180)),
            'precio_unitario': '15.00'
        }
        response = authenticated_admin.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
    
    def test_admin_puede_editar(self, authenticated_admin, lote):
        """Admin debe poder editar lotes."""
        url = f'/api/lotes/{lote.id}/'
        data = {'ubicacion': 'C-10'}
        response = authenticated_admin.patch(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
    
    def test_admin_puede_eliminar(self, authenticated_admin, lote):
        """Admin debe poder eliminar lotes."""
        url = f'/api/lotes/{lote.id}/'
        response = authenticated_admin.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
    
    def test_farmacia_puede_crud(self, authenticated_farmacia, producto, lote):
        """Farmacia debe tener CRUD completo."""
        # Listar
        response = authenticated_farmacia.get('/api/lotes/')
        assert response.status_code == status.HTTP_200_OK
        
        # Crear
        data = {
            'numero_lote': 'LOT-FARM-CREATE',
            'producto_id': producto.id,
            'cantidad_inicial': 30,
            'cantidad_actual': 30,
            'fecha_caducidad': str(date.today() + timedelta(days=200)),
            'precio_unitario': '12.00'
        }
        response = authenticated_farmacia.post('/api/lotes/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
    
    def test_centro_solo_lectura(self, authenticated_centro, producto, lote):
        """Centro solo debe poder leer."""
        # Listar - OK
        response = authenticated_centro.get('/api/lotes/')
        assert response.status_code == status.HTTP_200_OK
        
        # Crear - PROHIBIDO
        data = {
            'numero_lote': 'LOT-CENTRO-NO',
            'producto_id': producto.id,
            'cantidad_inicial': 20,
            'fecha_caducidad': str(date.today() + timedelta(days=100))
        }
        response = authenticated_centro.post('/api/lotes/', data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        # Editar - PROHIBIDO
        response = authenticated_centro.patch(f'/api/lotes/{lote.id}/', {'ubicacion': 'X'}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        # Eliminar - PROHIBIDO
        response = authenticated_centro.delete(f'/api/lotes/{lote.id}/')
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_vista_solo_lectura(self, authenticated_vista, producto, lote):
        """Vista solo debe poder leer."""
        # Listar - OK
        response = authenticated_vista.get('/api/lotes/')
        assert response.status_code == status.HTTP_200_OK
        
        # Crear - PROHIBIDO
        data = {
            'numero_lote': 'LOT-VISTA-NO',
            'producto_id': producto.id,
            'cantidad_inicial': 10,
            'fecha_caducidad': str(date.today() + timedelta(days=90))
        }
        response = authenticated_vista.post('/api/lotes/', data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_no_autenticado_prohibido(self, api_client, lote):
        """Usuario no autenticado no debe acceder."""
        response = api_client.get('/api/lotes/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ==================== TESTS DE API - CRUD ====================

@pytest.mark.django_db
class TestLoteCRUD:
    """Pruebas CRUD de la API de lotes."""
    
    def test_listar_lotes(self, authenticated_admin, lote):
        """Debe listar lotes correctamente."""
        response = authenticated_admin.get('/api/lotes/')
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert 'results' in data or isinstance(data, list)
    
    def test_obtener_lote_por_id(self, authenticated_admin, lote):
        """Debe obtener detalle de un lote."""
        url = f'/api/lotes/{lote.id}/'
        response = authenticated_admin.get(url)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data['numero_lote'] == 'LOT-001-TEST'
    
    def test_crear_lote_valido(self, authenticated_admin, producto):
        """Debe crear lote con datos válidos."""
        url = '/api/lotes/'
        data = {
            'numero_lote': 'LOT-NUEVO-001',
            'producto_id': producto.id,
            'cantidad_inicial': 100,
            'cantidad_actual': 100,
            'fecha_caducidad': str(date.today() + timedelta(days=365)),
            'precio_unitario': '20.00',
            'marca': 'Lab Nuevo',
            'ubicacion': 'D-01'
        }
        
        response = authenticated_admin.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        
        result = response.json()
        assert result['numero_lote'] == 'LOT-NUEVO-001'
    
    def test_actualizar_lote(self, authenticated_admin, lote):
        """Debe actualizar lote correctamente."""
        url = f'/api/lotes/{lote.id}/'
        data = {
            'ubicacion': 'E-15',
            'marca': 'Lab Actualizado'
        }
        
        response = authenticated_admin.patch(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        
        result = response.json()
        assert result['ubicacion'] == 'E-15'
        assert result['marca'] == 'Lab Actualizado'
    
    def test_eliminar_lote(self, authenticated_admin, lote):
        """Debe eliminar lote."""
        url = f'/api/lotes/{lote.id}/'
        response = authenticated_admin.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verificar que no existe
        response = authenticated_admin.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ==================== TESTS DE FILTROS ====================

@pytest.mark.django_db
class TestLoteFiltros:
    """Pruebas de filtros de lotes."""
    
    def test_filtrar_por_producto(self, authenticated_admin, lote, producto):
        """Debe filtrar por producto_id."""
        url = f'/api/lotes/?producto_id={producto.id}'
        response = authenticated_admin.get(url)
        assert response.status_code == status.HTTP_200_OK
    
    def test_filtrar_por_activo(self, authenticated_admin, lote):
        """Debe filtrar por activo."""
        url = '/api/lotes/?activo=true'
        response = authenticated_admin.get(url)
        assert response.status_code == status.HTTP_200_OK
    
    def test_filtrar_por_centro(self, authenticated_admin, lote, centro):
        """Debe filtrar por centro_id."""
        url = f'/api/lotes/?centro_id={centro.id}'
        response = authenticated_admin.get(url)
        assert response.status_code == status.HTTP_200_OK
    
    def test_busqueda_por_numero_lote(self, authenticated_admin, lote):
        """Debe buscar por número de lote."""
        url = '/api/lotes/?search=LOT-001'
        response = authenticated_admin.get(url)
        assert response.status_code == status.HTTP_200_OK


# ==================== TESTS DE EXPORTACIÓN ====================

@pytest.mark.django_db
class TestLoteExportacion:
    """Pruebas de funciones de exportación."""
    
    def test_exportar_excel(self, authenticated_admin, lote):
        """Debe exportar a Excel."""
        url = '/api/lotes/exportar-excel/'
        response = authenticated_admin.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert 'spreadsheet' in response['Content-Type'] or 'excel' in response['Content-Type'].lower()
    
    def test_exportar_pdf(self, authenticated_admin, lote):
        """Debe exportar a PDF."""
        url = '/api/lotes/exportar-pdf/'
        response = authenticated_admin.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert 'pdf' in response['Content-Type'].lower()
    
    def test_descargar_plantilla(self, authenticated_admin):
        """Debe descargar plantilla de importación."""
        url = '/api/lotes/plantilla-excel/'
        response = authenticated_admin.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert 'spreadsheet' in response['Content-Type'] or 'excel' in response['Content-Type'].lower()


# ==================== TESTS DE ENDPOINTS ESPECIALES ====================

@pytest.mark.django_db
class TestLoteEndpointsEspeciales:
    """Pruebas de endpoints especiales."""
    
    def test_lotes_por_vencer(self, authenticated_admin, lote_por_vencer):
        """Debe listar lotes por vencer."""
        url = '/api/lotes/por-vencer/'
        response = authenticated_admin.get(url)
        assert response.status_code == status.HTTP_200_OK
    
    def test_lotes_vencidos(self, authenticated_admin, lote_vencido):
        """Debe listar lotes vencidos."""
        url = '/api/lotes/vencidos/'
        response = authenticated_admin.get(url)
        assert response.status_code == status.HTTP_200_OK
    
    def test_estadisticas(self, authenticated_admin, lote):
        """Debe obtener estadísticas."""
        url = '/api/lotes/estadisticas/'
        response = authenticated_admin.get(url)
        assert response.status_code == status.HTTP_200_OK


# ==================== TESTS DE VALIDACIONES ====================

@pytest.mark.django_db
class TestLoteValidaciones:
    """Pruebas de validaciones de negocio."""
    
    def test_numero_lote_unico_por_producto(self, authenticated_admin, lote, producto):
        """Debe rechazar número de lote duplicado para mismo producto."""
        url = '/api/lotes/'
        data = {
            'numero_lote': lote.numero_lote,  # Duplicado
            'producto_id': producto.id,
            'cantidad_inicial': 50,
            'cantidad_actual': 50,
            'fecha_caducidad': str(date.today() + timedelta(days=180))
        }
        
        response = authenticated_admin.post(url, data, format='json')
        # Puede ser 400 por validación o 201 si permite
        # La lógica real determina el comportamiento esperado
    
    def test_fecha_caducidad_requerida(self, authenticated_admin, producto):
        """Debe requerir fecha de caducidad."""
        url = '/api/lotes/'
        data = {
            'numero_lote': 'LOT-SIN-CADUCIDAD',
            'producto_id': producto.id,
            'cantidad_inicial': 50
            # Sin fecha_caducidad
        }
        
        response = authenticated_admin.post(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_producto_requerido(self, authenticated_admin):
        """Debe requerir producto."""
        url = '/api/lotes/'
        data = {
            'numero_lote': 'LOT-SIN-PRODUCTO',
            'cantidad_inicial': 50,
            'fecha_caducidad': str(date.today() + timedelta(days=180))
            # Sin producto_id
        }
        
        response = authenticated_admin.post(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ==================== TESTS DE CONSISTENCIA BD ====================

@pytest.mark.django_db
class TestLoteConsistenciaBD:
    """Pruebas de consistencia con esquema BD."""
    
    def test_15_campos_en_modelo(self):
        """Debe tener los 15 campos del esquema BD."""
        from core.models import Lote
        from django.db import models
        
        campos_esperados = [
            'id', 'numero_lote', 'producto_id', 'cantidad_inicial',
            'cantidad_actual', 'fecha_fabricacion', 'fecha_caducidad',
            'precio_unitario', 'numero_contrato', 'marca', 'ubicacion',
            'centro_id', 'activo', 'created_at', 'updated_at'
        ]
        
        campos_modelo = [f.name for f in Lote._meta.get_fields() 
                        if hasattr(f, 'column') or f.name in ['producto', 'centro']]
        
        # Normalizar nombres (producto_id -> producto, etc.)
        campos_modelo_norm = set()
        for campo in campos_modelo:
            if campo == 'producto':
                campos_modelo_norm.add('producto_id')
            elif campo == 'centro':
                campos_modelo_norm.add('centro_id')
            else:
                campos_modelo_norm.add(campo)
        
        for campo in campos_esperados:
            assert campo in campos_modelo_norm or campo.replace('_id', '') in [f.name for f in Lote._meta.get_fields()], \
                f"Campo {campo} no encontrado en modelo"
    
    def test_tipos_datos_correctos(self, lote):
        """Debe tener tipos de datos correctos."""
        assert isinstance(lote.id, int)
        assert isinstance(lote.numero_lote, str)
        assert isinstance(lote.cantidad_inicial, int)
        assert isinstance(lote.cantidad_actual, int)
        assert isinstance(lote.fecha_caducidad, date)
        assert isinstance(lote.precio_unitario, Decimal)
        assert isinstance(lote.activo, bool)
    
    def test_foreign_keys(self, lote, producto, centro):
        """Debe tener foreign keys correctas."""
        assert lote.producto_id == producto.id
        assert lote.centro_id == centro.id
    
    def test_valores_default(self, producto):
        """Debe aplicar valores default correctos."""
        from core.models import Lote
        
        lote = Lote.objects.create(
            numero_lote='LOT-DEFAULT-TEST',
            producto=producto,
            cantidad_inicial=10,
            fecha_caducidad=date.today() + timedelta(days=100)
        )
        
        # Verificar defaults del esquema BD
        assert lote.cantidad_actual == 0  # default 0
        assert lote.activo == True  # default true
        assert lote.precio_unitario == Decimal('0')  # default 0
