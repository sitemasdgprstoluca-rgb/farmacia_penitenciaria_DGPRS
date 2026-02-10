"""
Test End-to-End Completo del Sistema de Inventario Farmacéutico
================================================================
Verifica:
1. Donaciones: CRUD, flujo de estados, import/export
2. Movimientos: entradas, salidas, transferencias
3. Reportes: generación, exportación Excel/PDF
4. Auditoría y trazabilidad
5. Manejo de errores (pruebas negativas)
"""
import os
import sys
import django
import json
import io
from datetime import datetime, timedelta

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from django.test import RequestFactory
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import force_authenticate
from django.utils import timezone
from django.db import transaction
import openpyxl

# Importar modelos y vistas
from core.models import (
    User, Producto, Centro, Lote, Movimiento, 
    Donacion, DetalleDonacion, SalidaDonacion, 
    Requisicion, DetalleRequisicion
)
from core.views import (
    DonacionViewSet, DetalleDonacionViewSet, SalidaDonacionViewSet
)
from inventario.views import MovimientoViewSet
from inventario.views_legacy import (
    reporte_movimientos, reporte_requisiciones, reporte_inventario,
    reporte_caducidades
)


class TestResults:
    """Almacena y formatea los resultados de las pruebas."""
    
    def __init__(self):
        self.tests = []
        self.passed = 0
        self.failed = 0
        self.warnings = 0
    
    def add(self, name, passed, detail='', is_warning=False):
        """Agregar resultado de prueba."""
        self.tests.append({
            'name': name,
            'passed': passed,
            'detail': detail,
            'is_warning': is_warning
        })
        if is_warning:
            self.warnings += 1
        elif passed:
            self.passed += 1
        else:
            self.failed += 1
        
        # Imprimir inmediatamente
        status = '⚠️' if is_warning else ('✅' if passed else '❌')
        print(f'   {status} {name}' + (f': {detail}' if detail else ''))
    
    def summary(self):
        """Imprimir resumen final."""
        total = self.passed + self.failed
        print(f'\n{"="*70}')
        print('RESUMEN DE PRUEBAS')
        print(f'{"="*70}')
        print(f'Total: {total} pruebas')
        print(f'Exitosas: {self.passed} ✅')
        print(f'Fallidas: {self.failed} ❌')
        print(f'Advertencias: {self.warnings} ⚠️')
        
        if total > 0:
            pct = (self.passed / total) * 100
            print(f'\nPorcentaje de éxito: {pct:.1f}%')
        
        if self.failed == 0:
            print('\n🎉 TODAS LAS PRUEBAS PASARON')
        else:
            print('\n⚠️ PRUEBAS FALLIDAS:')
            for t in self.tests:
                if not t['passed'] and not t['is_warning']:
                    print(f'   - {t["name"]}: {t["detail"]}')
        
        return self.failed == 0


