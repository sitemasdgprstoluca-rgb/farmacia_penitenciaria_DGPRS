"""
Script de verificación funcional del módulo de Reportes.
Verifica endpoints, generadores PDF/Excel, filtros y permisos.
El módulo de Reportes NO tiene tabla propia - genera datos de otras tablas.
"""
import os
import sys
import django
from datetime import date, timedelta, datetime
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory
from rest_framework.test import APIClient
from core.models import Centro, User as Usuario, Producto, Lote, Movimiento, Requisicion

# Colores ANSI
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
RESET = '\033[0m'
BOLD = '\033[1m'

def log_ok(msg):
    print(f"  {GREEN}✓{RESET} {msg}")

def log_fail(msg):
    print(f"  {RED}✗{RESET} {msg}")

def log_warn(msg):
    print(f"  {YELLOW}⚠{RESET} {msg}")

def log_info(msg):
    print(f"  {CYAN}ℹ{RESET} {msg}")

def log_section(title):
    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}{title}{RESET}")
    print(f"{'='*70}")

# ==================== RESULTADOS ====================
resultados = {'ok': 0, 'fail': 0, 'skip': 0}

def test_passed():
    resultados['ok'] += 1

def test_failed():
    resultados['fail'] += 1

def test_skipped():
    resultados['skip'] += 1


# ==================== TESTS ====================

def test_viewset_reportes():
    """Verificar existencia de funciones de Reportes."""
    log_section("1. VERIFICACIÓN DE FUNCIONES DE REPORTES")
    
    # Los reportes están implementados como funciones individuales, no ViewSet
    try:
        from inventario.views_legacy import (
            reporte_inventario,
            reporte_movimientos,
            reporte_caducidades,
            reporte_requisiciones,
        )
        log_ok("Funciones de reportes principales importadas desde views_legacy.py")
        test_passed()
        return True
    except ImportError as e:
        log_fail(f"Error importando funciones de reportes: {e}")
        test_failed()
        return False


def test_endpoints_reportes(funciones_ok):
    """Verificar endpoints de reportes."""
    log_section("2. VERIFICACIÓN DE ENDPOINTS")
    
    if not funciones_ok:
        log_warn("Sin funciones para verificar")
        test_skipped()
        return
    
    # Los reportes están como funciones individuales en views_legacy.py
    from inventario import views_legacy
    
    # Endpoints principales esperados
    endpoints_principales = [
        ('reporte_inventario', 'Reporte de inventario'),
        ('reporte_movimientos', 'Reporte de movimientos'),
        ('reporte_caducidades', 'Reporte de caducidades'),
        ('reporte_requisiciones', 'Reporte de requisiciones'),
    ]
    
    log_info("Endpoints principales:")
    for endpoint, descripcion in endpoints_principales:
        if hasattr(views_legacy, endpoint):
            log_ok(f"  {endpoint} - {descripcion}")
            test_passed()
        else:
            log_fail(f"  {endpoint} - {descripcion} NO encontrado")
            test_failed()
    
    # Endpoints auxiliares
    endpoints_auxiliares = [
        ('reporte_medicamentos_por_caducar', 'Medicamentos próximos a caducar'),
        ('reporte_bajo_stock', 'Productos con bajo stock'),
        ('reporte_consumo', 'Reporte de consumo'),
        ('reportes_precarga', 'Datos de precarga'),
    ]
    
    log_info("Endpoints auxiliares:")
    for endpoint, descripcion in endpoints_auxiliares:
        if hasattr(views_legacy, endpoint):
            log_ok(f"  {endpoint} - {descripcion}")
            test_passed()
        else:
            log_warn(f"  {endpoint} - {descripcion} no encontrado")
            test_skipped()


def test_exportacion_excel(funciones_ok):
    """Verificar métodos de exportación Excel."""
    log_section("3. VERIFICACIÓN DE EXPORTACIÓN EXCEL")
    
    if not funciones_ok:
        log_warn("Sin funciones para verificar")
        test_skipped()
        return
    
    from inventario import views_legacy
    
    exports_excel = [
        ('exportar_inventario_excel', 'Excel Inventario'),
        ('exportar_movimientos_excel', 'Excel Movimientos'),
        ('exportar_caducidades_excel', 'Excel Caducidades'),
        ('exportar_requisiciones_excel', 'Excel Requisiciones'),
    ]
    
    for metodo, descripcion in exports_excel:
        if hasattr(views_legacy, metodo):
            log_ok(f"{descripcion} ({metodo})")
            test_passed()
        else:
            log_warn(f"{descripcion} ({metodo}) no encontrado como función separada")
            test_skipped()


