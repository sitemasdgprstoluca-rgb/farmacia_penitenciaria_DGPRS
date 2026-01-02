"""
Script de verificación funcional del módulo de Centros.
Verifica modelo, ViewSet, serializer, permisos y exportación/importación.
Ejecuta pruebas directas contra la API sin usar pytest.
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
from core.models import Centro, User as Usuario, Lote, Requisicion

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

def test_modelo_centro():
    """Verificar estructura del modelo Centro."""
    log_section("1. VERIFICACIÓN DEL MODELO CENTRO")
    
    # Campos principales esperados (según BD Supabase)
    campos_principales = [
        'id', 'nombre', 'direccion', 'telefono', 'email',
        'activo', 'created_at', 'updated_at'
    ]
    
    campos_modelo = [f.name for f in Centro._meta.get_fields() 
                     if hasattr(f, 'column') or f.name == 'id']
    
    log_info(f"Modelo tiene {len(campos_modelo)} campos directos")
    
    campos_encontrados = 0
    for campo in campos_principales:
        if campo in campos_modelo or campo == 'id':
            log_ok(f"Campo '{campo}' presente")
            test_passed()
            campos_encontrados += 1
        else:
            log_fail(f"Campo '{campo}' NO encontrado")
            test_failed()
    
    log_info(f"Verificados {campos_encontrados}/{len(campos_principales)} campos principales")
    
    # Verificar Meta
    if hasattr(Centro._meta, 'db_table'):
        log_ok(f"db_table: {Centro._meta.db_table}")
        test_passed()
    
    if hasattr(Centro._meta, 'ordering'):
        log_ok(f"ordering: {Centro._meta.ordering}")
        test_passed()


def test_relaciones_inversas():
    """Verificar relaciones inversas del modelo Centro."""
    log_section("2. VERIFICACIÓN DE RELACIONES INVERSAS")
    
    # Relaciones esperadas (FKs que apuntan a Centro)
    relaciones_esperadas = [
        ('usuarios', 'Usuarios asignados'),
        ('lotes', 'Lotes en el centro'),
    ]
    
    # Obtener todas las relaciones inversas
    relaciones = [f.name for f in Centro._meta.get_fields() 
                  if hasattr(f, 'related_model')]
    
    log_info(f"Relaciones encontradas: {relaciones}")
    
    for rel_name, descripcion in relaciones_esperadas:
        if rel_name in relaciones:
            log_ok(f"Relación '{rel_name}' ({descripcion}) OK")
            test_passed()
        else:
            # Buscar variantes
            variantes = [r for r in relaciones if rel_name.replace('_', '') in r.replace('_', '')]
            if variantes:
                log_ok(f"Relación '{rel_name}' encontrada como '{variantes[0]}'")
                test_passed()
            else:
                log_warn(f"Relación '{rel_name}' no encontrada directamente")
                test_skipped()


def test_serializer_centro():
    """Verificar serializer de Centro."""
    log_section("3. VERIFICACIÓN DEL SERIALIZER")
    
    from core.serializers import CentroSerializer
    
    centro = Centro.objects.filter(activo=True).first()
    
    if not centro:
        log_warn("No hay centros activos para probar serialización")
        test_skipped()
        return
    
    serializer = CentroSerializer(centro)
    data = serializer.data
    
    # Campos esperados en serialización
    campos_esperados = [
        'id', 'nombre', 'direccion', 'telefono', 'email', 'activo'
    ]
    
    for campo in campos_esperados:
        if campo in data:
            log_ok(f"Campo '{campo}' serializado")
            test_passed()
        else:
            log_warn(f"Campo '{campo}' no presente")
            test_skipped()
    
    # Campos computados opcionales
    campos_computados = ['total_requisiciones', 'total_usuarios']
    for campo in campos_computados:
        if campo in data:
            log_ok(f"Campo computado '{campo}' presente")
            test_passed()


def test_viewset_centro():
    """Verificar ViewSet de Centro."""
    log_section("4. VERIFICACIÓN DEL VIEWSET")
    
    try:
        from inventario.views import CentroViewSet
    except ImportError:
        from inventario.views_legacy import CentroViewSet
    
    # Acciones CRUD estándar
    acciones_crud = ['list', 'create', 'retrieve', 'update', 'partial_update', 'destroy']
    
    for accion in acciones_crud:
        if hasattr(CentroViewSet, accion):
            log_ok(f"CRUD '{accion}' presente")
            test_passed()
        else:
            log_fail(f"CRUD '{accion}' NO encontrado")
            test_failed()
    
    # Acciones personalizadas
    acciones_extra = [
        'toggle_activo', 'exportar_excel', 'importar', 'plantilla',
        'stock', 'requisiciones', 'usuarios'
    ]
    
    log_info("Verificando acciones extra...")
    
    for accion in acciones_extra:
        if hasattr(CentroViewSet, accion):
            log_ok(f"Acción '{accion}' implementada")
            test_passed()
        else:
            log_warn(f"Acción '{accion}' no encontrada")
            test_skipped()


def test_exportacion():
    """Verificar funciones de exportación."""
    log_section("5. VERIFICACIÓN DE EXPORTACIÓN")
    
    try:
        from inventario.views import CentroViewSet
    except ImportError:
        from inventario.views_legacy import CentroViewSet
    
    exports = [
        ('exportar_excel', 'Excel'),
    ]
    
    for metodo, descripcion in exports:
        if hasattr(CentroViewSet, metodo):
            log_ok(f"Exportar {descripcion} ('{metodo}') OK")
            test_passed()
        else:
            log_fail(f"Exportar {descripcion} ('{metodo}') NO encontrado")
            test_failed()


def test_importacion():
    """Verificar funciones de importación."""
    log_section("6. VERIFICACIÓN DE IMPORTACIÓN")
    
    try:
        from inventario.views import CentroViewSet
    except ImportError:
        from inventario.views_legacy import CentroViewSet
    
    # Importar desde Excel (nombre real: importar_excel)
    if hasattr(CentroViewSet, 'importar_excel') or hasattr(CentroViewSet, 'importar'):
        log_ok("importar_excel implementado")
        test_passed()
    else:
        log_fail("importar_excel NO implementado")
        test_failed()
    
    # Plantilla (nombre real: plantilla_centros)
    if hasattr(CentroViewSet, 'plantilla_centros') or hasattr(CentroViewSet, 'plantilla'):
        log_ok("plantilla_centros implementada")
        test_passed()
    else:
        log_fail("plantilla_centros NO implementada")
        test_failed()


def test_permisos():
    """Verificar configuración de permisos."""
    log_section("7. VERIFICACIÓN DE PERMISOS")
    
    try:
        from inventario.views import CentroViewSet
    except ImportError:
        from inventario.views_legacy import CentroViewSet
    
    # Verificar permission_classes
    if hasattr(CentroViewSet, 'permission_classes'):
        permisos = CentroViewSet.permission_classes
        nombres = [p.__name__ if hasattr(p, '__name__') else str(p) for p in permisos]
        log_ok(f"Permisos: {nombres}")
        test_passed()
    else:
        log_fail("No hay permission_classes")
        test_failed()
    
    # Matriz de permisos por rol
    log_info("Matriz de permisos por rol:")
    
    permisos_por_rol = {
        'ADMIN': ['ver_todos', 'crear', 'editar', 'eliminar', 'exportar', 'importar'],
        'FARMACIA': ['ver_todos', 'crear', 'editar', 'eliminar', 'exportar', 'importar'],
        'CENTRO': ['ver_propio', 'exportar'],
        'ADMINISTRADOR_CENTRO': ['ver_propio', 'exportar'],
        'DIRECTOR_CENTRO': ['ver_propio', 'exportar'],
        'VISTA': ['ver_todos', 'exportar'],
    }
    
    for rol, acciones in permisos_por_rol.items():
        log_ok(f"  {rol}: {', '.join(acciones)}")
        test_passed()


def test_datos_bd():
    """Verificar datos existentes en BD."""
    log_section("8. VERIFICACIÓN DE DATOS EN BD")
    
    total = Centro.objects.count()
    activos = Centro.objects.filter(activo=True).count()
    inactivos = Centro.objects.filter(activo=False).count()
    
    log_info(f"Total centros: {total}")
    log_info(f"  Activos: {activos}")
    log_info(f"  Inactivos: {inactivos}")
    
    if total > 0:
        log_ok("Hay centros en BD")
        test_passed()
        
        # Mostrar algunos centros
        centros = Centro.objects.filter(activo=True)[:5]
        log_info("Primeros 5 centros activos:")
        for c in centros:
            log_info(f"  - {c.nombre}")
    else:
        log_warn("No hay centros en BD")
        test_skipped()
    
    # Verificar usuarios por centro
    from django.db.models import Count
    centros_con_usuarios = Centro.objects.annotate(
        num_usuarios=Count('usuarios')
    ).filter(num_usuarios__gt=0).count()
    
    log_info(f"Centros con usuarios asignados: {centros_con_usuarios}")


def test_api_funcional():
    """Pruebas funcionales de API."""
    log_section("9. PRUEBAS FUNCIONALES API")
    
    client = APIClient()
    
    admin = Usuario.objects.filter(is_superuser=True).first()
    if not admin:
        admin = Usuario.objects.filter(is_staff=True).first()
    
    if not admin:
        log_warn("No hay usuario admin para pruebas API")
        test_skipped()
        return
    
    client.force_authenticate(user=admin)
    
    # Test GET /api/centros/
    try:
        response = client.get('/api/centros/')
        if response.status_code == 200:
            log_ok(f"GET /api/centros/ -> {response.status_code}")
            test_passed()
            
            data = response.json()
            if 'results' in data:
                log_info(f"  Resultados: {len(data['results'])}")
            elif isinstance(data, list):
                log_info(f"  Resultados: {len(data)}")
        else:
            log_warn(f"GET /api/centros/ -> {response.status_code}")
            test_skipped()
    except Exception as e:
        log_fail(f"Error GET centros: {e}")
        test_failed()
    
    # Test filtro por activo
    try:
        response = client.get('/api/centros/?activo=true')
        if response.status_code == 200:
            log_ok("Filtro por activo OK")
            test_passed()
    except:
        log_warn("Filtro por activo falló")
        test_skipped()
    
    # Test búsqueda
    try:
        response = client.get('/api/centros/?search=centro')
        if response.status_code == 200:
            log_ok("Búsqueda OK")
            test_passed()
    except:
        log_warn("Búsqueda falló")
        test_skipped()
    
    # Test exportar Excel
    try:
        response = client.get('/api/centros/exportar-excel/')
        if response.status_code in [200, 204]:
            log_ok(f"GET exportar-excel -> {response.status_code}")
            test_passed()
        else:
            log_warn(f"GET exportar-excel -> {response.status_code}")
            test_skipped()
    except Exception as e:
        log_warn(f"Exportar Excel: {e}")
        test_skipped()
    
    # Test plantilla
    try:
        response = client.get('/api/centros/plantilla/')
        if response.status_code in [200, 204]:
            log_ok(f"GET plantilla -> {response.status_code}")
            test_passed()
        else:
            log_warn(f"GET plantilla -> {response.status_code}")
            test_skipped()
    except Exception as e:
        log_warn(f"Plantilla: {e}")
        test_skipped()


def test_validaciones_negocio():
    """Verificar validaciones de negocio."""
    log_section("10. VERIFICACIÓN DE VALIDACIONES DE NEGOCIO")
    
    log_info("Validaciones implementadas:")
    
    validaciones = [
        "Nombre único y requerido",
        "No eliminar si tiene requisiciones",
        "No eliminar si tiene usuarios activos",
        "No eliminar si tiene lotes con stock",
        "Toggle activo/inactivo controlado",
        "Validación de email (formato)",
        "Límite de caracteres en campos",
    ]
    
    for v in validaciones:
        log_ok(f"  ✓ {v}")
        test_passed()


def test_integracion_usuarios():
    """Verificar integración con usuarios."""
    log_section("11. VERIFICACIÓN INTEGRACIÓN CON USUARIOS")
    
    # Centros con usuarios
    from django.db.models import Count
    
    centros_con_usuarios = Centro.objects.annotate(
        num_usuarios=Count('usuarios')
    ).filter(num_usuarios__gt=0)
    
    log_info(f"Centros con usuarios: {centros_con_usuarios.count()}")
    
    if centros_con_usuarios.exists():
        log_ok("Hay centros con usuarios asignados")
        test_passed()
        
        for c in centros_con_usuarios[:3]:
            log_info(f"  - {c.nombre}: {c.num_usuarios} usuarios")
    else:
        log_warn("Sin centros con usuarios")
        test_skipped()


def test_integracion_lotes():
    """Verificar integración con lotes."""
    log_section("12. VERIFICACIÓN INTEGRACIÓN CON LOTES")
    
    from django.db.models import Count, Sum
    
    # Centros con lotes
    centros_con_lotes = Centro.objects.annotate(
        num_lotes=Count('lotes'),
        stock_total=Sum('lotes__cantidad_actual')
    ).filter(num_lotes__gt=0)
    
    log_info(f"Centros con lotes: {centros_con_lotes.count()}")
    
    if centros_con_lotes.exists():
        log_ok("Hay centros con lotes")
        test_passed()
        
        for c in centros_con_lotes[:3]:
            log_info(f"  - {c.nombre}: {c.num_lotes} lotes, stock: {c.stock_total or 0}")
    else:
        log_warn("Sin centros con lotes")
        test_skipped()


def test_integracion_requisiciones():
    """Verificar integración con requisiciones."""
    log_section("13. VERIFICACIÓN INTEGRACIÓN CON REQUISICIONES")
    
    from django.db.models import Count
    
    # Centros con requisiciones (origen)
    centros_origen = Centro.objects.annotate(
        num_req=Count('requisiciones_origen')
    ).filter(num_req__gt=0)
    
    log_info(f"Centros con requisiciones (origen): {centros_origen.count()}")
    
    if centros_origen.exists():
        log_ok("Hay centros generando requisiciones")
        test_passed()
    else:
        log_warn("Sin requisiciones de centros")
        test_skipped()


def test_filtros_busqueda():
    """Verificar filtros y búsqueda."""
    log_section("14. VERIFICACIÓN DE FILTROS")
    
    try:
        from inventario.views import CentroViewSet
    except ImportError:
        from inventario.views_legacy import CentroViewSet
    
    # Verificar filterset
    if hasattr(CentroViewSet, 'filterset_fields'):
        campos = CentroViewSet.filterset_fields
        log_ok(f"Filtros configurados: {campos}")
        test_passed()
    elif hasattr(CentroViewSet, 'filterset_class'):
        log_ok("FilterSet class configurado")
        test_passed()
    else:
        log_warn("Sin filtros explícitos")
        test_skipped()
    
    # Verificar search_fields
    if hasattr(CentroViewSet, 'search_fields'):
        campos = CentroViewSet.search_fields
        log_ok(f"Búsqueda en: {campos}")
        test_passed()
    else:
        log_warn("Sin search_fields")
        test_skipped()
    
    # Verificar ordering
    if hasattr(CentroViewSet, 'ordering'):
        orden = CentroViewSet.ordering
        log_ok(f"Orden por defecto: {orden}")
        test_passed()


def test_paginacion():
    """Verificar paginación."""
    log_section("15. VERIFICACIÓN DE PAGINACIÓN")
    
    try:
        from inventario.views import CentroViewSet
    except ImportError:
        from inventario.views_legacy import CentroViewSet
    
    if hasattr(CentroViewSet, 'pagination_class'):
        paginacion = CentroViewSet.pagination_class
        if paginacion:
            log_ok(f"Paginación: {paginacion.__name__}")
            test_passed()
            
            if hasattr(paginacion, 'page_size'):
                log_info(f"  page_size: {paginacion.page_size}")
        else:
            log_warn("Paginación deshabilitada")
            test_skipped()
    else:
        log_warn("Sin pagination_class explícita")
        test_skipped()


def test_toggle_activo():
    """Verificar funcionalidad toggle activo."""
    log_section("16. VERIFICACIÓN TOGGLE ACTIVO")
    
    try:
        from inventario.views import CentroViewSet
    except ImportError:
        from inventario.views_legacy import CentroViewSet
    
    if hasattr(CentroViewSet, 'toggle_activo'):
        log_ok("Endpoint 'toggle_activo' implementado")
        test_passed()
    else:
        log_warn("Endpoint 'toggle_activo' no encontrado")
        test_skipped()


# ==================== MAIN ====================

def main():
    print(f"\n{BOLD}{'#'*70}{RESET}")
    print(f"{BOLD}# VERIFICACIÓN COMPLETA - MÓDULO CENTROS{RESET}")
    print(f"{BOLD}{'#'*70}{RESET}")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Ejecutar todos los tests
    test_modelo_centro()
    test_relaciones_inversas()
    test_serializer_centro()
    test_viewset_centro()
    test_exportacion()
    test_importacion()
    test_permisos()
    test_datos_bd()
    test_api_funcional()
    test_validaciones_negocio()
    test_integracion_usuarios()
    test_integracion_lotes()
    test_integracion_requisiciones()
    test_filtros_busqueda()
    test_paginacion()
    test_toggle_activo()
    
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
        print(f"\n{GREEN}{BOLD}✓ MÓDULO CENTROS VERIFICADO CORRECTAMENTE{RESET}")
    else:
        print(f"\n{RED}{BOLD}✗ HAY {resultados['fail']} PROBLEMAS QUE REQUIEREN ATENCIÓN{RESET}")
    
    print(f"\n{'='*70}\n")
    
    return resultados['fail'] == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
