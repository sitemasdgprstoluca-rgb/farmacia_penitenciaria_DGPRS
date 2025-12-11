"""
ISS-002/ISS-005 FIX: Mixins y decoradores para enforcement de validaciones.

Este módulo proporciona:
1. Mixins para modelos managed=False que aseguran validaciones
2. Decoradores para restringir cambios de estado críticos
3. Guardrails para operaciones de inventario

PROBLEMA:
- Los modelos con managed=False no tienen constraints de BD automáticos
- Operaciones bulk o save() sin full_clean() pueden omitir validaciones
- Cambios de estado de requisición fuera de RequisicionService causan inconsistencias

SOLUCIÓN:
- ValidatedModelMixin: Fuerza full_clean() en save()
- RequireServiceMixin: Bloquea save() directo en modelos críticos
- @require_service: Decorador para vistas que modifican estado
- TransactionGuard: Contexto para operaciones atómicas con rollback
"""
import functools
import logging
from typing import Callable, List, Optional, Any, Set
from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils import timezone

logger = logging.getLogger(__name__)


class ValidationBypassError(Exception):
    """Error cuando se intenta bypassear validaciones en producción."""
    pass


class ServiceRequiredError(Exception):
    """Error cuando se intenta modificar estado sin usar el servicio correcto."""
    pass


class ValidatedModelMixin:
    """
    ISS-002 FIX: Mixin que fuerza validaciones en save().
    
    Uso:
        class MiModelo(ValidatedModelMixin, models.Model):
            ...
    
    Comportamiento:
    - Ejecuta full_clean() antes de save() siempre
    - En producción, bloquea skip_validation=True
    - Registra intentos de bypass para auditoría
    """
    
    # Campos que se pueden modificar sin validación completa
    CAMPOS_SIN_VALIDACION: Set[str] = set()
    
    def save(self, *args, **kwargs):
        """
        Override de save() que fuerza validaciones.
        
        Args:
            skip_validation: Si True, omite validaciones (SOLO para migraciones)
            update_fields: Si se especifica, valida solo esos campos
        """
        from django.conf import settings
        
        skip_validation = kwargs.pop('skip_validation', False)
        update_fields = kwargs.get('update_fields')
        
        # ISS-002: Bloquear skip_validation en producción
        if skip_validation:
            if not getattr(settings, 'DEBUG', False):
                logger.critical(
                    f"ISS-002 SECURITY: Intento de skip_validation en PRODUCCIÓN. "
                    f"Modelo: {self.__class__.__name__}, PK: {self.pk}"
                )
                # En producción, ignorar el flag y validar de todas formas
                skip_validation = False
        
        # Si hay update_fields y todos están en CAMPOS_SIN_VALIDACION, saltar
        if update_fields:
            campos_set = set(update_fields)
            if campos_set.issubset(self.CAMPOS_SIN_VALIDACION):
                return super().save(*args, **kwargs)
        
        # Ejecutar validación completa
        if not skip_validation:
            try:
                self.full_clean()
            except ValidationError as e:
                logger.warning(
                    f"Validación fallida para {self.__class__.__name__} (PK: {self.pk}): {e}"
                )
                raise
        
        return super().save(*args, **kwargs)


class RequireServiceMixin:
    """
    ISS-005 FIX: Mixin que restringe modificaciones de estado a servicios.
    
    Uso:
        class Requisicion(RequireServiceMixin, models.Model):
            CAMPOS_PROTEGIDOS = {'estado'}
            SERVICIO_REQUERIDO = 'RequisicionService'
    
    Comportamiento:
    - Bloquea save() si se modifican CAMPOS_PROTEGIDOS
    - Solo permite cambios vía el servicio especificado
    - Usa _service_context para permitir cambios desde el servicio
    """
    
    # Campos que solo pueden modificarse vía servicio
    CAMPOS_PROTEGIDOS: Set[str] = set()
    
    # Nombre del servicio autorizado
    SERVICIO_REQUERIDO: str = ''
    
    # Bandera de contexto para permitir cambios desde servicio
    _service_context: bool = False
    
    def _check_protected_fields(self) -> List[str]:
        """
        Verifica si hay campos protegidos modificados.
        
        Returns:
            Lista de campos protegidos que fueron modificados
        """
        if not self.pk:
            return []  # Nuevo registro, permitir
        
        if not self.CAMPOS_PROTEGIDOS:
            return []
        
        # Obtener valores originales de BD
        try:
            original = self.__class__.objects.get(pk=self.pk)
        except self.__class__.DoesNotExist:
            return []
        
        campos_modificados = []
        for campo in self.CAMPOS_PROTEGIDOS:
            valor_original = getattr(original, campo, None)
            valor_nuevo = getattr(self, campo, None)
            if valor_original != valor_nuevo:
                campos_modificados.append(campo)
        
        return campos_modificados
    
    def save(self, *args, **kwargs):
        """
        Override de save() que protege campos críticos.
        """
        if self._service_context:
            # Permitir si viene del servicio autorizado
            return super().save(*args, **kwargs)
        
        campos_modificados = self._check_protected_fields()
        if campos_modificados:
            logger.error(
                f"ISS-005 BLOCKED: Intento de modificar campos protegidos sin servicio. "
                f"Modelo: {self.__class__.__name__}, PK: {self.pk}, "
                f"Campos: {campos_modificados}, Servicio requerido: {self.SERVICIO_REQUERIDO}"
            )
            raise ServiceRequiredError(
                f"Los campos {campos_modificados} solo pueden modificarse usando "
                f"{self.SERVICIO_REQUERIDO}. No use save() directamente."
            )
        
        return super().save(*args, **kwargs)
    
    @classmethod
    def enable_service_context(cls, instance):
        """Habilita el contexto de servicio para una instancia."""
        instance._service_context = True
        return instance
    
    @classmethod
    def disable_service_context(cls, instance):
        """Deshabilita el contexto de servicio para una instancia."""
        instance._service_context = False
        return instance


