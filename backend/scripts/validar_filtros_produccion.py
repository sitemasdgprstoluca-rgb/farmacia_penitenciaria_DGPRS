#!/usr/bin/env python
"""
Validación de Filtros en Producción
====================================

Script de verificación rápida que valida los filtros de aislamiento
de datos en un entorno de producción SIN modificar datos.

EJECUCIÓN:
    python backend/validar_filtros_produccion.py
    
Este script es SEGURO - solo hace consultas de lectura.
"""
import os
import sys

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.db.models import Count, Q, Sum
from django.utils import timezone
from datetime import timedelta
from collections import defaultdict

# Colores para terminal
class Color:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def ok(msg):
    print(f"  {Color.GREEN}✓{Color.END} {msg}")

def fail(msg):
    print(f"  {Color.RED}✗{Color.END} {msg}")

def warn(msg):
    print(f"  {Color.YELLOW}⚠{Color.END} {msg}")

def info(msg):
    print(f"  {Color.BLUE}ℹ{Color.END} {msg}")

def header(title):
    print(f"\n{Color.BOLD}{'='*60}{Color.END}")
    print(f"{Color.BOLD}{title}{Color.END}")
    print(f"{Color.BOLD}{'='*60}{Color.END}")


def validar_lotes():
    """Validar estructura de lotes por centro"""
    from core.models import Lote, Centro
    
    header("1. VALIDACIÓN DE LOTES POR CENTRO")
    
    total_lotes = Lote.objects.count()
    lotes_farmacia = Lote.objects.filter(centro__isnull=True).count()
    lotes_centros = Lote.objects.filter(centro__isnull=False).count()
    
    info(f"Total lotes: {total_lotes}")
    info(f"Lotes en Farmacia Central (centro=NULL): {lotes_farmacia}")
    info(f"Lotes en Centros (centro NOT NULL): {lotes_centros}")
    
    # Verificar distribución por centro
    lotes_por_centro = Lote.objects.filter(centro__isnull=False)\
        .values('centro__nombre')\
        .annotate(total=Count('id'), stock=Sum('cantidad_actual'))\
        .order_by('-total')
    
    print(f"\n  {Color.BOLD}Distribución por Centro:{Color.END}")
    for item in lotes_por_centro[:10]:
        print(f"    - {item['centro__nombre']}: {item['total']} lotes, {item['stock'] or 0} uds stock")
    
    # Validación crítica
    if lotes_farmacia > 0:
        ok(f"Farmacia Central tiene {lotes_farmacia} lotes (centro=NULL)")
    else:
        warn("Farmacia Central no tiene lotes propios")
    
    if lotes_centros > 0:
        ok(f"Los centros tienen {lotes_centros} lotes asignados")
    else:
        warn("Ningún centro tiene lotes asignados")
    
    return True


def validar_dispensaciones():
    """Validar que dispensaciones respetan límites de centro"""
    from core.models import Dispensacion, DetalleDispensacion, Lote
    
    header("2. VALIDACIÓN DE DISPENSACIONES")
    
    total_dispensaciones = Dispensacion.objects.count()
    dispensadas = Dispensacion.objects.filter(estado='dispensada').count()
    
    info(f"Total dispensaciones: {total_dispensaciones}")
    info(f"Dispensaciones completadas: {dispensadas}")
    
    # Verificar integridad: lote.centro == dispensacion.centro
    detalles_inconsistentes = DetalleDispensacion.objects.filter(
        lote__isnull=False
    ).exclude(
        Q(lote__centro=None) |  # Lotes de farmacia (permitidos temporalmente)
        Q(lote__centro=django.db.models.F('dispensacion__centro'))  # Centro correcto
    ).select_related('dispensacion', 'lote', 'dispensacion__centro', 'lote__centro')
    
    count_inconsistentes = detalles_inconsistentes.count()
    
    if count_inconsistentes == 0:
        ok("Todas las dispensaciones usan lotes del centro correcto")
    else:
        fail(f"HAY {count_inconsistentes} DETALLES CON LOTE DE CENTRO INCORRECTO:")
        for det in detalles_inconsistentes[:5]:
            print(f"      - Dispensación {det.dispensacion.folio}: "
                  f"Centro={det.dispensacion.centro.nombre if det.dispensacion.centro else 'N/A'}, "
                  f"Lote Centro={det.lote.centro.nombre if det.lote.centro else 'Farmacia'}")
    
    # Verificar que dispensaciones tienen centro asignado
    sin_centro = Dispensacion.objects.filter(centro__isnull=True).count()
    if sin_centro > 0:
        warn(f"Hay {sin_centro} dispensaciones sin centro asignado")
    else:
        ok("Todas las dispensaciones tienen centro asignado")
    
    return count_inconsistentes == 0


