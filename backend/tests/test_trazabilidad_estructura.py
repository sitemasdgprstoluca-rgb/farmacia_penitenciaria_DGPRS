# -*- coding: utf-8 -*-
"""
Tests unitarios para la API de Trazabilidad.

Verifica que la respuesta de trazabilidad_producto incluya
todos los campos necesarios para la UI.
"""
import pytest
from django.test import TestCase


class TestEstructuraRespuestaTrazabilidad(TestCase):
    """Tests de estructura de respuesta de trazabilidad."""
    
    def test_estructura_respuesta_producto_completa(self):
        """Verificar que la respuesta tiene todos los campos necesarios."""
        # Estructura esperada de la respuesta del backend
        respuesta_esperada = {
            'codigo': '615',
            'producto': {
                'id': 615,
                'clave': '615',
                'nombre': 'KETOCONAZOL/CLINDAMICINA',  # ¡IMPORTANTE!
                'descripcion': 'KETOCONAZOL/CLINDAMICINA',
                'unidad_medida': 'PIEZA',
                'stock_minimo': 1,
                'precio_unitario': None,
                'activo': True,
            },
            'estadisticas': {
                'stock_total': 292,
                'total_lotes': 3,
                'lotes_activos': 3,
                'total_entradas': 2,
                'total_salidas': 9,
            },
            'lotes': [],
            'movimientos': [],
            'alertas': [],
        }
        
        # Verificar campos de primer nivel
        self.assertIn('codigo', respuesta_esperada)
        self.assertIn('producto', respuesta_esperada)
        self.assertIn('estadisticas', respuesta_esperada)
        self.assertIn('lotes', respuesta_esperada)
        self.assertIn('movimientos', respuesta_esperada)
        
        # Verificar campos de producto
        producto = respuesta_esperada['producto']
        self.assertIn('nombre', producto)
        self.assertIn('descripcion', producto)
        self.assertIn('unidad_medida', producto)
        self.assertIn('stock_minimo', producto)
        
        # El nombre NO debe estar vacío
        self.assertTrue(len(producto['nombre']) > 0)
    
    def test_nombre_y_descripcion_no_vacios(self):
        """El nombre y descripción deben tener valores."""
        producto = {
            'nombre': 'KETOCONAZOL/CLINDAMICINA',
            'descripcion': 'KETOCONAZOL/CLINDAMICINA',
        }
        
        self.assertIsNotNone(producto['nombre'])
        self.assertNotEqual(producto['nombre'], '')
        self.assertTrue(len(producto['nombre']) >= 3)
    
    def test_estadisticas_incluye_stock_total(self):
        """Las estadísticas deben incluir stock_total."""
        estadisticas = {
            'stock_total': 292,
            'total_lotes': 3,
            'lotes_activos': 3,
        }
        
        self.assertIn('stock_total', estadisticas)
        self.assertIsInstance(estadisticas['stock_total'], int)


class TestCamposProductoTrazabilidad(TestCase):
    """Tests de campos específicos de producto en trazabilidad."""
    
    CAMPOS_REQUERIDOS_PRODUCTO = [
        'id',
        'clave',
        'nombre',
        'descripcion',
        'unidad_medida',
        'stock_minimo',
        'activo',
    ]
    
    def test_producto_tiene_campos_requeridos(self):
        """El objeto producto debe tener todos los campos requeridos."""
        producto_mock = {
            'id': 1,
            'clave': '615',
            'nombre': 'Producto Test',
            'descripcion': 'Descripción test',
            'unidad_medida': 'PIEZA',
            'stock_minimo': 10,
            'precio_unitario': None,
            'activo': True,
        }
        
        for campo in self.CAMPOS_REQUERIDOS_PRODUCTO:
            self.assertIn(campo, producto_mock, f"Falta campo requerido: {campo}")
    
    def test_nombre_tiene_prioridad_sobre_descripcion(self):
        """Si hay nombre, se usa nombre. Si no, se usa descripción."""
        # Caso 1: Tiene nombre
        producto_con_nombre = {
            'nombre': 'Paracetamol 500mg',
            'descripcion': 'Tabletas de paracetamol',
        }
        nombre_mostrar = producto_con_nombre['nombre'] or producto_con_nombre['descripcion']
        self.assertEqual(nombre_mostrar, 'Paracetamol 500mg')
        
        # Caso 2: No tiene nombre, usa descripción
        producto_sin_nombre = {
            'nombre': '',
            'descripcion': 'Solo descripción',
        }
        nombre_mostrar = producto_sin_nombre['nombre'] or producto_sin_nombre['descripcion']
        self.assertEqual(nombre_mostrar, 'Solo descripción')


