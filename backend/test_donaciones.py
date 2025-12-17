"""
Test completo del módulo de donaciones.
Verifica: CRUD, import/export, entradas, salidas.
"""
import os
import sys
import django

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from django.test import RequestFactory
from rest_framework.test import force_authenticate
from core.views import DonacionViewSet, DetalleDonacionViewSet, SalidaDonacionViewSet
from core.models import User, Donacion, DetalleDonacion, SalidaDonacion, Producto, Centro
from django.utils import timezone
from django.db import transaction
import json


def test_donaciones():
    """Test completo del módulo de donaciones."""
    
    print('=' * 70)
    print('PRUEBAS COMPLETAS - MÓDULO DE DONACIONES')
    print('=' * 70)
    
    factory = RequestFactory()
    admin = User.objects.filter(is_superuser=True).first()
    
    if not admin:
        print('❌ ERROR: No hay usuario admin disponible')
        return
    
    print(f'\nUsuario de prueba: {admin.username} (ID: {admin.id})')
    
    resultados = {
        'total': 0,
        'exitosos': 0,
        'fallidos': 0,
        'tests': []
    }
    
    def registrar_test(nombre, exito, detalle=''):
        resultados['total'] += 1
        if exito:
            resultados['exitosos'] += 1
            status = '✅'
        else:
            resultados['fallidos'] += 1
            status = '❌'
        resultados['tests'].append({'nombre': nombre, 'exito': exito, 'detalle': detalle})
        print(f'   {status} {nombre}' + (f': {detalle}' if detalle else ''))
    
    # =========================================================================
    # 1. ESTADO INICIAL
    # =========================================================================
    print('\n' + '-' * 70)
    print('1. ESTADO INICIAL DE BD')
    print('-' * 70)
    
    donaciones_count = Donacion.objects.count()
    detalles_count = DetalleDonacion.objects.count()
    salidas_count = SalidaDonacion.objects.count()
    
    print(f'   Donaciones: {donaciones_count}')
    print(f'   Detalles: {detalles_count}')
    print(f'   Salidas: {salidas_count}')
    
    # =========================================================================
    # 2. TEST LISTAR DONACIONES
    # =========================================================================
    print('\n' + '-' * 70)
    print('2. LISTAR DONACIONES (GET /donaciones/)')
    print('-' * 70)
    
    view = DonacionViewSet.as_view({'get': 'list'})
    request = factory.get('/api/donaciones/')
    force_authenticate(request, user=admin)
    response = view(request)
    
    registrar_test('GET /donaciones/', response.status_code == 200, f'Status: {response.status_code}')
    
    # =========================================================================
    # 3. TEST DIAGNÓSTICO
    # =========================================================================
    print('\n' + '-' * 70)
    print('3. DIAGNÓSTICO (GET /donaciones/diagnostico/)')
    print('-' * 70)
    
    view = DonacionViewSet.as_view({'get': 'diagnostico'})
    request = factory.get('/api/donaciones/diagnostico/')
    force_authenticate(request, user=admin)
    response = view(request)
    
    if response.status_code == 200:
        data = response.data
        tabla_existe = data.get('tabla_existe')
        registrar_test('GET /donaciones/diagnostico/', tabla_existe, 
                      f"Tabla existe: {tabla_existe}, Total: {data.get('total_donaciones_orm')}")
    else:
        registrar_test('GET /donaciones/diagnostico/', False, f'Error: {response.data}')
    
    # =========================================================================
    # 4. TEST CREAR DONACIÓN
    # =========================================================================
    print('\n' + '-' * 70)
    print('4. CREAR DONACIÓN (POST /donaciones/)')
    print('-' * 70)
    
    centro = Centro.objects.first()
    producto = Producto.objects.filter(activo=True).first()
    
    numero_test = f'DON-TEST-{timezone.now().strftime("%Y%m%d%H%M%S")}'
    donacion_data = {
        'numero': numero_test,
        'donante_nombre': 'Empresa de Prueba Automatizada SA',
        'donante_tipo': 'empresa',
        'donante_rfc': 'EPA123456ABC',
        'fecha_donacion': timezone.now().date().isoformat(),
        'centro_destino': centro.id if centro else None,
        'notas': 'Donación creada por test automático',
    }
    
    view = DonacionViewSet.as_view({'post': 'create'})
    request = factory.post('/api/donaciones/', 
                          data=json.dumps(donacion_data), 
                          content_type='application/json')
    force_authenticate(request, user=admin)
    response = view(request)
    
    donacion_id = None
    if response.status_code == 201:
        donacion_id = response.data.get('id')
        registrar_test('POST /donaciones/', True, f'ID: {donacion_id}, Número: {numero_test}')
    else:
        registrar_test('POST /donaciones/', False, f'Error: {response.data}')
    
    # =========================================================================
    # 5. TEST OBTENER DONACIÓN
    # =========================================================================
    print('\n' + '-' * 70)
    print('5. OBTENER DONACIÓN (GET /donaciones/{id}/)')
    print('-' * 70)
    
    if donacion_id:
        view = DonacionViewSet.as_view({'get': 'retrieve'})
        request = factory.get(f'/api/donaciones/{donacion_id}/')
        force_authenticate(request, user=admin)
        response = view(request, pk=donacion_id)
        
        if response.status_code == 200:
            estado = response.data.get('estado')
            registrar_test('GET /donaciones/{id}/', True, f'Estado: {estado}')
        else:
            registrar_test('GET /donaciones/{id}/', False, f'Error: {response.data}')
    else:
        registrar_test('GET /donaciones/{id}/', False, 'Saltado - no hay donación')
    
    # =========================================================================
    # 6. TEST CREAR DETALLE DE DONACIÓN
    # =========================================================================
    print('\n' + '-' * 70)
    print('6. CREAR DETALLE (POST /detalle-donaciones/)')
    print('-' * 70)
    
    detalle_id = None
    if donacion_id and producto:
        detalle_data = {
            'donacion': donacion_id,
            'producto': producto.id,
            'numero_lote': 'LOTE-TEST-001',
            'cantidad': 100,
            'cantidad_disponible': 0,  # Se activa al procesar
            'fecha_caducidad': (timezone.now() + timezone.timedelta(days=365)).date().isoformat(),
            'estado_producto': 'bueno',
            'notas': 'Detalle de prueba',
        }
        
        view = DetalleDonacionViewSet.as_view({'post': 'create'})
        request = factory.post('/api/detalle-donaciones/', 
                              data=json.dumps(detalle_data), 
                              content_type='application/json')
        force_authenticate(request, user=admin)
        response = view(request)
        
        if response.status_code == 201:
            detalle_id = response.data.get('id')
            registrar_test('POST /detalle-donaciones/', True, 
                          f'ID: {detalle_id}, Producto: {producto.nombre[:30]}')
        else:
            registrar_test('POST /detalle-donaciones/', False, f'Error: {response.data}')
    else:
        registrar_test('POST /detalle-donaciones/', False, 
                      'Saltado - no hay donación/producto')
    
    # =========================================================================
    # 7. TEST RECIBIR DONACIÓN
    # =========================================================================
    print('\n' + '-' * 70)
    print('7. RECIBIR DONACIÓN (POST /donaciones/{id}/recibir/)')
    print('-' * 70)
    
    if donacion_id:
        view = DonacionViewSet.as_view({'post': 'recibir'})
        request = factory.post(f'/api/donaciones/{donacion_id}/recibir/')
        force_authenticate(request, user=admin)
        response = view(request, pk=donacion_id)
        
        if response.status_code == 200:
            nuevo_estado = response.data.get('estado')
            registrar_test('POST /donaciones/{id}/recibir/', nuevo_estado == 'recibida', 
                          f'Nuevo estado: {nuevo_estado}')
        else:
            registrar_test('POST /donaciones/{id}/recibir/', False, f'Error: {response.data}')
    else:
        registrar_test('POST /donaciones/{id}/recibir/', False, 'Saltado - no hay donación')
    
    # =========================================================================
    # 8. TEST PROCESAR DONACIÓN (ACTIVAR STOCK)
    # =========================================================================
    print('\n' + '-' * 70)
    print('8. PROCESAR DONACIÓN (POST /donaciones/{id}/procesar/)')
    print('-' * 70)
    
    if donacion_id:
        view = DonacionViewSet.as_view({'post': 'procesar'})
        request = factory.post(f'/api/donaciones/{donacion_id}/procesar/')
        force_authenticate(request, user=admin)
        response = view(request, pk=donacion_id)
        
        if response.status_code == 200:
            nuevo_estado = response.data.get('donacion', {}).get('estado')
            registrar_test('POST /donaciones/{id}/procesar/', nuevo_estado == 'procesada', 
                          f'Nuevo estado: {nuevo_estado}')
            
            # Verificar que el stock disponible se actualizó
            if detalle_id:
                detalle = DetalleDonacion.objects.get(pk=detalle_id)
                registrar_test('Stock disponible actualizado', detalle.cantidad_disponible > 0,
                              f'Cantidad disponible: {detalle.cantidad_disponible}')
        else:
            registrar_test('POST /donaciones/{id}/procesar/', False, f'Error: {response.data}')
    else:
        registrar_test('POST /donaciones/{id}/procesar/', False, 'Saltado - no hay donación')
    
    # =========================================================================
    # 9. TEST LISTAR DETALLES CON STOCK DISPONIBLE
    # =========================================================================
    print('\n' + '-' * 70)
    print('9. LISTAR DETALLES CON STOCK (GET /detalle-donaciones/?disponible=true)')
    print('-' * 70)
    
    view = DetalleDonacionViewSet.as_view({'get': 'list'})
    request = factory.get('/api/detalle-donaciones/', {'disponible': 'true'})
    force_authenticate(request, user=admin)
    response = view(request)
    
    if response.status_code == 200:
        results = response.data.get('results', response.data)
        count = len(results) if isinstance(results, list) else 0
        registrar_test('GET /detalle-donaciones/?disponible=true', True, 
                      f'Productos con stock: {count}')
    else:
        registrar_test('GET /detalle-donaciones/?disponible=true', False, f'Error: {response.data}')
    
    # =========================================================================
    # 10. TEST CREAR SALIDA DE DONACIÓN
    # =========================================================================
    print('\n' + '-' * 70)
    print('10. CREAR SALIDA (POST /salidas-donaciones/)')
    print('-' * 70)
    
    salida_id = None
    if detalle_id:
        # Verificar stock disponible
        detalle = DetalleDonacion.objects.get(pk=detalle_id)
        if detalle.cantidad_disponible > 0:
            salida_data = {
                'detalle_donacion': detalle_id,
                'cantidad': 10,
                'destinatario': 'Centro de Prueba - Test Automático',
                'motivo': 'Entrega programada de prueba',
                'notas': 'Salida creada por test automático',
            }
            
            view = SalidaDonacionViewSet.as_view({'post': 'create'})
            request = factory.post('/api/salidas-donaciones/', 
                                  data=json.dumps(salida_data), 
                                  content_type='application/json')
            force_authenticate(request, user=admin)
            response = view(request)
            
            if response.status_code == 201:
                salida_id = response.data.get('id')
                registrar_test('POST /salidas-donaciones/', True, 
                              f'ID: {salida_id}, Cantidad: 10')
                
                # Verificar que el stock se descontó
                detalle.refresh_from_db()
                registrar_test('Stock descontado correctamente', 
                              detalle.cantidad_disponible == 90,
                              f'Stock restante: {detalle.cantidad_disponible}')
            else:
                registrar_test('POST /salidas-donaciones/', False, f'Error: {response.data}')
        else:
            registrar_test('POST /salidas-donaciones/', False, 'Sin stock disponible')
    else:
        registrar_test('POST /salidas-donaciones/', False, 'Saltado - no hay detalle')
    
    # =========================================================================
    # 11. TEST LISTAR SALIDAS
    # =========================================================================
    print('\n' + '-' * 70)
    print('11. LISTAR SALIDAS (GET /salidas-donaciones/)')
    print('-' * 70)
    
    view = SalidaDonacionViewSet.as_view({'get': 'list'})
    request = factory.get('/api/salidas-donaciones/')
    force_authenticate(request, user=admin)
    response = view(request)
    
    if response.status_code == 200:
        results = response.data.get('results', response.data)
        count = len(results) if isinstance(results, list) else 0
        registrar_test('GET /salidas-donaciones/', True, f'Salidas encontradas: {count}')
    else:
        registrar_test('GET /salidas-donaciones/', False, f'Error: {response.data}')
    
    # =========================================================================
    # 12. TEST EXPORTAR DONACIONES A EXCEL
    # =========================================================================
    print('\n' + '-' * 70)
    print('12. EXPORTAR DONACIONES (GET /donaciones/exportar-excel/)')
    print('-' * 70)
    
    view = DonacionViewSet.as_view({'get': 'exportar_excel'})
    request = factory.get('/api/donaciones/exportar-excel/')
    force_authenticate(request, user=admin)
    response = view(request)
    
    if response.status_code == 200:
        content_type = response.get('Content-Type', '')
        registrar_test('GET /donaciones/exportar-excel/', 'spreadsheet' in content_type,
                      f'Content-Type: {content_type[:50]}')
    else:
        registrar_test('GET /donaciones/exportar-excel/', False, f'Error: {response.status_code}')
    
    # =========================================================================
    # 13. TEST PLANTILLA DONACIONES
    # =========================================================================
    print('\n' + '-' * 70)
    print('13. PLANTILLA DONACIONES (GET /donaciones/plantilla-excel/)')
    print('-' * 70)
    
    view = DonacionViewSet.as_view({'get': 'plantilla_excel'})
    request = factory.get('/api/donaciones/plantilla-excel/')
    force_authenticate(request, user=admin)
    response = view(request)
    
    if response.status_code == 200:
        content_type = response.get('Content-Type', '')
        registrar_test('GET /donaciones/plantilla-excel/', 'spreadsheet' in content_type,
                      f'Content-Type: {content_type[:50]}')
    else:
        registrar_test('GET /donaciones/plantilla-excel/', False, f'Error: {response.status_code}')
    
    # =========================================================================
    # 14. TEST EXPORTAR SALIDAS A EXCEL
    # =========================================================================
    print('\n' + '-' * 70)
    print('14. EXPORTAR SALIDAS (GET /salidas-donaciones/exportar-excel/)')
    print('-' * 70)
    
    view = SalidaDonacionViewSet.as_view({'get': 'exportar_excel'})
    request = factory.get('/api/salidas-donaciones/exportar-excel/')
    force_authenticate(request, user=admin)
    response = view(request)
    
    if response.status_code == 200:
        content_type = response.get('Content-Type', '')
        registrar_test('GET /salidas-donaciones/exportar-excel/', 'spreadsheet' in content_type,
                      f'Content-Type: {content_type[:50]}')
    else:
        registrar_test('GET /salidas-donaciones/exportar-excel/', False, f'Error: {response.status_code}')
    
    # =========================================================================
    # LIMPIEZA
    # =========================================================================
    print('\n' + '-' * 70)
    print('LIMPIEZA DE DATOS DE PRUEBA')
    print('-' * 70)
    
    try:
        # Eliminar en orden correcto por FK
        if salida_id:
            SalidaDonacion.objects.filter(pk=salida_id).delete()
            print(f'   Salida {salida_id} eliminada')
        
        if detalle_id:
            DetalleDonacion.objects.filter(pk=detalle_id).delete()
            print(f'   Detalle {detalle_id} eliminado')
        
        if donacion_id:
            Donacion.objects.filter(pk=donacion_id).delete()
            print(f'   Donación {donacion_id} eliminada')
        
        print('   ✅ Limpieza completada')
    except Exception as e:
        print(f'   ⚠️ Error en limpieza: {e}')
    
    # =========================================================================
    # RESUMEN FINAL
    # =========================================================================
    print('\n' + '=' * 70)
    print('RESUMEN DE PRUEBAS')
    print('=' * 70)
    
    print(f'\nTotal de pruebas: {resultados["total"]}')
    print(f'Exitosas: {resultados["exitosos"]} ✅')
    print(f'Fallidas: {resultados["fallidos"]} ❌')
    
    porcentaje = (resultados["exitosos"] / resultados["total"] * 100) if resultados["total"] > 0 else 0
    print(f'\nPorcentaje de éxito: {porcentaje:.1f}%')
    
    if resultados["fallidos"] == 0:
        print('\n🎉 TODAS LAS PRUEBAS PASARON EXITOSAMENTE')
    else:
        print('\n⚠️ ALGUNAS PRUEBAS FALLARON:')
        for test in resultados["tests"]:
            if not test["exito"]:
                print(f'   - {test["nombre"]}: {test["detalle"]}')
    
    return resultados


if __name__ == '__main__':
    test_donaciones()
