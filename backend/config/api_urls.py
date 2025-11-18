"""
URLs API v1
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

# Core views
from core.views import (
    CustomTokenObtainPairView, LogoutView, UserProfileView,
    UserViewSet, ImportacionLogViewSet, AuditoriaLogViewSet,
    DetalleRequisicionViewSet
)

# Inventario views
from inventario.views import (
    ProductoViewSet, LoteViewSet, RequisicionViewSet,
    MovimientoViewSet
)

# Router
router = DefaultRouter()

# Core
router.register(r'usuarios', UserViewSet, basename='usuario')
router.register(r'importaciones', ImportacionLogViewSet, basename='importacion')
router.register(r'auditoria', AuditoriaLogViewSet, basename='auditoria')

# Inventario
router.register(r'productos', ProductoViewSet, basename='producto')
router.register(r'lotes', LoteViewSet, basename='lote')
router.register(r'requisiciones', RequisicionViewSet, basename='requisicion')
router.register(r'detalles-requisicion', DetalleRequisicionViewSet, basename='detalle-requisicion')
router.register(r'movimientos', MovimientoViewSet, basename='movimiento')

urlpatterns = [
    # Autenticación
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('me/', UserProfileView.as_view(), name='me'),
    
    # Router
    path('', include(router.urls)),
]