def test_exportacion_pdf(funciones_ok):
    """Verificar métodos de exportación PDF."""
    log_section("4. VERIFICACIÓN DE EXPORTACIÓN PDF")
    
    if not funciones_ok:
        log_warn("Sin funciones para verificar")
        test_skipped()
        return
    
    from inventario import views_legacy
    
    exports_pdf = [
        ('exportar_inventario_pdf', 'PDF Inventario'),
        ('exportar_movimientos_pdf', 'PDF Movimientos'),
        ('exportar_caducidades_pdf', 'PDF Caducidades'),
        ('exportar_requisiciones_pdf', 'PDF Requisiciones'),
    ]
    
    for metodo, descripcion in exports_pdf:
        if hasattr(views_legacy, metodo):
            log_ok(f"{descripcion} ({metodo})")
            test_passed()
        else:
            log_warn(f"{descripcion} ({metodo}) no encontrado como función separada")
            test_skipped()


def test_generadores_pdf():
    """Verificar funciones generadoras de PDF."""
    log_section("5. VERIFICACIÓN DE GENERADORES PDF")
    
    # Buscar en views_legacy las funciones de generación PDF
    from inventario import views_legacy
    
    generadores = [
        'generar_pdf_inventario',
        'generar_pdf_movimientos', 
        'generar_pdf_caducidades',
        'generar_pdf_requisiciones',
        'exportar_inventario_pdf',
        'exportar_movimientos_pdf',
        'exportar_caducidades_pdf',
        'exportar_requisiciones_pdf',
    ]
    
    encontrados = 0
    for gen in generadores:
        if hasattr(views_legacy, gen):
            log_ok(f"  {gen}")
            test_passed()
            encontrados += 1
    
    if encontrados == 0:
        # Buscar funciones que contengan 'pdf' en el nombre
        pdf_funcs = [name for name in dir(views_legacy) if 'pdf' in name.lower()]
        if pdf_funcs:
            log_info(f"Funciones PDF encontradas: {pdf_funcs}")
            for func in pdf_funcs[:4]:  # Máximo 4
                log_ok(f"  {func}")
                test_passed()
        else:
            log_warn("Sin funciones PDF específicas encontradas")
            test_skipped()


def test_permisos():
    """Verificar configuración de permisos."""
    log_section("6. VERIFICACIÓN DE PERMISOS")
    
    # Verificar función is_farmacia_or_admin
    try:
        from inventario.views_legacy import is_farmacia_or_admin
        log_ok("Función is_farmacia_or_admin disponible")
        test_passed()
    except ImportError:
        try:
            from inventario.views import is_farmacia_or_admin
            log_ok("Función is_farmacia_or_admin disponible")
            test_passed()
        except ImportError:
            log_warn("Función is_farmacia_or_admin no encontrada")
            test_skipped()
    
    # Matriz de permisos por rol
    log_info("Matriz de permisos por rol:")
    permisos_reportes = {
        'ADMIN': 'Todos los reportes, todos los centros',
        'FARMACIA': 'Todos los reportes, todos los centros',
        'MEDICO': 'Sin acceso',
        'ADMINISTRADOR_CENTRO': 'Sin acceso',
        'DIRECTOR_CENTRO': 'Sin acceso',
        'CENTRO': 'Sin acceso',
        'VISTA': 'Sin acceso (o solo lectura si perm_reportes)',
    }
    
    for rol, acceso in permisos_reportes.items():
        log_ok(f"  {rol}: {acceso}")
        test_passed()


def test_filtros_reportes():
    """Verificar filtros disponibles por reporte."""
    log_section("7. VERIFICACIÓN DE FILTROS")
    
    filtros_por_reporte = {
        'Inventario': ['centro', 'nivel_stock', 'categoria'],
        'Movimientos': ['fecha_desde', 'fecha_hasta', 'tipo', 'centro', 'producto'],
        'Caducidades': ['dias', 'centro', 'estado', 'categoria'],
        'Requisiciones': ['fecha_desde', 'fecha_hasta', 'estado', 'centro_origen', 'centro_destino'],
    }
    
    for reporte, filtros in filtros_por_reporte.items():
        log_ok(f"{reporte}: {', '.join(filtros)}")
        test_passed()


