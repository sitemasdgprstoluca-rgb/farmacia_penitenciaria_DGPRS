"""
Helpers para verificar permisos de forma programatica.
Uso: en signals, management commands y logica de negocio.
"""
from core.models import UserProfile


def es_superuser(usuario):
    """
    Verifica si el usuario es superusuario o admin del sistema.

    Args:
        usuario: Objeto User

    Returns:
        bool: True si es superuser o staff
    """
    return usuario.is_superuser or usuario.is_staff


def es_farmacia_admin(usuario):
    """
    Verifica si el usuario puede administrar la farmacia.
    """
    if es_superuser(usuario):
        return True

    profile = getattr(usuario, 'userprofile', None)
    if not profile:
        return False

    return profile.role in ['FARMACIA_ADMIN', 'admin_farmacia']


def es_farmacia_viewer(usuario):
    """
    Verifica si el usuario es visualizador de farmacia.
    """
    profile = getattr(usuario, 'userprofile', None)
    if not profile:
        return False
    return profile.role in ['FARMACIA_VIEWER']


def es_farmacia_role(usuario):
    """
    Verifica si el usuario tiene cualquier rol de farmacia (admin o viewer).
    """
    if es_superuser(usuario):
        return True
    return es_farmacia_admin(usuario) or es_farmacia_viewer(usuario)


def es_centro_user(usuario):
    """
    Verifica si el usuario es de un centro penitenciario.
    """
    profile = getattr(usuario, 'userprofile', None)
    if not profile:
        return False
    return profile.role in ['CENTRO_USER', 'centro', 'usuario_normal']


def puede_ver_requisicion(usuario, requisicion):
    """
    Verifica si el usuario puede ver una requisicion especifica.
    
    ISS-FIX: Usar centro_origen (quien hizo la requisición), no centro (alias de centro_destino).
    Los usuarios de centro pueden ver requisiciones que ELLOS crearon (centro_origen = su centro).
    """
    if es_superuser(usuario):
        return True
    if es_farmacia_admin(usuario):
        return True
    if es_centro_user(usuario):
        if usuario.centro:
            # ISS-FIX: centro_origen es el centro que HIZO la requisición
            return requisicion.centro_origen == usuario.centro
        return False
    return requisicion.usuario_solicita == usuario


def puede_autorizar_requisicion(usuario, requisicion=None):
    """
    Verifica si el usuario puede autorizar/rechazar requisiciones.
    """
    if es_superuser(usuario):
        return True
    return es_farmacia_admin(usuario)


def puede_ver_producto(usuario):
    """
    Verifica si el usuario tiene acceso al catalogo de productos.
    """
    if es_superuser(usuario):
        return True
    return es_farmacia_role(usuario) or es_centro_user(usuario)


def puede_crear_producto(usuario):
    """
    Verifica si el usuario puede crear productos.
    """
    if es_superuser(usuario):
        return True
    return es_farmacia_admin(usuario)


def puede_ver_centro(usuario, centro):
    """
    Verifica si el usuario puede ver un centro especifico.
    """
    if es_superuser(usuario):
        return True
    if es_farmacia_role(usuario):
        return True
    profile = getattr(usuario, 'userprofile', None)
    if profile and profile.centro:
        return profile.centro == centro
    return False


def puede_ver_reportes(usuario, centro=None):
    """
    Verifica acceso a reportes.
    """
    if es_superuser(usuario):
        return True
    if es_farmacia_role(usuario):
        return True
    if es_centro_user(usuario) and centro:
        profile = getattr(usuario, 'userprofile', None)
        return profile and profile.centro == centro
    return False


def puede_gestionar_movimientos(usuario):
    """
    Verifica si el usuario puede registrar movimientos de inventario.
    """
    return es_superuser(usuario) or es_farmacia_admin(usuario)


def puede_ver_notificaciones(usuario):
    """
    Verifica si el usuario puede ver sus notificaciones.
    """
    return usuario.is_authenticated


def tiene_permiso(usuario, accion, obj=None):
    """
    Funcion generica para verificar permisos sobre un objeto especifico.
    """
    if accion == 'ver_requisicion' and obj is not None:
        return puede_ver_requisicion(usuario, obj)
    if accion == 'autorizar_requisicion':
        return puede_autorizar_requisicion(usuario, obj)
    if accion == 'ver_producto':
        return puede_ver_producto(usuario)
    if accion == 'crear_producto':
        return puede_crear_producto(usuario)
    if accion == 'ver_centro' and obj is not None:
        return puede_ver_centro(usuario, obj)
    if accion == 'ver_reportes':
        return puede_ver_reportes(usuario, obj)
    if accion == 'movimientos':
        return puede_gestionar_movimientos(usuario)
    return False
