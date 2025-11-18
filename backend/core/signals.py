"""
Signals para el sistema de Farmacia Penitenciaria
Incluye auditoría automática y actualización de estado de lotes
"""
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from .models import Movimiento, Lote, Requisicion, Producto, AuditoriaLog
from .middleware import get_current_request, get_current_user
import logging
import json

logger = logging.getLogger(__name__)


def registrar_auditoria(modelo, objeto, accion, cambios=None):
    """
    Función auxiliar para registrar auditoría
    """
    request = get_current_request()
    usuario = get_current_user()
    
    if not usuario or not usuario.is_authenticated:
        usuario = None
    
    ip_address = None
    user_agent = ''
    
    if request:
        # Obtener IP real (considerando proxies)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
    
    try:
        AuditoriaLog.objects.create(
            usuario=usuario,
            accion=accion,
            modelo=modelo,
            objeto_id=objeto.pk,
            objeto_repr=str(objeto)[:255],
            cambios=cambios or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
        logger.info(f"Auditoría registrada: {usuario} - {accion} - {modelo} #{objeto.pk}")
    except Exception as e:
        logger.error(f"Error al registrar auditoría: {str(e)}")


@receiver(post_save, sender=Movimiento)
def actualizar_existencia_lote(sender, instance, created, **kwargs):
    """
    Signal que actualiza la cantidad de un lote cuando se crea un movimiento
    Ya implementado en el método save() del modelo, pero se mantiene como backup
    """
    if created:
        lote = instance.lote
        logger.info(
            f"Signal disparado - Movimiento {instance.tipo} en Lote {lote.numero_lote}: "
            f"Cantidad: {instance.cantidad}, "
            f"Stock actual: {lote.cantidad_actual}"
        )


@receiver(pre_save, sender=Lote)
def validar_caducidad_lote(sender, instance, **kwargs):
    """
    Signal que marca automáticamente lotes vencidos antes de guardar
    """
    from datetime import date
    
    if instance.fecha_caducidad < date.today() and instance.estado != 'vencido':
        instance.estado = 'vencido'
        logger.warning(
            f"Lote {instance.numero_lote} marcado automáticamente como VENCIDO "
            f"(caducidad: {instance.fecha_caducidad})"
        )


@receiver(post_save, sender=Requisicion)
def auditar_cambios_requisicion(sender, instance, created, **kwargs):
    """
    Audita creación y cambios en requisiciones
    """
    if created:
        registrar_auditoria(
            modelo='Requisicion',
            objeto=instance,
            accion='crear',
            cambios={
                'folio': instance.folio,
                'centro': instance.centro.nombre,
                'estado': instance.estado,
                'total_productos': instance.detalles.count()
            }
        )
    else:
        # Capturar cambios de estado
        try:
            old_instance = Requisicion.objects.get(pk=instance.pk)
            cambios = {}
            
            if old_instance.estado != instance.estado:
                cambios['estado_anterior'] = old_instance.estado
                cambios['estado_nuevo'] = instance.estado
                
                # Registrar quien autorizó/rechazó
                if instance.estado in ['autorizada', 'rechazada'] and instance.usuario_autoriza:
                    cambios['usuario_autoriza'] = instance.usuario_autoriza.username
                
                if instance.estado == 'rechazada' and instance.motivo_rechazo:
                    cambios['motivo_rechazo'] = instance.motivo_rechazo
                
                registrar_auditoria(
                    modelo='Requisicion',
                    objeto=instance,
                    accion=f'cambiar_estado_{instance.estado}',
                    cambios=cambios
                )
        except Requisicion.DoesNotExist:
            pass


@receiver(pre_save, sender=Producto)
def snapshot_producto(sender, instance, **kwargs):
    """
    Conserva el estado previo del producto para detectar cambios reales.
    """
    if not instance.pk:
        instance._previous_state = None
        return
    
    try:
        instance._previous_state = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        instance._previous_state = None


@receiver(post_save, sender=Producto)
def auditar_cambios_producto(sender, instance, created, **kwargs):
    """
    Audita creación y cambios relevantes en productos.
    """
    if created:
        registrar_auditoria(
            modelo='Producto',
            objeto=instance,
            accion='crear',
            cambios={
                'clave': instance.clave,
                'descripcion': instance.descripcion,
                'unidad_medida': instance.unidad_medida,
                'precio_unitario': str(instance.precio_unitario),
                'stock_minimo': instance.stock_minimo,
                'activo': instance.activo
            }
        )
        return
    
    anterior = getattr(instance, '_previous_state', None)
    if not anterior:
        return
    
    cambios = {}
    if anterior.descripcion != instance.descripcion:
        cambios['descripcion'] = (anterior.descripcion, instance.descripcion)
    if anterior.unidad_medida != instance.unidad_medida:
        cambios['unidad_medida'] = (anterior.unidad_medida, instance.unidad_medida)
    if anterior.precio_unitario != instance.precio_unitario:
        cambios['precio_unitario'] = (str(anterior.precio_unitario), str(instance.precio_unitario))
    if anterior.stock_minimo != instance.stock_minimo:
        cambios['stock_minimo'] = (anterior.stock_minimo, instance.stock_minimo)
    if anterior.activo != instance.activo:
        cambios['activo'] = (anterior.activo, instance.activo)
    
    if cambios:
        registrar_auditoria(
            modelo='Producto',
            objeto=instance,
            accion='actualizar',
            cambios=cambios
        )


@receiver(post_save, sender=Lote)
def auditar_lote(sender, instance, created, **kwargs):
    """
    Audita creación y actualización de lotes
    """
    accion = 'crear' if created else 'actualizar'
    registrar_auditoria(
        modelo='Lote',
        objeto=instance,
        accion=accion,
        cambios={
            'numero_lote': instance.numero_lote,
            'producto': instance.producto.clave,
            'cantidad_actual': instance.cantidad_actual,
            'estado': instance.estado,
            'fecha_caducidad': instance.fecha_caducidad.isoformat()
        }
    )


@receiver(post_delete, sender=Producto)
def auditar_eliminacion_producto(sender, instance, **kwargs):
    """
    Auditoría específica para eliminaciones de productos.
    """
    registrar_auditoria(
        modelo='Producto',
        objeto=instance,
        accion='eliminar',
        cambios={'clave': instance.clave, 'razon': 'Producto eliminado'}
    )


@receiver(post_delete, sender=Lote)
@receiver(post_delete, sender=Requisicion)
def auditar_eliminacion(sender, instance, **kwargs):
    """
    Audita eliminación de objetos (excepto Producto que tiene handler propio)
    """
    registrar_auditoria(
        modelo=sender.__name__,
        objeto=instance,
        accion='eliminar',
        cambios={'objeto_eliminado': str(instance)}
    )
