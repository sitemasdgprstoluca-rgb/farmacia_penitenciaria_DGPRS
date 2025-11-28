from django.core.management.base import BaseCommand
from core.models import User
from django.contrib.auth.hashers import make_password


class Command(BaseCommand):
    help = 'Resetea la contraseña del admin a admin123'

    def handle(self, *args, **options):
        try:
            admin = User.objects.get(username='admin')
            admin.password = make_password('admin123')
            admin.save()
            
            self.stdout.write(self.style.SUCCESS(
                f'✓ Contraseña reseteada para: {admin.username}'
            ))
            self.stdout.write(f'  Email: {admin.email}')
            self.stdout.write(f'  Nueva contraseña: admin123')
            
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('Usuario admin no encontrado'))
