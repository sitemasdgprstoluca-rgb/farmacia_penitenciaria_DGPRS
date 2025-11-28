"""
Servicio de notificaciones automáticas.

Genera notificaciones para:
- Stock crítico de productos
- Lotes próximos a caducar
- Lotes vencidos
- Fallos de importación

Uso:
    from core.utils.notification_service import NotificationService
    
    # En una tarea programada o management command:
    NotificationService.notificar_stock_critico()
    NotificationService.notificar_lotes_por_caducar()
"""
import logging
from datetime import date, timedelta
from django.db.models import Sum, Q
from django.conf import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Servicio centralizado para generación de notificaciones."""
    
    @staticmethod
    def _get_usuarios_farmacia():
        """Obtiene usuarios con rol farmacia/admin que deben recibir alertas."""
        from core.models import User
        return User.objects.filter(
            Q(rol__in=['admin_sistema', 'superusuario', 'farmacia', 'admin_farmacia']) |
            Q(is_superuser=True),
            is_active=True,
            activo=True
        )
    
    @staticmethod
    def _crear_notificacion(usuario, titulo, mensaje, tipo='warning', requisicion=None):
        """Crea una notificación evitando duplicados recientes."""
        from core.models import Notificacion
        from django.utils import timezone
        
        # Evitar duplicados: no crear si ya existe una igual en las últimas 24h
        ayer = timezone.now() - timedelta(hours=24)
        existe = Notificacion.objects.filter(
            usuario=usuario,
            titulo=titulo,
            fecha_creacion__gte=ayer
        ).exists()
        
        if existe:
            logger.debug(f"Notificación duplicada omitida: {titulo} para {usuario.username}")
            return None
        
        try:
            notif = Notificacion.objects.create(
                usuario=usuario,
                titulo=titulo,
                mensaje=mensaje,
                tipo=tipo,
                requisicion=requisicion
            )
            logger.info(f"Notificación creada: {titulo} para {usuario.username}")
            return notif
        except Exception as e:
            logger.error(f"Error creando notificación: {e}")
            return None
    
    @classmethod
    def notificar_stock_critico(cls):
        """
        Genera notificaciones para productos con stock por debajo del mínimo.
        Solo notifica a usuarios farmacia/admin.
        
        Returns:
            int: Número de notificaciones creadas
        """
        from core.models import Producto, Lote
        
        usuarios = cls._get_usuarios_farmacia()
        if not usuarios.exists():
            logger.warning("No hay usuarios farmacia/admin para notificar stock crítico")
            return 0
        
        creadas = 0
        productos = Producto.objects.filter(activo=True)
        
        for producto in productos:
            stock_actual = Lote.objects.filter(
                producto=producto,
                deleted_at__isnull=True,
                estado='disponible'
            ).aggregate(total=Sum('cantidad_actual'))['total'] or 0
            
            if stock_actual < producto.stock_minimo:
                diferencia = producto.stock_minimo - stock_actual
                nivel = 'CRÍTICO' if stock_actual == 0 else 'BAJO'
                
                titulo = f'Stock {nivel}: {producto.clave}'
                mensaje = (
                    f'El producto {producto.clave} - {producto.descripcion} '
                    f'tiene stock {nivel.lower()}.\n'
                    f'Stock actual: {stock_actual} | Mínimo requerido: {producto.stock_minimo} | '
                    f'Diferencia: {diferencia}'
                )
                
                for usuario in usuarios:
                    if cls._crear_notificacion(
                        usuario=usuario,
                        titulo=titulo,
                        mensaje=mensaje,
                        tipo='error' if stock_actual == 0 else 'warning'
                    ):
                        creadas += 1
        
        logger.info(f"Notificaciones de stock crítico creadas: {creadas}")
        return creadas
    
    @classmethod
    def notificar_lotes_por_caducar(cls, dias_anticipacion=30):
        """
        Genera notificaciones para lotes próximos a caducar.
        
        Args:
            dias_anticipacion: Días de anticipación para la alerta (default 30)
            
        Returns:
            int: Número de notificaciones creadas
        """
        from core.models import Lote
        
        usuarios = cls._get_usuarios_farmacia()
        if not usuarios.exists():
            logger.warning("No hay usuarios farmacia/admin para notificar caducidades")
            return 0
        
        hoy = date.today()
        limite = hoy + timedelta(days=dias_anticipacion)
        
        # Lotes que caducan pronto y tienen stock
        lotes_por_caducar = Lote.objects.filter(
            deleted_at__isnull=True,
            cantidad_actual__gt=0,
            fecha_caducidad__gt=hoy,
            fecha_caducidad__lte=limite
        ).select_related('producto')
        
        creadas = 0
        
        for lote in lotes_por_caducar:
            dias_restantes = (lote.fecha_caducidad - hoy).days
            nivel = 'CRÍTICO' if dias_restantes <= 7 else 'PRÓXIMO'
            
            titulo = f'Caducidad {nivel}: Lote {lote.numero_lote}'
            mensaje = (
                f'El lote {lote.numero_lote} del producto {lote.producto.clave} - '
                f'{lote.producto.descripcion} caduca en {dias_restantes} días.\n'
                f'Fecha caducidad: {lote.fecha_caducidad.strftime("%d/%m/%Y")} | '
                f'Stock disponible: {lote.cantidad_actual}'
            )
            
            for usuario in usuarios:
                if cls._crear_notificacion(
                    usuario=usuario,
                    titulo=titulo,
                    mensaje=mensaje,
                    tipo='error' if dias_restantes <= 7 else 'warning'
                ):
                    creadas += 1
        
        logger.info(f"Notificaciones de caducidad creadas: {creadas}")
        return creadas
    
    @classmethod
    def notificar_lotes_vencidos(cls):
        """
        Genera notificaciones para lotes ya vencidos que aún tienen stock.
        
        Returns:
            int: Número de notificaciones creadas
        """
        from core.models import Lote
        
        usuarios = cls._get_usuarios_farmacia()
        if not usuarios.exists():
            return 0
        
        hoy = date.today()
        
        lotes_vencidos = Lote.objects.filter(
            deleted_at__isnull=True,
            cantidad_actual__gt=0,
            fecha_caducidad__lt=hoy
        ).select_related('producto')
        
        creadas = 0
        
        for lote in lotes_vencidos:
            dias_vencido = (hoy - lote.fecha_caducidad).days
            
            titulo = f'LOTE VENCIDO: {lote.numero_lote}'
            mensaje = (
                f'⚠️ El lote {lote.numero_lote} del producto {lote.producto.clave} - '
                f'{lote.producto.descripcion} está VENCIDO desde hace {dias_vencido} días.\n'
                f'Fecha caducidad: {lote.fecha_caducidad.strftime("%d/%m/%Y")} | '
                f'Stock remanente: {lote.cantidad_actual}\n'
                f'ACCIÓN REQUERIDA: Retirar del inventario disponible.'
            )
            
            for usuario in usuarios:
                if cls._crear_notificacion(
                    usuario=usuario,
                    titulo=titulo,
                    mensaje=mensaje,
                    tipo='error'
                ):
                    creadas += 1
        
        logger.info(f"Notificaciones de lotes vencidos creadas: {creadas}")
        return creadas
    
    @classmethod
    def notificar_fallo_importacion(cls, usuario, modelo, error, archivo=None):
        """
        Genera notificación para el usuario cuando falla una importación.
        
        Args:
            usuario: Usuario que realizó la importación
            modelo: Modelo que se intentó importar (Productos, Lotes, etc.)
            error: Mensaje de error
            archivo: Nombre del archivo (opcional)
        """
        titulo = f'Error en importación de {modelo}'
        mensaje = (
            f'La importación de {modelo} ha fallado.\n'
            f'Archivo: {archivo or "N/A"}\n'
            f'Error: {error}'
        )
        
        return cls._crear_notificacion(
            usuario=usuario,
            titulo=titulo,
            mensaje=mensaje,
            tipo='error'
        )
    
    @classmethod
    def ejecutar_todas_las_alertas(cls):
        """
        Ejecuta todas las verificaciones de alertas.
        Útil para tareas programadas (cron/celery).
        
        Returns:
            dict: Resumen de notificaciones creadas por tipo
        """
        return {
            'stock_critico': cls.notificar_stock_critico(),
            'por_caducar': cls.notificar_lotes_por_caducar(),
            'vencidos': cls.notificar_lotes_vencidos(),
        }
