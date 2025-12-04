"""
ISS-007: Detalle de errores en importación.
ISS-031: Sanitización de archivos importados.

Sistema de importación seguro con manejo detallado de errores
y sanitización de datos.
"""
import logging
import re
import html
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum

from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Severidad de errores de importación."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Categorías de errores de importación."""
    FORMATO = "formato"
    VALIDACION = "validacion"
    DUPLICADO = "duplicado"
    REFERENCIA = "referencia"
    SEGURIDAD = "seguridad"
    SISTEMA = "sistema"


@dataclass
class ImportError:
    """Detalle de un error de importación."""
    fila: int
    columna: Optional[str]
    valor_original: Any
    categoria: ErrorCategory
    severidad: ErrorSeverity
    mensaje: str
    sugerencia: Optional[str] = None
    campo_afectado: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'fila': self.fila,
            'columna': self.columna,
            'valor_original': str(self.valor_original)[:100],
            'categoria': self.categoria.value,
            'severidad': self.severidad.value,
            'mensaje': self.mensaje,
            'sugerencia': self.sugerencia,
            'campo_afectado': self.campo_afectado,
        }


@dataclass
class ImportResult:
    """Resultado completo de una importación."""
    exitoso: bool
    registros_procesados: int
    registros_exitosos: int
    registros_fallidos: int
    registros_actualizados: int
    errores: List[ImportError] = field(default_factory=list)
    advertencias: List[ImportError] = field(default_factory=list)
    tiempo_proceso_segundos: float = 0.0
    
    @property
    def resumen(self) -> Dict[str, Any]:
        return {
            'exitoso': self.exitoso,
            'total_procesados': self.registros_procesados,
            'exitosos': self.registros_exitosos,
            'fallidos': self.registros_fallidos,
            'actualizados': self.registros_actualizados,
            'total_errores': len(self.errores),
            'total_advertencias': len(self.advertencias),
            'tiempo_segundos': round(self.tiempo_proceso_segundos, 2),
        }
    
    def agregar_error(self, error: ImportError):
        if error.severidad in (ErrorSeverity.ERROR, ErrorSeverity.CRITICAL):
            self.errores.append(error)
        else:
            self.advertencias.append(error)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **self.resumen,
            'errores': [e.to_dict() for e in self.errores[:50]],  # Limitar a 50
            'advertencias': [e.to_dict() for e in self.advertencias[:50]],
        }


