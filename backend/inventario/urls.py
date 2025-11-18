from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'productos', views.ProductoViewSet, basename='producto')
router.register(r'lotes', views.LoteViewSet, basename='lote')
router.register(r'centros', views.CentroViewSet, basename='centro')
router.register(r'movimientos', views.MovimientoViewSet, basename='movimiento')
router.register(r'requisiciones', views.RequisicionViewSet, basename='requisicion')
router.register(r'usuarios', views.UserViewSet, basename='usuario')  # ← AGREGAR

urlpatterns = [
    path('', include(router.urls)),
    
    # Dashboard
    path('dashboard/', views.dashboard_resumen, name='dashboard'),
    
    # Trazabilidad
    path('trazabilidad/producto/<str:clave>/', views.trazabilidad_producto, name='trazabilidad-producto'),
    path('trazabilidad/lote/<str:codigo>/', views.trazabilidad_lote, name='trazabilidad-lote'),
    
    # Reportes
    path('reportes/inventario/', views.reporte_inventario, name='reporte-inventario'),
    path('reportes/movimientos/', views.reporte_movimientos, name='reporte-movimientos'),
    path('reportes/caducidades/', views.reporte_caducidades, name='reporte-caducidades'),
    path('reportes/precarga/', views.reportes_precarga, name='reportes-precarga'),
]
