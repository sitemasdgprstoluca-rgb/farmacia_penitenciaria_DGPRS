# -*- coding: utf-8 -*-
"""
Comando para generar notificaciones de alertas de inventario.

Este comando debe ejecutarse periódicamente (cron/scheduler) para:
1. Notificar sobre productos con stock bajo
2. Notificar sobre lotes próximos a caducar
3. Notificar sobre lotes ya caducados

Las notificaciones se envían a usuarios con rol de farmacia/admin.

Uso:
    python manage.py generar_alertas_inventario
    python manage.py generar_alertas_inventario --dry-run
    python manage.py generar_alertas_inventario --dias-caducidad=30
    python manage.py generar_alertas_inventario --forzar  # Ignora notificaciones previas
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Sum, Q
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Genera notificaciones de alertas de inventario para farmacia'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar alertas sin crear notificaciones'
        )
        parser.add_argument(
            '--dias-caducidad',
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
        parser.add_argument(
            '--forzar',
            action='store_true',
            help='Crear notificaciones aunque ya existan similares recientes'
        )

    def handle(self, *args, **options):
        from core.models import Lote, Producto, User, Notificacion
        
        dry_run = options['dry_run']
        dias_caducidad = options['dias_caducidad']
        dias_critico = options['dias_critico']
        forzar = options['forzar']
        
        hoy = timezone.now().date()
        fecha_alerta = hoy + timedelta(days=dias_caducidad)
        fecha_critico = hoy + timedelta(days=dias_critico)
        
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write("GENERACIÓN DE ALERTAS DE INVENTARIO")
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"Fecha: {hoy}")
        self.stdout.write(f"Modo: {'SIMULACIÓN' if dry_run else 'REAL'}")
        self.stdout.write(f"Días caducidad: {dias_caducidad}, Crítico: {dias_critico}\n")
        
        # Obtener usuarios de farmacia para notificar
        usuarios_farmacia = User.objects.filter(
            rol__in=['farmacia', 'admin_sistema', 'admin_farmacia', 'superusuario', 'FARMACIA', 'ADMIN'],
            is_active=True
        )
        
        if not usuarios_farmacia.exists():
            self.stdout.write(self.style.WARNING("⚠️  No hay usuarios de farmacia para notificar"))
            return
        
        self.stdout.write(f"Usuarios a notificar: {usuarios_farmacia.count()}\n")
        
        notificaciones_creadas = 0
        
        # ====================================================================
        # 1. ALERTAS DE STOCK BAJO
        # ====================================================================
        self.stdout.write(self.style.WARNING("\n📦 VERIFICANDO STOCK BAJO..."))
        
        # Productos con stock actual menor al mínimo
        productos_stock_bajo = []
        productos = Producto.objects.filter(activo=True, stock_minimo__gt=0)
        
        for producto in productos:
            # Calcular stock total de lotes activos
            stock_total = Lote.objects.filter(
                producto=producto,
                activo=True,
                fecha_caducidad__gte=hoy  # Solo lotes no vencidos
            ).aggregate(total=Sum('cantidad_actual'))['total'] or 0
            
            if stock_total < producto.stock_minimo:
                productos_stock_bajo.append({
                    'producto': producto,
                    'stock_actual': stock_total,
                    'stock_minimo': producto.stock_minimo,
                    'diferencia': producto.stock_minimo - stock_total
                })
        
        self.stdout.write(f"  Productos con stock bajo: {len(productos_stock_bajo)}")
        
        if productos_stock_bajo and not dry_run:
            # Crear notificación agrupada de stock bajo
            productos_texto = "\n".join([
                f"• {p['producto'].clave} - {p['producto'].nombre}: {p['stock_actual']}/{p['stock_minimo']}"
                for p in productos_stock_bajo[:10]  # Limitar a 10 en el mensaje
            ])
            
            if len(productos_stock_bajo) > 10:
                productos_texto += f"\n... y {len(productos_stock_bajo) - 10} más"
            
            for usuario in usuarios_farmacia:
                # Verificar si ya existe notificación reciente (últimas 24h)
                if not forzar:
                    existe = Notificacion.objects.filter(
                        usuario=usuario,
                        tipo='warning',
                        titulo__icontains='Stock Bajo',
                        created_at__gte=timezone.now() - timedelta(hours=24)
                    ).exists()
                    if existe:
                        continue
                
                try:
                    Notificacion.objects.create(
                        usuario=usuario,
                        tipo='warning',
                        titulo=f'⚠️ Alerta: {len(productos_stock_bajo)} Productos con Stock Bajo',
                        mensaje=f'Los siguientes productos tienen stock por debajo del mínimo:\n\n{productos_texto}',
                        datos={
                            'tipo_alerta': 'stock_bajo',
                            'cantidad_productos': len(productos_stock_bajo),
                            'productos': [p['producto'].clave for p in productos_stock_bajo[:20]]
                        },
                        url='/productos?filtro=stock_bajo'
                    )
                    notificaciones_creadas += 1
                except Exception as e:
                    logger.error(f"Error creando notificación stock bajo: {e}")
        
        # ====================================================================
        # 2. ALERTAS DE LOTES PRÓXIMOS A CADUCAR
        # ====================================================================
        self.stdout.write(self.style.WARNING("\n📅 VERIFICANDO CADUCIDADES..."))
        
        # Lotes críticos (vencen en dias_critico o menos)
        lotes_criticos = Lote.objects.filter(
            activo=True,
            cantidad_actual__gt=0,
            fecha_caducidad__gte=hoy,
            fecha_caducidad__lte=fecha_critico
        ).select_related('producto', 'centro').order_by('fecha_caducidad')
        
        self.stdout.write(f"  Lotes críticos (≤{dias_critico} días): {lotes_criticos.count()}")
        
        if lotes_criticos.exists() and not dry_run:
            lotes_texto = "\n".join([
                f"• {l.numero_lote} ({l.producto.clave}): Vence {l.fecha_caducidad.strftime('%d/%m/%Y')} - Cant: {l.cantidad_actual}"
                for l in lotes_criticos[:10]
            ])
            
            if lotes_criticos.count() > 10:
                lotes_texto += f"\n... y {lotes_criticos.count() - 10} más"
            
            for usuario in usuarios_farmacia:
                if not forzar:
                    existe = Notificacion.objects.filter(
                        usuario=usuario,
                        tipo='error',
                        titulo__icontains='Caducidad Crítica',
                        created_at__gte=timezone.now() - timedelta(hours=24)
                    ).exists()
                    if existe:
                        continue
                
                try:
                    Notificacion.objects.create(
                        usuario=usuario,
                        tipo='error',
                        titulo=f'🚨 CRÍTICO: {lotes_criticos.count()} Lotes por Caducar en {dias_critico} días',
                        mensaje=f'Los siguientes lotes caducan pronto y requieren atención URGENTE:\n\n{lotes_texto}',
                        datos={
                            'tipo_alerta': 'caducidad_critica',
                            'cantidad_lotes': lotes_criticos.count(),
                            'lotes': [l.numero_lote for l in lotes_criticos[:20]]
                        },
                        url='/lotes?filtro=por_caducar'
                    )
                    notificaciones_creadas += 1
                except Exception as e:
                    logger.error(f"Error creando notificación caducidad crítica: {e}")
        
        # Lotes próximos a caducar (entre dias_critico y dias_caducidad)
        lotes_proximos = Lote.objects.filter(
            activo=True,
            cantidad_actual__gt=0,
            fecha_caducidad__gt=fecha_critico,
            fecha_caducidad__lte=fecha_alerta
        ).select_related('producto', 'centro').order_by('fecha_caducidad')
        
        self.stdout.write(f"  Lotes próximos (≤{dias_caducidad} días): {lotes_proximos.count()}")
        
        if lotes_proximos.exists() and not dry_run:
            lotes_texto = "\n".join([
                f"• {l.numero_lote} ({l.producto.clave}): Vence {l.fecha_caducidad.strftime('%d/%m/%Y')} - Cant: {l.cantidad_actual}"
                for l in lotes_proximos[:10]
            ])
            
            if lotes_proximos.count() > 10:
                lotes_texto += f"\n... y {lotes_proximos.count() - 10} más"
            
            for usuario in usuarios_farmacia:
                if not forzar:
                    existe = Notificacion.objects.filter(
                        usuario=usuario,
                        tipo='warning',
                        titulo__icontains='Próximos a Caducar',
                        created_at__gte=timezone.now() - timedelta(hours=24)
                    ).exists()
                    if existe:
                        continue
                
                try:
                    Notificacion.objects.create(
                        usuario=usuario,
                        tipo='warning',
                        titulo=f'⚠️ Alerta: {lotes_proximos.count()} Lotes Próximos a Caducar',
                        mensaje=f'Los siguientes lotes vencen en los próximos {dias_caducidad} días:\n\n{lotes_texto}',
                        datos={
                            'tipo_alerta': 'caducidad_proxima',
                            'cantidad_lotes': lotes_proximos.count(),
                            'lotes': [l.numero_lote for l in lotes_proximos[:20]]
                        },
                        url='/lotes?filtro=por_caducar'
                    )
                    notificaciones_creadas += 1
                except Exception as e:
                    logger.error(f"Error creando notificación caducidad próxima: {e}")
        
        # ====================================================================
        # 3. ALERTAS DE LOTES YA CADUCADOS (pero con stock)
        # ====================================================================
        lotes_caducados = Lote.objects.filter(
            cantidad_actual__gt=0,
            fecha_caducidad__lt=hoy
        ).select_related('producto', 'centro')
        
        self.stdout.write(f"  Lotes caducados con stock: {lotes_caducados.count()}")
        
        if lotes_caducados.exists() and not dry_run:
            lotes_texto = "\n".join([
                f"• {l.numero_lote} ({l.producto.clave}): Venció {l.fecha_caducidad.strftime('%d/%m/%Y')} - Cant: {l.cantidad_actual}"
                for l in lotes_caducados[:10]
            ])
            
            if lotes_caducados.count() > 10:
                lotes_texto += f"\n... y {lotes_caducados.count() - 10} más"
            
            for usuario in usuarios_farmacia:
                if not forzar:
                    existe = Notificacion.objects.filter(
                        usuario=usuario,
                        tipo='error',
                        titulo__icontains='Lotes Caducados',
                        created_at__gte=timezone.now() - timedelta(hours=24)
                    ).exists()
                    if existe:
                        continue
                
                try:
                    Notificacion.objects.create(
                        usuario=usuario,
                        tipo='error',
                        titulo=f'🚫 URGENTE: {lotes_caducados.count()} Lotes CADUCADOS con Stock',
                        mensaje=f'Los siguientes lotes están CADUCADOS y deben retirarse del inventario:\n\n{lotes_texto}',
                        datos={
                            'tipo_alerta': 'caducados',
                            'cantidad_lotes': lotes_caducados.count(),
                            'lotes': [l.numero_lote for l in lotes_caducados[:20]]
                        },
                        url='/lotes?filtro=caducados'
                    )
                    notificaciones_creadas += 1
                except Exception as e:
                    logger.error(f"Error creando notificación lotes caducados: {e}")
        
        # ====================================================================
        # RESUMEN
        # ====================================================================
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write("📊 RESUMEN:")
        self.stdout.write(f"  • Productos con stock bajo: {len(productos_stock_bajo)}")
        self.stdout.write(f"  • Lotes críticos: {lotes_criticos.count()}")
        self.stdout.write(f"  • Lotes próximos a caducar: {lotes_proximos.count()}")
        self.stdout.write(f"  • Lotes caducados con stock: {lotes_caducados.count()}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f"\n⚠️  MODO SIMULACIÓN: No se crearon notificaciones"))
        else:
            self.stdout.write(self.style.SUCCESS(f"\n✅ Notificaciones creadas: {notificaciones_creadas}"))
        
        self.stdout.write(f"{'='*60}\n")
