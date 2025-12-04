"""
ISS-015: Generador atómico de folios.

Sistema de generación de folios con protección contra race conditions
usando locks de base de datos y transacciones atómicas.
"""
import logging
from datetime import date
from typing import Optional, Tuple
from django.db import transaction, models
from django.db.models import Max
from django.core.cache import cache

logger = logging.getLogger(__name__)


class FolioGenerator:
    """
    ISS-015: Generador atómico de folios con protección contra concurrencia.
    
    Características:
    - Usa SELECT FOR UPDATE para bloquear registros durante generación
    - Formato configurable por tipo de documento
    - Cache de último folio para optimización
    - Soporte para múltiples tipos de documentos
    """
    
    # Formatos por tipo de documento
    FORMATOS = {
        'requisicion': 'REQ-{centro}-{fecha}-{secuencia:04d}',
        'movimiento': 'MOV-{fecha}-{secuencia:06d}',
        'hoja_recoleccion': 'HR-{centro}-{fecha}-{secuencia:04d}',
        'ajuste': 'AJU-{fecha}-{secuencia:05d}',
    }
    
    # Prefijos para filtrar en BD
    PREFIJOS = {
        'requisicion': 'REQ',
        'movimiento': 'MOV',
        'hoja_recoleccion': 'HR',
        'ajuste': 'AJU',
    }
    
    def __init__(self, tipo_documento: str = 'requisicion'):
        """
        Inicializa el generador.
        
        Args:
            tipo_documento: Tipo de documento ('requisicion', 'movimiento', etc.)
        """
        if tipo_documento not in self.FORMATOS:
            raise ValueError(f"Tipo de documento no soportado: {tipo_documento}")
        
        self.tipo = tipo_documento
        self.formato = self.FORMATOS[tipo_documento]
        self.prefijo = self.PREFIJOS[tipo_documento]
    
    def _get_fecha_str(self) -> str:
        """Retorna fecha actual en formato YYYYMMDD."""
        return date.today().strftime('%Y%m%d')
    
    def _get_cache_key(self, prefijo_completo: str) -> str:
        """Genera key de cache para un prefijo de folio."""
        return f"folio_seq:{prefijo_completo}"
    
    def _extraer_secuencia(self, folio: str) -> int:
        """
        Extrae el número de secuencia de un folio.
        
        Args:
            folio: Folio completo (ej: 'REQ-CTR-20251204-0001')
        
        Returns:
            int: Número de secuencia extraído
        """
        try:
            # El número de secuencia siempre es la última parte
            partes = folio.split('-')
            return int(partes[-1])
        except (ValueError, IndexError):
            return 0
    
    @transaction.atomic
    def generar(
        self,
        modelo_class,
        campo_folio: str = 'folio',
        centro_codigo: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        ISS-015: Genera un folio único de forma atómica.
        
        Usa SELECT FOR UPDATE para garantizar exclusividad incluso
        bajo alta concurrencia.
        
        Args:
            modelo_class: Clase del modelo Django (ej: Requisicion)
            campo_folio: Nombre del campo de folio en el modelo
            centro_codigo: Código del centro (requerido para algunos tipos)
            **kwargs: Argumentos adicionales para el formato
        
        Returns:
            str: Folio único generado
        
        Raises:
            ValueError: Si faltan datos requeridos
        """
        fecha_str = self._get_fecha_str()
        centro_str = (centro_codigo or 'GEN')[:3].upper()
        
        # Construir prefijo para este día/centro
        if self.tipo == 'requisicion':
            prefijo = f"REQ-{centro_str}-{fecha_str}"
        elif self.tipo == 'movimiento':
            prefijo = f"MOV-{fecha_str}"
        elif self.tipo == 'hoja_recoleccion':
            prefijo = f"HR-{centro_str}-{fecha_str}"
        elif self.tipo == 'ajuste':
            prefijo = f"AJU-{fecha_str}"
        else:
            prefijo = f"{self.prefijo}-{fecha_str}"
        
        # Intentar obtener secuencia de cache primero
        cache_key = self._get_cache_key(prefijo)
        cached_seq = cache.get(cache_key)
        
        # ISS-015: SELECT FOR UPDATE para bloquear registros del prefijo
        filtro = {f'{campo_folio}__startswith': prefijo}
        
        # Bloquear filas existentes y obtener máximo
        ultimo_registro = (
            modelo_class.objects
            .select_for_update(nowait=False)  # Esperar si hay bloqueo
            .filter(**filtro)
            .order_by(f'-{campo_folio}')
            .first()
        )
        
        if ultimo_registro:
            ultimo_folio = getattr(ultimo_registro, campo_folio)
            ultima_secuencia = self._extraer_secuencia(ultimo_folio)
        else:
            ultima_secuencia = 0
        
        # Si cache tiene valor mayor, usar ese (puede haber registros eliminados)
        if cached_seq and cached_seq > ultima_secuencia:
            ultima_secuencia = cached_seq
        
        nueva_secuencia = ultima_secuencia + 1
        
        # Actualizar cache
        cache.set(cache_key, nueva_secuencia, timeout=86400)  # 24 horas
        
        # Generar folio según formato
        if self.tipo == 'requisicion':
            folio = f"{prefijo}-{nueva_secuencia:04d}"
        elif self.tipo == 'movimiento':
            folio = f"{prefijo}-{nueva_secuencia:06d}"
        elif self.tipo == 'hoja_recoleccion':
            folio = f"{prefijo}-{nueva_secuencia:04d}"
        elif self.tipo == 'ajuste':
            folio = f"{prefijo}-{nueva_secuencia:05d}"
        else:
            folio = f"{prefijo}-{nueva_secuencia:04d}"
        
        logger.info(f"ISS-015: Folio generado atómicamente: {folio}")
        return folio
    
    @classmethod
    def generar_folio_requisicion(cls, centro_codigo: str) -> str:
        """
        Helper para generar folio de requisición.
        
        Args:
            centro_codigo: Código del centro solicitante
        
        Returns:
            str: Folio único para requisición
        """
        from core.models import Requisicion
        
        generator = cls('requisicion')
        return generator.generar(
            modelo_class=Requisicion,
            campo_folio='folio',
            centro_codigo=centro_codigo
        )
    
    @classmethod
    def generar_folio_movimiento(cls) -> str:
        """
        Helper para generar folio de movimiento.
        
        Returns:
            str: Folio único para movimiento
        """
        from core.models import Movimiento
        
        generator = cls('movimiento')
        # Los movimientos no tienen folio en el modelo actual,
        # pero se puede usar para documento_referencia
        fecha_str = date.today().strftime('%Y%m%d')
        
        # Usar contador en cache para movimientos
        cache_key = f"mov_seq:{fecha_str}"
        seq = cache.get(cache_key, 0) + 1
        cache.set(cache_key, seq, timeout=86400)
        
        return f"MOV-{fecha_str}-{seq:06d}"


def generar_folio_atomico(
    modelo_class,
    tipo: str = 'requisicion',
    centro_codigo: Optional[str] = None,
    campo_folio: str = 'folio'
) -> str:
    """
    ISS-015: Función helper para generación atómica de folios.
    
    Uso:
        folio = generar_folio_atomico(Requisicion, 'requisicion', 'CTR-001')
    
    Args:
        modelo_class: Clase del modelo
        tipo: Tipo de documento
        centro_codigo: Código del centro (opcional)
        campo_folio: Nombre del campo de folio
    
    Returns:
        str: Folio único generado
    """
    generator = FolioGenerator(tipo)
    return generator.generar(
        modelo_class=modelo_class,
        campo_folio=campo_folio,
        centro_codigo=centro_codigo
    )


class FolioMixin:
    """
    ISS-015: Mixin para modelos que necesitan generación atómica de folios.
    
    Uso:
        class Requisicion(FolioMixin, models.Model):
            FOLIO_TIPO = 'requisicion'
            FOLIO_CAMPO = 'folio'
            ...
    """
    
    FOLIO_TIPO: str = 'requisicion'
    FOLIO_CAMPO: str = 'folio'
    
    def generar_folio(self, centro_codigo: Optional[str] = None) -> str:
        """
        Genera folio único para esta instancia.
        
        Args:
            centro_codigo: Código del centro (si aplica)
        
        Returns:
            str: Folio generado
        """
        generator = FolioGenerator(self.FOLIO_TIPO)
        return generator.generar(
            modelo_class=self.__class__,
            campo_folio=self.FOLIO_CAMPO,
            centro_codigo=centro_codigo
        )
