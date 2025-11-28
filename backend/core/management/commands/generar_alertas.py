"""
Management command para generar notificaciones de alertas del sistema.

Ejecutar manualmente:
    python manage.py generar_alertas

Ejecutar vía cron (recomendado diariamente):
    0 8 * * * cd /path/to/backend && python manage.py generar_alertas

Opciones:
    --stock-critico     Solo alertas de stock crítico
    --caducidad         Solo alertas de caducidad
    --vencidos          Solo alertas de lotes vencidos
    --dias N            Días de anticipación para caducidad (default: 30)
"""
from django.core.management.base import BaseCommand
from core.utils.notification_service import NotificationService


class Command(BaseCommand):
    help = 'Genera notificaciones de alertas del sistema (stock crítico, caducidad, vencidos)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--stock-critico',
            action='store_true',
            help='Solo generar alertas de stock crítico'
        )
        parser.add_argument(
            '--caducidad',
            action='store_true',
            help='Solo generar alertas de lotes por caducar'
        )
        parser.add_argument(
            '--vencidos',
            action='store_true',
            help='Solo generar alertas de lotes vencidos'
        )
        parser.add_argument(
            '--dias',
            type=int,
            default=30,
            help='Días de anticipación para alertas de caducidad (default: 30)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Generando alertas del sistema...'))
        
        # Si no se especifica ninguna opción, ejecutar todas
        ejecutar_todas = not any([
            options['stock_critico'],
            options['caducidad'],
            options['vencidos']
        ])
        
        resultados = {}
        
        if ejecutar_todas or options['stock_critico']:
            self.stdout.write('  → Verificando stock crítico...')
            resultados['stock_critico'] = NotificationService.notificar_stock_critico()
            self.stdout.write(f'    Creadas: {resultados["stock_critico"]}')
        
        if ejecutar_todas or options['caducidad']:
            dias = options['dias']
            self.stdout.write(f'  → Verificando lotes por caducar ({dias} días)...')
            resultados['por_caducar'] = NotificationService.notificar_lotes_por_caducar(dias)
            self.stdout.write(f'    Creadas: {resultados["por_caducar"]}')
        
        if ejecutar_todas or options['vencidos']:
            self.stdout.write('  → Verificando lotes vencidos...')
            resultados['vencidos'] = NotificationService.notificar_lotes_vencidos()
            self.stdout.write(f'    Creadas: {resultados["vencidos"]}')
        
        total = sum(resultados.values())
        
        if total > 0:
            self.stdout.write(self.style.SUCCESS(f'✓ Total de notificaciones creadas: {total}'))
        else:
            self.stdout.write(self.style.SUCCESS('✓ No hay nuevas alertas que notificar'))
        
        return str(total)
