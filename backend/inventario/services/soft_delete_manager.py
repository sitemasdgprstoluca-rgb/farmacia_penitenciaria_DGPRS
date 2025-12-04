"""
ISS-016: Manager de soft-delete consistente.

Sistema centralizado de soft-delete para mantener
consistencia en todas las entidades del sistema.
"""
import logging
from datetime import datetime
from typing import Optional, List, Any, TypeVar, Generic

from django.db import models, transaction
from django.db.models import QuerySet, Q
from django.utils import timezone

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=models.Model)


class SoftDeleteQuerySet(QuerySet):
    """
    ISS-016: QuerySet personalizado para soft-delete.
    
    Por defecto excluye registros eliminados (deleted_at != null).
    """
    
    def delete(self):
        """
        Override de delete para usar soft-delete.
        Para eliminación real, usar hard_delete().
        """
        return self.soft_delete()
    
    def soft_delete(self, usuario=None):
        """
        ISS-016: Marca registros como eliminados.
        
        Args:
            usuario: Usuario que realiza la eliminación (opcional)
        """
        ahora = timezone.now()
        update_fields = {'deleted_at': ahora}
        
        if usuario:
            update_fields['deleted_by_id'] = usuario.id
        
        count = self.update(**update_fields)
        
        logger.info(
            f"ISS-016: Soft-delete de {count} registros "
            f"por usuario {usuario.username if usuario else 'sistema'}"
        )
        
        return count, {}  # Emular retorno de delete()
    
    def hard_delete(self):
        """Eliminación real de registros."""
        return super().delete()
    
    def restore(self, usuario=None):
        """
        ISS-016: Restaura registros eliminados.
        
        Args:
            usuario: Usuario que realiza la restauración
        """
        update_fields = {
            'deleted_at': None,
            'deleted_by_id': None
        }
        
        if usuario:
            update_fields['restored_by_id'] = usuario.id
            update_fields['restored_at'] = timezone.now()
        
        count = self.update(**update_fields)
        
        logger.info(
            f"ISS-016: Restauración de {count} registros "
            f"por usuario {usuario.username if usuario else 'sistema'}"
        )
        
        return count
    
    def active(self):
        """Filtra solo registros activos (no eliminados)."""
        return self.filter(deleted_at__isnull=True)
    
    def deleted(self):
        """Filtra solo registros eliminados."""
        return self.filter(deleted_at__isnull=False)
    
    def with_deleted(self):
        """Retorna todos los registros, incluyendo eliminados."""
        return self.all()


class SoftDeleteManager(models.Manager):
    """
    ISS-016: Manager que por defecto excluye registros eliminados.
    """
    
    def get_queryset(self):
        """Retorna QuerySet excluyendo eliminados por defecto."""
        return SoftDeleteQuerySet(self.model, using=self._db).active()
    
    def active(self):
        """Alias explícito para registros activos."""
        return self.get_queryset()
    
    def deleted(self):
        """Retorna solo registros eliminados."""
        return SoftDeleteQuerySet(self.model, using=self._db).deleted()
    
    def with_deleted(self):
        """Retorna todos los registros, incluyendo eliminados."""
        return SoftDeleteQuerySet(self.model, using=self._db).all()
    
    def restore(self, pk, usuario=None):
        """
        ISS-016: Restaura un registro específico por PK.
        
        Args:
            pk: ID del registro a restaurar
            usuario: Usuario que realiza la restauración
        """
        try:
            obj = SoftDeleteQuerySet(
                self.model, using=self._db
            ).deleted().get(pk=pk)
            
            obj.deleted_at = None
            obj.deleted_by = None
            
            if hasattr(obj, 'restored_at'):
                obj.restored_at = timezone.now()
            if hasattr(obj, 'restored_by') and usuario:
                obj.restored_by = usuario
            
            obj.save()
            
            logger.info(
                f"ISS-016: Registro {self.model.__name__}#{pk} restaurado "
                f"por {usuario.username if usuario else 'sistema'}"
            )
            
            return obj
            
        except self.model.DoesNotExist:
            logger.warning(
                f"ISS-016: Intento de restaurar registro inexistente "
                f"{self.model.__name__}#{pk}"
            )
            return None


class AllObjectsManager(models.Manager):
    """
    ISS-016: Manager que incluye todos los registros (activos y eliminados).
    
    Usar para operaciones administrativas que necesiten ver todo.
    """
    
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).all()


