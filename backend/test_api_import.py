"""
Script para probar la importación de productos vía API REST.
Simula exactamente lo que hace el frontend.
"""
import os
import sys
import django
import requests
from pathlib import Path

# Setup Django
sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

# Configuración
ARCHIVO_PLANTILLA = r"C:\Users\zarag\Downloads\REVISAR\Plantilla_Productos.xlsx"
API_URL = "http://localhost:8000/api/productos/importar-excel/"

def test_import_api():
    """Prueba la importación via API REST como lo hace el frontend."""
    
    # 1. Verificar que existe el archivo
    if not os.path.exists(ARCHIVO_PLANTILLA):
        print(f"❌ ERROR: No se encuentra el archivo: {ARCHIVO_PLANTILLA}")
        return
    
    print(f"✓ Archivo encontrado: {ARCHIVO_PLANTILLA}")
    file_size = os.path.getsize(ARCHIVO_PLANTILLA)
    print(f"  Tamaño: {file_size / 1024:.2f} KB")
    
    # 2. Obtener o crear usuario de farmacia para el test
    try:
        user = User.objects.filter(rol='farmacia').first()
        if not user:
            print("❌ ERROR: No hay usuario con rol 'farmacia'")
            print("   Crear uno con: python manage.py crear_admin.py")
            return
        
        print(f"✓ Usuario farmacia encontrado: {user.email}")
    except Exception as e:
        print(f"❌ ERROR al buscar usuario: {e}")
        return
    
    # 3. Obtener token de autenticación JWT (simulando login)
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    print(f"✓ Token JWT obtenido: {access_token[:30]}...")
    
    # 4. Preparar la petición multipart/form-data
    try:
        with open(ARCHIVO_PLANTILLA, 'rb') as f:
            files = {'file': (os.path.basename(ARCHIVO_PLANTILLA), f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            
            print(f"\n🔄 Enviando petición POST a {API_URL}...")
            print(f"   Headers: Authorization: Bearer {access_token[:30]}...")
            print(f"   Files: {os.path.basename(ARCHIVO_PLANTILLA)}")
            
            response = requests.post(API_URL, files=files, headers=headers)
            
            print(f"\n📊 RESPUESTA:")
            print(f"   Status Code: {response.status_code}")
            print(f"   Headers: {dict(response.headers)}")
            
            try:
                data = response.json()
                print(f"\n   Body (JSON):")
                import json
                print(json.dumps(data, indent=2, ensure_ascii=False))
                
                # Analizar resultado
                if response.status_code == 200:
                    print(f"\n✅ ÉXITO!")
                    print(f"   Total procesados: {data.get('registros_totales', 0)}")
                    print(f"   Exitosos: {data.get('registros_exitosos', 0)}")
                    print(f"   Fallidos: {data.get('registros_fallidos', 0)}")
                    
                    if data.get('errores'):
                        print(f"\n⚠️  Errores encontrados:")
                        for err in data['errores'][:5]:  # Mostrar primeros 5
                            print(f"      - {err}")
                else:
                    print(f"\n❌ ERROR en la importación")
                    print(f"   Mensaje: {data.get('error', 'Sin mensaje')}")
                    print(f"   Detalles: {data.get('mensaje', 'Sin detalles')}")
                    
            except Exception as e:
                print(f"   Body (texto plano): {response.text[:500]}")
                print(f"   Error al parsear JSON: {e}")
                
    except FileNotFoundError:
        print(f"❌ ERROR: Archivo no encontrado durante lectura: {ARCHIVO_PLANTILLA}")
    except requests.exceptions.ConnectionError:
        print(f"❌ ERROR: No se puede conectar a {API_URL}")
        print("   ¿Está el servidor Django corriendo? (python manage.py runserver)")
    except Exception as e:
        print(f"❌ ERROR inesperado: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    print("="*70)
    print("TEST DE IMPORTACIÓN DE PRODUCTOS VIA API REST")
    print("="*70)
    test_import_api()
    print("\n" + "="*70)
