"""
Script para probar todos los endpoints de PDF del sistema
"""
import os
import sys
import django
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

BASE_URL = "http://127.0.0.1:8000/api"

def get_auth_token():
    """Obtener token de autenticación"""
    login_response = requests.post(f"{BASE_URL}/token/", json={
        'username': 'admin',
        'password': 'admin123'
    })
    if login_response.status_code == 200:
        return login_response.json().get('access')
    print(f"Error login: {login_response.status_code} - {login_response.text}")
    return None

def test_endpoint(name, url, token, params=None):
    """Probar un endpoint PDF"""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"URL: {url}")
    print(f"{'='*60}")
    
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            if 'pdf' in content_type:
                print(f"✅ PDF Size: {len(response.content)} bytes")
                return True
            elif 'json' in content_type:
                data = response.json()
                print(f"⚠️  Respuesta JSON (no PDF): {str(data)[:200]}...")
            else:
                print(f"⚠️  Tipo de respuesta inesperado: {content_type}")
        else:
            try:
                print(f"❌ Error: {response.json()}")
            except:
                print(f"❌ Error: {response.text[:200]}")
        return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("PRUEBA COMPLETA DE ENDPOINTS PDF")
    print("="*60)
    
    token = get_auth_token()
    if not token:
        print("No se pudo obtener token de autenticación")
        return
    
    print(f"\n✅ Token obtenido correctamente")
    
    # Obtener IDs de prueba
    from inventario.models import Requisicion, HojaRecoleccion, Producto, Movimiento
    
    requisicion = Requisicion.objects.first()
    hoja = HojaRecoleccion.objects.first()
    producto = Producto.objects.first()
    
    results = []
    
    # 1. Hoja de recolección desde Requisición
    if requisicion:
        success = test_endpoint(
            "Hoja de Recolección (Requisición)",
            f"{BASE_URL}/requisiciones/{requisicion.id}/hoja-recoleccion/",
            token
        )
        results.append(("Hoja Recolección (Req)", success))
    else:
        print("\n⚠️  No hay requisiciones para probar")
        results.append(("Hoja Recolección (Req)", None))
    
    # 2. PDF de Hoja de Recolección directa
    if hoja:
        success = test_endpoint(
            "PDF Hoja de Recolección (Direct)",
            f"{BASE_URL}/hojas-recoleccion/{hoja.id}/pdf/",
            token
        )
        results.append(("Hoja Recolección (Dir)", success))
    else:
        print("\n⚠️  No hay hojas de recolección para probar")
        results.append(("Hoja Recolección (Dir)", None))
    
    # 3. PDF de Rechazo
    req_rechazada = Requisicion.objects.filter(estado='rechazada').first()
    if req_rechazada:
        success = test_endpoint(
            "PDF de Rechazo",
            f"{BASE_URL}/requisiciones/{req_rechazada.id}/pdf-rechazo/",
            token
        )
        results.append(("PDF Rechazo", success))
    else:
        # Probar con cualquier requisición (debería funcionar igual)
        if requisicion:
            success = test_endpoint(
                "PDF de Rechazo (prueba)",
                f"{BASE_URL}/requisiciones/{requisicion.id}/pdf-rechazo/",
                token
            )
            results.append(("PDF Rechazo", success))
        else:
            results.append(("PDF Rechazo", None))
    
    # 4. Trazabilidad PDF
    if producto:
        success = test_endpoint(
            "Trazabilidad PDF",
            f"{BASE_URL}/movimientos/trazabilidad-pdf/",
            token,
            params={'producto_clave': producto.clave}
        )
        results.append(("Trazabilidad PDF", success))
    else:
        print("\n⚠️  No hay productos para probar trazabilidad")
        results.append(("Trazabilidad PDF", None))
    
    # 5. Auditoría PDF
    success = test_endpoint(
        "Auditoría PDF",
        f"{BASE_URL}/auditoria/exportar-pdf/",
        token
    )
    results.append(("Auditoría PDF", success))
    
    # Resumen
    print("\n" + "="*60)
    print("RESUMEN DE RESULTADOS")
    print("="*60)
    for name, success in results:
        if success is None:
            status = "⚠️  SIN DATOS"
        elif success:
            status = "✅ OK"
        else:
            status = "❌ ERROR"
        print(f"  {name}: {status}")

if __name__ == '__main__':
    main()
