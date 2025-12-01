"""
Pytest configuration for the backend tests.
"""
import pytest
import django
from django.conf import settings


def pytest_configure():
    """Configure Django settings for pytest."""
    settings.DEBUG = False
    settings.TESTING = True


@pytest.fixture(scope='session')
def django_db_setup():
    """Ensure the test database is set up."""
    pass


@pytest.fixture
def api_client():
    """Create a DRF API client for testing."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, django_user_model):
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
def admin_user(django_user_model):
    """Create an admin user for testing."""
    return django_user_model.objects.create_superuser(
        username='admin',
        email='admin@test.com',
        password='adminpass123',
        rol='ADMIN'
    )
