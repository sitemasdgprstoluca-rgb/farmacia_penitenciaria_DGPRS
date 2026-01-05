"""
Pruebas unitarias para AdminLimpiarDatosView
============================================

Valida la funcionalidad del endpoint de limpieza de datos administrativos
ubicado en: backend/core/views.py (línea ~4453)

Ruta API: POST /api/admin/limpiar-datos/
"""
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from django.test import RequestFactory
from rest_framework import status


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def request_factory():
    """Factory para crear requests de prueba"""
    return RequestFactory()


@pytest.fixture
def mock_superuser():
    """Mock de usuario superusuario"""
    user = MagicMock()
    user.is_superuser = True
    user.is_authenticated = True
    user.username = 'admin_test'
    user.email = 'admin@test.com'
    user.id = 1
    return user


@pytest.fixture
def mock_normal_user():
    """Mock de usuario normal (no superusuario)"""
    user = MagicMock()
    user.is_superuser = False
    user.is_authenticated = True
    user.username = 'user_test'
    user.email = 'user@test.com'
    user.id = 2
    return user


@pytest.fixture
def mock_cursor():
    """Mock del cursor de base de datos"""
    cursor = MagicMock()
    cursor.rowcount = 5  # Simula 5 filas afectadas
    cursor.fetchone.return_value = (10,)  # Para COUNT queries
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    return cursor


# ============================================================
# PRUEBAS DE PERMISOS
# ============================================================

class TestAdminLimpiarDatosPermisos:
    """Pruebas de control de acceso"""
    
    @pytest.mark.unit
    def test_get_solo_superusuarios_puede_ver_stats(self, request_factory, mock_normal_user):
        """Solo superusuarios pueden obtener estadísticas"""
        from core.views import AdminLimpiarDatosView
        
        view = AdminLimpiarDatosView()
        request = request_factory.get('/api/admin/limpiar-datos/')
        request.user = mock_normal_user
        
        response = view.get(request)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'SUPERUSUARIOS' in response.data.get('error', '')
    
    @pytest.mark.unit
    def test_post_solo_superusuarios_puede_limpiar(self, request_factory, mock_normal_user):
        """Solo superusuarios pueden ejecutar limpieza"""
        from core.views import AdminLimpiarDatosView
        
        view = AdminLimpiarDatosView()
        request = request_factory.post('/api/admin/limpiar-datos/')
        request.user = mock_normal_user
        request.data = {'confirmar': True, 'categoria': 'todos'}
        
        response = view.post(request)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'SUPERUSUARIOS' in response.data.get('error', '')


# ============================================================
# PRUEBAS DE VALIDACIÓN
# ============================================================

class TestAdminLimpiarDatosValidacion:
    """Pruebas de validación de parámetros"""
    
    @pytest.mark.unit
    def test_post_requiere_confirmacion(self, request_factory, mock_superuser):
        """POST sin confirmar=true debe rechazarse"""
        from core.views import AdminLimpiarDatosView
        
        view = AdminLimpiarDatosView()
        request = request_factory.post('/api/admin/limpiar-datos/')
        request.user = mock_superuser
        request.data = {'categoria': 'todos'}  # Sin confirmar
        
        response = view.post(request)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'confirmar' in response.data.get('error', '').lower()
    
    @pytest.mark.unit
    def test_post_confirmar_false_rechazado(self, request_factory, mock_superuser):
        """POST con confirmar=false debe rechazarse"""
        from core.views import AdminLimpiarDatosView
        
        view = AdminLimpiarDatosView()
        request = request_factory.post('/api/admin/limpiar-datos/')
        request.user = mock_superuser
        request.data = {'confirmar': False, 'categoria': 'todos'}
        
        response = view.post(request)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.unit
    def test_post_categoria_invalida_rechazada(self, request_factory, mock_superuser):
        """POST con categoría inválida debe rechazarse"""
        from core.views import AdminLimpiarDatosView
        
        view = AdminLimpiarDatosView()
        request = request_factory.post('/api/admin/limpiar-datos/')
        request.user = mock_superuser
        request.data = {'confirmar': True, 'categoria': 'categoria_inexistente'}
        
        response = view.post(request)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'inválida' in response.data.get('error', '').lower()
    
    @pytest.mark.unit
    @pytest.mark.parametrize('categoria', [
        'productos', 'lotes', 'requisiciones', 'movimientos', 
        'donaciones', 'notificaciones', 'todos'
    ])
    def test_categorias_validas_aceptadas(self, categoria, request_factory, mock_superuser, mock_cursor):
        """Todas las categorías válidas deben ser aceptadas"""
        from core.views import AdminLimpiarDatosView
        
        view = AdminLimpiarDatosView()
        request = request_factory.post('/api/admin/limpiar-datos/')
        request.user = mock_superuser
        request.data = {'confirmar': True, 'categoria': categoria}
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'Test'}
        
        # Mock de todos los modelos y cursor
        with patch('core.views.transaction.atomic'), \
             patch('django.db.connection.cursor') as mock_conn_cursor, \
             patch('core.models.AuditoriaLog.objects.create'):
            
            mock_conn_cursor.return_value = mock_cursor
            response = view.post(request)
        
        # No debe rechazar por categoría inválida
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            assert 'inválida' not in response.data.get('error', '').lower()


