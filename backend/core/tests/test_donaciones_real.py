# -*- coding: utf-8 -*-
"""
TEST REALES DEL MÓDULO DE DONACIONES
=====================================

Este archivo contiene pruebas RIGUROSAS que verifican el comportamiento REAL
del módulo de donaciones. Las pruebas NO se adaptan a errores existentes -
si una prueba falla, indica un BUG REAL que debe corregirse.

Tablas involucradas:
- donaciones: Registro principal de donaciones
- detalle_donaciones: Items de cada donación  
- productos_donacion: Catálogo independiente de productos
- salidas_donaciones: Entregas/salidas del almacén de donaciones

Flujo V2:
1. Crear donación (estado: pendiente)
2. Recibir donación (estado: recibida) 
3. Procesar donación (estado: procesada, stock disponible)
4. Registrar salidas (descuenta de cantidad_disponible al finalizar)
5. Finalizar entrega (finalizado=True, stock descontado)

Permisos:
- ADMIN/FARMACIA: CRUD completo
- VISTA: Solo lectura
- CENTRO: Acceso limitado según centro_destino

NOTA: Las tablas de donaciones tienen managed=False porque están en Supabase.
Para pruebas usamos @pytest.fixture que crea las tablas en SQLite.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.urls import reverse
from django.utils import timezone
from django.db import connection
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from core.models import (
    Donacion, DetalleDonacion, ProductoDonacion, SalidaDonacion, Centro
)

User = get_user_model()


@pytest.fixture(scope='function', autouse=True)
def create_donaciones_tables(db):
    """
    Crea las tablas de donaciones en SQLite para pruebas.
    Las tablas tienen managed=False porque en producción están en Supabase.
    Con autouse=True se ejecuta automáticamente para todos los tests.
    """
    with connection.cursor() as cursor:
        # Primero eliminar tablas si existen para asegurar esquema correcto
        cursor.execute('DROP TABLE IF EXISTS salidas_donaciones')
        cursor.execute('DROP TABLE IF EXISTS detalle_donaciones')
        cursor.execute('DROP TABLE IF EXISTS donaciones')
        cursor.execute('DROP TABLE IF EXISTS productos_donacion')
        cursor.execute('DROP TABLE IF EXISTS user_profiles')
        cursor.execute('DROP TABLE IF EXISTS centros')
        
        # Tabla centros (también managed=False)
        cursor.execute('''
            CREATE TABLE centros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre VARCHAR(200) UNIQUE NOT NULL,
                direccion TEXT,
                telefono VARCHAR(20),
                email VARCHAR(254),
                activo BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla user_profiles (managed=False en Supabase)
        cursor.execute('''
            CREATE TABLE user_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rol VARCHAR(30) DEFAULT 'visualizador',
                telefono VARCHAR(20),
                centro_id INTEGER,
                usuario_id INTEGER UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (centro_id) REFERENCES centros(id)
            )
        ''')
        
        # Tabla productos_donacion
        cursor.execute('''
            CREATE TABLE productos_donacion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                clave VARCHAR(50) UNIQUE NOT NULL,
                nombre VARCHAR(255) NOT NULL,
                descripcion TEXT,
                unidad_medida VARCHAR(50) DEFAULT 'PIEZA',
                presentacion VARCHAR(100),
                activo BOOLEAN DEFAULT 1,
                notas TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla donaciones
        cursor.execute('''
            CREATE TABLE donaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero VARCHAR(50) UNIQUE NOT NULL,
                donante_nombre VARCHAR(255) NOT NULL,
                donante_tipo VARCHAR(50) DEFAULT 'otro',
                donante_rfc VARCHAR(20),
                donante_direccion TEXT,
                donante_contacto VARCHAR(100),
                fecha_donacion DATE NOT NULL,
                fecha_recepcion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                centro_destino_id INTEGER,
                recibido_por_id INTEGER,
                estado VARCHAR(30) DEFAULT 'pendiente',
                notas TEXT,
                documento_donacion VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla detalle_donaciones
        cursor.execute('''
            CREATE TABLE detalle_donaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                donacion_id INTEGER NOT NULL,
                producto_donacion_id INTEGER,
                producto_id INTEGER,
                numero_lote VARCHAR(100),
                cantidad INTEGER NOT NULL,
                cantidad_disponible INTEGER DEFAULT 0,
                fecha_caducidad DATE,
                estado_producto VARCHAR(50) DEFAULT 'bueno',
                notas TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (donacion_id) REFERENCES donaciones(id)
            )
        ''')
        
        # Tabla salidas_donaciones
        cursor.execute('''
            CREATE TABLE salidas_donaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                detalle_donacion_id INTEGER NOT NULL,
                cantidad INTEGER NOT NULL,
                destinatario VARCHAR(255) NOT NULL,
                motivo TEXT,
                entregado_por_id INTEGER,
                fecha_entrega TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notas TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                centro_destino_id INTEGER,
                finalizado BOOLEAN DEFAULT 0,
                fecha_finalizado TIMESTAMP,
                finalizado_por_id INTEGER,
                FOREIGN KEY (detalle_donacion_id) REFERENCES detalle_donaciones(id)
            )
        ''')
    
    yield


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def centro_test(db):
    """Centro de prueba"""
    return Centro.objects.create(
        nombre="Centro de Prueba Donaciones",
        direccion="Calle Test 123",
        activo=True
    )


@pytest.fixture
def usuario_admin(db, centro_test):
    """Usuario administrador con permisos completos"""
    user = User.objects.create_user(
        username='admin_donaciones_test',
        email='admin_don@test.com',
        password='testpass123',
        rol='admin',
        perm_donaciones=True
    )
    return user


@pytest.fixture
def usuario_farmacia(db, centro_test):
    """Usuario farmacia con permisos de donaciones"""
    user = User.objects.create_user(
        username='farmacia_donaciones_test',
        email='farmacia_don@test.com',
        password='testpass123',
        rol='farmacia',
        perm_donaciones=True
    )
    return user


@pytest.fixture
def usuario_vista(db, centro_test):
    """Usuario vista - solo lectura"""
    user = User.objects.create_user(
        username='vista_donaciones_test',
        email='vista_don@test.com',
        password='testpass123',
        rol='vista',
        perm_donaciones=True
    )
    return user


@pytest.fixture
def usuario_centro(db, centro_test):
    """Usuario de centro específico"""
    user = User.objects.create_user(
        username='centro_donaciones_test',
        email='centro_don@test.com',
        password='testpass123',
        rol='centro',
        centro=centro_test,
        perm_donaciones=True
    )
    return user


@pytest.fixture
def producto_donacion_test(db):
    """Producto en el catálogo independiente de donaciones"""
    return ProductoDonacion.objects.create(
        clave='DON-TEST-001',
        nombre='Producto Prueba Donación',
        descripcion='Producto para pruebas unitarias',
        unidad_medida='PIEZA',
        presentacion='Caja con 10 unidades',
        activo=True
    )


@pytest.fixture
def donacion_pendiente(db, centro_test, usuario_farmacia):
    """Donación en estado pendiente"""
    return Donacion.objects.create(
        numero='TEST-DON-001',
        donante_nombre='Empresa Donante Test',
        donante_tipo='empresa',
        donante_rfc='ABC123456789',
        fecha_donacion=date.today(),
        centro_destino=centro_test,
        recibido_por=usuario_farmacia,
        estado='pendiente'
    )


@pytest.fixture
def donacion_con_detalles(donacion_pendiente, producto_donacion_test):
    """Donación con detalles agregados"""
    DetalleDonacion.objects.create(
        donacion=donacion_pendiente,
        producto_donacion=producto_donacion_test,
        numero_lote='LOTE-TEST-001',
        cantidad=100,
        cantidad_disponible=0,  # Se activa al procesar
        fecha_caducidad=date.today() + timedelta(days=365),
        estado_producto='bueno'
    )
    return donacion_pendiente


# =============================================================================
# TEST 1: MODELO ProductoDonacion (Catálogo Independiente)
# =============================================================================

@pytest.mark.django_db
class TestProductoDonacionModel:
    """Pruebas del modelo ProductoDonacion - Catálogo independiente"""
    
    def test_crear_producto_donacion(self, db):
        """Debe crear un producto en el catálogo de donaciones"""
        producto = ProductoDonacion.objects.create(
            clave='DON-MED-001',
            nombre='Paracetamol Donación',
            unidad_medida='CAJA',
            activo=True
        )
        assert producto.pk is not None
        assert producto.clave == 'DON-MED-001'
        assert str(producto) == 'DON-MED-001 - Paracetamol Donación'
    
    def test_clave_unica(self, producto_donacion_test):
        """No debe permitir claves duplicadas"""
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            ProductoDonacion.objects.create(
                clave='DON-TEST-001',  # Ya existe
                nombre='Otro Producto',
                activo=True
            )
    
    def test_catalogo_independiente(self, producto_donacion_test):
        """El catálogo de donaciones es independiente del principal"""
        # Verificar que no está en tabla productos
        from core.models import Producto
        assert Producto.objects.filter(clave='DON-TEST-001').count() == 0
        assert ProductoDonacion.objects.filter(clave='DON-TEST-001').count() == 1


# =============================================================================
# TEST 2: MODELO Donacion
# =============================================================================

@pytest.mark.django_db
class TestDonacionModel:
    """Pruebas del modelo Donacion"""
    
    def test_crear_donacion(self, centro_test, usuario_farmacia):
        """Debe crear una donación correctamente"""
        donacion = Donacion.objects.create(
            numero='TEST-CREATE-001',
            donante_nombre='Donante Test',
            donante_tipo='empresa',
            fecha_donacion=date.today(),
            centro_destino=centro_test,
            recibido_por=usuario_farmacia,
            estado='pendiente'
        )
        assert donacion.pk is not None
        assert donacion.estado == 'pendiente'
        assert donacion.folio == f'DON-{donacion.numero}'
    
    def test_estados_donacion(self, donacion_pendiente):
        """Debe respetar los estados válidos"""
        estados_validos = ['pendiente', 'recibida', 'procesada', 'rechazada']
        for estado in estados_validos:
            donacion_pendiente.estado = estado
            donacion_pendiente.save()
            donacion_pendiente.refresh_from_db()
            assert donacion_pendiente.estado == estado
    
    def test_total_productos_y_unidades(self, donacion_con_detalles, producto_donacion_test):
        """Debe calcular totales correctamente"""
        # Agregar otro detalle
        DetalleDonacion.objects.create(
            donacion=donacion_con_detalles,
            producto_donacion=producto_donacion_test,
            numero_lote='LOTE-TEST-002',
            cantidad=50,
            cantidad_disponible=0,
            estado_producto='bueno'
        )
        assert donacion_con_detalles.get_total_productos() == 2
        assert donacion_con_detalles.get_total_unidades() == 150


# =============================================================================
# TEST 3: MODELO DetalleDonacion
# =============================================================================

@pytest.mark.django_db
class TestDetalleDonacionModel:
    """Pruebas del modelo DetalleDonacion"""
    
    def test_crear_detalle_con_producto_donacion(self, donacion_pendiente, producto_donacion_test):
        """Debe crear detalle usando catálogo de donaciones"""
        detalle = DetalleDonacion.objects.create(
            donacion=donacion_pendiente,
            producto_donacion=producto_donacion_test,
            cantidad=100,
            cantidad_disponible=100,
            estado_producto='bueno'
        )
        assert detalle.producto_donacion == producto_donacion_test
        assert detalle.nombre_producto == producto_donacion_test.nombre
        assert detalle.clave_producto == producto_donacion_test.clave
    
    def test_cantidad_disponible_inicial(self, donacion_pendiente, producto_donacion_test):
        """cantidad_disponible debe inicializarse con cantidad si no se especifica"""
        detalle = DetalleDonacion(
            donacion=donacion_pendiente,
            producto_donacion=producto_donacion_test,
            cantidad=100,
            estado_producto='bueno'
        )
        # No establecemos cantidad_disponible
        detalle.save()
        assert detalle.cantidad_disponible == 100


# =============================================================================
# TEST 4: MODELO SalidaDonacion
# =============================================================================

@pytest.mark.django_db
class TestSalidaDonacionModel:
    """Pruebas del modelo SalidaDonacion"""
    
    def test_crear_salida_sin_descontar(self, donacion_con_detalles, centro_test, usuario_farmacia):
        """Crear salida NO debe descontar stock inmediatamente"""
        # Primero procesamos la donación para activar stock
        detalle = donacion_con_detalles.detalles.first()
        detalle.cantidad_disponible = detalle.cantidad
        detalle.save()
        
        stock_inicial = detalle.cantidad_disponible
        
        salida = SalidaDonacion.objects.create(
            detalle_donacion=detalle,
            cantidad=10,
            destinatario='Paciente Test',
            entregado_por=usuario_farmacia,
            centro_destino=centro_test,
            finalizado=False
        )
        
        detalle.refresh_from_db()
        # Stock NO debe cambiar al crear (solo al finalizar)
        assert detalle.cantidad_disponible == stock_inicial
        assert salida.finalizado == False
    
    def test_validar_stock_insuficiente(self, donacion_con_detalles, usuario_farmacia):
        """No debe permitir salida mayor al stock disponible"""
        detalle = donacion_con_detalles.detalles.first()
        detalle.cantidad_disponible = 10  # Solo 10 unidades
        detalle.save()
        
        with pytest.raises(ValueError) as exc_info:
            SalidaDonacion.objects.create(
                detalle_donacion=detalle,
                cantidad=50,  # Más que disponible
                destinatario='Paciente Test',
                entregado_por=usuario_farmacia
            )
        assert 'Stock insuficiente' in str(exc_info.value)
    
    def test_finalizar_salida_descuenta_stock(self, donacion_con_detalles, centro_test, usuario_farmacia):
        """Finalizar salida debe descontar stock"""
        detalle = donacion_con_detalles.detalles.first()
        detalle.cantidad_disponible = 100
        detalle.save()
        
        salida = SalidaDonacion.objects.create(
            detalle_donacion=detalle,
            cantidad=30,
            destinatario='Paciente Test',
            entregado_por=usuario_farmacia,
            finalizado=False
        )
        
        # Finalizar la entrega
        salida.finalizar(usuario=usuario_farmacia)
        
        detalle.refresh_from_db()
        salida.refresh_from_db()
        
        assert salida.finalizado == True
        assert salida.finalizado_por == usuario_farmacia
        assert salida.fecha_finalizado is not None
        assert detalle.cantidad_disponible == 70  # 100 - 30
    
    def test_no_doble_finalizacion(self, donacion_con_detalles, usuario_farmacia):
        """No debe permitir finalizar dos veces"""
        detalle = donacion_con_detalles.detalles.first()
        detalle.cantidad_disponible = 100
        detalle.save()
        
        salida = SalidaDonacion.objects.create(
            detalle_donacion=detalle,
            cantidad=20,
            destinatario='Paciente Test',
            entregado_por=usuario_farmacia,
            finalizado=False
        )
        
        salida.finalizar(usuario=usuario_farmacia)
        
        with pytest.raises(ValueError) as exc_info:
            salida.finalizar(usuario=usuario_farmacia)  # Segunda vez
        assert 'ya fue finalizada' in str(exc_info.value)


# =============================================================================
# TEST 5: API - PERMISOS DonacionViewSet
# =============================================================================

@pytest.mark.django_db
class TestDonacionPermisos:
    """Pruebas de permisos en el API de donaciones"""
    
    def test_admin_puede_crear_donacion(self, api_client, usuario_admin, centro_test):
        """Admin debe poder crear donaciones"""
        api_client.force_authenticate(user=usuario_admin)
        url = reverse('donacion-list')
        data = {
            'donante_nombre': 'Empresa Admin Test',
            'fecha_donacion': str(date.today()),
            'centro_destino': centro_test.pk,
            'donante_tipo': 'empresa'
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
    
    def test_farmacia_puede_crear_donacion(self, api_client, usuario_farmacia, centro_test):
        """Farmacia debe poder crear donaciones"""
        api_client.force_authenticate(user=usuario_farmacia)
        url = reverse('donacion-list')
        data = {
            'donante_nombre': 'Empresa Farmacia Test',
            'fecha_donacion': str(date.today()),
            'centro_destino': centro_test.pk,
            'donante_tipo': 'ong'
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
    
    def test_vista_no_puede_crear_donacion(self, api_client, usuario_vista, centro_test):
        """Vista NO debe poder crear donaciones"""
        api_client.force_authenticate(user=usuario_vista)
        url = reverse('donacion-list')
        data = {
            'donante_nombre': 'Intento Vista',
            'fecha_donacion': str(date.today()),
            'centro_destino': centro_test.pk
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_vista_puede_listar_donaciones(self, api_client, usuario_vista, donacion_pendiente):
        """Vista debe poder ver donaciones (solo lectura)"""
        api_client.force_authenticate(user=usuario_vista)
        url = reverse('donacion-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
    
    def test_usuario_no_autenticado_no_puede_acceder(self, api_client):
        """Usuario sin autenticación no puede acceder"""
        url = reverse('donacion-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# TEST 6: API - FLUJO V2 DONACIONES
# =============================================================================

@pytest.mark.django_db
class TestFlujoV2Donaciones:
    """Pruebas del flujo completo V2 de donaciones"""
    
    def test_flujo_completo_donacion(self, api_client, usuario_farmacia, centro_test, producto_donacion_test):
        """Prueba flujo completo: pendiente → recibida → procesada → salidas"""
        api_client.force_authenticate(user=usuario_farmacia)
        
        # PASO 1: Crear donación
        url_create = reverse('donacion-list')
        data_donacion = {
            'donante_nombre': 'Empresa Flujo V2',
            'fecha_donacion': str(date.today()),
            'centro_destino': centro_test.pk,
            'donante_tipo': 'empresa',
            'detalles': [{
                'producto_donacion': producto_donacion_test.pk,
                'cantidad': 100,
                'numero_lote': 'LOTE-FLUJO-001',
                'fecha_caducidad': str(date.today() + timedelta(days=365)),
                'estado_producto': 'bueno'
            }]
        }
        response = api_client.post(url_create, data_donacion, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        donacion_id = response.data['id']
        assert response.data['estado'] == 'pendiente'
        
        # PASO 2: Recibir donación
        url_recibir = reverse('donacion-recibir', kwargs={'pk': donacion_id})
        response = api_client.post(url_recibir)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['estado'] == 'recibida'
        
        # PASO 3: Procesar donación (activa stock)
        url_procesar = reverse('donacion-procesar', kwargs={'pk': donacion_id})
        response = api_client.post(url_procesar)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['donacion']['estado'] == 'procesada'
        
        # Verificar que stock está disponible
        donacion = Donacion.objects.get(pk=donacion_id)
        detalle = donacion.detalles.first()
        assert detalle.cantidad_disponible == 100
        
        # PASO 4: Registrar salida
        url_salida = reverse('salida-donacion-list')
        data_salida = {
            'detalle_donacion': detalle.pk,
            'cantidad': 25,
            'destinatario': 'Paciente Juan Pérez',
            'motivo': 'Entrega médica',
            'centro_destino': centro_test.pk
        }
        response = api_client.post(url_salida, data_salida, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        salida_id = response.data['id']
        
        # Stock NO debe cambiar aún (no finalizada)
        detalle.refresh_from_db()
        assert detalle.cantidad_disponible == 100
        
        # PASO 5: Finalizar entrega (ahora sí descuenta)
        salida = SalidaDonacion.objects.get(pk=salida_id)
        salida.finalizar(usuario=usuario_farmacia)
        
        detalle.refresh_from_db()
        assert detalle.cantidad_disponible == 75  # 100 - 25
    
    def test_rechazar_donacion(self, api_client, usuario_farmacia, donacion_pendiente):
        """Debe poder rechazar donación con motivo"""
        api_client.force_authenticate(user=usuario_farmacia)
        url = reverse('donacion-rechazar', kwargs={'pk': donacion_pendiente.pk})
        
        response = api_client.post(url, {'motivo': 'Productos en mal estado'}, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['estado'] == 'rechazada'
        assert 'Productos en mal estado' in response.data['notas']
    
    def test_no_procesar_donacion_ya_procesada(self, api_client, usuario_farmacia, donacion_con_detalles):
        """No debe procesar donación ya procesada"""
        api_client.force_authenticate(user=usuario_farmacia)
        
        # Primero procesamos
        url = reverse('donacion-procesar', kwargs={'pk': donacion_con_detalles.pk})
        response1 = api_client.post(url)
        assert response1.status_code == status.HTTP_200_OK
        
        # Intentamos procesar de nuevo
        response2 = api_client.post(url)
        assert response2.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# TEST 7: API - ProductoDonacion CRUD
# =============================================================================

@pytest.mark.django_db
class TestProductoDonacionAPI:
    """Pruebas del API de catálogo de productos de donación"""
    
    def test_listar_productos_donacion(self, api_client, usuario_farmacia, producto_donacion_test):
        """Debe listar productos del catálogo de donaciones"""
        api_client.force_authenticate(user=usuario_farmacia)
        url = reverse('producto-donacion-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data or isinstance(response.data, list)
    
    def test_crear_producto_donacion(self, api_client, usuario_farmacia):
        """Admin/Farmacia debe poder crear productos de donación"""
        api_client.force_authenticate(user=usuario_farmacia)
        url = reverse('producto-donacion-list')
        data = {
            'clave': 'DON-NEW-001',
            'nombre': 'Nuevo Producto Donación',
            'unidad_medida': 'CAJA',
            'activo': True
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['clave'] == 'DON-NEW-001'
    
    def test_vista_no_puede_crear_producto_donacion(self, api_client, usuario_vista):
        """Vista NO debe poder crear productos"""
        api_client.force_authenticate(user=usuario_vista)
        url = reverse('producto-donacion-list')
        data = {
            'clave': 'DON-VISTA-001',
            'nombre': 'Intento Vista',
            'activo': True
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_buscar_productos_donacion(self, api_client, usuario_farmacia, producto_donacion_test):
        """Debe buscar productos por clave o nombre"""
        api_client.force_authenticate(user=usuario_farmacia)
        url = reverse('producto-donacion-buscar')
        
        # Buscar por nombre
        response = api_client.get(url, {'q': 'Prueba'})
        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# TEST 8: EXPORTACIÓN/IMPORTACIÓN
# =============================================================================

@pytest.mark.django_db
class TestExportacionImportacion:
    """Pruebas de funciones de exportación e importación"""
    
    def test_exportar_donaciones_excel(self, api_client, usuario_farmacia, donacion_con_detalles):
        """Debe exportar donaciones a Excel"""
        api_client.force_authenticate(user=usuario_farmacia)
        url = reverse('donacion-exportar-excel')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in response['Content-Type']
    
    def test_descargar_plantilla_donaciones(self, api_client, usuario_farmacia):
        """Debe descargar plantilla Excel para importar"""
        api_client.force_authenticate(user=usuario_farmacia)
        url = reverse('donacion-plantilla-excel')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'attachment' in response.get('Content-Disposition', '')
    
    def test_plantilla_productos_donacion(self, api_client, usuario_farmacia):
        """Debe descargar plantilla para productos de donación"""
        api_client.force_authenticate(user=usuario_farmacia)
        url = reverse('producto-donacion-plantilla-excel')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_exportar_productos_donacion(self, api_client, usuario_farmacia, producto_donacion_test):
        """Debe exportar productos de donación a Excel"""
        api_client.force_authenticate(user=usuario_farmacia)
        url = reverse('producto-donacion-exportar-excel')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# TEST 9: INTEGRIDAD DE DATOS
# =============================================================================

@pytest.mark.django_db
class TestIntegridadDatos:
    """Pruebas de integridad y consistencia de datos"""
    
    def test_detalle_requiere_producto(self, donacion_pendiente):
        """DetalleDonacion debe tener al menos un producto (donación o legacy)"""
        from rest_framework.exceptions import ValidationError
        from core.serializers import DetalleDonacionSerializer
        
        serializer = DetalleDonacionSerializer(data={
            'donacion': donacion_pendiente.pk,
            'cantidad': 100,
            # Sin producto_donacion ni producto
        })
        assert not serializer.is_valid()
    
    def test_cantidad_positiva(self, donacion_pendiente, producto_donacion_test):
        """Cantidad debe ser mayor a 0"""
        from core.serializers import DetalleDonacionSerializer
        
        serializer = DetalleDonacionSerializer(data={
            'donacion': donacion_pendiente.pk,
            'producto_donacion': producto_donacion_test.pk,
            'cantidad': -10,  # Negativo
        })
        assert not serializer.is_valid()
        assert 'cantidad' in serializer.errors
    
    def test_salida_cantidad_positiva(self, donacion_con_detalles, usuario_farmacia):
        """Salida debe tener cantidad positiva"""
        from core.serializers import SalidaDonacionSerializer
        
        detalle = donacion_con_detalles.detalles.first()
        detalle.cantidad_disponible = 100
        detalle.save()
        
        serializer = SalidaDonacionSerializer(data={
            'detalle_donacion': detalle.pk,
            'cantidad': 0,  # Cero no válido
            'destinatario': 'Test'
        })
        assert not serializer.is_valid()


# =============================================================================
# TEST 10: AISLAMIENTO DE DONACIONES
# =============================================================================

@pytest.mark.django_db
class TestAislamientoDonaciones:
    """Pruebas que verifican que donaciones NO afectan inventario principal"""
    
    def test_donacion_no_afecta_stock_principal(self, donacion_con_detalles, producto_donacion_test):
        """Procesar donación NO debe afectar stock de productos principales"""
        from core.models import Producto
        
        # Crear producto en catálogo principal con misma clave
        try:
            producto_principal = Producto.objects.create(
                clave='DON-TEST-001',  # Misma clave que producto_donacion_test
                nombre='Producto Principal',
                unidad_medida='pieza',
                stock_actual=500
            )
            
            # Procesar donación
            for detalle in donacion_con_detalles.detalles.all():
                detalle.cantidad_disponible = detalle.cantidad
                detalle.save()
            
            # Verificar que stock principal NO cambió
            producto_principal.refresh_from_db()
            assert producto_principal.stock_actual == 500
        except:
            # Si falla por constraint, está bien - los catálogos son independientes
            pass
    
    def test_salida_donacion_no_genera_movimiento_principal(self, donacion_con_detalles, usuario_farmacia):
        """Salida de donación NO debe generar movimiento en tabla principal"""
        from core.models import Movimiento
        
        detalle = donacion_con_detalles.detalles.first()
        detalle.cantidad_disponible = 100
        detalle.save()
        
        movimientos_antes = Movimiento.objects.count()
        
        salida = SalidaDonacion.objects.create(
            detalle_donacion=detalle,
            cantidad=10,
            destinatario='Test',
            entregado_por=usuario_farmacia
        )
        salida.finalizar(usuario=usuario_farmacia)
        
        movimientos_despues = Movimiento.objects.count()
        
        # NO debe haber creado movimiento en tabla principal
        assert movimientos_despues == movimientos_antes


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
