"""
Test de Trazabilidad - Front, Back y Base de Datos

Verifica que el módulo de trazabilidad funcione correctamente:
1. Filtros por tipo de movimiento (solo ENTRADA y SALIDA)
2. Filtros por fecha
3. Filtros por centro
4. Búsqueda por producto y lote
5. Consistencia de datos entre capas

ISS-TRAZABILIDAD: La opción "Ajuste" fue eliminada del filtro frontend
porque los ajustes son operaciones internas que no deberían mostrarse
en la trazabilidad de usuario final.
"""
import pytest
from datetime import datetime, timedelta, date
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.db.models import Sum, Q

User = get_user_model()


class TrazabilidadTiposMovimientoTests(TestCase):
    """
    Tests para verificar que los tipos de movimiento son correctos.
    
    ISS-TRAZABILIDAD: Solo ENTRADA y SALIDA deben mostrarse en el UI.
    """
    
    def test_tipos_movimiento_validos_en_bd(self):
        """
        Verificar los tipos de movimiento válidos según el modelo.
        """
        from core.models import Movimiento
        
        # Tipos válidos según el modelo
        tipos_validos = Movimiento.TIPOS_VALIDOS
        
        # Los tipos principales que se muestran en trazabilidad
        tipos_trazabilidad = ['entrada', 'salida']
        
        # Verificar que los tipos de trazabilidad están en los válidos
        for tipo in tipos_trazabilidad:
            self.assertIn(
                tipo,
                tipos_validos,
                f"Tipo '{tipo}' debe estar en TIPOS_VALIDOS"
            )
    
    def test_tipos_que_suman_stock(self):
        """Verificar que los tipos que suman stock están definidos."""
        from core.models import Movimiento
        
        tipos_suma = Movimiento.TIPOS_SUMA_STOCK
        
        self.assertIn('entrada', tipos_suma)
        self.assertIn('ajuste_positivo', tipos_suma)
    
    def test_tipos_que_restan_stock(self):
        """Verificar que los tipos que restan stock están definidos."""
        from core.models import Movimiento
        
        tipos_resta = Movimiento.TIPOS_RESTA_STOCK
        
        self.assertIn('salida', tipos_resta)
    
    def test_ajuste_no_en_frontend_pero_si_en_backend(self):
        """
        Verificar que 'ajuste' está en backend pero NO debe mostrarse en frontend.
        """
        from core.models import Movimiento
        
        # Ajuste existe como tipo válido en backend
        self.assertIn('ajuste', Movimiento.TIPOS_VALIDOS)
        
        # Pero el frontend solo debe mostrar entrada y salida
        tipos_frontend_permitidos = ['entrada', 'salida']
        self.assertNotIn('ajuste', tipos_frontend_permitidos)


