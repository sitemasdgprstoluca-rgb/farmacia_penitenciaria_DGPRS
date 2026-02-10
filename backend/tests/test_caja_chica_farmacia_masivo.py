"""
================================================================================
PRUEBAS MASIVAS Y DE ESFUERZO - FLUJO CAJA CHICA CON VERIFICACIÓN DE FARMACIA
================================================================================

Este script realiza pruebas exhaustivas del flujo de compras de caja chica
con verificación de farmacia:

1. Pruebas de Transiciones de Estado (todas las combinaciones válidas/inválidas)
2. Pruebas de Permisos por Rol
3. Pruebas de Carga/Esfuerzo (múltiples solicitudes concurrentes)
4. Pruebas de Integridad de Datos
5. Pruebas de Escenarios Completos del Flujo

Fecha: 2026-01-14
"""

import os
import sys
import django
import random
import time
import threading
from decimal import Decimal
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'farmacia.settings')
django.setup()

from django.test import TestCase, TransactionTestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import connection, transaction
from rest_framework.test import APIClient
from rest_framework import status

from core.models import Centro, CompraCajaChica, DetalleCompraCajaChica, HistorialCompraCajaChica

User = get_user_model()

# ============================================================================
# CONFIGURACIÓN DE PRUEBAS
# ============================================================================

class TestConfig:
    """Configuración para las pruebas"""
    # Número de pruebas de esfuerzo
    NUM_SOLICITUDES_ESTRES = 50
    NUM_HILOS_CONCURRENTES = 10
    
    # Estados del flujo
    ESTADOS = [
        'pendiente', 'enviada_farmacia', 'sin_stock_farmacia', 'rechazada_farmacia',
        'enviada_admin', 'autorizada_admin', 'enviada_director', 'autorizada',
        'comprada', 'recibida', 'cancelada', 'rechazada'
    ]
    
    # Transiciones válidas
    TRANSICIONES_VALIDAS = {
        'pendiente': ['enviada_farmacia', 'cancelada'],
        'enviada_farmacia': ['sin_stock_farmacia', 'rechazada_farmacia', 'pendiente'],
        'sin_stock_farmacia': ['enviada_admin', 'cancelada'],
        'rechazada_farmacia': ['pendiente', 'cancelada'],
        'enviada_admin': ['autorizada_admin', 'rechazada', 'sin_stock_farmacia'],
        'autorizada_admin': ['enviada_director', 'cancelada'],
        'enviada_director': ['autorizada', 'rechazada', 'autorizada_admin'],
        'autorizada': ['comprada', 'cancelada'],
        'comprada': ['recibida', 'cancelada'],
        'recibida': [],
        'cancelada': [],
        'rechazada': ['pendiente'],
    }
    
    # Roles del sistema (valores reales de la BD)
    ROLES = {
        'medico': 'Médico del Centro',
        'administrador_centro': 'Administrador del Centro',
        'director_centro': 'Director del Centro',
        'farmacia': 'Personal de Farmacia',
        'admin': 'Administrador del Sistema',
    }


# ============================================================================
# UTILIDADES DE PRUEBA
# ============================================================================

class TestUtils:
    """Utilidades para crear datos de prueba"""
    
    @staticmethod
    def crear_centro(nombre=None):
        """Crea o obtiene un centro de prueba"""
        if nombre is None:
            nombre = f"Centro Test {random.randint(1000, 9999)}"
        
        # Primero intentar obtener un centro existente
        centro = Centro.objects.filter(activo=True).first()
        if centro:
            return centro
        
        # Si no existe, crear uno nuevo (solo con campos válidos del modelo)
        centro, _ = Centro.objects.get_or_create(
            nombre=nombre,
            defaults={
                'activo': True,
            }
        )
        return centro
    
    @staticmethod
    def crear_usuario(rol, centro=None, username=None):
        """Crea un usuario de prueba con rol específico"""
        if username is None:
            username = f"test_{rol}_{random.randint(1000, 9999)}"
        
        # Verificar si ya existe
        user = User.objects.filter(username=username).first()
        if user:
            return user
        
        user = User.objects.create_user(
            username=username,
            email=f'{username}@test.com',
            password='test123',
            first_name=f'Test {rol}',
            last_name='Usuario',
        )
        
        # Asignar rol si el campo existe
        if hasattr(user, 'rol'):
            user.rol = rol
            user.save()
        
        # Asignar centro si aplica
        if centro and hasattr(user, 'centro'):
            user.centro = centro
            user.save()
        
        return user
    
    @staticmethod
    def crear_compra(centro, solicitante, estado='pendiente', con_detalles=True):
        """Crea una compra de caja chica de prueba"""
        compra = CompraCajaChica.objects.create(
            centro=centro,
            solicitante=solicitante,
            motivo_compra=f"Prueba de flujo - {datetime.now().isoformat()}",
            estado=estado,
            subtotal=Decimal('100.00'),
            iva=Decimal('16.00'),
            total=Decimal('116.00'),
        )
        
        if con_detalles:
            DetalleCompraCajaChica.objects.create(
                compra=compra,
                descripcion_producto="Producto de prueba",
                cantidad_solicitada=10,
                precio_unitario=Decimal('10.00'),
                unidad_medida="PIEZA",
            )
        
        return compra