class DataSanitizer:
    """
    ISS-031: Sanitizador de datos de importación.
    
    Limpia y valida datos de entrada para prevenir:
    - Inyección de fórmulas Excel
    - XSS en datos de texto
    - SQL Injection (aunque Django lo maneja)
    - Caracteres de control maliciosos
    """
    
    # Caracteres que indican fórmulas Excel
    FORMULA_CHARS = ('=', '+', '-', '@', '\t', '\r', '\n')
    
    # Patrones peligrosos en texto
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'data:text/html',
    ]
    
    # Caracteres de control (excepto newline/tab comunes)
    CONTROL_CHARS = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
    
    @classmethod
    def sanitize_string(cls, value: Any, max_length: int = 500) -> str:
        """
        ISS-031: Sanitiza un valor de texto.
        
        Args:
            value: Valor a sanitizar
            max_length: Longitud máxima permitida
            
        Returns:
            Texto sanitizado
        """
        if value is None:
            return ""
        
        text = str(value).strip()
        
        # Eliminar caracteres de control
        text = cls.CONTROL_CHARS.sub('', text)
        
        # Prevenir fórmulas Excel
        if text and text[0] in cls.FORMULA_CHARS:
            text = "'" + text  # Escapar con apóstrofo
        
        # Escapar HTML
        text = html.escape(text)
        
        # Truncar si excede longitud
        if len(text) > max_length:
            text = text[:max_length]
        
        return text
    
    @classmethod
    def sanitize_numeric(
        cls,
        value: Any,
        allow_negative: bool = False,
        max_value: Optional[float] = None
    ) -> Tuple[Optional[Decimal], Optional[str]]:
        """
        ISS-031: Sanitiza un valor numérico.
        
        Returns:
            Tuple de (valor_sanitizado, mensaje_error)
        """
        if value is None or str(value).strip() == '':
            return None, None
        
        try:
            # Limpiar formato numérico
            text = str(value).strip()
            text = text.replace(',', '')  # Remover separadores de miles
            text = text.replace('$', '')  # Remover símbolo de moneda
            text = text.replace(' ', '')
            
            num = Decimal(text)
            
            if not allow_negative and num < 0:
                return None, "No se permiten valores negativos"
            
            if max_value and num > max_value:
                return None, f"Valor excede el máximo permitido ({max_value})"
            
            return num, None
            
        except (InvalidOperation, ValueError) as e:
            return None, f"Valor numérico inválido: {value}"
    
    @classmethod
    def sanitize_integer(
        cls,
        value: Any,
        allow_negative: bool = False,
        min_value: int = 0,
        max_value: int = 999999999
    ) -> Tuple[Optional[int], Optional[str]]:
        """
        ISS-031: Sanitiza un valor entero.
        """
        decimal_val, error = cls.sanitize_numeric(value, allow_negative)
        
        if error:
            return None, error
        
        if decimal_val is None:
            return None, None
        
        try:
            int_val = int(decimal_val)
            
            if int_val < min_value:
                return None, f"Valor menor al mínimo permitido ({min_value})"
            
            if int_val > max_value:
                return None, f"Valor mayor al máximo permitido ({max_value})"
            
            return int_val, None
            
        except (ValueError, OverflowError):
            return None, f"No se puede convertir a entero: {value}"
    
    @classmethod
    def sanitize_date(
        cls,
        value: Any,
        formats: List[str] = None
    ) -> Tuple[Optional[date], Optional[str]]:
        """
        ISS-031: Sanitiza un valor de fecha.
        """
        if value is None or str(value).strip() == '':
            return None, None
        
        if isinstance(value, date):
            return value, None
        
        if isinstance(value, datetime):
            return value.date(), None
        
        formats = formats or [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%Y/%m/%d',
            '%d.%m.%Y',
        ]
        
        text = str(value).strip()
        
        for fmt in formats:
            try:
                return datetime.strptime(text, fmt).date(), None
            except ValueError:
                continue
        
        return None, f"Formato de fecha no reconocido: {value}"
    
    @classmethod
    def sanitize_clave(cls, value: Any, max_length: int = 50) -> str:
        """
        ISS-031: Sanitiza una clave/código.
        Solo permite alfanuméricos, guiones y guiones bajos.
        """
        if value is None:
            return ""
        
        text = str(value).strip().upper()
        
        # Remover caracteres no permitidos
        text = re.sub(r'[^A-Z0-9\-_]', '', text)
        
        return text[:max_length]
    
    @classmethod
    def detectar_contenido_malicioso(cls, text: str) -> List[str]:
        """
        ISS-031: Detecta patrones potencialmente maliciosos.
        
        Returns:
            Lista de patrones detectados
        """
        problemas = []
        
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                problemas.append(f"Patrón sospechoso detectado: {pattern}")
        
        # Verificar caracteres de control
        if cls.CONTROL_CHARS.search(text):
            problemas.append("Caracteres de control detectados")
        
        return problemas


