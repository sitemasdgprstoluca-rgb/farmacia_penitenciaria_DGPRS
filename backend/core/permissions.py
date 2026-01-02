"""
Sistema completo de permisos basado en roles jerárquicos
Estructura: SUPER_ADMIN > FARMACIA_ADMIN > CENTRO_USER > VISTA_USER
"""
from rest_framework import permissions
import logging
from core.constants import EXTRA_PERMISSIONS

logger = logging.getLogger(__name__)


# =============================================================================
# ISS-004 FIX (audit16): HELPERS CENTRALIZADOS DE ROLES
# Funciones reutilizables para validar roles sin dependencia de DRF permissions
# =============================================================================

class RoleHelper:
    """
    ISS-004 FIX (audit16): Helper centralizado para validación de roles.
    
    Uso en servicios:
        from core.permissions import RoleHelper
        
        if not RoleHelper.is_farmacia_or_admin(usuario):
            raise PermisoRequisicionError("No tiene permisos de farmacia")
        
        centro = RoleHelper.get_user_centro(usuario)
    """
    
    ROLE_ALIASES = {
        'admin': {'admin', 'admin_sistema', 'superusuario'},
        'farmacia': {'farmacia', 'admin_farmacia', 'farmaceutico'},
        # FLUJO V2: Incluir roles jerárquicos del centro
        'centro': {'centro', 'usuario_normal', 'solicitante', 'medico', 'administrador_centro', 'director_centro', 'usuario_centro'},
        'vista': {'vista', 'usuario_vista'},
    }
    
    @classmethod
    def get_user_role(cls, user):
        """Obtiene el rol normalizado del usuario."""
        if not user or not getattr(user, 'is_authenticated', False):
            return None
        if user.is_superuser:
            return 'admin'
        return (getattr(user, 'rol', '') or '').lower()
    
    @classmethod
    def get_user_groups(cls, user):
        """Obtiene los grupos del usuario como set de nombres."""
        if not user or not getattr(user, 'is_authenticated', False):
            return set()
        return set(g.name.upper() for g in user.groups.all())
    
    @classmethod
    def get_user_centro(cls, user):
        """
        ISS-004 FIX: Obtiene el centro del usuario de forma segura.
        
        Returns:
            Centro del usuario o None si no tiene asignado.
        """
        if not user or not getattr(user, 'is_authenticated', False):
            return None
        return getattr(user, 'centro', None)
    
    @classmethod
    def has_role(cls, user, roles):
        """
        ISS-004 FIX: Verifica si usuario tiene alguno de los roles especificados.
        
        Args:
            user: Usuario a verificar
            roles: Lista de roles a verificar (ej: ['admin', 'farmacia'])
            
        Returns:
            bool: True si tiene alguno de los roles
        """
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        
        if user.is_superuser:
            return True
        
        normalized = cls.get_user_role(user)
        group_names = cls.get_user_groups(user)
        
        for role in roles:
            key = role.lower()
            # Verificar por campo rol
            if normalized in cls.ROLE_ALIASES.get(key, {key}):
                return True
            # Verificar por grupos
            if key == 'admin' and 'FARMACIA_ADMIN' in group_names:
                return True
            if key == 'farmacia' and ('FARMACIA_ADMIN' in group_names or 'FARMACEUTICO' in group_names):
                return True
            if key == 'centro' and ('CENTRO_USER' in group_names or 'SOLICITANTE' in group_names):
                return True
            if key == 'vista' and 'VISTA_USER' in group_names:
                return True
        
        return False
    
    @classmethod
    def is_admin(cls, user):
        """ISS-004 FIX: Verifica si usuario es administrador."""
        return cls.has_role(user, ['admin'])
    
    @classmethod
    def is_farmacia(cls, user):
        """ISS-004 FIX: Verifica si usuario es de farmacia (incluye admin)."""
        return cls.has_role(user, ['admin', 'farmacia'])
    
    @classmethod
    def is_farmacia_or_admin(cls, user):
        """ISS-004 FIX: Alias de is_farmacia para compatibilidad."""
        return cls.is_farmacia(user)
    
    @classmethod
    def is_centro(cls, user):
        """ISS-004 FIX: Verifica si usuario es de centro."""
        return cls.has_role(user, ['centro'])
    
    @classmethod
    def is_vista(cls, user):
        """ISS-004 FIX: Verifica si usuario es solo vista."""
        return cls.has_role(user, ['vista'])
    
    # =========================================================================
    # ISS-MEDICO FIX: Helpers para subroles específicos de centro
    # =========================================================================
    
    @classmethod
    def is_medico(cls, user):
        """
        ISS-MEDICO FIX: Verifica si usuario es específicamente médico.
        
        El rol médico tiene restricciones adicionales:
        - NO puede crear movimientos de inventario
        - NO puede ver historial de movimientos
        - Solo puede crear requisiciones
        """
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        normalized = cls.get_user_role(user)
        return normalized == 'medico'
    
    @classmethod
    def is_administrador_centro(cls, user):
        """ISS-MEDICO FIX: Verifica si usuario es administrador de centro."""
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        normalized = cls.get_user_role(user)
        return normalized == 'administrador_centro'
    
    @classmethod
    def is_director_centro(cls, user):
        """ISS-MEDICO FIX: Verifica si usuario es director de centro."""
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        normalized = cls.get_user_role(user)
        return normalized == 'director_centro'
    
    @classmethod
    def can_manage_inventory(cls, user):
        """
        ISS-MEDICO FIX: Verifica si usuario puede gestionar inventario (movimientos).
        
        Roles permitidos:
        - admin, farmacia: Siempre pueden
        - centro, usuario_centro, administrador_centro, director_centro: Pueden
        - medico: NO puede (solo requisiciones)
        - vista: NO puede
        """
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        if user.is_superuser:
            return True
        
        # Médico específicamente NO puede
        if cls.is_medico(user):
            return False
        
        # Vista NO puede
        if cls.is_vista(user):
            return False
        
        # Admin, farmacia y otros roles de centro SÍ pueden
        return cls.has_role(user, ['admin', 'farmacia', 'centro'])
    
    @classmethod
    def can_surtir(cls, user):
        """ISS-004 FIX: Verifica si usuario puede surtir requisiciones."""
        return cls.has_role(user, ['admin', 'farmacia'])
    
    @classmethod
    def can_autorizar(cls, user):
        """ISS-004 FIX: Verifica si usuario puede autorizar requisiciones."""
        return cls.has_role(user, ['admin', 'farmacia'])
    
    @classmethod
    def can_cancelar(cls, user):
        """ISS-004 FIX: Verifica si usuario puede cancelar requisiciones."""
        return cls.has_role(user, ['admin', 'farmacia'])
    
    @classmethod
    def validate_centro_access(cls, user, requisicion):
        """
        ISS-004 FIX: Valida que usuario tenga acceso a la requisición por centro.
        
        Args:
            user: Usuario a validar
            requisicion: Requisición a acceder
            
        Returns:
            bool: True si tiene acceso
            
        Raises:
            ValueError: Si no tiene acceso y no es admin/farmacia
        """
        # Admin y farmacia tienen acceso a todo
        if cls.is_farmacia(user):
            return True
        
        user_centro = cls.get_user_centro(user)
        if not user_centro:
            return False
        
        # Verificar por diferentes campos de centro
        req_centro = getattr(requisicion, 'centro_destino', None) or \
                     getattr(requisicion, 'centro_origen', None) or \
                     getattr(requisicion, 'centro', None)
        
        if req_centro and req_centro == user_centro:
            return True
        
        # Verificar por solicitante
        solicitante = getattr(requisicion, 'solicitante', None)
        if solicitante:
            sol_centro = getattr(solicitante, 'centro', None)
            if sol_centro == user_centro:
                return True
        
        return False


