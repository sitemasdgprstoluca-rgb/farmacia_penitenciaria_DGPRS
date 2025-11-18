"""
Management command para crear grupos de permisos
Ejecutar: python manage.py create_groups
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from core.models import Producto, Lote, Requisicion, Centro, Movimiento, DetalleRequisicion


class Command(BaseCommand):
    help = 'Crea los 4 grupos de permisos del sistema: ADMIN, FARMACEUTICO, SOLICITANTE, AUDITOR'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando creación de grupos y permisos...\n')
        
        # Crear grupos
        admin, _ = Group.objects.get_or_create(name='ADMIN')
        farmaceutico, _ = Group.objects.get_or_create(name='FARMACEUTICO')
        solicitante, _ = Group.objects.get_or_create(name='SOLICITANTE')
        auditor, _ = Group.objects.get_or_create(name='AUDITOR')
        
        self.stdout.write(self.style.SUCCESS('✓ Grupos creados/actualizados'))
        
        # Limpiar permisos existentes
        admin.permissions.clear()
        farmaceutico.permissions.clear()
        solicitante.permissions.clear()
        auditor.permissions.clear()
        
        # ============================================
        # GRUPO ADMIN - Acceso total
        # ============================================
        self.stdout.write('\nConfigurando permisos para ADMIN...')
        
        for model in [Producto, Lote, Requisicion, DetalleRequisicion, Centro, Movimiento]:
            ct = ContentType.objects.get_for_model(model)
            perms = Permission.objects.filter(content_type=ct)
            admin.permissions.add(*perms)
            self.stdout.write(f'  ✓ {model.__name__}: {perms.count()} permisos')
        
        # ============================================
        # GRUPO FARMACEUTICO - Gestión de inventario y requisiciones
        # ============================================
        self.stdout.write('\nConfigurando permisos para FARMACEUTICO...')
        
        # Productos: CRUD completo
        producto_ct = ContentType.objects.get_for_model(Producto)
        producto_perms = Permission.objects.filter(content_type=producto_ct)
        farmaceutico.permissions.add(*producto_perms)
        self.stdout.write(f'  ✓ Productos: {producto_perms.count()} permisos')
        
        # Lotes: CRUD completo
        lote_ct = ContentType.objects.get_for_model(Lote)
        lote_perms = Permission.objects.filter(content_type=lote_ct)
        farmaceutico.permissions.add(*lote_perms)
        self.stdout.write(f'  ✓ Lotes: {lote_perms.count()} permisos')
        
        # Requisiciones: view, change (autorizar)
        req_ct = ContentType.objects.get_for_model(Requisicion)
        req_perms = Permission.objects.filter(
            content_type=req_ct,
            codename__in=['view_requisicion', 'change_requisicion']
        )
        farmaceutico.permissions.add(*req_perms)
        self.stdout.write(f'  ✓ Requisiciones: view, change')
        
        # DetalleRequisicion: view, change
        detalle_ct = ContentType.objects.get_for_model(DetalleRequisicion)
        detalle_perms = Permission.objects.filter(
            content_type=detalle_ct,
            codename__in=['view_detallerequisicion', 'change_detallerequisicion']
        )
        farmaceutico.permissions.add(*detalle_perms)
        self.stdout.write(f'  ✓ DetalleRequisicion: view, change')
        
        # Movimientos: add, view
        mov_ct = ContentType.objects.get_for_model(Movimiento)
        mov_perms = Permission.objects.filter(
            content_type=mov_ct,
            codename__in=['add_movimiento', 'view_movimiento']
        )
        farmaceutico.permissions.add(*mov_perms)
        self.stdout.write(f'  ✓ Movimientos: add, view')
        
        # Centros: view
        centro_ct = ContentType.objects.get_for_model(Centro)
        centro_view = Permission.objects.get(
            content_type=centro_ct,
            codename='view_centro'
        )
        farmaceutico.permissions.add(centro_view)
        self.stdout.write(f'  ✓ Centros: view')
        
        # ============================================
        # GRUPO SOLICITANTE - Solo requisiciones
        # ============================================
        self.stdout.write('\nConfigurando permisos para SOLICITANTE...')
        
        # Requisiciones: add, view (solo las suyas)
        req_add = Permission.objects.get(content_type=req_ct, codename='add_requisicion')
        req_view = Permission.objects.get(content_type=req_ct, codename='view_requisicion')
        solicitante.permissions.add(req_add, req_view)
        self.stdout.write(f'  ✓ Requisiciones: add, view (propias)')
        
        # DetalleRequisicion: add, view
        detalle_add = Permission.objects.get(content_type=detalle_ct, codename='add_detallerequisicion')
        detalle_view = Permission.objects.get(content_type=detalle_ct, codename='view_detallerequisicion')
        solicitante.permissions.add(detalle_add, detalle_view)
        self.stdout.write(f'  ✓ DetalleRequisicion: add, view')
        
        # Productos: view (para consultar disponibilidad)
        producto_view = Permission.objects.get(content_type=producto_ct, codename='view_producto')
        solicitante.permissions.add(producto_view)
        self.stdout.write(f'  ✓ Productos: view')
        
        # Lotes: view (para ver disponibilidad)
        lote_view = Permission.objects.get(content_type=lote_ct, codename='view_lote')
        solicitante.permissions.add(lote_view)
        self.stdout.write(f'  ✓ Lotes: view')
        
        # ============================================
        # GRUPO AUDITOR - Solo lectura
        # ============================================
        self.stdout.write('\nConfigurando permisos para AUDITOR...')
        
        for model in [Producto, Lote, Requisicion, DetalleRequisicion, Centro, Movimiento]:
            ct = ContentType.objects.get_for_model(model)
            view_perm = Permission.objects.get(
                content_type=ct,
                codename=f'view_{model.__name__.lower()}'
            )
            auditor.permissions.add(view_perm)
            self.stdout.write(f'  ✓ {model.__name__}: view')
        
        # Resumen final
        self.stdout.write(self.style.SUCCESS('\n✅ Grupos y permisos configurados exitosamente'))
        self.stdout.write(f'\nADMIN: {admin.permissions.count()} permisos')
        self.stdout.write(f'FARMACEUTICO: {farmaceutico.permissions.count()} permisos')
        self.stdout.write(f'SOLICITANTE: {solicitante.permissions.count()} permisos')
        self.stdout.write(f'AUDITOR: {auditor.permissions.count()} permisos')
        self.stdout.write('\nEjecuta: python manage.py create_test_users para crear usuarios de prueba\n')