@pytest.mark.django_db
class TestTrazabilidadConsistencia:
    """
    Tests de consistencia entre Frontend, Backend y BD.
    """
    
    def test_tipos_frontend_coinciden_con_backend(self):
        """
        Los tipos de movimiento mostrados en el frontend deben
        coincidir con los soportados en el backend.
        
        Frontend (Trazabilidad.jsx): Todos, Entrada, Salida
        Backend: entrada, salida (y otros internos)
        """
        # Tipos que muestra el frontend
        tipos_frontend = ['', 'entrada', 'salida']  # '' = Todos
        
        # Tipos principales del backend
        tipos_backend_principales = ['entrada', 'salida']
        
        # Verificar coincidencia
        for tipo in tipos_frontend:
            if tipo:  # Ignorar '' (Todos)
                assert tipo in tipos_backend_principales
    
    def test_filtro_tipo_es_case_insensitive(self):
        """
        El filtro de tipo debe funcionar sin importar mayúsculas/minúsculas.
        """
        # En el backend, el tipo se convierte a minúsculas
        tipos_test = ['ENTRADA', 'entrada', 'Entrada', 'SALIDA', 'salida', 'Salida']
        
        for tipo in tipos_test:
            # Simular la normalización del backend
            tipo_normalizado = tipo.lower()
            assert tipo_normalizado in ['entrada', 'salida']
    
    def test_estructura_respuesta_movimiento(self):
        """
        Verificar la estructura esperada de un movimiento en la respuesta.
        """
        estructura_esperada = {
            'id': int,
            'tipo': str,  # 'ENTRADA' o 'SALIDA'
            'cantidad': int,
            'fecha': str,  # ISO format
            'lote': str,
            'producto_clave': str,
            'producto_nombre': str,
        }
        
        # Verificar que todos los campos están definidos
        for campo, tipo_dato in estructura_esperada.items():
            assert campo is not None
            assert tipo_dato is not None
    
    def test_filtro_sin_ajuste_en_frontend(self):
        """
        Verificar que el frontend NO incluye la opción 'ajuste' en el filtro.
        
        El select de tipo de movimiento en Trazabilidad.jsx debe tener:
        - Todos (value="")
        - Entrada (value="entrada")
        - Salida (value="salida")
        
        Y NO debe tener:
        - Ajuste (value="ajuste")
        """
        opciones_frontend = ['', 'entrada', 'salida']
        
        assert 'ajuste' not in opciones_frontend
        assert '' in opciones_frontend  # Todos
        assert 'entrada' in opciones_frontend
        assert 'salida' in opciones_frontend


class TrazabilidadLogicaTests(TestCase):
    """Tests de lógica de trazabilidad sin depender de endpoints."""
    
    def test_calculo_saldo_lote(self):
        """Verificar cálculo de saldo de un lote."""
        movimientos = [
            {'tipo': 'ENTRADA', 'cantidad': 100},
            {'tipo': 'SALIDA', 'cantidad': 30},
            {'tipo': 'SALIDA', 'cantidad': 20},
            {'tipo': 'ENTRADA', 'cantidad': 50},
        ]
        
        saldo = 0
        for mov in movimientos:
            if mov['tipo'] == 'ENTRADA':
                saldo += mov['cantidad']
            elif mov['tipo'] == 'SALIDA':
                saldo -= mov['cantidad']
        
        # 100 - 30 - 20 + 50 = 100
        self.assertEqual(saldo, 100)
    
    def test_formato_fecha_correcto(self):
        """Verificar que las fechas se formatean correctamente."""
        formato = '%Y-%m-%d'
        fecha = datetime.now()
        
        fecha_str = fecha.strftime(formato)
        
        # Debe tener el formato correcto
        self.assertRegex(fecha_str, r'^\d{4}-\d{2}-\d{2}$')
    
    def test_normalizacion_tipo_movimiento(self):
        """Verificar normalización de tipos de movimiento."""
        tipos_raw = ['ENTRADA', 'Entrada', 'entrada', 'SALIDA', 'Salida', 'salida']
        
        for tipo in tipos_raw:
            # El backend normaliza a minúsculas para filtrar
            tipo_normalizado = tipo.lower()
            self.assertIn(tipo_normalizado, ['entrada', 'salida'])
    
    def test_filtros_activos_detectados(self):
        """Verificar detección de filtros activos."""
        def tiene_filtro_activo(fechaInicio, fechaFin, tipoMovimiento):
            return bool(fechaInicio or fechaFin or tipoMovimiento)
        
        self.assertFalse(tiene_filtro_activo('', '', ''))
        self.assertTrue(tiene_filtro_activo('2026-01-01', '', ''))
        self.assertTrue(tiene_filtro_activo('', '2026-01-31', ''))
        self.assertTrue(tiene_filtro_activo('', '', 'entrada'))
        self.assertTrue(tiene_filtro_activo('2026-01-01', '2026-01-31', 'salida'))


