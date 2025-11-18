from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse

router = DefaultRouter()
router.register(r'usuarios', views.UsuariosViewSet, basename='usuario')
router.register(r'centros', views.CentroViewSet, basename='centro')
router.register(r'productos', views.ProductoViewSet, basename='producto')
router.register(r'lotes', views.LoteViewSet, basename='lote')
router.register(r'movimientos', views.MovimientoViewSet, basename='movimiento')
router.register(r'requisiciones', views.RequisicionViewSet, basename='requisicion')


@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({'detail': 'CSRF cookie set'})


urlpatterns = [
    path('', include(router.urls)),
    path('me/', views.MeView.as_view(), name='me'),
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('trazabilidad/producto/<str:clave>/', views.TrazabilidadProductoView.as_view(), name='trazabilidad-producto'),
    path('trazabilidad/lote/<str:codigo>/', views.TrazabilidadLoteView.as_view(), name='trazabilidad-lote'),
    path('reportes/precarga/', views.ReportesPrecargaView.as_view(), name='reportes-precarga'),
    path('csrf/', get_csrf_token, name='csrf'),  # Nueva ruta
]
