"""
Utilidades para importacion masiva desde Excel.
Valida datos fila por fila y genera logs de importacion.

FORMATO EXCEL PRODUCTOS:
- Clave, Nombre, Unidad, Stock Minimo, Categoria, Sustancia Activa,
  Presentacion, Concentracion, Via Admin, Requiere Receta, Controlado, Estado

FORMATO EXCEL LOTES:
- Clave, Lote, Cantidad, Caducidad, Precio, Marca, Ubicacion
"""

import logging
import re
from datetime import datetime, date
from decimal import Decimal

import openpyxl
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from core.models import Producto, Lote, Centro, ImportacionLog

logger = logging.getLogger(__name__)


class ResultadoImportacion:
    """Contenedor simple para acumular resultados de importacion."""

    def __init__(self, tipo_modelo: str):
        self.tipo_modelo = tipo_modelo
        self.total_procesados = 0
        self.exitosos = 0
        self.fallidos = 0
        self.errores = []

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
    """Carga un archivo Excel con validaciones de seguridad."""
    try:
        workbook = openpyxl.load_workbook(archivo, read_only=True, data_only=True)
        sheet = workbook.active
        filas_totales = sheet.max_row - 1

        if filas_totales > 10000:
            logger.warning(f"Archivo rechazado: {filas_totales} filas exceden límite")
            return None, 0, False
        
        if filas_totales <= 0:
            logger.warning("Archivo rechazado: sin filas de datos")
            return None, 0, False

        return workbook, filas_totales, True
    except Exception as exc:
        logger.error(f"Error al cargar Excel: {exc}")
        return None, 0, False


def normalizar_header(h):
    """Normaliza encabezados para mapeo robusto."""
    if not h:
        return ''
    texto = str(h).lower().strip()
    texto = texto.replace('*', '').replace('\n', ' ')
    texto = re.sub(r'\([^)]*\)', '', texto)
    # Remover acentos
    acentos = {'á':'a', 'é':'e', 'í':'i', 'ó':'o', 'ú':'u', 'ñ':'n', 'ü':'u'}
    for ac, rep in acentos.items():
        texto = texto.replace(ac, rep)
    texto = re.sub(r'[^a-z0-9]+', ' ', texto)
    return texto.strip()


def extraer_unidad_base(valor):
    """
    Extrae la unidad base de un valor de presentación.
    "CAJA CON 7 OVULOS" -> "CAJA"
    "FRASCO CON 120 ML" -> "FRASCO"
    """
    if not valor:
        return 'PIEZA'
    
    valor_upper = str(valor).upper().strip()
    
    # Mapeo de palabras a unidades estándar
    unidades_map = {
        'CAJA': 'CAJA', 'CAJAS': 'CAJA',
        'FRASCO': 'FRASCO', 'FRASCOS': 'FRASCO', 'FCO': 'FRASCO',
        'AMPOLLETA': 'AMPOLLETA', 'AMPOLLETAS': 'AMPOLLETA', 'AMP': 'AMPOLLETA',
        'SOBRE': 'SOBRE', 'SOBRES': 'SOBRE',
        'TABLETA': 'TABLETA', 'TABLETAS': 'TABLETA', 'TAB': 'TABLETA',
        'CAPSULA': 'CAPSULA', 'CAPSULAS': 'CAPSULA', 'CAP': 'CAPSULA',
        'PIEZA': 'PIEZA', 'PIEZAS': 'PIEZA', 'PZA': 'PIEZA', 'PZ': 'PIEZA',
        'TUBO': 'TUBO', 'TUBOS': 'TUBO',
        'BOLSA': 'BOLSA', 'BOLSAS': 'BOLSA',
        'ENVASE': 'FRASCO', 'ENVASES': 'FRASCO',
        'OVULO': 'PIEZA', 'OVULOS': 'PIEZA',
        'COMPRIMIDO': 'TABLETA', 'COMPRIMIDOS': 'TABLETA',
        'UNIDAD': 'PIEZA', 'UNIDADES': 'PIEZA',
        'ML': 'ML', 'MILILITROS': 'ML',
        'GR': 'GR', 'GRAMOS': 'GR', 'G': 'GR',
    }
    
    # Buscar la primera palabra que sea una unidad conocida
    palabras = valor_upper.split()
    for palabra in palabras:
        palabra_limpia = re.sub(r'[^A-Z]', '', palabra)
        if palabra_limpia in unidades_map:
            return unidades_map[palabra_limpia]
    
    return 'PIEZA'


