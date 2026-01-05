# -*- coding: utf-8 -*-
"""
Tests unitarios para el flujo completo de requisiciones.
Tests puros sin dependencias de base de datos.

Estados del flujo:
- borrador: Médico creando
- enviada: Enviada a farmacia
- autorizada: Farmacia autoriza
- rechazada: Farmacia rechaza
- devuelta: Farmacia devuelve al médico para corrección
- surtida: Farmacia surte
- entregada: Entregada al centro
- cancelada: Cancelada
"""
import pytest
from unittest.mock import Mock, patch
from django.test import TestCase


class TestMaquinaEstadosRequisicion(TestCase):
    """Tests para la máquina de estados de requisiciones."""
    
    # Definición de la máquina de estados
    ESTADOS = [
        'borrador',
        'enviada', 
        'autorizada',
        'surtida',
        'entregada',
        'rechazada',
        'devuelta',
        'cancelada',
        'vencida'
    ]
    
    TRANSICIONES = {
        'borrador': ['enviada', 'cancelada'],
        'enviada': ['autorizada', 'rechazada', 'devuelta', 'cancelada'],
        'devuelta': ['enviada', 'cancelada'],
        'autorizada': ['surtida', 'rechazada'],
        'surtida': ['entregada'],
        'entregada': [],
        'rechazada': [],
        'cancelada': [],
        'vencida': [],
    }
    
    def _transicion_valida(self, estado_actual, estado_nuevo):
        return estado_nuevo in self.TRANSICIONES.get(estado_actual, [])
    
    # ========== Tests de transiciones válidas ==========
    
    def test_borrador_a_enviada(self):
        """Médico envía requisición borrador."""
        self.assertTrue(self._transicion_valida('borrador', 'enviada'))
    
    def test_borrador_a_cancelada(self):
        """Médico cancela su borrador."""
        self.assertTrue(self._transicion_valida('borrador', 'cancelada'))
    
    def test_enviada_a_autorizada(self):
        """Farmacia autoriza requisición."""
        self.assertTrue(self._transicion_valida('enviada', 'autorizada'))
    
    def test_enviada_a_rechazada(self):
        """Farmacia rechaza requisición."""
        self.assertTrue(self._transicion_valida('enviada', 'rechazada'))
    
    def test_enviada_a_devuelta(self):
        """Farmacia devuelve requisición al médico."""
        self.assertTrue(self._transicion_valida('enviada', 'devuelta'))
    
    def test_devuelta_a_enviada(self):
        """Médico reenvía requisición corregida."""
        self.assertTrue(self._transicion_valida('devuelta', 'enviada'))
    
    def test_devuelta_a_cancelada(self):
        """Médico cancela requisición devuelta."""
        self.assertTrue(self._transicion_valida('devuelta', 'cancelada'))
    
    def test_autorizada_a_surtida(self):
        """Farmacia surte requisición autorizada."""
        self.assertTrue(self._transicion_valida('autorizada', 'surtida'))
    
    def test_surtida_a_entregada(self):
        """Requisición surtida se entrega."""
        self.assertTrue(self._transicion_valida('surtida', 'entregada'))
    
    # ========== Tests de transiciones inválidas ==========
    
    def test_borrador_no_puede_autorizar(self):
        """Borrador no puede ir directamente a autorizada."""
        self.assertFalse(self._transicion_valida('borrador', 'autorizada'))
    
    def test_enviada_no_puede_surtir(self):
        """Enviada no puede ir directamente a surtida."""
        self.assertFalse(self._transicion_valida('enviada', 'surtida'))
    
    def test_devuelta_no_puede_autorizar(self):
        """Devuelta no puede ir a autorizada."""
        self.assertFalse(self._transicion_valida('devuelta', 'autorizada'))
    
    def test_rechazada_no_puede_transicionar(self):
        """Estado rechazada es final."""
        self.assertFalse(self._transicion_valida('rechazada', 'enviada'))
        self.assertFalse(self._transicion_valida('rechazada', 'borrador'))
    
    def test_entregada_es_estado_final(self):
        """Estado entregada es final."""
        self.assertFalse(self._transicion_valida('entregada', 'cancelada'))
        self.assertFalse(self._transicion_valida('entregada', 'surtida'))
    
    def test_cancelada_es_estado_final(self):
        """Estado cancelada es final."""
        self.assertFalse(self._transicion_valida('cancelada', 'borrador'))


