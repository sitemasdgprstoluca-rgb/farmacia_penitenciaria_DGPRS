"""
Management command para crear grupos de usuarios y asignar permisos
Ejecutar: python manage.py setup_groups
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from core.models import Producto, Lote, Requisicion, Centro, Movimiento, User
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Crea grupos de usuarios y asigna permisos según jerarquía'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando creación de grupos y permisos...')
        
        # Crear grupos
        farmacia_admin, created = Group.objects.get_or_create(name='FARMACIA_ADMIN')
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Grupo FARMACIA_ADMIN creado'))
        
        centro_user, created = Group.objects.get_or_create(name='CENTRO_USER')
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Grupo CENTRO_USER creado'))
        
        vista_user, created = Group.objects.get_or_create(name='VISTA_USER')
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Grupo VISTA_USER creado'))
        
        # Limpiar permisos existentes
        farmacia_admin.permissions.clear()
        centro_user.permissions.clear()
        vista_user.permissions.clear()
        
        # ========================================
        # FARMACIA_ADMIN: CRUD completo de productos, lotes, requisiciones
        # ========================================
        self.stdout.write('\nConfigurando permisos para FARMACIA_ADMIN...')
        
        # Producto: add, change, delete, view
        producto_ct = ContentType.objects.get_for_model(Producto)
        producto_perms = Permission.objects.filter(content_type=producto_ct)
        farmacia_admin.permissions.add(*producto_perms)
        self.stdout.write(f'  ✓ Productos: {producto_perms.count()} permisos')
        
        # Lote: add, change, delete, view
        lote_ct = ContentType.objects.get_for_model(Lote)
        lote_perms = Permission.objects.filter(content_type=lote_ct)
        farmacia_admin.permissions.add(*lote_perms)
        self.stdout.write(f'  ✓ Lotes: {lote_perms.count()} permisos')
        
        # Requisicion: add, change, delete, view
        req_ct = ContentType.objects.get_for_model(Requisicion)
        req_perms = Permission.objects.filter(content_type=req_ct)
        farmacia_admin.permissions.add(*req_perms)
        self.stdout.write(f'  ✓ Requisiciones: {req_perms.count()} permisos')
        
        # Centro: add, change, delete, view
        centro_ct = ContentType.objects.get_for_model(Centro)
        centro_perms = Permission.objects.filter(content_type=centro_ct)
        farmacia_admin.permissions.add(*centro_perms)
        self.stdout.write(f'  ✓ Centros: {centro_perms.count()} permisos')
        
        # Movimiento: add, change, view
        mov_ct = ContentType.objects.get_for_model(Movimiento)
        mov_perms = Permission.objects.filter(
            content_type=mov_ct,
            codename__in=['add_movimiento', 'change_movimiento', 'view_movimiento']
        )
        farmacia_admin.permissions.add(*mov_perms)
        self.stdout.write(f'  ✓ Movimientos: {mov_perms.count()} permisos')
        
        # ========================================
        # CENTRO_USER: Solo requisiciones (crear, ver)
        # ========================================
        self.stdout.write('\nConfigurando permisos para CENTRO_USER...')
        
        # Requisicion: add, view (NO change, NO delete)
        req_view = Permission.objects.get(
            content_type=req_ct,
            codename='view_requisicion'
        )
        req_add = Permission.objects.get(
            content_type=req_ct,
            codename='add_requisicion'
        )
        centro_user.permissions.add(req_view, req_add)
        self.stdout.write(f'  ✓ Requisiciones: view, add')
        
        # Producto: view (para consultar disponibilidad)
        prod_view = Permission.objects.get(
            content_type=producto_ct,
            codename='view_producto'
        )
        centro_user.permissions.add(prod_view)
        self.stdout.write(f'  ✓ Productos: view')
        
        # Lote: view (para ver disponibilidad)
        lote_view = Permission.objects.get(
            content_type=lote_ct,
            codename='view_lote'
        )
        centro_user.permissions.add(lote_view)
        self.stdout.write(f'  ✓ Lotes: view')
        
        # ========================================
        # VISTA_USER: Solo view en todos
        # ========================================
        self.stdout.write('\nConfigurando permisos para VISTA_USER...')
        
        for model in [Producto, Lote, Requisicion, Centro, Movimiento]:
            ct = ContentType.objects.get_for_model(model)
            perm = Permission.objects.get(
                content_type=ct,
                codename=f'view_{model.__name__.lower()}'
            )
            vista_user.permissions.add(perm)
            self.stdout.write(f'  ✓ {model.__name__}: view')
        
        # Resumen final
        self.stdout.write(self.style.SUCCESS('\n✅ Grupos y permisos configurados exitosamente'))
        self.stdout.write(f'\nFARMACIA_ADMIN: {farmacia_admin.permissions.count()} permisos')
        self.stdout.write(f'CENTRO_USER: {centro_user.permissions.count()} permisos')
        self.stdout.write(f'VISTA_USER: {vista_user.permissions.count()} permisos')
