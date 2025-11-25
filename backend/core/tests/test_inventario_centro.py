import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from core.models import Centro, Producto, Lote, Notificacion
from django.utils import timezone
from decimal import Decimal


def auth_client(username: str, password: str):
    client = APIClient()
    resp = client.post(reverse("token_obtain_pair"), {"username": username, "password": password}, format="json")
    token = resp.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.mark.django_db
def test_inventario_por_centro_incluye_lote_asignado(django_user_model):
    centro = Centro.objects.create(clave="C1", nombre="Centro 1")
    user = django_user_model.objects.create_user(
        username="centro_user",
        password="12345678",
        centro=centro,
        rol="centro",
        email="c1@test.com",
    )
    producto = Producto.objects.create(
        clave="P1",
        descripcion="Prod 1",
        unidad_medida="PIEZA",
        precio_unitario=Decimal("10.00"),
        stock_minimo=1,
    )
    Lote.objects.create(
        producto=producto,
        centro=centro,
        numero_lote="L1",
        fecha_caducidad=timezone.now().date(),
        cantidad_inicial=10,
        cantidad_actual=5,
        estado="disponible",
    )
    client = auth_client("centro_user", "12345678")
    resp = client.get(f"/api/centros/{centro.id}/inventario/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["centro_id"] == centro.id
    assert data["total_productos"] == 1
    assert data["inventario"][0]["cantidad_disponible"] == 5


@pytest.mark.django_db
def test_notificaciones_listado_autorizado(django_user_model):
    user = django_user_model.objects.create_user(
        username="notif_user",
        password="12345678",
        email="notif@test.com",
        rol="vista",
    )
    Notificacion.objects.create(
        usuario=user,
        titulo="Prueba",
        mensaje="Mensaje",
        tipo="info",
    )
    client = auth_client("notif_user", "12345678")
    resp = client.get("/api/notificaciones/")
    assert resp.status_code == 200
    body = resp.json()
    # Puede ser paginado o lista plana según configuración
    items = body.get("results", body)
    assert len(items) >= 1


@pytest.mark.django_db
def test_requisicion_rechaza_stock_insuficiente(django_user_model):
    centro = Centro.objects.create(clave="C2", nombre="Centro 2")
    user = django_user_model.objects.create_user(
        username="centro_user2",
        password="12345678",
        centro=centro,
        rol="centro",
        email="c2@test.com",
    )
    producto = Producto.objects.create(
        clave="P2",
        descripcion="Prod 2",
        unidad_medida="PIEZA",
        precio_unitario=Decimal("10.00"),
        stock_minimo=1,
    )
    # Lote con poco stock asignado al centro
    Lote.objects.create(
        producto=producto,
        centro=centro,
        numero_lote="L2",
        fecha_caducidad=timezone.now().date(),
        cantidad_inicial=2,
        cantidad_actual=2,
        estado="disponible",
    )
    client = auth_client("centro_user2", "12345678")
    payload = {
        "centro": centro.id,
        "items": [
            {"producto": producto.id, "cantidad_solicitada": 5}
        ]
    }
    resp = client.post("/api/requisiciones/", payload, format="json")
    assert resp.status_code == 400
    assert "Stock insuficiente" in str(resp.data)
