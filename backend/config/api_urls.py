"""
URLs API v1
"""
from django.urls import path, include
from django.conf import settings
from rest_framework.routers import SimpleRouter

# Core views
from core.views import (
    LogoutView,
    UserViewSet, ImportacionLogViewSet, AuditoriaLogViewSet, DevAutoLoginView,
    DetalleRequisicionViewSet, NotificacionViewSet, ConfiguracionSistemaViewSet,
    TemaGlobalViewSet,
    ProductoImagenViewSet, LoteDocumentoViewSet, DonacionViewSet, DetalleDonacionViewSet,
    SalidaDonacionViewSet, ProductoDonacionViewSet,  # Catálogo independiente donaciones
    CatalogosView,  # ISS-002 FIX: Endpoint de catálogos
    AdminLimpiarDatosView,  # ADMIN: Limpieza de datos
)
# JWT Views seguros (cookies HttpOnly para refresh token)
from core.serializers_jwt import (
    SecureTokenObtainPairView,
    SecureTokenRefreshView,
    SecureLogoutView,
)
from core.password_reset import (
    PasswordResetRequestView, PasswordResetConfirmView, PasswordResetValidateTokenView
)

# Inventario views
from inventario.views import (
    ProductoViewSet, LoteViewSet, RequisicionViewSet, CentroViewSet,
    MovimientoViewSet, HojaRecoleccionViewSet, dashboard_resumen, dashboard_graficas, trazabilidad_producto,
    trazabilidad_lote, trazabilidad_buscar, trazabilidad_autocomplete, reporte_inventario, reporte_movimientos,
    reporte_caducidades, reporte_requisiciones, reportes_precarga,
    reporte_medicamentos_por_caducar, reporte_bajo_stock, reporte_consumo,
    trazabilidad_global, trazabilidad_producto_exportar, trazabilidad_lote_exportar,
    exportar_control_inventarios
)
from inventario.views.salida_masiva import salida_masiva, hoja_entrega_pdf, lotes_disponibles_farmacia, confirmar_entrega, estado_entrega, cancelar_salida

# SimpleRouter no expone la vista raíz de la API (mayor seguridad)
router = SimpleRouter()

# Core
router.register(r'usuarios', UserViewSet, basename='usuario')
router.register(r'importaciones', ImportacionLogViewSet, basename='importacion')
router.register(r'auditoria', AuditoriaLogViewSet, basename='auditoria')
router.register(r'notificaciones', NotificacionViewSet, basename='notificacion')

# Inventario
router.register(r'centros', CentroViewSet, basename='centro')
router.register(r'productos', ProductoViewSet, basename='producto')
router.register(r'lotes', LoteViewSet, basename='lote')
router.register(r'requisiciones', RequisicionViewSet, basename='requisicion')
router.register(r'detalles-requisicion', DetalleRequisicionViewSet, basename='detalle-requisicion')
router.register(r'movimientos', MovimientoViewSet, basename='movimiento')
router.register(r'hojas-recoleccion', HojaRecoleccionViewSet, basename='hoja-recoleccion')

# Nuevos endpoints
router.register(r'productos-imagenes', ProductoImagenViewSet, basename='producto-imagen')
router.register(r'lotes-documentos', LoteDocumentoViewSet, basename='lote-documento')
router.register(r'donaciones', DonacionViewSet, basename='donacion')
router.register(r'productos-donacion', ProductoDonacionViewSet, basename='producto-donacion')  # Catálogo independiente
router.register(r'detalle-donaciones', DetalleDonacionViewSet, basename='detalle-donacion')
router.register(r'salidas-donaciones', SalidaDonacionViewSet, basename='salida-donacion')

