"""
Sistema completo de permisos basado en roles jerárquicos
Estructura: SUPER_ADMIN > FARMACIA_ADMIN > CENTRO_USER > VISTA_USER
"""
from rest_framework import permissions
import logging
from core.constants import EXTRA_PERMISSIONS

logger = logging.getLogger(__name__)


def _has_extra_perm(user, extras):
    """Valida si el usuario tiene algún permiso extra (vía grupos)."""
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    group_names = set(g.name.upper() for g in user.groups.all())
    for extra in extras:
        if extra.upper() in group_names:
            return True
    return False


def _has_role(user, roles):
    """Valida roles por campo rol o por grupos heredados."""
    if not user or not getattr(user, 'is_authenticated', False):
        return False

    if user.is_superuser:
        return True

    normalized = (getattr(user, 'rol', '') or '').lower()
    group_names = set(g.name.upper() for g in user.groups.all())

    role_aliases = {
        'admin': {'admin_sistema', 'superusuario'},
        'farmacia': {'farmacia', 'admin_farmacia', 'farmaceutico'},  # + FARMACEUTICO
        'centro': {'centro', 'usuario_normal', 'solicitante'},  # + SOLICITANTE
        'vista': {'vista', 'usuario_vista'},
    }

    for role in roles:
        key = role.lower()
        if normalized in role_aliases.get(key, {key}):
            return True
        # Revisar grupos con aliases expandidos
        if key == 'admin' and 'FARMACIA_ADMIN' in group_names:
            return True
        if key == 'farmacia' and ('FARMACIA_ADMIN' in group_names or 'FARMACEUTICO' in group_names):
            return True
        if key == 'centro' and ('CENTRO_USER' in group_names or 'SOLICITANTE' in group_names):
            return True
        if key == 'vista' and 'VISTA_USER' in group_names:
            return True

    return False


def _has_permission(user, roles, extra_perms=None):
    """Evalúa rol base o permisos extra permitidos."""
    extra_perms = extra_perms or []
    return _has_role(user, roles) or _has_extra_perm(user, extra_perms)


class IsSuperuserOnly(permissions.BasePermission):
    """Permiso SOLO para superusuarios / admin_sistema."""
    def has_permission(self, request, view):
        return _has_permission(request.user, ['admin'], EXTRA_PERMISSIONS)


class IsAdminRole(permissions.BasePermission):
    """Administrador del sistema."""
    def has_permission(self, request, view):
        return _has_permission(request.user, ['admin'], ['CAN_MANAGE_USERS', 'CAN_MANAGE_CENTROS'])


class IsFarmaciaRole(permissions.BasePermission):
    """Usuarios de farmacia."""
    def has_permission(self, request, view):
        return _has_permission(request.user, ['admin', 'farmacia'], ['CAN_VIEW_ALL_REQUISICIONES'])


class IsCentroRole(permissions.BasePermission):
    """Usuarios de centro/unidad."""
    def has_permission(self, request, view):
        return _has_permission(request.user, ['admin', 'farmacia', 'centro'], ['CAN_VIEW_ALL_REQUISICIONES'])


class IsVistaRole(permissions.BasePermission):
    """Usuarios de solo consulta."""
    def has_permission(self, request, view):
        return _has_permission(request.user, ['admin', 'farmacia', 'vista'], ['CAN_VIEW_GLOBAL_REPORTS'])


class IsFarmaciaAdminOrReadOnly(permissions.BasePermission):
    """
    Lectura: requiere usuario autenticado.
    Escritura: solo admin o farmacia.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return _has_role(request.user, ['admin', 'farmacia'])


class IsAuthenticatedReadOnly(permissions.BasePermission):
    """Solo permite operaciones de lectura a usuarios autenticados."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.method in permissions.SAFE_METHODS)


class IsReadOnly(permissions.BasePermission):
    """
    Permiso que solo permite métodos de lectura (GET, HEAD, OPTIONS).
    Usado para garantizar que el rol VISTA nunca pueda modificar datos.
    """
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS


class IsCentroUser(permissions.BasePermission):
    """Centro puede operar en su propio ámbito; admin/farmacia también."""
    def has_permission(self, request, view):
        return _has_role(request.user, ['admin', 'farmacia', 'centro'])

    def has_object_permission(self, request, view, obj):
        if _has_role(request.user, ['admin', 'farmacia']):
            return True
        
        user_centro = getattr(request.user, 'centro', None)
        if not user_centro:
            return False  # ISS-012: Usuario sin centro no puede acceder a objetos
        
        # ISS-012: Validar por centro del objeto
        if hasattr(obj, 'centro') and obj.centro:
            return obj.centro == user_centro
        
        # ISS-012: Validar por centro_destino (para requisiciones)
        if hasattr(obj, 'centro_destino') and obj.centro_destino:
            return obj.centro_destino == user_centro
        
        # ISS-012: Validar por centro_origen (para requisiciones)
        if hasattr(obj, 'centro_origen') and obj.centro_origen:
            return obj.centro_origen == user_centro
        
        # ISS-012: Validar por solicitante (para requisiciones)
        if hasattr(obj, 'solicitante') and obj.solicitante:
            solicita_centro = getattr(obj.solicitante, 'centro', None)
            return solicita_centro == user_centro
        
        return False  # ISS-012: Por defecto denegar si no hay forma de validar


class CanAuthorizeRequisicion(permissions.BasePermission):
    """Autorizar/rechazar/surtir requisiciones: admin o farmacia."""
    def has_permission(self, request, view):
        return _has_role(request.user, ['admin', 'farmacia'])


class IsVistaUserOrAdmin(permissions.BasePermission):
    """Lectura para vista, farmacia o admin."""
    def has_permission(self, request, view):
        if request.method not in permissions.SAFE_METHODS:
            return False
        return _has_role(request.user, ['admin', 'farmacia', 'vista'])


class CanViewNotifications(permissions.BasePermission):
    """Permiso para ver notificaciones."""
    def has_permission(self, request, view):
        return _has_permission(request.user, ['admin', 'farmacia', 'centro', 'vista'], ['VER_NOTIFICACIONES'])


class CanViewProfile(permissions.BasePermission):
    """Permiso para ver/editar perfil propio."""
    def has_permission(self, request, view):
        return _has_permission(request.user, ['admin', 'farmacia', 'centro', 'vista'], ['VER_PERFIL'])


class CanManageOwnProfile(permissions.BasePermission):
    """Gestión de perfil propio."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if _has_role(request.user, ['admin']):
            return True
        return obj == request.user