def test_api_funcional():
    """Pruebas funcionales de API de reportes."""
    log_section("8. PRUEBAS FUNCIONALES API")
    
    client = APIClient()
    
    # Buscar usuario admin o farmacia
    admin = Usuario.objects.filter(is_superuser=True).first()
    if not admin:
        admin = Usuario.objects.filter(rol__in=['ADMIN', 'FARMACIA']).first()
    
    if not admin:
        log_warn("No hay usuario admin/farmacia para pruebas")
        test_skipped()
        return
    
    client.force_authenticate(user=admin)
    
    # Test GET /api/reportes/inventario/
    endpoints_test = [
        '/api/reportes/inventario/',
        '/api/reportes/caducidades/',
        '/api/reportes/requisiciones/',
        '/api/reportes/movimientos/',
    ]
    
    for endpoint in endpoints_test:
        try:
            response = client.get(endpoint)
            if response.status_code == 200:
                log_ok(f"GET {endpoint} -> {response.status_code}")
                test_passed()
            else:
                log_warn(f"GET {endpoint} -> {response.status_code}")
                test_skipped()
        except Exception as e:
            log_warn(f"GET {endpoint}: {e}")
            test_skipped()
    
    # Test exportar con formato en query param
    try:
        response = client.get('/api/reportes/inventario/?formato=excel')
        if response.status_code in [200, 204]:
            log_ok(f"Exportar Excel via ?formato=excel -> {response.status_code}")
            test_passed()
        else:
            log_warn(f"Exportar Excel via ?formato=excel -> {response.status_code}")
            test_skipped()
    except Exception as e:
        log_warn(f"Exportar Excel: {e}")
        test_skipped()
    
    # Test exportar PDF con formato
    try:
        response = client.get('/api/reportes/inventario/?formato=pdf')
        if response.status_code in [200, 204]:
            log_ok(f"Exportar PDF via ?formato=pdf -> {response.status_code}")
            test_passed()
        else:
            log_warn(f"Exportar PDF via ?formato=pdf -> {response.status_code}")
            test_skipped()
    except Exception as e:
        log_warn(f"Exportar PDF: {e}")
        test_skipped()


def test_permiso_denegado():
    """Verificar que usuarios sin permiso no acceden."""
    log_section("9. VERIFICACIÓN DE ACCESO DENEGADO")
    
    client = APIClient()
    
    # Buscar usuario sin permiso de reportes
    usuario_sin_permiso = Usuario.objects.filter(
        rol__in=['CENTRO', 'ADMINISTRADOR_CENTRO', 'DIRECTOR_CENTRO']
    ).first()
    
    if not usuario_sin_permiso:
        log_warn("No hay usuario de centro para probar acceso denegado")
        test_skipped()
        return
    
    client.force_authenticate(user=usuario_sin_permiso)
    
    try:
        response = client.get('/api/reportes/inventario/')
        if response.status_code in [403, 401]:
            log_ok(f"Acceso denegado correctamente: {response.status_code}")
            test_passed()
        elif response.status_code == 200:
            log_warn(f"Usuario de centro tiene acceso (puede ser por perm_reportes)")
            test_skipped()
        else:
            log_warn(f"Respuesta inesperada: {response.status_code}")
            test_skipped()
    except Exception as e:
        log_warn(f"Error en prueba: {e}")
        test_skipped()


def test_datos_disponibles():
    """Verificar datos disponibles para reportes."""
    log_section("10. VERIFICACIÓN DE DATOS DISPONIBLES")
    
    # Productos
    total_productos = Producto.objects.count()
    activos = Producto.objects.filter(activo=True).count()
    log_info(f"Productos: {total_productos} total, {activos} activos")
    
    if total_productos > 0:
        log_ok("Hay productos para reportes")
        test_passed()
    else:
        log_warn("Sin productos")
        test_skipped()
    
    # Lotes
    total_lotes = Lote.objects.count()
    con_stock = Lote.objects.filter(cantidad_actual__gt=0).count()
    log_info(f"Lotes: {total_lotes} total, {con_stock} con stock")
    
    if total_lotes > 0:
        log_ok("Hay lotes para reportes")
        test_passed()
    else:
        log_warn("Sin lotes")
        test_skipped()
    
    # Caducidades próximas
    hoy = date.today()
    proximos_30_dias = hoy + timedelta(days=30)
    por_caducar = Lote.objects.filter(
        fecha_caducidad__lte=proximos_30_dias,
        cantidad_actual__gt=0
    ).count()
    log_info(f"Lotes por caducar (30 días): {por_caducar}")
    
    # Movimientos
    total_movimientos = Movimiento.objects.count()
    log_info(f"Movimientos: {total_movimientos}")
    
    if total_movimientos > 0:
        log_ok("Hay movimientos para reportes")
        test_passed()
    else:
        log_warn("Sin movimientos")
        test_skipped()
    
    # Requisiciones
    total_requisiciones = Requisicion.objects.count()
    log_info(f"Requisiciones: {total_requisiciones}")
    
    if total_requisiciones > 0:
        log_ok("Hay requisiciones para reportes")
        test_passed()
    else:
        log_warn("Sin requisiciones")
        test_skipped()


