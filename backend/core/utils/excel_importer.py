"""
Utilidades para importacion masiva desde Excel.
Valida datos fila por fila y genera logs de importacion.
"""

import logging
from datetime import datetime, date
from decimal import Decimal

import openpyxl
from django.db import transaction

from core.models import Producto, Lote, Centro, ImportacionLog

logger = logging.getLogger(__name__)


class ResultadoImportacion:
    """Contenedor simple para acumular resultados de importacion."""

    def __init__(self, tipo_modelo: str):
        self.tipo_modelo = tipo_modelo
        self.total_procesados = 0
        self.exitosos = 0
        self.fallidos = 0
        self.errores = []  # lista de dicts

    def agregar_error(self, fila, campo, error):
        self.errores.append({
            'fila': fila,
            'campo': campo,
            'error': str(error),
        })
        self.fallidos += 1

    def agregar_exito(self):
        self.exitosos += 1

    def incrementar_procesados(self):
        self.total_procesados += 1

    def get_dict(self):
        return {
            'exitosa': self.fallidos == 0,
            'total_registros': self.total_procesados,
            'registros_exitosos': self.exitosos,
            'registros_fallidos': self.fallidos,
            'tasa_exito': round((self.exitosos / self.total_procesados * 100) if self.total_procesados else 0, 2),
            'errores': self.errores[:100],
        }


def cargar_excel(archivo):
    """
    Carga un archivo Excel y valida condiciones basicas.
    Retorna (workbook, filas_totales, valido).
    """
    try:
        workbook = openpyxl.load_workbook(archivo)
        sheet = workbook.active
        filas_totales = sheet.max_row - 1

        if filas_totales > 10000 or filas_totales <= 0:
            return None, 0, False

        return workbook, filas_totales, True
    except Exception as exc:  # pragma: no cover
        logger.error(f"Error al cargar Excel: {exc}")
        return None, 0, False


def importar_productos_desde_excel(archivo, usuario):
    """
    Importa productos desde Excel.

    Columnas esperadas:
    - clave (3-50 chars, unique)
    - descripcion (min 5 chars)
    - unidad_medida (PIEZA|CAJA|FRASCO|SOBRE|AMPOLLETA|TABLETA|CAPSULA|ML|GR)
    - precio_unitario (decimal > 0)
    - stock_minimo (int >= 0)
    - activo (opcional, boolean-like)
    """
    resultado = ResultadoImportacion('Producto')
    workbook, _, valido = cargar_excel(archivo)
    if not valido:
        resultado.agregar_error(0, 'archivo', 'Archivo Excel invalido o vacio')
        return resultado.get_dict()

    sheet = workbook.active
    encabezados = [cell.value for cell in sheet[1]]
    requeridos = ['clave', 'descripcion', 'unidad_medida', 'precio_unitario', 'stock_minimo']

    encabezados_norm = [str(e).lower() if e else '' for e in encabezados]
    for req in requeridos:
        if req not in encabezados_norm:
            resultado.agregar_error(1, 'encabezados', f'Columna requerida "{req}" no encontrada')
            return resultado.get_dict()

    col_map = {str(encabezados[i]).lower(): i for i in range(len(encabezados)) if encabezados[i]}
    unidades_validas = ['PIEZA', 'CAJA', 'FRASCO', 'SOBRE', 'AMPOLLETA', 'TABLETA', 'CAPSULA', 'ML', 'GR']

    with transaction.atomic():
        for fila_num in range(2, sheet.max_row + 1):
            resultado.incrementar_procesados()
            fila = sheet[fila_num]
            try:
                clave = str(fila[col_map['clave']].value).strip().upper() if fila[col_map['clave']].value else None
                descripcion = str(fila[col_map['descripcion']].value).strip() if fila[col_map['descripcion']].value else None
                unidad_medida = str(fila[col_map['unidad_medida']].value).strip().upper() if fila[col_map['unidad_medida']].value else None
                precio_raw = fila[col_map['precio_unitario']].value
                stock_raw = fila[col_map['stock_minimo']].value
                activo_idx = col_map.get('activo', -1)
                activo_raw = fila[activo_idx].value if activo_idx >= 0 and activo_idx < len(fila) else None

                if not clave or len(clave) < 3 or len(clave) > 50:
                    resultado.agregar_error(fila_num, 'clave', 'Clave 3-50 caracteres requerida')
                    continue
                if not descripcion or len(descripcion) < 5:
                    resultado.agregar_error(fila_num, 'descripcion', 'Descripcion minimo 5 caracteres')
                    continue
                if not unidad_medida or unidad_medida not in unidades_validas:
                    resultado.agregar_error(fila_num, 'unidad_medida', f'Unidad debe ser: {", ".join(unidades_validas)}')
                    continue

                try:
                    precio_unitario = Decimal(str(precio_raw).strip())
                    if precio_unitario <= 0:
                        raise ValueError('Precio debe ser > 0')
                except Exception as exc:
                    resultado.agregar_error(fila_num, 'precio_unitario', exc)
                    continue

                try:
                    stock_minimo = int(float(stock_raw))
                    if stock_minimo < 0:
                        raise ValueError('Stock minimo no puede ser negativo')
                except Exception as exc:
                    resultado.agregar_error(fila_num, 'stock_minimo', exc)
                    continue

                activo = str(activo_raw).strip().lower() if activo_raw is not None else 'true'
                activo_bool = activo in ['true', '1', 'si', 'yes', 'v', 'verdadero']

                Producto.objects.update_or_create(
                    clave=clave,
                    defaults={
                        'descripcion': descripcion,
                        'unidad_medida': unidad_medida,
                        'precio_unitario': precio_unitario,
                        'stock_minimo': stock_minimo,
                        'activo': activo_bool,
                    }
                )
                resultado.agregar_exito()
            except Exception as exc:  # pragma: no cover - log detalle
                logger.exception(f"Error importando producto fila {fila_num}: {exc}")
                resultado.agregar_error(fila_num, 'general', exc)

    return resultado.get_dict()


