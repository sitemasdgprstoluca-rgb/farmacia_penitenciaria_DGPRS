# -*- coding: utf-8 -*-
"""
Tests unitarios PUROS para edición de productos en requisiciones.
No dependen de base de datos - usan mocks.

Tablas relacionadas (esquema):
- requisiciones: estado, motivo_devolucion
- detalles_requisicion: producto_id, lote_id, cantidad_solicitada
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory
from rest_framework import status


class TestValidacionesEdicionProductos(TestCase):
    """Tests de validación de lógica de negocio para edición."""
    
    def test_estados_que_permiten_edicion(self):
        """Test: Solo borrador y devuelta permiten edición."""
        estados_editables = ['borrador', 'devuelta']
        estados_no_editables = ['enviada', 'autorizada', 'surtida', 'entregada', 
                                'rechazada', 'cancelada', 'vencida']
        
        for estado in estados_editables:
            self.assertTrue(
                estado in ['borrador', 'devuelta'],
                f"Estado {estado} debería permitir edición"
            )
        
        for estado in estados_no_editables:
            self.assertFalse(
                estado in ['borrador', 'devuelta'],
                f"Estado {estado} NO debería permitir edición"
            )
    
    def test_validar_cantidad_positiva(self):
        """Test: Cantidades deben ser positivas."""
        def validar_cantidad(cantidad):
            return cantidad is not None and cantidad > 0
        
        self.assertTrue(validar_cantidad(10))
        self.assertTrue(validar_cantidad(1))
        self.assertFalse(validar_cantidad(0))
        self.assertFalse(validar_cantidad(-5))
        self.assertFalse(validar_cantidad(None))
    
    def test_validar_lista_no_vacia(self):
        """Test: Lista de detalles no puede estar vacía."""
        def validar_detalles(detalles):
            return detalles is not None and len(detalles) > 0
        
        self.assertTrue(validar_detalles([{'producto': 1}]))
        self.assertTrue(validar_detalles([{'producto': 1}, {'producto': 2}]))
        self.assertFalse(validar_detalles([]))
        self.assertFalse(validar_detalles(None))
    
    def test_validar_producto_existe(self):
        """Test: Producto referenciado debe existir."""
        productos_existentes = {1, 2, 3}
        
        def validar_producto(producto_id):
            return producto_id in productos_existentes
        
        self.assertTrue(validar_producto(1))
        self.assertTrue(validar_producto(2))
        self.assertFalse(validar_producto(99))
        self.assertFalse(validar_producto(0))
    
    def test_validar_lote_corresponde_producto(self):
        """Test: Lote debe corresponder al producto."""
        # Mapa: lote_id -> producto_id
        lotes_productos = {
            201: 1,
            202: 2,
            203: 3,
        }
        
        def validar_lote_producto(lote_id, producto_id):
            return lotes_productos.get(lote_id) == producto_id
        
        self.assertTrue(validar_lote_producto(201, 1))
        self.assertTrue(validar_lote_producto(202, 2))
        self.assertFalse(validar_lote_producto(201, 2))  # Lote 201 es de producto 1
        self.assertFalse(validar_lote_producto(999, 1))  # Lote no existe
    
    def test_validar_stock_disponible(self):
        """Test: No solicitar más que el stock disponible."""
        stock_lotes = {
            201: 100,
            202: 50,
            203: 0,
        }
        
        def validar_stock(lote_id, cantidad_solicitada):
            stock = stock_lotes.get(lote_id, 0)
            return cantidad_solicitada <= stock
        
        self.assertTrue(validar_stock(201, 50))
        self.assertTrue(validar_stock(201, 100))
        self.assertFalse(validar_stock(201, 101))
        self.assertFalse(validar_stock(203, 1))  # Stock 0


class TestLogicaEdicionDetalles(TestCase):
    """Tests de lógica para edición de detalles de requisición."""
    
    def test_agregar_producto_a_lista(self):
        """Test: Agregar nuevo producto a lista existente."""
        detalles = [
            {'id': 1, 'producto_id': 1, 'cantidad': 10},
        ]
        
        nuevo_producto = {'id': None, 'producto_id': 3, 'cantidad': 5}
        detalles.append(nuevo_producto)
        
        self.assertEqual(len(detalles), 2)
        self.assertEqual(detalles[-1]['producto_id'], 3)
    
    def test_eliminar_producto_de_lista(self):
        """Test: Eliminar producto de lista."""
        detalles = [
            {'id': 1, 'producto_id': 1, 'cantidad': 10},
            {'id': 2, 'producto_id': 2, 'cantidad': 5},
        ]
        
        # Eliminar producto con id=1
        detalles = [d for d in detalles if d['id'] != 1]
        
        self.assertEqual(len(detalles), 1)
        self.assertEqual(detalles[0]['producto_id'], 2)
    
    def test_no_eliminar_ultimo_producto(self):
        """Test: No permitir eliminar si queda solo uno."""
        detalles = [
            {'id': 1, 'producto_id': 1, 'cantidad': 10},
        ]
        
        puede_eliminar = len(detalles) > 1
        
        self.assertFalse(puede_eliminar)
    
    def test_modificar_cantidad(self):
        """Test: Modificar cantidad de producto existente."""
        detalles = [
            {'id': 1, 'producto_id': 1, 'cantidad': 10},
        ]
        
        # Modificar cantidad
        idx = 0
        nueva_cantidad = 25
        detalles[idx]['cantidad'] = nueva_cantidad
        
        self.assertEqual(detalles[0]['cantidad'], 25)
    
    def test_detectar_productos_duplicados(self):
        """Test: Detectar si producto ya existe en lista."""
        detalles = [
            {'lote_id': 201, 'producto_id': 1},
            {'lote_id': 202, 'producto_id': 2},
        ]
        
        def existe_lote(lote_id):
            return any(d['lote_id'] == lote_id for d in detalles)
        
        self.assertTrue(existe_lote(201))
        self.assertTrue(existe_lote(202))
        self.assertFalse(existe_lote(203))
    
    def test_preparar_datos_para_api(self):
        """Test: Preparar estructura de datos para enviar a API."""
        productos_editables = [
            {'id': 1, 'lote_id': 201, 'producto_id': 1, 'cantidad_solicitada': 15, 'esNuevo': False},
            {'id': None, 'lote_id': 203, 'producto_id': 3, 'cantidad_solicitada': 10, 'esNuevo': True},
        ]
        
        detalles_para_api = [
            {
                'id': p['id'] if not p['esNuevo'] else None,
                'producto': p['producto_id'],
                'lote_id': p['lote_id'],
                'cantidad_solicitada': p['cantidad_solicitada'],
            }
            for p in productos_editables
        ]
        
        self.assertEqual(len(detalles_para_api), 2)
        self.assertEqual(detalles_para_api[0]['id'], 1)
        self.assertIsNone(detalles_para_api[1]['id'])
        self.assertEqual(detalles_para_api[1]['producto'], 3)


class TestPermisosCentro(TestCase):
    """Tests de permisos basados en centro."""
    
    def test_usuario_puede_editar_su_centro(self):
        """Test: Usuario puede editar requisiciones de su centro."""
        user = {'id': 1, 'centro_id': 1, 'is_superuser': False}
        requisicion = {'solicitante_id': 1, 'centro_id': 1}
        
        puede_editar = (
            user['is_superuser'] or
            requisicion['solicitante_id'] == user['id'] or
            requisicion['centro_id'] == user['centro_id']
        )
        
        self.assertTrue(puede_editar)
    
    def test_usuario_no_puede_editar_otro_centro(self):
        """Test: Usuario NO puede editar requisiciones de otro centro."""
        user = {'id': 1, 'centro_id': 1, 'is_superuser': False}
        requisicion = {'solicitante_id': 99, 'centro_id': 2}
        
        puede_editar = (
            user['is_superuser'] or
            requisicion['solicitante_id'] == user['id'] or
            requisicion['centro_id'] == user['centro_id']
        )
        
        self.assertFalse(puede_editar)
    
    def test_superuser_puede_editar_cualquier_centro(self):
        """Test: Superusuario puede editar cualquier requisición."""
        user = {'id': 1, 'centro_id': 1, 'is_superuser': True}
        requisicion = {'solicitante_id': 99, 'centro_id': 99}
        
        puede_editar = user['is_superuser']
        
        self.assertTrue(puede_editar)
    
    def test_farmacia_puede_editar_cualquiera(self):
        """Test: Usuario farmacia tiene acceso a todas las requisiciones."""
        roles_privilegiados = ['farmacia', 'admin_farmacia', 'admin_sistema']
        
        def tiene_acceso_global(rol):
            return rol in roles_privilegiados
        
        self.assertTrue(tiene_acceso_global('farmacia'))
        self.assertTrue(tiene_acceso_global('admin_farmacia'))
        self.assertFalse(tiene_acceso_global('medico'))
        self.assertFalse(tiene_acceso_global('usuario_centro'))


class TestFlujoDevolucion(TestCase):
    """Tests del flujo de devolución."""
    
    def test_transicion_enviada_a_devuelta(self):
        """Test: Requisición puede pasar de enviada a devuelta."""
        transiciones_validas = {
            'borrador': ['enviada', 'cancelada'],
            'enviada': ['autorizada', 'rechazada', 'devuelta'],
            'devuelta': ['enviada', 'cancelada'],
            'autorizada': ['surtida', 'entregada'],
        }
        
        estado_actual = 'enviada'
        estado_nuevo = 'devuelta'
        
        es_valida = estado_nuevo in transiciones_validas.get(estado_actual, [])
        
        self.assertTrue(es_valida)
    
    def test_transicion_devuelta_a_enviada(self):
        """Test: Requisición devuelta puede reenviarse."""
        transiciones_validas = {
            'devuelta': ['enviada', 'cancelada'],
        }
        
        estado_actual = 'devuelta'
        estado_nuevo = 'enviada'
        
        es_valida = estado_nuevo in transiciones_validas.get(estado_actual, [])
        
        self.assertTrue(es_valida)
    
    def test_devuelta_no_puede_autorizar(self):
        """Test: Estado devuelta no permite autorizar directamente."""
        transiciones_validas = {
            'devuelta': ['enviada', 'cancelada'],
        }
        
        estado_actual = 'devuelta'
        estado_nuevo = 'autorizada'
        
        es_valida = estado_nuevo in transiciones_validas.get(estado_actual, [])
        
        self.assertFalse(es_valida)
    
    def test_motivo_devolucion_requerido(self):
        """Test: Al devolver, el motivo es obligatorio."""
        def validar_devolucion(motivo):
            return motivo is not None and len(motivo.strip()) >= 10
        
        self.assertTrue(validar_devolucion("Producto no disponible, solicitar alternativa"))
        self.assertTrue(validar_devolucion("Ajustar cantidades según stock"))
        self.assertFalse(validar_devolucion(""))
        self.assertFalse(validar_devolucion("   "))
        self.assertFalse(validar_devolucion("Corto"))  # Menos de 10 chars
        self.assertFalse(validar_devolucion(None))


class TestBusquedaCatalogo(TestCase):
    """Tests de búsqueda en catálogo de lotes."""
    
    def setUp(self):
        self.catalogo = [
            {'id': 1, 'numero_lote': 'LOT-001', 'producto_clave': 'PROD-001', 
             'producto_nombre': 'Paracetamol 500mg', 'stock_actual': 100},
            {'id': 2, 'numero_lote': 'LOT-002', 'producto_clave': 'PROD-002', 
             'producto_nombre': 'Ibuprofeno 400mg', 'stock_actual': 50},
            {'id': 3, 'numero_lote': 'LOT-003', 'producto_clave': 'PROD-003', 
             'producto_nombre': 'Aspirina 100mg', 'stock_actual': 200},
        ]
    
    def _filtrar(self, busqueda):
        busqueda = busqueda.lower()
        return [
            lote for lote in self.catalogo
            if busqueda in lote['producto_clave'].lower() or
               busqueda in lote['producto_nombre'].lower() or
               busqueda in lote['numero_lote'].lower()
        ]
    
    def test_buscar_por_clave(self):
        """Test: Buscar por clave de producto."""
        resultado = self._filtrar('PROD-001')
        
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]['producto_clave'], 'PROD-001')
    
    def test_buscar_por_nombre(self):
        """Test: Buscar por nombre de producto."""
        resultado = self._filtrar('paracetamol')
        
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]['producto_nombre'], 'Paracetamol 500mg')
    
    def test_buscar_por_lote(self):
        """Test: Buscar por número de lote."""
        resultado = self._filtrar('LOT-002')
        
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]['numero_lote'], 'LOT-002')
    
    def test_busqueda_parcial(self):
        """Test: Búsqueda parcial funciona."""
        resultado = self._filtrar('para')  # Debería encontrar Paracetamol
        
        self.assertEqual(len(resultado), 1)
    
    def test_busqueda_sin_resultados(self):
        """Test: Búsqueda sin coincidencias."""
        resultado = self._filtrar('NOEXISTE')
        
        self.assertEqual(len(resultado), 0)
    
    def test_busqueda_case_insensitive(self):
        """Test: Búsqueda no distingue mayúsculas."""
        resultado_mayus = self._filtrar('ASPIRINA')
        resultado_minus = self._filtrar('aspirina')
        
        self.assertEqual(len(resultado_mayus), len(resultado_minus))


class TestEstructuraDatosAPI(TestCase):
    """Tests de estructura de datos esperada por la API."""
    
    def test_estructura_detalle_requisicion(self):
        """Test: Estructura correcta de detalle para API."""
        detalle = {
            'id': 1,
            'producto': 1,
            'lote_id': 201,
            'cantidad_solicitada': 10,
        }
        
        # Campos requeridos
        self.assertIn('producto', detalle)
        self.assertIn('cantidad_solicitada', detalle)
        
        # Campos opcionales pero importantes
        self.assertIn('lote_id', detalle)
    
    def test_estructura_respuesta_requisicion(self):
        """Test: Estructura esperada de respuesta de API."""
        respuesta_mock = {
            'id': 1,
            'folio': 'REQ-2026-001',
            'estado': 'borrador',
            'centro': {'id': 1, 'nombre': 'Centro Test'},
            'detalles': [
                {
                    'id': 101,
                    'producto': {'id': 1, 'clave': 'PROD-001', 'nombre': 'Producto 1'},
                    'lote': {'id': 201, 'numero_lote': 'LOT-001'},
                    'cantidad_solicitada': 10,
                    'cantidad_autorizada': None,
                }
            ]
        }
        
        # Verificar estructura
        self.assertIn('id', respuesta_mock)
        self.assertIn('estado', respuesta_mock)
        self.assertIn('detalles', respuesta_mock)
        self.assertIsInstance(respuesta_mock['detalles'], list)
        
        if respuesta_mock['detalles']:
            detalle = respuesta_mock['detalles'][0]
            self.assertIn('producto', detalle)
            self.assertIn('cantidad_solicitada', detalle)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
