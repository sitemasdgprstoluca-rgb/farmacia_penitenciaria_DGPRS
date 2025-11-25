import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from rest_framework.test import APIClient
from rest_framework import status

client = APIClient()
response = client.get('/api/v1/productos/')

print(f"Status Code: {response.status_code}")
print(f"Expected: {status.HTTP_401_UNAUTHORIZED}")
print(f"Response Data: {response.data}")
print(f"\nResponse keys: {list(response.data.keys())}")

# Ver si hay headers relevantes
print(f"\nWWW-Authenticate header: {response.get('WWW-Authenticate', 'NOT PRESENT')}")