def _has_extra_perm(user, extras):
    """Valida si el usuario tiene algún permiso extra (vía grupos)."""
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    group_names = set(g.name.upper() for g in user.groups.all())
    for extra in extras:
        if extra.upper() in group_names:
            return True
    return False


def _infer_role_from_user(user):
    """
    ISS-PERMS FIX: Infiere el rol del usuario cuando el campo rol está vacío.
    
    Orden de inferencia:
    1. Si is_superuser o is_staff -> admin
    2. Si tiene centro asignado -> centro
    3. Default -> vista (solo lectura, más seguro)
    """
    if not user:
        return ''
    
    # Campo rol tiene valor válido
    rol = (getattr(user, 'rol', '') or '').lower()
    if rol and rol not in ['', 'null', 'none']:
        return rol
    
    # Inferir basándose en otros campos
    if getattr(user, 'is_superuser', False):
        return 'admin_sistema'
    
    if getattr(user, 'is_staff', False):
        return 'farmacia'  # Staff sin superuser = farmacia
    
    # Si tiene centro asignado, es usuario de centro
    centro = getattr(user, 'centro', None) or getattr(user, 'centro_id', None)
    if centro:
        return 'centro'
    
    # Default: usuario vista (más restrictivo, más seguro)
    return 'vista'


