"""
Script para diagnosticar problemas con el endpoint de surtir.
Ejecutar desde la consola de Django: python manage.py runscript diagnostico_surtir_endpoint

Este script simula el flujo de surtido sin modificar la base de datos para
identificar el punto exacto donde falla.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from django.utils import timezone
from core.models import Requisicion, DetalleRequisicion, Lote, Centro, Usuario
from core.constants import ESTADOS_COMPROMETIDOS
from django.db.models import Sum, F
from django.db.models.functions import Coalesce

def diagnosticar_requisicion(requisicion_id):
    """Diagnostica una requisición específica para surtido."""
    
    print(f"\n{'='*80}")
    print(f"DIAGNÓSTICO DETALLADO DE REQUISICIÓN {requisicion_id}")
    print(f"{'='*80}\n")
    
    try:
        req = Requisicion.objects.select_related('centro', 'solicitante').get(pk=requisicion_id)
    except Requisicion.DoesNotExist:
        print(f"❌ ERROR: Requisición {requisicion_id} no existe")
        return
    
    print(f"✓ Requisición encontrada")
    print(f"  - Número: {req.numero}")
    print(f"  - Folio: {getattr(req, 'folio', 'N/A')}")
    print(f"  - Estado: {req.estado}")
    print(f"  - Centro: {req.centro.nombre if req.centro else 'SIN CENTRO'}")
    print(f"  - Solicitante: {req.solicitante.username if req.solicitante else 'N/A'}")
    print(f"  - Creado: {req.created_at}")
    
    # Verificar estado surtible
    ESTADOS_SURTIBLES = {'autorizada', 'autorizada_farmacia', 'en_surtido', 'parcial'}
    estado_lower = (req.estado or '').lower()
    if estado_lower in ESTADOS_SURTIBLES:
        print(f"\n✓ Estado '{req.estado}' es surtible")
    else:
        print(f"\n❌ Estado '{req.estado}' NO es surtible. Estados válidos: {ESTADOS_SURTIBLES}")
        return
    
    # Verificar detalles
    detalles = list(req.detalles.select_related('producto', 'lote').all())
    print(f"\n{'='*40}")
    print(f"DETALLES DE LA REQUISICIÓN ({len(detalles)} items)")
    print(f"{'='*40}")
    
    if not detalles:
        print(f"❌ ERROR: La requisición no tiene detalles")
        return
    
    hoy = timezone.now().date()
    errores_encontrados = []
    
    for i, det in enumerate(detalles, 1):
        print(f"\nDetalle #{i} (ID: {det.pk}):")
        
        # Verificar producto
        if not det.producto_id:
            print(f"  ❌ SIN PRODUCTO ASIGNADO")
            errores_encontrados.append(f"Detalle {det.pk} sin producto")
            continue
        
        print(f"  - Producto: {det.producto.clave} - {det.producto.nombre[:40]}...")
        print(f"  - Cantidad solicitada: {det.cantidad_solicitada}")
        print(f"  - Cantidad autorizada: {det.cantidad_autorizada}")
        print(f"  - Cantidad surtida: {det.cantidad_surtida}")
        
        # Verificar cantidad autorizada
        if det.cantidad_autorizada is None or det.cantidad_autorizada == 0:
            print(f"  ⚠️ cantidad_autorizada es NULL o 0 (se usará cantidad_solicitada)")
        
        # Calcular pendiente
        pendiente = (det.cantidad_autorizada or det.cantidad_solicitada) - (det.cantidad_surtida or 0)
        print(f"  - Pendiente por surtir: {pendiente}")
        
        if pendiente <= 0:
            print(f"  ✓ Ya surtido completamente")
            continue
        
        # Verificar lote específico vs FEFO
        if det.lote_id is not None:
            print(f"\n  LOTE ESPECÍFICO ASIGNADO:")
            lote = det.lote
            if lote:
                print(f"    - Número: {lote.numero_lote}")
                print(f"    - Centro: {lote.centro.nombre if lote.centro else 'Farmacia Central'}")
                print(f"    - Activo: {lote.activo}")
                print(f"    - Stock: {lote.cantidad_actual}")
                print(f"    - Caducidad: {lote.fecha_caducidad}")
                
                # Validaciones del lote específico
                if not lote.activo:
                    print(f"    ❌ Lote inactivo")
                    errores_encontrados.append(f"Lote {lote.numero_lote} inactivo")
                elif lote.cantidad_actual < pendiente:
                    print(f"    ❌ Stock insuficiente ({lote.cantidad_actual} < {pendiente})")
                    errores_encontrados.append(f"Stock insuficiente en lote {lote.numero_lote}")
                elif lote.fecha_caducidad and lote.fecha_caducidad < hoy:
                    print(f"    ❌ Lote vencido")
                    errores_encontrados.append(f"Lote {lote.numero_lote} vencido")
                else:
                    print(f"    ✓ Lote válido para surtido")
            else:
                print(f"    ❌ Referencia a lote {det.lote_id} pero no existe")
                errores_encontrados.append(f"Lote referenciado {det.lote_id} no existe")
        else:
            print(f"\n  FEFO AUTOMÁTICO (sin lote específico):")
            
            # Buscar lotes disponibles en farmacia central
            lotes_disponibles = Lote.objects.filter(
                centro__isnull=True,  # Farmacia central
                producto=det.producto,
                activo=True,
                cantidad_actual__gt=0,
                fecha_caducidad__gte=hoy
            ).order_by('fecha_caducidad')
            
            total_stock = sum(l.cantidad_actual for l in lotes_disponibles)
            print(f"    - Lotes disponibles en farmacia: {lotes_disponibles.count()}")
            print(f"    - Stock total: {total_stock}")
            
            if total_stock >= pendiente:
                print(f"    ✓ Stock suficiente para surtir")
                for l in lotes_disponibles[:3]:
                    print(f"      - {l.numero_lote}: {l.cantidad_actual} unidades (vence: {l.fecha_caducidad})")
            else:
                print(f"    ❌ Stock INSUFICIENTE ({total_stock} < {pendiente})")
                errores_encontrados.append(f"Stock insuficiente para {det.producto.clave}")
    
    # Resumen
    print(f"\n{'='*40}")
    print(f"RESUMEN DEL DIAGNÓSTICO")
    print(f"{'='*40}")
    
    if errores_encontrados:
        print(f"\n❌ SE ENCONTRARON {len(errores_encontrados)} ERRORES:")
        for err in errores_encontrados:
            print(f"   - {err}")
        print("\nEl surtido FALLARÁ por estos errores.")
    else:
        print(f"\n✓ No se encontraron errores. El surtido debería funcionar.")
    
    # Verificar centro destino
    print(f"\n{'='*40}")
    print(f"VERIFICACIÓN DEL CENTRO DESTINO")
    print(f"{'='*40}")
    
    if req.centro:
        print(f"✓ Centro: {req.centro.nombre} (ID: {req.centro.pk})")
        print(f"  - Activo: {getattr(req.centro, 'activo', 'N/A')}")
        
        # Verificar lotes existentes en el centro
        lotes_en_centro = Lote.objects.filter(centro=req.centro).count()
        print(f"  - Lotes actuales en centro: {lotes_en_centro}")
    else:
        print(f"⚠️ Sin centro destino (podría ser problema si se requiere transferencia)")
    
    return errores_encontrados

def ejecutar_diagnostico():
    """Ejecuta diagnóstico en todas las requisiciones surtibles."""
    
    print("\n" + "="*80)
    print("DIAGNÓSTICO DE REQUISICIONES SURTIBLES")
    print("="*80)
    
    ESTADOS_SURTIBLES = ['autorizada', 'autorizada_farmacia', 'en_surtido', 'parcial']
    requisiciones = Requisicion.objects.filter(estado__in=ESTADOS_SURTIBLES)
    
    print(f"\nRequisiciones en estados surtibles: {requisiciones.count()}")
    
    for req in requisiciones[:5]:  # Limitar a 5 para no saturar
        diagnosticar_requisicion(req.pk)
    
    print("\n" + "="*80)
    print("FIN DEL DIAGNÓSTICO")
    print("="*80)

if __name__ == '__main__':
    # Si se pasa un ID como argumento, diagnosticar esa requisición
    if len(sys.argv) > 1:
        try:
            req_id = int(sys.argv[1])
            diagnosticar_requisicion(req_id)
        except ValueError:
            print(f"Error: '{sys.argv[1]}' no es un ID válido")
    else:
        ejecutar_diagnostico()
