"""
Test real de API usando requests contra el servidor en localhost:8000
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

def test_login_and_api():
    print("="*60)
    print("TEST API REAL")
    print("="*60)
    
    # 1. Login para obtener token
    print("\n1. Probando login...")
    try:
        response = requests.post(
            f"{BASE_URL}/token/",
            json={"username": "admin", "password": "admin123"},
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            token = data.get('access') or data.get('token')
            if token:
                print(f"   Token obtenido: {token[:50]}...")
            else:
                print(f"   Respuesta: {data}")
                # Intentar con otra estructura
                token = data.get('data', {}).get('access')
                if token:
                    print(f"   Token (data.access): {token[:50]}...")
        else:
            print(f"   Error: {response.text[:200]}")
            return
    except requests.exceptions.ConnectionError:
        print("   ERROR: No se puede conectar al servidor.")
        print("   Asegúrate de que el servidor está corriendo en localhost:8000")
        return
    except Exception as e:
        print(f"   ERROR: {e}")
        return
    
    if not token:
        print("\n   No se pudo obtener token. Probando con credenciales diferentes...")
        # Intentar crear un token directamente
        from django.contrib.auth import get_user_model
        from rest_framework_simplejwt.tokens import RefreshToken
        User = get_user_model()
        admin = User.objects.filter(username='admin').first()
        if admin:
            refresh = RefreshToken.for_user(admin)
            token = str(refresh.access_token)
            print(f"   Token generado directamente: {token[:50]}...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Probar endpoints
    endpoints = [
        "/productos/",
        "/lotes/",
        "/movimientos/",
        "/centros/",
        "/requisiciones/",
    ]
    
    for endpoint in endpoints:
        print(f"\n2. Probando {endpoint}...")
        try:
            response = requests.get(
                f"{BASE_URL}{endpoint}",
                headers=headers,
                timeout=5
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    count = data.get('count', len(data.get('results', [])))
                    results = data.get('results', [])
                    print(f"   Count: {count}")
                    if results:
                        print(f"   Primer item: {json.dumps(results[0], indent=2, default=str)[:200]}...")
                    else:
                        print(f"   Sin resultados. Keys: {list(data.keys())}")
                elif isinstance(data, list):
                    print(f"   Items: {len(data)}")
            else:
                print(f"   Error: {response.text[:300]}")
        except Exception as e:
            print(f"   ERROR: {e}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    test_login_and_api()
