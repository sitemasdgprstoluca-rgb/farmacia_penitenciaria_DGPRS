"""
FLUJO V2: Tests de integración para el flujo de requisiciones.

NOTA: Estos tests requieren la base de datos de producción/staging
ya que los modelos tienen managed=False (Supabase).

Para ejecutar:
    pytest inventario/tests/test_flujo_v2.py -v --ds=config.settings_test

Prueba el flujo completo:
1. Médico crea requisición (borrador)
2. Médico envía a Admin (pendiente_admin)
3. Admin autoriza (pendiente_director)
4. Director autoriza (enviada)
5. Farmacia recibe (en_revision)
6. Farmacia autoriza con fecha límite (autorizada)
7. Farmacia surte (surtida)
8. Centro confirma entrega (entregada)

También prueba flujos alternativos:
- Devolución y reenvío
- Rechazo en diferentes etapas
- Vencimiento por fecha límite
"""

import pytest
from datetime import timedelta
from django.utils import timezone
from unittest.mock import Mock, patch, MagicMock

from core.constants import (
    TRANSICIONES_REQUISICION,
    PERMISOS_FLUJO_REQUISICION,
    ESTADOS_REQUISICION,
)


class TestTransicionesConstantes:
    """Tests de las constantes de transiciones."""
    
    def test_estados_definidos(self):
        """Verifica que todos los estados están definidos."""
        estados_esperados = [
            'borrador', 'pendiente_admin', 'pendiente_director',
            'enviada', 'en_revision', 'autorizada', 'en_surtido',
            'surtida', 'entregada', 'rechazada', 'vencida', 'cancelada', 'devuelta'
        ]
        estados_definidos = [e[0] for e in ESTADOS_REQUISICION]
        for estado in estados_esperados:
            assert estado in estados_definidos, f"Estado '{estado}' no definido"
    
    def test_transiciones_borrador(self):
        """Desde borrador solo puede ir a pendiente_admin o cancelada."""
        transiciones = TRANSICIONES_REQUISICION.get('borrador', [])
        assert 'pendiente_admin' in transiciones
        assert 'cancelada' in transiciones
        assert 'enviada' not in transiciones  # No puede saltar directo a farmacia
    
    def test_transiciones_pendiente_admin(self):
        """Desde pendiente_admin puede ir a pendiente_director, rechazada o devuelta."""
        transiciones = TRANSICIONES_REQUISICION.get('pendiente_admin', [])
        assert 'pendiente_director' in transiciones
        assert 'rechazada' in transiciones
        assert 'devuelta' in transiciones
    
    def test_transiciones_pendiente_director(self):
        """Desde pendiente_director puede ir a enviada, rechazada o devuelta."""
        transiciones = TRANSICIONES_REQUISICION.get('pendiente_director', [])
        assert 'enviada' in transiciones
        assert 'rechazada' in transiciones
        assert 'devuelta' in transiciones
    
    def test_transiciones_enviada(self):
        """Desde enviada puede ir a en_revision, autorizada o rechazada."""
        transiciones = TRANSICIONES_REQUISICION.get('enviada', [])
        assert 'en_revision' in transiciones
        assert 'autorizada' in transiciones
        assert 'rechazada' in transiciones
    
    def test_transiciones_surtida(self):
        """Desde surtida puede ir a entregada o vencida."""
        transiciones = TRANSICIONES_REQUISICION.get('surtida', [])
        assert 'entregada' in transiciones
        assert 'vencida' in transiciones
    
    def test_estados_finales_no_tienen_transiciones(self):
        """Estados finales no pueden cambiar."""
        estados_finales = ['entregada', 'rechazada', 'vencida', 'cancelada']
        for estado in estados_finales:
            transiciones = TRANSICIONES_REQUISICION.get(estado, [])
            assert len(transiciones) == 0, f"Estado final '{estado}' tiene transiciones: {transiciones}"
    
    def test_devuelta_puede_reenviar(self):
        """Desde devuelta puede volver a borrador para que médico corrija."""
        transiciones = TRANSICIONES_REQUISICION.get('devuelta', [])
        assert 'borrador' in transiciones
        assert 'cancelada' in transiciones


class TestPermisosFlujo:
    """Tests de permisos por rol."""
    
    def test_medico_puede_crear(self):
        """Médico puede crear requisiciones."""
        permisos = PERMISOS_FLUJO_REQUISICION.get('medico', {})
        assert permisos.get('puede_crear') is True
    
    def test_medico_puede_enviar_admin(self):
        """Médico puede enviar a admin."""
        permisos = PERMISOS_FLUJO_REQUISICION.get('medico', {})
        assert permisos.get('puede_enviar_admin') is True
    
    def test_medico_no_puede_autorizar(self):
        """Médico no puede autorizar."""
        permisos = PERMISOS_FLUJO_REQUISICION.get('medico', {})
        assert permisos.get('puede_autorizar_admin') is False
        assert permisos.get('puede_autorizar_director') is False
        assert permisos.get('puede_autorizar_farmacia') is False
    
    def test_admin_centro_puede_autorizar_admin(self):
        """Administrador del centro puede autorizar como admin."""
        permisos = PERMISOS_FLUJO_REQUISICION.get('administrador_centro', {})
        assert permisos.get('puede_autorizar_admin') is True
    
    def test_admin_centro_no_puede_autorizar_director(self):
        """Administrador del centro no puede autorizar como director."""
        permisos = PERMISOS_FLUJO_REQUISICION.get('administrador_centro', {})
        assert permisos.get('puede_autorizar_director') is False
    
    def test_director_puede_autorizar_director(self):
        """Director puede autorizar como director."""
        permisos = PERMISOS_FLUJO_REQUISICION.get('director_centro', {})
        assert permisos.get('puede_autorizar_director') is True
    
    def test_farmacia_puede_recibir_y_autorizar(self):
        """Farmacia puede recibir, autorizar y surtir."""
        permisos = PERMISOS_FLUJO_REQUISICION.get('farmacia', {})
        assert permisos.get('puede_recibir_farmacia') is True
        assert permisos.get('puede_autorizar_farmacia') is True
        assert permisos.get('puede_surtir') is True
    
    def test_farmacia_no_puede_crear(self):
        """Farmacia no puede crear requisiciones."""
        permisos = PERMISOS_FLUJO_REQUISICION.get('farmacia', {})
        assert permisos.get('puede_crear') is False
    
    def test_roles_centro_pueden_confirmar_entrega(self):
        """Todos los roles del centro pueden confirmar entrega."""
        for rol in ['medico', 'administrador_centro', 'director_centro']:
            permisos = PERMISOS_FLUJO_REQUISICION.get(rol, {})
            assert permisos.get('puede_confirmar_entrega') is True, f"{rol} debería poder confirmar entrega"


