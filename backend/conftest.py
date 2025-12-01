"""
Pytest configuration for the backend tests.
"""
import pytest
from django.conf import settings


def pytest_configure():
    """Configure Django settings for pytest."""
    settings.DEBUG = False
    settings.TESTING = True


# NOTE: Do not override django_db_setup - let pytest-django handle it


@pytest.fixture
def api_client():
    """Create a DRF API client for testing."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, django_user_model, db):
    """Create an authenticated API client."""
    user = django_user_model.objects.create_user(
        username='testuser',
        email='test@test.com',
        password='testpass123',
        rol='ADMIN'
    )
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def admin_user(django_user_model, db):
    """Create an admin user for testing."""
    return django_user_model.objects.create_superuser(
        username='admin',
        email='admin@test.com',
        password='adminpass123',
        rol='ADMIN'
    )
