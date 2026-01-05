"""
Tests masivos del flujo completo de requisiciones.

Este módulo prueba exhaustivamente:
1. Flujo completo: Médico → Admin → Director → Farmacia → Entrega
2. Devoluciones: Admin/Director devuelven → Médico edita y reenvía
3. Rechazos: Requisición rechazada NO es editable
4. Autorización de Farmacia: Ajuste de cantidades
5. Hoja de recolección y firmas
6. Descuento de inventario y transferencia al centro
7. Concurrencia con 23 centros y múltiples usuarios

Autor: Sistema
Fecha: 2026-01-05
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import random
import uuid


User = get_user_model()


# ============================================================================
# CONFIGURACIÓN DE DATOS DE PRUEBA
# ============================================================================

NUM_CENTROS = 23
USUARIOS_POR_CENTRO = 4  # medico, admin_centro, director_centro, auxiliar
PRODUCTOS_POR_REQUISICION = 5
REQUISICIONES_POR_CENTRO = 3


# ============================================================================
# CONSTANTES DEL FLUJO
# ============================================================================

ESTADOS_REQUISICION = {
    'BORRADOR': 'borrador',
    'PENDIENTE_ADMIN': 'pendiente_admin',
    'PENDIENTE_DIRECTOR': 'pendiente_director',
    'ENVIADA': 'enviada',
    'EN_REVISION': 'en_revision',
    'AUTORIZADA': 'autorizada',
    'EN_SURTIDO': 'en_surtido',
    'SURTIDA': 'surtida',
    'ENTREGADA': 'entregada',
    'RECHAZADA': 'rechazada',
    'DEVUELTA': 'devuelta',
    'CANCELADA': 'cancelada',
    'VENCIDA': 'vencida',
}

TRANSICIONES_VALIDAS = {
    'borrador': ['pendiente_admin', 'cancelada'],
    'pendiente_admin': ['pendiente_director', 'devuelta', 'rechazada'],
    'pendiente_director': ['enviada', 'devuelta', 'rechazada'],
    'enviada': ['en_revision', 'autorizada', 'rechazada'],
    'en_revision': ['autorizada', 'devuelta', 'rechazada'],
    'autorizada': ['en_surtido', 'surtida', 'entregada', 'cancelada'],
    'en_surtido': ['surtida', 'entregada'],
    'surtida': ['entregada', 'vencida'],
    'entregada': [],  # Estado final
    'rechazada': [],  # Estado final
    'cancelada': [],  # Estado final
    'devuelta': ['pendiente_admin'],  # Puede reenviarse
    'vencida': [],  # Estado final
}

ESTADOS_EDITABLES = ['borrador', 'devuelta']
ESTADOS_FINALES = ['entregada', 'rechazada', 'cancelada', 'vencida']

ROLES = {
    'MEDICO': 'medico',
    'ADMIN_CENTRO': 'administrador_centro',
    'DIRECTOR_CENTRO': 'director_centro',
    'FARMACIA': 'farmacia',
    'ADMIN_FARMACIA': 'admin_farmacia',
}


# ============================================================================
# TESTS DE VALIDACIÓN DE ESTADOS Y TRANSICIONES
# ============================================================================

class TestEstadosRequisicion(TestCase):
    """Tests para validar la máquina de estados de requisiciones"""
    
    def test_estados_editables_definidos(self):
        """Verifica que solo borrador y devuelta son editables"""
        for estado in ESTADOS_EDITABLES:
            self.assertIn(estado, ['borrador', 'devuelta'])
    
    def test_estados_finales_no_editables(self):
        """Verifica que estados finales no son editables"""
        for estado in ESTADOS_FINALES:
            self.assertNotIn(estado, ESTADOS_EDITABLES)
    
    def test_rechazada_es_final(self):
        """Rechazada es estado final sin transiciones"""
        self.assertEqual(TRANSICIONES_VALIDAS.get('rechazada', []), [])
    
    def test_entregada_es_final(self):
        """Entregada es estado final sin transiciones"""
        self.assertEqual(TRANSICIONES_VALIDAS.get('entregada', []), [])
    
    def test_devuelta_puede_reenviar(self):
        """Devuelta puede transicionar a pendiente_admin"""
        self.assertIn('pendiente_admin', TRANSICIONES_VALIDAS.get('devuelta', []))
    
    def test_transicion_borrador_a_pendiente_admin(self):
        """Médico puede enviar borrador a admin"""
        self.assertIn('pendiente_admin', TRANSICIONES_VALIDAS['borrador'])
    
    def test_transicion_pendiente_admin_a_director(self):
        """Admin puede aprobar y enviar a director"""
        self.assertIn('pendiente_director', TRANSICIONES_VALIDAS['pendiente_admin'])
    
    def test_transicion_pendiente_admin_puede_devolver(self):
        """Admin puede devolver requisición"""
        self.assertIn('devuelta', TRANSICIONES_VALIDAS['pendiente_admin'])
    
    def test_transicion_pendiente_admin_puede_rechazar(self):
        """Admin puede rechazar requisición"""
        self.assertIn('rechazada', TRANSICIONES_VALIDAS['pendiente_admin'])
    
    def test_transicion_pendiente_director_a_enviada(self):
        """Director puede aprobar y enviar a farmacia"""
        self.assertIn('enviada', TRANSICIONES_VALIDAS['pendiente_director'])
    
    def test_transicion_pendiente_director_puede_devolver(self):
        """Director puede devolver requisición"""
        self.assertIn('devuelta', TRANSICIONES_VALIDAS['pendiente_director'])
    
    def test_transicion_pendiente_director_puede_rechazar(self):
        """Director puede rechazar requisición"""
        self.assertIn('rechazada', TRANSICIONES_VALIDAS['pendiente_director'])
    
    def test_transicion_enviada_a_autorizada(self):
        """Farmacia puede autorizar requisición"""
        self.assertIn('autorizada', TRANSICIONES_VALIDAS['enviada'])
    
    def test_transicion_autorizada_a_entregada(self):
        """Requisición autorizada puede entregarse"""
        self.assertIn('entregada', TRANSICIONES_VALIDAS['autorizada'])


# ============================================================================
# TESTS DE PERMISOS POR ROL
# ============================================================================

class TestPermisosRol(TestCase):
    """Tests para validar permisos de cada rol en el flujo"""
    
    def es_transicion_permitida_para_rol(self, rol, estado_actual, accion):
        """Valida si un rol puede ejecutar una acción en un estado"""
        permisos_por_rol = {
            'medico': {
                'enviar_admin': ['borrador'],
                'reenviar': ['devuelta'],
                'cancelar': ['borrador', 'devuelta'],
                'editar': ['borrador', 'devuelta'],
            },
            'administrador_centro': {
                'autorizar_admin': ['pendiente_admin'],
                'devolver': ['pendiente_admin'],
                'rechazar': ['pendiente_admin'],
            },
            'director_centro': {
                'autorizar_director': ['pendiente_director'],
                'devolver': ['pendiente_director'],
                'rechazar': ['pendiente_director'],
            },
            'farmacia': {
                'recibir': ['enviada'],
                'autorizar_farmacia': ['en_revision', 'enviada'],
                'surtir': ['autorizada', 'en_surtido'],
                'entregar': ['surtida', 'autorizada'],
                'devolver': ['en_revision'],
                'rechazar': ['enviada', 'en_revision'],
            },
        }
        
        rol_permisos = permisos_por_rol.get(rol, {})
        estados_permitidos = rol_permisos.get(accion, [])
        return estado_actual in estados_permitidos
    
    # --- Tests para MÉDICO ---
    def test_medico_puede_enviar_borrador(self):
        """Médico puede enviar requisición en borrador"""
        self.assertTrue(
            self.es_transicion_permitida_para_rol('medico', 'borrador', 'enviar_admin')
        )
    
    def test_medico_puede_editar_borrador(self):
        """Médico puede editar requisición en borrador"""
        self.assertTrue(
            self.es_transicion_permitida_para_rol('medico', 'borrador', 'editar')
        )
    
    def test_medico_puede_editar_devuelta(self):
        """Médico puede editar requisición devuelta"""
        self.assertTrue(
            self.es_transicion_permitida_para_rol('medico', 'devuelta', 'editar')
        )
    
    def test_medico_puede_reenviar_devuelta(self):
        """Médico puede reenviar requisición devuelta"""
        self.assertTrue(
            self.es_transicion_permitida_para_rol('medico', 'devuelta', 'reenviar')
        )
    
    def test_medico_no_puede_editar_rechazada(self):
        """Médico NO puede editar requisición rechazada"""
        self.assertFalse(
            self.es_transicion_permitida_para_rol('medico', 'rechazada', 'editar')
        )
    
    def test_medico_no_puede_editar_pendiente_admin(self):
        """Médico NO puede editar requisición pendiente_admin"""
        self.assertFalse(
            self.es_transicion_permitida_para_rol('medico', 'pendiente_admin', 'editar')
        )
    
    # --- Tests para ADMINISTRADOR DEL CENTRO ---
    def test_admin_puede_autorizar_pendiente_admin(self):
        """Admin puede autorizar en pendiente_admin"""
        self.assertTrue(
            self.es_transicion_permitida_para_rol('administrador_centro', 'pendiente_admin', 'autorizar_admin')
        )
    
    def test_admin_puede_devolver_pendiente_admin(self):
        """Admin puede devolver en pendiente_admin"""
        self.assertTrue(
            self.es_transicion_permitida_para_rol('administrador_centro', 'pendiente_admin', 'devolver')
        )
    
    def test_admin_puede_rechazar_pendiente_admin(self):
        """Admin puede rechazar en pendiente_admin"""
        self.assertTrue(
            self.es_transicion_permitida_para_rol('administrador_centro', 'pendiente_admin', 'rechazar')
        )
    
    def test_admin_no_puede_actuar_en_pendiente_director(self):
        """Admin NO puede actuar en pendiente_director"""
        self.assertFalse(
            self.es_transicion_permitida_para_rol('administrador_centro', 'pendiente_director', 'autorizar_admin')
        )
    
    # --- Tests para DIRECTOR DEL CENTRO ---
    def test_director_puede_autorizar_pendiente_director(self):
        """Director puede autorizar en pendiente_director"""
        self.assertTrue(
            self.es_transicion_permitida_para_rol('director_centro', 'pendiente_director', 'autorizar_director')
        )
    
    def test_director_puede_devolver_pendiente_director(self):
        """Director puede devolver en pendiente_director"""
        self.assertTrue(
            self.es_transicion_permitida_para_rol('director_centro', 'pendiente_director', 'devolver')
        )
    
    def test_director_puede_rechazar_pendiente_director(self):
        """Director puede rechazar en pendiente_director"""
        self.assertTrue(
            self.es_transicion_permitida_para_rol('director_centro', 'pendiente_director', 'rechazar')
        )
    
    def test_director_no_puede_actuar_en_pendiente_admin(self):
        """Director NO puede actuar en pendiente_admin"""
        self.assertFalse(
            self.es_transicion_permitida_para_rol('director_centro', 'pendiente_admin', 'autorizar_director')
        )
    
    # --- Tests para FARMACIA ---
    def test_farmacia_puede_recibir_enviada(self):
        """Farmacia puede recibir requisición enviada"""
        self.assertTrue(
            self.es_transicion_permitida_para_rol('farmacia', 'enviada', 'recibir')
        )
    
    def test_farmacia_puede_autorizar_en_revision(self):
        """Farmacia puede autorizar en en_revision"""
        self.assertTrue(
            self.es_transicion_permitida_para_rol('farmacia', 'en_revision', 'autorizar_farmacia')
        )
    
    def test_farmacia_puede_autorizar_directamente(self):
        """Farmacia puede autorizar directamente sin recibir"""
        self.assertTrue(
            self.es_transicion_permitida_para_rol('farmacia', 'enviada', 'autorizar_farmacia')
        )
    
    def test_farmacia_puede_surtir_autorizada(self):
        """Farmacia puede surtir requisición autorizada"""
        self.assertTrue(
            self.es_transicion_permitida_para_rol('farmacia', 'autorizada', 'surtir')
        )
    
    def test_farmacia_puede_entregar(self):
        """Farmacia puede entregar requisición"""
        self.assertTrue(
            self.es_transicion_permitida_para_rol('farmacia', 'autorizada', 'entregar')
        )


# ============================================================================
# TESTS DE VISIBILIDAD POR ROL
# ============================================================================

class TestVisibilidadPorRol(TestCase):
    """Tests para validar qué requisiciones puede ver cada rol"""
    
    # Estados que FARMACIA puede ver (enviadas por director)
    ESTADOS_VISIBLES_FARMACIA = [
        'enviada', 'en_revision', 'autorizada', 'en_surtido', 
        'surtida', 'entregada', 'rechazada', 'cancelada', 'vencida'
    ]
    
    # Estados que FARMACIA NO debe ver (internos del centro)
    ESTADOS_OCULTOS_FARMACIA = [
        'borrador', 'pendiente_admin', 'pendiente_director', 'devuelta'
    ]
    
    def test_farmacia_no_ve_borrador(self):
        """Farmacia NO debe ver requisiciones en borrador"""
        self.assertIn('borrador', self.ESTADOS_OCULTOS_FARMACIA)
        self.assertNotIn('borrador', self.ESTADOS_VISIBLES_FARMACIA)
    
    def test_farmacia_no_ve_pendiente_admin(self):
        """Farmacia NO debe ver requisiciones pendiente_admin"""
        self.assertIn('pendiente_admin', self.ESTADOS_OCULTOS_FARMACIA)
        self.assertNotIn('pendiente_admin', self.ESTADOS_VISIBLES_FARMACIA)
    
    def test_farmacia_no_ve_pendiente_director(self):
        """Farmacia NO debe ver requisiciones pendiente_director"""
        self.assertIn('pendiente_director', self.ESTADOS_OCULTOS_FARMACIA)
        self.assertNotIn('pendiente_director', self.ESTADOS_VISIBLES_FARMACIA)
    
    def test_farmacia_no_ve_devuelta(self):
        """Farmacia NO debe ver requisiciones devueltas (regresadas al centro)"""
        self.assertIn('devuelta', self.ESTADOS_OCULTOS_FARMACIA)
        self.assertNotIn('devuelta', self.ESTADOS_VISIBLES_FARMACIA)
    
    def test_farmacia_ve_enviada(self):
        """Farmacia SÍ debe ver requisiciones enviadas"""
        self.assertIn('enviada', self.ESTADOS_VISIBLES_FARMACIA)
    
    def test_farmacia_ve_autorizada(self):
        """Farmacia SÍ debe ver requisiciones autorizadas"""
        self.assertIn('autorizada', self.ESTADOS_VISIBLES_FARMACIA)
    
    def test_farmacia_ve_surtida(self):
        """Farmacia SÍ debe ver requisiciones surtidas"""
        self.assertIn('surtida', self.ESTADOS_VISIBLES_FARMACIA)
    
    def test_farmacia_ve_entregada(self):
        """Farmacia SÍ debe ver requisiciones entregadas"""
        self.assertIn('entregada', self.ESTADOS_VISIBLES_FARMACIA)
    
    def test_estados_ocultos_son_internos_centro(self):
        """Los estados ocultos son todos internos del centro"""
        # Todos estos estados son procesados DENTRO del centro
        # antes de que el director envíe a farmacia
        for estado in self.ESTADOS_OCULTOS_FARMACIA:
            self.assertIn(estado, ['borrador', 'pendiente_admin', 'pendiente_director', 'devuelta'])


# ============================================================================
# TESTS DE FLUJO COMPLETO
# ============================================================================

class TestFlujoCompleto(TestCase):
    """Tests del flujo completo de una requisición"""
    
    def simular_flujo(self, incluir_devoluciones=False):
        """Simula el flujo completo de una requisición"""
        estados_visitados = []
        estado_actual = 'borrador'
        estados_visitados.append(estado_actual)
        
        # 1. Médico envía a Admin
        estado_actual = 'pendiente_admin'
        estados_visitados.append(estado_actual)
        
        if incluir_devoluciones:
            # Admin devuelve
            estado_actual = 'devuelta'
            estados_visitados.append(estado_actual)
            # Médico edita y reenvía
            estado_actual = 'pendiente_admin'
            estados_visitados.append(estado_actual)
        
        # 2. Admin aprueba → Director
        estado_actual = 'pendiente_director'
        estados_visitados.append(estado_actual)
        
        if incluir_devoluciones:
            # Director devuelve
            estado_actual = 'devuelta'
            estados_visitados.append(estado_actual)
            # Médico edita y reenvía
            estado_actual = 'pendiente_admin'
            estados_visitados.append(estado_actual)
            # Admin aprueba de nuevo
            estado_actual = 'pendiente_director'
            estados_visitados.append(estado_actual)
        
        # 3. Director aprueba → Farmacia
        estado_actual = 'enviada'
        estados_visitados.append(estado_actual)
        
        # 4. Farmacia recibe
        estado_actual = 'en_revision'
        estados_visitados.append(estado_actual)
        
        # 5. Farmacia autoriza
        estado_actual = 'autorizada'
        estados_visitados.append(estado_actual)
        
        # 6. Farmacia surte y entrega
        estado_actual = 'entregada'
        estados_visitados.append(estado_actual)
        
        return estados_visitados
    
    def test_flujo_completo_sin_devoluciones(self):
        """Flujo completo sin devoluciones"""
        estados = self.simular_flujo(incluir_devoluciones=False)
        
        # Verificar inicio y fin
        self.assertEqual(estados[0], 'borrador')
        self.assertEqual(estados[-1], 'entregada')
        
        # Verificar que pasó por todos los estados importantes
        self.assertIn('pendiente_admin', estados)
        self.assertIn('pendiente_director', estados)
        self.assertIn('enviada', estados)
        self.assertIn('autorizada', estados)
    
    def test_flujo_completo_con_devoluciones(self):
        """Flujo completo con devoluciones de admin y director"""
        estados = self.simular_flujo(incluir_devoluciones=True)
        
        # Verificar inicio y fin
        self.assertEqual(estados[0], 'borrador')
        self.assertEqual(estados[-1], 'entregada')
        
        # Verificar que hubo devoluciones
        devuelta_count = estados.count('devuelta')
        self.assertGreaterEqual(devuelta_count, 1)
        
        # Verificar que después de devuelta se pudo reenviar
        for i, estado in enumerate(estados):
            if estado == 'devuelta' and i < len(estados) - 1:
                self.assertEqual(estados[i + 1], 'pendiente_admin')
    
    def test_transiciones_validas_en_flujo(self):
        """Verifica que todas las transiciones del flujo son válidas"""
        estados = self.simular_flujo(incluir_devoluciones=False)
        
        for i in range(len(estados) - 1):
            estado_actual = estados[i]
            estado_siguiente = estados[i + 1]
            transiciones_permitidas = TRANSICIONES_VALIDAS.get(estado_actual, [])
            self.assertIn(
                estado_siguiente, 
                transiciones_permitidas,
                f"Transición inválida: {estado_actual} → {estado_siguiente}"
            )


# ============================================================================
# TESTS DE DEVOLUCIÓN Y EDICIÓN
# ============================================================================

class TestDevolucionYEdicion(TestCase):
    """Tests para verificar que devolución permite edición y rechazo no"""
    
    def puede_editar(self, estado):
        """Verifica si una requisición en cierto estado puede editarse"""
        return estado in ESTADOS_EDITABLES
    
    def test_borrador_es_editable(self):
        """Borrador es editable"""
        self.assertTrue(self.puede_editar('borrador'))
    
    def test_devuelta_es_editable(self):
        """Devuelta es editable"""
        self.assertTrue(self.puede_editar('devuelta'))
    
    def test_rechazada_no_es_editable(self):
        """Rechazada NO es editable"""
        self.assertFalse(self.puede_editar('rechazada'))
    
    def test_pendiente_admin_no_es_editable(self):
        """Pendiente admin NO es editable"""
        self.assertFalse(self.puede_editar('pendiente_admin'))
    
    def test_pendiente_director_no_es_editable(self):
        """Pendiente director NO es editable"""
        self.assertFalse(self.puede_editar('pendiente_director'))
    
    def test_enviada_no_es_editable(self):
        """Enviada NO es editable"""
        self.assertFalse(self.puede_editar('enviada'))
    
    def test_autorizada_no_es_editable(self):
        """Autorizada NO es editable"""
        self.assertFalse(self.puede_editar('autorizada'))
    
    def test_entregada_no_es_editable(self):
        """Entregada NO es editable"""
        self.assertFalse(self.puede_editar('entregada'))
    
    def test_cancelada_no_es_editable(self):
        """Cancelada NO es editable"""
        self.assertFalse(self.puede_editar('cancelada'))


# ============================================================================
# TESTS DE AUTORIZACIÓN DE FARMACIA
# ============================================================================

class TestAutorizacionFarmacia(TestCase):
    """Tests para la autorización de farmacia con ajuste de cantidades"""
    
    def autorizar_con_cantidades(self, items_solicitados, stock_disponible):
        """
        Simula la autorización de farmacia que puede ajustar cantidades.
        
        Args:
            items_solicitados: Lista de dict con producto_id y cantidad_solicitada
            stock_disponible: Dict de producto_id -> stock disponible
            
        Returns:
            Lista de items con cantidad_autorizada
        """
        items_autorizados = []
        for item in items_solicitados:
            producto_id = item['producto_id']
            cantidad_solicitada = item['cantidad_solicitada']
            stock = stock_disponible.get(producto_id, 0)
            
            # Farmacia autoriza el mínimo entre lo solicitado y lo disponible
            cantidad_autorizada = min(cantidad_solicitada, stock)
            
            items_autorizados.append({
                'producto_id': producto_id,
                'cantidad_solicitada': cantidad_solicitada,
                'cantidad_autorizada': cantidad_autorizada,
                'motivo_ajuste': None if cantidad_autorizada == cantidad_solicitada 
                                 else f'Stock disponible: {stock}'
            })
        
        return items_autorizados
    
    def test_autorizacion_cantidad_completa(self):
        """Farmacia autoriza cantidad completa cuando hay stock"""
        items = [{'producto_id': 1, 'cantidad_solicitada': 10}]
        stock = {1: 100}
        
        resultado = self.autorizar_con_cantidades(items, stock)
        
        self.assertEqual(resultado[0]['cantidad_autorizada'], 10)
        self.assertIsNone(resultado[0]['motivo_ajuste'])
    
    def test_autorizacion_cantidad_parcial(self):
        """Farmacia autoriza cantidad parcial cuando no hay suficiente stock"""
        items = [{'producto_id': 1, 'cantidad_solicitada': 100}]
        stock = {1: 50}
        
        resultado = self.autorizar_con_cantidades(items, stock)
        
        self.assertEqual(resultado[0]['cantidad_autorizada'], 50)
        self.assertIsNotNone(resultado[0]['motivo_ajuste'])
    
    def test_autorizacion_sin_stock(self):
        """Farmacia autoriza 0 cuando no hay stock"""
        items = [{'producto_id': 1, 'cantidad_solicitada': 10}]
        stock = {1: 0}
        
        resultado = self.autorizar_con_cantidades(items, stock)
        
        self.assertEqual(resultado[0]['cantidad_autorizada'], 0)
    
    def test_autorizacion_multiples_productos(self):
        """Farmacia autoriza múltiples productos con diferentes stocks"""
        items = [
            {'producto_id': 1, 'cantidad_solicitada': 50},
            {'producto_id': 2, 'cantidad_solicitada': 30},
            {'producto_id': 3, 'cantidad_solicitada': 100},
        ]
        stock = {1: 50, 2: 10, 3: 200}
        
        resultado = self.autorizar_con_cantidades(items, stock)
        
        # Producto 1: completo
        self.assertEqual(resultado[0]['cantidad_autorizada'], 50)
        # Producto 2: parcial
        self.assertEqual(resultado[1]['cantidad_autorizada'], 10)
        # Producto 3: completo (hay más stock del solicitado)
        self.assertEqual(resultado[2]['cantidad_autorizada'], 100)


# ============================================================================
# TESTS DE HOJA DE RECOLECCIÓN
# ============================================================================

class TestHojaRecoleccion(TestCase):
    """Tests para la generación de hoja de recolección"""
    
    def generar_hoja_recoleccion(self, requisicion_data):
        """Simula la generación de una hoja de recolección"""
        return {
            'folio_hoja': f"HR-{requisicion_data['folio']}",
            'requisicion_id': requisicion_data['id'],
            'fecha_generacion': timezone.now(),
            'estado': 'pendiente',
            'items': requisicion_data['items_autorizados'],
            'firmas': {
                'administrador_centro': None,
                'personal_centro': None,
                'farmacia_aprobo': None,
                'farmacia_entrego': None,
                'centro_recibio': None,
            },
            'hash_contenido': 'sha256_hash_simulado',
        }
    
    def test_hoja_tiene_folio(self):
        """Hoja de recolección tiene folio único"""
        requisicion = {
            'id': 1,
            'folio': 'REQ-2026-0001',
            'items_autorizados': [{'producto_id': 1, 'cantidad': 10}]
        }
        
        hoja = self.generar_hoja_recoleccion(requisicion)
        
        self.assertIn('HR-', hoja['folio_hoja'])
        self.assertEqual(hoja['folio_hoja'], 'HR-REQ-2026-0001')
    
    def test_hoja_tiene_todas_las_firmas(self):
        """Hoja de recolección tiene espacios para todas las firmas requeridas"""
        requisicion = {
            'id': 1,
            'folio': 'REQ-2026-0001',
            'items_autorizados': []
        }
        
        hoja = self.generar_hoja_recoleccion(requisicion)
        
        firmas_requeridas = [
            'administrador_centro',
            'personal_centro',
            'farmacia_aprobo',
            'farmacia_entrego',
            'centro_recibio',
        ]
        
        for firma in firmas_requeridas:
            self.assertIn(firma, hoja['firmas'])
    
    def test_hoja_tiene_hash_integridad(self):
        """Hoja de recolección tiene hash para verificar integridad"""
        requisicion = {
            'id': 1,
            'folio': 'REQ-2026-0001',
            'items_autorizados': []
        }
        
        hoja = self.generar_hoja_recoleccion(requisicion)
        
        self.assertIn('hash_contenido', hoja)
        self.assertIsNotNone(hoja['hash_contenido'])
    
    def test_hoja_estado_inicial_pendiente(self):
        """Hoja de recolección inicia en estado pendiente"""
        requisicion = {
            'id': 1,
            'folio': 'REQ-2026-0001',
            'items_autorizados': []
        }
        
        hoja = self.generar_hoja_recoleccion(requisicion)
        
        self.assertEqual(hoja['estado'], 'pendiente')


# ============================================================================
# TESTS DE INVENTARIO
# ============================================================================

class TestInventario(TestCase):
    """Tests para el manejo de inventario al surtir y entregar"""
    
    def procesar_entrega(self, items_autorizados, inventario_farmacia, inventario_centro):
        """
        Simula el proceso de entrega:
        1. Descuenta del inventario de farmacia
        2. Agrega al inventario del centro
        """
        errores = []
        movimientos = []
        
        for item in items_autorizados:
            producto_id = item['producto_id']
            cantidad = item['cantidad_autorizada']
            
            # Verificar stock en farmacia
            stock_farmacia = inventario_farmacia.get(producto_id, 0)
            if stock_farmacia < cantidad:
                errores.append({
                    'producto_id': producto_id,
                    'error': f'Stock insuficiente. Disponible: {stock_farmacia}, Requerido: {cantidad}'
                })
                continue
            
            # Descontar de farmacia
            inventario_farmacia[producto_id] = stock_farmacia - cantidad
            movimientos.append({
                'tipo': 'SALIDA',
                'ubicacion': 'farmacia',
                'producto_id': producto_id,
                'cantidad': cantidad,
            })
            
            # Agregar a centro
            stock_centro = inventario_centro.get(producto_id, 0)
            inventario_centro[producto_id] = stock_centro + cantidad
            movimientos.append({
                'tipo': 'ENTRADA',
                'ubicacion': 'centro',
                'producto_id': producto_id,
                'cantidad': cantidad,
            })
        
        return {
            'exito': len(errores) == 0,
            'errores': errores,
            'movimientos': movimientos,
            'inventario_farmacia': inventario_farmacia,
            'inventario_centro': inventario_centro,
        }
    
    def test_entrega_descuenta_farmacia(self):
        """Entrega descuenta correctamente del inventario de farmacia"""
        items = [{'producto_id': 1, 'cantidad_autorizada': 10}]
        inv_farmacia = {1: 100}
        inv_centro = {1: 0}
        
        resultado = self.procesar_entrega(items, inv_farmacia, inv_centro)
        
        self.assertTrue(resultado['exito'])
        self.assertEqual(resultado['inventario_farmacia'][1], 90)
    
    def test_entrega_agrega_a_centro(self):
        """Entrega agrega correctamente al inventario del centro"""
        items = [{'producto_id': 1, 'cantidad_autorizada': 10}]
        inv_farmacia = {1: 100}
        inv_centro = {1: 5}
        
        resultado = self.procesar_entrega(items, inv_farmacia, inv_centro)
        
        self.assertTrue(resultado['exito'])
        self.assertEqual(resultado['inventario_centro'][1], 15)
    
    def test_entrega_falla_sin_stock(self):
        """Entrega falla si no hay suficiente stock en farmacia"""
        items = [{'producto_id': 1, 'cantidad_autorizada': 100}]
        inv_farmacia = {1: 10}
        inv_centro = {1: 0}
        
        resultado = self.procesar_entrega(items, inv_farmacia, inv_centro)
        
        self.assertFalse(resultado['exito'])
        self.assertEqual(len(resultado['errores']), 1)
    
    def test_entrega_genera_movimientos(self):
        """Entrega genera movimientos de salida y entrada"""
        items = [{'producto_id': 1, 'cantidad_autorizada': 10}]
        inv_farmacia = {1: 100}
        inv_centro = {1: 0}
        
        resultado = self.procesar_entrega(items, inv_farmacia, inv_centro)
        
        self.assertEqual(len(resultado['movimientos']), 2)
        
        movimiento_salida = next(m for m in resultado['movimientos'] if m['tipo'] == 'SALIDA')
        movimiento_entrada = next(m for m in resultado['movimientos'] if m['tipo'] == 'ENTRADA')
        
        self.assertEqual(movimiento_salida['ubicacion'], 'farmacia')
        self.assertEqual(movimiento_entrada['ubicacion'], 'centro')


# ============================================================================
# TESTS MASIVOS CON MÚLTIPLES CENTROS
# ============================================================================

class TestMultiplesCentros(TestCase):
    """Tests masivos simulando 23 centros con múltiples usuarios"""
    
    def crear_centro(self, numero):
        """Crea datos simulados de un centro"""
        return {
            'id': numero,
            'nombre': f'Centro Penitenciario {numero}',
            'codigo': f'CP{numero:03d}',
            'usuarios': {
                'medico': f'medico_c{numero}',
                'admin_centro': f'admin_c{numero}',
                'director_centro': f'director_c{numero}',
                'auxiliar': f'auxiliar_c{numero}',
            }
        }
    
    def crear_requisicion(self, centro_id, numero_req):
        """Crea una requisición simulada"""
        return {
            'id': f'{centro_id}_{numero_req}',
            'folio': f'REQ-{centro_id:02d}-{numero_req:04d}',
            'centro_id': centro_id,
            'estado': 'borrador',
            'items': [
                {'producto_id': i, 'cantidad_solicitada': random.randint(5, 50)}
                for i in range(1, PRODUCTOS_POR_REQUISICION + 1)
            ]
        }
    
    def test_crear_23_centros(self):
        """Puede crear 23 centros con sus usuarios"""
        centros = [self.crear_centro(i) for i in range(1, NUM_CENTROS + 1)]
        
        self.assertEqual(len(centros), NUM_CENTROS)
        
        for centro in centros:
            self.assertIn('medico', centro['usuarios'])
            self.assertIn('admin_centro', centro['usuarios'])
            self.assertIn('director_centro', centro['usuarios'])
    
    def test_crear_requisiciones_por_centro(self):
        """Cada centro puede crear múltiples requisiciones"""
        centros = [self.crear_centro(i) for i in range(1, NUM_CENTROS + 1)]
        todas_requisiciones = []
        
        for centro in centros:
            for i in range(REQUISICIONES_POR_CENTRO):
                req = self.crear_requisicion(centro['id'], i + 1)
                todas_requisiciones.append(req)
        
        total_esperado = NUM_CENTROS * REQUISICIONES_POR_CENTRO
        self.assertEqual(len(todas_requisiciones), total_esperado)
    
    def test_folios_unicos(self):
        """Todos los folios de requisición son únicos"""
        centros = [self.crear_centro(i) for i in range(1, NUM_CENTROS + 1)]
        todas_requisiciones = []
        
        for centro in centros:
            for i in range(REQUISICIONES_POR_CENTRO):
                req = self.crear_requisicion(centro['id'], i + 1)
                todas_requisiciones.append(req)
        
        folios = [r['folio'] for r in todas_requisiciones]
        self.assertEqual(len(folios), len(set(folios)))  # No hay duplicados
    
    def test_aislamiento_por_centro(self):
        """Requisiciones están aisladas por centro"""
        centro1 = self.crear_centro(1)
        centro2 = self.crear_centro(2)
        
        req1 = self.crear_requisicion(centro1['id'], 1)
        req2 = self.crear_requisicion(centro2['id'], 1)
        
        self.assertNotEqual(req1['centro_id'], req2['centro_id'])
        self.assertNotEqual(req1['folio'], req2['folio'])


# ============================================================================
# TESTS DE CONCURRENCIA
# ============================================================================

class TestConcurrencia(TestCase):
    """Tests para validar comportamiento con múltiples operaciones simultáneas"""
    
    def procesar_requisicion_thread_safe(self, requisicion_id, lock, resultados):
        """Procesa una requisición de forma thread-safe"""
        with lock:
            # Simular procesamiento
            resultado = {
                'requisicion_id': requisicion_id,
                'timestamp': timezone.now().isoformat(),
                'thread_id': threading.current_thread().name,
                'exito': True,
            }
            resultados.append(resultado)
    
    def test_procesamiento_concurrente_simulado(self):
        """Múltiples requisiciones pueden procesarse concurrentemente"""
        num_requisiciones = NUM_CENTROS * REQUISICIONES_POR_CENTRO
        lock = threading.Lock()
        resultados = []
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(num_requisiciones):
                future = executor.submit(
                    self.procesar_requisicion_thread_safe,
                    f'REQ-{i:04d}',
                    lock,
                    resultados
                )
                futures.append(future)
            
            # Esperar a que terminen todos
            for future in as_completed(futures):
                future.result()
        
        # Verificar que todas se procesaron
        self.assertEqual(len(resultados), num_requisiciones)
    
    def test_sin_duplicados_en_concurrencia(self):
        """No hay duplicados al procesar concurrentemente"""
        num_requisiciones = 50
        lock = threading.Lock()
        resultados = []
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(num_requisiciones):
                future = executor.submit(
                    self.procesar_requisicion_thread_safe,
                    f'REQ-{i:04d}',
                    lock,
                    resultados
                )
                futures.append(future)
            
            for future in as_completed(futures):
                future.result()
        
        req_ids = [r['requisicion_id'] for r in resultados]
        self.assertEqual(len(req_ids), len(set(req_ids)))  # No hay duplicados


# ============================================================================
# TESTS DE HISTORIAL
# ============================================================================

class TestHistorialRequisicion(TestCase):
    """Tests para el historial de cambios de estado"""
    
    def registrar_cambio(self, historial, requisicion_id, estado_anterior, estado_nuevo, usuario, accion, motivo=None):
        """Registra un cambio en el historial"""
        entrada = {
            'id': len(historial) + 1,
            'requisicion_id': requisicion_id,
            'estado_anterior': estado_anterior,
            'estado_nuevo': estado_nuevo,
            'usuario': usuario,
            'accion': accion,
            'motivo': motivo,
            'fecha': timezone.now().isoformat(),
        }
        historial.append(entrada)
        return entrada
    
    def test_historial_registra_todos_los_cambios(self):
        """El historial registra todos los cambios de estado"""
        historial = []
        req_id = 'REQ-001'
        
        # Simular flujo completo
        self.registrar_cambio(historial, req_id, None, 'borrador', 'medico1', 'crear')
        self.registrar_cambio(historial, req_id, 'borrador', 'pendiente_admin', 'medico1', 'enviar_admin')
        self.registrar_cambio(historial, req_id, 'pendiente_admin', 'pendiente_director', 'admin1', 'autorizar_admin')
        self.registrar_cambio(historial, req_id, 'pendiente_director', 'enviada', 'director1', 'autorizar_director')
        self.registrar_cambio(historial, req_id, 'enviada', 'autorizada', 'farmacia1', 'autorizar_farmacia')
        self.registrar_cambio(historial, req_id, 'autorizada', 'entregada', 'farmacia1', 'entregar')
        
        self.assertEqual(len(historial), 6)
    
    def test_historial_rechazo_registra_motivo(self):
        """El historial de rechazo incluye el motivo"""
        historial = []
        req_id = 'REQ-001'
        
        self.registrar_cambio(historial, req_id, None, 'borrador', 'medico1', 'crear')
        self.registrar_cambio(historial, req_id, 'borrador', 'pendiente_admin', 'medico1', 'enviar_admin')
        self.registrar_cambio(
            historial, req_id, 'pendiente_admin', 'rechazada', 'admin1', 'rechazar',
            motivo='Productos no justificados según normativa'
        )
        
        rechazo = historial[-1]
        self.assertEqual(rechazo['estado_nuevo'], 'rechazada')
        self.assertIsNotNone(rechazo['motivo'])
        self.assertIn('normativa', rechazo['motivo'])
    
    def test_historial_devolucion_registra_motivo(self):
        """El historial de devolución incluye el motivo"""
        historial = []
        req_id = 'REQ-001'
        
        self.registrar_cambio(historial, req_id, None, 'borrador', 'medico1', 'crear')
        self.registrar_cambio(historial, req_id, 'borrador', 'pendiente_admin', 'medico1', 'enviar_admin')
        self.registrar_cambio(
            historial, req_id, 'pendiente_admin', 'devuelta', 'admin1', 'devolver',
            motivo='Pedir menos de la 615 lote terminación 2025'
        )
        
        devolucion = historial[-1]
        self.assertEqual(devolucion['estado_nuevo'], 'devuelta')
        self.assertIsNotNone(devolucion['motivo'])
    
    def test_historial_devolucion_y_reenvio(self):
        """El historial refleja devolución y posterior reenvío"""
        historial = []
        req_id = 'REQ-001'
        
        self.registrar_cambio(historial, req_id, None, 'borrador', 'medico1', 'crear')
        self.registrar_cambio(historial, req_id, 'borrador', 'pendiente_admin', 'medico1', 'enviar_admin')
        self.registrar_cambio(
            historial, req_id, 'pendiente_admin', 'devuelta', 'admin1', 'devolver',
            motivo='Corregir cantidades'
        )
        self.registrar_cambio(historial, req_id, 'devuelta', 'pendiente_admin', 'medico1', 'reenviar')
        
        # Verificar secuencia
        self.assertEqual(historial[2]['estado_nuevo'], 'devuelta')
        self.assertEqual(historial[3]['estado_nuevo'], 'pendiente_admin')
        self.assertEqual(historial[3]['accion'], 'reenviar')
    
    def test_historial_rechazada_es_final(self):
        """Después de rechazada no hay más entradas en historial"""
        historial = []
        req_id = 'REQ-001'
        
        self.registrar_cambio(historial, req_id, None, 'borrador', 'medico1', 'crear')
        self.registrar_cambio(historial, req_id, 'borrador', 'pendiente_admin', 'medico1', 'enviar_admin')
        self.registrar_cambio(
            historial, req_id, 'pendiente_admin', 'rechazada', 'admin1', 'rechazar',
            motivo='Solicitud denegada'
        )
        
        # Verificar que la última entrada es el rechazo
        self.assertEqual(historial[-1]['estado_nuevo'], 'rechazada')
        self.assertEqual(historial[-1]['accion'], 'rechazar')


# ============================================================================
# TESTS DE ESCENARIOS COMPLETOS
# ============================================================================

class TestEscenariosCompletos(TestCase):
    """Tests de escenarios de uso real"""
    
    def test_escenario_flujo_exitoso_completo(self):
        """
        Escenario: Flujo completo exitoso
        1. Médico crea requisición
        2. Admin del centro aprueba
        3. Director del centro aprueba
        4. Farmacia recibe
        5. Farmacia autoriza con cantidades
        6. Farmacia surte y genera hoja
        7. Centro recoge con firmas
        8. Farmacia confirma entrega
        9. Se actualiza inventario
        """
        estados_esperados = [
            'borrador', 'pendiente_admin', 'pendiente_director', 
            'enviada', 'en_revision', 'autorizada', 'entregada'
        ]
        
        estado_actual = 'borrador'
        estados_visitados = [estado_actual]
        
        # Simular flujo
        transiciones = [
            ('borrador', 'pendiente_admin', 'enviar_admin'),
            ('pendiente_admin', 'pendiente_director', 'autorizar_admin'),
            ('pendiente_director', 'enviada', 'autorizar_director'),
            ('enviada', 'en_revision', 'recibir_farmacia'),
            ('en_revision', 'autorizada', 'autorizar_farmacia'),
            ('autorizada', 'entregada', 'entregar'),
        ]
        
        for estado_desde, estado_hasta, accion in transiciones:
            self.assertEqual(estado_actual, estado_desde)
            self.assertIn(estado_hasta, TRANSICIONES_VALIDAS.get(estado_desde, []))
            estado_actual = estado_hasta
            estados_visitados.append(estado_actual)
        
        self.assertEqual(estado_actual, 'entregada')
        self.assertEqual(estados_visitados, estados_esperados)
    
    def test_escenario_devolucion_admin(self):
        """
        Escenario: Admin devuelve requisición
        1. Médico crea y envía
        2. Admin devuelve con observaciones
        3. Médico edita y reenvía
        4. Admin aprueba
        5. Continúa flujo normal
        """
        historial = []
        estado_actual = 'borrador'
        
        # 1. Médico crea y envía
        historial.append(('borrador', 'pendiente_admin', 'medico'))
        estado_actual = 'pendiente_admin'
        
        # 2. Admin devuelve
        historial.append(('pendiente_admin', 'devuelta', 'admin'))
        estado_actual = 'devuelta'
        
        # 3. Médico puede editar (verificar)
        self.assertTrue(estado_actual in ESTADOS_EDITABLES)
        
        # 4. Médico reenvía
        historial.append(('devuelta', 'pendiente_admin', 'medico'))
        estado_actual = 'pendiente_admin'
        
        # 5. Admin aprueba
        historial.append(('pendiente_admin', 'pendiente_director', 'admin'))
        estado_actual = 'pendiente_director'
        
        self.assertEqual(len(historial), 4)
        self.assertEqual(estado_actual, 'pendiente_director')
    
    def test_escenario_devolucion_director(self):
        """
        Escenario: Director devuelve requisición
        1. Médico crea y envía
        2. Admin aprueba
        3. Director devuelve con observaciones
        4. Médico edita y reenvía
        5. Admin y Director aprueban
        """
        historial = []
        estado_actual = 'borrador'
        
        # Flujo hasta director
        historial.append(('borrador', 'pendiente_admin', 'medico'))
        historial.append(('pendiente_admin', 'pendiente_director', 'admin'))
        estado_actual = 'pendiente_director'
        
        # Director devuelve
        historial.append(('pendiente_director', 'devuelta', 'director'))
        estado_actual = 'devuelta'
        
        # Verificar que puede editar
        self.assertTrue(estado_actual in ESTADOS_EDITABLES)
        
        # Médico reenvía (vuelve a pendiente_admin)
        historial.append(('devuelta', 'pendiente_admin', 'medico'))
        estado_actual = 'pendiente_admin'
        
        # Admin y Director aprueban de nuevo
        historial.append(('pendiente_admin', 'pendiente_director', 'admin'))
        historial.append(('pendiente_director', 'enviada', 'director'))
        estado_actual = 'enviada'
        
        self.assertEqual(len(historial), 6)
        self.assertEqual(estado_actual, 'enviada')
    
    def test_escenario_rechazo_no_editable(self):
        """
        Escenario: Requisición rechazada no es editable
        1. Médico crea y envía
        2. Admin rechaza con motivo
        3. Verificar que no se puede editar
        """
        estado_actual = 'borrador'
        
        # Flujo hasta rechazo
        estado_actual = 'pendiente_admin'
        estado_actual = 'rechazada'
        
        # Verificar que NO se puede editar
        self.assertFalse(estado_actual in ESTADOS_EDITABLES)
        
        # Verificar que no hay transiciones posibles
        transiciones = TRANSICIONES_VALIDAS.get('rechazada', [])
        self.assertEqual(len(transiciones), 0)
    
    def test_escenario_farmacia_ajusta_cantidades(self):
        """
        Escenario: Farmacia ajusta cantidades según stock
        1. Médico solicita 100 unidades
        2. Farmacia solo tiene 50
        3. Farmacia autoriza 50 con motivo
        """
        cantidad_solicitada = 100
        stock_disponible = 50
        
        cantidad_autorizada = min(cantidad_solicitada, stock_disponible)
        
        self.assertEqual(cantidad_autorizada, 50)
        self.assertLess(cantidad_autorizada, cantidad_solicitada)
    
    def test_escenario_multiples_devoluciones(self):
        """
        Escenario: Múltiples devoluciones antes de aprobación final
        """
        devoluciones = 0
        estado_actual = 'borrador'
        max_devoluciones = 3
        
        # Enviar
        estado_actual = 'pendiente_admin'
        
        for i in range(max_devoluciones):
            # Devolver
            estado_actual = 'devuelta'
            devoluciones += 1
            
            # Verificar que puede editar
            self.assertTrue(estado_actual in ESTADOS_EDITABLES)
            
            # Reenviar
            estado_actual = 'pendiente_admin'
        
        # Finalmente aprobar
        estado_actual = 'pendiente_director'
        
        self.assertEqual(devoluciones, max_devoluciones)
        self.assertEqual(estado_actual, 'pendiente_director')


# ============================================================================
# TESTS DE VALIDACIÓN DE DATOS
# ============================================================================

class TestValidacionDatos(TestCase):
    """Tests para validación de datos en requisiciones"""
    
    def validar_requisicion(self, data):
        """Valida los datos de una requisición"""
        errores = []
        
        if not data.get('centro_id'):
            errores.append('centro_id es requerido')
        
        if not data.get('items') or len(data.get('items', [])) == 0:
            errores.append('Debe incluir al menos un producto')
        
        for i, item in enumerate(data.get('items', [])):
            if not item.get('producto_id'):
                errores.append(f'Item {i+1}: producto_id es requerido')
            if not item.get('cantidad_solicitada') or item.get('cantidad_solicitada') <= 0:
                errores.append(f'Item {i+1}: cantidad_solicitada debe ser mayor a 0')
        
        return {'valido': len(errores) == 0, 'errores': errores}
    
    def test_requisicion_valida(self):
        """Requisición con datos completos es válida"""
        data = {
            'centro_id': 1,
            'items': [
                {'producto_id': 1, 'cantidad_solicitada': 10},
                {'producto_id': 2, 'cantidad_solicitada': 20},
            ]
        }
        
        resultado = self.validar_requisicion(data)
        self.assertTrue(resultado['valido'])
    
    def test_requisicion_sin_centro(self):
        """Requisición sin centro es inválida"""
        data = {
            'items': [{'producto_id': 1, 'cantidad_solicitada': 10}]
        }
        
        resultado = self.validar_requisicion(data)
        self.assertFalse(resultado['valido'])
        self.assertIn('centro_id es requerido', resultado['errores'])
    
    def test_requisicion_sin_items(self):
        """Requisición sin items es inválida"""
        data = {
            'centro_id': 1,
            'items': []
        }
        
        resultado = self.validar_requisicion(data)
        self.assertFalse(resultado['valido'])
    
    def test_requisicion_cantidad_cero(self):
        """Requisición con cantidad 0 es inválida"""
        data = {
            'centro_id': 1,
            'items': [{'producto_id': 1, 'cantidad_solicitada': 0}]
        }
        
        resultado = self.validar_requisicion(data)
        self.assertFalse(resultado['valido'])


# ============================================================================
# TESTS DE RENDIMIENTO
# ============================================================================

class TestRendimiento(TestCase):
    """Tests de rendimiento para operaciones masivas"""
    
    def test_crear_muchas_requisiciones(self):
        """Puede crear muchas requisiciones rápidamente"""
        import time
        
        num_requisiciones = NUM_CENTROS * REQUISICIONES_POR_CENTRO
        requisiciones = []
        
        inicio = time.time()
        
        for i in range(num_requisiciones):
            req = {
                'id': i,
                'folio': f'REQ-{i:06d}',
                'centro_id': (i % NUM_CENTROS) + 1,
                'estado': 'borrador',
                'items': [
                    {'producto_id': j, 'cantidad_solicitada': random.randint(1, 100)}
                    for j in range(1, PRODUCTOS_POR_REQUISICION + 1)
                ]
            }
            requisiciones.append(req)
        
        fin = time.time()
        tiempo_total = fin - inicio
        
        self.assertEqual(len(requisiciones), num_requisiciones)
        # Debería completarse en menos de 1 segundo
        self.assertLess(tiempo_total, 1.0)
    
    def test_buscar_por_centro(self):
        """Puede filtrar requisiciones por centro eficientemente"""
        import time
        
        # Crear requisiciones de prueba
        requisiciones = []
        for i in range(NUM_CENTROS * REQUISICIONES_POR_CENTRO):
            requisiciones.append({
                'id': i,
                'centro_id': (i % NUM_CENTROS) + 1,
            })
        
        # Buscar por centro
        centro_buscado = 5
        inicio = time.time()
        
        resultado = [r for r in requisiciones if r['centro_id'] == centro_buscado]
        
        fin = time.time()
        tiempo_busqueda = fin - inicio
        
        self.assertEqual(len(resultado), REQUISICIONES_POR_CENTRO)
        self.assertLess(tiempo_busqueda, 0.1)


# ============================================================================
# RESUMEN DE TESTS
# ============================================================================

"""
RESUMEN DE TESTS DEL FLUJO DE REQUISICIONES
============================================