def _has_role(user, roles):
    """Valida roles por campo rol o por grupos heredados.
    
    ISS-PERMS FIX: Ahora infiere rol si el campo está vacío.
    ISS-AUDIT FIX: Usa RoleHelper.ROLE_ALIASES como única fuente de verdad.
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return False

    if user.is_superuser:
        return True

    # ISS-PERMS FIX: Usar rol inferido si el campo está vacío
    normalized = _infer_role_from_user(user)
    group_names = set(g.name.upper() for g in user.groups.all())

    # ISS-AUDIT FIX: Usar RoleHelper.ROLE_ALIASES como única fuente de verdad
    # Esto evita duplicación y posibles divergencias
    for role in roles:
        key = role.lower()
        aliases = RoleHelper.ROLE_ALIASES.get(key, {key})
        if normalized in aliases:
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
    """
    Usuarios de centro/unidad.
    
    ISS-019 FIX: El rol vista tiene acceso de solo lectura para auditoría/controles regulatorios.
    ISS-MEDICO FIX: El rol 'medico' está incluido en 'centro' via ROLE_ALIASES.
    """
    def has_permission(self, request, view):
        user = request.user
        
        # ISS-019 FIX: Para lectura, permitir también al rol vista (auditoría)
        if request.method in permissions.SAFE_METHODS:
            return _has_permission(user, ['admin', 'farmacia', 'centro', 'vista'], ['CAN_VIEW_ALL_REQUISICIONES'])
        
        # Para escritura, mantener restricción original (sin vista)
        return _has_permission(user, ['admin', 'farmacia', 'centro'], ['CAN_VIEW_ALL_REQUISICIONES'])


class IsCentroCanManageInventory(permissions.BasePermission):
    """
    ISS-MEDICO FIX v2: Permiso para gestión de inventario (movimientos).
    
    Este permiso permite al médico crear movimientos de SALIDA únicamente
    (para dispensación de medicamentos a pacientes).
    
    Para operaciones de escritura (POST, PUT, PATCH, DELETE):
    - admin, farmacia: Permitido
    - centro, administrador_centro, director_centro: Permitido
    - medico: PERMITIDO solo para POST (salidas) - validación adicional en perform_create
    - vista: DENEGADO
    
    Para operaciones de lectura (GET):
    - Todos los roles de centro pueden leer (incluyendo médico si configurado)
    - ISS-019 FIX: vista puede leer para auditoría/trazabilidad
    """
    def has_permission(self, request, view):
        user = request.user
        
        # Primero verificar autenticación básica
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        
        # Superusuarios siempre tienen acceso
        if user.is_superuser:
            return True
        
        # Para operaciones de escritura, verificar permisos
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            # ISS-MEDICO FIX v2: Médicos pueden crear (POST) salidas
            # La validación del tipo se hace en perform_create
            if RoleHelper.is_medico(user):
                return request.method == 'POST'  # Solo crear, no editar ni eliminar
            # Para otros usuarios, usar el helper centralizado
            return RoleHelper.can_manage_inventory(user)
        
        # ISS-019 FIX: Para lectura, permitir a roles de centro y vista (auditoría)
        return _has_permission(user, ['admin', 'farmacia', 'centro', 'vista'], ['CAN_VIEW_ALL_REQUISICIONES'])


class IsFarmaciaAdminOrVistaReadOnly(permissions.BasePermission):
    """
    ISS-MEDICO FIX: Permiso para catálogos globales (Centros, Lotes).
    
    Este permiso BLOQUEA a roles de centro (incluyendo médico) de ver
    catálogos globales que no necesitan para su operación.
    
    Lectura (GET):
    - admin, farmacia, vista: Permitido
    - centro, medico, administrador_centro, director_centro: DENEGADO (403)
    
    Escritura (POST, PUT, DELETE):
    - admin, farmacia: Permitido
    - Todos los demás: DENEGADO
    
    Esto evita exposición de datos innecesarios a roles de centro.
    """
    def has_permission(self, request, view):
        user = request.user
        
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        
        if user.is_superuser:
            return True
        
        # Para lectura: solo admin, farmacia y vista
        if request.method in permissions.SAFE_METHODS:
            return _has_role(user, ['admin', 'farmacia', 'vista'])
        
        # Para escritura: solo admin y farmacia
        return _has_role(user, ['admin', 'farmacia'])


class IsCentroOwnResourcesOnly(permissions.BasePermission):
    """
    ISS-MEDICO FIX: Permiso para recursos propios del centro.
    
    Permite a usuarios de centro (incluyendo médico) acceder SOLO a recursos
    de su propio centro. Para catálogos globales, retorna 403.
    
    Este permiso requiere que la vista implemente get_queryset() con filtrado
    por centro, o que el recurso tenga un campo 'centro' relacionado.
    
    Lectura:
    - admin, farmacia, vista: Acceso completo
    - centro, medico: Solo recursos de su centro
    
    Escritura:
    - admin, farmacia: Acceso completo
    - centro (no médico): Solo en su centro
    - medico: DENEGADO (403) - solo puede crear requisiciones
    """
    def has_permission(self, request, view):
        user = request.user
        
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        
        if user.is_superuser:
            return True
        
        # Admin/farmacia/vista tienen acceso
        if _has_role(user, ['admin', 'farmacia', 'vista']):
            return True
        
        # Médico: solo lectura de recursos de su centro, NO escritura
        if RoleHelper.is_medico(user):
            if request.method in permissions.SAFE_METHODS:
                # Permitir lectura, el queryset filtrará por centro
                return True
            # Médico no puede escribir en lotes/centros
            return False
        
        # Otros roles de centro: lectura sí, escritura solo en su centro
        if _has_role(user, ['centro']):
            return True
        
        return False


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
    """Permiso para ver notificaciones.
    
    ISS-PERMS FIX: Cualquier usuario autenticado puede ver sus notificaciones.
    El queryset filtra automáticamente por usuario.
    """
    def has_permission(self, request, view):
        # Cualquier usuario autenticado puede ver sus propias notificaciones
        return request.user and request.user.is_authenticated


class CanViewProfile(permissions.BasePermission):
    """Permiso para ver/editar perfil propio.
    
    ISS-PERMS FIX: Cualquier usuario autenticado puede ver su perfil.
    """
    def has_permission(self, request, view):
        # Cualquier usuario autenticado puede ver su propio perfil
        return request.user and request.user.is_authenticated


class CanManageOwnProfile(permissions.BasePermission):
    """Gestión de perfil propio."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if _has_role(request.user, ['admin']):
            return True
        return obj == request.user
