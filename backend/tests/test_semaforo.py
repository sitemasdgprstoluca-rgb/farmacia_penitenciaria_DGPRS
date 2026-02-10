"""
Script para probar el flujo completo de fecha_caducidad con semáforo
Ejecutar con: python manage.py runscript test_semaforo --script-args
O simplemente: python manage.py shell y luego exec(open('test_semaforo.py').read())
"""

from datetime import date, timedelta
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from core.models import Donacion, DetalleDonacion, ProductoDonacion

def main():
    User = get_user_model()
    admin = User.objects.filter(is_superuser=True).first()
    client = APIClient()
    client.force_authenticate(user=admin)

    # Limpiar pruebas anteriores
    Donacion.objects.filter(numero__startswith='TEST-SEMAFORO').delete()

    # Obtener productos
    prods = list(ProductoDonacion.objects.filter(activo=True)[:4])
    print(f'Productos disponibles: {len(prods)}')
    
    if len(prods) < 4:
        print('ERROR: Necesito al menos 4 productos en el catálogo de donaciones')
        return

    hoy = date.today()

    # Crear donacion
    don = Donacion.objects.create(
        numero='TEST-SEMAFORO-001',
        donante_nombre='Test Semaforo Caducidad',
        donante_tipo='empresa',
        fecha_donacion=hoy,
        recibido_por=admin,
        estado='pendiente'
    )

    # Escenarios de semaforo segun la logica del frontend:
    # diasRestantes < 0 -> VENCIDO
    # diasRestantes <= 30 -> CRITICO
    # diasRestantes <= 90 -> PROXIMO
    # diasRestantes > 90 -> VIGENTE
    
    escenarios = [
        (prods[0], -30, 'VENCIDO', 'LOTE-VENCIDO'),
        (prods[1], 15, 'CRITICO', 'LOTE-CRITICO'),
        (prods[2], 60, 'PROXIMO', 'LOTE-PROXIMO'),
        (prods[3], 180, 'VIGENTE', 'LOTE-VIGENTE'),
    ]

    print('\n=== Creando datos de prueba ===')
    for prod, dias, esperado, lote in escenarios:
        fecha_cad = hoy + timedelta(days=dias)
        DetalleDonacion.objects.create(
            donacion=don,
            producto_donacion=prod,
            numero_lote=lote,
            cantidad=100,
            cantidad_disponible=0,
            fecha_caducidad=fecha_cad,
            estado_producto='bueno'
        )
        print(f'  {lote}: {prod.clave} → caducidad: {fecha_cad} → Esperado: {esperado}')

    # Procesar para activar stock
    print('\n=== Procesando donación ===')
    resp = client.post(f'/api/donaciones/{don.id}/procesar/')
    print(f'Status: {resp.status_code}')

    # Verificar API
    print('\n=== Verificando respuesta API ===')
    resp = client.get('/api/detalle-donaciones/')
    data = resp.json()
    items = data.get('results', data) if isinstance(data, dict) else data

    print(f'Total items en inventario donaciones: {len(items)}')
    print('\nItems de prueba:')
    for item in items:
        lote = item.get('numero_lote', '')
        if lote and 'LOTE-' in lote:
            print(f"  {lote}:")
            print(f"    - fecha_caducidad: {item.get('fecha_caducidad')}")
            print(f"    - cantidad_disponible: {item.get('cantidad_disponible')}")
            print(f"    - estado_producto: {item.get('estado_producto')}")

    print(f'\nDonacion TEST-SEMAFORO-001 creada con ID: {don.id}')
    print('\nPara probar en frontend:')
    print('   1. Abre: http://localhost:5173/donaciones')
    print('   2. Ve a la pestana Inventario')
    print('   3. Busca los lotes: LOTE-VENCIDO, LOTE-CRITICO, LOTE-PROXIMO, LOTE-VIGENTE')
    print('   4. Verifica que cada uno muestre el semaforo correcto')
    
    return don.id

if __name__ == '__main__':
    main()
