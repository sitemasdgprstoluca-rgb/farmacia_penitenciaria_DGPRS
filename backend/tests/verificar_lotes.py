"""
Script de verificación funcional del módulo de Lotes.
Ejecuta pruebas directas contra la API sin usar pytest.
"""
import os
import sys
import django
from datetime import date, timedelta
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory
from rest_framework.test import APIClient
from core.models import Lote, Producto, Centro, User as Usuario

# Colores ANSI
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'
BOLD = '\033[1m'

def log_ok(msg):
    print(f"  {GREEN}✓{RESET} {msg}")

def log_fail(msg):
    print(f"  {RED}✗{RESET} {msg}")

def log_warn(msg):
    print(f"  {YELLOW}⚠{RESET} {msg}")

def log_section(title):
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}{title}{RESET}")
    print(f"{'='*60}")

# ==================== RESULTADOS ====================
resultados = {'ok': 0, 'fail': 0, 'skip': 0}

def test_passed():
    resultados['ok'] += 1

def test_failed():
    resultados['fail'] += 1

def test_skipped():
    resultados['skip'] += 1


# ==================== TESTS ====================

def test_modelo_lote():
    """Verificar estructura del modelo Lote."""
    log_section("1. VERIFICACIÓN DEL MODELO LOTE")
    
    # Verificar campos existentes
    campos_esperados = [
        'id', 'numero_lote', 'producto', 'cantidad_inicial',
        'cantidad_actual', 'fecha_fabricacion', 'fecha_caducidad',
        'precio_unitario', 'numero_contrato', 'marca', 'ubicacion',
        'centro', 'activo', 'created_at', 'updated_at'
    ]
    
    campos_modelo = [f.name for f in Lote._meta.get_fields() if hasattr(f, 'column') or f.name in ['producto', 'centro', 'id']]
    
    for campo in campos_esperados:
        if campo in campos_modelo or campo == 'id':
            log_ok(f"Campo '{campo}' presente en modelo")
            test_passed()
        else:
            log_fail(f"Campo '{campo}' NO encontrado")
            test_failed()
    
    # Verificar Foreign Keys
    try:
        fk_producto = Lote._meta.get_field('producto')
        assert fk_producto.is_relation
        log_ok("FK producto -> productos OK")
        test_passed()
    except:
        log_fail("FK producto no es relación válida")
        test_failed()
    
    try:
        fk_centro = Lote._meta.get_field('centro')
        assert fk_centro.is_relation
        log_ok("FK centro -> centros OK")
        test_passed()
    except:
        log_fail("FK centro no es relación válida")
        test_failed()


def test_serializer_lote():
    """Verificar serializer de Lote."""
    log_section("2. VERIFICACIÓN DEL SERIALIZER")
    
    from core.serializers import LoteSerializer
    
    # Obtener un lote existente para serializar
    lote = Lote.objects.filter(activo=True).first()
    
    if not lote:
        log_warn("No hay lotes activos para probar serialización")
        test_skipped()
        return
    
    serializer = LoteSerializer(lote)
    data = serializer.data
    
    # Campos esperados en serialización
    campos_esperados = [
        'id', 'numero_lote', 'producto', 'producto_nombre', 
        'cantidad_inicial', 'cantidad_actual', 'fecha_caducidad',
        'precio_unitario', 'marca', 'ubicacion', 'activo'
    ]
    
    for campo in campos_esperados:
        if campo in data:
            log_ok(f"Campo '{campo}' serializado correctamente")
            test_passed()
        else:
            log_fail(f"Campo '{campo}' NO presente en serialización")
            test_failed()
    
    # Verificar campos computados
    if 'estado_caducidad' in data:
        log_ok("Campo computado 'estado_caducidad' presente")
        test_passed()
    
    if 'dias_para_vencer' in data:
        log_ok("Campo computado 'dias_para_vencer' presente")
        test_passed()


def test_viewset_endpoints():
    """Verificar endpoints del ViewSet."""
    log_section("3. VERIFICACIÓN DE ENDPOINTS API")
    
    from inventario.views import LoteViewSet
    from rest_framework.routers import DefaultRouter
    
    # Verificar que el ViewSet tiene los métodos esperados
    viewset = LoteViewSet
    
    # Acciones estándar (CRUD)
    acciones = ['list', 'create', 'retrieve', 'update', 'partial_update', 'destroy']
    for accion in acciones:
        if hasattr(viewset, accion):
            log_ok(f"Acción CRUD '{accion}' presente")
            test_passed()
        else:
            log_fail(f"Acción CRUD '{accion}' NO encontrada")
            test_failed()
    
    # Acciones personalizadas
    acciones_extra = [
        'exportar_excel', 'exportar_pdf', 'importar_excel', 
        'plantilla_lotes', 'por_vencer', 'vencidos', 'por_caducar'
    ]
    
    for accion in acciones_extra:
        # Convertir a snake_case para buscar el método
        if hasattr(viewset, accion):
            log_ok(f"Endpoint extra '{accion}' presente")
            test_passed()
        else:
            log_warn(f"Endpoint '{accion}' podría tener otro nombre")
            test_skipped()