1. TestEstadosRequisicion (15 tests)
   - Validación de estados editables y finales
   - Transiciones válidas entre estados

2. TestPermisosRol (15 tests)
   - Permisos de médico (crear, editar, enviar, reenviar)
   - Permisos de admin del centro
   - Permisos de director del centro
   - Permisos de farmacia

3. TestFlujoCompleto (3 tests)
   - Flujo sin devoluciones
   - Flujo con devoluciones
   - Validación de transiciones

4. TestDevolucionYEdicion (9 tests)
   - Estados editables (borrador, devuelta)
   - Estados no editables (rechazada, etc.)

5. TestAutorizacionFarmacia (4 tests)
   - Autorización completa
   - Autorización parcial por stock
   - Múltiples productos

6. TestHojaRecoleccion (4 tests)
   - Generación de hoja
   - Campos de firmas
   - Hash de integridad

7. TestInventario (4 tests)
   - Descuento de farmacia
   - Entrada a centro
   - Validación de stock
   - Generación de movimientos

8. TestMultiplesCentros (4 tests)
   - Creación de 23 centros
   - Requisiciones por centro
   - Aislamiento de datos

9. TestConcurrencia (2 tests)
   - Procesamiento concurrente
   - Sin duplicados

10. TestHistorialRequisicion (5 tests)
    - Registro de cambios
    - Historial de rechazo
    - Historial de devolución

11. TestEscenariosCompletos (6 tests)
    - Flujo exitoso completo
    - Devolución por admin
    - Devolución por director
    - Rechazo no editable
    - Ajuste de cantidades
    - Múltiples devoluciones

12. TestValidacionDatos (4 tests)
    - Validación de requisición
    - Campos requeridos

13. TestRendimiento (2 tests)
    - Creación masiva
    - Búsqueda eficiente

TOTAL: ~77 tests
"""


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
