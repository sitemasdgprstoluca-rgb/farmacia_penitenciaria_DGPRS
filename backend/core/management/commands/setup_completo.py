"""
Comando para setup completo del sistema desde cero.
Ejecuta migraciones, crea centros, usuarios y verifica integridad.

Uso:
    python manage.py setup_completo
    python manage.py setup_completo --interactive
    python manage.py setup_completo --reset (CUIDADO: borra datos existentes)
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from core.models import Centro, UserProfile
import logging
import subprocess
import sys

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Setup completo: migraciones, centros, usuarios y verificación'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--interactive',
            action='store_true',
            help='Modo interactivo (solicita confirmación para cada paso)'
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Borrar datos existentes antes de crear (¡CUIDADO!)'
        )
        parser.add_argument(
            '--skip-migrations',
            action='store_true',
            help='Saltar aplicación de migraciones'
        )
    
    def handle(self, *args, **options):
        interactive = options.get('interactive', False)
        reset = options.get('reset', False)
        skip_migrations = options.get('skip_migrations', False)
        
        self.stdout.write(self.style.SUCCESS('\n╔═══════════════════════════════════════╗'))
        self.stdout.write(self.style.SUCCESS('║   SETUP COMPLETO - FARMACIA PENITENCIARIA   ║'))
        self.stdout.write(self.style.SUCCESS('╚═══════════════════════════════════════╝\n'))
        
        if reset:
            self.stdout.write(self.style.WARNING('⚠️  MODO RESET ACTIVADO - SE BORRARÁN DATOS'))
            if interactive:
                confirm = input('¿Está seguro? (escriba "SI" para confirmar): ')
                if confirm != 'SI':
                    self.stdout.write(self.style.ERROR('✗ Operación cancelada'))
                    return
        
        try:
            with transaction.atomic():
                # PASO 1: Migraciones
                if not skip_migrations:
                    self.stdout.write('\n▶️  PASO 1: Aplicando migraciones...')
                    self._aplicar_migraciones()
                    self.stdout.write(self.style.SUCCESS('✓ Migraciones aplicadas'))
                else:
                    self.stdout.write(self.style.WARNING('⊘ Migraciones omitidas'))
                
                # PASO 2: Reset de datos (si se solicita)
                if reset:
                    self.stdout.write('\n▶️  PASO 2: Borrando datos existentes...')
                    self._reset_datos()
                    self.stdout.write(self.style.WARNING('✓ Datos borrados'))
                
                # PASO 3: Crear centros
                self.stdout.write('\n▶️  PASO 3: Creando centros...')
                centros_creados = self._crear_centros(interactive)
                self.stdout.write(self.style.SUCCESS(f'✓ {centros_creados} centros configurados'))
                
                # PASO 4: Crear usuarios
                self.stdout.write('\n▶️  PASO 4: Creando usuarios...')
                usuarios_creados = self._crear_usuarios(interactive)
                self.stdout.write(self.style.SUCCESS(f'✓ {usuarios_creados} usuarios configurados'))
                
                # PASO 5: Verificar integridad
                self.stdout.write('\n▶️  PASO 5: Verificando integridad del sistema...')
                self._verificar()
                self.stdout.write(self.style.SUCCESS('✓ Integridad verificada'))
                
                # Resumen final
                self.stdout.write(self.style.SUCCESS('\n╔═══════════════════════════════════════╗'))
                self.stdout.write(self.style.SUCCESS('║        ✅ SETUP COMPLETADO EXITOSAMENTE        ║'))
                self.stdout.write(self.style.SUCCESS('╚═══════════════════════════════════════╝\n'))
                
                self._mostrar_resumen()
        
        except Exception as e:
            logger.exception(f"Error en setup: {str(e)}")
            self.stdout.write(self.style.ERROR(f'\n✗ ERROR: {str(e)}'))
            raise CommandError(f'Setup falló: {str(e)}')
    
    def _aplicar_migraciones(self):
        """Ejecuta migraciones pendientes de Django"""
        try:
            result = subprocess.run(
                [sys.executable, 'manage.py', 'migrate'],
                capture_output=True,
                text=True,
                check=True
            )
            self.stdout.write(f'  {result.stdout}')
        except subprocess.CalledProcessError as e:
            raise Exception(f"Migraciones fallaron: {e.stderr}")
    
    def _reset_datos(self):
        """Borra todos los datos del sistema (CUIDADO)"""
        self.stdout.write(self.style.WARNING('  ⚠️  Borrando usuarios...'))
        User.objects.all().delete()
        
        self.stdout.write(self.style.WARNING('  ⚠️  Borrando centros...'))
        Centro.objects.all().delete()
        
        self.stdout.write(self.style.WARNING('  ⚠️  Datos borrados'))
    
    def _crear_centros(self, interactive):
        """Crea centros predeterminados del sistema"""
        centros_default = [
            {
                'codigo': 'FARM001',
                'nombre': 'Farmacia Central Penitenciaria',
                'tipo': 'Farmacia Central',
                'activo': True
            },
            {
                'codigo': 'CERESO001',
                'nombre': 'Centro de Readaptación Social #1',
                'tipo': 'Centro Penitenciario',
                'activo': True
            },
            {
                'codigo': 'CERESO002',
                'nombre': 'Centro de Readaptación Social #2',
                'tipo': 'Centro Penitenciario',
                'activo': True
            },
            {
                'codigo': 'CERESO003',
                'nombre': 'Centro Femenil de Readaptación Social',
                'tipo': 'Centro Penitenciario Femenil',
                'activo': True
            },
        ]
        
        creados = 0
        for centro_data in centros_default:
            centro, es_nuevo = Centro.objects.get_or_create(
                codigo=centro_data['codigo'],
                defaults={
                    'nombre': centro_data['nombre'],
                    'tipo': centro_data.get('tipo', ''),
                    'activo': centro_data.get('activo', True)
                }
            )
            
            if es_nuevo:
                self.stdout.write(f'  ✓ Creado: {centro.nombre}')
                creados += 1
            else:
                self.stdout.write(f'  → Ya existe: {centro.nombre}')
        
        return creados
    
    def _crear_usuarios(self, interactive):
        """Crea usuarios de prueba para cada rol"""
        usuarios_default = [
            {
                'username': 'admin',
                'email': 'admin@farmacia.gob.mx',
                'password': 'Admin@123',
                'first_name': 'Administrador',
                'last_name': 'del Sistema',
                'is_superuser': True,
                'is_staff': True,
                'centro_codigo': 'FARM001',
                'role': 'admin_sistema'
            },
            {
                'username': 'farmacia_admin',
                'email': 'farmacia.admin@farmacia.gob.mx',
                'password': 'Farmacia@123',
                'first_name': 'Administrador',
                'last_name': 'de Farmacia',
                'is_staff': True,
                'centro_codigo': 'FARM001',
                'role': 'FARMACIA_ADMIN'
            },
            {
                'username': 'cereso1_user',
                'email': 'cereso1@farmacia.gob.mx',
                'password': 'Cereso1@123',
                'first_name': 'Usuario',
                'last_name': 'CERESO 1',
                'centro_codigo': 'CERESO001',
                'role': 'CENTRO_USER'
            },
            {
                'username': 'cereso2_user',
                'email': 'cereso2@farmacia.gob.mx',
                'password': 'Cereso2@123',
                'first_name': 'Usuario',
                'last_name': 'CERESO 2',
                'centro_codigo': 'CERESO002',
                'role': 'CENTRO_USER'
            },
        ]
        
        creados = 0
        for user_data in usuarios_default:
            username = user_data['username']
            centro_codigo = user_data.pop('centro_codigo')
            role = user_data.pop('role')
            password = user_data.pop('password')
            
            # Buscar centro
            try:
                centro = Centro.objects.get(codigo=centro_codigo)
            except Centro.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'  ⚠️  Centro {centro_codigo} no existe, saltando usuario {username}'))
                continue
            
            # Crear usuario
            usuario, es_nuevo = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': user_data.get('email', f'{username}@test.com'),
                    'first_name': user_data.get('first_name', ''),
                    'last_name': user_data.get('last_name', ''),
                    'is_superuser': user_data.get('is_superuser', False),
                    'is_staff': user_data.get('is_staff', False),
                    'centro': centro
                }
            )
            
            if es_nuevo:
                usuario.set_password(password)
                usuario.save()
                
                # Crear perfil
                UserProfile.objects.get_or_create(
                    user=usuario,
                    defaults={'role': role}
                )
                
                self.stdout.write(f'  ✓ Creado: {username} ({role}) - Password: {password}')
                creados += 1
            else:
                self.stdout.write(f'  → Ya existe: {username}')
        
        return creados
    
    def _verificar(self):
        """Verifica que el sistema esté correctamente configurado"""
        # Verificar centros
        centros_count = Centro.objects.count()
        if centros_count == 0:
            raise Exception("No hay centros creados")
        self.stdout.write(f'  ✓ Centros: {centros_count}')
        
        # Verificar usuarios
        usuarios_count = User.objects.count()
        if usuarios_count == 0:
            raise Exception("No hay usuarios creados")
        self.stdout.write(f'  ✓ Usuarios: {usuarios_count}')
        
        # Verificar superuser
        superusers_count = User.objects.filter(is_superuser=True).count()
        if superusers_count == 0:
            self.stdout.write(self.style.WARNING('  ⚠️  No hay superusuarios'))
        else:
            self.stdout.write(f'  ✓ Superusuarios: {superusers_count}')
        
        # Verificar farmacia
        farmacia_centro = Centro.objects.filter(codigo__icontains='FARM').first()
        if not farmacia_centro:
            self.stdout.write(self.style.WARNING('  ⚠️  No hay centro de farmacia'))
        else:
            self.stdout.write(f'  ✓ Farmacia: {farmacia_centro.nombre}')
    
    def _mostrar_resumen(self):
        """Muestra resumen de credenciales y próximos pasos"""
        self.stdout.write('\n📋 CREDENCIALES DE ACCESO:\n')
        
        credenciales = [
            ('admin', 'Admin@123', 'Superusuario'),
            ('farmacia_admin', 'Farmacia@123', 'Admin de Farmacia'),
            ('cereso1_user', 'Cereso1@123', 'Usuario CERESO 1'),
            ('cereso2_user', 'Cereso2@123', 'Usuario CERESO 2'),
        ]
        
        for username, password, rol in credenciales:
            if User.objects.filter(username=username).exists():
                self.stdout.write(f'  • {username:20s} | {password:20s} | {rol}')
        
        self.stdout.write('\n📝 PRÓXIMOS PASOS:\n')
        self.stdout.write('  1. Iniciar servidor: python manage.py runserver')
        self.stdout.write('  2. Acceder a: http://localhost:8000/admin/')
        self.stdout.write('  3. Ejecutar tests: python manage.py test core.tests')
        self.stdout.write('  4. Ver API: http://localhost:8000/api/')
        self.stdout.write('')
