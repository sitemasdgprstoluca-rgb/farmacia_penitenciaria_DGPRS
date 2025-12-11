"""
ISS-001 FIX (audit17): Validadores de integridad para modelos managed=False.

Este módulo proporciona validaciones explícitas para garantizar integridad
de datos que Django NO aplica automáticamente cuando managed=False.

CONSTRAINTS VALIDADOS:
- Unicidad de campos críticos (producto.clave, lote.numero_lote, etc.)
- Existencia de foreign keys (producto_id, centro_id, etc.)
- Checks de negocio (cantidades positivas, estados válidos, etc.)

USO EN SERIALIZERS:
    from core.validators import IntegrityValidator
    
    class ProductoSerializer(serializers.ModelSerializer):
        def validate_clave(self, value):
            IntegrityValidator.validate_unique_clave_producto(value, self.instance)
            return value

USO EN SERVICIOS:
    from core.validators import IntegrityValidator
    
    def crear_producto(data):
        IntegrityValidator.validate_producto_integrity(data)
        # ... crear producto
"""
from django.core.exceptions import ValidationError
from django.db import models
import logging

logger = logging.getLogger(__name__)


class IntegrityValidator:
    """
    ISS-001 FIX: Validador centralizado de integridad de datos.
    
    Reemplaza las constraints de BD que Django no aplica con managed=False.
    """
    
    # =========================================================================
    # VALIDACIONES DE UNICIDAD
    # =========================================================================
    
    @staticmethod
    def validate_unique_clave_producto(clave: str, instance=None, raise_exception: bool = True) -> bool:
        """
        ISS-001 FIX: Valida unicidad de clave de producto.
        
        Args:
            clave: Clave del producto a validar
            instance: Instancia existente (para edición)
            raise_exception: Si True, lanza ValidationError
            
        Returns:
            bool: True si es única
            
        Raises:
            ValidationError: Si la clave ya existe
        """
        from core.models import Producto
        
        qs = Producto.objects.filter(clave__iexact=clave)
        if instance and instance.pk:
            qs = qs.exclude(pk=instance.pk)
        
        if qs.exists():
            msg = f"Ya existe un producto con la clave '{clave}'"
            logger.warning(f"ISS-001: Intento de duplicar clave producto: {clave}")
            if raise_exception:
                raise ValidationError({'clave': msg})
            return False
        return True
    
    @staticmethod
    def validate_unique_numero_lote(numero_lote: str, producto_id: int, instance=None, raise_exception: bool = True) -> bool:
        """
        ISS-001 FIX: Valida unicidad de número de lote por producto.
        
        Args:
            numero_lote: Número de lote
            producto_id: ID del producto
            instance: Instancia existente (para edición)
            raise_exception: Si True, lanza ValidationError
            
        Returns:
            bool: True si es único
        """
        from core.models import Lote
        
        qs = Lote.objects.filter(numero_lote__iexact=numero_lote, producto_id=producto_id)
        if instance and instance.pk:
            qs = qs.exclude(pk=instance.pk)
        
        if qs.exists():
            msg = f"Ya existe el lote '{numero_lote}' para este producto"
            logger.warning(f"ISS-001: Intento de duplicar lote: {numero_lote} producto_id={producto_id}")
            if raise_exception:
                raise ValidationError({'numero_lote': msg})
            return False
        return True
    
    @staticmethod
    def validate_unique_folio_requisicion(folio: str, instance=None, raise_exception: bool = True) -> bool:
        """
        ISS-001 FIX: Valida unicidad de folio de requisición.
        """
        from core.models import Requisicion
        
        qs = Requisicion.objects.filter(folio__iexact=folio)
        if instance and instance.pk:
            qs = qs.exclude(pk=instance.pk)
        
        if qs.exists():
            msg = f"Ya existe una requisición con el folio '{folio}'"
            logger.warning(f"ISS-001: Intento de duplicar folio requisición: {folio}")
            if raise_exception:
                raise ValidationError({'folio': msg})
            return False
        return True
    
    # =========================================================================
    # VALIDACIONES DE FOREIGN KEYS
    # =========================================================================
    
    @staticmethod
    def validate_fk_exists(model_class, pk: int, field_name: str, raise_exception: bool = True) -> bool:
        """
        ISS-001 FIX: Valida que una foreign key exista.
        
        Args:
            model_class: Clase del modelo relacionado
            pk: ID a validar
            field_name: Nombre del campo para el error
            raise_exception: Si True, lanza ValidationError
            
        Returns:
            bool: True si existe
        """
        if pk is None:
            return True  # Nulls se validan con otros métodos
        
        if not model_class.objects.filter(pk=pk).exists():
            model_name = model_class.__name__
            msg = f"No existe {model_name} con ID {pk}"
            logger.warning(f"ISS-001: FK inválida: {model_name}.{pk}")
            if raise_exception:
                raise ValidationError({field_name: msg})
            return False
        return True
    
    @staticmethod
    def validate_producto_exists(producto_id: int, raise_exception: bool = True) -> bool:
        """ISS-001 FIX: Valida que el producto exista."""
        from core.models import Producto
        return IntegrityValidator.validate_fk_exists(Producto, producto_id, 'producto', raise_exception)
    
    @staticmethod
    def validate_centro_exists(centro_id: int, raise_exception: bool = True) -> bool:
        """ISS-001 FIX: Valida que el centro exista."""
        from core.models import Centro
        return IntegrityValidator.validate_fk_exists(Centro, centro_id, 'centro', raise_exception)
    
    @staticmethod
    def validate_lote_exists(lote_id: int, raise_exception: bool = True) -> bool:
        """ISS-001 FIX: Valida que el lote exista."""
        from core.models import Lote
        return IntegrityValidator.validate_fk_exists(Lote, lote_id, 'lote', raise_exception)
    
    @staticmethod
    def validate_requisicion_exists(requisicion_id: int, raise_exception: bool = True) -> bool:
        """ISS-001 FIX: Valida que la requisición exista."""
        from core.models import Requisicion
        return IntegrityValidator.validate_fk_exists(Requisicion, requisicion_id, 'requisicion', raise_exception)
    
    @staticmethod
    def validate_contrato_exists(contrato_id: int, raise_exception: bool = True) -> bool:
        """ISS-001 FIX: Valida que el contrato exista."""
        from core.models import Contrato
        return IntegrityValidator.validate_fk_exists(Contrato, contrato_id, 'contrato', raise_exception)
    
    # =========================================================================
    # VALIDACIONES DE CHECKS DE NEGOCIO
    # =========================================================================
    
    @staticmethod
    def validate_cantidad_positiva(cantidad: int, field_name: str = 'cantidad', raise_exception: bool = True) -> bool:
        """
        ISS-001 FIX: Valida que una cantidad sea positiva.
        """
        if cantidad is None:
            return True
        
        if cantidad < 0:
            msg = f"La cantidad no puede ser negativa: {cantidad}"
            logger.warning(f"ISS-001: Cantidad negativa en {field_name}: {cantidad}")
            if raise_exception:
                raise ValidationError({field_name: msg})
            return False
        return True
    
    @staticmethod
    def validate_stock_no_negativo(producto_id: int, cantidad_salida: int, centro_id: int = None, raise_exception: bool = True) -> bool:
        """
        ISS-001 FIX: Valida que una salida no deje stock negativo.
        
        Args:
            producto_id: ID del producto
            cantidad_salida: Cantidad a restar
            centro_id: ID del centro (None = farmacia central)
            raise_exception: Si True, lanza ValidationError
        """
        from core.models import Producto
        
        try:
            producto = Producto.objects.get(pk=producto_id)
        except Producto.DoesNotExist:
            if raise_exception:
                raise ValidationError({'producto': f'Producto {producto_id} no existe'})
            return False
        
        if centro_id:
            stock_actual = producto.get_stock_centro(centro_id)
        else:
            stock_actual = producto.get_stock_farmacia_central()
        
        if stock_actual < cantidad_salida:
            ubicacion = f"centro {centro_id}" if centro_id else "farmacia central"
            msg = f"Stock insuficiente en {ubicacion}: disponible {stock_actual}, solicitado {cantidad_salida}"
            logger.warning(f"ISS-001: Stock insuficiente producto={producto_id}, {ubicacion}")
            if raise_exception:
                raise ValidationError({'cantidad': msg})
            return False
        return True
    
    @staticmethod
    def validate_estado_requisicion(estado: str, raise_exception: bool = True) -> bool:
        """
        ISS-001 FIX: Valida que el estado de requisición sea válido.
        """
        from core.constants import ESTADOS_REQUISICION
        
        estados_validos = [e[0] for e in ESTADOS_REQUISICION]
        
        if estado and estado.lower() not in [e.lower() for e in estados_validos]:
            msg = f"Estado inválido: {estado}. Válidos: {estados_validos}"
            logger.warning(f"ISS-001: Estado requisición inválido: {estado}")
            if raise_exception:
                raise ValidationError({'estado': msg})
            return False
        return True
    
    @staticmethod
    def validate_fecha_vencimiento_futura(fecha_vencimiento, raise_exception: bool = True) -> bool:
        """
        ISS-001 FIX: Valida que la fecha de vencimiento sea futura (para nuevos lotes).
        """
        from django.utils import timezone
        
        if fecha_vencimiento is None:
            return True
        
        hoy = timezone.now().date()
        if hasattr(fecha_vencimiento, 'date'):
            fecha_vencimiento = fecha_vencimiento.date()
        
        if fecha_vencimiento < hoy:
            msg = f"La fecha de vencimiento no puede ser pasada: {fecha_vencimiento}"
            logger.warning(f"ISS-001: Fecha vencimiento pasada: {fecha_vencimiento}")
            if raise_exception:
                raise ValidationError({'fecha_vencimiento': msg})
            return False
        return True
    
    # =========================================================================
    # VALIDACIONES COMPUESTAS
    # =========================================================================
    
    @staticmethod
    def validate_producto_integrity(data: dict, instance=None):
        """
        ISS-001 FIX: Validación completa de integridad para producto.
        
        Args:
            data: Datos del producto
            instance: Instancia existente (para edición)
            
        Raises:
            ValidationError: Si hay problemas de integridad
        """
        errors = {}
        
        # Unicidad de clave
        clave = data.get('clave')
        if clave:
            try:
                IntegrityValidator.validate_unique_clave_producto(clave, instance)
            except ValidationError as e:
                errors.update(e.message_dict)
        
        # Precio positivo
        precio = data.get('precio_unitario')
        if precio is not None and precio < 0:
            errors['precio_unitario'] = 'El precio no puede ser negativo'
        
        if errors:
            raise ValidationError(errors)
    
    @staticmethod
    def validate_lote_integrity(data: dict, instance=None):
        """
        ISS-001 FIX: Validación completa de integridad para lote.
        
        Args:
            data: Datos del lote
            instance: Instancia existente (para edición)
        """
        errors = {}
        
        # FK de producto
        producto_id = data.get('producto_id') or data.get('producto')
        if producto_id:
            try:
                IntegrityValidator.validate_producto_exists(producto_id)
            except ValidationError as e:
                errors.update(e.message_dict)
        
        # Unicidad de número de lote por producto
        numero_lote = data.get('numero_lote')
        if numero_lote and producto_id:
            try:
                IntegrityValidator.validate_unique_numero_lote(numero_lote, producto_id, instance)
            except ValidationError as e:
                errors.update(e.message_dict)
        
        # Cantidad positiva
        cantidad = data.get('cantidad_actual') or data.get('cantidad_inicial')
        if cantidad is not None:
            try:
                IntegrityValidator.validate_cantidad_positiva(cantidad, 'cantidad')
            except ValidationError as e:
                errors.update(e.message_dict)
        
        # Fecha vencimiento futura (solo para nuevos lotes)
        if not instance:
            fecha_vencimiento = data.get('fecha_vencimiento') or data.get('fecha_caducidad')
            if fecha_vencimiento:
                try:
                    IntegrityValidator.validate_fecha_vencimiento_futura(fecha_vencimiento)
                except ValidationError as e:
                    errors.update(e.message_dict)
        
        if errors:
            raise ValidationError(errors)
    
    @staticmethod
    def validate_movimiento_integrity(data: dict):
        """
        ISS-001 FIX: Validación completa de integridad para movimiento.
        """
        errors = {}
        
        # FK de producto
        producto_id = data.get('producto_id') or data.get('producto')
        if producto_id:
            try:
                IntegrityValidator.validate_producto_exists(producto_id)
            except ValidationError as e:
                errors.update(e.message_dict)
        
        # FK de lote (si se especifica)
        lote_id = data.get('lote_id') or data.get('lote')
        if lote_id:
            try:
                IntegrityValidator.validate_lote_exists(lote_id)
            except ValidationError as e:
                errors.update(e.message_dict)
        
        # Cantidad
        cantidad = data.get('cantidad')
        if cantidad is not None:
            # Para salidas, la cantidad es negativa
            tipo = data.get('tipo', '')
            if tipo == 'salida' and cantidad > 0:
                errors['cantidad'] = 'Las salidas deben tener cantidad negativa'
            elif tipo == 'entrada' and cantidad < 0:
                errors['cantidad'] = 'Las entradas deben tener cantidad positiva'
        
        if errors:
            raise ValidationError(errors)
    
    @staticmethod
    def validate_detalle_requisicion_integrity(data: dict):
        """
        ISS-001 FIX: Validación de integridad para detalle de requisición.
        """
        errors = {}
        
        # FK de producto
        producto_id = data.get('producto_id') or data.get('producto')
        if producto_id:
            try:
                IntegrityValidator.validate_producto_exists(producto_id)
            except ValidationError as e:
                errors.update(e.message_dict)
        
        # FK de requisición
        requisicion_id = data.get('requisicion_id') or data.get('requisicion')
        if requisicion_id:
            try:
                IntegrityValidator.validate_requisicion_exists(requisicion_id)
            except ValidationError as e:
                errors.update(e.message_dict)
        
        # Cantidades positivas
        cantidad_solicitada = data.get('cantidad_solicitada')
        if cantidad_solicitada is not None:
            try:
                IntegrityValidator.validate_cantidad_positiva(cantidad_solicitada, 'cantidad_solicitada')
            except ValidationError as e:
                errors.update(e.message_dict)
        
        cantidad_autorizada = data.get('cantidad_autorizada')
        if cantidad_autorizada is not None:
            try:
                IntegrityValidator.validate_cantidad_positiva(cantidad_autorizada, 'cantidad_autorizada')
            except ValidationError as e:
                errors.update(e.message_dict)
        
        if errors:
            raise ValidationError(errors)


