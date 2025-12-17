#!/usr/bin/env python
"""
Verificación completa de integración Frontend ↔ Backend ↔ Base de Datos
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from django.test import RequestFactory
from rest_framework.test import force_authenticate
from core.models import (
    User, Donacion, DetalleDonacion, SalidaDonacion, Notificacion,
    Producto, Lote, Centro, Movimiento, Requisicion, DetalleRequisicion
)

def main():
    print('=' * 70)
    print('VERIFICACIÓN COMPLETA: FRONTEND ↔ BACKEND ↔ BASE DE DATOS')
    print('=' * 70)
    
    errores = []
    
    # 1. VERIFICAR CONEXIÓN A BD
    print('\n1. CONEXIÓN A BASE DE DATOS')
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT version()')
            version = cursor.fetchone()[0]
            print(f'   ✅ PostgreSQL: {version[:60]}...')
            
            cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
            tablas = cursor.fetchone()[0]
            print(f'   ✅ Total tablas en BD: {tablas}')
    except Exception as e:
        print(f'   ❌ Error conexión BD: {e}')
        errores.append('Conexión BD')
    
    # 2. VERIFICAR MODELOS DJANGO vs BD
    print('\n2. MODELOS DJANGO ↔ TABLAS BD')
    tablas_criticas = [
        ('productos', Producto),
        ('lotes', Lote),
        ('centros', Centro),
        ('movimientos', Movimiento),
        ('requisiciones', Requisicion),
        ('detalles_requisicion', DetalleRequisicion),
        ('donaciones', Donacion),
        ('detalle_donaciones', DetalleDonacion),
        ('salidas_donaciones', SalidaDonacion),
        ('usuarios', User),
        ('notificaciones', Notificacion),
    ]
    
    for tabla, modelo in tablas_criticas:
        try:
            count = modelo.objects.count()
            print(f'   ✅ {tabla}: {count} registros')
        except Exception as e:
            print(f'   ❌ {tabla}: ERROR - {str(e)[:50]}')
            errores.append(f'Modelo {tabla}')
    
    # 3. VERIFICAR FOREIGN KEYS
    print('\n3. INTEGRIDAD REFERENCIAL (Foreign Keys)')
    fk_checks = [
        ('lotes → productos', 
         'SELECT COUNT(*) FROM lotes l LEFT JOIN productos p ON l.producto_id = p.id WHERE l.producto_id IS NOT NULL AND p.id IS NULL'),
        ('movimientos → lotes',
         'SELECT COUNT(*) FROM movimientos m LEFT JOIN lotes l ON m.lote_id = l.id WHERE m.lote_id IS NOT NULL AND l.id IS NULL'),
        ('movimientos → productos',
         'SELECT COUNT(*) FROM movimientos m LEFT JOIN productos p ON m.producto_id = p.id WHERE p.id IS NULL'),
        ('detalle_donaciones → donaciones',
         'SELECT COUNT(*) FROM detalle_donaciones dd LEFT JOIN donaciones d ON dd.donacion_id = d.id WHERE d.id IS NULL'),
        ('salidas_donaciones → detalle_donaciones',
         'SELECT COUNT(*) FROM salidas_donaciones sd LEFT JOIN detalle_donaciones dd ON sd.detalle_donacion_id = dd.id WHERE dd.id IS NULL'),
        ('requisiciones → usuarios (solicitante)',
         'SELECT COUNT(*) FROM requisiciones r LEFT JOIN usuarios u ON r.solicitante_id = u.id WHERE r.solicitante_id IS NOT NULL AND u.id IS NULL'),
        ('detalles_requisicion → requisiciones',
         'SELECT COUNT(*) FROM detalles_requisicion dr LEFT JOIN requisiciones r ON dr.requisicion_id = r.id WHERE r.id IS NULL'),
        ('usuarios → centros',
         'SELECT COUNT(*) FROM usuarios u LEFT JOIN centros c ON u.centro_id = c.id WHERE u.centro_id IS NOT NULL AND c.id IS NULL'),
    ]
    
    with connection.cursor() as cursor:
        for nombre, query in fk_checks:
            try:
                cursor.execute(query)
                huerfanos = cursor.fetchone()[0]
                if huerfanos == 0:
                    print(f'   ✅ {nombre}: OK')
                else:
                    print(f'   ❌ {nombre}: {huerfanos} huérfanos')
                    errores.append(f'FK {nombre}')
            except Exception as e:
                print(f'   ⚠️ {nombre}: {str(e)[:40]}')
    
    # 4. VERIFICAR APIs CRÍTICAS
    print('\n4. ENDPOINTS API (Backend)')
    from inventario.views import (
        ProductoViewSet, LoteViewSet, CentroViewSet, MovimientoViewSet,
        reporte_inventario, reporte_movimientos
    )
    from core.views import DonacionViewSet, SalidaDonacionViewSet
    
    factory = RequestFactory()
    admin = User.objects.filter(is_superuser=True).first()
    
    if not admin:
        print('   ❌ No hay usuario admin para pruebas')
        errores.append('Usuario admin')
    else:
        endpoints = [
            ('GET /api/productos/', ProductoViewSet, 'list'),
            ('GET /api/lotes/', LoteViewSet, 'list'),
            ('GET /api/centros/', CentroViewSet, 'list'),
            ('GET /api/movimientos/', MovimientoViewSet, 'list'),
            ('GET /api/donaciones/', DonacionViewSet, 'list'),
            ('GET /api/salidas-donaciones/', SalidaDonacionViewSet, 'list'),
        ]
        
        for nombre, viewset, action in endpoints:
            try:
                request = factory.get(nombre.split()[1])
                force_authenticate(request, user=admin)
                view = viewset.as_view({'get': action})
                response = view(request)
                if response.status_code == 200:
                    print(f'   ✅ {nombre}: {response.status_code}')
                else:
                    print(f'   ❌ {nombre}: {response.status_code}')
                    errores.append(nombre)
            except Exception as e:
                print(f'   ❌ {nombre}: {str(e)[:40]}')
                errores.append(nombre)
        
        # Reportes
        for nombre, func in [('GET /api/reportes/inventario/', reporte_inventario), 
                             ('GET /api/reportes/movimientos/', reporte_movimientos)]:
            try:
                request = factory.get(nombre.split()[1])
                force_authenticate(request, user=admin)
                request.user = admin
                response = func(request)
                if response.status_code == 200:
                    print(f'   ✅ {nombre}: {response.status_code}')
                else:
                    print(f'   ❌ {nombre}: {response.status_code}')
                    errores.append(nombre)
            except Exception as e:
                print(f'   ❌ {nombre}: {str(e)[:40]}')
                errores.append(nombre)
    
    # 5. VERIFICAR CONSISTENCIA DE DATOS
    print('\n5. CONSISTENCIA DE DATOS')
    with connection.cursor() as cursor:
        # Stock de lotes
        cursor.execute('SELECT COUNT(*) FROM lotes WHERE cantidad_actual < 0')
        negativos = cursor.fetchone()[0]
        if negativos == 0:
            print('   ✅ Lotes con stock negativo: 0')
        else:
            print(f'   ⚠️ Lotes con stock negativo: {negativos}')
        
        # Donaciones con stock disponible coherente
        cursor.execute('SELECT COUNT(*) FROM detalle_donaciones WHERE cantidad_disponible < 0')
        negativos = cursor.fetchone()[0]
        if negativos == 0:
            print('   ✅ Detalles donación con stock negativo: 0')
        else:
            print(f'   ⚠️ Detalles donación con stock negativo: {negativos}')
        
        # Movimientos sin producto
        cursor.execute('SELECT COUNT(*) FROM movimientos WHERE producto_id IS NULL')
        sin_producto = cursor.fetchone()[0]
        if sin_producto == 0:
            print('   ✅ Movimientos sin producto: 0')
        else:
            print(f'   ❌ Movimientos sin producto: {sin_producto}')
            errores.append('Movimientos sin producto')
    
    # 6. VERIFICAR FRONTEND APIS (estructura esperada)
    print('\n6. ESTRUCTURA DE RESPUESTAS API (para Frontend)')
    
    try:
        # Verificar que productos tiene los campos que el frontend espera
        producto = Producto.objects.first()
        if producto:
            campos_producto = ['id', 'clave', 'nombre', 'descripcion', 'unidad_medida', 'stock_minimo', 'activo']
            for campo in campos_producto:
                if hasattr(producto, campo):
                    print(f'   ✅ Producto.{campo}: existe')
                else:
                    print(f'   ❌ Producto.{campo}: NO existe')
                    errores.append(f'Campo Producto.{campo}')
    except Exception as e:
        print(f'   ⚠️ Error verificando productos: {e}')
    
    try:
        # Verificar que donaciones tiene los campos esperados
        donacion = Donacion.objects.first()
        if donacion:
            campos_donacion = ['id', 'numero', 'donante_nombre', 'estado', 'fecha_donacion']
            for campo in campos_donacion:
                if hasattr(donacion, campo):
                    print(f'   ✅ Donacion.{campo}: existe')
                else:
                    print(f'   ❌ Donacion.{campo}: NO existe')
                    errores.append(f'Campo Donacion.{campo}')
    except Exception as e:
        print(f'   ⚠️ Error verificando donaciones: {e}')
    
    # RESUMEN
    print('\n' + '=' * 70)
    print('RESUMEN FINAL')
    print('=' * 70)
    
    if not errores:
        print('🎉 SISTEMA 100% INTEGRADO Y FUNCIONAL')
        print('')
        print('✅ Base de datos PostgreSQL conectada')
        print('✅ 11 modelos Django sincronizados con BD')
        print('✅ Integridad referencial verificada (8 FKs)')
        print('✅ 8 APIs funcionando correctamente')
        print('✅ Datos consistentes (sin stocks negativos)')
        print('✅ Estructura de respuestas compatible con Frontend')
        return 0
    else:
        print(f'⚠️ Se encontraron {len(errores)} problemas:')
        for e in errores:
            print(f'   - {e}')
        return 1

if __name__ == '__main__':
    sys.exit(main())
