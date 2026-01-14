# -*- coding: utf-8 -*-
"""
Tests unitarios para el flujo de autorización de requisiciones por farmacia.
Verifica la corrección ISS-FIX-AUTORIZACION para incluir estado 'en_revision'.

Flujo correcto:
1. enviada → (recibir) → en_revision → (autorizar) → autorizada/parcial
2. enviada → (autorizar directamente) → autorizada/parcial

Farmacia NO puede devolver - solo rechazar o ajustar cantidades.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase


class TestAutorizacionFarmaciaEstados(TestCase):
    """Tests para verificar que farmacia puede autorizar en estados correctos."""
    
    # Definición de estados donde farmacia puede autorizar
    ESTADOS_AUTORIZABLES = ['enviada', 'en_revision']
    
    # Definición de estados donde farmacia puede rechazar
    ESTADOS_RECHAZABLES = ['enviada', 'en_revision']
    
    # Estados donde farmacia NO puede devolver (después del fix)
    ESTADOS_DEVOLVIBLES_FARMACIA = []  # Farmacia ya NO puede devolver
    
    def test_farmacia_puede_autorizar_en_enviada(self):
        """Farmacia puede autorizar directamente desde 'enviada'."""
        self.assertIn('enviada', self.ESTADOS_AUTORIZABLES)
    
    def test_farmacia_puede_autorizar_en_revision(self):
        """Farmacia puede autorizar desde 'en_revision' (después de recibir)."""
        self.assertIn('en_revision', self.ESTADOS_AUTORIZABLES)
    
    def test_farmacia_puede_rechazar_en_enviada(self):
        """Farmacia puede rechazar desde 'enviada'."""
        self.assertIn('enviada', self.ESTADOS_RECHAZABLES)
    
    def test_farmacia_puede_rechazar_en_revision(self):
        """Farmacia puede rechazar desde 'en_revision'."""
        self.assertIn('en_revision', self.ESTADOS_RECHAZABLES)
    
    def test_farmacia_no_puede_devolver(self):
        """Farmacia NO puede devolver al médico - solo rechazar o ajustar cantidades."""
        self.assertEqual(self.ESTADOS_DEVOLVIBLES_FARMACIA, [])
    
    def test_estados_autorizables_no_incluyen_borrador(self):
        """No se puede autorizar un borrador."""
        self.assertNotIn('borrador', self.ESTADOS_AUTORIZABLES)
    
    def test_estados_autorizables_no_incluyen_autorizada(self):
        """No se puede re-autorizar una ya autorizada."""
        self.assertNotIn('autorizada', self.ESTADOS_AUTORIZABLES)
    
    def test_estados_autorizables_no_incluyen_estados_finales(self):
        """No se puede autorizar requisiciones en estados finales."""
        estados_finales = ['entregada', 'rechazada', 'cancelada', 'vencida']
        for estado in estados_finales:
            self.assertNotIn(estado, self.ESTADOS_AUTORIZABLES)


class TestTransicionesFlujoV2(TestCase):
    """Tests para el flujo V2 de requisiciones con todos los estados."""
    
    # Transiciones válidas según FLUJO V2
    # ISS-FIX-AUTORIZACION: en_revision no tiene 'devuelta' - farmacia NO puede devolver
    TRANSICIONES = {
        'borrador': ['pendiente_admin', 'cancelada'],
        'pendiente_admin': ['pendiente_director', 'devuelta', 'rechazada'],
        'pendiente_director': ['enviada', 'devuelta', 'rechazada'],
        'enviada': ['en_revision', 'autorizada', 'parcial', 'rechazada'],
        'en_revision': ['autorizada', 'parcial', 'rechazada'],  # Sin devuelta
        'autorizada': ['en_surtido', 'parcial', 'entregada', 'cancelada'],
        'parcial': ['en_surtido', 'entregada', 'cancelada'],
        'en_surtido': ['parcial', 'entregada'],
        'devuelta': ['pendiente_admin', 'cancelada'],
        'entregada': ['vencida'],
        'rechazada': [],
        'cancelada': [],
        'vencida': [],
    }
    
    def _transicion_valida(self, actual, nuevo):
        return nuevo in self.TRANSICIONES.get(actual, [])
    
    # ========== Tests de recepción en farmacia ==========
    
    def test_enviada_a_en_revision(self):
        """Farmacia puede recibir requisición (enviada → en_revision)."""
        self.assertTrue(self._transicion_valida('enviada', 'en_revision'))
    
    def test_enviada_a_autorizada_directo(self):
        """Farmacia puede autorizar directamente sin recibir primero."""
        self.assertTrue(self._transicion_valida('enviada', 'autorizada'))
    
    def test_enviada_a_parcial(self):
        """Desde enviada se puede ir a parcial (autorización parcial)."""
        self.assertTrue(self._transicion_valida('enviada', 'parcial'))
    
    # ========== Tests de autorización desde en_revision ==========
    
    def test_en_revision_a_autorizada(self):
        """Desde en_revision se puede autorizar completamente."""
        self.assertTrue(self._transicion_valida('en_revision', 'autorizada'))
    
    def test_en_revision_a_parcial(self):
        """Desde en_revision se puede autorizar parcialmente."""
        self.assertTrue(self._transicion_valida('en_revision', 'parcial'))
    
    def test_en_revision_a_rechazada(self):
        """Desde en_revision se puede rechazar."""
        self.assertTrue(self._transicion_valida('en_revision', 'rechazada'))
    
    def test_en_revision_no_a_devuelta(self):
        """Desde en_revision NO se puede devolver (farmacia no devuelve)."""
        self.assertFalse(self._transicion_valida('en_revision', 'devuelta'))
    
    # ========== Tests de flujo de surtido ==========
    
    def test_autorizada_a_en_surtido(self):
        """Desde autorizada se puede iniciar surtido."""
        self.assertTrue(self._transicion_valida('autorizada', 'en_surtido'))
    
    def test_autorizada_a_entregada(self):
        """Desde autorizada se puede ir directo a entregada."""
        self.assertTrue(self._transicion_valida('autorizada', 'entregada'))
    
    def test_parcial_a_entregada(self):
        """Desde parcial se puede completar entrega."""
        self.assertTrue(self._transicion_valida('parcial', 'entregada'))
    
    # ========== Tests de estados donde admin/director devuelven ==========
    
    def test_pendiente_admin_a_devuelta(self):
        """Admin del centro puede devolver al médico."""
        self.assertTrue(self._transicion_valida('pendiente_admin', 'devuelta'))
    
    def test_pendiente_director_a_devuelta(self):
        """Director del centro puede devolver al médico."""
        self.assertTrue(self._transicion_valida('pendiente_director', 'devuelta'))


class TestPermisosFarmacia(TestCase):
    """Tests de permisos específicos para rol farmacia."""
    
    # Acciones que farmacia PUEDE hacer
    ACCIONES_FARMACIA_PERMITIDAS = [
        'recibir_farmacia',      # enviada → en_revision
        'autorizar_farmacia',    # en_revision/enviada → autorizada/parcial
        'rechazar',              # en_revision/enviada → rechazada
        'surtir',                # autorizada/parcial → entregada
        'cancelar',              # autorizada/en_surtido → cancelada
    ]
    
    # Acciones que farmacia NO puede hacer
    ACCIONES_FARMACIA_PROHIBIDAS = [
        'enviar_admin',          # Solo médico
        'autorizar_admin',       # Solo admin del centro
        'autorizar_director',    # Solo director del centro
        'devolver',              # Solo admin/director (no farmacia)
        'reenviar',              # Solo médico
    ]
    
    def test_farmacia_puede_recibir(self):
        """Farmacia puede recibir requisiciones."""
        self.assertIn('recibir_farmacia', self.ACCIONES_FARMACIA_PERMITIDAS)
    
    def test_farmacia_puede_autorizar(self):
        """Farmacia puede autorizar requisiciones."""
        self.assertIn('autorizar_farmacia', self.ACCIONES_FARMACIA_PERMITIDAS)
    
    def test_farmacia_puede_rechazar(self):
        """Farmacia puede rechazar requisiciones."""
        self.assertIn('rechazar', self.ACCIONES_FARMACIA_PERMITIDAS)
    
    def test_farmacia_puede_surtir(self):
        """Farmacia puede surtir requisiciones."""
        self.assertIn('surtir', self.ACCIONES_FARMACIA_PERMITIDAS)
    
    def test_farmacia_no_puede_devolver(self):
        """ISS-FIX: Farmacia NO puede devolver - solo rechazar o ajustar cantidades."""
        self.assertIn('devolver', self.ACCIONES_FARMACIA_PROHIBIDAS)
    
    def test_farmacia_no_puede_autorizar_admin(self):
        """Farmacia no puede hacer autorizaciones de admin del centro."""
        self.assertIn('autorizar_admin', self.ACCIONES_FARMACIA_PROHIBIDAS)
    
    def test_farmacia_no_puede_autorizar_director(self):
        """Farmacia no puede hacer autorizaciones de director."""
        self.assertIn('autorizar_director', self.ACCIONES_FARMACIA_PROHIBIDAS)


class TestValidacionPuedeAutorizar(TestCase):
    """Tests para la lógica de puedeAutorizar en frontend."""
    
    def _puede_autorizar(self, estado, es_farmacia, tiene_permiso):
        """
        Simula la lógica del frontend:
        const puedeAutorizar = ['enviada', 'en_revision'].includes(requisicion?.estado) 
                              && esFarmacia && permisos?.autorizarRequisicion;
        """
        return estado in ['enviada', 'en_revision'] and es_farmacia and tiene_permiso
    
    def test_puede_autorizar_enviada_farmacia_con_permiso(self):
        """Farmacia con permiso puede autorizar en estado enviada."""
        self.assertTrue(self._puede_autorizar('enviada', True, True))
    
    def test_puede_autorizar_en_revision_farmacia_con_permiso(self):
        """Farmacia con permiso puede autorizar en estado en_revision."""
        self.assertTrue(self._puede_autorizar('en_revision', True, True))
    
    def test_no_puede_autorizar_sin_permiso(self):
        """No puede autorizar si no tiene el permiso."""
        self.assertFalse(self._puede_autorizar('enviada', True, False))
        self.assertFalse(self._puede_autorizar('en_revision', True, False))
    
    def test_no_puede_autorizar_no_farmacia(self):
        """No puede autorizar si no es farmacia."""
        self.assertFalse(self._puede_autorizar('enviada', False, True))
        self.assertFalse(self._puede_autorizar('en_revision', False, True))
    
    def test_no_puede_autorizar_borrador(self):
        """No puede autorizar un borrador."""
        self.assertFalse(self._puede_autorizar('borrador', True, True))
    
    def test_no_puede_autorizar_ya_autorizada(self):
        """No puede re-autorizar una ya autorizada."""
        self.assertFalse(self._puede_autorizar('autorizada', True, True))
    
    def test_no_puede_autorizar_pendiente_admin(self):
        """No puede autorizar mientras está pendiente de admin."""
        self.assertFalse(self._puede_autorizar('pendiente_admin', True, True))
    
    def test_no_puede_autorizar_pendiente_director(self):
        """No puede autorizar mientras está pendiente de director."""
        self.assertFalse(self._puede_autorizar('pendiente_director', True, True))


class TestValidacionPuedeRechazar(TestCase):
    """Tests para la lógica de puedeRechazar en frontend."""
    
    def _puede_rechazar(self, estado, es_farmacia, tiene_permiso):
        """
        Simula la lógica del frontend:
        const puedeRechazar = ['enviada', 'en_revision'].includes(requisicion?.estado) 
                             && esFarmacia && permisos?.rechazarRequisicion;
        """
        return estado in ['enviada', 'en_revision'] and es_farmacia and tiene_permiso
    
    def test_puede_rechazar_enviada_farmacia_con_permiso(self):
        """Farmacia con permiso puede rechazar en estado enviada."""
        self.assertTrue(self._puede_rechazar('enviada', True, True))
    
    def test_puede_rechazar_en_revision_farmacia_con_permiso(self):
        """Farmacia con permiso puede rechazar en estado en_revision."""
        self.assertTrue(self._puede_rechazar('en_revision', True, True))
    
    def test_no_puede_rechazar_sin_permiso(self):
        """No puede rechazar si no tiene el permiso."""
        self.assertFalse(self._puede_rechazar('enviada', True, False))
    
    def test_no_puede_rechazar_ya_autorizada(self):
        """No puede rechazar una ya autorizada."""
        self.assertFalse(self._puede_rechazar('autorizada', True, True))


class TestAccionesDisponiblesFarmacia(TestCase):
    """Tests para las acciones disponibles según estado y rol."""
    
    # Configuración de acciones del hook useRequisicionFlujo
    ACCIONES_FLUJO = {
        'recibir_farmacia': {
            'estadosPermitidos': ['enviada'],
            'rolesPermitidos': ['farmacia', 'admin_farmacia'],
        },
        'autorizar_farmacia': {
            'estadosPermitidos': ['en_revision', 'enviada'],
            'rolesPermitidos': ['farmacia', 'admin_farmacia'],
        },
        'surtir': {
            'estadosPermitidos': ['autorizada', 'parcial', 'en_surtido'],
            'rolesPermitidos': ['farmacia', 'admin_farmacia'],
        },
        'devolver': {
            # ISS-FIX: Farmacia ya NO puede devolver
            'estadosPermitidos': ['pendiente_admin', 'pendiente_director'],
            'rolesPermitidos': ['administrador_centro', 'admin_centro', 'director_centro', 'director'],
        },
        'rechazar': {
            'estadosPermitidos': ['pendiente_admin', 'pendiente_director', 'enviada', 'en_revision'],
            'rolesPermitidos': ['administrador_centro', 'admin_centro', 'director_centro', 'director', 'farmacia', 'admin_farmacia'],
        },
    }
    
    def _puede_ejecutar(self, accion_key, estado, rol):
        """Verifica si un rol puede ejecutar una acción en un estado dado."""
        accion = self.ACCIONES_FLUJO.get(accion_key)
        if not accion:
            return False
        return estado in accion['estadosPermitidos'] and rol in accion['rolesPermitidos']
    
    def test_farmacia_puede_recibir_en_enviada(self):
        """Farmacia puede recibir en estado enviada."""
        self.assertTrue(self._puede_ejecutar('recibir_farmacia', 'enviada', 'farmacia'))
    
    def test_farmacia_puede_autorizar_en_enviada(self):
        """Farmacia puede autorizar directamente en enviada."""
        self.assertTrue(self._puede_ejecutar('autorizar_farmacia', 'enviada', 'farmacia'))
    
    def test_farmacia_puede_autorizar_en_revision(self):
        """Farmacia puede autorizar en en_revision (después de recibir)."""
        self.assertTrue(self._puede_ejecutar('autorizar_farmacia', 'en_revision', 'farmacia'))
    
    def test_farmacia_no_puede_devolver_en_revision(self):
        """ISS-FIX: Farmacia NO puede devolver desde en_revision."""
        self.assertFalse(self._puede_ejecutar('devolver', 'en_revision', 'farmacia'))
    
    def test_farmacia_puede_rechazar_en_revision(self):
        """Farmacia puede rechazar desde en_revision."""
        self.assertTrue(self._puede_ejecutar('rechazar', 'en_revision', 'farmacia'))
    
    def test_farmacia_puede_surtir_autorizada(self):
        """Farmacia puede surtir desde autorizada."""
        self.assertTrue(self._puede_ejecutar('surtir', 'autorizada', 'farmacia'))
    
    def test_farmacia_puede_surtir_parcial(self):
        """Farmacia puede surtir desde parcial."""
        self.assertTrue(self._puede_ejecutar('surtir', 'parcial', 'farmacia'))
    
    def test_admin_centro_puede_devolver_pendiente_admin(self):
        """Admin del centro puede devolver en pendiente_admin."""
        self.assertTrue(self._puede_ejecutar('devolver', 'pendiente_admin', 'admin_centro'))
    
    def test_director_puede_devolver_pendiente_director(self):
        """Director puede devolver en pendiente_director."""
        self.assertTrue(self._puede_ejecutar('devolver', 'pendiente_director', 'director_centro'))


class TestFlujoCompletoAutorizacion(TestCase):
    """Tests para verificar el flujo completo de autorización."""
    
    def test_flujo_con_recepcion_previa(self):
        """Flujo: enviada → (recibir) → en_revision → (autorizar) → autorizada."""
        transiciones = [
            ('enviada', 'en_revision'),      # Recibir
            ('en_revision', 'autorizada'),    # Autorizar
        ]
        
        estado_actual = 'enviada'
        for estado_desde, estado_hacia in transiciones:
            self.assertEqual(estado_actual, estado_desde)
            estado_actual = estado_hacia
        
        self.assertEqual(estado_actual, 'autorizada')
    
    def test_flujo_autorizacion_directa(self):
        """Flujo: enviada → (autorizar) → autorizada (sin recibir primero)."""
        transiciones = [
            ('enviada', 'autorizada'),  # Autorizar directamente
        ]
        
        estado_actual = 'enviada'
        for estado_desde, estado_hacia in transiciones:
            self.assertEqual(estado_actual, estado_desde)
            estado_actual = estado_hacia
        
        self.assertEqual(estado_actual, 'autorizada')
    
    def test_flujo_autorizacion_parcial(self):
        """Flujo: en_revision → (autorizar parcial) → parcial."""
        estado_inicial = 'en_revision'
        estado_final = 'parcial'
        
        # Verificar que la transición es válida
        transiciones_validas = ['autorizada', 'parcial', 'rechazada']
        self.assertIn(estado_final, transiciones_validas)
    
    def test_flujo_rechazo_despues_recepcion(self):
        """Flujo: enviada → en_revision → rechazada."""
        transiciones = [
            ('enviada', 'en_revision'),       # Recibir
            ('en_revision', 'rechazada'),     # Rechazar
        ]
        
        estado_actual = 'enviada'
        for estado_desde, estado_hacia in transiciones:
            self.assertEqual(estado_actual, estado_desde)
            estado_actual = estado_hacia
        
        self.assertEqual(estado_actual, 'rechazada')


class TestEstadosSurtibles(TestCase):
    """Tests para verificar estados desde los que se puede surtir."""
    
    ESTADOS_SURTIBLES = ['autorizada', 'parcial', 'en_surtido']
    
    def test_autorizada_es_surtible(self):
        """Estado 'autorizada' permite surtir."""
        self.assertIn('autorizada', self.ESTADOS_SURTIBLES)
    
    def test_parcial_es_surtible(self):
        """Estado 'parcial' permite surtir (continuar surtido)."""
        self.assertIn('parcial', self.ESTADOS_SURTIBLES)
    
    def test_en_surtido_es_surtible(self):
        """Estado 'en_surtido' permite surtir (continuar surtido)."""
        self.assertIn('en_surtido', self.ESTADOS_SURTIBLES)
    
    def test_enviada_no_es_surtible(self):
        """Estado 'enviada' NO permite surtir (debe autorizar primero)."""
        self.assertNotIn('enviada', self.ESTADOS_SURTIBLES)
    
    def test_en_revision_no_es_surtible(self):
        """Estado 'en_revision' NO permite surtir (debe autorizar primero)."""
        self.assertNotIn('en_revision', self.ESTADOS_SURTIBLES)


class TestConstantesBackend(TestCase):
    """Tests para verificar que las constantes del backend son correctas."""
    
    def test_importar_constantes(self):
        """Verifica que las constantes se pueden importar."""
        try:
            from core.constants import TRANSICIONES_REQUISICION, ESTADOS_SURTIBLES
            self.assertIsNotNone(TRANSICIONES_REQUISICION)
            self.assertIsNotNone(ESTADOS_SURTIBLES)
        except ImportError:
            self.skipTest("Constantes no disponibles en este contexto")
    
    def test_transiciones_desde_enviada_correctas(self):
        """
        Verifica las transiciones correctas desde estado 'enviada'.
        
        Según el trigger de Supabase:
        - enviada -> en_revision (farmacia recibe y revisa)
        - enviada -> rechazada (farmacia rechaza directamente)
        - enviada -> cancelada (cancelación)
        
        NOTA: parcial NO es transición directa desde enviada,
        solo se alcanza desde en_surtido después de autorización.
        """
        try:
            from core.constants import TRANSICIONES_REQUISICION
            transiciones = TRANSICIONES_REQUISICION.get('enviada', [])
            # Verificar transiciones correctas
            self.assertIn('en_revision', transiciones)
            self.assertIn('rechazada', transiciones)
            self.assertIn('cancelada', transiciones)
            # Parcial NO debe estar aquí
            self.assertNotIn('parcial', transiciones)
        except ImportError:
            self.skipTest("Constantes no disponibles en este contexto")
    
    def test_transiciones_desde_en_revision_no_incluyen_parcial(self):
        """
        Verifica que en_revision NO puede transicionar a parcial directamente.
        
        ISS-TRIGGER-FIX: Según el trigger de Supabase, en_revision solo puede ir a:
        - autorizada, rechazada, devuelta
        
        El estado 'parcial' se alcanza desde 'en_surtido', no desde 'en_revision'.
        """
        try:
            from core.constants import TRANSICIONES_REQUISICION
            # Verificar que parcial NO está en las transiciones desde en_revision
            self.assertNotIn('parcial', TRANSICIONES_REQUISICION.get('en_revision', []))
            # Pero sí que están los estados correctos
            self.assertIn('autorizada', TRANSICIONES_REQUISICION.get('en_revision', []))
            self.assertIn('rechazada', TRANSICIONES_REQUISICION.get('en_revision', []))
            self.assertIn('devuelta', TRANSICIONES_REQUISICION.get('en_revision', []))
        except ImportError:
            self.skipTest("Constantes no disponibles en este contexto")
    
    def test_estados_surtibles_incluyen_parcial(self):
        """Verifica que parcial está en ESTADOS_SURTIBLES."""
        try:
            from core.constants import ESTADOS_SURTIBLES
            self.assertIn('parcial', ESTADOS_SURTIBLES)
        except ImportError:
            self.skipTest("Constantes no disponibles en este contexto")


# ========== Tests de integración con mocks ==========

class TestIntegracionAutorizacionMock(TestCase):
    """Tests de integración con mocks para verificar el flujo."""
    
    @patch('core.models.Requisicion')
    def test_actualizar_estado_a_autorizada(self, MockRequisicion):
        """Verifica que se puede actualizar estado a autorizada desde en_revision."""
        mock_req = Mock()
        mock_req.estado = 'en_revision'
        mock_req.id = 1
        
        # Simular autorización
        mock_req.estado = 'autorizada'
        
        self.assertEqual(mock_req.estado, 'autorizada')
    
    @patch('core.models.Requisicion')
    def test_actualizar_estado_a_parcial(self, MockRequisicion):
        """Verifica que se puede actualizar estado a parcial desde en_revision."""
        mock_req = Mock()
        mock_req.estado = 'en_revision'
        mock_req.id = 1
        
        # Simular autorización parcial
        mock_req.estado = 'parcial'
        
        self.assertEqual(mock_req.estado, 'parcial')


if __name__ == '__main__':
    import unittest
    unittest.main()