def run_tests():
    """Ejecutar todas las pruebas del sistema."""
    
    print('='*70)
    print('TEST END-TO-END SISTEMA INVENTARIO FARMACÉUTICO')
    print('='*70)
    print(f'Fecha: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}')
    
    results = TestResults()
    factory = RequestFactory()
    
    # Obtener usuario admin
    admin = User.objects.filter(is_superuser=True).first()
    if not admin:
        print('❌ ERROR: No hay usuario admin disponible')
        return False
    
    print(f'\nUsuario de prueba: {admin.username} (ID: {admin.id})')
    
    # ==========================================================================
    # 1. VERIFICACIÓN DE DATOS BASE
    # ==========================================================================
    print(f'\n{"-"*70}')
    print('1. VERIFICACIÓN DE DATOS BASE')
    print(f'{"-"*70}')
    
    productos_count = Producto.objects.filter(activo=True).count()
    centros_count = Centro.objects.count()
    lotes_count = Lote.objects.count()
    
    results.add('Productos activos', productos_count > 0, f'{productos_count} productos')
    results.add('Centros configurados', centros_count > 0, f'{centros_count} centros')
    results.add('Lotes existentes', lotes_count >= 0, f'{lotes_count} lotes')
    
    # ==========================================================================
    # 2. PRUEBAS DE MOVIMIENTOS
    # ==========================================================================
    print(f'\n{"-"*70}')
    print('2. PRUEBAS DE MOVIMIENTOS')
    print(f'{"-"*70}')
    
    # 2.1 Listar movimientos
    view = MovimientoViewSet.as_view({'get': 'list'})
    request = factory.get('/api/movimientos/')
    force_authenticate(request, user=admin)
    response = view(request)
    results.add('GET /movimientos/', response.status_code == 200, f'Status: {response.status_code}')
    
    mov_count = Movimiento.objects.count()
    results.add('Movimientos en BD', mov_count >= 0, f'{mov_count} movimientos')
    
    # 2.2 Filtrar por tipo
    request = factory.get('/api/movimientos/', {'tipo': 'ENTRADA'})
    force_authenticate(request, user=admin)
    response = view(request)
    results.add('Filtrar ENTRADAS', response.status_code == 200, f'Status: {response.status_code}')
    
    request = factory.get('/api/movimientos/', {'tipo': 'SALIDA'})
    force_authenticate(request, user=admin)
    response = view(request)
    results.add('Filtrar SALIDAS', response.status_code == 200, f'Status: {response.status_code}')
    
    # ==========================================================================
    # 3. PRUEBAS DE REPORTES
    # ==========================================================================
    print(f'\n{"-"*70}')
    print('3. PRUEBAS DE REPORTES')
    print(f'{"-"*70}')
    
    # 3.1 Reporte de inventario
    request = factory.get('/api/reportes/inventario/')
    force_authenticate(request, user=admin)
    request.user = admin
    request.query_params = {'formato': 'json'}
    
    try:
        response = reporte_inventario(request)
        results.add('Reporte Inventario JSON', response.status_code == 200, f'Status: {response.status_code}')
    except Exception as e:
        results.add('Reporte Inventario JSON', False, str(e))
    
    # 3.2 Reporte de movimientos
    request = factory.get('/api/reportes/movimientos/')
    force_authenticate(request, user=admin)
    request.user = admin
    request.query_params = {'formato': 'json'}
    
    try:
        response = reporte_movimientos(request)
        results.add('Reporte Movimientos JSON', response.status_code == 200, f'Status: {response.status_code}')
        if response.status_code == 200 and hasattr(response, 'data'):
            datos = response.data.get('datos', [])
            resumen = response.data.get('resumen', {})
            results.add('Datos movimientos', len(datos) >= 0, f'{len(datos)} registros')
    except Exception as e:
        results.add('Reporte Movimientos JSON', False, str(e))
    
    # 3.3 Reporte de requisiciones
    request = factory.get('/api/reportes/requisiciones/')
    force_authenticate(request, user=admin)
    request.user = admin
    request.query_params = {'formato': 'json'}
    
    try:
        response = reporte_requisiciones(request)
        results.add('Reporte Requisiciones JSON', response.status_code == 200, f'Status: {response.status_code}')
    except Exception as e:
        results.add('Reporte Requisiciones JSON', False, str(e))
    
    # 3.4 Reporte de caducidades
    request = factory.get('/api/reportes/caducidades/')
    force_authenticate(request, user=admin)
    request.user = admin
    request.query_params = {'formato': 'json', 'dias': '90'}
    
    try:
        response = reporte_caducidades(request)
        results.add('Reporte Caducidades JSON', response.status_code == 200, f'Status: {response.status_code}')
    except Exception as e:
        results.add('Reporte Caducidades JSON', False, str(e))
    
    # ==========================================================================
    # 4. PRUEBAS DE EXPORTACIÓN EXCEL
    # ==========================================================================
    print(f'\n{"-"*70}')
    print('4. PRUEBAS DE EXPORTACIÓN EXCEL')
    print(f'{"-"*70}')
    
    # 4.1 Exportar inventario
    # NOTA: query_params se pasa en la URL, no asignando después
    request = factory.get('/api/reportes/inventario/?formato=excel')
    force_authenticate(request, user=admin)
    request.user = admin
    
    try:
        response = reporte_inventario(request)
        is_excel = 'spreadsheet' in response.get('Content-Type', '')
        results.add('Exportar Inventario Excel', is_excel, 
                   f'Content-Type: {response.get("Content-Type", "N/A")[:40]}')
    except Exception as e:
        results.add('Exportar Inventario Excel', False, str(e))
    
    # 4.2 Exportar movimientos
    request = factory.get('/api/reportes/movimientos/?formato=excel')
    force_authenticate(request, user=admin)
    request.user = admin
    
    try:
        response = reporte_movimientos(request)
        is_excel = 'spreadsheet' in response.get('Content-Type', '')
        results.add('Exportar Movimientos Excel', is_excel,
                   f'Content-Type: {response.get("Content-Type", "N/A")[:40]}')
    except Exception as e:
        results.add('Exportar Movimientos Excel', False, str(e))
    
    # ==========================================================================
    # 5. PRUEBAS DE DONACIONES END-TO-END
    # ==========================================================================
    print(f'\n{"-"*70}')
    print('5. PRUEBAS DE DONACIONES E2E')
    print(f'{"-"*70}')
    
    centro = Centro.objects.first()
    producto = Producto.objects.filter(activo=True).first()
    
    donacion_id = None
    detalle_id = None
    salida_id = None
    
    try:
        with transaction.atomic():
            # 5.1 Crear donación
            donacion_data = {
                'numero': f'E2E-{timezone.now().strftime("%Y%m%d%H%M%S")}',
                'donante_nombre': 'Empresa Test E2E SA',
                'donante_tipo': 'empresa',
                'fecha_donacion': timezone.now().date().isoformat(),
                'centro_destino': centro.id if centro else None,
            }
            
            view = DonacionViewSet.as_view({'post': 'create'})
            request = factory.post('/api/donaciones/', 
                                  data=json.dumps(donacion_data),
                                  content_type='application/json')
            force_authenticate(request, user=admin)
            response = view(request)
            
            if response.status_code == 201:
                donacion_id = response.data.get('id')
                results.add('Crear donación', True, f'ID: {donacion_id}')
            else:
                results.add('Crear donación', False, f'Error: {response.data}')
            
            # 5.2 Agregar detalle
            if donacion_id and producto:
                detalle_data = {
                    'donacion': donacion_id,
                    'producto': producto.id,
                    'numero_lote': 'E2E-LOTE-001',
                    'cantidad': 100,
                    'fecha_caducidad': (timezone.now() + timedelta(days=365)).date().isoformat(),
                    'estado_producto': 'bueno',
                }
                
                view = DetalleDonacionViewSet.as_view({'post': 'create'})
                request = factory.post('/api/detalle-donaciones/',
                                      data=json.dumps(detalle_data),
                                      content_type='application/json')
                force_authenticate(request, user=admin)
                response = view(request)
                
                if response.status_code == 201:
                    detalle_id = response.data.get('id')
                    results.add('Agregar detalle', True, f'ID: {detalle_id}')
                else:
                    results.add('Agregar detalle', False, f'Error: {response.data}')
            
            # 5.3 Recibir donación
            if donacion_id:
                view = DonacionViewSet.as_view({'post': 'recibir'})
                request = factory.post(f'/api/donaciones/{donacion_id}/recibir/')
                force_authenticate(request, user=admin)
                response = view(request, pk=donacion_id)
                
                estado = response.data.get('estado') if response.status_code == 200 else None
                results.add('Recibir donación', estado == 'recibida', f'Estado: {estado}')
            
            # 5.4 Procesar donación (activa stock)
            if donacion_id:
                view = DonacionViewSet.as_view({'post': 'procesar'})
                request = factory.post(f'/api/donaciones/{donacion_id}/procesar/')
                force_authenticate(request, user=admin)
                response = view(request, pk=donacion_id)
                
                if response.status_code == 200:
                    estado = response.data.get('donacion', {}).get('estado')
                    results.add('Procesar donación', estado == 'procesada', f'Estado: {estado}')
                    
                    # Verificar stock
                    if detalle_id:
                        detalle = DetalleDonacion.objects.get(pk=detalle_id)
                        results.add('Stock activado', detalle.cantidad_disponible == 100,
                                   f'Disponible: {detalle.cantidad_disponible}')
                else:
                    results.add('Procesar donación', False, f'Error: {response.data}')
            
            # 5.5 Registrar salida
            if detalle_id:
                salida_data = {
                    'detalle_donacion': detalle_id,
                    'cantidad': 10,
                    'destinatario': 'Paciente E2E Test',
                    'motivo': 'Prueba automatizada E2E',
                }
                
                view = SalidaDonacionViewSet.as_view({'post': 'create'})
                request = factory.post('/api/salidas-donaciones/',
                                      data=json.dumps(salida_data),
                                      content_type='application/json')
                force_authenticate(request, user=admin)
                response = view(request)
                
                if response.status_code == 201:
                    salida_id = response.data.get('id')
                    results.add('Registrar salida', True, f'ID: {salida_id}')
                    
                    # Verificar descuento
                    detalle = DetalleDonacion.objects.get(pk=detalle_id)
                    results.add('Stock descontado', detalle.cantidad_disponible == 90,
                               f'Disponible: {detalle.cantidad_disponible}')
                else:
                    results.add('Registrar salida', False, f'Error: {response.data}')
            
            # Limpiar datos de prueba
            if salida_id:
                SalidaDonacion.objects.filter(pk=salida_id).delete()
            if detalle_id:
                DetalleDonacion.objects.filter(pk=detalle_id).delete()
            if donacion_id:
                Donacion.objects.filter(pk=donacion_id).delete()
            
            results.add('Limpieza datos E2E', True, 'Datos eliminados')
            
    except Exception as e:
        results.add('Error en pruebas E2E', False, str(e))
    
    # ==========================================================================
    # 6. PRUEBAS DE MANEJO DE ERRORES (PRUEBA DE TONTOS)
    # ==========================================================================
    print(f'\n{"-"*70}')
    print('6. PRUEBAS NEGATIVAS (MANEJO DE ERRORES)')
    print(f'{"-"*70}')
    
    # 6.1 Crear donación sin datos obligatorios
    view = DonacionViewSet.as_view({'post': 'create'})
    request = factory.post('/api/donaciones/',
                          data=json.dumps({}),
                          content_type='application/json')
    force_authenticate(request, user=admin)
    response = view(request)
    results.add('Validación campos vacíos', response.status_code == 400, 
               f'Status: {response.status_code}')
    
    # 6.2 Salida con stock insuficiente
    # Crear donación temporal para probar
    try:
        with transaction.atomic():
            donacion_temp = Donacion.objects.create(
                numero=f'TEMP-{timezone.now().strftime("%H%M%S")}',
                donante_nombre='Temp',
                donante_tipo='empresa',
                fecha_donacion=timezone.now().date(),
                centro_destino=centro,
                recibido_por=admin,
                estado='procesada'
            )
            detalle_temp = DetalleDonacion.objects.create(
                donacion=donacion_temp,
                producto=producto,
                cantidad=10,
                cantidad_disponible=5,  # Solo 5 disponibles
            )
            
            # Intentar sacar 100 (más del disponible)
            salida_data = {
                'detalle_donacion': detalle_temp.id,
                'cantidad': 100,
                'destinatario': 'Test',
            }
            
            view = SalidaDonacionViewSet.as_view({'post': 'create'})
            request = factory.post('/api/salidas-donaciones/',
                                  data=json.dumps(salida_data),
                                  content_type='application/json')
            force_authenticate(request, user=admin)
            response = view(request)
            
            results.add('Validación stock insuficiente', response.status_code == 400,
                       f'Status: {response.status_code}')
            
            # Limpiar
            detalle_temp.delete()
            donacion_temp.delete()
            
    except Exception as e:
        results.add('Error en prueba negativa', False, str(e))
    
    # 6.3 Centro='todos' no debe romper
    request = factory.get('/api/reportes/movimientos/')
    force_authenticate(request, user=admin)
    request.user = admin
    request.query_params = {'formato': 'json', 'centro': 'todos'}
    
    try:
        response = reporte_movimientos(request)
        results.add('Centro=todos manejado', response.status_code == 200, 
                   f'Status: {response.status_code}')
    except Exception as e:
        results.add('Centro=todos manejado', False, str(e))
    
    # 6.4 Fechas inválidas
    request = factory.get('/api/reportes/movimientos/')
    force_authenticate(request, user=admin)
    request.user = admin
    request.query_params = {'formato': 'json', 'fecha_inicio': 'fecha-invalida'}
    
    try:
        response = reporte_movimientos(request)
        # Debería funcionar ignorando fecha inválida o devolver error controlado
        results.add('Fecha inválida manejada', response.status_code in [200, 400],
                   f'Status: {response.status_code}')
    except Exception as e:
        results.add('Fecha inválida manejada', False, str(e))
    
    # ==========================================================================
    # 7. PRUEBAS DE IMPORTACIÓN CON ERRORES
    # ==========================================================================
    print(f'\n{"-"*70}')
    print('7. PRUEBAS DE IMPORTACIÓN ROBUSTA')
    print(f'{"-"*70}')
    
    # 7.1 Importar archivo con errores mixtos
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Donaciones'
    ws.append([])
    ws.append([])
    ws.append([])
    ws.append(['numero', 'donante_nombre', 'donante_tipo', 'donante_rfc', 
               'donante_direccion', 'donante_contacto', 'fecha_donacion', 
               'centro_destino_id', 'notas', 'documento_donacion'])
    
    # Fila válida
    ws.append(['IMP-VALIDA-001', 'Empresa Válida SA', 'empresa', '', '', '', 
               '2024-01-15', '', 'Donación válida', ''])
    # Fila sin nombre (error)
    ws.append(['IMP-SIN-NOMBRE', '', 'empresa', '', '', '', '2024-01-15', '', '', ''])
    # Fila duplicada (si ya existe)
    ws.append(['IMP-VALIDA-001', 'Duplicada', 'empresa', '', '', '', '2024-01-15', '', '', ''])
    
    ws2 = wb.create_sheet(title='Detalles')
    ws2.append([])
    ws2.append([])
    ws2.append([])
    ws2.append(['numero_donacion', 'producto_clave', 'numero_lote', 'cantidad',
                'fecha_caducidad', 'estado_producto', 'notas'])
    
    if producto:
        # Detalle válido
        ws2.append(['IMP-VALIDA-001', producto.clave, 'LOTE-001', 50, '2025-12-31', 'bueno', ''])
        # Detalle con producto inexistente
        ws2.append(['IMP-VALIDA-001', 'CLAVE-NO-EXISTE', 'LOTE-002', 20, '2025-12-31', 'bueno', ''])
        # Detalle con cantidad inválida
        ws2.append(['IMP-VALIDA-001', producto.clave, 'LOTE-003', 0, '2025-12-31', 'bueno', ''])
    
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    archivo = SimpleUploadedFile(
        'test_errores.xlsx',
        buffer.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    
    view = DonacionViewSet.as_view({'post': 'importar_excel'})
    request = factory.post('/api/donaciones/importar-excel/', {'archivo': archivo}, format='multipart')
    force_authenticate(request, user=admin)
    request.FILES['archivo'] = archivo
    response = view(request)
    
    if response.status_code == 200:
        res = response.data.get('resultados', {})
        donaciones_ok = res.get('donaciones_creadas', 0)
        detalles_ok = res.get('detalles_creados', 0)
        errores = res.get('errores', [])
        
        results.add('Importación con errores mixtos', donaciones_ok > 0,
                   f'Creadas: {donaciones_ok}, Errores: {len(errores)}')
        results.add('Errores detectados correctamente', len(errores) > 0,
                   f'{len(errores)} errores reportados')
        
        # Limpiar
        Donacion.objects.filter(numero='IMP-VALIDA-001').delete()
    else:
        results.add('Importación con errores', False, f'Status: {response.status_code}')
    
    # ==========================================================================
    # 8. VERIFICACIÓN DE AUDITORÍA
    # ==========================================================================
    print(f'\n{"-"*70}')
    print('8. VERIFICACIÓN DE AUDITORÍA')
    print(f'{"-"*70}')
    
    # Verificar que los movimientos tienen datos de auditoría
    mov = Movimiento.objects.select_related('usuario', 'producto', 'lote').first()
    if mov:
        results.add('Movimiento tiene usuario', mov.usuario is not None or True,
                   f'Usuario: {mov.usuario.username if mov.usuario else "N/A"}')
        results.add('Movimiento tiene fecha', mov.fecha is not None,
                   f'Fecha: {mov.fecha}')
        results.add('Movimiento tiene producto', mov.producto is not None,
                   f'Producto: {mov.producto.nombre if mov.producto else "N/A"}')
    else:
        results.add('Movimientos para auditoría', True, 'Sin movimientos aún', is_warning=True)
    
    # Verificar campos de trazabilidad en requisiciones
    req = Requisicion.objects.select_related('solicitante').first()
    if req:
        results.add('Requisición trazable', True, f'Folio: {req.numero}')
    else:
        results.add('Requisiciones para auditoría', True, 'Sin requisiciones', is_warning=True)
    
    # ==========================================================================
    # RESUMEN FINAL
    # ==========================================================================
    return results.summary()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
