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
    django_user_model.objects.create_user(username="meuser", password="12345678", email="me@test.com")
    client = _client_for("meuser", "12345678")
    r = client.get("/api/usuarios/me/")
    assert r.status_code == 200
    assert r.data["username"] == "meuser"


@pytest.mark.django_db
def test_me_endpoint_patch(django_user_model):
    django_user_model.objects.create_user(username="meuser2", password="12345678", email="me2@test.com")
    client = _client_for("meuser2", "12345678")
    r = client.patch("/api/usuarios/me/", {"first_name": "Nuevo"}, format="json")
    assert r.status_code == 200
    assert r.data["first_name"] == "Nuevo"


@pytest.mark.django_db
def test_change_password(django_user_model):
    django_user_model.objects.create_user(username="meuser3", password="12345678", email="me3@test.com")
    client = _client_for("meuser3", "12345678")
    r = client.post("/api/usuarios/me/change-password/", {
        "old_password": "12345678",
        "new_password": "87654321",
        "confirm_password": "87654321"
    }, format="json")
    assert r.status_code == 200
    # Login con nueva contraseña
    resp2 = APIClient().post(reverse("token_obtain_pair"), {"username": "meuser3", "password": "87654321"}, format="json")
    assert resp2.status_code == 200