def require_service(service_name: str, campos: Optional[List[str]] = None):
    """
    ISS-005 FIX: Decorador para vistas que modifican campos protegidos.
    
    Uso:
        @require_service('RequisicionService', ['estado'])
        def update(self, request, *args, **kwargs):
            ...
    
    Args:
        service_name: Nombre del servicio requerido
        campos: Lista de campos que la vista no debe modificar directamente
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, request, *args, **kwargs):
            # Advertir si se detecta modificación directa de campos
            if campos and hasattr(request, 'data'):
                campos_en_request = set(request.data.keys()) & set(campos)
                if campos_en_request:
                    logger.warning(
                        f"ISS-005: Vista {func.__name__} recibió campos protegidos: "
                        f"{campos_en_request}. Debe usar {service_name}."
                    )
            return func(self, request, *args, **kwargs)
        return wrapper
    return decorator


class TransactionGuard:
    """
    ISS-005 FIX: Context manager para operaciones atómicas con validación.
    
    Uso:
        with TransactionGuard('surtir_requisicion', requisicion=req) as guard:
            # Operaciones dentro de transacción
            guard.registrar_operacion('descontar_lote', lote_id=1)
            guard.registrar_operacion('crear_movimiento', mov_id=1)
    
    Comportamiento:
    - Abre transacción atómica
    - Registra todas las operaciones para trazabilidad
    - Hace rollback automático en excepciones
    - Registra en log para auditoría
    """
    
    def __init__(self, operacion: str, **contexto):
        self.operacion = operacion
        self.contexto = contexto
        self.operaciones = []
        self.inicio = None
        self.fin = None
        self.exito = False
        self._atomic = None
    
    def __enter__(self):
        self.inicio = timezone.now()
        self._atomic = transaction.atomic()
        self._atomic.__enter__()
        
        logger.info(
            f"ISS-005 TRANSACTION START: {self.operacion} | "
            f"Contexto: {self.contexto}"
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.fin = timezone.now()
        duracion = (self.fin - self.inicio).total_seconds()
        
        if exc_type is None:
            self.exito = True
            logger.info(
                f"ISS-005 TRANSACTION END: {self.operacion} | "
                f"Éxito: {self.exito} | Duración: {duracion:.3f}s | "
                f"Operaciones: {len(self.operaciones)}"
            )
        else:
            self.exito = False
            logger.error(
                f"ISS-005 TRANSACTION ROLLBACK: {self.operacion} | "
                f"Error: {exc_type.__name__}: {exc_val} | "
                f"Duración: {duracion:.3f}s | "
                f"Operaciones antes del rollback: {len(self.operaciones)}"
            )
        
        # Propagar al atomic context
        return self._atomic.__exit__(exc_type, exc_val, exc_tb)
    
    def registrar_operacion(self, nombre: str, **datos):
        """
        Registra una operación dentro de la transacción.
        
        Args:
            nombre: Nombre de la operación (ej: 'descontar_lote')
            **datos: Datos asociados (ej: lote_id=1, cantidad=10)
        """
        self.operaciones.append({
            'nombre': nombre,
            'timestamp': timezone.now().isoformat(),
            'datos': datos,
        })
    
    def get_resumen(self) -> dict:
        """Retorna resumen de la transacción para logging."""
        return {
            'operacion': self.operacion,
            'contexto': self.contexto,
            'inicio': self.inicio.isoformat() if self.inicio else None,
            'fin': self.fin.isoformat() if self.fin else None,
            'exito': self.exito,
            'operaciones': len(self.operaciones),
        }


def validate_before_save(model_class):
    """
    ISS-002 FIX: Decorador de clase que fuerza validación en save().
    
    Uso:
        @validate_before_save
        class MiModelo(models.Model):
            ...
    """
    original_save = model_class.save
    
    @functools.wraps(original_save)
    def validated_save(self, *args, **kwargs):
        skip_validation = kwargs.pop('skip_validation', False)
        
        if not skip_validation:
            self.full_clean()
        
        return original_save(self, *args, **kwargs)
    
    model_class.save = validated_save
    return model_class
