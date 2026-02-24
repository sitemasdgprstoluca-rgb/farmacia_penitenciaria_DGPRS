"""
Comando para sincronizar fecha_fabricacion de lotes existentes.

Para lotes que tienen parcialidades pero no tienen fecha_fabricacion,
copia la fecha de la primera parcialidad al campo fecha_fabricacion.

EJECUCIÓN EN RENDER:
    python manage.py sincronizar_fechas_lotes

OPCIONES:
    --dry-run     Solo mostrar qué se actualizaría, sin hacer cambios
    --all         Actualizar TODOS los lotes (incluso si ya tienen fecha)
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import Lote, LoteParcialidad


class Command(BaseCommand):
    help = 'Sincroniza fecha_fabricacion de lotes usando sus parcialidades'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar qué se actualizaría, sin hacer cambios',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Actualizar TODOS los lotes (incluso si ya tienen fecha)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        actualizar_todos = options['all']

        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS(
            "SINCRONIZAR: fecha_fabricacion desde parcialidades"
        ))
        self.stdout.write("=" * 60)

        if dry_run:
            self.stdout.write(self.style.WARNING("\n⚠️  MODO DRY-RUN: No se aplicarán cambios\n"))

        # Filtrar lotes según opciones
        if actualizar_todos:
            lotes = Lote.objects.filter(activo=True).select_related('producto')
            self.stdout.write(f"\nModo: Actualizar TODOS los lotes activos")
        else:
            lotes = Lote.objects.filter(
                fecha_fabricacion__isnull=True,
                activo=True
            ).select_related('producto')
            self.stdout.write(f"\nModo: Solo lotes SIN fecha_fabricacion")

        total = lotes.count()
        self.stdout.write(f"Lotes a procesar: {total}")

        if total == 0:
            self.stdout.write(self.style.SUCCESS(
                "\n✓ No hay lotes que necesiten actualización"
            ))
            return

        actualizados = 0
        sin_parcialidad = 0
        errores = 0

        with transaction.atomic():
            for lote in lotes:
                try:
                    # Buscar la primera parcialidad del lote
                    parcialidad = LoteParcialidad.objects.filter(
                        lote=lote
                    ).order_by('fecha_entrega').first()

                    if parcialidad and parcialidad.fecha_entrega:
                        nueva_fecha = parcialidad.fecha_entrega
                        fecha_anterior = lote.fecha_fabricacion

                        if dry_run:
                            self.stdout.write(
                                f"  [DRY-RUN] {lote.numero_lote}: "
                                f"{fecha_anterior} → {nueva_fecha}"
                            )
                        else:
                            lote.fecha_fabricacion = nueva_fecha
                            lote.save(update_fields=['fecha_fabricacion'])
                            self.stdout.write(
                                f"  ✓ {lote.numero_lote}: {nueva_fecha}"
                            )
                        actualizados += 1
                    else:
                        # Lote sin parcialidades - usar fecha actual como fallback
                        if not dry_run and lote.fecha_fabricacion is None:
                            lote.fecha_fabricacion = timezone.now().date()
                            lote.save(update_fields=['fecha_fabricacion'])
                            self.stdout.write(self.style.WARNING(
                                f"  ⚠️ {lote.numero_lote}: Sin parcialidades, "
                                f"usando fecha actual"
                            ))
                        sin_parcialidad += 1

                except Exception as e:
                    errores += 1
                    self.stdout.write(self.style.ERROR(
                        f"  ✗ Error en {lote.numero_lote}: {e}"
                    ))

            if dry_run:
                # En dry-run, revertir la transacción
                transaction.set_rollback(True)

        # Resumen final
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("RESUMEN:"))
        self.stdout.write(f"  • Lotes actualizados: {actualizados}")
        self.stdout.write(f"  • Sin parcialidades: {sin_parcialidad}")
        if errores:
            self.stdout.write(self.style.ERROR(f"  • Errores: {errores}"))
        
        if dry_run:
            self.stdout.write(self.style.WARNING(
                "\n⚠️ MODO DRY-RUN: No se aplicaron cambios"
            ))
            self.stdout.write(
                "Ejecuta sin --dry-run para aplicar los cambios"
            )
        else:
            self.stdout.write(self.style.SUCCESS("\n✓ Sincronización completada"))
