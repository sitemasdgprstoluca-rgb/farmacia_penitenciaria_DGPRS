"""
ISS-006: Comando para actualizar estados de lotes caducados.

Este comando debe ejecutarse diariamente (cron/scheduler) para:
1. Marcar lotes vencidos como inactivos (activo=False)
2. Alertar sobre lotes próximos a vencer
3. Generar reporte de lotes críticos

Uso:
    python manage.py actualizar_caducidades
    python manage.py actualizar_caducidades --dry-run  # Solo mostrar, no modificar
    python manage.py actualizar_caducidades --dias-alerta=30  # Alertar 30 días antes
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'ISS-006: Actualiza estados de lotes caducados y genera alertas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar cambios sin aplicarlos'
        )
        parser.add_argument(
            '--dias-alerta',
            type=int,
            default=30,
            help='Días antes de caducidad para alertar (default: 30)'
        )
        parser.add_argument(
            '--dias-critico',
            type=int,
            default=7,
            help='Días antes de caducidad para alerta crítica (default: 7)'
        )

    def handle(self, *args, **options):
        from core.models import Lote
        
        dry_run = options['dry_run']
        dias_alerta = options['dias_alerta']
        dias_critico = options['dias_critico']
        
        hoy = timezone.now().date()
        fecha_alerta = hoy + timedelta(days=dias_alerta)
        fecha_critico = hoy + timedelta(days=dias_critico)
        
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"ISS-006: Actualización de caducidades de lotes")
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"Fecha actual: {hoy}")
        self.stdout.write(f"Modo: {'SIMULACIÓN (dry-run)' if dry_run else 'EJECUCIÓN REAL'}")
        self.stdout.write(f"Días alerta: {dias_alerta}, Días crítico: {dias_critico}\n")
        
        # 1. Lotes ya vencidos que aún están activos
        lotes_vencidos = Lote.objects.filter(
            fecha_caducidad__lt=hoy,
            activo=True,
            deleted_at__isnull=True
        ).select_related('producto', 'centro')
        
        self.stdout.write(self.style.ERROR(f"\n📛 LOTES VENCIDOS ({lotes_vencidos.count()}):"))
        
        if lotes_vencidos.exists():
            with transaction.atomic():
                for lote in lotes_vencidos:
                    dias_vencido = (hoy - lote.fecha_caducidad).days
                    centro_nombre = lote.centro.nombre if lote.centro else 'Farmacia Central'
                    
                    self.stdout.write(
                        f"  • {lote.numero_lote} - {lote.producto.clave} "
                        f"({centro_nombre}) - Venció hace {dias_vencido} días - "
                        f"Cantidad: {lote.cantidad_actual}"
                    )
                    
                    if not dry_run:
                        lote.activo = False
                        lote.save(update_fields=['activo', 'updated_at'])
                        logger.warning(
                            f"ISS-006: Lote {lote.numero_lote} marcado como vencido (activo=False) "
                            f"(producto: {lote.producto.clave}, centro: {centro_nombre})"
                        )
        else:
            self.stdout.write("  ✓ No hay lotes vencidos pendientes de actualizar")
        
        # 2. Lotes en estado crítico (próximos a vencer en menos de dias_critico)
        lotes_criticos = Lote.objects.filter(
            fecha_caducidad__gte=hoy,
            fecha_caducidad__lte=fecha_critico,
            activo=True,
            deleted_at__isnull=True
        ).select_related('producto', 'centro').order_by('fecha_caducidad')
        
        self.stdout.write(self.style.WARNING(f"\n⚠️  LOTES CRÍTICOS - Vencen en {dias_critico} días o menos ({lotes_criticos.count()}):"))
        
        if lotes_criticos.exists():
            for lote in lotes_criticos:
                dias_para_vencer = (lote.fecha_caducidad - hoy).days
                centro_nombre = lote.centro.nombre if lote.centro else 'Farmacia Central'
                
                self.stdout.write(
                    f"  • {lote.numero_lote} - {lote.producto.clave} "
                    f"({centro_nombre}) - Vence en {dias_para_vencer} días - "
                    f"Cantidad: {lote.cantidad_actual}"
                )
        else:
            self.stdout.write("  ✓ No hay lotes en estado crítico")
        
        # 3. Lotes próximos a vencer (entre dias_critico y dias_alerta)
        lotes_proximos = Lote.objects.filter(
            fecha_caducidad__gt=fecha_critico,
            fecha_caducidad__lte=fecha_alerta,
            activo=True,
            deleted_at__isnull=True
        ).select_related('producto', 'centro').order_by('fecha_caducidad')
        
        self.stdout.write(self.style.NOTICE(f"\n📅 LOTES PRÓXIMOS A VENCER - Vencen en {dias_alerta} días o menos ({lotes_proximos.count()}):"))
        
        if lotes_proximos.exists():
            for lote in lotes_proximos[:20]:  # Limitar a 20 para no saturar
                dias_para_vencer = (lote.fecha_caducidad - hoy).days
                centro_nombre = lote.centro.nombre if lote.centro else 'Farmacia Central'
                
                self.stdout.write(
                    f"  • {lote.numero_lote} - {lote.producto.clave} "
                    f"({centro_nombre}) - Vence en {dias_para_vencer} días - "
                    f"Cantidad: {lote.cantidad_actual}"
                )
            if lotes_proximos.count() > 20:
                self.stdout.write(f"  ... y {lotes_proximos.count() - 20} más")
        else:
            self.stdout.write("  ✓ No hay lotes próximos a vencer")
        
        # 4. Resumen estadístico
        total_disponibles = Lote.objects.filter(
            activo=True,
            deleted_at__isnull=True
        ).count()
        
        total_vencidos = Lote.objects.filter(
            activo=False,
            deleted_at__isnull=True
        ).count()
        
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write("📊 RESUMEN:")
        self.stdout.write(f"  • Lotes disponibles: {total_disponibles}")
        self.stdout.write(f"  • Lotes vencidos (total): {total_vencidos}")
        self.stdout.write(f"  • Lotes actualizados ahora: {lotes_vencidos.count() if not dry_run else 0}")
        self.stdout.write(f"  • Lotes en alerta crítica: {lotes_criticos.count()}")
        self.stdout.write(f"  • Lotes en alerta normal: {lotes_proximos.count()}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\n⚠️  MODO SIMULACIÓN: No se aplicaron cambios"))
        else:
            self.stdout.write(self.style.SUCCESS(f"\n✅ Proceso completado exitosamente"))
        
        self.stdout.write(f"{'='*60}\n")