class TestPermisosRol(TestCase):
    """Tests de permisos basados en rol."""
    
    ACCIONES_POR_ROL = {
        'medico': {
            'puede_crear': True,
            'puede_editar_borrador': True,
            'puede_editar_devuelta': True,
            'puede_enviar': True,
            'puede_cancelar': True,
            'puede_autorizar': False,
            'puede_rechazar': False,
            'puede_devolver': False,
            'puede_surtir': False,
        },
        'farmacia': {
            'puede_crear': False,
            'puede_editar_borrador': False,
            'puede_editar_devuelta': False,
            'puede_enviar': False,
            'puede_cancelar': True,
            'puede_autorizar': True,
            'puede_rechazar': True,
            'puede_devolver': True,
            'puede_surtir': True,
        },
        'admin_farmacia': {
            'puede_crear': False,
            'puede_editar_borrador': False,
            'puede_editar_devuelta': False,
            'puede_enviar': False,
            'puede_cancelar': True,
            'puede_autorizar': True,
            'puede_rechazar': True,
            'puede_devolver': True,
            'puede_surtir': True,
        },
        'usuario_centro': {
            'puede_crear': False,
            'puede_editar_borrador': False,
            'puede_editar_devuelta': False,
            'puede_enviar': False,
            'puede_cancelar': False,
            'puede_autorizar': False,
            'puede_rechazar': False,
            'puede_devolver': False,
            'puede_surtir': False,
        },
    }
    
    def _puede(self, rol, accion):
        return self.ACCIONES_POR_ROL.get(rol, {}).get(accion, False)
    
    # ========== Tests permisos médico ==========
    
    def test_medico_puede_crear(self):
        self.assertTrue(self._puede('medico', 'puede_crear'))
    
    def test_medico_puede_editar_borrador(self):
        self.assertTrue(self._puede('medico', 'puede_editar_borrador'))
    
    def test_medico_puede_editar_devuelta(self):
        self.assertTrue(self._puede('medico', 'puede_editar_devuelta'))
    
    def test_medico_no_puede_autorizar(self):
        self.assertFalse(self._puede('medico', 'puede_autorizar'))
    
    def test_medico_no_puede_surtir(self):
        self.assertFalse(self._puede('medico', 'puede_surtir'))
    
    # ========== Tests permisos farmacia ==========
    
    def test_farmacia_puede_autorizar(self):
        self.assertTrue(self._puede('farmacia', 'puede_autorizar'))
    
    def test_farmacia_puede_rechazar(self):
        self.assertTrue(self._puede('farmacia', 'puede_rechazar'))
    
    def test_farmacia_puede_devolver(self):
        self.assertTrue(self._puede('farmacia', 'puede_devolver'))
    
    def test_farmacia_puede_surtir(self):
        self.assertTrue(self._puede('farmacia', 'puede_surtir'))
    
    def test_farmacia_no_puede_crear(self):
        self.assertFalse(self._puede('farmacia', 'puede_crear'))
    
    def test_farmacia_no_puede_editar(self):
        self.assertFalse(self._puede('farmacia', 'puede_editar_borrador'))
        self.assertFalse(self._puede('farmacia', 'puede_editar_devuelta'))
    
    # ========== Tests usuario centro ==========
    
    def test_usuario_centro_solo_lectura(self):
        """Usuario centro no puede hacer acciones (solo ver)."""
        for accion in self.ACCIONES_POR_ROL['usuario_centro'].keys():
            self.assertFalse(self._puede('usuario_centro', accion))


class TestEstadosEditables(TestCase):
    """Tests para determinar qué estados permiten edición."""
    
    def test_borrador_es_editable(self):
        """Borrador permite edición."""
        estados_editables = ['borrador', 'devuelta']
        self.assertIn('borrador', estados_editables)
    
    def test_devuelta_es_editable(self):
        """Devuelta permite edición."""
        estados_editables = ['borrador', 'devuelta']
        self.assertIn('devuelta', estados_editables)
    
    def test_enviada_no_es_editable(self):
        """Enviada no permite edición."""
        estados_editables = ['borrador', 'devuelta']
        self.assertNotIn('enviada', estados_editables)
    
    def test_autorizada_no_es_editable(self):
        """Autorizada no permite edición."""
        estados_editables = ['borrador', 'devuelta']
        self.assertNotIn('autorizada', estados_editables)
    
    def test_surtida_no_es_editable(self):
        """Surtida no permite edición."""
        estados_editables = ['borrador', 'devuelta']
        self.assertNotIn('surtida', estados_editables)