def _parse_bool(valor):
    """Convierte valores variados a booleano."""
    if valor is None:
        return False
    if isinstance(valor, bool):
        return valor
    valor_str = str(valor).strip().lower()
    return valor_str in ['si', 'sí', 'yes', 'true', '1', 'verdadero', 'v', 'activo']


def importar_productos_desde_excel(archivo, usuario):
    """
    Importa productos desde Excel.
    
    Columnas soportadas:
    - Clave (REQUERIDO): código único del producto (615, 616, etc.)
    - Nombre (REQUERIDO): nombre del producto
    - Unidad: unidad de medida o presentación
    - Stock Minimo: inventario mínimo
    - Categoria: tipo de producto
    - Sustancia Activa: principio activo
    - Presentacion: forma farmacéutica
    - Concentracion: dosis
    - Via Admin: vía de administración
    - Requiere Receta: Si/No
    - Controlado: Si/No
    - Estado: Activo/Inactivo
    """
    resultado = ResultadoImportacion('Producto')
    workbook, _, valido = cargar_excel(archivo)
    if not valido:
        resultado.agregar_error(0, 'archivo', 'Archivo Excel invalido o vacio')
        return resultado.get_dict()

    sheet = workbook.active
    encabezados = [cell.value for cell in sheet[1]]
    encabezados_norm = [normalizar_header(e) for e in encabezados]
    
    logger.info(f"Productos - Encabezados: {encabezados}")
    logger.info(f"Productos - Normalizados: {encabezados_norm}")
    
    # Mapeo de columnas con sinónimos
    SINONIMOS = {
        'clave': ['clave', 'codigo', 'code', 'id', 'cve', 'sku', 'key', 'producto id', 
                  'codigo barras', 'codigo de barras', 'barcode'],
        'nombre': ['nombre', 'descripcion', 'nombre generico', 'medicamento', 'producto', 
                   'nombre del medicamento', 'nombre generico del medicamento', 'articulo'],
        'unidad_medida': ['unidad', 'unidad medida', 'um', 'unidad de medida'],
        'categoria': ['categoria', 'tipo', 'clasificacion', 'clase', 'grupo'],
        'presentacion': ['presentacion', 'forma farmaceutica', 'forma', 'envase'],
        'sustancia_activa': ['sustancia activa', 'principio activo', 'formula', 'activo', 
                             'composicion', 'ingrediente'],
        'concentracion': ['concentracion', 'dosis', 'potencia', 'gramaje'],
        'via_administracion': ['via admin', 'via administracion', 'via', 'ruta', 'administracion'],
        'stock_minimo': ['stock minimo', 'minimo', 'stock min', 'inv minimo', 'inventario minimo'],
        'requiere_receta': ['requiere receta', 'receta', 'prescripcion'],
        'es_controlado': ['controlado', 'es controlado', 'control'],
        'activo': ['estado', 'activo', 'estatus', 'status'],
        'marca': ['marca', 'laboratorio', 'fabricante'],
    }
    
    def buscar_columna(sinonimos_lista):
        for i, h in enumerate(encabezados_norm):
            if not h:
                continue
            for sinonimo in sinonimos_lista:
                if sinonimo == h or (len(sinonimo) > 2 and sinonimo in h):
                    return i
        return -1
    
    col_map = {}
    for campo, sinonimos in SINONIMOS.items():
        idx = buscar_columna(sinonimos)
        if idx >= 0:
            col_map[campo] = idx
    
    logger.info(f"Productos - Mapeo: {col_map}")
    
    # Validar columnas mínimas
    if 'clave' not in col_map:
        resultado.agregar_error(1, 'encabezados', 
            f'No se encontró columna "Clave". Columnas: {encabezados}')
        return resultado.get_dict()
    
    if 'nombre' not in col_map:
        resultado.agregar_error(1, 'encabezados', 
            f'No se encontró columna "Nombre". Columnas: {encabezados}')
        return resultado.get_dict()
    
    creados = 0
    actualizados = 0

    with transaction.atomic():
        for fila_num in range(2, sheet.max_row + 1):
            resultado.incrementar_procesados()
            fila = list(sheet[fila_num])
            
            try:
                def get_val(col_name, default=None):
                    idx = col_map.get(col_name, -1)
                    if idx >= 0 and idx < len(fila):
                        val = fila[idx].value
                        if val is not None and str(val).strip():
                            return str(val).strip()
                    return default
                
                # ========== CLAVE (requerido) ==========
                clave_raw = get_val('clave')
                if not clave_raw:
                    resultado.total_procesados -= 1
                    continue
                
                # La clave se guarda tal cual viene (615, 616, 1A, etc.)
                clave = str(clave_raw).strip().upper()[:50]
                
                # ========== NOMBRE (requerido) ==========
                nombre_raw = get_val('nombre')
                if not nombre_raw:
                    resultado.agregar_error(fila_num, 'nombre', 'Nombre vacío')
                    continue
                nombre = nombre_raw[:500]
                
                # ========== UNIDAD DE MEDIDA ==========
                # Guardar texto libre completo (ej: "CAJA CON 7 OVULOS")
                unidad_raw = get_val('unidad_medida', 'PIEZA')
                unidad_medida = str(unidad_raw).strip().upper()[:100] if unidad_raw else 'PIEZA'
                
                # ========== PRESENTACION ==========
                presentacion = get_val('presentacion', '')
                
                # ========== CATEGORIA ==========
                categoria_raw = get_val('categoria', '')
                if not categoria_raw or categoria_raw.upper() in ['N/A', 'NA', '-', 'NINGUNA', '']:
                    categoria = 'medicamento'
                else:
                    categoria = categoria_raw.lower().replace(' ', '_')
                    categorias_validas = ['medicamento', 'material_curacion', 'insumo']
                    if categoria not in categorias_validas:
                        categoria = 'medicamento'
                
                # ========== SUSTANCIA ACTIVA ==========
                sustancia_activa = get_val('sustancia_activa', '')
                
                # ========== CONCENTRACION ==========
                concentracion = get_val('concentracion', '')
                
                # ========== VIA ADMINISTRACION ==========
                via_administracion = get_val('via_administracion', '')
                
                # ========== MARCA ==========
                marca = get_val('marca', '')
                
                # ========== STOCK MINIMO ==========
                stock_raw = get_val('stock_minimo', '1')
                try:
                    stock_minimo = max(0, int(float(stock_raw)))
                except (ValueError, TypeError):
                    stock_minimo = 1
                
                # ========== REQUIERE RECETA ==========
                requiere_receta = _parse_bool(get_val('requiere_receta', 'No'))
                
                # ========== ES CONTROLADO ==========
                es_controlado = _parse_bool(get_val('es_controlado', 'No'))
                
                # ========== ACTIVO/ESTADO ==========
                estado_raw = get_val('activo', 'Activo')
                activo = _parse_bool(estado_raw) if estado_raw else True
                
                # ========== DESCRIPCION ==========
                desc_parts = [p for p in [presentacion, concentracion, marca] if p]
                descripcion = ', '.join(desc_parts)[:500] if desc_parts else None

                # Crear o actualizar producto
                obj, created = Producto.objects.update_or_create(
                    clave=clave,
                    defaults={
                        'nombre': nombre,
                        'descripcion': descripcion,
                        'unidad_medida': unidad_medida,
                        'categoria': categoria,
                        'sustancia_activa': sustancia_activa[:200] if sustancia_activa else None,
                        'presentacion': presentacion[:200] if presentacion else None,
                        'concentracion': concentracion[:100] if concentracion else None,
                        'via_administracion': via_administracion[:50] if via_administracion else None,
                        'stock_minimo': stock_minimo,
                        'requiere_receta': requiere_receta,
                        'es_controlado': es_controlado,
                        'activo': activo,
                    }
                )
                
                if created:
                    creados += 1
                else:
                    actualizados += 1
                resultado.agregar_exito()
                
            except Exception as exc:
                logger.exception(f"Error fila {fila_num}: {exc}")
                resultado.agregar_error(fila_num, 'general', str(exc))

    result = resultado.get_dict()
    result['creados'] = creados
    result['actualizados'] = actualizados
    return result