# ============================================================
# PRUEBAS DE ELIMINACIÓN CON SQL DIRECTO
# ============================================================

class TestAdminLimpiarDatosSQLDirecto:
    """Pruebas de que se usa SQL directo en vez de ORM"""
    
    @pytest.mark.unit
    def test_eliminar_movimientos_usa_sql_directo(self, request_factory, mock_superuser, mock_cursor):
        """Categoría 'movimientos' debe usar SQL DELETE directo"""
        from core.views import AdminLimpiarDatosView
        
        view = AdminLimpiarDatosView()
        request = request_factory.post('/api/admin/limpiar-datos/')
        request.user = mock_superuser
        request.data = {'confirmar': True, 'categoria': 'movimientos'}
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'Test'}
        
        with patch('core.views.transaction.atomic'), \
             patch('django.db.connection.cursor') as mock_conn_cursor, \
             patch('core.models.AuditoriaLog.objects.create'):
            
            mock_conn_cursor.return_value = mock_cursor
            response = view.post(request)
        
        # Verificar que se ejecutó DELETE FROM movimientos
        calls = mock_cursor.execute.call_args_list
        sql_calls = [str(call) for call in calls]
        assert any('DELETE FROM movimientos' in str(call) for call in sql_calls), \
            f"No se encontró DELETE FROM movimientos. Calls: {sql_calls}"
    
    @pytest.mark.unit
    def test_eliminar_donaciones_usa_sql_directo(self, request_factory, mock_superuser, mock_cursor):
        """Categoría 'donaciones' debe usar SQL DELETE directo en orden correcto"""
        from core.views import AdminLimpiarDatosView
        
        view = AdminLimpiarDatosView()
        request = request_factory.post('/api/admin/limpiar-datos/')
        request.user = mock_superuser
        request.data = {'confirmar': True, 'categoria': 'donaciones'}
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'Test'}
        
        with patch('core.views.transaction.atomic'), \
             patch('django.db.connection.cursor') as mock_conn_cursor, \
             patch('core.models.AuditoriaLog.objects.create'):
            
            mock_conn_cursor.return_value = mock_cursor
            response = view.post(request)
        
        # Verificar las 3 tablas de donaciones
        calls = [str(call) for call in mock_cursor.execute.call_args_list]
        assert any('DELETE FROM salidas_donaciones' in call for call in calls)
        assert any('DELETE FROM detalle_donaciones' in call for call in calls)
        assert any('DELETE FROM donaciones' in call for call in calls)
    
    @pytest.mark.unit
    def test_eliminar_requisiciones_usa_sql_directo(self, request_factory, mock_superuser, mock_cursor):
        """Categoría 'requisiciones' debe usar SQL DELETE directo"""
        from core.views import AdminLimpiarDatosView
        
        view = AdminLimpiarDatosView()
        request = request_factory.post('/api/admin/limpiar-datos/')
        request.user = mock_superuser
        request.data = {'confirmar': True, 'categoria': 'requisiciones'}
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'Test'}
        
        with patch('core.views.transaction.atomic'), \
             patch('django.db.connection.cursor') as mock_conn_cursor, \
             patch('core.models.AuditoriaLog.objects.create'):
            
            mock_conn_cursor.return_value = mock_cursor
            response = view.post(request)
        
        # Verificar las tablas relacionadas
        calls = [str(call) for call in mock_cursor.execute.call_args_list]
        assert any('DELETE FROM detalle_hojas_recoleccion' in call for call in calls)
        assert any('DELETE FROM hojas_recoleccion' in call for call in calls)
        assert any('DELETE FROM requisicion_ajustes_cantidad' in call for call in calls)
        assert any('DELETE FROM detalles_requisicion' in call for call in calls)
        assert any('DELETE FROM requisicion_historial_estados' in call for call in calls)
        assert any('DELETE FROM requisiciones' in call for call in calls)
    
    @pytest.mark.unit
    def test_eliminar_lotes_usa_sql_directo(self, request_factory, mock_superuser, mock_cursor):
        """Categoría 'lotes' debe usar SQL DELETE directo y UPDATE para productos"""
        from core.views import AdminLimpiarDatosView
        
        view = AdminLimpiarDatosView()
        request = request_factory.post('/api/admin/limpiar-datos/')
        request.user = mock_superuser
        request.data = {'confirmar': True, 'categoria': 'lotes'}
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'Test'}
        
        with patch('core.views.transaction.atomic'), \
             patch('django.db.connection.cursor') as mock_conn_cursor, \
             patch('core.models.AuditoriaLog.objects.create'):
            
            mock_conn_cursor.return_value = mock_cursor
            response = view.post(request)
        
        calls = [str(call) for call in mock_cursor.execute.call_args_list]
        assert any('DELETE FROM lotes' in call for call in calls)
        assert any('DELETE FROM lote_documentos' in call for call in calls)
        # También debe actualizar el stock a 0
        assert any('UPDATE productos SET stock_actual = 0' in call for call in calls)
    
    @pytest.mark.unit
    def test_eliminar_todos_incluye_todas_tablas(self, request_factory, mock_superuser, mock_cursor):
        """Categoría 'todos' debe limpiar TODAS las tablas operativas"""
        from core.views import AdminLimpiarDatosView
        
        view = AdminLimpiarDatosView()
        request = request_factory.post('/api/admin/limpiar-datos/')
        request.user = mock_superuser
        request.data = {'confirmar': True, 'categoria': 'todos'}
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'Test'}
        
        with patch('core.views.transaction.atomic'), \
             patch('django.db.connection.cursor') as mock_conn_cursor, \
             patch('core.models.AuditoriaLog.objects.create'):
            
            mock_conn_cursor.return_value = mock_cursor
            response = view.post(request)
        
        calls = [str(call) for call in mock_cursor.execute.call_args_list]
        
        # Tablas que deben eliminarse en 'todos'
        tablas_requeridas = [
            'detalle_hojas_recoleccion',
            'hojas_recoleccion', 
            'requisicion_ajustes_cantidad',
            'detalles_requisicion',
            'requisicion_historial_estados',
            'movimientos',
            'requisiciones',
            'lote_documentos',
            'lotes',
            'producto_imagenes',
            'productos',
            'importacion_logs',
            'salidas_donaciones',
            'detalle_donaciones',
            'donaciones',
            'notificaciones',
        ]
        
        for tabla in tablas_requeridas:
            assert any(f'DELETE FROM {tabla}' in call for call in calls), \
                f"Tabla {tabla} no está siendo limpiada en 'todos'"