class TestValidadorTransiciones:
    """Tests del validador de transiciones."""
    
    def test_transicion_valida(self):
        """Verifica transiciones válidas."""
        def validar_transicion(estado_actual, estado_nuevo):
            transiciones = TRANSICIONES_REQUISICION.get(estado_actual, [])
            return estado_nuevo in transiciones
        
        # Transiciones válidas
        assert validar_transicion('borrador', 'pendiente_admin') is True
        assert validar_transicion('pendiente_admin', 'pendiente_director') is True
        assert validar_transicion('pendiente_director', 'enviada') is True
        assert validar_transicion('surtida', 'entregada') is True
    
    def test_transicion_invalida(self):
        """Verifica que transiciones inválidas sean rechazadas."""
        def validar_transicion(estado_actual, estado_nuevo):
            transiciones = TRANSICIONES_REQUISICION.get(estado_actual, [])
            return estado_nuevo in transiciones
        
        # Transiciones inválidas
        assert validar_transicion('borrador', 'enviada') is False  # Salta pasos
        assert validar_transicion('borrador', 'surtida') is False
        assert validar_transicion('entregada', 'borrador') is False  # Estado final
        assert validar_transicion('cancelada', 'enviada') is False  # Estado final


class TestFlujoSimulado:
    """Tests del flujo usando mocks."""
    
    def test_flujo_completo_estados(self):
        """Simula el flujo completo verificando los estados."""
        flujo = [
            ('borrador', 'pendiente_admin'),
            ('pendiente_admin', 'pendiente_director'),
            ('pendiente_director', 'enviada'),
            ('enviada', 'en_revision'),
            ('en_revision', 'autorizada'),
            ('autorizada', 'surtida'),
            ('surtida', 'entregada'),
        ]
        
        estado_actual = 'borrador'
        for estado_desde, estado_hasta in flujo:
            assert estado_actual == estado_desde
            transiciones = TRANSICIONES_REQUISICION.get(estado_actual, [])
            assert estado_hasta in transiciones, f"Transición {estado_desde} → {estado_hasta} no válida"
            estado_actual = estado_hasta
        
        assert estado_actual == 'entregada'
    
    def test_flujo_con_devolucion(self):
        """Simula flujo con devolución: admin devuelve → médico corrige en borrador → reinicia ciclo."""
        flujo = [
            ('borrador', 'pendiente_admin'),
            ('pendiente_admin', 'devuelta'),  # Admin devuelve
            ('devuelta', 'borrador'),  # Regresa a borrador para corrección
            ('borrador', 'pendiente_admin'),  # Médico reenvía corregido
            ('pendiente_admin', 'pendiente_director'),
            ('pendiente_director', 'enviada'),
        ]
        
        estado_actual = 'borrador'
        for estado_desde, estado_hasta in flujo:
            assert estado_actual == estado_desde
            transiciones = TRANSICIONES_REQUISICION.get(estado_actual, [])
            assert estado_hasta in transiciones
            estado_actual = estado_hasta
    
    def test_flujo_vencimiento(self):
        """Simula vencimiento cuando no se recoge a tiempo."""
        flujo = [
            ('borrador', 'pendiente_admin'),
            ('pendiente_admin', 'pendiente_director'),
            ('pendiente_director', 'enviada'),
            ('enviada', 'autorizada'),  # Farmacia puede autorizar directo
            ('autorizada', 'surtida'),
            ('surtida', 'vencida'),  # No se recogió a tiempo
        ]
        
        estado_actual = 'borrador'
        for estado_desde, estado_hasta in flujo:
            assert estado_actual == estado_desde
            transiciones = TRANSICIONES_REQUISICION.get(estado_actual, [])
            assert estado_hasta in transiciones
            estado_actual = estado_hasta
        
        assert estado_actual == 'vencida'
        # Verificar que es estado final
        assert len(TRANSICIONES_REQUISICION.get('vencida', [])) == 0


# Marcamos tests que requieren DB como skip por ahora
@pytest.mark.skip(reason="Requiere base de datos Supabase - ejecutar manualmente")
class TestIntegracionDB:
    """
    Tests de integración que requieren la base de datos real.
    
    Para ejecutar estos tests, configurar conexión a Supabase
    y usar: pytest -k TestIntegracionDB --runslow
    """
    
    @pytest.mark.django_db
    def test_crear_requisicion(self):
        """Test de creación de requisición en DB."""
        pass
    
    @pytest.mark.django_db
    def test_transicion_estado_real(self):
        """Test de transición de estado real en DB."""
        pass

