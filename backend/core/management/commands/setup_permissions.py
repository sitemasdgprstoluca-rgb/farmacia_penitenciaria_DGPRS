from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from core.models import Producto, Lote, Requisicion, Centro, Movimiento


class Command(BaseCommand):
    help = 'Crea grupos de usuarios y asigna permisos'

    def handle(self, *args, **options):
        self.stdout.write('Creando grupos y permisos...')
        
        # Crear grupos
        farmacia_admin, _ = Group.objects.get_or_create(name='FARMACIA_ADMIN')
        centro_user, _ = Group.objects.get_or_create(name='CENTRO_USER')
        vista_user, _ = Group.objects.get_or_create(name='VISTA_USER')
        
        self.stdout.write(self.style.SUCCESS('✓ Grupos creados'))
        
        # Limpiar permisos
        farmacia_admin.permissions.clear()
        centro_user.permissions.clear()
        vista_user.permissions.clear()
        
        # FARMACIA_ADMIN - Todos los permisos
        for model in [Producto, Lote, Requisicion, Centro, Movimiento]:
            ct = ContentType.objects.get_for_model(model)
            perms = Permission.objects.filter(content_type=ct)
            farmacia_admin.permissions.add(*perms)
        
        self.stdout.write(self.style.SUCCESS(f'✓ FARMACIA_ADMIN: {farmacia_admin.permissions.count()} permisos'))
        
        # CENTRO_USER - Ver y crear requisiciones
        req_ct = ContentType.objects.get_for_model(Requisicion)
        centro_user.permissions.add(
            Permission.objects.get(content_type=req_ct, codename='view_requisicion'),
            Permission.objects.get(content_type=req_ct, codename='add_requisicion'),
        )
        
        # Ver productos y lotes
        prod_ct = ContentType.objects.get_for_model(Producto)
        centro_user.permissions.add(
            Permission.objects.get(content_type=prod_ct, codename='view_producto')
        )
        
        self.stdout.write(self.style.SUCCESS(f'✓ CENTRO_USER: {centro_user.permissions.count()} permisos'))
        
        # VISTA_USER - Solo lectura
        for model in [Producto, Lote, Requisicion, Centro, Movimiento]:
            ct = ContentType.objects.get_for_model(model)
            vista_user.permissions.add(
                Permission.objects.get(content_type=ct, codename=f'view_{model.__name__.lower()}')
            )
        
        self.stdout.write(self.style.SUCCESS(f'✓ VISTA_USER: {vista_user.permissions.count()} permisos'))
        
        self.stdout.write(self.style.SUCCESS('\n✅ Grupos y permisos configurados correctamente'))