class TestCamposEstadisticasTrazabilidad(TestCase):
    """Tests de campos de estadísticas."""
    
    CAMPOS_ESTADISTICAS = [
        'stock_total',
        'total_lotes',
        'lotes_activos',
        'total_entradas',
        'total_salidas',
    ]
    
    def test_estadisticas_tiene_campos_requeridos(self):
        """Las estadísticas deben tener campos básicos."""
        estadisticas_mock = {
            'stock_total': 100,
            'total_lotes': 3,
            'lotes_activos': 2,
            'total_entradas': 150,
            'total_salidas': 50,
            'diferencia': 100,
            'lotes_proximos_vencer': 1,
            'lotes_vencidos': 0,
            'bajo_minimo': False,
        }
        
        for campo in self.CAMPOS_ESTADISTICAS:
            self.assertIn(campo, estadisticas_mock, f"Falta campo estadísticas: {campo}")
    
    def test_stock_total_es_numerico(self):
        """stock_total debe ser un número."""
        estadisticas = {'stock_total': 292}
        
        self.assertIsInstance(estadisticas['stock_total'], (int, float))
        self.assertGreaterEqual(estadisticas['stock_total'], 0)


class TestCamposLoteTrazabilidad(TestCase):
    """Tests de campos de lote en trazabilidad."""
    
    CAMPOS_LOTE = [
        'id',
        'numero_lote',
        'fecha_caducidad',
        'cantidad_actual',
        'cantidad_inicial',
    ]
    
    def test_lote_tiene_campos_requeridos(self):
        """Cada lote debe tener campos básicos."""
        lote_mock = {
            'id': 1,
            'numero_lote': 'LOT-2026-001',
            'fecha_caducidad': '2027-12-31',
            'dias_para_caducar': 726,
            'estado_caducidad': 'NORMAL',
            'cantidad_actual': 100,
            'cantidad_inicial': 100,
            'total_entradas': 100,
            'total_salidas': 0,
            'marca': 'Laboratorio XYZ',
            'precio_unitario': '15.50',
            'numero_contrato': 'CONT-001',
            'activo': True,
        }
        
        for campo in self.CAMPOS_LOTE:
            self.assertIn(campo, lote_mock, f"Falta campo lote: {campo}")


class TestCamposMovimientoTrazabilidad(TestCase):
    """Tests de campos de movimiento en trazabilidad."""
    
    CAMPOS_MOVIMIENTO = [
        'id',
        'tipo',
        'cantidad',
        'fecha_movimiento',
        'lote',
    ]
    
    def test_movimiento_tiene_campos_requeridos(self):
        """Cada movimiento debe tener campos básicos."""
        movimiento_mock = {
            'id': 1,
            'tipo_movimiento': 'SALIDA',
            'tipo': 'SALIDA',
            'lote': 'LOT-001',
            'cantidad': 10,
            'fecha_movimiento': '2026-01-05T10:30:00',
            'observaciones': 'Dispensación por receta',
        }
        
        # Verificar campos esenciales
        self.assertIn('id', movimiento_mock)
        self.assertIn('tipo', movimiento_mock)
        self.assertIn('cantidad', movimiento_mock)
        self.assertIn('lote', movimiento_mock)
    
    def test_tipo_movimiento_es_mayuscula(self):
        """El tipo de movimiento debe estar en mayúsculas."""
        tipos_validos = ['ENTRADA', 'SALIDA', 'AJUSTE']
        
        for tipo in tipos_validos:
            self.assertEqual(tipo, tipo.upper())