def importar_lotes_desde_excel(archivo, usuario, centro_id=None):
    """
    Importa lotes desde Excel.
    
    COLUMNAS OBLIGATORIAS:
    - Clave Producto (REQUERIDO): código/clave del producto
    - Nombre Producto (REQUERIDO): nombre del producto (debe coincidir con clave)
    - Lote (REQUERIDO): número de lote
    - Cantidad Inicial (REQUERIDO): cantidad inicial
    - Fecha Caducidad (REQUERIDO): fecha de vencimiento
    
    COLUMNAS OPCIONALES:
    - Precio Unitario: precio unitario (default 0)
    - Número Contrato: número de contrato
    - Marca: laboratorio (opcional)
    - Fecha Fabricación: fecha de elaboración
    - Activo: estado del lote (default Activo)
    
    IMPORTANTE: El sistema verifica que CLAVE y NOMBRE coincidan con el producto
    en la base de datos. Si hay discrepancia, se reporta error para evitar
    sumar cantidades a productos incorrectos.
    
    Detecta automáticamente la fila de encabezados.
    """
    resultado = ResultadoImportacion('Lote')
    workbook, _, valido = cargar_excel(archivo)
    if not valido:
        resultado.agregar_error(0, 'archivo', 'Archivo Excel invalido o vacio')
        return resultado.get_dict()

    sheet = workbook.active
    
    # Detectar fila de encabezados (puede estar en fila 1, 2 o 3)
    fila_inicio_datos = 2
    encabezados = []
    for fila_num in range(1, min(5, sheet.max_row + 1)):
        temp_headers = [cell.value for cell in sheet[fila_num]]
        # Si encuentra columnas con "lote" o "producto", esa es la fila de encabezados
        if any(h and ('lote' in str(h).lower() or 'producto' in str(h).lower()) for h in temp_headers):
            encabezados = temp_headers
            fila_inicio_datos = fila_num + 1
            logger.info(f"Lotes - Encabezados detectados en fila {fila_num}: {encabezados}")
            break
    
    if not encabezados or not any(h for h in encabezados):
        encabezados = [cell.value for cell in sheet[1]]
        fila_inicio_datos = 2
    
    encabezados_norm = [normalizar_header(e) for e in encabezados]
    
    logger.info(f"Lotes - Encabezados: {encabezados}")
    logger.info(f"Lotes - Normalizados: {encabezados_norm}")
    
    # IMPORTANTE: Los sinónimos más específicos primero para evitar conflictos
    # 'nombre producto' debe mapearse a producto_nombre, NO a producto_clave
    SINONIMOS_LOTE = {
        'producto_nombre': ['nombre producto', 'nombre del producto', 'producto nombre', 'descripcion'],
        'producto_clave': ['clave producto', 'clave', 'codigo producto', 'codigo', 'sku', 'key'],
        'producto_id': ['id producto', 'producto id', 'id_producto'],
        'numero_lote': ['numero lote', 'lote', 'num lote', 'no lote', 'numero de lote', 
                        'n lote', 'nro lote', 'batch'],
        'cantidad_inicial': ['cantidad inicial', 'cantidad', 'cant inicial', 'stock', 'existencia', 
                             'qty', 'unidades', 'piezas', 'cant'],
        'cantidad_actual': ['cantidad actual', 'cant actual', 'stock actual'],
        'caducidad': ['fecha caducidad', 'caducidad', 'vencimiento', 'fecha vencimiento', 
                      'expira', 'fec cad', 'expiracion', 'fecha expiracion'],
        'fabricacion': ['fecha fabricacion', 'fabricacion', 'elaboracion', 
                        'fecha elaboracion', 'fec fab'],
        'precio': ['precio unitario', 'precio', 'costo', 'valor', 'precio unit', 'pu'],
        'contrato': ['numero contrato', 'contrato', 'no contrato', 'num contrato'],
        'marca': ['marca', 'laboratorio', 'fabricante', 'proveedor', 'lab'],
        'ubicacion': ['ubicacion', 'almacen', 'bodega', 'estante', 'localizacion'],
        'centro': ['centro', 'centro nombre', 'nombre centro', 'centro destino'],
        'activo': ['activo', 'estado', 'status', 'active'],
    }
    
    def buscar_columna(sinonimos_lista):
        # Primero buscar coincidencia EXACTA
        for i, h in enumerate(encabezados_norm):
            if not h:
                continue
            if h in sinonimos_lista:
                return i
        return -1
    
    col_map = {}
    for campo, sinonimos in SINONIMOS_LOTE.items():
        idx = buscar_columna(sinonimos)
        if idx >= 0:
            col_map[campo] = idx
    
    logger.info(f"Lotes - Mapeo: {col_map}")
    
    # FIX: Validar columnas mínimas - CLAVE y NOMBRE son OBLIGATORIAS
    # Ambos deben coincidir con el producto en la base de datos
    tiene_clave = ('producto_clave' in col_map or 'producto_id' in col_map)
    tiene_nombre = 'producto_nombre' in col_map
    tiene_lote = 'numero_lote' in col_map
    tiene_cantidad = 'cantidad_inicial' in col_map
    tiene_caducidad = 'caducidad' in col_map
    
    if not (tiene_clave and tiene_nombre and tiene_lote and tiene_cantidad and tiene_caducidad):
        faltantes = []
        if not tiene_clave:
            faltantes.append('Clave Producto (obligatoria)')
        if not tiene_nombre:
            faltantes.append('Nombre Producto (obligatorio - debe coincidir con clave)')
        if not tiene_lote:
            faltantes.append('Número Lote')
        if not tiene_cantidad:
            faltantes.append('Cantidad Inicial')
        if not tiene_caducidad:
            faltantes.append('Fecha Caducidad')
        
        resultado.agregar_error(1, 'encabezados', 
            f'Columnas faltantes: {", ".join(faltantes)}. Detectadas: {encabezados}. '
            f'NOTA: Tanto Clave como Nombre del producto son obligatorios y deben coincidir.')
        return resultado.get_dict()
    
    # Centro: NULL = Almacén Central (FARMACIA)
    # Solo se usa centro_id si se pasa explícitamente como parámetro
    centro = None
    if centro_id:
        try:
            centro = Centro.objects.get(id=centro_id)
            logger.info(f"Lotes - Centro especificado: {centro.nombre} (ID: {centro.id})")
        except Centro.DoesNotExist:
            resultado.agregar_error(0, 'centro', f'Centro ID {centro_id} no existe')
            return resultado.get_dict()
    else:
        # NULL = Almacén Central (FARMACIA) - comportamiento por defecto
        logger.info("Lotes - Centro: NULL (Almacén Central/FARMACIA)")

    creados = 0
    
    with transaction.atomic():
        for fila_num in range(fila_inicio_datos, sheet.max_row + 1):
            resultado.incrementar_procesados()
            fila = list(sheet[fila_num])
            
            try:
                def get_val(col_name, default=None):
                    idx = col_map.get(col_name, -1)
                    if idx >= 0 and idx < len(fila):
                        val = fila[idx].value
                        if val is not None and str(val).strip():
                            return str(val).strip()
                    return default
                
                # ========== PRODUCTO (requerido - CLAVE Y NOMBRE son OBLIGATORIOS) ==========
                # FIX: AMBOS campos son obligatorios y deben coincidir con la BD
                producto = None
                producto_ref = None
                clave_producto = None
                nombre_producto = None
                
                # Obtener CLAVE (obligatoria)
                if 'producto_clave' in col_map:
                    clave_producto = get_val('producto_clave')
                
                # Obtener NOMBRE (obligatorio)
                if 'producto_nombre' in col_map:
                    nombre_producto = get_val('producto_nombre')
                
                # Validar que AMBOS campos estén presentes
                if not clave_producto:
                    resultado.agregar_error(fila_num, 'producto', 
                        f'Clave de producto es OBLIGATORIA. Nombre proporcionado: {nombre_producto or "N/A"}')
                    continue
                
                if not nombre_producto:
                    resultado.agregar_error(fila_num, 'producto', 
                        f'Nombre de producto es OBLIGATORIO. Clave proporcionada: {clave_producto}')
                    continue
                
                # Buscar producto por CLAVE
                producto_ref = clave_producto.upper()
                try:
                    producto = Producto.objects.get(clave__iexact=clave_producto)
                except Producto.DoesNotExist:
                    resultado.agregar_error(fila_num, 'producto', 
                        f'Clave "{clave_producto}" no encontrada en el catálogo de productos. '
                        f'Nombre: {nombre_producto}. Verifique que el producto exista.')
                    continue
                
                # VERIFICACIÓN CRÍTICA: El nombre en Excel debe coincidir con el nombre en BD
                nombre_bd_normalizado = producto.nombre.strip().lower()
                nombre_excel_normalizado = nombre_producto.strip().lower()
                
                # Verificar si el nombre coincide (completo o parcialmente al inicio)
                if not (nombre_bd_normalizado == nombre_excel_normalizado or 
                        nombre_bd_normalizado.startswith(nombre_excel_normalizado) or
                        nombre_excel_normalizado.startswith(nombre_bd_normalizado)):
                    resultado.agregar_error(fila_num, 'producto', 
                        f'DISCREPANCIA: Clave "{clave_producto}" corresponde a '
                        f'"{producto.nombre}" en BD, pero Excel dice "{nombre_producto}". '
                        f'Verifique que clave y nombre sean correctos.')
                    continue
                
                # ========== NUMERO LOTE (requerido) ==========
                numero_lote = get_val('numero_lote')
                if not numero_lote:
                    resultado.agregar_error(fila_num, 'lote', 
                        'Producto y numero de lote son obligatorios')
                    continue
                
                # Verificar duplicado
                lote_query = Lote.objects.filter(
                    producto=producto, 
                    numero_lote__iexact=numero_lote,
                    activo=True
                )
                if centro:
                    lote_query = lote_query.filter(centro=centro)
                
                if lote_query.exists():
                    resultado.agregar_error(fila_num, 'lote', 
                        f'Lote {numero_lote} ya existe para producto {clave_producto}')
                    continue
                
                # ========== CANTIDAD INICIAL (requerido) ==========
                cant_raw = get_val('cantidad_inicial', '0')
                try:
                    cantidad_inicial = max(1, int(float(cant_raw)))
                except:
                    resultado.agregar_error(fila_num, 'cantidad', f'Cantidad inválida: {cant_raw}')
                    continue
                
                # Nota: cantidad_actual se ignora del archivo y se iguala a cantidad_inicial
                # según lógica de negocio
                
                # ========== FECHA CADUCIDAD (requerido) ==========
                idx_cad = col_map['caducidad']
                fecha_cad_raw = fila[idx_cad].value if idx_cad < len(fila) else None
                
                fecha_caducidad = None
                try:
                    if isinstance(fecha_cad_raw, (datetime, date)):
                        fecha_caducidad = fecha_cad_raw.date() if isinstance(fecha_cad_raw, datetime) else fecha_cad_raw
                    elif fecha_cad_raw:
                        fecha_str = str(fecha_cad_raw).strip()
                        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y', '%Y/%m/%d']:
                            try:
                                fecha_caducidad = datetime.strptime(fecha_str, fmt).date()
                                break
                            except:
                                continue
                        if not fecha_caducidad:
                            raise ValueError(f'Formato no reconocido: {fecha_cad_raw}')
                    else:
                        raise ValueError('Fecha vacía')
                except Exception as e:
                    resultado.agregar_error(fila_num, 'caducidad', f'Fecha inválida: {e}')
                    continue
                
                # ========== FECHA FABRICACION (opcional) ==========
                fecha_fabricacion = None
                if 'fabricacion' in col_map:
                    idx_fab = col_map['fabricacion']
                    fecha_fab_raw = fila[idx_fab].value if idx_fab < len(fila) else None
                    if fecha_fab_raw:
                        try:
                            if isinstance(fecha_fab_raw, (datetime, date)):
                                fecha_fabricacion = fecha_fab_raw.date() if isinstance(fecha_fab_raw, datetime) else fecha_fab_raw
                            else:
                                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                                    try:
                                        fecha_fabricacion = datetime.strptime(str(fecha_fab_raw).strip(), fmt).date()
                                        break
                                    except:
                                        continue
                        except:
                            pass
                
                # ========== PRECIO (opcional) ==========
                precio_raw = get_val('precio', '0')
                try:
                    precio_str = str(precio_raw).replace(',', '.').replace('$', '').replace(' ', '')
                    precio_unitario = max(Decimal('0'), Decimal(precio_str))
                except:
                    precio_unitario = Decimal('0')
                
                # ========== CAMPOS OPCIONALES ==========
                numero_contrato = get_val('contrato')
                marca = get_val('marca')
                
                # Centro ya está asignado automáticamente a FARMACIA
                centro_lote = centro
                
                # ========== ACTIVO (opcional) ==========
                activo = True
                if 'activo' in col_map:
                    activo_raw = get_val('activo', 'activo')
                    activo = _parse_bool(activo_raw)
                
                # Crear lote
                Lote.objects.create(
                    producto=producto,
                    centro=centro_lote,
                    numero_lote=numero_lote,
                    cantidad_inicial=cantidad_inicial,
                    cantidad_actual=cantidad_inicial,
                    fecha_caducidad=fecha_caducidad,
                    fecha_fabricacion=fecha_fabricacion,
                    precio_unitario=precio_unitario,
                    numero_contrato=numero_contrato,
                    marca=marca,
                    ubicacion='Almacén Central',  # Todo llega a Farmacia
                    activo=activo,
                )
                
                # Actualizar stock del producto
                Producto.objects.filter(pk=producto.pk).update(
                    stock_actual=F('stock_actual') + cantidad_inicial
                )
                
                creados += 1
                resultado.agregar_exito()
                
            except Exception as exc:
                logger.exception(f"Error lote fila {fila_num}: {exc}")
                resultado.agregar_error(fila_num, 'general', str(exc))

    result = resultado.get_dict()
    result['creados'] = creados
    return result


def crear_log_importacion(usuario, tipo, archivo_nombre, resultado_dict):
    """
    Crea registro de ImportacionLog con los campos correctos de la BD.
    
    Campos de la tabla importacion_logs:
    - archivo, tipo_importacion, usuario_id, registros_totales,
    - registros_exitosos, registros_fallidos, errores (jsonb),
    - estado, fecha_inicio, fecha_fin
    """
    try:
        ImportacionLog.objects.create(
            usuario=usuario if usuario and getattr(usuario, 'is_authenticated', False) else None,
            archivo=archivo_nombre[:255],  # Max 255 chars
            tipo_importacion=tipo[:50],  # Max 50 chars
            registros_totales=resultado_dict.get('total_registros', 0),
            registros_exitosos=resultado_dict.get('registros_exitosos', 0),
            registros_fallidos=resultado_dict.get('registros_fallidos', 0),
            errores=resultado_dict.get('errores', []),  # Campo JSONField
            estado='procesando' if resultado_dict.get('exitosa') else ('parcial' if resultado_dict.get('registros_exitosos', 0) > 0 else 'fallida'),
            fecha_fin=timezone.now(),  # Marcar como completado
        )
    except Exception as exc:
        logger.error(f"Error creando ImportacionLog: {exc}")

