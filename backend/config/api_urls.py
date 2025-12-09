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
    SalidaDonacionViewSet
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
    trazabilidad_lote, reporte_inventario, reporte_movimientos,
    reporte_caducidades, reporte_requisiciones, reportes_precarga,
    reporte_medicamentos_por_caducar, reporte_bajo_stock, reporte_consumo
)

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
    
    # Router (incluye /usuarios/me/ como accion del UserViewSet)
    path('', include(router.urls)),

    # Dashboard y reportes
    path('dashboard/', dashboard_resumen, name='dashboard'),
    path('dashboard/graficas/', dashboard_graficas, name='dashboard-graficas'),
    path('trazabilidad/producto/<str:clave>/', trazabilidad_producto, name='trazabilidad-producto'),
    path('trazabilidad/lote/<str:codigo>/', trazabilidad_lote, name='trazabilidad-lote'),
    path('reportes/inventario/', reporte_inventario, name='reporte-inventario'),
    path('reportes/movimientos/', reporte_movimientos, name='reporte-movimientos'),
    path('reportes/caducidades/', reporte_caducidades, name='reporte-caducidades'),
    path('reportes/requisiciones/', reporte_requisiciones, name='reporte-requisiciones'),
    path('reportes/medicamentos-por-caducar/', reporte_medicamentos_por_caducar, name='reporte-medicamentos-por-caducar'),
    path('reportes/bajo-stock/', reporte_bajo_stock, name='reporte-bajo-stock'),
    path('reportes/consumo/', reporte_consumo, name='reporte-consumo'),
    path('reportes/precarga/', reportes_precarga, name='reportes-precarga'),
]

# SOLO EN DESARROLLO: Endpoint de autologin automatico
if settings.DEBUG:
    urlpatterns.append(path('dev-autologin/', DevAutoLoginView.as_view(), name='dev-autologin'))
