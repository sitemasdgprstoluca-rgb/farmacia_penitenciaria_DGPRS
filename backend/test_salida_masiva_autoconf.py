"""
Prueba exhaustiva del flujo de salida masiva con auto-confirmación.
"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient

from core.models import Lote, Movimiento, Centro
from django.contrib.auth import get_user_model

User = get_user_model()


def test_salida_masiva_autoconfirmada():
    """Prueba completa del flujo de salida masiva auto-confirmada."""
    print("=" * 60)
    print("PRUEBA: SALIDA MASIVA AUTO-CONFIRMADA")
    print("=" * 60)
    
    # 1. Obtener datos de prueba
    lote = Lote.objects.filter(
        centro__isnull=True,  # Farmacia Central
        activo=True,
        cantidad_actual__gt=100
    ).first()
    
    if not lote:
        print("ERROR: No hay lotes disponibles para prueba")
        return False
    
    centro_destino = Centro.objects.get(id=8)  # CHALCO
    admin = User.objects.filter(is_superuser=True).first()
    
    stock_origen_antes = lote.cantidad_actual
    
    # Verificar si ya existe lote en destino
    lote_destino_antes = Lote.objects.filter(
        numero_lote=lote.numero_lote,
        producto=lote.producto,
        centro=centro_destino
    ).first()
    stock_destino_antes = lote_destino_antes.cantidad_actual if lote_destino_antes else 0
    
    print(f"\n1. ESTADO INICIAL:")
    print(f"   Lote origen: {lote.numero_lote}")
    print(f"   Producto: {lote.producto.clave}")
    print(f"   Stock origen: {stock_origen_antes}")
    print(f"   Centro destino: {centro_destino.nombre[:40]}")
    print(f"   Stock destino antes: {stock_destino_antes}")
    
    # 2. Ejecutar salida masiva usando APIClient
    client = APIClient()
    client.force_authenticate(user=admin)
    
    cantidad_a_enviar = 10
    
    data = {
        'centro_destino_id': centro_destino.id,
        'observaciones': 'Prueba auto-confirmacion',
        'auto_confirmar': True,
        'items': [
            {'lote_id': lote.id, 'cantidad': cantidad_a_enviar}
        ]
    }
    
    print(f"\n2. EJECUTANDO SALIDA MASIVA (cantidad: {cantidad_a_enviar})...")
    
    response = client.post('/api/salida-masiva/', data, format='json')
    
    print(f"\n3. RESULTADO:")
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 201:
        result = response.data
        print(f"   Success: {result.get('success')}")
        print(f"   Confirmado: {result.get('confirmado')}")
        print(f"   Grupo salida: {result.get('grupo_salida')}")
        
        # 4. Verificar cambios
        lote.refresh_from_db()
        stock_origen_despues = lote.cantidad_actual
        
        lote_destino = Lote.objects.filter(
            numero_lote=lote.numero_lote,
            producto=lote.producto,
            centro=centro_destino
        ).first()
        
        stock_destino_despues = lote_destino.cantidad_actual if lote_destino else 0
        
        print(f"\n4. VERIFICACION DE STOCK:")
        print(f"   Stock origen: {stock_origen_antes} -> {stock_origen_despues}")
        print(f"   Stock destino: {stock_destino_antes} -> {stock_destino_despues}")
        
        # Validaciones
        ok_origen = stock_origen_despues == stock_origen_antes - cantidad_a_enviar
        ok_destino = stock_destino_despues == stock_destino_antes + cantidad_a_enviar
        
        print(f"   Stock origen OK: {ok_origen}")
        print(f"   Stock destino OK: {ok_destino}")
        
        # 5. Verificar movimientos
        grupo = result.get('grupo_salida')
        movimientos = Movimiento.objects.filter(motivo__contains=grupo)
        
        print(f"\n5. MOVIMIENTOS REGISTRADOS ({movimientos.count()}):")
        for m in movimientos:
            print(f"   - {m.tipo.upper()}: cantidad={m.cantidad}")
            print(f"     Centro destino: {m.centro_destino}")
            print(f"     Motivo: {m.motivo[:60]}...")
        
        # Verificar que hay 2 movimientos: salida y entrada
        mov_salida = movimientos.filter(tipo='salida').first()
        mov_entrada = movimientos.filter(tipo='entrada').first()
        
        ok_movimientos = mov_salida and mov_entrada
        print(f"\n   Mov salida existe: {bool(mov_salida)}")
        print(f"   Mov entrada existe: {bool(mov_entrada)}")
        
        # Resultado final
        print("\n" + "=" * 60)
        if ok_origen and ok_destino and ok_movimientos:
            print("RESULTADO: PRUEBA EXITOSA ✓")
            return True
        else:
            print("RESULTADO: PRUEBA FALLIDA ✗")
            return False
    else:
        print(f"   ERROR: {response.data}")
        return False


def test_salida_masiva_sin_autoconfirmar():
    """Prueba de salida masiva SIN auto-confirmar (modo pendiente)."""
    print("\n" + "=" * 60)
    print("PRUEBA: SALIDA MASIVA SIN AUTO-CONFIRMAR (PENDIENTE)")
    print("=" * 60)
    
    lote = Lote.objects.filter(
        centro__isnull=True,
        activo=True,
        cantidad_actual__gt=50
    ).first()
    
    if not lote:
        print("ERROR: No hay lotes disponibles")
        return False
    
    centro_destino = Centro.objects.get(id=7)  # CUAUTITLAN
    admin = User.objects.filter(is_superuser=True).first()
    
    stock_origen_antes = lote.cantidad_actual
    
    print(f"\n1. ESTADO INICIAL:")
    print(f"   Lote: {lote.numero_lote}, Stock: {stock_origen_antes}")
    
    # Ejecutar con auto_confirmar=False usando APIClient
    client = APIClient()
    client.force_authenticate(user=admin)
    
    cantidad = 5
    
    data = {
        'centro_destino_id': centro_destino.id,
        'observaciones': 'Prueba sin auto-confirmar',
        'auto_confirmar': False,  # <-- No auto-confirmar
        'items': [
            {'lote_id': lote.id, 'cantidad': cantidad}
        ]
    }
    
    print(f"\n2. EJECUTANDO (auto_confirmar=False)...")
    response = client.post('/api/salida-masiva/', data, format='json')
    
    print(f"\n3. RESULTADO: Status {response.status_code}")
    
    if response.status_code == 201:
        result = response.data
        print(f"   Confirmado: {result.get('confirmado')}")  # Debe ser False
        
        lote.refresh_from_db()
        stock_despues = lote.cantidad_actual
        
        print(f"\n4. VERIFICACION:")
        print(f"   Stock origen: {stock_origen_antes} -> {stock_despues}")
        
        # En modo PENDIENTE, el stock NO debe cambiar
        ok_stock = stock_despues == stock_origen_antes
        print(f"   Stock sin cambio (pendiente): {ok_stock}")
        
        # Verificar que el movimiento está como PENDIENTE
        grupo = result.get('grupo_salida')
        mov = Movimiento.objects.filter(motivo__contains=grupo).first()
        es_pendiente = '[PENDIENTE]' in (mov.motivo or '') if mov else False
        print(f"   Movimiento PENDIENTE: {es_pendiente}")
        
        print("\n" + "=" * 60)
        if ok_stock and es_pendiente:
            print("RESULTADO: PRUEBA EXITOSA ✓")
            return True
        else:
            print("RESULTADO: PRUEBA FALLIDA ✗")
            return False
    else:
        print(f"   ERROR: {response.data}")
        return False


if __name__ == '__main__':
    print("\n" + "#" * 60)
    print("# SUITE DE PRUEBAS: SALIDA MASIVA")
    print("#" * 60)
    
    resultado1 = test_salida_masiva_autoconfirmada()
    resultado2 = test_salida_masiva_sin_autoconfirmar()
    
    print("\n" + "#" * 60)
    print("# RESUMEN FINAL")
    print("#" * 60)
    print(f"   Auto-confirmada: {'✓ PASS' if resultado1 else '✗ FAIL'}")
    print(f"   Sin confirmar:   {'✓ PASS' if resultado2 else '✗ FAIL'}")
    print("#" * 60)
