from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Crea el superusuario super_admin automáticamente'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('========================================'))
        self.stdout.write(self.style.SUCCESS('Creando Superusuario'))
        self.stdout.write(self.style.SUCCESS('========================================\n'))

        username = 'super_admin'
        email = 'admin@edomex.gob.mx'
        password = '123456789'

        # Verificar si ya existe
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'⚠ El usuario "{username}" ya existe.'))
            
            # Actualizar contraseña
            user = User.objects.get(username=username)
            user.set_password(password)
            user.is_superuser = True
            user.is_staff = True
            user.save()
            
            self.stdout.write(self.style.SUCCESS(f'✓ Contraseña actualizada para: {username}\n'))
        else:
            # Crear nuevo superusuario
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            user.first_name = 'Super'
            user.last_name = 'Administrador'
            user.save()
            
            self.stdout.write(self.style.SUCCESS(f'✓ Superusuario creado exitosamente!\n'))

        # Mostrar credenciales
        self.stdout.write(self.style.SUCCESS('========================================'))
        self.stdout.write(self.style.SUCCESS('CREDENCIALES DE ACCESO:'))
        self.stdout.write(self.style.SUCCESS('========================================'))
        self.stdout.write(f'Usuario:    {username}')
        self.stdout.write(f'Contraseña: {password}')
        self.stdout.write(f'Email:      {email}')
        self.stdout.write(self.style.SUCCESS('========================================\n'))
        
        self.stdout.write(self.style.SUCCESS('Accede al sistema en:'))
        self.stdout.write('  Frontend:     http://localhost:5173')
        self.stdout.write('  Django Admin: http://localhost:8000/admin\n')