# ============================================================
# PRUEBAS DE RESPUESTA
# ============================================================

class TestAdminLimpiarDatosRespuesta:
    """Pruebas de formato de respuesta"""
    
    @pytest.mark.unit
    def test_respuesta_exitosa_incluye_campos_requeridos(self, request_factory, mock_superuser, mock_cursor):
        """Respuesta exitosa debe incluir campos esperados"""
        from core.views import AdminLimpiarDatosView
        
        view = AdminLimpiarDatosView()
        request = request_factory.post('/api/admin/limpiar-datos/')
        request.user = mock_superuser
        request.data = {'confirmar': True, 'categoria': 'movimientos'}
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'Test'}
        
        with patch('core.views.transaction.atomic'), \
             patch('django.db.connection.cursor') as mock_conn_cursor, \
             patch('core.models.AuditoriaLog.objects.create'):
            
            mock_conn_cursor.return_value = mock_cursor
            response = view.post(request)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        
        # Campos requeridos
        assert 'success' in data
        assert data['success'] is True
        assert 'mensaje' in data
        assert 'categoria' in data
        assert 'eliminados' in data
        assert 'total_registros_eliminados' in data
        assert 'ejecutado_por' in data
        assert 'fecha' in data
    
    @pytest.mark.unit
    def test_respuesta_incluye_conteo_eliminados(self, request_factory, mock_superuser, mock_cursor):
        """Respuesta debe incluir conteo de registros eliminados"""
        from core.views import AdminLimpiarDatosView
        
        view = AdminLimpiarDatosView()
        request = request_factory.post('/api/admin/limpiar-datos/')
        request.user = mock_superuser
        request.data = {'confirmar': True, 'categoria': 'movimientos'}
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'Test'}
        
        # Mock cursor que retorna 15 filas afectadas
        mock_cursor.rowcount = 15
        
        with patch('core.views.transaction.atomic'), \
             patch('django.db.connection.cursor') as mock_conn_cursor, \
             patch('core.models.AuditoriaLog.objects.create'):
            
            mock_conn_cursor.return_value = mock_cursor
            response = view.post(request)
        
        assert response.data['eliminados']['movimientos'] == 15
        assert response.data['total_registros_eliminados'] == 15


