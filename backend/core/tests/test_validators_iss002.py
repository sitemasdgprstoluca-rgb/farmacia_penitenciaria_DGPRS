"""
ISS-002 FIX: Tests para validadores de archivos/imágenes.

Valida que los validadores manejen correctamente:
- Valores None
- Archivos vacíos
- Tamaños excedidos
- Casos límite

Corrige hueco de pruebas identificado en auditoría de calidad.
"""
import pytest
from unittest.mock import Mock, MagicMock
from django.core.exceptions import ValidationError

from core.models import (
    validate_image_size,
    validate_image_max_size,
    validate_logo_size,
    validate_firma_path,
    requisicion_firma_path,
)


class TestValidateImageSize:
    """Tests para validate_image_size - ISS-002 FIX"""
    
    def test_none_value_returns_none(self):
        """ISS-002: Debe retornar sin error cuando value es None"""
        # No debe lanzar excepción
        result = validate_image_size(None)
        assert result is None
    
    def test_empty_value_returns_none(self):
        """ISS-002: Debe retornar sin error cuando value es falsy"""
        result = validate_image_size('')
        assert result is None
        
        result = validate_image_size(0)
        assert result is None
    
    def test_valid_size_passes(self):
        """Archivo dentro del límite debe pasar"""
        mock_file = Mock()
        mock_file.size = 1 * 1024 * 1024  # 1 MB
        
        # No debe lanzar excepción
        result = validate_image_size(mock_file)
        assert result is None
    
    def test_exactly_2mb_passes(self):
        """Archivo de exactamente 2MB debe pasar"""
        mock_file = Mock()
        mock_file.size = 2 * 1024 * 1024  # 2 MB exactos
        
        # No debe lanzar excepción
        result = validate_image_size(mock_file)
        assert result is None
    
    def test_exceeds_2mb_raises_error(self):
        """Archivo mayor a 2MB debe lanzar ValidationError"""
        mock_file = Mock()
        mock_file.size = 3 * 1024 * 1024  # 3 MB
        
        with pytest.raises(ValidationError) as exc_info:
            validate_image_size(mock_file)
        
        assert '2MB' in str(exc_info.value)
    
    def test_slightly_over_2mb_raises_error(self):
        """Archivo apenas sobre 2MB debe lanzar ValidationError"""
        mock_file = Mock()
        mock_file.size = 2 * 1024 * 1024 + 1  # 2 MB + 1 byte
        
        with pytest.raises(ValidationError):
            validate_image_size(mock_file)


class TestValidateImageMaxSize:
    """Tests para validate_image_max_size con tamaño configurable"""
    
    def test_none_value_with_explicit_check(self):
        """Debe manejar None con check explícito en valor"""
        # El validador tiene `if value:` al inicio
        mock_file = None
        
        # No debe lanzar excepción
        result = validate_image_max_size(mock_file, max_size_kb=500)
        assert result is None
    
    def test_custom_max_size_500kb(self):
        """Validar con límite personalizado de 500KB"""
        mock_file = Mock()
        mock_file.size = 400 * 1024  # 400 KB
        
        # Debe pasar
        result = validate_image_max_size(mock_file, max_size_kb=500)
        assert result is None
    
    def test_custom_max_size_exceeds_raises(self):
        """Archivo que excede límite personalizado debe fallar"""
        mock_file = Mock()
        mock_file.size = 600 * 1024  # 600 KB
        
        with pytest.raises(ValidationError) as exc_info:
            validate_image_max_size(mock_file, max_size_kb=500)
        
        assert '500KB' in str(exc_info.value)


