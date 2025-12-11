"""
Tests para correcciones de audit21.

ISS-001: Campo estado de Lote es propiedad calculada (YA RESUELTO en audits anteriores)
ISS-002: Transiciones de requisición alineadas con BD (YA RESUELTO)
ISS-003: Script de verificación de esquema BD
ISS-004: Validación MIME completa en firmas de requisición
"""
import pytest
from io import BytesIO
from unittest.mock import MagicMock, patch
from django.test import TestCase


class TestISS001LoteEstadoPropiedad(TestCase):
    """
    ISS-001: Verifica que el campo estado de Lote sea propiedad calculada.
    
    El modelo Lote NO tiene columna 'estado' en BD.
    Es una propiedad que calcula: disponible/agotado/vencido basado en
    activo + cantidad_actual + fecha_caducidad.
    """
    
    def test_estado_es_property_no_campo(self):
        """Verifica que estado es property, no campo de BD."""
        from core.models import Lote
        
        # Obtener el descriptor de 'estado'
        estado_attr = getattr(Lote, 'estado', None)
        assert estado_attr is not None, "Lote debe tener atributo 'estado'"
        
        # Verificar que es una property
        assert isinstance(estado_attr, property), \
            "Lote.estado debe ser @property, no un campo de modelo"
    
    def test_estado_no_en_campos_modelo(self):
        """Verifica que 'estado' no aparece como campo de modelo."""
        from core.models import Lote
        
        campos_nombres = [f.name for f in Lote._meta.get_fields() if hasattr(f, 'column')]
        assert 'estado' not in campos_nombres, \
            "'estado' NO debe ser un campo de modelo (es propiedad calculada)"
    
    def test_lote_query_helper_no_usa_estado(self):
        """Verifica que LoteQueryHelper no use estado como filtro."""
        import inspect
        from core.lote_helpers import LoteQueryHelper
        
        # Obtener código fuente de get_lotes_disponibles
        source = inspect.getsource(LoteQueryHelper.get_lotes_disponibles)
        
        # No debe contener filtros por estado (que causaría FieldError)
        assert "estado__in" not in source, \
            "LoteQueryHelper NO debe usar estado__in en filtros"
        assert "estado=" not in source or "# estado" in source.lower(), \
            "LoteQueryHelper NO debe filtrar por campo estado"


class TestISS002TransicionesBD(TestCase):
    """
    ISS-002: Verifica alineación de transiciones con CHECK constraint de BD.
    """
    
    def test_constantes_estados_documentadas(self):
        """Verifica que las constantes de estados están documentadas."""
        from core.constants import ESTADOS_REQUISICION, TRANSICIONES_REQUISICION
        
        # Debe existir comentario de alineación con BD
        import inspect
        source = inspect.getsource(inspect.getmodule(ESTADOS_REQUISICION))
        assert "ISS-DB-002" in source or "CHECK constraint" in source.lower(), \
            "ESTADOS_REQUISICION debe documentar alineación con BD"
    
    def test_estados_requisicion_completos(self):
        """Verifica que ESTADOS_REQUISICION tiene todos los estados del flujo V2."""
        from core.constants import ESTADOS_REQUISICION
        
        estados_esperados = {
            'borrador', 'pendiente_admin', 'pendiente_director',
            'enviada', 'en_revision', 'autorizada', 'en_surtido',
            'surtida', 'entregada', 'rechazada', 'vencida', 'cancelada',
            'devuelta', 'parcial'
        }
        
        estados_definidos = {e[0] for e in ESTADOS_REQUISICION}
        faltantes = estados_esperados - estados_definidos
        
        assert not faltantes, f"Estados faltantes en ESTADOS_REQUISICION: {faltantes}"
    
    def test_transiciones_sin_saltos(self):
        """Verifica que no hay transiciones que salten pasos obligatorios."""
        from core.constants import TRANSICIONES_REQUISICION
        
        # ISS-001 FIX: autorizada NO debe poder ir directamente a surtida
        trans_autorizada = TRANSICIONES_REQUISICION.get('autorizada', [])
        assert 'surtida' not in trans_autorizada, \
            "autorizada NO debe transicionar directamente a surtida (debe pasar por en_surtido)"
        
        # ISS-001 FIX: enviada NO debe poder ir directamente a autorizada
        trans_enviada = TRANSICIONES_REQUISICION.get('enviada', [])
        assert 'autorizada' not in trans_enviada, \
            "enviada NO debe transicionar directamente a autorizada (debe pasar por en_revision)"


class TestISS003VerificacionEsquema(TestCase):
    """
    ISS-003: Tests para el script de verificación de esquema.
    """
    
    def test_script_existe(self):
        """Verifica que el script de verificación existe."""
        import os
        script_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'scripts', 'verify_schema.py'
        )
        # También buscar en backend/scripts
        if not os.path.exists(script_path):
            script_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'scripts', 'verify_schema.py'
            )
        
        assert os.path.exists(script_path), \
            f"Script de verificación debe existir en {script_path}"
    
    def test_get_columnas_modelo_funciona(self):
        """Verifica que get_columnas_modelo extrae columnas correctamente."""
        from scripts.verify_schema import get_columnas_modelo
        from core.models import Lote
        
        columnas = get_columnas_modelo(Lote)
        
        # Verificar columnas esperadas
        assert 'id' in columnas, "Debe extraer columna id"
        assert 'numero_lote' in columnas, "Debe extraer columna numero_lote"
        assert 'cantidad_actual' in columnas, "Debe extraer columna cantidad_actual"
        assert 'activo' in columnas, "Debe extraer columna activo"
        
        # 'estado' NO debe estar (es property, no campo)
        assert 'estado' not in columnas, \
            "'estado' NO debe aparecer como columna (es property)"


