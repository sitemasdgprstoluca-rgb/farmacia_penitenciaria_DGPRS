"""
FLUJO V2: Comando de Django para verificar requisiciones vencidas

Uso:
    python manage.py verificar_vencidas
    python manage.py verificar_vencidas --dry-run  # Solo reportar sin cambios
    
Configura como cron job:
    0 0 * * * cd /path/to/backend && python manage.py verificar_vencidas >> /var/log/vencidas.log 2>&1
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from inventario.models import Requisicion, HistorialEstadoRequisicion


class Command(BaseCommand):
    help = 'Verifica y marca como vencidas las requisiciones con fecha límite pasada'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar lo que se haría sin hacer cambios',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        ahora = timezone.now()
        
        self.stdout.write(f"[{ahora}] Verificando requisiciones vencidas...")
        
        # Buscar requisiciones surtidas con fecha límite vencida
        requisiciones_vencidas = Requisicion.objects.filter(
            estado='surtida',
            fecha_recoleccion_limite__isnull=False,
            fecha_recoleccion_limite__lt=ahora
        )
        
        total = requisiciones_vencidas.count()
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS('No hay requisiciones vencidas'))
            return
        
        self.stdout.write(f"Encontradas: {total} requisición(es) con fecha límite vencida")
        
        if dry_run:
            self.stdout.write(self.style.WARNING('MODO DRY-RUN: No se harán cambios'))
            for req in requisiciones_vencidas:
                self.stdout.write(f"  - {req.folio}: límite {req.fecha_recoleccion_limite}")
            return
        
        marcadas = 0
        errores = 0
        
        for req in requisiciones_vencidas:
            try:
                with transaction.atomic():
                    estado_anterior = req.estado
                    req.estado = 'vencida'
                    req.motivo_vencimiento = (
                        f"Fecha límite de recolección vencida: {req.fecha_recoleccion_limite}"
                    )
                    req.save()
                    
                    # Registrar en historial
                    HistorialEstadoRequisicion.objects.create(
                        requisicion=req,
                        estado_anterior=estado_anterior,
                        estado_nuevo='vencida',
                        accion='marcar_vencida',
                        motivo=req.motivo_vencimiento,
                        usuario=None  # Acción automática del sistema
                    )
                    
                    marcadas += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✓ {req.folio} marcada como vencida")
                    )
                    
            except Exception as e:
                errores += 1
                self.stdout.write(
                    self.style.ERROR(f"  ✗ Error en {req.folio}: {str(e)}")
                )
        
        self.stdout.write('')
        self.stdout.write(f"Resumen: {marcadas}/{total} marcadas, {errores} errores")
        
        if errores > 0:
            self.stdout.write(self.style.ERROR('Completado con errores'))
        else:
            self.stdout.write(self.style.SUCCESS('Completado exitosamente'))