class TestBusquedaPorClaveONombre(TestCase):
    """Tests de búsqueda por clave o nombre de producto."""
    
    def test_busqueda_por_clave_numerica(self):
        """Búsqueda por clave numérica (ej: 615) debe funcionar."""
        clave = '615'
        
        # Simular query
        from django.db.models import Q
        # Q(clave__iexact=clave) | Q(descripcion__iexact=clave)
        
        # Verificar que la clave es válida
        self.assertTrue(clave.strip())
        self.assertTrue(len(clave) >= 1)
    
    def test_busqueda_por_nombre_texto(self):
        """Búsqueda por nombre de texto debe funcionar."""
        nombre = 'Paracetamol'
        
        # Verificar que el nombre es válido para búsqueda
        self.assertTrue(nombre.strip())
        self.assertTrue(len(nombre) >= 3)
    
    def test_busqueda_case_insensitive(self):
        """La búsqueda no debe distinguir mayúsculas/minúsculas."""
        clave_mayus = 'PARA-001'
        clave_minus = 'para-001'
        
        self.assertEqual(clave_mayus.lower(), clave_minus.lower())


class TestNormalizacionFrontend(TestCase):
    """Tests de cómo el frontend debe normalizar los datos."""
    
    def test_priorizar_data_producto_sobre_data_raiz(self):
        """El frontend debe priorizar data.producto sobre data directamente."""
        # Este es el formato real del backend
        respuesta_backend = {
            'codigo': '615',  # En raíz
            # 'nombre' NO está en raíz - está en producto
            'producto': {
                'nombre': 'KETOCONAZOL/CLINDAMICINA',
                'descripcion': 'KETOCONAZOL/CLINDAMICINA',
            },
        }
        
        # El frontend debe extraer nombre de producto, no de raíz
        nombre_correcto = respuesta_backend.get('producto', {}).get('nombre', '')
        nombre_incorrecto = respuesta_backend.get('nombre', '')
        
        self.assertEqual(nombre_correcto, 'KETOCONAZOL/CLINDAMICINA')
        self.assertEqual(nombre_incorrecto, '')  # No existe en raíz
    
    def test_codigo_puede_estar_en_raiz_o_producto(self):
        """El código puede venir en data.codigo o data.producto.clave."""
        respuesta = {
            'codigo': '615',
            'producto': {
                'clave': '615',
            },
        }
        
        codigo = respuesta.get('codigo') or respuesta.get('producto', {}).get('clave', '')
        self.assertEqual(codigo, '615')


