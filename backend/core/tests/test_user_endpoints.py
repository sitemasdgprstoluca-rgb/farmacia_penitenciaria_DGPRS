import pytest
from rest_framework.test import APIClient
from django.urls import reverse


def _client_for(username: str, password: str):
    client = APIClient()
    resp = client.post(reverse("token_obtain_pair"), {"username": username, "password": password}, format="json")
    token = resp.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.mark.django_db
def test_me_endpoint_get(django_user_model):
    django_user_model.objects.create_user(username="meuser", password="Test1234", email="me@test.com")
    client = _client_for("meuser", "Test1234")
    r = client.get("/api/usuarios/me/")
    assert r.status_code == 200
    assert r.data["username"] == "meuser"


@pytest.mark.django_db
def test_me_endpoint_patch(django_user_model):
    django_user_model.objects.create_user(username="meuser2", password="Test1234", email="me2@test.com")
    client = _client_for("meuser2", "Test1234")
    r = client.patch("/api/usuarios/me/", {"first_name": "Nuevo"}, format="json")
    assert r.status_code == 200
    assert r.data["first_name"] == "Nuevo"


@pytest.mark.django_db
def test_me_endpoint_patch_telefono_cargo(django_user_model):
    """Test que se puede actualizar teléfono y cargo del perfil."""
    django_user_model.objects.create_user(username="meuser_profile", password="Test1234", email="profile@test.com")
    client = _client_for("meuser_profile", "Test1234")
    r = client.patch("/api/usuarios/me/", {
        "telefono": "5551234567",
        "cargo": "Jefe de Farmacia"
    }, format="json")
    assert r.status_code == 200
    assert r.data["telefono"] == "5551234567"
    assert r.data["cargo"] == "Jefe de Farmacia"


@pytest.mark.django_db
def test_change_password(django_user_model):
    """Test cambio de contraseña con nueva política de complejidad."""
    django_user_model.objects.create_user(username="meuser3", password="Test1234", email="me3@test.com")
    client = _client_for("meuser3", "Test1234")
    r = client.post("/api/usuarios/me/change-password/", {
        "old_password": "Test1234",
        "new_password": "NuevaPass1",  # Cumple: 8+ chars, mayúscula, número
        "confirm_password": "NuevaPass1"
    }, format="json")
    assert r.status_code == 200
    # Login con nueva contraseña
    resp2 = APIClient().post(reverse("token_obtain_pair"), {"username": "meuser3", "password": "NuevaPass1"}, format="json")
    assert resp2.status_code == 200


@pytest.mark.django_db
def test_change_password_requires_uppercase(django_user_model):
    """Test que nueva contraseña requiere mayúscula."""
    django_user_model.objects.create_user(username="meuser4", password="Test1234", email="me4@test.com")
    client = _client_for("meuser4", "Test1234")
    r = client.post("/api/usuarios/me/change-password/", {
        "old_password": "Test1234",
        "new_password": "nuevapass1",  # Sin mayúscula
        "confirm_password": "nuevapass1"
    }, format="json")
    assert r.status_code == 400
    assert "mayúscula" in r.data.get("error", "").lower()


@pytest.mark.django_db
def test_change_password_requires_number(django_user_model):
    """Test que nueva contraseña requiere número."""
    django_user_model.objects.create_user(username="meuser5", password="Test1234", email="me5@test.com")
    client = _client_for("meuser5", "Test1234")
    r = client.post("/api/usuarios/me/change-password/", {
        "old_password": "Test1234",
        "new_password": "NuevaPassSinNum",  # Sin número
        "confirm_password": "NuevaPassSinNum"
    }, format="json")
    assert r.status_code == 400
    assert "número" in r.data.get("error", "").lower()


@pytest.mark.django_db
def test_change_password_wrong_old_password(django_user_model):
    """Test que contraseña actual incorrecta falla."""
    django_user_model.objects.create_user(username="meuser6", password="Test1234", email="me6@test.com")
    client = _client_for("meuser6", "Test1234")
    r = client.post("/api/usuarios/me/change-password/", {
        "old_password": "PasswordIncorrecta1",
        "new_password": "NuevaPass1",
        "confirm_password": "NuevaPass1"
    }, format="json")
    assert r.status_code == 400
    assert "incorrecta" in r.data.get("error", "").lower()


@pytest.mark.django_db
def test_change_password_same_as_old(django_user_model):
    """Test que nueva contraseña debe ser diferente a la anterior."""
    django_user_model.objects.create_user(username="meuser7", password="Test1234", email="me7@test.com")
    client = _client_for("meuser7", "Test1234")
    r = client.post("/api/usuarios/me/change-password/", {
        "old_password": "Test1234",
        "new_password": "Test1234",  # Igual a la anterior
        "confirm_password": "Test1234"
    }, format="json")
    assert r.status_code == 400
    assert "diferente" in r.data.get("error", "").lower()