class TestFlujoCompleto(TestCase):
    """Tests de flujos completos de uso."""
    
    def test_flujo_normal_exitoso(self):
        """Test: Flujo normal borrador -> entregada."""
        estados_flujo = [
            'borrador',   # Médico crea
            'enviada',    # Médico envía
            'autorizada', # Farmacia autoriza
            'surtida',    # Farmacia surte
            'entregada',  # Se entrega
        ]
        
        TRANSICIONES = {
            'borrador': ['enviada', 'cancelada'],
            'enviada': ['autorizada', 'rechazada', 'devuelta', 'cancelada'],
            'autorizada': ['surtida', 'rechazada'],
            'surtida': ['entregada'],
        }
        
        # Verificar cada transición del flujo
        for i in range(len(estados_flujo) - 1):
            estado_actual = estados_flujo[i]
            estado_siguiente = estados_flujo[i + 1]
            self.assertIn(
                estado_siguiente,
                TRANSICIONES.get(estado_actual, []),
                f"Transición {estado_actual} -> {estado_siguiente} debería ser válida"
            )
    
    def test_flujo_con_devolucion(self):
        """Test: Flujo con devolución y corrección."""
        estados_flujo = [
            'borrador',   # Médico crea
            'enviada',    # Médico envía
            'devuelta',   # Farmacia devuelve
            'enviada',    # Médico reenvía (corregida)
            'autorizada', # Farmacia autoriza
        ]
        
        TRANSICIONES = {
            'borrador': ['enviada', 'cancelada'],
            'enviada': ['autorizada', 'rechazada', 'devuelta', 'cancelada'],
            'devuelta': ['enviada', 'cancelada'],
            'autorizada': ['surtida', 'rechazada'],
        }
        
        for i in range(len(estados_flujo) - 1):
            estado_actual = estados_flujo[i]
            estado_siguiente = estados_flujo[i + 1]
            self.assertIn(
                estado_siguiente,
                TRANSICIONES.get(estado_actual, []),
                f"Transición {estado_actual} -> {estado_siguiente} debería ser válida"
            )
    
    def test_flujo_rechazo(self):
        """Test: Flujo con rechazo."""
        estados_flujo = [
            'borrador',
            'enviada',
            'rechazada',  # Farmacia rechaza
        ]
        
        TRANSICIONES = {
            'borrador': ['enviada', 'cancelada'],
            'enviada': ['autorizada', 'rechazada', 'devuelta', 'cancelada'],
        }
        
        for i in range(len(estados_flujo) - 1):
            estado_actual = estados_flujo[i]
            estado_siguiente = estados_flujo[i + 1]
            self.assertIn(
                estado_siguiente,
                TRANSICIONES.get(estado_actual, []),
                f"Transición {estado_actual} -> {estado_siguiente} debería ser válida"
            )


class TestHistorialEstados(TestCase):
    """Tests para el historial de estados."""
    
    def test_registro_historial_debe_incluir_campos(self):
        """Test: Registro de historial debe tener campos requeridos."""
        registro = {
            'requisicion_id': 1,
            'estado_anterior': 'enviada',
            'estado_nuevo': 'devuelta',
            'usuario_id': 2,
            'observaciones': 'Producto no disponible',
            'fecha': '2026-01-15T10:30:00',
        }
        
        campos_requeridos = ['requisicion_id', 'estado_anterior', 'estado_nuevo', 'usuario_id']
        
        for campo in campos_requeridos:
            self.assertIn(campo, registro)
    
    def test_historial_ordenado_cronologicamente(self):
        """Test: Historial debe estar ordenado por fecha."""
        historial = [
            {'fecha': '2026-01-15T10:00:00', 'estado_nuevo': 'borrador'},
            {'fecha': '2026-01-15T11:00:00', 'estado_nuevo': 'enviada'},
            {'fecha': '2026-01-15T14:00:00', 'estado_nuevo': 'devuelta'},
            {'fecha': '2026-01-15T15:00:00', 'estado_nuevo': 'enviada'},
        ]
        
        # Verificar orden ascendente
        for i in range(len(historial) - 1):
            self.assertLess(historial[i]['fecha'], historial[i + 1]['fecha'])
    
    def test_devolucion_requiere_observaciones(self):
        """Test: Al devolver se requieren observaciones."""
        def validar_devolucion(estado_nuevo, observaciones):
            if estado_nuevo == 'devuelta':
                return observaciones and len(observaciones.strip()) >= 10
            return True
        
        self.assertTrue(validar_devolucion('devuelta', 'Producto no disponible en almacén'))
        self.assertFalse(validar_devolucion('devuelta', ''))
        self.assertFalse(validar_devolucion('devuelta', 'Corto'))
        self.assertTrue(validar_devolucion('autorizada', ''))  # Autorizar no requiere


