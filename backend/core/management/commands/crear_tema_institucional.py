"""
Comando para crear el tema institucional por defecto.
Este tema se usa como base para la personalización del sistema.
"""

from django.core.management.base import BaseCommand
from core.models import TemaGlobal


class Command(BaseCommand):
    help = 'Crea el tema institucional por defecto si no existe'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar recreación del tema institucional (elimina el existente)',
        )
    
    def handle(self, *args, **options):
        force = options.get('force', False)
        
        # Verificar si ya existe un tema institucional
        tema_existente = TemaGlobal.objects.filter(es_tema_institucional=True).first()
        
        if tema_existente:
            if force:
                self.stdout.write(
                    self.style.WARNING(f'Eliminando tema institucional existente: {tema_existente.nombre}')
                )
                tema_existente.delete()
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'Ya existe un tema institucional: {tema_existente.nombre}')
                )
                self.stdout.write(
                    self.style.NOTICE('Use --force para recrearlo')
                )
                return
        
        # Crear tema institucional
        tema = TemaGlobal.crear_tema_institucional()
        
        self.stdout.write(
            self.style.SUCCESS(f'Tema institucional creado: {tema.nombre}')
        )
        self.stdout.write(f'  - ID: {tema.id}')
        self.stdout.write(f'  - Color primario: {tema.color_primario}')
        self.stdout.write(f'  - Color secundario: {tema.color_secundario}')
        self.stdout.write(f'  - Fuente principal: {tema.fuente_principal}')
        self.stdout.write(f'  - Activo: {tema.activo}')
