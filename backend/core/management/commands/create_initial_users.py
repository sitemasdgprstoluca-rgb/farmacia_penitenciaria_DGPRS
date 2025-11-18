"""
Management command para crear usuarios iniciales de prueba
Ejecutar: python manage.py create_initial_users
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from core.models import User, Centro, UserProfile
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Crea usuarios iniciales para cada rol del sistema'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando creación de usuarios iniciales...')
        
        # ========================================
        # 1. SUPER ADMINISTRADOR
        # ========================================
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@farmacia.gob.mx',
                password='Admin@2025',
                first_name='Super',
                last_name='Administrador',
                rol='superusuario'
            )
            self.stdout.write(self.style.SUCCESS('✓ SUPER_ADMIN creado: admin / Admin@2025'))
        else:
            self.stdout.write(self.style.WARNING('⚠ SUPER_ADMIN ya existe'))
        
        # ========================================
        # 2. FARMACIA_ADMIN
        # ========================================
        if not User.objects.filter(username='farmacia_admin').exists():
            farmacia_user = User.objects.create_user(
                username='farmacia_admin',
                email='farmacia@penitenciaria.gob.mx',
                password='Farmacia@2025',
                first_name='María',
                last_name='García López',
                rol='admin_farmacia'
            )
            
            farmacia_admin_group = Group.objects.get(name='FARMACIA_ADMIN')
            farmacia_user.groups.add(farmacia_admin_group)
            
            self.stdout.write(self.style.SUCCESS('✓ FARMACIA_ADMIN creado: farmacia_admin / Farmacia@2025'))
        else:
            self.stdout.write(self.style.WARNING('⚠ FARMACIA_ADMIN ya existe'))
        
        # ========================================
        # 3. CENTROS DE PRUEBA Y USUARIOS
        # ========================================
        centros_data = [
            {
                'clave': 'CP-NORTE',
                'nombre': 'Centro Penitenciario Norte',
                'tipo': 'CERESO',
                'responsable': 'Lic. Juan López',
                'username': 'centro_norte',
                'first_name': 'Juan',
                'last_name': 'López Rodríguez'
            },
            {
                'clave': 'CP-SUR',
                'nombre': 'Centro Penitenciario Sur',
                'tipo': 'CERESO',
                'responsable': 'Dra. Ana Martínez',
                'username': 'centro_sur',
                'first_name': 'Ana',
                'last_name': 'Martínez Sánchez'
            },
            {
                'clave': 'CEFERESO-01',
                'nombre': 'Centro Federal de Readaptación Social No. 1',
                'tipo': 'CEFERESO',
                'responsable': 'Mtro. Carlos Ramírez',
                'username': 'cefereso_01',
                'first_name': 'Carlos',
                'last_name': 'Ramírez Torres'
            }
        ]
        
        centro_user_group = Group.objects.get(name='CENTRO_USER')
        
        for centro_data in centros_data:
            # Crear centro si no existe
            centro, centro_created = Centro.objects.get_or_create(
                clave=centro_data['clave'],
                defaults={
                    'nombre': centro_data['nombre'],
                    'tipo': centro_data['tipo'],
                    'responsable': centro_data['responsable']
                }
            )
            
            if centro_created:
                self.stdout.write(f'  ✓ Centro creado: {centro.clave}')
            
            # Crear usuario si no existe
            if not User.objects.filter(username=centro_data['username']).exists():
                centro_user = User.objects.create_user(
                    username=centro_data['username'],
                    email=f"{centro_data['username']}@penitenciaria.gob.mx",
                    password='Centro@2025',
                    first_name=centro_data['first_name'],
                    last_name=centro_data['last_name'],
                    rol='usuario_normal',
                    centro=centro
                )
                
                centro_user.groups.add(centro_user_group)
                
                # Crear perfil extendido
                UserProfile.objects.create(
                    user=centro_user,
                    centro=centro,
                    cargo='Responsable de Centro'
                )
                
                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ CENTRO_USER creado: {centro_data["username"]} / Centro@2025'
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f'  ⚠ Usuario {centro_data["username"]} ya existe'
                ))
        
        # ========================================
        # 4. VISTA_USER (Reportes)
        # ========================================
        if not User.objects.filter(username='reportes').exists():
            vista_user = User.objects.create_user(
                username='reportes',
                email='reportes@penitenciaria.gob.mx',
                password='Reportes@2025',
                first_name='Sandra',
                last_name='Martínez Díaz',
                rol='vista_user'
            )
            
            vista_user_group = Group.objects.get(name='VISTA_USER')
            vista_user.groups.add(vista_user_group)
            
            self.stdout.write(self.style.SUCCESS('✓ VISTA_USER creado: reportes / Reportes@2025'))
        else:
            self.stdout.write(self.style.WARNING('⚠ VISTA_USER ya existe'))
        
        # Resumen final
        self.stdout.write(self.style.SUCCESS('\n✅ Usuarios iniciales creados exitosamente'))
        self.stdout.write('\n📋 CREDENCIALES DE ACCESO:')
        self.stdout.write('─' * 60)
        self.stdout.write('SUPER_ADMIN:     admin / Admin@2025')
        self.stdout.write('FARMACIA_ADMIN:  farmacia_admin / Farmacia@2025')
        self.stdout.write('CENTRO_NORTE:    centro_norte / Centro@2025')
        self.stdout.write('CENTRO_SUR:      centro_sur / Centro@2025')
        self.stdout.write('CEFERESO_01:     cefereso_01 / Centro@2025')
        self.stdout.write('VISTA_USER:      reportes / Reportes@2025')
        self.stdout.write('─' * 60)
