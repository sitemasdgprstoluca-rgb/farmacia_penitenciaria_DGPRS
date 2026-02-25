"""
Capa unificada de parsing/validación de filtros para el módulo de Reportes.

Garantiza:
 - Normalización de strings (trim, "" → None)
 - Parseo de fechas (ISO yyyy-mm-dd y dd/mm/yyyy)
 - Validación de rango desde <= hasta
 - Normalización de centro ("todos" / "central" / ID numérico)
 - Normalización de booleanos
 - Defaults por reporte
 - Nunca 500 por parámetros faltantes o vacíos
"""
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, Any

from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


# ─────────────────────────────────── helpers primitivos ───────────────────────

def _norm_str(val: Any) -> Optional[str]:
    """Convierte cualquier valor a str limpio; '', 'null', 'undefined' → None."""
    if val is None:
        return None
    s = str(val).strip()
    if s.lower() in ('', 'null', 'undefined', 'none'):
        return None
    return s


def _norm_bool(val: Any) -> bool:
    """Normaliza a booleano: 'true', '1', True → True, todo lo demás → False."""
    if isinstance(val, bool):
        return val
    if val is None:
        return False
    return str(val).strip().lower() in ('true', '1', 'yes', 'si', 'sí')


def _parse_date(val: Any) -> Optional[date]:
    """
    Acepta ISO (yyyy-mm-dd) o dd/mm/yyyy.
    Retorna date o None si no puede parsear.
    """
    s = _norm_str(val)
    if not s:
        return None
    for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None  # fecha inválida — se reportará en validate_dates


def _parse_int(val: Any) -> Optional[int]:
    """Intenta convertir a int; None si no puede."""
    s = _norm_str(val)
    if not s:
        return None
    try:
        return int(s)
    except (ValueError, TypeError):
        return None


# ─────────────────────────────── centro resolution ────────────────────────────

CENTRO_TODOS = 'todos'
CENTRO_CENTRAL = 'central'


@dataclass
class CentroResuelto:
    """Resultado de resolver el parámetro 'centro'."""
    es_todos: bool = False       # Ver todos los centros (sin filtro)
    es_central: bool = False     # Solo Farmacia Central (centro IS NULL)
    centro_id: Optional[int] = None  # ID numérico de un centro específico
    es_especifico: bool = False  # True si se resolvió un centro por ID

    @property
    def debe_filtrar(self) -> bool:
        return self.es_central or self.es_especifico


def resolver_centro(raw: Any) -> CentroResuelto:
    """
    Normaliza el parámetro de centro a una estructura clara.
    
    'todos'   → es_todos=True
    'central' → es_central=True
    '123'     → centro_id=123, es_especifico=True
    None/''   → es_todos=True  (default permisivo)
    """
    s = _norm_str(raw)
    if s is None:
        return CentroResuelto(es_todos=True)
    
    low = s.lower()
    if low == CENTRO_TODOS:
        return CentroResuelto(es_todos=True)
    if low == CENTRO_CENTRAL:
        return CentroResuelto(es_central=True)
    
    parsed = _parse_int(s)
    if parsed is not None and parsed > 0:
        return CentroResuelto(centro_id=parsed, es_especifico=True)
    
    # Fallback: valor no reconocido → tratar como todos
    logger.warning(f"resolver_centro: valor no reconocido '{raw}', tratando como 'todos'")
    return CentroResuelto(es_todos=True)


# ─────────────────────────────── filtros parsed ───────────────────────────────