class AuditLogger:
    """
    ISS-006 FIX (audit17): Logger de auditoría para accesos privilegiados.
    
    Registra accesos de usuarios privilegiados a datos sensibles.
    Usa el logger 'audit' configurado en settings.py.
    """
    
    # Logger específico de auditoría
    _audit_logger = logging.getLogger('audit')
    
    @classmethod
    def log_privileged_access(cls, user, resource: str = None, resource_type: str = None, 
                              resource_id=None, action: str = 'view', 
                              filter_applied: bool = False, details: dict = None):
        """
        ISS-006 FIX: Registra acceso privilegiado.
        
        Args:
            user: Usuario que accede
            resource: Alias para resource_type
            resource_type: Tipo de recurso (requisicion, inventario, etc.)
            resource_id: ID del recurso (opcional)
            action: Acción realizada (view, list, export, etc.)
            filter_applied: Si se aplicó filtro de centro
            details: Detalles adicionales
        """
        if not user or not getattr(user, 'is_authenticated', False):
            return
        
        # Compatibilidad: usar resource si resource_type no está especificado
        resource_type = resource_type or resource
        
        is_privileged = (
            getattr(user, 'is_superuser', False) or 
            getattr(user, 'is_staff', False) or
            getattr(user, 'rol', '').lower() in ['admin', 'admin_sistema', 'farmacia', 'admin_farmacia']
        )
        
        if is_privileged:
            log_data = {
                'event': 'privileged_access',
                'user_id': getattr(user, 'id', None),
                'username': getattr(user, 'username', 'unknown'),
                'rol': getattr(user, 'rol', 'unknown'),
                'is_superuser': getattr(user, 'is_superuser', False),
                'is_staff': getattr(user, 'is_staff', False),
                'resource_type': resource_type,
                'resource_id': resource_id,
                'action': action,
                'filter_applied': filter_applied,
                'details': details or {}
            }
            
            # Usar warning para accesos privilegiados sin filtro
            if not filter_applied:
                logger.warning(f"AUDIT: Acceso privilegiado sin filtro - {log_data}")
            else:
                cls._audit_logger.info(f"AUDIT: Acceso privilegiado - {log_data}")
    
    @classmethod
    def log_global_query(cls, user, queryset=None, queryset_count: int = None,
                         model_name: str = None, filter_applied: bool = False,
                         filters_applied: dict = None):
        """
        ISS-006 FIX: Registra cuando un usuario privilegiado consulta datos globales.
        
        Args:
            user: Usuario que realiza la consulta
            queryset: QuerySet consultado (opcional)
            queryset_count: Número de registros (opcional)
            model_name: Nombre del modelo (opcional, se extrae de queryset)
            filter_applied: Si se aplicó algún filtro
            filters_applied: Diccionario de filtros aplicados
        """
        if not user or not getattr(user, 'is_authenticated', False):
            return
        
        is_global = (
            getattr(user, 'is_superuser', False) or 
            getattr(user, 'is_staff', False) or
            getattr(user, 'rol', '').lower() in ['admin', 'admin_sistema']
        )
        
        # Determinar nombre del modelo
        if not model_name and queryset and hasattr(queryset, 'model'):
            model_name = queryset.model.__name__
        
        # Determinar count
        if queryset_count is None and queryset is not None:
            try:
                queryset_count = queryset.count()
            except Exception:
                queryset_count = -1
        
        if is_global:
            log_data = {
                'event': 'global_query',
                'user_id': getattr(user, 'id', None),
                'username': getattr(user, 'username', 'unknown'),
                'model': model_name or 'unknown',
                'filter_applied': filter_applied,
                'filters_applied': filters_applied or {},
                'result_count': queryset_count
            }
            
            # Warning si es consulta grande sin filtros
            if not filter_applied or (queryset_count and queryset_count > 1000):
                logger.warning(f"AUDIT: Consulta global - {log_data}")
            else:
                cls._audit_logger.info(f"AUDIT: Consulta filtrada - {log_data}")
    
    @classmethod
    def log_stock_operation(cls, user, operation: str, producto_id, cantidad,
                           resultado: str, modo: str = None, requisicion_id: int = None):
        """
        ISS-006 FIX: Registra operaciones de stock.
        
        Args:
            user: Usuario que realiza la operación
            operation: Tipo de operación (validacion, revalidacion_envio, etc.)
            producto_id: ID del producto
            cantidad: Cantidad involucrada
            resultado: Resultado (ok, insuficiente, error)
            modo: Modo de validación (estricto, informativo)
            requisicion_id: ID de requisición relacionada (opcional)
        """
        log_data = {
            'event': 'stock_operation',
            'user_id': getattr(user, 'id', None) if user else None,
            'username': getattr(user, 'username', 'unknown') if user else 'system',
            'operation': operation,
            'producto_id': producto_id,
            'cantidad': cantidad,
            'resultado': resultado,
            'modo': modo,
            'requisicion_id': requisicion_id
        }
        
        if resultado in ['insuficiente', 'error', 'failed']:
            logger.warning(f"AUDIT: Operación stock fallida - {log_data}")
        else:
            logger.info(f"AUDIT: Operación stock - {log_data}")
    
    @classmethod
    def log_state_transition(cls, user, model: str, object_id, old_state: str, 
                            new_state: str, motivo: str = None):
        """
        ISS-006 FIX: Registra transiciones de estado.
        
        Args:
            user: Usuario que realiza la transición
            model: Modelo afectado
            object_id: ID del objeto
            old_state: Estado anterior
            new_state: Nuevo estado
            motivo: Motivo de la transición (para cancelaciones)
        """
        log_data = {
            'event': 'state_transition',
            'user_id': getattr(user, 'id', None) if user else None,
            'username': getattr(user, 'username', 'unknown') if user else 'system',
            'model': model,
            'object_id': object_id,
            'old_state': old_state,
            'new_state': new_state,
            'motivo': motivo
        }
        
        # Cancelaciones son warnings
        if new_state and 'cancel' in new_state.lower():
            logger.warning(f"AUDIT: Cancelación - {log_data}")
        else:
            logger.info(f"AUDIT: Transición de estado - {log_data}")
