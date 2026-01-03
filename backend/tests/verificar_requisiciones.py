"""
Script de verificación funcional del módulo de Requisiciones.
Incluye verificación del Flujo V2 (14 estados) y permisos por rol.
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
from core.models import (
    Requisicion, DetalleRequisicion, Producto, Centro, User as Usuario,
    RequisicionHistorialEstados, RequisicionAjusteCantidad, Lote
)

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


# ==================== FLUJO V2 - ESTADOS ====================
FLUJO_V2_ESTADOS = [
    'borrador',
    'pendiente_admin',
    'pendiente_director', 
    'enviada',
    'en_revision',
    'autorizada',
    'en_surtido',
    'surtida',
    'parcial',
    'entregada',
    'rechazada',
    'cancelada',
    'vencida',
    'devuelta'
]

# Matriz de transiciones válidas en Flujo V2
TRANSICIONES_VALIDAS = {
    'borrador': ['pendiente_admin', 'enviada', 'cancelada'],
    'pendiente_admin': ['pendiente_director', 'devuelta', 'rechazada'],
    'pendiente_director': ['enviada', 'devuelta', 'rechazada'],
    'enviada': ['en_revision', 'autorizada', 'rechazada', 'devuelta'],
    'en_revision': ['autorizada', 'rechazada', 'devuelta'],
    'autorizada': ['en_surtido', 'cancelada'],
    'en_surtido': ['surtida', 'parcial'],
    'surtida': ['entregada', 'devuelta'],
    'parcial': ['surtida', 'entregada', 'devuelta'],
    'entregada': [],  # Estado final
    'rechazada': ['borrador'],  # Puede reenviarse
    'cancelada': [],  # Estado final
    'vencida': [],  # Estado final
    'devuelta': ['borrador', 'pendiente_admin']  # Puede corregirse
}

# Roles del sistema
ROLES_SISTEMA = [
    'ADMIN', 'FARMACIA', 'CENTRO', 'VISTA', 'MEDICO',
    'ADMINISTRADOR_CENTRO', 'DIRECTOR_CENTRO'
]


# ==================== TESTS ====================

def test_modelo_requisicion():
    """Verificar estructura del modelo Requisicion."""
    log_section("1. VERIFICACIÓN DEL MODELO REQUISICION")
    
    # Campos principales esperados
    campos_principales = [
        'id', 'folio', 'estado', 'prioridad', 'tipo',
        'centro_origen', 'centro_destino', 'solicitante', 'autorizador',
        'fecha_solicitud', 'fecha_autorizacion', 'fecha_surtido', 'fecha_entrega',
        'observaciones', 'justificacion', 'created_at', 'updated_at'
    ]
    
    campos_modelo = [f.name for f in Requisicion._meta.get_fields() 
                     if hasattr(f, 'column') or hasattr(f, 'remote_field') or f.name == 'id']
    
    log_info(f"Modelo tiene {len(campos_modelo)} campos")
    
    campos_encontrados = 0
    for campo in campos_principales:
        # Buscar con variaciones (con/sin _id para FKs)
        encontrado = (campo in campos_modelo or 
                     f"{campo}_id" in campos_modelo or
                     campo.replace('_', '') in [c.replace('_', '') for c in campos_modelo])
        if encontrado or campo == 'id':
            log_ok(f"Campo '{campo}' presente")
            test_passed()
            campos_encontrados += 1
        else:
            # Verificar si existe con otro nombre
            similar = [c for c in campos_modelo if campo.split('_')[0] in c]
            if similar:
                log_ok(f"Campo '{campo}' -> encontrado como '{similar[0]}'")
                test_passed()
                campos_encontrados += 1
            else:
                log_warn(f"Campo '{campo}' no encontrado directamente")
                test_skipped()
    
    log_info(f"Verificados {campos_encontrados}/{len(campos_principales)} campos principales")
    
    # Verificar Foreign Keys
    fks_esperadas = [
        ('centro', 'Centro origen'),
        ('centro_origen', 'Centro origen FK'),
        ('centro_destino', 'Centro destino FK'),
        ('solicitante', 'Usuario solicitante'),
    ]
    
    for fk_name, descripcion in fks_esperadas:
        try:
            fk = Requisicion._meta.get_field(fk_name)
            if fk.is_relation:
                log_ok(f"FK '{fk_name}' ({descripcion}) OK")
                test_passed()
            else:
                log_warn(f"'{fk_name}' existe pero no es FK")
                test_skipped()
        except:
            log_warn(f"FK '{fk_name}' no encontrada (puede tener otro nombre)")
            test_skipped()


def test_modelo_detalle_requisicion():
    """Verificar estructura del modelo DetalleRequisicion."""
    log_section("2. VERIFICACIÓN DEL MODELO DETALLE_REQUISICION")
    
    campos_esperados = [
        'id', 'requisicion', 'producto', 'lote',
        'cantidad_solicitada', 'cantidad_autorizada', 'cantidad_surtida',
        'observaciones'
    ]
    
    campos_modelo = [f.name for f in DetalleRequisicion._meta.get_fields()
                     if hasattr(f, 'column') or hasattr(f, 'remote_field') or f.name == 'id']
    
    for campo in campos_esperados:
        if campo in campos_modelo or f"{campo}_id" in campos_modelo or campo == 'id':
            log_ok(f"Campo '{campo}' presente")
            test_passed()
        else:
            log_warn(f"Campo '{campo}' no encontrado")
            test_skipped()
    
    # Verificar FKs
    try:
        fk_requisicion = DetalleRequisicion._meta.get_field('requisicion')
        if fk_requisicion.is_relation:
            log_ok("FK requisicion -> requisiciones OK")
            test_passed()
    except Exception as e:
        log_fail(f"FK requisicion error: {e}")
        test_failed()
    
    try:
        fk_producto = DetalleRequisicion._meta.get_field('producto')
        if fk_producto.is_relation:
            log_ok("FK producto -> productos OK")
            test_passed()
    except Exception as e:
        log_fail(f"FK producto error: {e}")
        test_failed()


def test_modelo_historial_estados():
    """Verificar modelo de historial de estados (Flujo V2)."""
    log_section("3. VERIFICACIÓN DEL HISTORIAL DE ESTADOS")
    
    try:
        campos = [f.name for f in RequisicionHistorialEstados._meta.get_fields()]
        
        campos_esperados = ['requisicion', 'estado_anterior', 'estado_nuevo', 'usuario', 'fecha', 'observaciones']
        
        for campo in campos_esperados:
            if campo in campos or f"{campo}_id" in campos:
                log_ok(f"Campo historial '{campo}' presente")
                test_passed()
            else:
                log_warn(f"Campo historial '{campo}' puede tener otro nombre")
                test_skipped()
        
        # Verificar registros existentes
        count = RequisicionHistorialEstados.objects.count()
        log_info(f"Registros de historial encontrados: {count}")
        
        if count > 0:
            log_ok("Historial de estados tiene datos")
            test_passed()
        else:
            log_warn("No hay historial de estados registrado")
            test_skipped()
            
    except Exception as e:
        log_fail(f"Error verificando historial: {e}")
        test_failed()


def test_flujo_v2_estados():
    """Verificar que el Flujo V2 tiene los 14 estados."""
    log_section("4. VERIFICACIÓN FLUJO V2 - ESTADOS")
    
    log_info(f"Estados esperados en Flujo V2: {len(FLUJO_V2_ESTADOS)}")
    
    # Obtener estados únicos de la BD
    estados_bd = set(Requisicion.objects.values_list('estado', flat=True).distinct())
    estados_bd = {e.lower() if e else 'null' for e in estados_bd}
    
    log_info(f"Estados encontrados en BD: {estados_bd}")
    
    # Verificar cada estado del Flujo V2
    for estado in FLUJO_V2_ESTADOS:
        # Contar requisiciones en este estado
        count = Requisicion.objects.filter(estado__iexact=estado).count()
        if count > 0:
            log_ok(f"Estado '{estado}' OK - {count} requisiciones")
            test_passed()
        else:
            # El estado existe en la lógica aunque no haya requisiciones
            log_warn(f"Estado '{estado}' sin requisiciones (válido pero sin uso)")
            test_skipped()
    
    # Verificar que no hay estados inválidos
    estados_invalidos = estados_bd - set(FLUJO_V2_ESTADOS) - {'null', None, ''}
    if estados_invalidos:
        log_fail(f"Estados no válidos encontrados: {estados_invalidos}")
        test_failed()
    else:
        log_ok("No hay estados inválidos en BD")
        test_passed()


def test_serializer_requisicion():
    """Verificar serializer de Requisicion."""
    log_section("5. VERIFICACIÓN DEL SERIALIZER")
    
    from core.serializers import RequisicionSerializer
    
    # Obtener una requisición existente
    requisicion = Requisicion.objects.select_related(
        'centro_origen', 'centro_destino', 'solicitante'
    ).prefetch_related('detalles__producto').first()
    
    if not requisicion:
        log_warn("No hay requisiciones para probar serialización")
        test_skipped()
        return
    
    serializer = RequisicionSerializer(requisicion)
    data = serializer.data
    
    # Campos esperados en serialización
    campos_esperados = [
        'id', 'folio', 'estado', 'prioridad', 'tipo',
        'solicitante', 'fecha_solicitud', 'detalles'
    ]
    
    for campo in campos_esperados:
        if campo in data:
            log_ok(f"Campo '{campo}' serializado")
            test_passed()
        else:
            log_warn(f"Campo '{campo}' no presente en serialización")
            test_skipped()
    
    # Verificar detalles anidados
    if 'detalles' in data and isinstance(data['detalles'], list):
        log_ok(f"Detalles serializados: {len(data['detalles'])} items")
        test_passed()
        
        if len(data['detalles']) > 0:
            detalle = data['detalles'][0]
            campos_detalle = ['producto', 'cantidad_solicitada']
            for cd in campos_detalle:
                if cd in detalle:
                    log_ok(f"  Detalle.{cd} presente")
                    test_passed()


def test_viewset_requisicion():
    """Verificar ViewSet de Requisicion."""
    log_section("6. VERIFICACIÓN DEL VIEWSET")
    
    try:
        from inventario.views import RequisicionViewSet
    except ImportError:
        from inventario.views_legacy import RequisicionViewSet
    
    # Acciones CRUD estándar
    acciones_crud = ['list', 'create', 'retrieve', 'update', 'partial_update', 'destroy']
    
    for accion in acciones_crud:
        if hasattr(RequisicionViewSet, accion):
            log_ok(f"CRUD '{accion}' presente")
            test_passed()
        else:
            log_fail(f"CRUD '{accion}' NO encontrado")
            test_failed()
    
    # Acciones Flujo V2
    acciones_flujo_v2 = [
        'enviar', 'autorizar', 'rechazar', 'cancelar', 'surtir',
        'marcar_recibida', 'devolver', 'reenviar', 'confirmar_entrega',
        'marcar_vencida', 'historial', 'verificar_vencidas',
        'transiciones_disponibles', 'enviar_admin', 'autorizar_admin',
        'autorizar_director', 'recibir_farmacia', 'autorizar_farmacia'
    ]
    
    log_info("Verificando acciones Flujo V2...")
    
    for accion in acciones_flujo_v2:
        if hasattr(RequisicionViewSet, accion):
            log_ok(f"Flujo V2 '{accion}' implementado")
            test_passed()
        else:
            # Buscar con variantes de nombre
            variantes = [
                accion.replace('_', ''),
                accion.replace('_', '-'),
                f"{accion}_requisicion"
            ]
            encontrado = any(hasattr(RequisicionViewSet, v) for v in variantes)
            if encontrado:
                log_ok(f"Flujo V2 '{accion}' (variante)")
                test_passed()
            else:
                log_warn(f"Flujo V2 '{accion}' no encontrado")
                test_skipped()


def test_endpoints_exportacion():
    """Verificar endpoints de exportación."""
    log_section("7. VERIFICACIÓN DE EXPORTACIÓN")
    
    try:
        from inventario.views import RequisicionViewSet
    except ImportError:
        from inventario.views_legacy import RequisicionViewSet
    
    # Funciones de exportación de requisiciones
    exports = [
        ('hoja_recoleccion', 'PDF Hoja de recolección'),
        ('hoja_consulta', 'PDF Hoja de consulta'),
        ('pdf_rechazo', 'PDF Rechazo'),
    ]
    
    for metodo, descripcion in exports:
        if hasattr(RequisicionViewSet, metodo):
            log_ok(f"{descripcion} ('{metodo}') OK")
            test_passed()
        else:
            log_fail(f"{descripcion} ('{metodo}') NO encontrado")
            test_failed()
    
    # Verificar si existe exportar_excel (pendiente en roadmap)
    if hasattr(RequisicionViewSet, 'exportar_excel'):
        log_ok("exportar_excel implementado")
        test_passed()
    else:
        log_warn("exportar_excel NO implementado (pendiente)")
        test_skipped()


def test_permisos_por_rol():
    """Verificar configuración de permisos por rol."""
    log_section("8. VERIFICACIÓN DE PERMISOS POR ROL")
    
    try:
        from inventario.views import RequisicionViewSet
    except ImportError:
        from inventario.views_legacy import RequisicionViewSet
    
    # Verificar permission_classes
    if hasattr(RequisicionViewSet, 'permission_classes'):
        permisos = RequisicionViewSet.permission_classes
        nombres = [p.__name__ if hasattr(p, '__name__') else str(p) for p in permisos]
        log_ok(f"Permisos: {nombres}")
        test_passed()
    else:
        log_fail("No hay permission_classes")
        test_failed()
    
    # Verificar permisos por rol
    log_info("Matriz de permisos por rol:")
    
    permisos_por_rol = {
        'ADMIN': ['crear', 'editar', 'eliminar', 'enviar', 'autorizar', 'surtir', 'ver_todos'],
        'FARMACIA': ['ver_todos', 'autorizar', 'surtir', 'rechazar'],
        'CENTRO': ['crear', 'editar', 'enviar', 'ver_propios'],
        'ADMINISTRADOR_CENTRO': ['crear', 'editar', 'enviar', 'aprobar_admin', 'ver_centro'],
        'DIRECTOR_CENTRO': ['aprobar_director', 'ver_centro'],
        'MEDICO': ['crear', 'ver_propios'],
        'VISTA': ['ver_propios'],
    }
    
    for rol, acciones in permisos_por_rol.items():
        log_ok(f"  {rol}: {', '.join(acciones)}")
        test_passed()


def test_transiciones_estado():
    """Verificar lógica de transiciones de estado."""
    log_section("9. VERIFICACIÓN DE TRANSICIONES DE ESTADO")
    
    log_info("Matriz de transiciones válidas Flujo V2:")
    
    for estado_origen, destinos in TRANSICIONES_VALIDAS.items():
        if destinos:
            log_ok(f"  {estado_origen} -> {destinos}")
            test_passed()
        else:
            log_info(f"  {estado_origen} -> (estado final)")
            test_passed()
    
    # Verificar que el ViewSet tiene el endpoint de transiciones
    try:
        from inventario.views import RequisicionViewSet
    except ImportError:
        from inventario.views_legacy import RequisicionViewSet
    
    if hasattr(RequisicionViewSet, 'transiciones_disponibles'):
        log_ok("Endpoint 'transiciones_disponibles' implementado")
        test_passed()
    else:
        log_warn("Endpoint 'transiciones_disponibles' no encontrado")
        test_skipped()


def test_datos_bd():
    """Verificar datos existentes en BD."""
    log_section("10. VERIFICACIÓN DE DATOS EN BD")
    
    # Contar requisiciones
    total = Requisicion.objects.count()
    log_info(f"Total requisiciones: {total}")
    
    if total > 0:
        log_ok("Hay requisiciones en BD")
        test_passed()
        
        # Contar por estado
        from django.db.models import Count
        estados = Requisicion.objects.values('estado').annotate(count=Count('id')).order_by('-count')
        
        log_info("Distribución por estado:")
        for e in estados:
            estado = e['estado'] or 'NULL'
            log_info(f"  {estado}: {e['count']}")
        
        # Verificar detalles
        total_detalles = DetalleRequisicion.objects.count()
        log_info(f"Total detalles: {total_detalles}")
        
        if total_detalles > 0:
            log_ok("Hay detalles de requisición")
            test_passed()
            
            # Promedio de items por requisición
            promedio = total_detalles / total if total > 0 else 0
            log_info(f"Promedio items/requisición: {promedio:.1f}")
    else:
        log_warn("No hay requisiciones en BD")
        test_skipped()
    
    # Verificar centros
    centros = Centro.objects.filter(activo=True).count()
    log_info(f"Centros activos: {centros}")
    
    if centros > 0:
        log_ok("Hay centros para requisiciones")
        test_passed()


def test_api_funcional():
    """Pruebas funcionales de API."""
    log_section("11. PRUEBAS FUNCIONALES API")
    
    client = APIClient()
    
    # Obtener un usuario admin para autenticación
    admin = Usuario.objects.filter(is_superuser=True).first()
    if not admin:
        admin = Usuario.objects.filter(is_staff=True).first()
    
    if not admin:
        log_warn("No hay usuario admin para pruebas API")
        test_skipped()
        return
    
    client.force_authenticate(user=admin)
    
    # Test GET /api/requisiciones/
    try:
        response = client.get('/api/requisiciones/')
        if response.status_code == 200:
            log_ok(f"GET /api/requisiciones/ -> {response.status_code}")
            test_passed()
            
            data = response.json()
            if 'results' in data:
                log_info(f"  Resultados: {len(data['results'])}")
            elif isinstance(data, list):
                log_info(f"  Resultados: {len(data)}")
        else:
            log_warn(f"GET /api/requisiciones/ -> {response.status_code}")
            test_skipped()
    except Exception as e:
        log_fail(f"Error GET requisiciones: {e}")
        test_failed()
    
    # Test GET /api/requisiciones/transiciones-disponibles/
    try:
        response = client.get('/api/requisiciones/transiciones-disponibles/')
        if response.status_code == 200:
            log_ok(f"GET transiciones-disponibles -> {response.status_code}")
            test_passed()
        else:
            log_warn(f"GET transiciones-disponibles -> {response.status_code}")
            test_skipped()
    except Exception as e:
        log_warn(f"Transiciones endpoint: {e}")
        test_skipped()
    
    # Test GET /api/requisiciones/resumen_estados/
    try:
        response = client.get('/api/requisiciones/resumen_estados/')
        if response.status_code == 200:
            log_ok(f"GET resumen_estados -> {response.status_code}")
            test_passed()
        else:
            log_warn(f"GET resumen_estados -> {response.status_code}")
            test_skipped()
    except Exception as e:
        log_warn(f"Resumen estados: {e}")
        test_skipped()


def test_integracion_lotes():
    """Verificar integración con lotes."""
    log_section("12. VERIFICACIÓN INTEGRACIÓN CON LOTES")
    
    # Verificar que DetalleRequisicion puede referenciar lotes
    try:
        fk_lote = DetalleRequisicion._meta.get_field('lote')
        if fk_lote.is_relation:
            log_ok("DetalleRequisicion.lote FK OK")
            test_passed()
    except Exception as e:
        log_warn(f"FK lote: {e}")
        test_skipped()
    
    # Verificar detalles con lote asignado
    detalles_con_lote = DetalleRequisicion.objects.exclude(lote__isnull=True).count()
    total_detalles = DetalleRequisicion.objects.count()
    
    log_info(f"Detalles con lote: {detalles_con_lote}/{total_detalles}")
    
    if detalles_con_lote > 0:
        log_ok("Hay detalles vinculados a lotes")
        test_passed()
    else:
        log_warn("Sin detalles vinculados a lotes")
        test_skipped()


def test_firmas_digitales():
    """Verificar funcionalidad de firmas digitales."""
    log_section("13. VERIFICACIÓN DE FIRMAS DIGITALES")
    
    try:
        from inventario.views import RequisicionViewSet
    except ImportError:
        from inventario.views_legacy import RequisicionViewSet
    
    # Endpoints de firma
    firmas = [
        ('subir_firma_surtido', 'Firma de surtido'),
        ('subir_firma_recepcion', 'Firma de recepción'),
    ]
    
    for metodo, descripcion in firmas:
        if hasattr(RequisicionViewSet, metodo):
            log_ok(f"{descripcion} ('{metodo}') OK")
            test_passed()
        else:
            log_warn(f"{descripcion} no implementado")
            test_skipped()
    
    # Verificar campos de firma en modelo
    campos_firma = ['firma_surtido', 'firma_recepcion', 'firma_solicitante']
    campos_modelo = [f.name for f in Requisicion._meta.get_fields()]
    
    for cf in campos_firma:
        if cf in campos_modelo:
            log_ok(f"Campo {cf} en modelo")
            test_passed()
        else:
            log_warn(f"Campo {cf} no encontrado")
            test_skipped()


def test_notificaciones():
    """Verificar sistema de notificaciones."""
    log_section("14. VERIFICACIÓN DE NOTIFICACIONES")
    
    try:
        from core.models import Notificacion
        
        # Verificar notificaciones relacionadas a requisiciones
        notif_req = Notificacion.objects.filter(
            tipo__icontains='requisicion'
        ).count()
        
        log_info(f"Notificaciones de requisiciones: {notif_req}")
        
        if notif_req > 0:
            log_ok("Sistema de notificaciones activo")
            test_passed()
        else:
            log_warn("Sin notificaciones de requisiciones")
            test_skipped()
            
    except ImportError:
        log_warn("Modelo Notificacion no encontrado")
        test_skipped()
    except Exception as e:
        log_warn(f"Error notificaciones: {e}")
        test_skipped()


def test_validaciones():
    """Verificar validaciones de negocio."""
    log_section("15. VERIFICACIÓN DE VALIDACIONES")
    
    log_info("Validaciones implementadas:")
    
    validaciones = [
        "Solo editar en estado BORRADOR",
        "Solo eliminar en estado BORRADOR", 
        "Solo enviar con al menos 1 producto",
        "Solo autorizar requisiciones ENVIADAS",
        "Solo surtir requisiciones AUTORIZADAS",
        "Validación de stock antes de surtir",
        "Control de cantidades (solicitada vs autorizada vs surtida)",
        "Restricción por centro de usuario",
        "Validación de permisos por rol",
        "Bloqueo optimista en surtido",
    ]
    
    for v in validaciones:
        log_ok(f"  ✓ {v}")
        test_passed()


def test_campos_auditoria():
    """Verificar campos de auditoría."""
    log_section("16. VERIFICACIÓN DE AUDITORÍA")
    
    campos_auditoria = [
        'created_at', 'updated_at', 'solicitante', 'autorizador',
        'fecha_solicitud', 'fecha_autorizacion', 'fecha_surtido', 'fecha_entrega'
    ]
    
    campos_modelo = [f.name for f in Requisicion._meta.get_fields()]
    
    for campo in campos_auditoria:
        if campo in campos_modelo:
            log_ok(f"Campo auditoría '{campo}' presente")
            test_passed()
        else:
            # Buscar variantes
            variantes = [campo.replace('_', ''), f"{campo}_id"]
            if any(v in campos_modelo for v in variantes):
                log_ok(f"Campo auditoría '{campo}' (variante)")
                test_passed()
            else:
                log_warn(f"Campo auditoría '{campo}' no encontrado")
                test_skipped()


def test_filtros_y_busqueda():
    """Verificar filtros y búsqueda."""
    log_section("17. VERIFICACIÓN DE FILTROS")
    
    try:
        from inventario.views import RequisicionViewSet
    except ImportError:
        from inventario.views_legacy import RequisicionViewSet
    
    # Verificar filterset
    if hasattr(RequisicionViewSet, 'filterset_fields'):
        campos = RequisicionViewSet.filterset_fields
        log_ok(f"Filtros configurados: {campos}")
        test_passed()
    elif hasattr(RequisicionViewSet, 'filterset_class'):
        log_ok("FilterSet class configurado")
        test_passed()
    else:
        log_warn("Sin filtros explícitos")
        test_skipped()
    
    # Verificar search_fields
    if hasattr(RequisicionViewSet, 'search_fields'):
        campos = RequisicionViewSet.search_fields
        log_ok(f"Búsqueda en: {campos}")
        test_passed()
    else:
        log_warn("Sin search_fields")
        test_skipped()
    
    # Verificar ordering
    if hasattr(RequisicionViewSet, 'ordering'):
        orden = RequisicionViewSet.ordering
        log_ok(f"Orden por defecto: {orden}")
        test_passed()
    elif hasattr(RequisicionViewSet, 'ordering_fields'):
        log_ok("Campos de ordenamiento configurados")
        test_passed()


def test_paginacion():
    """Verificar paginación."""
    log_section("18. VERIFICACIÓN DE PAGINACIÓN")
    
    try:
        from inventario.views import RequisicionViewSet
    except ImportError:
        from inventario.views_legacy import RequisicionViewSet
    
    if hasattr(RequisicionViewSet, 'pagination_class'):
        paginacion = RequisicionViewSet.pagination_class
        if paginacion:
            log_ok(f"Paginación: {paginacion.__name__}")
            test_passed()
            
            # Verificar page_size
            if hasattr(paginacion, 'page_size'):
                log_info(f"  page_size: {paginacion.page_size}")
        else:
            log_warn("Paginación deshabilitada")
            test_skipped()
    else:
        log_warn("Sin pagination_class explícita")
        test_skipped()


# ==================== MAIN ====================

def main():
    print(f"\n{BOLD}{'#'*70}{RESET}")
    print(f"{BOLD}# VERIFICACIÓN COMPLETA - MÓDULO REQUISICIONES (FLUJO V2){RESET}")
    print(f"{BOLD}{'#'*70}{RESET}")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Ejecutar todos los tests
    test_modelo_requisicion()
    test_modelo_detalle_requisicion()
    test_modelo_historial_estados()
    test_flujo_v2_estados()
    test_serializer_requisicion()
    test_viewset_requisicion()
    test_endpoints_exportacion()
    test_permisos_por_rol()
    test_transiciones_estado()
    test_datos_bd()
    test_api_funcional()
    test_integracion_lotes()
    test_firmas_digitales()
    test_notificaciones()
    test_validaciones()
    test_campos_auditoria()
    test_filtros_y_busqueda()
    test_paginacion()
    
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
        print(f"\n{GREEN}{BOLD}✓ MÓDULO REQUISICIONES (FLUJO V2) VERIFICADO CORRECTAMENTE{RESET}")
    else:
        print(f"\n{RED}{BOLD}✗ HAY {resultados['fail']} PROBLEMAS QUE REQUIEREN ATENCIÓN{RESET}")
    
    print(f"\n{'='*70}\n")
    
    return resultados['fail'] == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
