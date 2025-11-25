"""
URLs API v1
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

# Core views
from core.views import (
    CustomTokenObtainPairView, LogoutView,
    UserViewSet, ImportacionLogViewSet, AuditoriaLogViewSet, DevAutoLoginView,
    DetalleRequisicionViewSet, NotificacionViewSet
)

# Inventario views
from inventario.views import (
    ProductoViewSet, LoteViewSet, RequisicionViewSet, CentroViewSet,
    MovimientoViewSet, dashboard_resumen, trazabilidad_producto,
    trazabilidad_lote, reporte_inventario, reporte_movimientos,
    reporte_caducidades, reportes_precarga,
    reporte_medicamentos_por_caducar, reporte_bajo_stock, reporte_consumo
)

router = DefaultRouter()

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

urlpatterns = [
    # Autenticacion
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('dev-autologin/', DevAutoLoginView.as_view(), name='dev-autologin'),
    
    # Router (incluye /usuarios/me/ como accion del UserViewSet)
    path('', include(router.urls)),

    # Dashboard y reportes
    path('dashboard/', dashboard_resumen, name='dashboard'),
    path('trazabilidad/producto/<str:clave>/', trazabilidad_producto, name='trazabilidad-producto'),
    path('trazabilidad/lote/<str:codigo>/', trazabilidad_lote, name='trazabilidad-lote'),
    path('reportes/inventario/', reporte_inventario, name='reporte-inventario'),
    path('reportes/movimientos/', reporte_movimientos, name='reporte-movimientos'),
    path('reportes/caducidades/', reporte_caducidades, name='reporte-caducidades'),
    path('reportes/medicamentos_por_caducar/', reporte_medicamentos_por_caducar, name='reporte-medicamentos-por-caducar'),
    path('reportes/bajo_stock/', reporte_bajo_stock, name='reporte-bajo-stock'),
    path('reportes/consumo/', reporte_consumo, name='reporte-consumo'),
    path('reportes/precarga/', reportes_precarga, name='reportes-precarga'),
]
