import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Lote, Producto
from django.contrib.auth import get_user_model

User = get_user_model()

print('='*60)
print('DIAGNÓSTICO DE DATOS')
print('='*60)

# Verificar lotes
lotes = Lote.objects.filter(deleted_at__isnull=True)
print(f'\nLotes activos: {lotes.count()}')
for l in lotes[:10]:
    c = l.centro.clave if l.centro else 'FARMACIA'
    print(f'  {l.numero_lote} | {c} | stock: {l.cantidad_actual}')

# Verificar productos
productos = Producto.objects.filter(activo=True)
print(f'\nProductos activos: {productos.count()}')

# Verificar función is_farmacia_or_admin
from inventario.views import is_farmacia_or_admin

admin = User.objects.filter(is_superuser=True).first()
print(f'\nAdmin user: {admin.username}')
print(f'is_farmacia_or_admin(admin): {is_farmacia_or_admin(admin)}')

# Verificar usuarios de farmacia
farmacia_users = User.objects.filter(rol__icontains='farmacia')
print(f'\nUsuarios farmacia: {farmacia_users.count()}')
for u in farmacia_users:
    print(f'  {u.username} | rol: {u.rol} | is_farmacia_or_admin: {is_farmacia_or_admin(u)}')

# Verificar caché
from django.core.cache import cache
cache_keys = ['dashboard_resumen_global', 'dashboard_graficas_global']
print('\nCaché:')
for key in cache_keys:
    val = cache.get(key)
    print(f'  {key}: {"EXISTE" if val else "NO EXISTE"}')

# Limpiar caché
cache.clear()
print('\n✓ Caché limpiado')