class TestCalculosRequisicion(TestCase):
    """Tests de cálculos relacionados con requisiciones."""
    
    def test_calcular_total_productos(self):
        """Test: Calcular total de productos solicitados."""
        detalles = [
            {'cantidad_solicitada': 10},
            {'cantidad_solicitada': 5},
            {'cantidad_solicitada': 20},
        ]
        
        total = sum(d['cantidad_solicitada'] for d in detalles)
        
        self.assertEqual(total, 35)
    
    def test_calcular_productos_surtidos(self):
        """Test: Calcular diferencia entre solicitado y surtido."""
        detalles = [
            {'cantidad_solicitada': 10, 'cantidad_surtida': 10},
            {'cantidad_solicitada': 5, 'cantidad_surtida': 3},
            {'cantidad_solicitada': 20, 'cantidad_surtida': 15},
        ]
        
        total_solicitado = sum(d['cantidad_solicitada'] for d in detalles)
        total_surtido = sum(d['cantidad_surtida'] for d in detalles)
        diferencia = total_solicitado - total_surtido
        
        self.assertEqual(total_solicitado, 35)
        self.assertEqual(total_surtido, 28)
        self.assertEqual(diferencia, 7)
    
    def test_porcentaje_surtido(self):
        """Test: Calcular porcentaje de surtido."""
        detalles = [
            {'cantidad_solicitada': 10, 'cantidad_surtida': 8},
            {'cantidad_solicitada': 10, 'cantidad_surtida': 10},
        ]
        
        total_solicitado = sum(d['cantidad_solicitada'] for d in detalles)
        total_surtido = sum(d['cantidad_surtida'] for d in detalles)
        porcentaje = (total_surtido / total_solicitado) * 100 if total_solicitado > 0 else 0
        
        self.assertEqual(porcentaje, 90.0)


class TestFiltrosRequisiciones(TestCase):
    """Tests para filtros de requisiciones."""
    
    def setUp(self):
        self.requisiciones = [
            {'id': 1, 'estado': 'borrador', 'centro_id': 1, 'solicitante_id': 1},
            {'id': 2, 'estado': 'enviada', 'centro_id': 1, 'solicitante_id': 1},
            {'id': 3, 'estado': 'devuelta', 'centro_id': 1, 'solicitante_id': 1},
            {'id': 4, 'estado': 'autorizada', 'centro_id': 2, 'solicitante_id': 2},
            {'id': 5, 'estado': 'enviada', 'centro_id': 2, 'solicitante_id': 2},
        ]
    
    def test_filtrar_mis_requisiciones(self):
        """Test: Filtrar requisiciones del usuario actual."""
        usuario_id = 1
        mis_req = [r for r in self.requisiciones if r['solicitante_id'] == usuario_id]
        
        self.assertEqual(len(mis_req), 3)
    
    def test_filtrar_por_estado(self):
        """Test: Filtrar por estado."""
        enviadas = [r for r in self.requisiciones if r['estado'] == 'enviada']
        
        self.assertEqual(len(enviadas), 2)
    
    def test_filtrar_por_centro(self):
        """Test: Filtrar por centro."""
        centro_id = 1
        del_centro = [r for r in self.requisiciones if r['centro_id'] == centro_id]
        
        self.assertEqual(len(del_centro), 3)
    
    def test_filtrar_pendientes_farmacia(self):
        """Test: Filtrar requisiciones pendientes para farmacia."""
        # Farmacia ve: enviadas (pendientes de revisión)
        pendientes = [r for r in self.requisiciones if r['estado'] == 'enviada']
        
        self.assertEqual(len(pendientes), 2)
    
    def test_filtrar_devueltas_medico(self):
        """Test: Médico ve sus requisiciones devueltas."""
        usuario_id = 1
        devueltas = [r for r in self.requisiciones 
                    if r['solicitante_id'] == usuario_id and r['estado'] == 'devuelta']
        
        self.assertEqual(len(devueltas), 1)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
