"""
Sistema completo de permisos basado en roles jerárquicos
Estructura: SUPER_ADMIN > FARMACIA_ADMIN > CENTRO_USER > VISTA_USER
"""
from rest_framework import permissions
import logging

logger = logging.getLogger(__name__)


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
        'farmacia': {'farmacia', 'admin_farmacia'},
        'centro': {'centro', 'usuario_normal'},
        'vista': {'vista', 'usuario_vista'},
    }

    for role in roles:
        key = role.lower()
        if normalized in role_aliases.get(key, {key}):
            return True
        if key == 'admin' and 'FARMACIA_ADMIN' in group_names:
            return True
        if key == 'farmacia' and 'FARMACIA_ADMIN' in group_names:
            return True
        if key == 'centro' and 'CENTRO_USER' in group_names:
            return True
        if key == 'vista' and 'VISTA_USER' in group_names:
            return True
    return False


class IsSuperuserOnly(permissions.BasePermission):
    """Permiso SOLO para superusuarios / admin_sistema."""
    def has_permission(self, request, view):
        return _has_role(request.user, ['admin'])


class IsAdminRole(permissions.BasePermission):
    """Administrador del sistema."""
    def has_permission(self, request, view):
        return _has_role(request.user, ['admin'])


class IsFarmaciaRole(permissions.BasePermission):
    """Usuarios de farmacia."""
    def has_permission(self, request, view):
        return _has_role(request.user, ['admin', 'farmacia'])


class IsCentroRole(permissions.BasePermission):
    """Usuarios de centro/unidad."""
    def has_permission(self, request, view):
        return _has_role(request.user, ['admin', 'farmacia', 'centro'])


class IsVistaRole(permissions.BasePermission):
    """Usuarios de solo consulta."""
    def has_permission(self, request, view):
        return _has_role(request.user, ['admin', 'farmacia', 'vista'])


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


class IsCentroUser(permissions.BasePermission):
    """Centro puede operar en su propio ámbito; admin/farmacia también."""
    def has_permission(self, request, view):
        return _has_role(request.user, ['admin', 'farmacia', 'centro'])

    def has_object_permission(self, request, view, obj):
        if _has_role(request.user, ['admin', 'farmacia']):
            return True
        if hasattr(obj, 'centro'):
            user_centro = getattr(request.user, 'centro', None) or getattr(getattr(request.user, 'profile', None), 'centro', None)
            return obj.centro == user_centro
        return False


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


class CanManageOwnProfile(permissions.BasePermission):
    """Gestión de perfil propio."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if _has_role(request.user, ['admin']):
            return True
        return obj == request.user
