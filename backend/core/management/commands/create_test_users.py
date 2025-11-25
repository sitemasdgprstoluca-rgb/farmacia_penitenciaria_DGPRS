"""
Management command para crear usuarios de prueba
Ejecutar: python manage.py create_test_users
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from core.models import User, Centro, UserProfile


class Command(BaseCommand):
    help = 'Crea usuarios de prueba para cada grupo del sistema'

    def handle(self, *args, **options):
        self.stdout.write('Creando usuarios de prueba...\n')
        
        # Crear centros de prueba
        centro_norte, _ = Centro.objects.get_or_create(
            clave='CP-NORTE',
            defaults={
                'nombre': 'Centro Penitenciario Norte',
                'tipo': 'CERESO',
                'responsable': 'Lic. Juan López'
            }
        )
        
        centro_sur, _ = Centro.objects.get_or_create(
            clave='CP-SUR',
            defaults={
                'nombre': 'Centro Penitenciario Sur',
                'tipo': 'CERESO',
                'responsable': 'Dra. Ana Martínez'
            }
        )
        
        self.stdout.write(self.style.SUCCESS('✓ Centros de prueba creados'))
        
        # ============================================
        # Usuario ADMIN (Superusuario)
        # ============================================
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@farmacia.gob.mx',
                password='Admin@2025',
                first_name='Super',
                last_name='Administrador'
            )
            self.stdout.write(self.style.SUCCESS('✓ ADMIN creado: admin / Admin@2025'))
        else:
            self.stdout.write(self.style.WARNING('⚠ Usuario admin ya existe'))
        
        # ============================================
        # Usuario FARMACEUTICO
        # ============================================
        if not User.objects.filter(username='farmacia').exists():
            farmacia_user = User.objects.create_user(
                username='farmacia',
                email='farmacia@penitenciaria.gob.mx',
                password='Farmacia@2025',
                first_name='María',
                last_name='García'
            )
            
            grupo_farmaceutico = Group.objects.get(name='FARMACEUTICO')
            farmacia_user.groups.add(grupo_farmaceutico)
            
            self.stdout.write(self.style.SUCCESS('✓ FARMACEUTICO creado: farmacia / Farmacia@2025'))
        else:
            self.stdout.write(self.style.WARNING('⚠ Usuario farmacia ya existe'))
        
        # ============================================
        # Usuario SOLICITANTE - Centro Norte
        # ============================================
        if not User.objects.filter(username='solicitante_norte').exists():
            solicitante_norte = User.objects.create_user(
                username='solicitante_norte',
                email='norte@penitenciaria.gob.mx',
                password='Solicitante@2025',
                first_name='Juan',
                last_name='López',
                centro=centro_norte
            )
            
            grupo_solicitante = Group.objects.get(name='SOLICITANTE')
            solicitante_norte.groups.add(grupo_solicitante)
            
            # Crear perfil
            UserProfile.objects.create(
                user=solicitante_norte,
                cargo='Responsable de Centro'
            )
            
            self.stdout.write(self.style.SUCCESS('✓ SOLICITANTE (Norte) creado: solicitante_norte / Solicitante@2025'))
        else:
            self.stdout.write(self.style.WARNING('⚠ Usuario solicitante_norte ya existe'))
        
        # ============================================
        # Usuario SOLICITANTE - Centro Sur
        # ============================================
        if not User.objects.filter(username='solicitante_sur').exists():
            solicitante_sur = User.objects.create_user(
                username='solicitante_sur',
                email='sur@penitenciaria.gob.mx',
                password='Solicitante@2025',
                first_name='Ana',
                last_name='Martínez',
                centro=centro_sur
            )
            
            grupo_solicitante = Group.objects.get(name='SOLICITANTE')
            solicitante_sur.groups.add(grupo_solicitante)
            
            UserProfile.objects.create(
                user=solicitante_sur,
                cargo='Responsable de Centro'
            )
            
            self.stdout.write(self.style.SUCCESS('✓ SOLICITANTE (Sur) creado: solicitante_sur / Solicitante@2025'))
        else:
            self.stdout.write(self.style.WARNING('⚠ Usuario solicitante_sur ya existe'))
        
        # ============================================
        # Usuario AUDITOR
        # ============================================
        if not User.objects.filter(username='auditor').exists():
            auditor_user = User.objects.create_user(
                username='auditor',
                email='auditor@penitenciaria.gob.mx',
                password='Auditor@2025',
                first_name='Sandra',
                last_name='Ramírez'
            )
            
            grupo_auditor = Group.objects.get(name='AUDITOR')
            auditor_user.groups.add(grupo_auditor)
            
            self.stdout.write(self.style.SUCCESS('✓ AUDITOR creado: auditor / Auditor@2025'))
        else:
            self.stdout.write(self.style.WARNING('⚠ Usuario auditor ya existe'))
        
        # Resumen
        self.stdout.write(self.style.SUCCESS('\n✅ Usuarios de prueba creados exitosamente'))
        self.stdout.write('\n📋 CREDENCIALES DE ACCESO:')
        self.stdout.write('─' * 60)
        self.stdout.write('ADMIN:             admin / Admin@2025')
        self.stdout.write('FARMACEUTICO:      farmacia / Farmacia@2025')
        self.stdout.write('SOLICITANTE NORTE: solicitante_norte / Solicitante@2025')
        self.stdout.write('SOLICITANTE SUR:   solicitante_sur / Solicitante@2025')
        self.stdout.write('AUDITOR:           auditor / Auditor@2025')
        self.stdout.write('─' * 60 + '\n')