def importar_lotes_desde_excel(archivo, usuario):
    """
    Importa lotes desde Excel.

    Columnas esperadas:
    - producto_clave
    - numero_lote
    - fecha_caducidad (YYYY-MM-DD, futura)
    - cantidad_inicial (int > 0)
    - cantidad_actual (int >= 0 y <= inicial)
    - precio_compra (opcional, decimal >= 0)
    - proveedor (opcional)
    """
    resultado = ResultadoImportacion('Lote')
    workbook, _, valido = cargar_excel(archivo)
    if not valido:
        resultado.agregar_error(0, 'archivo', 'Archivo Excel invalido o vacio')
        return resultado.get_dict()

    sheet = workbook.active
    encabezados = [cell.value for cell in sheet[1]]
    requeridos = ['producto_clave', 'numero_lote', 'fecha_caducidad', 'cantidad_inicial', 'cantidad_actual']

    encabezados_norm = [str(e).lower() if e else '' for e in encabezados]
    for req in requeridos:
        if req not in encabezados_norm:
            resultado.agregar_error(1, 'encabezados', f'Columna requerida "{req}" no encontrada')
            return resultado.get_dict()

    col_map = {str(encabezados[i]).lower(): i for i in range(len(encabezados)) if encabezados[i]}

    with transaction.atomic():
        for fila_num in range(2, sheet.max_row + 1):
            resultado.incrementar_procesados()
            fila = sheet[fila_num]
            try:
                producto_clave = str(fila[col_map['producto_clave']].value).strip().upper() if fila[col_map['producto_clave']].value else None
                numero_lote = str(fila[col_map['numero_lote']].value).strip().upper() if fila[col_map['numero_lote']].value else None
                fecha_raw = fila[col_map['fecha_caducidad']].value
                cant_inicial_raw = fila[col_map['cantidad_inicial']].value
                cant_actual_raw = fila[col_map['cantidad_actual']].value
                precio_compra_raw = fila[col_map.get('precio_compra', -1)].value if col_map.get('precio_compra', -1) is not None and col_map.get('precio_compra', -1) >= 0 else None
                proveedor = str(fila[col_map.get('proveedor', -1)].value).strip() if col_map.get('proveedor', -1) is not None and col_map.get('proveedor', -1) >= 0 and fila[col_map.get('proveedor', -1)].value else ''

                if not producto_clave:
                    resultado.agregar_error(fila_num, 'producto_clave', 'Clave de producto requerida')
                    continue
                try:
                    producto = Producto.objects.get(clave=producto_clave)
                except Producto.DoesNotExist:
                    resultado.agregar_error(fila_num, 'producto_clave', f'Producto "{producto_clave}" no existe')
                    continue

                if not numero_lote or len(numero_lote) < 3:
                    resultado.agregar_error(fila_num, 'numero_lote', 'Numero de lote: minimo 3 caracteres')
                    continue
                if Lote.objects.filter(producto=producto, numero_lote__iexact=numero_lote, deleted_at__isnull=True).exists():
                    resultado.agregar_error(fila_num, 'numero_lote', f'Lote "{numero_lote}" ya existe')
                    continue

                try:
                    if isinstance(fecha_raw, (datetime, date)):
                        fecha_caducidad = fecha_raw.date() if isinstance(fecha_raw, datetime) else fecha_raw
                    else:
                        fecha_caducidad = datetime.strptime(str(fecha_raw), '%Y-%m-%d').date()
                    if fecha_caducidad < date.today():
                        raise ValueError('Fecha debe ser futura')
                except Exception as exc:
                    resultado.agregar_error(fila_num, 'fecha_caducidad', exc)
                    continue

                try:
                    cantidad_inicial = int(float(cant_inicial_raw))
                    if cantidad_inicial <= 0:
                        raise ValueError('Cantidad inicial debe ser > 0')
                except Exception as exc:
                    resultado.agregar_error(fila_num, 'cantidad_inicial', exc)
                    continue

                try:
                    cantidad_actual = int(float(cant_actual_raw))
                    if cantidad_actual < 0:
                        raise ValueError('Cantidad actual no puede ser negativa')
                    if cantidad_actual > cantidad_inicial:
                        raise ValueError(f'Cantidad actual ({cantidad_actual}) no puede exceder inicial ({cantidad_inicial})')
                except Exception as exc:
                    resultado.agregar_error(fila_num, 'cantidad_actual', exc)
                    continue

                precio_compra = None
                if precio_compra_raw not in [None, '']:
                    try:
                        precio_compra = Decimal(str(precio_compra_raw).strip())
                        if precio_compra < 0:
                            raise ValueError('Precio no puede ser negativo')
                    except Exception as exc:
                        resultado.agregar_error(fila_num, 'precio_compra', exc)
                        continue

                from django.utils import timezone
                Lote.objects.create(
                    producto=producto,
                    numero_lote=numero_lote,
                    fecha_caducidad=fecha_caducidad,
                    fecha_entrada=timezone.now().date(),
                    cantidad_inicial=cantidad_inicial,
                    cantidad_actual=cantidad_actual,
                    precio_compra=precio_compra or 0,
                )
                resultado.agregar_exito()
            except Exception as exc:  # pragma: no cover
                logger.exception(f"Error importando lote fila {fila_num}: {exc}")
                resultado.agregar_error(fila_num, 'general', exc)

    return resultado.get_dict()


def crear_log_importacion(usuario, tipo, archivo_nombre, resultado_dict):
    """Crea registro de ImportacionLog a partir del resumen."""
    try:
        ImportacionLog.objects.create(
            usuario=usuario if usuario and getattr(usuario, 'is_authenticated', False) else None,
            archivo_nombre=archivo_nombre,
            modelo=tipo,
            total_registros=resultado_dict.get('total_registros', 0),
            registros_exitosos=resultado_dict.get('registros_exitosos', 0),
            registros_fallidos=resultado_dict.get('registros_fallidos', 0),
            estado='exitosa' if resultado_dict.get('exitosa') else ('parcial' if resultado_dict.get('registros_exitosos', 0) > 0 else 'fallida'),
            resultado_procesamiento=resultado_dict,
        )
    except Exception as exc:  # pragma: no cover
        logger.error(f"Error creando ImportacionLog: {exc}")

