from rest_framework import permissions


class IsSuperuserAll(permissions.BasePermission):
    """Permite todo al superusuario"""
    def has_permission(self, request, view):
        return request.user and request.user.is_superuser


class IsFarmaciaAdmin(permissions.BasePermission):
    """Solo usuarios del grupo FARMACIA_ADMIN"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return (
            request.user.is_superuser or 
            request.user.groups.filter(name='FARMACIA_ADMIN').exists()
        )


class IsFarmaciaAdminOrReadOnly(permissions.BasePermission):
    """FARMACIA_ADMIN puede todo, otros solo lectura"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return (
            request.user.is_superuser or 
            request.user.groups.filter(name='FARMACIA_ADMIN').exists()
        )


class IsCentroUser(permissions.BasePermission):
    """Solo usuarios del grupo CENTRO_USER"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return (
            request.user.is_superuser or 
            request.user.groups.filter(name='CENTRO_USER').exists()
        )


class IsCentroUserForOwnRequests(permissions.BasePermission):
    """CENTRO_USER solo puede ver/editar sus propias requisiciones"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser or request.user.groups.filter(name='FARMACIA_ADMIN').exists():
            return True
        
        return request.user.groups.filter(name='CENTRO_USER').exists()

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser or request.user.groups.filter(name='FARMACIA_ADMIN').exists():
            return True
        
        if request.user.groups.filter(name='CENTRO_USER').exists():
            return obj.solicitante == request.user
        
        return False


class IsViewerReadOnly(permissions.BasePermission):
    """VISTA_USER solo puede leer"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.method not in permissions.SAFE_METHODS:
            return False
        
        return (
            request.user.is_superuser or 
            request.user.groups.filter(name__in=['FARMACIA_ADMIN', 'VISTA_USER']).exists()
        )