urlpatterns = [
    # Autenticación segura (refresh token en HttpOnly cookie)
    path('token/', SecureTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', SecureTokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', SecureLogoutView.as_view(), name='logout'),
    
    # Recuperación de contraseña (público)
    path('password-reset/request/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('password-reset/validate/', PasswordResetValidateTokenView.as_view(), name='password-reset-validate'),
    
    # Configuración del Sistema (tema/colores) - accesible públicamente para GET
    path('configuracion/tema/', ConfiguracionSistemaViewSet.as_view({
        'get': 'list',
        'put': 'bulk_update',
    }), name='configuracion-tema'),
    path('configuracion/tema/aplicar-tema/', ConfiguracionSistemaViewSet.as_view({
        'post': 'aplicar_tema'
    }), name='configuracion-aplicar-tema'),
    path('configuracion/tema/restablecer/', ConfiguracionSistemaViewSet.as_view({
        'post': 'restablecer'
    }), name='configuracion-restablecer'),
    
    # Tema Global (personalización completa)
    path('tema/', TemaGlobalViewSet.as_view({
        'get': 'list',
        'put': 'update',
    }), name='tema-global'),
    path('tema/activo/', TemaGlobalViewSet.as_view({
        'get': 'tema_activo'
    }), name='tema-activo'),
    path('tema/restablecer/', TemaGlobalViewSet.as_view({
        'post': 'restablecer_institucional'
    }), name='tema-restablecer'),
    path('tema/eliminar-logo/<str:tipo>/', TemaGlobalViewSet.as_view({
        'delete': 'eliminar_logo'
    }), name='tema-eliminar-logo'),
    path('tema/subir-logo/<str:tipo>/', TemaGlobalViewSet.as_view({
        'post': 'subir_logo'
    }), name='tema-subir-logo'),
    
    # ISS-002 FIX: Catálogos del sistema (unidades, categorías, estados, etc.)
    # Públicos para sincronizar formularios frontend/backend
    path('catalogos/', CatalogosView.as_view(), name='catalogos'),
    path('catalogos/<str:catalogo>/', CatalogosView.as_view(), name='catalogos-detalle'),
    
    # Router (incluye /usuarios/me/ como accion del UserViewSet)
    path('', include(router.urls)),

    # Dashboard y reportes
    path('dashboard/', dashboard_resumen, name='dashboard'),
    path('dashboard/graficas/', dashboard_graficas, name='dashboard-graficas'),
    path('trazabilidad/buscar/', trazabilidad_buscar, name='trazabilidad-buscar'),
    path('trazabilidad/autocomplete/', trazabilidad_autocomplete, name='trazabilidad-autocomplete'),
    path('trazabilidad/producto/<str:clave>/', trazabilidad_producto, name='trazabilidad-producto'),
    path('trazabilidad/lote/<str:codigo>/', trazabilidad_lote, name='trazabilidad-lote'),
    path('trazabilidad/global/', trazabilidad_global, name='trazabilidad-global'),
    path('trazabilidad/producto/<str:clave>/exportar/', trazabilidad_producto_exportar, name='trazabilidad-producto-exportar'),
    path('trazabilidad/lote/<str:codigo>/exportar/', trazabilidad_lote_exportar, name='trazabilidad-lote-exportar'),
    path('trazabilidad/exportar-control-inventarios/', exportar_control_inventarios, name='exportar-control-inventarios'),
    path('reportes/inventario/', reporte_inventario, name='reporte-inventario'),
    path('reportes/movimientos/', reporte_movimientos, name='reporte-movimientos'),
    path('reportes/caducidades/', reporte_caducidades, name='reporte-caducidades'),
    path('reportes/requisiciones/', reporte_requisiciones, name='reporte-requisiciones'),
    path('reportes/medicamentos-por-caducar/', reporte_medicamentos_por_caducar, name='reporte-medicamentos-por-caducar'),
    path('reportes/bajo-stock/', reporte_bajo_stock, name='reporte-bajo-stock'),
    path('reportes/consumo/', reporte_consumo, name='reporte-consumo'),
    path('reportes/precarga/', reportes_precarga, name='reportes-precarga'),
    
    # Salida masiva (solo Farmacia)
    path('salida-masiva/', salida_masiva, name='salida-masiva'),
    path('salida-masiva/lotes-disponibles/', lotes_disponibles_farmacia, name='lotes-disponibles-farmacia'),
    path('salida-masiva/hoja-entrega/<str:grupo_salida>/', hoja_entrega_pdf, name='hoja-entrega-pdf'),
    path('salida-masiva/confirmar-entrega/<str:grupo_salida>/', confirmar_entrega, name='confirmar-entrega'),
    path('salida-masiva/estado-entrega/<str:grupo_salida>/', estado_entrega, name='estado-entrega'),
    path('salida-masiva/cancelar/<str:grupo_salida>/', cancelar_salida, name='cancelar-salida'),
    
    # ADMIN: Limpieza de datos (solo superusuarios)
    path('admin/limpiar-datos/', AdminLimpiarDatosView.as_view(), name='admin-limpiar-datos'),
]

# SOLO EN DESARROLLO: Endpoint de autologin automatico
if settings.DEBUG:
    urlpatterns.append(path('dev-autologin/', DevAutoLoginView.as_view(), name='dev-autologin'))