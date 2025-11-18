from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from core.models import Centro, Producto, Lote, Movimiento, Requisicion, DetalleRequisicion


class Command(BaseCommand):
    help = 'Configura grupos y permisos del sistema'

    def handle(self, *args, **kwargs):
        self.stdout.write('Configurando grupos y permisos...')

        # Crear grupos
        farmacia_admin, _ = Group.objects.get_or_create(name='FARMACIA_ADMIN')
        centro_user, _ = Group.objects.get_or_create(name='CENTRO_USER')
        vista_user, _ = Group.objects.get_or_create(name='VISTA_USER')

        # FARMACIA_ADMIN - Todos los permisos
        modelos = [Centro, Producto, Lote, Movimiento, Requisicion, DetalleRequisicion]
        permisos_admin = []
        
        for modelo in modelos:
            ct = ContentType.objects.get_for_model(modelo)
            permisos_admin.extend(Permission.objects.filter(content_type=ct))
        
        farmacia_admin.permissions.set(permisos_admin)
        self.stdout.write(self.style.SUCCESS(f'✓ FARMACIA_ADMIN: {len(permisos_admin)} permisos'))

        # CENTRO_USER - Solo requisiciones propias
        permisos_centro = []
        for modelo in [Requisicion, DetalleRequisicion, Producto]:
            ct = ContentType.objects.get_for_model(modelo)
            permisos_centro.extend(Permission.objects.filter(
                content_type=ct,
                codename__in=['view_' + modelo._meta.model_name, 'add_requisicion', 'change_requisicion']
            ))
        
        centro_user.permissions.set(permisos_centro)
        self.stdout.write(self.style.SUCCESS(f'✓ CENTRO_USER: {len(permisos_centro)} permisos'))

        # VISTA_USER - Solo lectura
        permisos_vista = []
        for modelo in modelos:
            ct = ContentType.objects.get_for_model(modelo)
            permisos_vista.extend(Permission.objects.filter(
                content_type=ct,
                codename__startswith='view_'
            ))
        
        vista_user.permissions.set(permisos_vista)
        self.stdout.write(self.style.SUCCESS(f'✓ VISTA_USER: {len(permisos_vista)} permisos'))

        self.stdout.write(self.style.SUCCESS('Grupos configurados exitosamente'))