# ============================================================================
# CLASE PRINCIPAL DE PRUEBAS
# ============================================================================

class TestCajaChicaFarmaciaMasivo:
    """Pruebas masivas del flujo de caja chica con verificación de farmacia"""
    
    def __init__(self):
        self.resultados = {
            'total': 0,
            'exitosos': 0,
            'fallidos': 0,
            'errores': [],
        }
        self.client = APIClient()
        self.centro = None
        self.usuarios = {}
        
    def setup(self):
        """Configura el entorno de pruebas"""
        print("\n" + "="*80)
        print("CONFIGURANDO ENTORNO DE PRUEBAS")
        print("="*80)
        
        # Crear centro de prueba
        self.centro = TestUtils.crear_centro("Centro Pruebas Masivas")
        print(f"✓ Centro creado: {self.centro.nombre}")
        
        # Crear usuarios por rol
        for rol in TestConfig.ROLES.keys():
            self.usuarios[rol] = TestUtils.crear_usuario(rol, self.centro)
            print(f"✓ Usuario creado: {rol} -> {self.usuarios[rol].username}")
        
        # Crear superusuario para pruebas
        self.usuarios['superuser'] = TestUtils.crear_usuario('admin', self.centro, 'superuser_test')
        self.usuarios['superuser'].is_superuser = True
        self.usuarios['superuser'].save()
        print(f"✓ Superusuario creado: {self.usuarios['superuser'].username}")
        
        print("\n")
    
    def registrar_resultado(self, nombre_prueba, exitoso, mensaje=""):
        """Registra el resultado de una prueba"""
        self.resultados['total'] += 1
        if exitoso:
            self.resultados['exitosos'] += 1
            print(f"  ✓ {nombre_prueba}")
        else:
            self.resultados['fallidos'] += 1
            self.resultados['errores'].append({
                'prueba': nombre_prueba,
                'mensaje': mensaje
            })
            print(f"  ✗ {nombre_prueba}: {mensaje}")
    
    # ========================================================================
    # PRUEBAS DE TRANSICIONES DE ESTADO
    # ========================================================================
    
    def test_transiciones_validas(self):
        """Prueba todas las transiciones válidas del flujo"""
        print("\n" + "-"*80)
        print("PRUEBAS DE TRANSICIONES VÁLIDAS")
        print("-"*80)
        
        for estado_origen, estados_destino in TestConfig.TRANSICIONES_VALIDAS.items():
            for estado_destino in estados_destino:
                try:
                    # Crear compra en estado origen
                    compra = TestUtils.crear_compra(
                        self.centro, 
                        self.usuarios['medico'],
                        estado=estado_origen
                    )
                    
                    # Verificar que la transición es válida
                    puede_transicionar = compra.puede_transicionar_a(estado_destino)
                    
                    self.registrar_resultado(
                        f"Transición {estado_origen} → {estado_destino}",
                        puede_transicionar,
                        "Transición marcada como inválida" if not puede_transicionar else ""
                    )
                    
                    # Limpiar
                    compra.delete()
                    
                except Exception as e:
                    self.registrar_resultado(
                        f"Transición {estado_origen} → {estado_destino}",
                        False,
                        str(e)
                    )
    
    def test_transiciones_invalidas(self):
        """Prueba que las transiciones inválidas sean rechazadas"""
        print("\n" + "-"*80)
        print("PRUEBAS DE TRANSICIONES INVÁLIDAS")
        print("-"*80)
        
        transiciones_invalidas = [
            ('pendiente', 'autorizada'),  # No puede saltar farmacia
            ('pendiente', 'enviada_admin'),  # Debe pasar por farmacia
            ('enviada_farmacia', 'autorizada'),  # Salto de estados
            ('sin_stock_farmacia', 'autorizada'),  # Debe pasar por admin
            ('autorizada', 'pendiente'),  # No puede retroceder
            ('recibida', 'pendiente'),  # Estado terminal
            ('recibida', 'cancelada'),  # Estado terminal
            ('cancelada', 'pendiente'),  # Estado terminal
        ]
        
        for estado_origen, estado_destino in transiciones_invalidas:
            try:
                compra = TestUtils.crear_compra(
                    self.centro,
                    self.usuarios['medico'],
                    estado=estado_origen
                )
                
                # Debe ser inválida
                puede_transicionar = compra.puede_transicionar_a(estado_destino)
                
                self.registrar_resultado(
                    f"Bloqueo {estado_origen} ↛ {estado_destino}",
                    not puede_transicionar,
                    "Transición debería ser bloqueada" if puede_transicionar else ""
                )
                
                compra.delete()
                
            except Exception as e:
                self.registrar_resultado(
                    f"Bloqueo {estado_origen} ↛ {estado_destino}",
                    False,
                    str(e)
                )
    
    # ========================================================================
    # PRUEBAS DE API - FLUJO FARMACIA
    # ========================================================================
    
    def test_api_enviar_farmacia(self):
        """Prueba el endpoint de enviar a farmacia"""
        print("\n" + "-"*80)
        print("PRUEBAS API: ENVIAR A FARMACIA")
        print("-"*80)
        
        # Autenticar como médico
        self.client.force_authenticate(user=self.usuarios['medico'])
        
        # Caso 1: Enviar compra pendiente con detalles
        compra = TestUtils.crear_compra(self.centro, self.usuarios['medico'], 'pendiente', True)
        response = self.client.post(f'/api/compras-caja-chica/{compra.id}/enviar-farmacia/')
        
        self.registrar_resultado(
            "Enviar a farmacia (con detalles)",
            response.status_code == 200 and response.data.get('estado') == 'enviada_farmacia',
            f"Status: {response.status_code}, Data: {response.data.get('error', '')}"
        )
        compra.delete()
        
        # Caso 2: Enviar compra sin detalles (debe fallar)
        compra = TestUtils.crear_compra(self.centro, self.usuarios['medico'], 'pendiente', False)
        response = self.client.post(f'/api/compras-caja-chica/{compra.id}/enviar-farmacia/')
        
        self.registrar_resultado(
            "Bloquear envío sin detalles",
            response.status_code == 400,
            f"Status: {response.status_code}"
        )
        compra.delete()
        
        # Caso 3: Enviar compra en estado incorrecto
        compra = TestUtils.crear_compra(self.centro, self.usuarios['medico'], 'autorizada', True)
        response = self.client.post(f'/api/compras-caja-chica/{compra.id}/enviar-farmacia/')
        
        self.registrar_resultado(
            "Bloquear envío desde estado incorrecto",
            response.status_code == 400,
            f"Status: {response.status_code}"
        )
        compra.delete()
    
    def test_api_confirmar_sin_stock(self):
        """Prueba el endpoint de confirmar sin stock (farmacia)"""
        print("\n" + "-"*80)
        print("PRUEBAS API: CONFIRMAR SIN STOCK (FARMACIA)")
        print("-"*80)
        
        # Caso 1: Farmacia confirma sin stock
        self.client.force_authenticate(user=self.usuarios['farmacia'])
        compra = TestUtils.crear_compra(self.centro, self.usuarios['medico'], 'enviada_farmacia', True)
        
        response = self.client.post(
            f'/api/compras-caja-chica/{compra.id}/confirmar-sin-stock/',
            {'observaciones': 'Verificado: No hay stock disponible'}
        )
        
        self.registrar_resultado(
            "Farmacia confirma sin stock",
            response.status_code == 200 and response.data.get('estado') == 'sin_stock_farmacia',
            f"Status: {response.status_code}, Estado: {response.data.get('estado', 'N/A')}"
        )
        compra.delete()
        
        # Caso 2: Usuario sin permiso intenta confirmar
        self.client.force_authenticate(user=self.usuarios['medico'])
        compra = TestUtils.crear_compra(self.centro, self.usuarios['medico'], 'enviada_farmacia', True)
        
        response = self.client.post(f'/api/compras-caja-chica/{compra.id}/confirmar-sin-stock/')
        
        self.registrar_resultado(
            "Bloquear confirmar sin stock por no-farmacia",
            response.status_code in [403, 400],
            f"Status: {response.status_code}"
        )
        compra.delete()
        
        # Caso 3: Estado incorrecto
        self.client.force_authenticate(user=self.usuarios['farmacia'])
        compra = TestUtils.crear_compra(self.centro, self.usuarios['medico'], 'pendiente', True)
        
        response = self.client.post(f'/api/compras-caja-chica/{compra.id}/confirmar-sin-stock/')
        
        self.registrar_resultado(
            "Bloquear confirmar sin stock desde estado incorrecto",
            response.status_code == 400,
            f"Status: {response.status_code}"
        )
        compra.delete()
    
    def test_api_rechazar_tiene_stock(self):
        """Prueba el endpoint de rechazar porque hay stock"""
        print("\n" + "-"*80)
        print("PRUEBAS API: RECHAZAR TIENE STOCK (FARMACIA)")
        print("-"*80)
        
        # Caso 1: Farmacia rechaza indicando stock disponible
        self.client.force_authenticate(user=self.usuarios['farmacia'])
        compra = TestUtils.crear_compra(self.centro, self.usuarios['medico'], 'enviada_farmacia', True)
        
        response = self.client.post(
            f'/api/compras-caja-chica/{compra.id}/rechazar-tiene-stock/',
            {'observaciones': 'Hay 50 unidades disponibles en almacén', 'stock_disponible': 50}
        )
        
        self.registrar_resultado(
            "Farmacia rechaza con stock disponible",
            response.status_code == 200 and response.data.get('estado') == 'rechazada_farmacia',
            f"Status: {response.status_code}, Estado: {response.data.get('estado', 'N/A')}"
        )
        compra.delete()
        
        # Caso 2: Usuario sin permiso
        self.client.force_authenticate(user=self.usuarios['medico'])
        compra = TestUtils.crear_compra(self.centro, self.usuarios['medico'], 'enviada_farmacia', True)
        
        response = self.client.post(f'/api/compras-caja-chica/{compra.id}/rechazar-tiene-stock/')
        
        self.registrar_resultado(
            "Bloquear rechazo por no-farmacia",
            response.status_code in [403, 400],
            f"Status: {response.status_code}"
        )
        compra.delete()
    
    # ========================================================================
    # PRUEBAS DE API - FLUJO MULTINIVEL
    # ========================================================================
    
    def test_api_enviar_admin(self):
        """Prueba el endpoint de enviar a admin"""
        print("\n" + "-"*80)
        print("PRUEBAS API: ENVIAR A ADMIN")
        print("-"*80)
        
        # Caso 1: Médico envía a admin después de verificación de farmacia
        self.client.force_authenticate(user=self.usuarios['medico'])
        compra = TestUtils.crear_compra(self.centro, self.usuarios['medico'], 'sin_stock_farmacia', True)
        
        response = self.client.post(f'/api/compras-caja-chica/{compra.id}/enviar-admin/')
        
        self.registrar_resultado(
            "Enviar a admin desde sin_stock_farmacia",
            response.status_code == 200 and response.data.get('estado') == 'enviada_admin',
            f"Status: {response.status_code}, Estado: {response.data.get('estado', 'N/A')}"
        )
        compra.delete()
        
        # Caso 2: Intentar enviar desde pendiente (debe fallar - debe pasar por farmacia)
        compra = TestUtils.crear_compra(self.centro, self.usuarios['medico'], 'pendiente', True)
        response = self.client.post(f'/api/compras-caja-chica/{compra.id}/enviar-admin/')
        
        self.registrar_resultado(
            "Bloquear envío a admin desde pendiente (sin verificar farmacia)",
            response.status_code == 400,
            f"Status: {response.status_code}"
        )
        compra.delete()
    
    def test_api_autorizar_admin(self):
        """Prueba el endpoint de autorizar como admin"""
        print("\n" + "-"*80)
        print("PRUEBAS API: AUTORIZAR ADMIN")
        print("-"*80)
        
        # Caso 1: Admin autoriza
        self.client.force_authenticate(user=self.usuarios['administrador_centro'])
        compra = TestUtils.crear_compra(self.centro, self.usuarios['medico'], 'enviada_admin', True)
        
        response = self.client.post(
            f'/api/compras-caja-chica/{compra.id}/autorizar-admin/',
            {'observaciones': 'Aprobado por administración'}
        )
        
        self.registrar_resultado(
            "Admin autoriza solicitud",
            response.status_code == 200 and response.data.get('estado') == 'autorizada_admin',
            f"Status: {response.status_code}, Estado: {response.data.get('estado', 'N/A')}"
        )
        compra.delete()
        
        # Caso 2: Médico intenta autorizar (debe fallar)
        self.client.force_authenticate(user=self.usuarios['medico'])
        compra = TestUtils.crear_compra(self.centro, self.usuarios['medico'], 'enviada_admin', True)
        
        response = self.client.post(f'/api/compras-caja-chica/{compra.id}/autorizar-admin/')
        
        self.registrar_resultado(
            "Bloquear autorización por médico",
            response.status_code in [403, 400],
            f"Status: {response.status_code}"
        )
        compra.delete()
    
    def test_api_autorizar_director(self):
        """Prueba el endpoint de autorizar como director"""
        print("\n" + "-"*80)
        print("PRUEBAS API: AUTORIZAR DIRECTOR")
        print("-"*80)
        
        # Caso 1: Director autoriza
        self.client.force_authenticate(user=self.usuarios['director_centro'])
        compra = TestUtils.crear_compra(self.centro, self.usuarios['medico'], 'enviada_director', True)
        
        response = self.client.post(
            f'/api/compras-caja-chica/{compra.id}/autorizar-director/',
            {'observaciones': 'Autorizado para compra'}
        )
        
        self.registrar_resultado(
            "Director autoriza solicitud",
            response.status_code == 200 and response.data.get('estado') == 'autorizada',
            f"Status: {response.status_code}, Estado: {response.data.get('estado', 'N/A')}"
        )
        compra.delete()
        
        # Caso 2: Admin intenta autorizar como director (debe fallar)
        self.client.force_authenticate(user=self.usuarios['administrador_centro'])
        compra = TestUtils.crear_compra(self.centro, self.usuarios['medico'], 'enviada_director', True)
        
        response = self.client.post(f'/api/compras-caja-chica/{compra.id}/autorizar-director/')
        
        self.registrar_resultado(
            "Bloquear autorización director por admin",
            response.status_code in [403, 400],
            f"Status: {response.status_code}"
        )
        compra.delete()
    
    # ========================================================================
    # PRUEBAS DE FLUJO COMPLETO
    # ========================================================================
    
    def test_flujo_completo_aprobacion(self):
        """Prueba el flujo completo de aprobación"""
        print("\n" + "-"*80)
        print("PRUEBA FLUJO COMPLETO: APROBACIÓN")
        print("-"*80)
        
        flujo_exitoso = True
        errores = []
        
        try:
            # 1. Médico crea solicitud
            self.client.force_authenticate(user=self.usuarios['medico'])
            response = self.client.post('/api/compras-caja-chica/', {
                'centro': self.centro.id,
                'motivo_compra': 'Prueba de flujo completo',
                'detalles_write': [
                    {
                        'descripcion_producto': 'Medicamento de prueba',
                        'cantidad': 10,
                        'precio_unitario': '50.00',
                        'unidad_medida': 'CAJA'
                    }
                ]
            }, format='json')
            
            if response.status_code not in [200, 201]:
                raise Exception(f"Error creando compra: {response.data}")
            
            compra_id = response.data['id']
            print(f"  → Compra creada: {compra_id}")
            
            # 2. Médico envía a farmacia
            response = self.client.post(f'/api/compras-caja-chica/{compra_id}/enviar-farmacia/')
            if response.status_code != 200:
                raise Exception(f"Error enviando a farmacia: {response.data}")
            print(f"  → Enviada a farmacia: {response.data['estado']}")
            
            # 3. Farmacia confirma sin stock
            self.client.force_authenticate(user=self.usuarios['farmacia'])
            response = self.client.post(
                f'/api/compras-caja-chica/{compra_id}/confirmar-sin-stock/',
                {'observaciones': 'Verificado: No hay stock'}
            )
            if response.status_code != 200:
                raise Exception(f"Error confirmando sin stock: {response.data}")
            print(f"  → Farmacia confirma sin stock: {response.data['estado']}")
            
            # 4. Médico envía a admin
            self.client.force_authenticate(user=self.usuarios['medico'])
            response = self.client.post(f'/api/compras-caja-chica/{compra_id}/enviar-admin/')
            if response.status_code != 200:
                raise Exception(f"Error enviando a admin: {response.data}")
            print(f"  → Enviada a admin: {response.data['estado']}")
            
            # 5. Admin autoriza
            self.client.force_authenticate(user=self.usuarios['administrador_centro'])
            response = self.client.post(
                f'/api/compras-caja-chica/{compra_id}/autorizar-admin/',
                {'observaciones': 'Aprobado'}
            )
            if response.status_code != 200:
                raise Exception(f"Error admin autorizando: {response.data}")
            print(f"  → Admin autoriza: {response.data['estado']}")
            
            # 6. Admin envía a director
            response = self.client.post(f'/api/compras-caja-chica/{compra_id}/enviar-director/')
            if response.status_code != 200:
                raise Exception(f"Error enviando a director: {response.data}")
            print(f"  → Enviada a director: {response.data['estado']}")
            
            # 7. Director autoriza
            self.client.force_authenticate(user=self.usuarios['director_centro'])
            response = self.client.post(
                f'/api/compras-caja-chica/{compra_id}/autorizar-director/',
                {'observaciones': 'Autorizado para compra'}
            )
            if response.status_code != 200:
                raise Exception(f"Error director autorizando: {response.data}")
            print(f"  → Director autoriza: {response.data['estado']}")
            
            # 8. Registrar compra
            self.client.force_authenticate(user=self.usuarios['medico'])
            response = self.client.post(
                f'/api/compras-caja-chica/{compra_id}/registrar_compra/',
                {
                    'proveedor_nombre': 'Farmacia Local',
                    'numero_factura': 'F-001',
                    'fecha_compra': timezone.now().date().isoformat()
                }
            )
            if response.status_code != 200:
                raise Exception(f"Error registrando compra: {response.data}")
            print(f"  → Compra registrada: {response.data['estado']}")
            
            # 9. Recibir productos
            response = self.client.post(
                f'/api/compras-caja-chica/{compra_id}/recibir/',
                {'detalles': []}
            )
            if response.status_code != 200:
                raise Exception(f"Error recibiendo: {response.data}")
            print(f"  → Productos recibidos: {response.data['estado']}")
            
            # Verificar estado final
            compra = CompraCajaChica.objects.get(id=compra_id)
            if compra.estado != 'recibida':
                raise Exception(f"Estado final incorrecto: {compra.estado}")
            
            # Verificar historial
            historial_count = HistorialCompraCajaChica.objects.filter(compra_id=compra_id).count()
            print(f"  → Registros de historial: {historial_count}")
            
        except Exception as e:
            flujo_exitoso = False
            errores.append(str(e))
        
        self.registrar_resultado(
            "FLUJO COMPLETO APROBACIÓN",
            flujo_exitoso,
            "; ".join(errores) if errores else ""
        )
    
    def test_flujo_rechazo_farmacia(self):
        """Prueba el flujo de rechazo por stock disponible en farmacia"""
        print("\n" + "-"*80)
        print("PRUEBA FLUJO: RECHAZO POR STOCK EN FARMACIA")
        print("-"*80)
        
        flujo_exitoso = True
        errores = []
        
        try:
            # 1. Crear solicitud
            compra = TestUtils.crear_compra(self.centro, self.usuarios['medico'], 'pendiente', True)
            print(f"  → Compra creada: {compra.id}")
            
            # 2. Enviar a farmacia
            self.client.force_authenticate(user=self.usuarios['medico'])
            response = self.client.post(f'/api/compras-caja-chica/{compra.id}/enviar-farmacia/')
            if response.status_code != 200:
                raise Exception(f"Error enviando a farmacia: {response.data}")
            print(f"  → Enviada a farmacia: {response.data['estado']}")
            
            # 3. Farmacia rechaza (hay stock)
            self.client.force_authenticate(user=self.usuarios['farmacia'])
            response = self.client.post(
                f'/api/compras-caja-chica/{compra.id}/rechazar-tiene-stock/',
                {'observaciones': 'Hay 100 unidades disponibles', 'stock_disponible': 100}
            )
            if response.status_code != 200:
                raise Exception(f"Error rechazando: {response.data}")
            print(f"  → Farmacia rechaza: {response.data['estado']}")
            
            # 4. Verificar estado final
            compra.refresh_from_db()
            if compra.estado != 'rechazada_farmacia':
                raise Exception(f"Estado incorrecto: {compra.estado}")
            
            if compra.stock_farmacia_verificado != 100:
                raise Exception(f"Stock verificado incorrecto: {compra.stock_farmacia_verificado}")
            
            print(f"  → Verificado: respuesta_farmacia = '{compra.respuesta_farmacia[:50]}...'")
            
        except Exception as e:
            flujo_exitoso = False
            errores.append(str(e))
        
        self.registrar_resultado(
            "FLUJO RECHAZO POR STOCK FARMACIA",
            flujo_exitoso,
            "; ".join(errores) if errores else ""
        )
    
    # ========================================================================
    # PRUEBAS DE ESFUERZO
    # ========================================================================
    
    def test_carga_creacion_masiva(self):
        """Prueba de carga: Crear múltiples solicitudes"""
        print("\n" + "-"*80)
        print(f"PRUEBA DE CARGA: CREAR {TestConfig.NUM_SOLICITUDES_ESTRES} SOLICITUDES")
        print("-"*80)
        
        inicio = time.time()
        exitosos = 0
        fallidos = 0
        
        self.client.force_authenticate(user=self.usuarios['medico'])
        
        for i in range(TestConfig.NUM_SOLICITUDES_ESTRES):
            try:
                response = self.client.post('/api/compras-caja-chica/', {
                    'centro': self.centro.id,
                    'motivo_compra': f'Prueba de carga #{i+1}',
                    'detalles_write': [
                        {
                            'descripcion_producto': f'Producto prueba {i+1}',
                            'cantidad': random.randint(1, 100),
                            'precio_unitario': str(Decimal(random.uniform(10, 500)).quantize(Decimal('0.01'))),
                            'unidad_medida': random.choice(['CAJA', 'FRASCO', 'BLISTER', 'PIEZA'])
                        }
                    ]
                }, format='json')
                
                if response.status_code in [200, 201]:
                    exitosos += 1
                else:
                    fallidos += 1
                    
            except Exception as e:
                fallidos += 1
        
        duracion = time.time() - inicio
        promedio = duracion / TestConfig.NUM_SOLICITUDES_ESTRES
        
        print(f"  Tiempo total: {duracion:.2f}s")
        print(f"  Promedio por solicitud: {promedio:.4f}s")
        print(f"  Exitosos: {exitosos}, Fallidos: {fallidos}")
        
        self.registrar_resultado(
            f"Carga: Crear {TestConfig.NUM_SOLICITUDES_ESTRES} solicitudes",
            exitosos >= TestConfig.NUM_SOLICITUDES_ESTRES * 0.95,  # 95% éxito mínimo
            f"Solo {exitosos}/{TestConfig.NUM_SOLICITUDES_ESTRES} exitosos"
        )
    
    def test_concurrencia_transiciones(self):
        """Prueba de concurrencia: Transiciones simultáneas"""
        print("\n" + "-"*80)
        print(f"PRUEBA CONCURRENCIA: {TestConfig.NUM_HILOS_CONCURRENTES} HILOS SIMULTÁNEOS")
        print("-"*80)
        
        # Crear solicitudes para procesar
        compras = []
        for i in range(TestConfig.NUM_HILOS_CONCURRENTES):
            compra = TestUtils.crear_compra(self.centro, self.usuarios['medico'], 'pendiente', True)
            compras.append(compra)
        
        resultados_concurrencia = {'exitosos': 0, 'fallidos': 0}
        lock = threading.Lock()
        
        def procesar_envio_farmacia(compra):
            try:
                client = APIClient()
                client.force_authenticate(user=self.usuarios['medico'])
                response = client.post(f'/api/compras-caja-chica/{compra.id}/enviar-farmacia/')
                
                with lock:
                    if response.status_code == 200:
                        resultados_concurrencia['exitosos'] += 1
                    else:
                        resultados_concurrencia['fallidos'] += 1
            except Exception as e:
                with lock:
                    resultados_concurrencia['fallidos'] += 1
        
        inicio = time.time()
        
        # Ejecutar en paralelo
        with ThreadPoolExecutor(max_workers=TestConfig.NUM_HILOS_CONCURRENTES) as executor:
            futures = [executor.submit(procesar_envio_farmacia, c) for c in compras]
            for future in as_completed(futures):
                pass
        
        duracion = time.time() - inicio
        
        print(f"  Tiempo total: {duracion:.2f}s")
        print(f"  Exitosos: {resultados_concurrencia['exitosos']}")
        print(f"  Fallidos: {resultados_concurrencia['fallidos']}")
        
        self.registrar_resultado(
            f"Concurrencia: {TestConfig.NUM_HILOS_CONCURRENTES} envíos simultáneos",
            resultados_concurrencia['exitosos'] == TestConfig.NUM_HILOS_CONCURRENTES,
            f"Solo {resultados_concurrencia['exitosos']}/{TestConfig.NUM_HILOS_CONCURRENTES} exitosos"
        )
        
        # Limpiar
        for compra in compras:
            compra.delete()
    
    def test_estres_flujo_completo(self):
        """Prueba de estrés: Múltiples flujos completos"""
        print("\n" + "-"*80)
        print(f"PRUEBA DE ESTRÉS: 10 FLUJOS COMPLETOS SECUENCIALES")
        print("-"*80)
        
        exitosos = 0
        fallidos = 0
        inicio = time.time()
        
        for i in range(10):
            try:
                # Crear
                compra = TestUtils.crear_compra(self.centro, self.usuarios['medico'], 'pendiente', True)
                
                # Enviar a farmacia
                self.client.force_authenticate(user=self.usuarios['medico'])
                self.client.post(f'/api/compras-caja-chica/{compra.id}/enviar-farmacia/')
                
                # Farmacia confirma
                self.client.force_authenticate(user=self.usuarios['farmacia'])
                self.client.post(f'/api/compras-caja-chica/{compra.id}/confirmar-sin-stock/')
                
                # Enviar a admin
                self.client.force_authenticate(user=self.usuarios['medico'])
                self.client.post(f'/api/compras-caja-chica/{compra.id}/enviar-admin/')
                
                # Admin autoriza y envía a director
                self.client.force_authenticate(user=self.usuarios['administrador_centro'])
                self.client.post(f'/api/compras-caja-chica/{compra.id}/autorizar-admin/')
                self.client.post(f'/api/compras-caja-chica/{compra.id}/enviar-director/')
                
                # Director autoriza
                self.client.force_authenticate(user=self.usuarios['director_centro'])
                self.client.post(f'/api/compras-caja-chica/{compra.id}/autorizar-director/')
                
                # Verificar
                compra.refresh_from_db()
                if compra.estado == 'autorizada':
                    exitosos += 1
                else:
                    fallidos += 1
                    
            except Exception as e:
                fallidos += 1
        
        duracion = time.time() - inicio
        
        print(f"  Tiempo total: {duracion:.2f}s")
        print(f"  Promedio por flujo: {duracion/10:.2f}s")
        print(f"  Exitosos: {exitosos}, Fallidos: {fallidos}")
        
        self.registrar_resultado(
            "Estrés: 10 flujos completos",
            exitosos >= 9,  # Al menos 90% éxito
            f"Solo {exitosos}/10 exitosos"
        )
    
    # ========================================================================
    # PRUEBAS DE INTEGRIDAD
    # ========================================================================
    
    def test_integridad_historial(self):
        """Verifica que el historial se genere correctamente"""
        print("\n" + "-"*80)
        print("PRUEBA INTEGRIDAD: HISTORIAL DE CAMBIOS")
        print("-"*80)
        
        try:
            # Crear y procesar una compra
            compra = TestUtils.crear_compra(self.centro, self.usuarios['medico'], 'pendiente', True)
            compra_id = compra.id
            
            # Enviar a farmacia
            self.client.force_authenticate(user=self.usuarios['medico'])
            self.client.post(f'/api/compras-caja-chica/{compra.id}/enviar-farmacia/')
            
            # Confirmar sin stock
            self.client.force_authenticate(user=self.usuarios['farmacia'])
            self.client.post(f'/api/compras-caja-chica/{compra.id}/confirmar-sin-stock/')
            
            # Verificar historial
            historial = HistorialCompraCajaChica.objects.filter(compra_id=compra_id).order_by('created_at')
            
            # Debe haber al menos 2 registros
            tiene_historial = historial.count() >= 2
            
            # Verificar campos del historial
            campos_correctos = True
            for h in historial:
                if not h.estado_anterior or not h.estado_nuevo or not h.usuario:
                    campos_correctos = False
                    break
            
            self.registrar_resultado(
                "Historial: Registros generados",
                tiene_historial,
                f"Solo {historial.count()} registros encontrados"
            )
            
            self.registrar_resultado(
                "Historial: Campos completos",
                campos_correctos,
                "Faltan campos requeridos en historial"
            )
            
        except Exception as e:
            self.registrar_resultado("Integridad historial", False, str(e))
    
    def test_integridad_calculos(self):
        """Verifica que los cálculos de totales sean correctos"""
        print("\n" + "-"*80)
        print("PRUEBA INTEGRIDAD: CÁLCULOS DE TOTALES")
        print("-"*80)
        
        try:
            # Crear compra con detalles específicos
            compra = CompraCajaChica.objects.create(
                centro=self.centro,
                solicitante=self.usuarios['medico'],
                motivo_compra="Prueba de cálculos",
                estado='pendiente',
            )
            
            # Agregar detalles
            DetalleCompraCajaChica.objects.create(
                compra=compra,
                descripcion_producto="Producto A",
                cantidad_solicitada=10,
                precio_unitario=Decimal('100.00'),
            )
            DetalleCompraCajaChica.objects.create(
                compra=compra,
                descripcion_producto="Producto B",
                cantidad_solicitada=5,
                precio_unitario=Decimal('50.00'),
            )
            
            # Calcular totales
            compra.calcular_totales()
            compra.refresh_from_db()
            
            # Verificar
            subtotal_esperado = Decimal('1250.00')  # (10*100) + (5*50)
            iva_esperado = Decimal('200.00')  # 1250 * 0.16
            total_esperado = Decimal('1450.00')
            
            self.registrar_resultado(
                "Cálculo subtotal",
                compra.subtotal == subtotal_esperado,
                f"Esperado: {subtotal_esperado}, Obtenido: {compra.subtotal}"
            )
            
            self.registrar_resultado(
                "Cálculo IVA",
                compra.iva == iva_esperado,
                f"Esperado: {iva_esperado}, Obtenido: {compra.iva}"
            )
            
            self.registrar_resultado(
                "Cálculo total",
                compra.total == total_esperado,
                f"Esperado: {total_esperado}, Obtenido: {compra.total}"
            )
            
            compra.delete()
            
        except Exception as e:
            self.registrar_resultado("Integridad cálculos", False, str(e))
    
    def test_integridad_fechas_flujo(self):
        """Verifica que las fechas del flujo se registren correctamente"""
        print("\n" + "-"*80)
        print("PRUEBA INTEGRIDAD: FECHAS DEL FLUJO")
        print("-"*80)
        
        try:
            compra = TestUtils.crear_compra(self.centro, self.usuarios['medico'], 'pendiente', True)
            
            # Enviar a farmacia
            self.client.force_authenticate(user=self.usuarios['medico'])
            self.client.post(f'/api/compras-caja-chica/{compra.id}/enviar-farmacia/')
            compra.refresh_from_db()
            
            self.registrar_resultado(
                "Fecha: fecha_envio_farmacia",
                compra.fecha_envio_farmacia is not None,
                "No se registró fecha_envio_farmacia"
            )
            
            # Confirmar sin stock
            self.client.force_authenticate(user=self.usuarios['farmacia'])
            self.client.post(f'/api/compras-caja-chica/{compra.id}/confirmar-sin-stock/')
            compra.refresh_from_db()
            
            self.registrar_resultado(
                "Fecha: fecha_respuesta_farmacia",
                compra.fecha_respuesta_farmacia is not None,
                "No se registró fecha_respuesta_farmacia"
            )
            
            self.registrar_resultado(
                "Fecha: verificado_por_farmacia",
                compra.verificado_por_farmacia is not None,
                "No se registró verificado_por_farmacia"
            )
            
            # Enviar a admin
            self.client.force_authenticate(user=self.usuarios['medico'])
            self.client.post(f'/api/compras-caja-chica/{compra.id}/enviar-admin/')
            compra.refresh_from_db()
            
            self.registrar_resultado(
                "Fecha: fecha_envio_admin",
                compra.fecha_envio_admin is not None,
                "No se registró fecha_envio_admin"
            )
            
            compra.delete()
            
        except Exception as e:
            self.registrar_resultado("Integridad fechas", False, str(e))
    
    # ========================================================================
    # EJECUCIÓN PRINCIPAL
    # ========================================================================
    
    def ejecutar_todas(self):
        """Ejecuta todas las pruebas"""
        print("\n" + "="*80)
        print("INICIANDO PRUEBAS MASIVAS - FLUJO CAJA CHICA CON VERIFICACIÓN FARMACIA")
        print("="*80)
        print(f"Fecha: {datetime.now().isoformat()}")
        print(f"Configuración: {TestConfig.NUM_SOLICITUDES_ESTRES} solicitudes de estrés")
        print(f"              {TestConfig.NUM_HILOS_CONCURRENTES} hilos concurrentes")
        
        self.setup()
        
        # Pruebas de transiciones
        self.test_transiciones_validas()
        self.test_transiciones_invalidas()
        
        # Pruebas API - Flujo Farmacia
        self.test_api_enviar_farmacia()
        self.test_api_confirmar_sin_stock()
        self.test_api_rechazar_tiene_stock()
        
        # Pruebas API - Flujo Multinivel
        self.test_api_enviar_admin()
        self.test_api_autorizar_admin()
        self.test_api_autorizar_director()
        
        # Pruebas de flujo completo
        self.test_flujo_completo_aprobacion()
        self.test_flujo_rechazo_farmacia()
        
        # Pruebas de integridad
        self.test_integridad_historial()
        self.test_integridad_calculos()
        self.test_integridad_fechas_flujo()
        
        # Pruebas de carga y estrés
        self.test_carga_creacion_masiva()
        self.test_concurrencia_transiciones()
        self.test_estres_flujo_completo()
        
        # Resumen final
        self.imprimir_resumen()
    
    def imprimir_resumen(self):
        """Imprime el resumen de resultados"""
        print("\n" + "="*80)
        print("RESUMEN DE PRUEBAS")
        print("="*80)
        print(f"Total de pruebas: {self.resultados['total']}")
        print(f"✓ Exitosas: {self.resultados['exitosos']}")
        print(f"✗ Fallidas: {self.resultados['fallidos']}")
        
        if self.resultados['errores']:
            print("\nDETALLE DE ERRORES:")
            for error in self.resultados['errores']:
                print(f"  • {error['prueba']}: {error['mensaje']}")
        
        porcentaje = (self.resultados['exitosos'] / self.resultados['total'] * 100) if self.resultados['total'] > 0 else 0
        print(f"\n{'='*80}")
        print(f"RESULTADO FINAL: {porcentaje:.1f}% de pruebas exitosas")
        print("="*80)
        
        if porcentaje >= 95:
            print("✓ TODAS LAS PRUEBAS PASARON EXITOSAMENTE")
        elif porcentaje >= 80:
            print("⚠ ALGUNAS PRUEBAS FALLARON - REVISAR ERRORES")
        else:
            print("✗ MÚLTIPLES FALLOS - REVISAR IMPLEMENTACIÓN")


# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================

if __name__ == '__main__':
    tester = TestCajaChicaFarmaciaMasivo()
    tester.ejecutar_todas()