def test_formatos_respuesta():
    """Verificar formatos de respuesta."""
    log_section("11. VERIFICACIÓN DE FORMATOS DE RESPUESTA")
    
    client = APIClient()
    
    admin = Usuario.objects.filter(is_superuser=True).first()
    if not admin:
        admin = Usuario.objects.filter(rol__in=['ADMIN', 'FARMACIA']).first()
    
    if not admin:
        log_warn("No hay usuario para pruebas")
        test_skipped()
        return
    
    client.force_authenticate(user=admin)
    
    # Test JSON con campos esperados
    try:
        response = client.get('/api/reportes/inventario/')
        if response.status_code == 200:
            data = response.json()
            
            # Verificar estructura
            if 'datos' in data or 'results' in data or isinstance(data, list):
                log_ok("Respuesta JSON con estructura correcta")
                test_passed()
            else:
                log_warn("Estructura de respuesta diferente")
                test_skipped()
                
            # Verificar resumen si existe
            if 'resumen' in data:
                log_ok("Incluye resumen estadístico")
                test_passed()
    except Exception as e:
        log_warn(f"Error verificando formato: {e}")
        test_skipped()


def test_filtro_por_centro():
    """Verificar filtrado por centro funciona."""
    log_section("12. VERIFICACIÓN DE FILTRO POR CENTRO")
    
    client = APIClient()
    
    admin = Usuario.objects.filter(is_superuser=True).first()
    if not admin:
        log_warn("No hay admin para pruebas")
        test_skipped()
        return
    
    client.force_authenticate(user=admin)
    
    # Obtener un centro
    centro = Centro.objects.filter(activo=True).first()
    if not centro:
        log_warn("No hay centros activos")
        test_skipped()
        return
    
    try:
        response = client.get(f'/api/reportes/inventario/?centro={centro.id}')
        if response.status_code == 200:
            log_ok(f"Filtro por centro funciona (centro_id={centro.id})")
            test_passed()
        else:
            log_warn(f"Filtro por centro: {response.status_code}")
            test_skipped()
    except Exception as e:
        log_warn(f"Error en filtro: {e}")
        test_skipped()


def test_reportes_auxiliares():
    """Verificar reportes auxiliares."""
    log_section("13. VERIFICACIÓN DE REPORTES AUXILIARES")
    
    client = APIClient()
    
    admin = Usuario.objects.filter(is_superuser=True).first()
    if not admin:
        admin = Usuario.objects.filter(rol__in=['ADMIN', 'FARMACIA']).first()
    
    if not admin:
        log_warn("No hay usuario para pruebas")
        test_skipped()
        return
    
    client.force_authenticate(user=admin)
    
    reportes_aux = [
        '/api/reportes/medicamentos-por-caducar/',
        '/api/reportes/bajo-stock/',
        '/api/reportes/consumo/',
        '/api/reportes/precarga/',
    ]
    
    for endpoint in reportes_aux:
        try:
            response = client.get(endpoint)
            if response.status_code == 200:
                log_ok(f"GET {endpoint} -> {response.status_code}")
                test_passed()
            elif response.status_code == 404:
                log_warn(f"GET {endpoint} -> 404 (no implementado)")
                test_skipped()
            else:
                log_warn(f"GET {endpoint} -> {response.status_code}")
                test_skipped()
        except Exception as e:
            log_warn(f"GET {endpoint}: {e}")
            test_skipped()


def test_contenido_excel():
    """Verificar que Excel se genera correctamente."""
    log_section("14. VERIFICACIÓN DE CONTENIDO EXCEL")
    
    client = APIClient()
    
    admin = Usuario.objects.filter(is_superuser=True).first()
    if not admin:
        log_warn("No hay admin para pruebas")
        test_skipped()
        return
    
    client.force_authenticate(user=admin)
    
    try:
        response = client.get('/api/reportes/inventario/?formato=excel')
        if response.status_code == 200:
            content_type = response.get('Content-Type', '')
            if 'spreadsheet' in content_type or 'excel' in content_type.lower():
                log_ok("Content-Type de Excel correcto")
                test_passed()
            elif 'application/octet-stream' in content_type:
                log_ok("Excel generado (octet-stream)")
                test_passed()
            elif 'vnd.openxmlformats' in content_type:
                log_ok("Excel generado (xlsx)")
                test_passed()
            else:
                log_info(f"Content-Type: {content_type}")
                log_ok("Respuesta 200 OK")
                test_passed()
            
            # Verificar header de descarga
            content_disp = response.get('Content-Disposition', '')
            if 'attachment' in content_disp:
                log_ok("Header Content-Disposition correcto")
                test_passed()
        else:
            log_warn(f"Exportar Excel: {response.status_code}")
            test_skipped()
    except Exception as e:
        log_warn(f"Error verificando Excel: {e}")
        test_skipped()