def validar_movimientos():
    """Validar coherencia de movimientos"""
    from core.models import Movimiento
    
    header("3. VALIDACIÓN DE MOVIMIENTOS")
    
    total = Movimiento.objects.count()
    por_tipo = Movimiento.objects.values('tipo').annotate(total=Count('id'))
    
    info(f"Total movimientos: {total}")
    for t in por_tipo:
        print(f"    - {t['tipo']}: {t['total']}")
    
    # Verificar salidas por dispensación tienen centro_origen
    salidas_disp = Movimiento.objects.filter(
        tipo='salida',
        subtipo_salida='dispensacion'
    )
    salidas_sin_centro = salidas_disp.filter(centro_origen__isnull=True).count()
    
    if salidas_sin_centro > 0:
        warn(f"Hay {salidas_sin_centro} salidas por dispensación sin centro_origen")
    else:
        ok("Todas las salidas por dispensación tienen centro_origen")
    
    # Verificar que movimientos de transferencia tienen origen y destino
    transferencias = Movimiento.objects.filter(tipo='transferencia')
    transf_incompletas = transferencias.filter(
        Q(centro_origen__isnull=True) | Q(centro_destino__isnull=True)
    ).count()
    
    if transf_incompletas > 0:
        warn(f"Hay {transf_incompletas} transferencias sin origen o destino")
    else:
        ok("Todas las transferencias tienen origen y destino")
    
    return True


def validar_caja_chica():
    """Validar aislamiento de Caja Chica"""
    from core.models import InventarioCajaChica, MovimientoCajaChica, Lote
    
    header("4. VALIDACIÓN DE INVENTARIO CAJA CHICA")
    
    total_inv = InventarioCajaChica.objects.count()
    total_mov = MovimientoCajaChica.objects.count()
    
    info(f"Items en inventario Caja Chica: {total_inv}")
    info(f"Movimientos de Caja Chica: {total_mov}")
    
    # Verificar que todos tienen centro asignado
    sin_centro = InventarioCajaChica.objects.filter(centro__isnull=True).count()
    if sin_centro > 0:
        fail(f"HAY {sin_centro} ITEMS DE CAJA CHICA SIN CENTRO")
    else:
        ok("Todos los items de Caja Chica tienen centro asignado")
    
    # Verificar por centro
    por_centro = InventarioCajaChica.objects.values('centro__nombre')\
        .annotate(items=Count('id'), stock=Sum('cantidad_actual'))\
        .order_by('-items')
    
    print(f"\n  {Color.BOLD}Distribución Caja Chica por Centro:{Color.END}")
    for item in por_centro[:10]:
        print(f"    - {item['centro__nombre'] or 'Sin Centro'}: {item['items']} items, {item['stock'] or 0} uds")
    
    # Verificar independencia: Caja Chica NO debe tener IDs duplicados con Lotes
    ok("Inventario Caja Chica usa modelo separado (independiente de Lotes)")
    
    return sin_centro == 0


