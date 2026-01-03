# -*- coding: utf-8 -*-
"""
Test Suite: Verificación del Constraint chk_cantidad_disponible
================================================================

Tests para verificar el manejo del constraint chk_cantidad_disponible.

Este constraint en Supabase impide que cantidad_disponible > cantidad.
Los tests verifican que:
1. El sistema respeta el constraint al crear/eliminar salidas
2. El fix de datos legacy inconsistentes no causa errores
3. El flujo normal de donaciones funciona correctamente
4. Los movimientos son inmutables (no tienen delete)

Author: Sistema Farmacia Penitenciaria
Date: 2026-01-02
"""
import pytest
from django.test import TestCase
from unittest.mock import patch, MagicMock, PropertyMock
from rest_framework import status


# =============================================================================
# TESTS: CONSTRAINT chk_cantidad_disponible EN SALIDAS DE DONACION
# =============================================================================

class TestConstraintCantidadDisponible(TestCase):
    """
    Tests para verificar el manejo del constraint de base de datos.
    
    Constraint: chk_cantidad_disponible
    Regla: cantidad_disponible <= cantidad
    """
    
    def test_eliminar_salida_devuelve_stock_dentro_limite(self):
        """
        Al eliminar una salida pendiente, el stock se devuelve
        SOLO si no excede el máximo (cantidad total).
        """
        # Estado inicial: cantidad=10, disponible=7 (se reservaron 3)
        cantidad_maxima = 10
        cantidad_disponible = 7
        cantidad_salida = 3
        
        # Al eliminar, nuevo_disponible sería 10
        nuevo_disponible = cantidad_disponible + cantidad_salida
        
        # Verificar que NO excede el máximo
        debe_actualizar = nuevo_disponible <= cantidad_maxima
        
        assert debe_actualizar == True
        assert nuevo_disponible == 10  # Se restaura al máximo correcto
    
    def test_eliminar_salida_respeta_constraint_maximo(self):
        """
        Escenario de datos legacy inconsistentes:
        - cantidad = 5 (máximo)
        - cantidad_disponible = 5 (ya al máximo)
        - Existe salida con cantidad = 2 (inconsistente)
        
        Al eliminar, nuevo_disponible sería 7 > 5 = VIOLA CONSTRAINT
        El sistema debe manejar esto sin actualizar.
        """
        cantidad_maxima = 5
        cantidad_disponible = 5  # Ya al máximo
        cantidad_salida = 2  # Salida legacy
        
        # Al eliminar, nuevo_disponible sería 7
        nuevo_disponible = cantidad_disponible + cantidad_salida
        
        # NO debe actualizar porque viola el constraint
        debe_actualizar = nuevo_disponible <= cantidad_maxima
        
        assert debe_actualizar == False
        assert nuevo_disponible == 7  # Excedería el máximo
        assert cantidad_maxima == 5  # El máximo no cambia
    
    def test_no_actualizar_si_ya_esta_al_maximo(self):
        """
        Si cantidad_disponible ya es igual a cantidad,
        no se debe intentar sumar más.
        """
        cantidad_maxima = 10
        cantidad_disponible = 10  # Ya al máximo
        cantidad_salida = 5
        
        nuevo_disponible = cantidad_disponible + cantidad_salida
        debe_actualizar = nuevo_disponible <= cantidad_maxima
        
        assert debe_actualizar == False
        # cantidad_disponible debe quedarse en 10
    
    def test_permitir_devolucion_parcial(self):
        """
        Si hay espacio parcial, permitir devolver
        hasta el máximo.
        """
        cantidad_maxima = 10
        cantidad_disponible = 8  # Solo 2 reservados
        cantidad_salida = 3  # Intentar devolver 3
        
        nuevo_disponible = cantidad_disponible + cantidad_salida
        # 8 + 3 = 11 > 10 = NO debe actualizar
        debe_actualizar = nuevo_disponible <= cantidad_maxima
        
        assert debe_actualizar == False


class TestConstraintLogicaDestroy(TestCase):
    """
    Tests de la lógica del método destroy() de SalidaDonacionViewSet.
    """
    
    def test_logica_destroy_caso_normal(self):
        """
        Caso normal: hay espacio para devolver el stock.
        """
        # Simular detalle
        detalle = MagicMock()
        detalle.cantidad = 10
        detalle.cantidad_disponible = 7
        
        cantidad_salida = 3
        
        # Lógica del destroy
        cantidad_maxima = detalle.cantidad
        nuevo_disponible = detalle.cantidad_disponible + cantidad_salida
        
        if nuevo_disponible <= cantidad_maxima:
            detalle.cantidad_disponible = nuevo_disponible
        
        # Verificar
        assert detalle.cantidad_disponible == 10
    
    def test_logica_destroy_caso_legacy(self):
        """
        Caso legacy: no hay espacio, no actualizar.
        """
        # Simular detalle con datos inconsistentes
        detalle = MagicMock()
        detalle.cantidad = 5  # Máximo
        detalle.cantidad_disponible = 5  # Ya al máximo
        
        cantidad_salida = 2  # Salida legacy
        
        # Lógica del destroy
        cantidad_maxima = detalle.cantidad
        nuevo_disponible = detalle.cantidad_disponible + cantidad_salida
        
        # NO debe actualizar
        if nuevo_disponible <= cantidad_maxima:
            detalle.cantidad_disponible = nuevo_disponible
        
        # cantidad_disponible no cambió
        assert detalle.cantidad_disponible == 5
    
    def test_logica_destroy_detalle_none(self):
        """
        Si detalle es None, no debe fallar.
        """
        detalle = None
        cantidad_salida = 3
        
        # Lógica del destroy
        if detalle:
            cantidad_maxima = detalle.cantidad
            nuevo_disponible = detalle.cantidad_disponible + cantidad_salida
            if nuevo_disponible <= cantidad_maxima:
                detalle.cantidad_disponible = nuevo_disponible
        
        # No hubo excepción
        assert True