class TestValidateLogoSize:
    """Tests para validate_logo_size (wrapper de validate_image_max_size)"""
    
    def test_logo_under_500kb_passes(self):
        """Logo menor a 500KB debe pasar"""
        mock_file = Mock()
        mock_file.size = 300 * 1024  # 300 KB
        
        result = validate_logo_size(mock_file)
        assert result is None
    
    def test_logo_over_500kb_fails(self):
        """Logo mayor a 500KB debe fallar"""
        mock_file = Mock()
        mock_file.size = 600 * 1024  # 600 KB
        
        with pytest.raises(ValidationError):
            validate_logo_size(mock_file)
    
    def test_logo_none_value(self):
        """Logo con valor None debe pasar"""
        result = validate_logo_size(None)
        assert result is None


class TestValidateFirmaPath:
    """Tests para validate_firma_path - validación de rutas seguras"""
    
    def test_none_value_passes(self):
        """Ruta None debe pasar (campo opcional)"""
        result = validate_firma_path(None)
        assert result is None
    
    def test_empty_string_passes(self):
        """Ruta vacía debe pasar"""
        result = validate_firma_path('')
        assert result is None
    
    def test_valid_path_passes(self):
        """Ruta válida debe pasar"""
        result = validate_firma_path('requisiciones/firmas/REQ001_20231215.jpg')
        assert result is None
    
    def test_path_traversal_blocked(self):
        """Path traversal debe ser bloqueado"""
        with pytest.raises(ValidationError):
            validate_firma_path('../../../etc/passwd')
    
    def test_double_dot_blocked(self):
        """Doble punto en ruta debe ser bloqueado"""
        with pytest.raises(ValidationError):
            validate_firma_path('firmas/..hidden/file.jpg')
    
    def test_backslash_blocked(self):
        """Backslash debe ser bloqueado"""
        with pytest.raises(ValidationError):
            validate_firma_path('firmas\\..\\secret.jpg')
    
    def test_null_byte_blocked(self):
        """Null byte debe ser bloqueado"""
        with pytest.raises(ValidationError):
            validate_firma_path('firma.jpg\x00.exe')
    
    def test_invalid_extension_blocked(self):
        """Extensiones no permitidas deben ser bloqueadas"""
        with pytest.raises(ValidationError):
            validate_firma_path('firma.exe')
        
        with pytest.raises(ValidationError):
            validate_firma_path('firma.php')


class TestRequisicionFirmaPath:
    """Tests para requisicion_firma_path - generación de rutas seguras"""
    
    def test_generates_safe_path(self):
        """Debe generar ruta con formato seguro"""
        mock_instance = Mock()
        mock_instance.folio = 'REQ-2023-001'
        
        path = requisicion_firma_path(mock_instance, 'foto.jpg')
        
        assert path.startswith('requisiciones/firmas/')
        assert 'REQ-2023-001' in path
        assert path.endswith('.jpg')
    
    def test_sanitizes_folio(self):
        """Debe sanitizar caracteres peligrosos del folio"""
        mock_instance = Mock()
        mock_instance.folio = '../../../etc/passwd'
        
        path = requisicion_firma_path(mock_instance, 'foto.jpg')
        
        # No debe contener caracteres de path traversal
        assert '..' not in path
        assert '/' not in path.split('/')[-1].split('_')[0] or 'REQ' in path
    
    def test_handles_invalid_extension(self):
        """Debe usar extensión por defecto si la original es inválida"""
        mock_instance = Mock()
        mock_instance.folio = 'REQ001'
        
        path = requisicion_firma_path(mock_instance, 'file.exe')
        
        # Debe usar .jpg como fallback
        assert path.endswith('.jpg')
    
    def test_handles_none_folio(self):
        """Debe manejar folio None"""
        mock_instance = Mock()
        mock_instance.folio = None
        
        path = requisicion_firma_path(mock_instance, 'foto.png')
        
        assert path.startswith('requisiciones/firmas/')
        assert 'REQ' in path  # Usa default 'REQ'
    
    def test_valid_extensions_preserved(self):
        """Extensiones válidas deben preservarse"""
        mock_instance = Mock()
        mock_instance.folio = 'REQ001'
        
        for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            path = requisicion_firma_path(mock_instance, f'foto{ext}')
            assert path.endswith(ext)