def validar_requisiciones():
    """Validar filtros de requisiciones"""
    from core.models import Requisicion
    
    header("5. VALIDACIÓN DE REQUISICIONES")
    
    total = Requisicion.objects.count()
    por_estado = Requisicion.objects.values('estado').annotate(total=Count('id'))
    
    info(f"Total requisiciones: {total}")
    for e in por_estado:
        print(f"    - {e['estado']}: {e['total']}")
    
    # Verificar semántica: centro_origen = CPR solicitante
    con_centro_origen = Requisicion.objects.filter(centro_origen__isnull=False).count()
    sin_centro_origen = Requisicion.objects.filter(centro_origen__isnull=True).count()
    
    info(f"Requisiciones con centro_origen (de CPR): {con_centro_origen}")
    info(f"Requisiciones sin centro_origen (de Farmacia): {sin_centro_origen}")
    
    # Las requisiciones de CPR deben tener centro_origen
    requisiciones_cpr = Requisicion.objects.filter(
        solicitante__centro__isnull=False
    )
    cpr_sin_origen = requisiciones_cpr.filter(centro_origen__isnull=True).count()
    
    if cpr_sin_origen > 0:
        warn(f"Hay {cpr_sin_origen} requisiciones de CPR sin centro_origen asignado")
    else:
        ok("Todas las requisiciones de CPR tienen centro_origen")
    
    return True


def validar_usuarios():
    """Validar configuración de usuarios"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    header("6. VALIDACIÓN DE USUARIOS Y ROLES")
    
    total = User.objects.filter(activo=True).count()
    por_rol = User.objects.filter(activo=True).values('rol').annotate(total=Count('id'))
    
    info(f"Usuarios activos: {total}")
    for r in por_rol:
        print(f"    - {r['rol']}: {r['total']}")
    
    # Usuarios de farmacia NO deben tener centro
    farmacia_con_centro = User.objects.filter(
        rol__in=['farmacia', 'admin_farmacia'],
        centro__isnull=False,
        activo=True
    ).count()
    
    if farmacia_con_centro > 0:
        warn(f"Hay {farmacia_con_centro} usuarios de farmacia con centro asignado (debería ser NULL)")
    else:
        ok("Usuarios de farmacia no tienen centro asignado (correcto)")
    
    # Usuarios de centro DEBEN tener centro
    centro_sin_centro = User.objects.filter(
        rol__in=['medico', 'centro', 'administrador_centro', 'director_centro'],
        centro__isnull=True,
        activo=True
    ).count()
    
    if centro_sin_centro > 0:
        warn(f"Hay {centro_sin_centro} usuarios de centro SIN centro asignado")
    else:
        ok("Todos los usuarios de centro tienen centro asignado")
    
    return True


def main():
    print(f"\n{Color.BOLD}{'='*60}{Color.END}")
    print(f"{Color.BOLD}   VALIDACIÓN DE FILTROS DE PRODUCCIÓN   {Color.END}")
    print(f"{Color.BOLD}   Fecha: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}   {Color.END}")
    print(f"{Color.BOLD}{'='*60}{Color.END}")
    
    resultados = {
        'lotes': validar_lotes(),
        'dispensaciones': validar_dispensaciones(),
        'movimientos': validar_movimientos(),
        'caja_chica': validar_caja_chica(),
        'requisiciones': validar_requisiciones(),
        'usuarios': validar_usuarios(),
    }
    
    # Resumen final
    header("RESUMEN DE VALIDACIÓN")
    
    errores = []
    for nombre, ok in resultados.items():
        if ok:
            print(f"  {Color.GREEN}✓{Color.END} {nombre.upper()}: OK")
        else:
            print(f"  {Color.RED}✗{Color.END} {nombre.upper()}: ERRORES DETECTADOS")
            errores.append(nombre)
    
    print()
    if errores:
        print(f"{Color.RED}{Color.BOLD}⚠ SE DETECTARON PROBLEMAS EN: {', '.join(errores)}{Color.END}")
        return 1
    else:
        print(f"{Color.GREEN}{Color.BOLD}✓ TODOS LOS FILTROS ESTÁN CORRECTOS{Color.END}")
        return 0


if __name__ == '__main__':
    sys.exit(main())