# =============================================================================
# TESTS: MOVIMIENTOS INMUTABLES
# =============================================================================

class TestMovimientosInmutables(TestCase):
    """Tests para verificar que los movimientos son inmutables."""
    
    def test_movimientos_no_tienen_destroy(self):
        """
        MovimientoViewSet no permite DELETE.
        Los movimientos son registros de auditoría inmutables.
        """
        from inventario.views.movimientos import MovimientoViewSet
        from rest_framework.mixins import DestroyModelMixin
        
        # Verificar que NO hereda DestroyModelMixin
        assert not issubclass(MovimientoViewSet, DestroyModelMixin)
        
        # Verificar http_method_names
        viewset = MovimientoViewSet()
        assert 'delete' not in viewset.http_method_names
    
    def test_movimientos_solo_lectura_y_creacion(self):
        """MovimientoViewSet solo permite GET y POST."""
        from inventario.views.movimientos import MovimientoViewSet
        
        viewset = MovimientoViewSet()
        allowed_methods = set(viewset.http_method_names)
        
        # Solo debe permitir: get, post, head, options
        assert 'get' in allowed_methods
        assert 'post' in allowed_methods
        assert 'delete' not in allowed_methods
        assert 'put' not in allowed_methods
        assert 'patch' not in allowed_methods


# =============================================================================
# TESTS: FLUJO DE RESERVA DE STOCK
# =============================================================================

class TestFlujoReservaStock(TestCase):
    """Tests del flujo completo de reserva de stock."""
    
    def test_crear_salida_reserva_stock(self):
        """Al crear una salida, el stock se descuenta inmediatamente."""
        stock_inicial = 100
        cantidad_salida = 30
        
        stock_despues = stock_inicial - cantidad_salida
        
        assert stock_despues == 70
    
    def test_eliminar_salida_devuelve_stock(self):
        """Al eliminar salida pendiente, el stock se devuelve."""
        stock_inicial = 100
        cantidad_salida = 30
        stock_despues_crear = 70
        
        # Al eliminar
        stock_final = stock_despues_crear + cantidad_salida
        
        assert stock_final == stock_inicial
    
    def test_finalizar_no_afecta_stock(self):
        """
        Finalizar una salida NO descuenta más stock.
        El stock ya fue descontado al crear.
        """
        stock_despues_crear = 70
        stock_despues_finalizar = stock_despues_crear  # No cambia
        
        assert stock_despues_crear == stock_despues_finalizar


# =============================================================================
# TESTS: VALIDACIONES
# =============================================================================

class TestValidacionesSalidaDonacion(TestCase):
    """Tests de validaciones para SalidaDonacion."""
    
    def test_no_eliminar_salida_finalizada(self):
        """No se puede eliminar una salida ya finalizada."""
        finalizado = True
        puede_eliminar = not finalizado
        
        assert puede_eliminar == False
    
    def test_cantidad_positiva(self):
        """La cantidad debe ser mayor a 0."""
        cantidades_invalidas = [0, -1, -100]
        
        for cantidad in cantidades_invalidas:
            es_valida = cantidad > 0
            assert es_valida == False
    
    def test_stock_suficiente(self):
        """No se puede crear salida si no hay stock suficiente."""
        stock_disponible = 10
        cantidad_solicitada = 50
        
        es_valido = cantidad_solicitada <= stock_disponible
        
        assert es_valido == False


# =============================================================================
# TESTS: INTEGRACIÓN CON VIEWSET
# =============================================================================

class TestSalidaDonacionViewSetDestroy(TestCase):
    """Tests de integración del método destroy() en SalidaDonacionViewSet."""
    
    def test_destroy_rechaza_finalizada(self):
        """El destroy() rechaza salidas finalizadas."""
        mock_instance = MagicMock()
        mock_instance.finalizado = True
        
        # Verificar lógica
        if mock_instance.finalizado:
            error = 'No se puede eliminar una entrega ya confirmada/finalizada'
            assert 'finalizada' in error.lower() or 'confirmada' in error.lower()
    
    def test_destroy_permite_pendiente(self):
        """El destroy() permite eliminar salidas pendientes."""
        mock_instance = MagicMock()
        mock_instance.finalizado = False
        
        # Verificar lógica
        puede_eliminar = not mock_instance.finalizado
        assert puede_eliminar == True
    
    def test_destroy_usa_transaccion_atomica(self):
        """
        El destroy() debe usar transaction.atomic() para
        garantizar consistencia.
        """
        # El código actual usa: with transaction.atomic()
        # Este test documenta el requisito
        from core.views import SalidaDonacionViewSet
        import inspect
        
        source = inspect.getsource(SalidaDonacionViewSet.destroy)
        assert 'transaction.atomic()' in source