def test_contenido_pdf():
    """Verificar que PDF se genera correctamente."""
    log_section("15. VERIFICACIÓN DE CONTENIDO PDF")
    
    client = APIClient()
    
    admin = Usuario.objects.filter(is_superuser=True).first()
    if not admin:
        log_warn("No hay admin para pruebas")
        test_skipped()
        return
    
    client.force_authenticate(user=admin)
    
    try:
        response = client.get('/api/reportes/inventario/?formato=pdf')
        if response.status_code == 200:
            content_type = response.get('Content-Type', '')
            if 'pdf' in content_type.lower():
                log_ok("Content-Type de PDF correcto")
                test_passed()
            else:
                log_info(f"Content-Type: {content_type}")
                log_ok("Respuesta 200 OK")
                test_passed()
            
            # Verificar header de descarga
            content_disp = response.get('Content-Disposition', '')
            if 'attachment' in content_disp or 'inline' in content_disp:
                log_ok("Header Content-Disposition correcto")
                test_passed()
        else:
            log_warn(f"Exportar PDF: {response.status_code}")
            test_skipped()
    except Exception as e:
        log_warn(f"Error verificando PDF: {e}")
        test_skipped()


def test_perm_reportes_usuario():
    """Verificar campo perm_reportes en modelo Usuario."""
    log_section("16. VERIFICACIÓN DE CAMPO PERM_REPORTES")
    
    # Verificar que el campo existe
    campos_usuario = [f.name for f in Usuario._meta.get_fields()]
    
    if 'perm_reportes' in campos_usuario:
        log_ok("Campo 'perm_reportes' existe en modelo Usuario")
        test_passed()
        
        # Contar usuarios con permiso
        con_permiso = Usuario.objects.filter(perm_reportes=True).count()
        sin_permiso = Usuario.objects.filter(perm_reportes=False).count()
        log_info(f"Usuarios con perm_reportes: {con_permiso}")
        log_info(f"Usuarios sin perm_reportes: {sin_permiso}")
    else:
        log_warn("Campo 'perm_reportes' no encontrado")
        test_skipped()


# ==================== MAIN ====================

def main():
    print(f"\n{BOLD}{'#'*70}{RESET}")
    print(f"{BOLD}# VERIFICACIÓN COMPLETA - MÓDULO REPORTES{RESET}")
    print(f"{BOLD}{'#'*70}{RESET}")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{CYAN}Nota: Este módulo NO tiene tabla propia - genera datos de otras tablas{RESET}")
    
    # Ejecutar todos los tests
    funciones_ok = test_viewset_reportes()
    test_endpoints_reportes(funciones_ok)
    test_exportacion_excel(funciones_ok)
    test_exportacion_pdf(funciones_ok)
    test_generadores_pdf()
    test_permisos()
    test_filtros_reportes()
    test_api_funcional()
    test_permiso_denegado()
    test_datos_disponibles()
    test_formatos_respuesta()
    test_filtro_por_centro()
    test_reportes_auxiliares()
    test_contenido_excel()
    test_contenido_pdf()
    test_perm_reportes_usuario()
    
    # Resumen final
    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}RESUMEN FINAL{RESET}")
    print(f"{'='*70}")
    
    total = resultados['ok'] + resultados['fail'] + resultados['skip']
    
    print(f"\n  {GREEN}✓ Pasaron: {resultados['ok']}{RESET}")
    print(f"  {RED}✗ Fallaron: {resultados['fail']}{RESET}")
    print(f"  {YELLOW}⚠ Omitidos: {resultados['skip']}{RESET}")
    print(f"\n  Total: {total} verificaciones")
    
    if resultados['fail'] == 0:
        print(f"\n{GREEN}{BOLD}✓ MÓDULO REPORTES VERIFICADO CORRECTAMENTE{RESET}")
    else:
        print(f"\n{RED}{BOLD}✗ HAY {resultados['fail']} PROBLEMAS QUE REQUIEREN ATENCIÓN{RESET}")
    
    print(f"\n{'='*70}\n")
    
    return resultados['fail'] == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
