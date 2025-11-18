from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.db import IntegrityError


class Command(BaseCommand):
    help = 'Crea usuarios de prueba con sus respectivos roles'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('========================================'))
        self.stdout.write(self.style.SUCCESS('Creando Usuarios de Prueba'))
        self.stdout.write(self.style.SUCCESS('========================================\n'))

        # Verificar que existan los grupos
        try:
            farmacia_admin = Group.objects.get(name='FARMACIA_ADMIN')
            centro_user = Group.objects.get(name='CENTRO_USER')
            vista_user = Group.objects.get(name='VISTA_USER')
        except Group.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                'Los grupos no existen. Ejecuta primero: python manage.py setup_permissions'
            ))
            return

        users_to_create = [
            {
                'username': 'admin_farmacia',
                'email': 'farmacia@edomex.gob.mx',
                'password': 'Farmacia2024!',
                'first_name': 'Administrador',
                'last_name': 'Farmacia',
                'group': farmacia_admin,
                'description': 'Administrador de Farmacia - Acceso completo al inventario'
            },
            {
                'username': 'centro_cereso01',
                'email': 'cereso01@edomex.gob.mx',
                'password': 'Cereso2024!',
                'first_name': 'Usuario',
                'last_name': 'CERESO-01',
                'group': centro_user,
                'description': 'Usuario Centro CERESO-01 - Puede crear requisiciones'
            },
            {
                'username': 'centro_cereso02',
                'email': 'cereso02@edomex.gob.mx',
                'password': 'Cereso2024!',
                'first_name': 'Usuario',
                'last_name': 'CERESO-02',
                'group': centro_user,
                'description': 'Usuario Centro CERESO-02 - Puede crear requisiciones'
            },
            {
                'username': 'vista_reportes',
                'email': 'reportes@edomex.gob.mx',
                'password': 'Vista2024!',
                'first_name': 'Consulta',
                'last_name': 'Reportes',
                'group': vista_user,
                'description': 'Usuario de Vista - Solo lectura en reportes y trazabilidad'
            },
        ]

        created_count = 0
        existing_count = 0

        for user_data in users_to_create:
            try:
                user = User.objects.create_user(
                    username=user_data['username'],
                    email=user_data['email'],
                    password=user_data['password'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name']
                )
                user.groups.add(user_data['group'])
                user.save()

                self.stdout.write(self.style.SUCCESS(f'✓ Usuario creado: {user_data["username"]}'))
                self.stdout.write(f'  Email: {user_data["email"]}')
                self.stdout.write(f'  Contraseña: {user_data["password"]}')
                self.stdout.write(f'  Rol: {user_data["group"].name}')
                self.stdout.write(f'  Descripción: {user_data["description"]}\n')
                created_count += 1

            except IntegrityError:
                self.stdout.write(self.style.WARNING(f'⚠ Usuario ya existe: {user_data["username"]}\n'))
                existing_count += 1

        self.stdout.write(self.style.SUCCESS('========================================'))
        self.stdout.write(self.style.SUCCESS(f'Resumen:'))
        self.stdout.write(self.style.SUCCESS(f'  Usuarios creados: {created_count}'))
        self.stdout.write(self.style.WARNING(f'  Usuarios existentes: {existing_count}'))
        self.stdout.write(self.style.SUCCESS('========================================\n'))

        if created_count > 0:
            self.stdout.write(self.style.SUCCESS('CREDENCIALES DE ACCESO:\n'))
            self.stdout.write('1. SUPERUSUARIO (si lo creaste):')
            self.stdout.write('   Usuario: admin')
            self.stdout.write('   Contraseña: [la que definiste]\n')

            self.stdout.write('2. ADMINISTRADOR FARMACIA:')
            self.stdout.write('   Usuario: admin_farmacia')
            self.stdout.write('   Contraseña: Farmacia2024!')
            self.stdout.write('   Rol: Gestión completa del sistema\n')

            self.stdout.write('3. USUARIO CENTRO 1:')
            self.stdout.write('   Usuario: centro_cereso01')
            self.stdout.write('   Contraseña: Cereso2024!')
            self.stdout.write('   Rol: Crear y enviar requisiciones\n')

            self.stdout.write('4. USUARIO CENTRO 2:')
            self.stdout.write('   Usuario: centro_cereso02')
            self.stdout.write('   Contraseña: Cereso2024!')
            self.stdout.write('   Rol: Crear y enviar requisiciones\n')

            self.stdout.write('5. USUARIO VISTA:')
            self.stdout.write('   Usuario: vista_reportes')
            self.stdout.write('   Contraseña: Vista2024!')
            self.stdout.write('   Rol: Solo lectura (reportes y consultas)\n')

            self.stdout.write(self.style.SUCCESS('Ahora puedes iniciar sesión en: http://localhost:5173'))