class ImportErrorCollector:
    """
    ISS-007: Colector de errores de importación.
    
    Agrupa y organiza errores para reportes detallados.
    """
    
    def __init__(self, max_errores: int = 1000):
        self.errores: List[ImportError] = []
        self.advertencias: List[ImportError] = []
        self.max_errores = max_errores
        self._truncado = False
    
    def agregar(
        self,
        fila: int,
        columna: str,
        valor: Any,
        categoria: ErrorCategory,
        severidad: ErrorSeverity,
        mensaje: str,
        sugerencia: str = None,
        campo: str = None
    ):
        """Agrega un error/advertencia."""
        error = ImportError(
            fila=fila,
            columna=columna,
            valor_original=valor,
            categoria=categoria,
            severidad=severidad,
            mensaje=mensaje,
            sugerencia=sugerencia,
            campo_afectado=campo
        )
        
        if severidad in (ErrorSeverity.ERROR, ErrorSeverity.CRITICAL):
            if len(self.errores) < self.max_errores:
                self.errores.append(error)
            else:
                self._truncado = True
        else:
            if len(self.advertencias) < self.max_errores:
                self.advertencias.append(error)
    
    def error_formato(
        self,
        fila: int,
        columna: str,
        valor: Any,
        mensaje: str,
        sugerencia: str = None
    ):
        """Registra error de formato."""
        self.agregar(
            fila, columna, valor,
            ErrorCategory.FORMATO,
            ErrorSeverity.ERROR,
            mensaje, sugerencia
        )
    
    def error_validacion(
        self,
        fila: int,
        columna: str,
        valor: Any,
        mensaje: str,
        sugerencia: str = None,
        campo: str = None
    ):
        """Registra error de validación."""
        self.agregar(
            fila, columna, valor,
            ErrorCategory.VALIDACION,
            ErrorSeverity.ERROR,
            mensaje, sugerencia, campo
        )
    
    def error_duplicado(
        self,
        fila: int,
        columna: str,
        valor: Any,
        mensaje: str = None
    ):
        """Registra error de duplicado."""
        self.agregar(
            fila, columna, valor,
            ErrorCategory.DUPLICADO,
            ErrorSeverity.ERROR,
            mensaje or f"Valor duplicado: {valor}",
            "Verifique que no exista otro registro con este valor"
        )
    
    def error_referencia(
        self,
        fila: int,
        columna: str,
        valor: Any,
        entidad: str
    ):
        """Registra error de referencia no encontrada."""
        self.agregar(
            fila, columna, valor,
            ErrorCategory.REFERENCIA,
            ErrorSeverity.ERROR,
            f"{entidad} no encontrado(a): {valor}",
            f"Verifique que el/la {entidad.lower()} exista en el sistema"
        )
    
    def warning(
        self,
        fila: int,
        columna: str,
        valor: Any,
        mensaje: str
    ):
        """Registra una advertencia."""
        self.agregar(
            fila, columna, valor,
            ErrorCategory.VALIDACION,
            ErrorSeverity.WARNING,
            mensaje
        )
    
    def error_seguridad(
        self,
        fila: int,
        columna: str,
        valor: Any,
        mensaje: str
    ):
        """Registra error de seguridad."""
        self.agregar(
            fila, columna, valor,
            ErrorCategory.SEGURIDAD,
            ErrorSeverity.CRITICAL,
            mensaje,
            "El valor ha sido rechazado por motivos de seguridad"
        )
    
    @property
    def tiene_errores(self) -> bool:
        return len(self.errores) > 0
    
    @property
    def fue_truncado(self) -> bool:
        return self._truncado
    
    def get_resumen_por_categoria(self) -> Dict[str, int]:
        """Obtiene conteo de errores por categoría."""
        resumen = {}
        for error in self.errores:
            cat = error.categoria.value
            resumen[cat] = resumen.get(cat, 0) + 1
        return resumen
    
    def get_resumen_por_columna(self) -> Dict[str, int]:
        """Obtiene conteo de errores por columna."""
        resumen = {}
        for error in self.errores:
            if error.columna:
                resumen[error.columna] = resumen.get(error.columna, 0) + 1
        return resumen
    
    def generar_reporte(self) -> Dict[str, Any]:
        """
        ISS-007: Genera reporte detallado de errores.
        """
        return {
            'total_errores': len(self.errores),
            'total_advertencias': len(self.advertencias),
            'fue_truncado': self._truncado,
            'por_categoria': self.get_resumen_por_categoria(),
            'por_columna': self.get_resumen_por_columna(),
            'errores': [e.to_dict() for e in self.errores],
            'advertencias': [e.to_dict() for e in self.advertencias],
        }


