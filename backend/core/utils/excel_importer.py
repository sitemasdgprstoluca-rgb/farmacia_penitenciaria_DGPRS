"""
Utilidades para importacion masiva desde Excel.
Valida datos fila por fila y genera logs de importacion.
"""

import logging
from datetime import datetime, date
from decimal import Decimal

import openpyxl
from django.db import transaction
from django.db.models import Q

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
    Importa productos desde Excel según esquema público.productos.

    Columnas esperadas:
    - clave (3-50 chars, unique)
    - nombre (min 5 chars) 
    - descripcion (opcional)
    - unidad_medida (pieza|caja|frasco|sobre|ampolleta|tableta|capsula|ml|gr)
    - categoria (medicamento|material_curacion|insumo)
    - sustancia_activa, presentacion, concentracion, via_administracion (opcional)
    - stock_minimo (int >= 0)
    - requiere_receta, es_controlado, activo (boolean)
    """
    resultado = ResultadoImportacion('Producto')
    workbook, _, valido = cargar_excel(archivo)
    if not valido:
        resultado.agregar_error(0, 'archivo', 'Archivo Excel invalido o vacio')
        return resultado.get_dict()

    sheet = workbook.active
    encabezados = [cell.value for cell in sheet[1]]
    
    # Mapeo flexible de headers (soporta con/sin asteriscos y saltos de línea)
    def normalizar_header(h):
        if not h:
            return ''
        return str(h).lower().replace('*', '').replace('\n', ' ').strip()
    
    encabezados_norm = [normalizar_header(e) for e in encabezados]
    
    # Buscar índices de columnas
    col_map = {}
    for i, h in enumerate(encabezados_norm):
        if 'clave' in h:
            col_map['clave'] = i
        elif 'nombre' in h:
            col_map['nombre'] = i
        elif 'descripci' in h:
            col_map['descripcion'] = i
        elif 'unidad' in h:
            col_map['unidad_medida'] = i
        elif 'categor' in h:
            col_map['categoria'] = i
        elif 'sustancia' in h:
            col_map['sustancia_activa'] = i
        elif 'presentaci' in h:
            col_map['presentacion'] = i
        elif 'concentraci' in h:
            col_map['concentracion'] = i
        elif 'v' in h and 'administraci' in h:
            col_map['via_administracion'] = i
        elif 'stock' in h:
            col_map['stock_minimo'] = i
        elif 'receta' in h:
            col_map['requiere_receta'] = i
        elif 'controlado' in h:
            col_map['es_controlado'] = i
        elif 'activo' in h:
            col_map['activo'] = i
    
    requeridos = ['clave', 'nombre', 'unidad_medida', 'categoria', 'stock_minimo']
    for req in requeridos:
        if req not in col_map:
            resultado.agregar_error(1, 'encabezados', f'Columna requerida "{req}" no encontrada')
            return resultado.get_dict()
    
    unidades_validas = ['PIEZA', 'CAJA', 'FRASCO', 'SOBRE', 'AMPOLLETA', 'TABLETA', 'CAPSULA', 'ML', 'GR']
    categorias_validas = ['MEDICAMENTO', 'MATERIAL_CURACION', 'INSUMO']

    with transaction.atomic():
        for fila_num in range(2, sheet.max_row + 1):
            resultado.incrementar_procesados()
            fila = sheet[fila_num]
            try:
                # Extraer valores con manejo seguro de None
                clave_val = fila[col_map['clave']].value
                clave = str(clave_val).strip().upper() if clave_val not in [None, ''] else None
                
                nombre_val = fila[col_map['nombre']].value
                nombre = str(nombre_val).strip() if nombre_val not in [None, ''] else None
                
                desc_idx = col_map.get('descripcion', -1)
                descripcion = ''
                if desc_idx >= 0 and desc_idx < len(fila):
                    desc_val = fila[desc_idx].value
                    descripcion = str(desc_val).strip() if desc_val not in [None, ''] else ''
                
                um_val = fila[col_map['unidad_medida']].value
                unidad_medida = str(um_val).strip().upper() if um_val not in [None, ''] else None
                
                cat_val = fila[col_map['categoria']].value
                categoria = str(cat_val).strip().upper() if cat_val not in [None, ''] else 'MEDICAMENTO'
                
                # Campos opcionales con manejo seguro
                def get_optional_str(col_name, default=None):
                    idx = col_map.get(col_name, -1)
                    if idx >= 0 and idx < len(fila):
                        val = fila[idx].value
                        return str(val).strip() if val not in [None, ''] else default
                    return default
                
                sustancia_activa = get_optional_str('sustancia_activa')
                presentacion = get_optional_str('presentacion')
                concentracion = get_optional_str('concentracion')
                via_administracion = get_optional_str('via_administracion')
                
                stock_raw = fila[col_map['stock_minimo']].value
                
                # Booleanos con manejo seguro
                def get_bool_value(col_name, default_val='No'):
                    idx = col_map.get(col_name, -1)
                    if idx >= 0 and idx < len(fila):
                        return fila[idx].value
                    return default_val
                
                requiere_receta = _parse_bool(get_bool_value('requiere_receta', 'No'))
                es_controlado = _parse_bool(get_bool_value('es_controlado', 'No'))
                activo = _parse_bool(get_bool_value('activo', 'Si'))

                # Validaciones
                if not clave or len(clave) < 3 or len(clave) > 50:
                    resultado.agregar_error(fila_num, 'clave', 'Clave debe tener 3-50 caracteres')
                    continue
                
                if not nombre or len(nombre) < 5:
                    resultado.agregar_error(fila_num, 'nombre', 'Nombre debe tener mínimo 5 caracteres')
                    continue
                
                if not unidad_medida or unidad_medida not in unidades_validas:
                    resultado.agregar_error(fila_num, 'unidad_medida', f'Unidad debe ser: {", ".join(unidades_validas)}')
                    continue
                
                if categoria not in categorias_validas:
                    resultado.agregar_error(fila_num, 'categoria', f'Categoría debe ser: {", ".join(categorias_validas)}')
                    continue

                try:
                    stock_minimo = int(float(stock_raw))
                    if stock_minimo < 0:
                        raise ValueError('Stock mínimo no puede ser negativo')
                except Exception as exc:
                    resultado.agregar_error(fila_num, 'stock_minimo', str(exc))
                    continue

                # Crear/actualizar producto
                Producto.objects.update_or_create(
                    clave=clave,
                    defaults={
                        'nombre': nombre,
                        'descripcion': descripcion,
                        'unidad_medida': unidad_medida.lower(),
                        'categoria': categoria.lower(),
                        'sustancia_activa': sustancia_activa,
                        'presentacion': presentacion,
                        'concentracion': concentracion,
                        'via_administracion': via_administracion,
                        'stock_minimo': stock_minimo,
                        'requiere_receta': requiere_receta,
                        'es_controlado': es_controlado,
                        'activo': activo,
                    }
                )
                resultado.agregar_exito()
            except Exception as exc:  # pragma: no cover - log detalle
                logger.exception(f"Error importando producto fila {fila_num}: {exc}")
                resultado.agregar_error(fila_num, 'general', str(exc))

    return resultado.get_dict()


def _parse_bool(valor):
    """Convierte valores variados a booleano."""
    if valor is None:
        return False
    if isinstance(valor, bool):
        return valor
    valor_str = str(valor).strip().lower()
    return valor_str in ['si', 'sí', 'yes', 'true', '1', 'verdadero', 'v']


def importar_lotes_desde_excel(archivo, usuario, centro_id=None):
    """
    Importa lotes desde Excel según esquema público.lotes.

    Columnas esperadas:
    - clave_producto (código del producto, debe existir)
    - numero_lote (único)
    - cantidad_inicial (int > 0)
    - fecha_caducidad (YYYY-MM-DD, futura)
    - fecha_fabricacion (YYYY-MM-DD, opcional)
    - precio_unitario (decimal >= 0)
    - numero_contrato, marca, ubicacion (opcional)
    """
    resultado = ResultadoImportacion('Lote')
    workbook, _, valido = cargar_excel(archivo)
    if not valido:
        resultado.agregar_error(0, 'archivo', 'Archivo Excel invalido o vacio')
        return resultado.get_dict()

    sheet = workbook.active
    encabezados = [cell.value for cell in sheet[1]]
    
    # Mapeo flexible
    def normalizar_header(h):
        if not h:
            return ''
        return str(h).lower().replace('*', '').replace('\n', ' ').strip()
    
    encabezados_norm = [normalizar_header(e) for e in encabezados]
    
    col_map = {}
    for i, h in enumerate(encabezados_norm):
        if 'clave' in h and 'producto' in h:
            col_map['clave_producto'] = i
        elif 'lote' in h and 'numero' in h:
            col_map['numero_lote'] = i
        elif 'cantidad' in h and 'inicial' in h:
            col_map['cantidad_inicial'] = i
        elif 'caducidad' in h:
            col_map['fecha_caducidad'] = i
        elif 'fabricaci' in h:
            col_map['fecha_fabricacion'] = i
        elif 'precio' in h:
            col_map['precio_unitario'] = i
        elif 'contrato' in h:
            col_map['numero_contrato'] = i
        elif 'marca' in h:
            col_map['marca'] = i
        elif 'ubicaci' in h:
            col_map['ubicacion'] = i

    requeridos = ['clave_producto', 'numero_lote', 'cantidad_inicial', 'fecha_caducidad', 'precio_unitario']
    for req in requeridos:
        if req not in col_map:
            resultado.agregar_error(1, 'encabezados', f'Columna requerida "{req}" no encontrada')
            return resultado.get_dict()
    
    # Obtener centro
    centro = None
    if centro_id:
        try:
            centro = Centro.objects.get(id=centro_id)
        except Centro.DoesNotExist:
            resultado.agregar_error(0, 'centro', f'Centro con ID {centro_id} no existe')
            return resultado.get_dict()

    with transaction.atomic():
        for fila_num in range(2, sheet.max_row + 1):
            resultado.incrementar_procesados()
            fila = sheet[fila_num]
            try:
                # Extraer valores
                clave_producto = str(fila[col_map['clave_producto']].value).strip().upper() if fila[col_map['clave_producto']].value else None
                numero_lote = str(fila[col_map['numero_lote']].value).strip() if fila[col_map['numero_lote']].value else None
                fecha_cad_raw = fila[col_map['fecha_caducidad']].value
                fecha_fab_raw = fila[col_map.get('fecha_fabricacion', -1)].value if col_map.get('fecha_fabricacion') else None
                cant_inicial_raw = fila[col_map['cantidad_inicial']].value
                precio_unitario_raw = fila[col_map['precio_unitario']].value
                
                # Opcionales
                numero_contrato = str(fila[col_map.get('numero_contrato', -1)].value).strip() if col_map.get('numero_contrato') and fila[col_map.get('numero_contrato')].value else None
                marca = str(fila[col_map.get('marca', -1)].value).strip() if col_map.get('marca') and fila[col_map.get('marca')].value else None
                ubicacion = str(fila[col_map.get('ubicacion', -1)].value).strip() if col_map.get('ubicacion') and fila[col_map.get('ubicacion')].value else None

                # Validar producto
                if not clave_producto:
                    resultado.agregar_error(fila_num, 'clave_producto', 'Clave de producto requerida')
                    continue
                
                try:
                    producto = Producto.objects.get(clave__iexact=clave_producto)
                except Producto.DoesNotExist:
                    resultado.agregar_error(fila_num, 'clave_producto', f'Producto "{clave_producto}" no existe')
                    continue

                # Validar lote
                if not numero_lote or len(numero_lote) < 3:
                    resultado.agregar_error(fila_num, 'numero_lote', 'Número de lote debe tener mínimo 3 caracteres')
                    continue
                
                # Verificar duplicado (producto + numero_lote + centro)
                if centro:
                    if Lote.objects.filter(producto=producto, numero_lote__iexact=numero_lote, centro=centro, activo=True).exists():
                        resultado.agregar_error(fila_num, 'numero_lote', f'Lote "{numero_lote}" ya existe en este centro')
                        continue
                else:
                    if Lote.objects.filter(producto=producto, numero_lote__iexact=numero_lote, activo=True).exists():
                        resultado.agregar_error(fila_num, 'numero_lote', f'Lote "{numero_lote}" ya existe')
                        continue

                # Fecha caducidad
                try:
                    if isinstance(fecha_cad_raw, (datetime, date)):
                        fecha_caducidad = fecha_cad_raw.date() if isinstance(fecha_cad_raw, datetime) else fecha_cad_raw
                    else:
                        fecha_caducidad = datetime.strptime(str(fecha_cad_raw).strip(), '%Y-%m-%d').date()
                    
                    if fecha_caducidad < date.today():
                        raise ValueError('Fecha de caducidad debe ser futura')
                except Exception as exc:
                    resultado.agregar_error(fila_num, 'fecha_caducidad', f'Fecha inválida: {exc}')
                    continue

                # Fecha fabricación (opcional)
                fecha_fabricacion = None
                if fecha_fab_raw:
                    try:
                        if isinstance(fecha_fab_raw, (datetime, date)):
                            fecha_fabricacion = fecha_fab_raw.date() if isinstance(fecha_fab_raw, datetime) else fecha_fab_raw
                        else:
                            fecha_fabricacion = datetime.strptime(str(fecha_fab_raw).strip(), '%Y-%m-%d').date()
                    except:
                        pass  # Opcional, si falla se ignora

                # Cantidad
                try:
                    cantidad_inicial = int(float(cant_inicial_raw))
                    if cantidad_inicial <= 0:
                        raise ValueError('Cantidad inicial debe ser > 0')
                except Exception as exc:
                    resultado.agregar_error(fila_num, 'cantidad_inicial', str(exc))
                    continue

                # Precio
                try:
                    precio_unitario = Decimal(str(precio_unitario_raw).strip())
                    if precio_unitario < 0:
                        raise ValueError('Precio no puede ser negativo')
                except Exception as exc:
                    resultado.agregar_error(fila_num, 'precio_unitario', str(exc))
                    continue

                # Crear lote
                lote = Lote.objects.create(
                    producto=producto,
                    centro=centro,
                    numero_lote=numero_lote,
                    cantidad_inicial=cantidad_inicial,
                    cantidad_actual=cantidad_inicial,  # Al inicio es igual
                    fecha_caducidad=fecha_caducidad,
                    fecha_fabricacion=fecha_fabricacion,
                    precio_unitario=precio_unitario,
                    numero_contrato=numero_contrato,
                    marca=marca,
                    ubicacion=ubicacion,
                    activo=True,
                )
                
                # Actualizar stock del producto
                producto.stock_actual = (producto.stock_actual or 0) + cantidad_inicial
                producto.save(update_fields=['stock_actual'])
                
                resultado.agregar_exito()
                
            except Exception as exc:  # pragma: no cover
                logger.exception(f"Error importando lote fila {fila_num}: {exc}")
                resultado.agregar_error(fila_num, 'general', str(exc))

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