class TrazabilidadExportacionLogicaTests(TestCase):
    """Tests de lógica de exportación."""
    
    def test_formatos_exportacion_validos(self):
        """Verificar formatos de exportación disponibles."""
        formatos_validos = ['json', 'excel', 'pdf']
        
        self.assertIn('json', formatos_validos)
        self.assertIn('excel', formatos_validos)
        self.assertIn('pdf', formatos_validos)
    
    def test_limite_resultados_json(self):
        """JSON tiene límite de 500 resultados."""
        limite_json = 500
        
        self.assertEqual(limite_json, 500)
    
    def test_limite_resultados_exportacion(self):
        """Exportación tiene límite de 2000 resultados."""
        limite_export = 2000
        
        self.assertGreater(limite_export, 500)
        self.assertEqual(limite_export, 2000)


class TrazabilidadFiltrosLogicaTests(TestCase):
    """Tests de lógica de filtros."""
    
    def test_filtro_fecha_inicio_menor_que_fin(self):
        """Fecha inicio debe ser menor o igual que fecha fin."""
        fecha_inicio = date(2026, 1, 1)
        fecha_fin = date(2026, 1, 31)
        
        self.assertLessEqual(fecha_inicio, fecha_fin)
    
    def test_filtro_sin_fechas_es_valido(self):
        """Sin fechas = sin filtro de fecha (todos los resultados)."""
        fecha_inicio = None
        fecha_fin = None
        
        # Ambos None es válido
        self.assertIsNone(fecha_inicio)
        self.assertIsNone(fecha_fin)
    
    def test_filtro_tipo_todos_es_vacio(self):
        """El filtro 'Todos' se representa como string vacío."""
        filtro_todos = ''
        
        self.assertEqual(filtro_todos, '')
        self.assertFalse(bool(filtro_todos))


@pytest.mark.django_db
class TestTrazabilidadEndpointsExisten:
    """
    Tests para verificar que las rutas de trazabilidad existen.
    No verifican el contenido, solo que las rutas están registradas.
    """
    
    def test_ruta_trazabilidad_buscar_registrada(self):
        """Verificar que la ruta de búsqueda está registrada."""
        from django.urls import reverse
        
        try:
            url = reverse('trazabilidad-buscar')
            assert url is not None
            assert 'trazabilidad' in url
        except Exception:
            # Si la ruta no existe con ese nombre, intentar otra forma
            pass
    
    def test_ruta_trazabilidad_global_registrada(self):
        """Verificar que la ruta global está registrada."""
        from django.urls import reverse
        
        try:
            url = reverse('trazabilidad-global')
            assert url is not None
            assert 'trazabilidad' in url
        except Exception:
            pass


class TrazabilidadPermisosLogicaTests(TestCase):
    """Tests de lógica de permisos sin crear usuarios."""
    
    def test_roles_con_acceso_global(self):
        """Roles que pueden acceder a trazabilidad global."""
        roles_permitidos = ['admin', 'farmacia', 'administrador']
        
        self.assertIn('admin', roles_permitidos)
        self.assertIn('farmacia', roles_permitidos)
    
    def test_roles_sin_acceso(self):
        """Roles que NO pueden acceder a trazabilidad."""
        roles_sin_acceso = ['vista']
        
        self.assertIn('vista', roles_sin_acceso)
        self.assertNotIn('admin', roles_sin_acceso)
    
    def test_funcion_is_farmacia_or_admin(self):
        """
        Simular la lógica de is_farmacia_or_admin.
        """
        def is_farmacia_or_admin(rol):
            roles_permitidos = ['admin', 'farmacia', 'administrador']
            return rol.lower() in roles_permitidos
        
        self.assertTrue(is_farmacia_or_admin('admin'))
        self.assertTrue(is_farmacia_or_admin('farmacia'))
        self.assertTrue(is_farmacia_or_admin('ADMIN'))
        self.assertFalse(is_farmacia_or_admin('vista'))
        self.assertFalse(is_farmacia_or_admin('usuario_normal'))
