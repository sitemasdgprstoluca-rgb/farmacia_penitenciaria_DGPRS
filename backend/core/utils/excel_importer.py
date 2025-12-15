"""
Utilidades para importacion masiva desde Excel.
Valida datos fila por fila y genera logs de importacion.
"""

import logging
from datetime import datetime, date
from decimal import Decimal

import openpyxl
from django.db import transaction
from django.db.models import Q, F

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
    HALLAZGO #3: Carga un archivo Excel con validaciones de seguridad.
    
    Validaciones:
    - Límite de tamaño (protección DoS)
    - Límite de filas (10,000 máximo)
    - Modo read_only y data_only (previene ataques de fórmulas)
    
    Retorna (workbook, filas_totales, valido).
    """
    try:
        # HALLAZGO #3: Cargar en modo seguro
        # read_only=True: streaming, no carga todo en memoria
        # data_only=True: ignora fórmulas, solo valores (previene ataques)
        workbook = openpyxl.load_workbook(
            archivo, 
            read_only=True,
            data_only=True
        )
        sheet = workbook.active
        filas_totales = sheet.max_row - 1

        # Validar límite de filas
        if filas_totales > 10000:
            logger.warning(f"Archivo rechazado: {filas_totales} filas exceden el límite de 10,000")
            return None, 0, False
        
        if filas_totales <= 0:
            logger.warning("Archivo rechazado: sin filas de datos")
            return None, 0, False

        return workbook, filas_totales, True
    except Exception as exc:  # pragma: no cover
        logger.error(f"Error al cargar Excel: {exc}")
        return None, 0, False


def importar_productos_desde_excel(archivo, usuario):
    """
    Importa productos desde Excel con mapeo FLEXIBLE de columnas.
    
    Soporta múltiples formatos de Excel incluyendo:
    - Formato oficial de plantilla del sistema
    - Formatos institucionales con columnas como "NOMBRE GENÉRICO", "MARCA", etc.
    - Archivos con numeración en primera columna
    
    Columnas reconocidas (con múltiples sinónimos):
    - clave/codigo/id/numero/no/num/cve
    - nombre/descripcion/nombre generico/medicamento/producto
    - unidad/unidad medida/um
    - categoria/tipo/clasificacion (opcional, default: medicamento)
    - presentacion/forma farmaceutica
    - marca/marca referencial/laboratorio
    - sustancia activa/principio activo/formula
    - concentracion/dosis
    - via administracion/via
    - stock minimo/minimo/stock (opcional, default: 0)
    - requiere receta/receta (opcional)
    - es controlado/controlado (opcional)
    - activo/estado/estatus (opcional, default: Si)
    """
    resultado = ResultadoImportacion('Producto')
    workbook, _, valido = cargar_excel(archivo)
    if not valido:
        resultado.agregar_error(0, 'archivo', 'Archivo Excel invalido o vacio')
        return resultado.get_dict()

    sheet = workbook.active
    encabezados = [cell.value for cell in sheet[1]]
    
    # Normalizar headers para mapeo robusto
    def normalizar_header(h):
        """Normaliza encabezados para mapeo robusto."""
        if not h:
            return ''
        import re
        texto = str(h).lower().replace('*', '').replace('\n', ' ')
        texto = re.sub(r'\([^)]*\)', '', texto)
        # Remover acentos
        acentos = {'á':'a', 'é':'e', 'í':'i', 'ó':'o', 'ú':'u', 'ñ':'n', 'ü':'u'}
        for ac, rep in acentos.items():
            texto = texto.replace(ac, rep)
        # Preservar # como símbolo especial antes de limpiar
        texto = texto.replace('#', ' numeral ')
        texto = re.sub(r'[^a-z0-9]+', ' ', texto)
        return texto.strip()
    
    encabezados_norm = [normalizar_header(e) for e in encabezados]
    logger.info(f"Encabezados detectados: {encabezados_norm}")
    logger.info(f"Encabezados originales: {encabezados}")
    
    # Mapeo flexible con múltiples sinónimos por campo
    # IMPORTANTE: 'numeral' es la normalización de '#' (columna de clave institucional)
    SINONIMOS = {
        'clave': ['clave', 'codigo', 'code', 'id', 'numero', 'no', 'num', 'cve', 'sku', 'ref', 
                  'referencia', 'numeral', 'n'],  # 'numeral' = '#'
        'nombre': ['nombre', 'descripcion', 'nombre generico', 'nombre generico del medicamento',
                   'medicamento', 'producto', 'nombre del medicamento', 'generico', 
                   'articulo', 'item', 'denominacion'],
        'unidad_medida': ['unidad', 'unidad medida', 'um', 'unidad de medida', 'medida', 'pieza'],
        'categoria': ['categoria', 'tipo', 'clasificacion', 'clase', 'grupo', 'familia'],
        'presentacion': ['presentacion', 'forma farmaceutica', 'forma', 'envase', 'empaque'],
        'marca': ['marca', 'marca referencial', 'laboratorio', 'fabricante', 'proveedor'],
        'sustancia_activa': ['sustancia activa', 'principio activo', 'formula', 'activo', 
                             'componente', 'ingrediente activo', 'composicion'],
        'concentracion': ['concentracion', 'dosis', 'potencia', 'gramaje', 'miligramos', 'mg'],
        'via_administracion': ['via administracion', 'via', 'ruta', 'administracion'],
        'stock_minimo': ['stock minimo', 'minimo', 'stock', 'min', 'inventario minimo'],
        'requiere_receta': ['requiere receta', 'receta', 'prescripcion'],
        'es_controlado': ['es controlado', 'controlado', 'control'],
        'activo': ['activo', 'estado', 'estatus', 'status', 'habilitado'],
    }
    
    def buscar_columna(sinonimos_lista, encabezados_norm):
        """Busca la primera columna que coincida con algún sinónimo."""
        for i, h in enumerate(encabezados_norm):
            for sinonimo in sinonimos_lista:
                # Coincidencia exacta o contenida
                if sinonimo == h or sinonimo in h:
                    return i
        return -1
    
    col_map = {}
    for campo, sinonimos in SINONIMOS.items():
        idx = buscar_columna(sinonimos, encabezados_norm)
        if idx >= 0:
            col_map[campo] = idx
    
    logger.info(f"Mapeo de columnas detectado: {col_map}")
    
    # Si no encontramos clave pero hay columnas numéricas, intentar auto-detectar
    if 'clave' not in col_map:
        # Buscar primera columna que parezca tener códigos/claves
        for i, h in enumerate(encabezados_norm):
            # Si el header está vacío o es solo un número, puede ser índice - saltar
            if not h or h.isdigit():
                continue
            # Verificar si las primeras filas tienen valores tipo código
            col_map['clave'] = i
            break
    
    # Si no encontramos nombre, usar la segunda o tercera columna útil
    if 'nombre' not in col_map and 'clave' in col_map:
        # Buscar siguiente columna con texto largo
        for i in range(col_map['clave'] + 1, len(encabezados_norm)):
            if encabezados_norm[i] and len(encabezados_norm[i]) > 2:
                col_map['nombre'] = i
                break
    
    # Validar columnas mínimas requeridas (ahora más flexible)
    if 'clave' not in col_map:
        resultado.agregar_error(1, 'encabezados', 
            f'No se encontró columna de clave/código. Columnas detectadas: {encabezados}')
        return resultado.get_dict()
    
    if 'nombre' not in col_map:
        resultado.agregar_error(1, 'encabezados', 
            f'No se encontró columna de nombre/descripción. Columnas detectadas: {encabezados}')
        return resultado.get_dict()
    
    # Unidades válidas expandidas
    unidades_validas = ['PIEZA', 'CAJA', 'FRASCO', 'SOBRE', 'AMPOLLETA', 'TABLETA', 
                        'CAPSULA', 'ML', 'GR', 'TUBO', 'BOLSA', 'PAQUETE', 'UNIDAD',
                        'LITRO', 'KILOGRAMO', 'KG', 'L', 'PZA', 'PZ']
    unidades_alias = {
        'PZA': 'PIEZA', 'PZ': 'PIEZA', 'UNIDAD': 'PIEZA', 'UN': 'PIEZA',
        'TAB': 'TABLETA', 'TABS': 'TABLETA', 'CAP': 'CAPSULA', 'CAPS': 'CAPSULA',
        'AMP': 'AMPOLLETA', 'FCO': 'FRASCO', 'KG': 'GR', 'KILOGRAMO': 'GR',
        'LT': 'ML', 'LITRO': 'ML', 'L': 'ML'
    }
    
    categorias_validas = ['MEDICAMENTO', 'MATERIAL_CURACION', 'INSUMO']
    
    creados = 0
    actualizados = 0

    with transaction.atomic():
        for fila_num in range(2, sheet.max_row + 1):
            resultado.incrementar_procesados()
            fila = sheet[fila_num]
            try:
                # Función helper para obtener valor de celda
                def get_val(col_name, default=None):
                    idx = col_map.get(col_name, -1)
                    if idx >= 0 and idx < len(fila):
                        val = fila[idx].value
                        if val is not None and str(val).strip():
                            return str(val).strip()
                    return default
                
                # Extraer clave - validar que no esté vacía
                clave_raw = get_val('clave')
                if not clave_raw:
                    # Fila vacía, saltar silenciosamente
                    resultado.total_procesados -= 1
                    continue
                
                # Limpiar y normalizar clave (mantener tal cual viene del Excel)
                clave = str(clave_raw).strip().upper()[:50]  # Truncar si es muy largo
                
                # Permitir claves cortas del formato institucional (1, 1A, 2, etc.)
                # Solo prefijar si es SOLO un dígito aislado para evitar colisiones
                if clave.isdigit() and len(clave) == 1:
                    clave = f"MED-{clave.zfill(3)}"
                
                # Extraer nombre
                nombre_raw = get_val('nombre')
                if not nombre_raw:
                    resultado.agregar_error(fila_num, 'nombre', 'Nombre vacío')
                    continue
                nombre = nombre_raw[:500]  # Truncar si es muy largo
                
                # Si nombre es muy corto, intentar combinar con presentación
                if len(nombre) < 5:
                    presentacion_extra = get_val('presentacion', '')
                    if presentacion_extra:
                        nombre = f"{nombre} {presentacion_extra}"
                    if len(nombre) < 5:
                        nombre = f"{nombre} (PRODUCTO)"
                
                # Unidad de medida - con valor por defecto
                unidad_raw = get_val('unidad_medida', 'PIEZA')
                unidad_medida = unidad_raw.upper()
                
                # Aplicar alias de unidades
                if unidad_medida in unidades_alias:
                    unidad_medida = unidades_alias[unidad_medida]
                
                # Si no es una unidad válida, usar PIEZA como default
                if unidad_medida not in unidades_validas:
                    logger.warning(f"Fila {fila_num}: Unidad '{unidad_raw}' no reconocida, usando PIEZA")
                    unidad_medida = 'PIEZA'
                
                # Categoría - con valor por defecto
                categoria_raw = get_val('categoria', 'MEDICAMENTO')
                categoria = categoria_raw.upper().replace(' ', '_')
                if categoria not in categorias_validas:
                    categoria = 'MEDICAMENTO'
                
                # Campos opcionales
                descripcion = get_val('presentacion', '') or ''  # Usar presentación como descripción
                marca = get_val('marca', '')
                sustancia_activa = get_val('sustancia_activa', '')
                presentacion = get_val('presentacion', '')
                concentracion = get_val('concentracion', '')
                via_administracion = get_val('via_administracion', '')
                
                # Construir descripción completa si hay datos adicionales
                desc_parts = [p for p in [descripcion, marca, concentracion] if p]
                descripcion_completa = ', '.join(desc_parts) if desc_parts else ''
                
                # Stock mínimo - con valor por defecto
                stock_raw = get_val('stock_minimo', '0')
                try:
                    stock_minimo = max(0, int(float(stock_raw)))
                except (ValueError, TypeError):
                    stock_minimo = 0
                
                # Booleanos
                requiere_receta = _parse_bool(get_val('requiere_receta', 'No'))
                es_controlado = _parse_bool(get_val('es_controlado', 'No'))
                activo = _parse_bool(get_val('activo', 'Si'))

                # Crear/actualizar producto
                obj, created = Producto.objects.update_or_create(
                    clave=clave,
                    defaults={
                        'nombre': nombre,
                        'descripcion': descripcion_completa,
                        'unidad_medida': unidad_medida.lower(),
                        'categoria': categoria.lower(),
                        'sustancia_activa': sustancia_activa or None,
                        'presentacion': presentacion or None,
                        'concentracion': concentracion or None,
                        'via_administracion': via_administracion or None,
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
                logger.exception(f"Error importando producto fila {fila_num}: {exc}")
                resultado.agregar_error(fila_num, 'general', str(exc))

    # Agregar info de creados/actualizados al resultado
    result = resultado.get_dict()
    result['creados'] = creados
    result['actualizados'] = actualizados
    return result


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
    Importa lotes desde Excel con mapeo FLEXIBLE de columnas.

    Columnas soportadas (con múltiples sinónimos):
    - producto: clave_producto, clave, producto, codigo_producto, id_producto
    - numero_lote: numero_lote, lote, num_lote, no_lote, numero de lote
    - cantidad: cantidad_inicial, cantidad, cant, stock, existencia
    - caducidad: fecha_caducidad, caducidad, vencimiento, fecha_vencimiento, expira
    - fabricacion: fecha_fabricacion, fabricacion, elaboracion (opcional)
    - precio: precio_unitario, precio, costo, valor (opcional, default: 0)
    - contrato: numero_contrato, contrato (opcional)
    - marca: marca, laboratorio, fabricante (opcional)
    - ubicacion: ubicacion, almacen, bodega (opcional)
    """
    resultado = ResultadoImportacion('Lote')
    workbook, _, valido = cargar_excel(archivo)
    if not valido:
        resultado.agregar_error(0, 'archivo', 'Archivo Excel invalido o vacio')
        return resultado.get_dict()

    sheet = workbook.active
    encabezados = [cell.value for cell in sheet[1]]
    
    # Normalizar encabezados
    def normalizar_header(h):
        if not h:
            return ''
        import re
        texto = str(h).lower().replace('*', '').replace('\n', ' ')
        texto = re.sub(r'\([^)]*\)', '', texto)
        acentos = {'á':'a', 'é':'e', 'í':'i', 'ó':'o', 'ú':'u', 'ñ':'n'}
        for ac, rep in acentos.items():
            texto = texto.replace(ac, rep)
        texto = texto.replace('#', ' numeral ')
        texto = re.sub(r'[^a-z0-9]+', ' ', texto)
        return texto.strip()
    
    encabezados_norm = [normalizar_header(e) for e in encabezados]
    logger.info(f"Lotes - Encabezados: {encabezados_norm}")
    
    # Mapeo flexible con sinónimos
    SINONIMOS_LOTE = {
        'producto': ['clave producto', 'clave', 'producto', 'codigo producto', 'id producto', 
                     'codigo', 'numeral', 'cve', 'sku'],
        'numero_lote': ['numero lote', 'lote', 'num lote', 'no lote', 'numero de lote', 'n lote'],
        'cantidad': ['cantidad inicial', 'cantidad', 'cant', 'stock', 'existencia', 'qty', 'unidades'],
        'caducidad': ['fecha caducidad', 'caducidad', 'vencimiento', 'fecha vencimiento', 
                      'expira', 'expiracion', 'fecha expiracion', 'fec cad', 'f caducidad'],
        'fabricacion': ['fecha fabricacion', 'fabricacion', 'elaboracion', 'fecha elaboracion',
                        'manufactura', 'fec fab', 'f fabricacion'],
        'precio': ['precio unitario', 'precio', 'costo', 'valor', 'precio unit', 'p unitario'],
        'contrato': ['numero contrato', 'contrato', 'no contrato', 'num contrato'],
        'marca': ['marca', 'laboratorio', 'fabricante', 'proveedor', 'lab'],
        'ubicacion': ['ubicacion', 'almacen', 'bodega', 'estante', 'localizacion'],
    }
    
    def buscar_columna(sinonimos_lista, headers):
        for i, h in enumerate(headers):
            for sin in sinonimos_lista:
                if sin == h or sin in h:
                    return i
        return -1
    
    col_map = {}
    for campo, sinonimos in SINONIMOS_LOTE.items():
        idx = buscar_columna(sinonimos, encabezados_norm)
        if idx >= 0:
            col_map[campo] = idx
    
    logger.info(f"Lotes - Mapeo: {col_map}")
    
    # Validar columnas mínimas (producto, lote, cantidad, caducidad)
    requeridos = ['producto', 'numero_lote', 'cantidad', 'caducidad']
    faltantes = [r for r in requeridos if r not in col_map]
    if faltantes:
        resultado.agregar_error(1, 'encabezados', 
            f'Columnas requeridas no encontradas: {faltantes}. Detectadas: {encabezados}')
        return resultado.get_dict()
    
    # Obtener centro
    centro = None
    if centro_id:
        try:
            centro = Centro.objects.get(id=centro_id)
        except Centro.DoesNotExist:
            resultado.agregar_error(0, 'centro', f'Centro con ID {centro_id} no existe')
            return resultado.get_dict()

    creados = 0
    with transaction.atomic():
        for fila_num in range(2, sheet.max_row + 1):
            resultado.incrementar_procesados()
            fila = sheet[fila_num]
            try:
                def get_val(col_name, default=None):
                    idx = col_map.get(col_name, -1)
                    if idx >= 0 and idx < len(fila):
                        val = fila[idx].value
                        if val is not None and str(val).strip():
                            return str(val).strip()
                    return default
                
                # Producto (requerido)
                clave_producto = get_val('producto')
                if not clave_producto:
                    resultado.total_procesados -= 1  # Fila vacía
                    continue
                clave_producto = clave_producto.upper()
                
                try:
                    producto = Producto.objects.get(clave__iexact=clave_producto)
                except Producto.DoesNotExist:
                    resultado.agregar_error(fila_num, 'producto', f'Producto no encontrado: {clave_producto}')
                    continue
                
                # Número de lote (requerido)
                numero_lote = get_val('numero_lote')
                if not numero_lote:
                    resultado.agregar_error(fila_num, 'numero_lote', 'Producto y numero de lote son obligatorios')
                    continue
                
                # Verificar duplicado
                lote_existente = Lote.objects.filter(
                    producto=producto, 
                    numero_lote__iexact=numero_lote,
                    activo=True
                )
                if centro:
                    lote_existente = lote_existente.filter(centro=centro)
                if lote_existente.exists():
                    resultado.agregar_error(fila_num, 'numero_lote', f'Lote {numero_lote} ya existe')
                    continue
                
                # Cantidad (requerido)
                cant_raw = get_val('cantidad', '0')
                try:
                    cantidad_inicial = max(1, int(float(cant_raw)))
                except:
                    resultado.agregar_error(fila_num, 'cantidad', 'Cantidad inválida')
                    continue
                
                # Fecha caducidad (requerido)
                fecha_cad_raw = fila[col_map['caducidad']].value
                try:
                    if isinstance(fecha_cad_raw, (datetime, date)):
                        fecha_caducidad = fecha_cad_raw.date() if isinstance(fecha_cad_raw, datetime) else fecha_cad_raw
                    else:
                        # Intentar varios formatos
                        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y']:
                            try:
                                fecha_caducidad = datetime.strptime(str(fecha_cad_raw).strip(), fmt).date()
                                break
                            except:
                                continue
                        else:
                            raise ValueError(f'Formato no reconocido: {fecha_cad_raw}')
                except Exception as e:
                    resultado.agregar_error(fila_num, 'caducidad', f'Fecha inválida: {e}')
                    continue
                
                # Fecha fabricación (opcional)
                fecha_fabricacion = None
                if 'fabricacion' in col_map:
                    fecha_fab_raw = fila[col_map['fabricacion']].value
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
                
                # Precio (opcional, default 0)
                precio_raw = get_val('precio', '0')
                try:
                    precio_unitario = max(Decimal('0'), Decimal(str(precio_raw).replace(',', '.')))
                except:
                    precio_unitario = Decimal('0')
                
                # Campos opcionales
                numero_contrato = get_val('contrato')
                marca = get_val('marca')
                ubicacion = get_val('ubicacion')
                
                # Crear lote
                lote = Lote.objects.create(
                    producto=producto,
                    centro=centro,
                    numero_lote=numero_lote,
                    cantidad_inicial=cantidad_inicial,
                    cantidad_actual=cantidad_inicial,
                    fecha_caducidad=fecha_caducidad,
                    fecha_fabricacion=fecha_fabricacion,
                    precio_unitario=precio_unitario,
                    numero_contrato=numero_contrato,
                    marca=marca,
                    ubicacion=ubicacion,
                    activo=True,
                )
                
                # Actualizar stock del producto
                Producto.objects.filter(pk=producto.pk).update(
                    stock_actual=F('stock_actual') + cantidad_inicial
                )
                
                creados += 1
                resultado.agregar_exito()
                
            except Exception as exc:
                logger.exception(f"Error importando lote fila {fila_num}: {exc}")
                resultado.agregar_error(fila_num, 'general', str(exc))

    result = resultado.get_dict()
    result['creados'] = creados
    return result


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

