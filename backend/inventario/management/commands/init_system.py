import os
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth import get_user_model
from pathlib import Path

class Command(BaseCommand):
    help = 'Inicializa el sistema: crea BD, migraciones y usuario admin'

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("🚀 INICIANDO SISTEMA"))
        self.stdout.write("=" * 60)
        
        # Verificar BD
        db_path = Path(__file__).resolve().parent.parent.parent.parent.parent / 'db.sqlite3'
        
        if not db_path.exists():
            self.stdout.write(self.style.WARNING(f"⚠️  Creando base de datos: {db_path}"))
        
        # Crear migraciones en ORDEN para evitar dependencia circular
        self.stdout.write("\n📝 Creando migraciones...")
        
        try:
            # Primero core
            call_command('makemigrations', 'core', verbosity=0)
            self.stdout.write(self.style.SUCCESS("✅ Migraciones de 'core' creadas"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"ℹ️  core: {e}"))
        
        try:
            # Luego inventario
            call_command('makemigrations', 'inventario', verbosity=0)
            self.stdout.write(self.style.SUCCESS("✅ Migraciones de 'inventario' creadas"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"ℹ️  inventario: {e}"))
        
        # Aplicar migraciones
        self.stdout.write("\n🔧 Aplicando migraciones...")
        try:
            call_command('migrate', verbosity=0)
            self.stdout.write(self.style.SUCCESS("✅ Migraciones aplicadas"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error al migrar: {e}"))
            self.stdout.write(self.style.WARNING("\n💡 Ejecuta: python fix_migrations.py"))
            return
        
        # Crear admin
        self.stdout.write("\n👤 Verificando usuario admin...")
        User = get_user_model()
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            self.stdout.write(self.style.SUCCESS("✅ Usuario admin creado (admin/admin123)"))
        else:
            self.stdout.write(self.style.WARNING("ℹ️  Usuario admin ya existe"))
        
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("✅ SISTEMA LISTO"))
        self.stdout.write("=" * 60)
