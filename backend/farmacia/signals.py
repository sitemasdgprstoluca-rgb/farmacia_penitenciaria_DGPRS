from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import Movimiento, Lote

@receiver(post_save, sender=Movimiento)
def actualizar_existencia_lote(sender, instance, created, **kwargs):
    """
    Actualiza la existencia del lote cuando se crea un movimiento.
    ENTRADA: suma existencia
    SALIDA: resta existencia
    AJUSTE: ajusta existencia
    """
    if not created or not instance.lote:
        return
    
    lote = instance.lote
    
    if instance.tipo == 'ENTRADA':
        lote.existencia_actual += instance.cantidad
    elif instance.tipo == 'SALIDA':
        if lote.existencia_actual < instance.cantidad:
            raise ValidationError(
                f'Stock insuficiente en lote {lote.codigo_lote}. '
                f'Disponible: {lote.existencia_actual}, Solicitado: {instance.cantidad}'
            )
        lote.existencia_actual -= instance.cantidad
    elif instance.tipo == 'AJUSTE':
        nueva_existencia = instance.cantidad
        if nueva_existencia < 0:
            raise ValidationError('La existencia ajustada no puede ser negativa')
        lote.existencia_actual = nueva_existencia
    elif instance.tipo == 'DEVOLUCION':
        lote.existencia_actual += instance.cantidad
    
    lote.save()