class SoftDeleteMixin(models.Model):
    """
    ISS-016: Mixin para agregar soft-delete a cualquier modelo.
    
    Uso:
        class MiModelo(SoftDeleteMixin, models.Model):
            nombre = models.CharField(max_length=100)
            
            objects = SoftDeleteManager()
            all_objects = AllObjectsManager()
    """
    
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Fecha de eliminación (soft-delete)"
    )
    deleted_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_deleted',
        help_text="Usuario que eliminó el registro"
    )
    
    # Campos opcionales de restauración
    restored_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha de última restauración"
    )
    restored_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_restored',
        help_text="Usuario que restauró el registro"
    )
    
    class Meta:
        abstract = True
    
    @property
    def is_deleted(self) -> bool:
        """Indica si el registro está eliminado."""
        return self.deleted_at is not None
    
    def soft_delete(self, usuario=None):
        """
        ISS-016: Marca este registro como eliminado.
        
        Args:
            usuario: Usuario que realiza la eliminación
        """
        self.deleted_at = timezone.now()
        if usuario:
            self.deleted_by = usuario
        
        self.save(update_fields=['deleted_at', 'deleted_by'])
        
        logger.info(
            f"ISS-016: {self.__class__.__name__}#{self.pk} soft-deleted "
            f"por {usuario.username if usuario else 'sistema'}"
        )
    
    def restore(self, usuario=None):
        """
        ISS-016: Restaura este registro.
        
        Args:
            usuario: Usuario que realiza la restauración
        """
        self.deleted_at = None
        self.deleted_by = None
        self.restored_at = timezone.now()
        if usuario:
            self.restored_by = usuario
        
        self.save(update_fields=[
            'deleted_at', 'deleted_by', 'restored_at', 'restored_by'
        ])
        
        logger.info(
            f"ISS-016: {self.__class__.__name__}#{self.pk} restaurado "
            f"por {usuario.username if usuario else 'sistema'}"
        )
    
    def hard_delete(self):
        """Eliminación permanente del registro."""
        logger.warning(
            f"ISS-016: {self.__class__.__name__}#{self.pk} "
            "eliminado permanentemente (hard-delete)"
        )
        super().delete()


class SoftDeleteService:
    """
    ISS-016: Servicio centralizado para operaciones de soft-delete.
    
    Proporciona operaciones consistentes para múltiples modelos.
    """
    
    @staticmethod
    def soft_delete_batch(
        modelo: models.Model,
        ids: List[int],
        usuario=None
    ) -> int:
        """
        ISS-016: Elimina múltiples registros.
        
        Args:
            modelo: Clase del modelo
            ids: Lista de IDs a eliminar
            usuario: Usuario que realiza la operación
            
        Returns:
            Cantidad de registros eliminados
        """
        with transaction.atomic():
            count = modelo.objects.filter(
                pk__in=ids,
                deleted_at__isnull=True
            ).update(
                deleted_at=timezone.now(),
                deleted_by=usuario
            )
        
        logger.info(
            f"ISS-016: Batch soft-delete de {count} registros de {modelo.__name__} "
            f"por {usuario.username if usuario else 'sistema'}"
        )
        
        return count
    
    @staticmethod
    def restore_batch(
        modelo: models.Model,
        ids: List[int],
        usuario=None
    ) -> int:
        """
        ISS-016: Restaura múltiples registros.
        """
        with transaction.atomic():
            qs = SoftDeleteQuerySet(modelo).filter(
                pk__in=ids,
                deleted_at__isnull=False
            )
            
            update_fields = {
                'deleted_at': None,
                'deleted_by': None,
            }
            
            if hasattr(modelo, 'restored_at'):
                update_fields['restored_at'] = timezone.now()
            if hasattr(modelo, 'restored_by') and usuario:
                update_fields['restored_by'] = usuario
            
            count = qs.update(**update_fields)
        
        logger.info(
            f"ISS-016: Batch restore de {count} registros de {modelo.__name__} "
            f"por {usuario.username if usuario else 'sistema'}"
        )
        
        return count
    
    @staticmethod
    def purge_deleted(
        modelo: models.Model,
        dias_antiguedad: int = 90,
        usuario=None
    ) -> int:
        """
        ISS-016: Elimina permanentemente registros soft-deleted antiguos.
        
        Args:
            modelo: Clase del modelo
            dias_antiguedad: Días mínimos desde la eliminación
            usuario: Usuario que autoriza la purga
            
        Returns:
            Cantidad de registros purgados
        """
        from datetime import timedelta
        
        fecha_limite = timezone.now() - timedelta(days=dias_antiguedad)
        
        with transaction.atomic():
            count, _ = SoftDeleteQuerySet(modelo).filter(
                deleted_at__lt=fecha_limite
            ).hard_delete()
        
        logger.warning(
            f"ISS-016: Purga de {count} registros de {modelo.__name__} "
            f"(>{dias_antiguedad} días) por {usuario.username if usuario else 'sistema'}"
        )
        
        return count
    
    @staticmethod
    def get_deletion_stats(modelo: models.Model) -> dict:
        """
        ISS-016: Obtiene estadísticas de eliminación.
        """
        from django.db.models import Count
        from datetime import timedelta
        
        ahora = timezone.now()
        hace_30_dias = ahora - timedelta(days=30)
        hace_90_dias = ahora - timedelta(days=90)
        
        total_activos = modelo.objects.count()
        
        deleted_qs = SoftDeleteQuerySet(modelo).deleted()
        total_eliminados = deleted_qs.count()
        eliminados_30d = deleted_qs.filter(deleted_at__gte=hace_30_dias).count()
        eliminados_90d = deleted_qs.filter(deleted_at__lt=hace_90_dias).count()
        
        return {
            'modelo': modelo.__name__,
            'total_activos': total_activos,
            'total_eliminados': total_eliminados,
            'eliminados_ultimos_30d': eliminados_30d,
            'purgables_90d': eliminados_90d,
            'porcentaje_eliminados': round(
                total_eliminados / (total_activos + total_eliminados) * 100, 2
            ) if (total_activos + total_eliminados) > 0 else 0
        }
