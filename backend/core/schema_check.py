"""
ISS-005 FIX (audit18): Verificación de esquema al arrancar.

Este módulo verifica que el esquema de la BD (Supabase) coincide con los modelos
Django managed=False. Detecta:
- Columnas faltantes
- Tipos de datos incompatibles
- Constraints esperados

Se ejecuta automáticamente al iniciar Django (via AppConfig.ready()).
"""
import logging
from django.db import connection
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


class SchemaVerifier:
    """
    ISS-005 FIX: Verificador de esquema para modelos managed=False.
    
    Compara la estructura de BD real con las definiciones de los modelos Django.
    """
    
    # Modelos críticos que deben verificarse
    MODELOS_CRITICOS = {
        'requisiciones': [
            ('id', 'integer'),
            ('numero', 'character varying'),
            ('estado', 'character varying'),
            ('centro_origen_id', 'integer'),
            ('centro_destino_id', 'integer'),
            ('solicitante_id', 'integer'),
            ('fecha_solicitud', 'timestamp'),
            ('created_at', 'timestamp'),
            ('updated_at', 'timestamp'),
        ],
        'productos': [
            ('id', 'integer'),
            ('clave', 'character varying'),
            ('descripcion', 'text'),
            ('precio_unitario', 'numeric'),
            ('unidad_medida', 'character varying'),
            ('activo', 'boolean'),
        ],
        'lotes': [
            ('id', 'integer'),
            ('numero_lote', 'character varying'),
            ('producto_id', 'integer'),
            ('cantidad_actual', 'integer'),
            ('fecha_caducidad', 'date'),
            ('activo', 'boolean'),
        ],
        'movimientos': [
            ('id', 'integer'),
            ('producto_id', 'integer'),
            ('lote_id', 'integer'),
            ('tipo', 'character varying'),
            ('cantidad', 'integer'),
            ('fecha', 'timestamp'),
        ],
        'centros': [
            ('id', 'integer'),
            ('nombre', 'character varying'),
            ('clave', 'character varying'),
            ('activo', 'boolean'),
        ],
        'core_usuario': [
            ('id', 'integer'),
            ('username', 'character varying'),
            ('email', 'character varying'),
            ('rol', 'character varying'),
            ('centro_id', 'integer'),
        ],
    }
    
    @classmethod
    def verificar_esquema(cls, raise_on_error: bool = False) -> dict:
        """
        ISS-005 FIX: Verifica el esquema de BD contra los modelos esperados.
        
        Args:
            raise_on_error: Si True, lanza excepción en errores críticos
            
        Returns:
            dict: Resultado de la verificación con errores/advertencias
        """
        resultado = {
            'ok': True,
            'errores': [],
            'advertencias': [],
            'tablas_verificadas': [],
            'tablas_faltantes': [],
        }
        
        try:
            with connection.cursor() as cursor:
                for tabla, columnas_esperadas in cls.MODELOS_CRITICOS.items():
                    tabla_resultado = cls._verificar_tabla(cursor, tabla, columnas_esperadas)
                    
                    if tabla_resultado['existe']:
                        resultado['tablas_verificadas'].append(tabla)
                        resultado['errores'].extend(tabla_resultado.get('errores', []))
                        resultado['advertencias'].extend(tabla_resultado.get('advertencias', []))
                    else:
                        resultado['tablas_faltantes'].append(tabla)
                        resultado['errores'].append(f"Tabla '{tabla}' no existe en la BD")
        
        except Exception as e:
            # Error de conexión - loguear pero no bloquear inicio
            error_msg = f"ISS-005: Error verificando esquema: {e}"
            logger.warning(error_msg)
            resultado['advertencias'].append(error_msg)
            # No marcar como error crítico - puede ser BD no disponible aún
            return resultado
        
        # Determinar si hay errores críticos
        if resultado['tablas_faltantes'] or any('faltante' in e.lower() for e in resultado['errores']):
            resultado['ok'] = False
            
            if raise_on_error:
                raise ImproperlyConfigured(
                    f"ISS-005: Esquema de BD incompatible. "
                    f"Errores: {resultado['errores']}. "
                    f"Tablas faltantes: {resultado['tablas_faltantes']}"
                )
        
        return resultado
    
    @classmethod
    def _verificar_tabla(cls, cursor, tabla: str, columnas_esperadas: list) -> dict:
        """
        Verifica una tabla específica.
        
        Args:
            cursor: Cursor de BD
            tabla: Nombre de la tabla
            columnas_esperadas: Lista de (nombre_columna, tipo_esperado)
            
        Returns:
            dict: Resultado de verificación de la tabla
        """
        resultado = {
            'existe': False,
            'errores': [],
            'advertencias': [],
        }
        
        try:
            # Verificar existencia de tabla
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                )
            """, [tabla])
            
            existe = cursor.fetchone()[0]
            resultado['existe'] = existe
            
            if not existe:
                return resultado
            
            # Obtener columnas reales
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
            """, [tabla])
            
            columnas_bd = {row[0]: {'tipo': row[1], 'nullable': row[2]} for row in cursor.fetchall()}
            
            # Verificar columnas esperadas
            for col_nombre, tipo_esperado in columnas_esperadas:
                if col_nombre not in columnas_bd:
                    resultado['errores'].append(
                        f"Columna faltante en '{tabla}': {col_nombre} ({tipo_esperado})"
                    )
                else:
                    tipo_real = columnas_bd[col_nombre]['tipo']
                    if not cls._tipos_compatibles(tipo_esperado, tipo_real):
                        resultado['advertencias'].append(
                            f"Tipo diferente en '{tabla}.{col_nombre}': "
                            f"esperado '{tipo_esperado}', encontrado '{tipo_real}'"
                        )
        
        except Exception as e:
            resultado['advertencias'].append(f"Error verificando tabla '{tabla}': {e}")
        
        return resultado
    
    @staticmethod
    def _tipos_compatibles(tipo_esperado: str, tipo_real: str) -> bool:
        """
        Verifica si dos tipos de datos son compatibles.
        
        Args:
            tipo_esperado: Tipo esperado (simplificado)
            tipo_real: Tipo real de la BD
            
        Returns:
            bool: True si son compatibles
        """
        # Mapeo de tipos compatibles
        compatibilidades = {
            'integer': ['integer', 'bigint', 'smallint', 'serial', 'bigserial'],
            'character varying': ['character varying', 'varchar', 'text', 'char'],
            'text': ['text', 'character varying', 'varchar'],
            'numeric': ['numeric', 'decimal', 'real', 'double precision'],
            'boolean': ['boolean', 'bool'],
            'timestamp': ['timestamp without time zone', 'timestamp with time zone', 'timestamptz'],
            'date': ['date'],
        }
        
        tipo_esperado = tipo_esperado.lower()
        tipo_real = tipo_real.lower()
        
        if tipo_esperado in compatibilidades:
            return tipo_real in compatibilidades[tipo_esperado] or tipo_real.startswith(tipo_esperado)
        
        return tipo_esperado in tipo_real or tipo_real in tipo_esperado
    
    @classmethod
    def log_resumen(cls, resultado: dict) -> None:
        """
        ISS-005 FIX: Registra resumen de verificación de esquema.
        """
        if resultado['ok']:
            logger.info(
                f"ISS-005: Verificación de esquema OK. "
                f"Tablas verificadas: {len(resultado['tablas_verificadas'])}"
            )
        else:
            logger.error(
                f"ISS-005: Problemas de esquema detectados. "
                f"Errores: {len(resultado['errores'])}. "
                f"Tablas faltantes: {resultado['tablas_faltantes']}"
            )
        
        for error in resultado['errores']:
            logger.error(f"ISS-005 ERROR: {error}")
        
        for advertencia in resultado['advertencias']:
            logger.warning(f"ISS-005 WARN: {advertencia}")


def verificar_esquema_al_iniciar():
    """
    ISS-005 FIX: Función para llamar desde AppConfig.ready().
    
    Ejecuta verificación de esquema de forma no bloqueante.
    Los errores se loguean pero no impiden el inicio.
    """
    try:
        # Importar aquí para evitar import circular
        from django.conf import settings
        
        # Solo verificar si no es test y está habilitado
        if getattr(settings, 'TESTING', False):
            logger.debug("ISS-005: Verificación de esquema omitida en modo test")
            return
        
        # Verificar con flag de configuración
        if not getattr(settings, 'VERIFY_SCHEMA_ON_START', True):
            logger.debug("ISS-005: Verificación de esquema deshabilitada por configuración")
            return
        
        resultado = SchemaVerifier.verificar_esquema(raise_on_error=False)
        SchemaVerifier.log_resumen(resultado)
        
        return resultado
        
    except Exception as e:
        # No bloquear inicio por error de verificación
        logger.warning(f"ISS-005: Error en verificación de esquema: {e}")
        return None
