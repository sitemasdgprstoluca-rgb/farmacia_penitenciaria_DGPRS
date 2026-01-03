# -*- coding: utf-8 -*-
"""
Script para limpiar donaciones de prueba del servidor.
Elimina donaciones que fueron creadas erróneamente con productos del inventario ordinario.

Ejecutar: python limpiar_donaciones_prueba.py [URL_BASE]
"""
import sys
import requests

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else 'https://farmacia-penitenciaria.onrender.com'

def limpiar_donaciones():
    print(f"\n{'='*60}")
    print("  LIMPIEZA DE DONACIONES DE PRUEBA")
    print(f"{'='*60}\n")
    print(f"Servidor: {BASE_URL}")
    
    # 1. Autenticar
    print("\n[1] Autenticando...")
    credenciales = [
        ('admin', 'admin123'),
        ('admin', 'Admin123!'),
    ]
    
    token = None
    for user, pwd in credenciales:
        try:
            response = requests.post(
                f'{BASE_URL}/api/token/',
                json={'username': user, 'password': pwd},
                timeout=10
            )
            if response.status_code == 200:
                token = response.json().get('access')
                print(f"✓ Autenticado como: {user}")
                break
        except Exception as e:
            pass
    
    if not token:
        print("✗ No se pudo autenticar")
        return
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # 2. Obtener todas las donaciones
    print("\n[2] Obteniendo donaciones...")
    try:
        response = requests.get(
            f'{BASE_URL}/api/donaciones/?page_size=100',
            headers=headers,
            timeout=30
        )
        if response.status_code != 200:
            print(f"✗ Error obteniendo donaciones: {response.status_code}")
            return
        
        data = response.json()
        donaciones = data.get('results', data) if isinstance(data, dict) else data
        print(f"✓ Encontradas {len(donaciones)} donaciones")
    except Exception as e:
        print(f"✗ Error: {e}")
        return
    
    # 3. Identificar donaciones de prueba (las que tienen "Empresa Prueba" o números de prueba)
    print("\n[3] Identificando donaciones de prueba...")
    donaciones_a_eliminar = []
    
    for don in donaciones:
        donante = don.get('donante_nombre', '')
        numero = don.get('numero', '')
        
        # Criterios para identificar donaciones de prueba
        es_prueba = (
            'Prueba' in donante or
            'prueba' in donante.lower() or
            'TEST' in donante.upper() or
            numero.startswith('20260103-')  # Donaciones creadas hoy por las pruebas
        )
        
        if es_prueba:
            donaciones_a_eliminar.append({
                'id': don.get('id'),
                'numero': numero,
                'donante': donante,
                'estado': don.get('estado')
            })
    
    print(f"✓ Identificadas {len(donaciones_a_eliminar)} donaciones de prueba")
    
    if not donaciones_a_eliminar:
        print("\n✓ No hay donaciones de prueba que eliminar")
        return
    
    # 4. Mostrar las donaciones a eliminar
    print("\n[4] Donaciones a eliminar:")
    for don in donaciones_a_eliminar[:10]:
        print(f"   - {don['numero']} | {don['donante'][:30]} | Estado: {don['estado']}")
    if len(donaciones_a_eliminar) > 10:
        print(f"   ... y {len(donaciones_a_eliminar) - 10} más")
    
    # 5. Confirmar eliminación
    print(f"\n¿Eliminar {len(donaciones_a_eliminar)} donaciones de prueba? (s/n): ", end='')
    confirmar = input().strip().lower()
    
    if confirmar != 's':
        print("Cancelado por el usuario")
        return
    
    # 6. Eliminar donaciones
    print("\n[5] Eliminando donaciones...")
    eliminadas = 0
    errores = 0
    
    for don in donaciones_a_eliminar:
        try:
            response = requests.delete(
                f'{BASE_URL}/api/donaciones/{don["id"]}/',
                headers=headers,
                timeout=10
            )
            if response.status_code in [200, 204]:
                eliminadas += 1
                print(f"   ✓ Eliminada: {don['numero']}")
            else:
                errores += 1
                print(f"   ✗ Error {response.status_code} eliminando {don['numero']}: {response.text[:100]}")
        except Exception as e:
            errores += 1
            print(f"   ✗ Excepción eliminando {don['numero']}: {e}")
    
    # 7. Resumen
    print(f"\n{'='*60}")
    print("  RESUMEN DE LIMPIEZA")
    print(f"{'='*60}")
    print(f"  Eliminadas: {eliminadas}")
    print(f"  Errores: {errores}")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    limpiar_donaciones()