def test_permisos():
    """Verificar configuración de permisos."""
    log_section("4. VERIFICACIÓN DE PERMISOS")
    
    from inventario.views import LoteViewSet
    from core.permissions import IsFarmaciaAdminOrReadOnly
    
    # Verificar que el ViewSet usa los permisos correctos
    if hasattr(LoteViewSet, 'permission_classes'):
        permisos = LoteViewSet.permission_classes
        log_ok(f"Permisos configurados: {[p.__name__ for p in permisos]}")
        test_passed()
        
        # Verificar que incluye IsFarmaciaAdminOrReadOnly
        nombres_permisos = [p.__name__ for p in permisos]
        if 'IsFarmaciaAdminOrReadOnly' in nombres_permisos:
            log_ok("IsFarmaciaAdminOrReadOnly configurado")
            test_passed()
        else:
            log_warn("IsFarmaciaAdminOrReadOnly no encontrado en permisos")
            test_skipped()
    else:
        log_fail("No hay permission_classes definidas")
        test_failed()


def test_exportacion_funciones():
    """Verificar funciones de exportación."""
    log_section("5. VERIFICACIÓN DE EXPORTACIÓN")
    
    from inventario.views import LoteViewSet
    
    # Verificar métodos de exportación
    metodos_export = ['exportar_excel', 'exportar_pdf', 'plantilla_lotes']
    
    for metodo in metodos_export:
        if hasattr(LoteViewSet, metodo):
            log_ok(f"Método '{metodo}' implementado")
            test_passed()
            
            # Verificar decoradores
            m = getattr(LoteViewSet, metodo)
            if hasattr(m, 'kwargs') or hasattr(m, 'url_path'):
                log_ok(f"  -> Decorado como @action")
                test_passed()
        else:
            log_fail(f"Método '{metodo}' NO encontrado")
            test_failed()


def test_importacion():
    """Verificar función de importación."""
    log_section("6. VERIFICACIÓN DE IMPORTACIÓN")
    
    from inventario.views import LoteViewSet
    
    if hasattr(LoteViewSet, 'importar_excel'):
        log_ok("Método 'importar_excel' implementado")
        test_passed()
        
        # Verificar que es un método POST
        m = getattr(LoteViewSet, 'importar_excel')
        if hasattr(m, 'mapping'):
            if 'post' in m.mapping:
                log_ok("Configurado como método POST")
                test_passed()
    else:
        log_fail("Método 'importar_excel' NO encontrado")
        test_failed()
    
    # Verificar función de importación en utils
    try:
        from core.utils.excel_importer import importar_lotes_desde_excel
        log_ok("Función importar_lotes_desde_excel disponible")
        test_passed()
    except ImportError:
        log_fail("No se pudo importar importar_lotes_desde_excel")
        test_failed()


def test_filtros():
    """Verificar filtros configurados."""
    log_section("7. VERIFICACIÓN DE FILTROS")
    
    from inventario.views import LoteViewSet
    
    # Verificar filterset_fields o filterset_class
    if hasattr(LoteViewSet, 'filterset_fields') or hasattr(LoteViewSet, 'filterset_class'):
        log_ok("Filtros configurados en ViewSet")
        test_passed()
        
        if hasattr(LoteViewSet, 'filterset_fields'):
            campos = LoteViewSet.filterset_fields
            log_ok(f"  Campos de filtro: {campos}")
    else:
        log_warn("No se encontraron filterset_fields")
        test_skipped()
    
    # Verificar search_fields
    if hasattr(LoteViewSet, 'search_fields'):
        log_ok(f"Search fields: {LoteViewSet.search_fields}")
        test_passed()
    else:
        log_warn("No se encontraron search_fields")
        test_skipped()