# ============================================================
# PRUEBAS DE AUDITORÍA
# ============================================================

class TestAdminLimpiarDatosAuditoria:
    """Pruebas de registro de auditoría"""
    
    @pytest.mark.unit
    def test_limpieza_crea_registro_auditoria(self, request_factory, mock_superuser, mock_cursor):
        """Limpieza debe crear registro en AuditoriaLog"""
        from core.views import AdminLimpiarDatosView
        
        view = AdminLimpiarDatosView()
        request = request_factory.post('/api/admin/limpiar-datos/')
        request.user = mock_superuser
        request.data = {'confirmar': True, 'categoria': 'movimientos'}
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'Test'}
        
        with patch('core.views.transaction.atomic'), \
             patch('django.db.connection.cursor') as mock_conn_cursor, \
             patch('core.models.AuditoriaLog.objects.create') as mock_audit:
            
            mock_conn_cursor.return_value = mock_cursor
            response = view.post(request)
        
        # Verificar que se llamó a crear auditoría
        mock_audit.assert_called_once()
        
        # Verificar parámetros de auditoría
        call_kwargs = mock_audit.call_args.kwargs
        assert call_kwargs['usuario'] == mock_superuser
        assert call_kwargs['accion'] == 'LIMPIEZA_DATOS'
        assert call_kwargs['modelo'] == 'SISTEMA'
        assert 'categoria' in call_kwargs['detalles']
        assert call_kwargs['detalles']['categoria'] == 'movimientos'


# ============================================================
# PRUEBAS DE GET (ESTADÍSTICAS)
# ============================================================

class TestAdminLimpiarDatosEstadisticas:
    """Pruebas del endpoint GET para estadísticas"""
    
    @pytest.mark.unit
    def test_get_retorna_estadisticas_por_categoria(self, request_factory, mock_superuser, mock_cursor):
        """GET debe retornar estadísticas organizadas por categoría"""
        from core.views import AdminLimpiarDatosView
        
        view = AdminLimpiarDatosView()
        request = request_factory.get('/api/admin/limpiar-datos/')
        request.user = mock_superuser
        
        # Mock de los modelos
        with patch('core.models.Producto.objects') as mock_prod, \
             patch('core.models.Lote.objects') as mock_lote, \
             patch('core.models.Movimiento.objects') as mock_mov, \
             patch('core.models.Requisicion.objects') as mock_req, \
             patch('core.models.DetalleRequisicion.objects') as mock_det_req, \
             patch('core.models.HojaRecoleccion.objects') as mock_hoja, \
             patch('core.models.DetalleHojaRecoleccion.objects') as mock_det_hoja, \
             patch('core.models.LoteDocumento.objects') as mock_lot_doc, \
             patch('core.models.ProductoImagen.objects') as mock_prod_img, \
             patch('core.models.Donacion.objects') as mock_don, \
             patch('core.models.DetalleDonacion.objects') as mock_det_don, \
             patch('core.models.SalidaDonacion.objects') as mock_sal_don, \
             patch('core.models.Notificacion.objects') as mock_notif, \
             patch('django.db.connection.cursor') as mock_conn_cursor:
            
            # Configurar mocks con conteos
            mock_prod.count.return_value = 100
            mock_lote.count.return_value = 50
            mock_mov.count.return_value = 200
            mock_req.count.return_value = 30
            mock_det_req.count.return_value = 90
            mock_hoja.count.return_value = 10
            mock_det_hoja.count.return_value = 40
            mock_lot_doc.count.return_value = 25
            mock_prod_img.count.return_value = 75
            mock_don.count.return_value = 5
            mock_det_don.count.return_value = 15
            mock_det_don.values.return_value.distinct.return_value.count.return_value = 3
            mock_sal_don.count.return_value = 8
            mock_notif.count.return_value = 50
            
            mock_conn_cursor.return_value = mock_cursor
            
            response = view.get(request)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        
        # Verificar estructura
        assert 'categorias' in data
        assert 'resumen' in data
        assert 'no_se_eliminara' in data
        
        # Verificar categorías disponibles
        categorias = data['categorias']
        assert 'productos' in categorias
        assert 'lotes' in categorias
        assert 'requisiciones' in categorias
        assert 'movimientos' in categorias
        assert 'donaciones' in categorias
        assert 'notificaciones' in categorias
        assert 'todos' in categorias
    
    @pytest.mark.unit
    def test_get_incluye_lista_no_se_eliminara(self, request_factory, mock_superuser, mock_cursor):
        """GET debe incluir lista de lo que NO se elimina"""
        from core.views import AdminLimpiarDatosView
        
        view = AdminLimpiarDatosView()
        request = request_factory.get('/api/admin/limpiar-datos/')
        request.user = mock_superuser
        
        with patch('core.models.Producto.objects') as mock_prod, \
             patch('core.models.Lote.objects') as mock_lote, \
             patch('core.models.Movimiento.objects') as mock_mov, \
             patch('core.models.Requisicion.objects') as mock_req, \
             patch('core.models.DetalleRequisicion.objects') as mock_det_req, \
             patch('core.models.HojaRecoleccion.objects') as mock_hoja, \
             patch('core.models.DetalleHojaRecoleccion.objects') as mock_det_hoja, \
             patch('core.models.LoteDocumento.objects') as mock_lot_doc, \
             patch('core.models.ProductoImagen.objects') as mock_prod_img, \
             patch('core.models.Donacion.objects') as mock_don, \
             patch('core.models.DetalleDonacion.objects') as mock_det_don, \
             patch('core.models.SalidaDonacion.objects') as mock_sal_don, \
             patch('core.models.Notificacion.objects') as mock_notif, \
             patch('django.db.connection.cursor') as mock_conn_cursor:
            
            # Configurar mocks
            for mock in [mock_prod, mock_lote, mock_mov, mock_req, mock_det_req,
                        mock_hoja, mock_det_hoja, mock_lot_doc, mock_prod_img,
                        mock_don, mock_det_don, mock_sal_don, mock_notif]:
                mock.count.return_value = 0
            mock_det_don.values.return_value.distinct.return_value.count.return_value = 0
            
            mock_conn_cursor.return_value = mock_cursor
            
            response = view.get(request)
        
        no_eliminar = response.data.get('no_se_eliminara', [])
        
        # Verificar que menciona elementos protegidos
        no_eliminar_texto = ' '.join(no_eliminar).lower()
        assert 'usuario' in no_eliminar_texto
        assert 'centro' in no_eliminar_texto
        assert 'configuración' in no_eliminar_texto or 'configuracion' in no_eliminar_texto


