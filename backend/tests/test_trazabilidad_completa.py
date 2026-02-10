# -*- coding: utf-8 -*-
"""
Test exhaustivo de trazabilidad y aritmética de stock
Verifica:
1. Sumas y restas de stock correctas
2. Trazabilidad por lote perfecta
3. Movimientos registrados correctamente
4. Consistencia de datos
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from django.db.models import Sum, F
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from core.models import Centro, Producto, Lote, Movimiento
from django.utils import timezone
from decimal import Decimal

User = get_user_model()

VERDE = '\033[92m'
ROJO = '\033[91m'
AMARILLO = '\033[93m'
RESET = '\033[0m'

def ok(msg):
    print(f"  {VERDE}✓{RESET} {msg}")

def fail(msg):
    print(f"  {ROJO}✗{RESET} {msg}")

def warn(msg):
    print(f"  {AMARILLO}⚠{RESET} {msg}")

def header(title):
    print(f"\n{'='*60}")
    print(f" {title}")
    print('='*60)


def test_aritmetica_stock():
    """Verifica que cantidad_actual = cantidad_inicial + entradas - salidas"""
    header("1. VERIFICACIÓN ARITMÉTICA DE STOCK")
    
    errores = []
    verificados = 0
    
    # Obtener todos los lotes activos con movimientos
    lotes_con_movimientos = Lote.objects.filter(
        movimientos__isnull=False
    ).distinct()[:50]  # Limitar a 50 para la prueba
    
    print(f"\n  Verificando {lotes_con_movimientos.count()} lotes con movimientos...")
    
    for lote in lotes_con_movimientos:
        # Calcular entradas y salidas desde movimientos
        movs = Movimiento.objects.filter(lote=lote)
        
        entradas = movs.filter(tipo='entrada').aggregate(
            total=Sum('cantidad')
        )['total'] or 0
        
        salidas = movs.filter(tipo='salida').aggregate(
            total=Sum('cantidad')
        )['total'] or 0
        
        ajustes_pos = movs.filter(tipo='ajuste', cantidad__gt=0).aggregate(
            total=Sum('cantidad')
        )['total'] or 0
        
        ajustes_neg = movs.filter(tipo='ajuste', cantidad__lt=0).aggregate(
            total=Sum('cantidad')
        )['total'] or 0
        
        # Stock calculado = inicial + entradas - salidas + ajustes
        # Nota: cantidad_inicial ya incluye la entrada inicial en algunos casos
        stock_calculado_desde_movs = entradas - salidas + ajustes_pos + ajustes_neg
        
        # Para lotes sin entrada inicial explícita, comparamos contra cantidad_actual
        diferencia = lote.cantidad_actual - stock_calculado_desde_movs
        
        verificados += 1
        
        # Si hay diferencia significativa, puede ser porque cantidad_inicial
        # representa el stock antes de movimientos
        if abs(diferencia) > 0 and diferencia != lote.cantidad_inicial:
            # Verificar si cantidad_inicial + movimientos = cantidad_actual
            stock_esperado = lote.cantidad_inicial + entradas - salidas + ajustes_pos + ajustes_neg
            
            if stock_esperado != lote.cantidad_actual:
                errores.append({
                    'lote': lote.numero_lote,
                    'producto': lote.producto.clave if lote.producto else 'N/A',
                    'cantidad_inicial': lote.cantidad_inicial,
                    'cantidad_actual': lote.cantidad_actual,
                    'entradas': entradas,
                    'salidas': salidas,
                    'ajustes': ajustes_pos + ajustes_neg,
                    'esperado': stock_esperado,
                    'diferencia': lote.cantidad_actual - stock_esperado
                })
    
    if errores:
        fail(f"Encontrados {len(errores)} lotes con discrepancias:")
        for e in errores[:5]:  # Mostrar solo primeros 5
            print(f"      Lote {e['lote']}: actual={e['cantidad_actual']}, esperado={e['esperado']}, diff={e['diferencia']}")
        return False
    else:
        ok(f"Todos los {verificados} lotes verificados tienen aritmética correcta")
        return True


def test_trazabilidad_lote():
    """Verifica trazabilidad completa de un lote específico"""
    header("2. TRAZABILIDAD POR LOTE")
    
    # Buscar un lote con varios movimientos
    lote = Lote.objects.annotate(
        num_movs=Sum('movimientos__cantidad')
    ).filter(
        movimientos__isnull=False,
        cantidad_actual__gt=0
    ).order_by('-num_movs').first()
    
    if not lote:
        warn("No hay lotes con movimientos para verificar")
        return True
    
    print(f"\n  Lote seleccionado: {lote.numero_lote}")
    print(f"  Producto: {lote.producto.clave if lote.producto else 'N/A'}")
    print(f"  Centro: {lote.centro.nombre if lote.centro else 'Farmacia Central'}")
    print(f"  Cantidad inicial: {lote.cantidad_inicial}")
    print(f"  Cantidad actual: {lote.cantidad_actual}")
    
    # Obtener todos los movimientos ordenados por fecha
    movimientos = Movimiento.objects.filter(lote=lote).order_by('fecha')
    
    print(f"\n  Movimientos ({movimientos.count()}):")
    
    saldo = lote.cantidad_inicial
    historial_ok = True
    
    for mov in movimientos:
        if mov.tipo == 'entrada':
            saldo += mov.cantidad
            signo = '+'
        elif mov.tipo == 'salida':
            saldo -= mov.cantidad
            signo = '-'
        else:  # ajuste
            saldo += mov.cantidad  # ajuste puede ser positivo o negativo
            signo = '+' if mov.cantidad >= 0 else ''
        
        fecha_str = mov.fecha.strftime('%Y-%m-%d %H:%M') if mov.fecha else 'N/A'
        usuario_str = mov.usuario.username if mov.usuario else 'Sistema'
        
        print(f"    [{fecha_str}] {mov.tipo.upper():8} {signo}{abs(mov.cantidad):>5} → Saldo: {saldo:>6} | {usuario_str}")
        
        # Verificar que el saldo nunca sea negativo
        if saldo < 0:
            fail(f"¡Saldo negativo detectado! ({saldo})")
            historial_ok = False
    
    # Verificar que el saldo final coincide con cantidad_actual
    if saldo == lote.cantidad_actual:
        ok(f"Saldo final ({saldo}) coincide con cantidad_actual ({lote.cantidad_actual})")
    else:
        fail(f"Saldo final ({saldo}) NO coincide con cantidad_actual ({lote.cantidad_actual})")
        historial_ok = False
    
    return historial_ok


def test_transferencias_centro():
    """Verifica que las transferencias a centros estén bien registradas"""
    header("3. VERIFICACIÓN DE TRANSFERENCIAS A CENTROS")
    
    # Buscar movimientos de transferencia recientes
    transferencias = Movimiento.objects.filter(
        tipo='salida',
        centro_destino__isnull=False,
        referencia__startswith='SAL-'
    ).order_by('-fecha')[:10]
    
    if not transferencias.exists():
        warn("No hay transferencias recientes para verificar")
        return True
    
    print(f"\n  Últimas {transferencias.count()} transferencias:")
    
    errores = []
    
    for mov in transferencias:
        grupo_salida = mov.referencia
        centro_destino = mov.centro_destino
        
        # Buscar el movimiento de entrada correspondiente
        entrada = Movimiento.objects.filter(
            tipo='entrada',
            referencia=grupo_salida,
            lote__centro=centro_destino
        ).first()
        
        print(f"\n    {grupo_salida}:")
        print(f"      SALIDA: {mov.cantidad} unidades de lote {mov.lote.numero_lote[:20]}...")
        print(f"      Centro destino: {centro_destino.nombre}")
        
        if entrada:
            if entrada.cantidad == mov.cantidad:
                ok(f"ENTRADA correspondiente encontrada: {entrada.cantidad} unidades")
            else:
                fail(f"ENTRADA con cantidad diferente: {entrada.cantidad} vs {mov.cantidad}")
                errores.append(f"{grupo_salida}: cantidades no coinciden")
        else:
            # Verificar si el lote existe en el centro destino
            lote_destino = Lote.objects.filter(
                numero_lote=mov.lote.numero_lote,
                producto=mov.lote.producto,
                centro=centro_destino
            ).first()
            
            if lote_destino:
                ok(f"Lote espejo encontrado en {centro_destino.nombre}: {lote_destino.cantidad_actual} unidades")
            else:
                fail(f"No se encontró lote espejo ni movimiento de entrada")
                errores.append(f"{grupo_salida}: sin lote espejo")
    
    if errores:
        fail(f"{len(errores)} errores en transferencias")
        return False
    else:
        ok("Todas las transferencias verificadas correctamente")
        return True


def test_consistencia_stock_global():
    """Verifica consistencia global: suma de lotes = stock reportado"""
    header("4. CONSISTENCIA STOCK GLOBAL")
    
    # Para algunos productos, verificar que la suma de lotes coincide
    productos_con_lotes = Producto.objects.filter(
        lotes__cantidad_actual__gt=0
    ).distinct()[:10]
    
    print(f"\n  Verificando {productos_con_lotes.count()} productos...")
    
    errores = []
    
    for producto in productos_con_lotes:
        # Suma de stock en todos los lotes del producto
        stock_total_lotes = Lote.objects.filter(
            producto=producto,
            activo=True
        ).aggregate(total=Sum('cantidad_actual'))['total'] or 0
        
        # Stock en lotes de Farmacia Central (centro=NULL)
        stock_farmacia = Lote.objects.filter(
            producto=producto,
            centro__isnull=True,
            activo=True
        ).aggregate(total=Sum('cantidad_actual'))['total'] or 0
        
        # Stock en centros
        stock_centros = Lote.objects.filter(
            producto=producto,
            centro__isnull=False,
            activo=True
        ).aggregate(total=Sum('cantidad_actual'))['total'] or 0
        
        # Verificar que farmacia + centros = total
        if stock_farmacia + stock_centros != stock_total_lotes:
            errores.append({
                'producto': producto.clave,
                'farmacia': stock_farmacia,
                'centros': stock_centros,
                'total': stock_total_lotes
            })
        else:
            print(f"    {producto.clave}: Farmacia={stock_farmacia}, Centros={stock_centros}, Total={stock_total_lotes} ✓")
    
    if errores:
        fail(f"{len(errores)} productos con inconsistencia")
        for e in errores:
            print(f"      {e['producto']}: {e['farmacia']} + {e['centros']} ≠ {e['total']}")
        return False
    else:
        ok("Stock global consistente en todos los productos verificados")
        return True


def test_movimientos_tienen_trazabilidad():
    """Verifica que todos los movimientos tengan datos de trazabilidad"""
    header("5. TRAZABILIDAD EN MOVIMIENTOS")
    
    # Verificar movimientos recientes
    movimientos_recientes = Movimiento.objects.order_by('-fecha')[:100]
    
    sin_usuario = 0
    sin_motivo = 0
    sin_lote = 0
    transferencias_sin_referencia = 0
    
    for mov in movimientos_recientes:
        if not mov.usuario:
            sin_usuario += 1
        if not mov.motivo:
            sin_motivo += 1
        if not mov.lote:
            sin_lote += 1
        if mov.centro_destino and not mov.referencia:
            transferencias_sin_referencia += 1
    
    print(f"\n  Analizados: {movimientos_recientes.count()} movimientos recientes")
    
    problemas = False
    
    if sin_usuario > 0:
        warn(f"Movimientos sin usuario: {sin_usuario}")
        problemas = True
    else:
        ok("Todos los movimientos tienen usuario")
    
    if sin_motivo > 0:
        warn(f"Movimientos sin motivo: {sin_motivo}")
    else:
        ok("Todos los movimientos tienen motivo")
    
    if sin_lote > 0:
        fail(f"Movimientos sin lote: {sin_lote}")
        problemas = True
    else:
        ok("Todos los movimientos tienen lote")
    
    if transferencias_sin_referencia > 0:
        warn(f"Transferencias sin referencia de grupo: {transferencias_sin_referencia}")
    else:
        ok("Todas las transferencias tienen referencia de grupo")
    
    return not problemas


def test_salida_masiva_integridad():
    """Test de integridad de una salida masiva real"""
    header("6. TEST EN VIVO: SALIDA MASIVA")
    
    client = APIClient()
    admin = User.objects.filter(is_superuser=True).first()
    
    if not admin:
        warn("No hay usuario admin para prueba")
        return True
    
    # Buscar un lote con stock suficiente en Farmacia Central
    lote_origen = Lote.objects.filter(
        centro__isnull=True,
        cantidad_actual__gte=20,
        activo=True
    ).select_related('producto').first()
    
    if not lote_origen:
        warn("No hay lotes con stock suficiente para prueba")
        return True
    
    centro = Centro.objects.exclude(nombre__icontains='farmacia').first()
    if not centro:
        warn("No hay centro destino disponible")
        return True
    
    # Guardar estados iniciales
    stock_inicial_origen = lote_origen.cantidad_actual
    
    lote_destino_inicial = Lote.objects.filter(
        numero_lote=lote_origen.numero_lote,
        producto=lote_origen.producto,
        centro=centro
    ).first()
    stock_inicial_destino = lote_destino_inicial.cantidad_actual if lote_destino_inicial else 0
    
    cantidad_transferir = 5
    
    print(f"\n  Datos de prueba:")
    print(f"    Lote: {lote_origen.numero_lote}")
    print(f"    Producto: {lote_origen.producto.clave}")
    print(f"    Centro destino: {centro.nombre}")
    print(f"    Stock origen antes: {stock_inicial_origen}")
    print(f"    Stock destino antes: {stock_inicial_destino}")
    print(f"    Cantidad a transferir: {cantidad_transferir}")
    
    # Ejecutar salida masiva
    client.force_authenticate(user=admin)
    
    response = client.post('/api/salida-masiva/', {
        'centro_destino_id': centro.id,
        'observaciones': 'Test de integridad automatizado',
        'auto_confirmar': True,
        'items': [
            {'lote_id': lote_origen.id, 'cantidad': cantidad_transferir}
        ]
    }, format='json')
    
    if response.status_code != 201:
        fail(f"Error en salida masiva: {response.status_code}")
        print(f"    Respuesta: {response.data}")
        return False
    
    grupo_salida = response.data.get('grupo_salida')
    print(f"\n  Grupo salida: {grupo_salida}")
    
    # Refrescar datos
    lote_origen.refresh_from_db()
    
    lote_destino = Lote.objects.filter(
        numero_lote=lote_origen.numero_lote,
        producto=lote_origen.producto,
        centro=centro
    ).first()
    
    # Verificaciones
    errores = []
    
    # 1. Stock origen decrementó correctamente
    stock_esperado_origen = stock_inicial_origen - cantidad_transferir
    if lote_origen.cantidad_actual == stock_esperado_origen:
        ok(f"Stock origen: {stock_inicial_origen} - {cantidad_transferir} = {lote_origen.cantidad_actual}")
    else:
        fail(f"Stock origen: esperado {stock_esperado_origen}, actual {lote_origen.cantidad_actual}")
        errores.append("stock_origen")
    
    # 2. Stock destino incrementó correctamente
    if lote_destino:
        stock_esperado_destino = stock_inicial_destino + cantidad_transferir
        if lote_destino.cantidad_actual == stock_esperado_destino:
            ok(f"Stock destino: {stock_inicial_destino} + {cantidad_transferir} = {lote_destino.cantidad_actual}")
        else:
            fail(f"Stock destino: esperado {stock_esperado_destino}, actual {lote_destino.cantidad_actual}")
            errores.append("stock_destino")
    else:
        fail("Lote destino no creado")
        errores.append("lote_destino")
    
    # 3. Movimiento de salida existe
    mov_salida = Movimiento.objects.filter(
        lote=lote_origen,
        tipo='salida',
        referencia=grupo_salida
    ).first()
    
    if mov_salida:
        ok(f"Movimiento SALIDA registrado: {mov_salida.cantidad} unidades")
    else:
        fail("Movimiento de SALIDA no encontrado")
        errores.append("mov_salida")
    
    # 4. Movimiento de entrada existe
    mov_entrada = Movimiento.objects.filter(
        lote=lote_destino,
        tipo='entrada',
        referencia=grupo_salida
    ).first() if lote_destino else None
    
    if mov_entrada:
        ok(f"Movimiento ENTRADA registrado: {mov_entrada.cantidad} unidades")
    else:
        fail("Movimiento de ENTRADA no encontrado")
        errores.append("mov_entrada")
    
    # 5. Las cantidades coinciden
    if mov_salida and mov_entrada:
        if mov_salida.cantidad == mov_entrada.cantidad == cantidad_transferir:
            ok(f"Cantidades consistentes: SALIDA={mov_salida.cantidad}, ENTRADA={mov_entrada.cantidad}")
        else:
            fail(f"Cantidades inconsistentes: SALIDA={mov_salida.cantidad}, ENTRADA={mov_entrada.cantidad}")
            errores.append("cantidades")
    
    # 6. Trazabilidad de usuarios
    if mov_salida and mov_salida.usuario == admin:
        ok(f"Usuario registrado correctamente: {admin.username}")
    else:
        warn("Usuario no registrado en movimiento")
    
    return len(errores) == 0


def test_query_filtros_movimientos():
    """Verifica que los filtros de movimientos funcionen"""
    header("7. FILTROS DE BÚSQUEDA")
    
    client = APIClient()
    admin = User.objects.filter(is_superuser=True).first()
    client.force_authenticate(user=admin)
    
    errores = []
    
    # Test filtro por referencia
    response = client.get('/api/movimientos/', {'referencia': 'SAL-'})
    if response.status_code == 200:
        count = response.data.get('count', len(response.data.get('results', [])))
        ok(f"Filtro por referencia funciona: {count} resultados")
    else:
        fail(f"Error en filtro por referencia: {response.status_code}")
        errores.append("filtro_referencia")
    
    # Test filtro por tipo
    response = client.get('/api/movimientos/', {'tipo': 'salida'})
    if response.status_code == 200:
        count = response.data.get('count', len(response.data.get('results', [])))
        ok(f"Filtro por tipo funciona: {count} salidas")
    else:
        fail(f"Error en filtro por tipo: {response.status_code}")
        errores.append("filtro_tipo")
    
    # Test filtro por centro_destino
    centro = Centro.objects.first()
    if centro:
        response = client.get('/api/movimientos/', {'centro_destino': centro.id})
        if response.status_code == 200:
            count = response.data.get('count', len(response.data.get('results', [])))
            ok(f"Filtro por centro_destino funciona: {count} resultados")
        else:
            fail(f"Error en filtro por centro_destino: {response.status_code}")
            errores.append("filtro_centro_destino")
    
    # Test búsqueda general
    response = client.get('/api/movimientos/', {'search': 'transferencia'})
    if response.status_code == 200:
        count = response.data.get('count', len(response.data.get('results', [])))
        ok(f"Búsqueda general funciona: {count} resultados para 'transferencia'")
    else:
        fail(f"Error en búsqueda: {response.status_code}")
        errores.append("busqueda")
    
    return len(errores) == 0


if __name__ == '__main__':
    print("\n" + "#"*60)
    print("# VERIFICACIÓN COMPLETA DE TRAZABILIDAD Y STOCK")
    print("#"*60)
    
    resultados = {
        'aritmetica_stock': test_aritmetica_stock(),
        'trazabilidad_lote': test_trazabilidad_lote(),
        'transferencias_centro': test_transferencias_centro(),
        'consistencia_global': test_consistencia_stock_global(),
        'trazabilidad_movs': test_movimientos_tienen_trazabilidad(),
        'salida_masiva_vivo': test_salida_masiva_integridad(),
        'filtros_busqueda': test_query_filtros_movimientos(),
    }
    
    # Resumen
    print("\n" + "#"*60)
    print("# RESUMEN FINAL")
    print("#"*60)
    
    total = len(resultados)
    exitosos = sum(1 for v in resultados.values() if v)
    
    for nombre, resultado in resultados.items():
        status = f"{VERDE}✓ PASS{RESET}" if resultado else f"{ROJO}✗ FAIL{RESET}"
        print(f"  {nombre}: {status}")
    
    print(f"\n  Total: {exitosos}/{total} pruebas exitosas")
    print("#"*60)
    
    exit(0 if exitosos == total else 1)
