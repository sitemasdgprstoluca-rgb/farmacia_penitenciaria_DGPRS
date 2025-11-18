"""
Sistema completo de permisos basado en roles jerárquicos
Estructura: SUPER_ADMIN > FARMACIA_ADMIN > CENTRO_USER > VISTA_USER
"""
from rest_framework import permissions
import logging

logger = logging.getLogger(__name__)


class IsSuperuserOnly(permissions.BasePermission):
    """
    Permiso SOLO para superusuarios
    Uso: Gestión de usuarios, configuración del sistema
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_superuser


class IsFarmaciaAdmin(permissions.BasePermission):
    """
    Permiso para FARMACIA_ADMIN y SUPERUSER
    Uso: Gestión de productos, lotes, autorización de requisiciones
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superusuario siempre tiene acceso
        if request.user.is_superuser:
            return True
        
        # Verificar si pertenece al grupo FARMACIA_ADMIN
        return request.user.groups.filter(name='FARMACIA_ADMIN').exists()


class IsFarmaciaAdminOrReadOnly(permissions.BasePermission):
    """
    Permiso que permite:
    - Lectura: Todos los usuarios autenticados
    - Escritura: Solo FARMACIA_ADMIN y SUPERUSER
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Escritura solo para superusuario o farmacia_admin
        if request.user.is_superuser:
            return True
        
        return request.user.groups.filter(name='FARMACIA_ADMIN').exists()


class IsCentroUser(permissions.BasePermission):
    """
    Permiso para CENTRO_USER (usuarios de centros penitenciarios)
    Pueden crear requisiciones solo para su centro
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superusuario y Farmacia_Admin siempre tienen acceso
        if request.user.is_superuser or request.user.groups.filter(name='FARMACIA_ADMIN').exists():
            return True
        
        # CENTRO_USER tiene acceso
        return request.user.groups.filter(name='CENTRO_USER').exists()
    
    def has_object_permission(self, request, view, obj):
        """
        Validación a nivel de objeto:
        - CENTRO_USER solo puede ver/editar sus propias requisiciones
        """
        if request.user.is_superuser or request.user.groups.filter(name='FARMACIA_ADMIN').exists():
            return True
        
        # Para CENTRO_USER: validar que sea de su centro
        if hasattr(obj, 'centro'):
            user_centro = getattr(request.user.profile, 'centro', None) if hasattr(request.user, 'profile') else None
            return obj.centro == user_centro or obj.centro == request.user.centro
        
        return False


class CanAuthorizeRequisicion(permissions.BasePermission):
    """
    Permiso para autorizar/rechazar/surtir requisiciones
    Solo FARMACIA_ADMIN y SUPERUSER
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        return request.user.groups.filter(name='FARMACIA_ADMIN').exists()


class IsVistaUserOrAdmin(permissions.BasePermission):
    """
    Permiso para VISTA_USER (solo lectura de reportes)
    También permite acceso a FARMACIA_ADMIN y SUPERUSER
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Solo métodos de lectura
        if request.method not in permissions.SAFE_METHODS:
            return False
        
        # Superusuario siempre puede
        if request.user.is_superuser:
            return True
        
        # FARMACIA_ADMIN puede ver reportes
        if request.user.groups.filter(name='FARMACIA_ADMIN').exists():
            return True
        
        # VISTA_USER puede ver reportes
        return request.user.groups.filter(name='VISTA_USER').exists()


class CanManageOwnProfile(permissions.BasePermission):
    """
    Permiso para gestionar perfil propio
    Todos pueden editar su propio perfil
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Superusuario puede editar cualquier perfil
        if request.user.is_superuser:
            return True
        
        # Usuario solo puede editar su propio perfil
        return obj == request.user