# ============================================================
# PRUEBAS DE MANEJO DE ERRORES
# ============================================================

class TestAdminLimpiarDatosErrores:
    """Pruebas de manejo de errores"""
    
    @pytest.mark.unit
    def test_error_sql_retorna_500(self, request_factory, mock_superuser):
        """Error en SQL debe retornar 500 con mensaje de error"""
        from core.views import AdminLimpiarDatosView
        
        view = AdminLimpiarDatosView()
        request = request_factory.post('/api/admin/limpiar-datos/')
        request.user = mock_superuser
        request.data = {'confirmar': True, 'categoria': 'movimientos'}
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'Test'}
        
        with patch('core.views.transaction.atomic'), \
             patch('django.db.connection.cursor') as mock_conn_cursor:
            
            # Simular error de SQL
            mock_cursor = MagicMock()
            mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
            mock_cursor.__exit__ = MagicMock(return_value=False)
            mock_cursor.execute.side_effect = Exception("Error de conexión a BD")
            mock_conn_cursor.return_value = mock_cursor
            
            response = view.post(request)
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert 'error' in response.data
        assert 'Error al limpiar datos' in response.data['error']


# ============================================================
# RESUMEN DE PRUEBAS
# ============================================================

"""
Total de pruebas: 19

Permisos (2):
- test_get_solo_superusuarios_puede_ver_stats
- test_post_solo_superusuarios_puede_limpiar

Validación (4):
- test_post_requiere_confirmacion
- test_post_confirmar_false_rechazado
- test_post_categoria_invalida_rechazada
- test_categorias_validas_aceptadas (parametrizada, 7 variantes)

SQL Directo (5):
- test_eliminar_movimientos_usa_sql_directo
- test_eliminar_donaciones_usa_sql_directo
- test_eliminar_requisiciones_usa_sql_directo
- test_eliminar_lotes_usa_sql_directo
- test_eliminar_todos_incluye_todas_tablas

Respuesta (2):
- test_respuesta_exitosa_incluye_campos_requeridos
- test_respuesta_incluye_conteo_eliminados

Auditoría (1):
- test_limpieza_crea_registro_auditoria

Estadísticas GET (2):
- test_get_retorna_estadisticas_por_categoria
- test_get_incluye_lista_no_se_eliminara

Errores (1):
- test_error_sql_retorna_500
"""