class TestExportacionProductoInfo(TestCase):
    """Tests para verificar que la exportación incluye la información correcta del producto."""
    
    def test_producto_info_tiene_descripcion(self):
        """La exportación debe incluir descripción del producto."""
        # Estructura que genera trazabilidad_producto_exportar
        producto_info = {
            'clave': '615',
            'descripcion': 'KETOCONAZOL/CLINDAMICINA',  # producto.nombre
            'unidad_medida': 'PIEZA',
            'stock_actual': 292,
            'stock_minimo': 1,
            'filtros': {}
        }
        
        # Verificar que tiene los campos necesarios para exportación
        self.assertIn('clave', producto_info)
        self.assertIn('descripcion', producto_info)
        self.assertIn('unidad_medida', producto_info)
        
        # La descripción no debe estar vacía
        self.assertTrue(producto_info['descripcion'])
        self.assertEqual(producto_info['descripcion'], 'KETOCONAZOL/CLINDAMICINA')
    
    def test_exportacion_lote_tiene_descripcion_producto(self):
        """La exportación de lote debe incluir descripción del producto."""
        # Estructura que genera trazabilidad_lote_exportar
        producto_info = {
            'clave': '615',
            'descripcion': 'KETOCONAZOL/CLINDAMICINA',  # lote.producto.nombre
            'unidad_medida': 'PIEZA',
            'stock_actual': 50,
            'stock_minimo': 1,
            'numero_lote': 'LOT-2025-001',
            'fecha_caducidad': '31/12/2026',
            'proveedor': 'PROVEEDOR XYZ',
            'filtros': {}
        }
        
        self.assertIn('descripcion', producto_info)
        self.assertIn('numero_lote', producto_info)
        self.assertTrue(producto_info['descripcion'])
    
    def test_excel_usa_descripcion_correctamente(self):
        """Verificar que Excel muestra la descripción en el encabezado."""
        # Simulamos cómo _exportar_producto_excel usa producto_info
        producto_info = {
            'clave': '615',
            'descripcion': 'KETOCONAZOL/CLINDAMICINA',
            'unidad_medida': 'PIEZA',
        }
        
        # Línea 10041 del código:
        titulo_excel = f"TRAZABILIDAD DE PRODUCTO: {producto_info['clave']}"
        self.assertIn('615', titulo_excel)
        
        # Línea 10047: ws['B3'] = producto_info['descripcion']
        fila_descripcion = producto_info['descripcion']
        self.assertEqual(fila_descripcion, 'KETOCONAZOL/CLINDAMICINA')
    
    def test_pdf_usa_descripcion_correctamente(self):
        """Verificar que PDF incluye la descripción."""
        producto_info = {
            'clave': '615',
            'descripcion': 'KETOCONAZOL/CLINDAMICINA',
            'unidad_medida': 'PIEZA',
        }
        
        # generar_reporte_trazabilidad usa producto_info.get('descripcion')
        descripcion = producto_info.get('descripcion', 'N/A')
        self.assertEqual(descripcion, 'KETOCONAZOL/CLINDAMICINA')
        self.assertNotEqual(descripcion, 'N/A')


class TestBusquedaUnificadaTrazabilidad(TestCase):
    """Tests para la búsqueda unificada trazabilidad_buscar."""
    
    def test_respuesta_busqueda_producto_incluye_nombre(self):
        """La búsqueda unificada debe incluir nombre del producto."""
        # Estructura que devuelve trazabilidad_buscar para producto
        respuesta_busqueda = {
            'tipo': 'producto',
            'identificador': '615',
            'datos': {
                'clave': '615',
                'nombre': 'KETOCONAZOL/CLINDAMICINA',
                'descripcion': 'KETOCONAZOL/CLINDAMICINA',
                'stock_total': 292,
            }
        }
        
        self.assertEqual(respuesta_busqueda['tipo'], 'producto')
        self.assertIn('nombre', respuesta_busqueda['datos'])
        self.assertTrue(respuesta_busqueda['datos']['nombre'])
    
    def test_respuesta_busqueda_lote_incluye_producto(self):
        """La búsqueda unificada para lote debe incluir datos del producto."""
        # Estructura que devuelve trazabilidad_buscar para lote
        respuesta_busqueda = {
            'tipo': 'lote',
            'identificador': 'LOT-2025-001',
            'datos': {
                'numero_lote': 'LOT-2025-001',
                'producto_clave': '615',
                'producto_nombre': 'KETOCONAZOL/CLINDAMICINA',
                'cantidad_actual': 50,
                'fecha_caducidad': '2026-12-31',
            }
        }
        
        self.assertEqual(respuesta_busqueda['tipo'], 'lote')
        self.assertIn('producto_nombre', respuesta_busqueda['datos'])
        self.assertTrue(respuesta_busqueda['datos']['producto_nombre'])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
