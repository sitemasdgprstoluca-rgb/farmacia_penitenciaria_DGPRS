"""
Tests para el módulo de Salidas de Donaciones (Entregas).

Este módulo prueba:
1. Creación de entregas con reserva de stock
2. Validación de stock disponible
3. Eliminación de entregas no finalizadas (devuelve stock)
4. Finalización de entregas
5. No se puede eliminar entregas finalizadas
6. Exportación/Importación Excel

IMPORTANTE: Las salidas de donaciones son INTERNAS y no generan movimientos
en la tabla principal de movimientos del inventario.
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date
from decimal import Decimal
import io

User = get_user_model()


def centro_table_has_email_column():
    """Verifica si la tabla centros tiene la columna email (Supabase)."""
    from django.db import connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA table_info(centros)")
            columns = {col[1] for col in cursor.fetchall()}
            return 'email' in columns
    except Exception:
        return False


def get_or_create_centro(nombre):
    """Helper para crear/obtener centro de forma compatible."""
    from core.models import Centro
    try:
        return Centro.objects.get(nombre=nombre)
    except Centro.DoesNotExist:
        try:
            return Centro.objects.create(nombre=nombre)
        except Exception:
            return Centro.objects.first()


def crear_usuario_farmacia(username):
    """Crea un usuario con permisos de farmacia (superuser para simplificar)."""
    user = User.objects.create_user(
        username=username,
        password='test123',
        is_staff=True,
        is_superuser=True  # Superuser tiene todos los permisos
    )
    return user


class TestCrearSalidaDonacion(TestCase):
    """Pruebas de creación de salidas/entregas."""
    
    def setUp(self):
        self.user = crear_usuario_farmacia('salidas_admin')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Crear producto de donación
        from core.models import ProductoDonacion
        self.producto = ProductoDonacion.objects.create(
            clave='SAL-001',
            nombre='Producto para Salida',
            unidad_medida='CAJA'
        )
        
        # Crear donación procesada
        from core.models import Donacion
        self.donacion = Donacion.objects.create(
            numero='DON-SAL-001',
            donante_nombre='Donante Test',
            fecha_donacion=date.today(),
            estado='procesada'
        )
        
        # Crear detalle con stock
        from core.models import DetalleDonacion
        self.detalle = DetalleDonacion.objects.create(
            donacion=self.donacion,
            producto_donacion=self.producto,
            cantidad=100,
            cantidad_disponible=100
        )
    
    def test_crear_salida_reserva_stock(self):
        """Al crear salida, el stock se descuenta inmediatamente."""
        data = {
            'detalle_donacion': self.detalle.id,
            'cantidad': 20,
            'destinatario': 'Paciente Test'
        }
        
        response = self.client.post('/api/salidas-donaciones/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verificar que stock se descontó
        self.detalle.refresh_from_db()
        self.assertEqual(self.detalle.cantidad_disponible, 80)
    
    def test_validar_stock_insuficiente(self):
        """No permite crear salida si el stock es insuficiente."""
        data = {
            'detalle_donacion': self.detalle.id,
            'cantidad': 150,  # Más del disponible (100)
            'destinatario': 'Paciente Test'
        }
        
        response = self.client.post('/api/salidas-donaciones/', data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Stock insuficiente', str(response.data))
    
    def test_crear_salida_estado_pendiente(self):
        """Una salida nueva tiene estado pendiente por defecto."""
        data = {
            'detalle_donacion': self.detalle.id,
            'cantidad': 10,
            'destinatario': 'Paciente Pendiente'
        }
        
        response = self.client.post('/api/salidas-donaciones/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data['finalizado'])
        self.assertEqual(response.data['estado_entrega'], 'pendiente')
    
    def test_crear_salida_asigna_usuario(self):
        """La salida se asigna al usuario autenticado."""
        data = {
            'detalle_donacion': self.detalle.id,
            'cantidad': 5,
            'destinatario': 'Paciente Asignado'
        }
        
        response = self.client.post('/api/salidas-donaciones/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['entregado_por'], self.user.id)


class TestEliminarSalidaDonacion(TestCase):
    """Pruebas de eliminación de salidas."""
    
    def setUp(self):
        self.user = crear_usuario_farmacia('eliminar_admin')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        from core.models import ProductoDonacion, Donacion, DetalleDonacion
        
        self.producto = ProductoDonacion.objects.create(
            clave='ELIM-001',
            nombre='Producto para Eliminar'
        )
        
        self.donacion = Donacion.objects.create(
            numero='DON-ELIM-001',
            donante_nombre='Donante Eliminar',
            fecha_donacion=date.today(),
            estado='procesada'
        )
        
        self.detalle = DetalleDonacion.objects.create(
            donacion=self.donacion,
            producto_donacion=self.producto,
            cantidad=50,
            cantidad_disponible=50
        )
    
    def test_eliminar_pendiente_devuelve_stock(self):
        """Eliminar salida pendiente devuelve el stock."""
        # Crear salida
        data = {
            'detalle_donacion': self.detalle.id,
            'cantidad': 15,
            'destinatario': 'Paciente a Eliminar'
        }
        response = self.client.post('/api/salidas-donaciones/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        salida_id = response.data['id']
        
        # Verificar que stock se descontó
        self.detalle.refresh_from_db()
        self.assertEqual(self.detalle.cantidad_disponible, 35)
        
        # Eliminar salida
        response = self.client.delete(f'/api/salidas-donaciones/{salida_id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verificar que stock se devolvió
        self.detalle.refresh_from_db()
        self.assertEqual(self.detalle.cantidad_disponible, 50)
    
    def test_no_eliminar_salida_finalizada(self):
        """No se puede eliminar una salida ya finalizada."""
        from core.models import SalidaDonacion
        
        # Crear salida
        data = {
            'detalle_donacion': self.detalle.id,
            'cantidad': 10,
            'destinatario': 'Paciente Finalizado'
        }
        response = self.client.post('/api/salidas-donaciones/', data)
        salida_id = response.data['id']
        
        # Finalizar la salida
        response = self.client.post(f'/api/salidas-donaciones/{salida_id}/finalizar/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Intentar eliminar
        response = self.client.delete(f'/api/salidas-donaciones/{salida_id}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('finalizada', str(response.data['error']).lower())


class TestFinalizarSalidaDonacion(TestCase):
    """Pruebas del proceso de finalización."""
    
    def setUp(self):
        self.user = crear_usuario_farmacia('finalizar_admin')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        from core.models import ProductoDonacion, Donacion, DetalleDonacion
        
        self.producto = ProductoDonacion.objects.create(
            clave='FIN-001',
            nombre='Producto para Finalizar'
        )
        
        self.donacion = Donacion.objects.create(
            numero='DON-FIN-001',
            donante_nombre='Donante Finalizar',
            fecha_donacion=date.today(),
            estado='procesada'
        )
        
        self.detalle = DetalleDonacion.objects.create(
            donacion=self.donacion,
            producto_donacion=self.producto,
            cantidad=30,
            cantidad_disponible=30
        )
    
    def test_finalizar_salida_cambia_estado(self):
        """Finalizar cambia estado a entregado."""
        # Crear salida
        data = {
            'detalle_donacion': self.detalle.id,
            'cantidad': 5,
            'destinatario': 'Paciente para Finalizar'
        }
        response = self.client.post('/api/salidas-donaciones/', data)
        salida_id = response.data['id']
        
        # Finalizar
        response = self.client.post(f'/api/salidas-donaciones/{salida_id}/finalizar/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['salida']['finalizado'])
        self.assertEqual(response.data['salida']['estado_entrega'], 'entregado')
        self.assertIsNotNone(response.data['salida']['fecha_finalizado'])
    
    def test_finalizar_no_cambia_stock(self):
        """Finalizar no vuelve a descontar stock (ya se descontó al crear)."""
        # Crear salida
        data = {
            'detalle_donacion': self.detalle.id,
            'cantidad': 10,
            'destinatario': 'Paciente Stock Test'
        }
        response = self.client.post('/api/salidas-donaciones/', data)
        salida_id = response.data['id']
        
        # Verificar stock después de crear
        self.detalle.refresh_from_db()
        stock_despues_crear = self.detalle.cantidad_disponible
        self.assertEqual(stock_despues_crear, 20)  # 30 - 10
        
        # Finalizar
        self.client.post(f'/api/salidas-donaciones/{salida_id}/finalizar/')
        
        # Verificar stock después de finalizar (no debe cambiar)
        self.detalle.refresh_from_db()
        self.assertEqual(self.detalle.cantidad_disponible, stock_despues_crear)
    
    def test_no_finalizar_dos_veces(self):
        """No se puede finalizar una salida ya finalizada."""
        # Crear y finalizar
        data = {
            'detalle_donacion': self.detalle.id,
            'cantidad': 5,
            'destinatario': 'Doble Finalizar'
        }
        response = self.client.post('/api/salidas-donaciones/', data)
        salida_id = response.data['id']
        self.client.post(f'/api/salidas-donaciones/{salida_id}/finalizar/')
        
        # Intentar finalizar de nuevo
        response = self.client.post(f'/api/salidas-donaciones/{salida_id}/finalizar/')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('ya fue finalizada', str(response.data['error']).lower())


class TestListarFiltrarSalidas(TestCase):
    """Pruebas de listado y filtros."""
    
    def setUp(self):
        self.user = crear_usuario_farmacia('listar_admin')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        from core.models import ProductoDonacion, Donacion, DetalleDonacion
        
        self.producto = ProductoDonacion.objects.create(
            clave='LIST-001',
            nombre='Producto Listar'
        )
        
        self.donacion = Donacion.objects.create(
            numero='DON-LIST-001',
            donante_nombre='Donante Listar',
            fecha_donacion=date.today(),
            estado='procesada'
        )
        
        self.detalle = DetalleDonacion.objects.create(
            donacion=self.donacion,
            producto_donacion=self.producto,
            cantidad=100,
            cantidad_disponible=100
        )
    
    def test_listar_salidas(self):
        """Puede listar todas las salidas."""
        # Crear algunas salidas
        for i in range(3):
            self.client.post('/api/salidas-donaciones/', {
                'detalle_donacion': self.detalle.id,
                'cantidad': 5,
                'destinatario': f'Paciente {i}'
            })
        
        response = self.client.get('/api/salidas-donaciones/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['count'], 3)
    
    def test_filtrar_por_estado_finalizado(self):
        """Filtra por estado finalizado/pendiente."""
        # Crear salida y finalizarla
        response = self.client.post('/api/salidas-donaciones/', {
            'detalle_donacion': self.detalle.id,
            'cantidad': 5,
            'destinatario': 'Paciente Filtro'
        })
        salida_id = response.data['id']
        self.client.post(f'/api/salidas-donaciones/{salida_id}/finalizar/')
        
        # Filtrar solo finalizados
        response = self.client.get('/api/salidas-donaciones/?finalizado=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verificar que todas las salidas mostradas están finalizadas
        for salida in response.data.get('results', []):
            self.assertTrue(salida['finalizado'])


class TestExportarPlantillaSalidas(TestCase):
    """Pruebas de exportación e importación Excel."""
    
    def setUp(self):
        self.user = crear_usuario_farmacia('export_admin')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
    
    def test_descargar_plantilla_excel(self):
        """Puede descargar plantilla Excel."""
        response = self.client.get('/api/salidas-donaciones/plantilla-excel/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('application/vnd.openxmlformats', response['Content-Type'])
        self.assertIn('attachment', response['Content-Disposition'])
    
    def test_exportar_entregas_excel(self):
        """Puede exportar entregas a Excel."""
        from core.models import ProductoDonacion, Donacion, DetalleDonacion
        
        # Crear datos
        producto = ProductoDonacion.objects.create(
            clave='EXP-001',
            nombre='Producto Exportar'
        )
        donacion = Donacion.objects.create(
            numero='DON-EXP-001',
            donante_nombre='Donante Export',
            fecha_donacion=date.today(),
            estado='procesada'
        )
        detalle = DetalleDonacion.objects.create(
            donacion=donacion,
            producto_donacion=producto,
            cantidad=50,
            cantidad_disponible=50
        )
        
        # Crear una salida
        self.client.post('/api/salidas-donaciones/', {
            'detalle_donacion': detalle.id,
            'cantidad': 10,
            'destinatario': 'Paciente Exportar'
        })
        
        response = self.client.get('/api/salidas-donaciones/exportar-excel/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('application/vnd.openxmlformats', response['Content-Type'])


class TestNoGeneraMovimientos(TestCase):
    """
    Verifica que las salidas de donaciones NO afectan la tabla de movimientos principal.
    Esto es crucial para mantener el módulo de donaciones aislado.
    """
    
    def setUp(self):
        self.user = crear_usuario_farmacia('aislamiento_admin')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        from core.models import ProductoDonacion, Donacion, DetalleDonacion
        
        self.producto = ProductoDonacion.objects.create(
            clave='AISLA-001',
            nombre='Producto Aislamiento'
        )
        
        self.donacion = Donacion.objects.create(
            numero='DON-AISLA-001',
            donante_nombre='Donante Aislamiento',
            fecha_donacion=date.today(),
            estado='procesada'
        )
        
        self.detalle = DetalleDonacion.objects.create(
            donacion=self.donacion,
            producto_donacion=self.producto,
            cantidad=100,
            cantidad_disponible=100
        )
    
    def test_crear_salida_no_genera_movimiento(self):
        """Crear salida de donación NO crea movimiento."""
        from core.models import Movimiento
        
        # Contar movimientos antes
        movs_antes = Movimiento.objects.count()
        
        # Crear salida
        self.client.post('/api/salidas-donaciones/', {
            'detalle_donacion': self.detalle.id,
            'cantidad': 10,
            'destinatario': 'Paciente Movimiento'
        })
        
        # Verificar que NO se crearon movimientos
        movs_despues = Movimiento.objects.count()
        self.assertEqual(movs_antes, movs_despues)
    
    def test_finalizar_salida_no_genera_movimiento(self):
        """Finalizar salida de donación NO crea movimiento."""
        from core.models import Movimiento
        
        # Crear salida
        response = self.client.post('/api/salidas-donaciones/', {
            'detalle_donacion': self.detalle.id,
            'cantidad': 15,
            'destinatario': 'Paciente Final Mov'
        })
        salida_id = response.data['id']
        
        # Contar movimientos antes de finalizar
        movs_antes = Movimiento.objects.count()
        
        # Finalizar
        self.client.post(f'/api/salidas-donaciones/{salida_id}/finalizar/')
        
        # Verificar que NO se crearon movimientos
        movs_despues = Movimiento.objects.count()
        self.assertEqual(movs_antes, movs_despues)


class TestPermisosAccesoSalidas(TestCase):
    """Pruebas de permisos de acceso."""
    
    def setUp(self):
        # Usuario farmacia (superuser)
        self.farmacia_user = crear_usuario_farmacia('farmacia_salidas')
        
        # Usuario solo lectura (no superuser, no staff)
        self.reader_user = User.objects.create_user(
            username='reader_salidas',
            password='test123',
            is_staff=False,
            is_superuser=False
        )
        
        self.client = APIClient()
        
        from core.models import ProductoDonacion, Donacion, DetalleDonacion
        
        self.producto = ProductoDonacion.objects.create(
            clave='PERM-001',
            nombre='Producto Permisos'
        )
        
        self.donacion = Donacion.objects.create(
            numero='DON-PERM-001',
            donante_nombre='Donante Permisos',
            fecha_donacion=date.today(),
            estado='procesada'
        )
        
        self.detalle = DetalleDonacion.objects.create(
            donacion=self.donacion,
            producto_donacion=self.producto,
            cantidad=50,
            cantidad_disponible=50
        )
    
    def test_usuario_autenticado_puede_listar(self):
        """Cualquier usuario autenticado puede listar salidas."""
        self.client.force_authenticate(user=self.reader_user)
        
        response = self.client.get('/api/salidas-donaciones/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_solo_farmacia_puede_crear(self):
        """Solo usuarios de farmacia pueden crear salidas."""
        # Usuario sin permisos
        self.client.force_authenticate(user=self.reader_user)
        
        response = self.client.post('/api/salidas-donaciones/', {
            'detalle_donacion': self.detalle.id,
            'cantidad': 5,
            'destinatario': 'Test'
        })
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Usuario farmacia
        self.client.force_authenticate(user=self.farmacia_user)
        
        response = self.client.post('/api/salidas-donaciones/', {
            'detalle_donacion': self.detalle.id,
            'cantidad': 5,
            'destinatario': 'Test'
        })
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