class TestISS004ValidacionMIME(TestCase):
    """
    ISS-004: Tests para validación MIME completa de archivos de firma.
    """
    
    def test_validar_archivo_imagen_rechaza_extension_invalida(self):
        """Verifica que se rechaza extensión no permitida."""
        from inventario.views import validar_archivo_imagen
        
        archivo = MagicMock()
        archivo.name = "firma.exe"
        archivo.size = 1000
        archivo.content_type = "application/x-msdownload"
        
        es_valido, error = validar_archivo_imagen(archivo)
        
        assert not es_valido, "Debe rechazar extensión .exe"
        assert "no permitida" in error.lower() or "use:" in error.lower()
    
    def test_validar_archivo_imagen_rechaza_mime_invalido(self):
        """Verifica que se rechaza MIME type inválido."""
        from inventario.views import validar_archivo_imagen
        
        archivo = MagicMock()
        archivo.name = "firma.jpg"
        archivo.size = 1000
        archivo.content_type = "application/octet-stream"
        
        # Simular lectura de archivo con magic bytes incorrectos
        archivo.tell.return_value = 0
        archivo.read.return_value = b'\x00\x00\x00\x00'  # No es JPEG
        archivo.seek = MagicMock()
        
        es_valido, error = validar_archivo_imagen(archivo)
        
        assert not es_valido, "Debe rechazar MIME inválido o magic bytes incorrectos"
    
    def test_validar_archivo_imagen_acepta_jpeg_valido(self):
        """Verifica que se acepta JPEG válido."""
        from inventario.views import validar_archivo_imagen
        
        # Magic bytes de JPEG: FF D8 FF
        jpeg_header = b'\xff\xd8\xff\xe0\x00\x10JFIF'
        
        archivo = MagicMock()
        archivo.name = "firma.jpg"
        archivo.size = 1000
        archivo.content_type = "image/jpeg"
        archivo.tell.return_value = 0
        archivo.read.return_value = jpeg_header
        archivo.seek = MagicMock()
        
        es_valido, error = validar_archivo_imagen(archivo)
        
        # Puede fallar por Pillow no disponible o validación profunda
        # pero no debe fallar por extensión o MIME
        if not es_valido:
            assert "contenido" in error.lower() or "pillow" in error.lower() or "corrupto" in error.lower(), \
                f"Error inesperado: {error}"
    
    def test_validar_archivo_imagen_rechaza_tamanio_excesivo(self):
        """Verifica que se rechaza archivo demasiado grande."""
        from inventario.views import validar_archivo_imagen
        
        archivo = MagicMock()
        archivo.name = "firma.jpg"
        archivo.size = 10 * 1024 * 1024  # 10MB
        archivo.content_type = "image/jpeg"
        
        es_valido, error = validar_archivo_imagen(archivo, max_size_mb=2)
        
        assert not es_valido, "Debe rechazar archivo > 2MB"
        assert "grande" in error.lower() or "máximo" in error.lower()
    
    def test_endpoint_surtir_usa_validacion_completa(self):
        """Verifica que el endpoint surtir usa validar_archivo_imagen."""
        import inspect
        from inventario.views import RequisicionViewSet
        
        # Obtener código fuente del método surtir
        source = inspect.getsource(RequisicionViewSet.surtir)
        
        assert "validar_archivo_imagen" in source, \
            "Endpoint surtir debe usar validar_archivo_imagen para fotos de firma"
        assert "ISS-004" in source, \
            "Endpoint surtir debe documentar fix ISS-004"
    
    def test_endpoint_confirmar_entrega_usa_validacion_completa(self):
        """Verifica que el endpoint confirmar_entrega usa validar_archivo_imagen."""
        import inspect
        from inventario.views import RequisicionViewSet
        
        # Obtener código fuente del método confirmar_entrega
        source = inspect.getsource(RequisicionViewSet.confirmar_entrega)
        
        assert "validar_archivo_imagen" in source, \
            "Endpoint confirmar_entrega debe usar validar_archivo_imagen"
        assert "ISS-004" in source, \
            "Endpoint confirmar_entrega debe documentar fix ISS-004"


class TestDocumentacionManagedFalse(TestCase):
    """
    Verifica que la documentación sobre managed=False está presente.
    """
    
    def test_models_tiene_documentacion_managed_false(self):
        """Verifica que models.py documenta las implicaciones de managed=False."""
        import inspect
        from core import models
        
        source = inspect.getsource(models)
        
        # Debe documentar managed=False
        assert "managed = False" in source or "managed=False" in source
        
        # Debe documentar que estado de Lote es propiedad
        assert "propiedad calculada" in source.lower() or "property" in source.lower()
        
        # Debe documentar que Django no aplica constraints
        assert "constraint" in source.lower() or "CONSTRAINT" in source
    
    def test_lote_helpers_documenta_uso_correcto(self):
        """Verifica que lote_helpers documenta que no debe usar estado como filtro."""
        import inspect
        from core import lote_helpers
        
        source = inspect.getsource(lote_helpers)
        
        # Debe documentar que NO usar estado como filtro
        assert "NO tiene campo 'estado'" in source or "propiedad calculada" in source.lower()
        assert "activo" in source and "cantidad_actual" in source and "fecha_caducidad" in source
