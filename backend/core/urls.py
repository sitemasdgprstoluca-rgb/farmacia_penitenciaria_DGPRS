from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, CentroViewSet, ProductoViewSet, LoteViewSet,
    RequisicionViewSet, MovimientoViewSet, DashboardViewSet, ReportesViewSet,
    TrazabilidadLoteView, TrazabilidadProductoView,
    ReportesInventarioView, ReportesMovimientosView, 
    ReportesCaducidadesView, ReportesPrecargaView, AuditoriaViewSet
)

router = DefaultRouter()
router.register(r'usuarios', UserViewSet)
router.register(r'centros', CentroViewSet)
router.register(r'productos', ProductoViewSet)
router.register(r'lotes', LoteViewSet)
router.register(r'requisiciones', RequisicionViewSet)
router.register(r'movimientos', MovimientoViewSet)
router.register(r'dashboard', DashboardViewSet, basename='dashboard')
router.register(r'reportes', ReportesViewSet, basename='reportes')
router.register(r'auditoria', AuditoriaViewSet, basename='auditoria')

urlpatterns = [
    path('', include(router.urls)),
    
    # Trazabilidad - ✅ CORREGIDO: usa numero_lote
    path(
        'trazabilidad/lote/<str:numero_lote>/',
        TrazabilidadLoteView.as_view(),
        name='trazabilidad-lote'
    ),
    path(
        'trazabilidad/producto/<str:clave>/',
        TrazabilidadProductoView.as_view(),
        name='trazabilidad-producto'
    ),
    
    # Reportes - ✅ NUEVO: Implementados
    path(
        'reportes/inventario/',
        ReportesInventarioView.as_view(),
        name='reportes-inventario'
    ),
    path(
        'reportes/movimientos/',
        ReportesMovimientosView.as_view(),
        name='reportes-movimientos'
    ),
    path(
        'reportes/caducidades/',
        ReportesCaducidadesView.as_view(),
        name='reportes-caducidades'
    ),
    path(
        'reportes/precarga/',
        ReportesPrecargaView.as_view(),
        name='reportes-precarga'
    ),
]
