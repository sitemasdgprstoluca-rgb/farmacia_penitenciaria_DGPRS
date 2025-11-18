# filepath: apps/inventario/permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS

CATALOG_EDIT_GROUPS = ["ADMIN_SISTEMA", "FARMACIA_CENTRAL"]
INVENTORY_EDIT_GROUPS = ["ADMIN_SISTEMA", "FARMACIA_CENTRAL", "FARMACIA_UM"]


def user_in_groups(user, names):
  return user.groups.filter(name__in=names).exists()


class IsCatalogEditorOrReadOnly(BasePermission):
  """
  - Siempre requiere usuario autenticado.
  - Superuser o grupos de catálogo pueden crear/editar/borrar.
  - Cualquier usuario logueado puede hacer solo lectura (GET/HEAD/OPTIONS).
  """

  def has_permission(self, request, view):
    user = request.user

    # Nadie anónimo
    if not user or not user.is_authenticated:
      return False

    # Lectura para cualquier usuario logueado
    if request.method in SAFE_METHODS:
      return True

    # Escritura solo para superuser o grupos de catálogo
    if user.is_superuser or user_in_groups(user, CATALOG_EDIT_GROUPS):
      return True

    return False


class IsInventoryEditorOrReadOnly(BasePermission):
  """
  - Siempre requiere usuario autenticado.
  - Superuser o grupos de inventario pueden crear/editar/borrar.
  - Cualquier usuario logueado puede hacer solo lectura.
  """

  def has_permission(self, request, view):
    user = request.user

    if not user or not user.is_authenticated:
      return False

    if request.method in SAFE_METHODS:
      return True

    if user.is_superuser or user_in_groups(user, INVENTORY_EDIT_GROUPS):
      return True

    return False