@dataclass
class FiltrosReporte:
    """Contiene todos los filtros parseados y validados para un reporte."""
    
    # Centro
    centro: CentroResuelto = field(default_factory=lambda: CentroResuelto(es_todos=True))
    
    # Fechas
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    
    # Inventario
    nivel_stock: Optional[str] = None  # alto, bajo, normal, sin_stock, critico
    
    # Caducidades
    dias: int = 30
    estado_caducidad: Optional[str] = None  # vencido, critico, proximo
    
    # Requisiciones / Movimientos
    estado: Optional[str] = None
    tipo_movimiento: Optional[str] = None  # entrada, salida
    estado_confirmacion: str = 'confirmado'  # confirmado, pendiente, todos
    
    # Contratos
    numero_contrato: Optional[str] = None
    incluir_movimientos: bool = True
    
    # Parcialidades
    es_sobreentrega: bool = False
    numero_lote: Optional[str] = None
    clave_producto: Optional[str] = None
    
    # Control Mensual
    mes: int = 0
    anio: int = 0
    
    # Formato
    formato: str = 'json'  # json, excel, pdf
    
    # Errores de validación (si hay alguno, la vista debe devolver 400)
    _errores: list = field(default_factory=list)
    
    @property
    def tiene_errores(self) -> bool:
        return len(self._errores) > 0
    
    @property
    def errores(self) -> list:
        return self._errores
    
    def respuesta_error(self) -> Response:
        """Genera una Response 400 con todos los errores acumulados."""
        return Response(
            {'error': '; '.join(self._errores), 'errores': self._errores},
            status=status.HTTP_400_BAD_REQUEST
        )


def parse_report_filters(request, tipo_reporte: str = '') -> FiltrosReporte:
    """
    Punto de entrada único para parsear query params de un request de reporte.
    
    Normaliza, valida, y aplica defaults según el tipo de reporte.
    Si hay errores de validación, quedan en filtros._errores y la vista 
    puede devolver filtros.respuesta_error().
    """
    params = request.query_params
    f = FiltrosReporte()
    
    # ── Centro ──────────────────────────────────────────────────
    f.centro = resolver_centro(params.get('centro'))
    
    # ── Formato ─────────────────────────────────────────────────
    fmt = _norm_str(params.get('formato'))
    if fmt and fmt.lower() in ('json', 'excel', 'pdf'):
        f.formato = fmt.lower()
    
    # ── Fechas ──────────────────────────────────────────────────
    raw_inicio = _norm_str(params.get('fecha_inicio'))
    raw_fin = _norm_str(params.get('fecha_fin'))
    
    if raw_inicio:
        f.fecha_inicio = _parse_date(raw_inicio)
        if f.fecha_inicio is None:
            f._errores.append(f'fecha_inicio inválida: "{raw_inicio}". Use formato YYYY-MM-DD o DD/MM/YYYY')
    
    if raw_fin:
        f.fecha_fin = _parse_date(raw_fin)
        if f.fecha_fin is None:
            f._errores.append(f'fecha_fin inválida: "{raw_fin}". Use formato YYYY-MM-DD o DD/MM/YYYY')
    
    # Validar rango: inicio <= fin
    if f.fecha_inicio and f.fecha_fin and f.fecha_inicio > f.fecha_fin:
        f._errores.append(
            f'Rango de fechas inválido: fecha_inicio ({f.fecha_inicio}) es posterior a fecha_fin ({f.fecha_fin})'
        )
    
    # ── Nivel de stock (inventario) ─────────────────────────────
    ns = _norm_str(params.get('nivel_stock'))
    if ns:
        ns_lower = ns.lower()
        if ns_lower in ('alto', 'bajo', 'normal', 'sin_stock', 'critico'):
            f.nivel_stock = ns_lower
        else:
            f._errores.append(f'nivel_stock inválido: "{ns}". Valores permitidos: alto, bajo, normal, sin_stock, critico')
    
    # ── Días próximos (caducidades) ─────────────────────────────
    dias_raw = params.get('dias')
    if dias_raw is not None:
        dias_parsed = _parse_int(dias_raw)
        if dias_parsed is not None and dias_parsed > 0:
            f.dias = min(dias_parsed, 3650)  # Cap a 10 años
        elif _norm_str(dias_raw) is not None:
            f._errores.append(f'dias debe ser un número positivo, recibido: "{dias_raw}"')
    
    # ── Estado (caducidad, requisiciones) ───────────────────────
    f.estado_caducidad = _norm_str(params.get('estado'))
    f.estado = _norm_str(params.get('estado'))
    
    # ── Tipo movimiento ─────────────────────────────────────────
    tm = _norm_str(params.get('tipo'))
    if tm:
        tm_lower = tm.lower()
        if tm_lower in ('entrada', 'salida'):
            f.tipo_movimiento = tm_lower
        else:
            f._errores.append(f'tipo de movimiento inválido: "{tm}". Valores permitidos: entrada, salida')
    
    # ── Estado confirmación (movimientos) ───────────────────────
    ec = _norm_str(params.get('estado_confirmacion'))
    if ec:
        ec_lower = ec.lower()
        if ec_lower in ('confirmado', 'pendiente', 'todos'):
            f.estado_confirmacion = ec_lower
    
    # ── Contrato ────────────────────────────────────────────────
    f.numero_contrato = _norm_str(params.get('numero_contrato'))
    f.incluir_movimientos = not _norm_bool(params.get('excluir_movimientos'))
    
    # ── Parcialidades ───────────────────────────────────────────
    f.es_sobreentrega = _norm_bool(params.get('es_sobreentrega'))
    f.numero_lote = _norm_str(params.get('numero_lote'))
    f.clave_producto = _norm_str(params.get('clave_producto'))
    
    # ── Control Mensual ─────────────────────────────────────────
    from django.utils import timezone
    now = timezone.now()
    
    mes_raw = _parse_int(params.get('mes'))
    if mes_raw is not None:
        if 1 <= mes_raw <= 12:
            f.mes = mes_raw
        else:
            f._errores.append(f'mes debe estar entre 1 y 12, recibido: {mes_raw}')
    else:
        f.mes = now.month
    
    anio_raw = _parse_int(params.get('anio'))
    if anio_raw is not None:
        if 2020 <= anio_raw <= now.year + 1:
            f.anio = anio_raw
        else:
            f._errores.append(f'anio debe estar entre 2020 y {now.year + 1}, recibido: {anio_raw}')
    else:
        f.anio = now.year
    
    # ── Logging ─────────────────────────────────────────────────
    if f.tiene_errores:
        logger.warning(f"parse_report_filters({tipo_reporte}): errores de validación: {f.errores}")
    else:
        logger.debug(
            f"parse_report_filters({tipo_reporte}): centro={f.centro}, "
            f"fechas={f.fecha_inicio}..{f.fecha_fin}, formato={f.formato}"
        )
    
    return f


