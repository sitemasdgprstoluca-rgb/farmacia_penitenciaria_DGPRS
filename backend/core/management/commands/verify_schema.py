"""
ISS-001/003 FIX (audit22): Comando de verificación de esquema BD.

Este comando valida que el esquema de BD esté alineado con los modelos Django
antes de despliegues o al iniciar el servidor.

USO:
    python manage.py verify_schema
    python manage.py verify_schema --strict  # Falla si hay discrepancias
    python manage.py verify_schema --sql     # Genera SQL para constraints
"""
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import sys


class Command(BaseCommand):
    help = 'Verifica que el esquema de BD esté alineado con los modelos Django (managed=False)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--strict',
            action='store_true',
            help='Falla con exit code 1 si hay columnas críticas faltantes',
        )
        parser.add_argument(
            '--sql',
            action='store_true',
            help='Genera SQL para aplicar constraints recomendados',
        )
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Solo mostrar errores',
        )
    
    def handle(self, *args, **options):
        from scripts.verify_schema import (
            verificar_esquema,
            verificar_columnas_criticas,
            verificar_constraints,
            generar_sql_constraints,
        )
        
        verbose = not options['quiet']
        strict = options['strict']
        show_sql = options['sql']
        
        # Verificar que no sea SQLite
        engine = settings.DATABASES.get('default', {}).get('ENGINE', '')
        if 'sqlite' in engine:
            self.stdout.write(self.style.WARNING(
                'SQLite detectado - Verificación de esquema omitida'
            ))
            return
        
        if show_sql:
            self.stdout.write(generar_sql_constraints())
            return
        
        if verbose:
            self.stdout.write("=" * 60)
            self.stdout.write("ISS-001/003: Verificación de esquema BD")
            self.stdout.write("=" * 60)
        
        # 1. Verificar columnas críticas
        if verbose:
            self.stdout.write("\n--- Columnas críticas ---")
        
        faltantes_cols = verificar_columnas_criticas(verbose=verbose)
        
        # 2. Verificar constraints (solo informativo)
        if verbose:
            self.stdout.write("\n--- Constraints recomendados ---")
        
        faltantes_cons = verificar_constraints(verbose=verbose)
        
        # 3. Resumen
        if verbose:
            self.stdout.write("\n" + "=" * 60)
        
        if faltantes_cols:
            msg = f"CRÍTICO: Columnas faltantes: {faltantes_cols}"
            self.stdout.write(self.style.ERROR(msg))
            
            if strict:
                raise CommandError(
                    "Esquema de BD incompleto. Aplicar migraciones SQL antes de continuar."
                )
        else:
            self.stdout.write(self.style.SUCCESS(
                "✅ Todas las columnas críticas presentes"
            ))
        
        if faltantes_cons:
            self.stdout.write(self.style.WARNING(
                f"⚠️  Constraints recomendados faltantes: {list(faltantes_cons.keys())}"
            ))
            self.stdout.write(self.style.WARNING(
                "   Ejecutar: python manage.py verify_schema --sql"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "✅ Constraints de integridad presentes"
            ))
