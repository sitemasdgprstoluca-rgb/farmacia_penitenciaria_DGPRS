import os
import django
import sys
from io import BytesIO
import openpyxl

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from rest_framework.test import APIRequestFactory
from rest_framework.request import Request
from inventario.views.productos import ProductoViewSet
from inventario.views.lotes import LoteViewSet
from core.models import User

def verify_exports():
    factory = APIRequestFactory()
    
    # Create a dummy user for permissions
    try:
        user = User.objects.first()
        if not user:
            print("No users found in DB. Creating dummy user.")
            user = User.objects.create_superuser('testadmin', 'test@example.com', 'pass')
    except Exception as e:
        print(f"Error getting user: {e}")
        return

    print("--- Verifying Productos Export ---")
    req_prod = factory.get('/api/productos/exportar-excel/')
    req_prod.user = user
    request_prod = Request(req_prod)
    
    view_prod = ProductoViewSet()
    view_prod.setup(request_prod, action='exportar_excel')
    
    response_prod = view_prod.exportar_excel(request_prod)
    
    if response_prod.status_code != 200:
        print(f"FAILED: Status code {response_prod.status_code}")
        return

    wb_prod = openpyxl.load_workbook(BytesIO(response_prod.content))
    ws_prod = wb_prod.active
    
    headers_prod = [cell.value for cell in ws_prod[1]]
    expected_prod = [
        'Clave', 'Nombre', 'Nombre Comercial', 
        'Unidad de Medida', 'Stock Mínimo', 'Categoría', 'Presentación',
        'Descripción Adicional', 'Sustancia Activa', 'Concentración', 'Vía de Administración',
        'Requiere Receta', 'Es Controlado'
    ]
    
    print(f"Prod Headers Found: {headers_prod}")
    
    if headers_prod == expected_prod:
        print("✅ PRODUCTOS EXPORT HEADERS MATCH!")
    else:
        print("❌ PRODUCTOS EXPORT HEADERS MISMATCH!")
        print(f"Expected: {expected_prod}")
        print(f"Got:      {headers_prod}")

    print("\n--- Verifying Lotes Export ---")
    req_lote = factory.get('/api/lotes/exportar-excel/')
    req_lote.user = user
    request_lote = Request(req_lote)
    
    view_lote = LoteViewSet()
    view_lote.setup(request_lote, action='exportar_excel')
    
    response_lote = view_lote.exportar_excel(request_lote)
    
    if response_lote.status_code != 200:
        print(f"FAILED: Status code {response_lote.status_code}")
        return

    wb_lote = openpyxl.load_workbook(BytesIO(response_lote.content))
    ws_lote = wb_lote.active
    
    headers_lote = [cell.value for cell in ws_lote[1]]
    expected_lote = [
        'Producto', 'Presentación', 'Código de Lote', 'Fecha de Caducidad',
        'Cantidad Inicial', 'Cantidad Actual', 'Precio Unitario', 'Fecha de Fabricación',
        'Ubicación', 'Número de Contrato', 'Marca / Laboratorio', 'Lote activo'
    ]
    
    print(f"Lote Headers Found: {headers_lote}")
    
    if headers_lote == expected_lote:
        print("✅ LOTES EXPORT HEADERS MATCH!")
    else:
        print("❌ LOTES EXPORT HEADERS MISMATCH!")
        print(f"Expected: {expected_lote}")
        print(f"Got:      {headers_lote}")

if __name__ == '__main__':
    verify_exports()