# ─────────────────────── Permission / centro helper ───────────────────────────

def verificar_permisos_reporte(request, requiere_admin=False):
    """
    Verifica permisos comunes para reportes.
    
    Returns:
        (user, es_admin, user_centro, error_response)
        Si error_response no es None, la vista debe retornarlo inmediatamente.
    """
    from inventario.views_legacy import is_farmacia_or_admin, get_user_centro
    
    user = request.user
    if not user or not user.is_authenticated:
        return None, False, None, Response(
            {'error': 'Autenticación requerida'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    es_admin = is_farmacia_or_admin(user)
    
    if requiere_admin and not es_admin:
        return user, es_admin, None, Response(
            {'error': 'Solo usuarios de farmacia o administradores pueden acceder a este reporte'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    user_centro = get_user_centro(user) if not es_admin else None
    
    # Usuario no-admin sin centro → no puede ver reportes globales
    if not es_admin and not user_centro:
        # Verificar perm_reportes
        perm_reportes = getattr(user, 'perm_reportes', None)
        if perm_reportes is None:
            from core.models import User as UserModel
            rol = (getattr(user, 'rol', '') or '').lower()
            permisos_rol = UserModel.PERMISOS_POR_ROL.get(rol, {})
            perm_reportes = permisos_rol.get('perm_reportes', False)
        
        if not perm_reportes:
            return user, es_admin, None, Response(
                {'error': 'Usuario sin centro asignado y sin permiso de reportes'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    return user, es_admin, user_centro, None


def resolver_centro_para_queryset(filtros: FiltrosReporte, es_admin: bool, user_centro):
    """
    Combina el centro parseado con los permisos del usuario.
    
    Returns:
        CentroResuelto final (puede sobreescribir el del request si el usuario
        no es admin y tiene centro forzado).
    """
    if not es_admin and user_centro:
        # Forzar al centro del usuario
        return CentroResuelto(
            centro_id=user_centro.id if hasattr(user_centro, 'id') else user_centro,
            es_especifico=True
        )
    return filtros.centro