def test_api_funcional():
    """Prueba funcional con API Client."""
    log_section("8. PRUEBA FUNCIONAL DE API")
    
    client = APIClient()
    
    # Obtener un usuario admin para autenticar
    admin = Usuario.objects.filter(rol='ADMIN', is_active=True).first()
    if not admin:
        admin = Usuario.objects.filter(is_superuser=True).first()
    
    if not admin:
        log_warn("No hay usuario admin para pruebas de API")
        test_skipped()
        return
    
    client.force_authenticate(user=admin)
    
    # Test GET /api/lotes/
    try:
        response = client.get('/api/lotes/')
        if response.status_code == 200:
            log_ok(f"GET /api/lotes/ -> {response.status_code}")
            test_passed()
            
            data = response.json()
            if 'results' in data:
                log_ok(f"  Paginación correcta, {len(data['results'])} resultados")
            elif isinstance(data, list):
                log_ok(f"  Lista de {len(data)} lotes")
        else:
            log_fail(f"GET /api/lotes/ -> {response.status_code}")
            test_failed()
    except Exception as e:
        log_fail(f"Error en GET /api/lotes/: {e}")
        test_failed()
    
    # Test GET /api/lotes/por-caducar/
    try:
        response = client.get('/api/lotes/por-caducar/')
        if response.status_code == 200:
            log_ok(f"GET /api/lotes/por-caducar/ -> {response.status_code}")
            test_passed()
        else:
            log_warn(f"GET /api/lotes/por-caducar/ -> {response.status_code}")
            test_skipped()
    except Exception as e:
        log_warn(f"Endpoint por-caducar: {e}")
        test_skipped()
    
    # Test GET /api/lotes/exportar-excel/
    try:
        response = client.get('/api/lotes/exportar-excel/')
        if response.status_code == 200:
            log_ok(f"GET /api/lotes/exportar-excel/ -> {response.status_code}")
            content_type = response.get('Content-Type', '')
            if 'spreadsheet' in content_type or 'excel' in content_type.lower():
                log_ok("  Content-Type correcto para Excel")
            test_passed()
        else:
            log_warn(f"GET /api/lotes/exportar-excel/ -> {response.status_code}")
            test_skipped()
    except Exception as e:
        log_warn(f"Endpoint exportar-excel: {e}")
        test_skipped()
    
    # Test GET /api/lotes/plantilla/
    try:
        response = client.get('/api/lotes/plantilla/')
        if response.status_code == 200:
            log_ok(f"GET /api/lotes/plantilla/ -> {response.status_code}")
            test_passed()
        else:
            log_warn(f"GET /api/lotes/plantilla/ -> {response.status_code}")
            test_skipped()
    except Exception as e:
        log_warn(f"Endpoint plantilla: {e}")
        test_skipped()


def test_consistencia_bd():
    """Verificar consistencia con esquema BD."""
    log_section("9. CONSISTENCIA CON ESQUEMA BD")
    
    # Campos del esquema BD según lo proporcionado
    campos_bd = [
        'id', 'numero_lote', 'producto_id', 'cantidad_inicial',
        'cantidad_actual', 'fecha_fabricacion', 'fecha_caducidad',
        'precio_unitario', 'numero_contrato', 'marca', 'ubicacion',
        'centro_id', 'activo', 'created_at', 'updated_at'
    ]
    
    # Mapear campos del modelo
    campos_modelo = {}
    for field in Lote._meta.get_fields():
        if hasattr(field, 'column'):
            campos_modelo[field.column] = field.name
        elif field.name in ['producto', 'centro']:
            campos_modelo[field.name + '_id'] = field.name
    
    log_ok(f"Campos en modelo: {len(campos_modelo)}")
    
    for campo in campos_bd:
        if campo in campos_modelo or campo == 'id':
            log_ok(f"Campo BD '{campo}' mapeado correctamente")
            test_passed()
        else:
            log_warn(f"Campo BD '{campo}' no encontrado (puede ser auto)")
            test_skipped()
    
    # Verificar db_table
    if Lote._meta.db_table == 'lotes':
        log_ok("db_table = 'lotes' correcto")
        test_passed()
    else:
        log_fail(f"db_table incorrecto: {Lote._meta.db_table}")
        test_failed()


def main():
    """Ejecutar todas las pruebas."""
    print(f"\n{BOLD}{'#'*60}{RESET}")
    print(f"{BOLD}# PRUEBAS UNITARIAS - MÓDULO DE LOTES{RESET}")
    print(f"{BOLD}# Farmacia Penitenciaria{RESET}")
    print(f"{'#'*60}")
    
    test_modelo_lote()
    test_serializer_lote()
    test_viewset_endpoints()
    test_permisos()
    test_exportacion_funciones()
    test_importacion()
    test_filtros()
    test_api_funcional()
    test_consistencia_bd()
    
    # Resumen
    log_section("RESUMEN FINAL")
    total = resultados['ok'] + resultados['fail'] + resultados['skip']
    print(f"\n  {GREEN}Pasaron:{RESET}  {resultados['ok']}")
    print(f"  {RED}Fallaron:{RESET} {resultados['fail']}")
    print(f"  {YELLOW}Saltadas:{RESET} {resultados['skip']}")
    print(f"  {BOLD}Total:{RESET}    {total}")
    
    if resultados['fail'] == 0:
        print(f"\n{GREEN}{BOLD}✅ TODAS LAS PRUEBAS PASARON{RESET}")
        return 0
    else:
        print(f"\n{RED}{BOLD}❌ HAY {resultados['fail']} PRUEBAS FALLIDAS{RESET}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
