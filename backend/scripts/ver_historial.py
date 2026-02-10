#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Ver historial de estados de una requisición específica
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import Requisicion, RequisicionHistorialEstados

print("=" * 80)
print("HISTORIAL DE ESTADOS - REQ-20260112-1887")
print("=" * 80)

# Buscar la requisición
req = Requisicion.objects.filter(numero='REQ-20260112-1887').first()
if not req:
    print("❌ Requisición no encontrada")
else:
    print(f"📋 Requisición: {req.numero}")
    print(f"   Estado actual: {req.estado}")
    print(f"   Fecha solicitud: {req.fecha_solicitud}")
    print(f"   Fecha surtido: {req.fecha_surtido}")
    print(f"   Fecha entrega: {req.fecha_entrega}")
    print(f"   Surtidor: {req.surtidor.username if req.surtidor else 'N/A'}")
    
    # Ver historial de estados
    print("\n📜 HISTORIAL DE ESTADOS:")
    historial = RequisicionHistorialEstados.objects.filter(requisicion=req).order_by('fecha_cambio')
    
    if not historial.exists():
        print("   ⚠️ No hay historial de estados registrado")
    else:
        for h in historial:
            print(f"   {h.fecha_cambio}: {h.estado_anterior} → {h.estado_nuevo}")
            print(f"      Usuario: {h.usuario.username if h.usuario else 'N/A'}")
            print(f"      Acción: {h.accion}")
            if h.datos_adicionales:
                print(f"      Datos: {str(h.datos_adicionales)[:100]}...")

print("\n" + "=" * 80)
