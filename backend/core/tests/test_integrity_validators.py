"""
Tests para IntegrityValidator - ISS-001 FIX (audit17)

Estos tests verifican las validaciones de integridad de datos
que reemplazan las constraints de BD en modelos managed=False.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from django.core.exceptions import ValidationError
from datetime import date, timedelta
from decimal import Decimal


class TestIntegrityValidatorUnicidad:
    """Tests para validaciones de unicidad."""
    
    def test_clave_producto_unica_cuando_no_existe(self):
        """Clave de producto es válida si no existe."""
        from core.validators import IntegrityValidator
        
        with patch('core.models.Producto.objects.filter') as mock_filter:
            mock_filter.return_value.exclude.return_value.exists.return_value = False
            mock_filter.return_value.exists.return_value = False
            
            result = IntegrityValidator.validate_unique_clave_producto(
                'NUEVO-001', 
                instance=None, 
                raise_exception=False
            )
            assert result is True
    
    def test_clave_producto_duplicada_falla(self):
        """Clave de producto duplicada lanza error."""
        from core.validators import IntegrityValidator
        
        with patch('core.models.Producto.objects.filter') as mock_filter:
            mock_filter.return_value.exclude.return_value.exists.return_value = True
            mock_filter.return_value.exists.return_value = True
            
            result = IntegrityValidator.validate_unique_clave_producto(
                'EXISTENTE-001', 
                instance=None, 
                raise_exception=False
            )
            assert result is False
    
    def test_clave_producto_edicion_propia(self):
        """Editar producto con su propia clave es válido."""
        from core.validators import IntegrityValidator
        
        instance = Mock()
        instance.pk = 123
        
        with patch('core.models.Producto.objects.filter') as mock_filter:
            # La consulta excluye el pk propio
            mock_qs = mock_filter.return_value
            mock_qs.exclude.return_value.exists.return_value = False
            
            result = IntegrityValidator.validate_unique_clave_producto(
                'MI-CLAVE', 
                instance=instance, 
                raise_exception=False
            )
            # Verificar que se llamó exclude con el pk
            mock_qs.exclude.assert_called_once_with(pk=123)
    
    def test_numero_lote_unico_por_producto(self):
        """Número de lote debe ser único dentro del mismo producto."""
        from core.validators import IntegrityValidator
        
        with patch('core.models.Lote.objects.filter') as mock_filter:
            mock_filter.return_value.exclude.return_value.exists.return_value = False
            mock_filter.return_value.exists.return_value = False
            
            result = IntegrityValidator.validate_unique_numero_lote(
                'LOT-001', 
                producto_id=1, 
                instance=None, 
                raise_exception=False
            )
            assert result is True
            
            # Verificar que filtró por producto_id
            mock_filter.assert_called()
    
    def test_folio_requisicion_unico(self):
        """Folio de requisición debe ser único."""
        from core.validators import IntegrityValidator
        
        with patch('core.models.Requisicion.objects.filter') as mock_filter:
            mock_filter.return_value.exists.return_value = False
            mock_filter.return_value.exclude.return_value.exists.return_value = False
            
            result = IntegrityValidator.validate_unique_folio_requisicion(
                'REQ-2024-001', 
                instance=None, 
                raise_exception=False
            )
            assert result is True


class TestIntegrityValidatorForeignKeys:
    """Tests para validaciones de foreign keys."""
    
    def test_fk_existe_cuando_existe(self):
        """FK válida si el registro existe."""
        from core.validators import IntegrityValidator
        
        mock_model = Mock()
        mock_model.objects.filter.return_value.exists.return_value = True
        
        result = IntegrityValidator.validate_fk_exists(
            mock_model, 
            pk=1, 
            field_name='producto', 
            raise_exception=False
        )
        assert result is True
    
    def test_fk_no_existe_falla(self):
        """FK inválida si el registro no existe."""
        from core.validators import IntegrityValidator
        
        mock_model = Mock()
        mock_model.objects.filter.return_value.exists.return_value = False
        mock_model.__name__ = 'Producto'
        
        result = IntegrityValidator.validate_fk_exists(
            mock_model, 
            pk=999, 
            field_name='producto', 
            raise_exception=False
        )
        assert result is False
    
    def test_fk_null_es_valida(self):
        """FK null se considera válida (se valida por separado)."""
        from core.validators import IntegrityValidator
        
        mock_model = Mock()
        
        result = IntegrityValidator.validate_fk_exists(
            mock_model, 
            pk=None, 
            field_name='producto', 
            raise_exception=False
        )
        assert result is True
    
    def test_validate_producto_exists(self):
        """Método helper para validar producto."""
        from core.validators import IntegrityValidator
        
        with patch('core.models.Producto.objects.filter') as mock_filter:
            mock_filter.return_value.exists.return_value = True
            
            result = IntegrityValidator.validate_producto_exists(1, raise_exception=False)
            assert result is True
    
    def test_validate_centro_exists(self):
        """Método helper para validar centro."""
        from core.validators import IntegrityValidator
        
        with patch('core.models.Centro.objects.filter') as mock_filter:
            mock_filter.return_value.exists.return_value = True
            
            result = IntegrityValidator.validate_centro_exists(1, raise_exception=False)
            assert result is True


class TestIntegrityValidatorChecks:
    """Tests para validaciones de checks de negocio."""
    
    def test_cantidad_positiva_valida(self):
        """Cantidad positiva es válida."""
        from core.validators import IntegrityValidator
        
        assert IntegrityValidator.validate_cantidad_positiva(10, 'cantidad', False) is True
        assert IntegrityValidator.validate_cantidad_positiva(0, 'cantidad', False) is True
        assert IntegrityValidator.validate_cantidad_positiva(1, 'cantidad', False) is True
    
    def test_cantidad_negativa_falla(self):
        """Cantidad negativa es inválida."""
        from core.validators import IntegrityValidator
        
        assert IntegrityValidator.validate_cantidad_positiva(-1, 'cantidad', False) is False
        assert IntegrityValidator.validate_cantidad_positiva(-100, 'cantidad', False) is False
    
    def test_cantidad_none_valida(self):
        """Cantidad None se considera válida (se valida por separado)."""
        from core.validators import IntegrityValidator
        
        assert IntegrityValidator.validate_cantidad_positiva(None, 'cantidad', False) is True
    
    def test_stock_negativo_detectado(self):
        """Detecta cuando una salida dejaría stock negativo."""
        from core.validators import IntegrityValidator
        
        with patch('core.models.Producto.objects.get') as mock_get:
            producto = Mock()
            producto.get_stock_farmacia_central.return_value = 5
            mock_get.return_value = producto
            
            # Intentar sacar más de lo disponible
            result = IntegrityValidator.validate_stock_no_negativo(
                producto_id=1, 
                cantidad_salida=10, 
                centro_id=None, 
                raise_exception=False
            )
            assert result is False
    
    def test_stock_suficiente_valido(self):
        """Stock suficiente es válido."""
        from core.validators import IntegrityValidator
        
        with patch('core.models.Producto.objects.get') as mock_get:
            producto = Mock()
            producto.get_stock_farmacia_central.return_value = 20
            mock_get.return_value = producto
            
            result = IntegrityValidator.validate_stock_no_negativo(
                producto_id=1, 
                cantidad_salida=10, 
                centro_id=None, 
                raise_exception=False
            )
            assert result is True
    
    def test_fecha_vencimiento_futura_valida(self):
        """Fecha de vencimiento futura es válida."""
        from core.validators import IntegrityValidator
        
        fecha_futura = date.today() + timedelta(days=30)
        
        result = IntegrityValidator.validate_fecha_vencimiento_futura(
            fecha_futura, 
            raise_exception=False
        )
        assert result is True
    
    def test_fecha_vencimiento_pasada_falla(self):
        """Fecha de vencimiento pasada es inválida."""
        from core.validators import IntegrityValidator
        
        fecha_pasada = date.today() - timedelta(days=1)
        
        result = IntegrityValidator.validate_fecha_vencimiento_futura(
            fecha_pasada, 
            raise_exception=False
        )
        assert result is False
    
    def test_fecha_vencimiento_hoy_valida(self):
        """Fecha de vencimiento hoy es válida (vence al final del día)."""
        from core.validators import IntegrityValidator
        
        fecha_hoy = date.today()
        
        result = IntegrityValidator.validate_fecha_vencimiento_futura(
            fecha_hoy, 
            raise_exception=False
        )
        # Depende de la implementación - en este caso sí es válida
        assert result is True


class TestIntegrityValidatorCompuestas:
    """Tests para validaciones compuestas."""
    
    def test_validate_producto_integrity_completa(self):
        """Validación completa de producto."""
        from core.validators import IntegrityValidator
        
        with patch.object(IntegrityValidator, 'validate_unique_clave_producto') as mock_unique:
            mock_unique.return_value = True
            
            data = {
                'clave': 'PROD-001',
                'precio_unitario': Decimal('100.00')
            }
            
            # No debería lanzar excepción
            try:
                IntegrityValidator.validate_producto_integrity(data, instance=None)
                validacion_ok = True
            except ValidationError:
                validacion_ok = False
            
            assert validacion_ok is True
    
    def test_validate_producto_integrity_precio_negativo(self):
        """Precio negativo es inválido."""
        from core.validators import IntegrityValidator
        
        with patch.object(IntegrityValidator, 'validate_unique_clave_producto') as mock_unique:
            mock_unique.return_value = True
            
            data = {
                'clave': 'PROD-001',
                'precio_unitario': Decimal('-50.00')
            }
            
            with pytest.raises(ValidationError) as exc_info:
                IntegrityValidator.validate_producto_integrity(data, instance=None)
            
            assert 'precio_unitario' in exc_info.value.message_dict
    
    def test_validate_lote_integrity_completa(self):
        """Validación completa de lote."""
        from core.validators import IntegrityValidator
        
        with patch.object(IntegrityValidator, 'validate_producto_exists') as mock_producto:
            with patch.object(IntegrityValidator, 'validate_unique_numero_lote') as mock_lote:
                with patch.object(IntegrityValidator, 'validate_cantidad_positiva') as mock_cantidad:
                    with patch.object(IntegrityValidator, 'validate_fecha_vencimiento_futura') as mock_fecha:
                        mock_producto.return_value = True
                        mock_lote.return_value = True
                        mock_cantidad.return_value = True
                        mock_fecha.return_value = True
                        
                        data = {
                            'producto_id': 1,
                            'numero_lote': 'LOT-001',
                            'cantidad_actual': 100,
                            'fecha_vencimiento': date.today() + timedelta(days=365)
                        }
                        
                        # No debería lanzar excepción
                        try:
                            IntegrityValidator.validate_lote_integrity(data, instance=None)
                            validacion_ok = True
                        except ValidationError:
                            validacion_ok = False
                        
                        assert validacion_ok is True
    
    def test_validate_movimiento_integrity(self):
        """Validación de integridad de movimiento."""
        from core.validators import IntegrityValidator
        
        # Movimiento de entrada debe tener cantidad positiva
        data_entrada = {
            'producto_id': 1,
            'tipo': 'entrada',
            'cantidad': 10
        }
        
        with patch.object(IntegrityValidator, 'validate_producto_exists') as mock_prod:
            mock_prod.return_value = True
            
            # No debería lanzar excepción
            try:
                IntegrityValidator.validate_movimiento_integrity(data_entrada)
                validacion_ok = True
            except ValidationError:
                validacion_ok = False
            
            assert validacion_ok is True
    
    def test_validate_movimiento_salida_positiva_falla(self):
        """Salida con cantidad positiva es inválida."""
        from core.validators import IntegrityValidator
        
        data_salida = {
            'producto_id': 1,
            'tipo': 'salida',
            'cantidad': 10  # Debería ser negativo
        }
        
        with patch.object(IntegrityValidator, 'validate_producto_exists') as mock_prod:
            mock_prod.return_value = True
            
            with pytest.raises(ValidationError) as exc_info:
                IntegrityValidator.validate_movimiento_integrity(data_salida)
            
            assert 'cantidad' in exc_info.value.message_dict


class TestIntegrityValidatorExcepciones:
    """Tests para comportamiento de excepciones."""
    
    def test_raise_exception_true_lanza(self):
        """Con raise_exception=True, se lanza ValidationError."""
        from core.validators import IntegrityValidator
        
        with patch('core.models.Producto.objects.filter') as mock_filter:
            mock_filter.return_value.exists.return_value = True
            mock_filter.return_value.exclude.return_value.exists.return_value = True
            
            with pytest.raises(ValidationError):
                IntegrityValidator.validate_unique_clave_producto(
                    'EXISTENTE', 
                    instance=None, 
                    raise_exception=True
                )
    
    def test_raise_exception_false_retorna_bool(self):
        """Con raise_exception=False, retorna False en lugar de lanzar."""
        from core.validators import IntegrityValidator
        
        with patch('core.models.Producto.objects.filter') as mock_filter:
            mock_filter.return_value.exists.return_value = True
            mock_filter.return_value.exclude.return_value.exists.return_value = True
            
            result = IntegrityValidator.validate_unique_clave_producto(
                'EXISTENTE', 
                instance=None, 
                raise_exception=False
            )
            assert result is False
