# filepath: apps/inventario/api_urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ProductoViewSet,
    LoteViewSet,
    MovimientoViewSet,
    dashboard_resumen,
    user_info,
    importar_productos_excel,
    reportes_movimientos,   # 👈 solo este, ya NO importamos reportes_movimientos_pdf
)

router = DefaultRouter()
router.register(r"productos", ProductoViewSet, basename="producto")
router.register(r"lotes", LoteViewSet, basename="lote")
router.register(r"movimientos", MovimientoViewSet, basename="movimiento")

urlpatterns = [
    path("", include(router.urls)),
    path("dashboard-resumen/", dashboard_resumen, name="dashboard_resumen"),
    path("user-info/", user_info, name="user_info"),
    path(
        "importar-productos-excel/",
        importar_productos_excel,
        name="importar_productos_excel",
    ),
    # Endpoint de reportes (JSON y PDF según ?formato=)
    path(
        "reportes/movimientos/",
        reportes_movimientos,
        name="reportes_movimientos",
    ),
]