class SafeImporter:
    """
    ISS-007 + ISS-031: Importador seguro con validación y sanitización.
    
    Ejemplo de uso:
        importer = SafeImporter(collector)
        for fila, datos in enumerate(filas, start=2):
            clave = importer.get_clave(fila, 'A', datos.get('clave'))
            cantidad = importer.get_integer(fila, 'B', datos.get('cantidad'))
            fecha = importer.get_date(fila, 'C', datos.get('fecha'))
    """
    
    def __init__(self, collector: ImportErrorCollector):
        self.collector = collector
        self.sanitizer = DataSanitizer
    
    def get_string(
        self,
        fila: int,
        columna: str,
        valor: Any,
        requerido: bool = False,
        max_length: int = 500,
        campo: str = None
    ) -> Optional[str]:
        """Obtiene y sanitiza un string."""
        # Detectar contenido malicioso primero
        if valor:
            problemas = self.sanitizer.detectar_contenido_malicioso(str(valor))
            if problemas:
                self.collector.error_seguridad(
                    fila, columna, valor,
                    f"Contenido potencialmente malicioso: {problemas[0]}"
                )
                return None
        
        sanitizado = self.sanitizer.sanitize_string(valor, max_length)
        
        if requerido and not sanitizado:
            self.collector.error_validacion(
                fila, columna, valor,
                "Campo requerido está vacío",
                "Proporcione un valor para este campo",
                campo
            )
            return None
        
        return sanitizado
    
    def get_clave(
        self,
        fila: int,
        columna: str,
        valor: Any,
        requerido: bool = True,
        max_length: int = 50
    ) -> Optional[str]:
        """Obtiene y sanitiza una clave."""
        clave = self.sanitizer.sanitize_clave(valor, max_length)
        
        if requerido and not clave:
            self.collector.error_validacion(
                fila, columna, valor,
                "Clave requerida está vacía o es inválida",
                "Proporcione una clave alfanumérica válida"
            )
            return None
        
        return clave
    
    def get_integer(
        self,
        fila: int,
        columna: str,
        valor: Any,
        requerido: bool = False,
        min_valor: int = 0,
        max_valor: int = 999999999
    ) -> Optional[int]:
        """Obtiene y sanitiza un entero."""
        resultado, error = self.sanitizer.sanitize_integer(
            valor, min_value=min_valor, max_value=max_valor
        )
        
        if error:
            self.collector.error_formato(
                fila, columna, valor, error,
                f"Ingrese un número entero entre {min_valor} y {max_valor}"
            )
            return None
        
        if requerido and resultado is None:
            self.collector.error_validacion(
                fila, columna, valor,
                "Campo numérico requerido está vacío"
            )
            return None
        
        return resultado
    
    def get_decimal(
        self,
        fila: int,
        columna: str,
        valor: Any,
        requerido: bool = False,
        allow_negative: bool = False,
        max_valor: float = None
    ) -> Optional[Decimal]:
        """Obtiene y sanitiza un decimal."""
        resultado, error = self.sanitizer.sanitize_numeric(
            valor, allow_negative, max_valor
        )
        
        if error:
            self.collector.error_formato(fila, columna, valor, error)
            return None
        
        if requerido and resultado is None:
            self.collector.error_validacion(
                fila, columna, valor,
                "Campo decimal requerido está vacío"
            )
            return None
        
        return resultado
    
    def get_date(
        self,
        fila: int,
        columna: str,
        valor: Any,
        requerido: bool = False,
        min_fecha: date = None,
        max_fecha: date = None
    ) -> Optional[date]:
        """Obtiene y sanitiza una fecha."""
        resultado, error = self.sanitizer.sanitize_date(valor)
        
        if error:
            self.collector.error_formato(
                fila, columna, valor, error,
                "Use formato DD/MM/YYYY o YYYY-MM-DD"
            )
            return None
        
        if resultado:
            if min_fecha and resultado < min_fecha:
                self.collector.error_validacion(
                    fila, columna, valor,
                    f"Fecha anterior a la mínima permitida ({min_fecha})"
                )
                return None
            
            if max_fecha and resultado > max_fecha:
                self.collector.error_validacion(
                    fila, columna, valor,
                    f"Fecha posterior a la máxima permitida ({max_fecha})"
                )
                return None
        
        if requerido and resultado is None:
            self.collector.error_validacion(
                fila, columna, valor,
                "Fecha requerida está vacía"
            )
            return None
        
        return resultado
    
    def verificar_referencia(
        self,
        fila: int,
        columna: str,
        valor: Any,
        modelo,
        campo_busqueda: str = 'pk',
        nombre_entidad: str = "Registro"
    ) -> Optional[Any]:
        """Verifica que exista una referencia."""
        if not valor:
            return None
        
        try:
            filtro = {campo_busqueda: valor}
            return modelo.objects.get(**filtro)
        except modelo.DoesNotExist:
            self.collector.error_referencia(
                fila, columna, valor, nombre_entidad
            )
            return None
        except Exception as e:
            self.collector.agregar(
                fila, columna, valor,
                ErrorCategory.SISTEMA,
                ErrorSeverity.ERROR,
                f"Error al buscar {nombre_entidad}: {str(e)}"
            )
            return None
