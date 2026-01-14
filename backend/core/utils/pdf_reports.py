"""
Generador de reportes PDF profesionales para el sistema de farmacia penitenciaria
Con imagen de fondo oficial del Gobierno del Estado de México
Integra colores del TemaGlobal para personalización
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.platypus import Image as RLImage
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfgen import canvas
from django.conf import settings
from django.utils import timezone
from io import BytesIO
from datetime import date, timedelta, datetime
from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)


def _obtener_colores_tema():
    """
    Obtiene los colores del TemaGlobal activo.
    Retorna un diccionario con colores HexColor de ReportLab.
    Si no hay tema, usa valores por defecto institucionales.
    """
    try:
        from core.models import TemaGlobal
        tema = TemaGlobal.get_tema_activo()
        
        return {
            'primario': colors.HexColor(tema.color_primario or '#632842'),
            'primario_hover': colors.HexColor(tema.color_primario_hover or '#8a3b5c'),
            'secundario': colors.HexColor(tema.color_secundario or '#424242'),
            'texto': colors.HexColor(tema.color_texto_principal or '#1f2937'),
            'texto_secundario': colors.HexColor(tema.color_texto_secundario or '#6b7280'),
            'encabezado': colors.HexColor(tema.reporte_color_encabezado or '#632842'),
            'texto_encabezado': colors.HexColor(tema.reporte_color_texto_encabezado or '#FFFFFF'),
            'filas_alternas': colors.HexColor(tema.reporte_color_filas_alternas or '#F5F5F5'),
            'exito': colors.HexColor(tema.color_exito or '#4CAF50'),
            'error': colors.HexColor(tema.color_error or '#F44336'),
            'advertencia': colors.HexColor(tema.color_advertencia or '#FF9800'),
            'info': colors.HexColor(tema.color_info or '#2196F3'),
            # Metadatos del tema
            'nombre_institucion': tema.reporte_titulo_institucion or 'Sistema de Farmacia Penitenciaria',
            'subtitulo': tema.reporte_subtitulo or 'Secretaría de Seguridad',
            'pie_pagina': tema.reporte_pie_pagina or '',
            'ano_visible': tema.reporte_ano_visible,
            # Logo de reportes (ruta del archivo)
            'logo_reportes_path': _obtener_ruta_logo_reportes(tema),
            'fondo_reportes_path': _obtener_ruta_fondo_reportes(tema),
        }
    except Exception as e:
        logger.warning(f"No se pudo cargar TemaGlobal: {e}")
        # Valores por defecto
        return {
            'primario': colors.HexColor('#632842'),
            'primario_hover': colors.HexColor('#8a3b5c'),
            'secundario': colors.HexColor('#424242'),
            'texto': colors.HexColor('#1f2937'),
            'texto_secundario': colors.HexColor('#6b7280'),
            'encabezado': colors.HexColor('#632842'),
            'texto_encabezado': colors.HexColor('#FFFFFF'),
            'filas_alternas': colors.HexColor('#F5F5F5'),
            'exito': colors.HexColor('#4CAF50'),
            'error': colors.HexColor('#F44336'),
            'advertencia': colors.HexColor('#FF9800'),
            'info': colors.HexColor('#2196F3'),
            'nombre_institucion': 'Sistema de Farmacia Penitenciaria',
            'subtitulo': 'Secretaría de Seguridad',
            'pie_pagina': '',
            'ano_visible': True,
            'logo_reportes_path': None,
            'fondo_reportes_path': None,
        }


def _obtener_ruta_logo_reportes(tema):
    """
    Obtiene la ruta absoluta del logo de reportes desde el TemaGlobal.
    """
    try:
        if tema and tema.logo_reportes:
            logo_path = Path(settings.MEDIA_ROOT) / tema.logo_reportes.name
            if logo_path.exists():
                return str(logo_path)
    except Exception as e:
        logger.warning(f"Error obteniendo logo de reportes: {e}")
    return None


def _obtener_ruta_fondo_reportes(tema):
    """
    Obtiene la ruta absoluta del fondo de reportes desde el TemaGlobal.
    Si no hay fondo personalizado, usa el fondo institucional por defecto.
    """
    try:
        if tema and tema.imagen_fondo_reportes:
            fondo_path = Path(settings.MEDIA_ROOT) / tema.imagen_fondo_reportes.name
            if fondo_path.exists():
                return str(fondo_path)
    except Exception as e:
        logger.warning(f"Error obteniendo fondo de reportes: {e}")
    # Fallback a fondo institucional
    return None


# Colores institucionales - ahora se cargan dinámicamente desde TemaGlobal
# Estos valores son fallback para compatibilidad
COLOR_GUINDA = colors.HexColor('#632842')  # Color oficial
COLOR_GUINDA_CLARO = colors.HexColor('#8a3b5c')
COLOR_DORADO = colors.HexColor('#B8860B')
COLOR_TEXTO = colors.HexColor('#1f2937')
COLOR_GRIS = colors.HexColor('#6b7280')

# Ruta a la imagen de fondo institucional (usando settings.BASE_DIR)
# Funciona tanto en desarrollo como en producción después de collectstatic
# Usar la imagen original sin degradar para que se vea el colibrí y colores
FONDO_INSTITUCIONAL_PATH = Path(settings.BASE_DIR) / 'static' / 'img' / 'pdf' / 'fondoOficial.png'

# En producción, si collectstatic está configurado, la imagen estará en staticfiles
# Intentar primero en static/, luego en staticfiles/
def obtener_ruta_fondo():
    """
    Obtiene la ruta correcta al fondo institucional.
    Funciona en desarrollo (static/) y producción (staticfiles/).
    También considera el fondo personalizado del tema si existe.
    """
    # Primero intentar obtener fondo del tema
    colores_tema = _obtener_colores_tema()
    if colores_tema.get('fondo_reportes_path'):
        return Path(colores_tema['fondo_reportes_path'])
    
    # Fallback a fondo institucional
    rutas_posibles = [
        Path(settings.BASE_DIR) / 'static' / 'img' / 'pdf' / 'fondoOficial.png',
        Path(settings.STATIC_ROOT) / 'img' / 'pdf' / 'fondoOficial.png' if hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT else None,
    ]
    
    for ruta in rutas_posibles:
        if ruta and ruta.exists():
            return ruta
    
    logger.warning(f"Imagen de fondo no encontrada en: {rutas_posibles}")
    return FONDO_INSTITUCIONAL_PATH  # Retornar default aunque no exista


from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate


# Variable global para la ruta del fondo
_FONDO_PATH_ACTUAL = None


class CanvasConFondo(canvas.Canvas):
    """
    Canvas que dibuja el fondo institucional AL INICIO de cada página,
    ANTES de que se dibuje cualquier contenido.
    """
    
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        # Dibujar fondo inmediatamente al crear el canvas (primera página)
        self._dibujar_fondo()
    
    def showPage(self):
        """
        Se llama cuando se termina una página y se va a la siguiente.
        Primero terminamos la página actual, luego dibujamos el fondo en la nueva.
        """
        canvas.Canvas.showPage(self)
        # Dibujar fondo para la NUEVA página
        self._dibujar_fondo()
    
    def _dibujar_fondo(self):
        """Dibuja la imagen de fondo institucional"""
        global _FONDO_PATH_ACTUAL
        if _FONDO_PATH_ACTUAL and os.path.exists(_FONDO_PATH_ACTUAL):
            try:
                page_width, page_height = letter
                self.drawImage(
                    str(_FONDO_PATH_ACTUAL),
                    0, 0,
                    width=page_width,
                    height=page_height,
                    preserveAspectRatio=False,
                    mask='auto'
                )
            except Exception as e:
                logger.warning(f"No se pudo cargar imagen de fondo: {e}")


class FondoOficialCanvas(canvas.Canvas):
    """
    Canvas con fondo institucional oficial del Gobierno del Estado de México.
    Acepta parámetros adicionales para personalizar el reporte.
    """
    
    def __init__(self, *args, fondo_path=None, titulo_reporte='', **kwargs):
        self.fondo_path = fondo_path
        self.titulo_reporte = titulo_reporte
        canvas.Canvas.__init__(self, *args, **kwargs)
        # Dibujar fondo en primera página
        self._dibujar_fondo()
    
    def showPage(self):
        """Al cambiar de página, dibujar fondo en la nueva."""
        canvas.Canvas.showPage(self)
        self._dibujar_fondo()
    
    def _dibujar_fondo(self):
        """Dibuja la imagen de fondo institucional si existe."""
        if self.fondo_path and os.path.exists(self.fondo_path):
            try:
                page_width, page_height = letter
                self.drawImage(
                    str(self.fondo_path),
                    0, 0,
                    width=page_width,
                    height=page_height,
                    preserveAspectRatio=False,
                    mask='auto'
                )
            except Exception as e:
                logger.warning(f"No se pudo cargar imagen de fondo: {e}")


def _crear_doc_con_fondo(buffer, fondo_path):
    """
    Crea un SimpleDocTemplate que usa CanvasConFondo para dibujar el fondo.
    """
    global _FONDO_PATH_ACTUAL
    _FONDO_PATH_ACTUAL = fondo_path
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=1.8*inch,
        bottomMargin=1.2*inch,
        leftMargin=0.6*inch,
        rightMargin=0.6*inch
    )
    
    return doc


def _build_con_fondo(doc, elements):
    """
    Construye el documento usando el canvas con fondo.
    """
    doc.build(elements, canvasmaker=CanvasConFondo)


def _obtener_estilos_institucionales(colores_tema=None):
    """
    Retorna estilos personalizados con colores institucionales.
    
    Args:
        colores_tema: dict con colores del tema (opcional).
                     Si no se proporciona, se cargan del TemaGlobal.
    """
    if colores_tema is None:
        colores_tema = _obtener_colores_tema()
    
    styles = getSampleStyleSheet()
    
    color_primario = colores_tema.get('primario', COLOR_GUINDA)
    color_texto = colores_tema.get('texto', COLOR_TEXTO)
    
    # Título principal del reporte
    styles.add(ParagraphStyle(
        'TituloReporte',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=color_primario,
        alignment=TA_CENTER,
        spaceAfter=20,
        spaceBefore=10,
        fontName='Helvetica-Bold'
    ))
    
    # Subtítulo
    styles.add(ParagraphStyle(
        'SubtituloReporte',
        parent=styles['Heading2'],
        fontSize=11,
        textColor=color_texto,
        alignment=TA_CENTER,
        spaceAfter=15,
        fontName='Helvetica'
    ))
    
    # Sección
    styles.add(ParagraphStyle(
        'SeccionTitulo',
        parent=styles['Heading3'],
        fontSize=11,
        textColor=color_primario,
        spaceAfter=8,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    ))
    
    return styles


def _crear_tabla_institucional(data, col_widths=None, header=True, colores_tema=None):
    """
    Crea una tabla con estilo institucional - fondo transparente para ver imagen de fondo.
    
    Args:
        data: Datos de la tabla
        col_widths: Anchos de columnas
        header: Si la primera fila es encabezado
        colores_tema: dict con colores del tema (opcional)
    """
    if colores_tema is None:
        colores_tema = _obtener_colores_tema()
    
    color_primario = colores_tema.get('primario', COLOR_GUINDA)
    color_texto = colores_tema.get('texto', COLOR_TEXTO)
    color_encabezado = colores_tema.get('encabezado', COLOR_GUINDA)
    color_texto_encabezado = colores_tema.get('texto_encabezado', colors.white)
    color_filas_alternas = colores_tema.get('filas_alternas', colors.HexColor('#F5F5F5'))
    
    table = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)
    
    estilos = [
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # TOP para mejor visualización de texto largo
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),  # Reducir a 7pt para mejor ajuste
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, color_primario),
        ('TEXTCOLOR', (0, 0), (-1, -1), color_texto),
        ('WORDWRAP', (0, 0), (-1, -1), True),
    ]
    
    if header:
        estilos.extend([
            ('BACKGROUND', (0, 0), (-1, 0), color_encabezado),
            ('TEXTCOLOR', (0, 0), (-1, 0), color_texto_encabezado),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 7),  # Reducir también el header
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),  # Header centrado verticalmente
        ])
    
    table.setStyle(TableStyle(estilos))
    return table


def crear_encabezado(styles, colores_tema=None):
    """
    Crea el encabezado estándar para reportes.
    
    Args:
        styles: Estilos base de ReportLab
        colores_tema: dict con colores del tema (opcional)
    """
    if colores_tema is None:
        colores_tema = _obtener_colores_tema()
    
    color_primario = colores_tema.get('primario', COLOR_GUINDA)
    
    titulo_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=color_primario,
        alignment=TA_CENTER,
        spaceAfter=30
    )
    
    return titulo_style


def crear_pie_pagina(canvas, doc, colores_tema=None):
    """
    Agrega número de página al pie con información del tema.
    Incluye año si está configurado en el tema.
    """
    if colores_tema is None:
        colores_tema = _obtener_colores_tema()
    
    canvas.saveState()
    canvas.setFont('Helvetica', 9)
    page_num = canvas.getPageNumber()
    
    # Pie izquierdo: fecha y opcional año configurable del tema
    fecha_texto = f"Generado: {timezone.now().strftime('%d/%m/%Y %H:%M')}"
    ano_tema = colores_tema.get('ano_visible', '')
    if ano_tema:
        fecha_texto = f"{ano_tema} - {fecha_texto}"
    
    # Pie derecho: página y opcional pie personalizado
    pie_personalizado = colores_tema.get('pie_pagina', '')
    pagina_texto = f"Página {page_num}"
    
    canvas.drawString(inch, 0.5 * inch, fecha_texto)
    canvas.drawRightString(7.5 * inch, 0.5 * inch, pagina_texto)
    
    # Pie central si hay texto personalizado
    if pie_personalizado:
        canvas.setFont('Helvetica', 7)
        canvas.drawCentredString(4.25 * inch, 0.35 * inch, pie_personalizado)
    
    canvas.restoreState()


def _crear_encabezado_con_logo(elements, styles, titulo_reporte, colores_tema=None):
    """
    Crea un encabezado de reporte que incluye logo si está configurado.
    
    Args:
        elements: Lista de elementos del PDF
        styles: Estilos de ReportLab
        titulo_reporte: Título del reporte
        colores_tema: Configuración del tema
    """
    if colores_tema is None:
        colores_tema = _obtener_colores_tema()
    
    # Logo de reportes (si existe)
    logo_path = colores_tema.get('logo_reportes_path')
    if logo_path and os.path.exists(logo_path):
        try:
            logo = RLImage(logo_path, width=1.5*inch, height=0.75*inch)
            logo.hAlign = 'CENTER'
            elements.append(logo)
            elements.append(Spacer(1, 0.1*inch))
        except Exception as e:
            logger.warning(f"No se pudo cargar logo de reportes: {e}")
    
    # Título del reporte
    titulo = Paragraph(titulo_reporte, styles['TituloReporte'])
    elements.append(titulo)
    
    # Subtítulo con nombre de institución si está configurado
    nombre_institucion = colores_tema.get('nombre_institucion', '')
    subtitulo = colores_tema.get('subtitulo', '')
    if nombre_institucion or subtitulo:
        subtitulo_texto = f"{nombre_institucion}"
        if subtitulo:
            subtitulo_texto += f"<br/>{subtitulo}"
        elements.append(Paragraph(subtitulo_texto, styles['SubtituloReporte']))
    
    elements.append(Spacer(1, 0.2*inch))


def generar_reporte_inventario(productos_data, formato='pdf', filtros=None):
    """
    Genera reporte PDF de inventario completo con fondo oficial
    
    Args:
        productos_data: Lista de diccionarios con datos de productos
        formato: 'pdf' (default)
        filtros: Diccionario opcional con filtros aplicados
    
    Returns:
        BytesIO con el PDF generado
    """
    buffer = BytesIO()
    colores_tema = _obtener_colores_tema()
    
    # Usar fondo del tema o institucional
    fondo_path = colores_tema.get('fondo_reportes_path')
    if not fondo_path:
        fondo_path = str(FONDO_INSTITUCIONAL_PATH) if FONDO_INSTITUCIONAL_PATH.exists() else None
    
    doc = _crear_doc_con_fondo(buffer, fondo_path)
    
    elements = []
    styles = _obtener_estilos_institucionales(colores_tema)
    
    # Encabezado con logo
    _crear_encabezado_con_logo(elements, styles, "REPORTE DE INVENTARIO GENERAL", colores_tema)
    
    # Título
    titulo = Paragraph("REPORTE DE INVENTARIO GENERAL", styles['TituloReporte'])
    elements.append(titulo)
    elements.append(Spacer(1, 0.2*inch))
    
    # Información del reporte
    info_text = f"<b>Fecha de generación:</b> {timezone.now().strftime('%d/%m/%Y %H:%M')}<br/>"
    info_text += f"<b>Total de productos:</b> {len(productos_data)}"
    
    if filtros:
        if filtros.get('centro'):
            info_text += f"<br/><b>Centro:</b> {filtros['centro']}"
        if filtros.get('categoria'):
            info_text += f"<br/><b>Categoría:</b> {filtros['categoria']}"
        if filtros.get('nivel_stock'):
            info_text += f"<br/><b>Nivel de stock:</b> {filtros['nivel_stock']}"
    
    fecha_info = Paragraph(info_text, styles['Normal'])
    elements.append(fecha_info)
    elements.append(Spacer(1, 0.2*inch))
    
    # Estilo para celdas de texto largo
    estilo_celda = ParagraphStyle(
        'CeldaTexto',
        parent=styles['Normal'],
        fontSize=6.5,
        leading=8,
        wordWrap='CJK',
    )
    
    # Estilo para celdas de unidad (texto largo como "CAJA CON 20 TABLETAS")
    estilo_celda_unidad = ParagraphStyle(
        'CeldaUnidadInv',
        parent=styles['Normal'],
        fontSize=6,
        leading=7,
        wordWrap='CJK',
        alignment=TA_CENTER,
    )
    
    # Tabla de datos con Paragraph para texto largo
    data = [['Clave', 'Descripción', 'Stock', 'Mín.', 'Nivel', 'Unidad']]
    
    for producto in productos_data:
        nivel = str(producto.get('nivel', producto.get('nivel_stock', 'N/A'))).upper()
        descripcion = str(producto.get('descripcion', ''))
        # Usar Paragraph para la descripción para que se ajuste automáticamente
        desc_paragraph = Paragraph(descripcion, estilo_celda)
        # Usar Paragraph para unidad - permite texto largo
        unidad = str(producto.get('unidad', producto.get('unidad_medida', '')))
        unidad_paragraph = Paragraph(unidad, estilo_celda_unidad)
        data.append([
            str(producto.get('clave', '')),
            desc_paragraph,
            str(producto.get('stock_actual', 0)),
            str(producto.get('stock_minimo', 0)),
            nivel,
            unidad_paragraph
        ])
    
    # Ajustar anchos para que sumen exactamente el ancho disponible (7 pulgadas)
    # Descripción más ancha, Unidad ampliada para textos largos
    col_widths = [0.9*inch, 3.0*inch, 0.6*inch, 0.5*inch, 0.6*inch, 1.4*inch]
    table = _crear_tabla_institucional(data, col_widths)
    # Alinear números a la derecha
    table.setStyle(TableStyle([
        ('ALIGN', (2, 1), (3, -1), 'RIGHT'),  # Stock y Mín. alineados a la derecha
        ('ALIGN', (4, 1), (4, -1), 'CENTER'), # Nivel centrado
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Resumen
    productos_criticos = sum(1 for p in productos_data if str(p.get('nivel', p.get('nivel_stock', ''))).lower() == 'critico')
    productos_sin_stock = sum(1 for p in productos_data if p.get('stock_actual', 0) == 0)
    
    resumen_titulo = Paragraph("RESUMEN EJECUTIVO", styles['SeccionTitulo'])
    elements.append(resumen_titulo)
    
    resumen_data = [
        ['Total de productos', str(len(productos_data))],
        ['Productos sin stock', str(productos_sin_stock)],
        ['Productos en nivel crítico', str(productos_criticos)],
    ]
    
    resumen_table = Table(resumen_data, colWidths=[2.5*inch, 1.5*inch])
    resumen_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_TEXTO),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GUINDA),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(resumen_table)
    
    # Construir el documento con fondo
    _build_con_fondo(doc, elements)
    
    buffer.seek(0)
    logger.info(f"Reporte de inventario PDF generado: {len(productos_data)} productos")
    return buffer


def generar_reporte_inventario_lotes(lotes_data, filtros=None):
    """
    Genera reporte PDF de inventario con DETALLE POR LOTES incluyendo marca/laboratorio
    
    Args:
        lotes_data: Lista de diccionarios con datos de lotes individuales
        filtros: Diccionario opcional con filtros aplicados
    
    Returns:
        BytesIO con el PDF generado
    """
    buffer = BytesIO()
    colores_tema = _obtener_colores_tema()
    
    # Usar fondo del tema o institucional
    fondo_path = colores_tema.get('fondo_reportes_path')
    if not fondo_path:
        fondo_path = str(FONDO_INSTITUCIONAL_PATH) if FONDO_INSTITUCIONAL_PATH.exists() else None
    
    doc = _crear_doc_con_fondo(buffer, fondo_path)
    
    elements = []
    styles = _obtener_estilos_institucionales(colores_tema)
    
    # Encabezado con logo
    _crear_encabezado_con_logo(elements, styles, "INVENTARIO - DETALLE POR LOTES", colores_tema)
    
    # Título
    titulo = Paragraph("REPORTE DE INVENTARIO - DETALLE POR LOTES", styles['TituloReporte'])
    elements.append(titulo)
    elements.append(Spacer(1, 0.15*inch))
    
    # Información del reporte
    info_text = f"<b>Fecha de generación:</b> {filtros.get('fecha_generacion', 'N/A')}<br/>"
    info_text += f"<b>Total de lotes:</b> {filtros.get('total_lotes', len(lotes_data))}"
    info_text += f" | <b>Productos únicos:</b> {filtros.get('total_productos', 'N/A')}"
    
    if filtros and filtros.get('centro'):
        info_text += f"<br/><b>Centro:</b> {filtros['centro']}"
    
    fecha_info = Paragraph(info_text, styles['Normal'])
    elements.append(fecha_info)
    elements.append(Spacer(1, 0.15*inch))
    
    # Estilo para celdas compactas
    estilo_celda = ParagraphStyle(
        'CeldaLote',
        parent=styles['Normal'],
        fontSize=6,
        leading=7,
        wordWrap='CJK',
    )
    
    # Tabla de datos por lotes
    data = [['Clave', 'Producto', 'Lote', 'Caducidad', 'Stock', 'Precio', 'Marca/Lab.']]
    
    total_unidades = 0
    for lote in lotes_data:
        # SIN TRUNCAR - usar Paragraph para wrap automático
        producto_text = str(lote.get('producto', ''))
        producto_paragraph = Paragraph(producto_text, estilo_celda)
        marca_text = str(lote.get('marca', '-'))
        marca_paragraph = Paragraph(marca_text, estilo_celda)
        lote_text = str(lote.get('numero_lote', ''))
        lote_paragraph = Paragraph(lote_text, estilo_celda)
        
        cantidad = lote.get('cantidad', 0)
        total_unidades += cantidad
        
        data.append([
            str(lote.get('clave', '')),
            producto_paragraph,
            lote_paragraph,
            str(lote.get('fecha_caducidad', '-')),
            str(cantidad),
            f"${lote.get('precio_unitario', 0):.2f}",
            marca_paragraph
        ])
    
    # Ajustar anchos (total ~7 pulgadas)
    col_widths = [0.6*inch, 2.2*inch, 0.9*inch, 0.7*inch, 0.5*inch, 0.7*inch, 1.4*inch]
    table = _crear_tabla_institucional(data, col_widths)
    table.setStyle(TableStyle([
        ('ALIGN', (4, 1), (5, -1), 'RIGHT'),  # Stock y Precio alineados a la derecha
        ('FONTSIZE', (0, 0), (-1, -1), 6),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Resumen
    resumen_titulo = Paragraph("RESUMEN", styles['SeccionTitulo'])
    elements.append(resumen_titulo)
    
    resumen_data = [
        ['Total de lotes', str(len(lotes_data))],
        ['Total de unidades', f"{total_unidades:,}"],
        ['Productos únicos', str(filtros.get('total_productos', 'N/A'))],
    ]
    
    resumen_table = Table(resumen_data, colWidths=[2*inch, 1.5*inch])
    resumen_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_TEXTO),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GUINDA),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(resumen_table)
    
    # Construir el documento con fondo
    _build_con_fondo(doc, elements)
    
    buffer.seek(0)
    logger.info(f"Reporte de inventario por lotes PDF generado: {len(lotes_data)} lotes")
    return buffer


def generar_reporte_caducidades(lotes_data, dias=30, filtros=None):
    """
    Genera reporte PDF de lotes próximos a caducar con fondo oficial
    
    Args:
        lotes_data: Lista de diccionarios con datos de lotes
        dias: Días de anticipación para el reporte
        filtros: Diccionario opcional con filtros aplicados
    
    Returns:
        BytesIO con el PDF generado
    """
    buffer = BytesIO()
    fondo_path = str(FONDO_INSTITUCIONAL_PATH) if FONDO_INSTITUCIONAL_PATH.exists() else None
    
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter, 
        topMargin=1.8*inch,
        bottomMargin=1.2*inch,
        leftMargin=0.6*inch,
        rightMargin=0.6*inch
    )
    
    elements = []
    styles = _obtener_estilos_institucionales()
    
    # Título con énfasis en urgencia
    titulo = Paragraph(
        f"⚠️ REPORTE DE CADUCIDADES",
        styles['TituloReporte']
    )
    elements.append(titulo)
    elements.append(Spacer(1, 0.2*inch))
    
    # Información del reporte
    info_text = f"<b>Fecha de generación:</b> {timezone.now().strftime('%d/%m/%Y %H:%M')}<br/>"
    info_text += f"<b>Lotes identificados:</b> {len(lotes_data)}<br/>"
    if filtros and filtros.get('dias'):
        info_text += f"<b>Período de análisis:</b> Próximos {filtros['dias']} días"
    else:
        info_text += f"<b>Período de análisis:</b> Próximos {dias} días"
    
    fecha_info = Paragraph(info_text, styles['Normal'])
    elements.append(fecha_info)
    elements.append(Spacer(1, 0.2*inch))
    
    # Resumen de alertas
    vencidos = sum(1 for l in lotes_data if str(l.get('alerta', l.get('estado_caducidad', ''))).lower() == 'vencido')
    criticos = sum(1 for l in lotes_data if str(l.get('alerta', l.get('estado_caducidad', ''))).lower() == 'critico')
    proximos = sum(1 for l in lotes_data if str(l.get('alerta', l.get('estado_caducidad', ''))).lower() == 'proximo')
    
    alertas_titulo = Paragraph("RESUMEN DE ALERTAS", styles['SeccionTitulo'])
    elements.append(alertas_titulo)
    
    alertas_data = [
        ['Tipo de Alerta', 'Cantidad', 'Acción Requerida'],
        ['VENCIDOS', str(vencidos), 'Retiro inmediato'],
        ['CRÍTICOS (≤7 días)', str(criticos), 'Uso prioritario'],
        ['PRÓXIMOS (≤30 días)', str(proximos), 'Monitoreo'],
        ['TOTAL', str(len(lotes_data)), ''],
    ]
    
    alertas_table = Table(alertas_data, colWidths=[2*inch, 1*inch, 2*inch])
    alertas_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_GUINDA),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 1), (-1, -1), COLOR_TEXTO),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GUINDA),
        ('FONTNAME', (0, 4), (-1, 4), 'Helvetica-Bold'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(alertas_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Tabla de lotes
    lotes_titulo = Paragraph("DETALLE DE LOTES", styles['SeccionTitulo'])
    elements.append(lotes_titulo)
    
    # Estilo para celdas de texto largo
    estilo_celda = ParagraphStyle(
        'CeldaTextoLotes',
        parent=styles['Normal'],
        fontSize=7,
        leading=9,
        wordWrap='CJK',
    )
    
    data = [['Producto', 'Lote', 'Caducidad', 'Días', 'Cant.', 'Estado']]
    
    for lote in lotes_data:
        alerta = str(lote.get('alerta', lote.get('estado_caducidad', 'N/A'))).upper()
        dias_restantes = lote.get('dias_restantes', lote.get('dias_para_caducar', 'N/A'))
        producto_desc = str(lote.get('producto_descripcion', lote.get('producto', '')))
        producto_paragraph = Paragraph(producto_desc, estilo_celda)
        
        data.append([
            producto_paragraph,
            str(lote.get('numero_lote', '')),
            lote.get('fecha_caducidad', ''),
            str(dias_restantes),
            str(lote.get('cantidad_actual', 0)),
            alerta
        ])
    
    col_widths = [2.5*inch, 1*inch, 0.85*inch, 0.45*inch, 0.55*inch, 0.8*inch]
    table = _crear_tabla_institucional(data, col_widths)
    elements.append(table)
    
    # Usar canvas con fondo institucional
    def make_canvas(*args, **kwargs):
        return FondoOficialCanvas(*args, fondo_path=fondo_path, titulo_reporte='CADUCIDADES', **kwargs)
    
    doc.build(elements, canvasmaker=make_canvas)
    
    buffer.seek(0)
    logger.info(f"Reporte de caducidades PDF generado: {len(lotes_data)} lotes")
    return buffer


def generar_reporte_lotes(lotes_data, filtros=None):
    """
    Genera reporte PDF de inventario general de lotes con fondo oficial.
    
    Incluye información completa de cada lote: producto, número de lote,
    fechas de fabricación y caducidad, cantidades, ubicación, centro y estado.
    
    Args:
        lotes_data: Lista de diccionarios con datos de lotes
        filtros: Diccionario opcional con filtros aplicados
    
    Returns:
        BytesIO con el PDF generado
    """
    buffer = BytesIO()
    fondo_path = str(FONDO_INSTITUCIONAL_PATH) if FONDO_INSTITUCIONAL_PATH.exists() else None
    
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=landscape(letter),  # Horizontal para más columnas
        topMargin=1.5*inch,
        bottomMargin=1*inch,
        leftMargin=0.5*inch,
        rightMargin=0.5*inch
    )
    
    elements = []
    styles = _obtener_estilos_institucionales()
    
    # Título
    titulo = Paragraph("REPORTE DE INVENTARIO - LOTES", styles['TituloReporte'])
    elements.append(titulo)
    elements.append(Spacer(1, 0.15*inch))
    
    # Información del reporte y filtros
    info_text = f"<b>Fecha de generación:</b> {timezone.now().strftime('%d/%m/%Y %H:%M')}<br/>"
    info_text += f"<b>Total de lotes:</b> {len(lotes_data)}<br/>"
    
    if filtros:
        if filtros.get('centro'):
            info_text += f"<b>Centro:</b> {filtros['centro']}<br/>"
        if filtros.get('producto'):
            info_text += f"<b>Producto:</b> {filtros['producto']}<br/>"
        if filtros.get('caducidad'):
            caducidad_map = {
                'vencido': 'Vencidos',
                'critico': 'Críticos (< 90 días)',
                'proximo': 'Próximos (90-180 días)',
                'normal': 'Normal (> 180 días)'
            }
            info_text += f"<b>Estado caducidad:</b> {caducidad_map.get(filtros['caducidad'], filtros['caducidad'])}<br/>"
        if filtros.get('con_stock'):
            stock_map = {'con_stock': 'Con stock', 'sin_stock': 'Sin stock'}
            info_text += f"<b>Stock:</b> {stock_map.get(filtros['con_stock'], filtros['con_stock'])}<br/>"
        if filtros.get('activo'):
            info_text += f"<b>Estado:</b> {'Activos' if filtros['activo'] == 'true' else 'Inactivos'}<br/>"
    
    info = Paragraph(info_text, styles['Normal'])
    elements.append(info)
    elements.append(Spacer(1, 0.15*inch))
    
    # Resumen de inventario
    total_cantidad = sum(int(l.get('cantidad_actual', 0)) for l in lotes_data)
    lotes_activos = sum(1 for l in lotes_data if l.get('activo', True))
    lotes_con_stock = sum(1 for l in lotes_data if int(l.get('cantidad_actual', 0)) > 0)
    
    # Calcular lotes por estado de caducidad
    from datetime import date
    hoy = date.today()
    vencidos = 0
    criticos = 0
    proximos = 0
    normales = 0
    
    for lote in lotes_data:
        fecha_cad = lote.get('fecha_caducidad_raw') or lote.get('fecha_caducidad')
        if fecha_cad:
            try:
                if isinstance(fecha_cad, str):
                    from datetime import datetime
                    fecha_cad = datetime.strptime(fecha_cad[:10], '%Y-%m-%d').date()
                dias = (fecha_cad - hoy).days
                if dias < 0:
                    vencidos += 1
                elif dias <= 90:
                    criticos += 1
                elif dias <= 180:
                    proximos += 1
                else:
                    normales += 1
            except:
                pass
    
    resumen_titulo = Paragraph("RESUMEN DE INVENTARIO", styles['SeccionTitulo'])
    elements.append(resumen_titulo)
    
    resumen_data = [
        ['Concepto', 'Cantidad'],
        ['Total de lotes', str(len(lotes_data))],
        ['Lotes activos', str(lotes_activos)],
        ['Lotes con stock', str(lotes_con_stock)],
        ['Unidades totales', str(total_cantidad)],
        ['', ''],
        ['Estado de Caducidad', 'Lotes'],
        ['Vencidos', str(vencidos)],
        ['Críticos (≤90 días)', str(criticos)],
        ['Próximos (91-180 días)', str(proximos)],
        ['Normal (>180 días)', str(normales)],
    ]
    
    resumen_table = Table(resumen_data, colWidths=[2.2*inch, 1*inch])
    resumen_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_GUINDA),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 1), (-1, -1), COLOR_TEXTO),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GUINDA),
        ('FONTNAME', (0, 6), (-1, 6), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 6), (-1, 6), COLOR_GUINDA),
        ('TEXTCOLOR', (0, 6), (-1, 6), colors.white),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(resumen_table)
    elements.append(Spacer(1, 0.15*inch))
    
    # Tabla de lotes
    lotes_titulo = Paragraph("DETALLE DE LOTES", styles['SeccionTitulo'])
    elements.append(lotes_titulo)
    
    # Estilo para celdas de texto largo
    estilo_celda = ParagraphStyle(
        'CeldaTextoLotesInv',
        parent=styles['Normal'],
        fontSize=6,
        leading=8,
        wordWrap='CJK',
    )
    
    data = [['#', 'Clave', 'Producto', 'Lote', 'F. Fabricación', 'F. Caducidad', 'Cant. Inicial', 'Cant. Actual', 'Centro', 'Estado']]
    
    for idx, lote in enumerate(lotes_data, 1):
        # SIN TRUNCAR - usar Paragraph para wrap automático
        producto_desc = str(lote.get('producto_nombre', lote.get('producto', '')))
        producto_paragraph = Paragraph(producto_desc, estilo_celda)
        
        # ISS-FIX: No truncar el nombre del centro - usar Paragraph para wrap automático
        centro = str(lote.get('centro_nombre', lote.get('centro', 'Farmacia Central')))
        centro_paragraph = Paragraph(centro, estilo_celda)
        
        # Determinar estado visual de caducidad
        estado_cad = ''
        fecha_cad = lote.get('fecha_caducidad_raw') or lote.get('fecha_caducidad')
        if fecha_cad:
            try:
                if isinstance(fecha_cad, str):
                    from datetime import datetime
                    fecha_cad_date = datetime.strptime(fecha_cad[:10], '%Y-%m-%d').date()
                else:
                    fecha_cad_date = fecha_cad
                dias = (fecha_cad_date - hoy).days
                if dias < 0:
                    estado_cad = '⚠️ VENCIDO'
                elif dias <= 90:
                    estado_cad = '🔴 CRÍTICO'
                elif dias <= 180:
                    estado_cad = '🟡 PRÓXIMO'
                else:
                    estado_cad = '🟢 OK'
            except:
                estado_cad = 'N/A'
        
        activo = 'Activo' if lote.get('activo', True) else 'Inactivo'
        
        # SIN TRUNCAR clave y lote - usar Paragraph para wrap automático
        clave_paragraph = Paragraph(str(lote.get('producto_clave', lote.get('clave', ''))), estilo_celda)
        lote_num_paragraph = Paragraph(str(lote.get('numero_lote', '')), estilo_celda)
        
        data.append([
            str(idx),
            clave_paragraph,
            producto_paragraph,
            lote_num_paragraph,
            str(lote.get('fecha_fabricacion', '')),
            str(lote.get('fecha_caducidad', '')),
            str(lote.get('cantidad_inicial', 0)),
            str(lote.get('cantidad_actual', 0)),
            centro_paragraph,
            f"{activo}\n{estado_cad}"
        ])
    
    # ISS-FIX: Anchos ajustados - columna Centro más ancha para nombres largos
    col_widths = [0.3*inch, 0.65*inch, 1.6*inch, 0.75*inch, 0.7*inch, 0.7*inch, 0.55*inch, 0.55*inch, 1.5*inch, 0.75*inch]
    table = _crear_tabla_institucional(data, col_widths)
    elements.append(table)
    
    # Usar canvas con fondo institucional
    def make_canvas(*args, **kwargs):
        return FondoOficialCanvas(*args, fondo_path=fondo_path, titulo_reporte='INVENTARIO LOTES', **kwargs)
    
    doc.build(elements, canvasmaker=make_canvas)
    
    buffer.seek(0)
    logger.info(f"Reporte de lotes PDF generado: {len(lotes_data)} lotes")
    return buffer


def generar_reporte_requisiciones(requisiciones_data, filtros=None):
    """
    Genera reporte PDF de requisiciones con fondo oficial
    
    Args:
        requisiciones_data: Lista de diccionarios con datos de requisiciones
        filtros: Diccionario con filtros aplicados (estado, fechas, etc.)
    
    Returns:
        BytesIO con el PDF generado
    """
    buffer = BytesIO()
    fondo_path = str(FONDO_INSTITUCIONAL_PATH) if FONDO_INSTITUCIONAL_PATH.exists() else None
    
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter, 
        topMargin=1.8*inch,
        bottomMargin=1.2*inch,
        leftMargin=0.6*inch,
        rightMargin=0.6*inch
    )
    
    elements = []
    styles = _obtener_estilos_institucionales()
    
    # Título
    titulo = Paragraph("REPORTE DE REQUISICIONES", styles['TituloReporte'])
    elements.append(titulo)
    elements.append(Spacer(1, 0.2*inch))
    
    # Información y filtros
    info_text = "<b>Fecha de generación:</b> " + timezone.now().strftime('%d/%m/%Y %H:%M') + "<br/>"
    if filtros:
        if filtros.get('estado'):
            info_text += f"<b>Estado:</b> {filtros['estado']}<br/>"
        if filtros.get('centro'):
            info_text += f"<b>Centro:</b> {filtros['centro']}<br/>"
        if filtros.get('fecha_inicio'):
            info_text += f"<b>Desde:</b> {filtros['fecha_inicio']}<br/>"
        if filtros.get('fecha_fin'):
            info_text += f"<b>Hasta:</b> {filtros['fecha_fin']}<br/>"
    info_text += f"<b>Total de requisiciones:</b> {len(requisiciones_data)}"
    
    info = Paragraph(info_text, styles['Normal'])
    elements.append(info)
    elements.append(Spacer(1, 0.2*inch))
    
    # Resumen por estados
    estados = {}
    for req in requisiciones_data:
        estado = req.get('estado', 'N/A')
        estados[estado] = estados.get(estado, 0) + 1
    
    resumen_titulo = Paragraph("RESUMEN POR ESTADO", styles['SeccionTitulo'])
    elements.append(resumen_titulo)
    
    resumen_data = [['Estado', 'Cantidad']]
    for estado, count in estados.items():
        resumen_data.append([estado.upper(), str(count)])
    resumen_data.append(['TOTAL', str(len(requisiciones_data))])
    
    resumen_table = Table(resumen_data, colWidths=[2*inch, 1*inch])
    resumen_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_GUINDA),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 1), (-1, -1), COLOR_TEXTO),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GUINDA),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(resumen_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Tabla de requisiciones
    req_titulo = Paragraph("DETALLE DE REQUISICIONES", styles['SeccionTitulo'])
    elements.append(req_titulo)
    
    # Estilo para celdas de texto largo
    estilo_celda = ParagraphStyle(
        'CeldaTextoReq',
        parent=styles['Normal'],
        fontSize=7,
        leading=9,
        wordWrap='CJK',
    )
    
    data = [['Folio', 'Centro', 'Estado', 'Fecha', 'Items', 'Solicitante']]
    
    for req in requisiciones_data:
        centro_nombre = str(req.get('centro_nombre', req.get('centro', '')))
        centro_paragraph = Paragraph(centro_nombre, estilo_celda)
        solicitante = str(req.get('usuario_solicita', req.get('solicitante', '')))
        solicitante_paragraph = Paragraph(solicitante, estilo_celda)
        
        data.append([
            str(req.get('folio', '')),
            centro_paragraph,
            str(req.get('estado', '')).upper(),
            str(req.get('fecha_solicitud', '')),
            str(req.get('total_items', req.get('total_productos', 0))),
            solicitante_paragraph
        ])
    
    col_widths = [1*inch, 1.9*inch, 0.75*inch, 0.8*inch, 0.45*inch, 1.25*inch]
    table = _crear_tabla_institucional(data, col_widths)
    elements.append(table)
    elements.append(Spacer(1, 0.3*inch))
    
    # === DETALLE DE PRODUCTOS POR REQUISICIÓN ===
    detalle_titulo = Paragraph("DETALLE DE PRODUCTOS POR REQUISICIÓN", styles['SeccionTitulo'])
    elements.append(detalle_titulo)
    elements.append(Spacer(1, 0.1*inch))
    
    # Estilo para el folio de cada requisición
    estilo_folio = ParagraphStyle(
        'FolioReq',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica-Bold',
        textColor=COLOR_GUINDA,
        spaceBefore=10,
        spaceAfter=5,
    )
    
    for req in requisiciones_data:
        productos = req.get('productos', [])
        if not productos:
            continue
        
        # Encabezado de la requisición
        folio_text = f"📋 {req.get('folio', 'N/A')} - {req.get('centro', 'N/A')} - Estado: {req.get('estado', 'N/A')}"
        folio_p = Paragraph(folio_text, estilo_folio)
        elements.append(folio_p)
        
        # Tabla de productos de esta requisición
        productos_data = [['Clave', 'Producto', 'Solicitado', 'Autorizado', 'Surtido']]
        
        for prod in productos:
            # ISS-FIX: Sin truncar - usar Paragraph para wrap automático
            nombre = str(prod.get('nombre', 'N/A'))
            productos_data.append([
                str(prod.get('clave', 'N/A')),
                Paragraph(nombre, estilo_celda),
                str(prod.get('cantidad_solicitada', 0)),
                str(prod.get('cantidad_autorizada', 0)),
                str(prod.get('cantidad_surtida', 0)),
            ])
        
        prod_col_widths = [0.7*inch, 3.5*inch, 0.7*inch, 0.8*inch, 0.8*inch]
        prod_table = Table(productos_data, colWidths=prod_col_widths)
        prod_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_GUINDA),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('TEXTCOLOR', (0, 1), (-1, -1), COLOR_TEXTO),
            ('GRID', (0, 0), (-1, -1), 0.3, COLOR_GUINDA),
            ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(prod_table)
        elements.append(Spacer(1, 0.15*inch))
    
    # Usar canvas con fondo institucional
    def make_canvas(*args, **kwargs):
        return FondoOficialCanvas(*args, fondo_path=fondo_path, titulo_reporte='REQUISICIONES', **kwargs)
    
    doc.build(elements, canvasmaker=make_canvas)
    
    buffer.seek(0)
    logger.info(f"Reporte de requisiciones PDF generado: {len(requisiciones_data)} registros")
    return buffer


def generar_reporte_movimientos(transacciones_data, filtros=None, resumen=None):
    """
    Genera reporte PDF de movimientos de inventario agrupados por transacción
    
    Args:
        transacciones_data: Lista de diccionarios con transacciones agrupadas
            Cada transacción tiene: referencia, fecha, tipo, centro_origen, centro_destino,
            total_productos, total_cantidad, detalles[]
        filtros: Diccionario con filtros aplicados
        resumen: Diccionario con resumen de movimientos
    
    Returns:
        BytesIO con el PDF generado
    """
    buffer = BytesIO()
    fondo_path = str(FONDO_INSTITUCIONAL_PATH) if FONDO_INSTITUCIONAL_PATH.exists() else None
    
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter, 
        topMargin=1.8*inch,
        bottomMargin=1.2*inch,
        leftMargin=0.5*inch,
        rightMargin=0.5*inch
    )
    
    elements = []
    styles = _obtener_estilos_institucionales()
    
    titulo = Paragraph("REPORTE DE MOVIMIENTOS DE INVENTARIO", styles['TituloReporte'])
    elements.append(titulo)
    elements.append(Spacer(1, 0.15*inch))
    
    # Información del reporte
    total_transacciones = len(transacciones_data)
    total_movimientos = resumen.get('total_movimientos', 0) if resumen else sum(t.get('total_productos', 0) for t in transacciones_data)
    
    info_text = f"<b>Fecha de generación:</b> {timezone.now().strftime('%d/%m/%Y %H:%M')}<br/>"
    info_text += f"<b>Total de transacciones:</b> {total_transacciones}<br/>"
    info_text += f"<b>Total de movimientos:</b> {total_movimientos}"
    
    if filtros:
        if filtros.get('fecha_inicio'):
            info_text += f"<br/><b>Desde:</b> {filtros['fecha_inicio']}"
        if filtros.get('fecha_fin'):
            info_text += f"<br/><b>Hasta:</b> {filtros['fecha_fin']}"
        if filtros.get('tipo'):
            info_text += f"<br/><b>Tipo:</b> {filtros['tipo'].upper()}"
        if filtros.get('centro'):
            info_text += f"<br/><b>Centro:</b> {filtros['centro']}"
    
    info = Paragraph(info_text, styles['Normal'])
    elements.append(info)
    elements.append(Spacer(1, 0.15*inch))
    
    # Resumen de movimientos
    if resumen:
        resumen_titulo = Paragraph("RESUMEN", styles['SeccionTitulo'])
        elements.append(resumen_titulo)
        
        resumen_data = [
            ['Concepto', 'Cantidad'],
            ['Transacciones', str(resumen.get('total_transacciones', 0))],
            ['Total Entradas', str(resumen.get('total_entradas', 0))],
            ['Total Salidas', str(resumen.get('total_salidas', 0))],
            ['Diferencia', str(resumen.get('diferencia', 0))],
        ]
        
        resumen_table = Table(resumen_data, colWidths=[2*inch, 1*inch])
        resumen_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_GUINDA),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 1), (-1, -1), COLOR_TEXTO),
            ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GUINDA),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(resumen_table)
        elements.append(Spacer(1, 0.2*inch))
    
    # Estilo para celdas de texto - mejorado para ajuste de texto
    estilo_celda = ParagraphStyle(
        'CeldaTextoMov',
        parent=styles['Normal'],
        fontSize=7,
        leading=8,
        wordWrap='CJK',
        splitLongWords=True,
        spaceBefore=0,
        spaceAfter=0,
    )
    
    estilo_celda_pequena = ParagraphStyle(
        'CeldaTextoPequena',
        parent=styles['Normal'],
        fontSize=6,
        leading=7,
        wordWrap='CJK',
        splitLongWords=True,
        spaceBefore=0,
        spaceAfter=0,
    )
    
    # Tabla de transacciones agrupadas
    trans_titulo = Paragraph("DETALLE DE TRANSACCIONES", styles['SeccionTitulo'])
    elements.append(trans_titulo)
    
    # Encabezado de transacciones
    data = [['Referencia', 'Fecha', 'Tipo', 'Origen', 'Destino', 'Prods', 'Cant.']]
    
    for trans in transacciones_data:
        tipo = str(trans.get('tipo', '')).upper()
        # Usar Paragraph para textos largos - SIN TRUNCAR para mejor legibilidad
        referencia_p = Paragraph(str(trans.get('referencia', '')), estilo_celda)
        fecha_p = Paragraph(str(trans.get('fecha', '')), estilo_celda)
        # Centros sin truncar - el Paragraph hará wrap automático
        origen_texto = str(trans.get('centro_origen', 'Farmacia Central'))
        destino_texto = str(trans.get('centro_destino', 'Farmacia Central'))
        origen_p = Paragraph(origen_texto, estilo_celda)
        destino_p = Paragraph(destino_texto, estilo_celda)
        
        data.append([
            referencia_p,
            fecha_p,
            tipo,
            origen_p,
            destino_p,
            str(trans.get('total_productos', 0)),
            str(trans.get('total_cantidad', 0))
        ])
    
    # Anchos de columnas - Origen y Destino más anchos para nombres completos
    col_widths = [1.2*inch, 0.85*inch, 0.55*inch, 1.5*inch, 1.5*inch, 0.45*inch, 0.45*inch]
    table = _crear_tabla_institucional(data, col_widths)
    elements.append(table)
    elements.append(Spacer(1, 0.25*inch))
    
    # Detalle de productos por transacción
    det_titulo = Paragraph("DETALLE DE PRODUCTOS POR TRANSACCIÓN", styles['SeccionTitulo'])
    elements.append(det_titulo)
    elements.append(Spacer(1, 0.1*inch))
    
    for trans in transacciones_data:
        detalles = trans.get('detalles', [])
        if not detalles:
            continue
            
        # Mini encabezado de la transacción - Mejorado para centros largos
        origen = trans.get('centro_origen', 'Farmacia Central') or 'Farmacia Central'
        destino = trans.get('centro_destino', 'Farmacia Central') or 'Farmacia Central'
        trans_header = f"<b>{trans.get('referencia', 'N/A')}</b> | {trans.get('fecha', '')} | " \
                       f"<b>{trans.get('tipo', '')}</b><br/>" \
                       f"<i>Origen:</i> {origen} → <i>Destino:</i> {destino}"
        trans_header_p = Paragraph(trans_header, ParagraphStyle(
            'TransHeader',
            parent=styles['Normal'],
            fontSize=8,
            leading=11,
            spaceAfter=4,
            textColor=COLOR_GUINDA,
            wordWrap='CJK',
        ))
        elements.append(trans_header_p)
        
        # Tabla de productos
        det_data = [['#', 'Producto', 'Lote', 'Cantidad']]
        for idx, det in enumerate(detalles, 1):
            # Usar Paragraph para producto - SIN truncar para mejor legibilidad
            producto_texto = str(det.get('producto', ''))
            producto_p = Paragraph(producto_texto, estilo_celda_pequena)
            lote_p = Paragraph(str(det.get('lote', 'N/A')), estilo_celda_pequena)
            det_data.append([
                str(idx),
                producto_p,
                lote_p,
                str(det.get('cantidad', 0))
            ])
        
        # Fila de total
        det_data.append(['', '', 'TOTAL:', str(trans.get('total_cantidad', 0))])
        
        # Aumentar ancho de columna de producto para mejor ajuste
        det_col_widths = [0.3*inch, 4.2*inch, 1.0*inch, 0.6*inch]
        det_table = Table(det_data, colWidths=det_col_widths)
        det_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E5E7EB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_TEXTO),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('TEXTCOLOR', (0, 1), (-1, -1), COLOR_TEXTO),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#D1D5DB')),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F3F4F6')),
        ]))
        elements.append(det_table)
        elements.append(Spacer(1, 0.15*inch))
    
    # Usar canvas con fondo institucional
    def make_canvas(*args, **kwargs):
        return FondoOficialCanvas(*args, fondo_path=fondo_path, titulo_reporte='MOVIMIENTOS', **kwargs)
    
    doc.build(elements, canvasmaker=make_canvas)
    
    buffer.seek(0)
    logger.info(f"Reporte de movimientos PDF generado: {len(transacciones_data)} transacciones")
    return buffer


def generar_reporte_auditoria(auditoria_data, filtros=None):
    """
    Genera reporte PDF de auditoría del sistema con fondo oficial.
    Esencial para revisiones de seguridad y cumplimiento normativo.
    
    Args:
        auditoria_data: Lista de diccionarios con datos de auditoría
        filtros: Diccionario opcional con filtros aplicados
    
    Returns:
        BytesIO con el PDF generado
    """
    buffer = BytesIO()
    fondo_path = str(FONDO_INSTITUCIONAL_PATH) if FONDO_INSTITUCIONAL_PATH.exists() else None
    
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter, 
        topMargin=1.8*inch,
        bottomMargin=1.2*inch,
        leftMargin=0.6*inch,
        rightMargin=0.6*inch
    )
    
    elements = []
    styles = _obtener_estilos_institucionales()
    
    # Título
    titulo = Paragraph("REPORTE DE AUDITORÍA DEL SISTEMA", styles['TituloReporte'])
    elements.append(titulo)
    elements.append(Spacer(1, 0.2*inch))
    
    # Información del reporte
    info_text = f"<b>Fecha de generación:</b> {timezone.now().strftime('%d/%m/%Y %H:%M')}<br/>"
    info_text += f"<b>Total de registros:</b> {len(auditoria_data)}<br/>"
    info_text += "<b>Tipo de reporte:</b> Auditoría de acciones del sistema"
    
    if filtros:
        if filtros.get('fecha_inicio'):
            info_text += f"<br/><b>Desde:</b> {filtros['fecha_inicio']}"
        if filtros.get('fecha_fin'):
            info_text += f"<br/><b>Hasta:</b> {filtros['fecha_fin']}"
        if filtros.get('usuario'):
            info_text += f"<br/><b>Usuario:</b> {filtros['usuario']}"
        if filtros.get('accion'):
            info_text += f"<br/><b>Acción:</b> {filtros['accion']}"
        if filtros.get('modelo'):
            info_text += f"<br/><b>Módulo:</b> {filtros['modelo']}"
    
    info = Paragraph(info_text, styles['Normal'])
    elements.append(info)
    elements.append(Spacer(1, 0.2*inch))
    
    # Resumen de acciones
    acciones_count = {}
    for log in auditoria_data:
        accion = str(log.get('accion', 'N/A')).upper()
        acciones_count[accion] = acciones_count.get(accion, 0) + 1
    
    resumen_titulo = Paragraph("RESUMEN DE ACCIONES", styles['SeccionTitulo'])
    elements.append(resumen_titulo)
    
    resumen_data = [['Acción', 'Cantidad']]
    for accion, count in sorted(acciones_count.items(), key=lambda x: -x[1]):
        resumen_data.append([accion, str(count)])
    resumen_data.append(['TOTAL', str(len(auditoria_data))])
    
    resumen_table = Table(resumen_data, colWidths=[2*inch, 1*inch])
    resumen_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_GUINDA),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 1), (-1, -1), COLOR_TEXTO),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GUINDA),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(resumen_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Tabla de detalle
    detalle_titulo = Paragraph("DETALLE DE AUDITORÍA", styles['SeccionTitulo'])
    elements.append(detalle_titulo)
    
    # Estilo para celdas de texto largo
    estilo_celda = ParagraphStyle(
        'CeldaTextoAudit',
        parent=styles['Normal'],
        fontSize=7,
        leading=9,
        wordWrap='CJK',
    )
    
    data = [['Fecha', 'Usuario', 'Acción', 'Módulo', 'Descripción', 'IP']]
    
    for log in auditoria_data:
        fecha = log.get('fecha', '')
        if hasattr(fecha, 'strftime'):
            fecha = fecha.strftime('%d/%m/%Y %H:%M')
        else:
            fecha = str(fecha)
        
        descripcion = str(log.get('objeto_repr', log.get('descripcion', '')))
        descripcion_paragraph = Paragraph(descripcion, estilo_celda)
        
        # SIN TRUNCAR - usar Paragraph para wrap automático
        usuario_p = Paragraph(str(log.get('usuario', log.get('usuario_username', 'Sistema'))), estilo_celda)
        accion_p = Paragraph(str(log.get('accion', '')), estilo_celda)
        modelo_p = Paragraph(str(log.get('modelo', '')), estilo_celda)
        ip_p = Paragraph(str(log.get('ip_address', log.get('ip', ''))), estilo_celda)
        
        data.append([
            fecha,
            usuario_p,
            accion_p,
            modelo_p,
            descripcion_paragraph,
            ip_p
        ])
    
    col_widths = [1*inch, 0.85*inch, 0.7*inch, 0.9*inch, 2.1*inch, 0.7*inch]
    table = _crear_tabla_institucional(data, col_widths)
    elements.append(table)
    
    # Usar canvas con fondo institucional
    def make_canvas(*args, **kwargs):
        return FondoOficialCanvas(*args, fondo_path=fondo_path, titulo_reporte='AUDITORÍA', **kwargs)
    
    doc.build(elements, canvasmaker=make_canvas)
    
    buffer.seek(0)
    logger.info(f"Reporte de auditoría PDF generado: {len(auditoria_data)} registros")
    return buffer


def generar_reporte_trazabilidad(trazabilidad_data, producto_info=None, filtros=None):
    """
    Genera reporte PDF de trazabilidad de productos/lotes con fondo oficial.
    Esencial para rastrear el historial completo de un producto o lote.
    
    Args:
        trazabilidad_data: Lista de diccionarios con datos de trazabilidad
        producto_info: Diccionario con información del producto (opcional)
        filtros: Diccionario opcional con filtros aplicados
    
    Returns:
        BytesIO con el PDF generado
    """
    buffer = BytesIO()
    fondo_path = str(FONDO_INSTITUCIONAL_PATH) if FONDO_INSTITUCIONAL_PATH.exists() else None
    
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter, 
        topMargin=1.8*inch,
        bottomMargin=1.2*inch,
        leftMargin=0.6*inch,
        rightMargin=0.6*inch
    )
    
    elements = []
    styles = _obtener_estilos_institucionales()
    
    # Título
    titulo = Paragraph("REPORTE DE TRAZABILIDAD", styles['TituloReporte'])
    elements.append(titulo)
    elements.append(Spacer(1, 0.2*inch))
    
    # Información del producto si está disponible
    if producto_info:
        prod_titulo = Paragraph("INFORMACIÓN DEL PRODUCTO", styles['SeccionTitulo'])
        elements.append(prod_titulo)
        
        # Estilo para descripción larga
        estilo_desc = ParagraphStyle(
            'DescProd',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            wordWrap='CJK',
        )
        descripcion = str(producto_info.get('descripcion', 'N/A'))
        desc_paragraph = Paragraph(descripcion, estilo_desc)
        
        # Información básica del producto (sin No. Contrato y No. Lote específicos)
        prod_data = [
            ['Clave:', str(producto_info.get('clave', 'N/A')), 'Descripción:', desc_paragraph],
            ['Unidad:', str(producto_info.get('unidad_medida', 'N/A')), 'Precio:', f"${producto_info.get('precio_unitario', 0):.2f}" if producto_info.get('precio_unitario') else 'N/A'],
            ['Stock Actual:', str(producto_info.get('stock_actual', 0)), 'Stock Mínimo:', str(producto_info.get('stock_minimo', 0))],
        ]
        
        # Solo agregar No. Contrato y No. Lote si es búsqueda de lote específico (no de producto)
        if producto_info.get('numero_lote') and producto_info.get('numero_lote') != 'N/A':
            prod_data.append(['No. Contrato:', str(producto_info.get('numero_contrato', 'N/A')), 'No. Lote:', str(producto_info.get('numero_lote', 'N/A'))])
            # Agregar fila de caducidad y proveedor si están disponibles
            if producto_info.get('fecha_caducidad') or producto_info.get('proveedor'):
                prod_data.append([
                    'Caducidad:', str(producto_info.get('fecha_caducidad', 'N/A')), 
                    'Proveedor/Marca:', str(producto_info.get('proveedor', 'N/A'))
                ])
        else:
            # Si hay total de lotes, mostrarlo
            if producto_info.get('total_lotes'):
                prod_data.append(['Total Lotes:', str(producto_info.get('total_lotes', 0)), '', ''])
        
        prod_table = Table(prod_data, colWidths=[1.1*inch, 2.4*inch, 1.1*inch, 2.4*inch])
        prod_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_TEXTO),
            ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GUINDA),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(prod_table)
        elements.append(Spacer(1, 0.2*inch))
        
        # ========== SECCIÓN DE LOTES (cuando se busca por producto) ==========
        lotes = producto_info.get('lotes', [])
        if lotes:
            lotes_titulo = Paragraph("LOTES DEL PRODUCTO", styles['SeccionTitulo'])
            elements.append(lotes_titulo)
            
            # ISS-FIX: Estilo para celdas con wrap de texto
            estilo_celda_lote = ParagraphStyle(
                'CeldaLoteTraz',
                parent=styles['Normal'],
                fontSize=7,
                leading=8,
                wordWrap='CJK',
            )
            
            # Tabla de lotes
            lotes_header = [['No. Lote', 'No. Contrato', 'Caducidad', 'Stock', 'Marca', 'Centro']]
            for lote in lotes:
                # ISS-FIX: Usar Paragraph para todos los campos de texto para permitir wrap
                lote_paragraph = Paragraph(str(lote.get('numero_lote', 'N/A')), estilo_celda_lote)
                contrato_paragraph = Paragraph(str(lote.get('numero_contrato', 'N/A')), estilo_celda_lote)
                marca_paragraph = Paragraph(str(lote.get('marca', 'N/A')), estilo_celda_lote)
                centro_paragraph = Paragraph(str(lote.get('centro', 'N/A')), estilo_celda_lote)
                lotes_header.append([
                    lote_paragraph,
                    contrato_paragraph,
                    str(lote.get('fecha_caducidad', 'N/A')),
                    str(lote.get('cantidad_actual', 0)),
                    marca_paragraph,
                    centro_paragraph,
                ])
            
            # ISS-FIX: Aumentar ancho de columna Centro
            lotes_col_widths = [1.0*inch, 1.0*inch, 0.85*inch, 0.5*inch, 0.9*inch, 1.85*inch]
            lotes_table = Table(lotes_header, colWidths=lotes_col_widths)
            lotes_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), COLOR_GUINDA),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('TEXTCOLOR', (0, 1), (-1, -1), COLOR_TEXTO),
                ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GUINDA),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('ALIGN', (3, 0), (3, -1), 'RIGHT'),  # Stock alineado a la derecha
            ]))
            elements.append(lotes_table)
            elements.append(Spacer(1, 0.2*inch))
    
    # Información del reporte
    info_text = f"<b>Fecha de generación:</b> {timezone.now().strftime('%d/%m/%Y %H:%M')}<br/>"
    info_text += f"<b>Total de movimientos:</b> {len(trazabilidad_data)}"
    
    # Obtener filtros de parámetro o de producto_info
    filtros_aplicados = filtros or (producto_info.get('filtros') if producto_info else None)
    
    if filtros_aplicados:
        if filtros_aplicados.get('fecha_inicio'):
            info_text += f"<br/><b>Desde:</b> {filtros_aplicados['fecha_inicio']}"
        if filtros_aplicados.get('fecha_fin'):
            info_text += f"<br/><b>Hasta:</b> {filtros_aplicados['fecha_fin']}"
        if filtros_aplicados.get('lote'):
            info_text += f"<br/><b>Lote:</b> {filtros_aplicados['lote']}"
        # ISS-FIX: Mostrar titulo_centro legible en lugar del ID/código
        if producto_info and producto_info.get('titulo_centro'):
            info_text += f"<br/><b>Centro:</b> {producto_info['titulo_centro']}"
        elif filtros_aplicados.get('centro'):
            info_text += f"<br/><b>Centro:</b> {filtros_aplicados['centro']}"
    
    info = Paragraph(info_text, styles['Normal'])
    elements.append(info)
    elements.append(Spacer(1, 0.2*inch))
    
    # Resumen de movimientos
    total_entradas = sum(1 for t in trazabilidad_data if str(t.get('tipo', '')).lower() == 'entrada')
    total_salidas = sum(1 for t in trazabilidad_data if str(t.get('tipo', '')).lower() == 'salida')
    total_ajustes = sum(1 for t in trazabilidad_data if str(t.get('tipo', '')).lower() == 'ajuste')
    
    resumen_titulo = Paragraph("RESUMEN DE TRAZABILIDAD", styles['SeccionTitulo'])
    elements.append(resumen_titulo)
    
    resumen_data = [
        ['Concepto', 'Cantidad'],
        ['Entradas', str(total_entradas)],
        ['Salidas', str(total_salidas)],
        ['Ajustes', str(total_ajustes)],
        ['TOTAL MOVIMIENTOS', str(len(trazabilidad_data))],
    ]
    
    resumen_table = Table(resumen_data, colWidths=[2*inch, 1*inch])
    resumen_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_GUINDA),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 1), (-1, -1), COLOR_TEXTO),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GUINDA),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(resumen_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Tabla de historial de trazabilidad
    historial_titulo = Paragraph("HISTORIAL DE MOVIMIENTOS", styles['SeccionTitulo'])
    elements.append(historial_titulo)
    
    # Estilo para celdas de texto largo - Mejorado para wrap efectivo
    estilo_celda = ParagraphStyle(
        'CeldaTextoTraz',
        parent=styles['Normal'],
        fontSize=6,
        leading=8,
        wordWrap='CJK',
        splitLongWords=True,
    )
    
    # ISS-FIX: Incluir Subtipo, No. Expediente y Observaciones para trazabilidad completa
    data = [['Fecha', 'Tipo', 'Lote', 'Cant.', 'Centro', 'Usuario', 'Exp.', 'Observaciones']]
    
    for mov in trazabilidad_data:
        fecha = mov.get('fecha', mov.get('fecha_movimiento', ''))
        if hasattr(fecha, 'strftime'):
            fecha = fecha.strftime('%d/%m/%Y')
        else:
            # Convertir fecha string a formato corto sin truncar arbitrariamente
            fecha_str = str(fecha)
            if 'T' in fecha_str:
                fecha = fecha_str.split('T')[0]
            elif ' ' in fecha_str:
                fecha = fecha_str.split(' ')[0]
            else:
                fecha = fecha_str
        fecha_p = Paragraph(str(fecha), estilo_celda)
        
        cantidad = mov.get('cantidad', 0)
        tipo = str(mov.get('tipo', '')).upper()
        subtipo = mov.get('subtipo_salida', '')
        # SIN TRUNCAR - mostrar tipo completo con subtipo si existe
        if subtipo:
            tipo_display = f"{tipo}/{subtipo}"
        else:
            tipo_display = tipo
        tipo_p = Paragraph(tipo_display, estilo_celda)
        signo = '+' if tipo == 'ENTRADA' else ('-' if tipo == 'SALIDA' else '')
        
        # ISS-FIX: Centro SIN truncar - usar Paragraph para wrap automático
        centro = str(mov.get('centro_nombre', mov.get('centro', mov.get('destino', ''))))
        centro_paragraph = Paragraph(centro, estilo_celda)
        
        # No. Expediente - Campo crítico para trazabilidad de pacientes
        num_expediente = str(mov.get('numero_expediente', '') or '-')
        num_expediente_p = Paragraph(num_expediente, estilo_celda)
        
        # Usuario - usar Paragraph para wrap
        usuario = str(mov.get('usuario', mov.get('usuario_username', '')))
        usuario_p = Paragraph(usuario, estilo_celda)
        
        # ISS-FIX: Observaciones SIN truncar - usar Paragraph para wrap automático
        observaciones = str(mov.get('observaciones', mov.get('documento_referencia', mov.get('referencia', ''))) or '')
        obs_paragraph = Paragraph(observaciones, estilo_celda)
        
        # Lote SIN truncar - usar Paragraph
        lote_texto = str(mov.get('numero_lote', mov.get('lote', '')))
        lote_p = Paragraph(lote_texto, estilo_celda)
        
        data.append([
            fecha_p,
            tipo_p,
            lote_p,
            f"{signo}{cantidad}",
            centro_paragraph,
            usuario_p,
            num_expediente_p,
            obs_paragraph
        ])
    
    # ISS-FIX: Anchos recalculados - Página letter tiene 8.5", con márgenes 0.6" = 7.3" disponibles
    # Fecha:0.55 + Tipo:0.45 + Lote:0.6 + Cant:0.35 + Centro:1.5 + Usuario:0.6 + Exp:0.65 + Obs:1.6 = 6.3"
    col_widths = [0.55*inch, 0.45*inch, 0.6*inch, 0.35*inch, 1.5*inch, 0.6*inch, 0.65*inch, 1.6*inch]
    table = _crear_tabla_institucional(data, col_widths)
    elements.append(table)
    
    # Nota de trazabilidad
    elements.append(Spacer(1, 0.3*inch))
    nota_style = ParagraphStyle('Nota', parent=styles['Normal'], fontSize=8, textColor=COLOR_GRIS, alignment=TA_CENTER)
    elements.append(Paragraph(
        "Este reporte de trazabilidad cumple con los requisitos de la NOM-059-SSA1-2015 para el control de medicamentos.",
        nota_style
    ))
    
    # Usar canvas con fondo institucional
    def make_canvas(*args, **kwargs):
        return FondoOficialCanvas(*args, fondo_path=fondo_path, titulo_reporte='TRAZABILIDAD', **kwargs)
    
    doc.build(elements, canvasmaker=make_canvas)
    
    buffer.seek(0)
    logger.info(f"Reporte de trazabilidad PDF generado: {len(trazabilidad_data)} registros")
    return buffer


def generar_recibo_salida_movimiento(movimiento_data, finalizado=False):
    """
    Genera un PDF de recibo de salida para transferencias de inventario.
    
    Args:
        movimiento_data: dict con datos del movimiento:
            - folio: ID del movimiento
            - fecha: fecha del movimiento
            - tipo: tipo de movimiento (salida)
            - subtipo_salida: subtipo (transferencia, consumo, etc.)
            - centro_origen: dict con id y nombre del origen
            - centro_destino: dict con id y nombre del destino
            - cantidad: cantidad transferida
            - producto: nombre del producto
            - producto_clave: clave del producto
            - lote: número de lote
            - presentacion: presentación del producto
            - usuario: nombre del usuario que realizó el movimiento
            - observaciones: observaciones/motivo
        finalizado: si True, muestra sello de ENTREGADO en lugar de firmas
    
    Returns:
        BytesIO: Buffer con el PDF generado
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=50,
        leftMargin=50,
        topMargin=60,
        bottomMargin=50
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    title_style = ParagraphStyle(
        'TitleRecibo',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=1,
        spaceAfter=20,
        textColor=colors.Color(0.39, 0.14, 0.25)  # Color institucional
    )
    
    subtitle_style = ParagraphStyle(
        'SubtitleRecibo',
        parent=styles['Normal'],
        fontSize=12,
        alignment=1,
        spaceAfter=10
    )
    
    normal_style = ParagraphStyle(
        'NormalRecibo',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6
    )
    
    # Estilo para celdas de tabla con wrap
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        wordWrap='CJK'
    )
    
    cell_style_center = ParagraphStyle(
        'CellStyleCenter',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        alignment=1,
        wordWrap='CJK'
    )
    
    # Título según tipo
    subtipo = movimiento_data.get('subtipo_salida', 'transferencia') or 'transferencia'
    if subtipo.lower() == 'transferencia':
        titulo = "RECIBO DE TRANSFERENCIA DE MEDICAMENTOS"
    else:
        titulo = f"RECIBO DE SALIDA - {subtipo.upper()}"
    
    elements.append(Paragraph(titulo, title_style))
    elements.append(Paragraph("Sistema de Inventario Farmacéutico Penitenciario", subtitle_style))
    elements.append(Spacer(1, 15))
    
    # Información del movimiento
    folio = movimiento_data.get('folio', movimiento_data.get('id', 'N/A'))
    fecha = movimiento_data.get('fecha', datetime.now().strftime('%Y-%m-%d %H:%M'))
    if isinstance(fecha, str) and 'T' in fecha:
        fecha = fecha.replace('T', ' ')
    
    centro_origen = movimiento_data.get('centro_origen', {})
    if isinstance(centro_origen, dict):
        centro_origen_nombre = centro_origen.get('nombre', '') or 'Farmacia Central'
    else:
        centro_origen_nombre = str(centro_origen) if centro_origen else 'Farmacia Central'
    
    centro_destino = movimiento_data.get('centro_destino', {})
    if isinstance(centro_destino, dict):
        centro_destino_nombre = centro_destino.get('nombre', '') or 'N/A'
    else:
        centro_destino_nombre = str(centro_destino) if centro_destino else 'N/A'
    
    usuario = movimiento_data.get('usuario', 'Sistema')
    
    # Tabla de información con Paragraphs para word wrap
    info_data = [
        [Paragraph('<b>Folio:</b>', cell_style), Paragraph(f'MOV-{folio}', cell_style), 
         Paragraph('<b>Fecha:</b>', cell_style), Paragraph(str(fecha), cell_style)],
        [Paragraph('<b>Origen:</b>', cell_style), Paragraph(str(centro_origen_nombre), cell_style), 
         Paragraph('<b>Destino:</b>', cell_style), Paragraph(str(centro_destino_nombre), cell_style)],
        [Paragraph('<b>Registrado por:</b>', cell_style), Paragraph(str(usuario), cell_style), 
         Paragraph('<b>Tipo:</b>', cell_style), Paragraph(str(subtipo).capitalize(), cell_style)],
    ]
    
    # Anchos de columna balanceados
    info_table = Table(info_data, colWidths=[85, 155, 55, 185])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.95, 0.95, 0.95)),
        ('BACKGROUND', (2, 0), (2, -1), colors.Color(0.95, 0.95, 0.95)),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(info_table)
    
    elements.append(Spacer(1, 15))
    
    # Tabla de detalle del producto
    elements.append(Paragraph("<b>Detalle del Producto:</b>", normal_style))
    elements.append(Spacer(1, 10))
    
    producto = movimiento_data.get('producto', 'N/A')
    producto_clave = movimiento_data.get('producto_clave', 'N/A')
    lote = movimiento_data.get('lote', 'N/A')
    # Asegurar cantidad nunca negativa
    cantidad = max(0, abs(int(movimiento_data.get('cantidad', 0))))
    presentacion = movimiento_data.get('presentacion', 'N/A') or 'N/A'
    
    # Encabezados con estilo
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.white,
        alignment=1
    )
    
    # Tabla de detalle con Paragraphs para word wrap
    detalle_data = [
        [Paragraph('<b>Clave</b>', header_style), Paragraph('<b>Producto</b>', header_style), 
         Paragraph('<b>Lote</b>', header_style), Paragraph('<b>Cantidad</b>', header_style), 
         Paragraph('<b>Presentación</b>', header_style)],
        [Paragraph(str(producto_clave), cell_style_center), Paragraph(str(producto), cell_style_center), 
         Paragraph(str(lote), cell_style_center), Paragraph(str(cantidad), cell_style_center), 
         Paragraph(str(presentacion), cell_style_center)]
    ]
    
    # Anchos ajustados para mejor visualización (total ~480)
    detalle_table = Table(detalle_data, colWidths=[50, 160, 80, 50, 140])
    detalle_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.39, 0.14, 0.25)),  # Color institucional
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('WORDWRAP', (0, 0), (-1, -1), True),
    ]))
    elements.append(detalle_table)
    elements.append(Spacer(1, 20))
    
    # Observaciones si hay
    observaciones = movimiento_data.get('observaciones', '') or ''
    if observaciones:
        elements.append(Paragraph(f"<b>Observaciones:</b> {observaciones}", normal_style))
        elements.append(Spacer(1, 20))
    
    # Sección de firmas o sello de entregado
    if finalizado:
        # Mostrar sello de ENTREGADO centrado
        elements.append(Spacer(1, 30))
        
        entregado_box = Table(
            [['✓ ENTREGADO']],
            colWidths=[200]
        )
        entregado_box.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 24),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.Color(0.2, 0.6, 0.2)),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOX', (0, 0), (-1, -1), 3, colors.Color(0.2, 0.6, 0.2)),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ]))
        
        # Centrar el sello usando una tabla contenedora con alineación central
        centered_table = Table(
            [[entregado_box]], 
            colWidths=[500]
        )
        centered_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(centered_table)
        elements.append(Spacer(1, 10))
        
        fecha_entrega = movimiento_data.get('fecha_entrega', datetime.now().strftime('%d/%m/%Y %H:%M'))
        elements.append(Paragraph(
            f"Fecha de confirmación: {fecha_entrega}",
            ParagraphStyle('FechaEntrega', parent=styles['Normal'], fontSize=10, alignment=1)
        ))
    else:
        # Campos para firmas (AUTORIZA, ENTREGA, RECIBE)
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("<b>FIRMAS DE CONFORMIDAD</b>", ParagraphStyle(
            'FirmasTitle',
            parent=styles['Normal'],
            fontSize=12,
            alignment=1,
            spaceAfter=20
        )))
        
        firma_data = [
            ['', '', ''],
            ['_' * 30, '_' * 30, '_' * 30],
            ['AUTORIZA', 'ENTREGA', 'RECIBE'],
            ['Nombre:', 'Nombre:', 'Nombre:'],
            ['Cargo:', 'Cargo:', 'Cargo:'],
            ['Fecha:', 'Fecha:', 'Fecha:'],
        ]
        
        firma_table = Table(firma_data, colWidths=[160, 160, 160])
        firma_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 40),  # Espacio para firma
        ]))
        elements.append(firma_table)
    
    # Pie de página con fecha/hora de generación
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(
        f"Documento generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M:%S')}",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, alignment=1, textColor=colors.grey)
    ))
    
    # Usar canvas con fondo institucional
    colores_tema = _obtener_colores_tema()
    fondo_path = colores_tema.get('fondo_reportes_path')
    if not fondo_path:
        fondo_path = str(FONDO_INSTITUCIONAL_PATH) if FONDO_INSTITUCIONAL_PATH.exists() else None
    
    def make_canvas(*args, **kwargs):
        return FondoOficialCanvas(*args, fondo_path=fondo_path, titulo_reporte='TRANSFERENCIA', **kwargs)
    
    # Construir PDF con fondo institucional
    doc.build(elements, canvasmaker=make_canvas)
    
    buffer.seek(0)
    logger.info(f"Recibo de salida/transferencia PDF generado - Folio: MOV-{folio}")
    return buffer


def generar_recibo_salida_donacion(movimiento_data, items_data=None, finalizado=False):
    """
    Genera un PDF de recibo de salida con campos para firmas.
    
    Args:
        movimiento_data: dict con datos del movimiento
        items_data: lista de items del movimiento (opcional)
        finalizado: si True, muestra sello de ENTREGADO en lugar de firmas
    
    Returns:
        BytesIO: Buffer con el PDF generado
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=50,
        leftMargin=50,
        topMargin=60,
        bottomMargin=50
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    title_style = ParagraphStyle(
        'TitleRecibo',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=1,
        spaceAfter=20
    )
    
    subtitle_style = ParagraphStyle(
        'SubtitleRecibo',
        parent=styles['Normal'],
        fontSize=12,
        alignment=1,
        spaceAfter=10
    )
    
    normal_style = ParagraphStyle(
        'NormalRecibo',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6
    )
    
    # Título
    elements.append(Paragraph("RECIBO DE SALIDA DE MEDICAMENTOS", title_style))
    elements.append(Paragraph("Sistema de Farmacia Penitenciaria", subtitle_style))
    elements.append(Spacer(1, 15))
    
    # Información del movimiento
    folio = movimiento_data.get('folio', movimiento_data.get('id', 'N/A'))
    fecha = movimiento_data.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    if isinstance(fecha, str) and 'T' in fecha:
        fecha = fecha.split('T')[0]
    
    centro_origen = movimiento_data.get('centro_origen', 'Central')
    if isinstance(centro_origen, dict):
        centro_origen = centro_origen.get('nombre', centro_origen.get('id', 'Central'))
    
    centro_destino = movimiento_data.get('centro_destino', '')
    if isinstance(centro_destino, dict):
        centro_destino = centro_destino.get('nombre', centro_destino.get('id', ''))
    
    tipo = movimiento_data.get('tipo', 'Salida')
    subtipo = movimiento_data.get('subtipo_salida', 'Transferencia')
    
    # Tabla de información general
    info_data = [
        ['Folio:', str(folio), 'Fecha:', str(fecha)],
        ['Origen:', str(centro_origen), 'Destino:', str(centro_destino)],
        ['Tipo:', str(tipo).capitalize(), 'Subtipo:', str(subtipo).capitalize()],
    ]
    
    info_table = Table(info_data, colWidths=[70, 170, 70, 170])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.95, 0.95, 0.95)),
        ('BACKGROUND', (2, 0), (2, -1), colors.Color(0.95, 0.95, 0.95)),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 20))
    
    # Tabla de items si hay
    if items_data and len(items_data) > 0:
        elements.append(Paragraph("<b>Detalle de Productos:</b>", normal_style))
        elements.append(Spacer(1, 10))
        
        # Estilo para celdas con texto largo
        item_cell_style = ParagraphStyle(
            'ItemCellStyle',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            wordWrap='CJK',
        )
        
        items_header = ['#', 'Producto', 'Lote', 'Cantidad', 'Presentación']
        items_rows = [items_header]
        
        for idx, item in enumerate(items_data, 1):
            producto = item.get('producto', item.get('producto_nombre', ''))
            if isinstance(producto, dict):
                producto = producto.get('nombre', str(producto.get('id', '')))
            
            lote = item.get('lote', item.get('numero_lote', ''))
            if isinstance(lote, dict):
                lote = lote.get('numero_lote', str(lote.get('id', '')))
            
            cantidad = item.get('cantidad', 0)
            presentacion = item.get('presentacion', item.get('presentacion_producto', 'N/A'))
            
            # SIN TRUNCAR - usar Paragraph para wrap automático
            producto_p = Paragraph(str(producto), item_cell_style)
            lote_p = Paragraph(str(lote), item_cell_style)
            presentacion_p = Paragraph(str(presentacion), item_cell_style)
            
            items_rows.append([
                str(idx),
                producto_p,
                lote_p,
                str(cantidad),
                presentacion_p
            ])
        
        items_table = Table(items_rows, colWidths=[30, 180, 100, 60, 110])
        items_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.4, 0.6)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(items_table)
    else:
        # Si no hay items detallados, mostrar resumen del movimiento
        producto = movimiento_data.get('producto', movimiento_data.get('producto_nombre', ''))
        if isinstance(producto, dict):
            producto = producto.get('nombre', str(producto.get('id', '')))
        
        lote = movimiento_data.get('lote', movimiento_data.get('numero_lote', ''))
        if isinstance(lote, dict):
            lote = lote.get('numero_lote', str(lote.get('id', '')))
        
        cantidad = movimiento_data.get('cantidad', 0)
        presentacion = movimiento_data.get('presentacion', 'N/A')
        
        # Estilo para celdas con texto que puede ser largo
        cell_style = ParagraphStyle(
            'CellStyle',
            parent=styles['Normal'],
            fontSize=9,
            alignment=0,  # LEFT
            wordWrap='CJK',  # Permite word wrap
        )
        cell_style_center = ParagraphStyle(
            'CellStyleCenter',
            parent=styles['Normal'],
            fontSize=9,
            alignment=1,  # CENTER
        )
        
        # Usar Paragraph para que el texto se ajuste automáticamente
        simple_data = [
            ['Producto', 'Lote', 'Cantidad', 'Presentación'],
            [
                Paragraph(str(producto) if producto else 'N/A', cell_style),
                Paragraph(str(lote) if lote else 'N/A', cell_style),
                Paragraph(str(cantidad), cell_style_center),
                Paragraph(str(presentacion) if presentacion else 'N/A', cell_style)
            ]
        ]
        
        # Ajustar anchos de columna para mejor distribución
        simple_table = Table(simple_data, colWidths=[200, 120, 60, 100])
        simple_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.4, 0.6)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(Paragraph("<b>Detalle:</b>", normal_style))
        elements.append(Spacer(1, 10))
        elements.append(simple_table)
    
    elements.append(Spacer(1, 30))
    
    # Observaciones si hay
    observaciones = movimiento_data.get('observaciones', movimiento_data.get('motivo', ''))
    if observaciones:
        elements.append(Paragraph(f"<b>Observaciones:</b> {observaciones}", normal_style))
        elements.append(Spacer(1, 20))
    
    # Sección de firmas o sello de entregado
    if finalizado:
        # Mostrar sello de ENTREGADO
        elements.append(Spacer(1, 30))
        
        entregado_style = ParagraphStyle(
            'Entregado',
            parent=styles['Heading1'],
            fontSize=24,
            alignment=1,
            textColor=colors.Color(0.2, 0.6, 0.2),
            borderWidth=2,
            borderColor=colors.Color(0.2, 0.6, 0.2),
            borderPadding=10
        )
        
        fecha_entrega = movimiento_data.get('fecha_entrega', datetime.now().strftime('%Y-%m-%d %H:%M'))
        elements.append(Paragraph("✓ ENTREGADO", entregado_style))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(f"Fecha de entrega: {fecha_entrega}", ParagraphStyle(
            'FechaEntrega',
            parent=styles['Normal'],
            fontSize=10,
            alignment=1
        )))
    else:
        # Campos para firmas
        elements.append(Paragraph("<b>FIRMAS DE CONFORMIDAD</b>", ParagraphStyle(
            'FirmasTitle',
            parent=styles['Normal'],
            fontSize=12,
            alignment=1,
            spaceAfter=20
        )))
        
        firma_data = [
            ['', '', ''],
            ['_' * 30, '_' * 30, '_' * 30],
            ['AUTORIZA', 'ENTREGA', 'RECIBE'],
            ['Nombre:', 'Nombre:', 'Nombre:'],
            ['Cargo:', 'Cargo:', 'Cargo:'],
            ['Fecha:', 'Fecha:', 'Fecha:'],
        ]
        
        firma_table = Table(firma_data, colWidths=[160, 160, 160])
        firma_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 40),  # Espacio para firma
        ]))
        elements.append(firma_table)
    
    # Pie de página con fecha/hora de generación
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(
        f"Documento generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M:%S')}",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, alignment=1, textColor=colors.grey)
    ))
    
    # Usar canvas con fondo institucional
    colores_tema = _obtener_colores_tema()
    fondo_path = colores_tema.get('fondo_reportes_path')
    if not fondo_path:
        fondo_path = str(FONDO_INSTITUCIONAL_PATH) if FONDO_INSTITUCIONAL_PATH.exists() else None
    
    def make_canvas(*args, **kwargs):
        return FondoOficialCanvas(*args, fondo_path=fondo_path, titulo_reporte='DONACIÓN', **kwargs)
    
    # Construir PDF con fondo institucional
    doc.build(elements, canvasmaker=make_canvas)
    
    buffer.seek(0)
    logger.info(f"Recibo de salida PDF generado - Folio: {folio}")
    return buffer


def generar_tarjeta_entradas_salidas_formato_b(lote_info, movimientos_data, es_cprs=False):
    """
    Genera PDF con formato oficial "Tarjeta de Entradas/Salidas de Almacén (B)".
    
    Este formato es el kardex oficial por producto/lote que registra cada movimiento
    con detalle. Compatible tanto para CIA (Farmacia Central) como para CPRS (Centros).
    
    Args:
        lote_info: dict con información del lote:
            - numero_lote: Número del lote
            - producto_nombre: Nombre del insumo médico
            - producto_clave: Clave del insumo
            - presentacion: Presentación farmacéutica
            - fecha_caducidad: Fecha de vencimiento
            - centro_nombre: Nombre de la institución (None = CIA)
            - numero_contrato: Número de contrato
        movimientos_data: Lista de movimientos con:
            - fecha: Fecha del movimiento
            - folio_documento: Folio/documento de entrada
            - cantidad: Cantidad (positivo entrada, negativo salida)
            - tipo: ENTRADA, SALIDA
            - saldo: Saldo acumulado tras el movimiento
            - usuario: Nombre del personal responsable
            - observaciones: Observaciones
        es_cprs: True si es para Centro Penitenciario, False para CIA
    
    Returns:
        BytesIO: Buffer con el PDF generado en formato oficial B
    """
    buffer = BytesIO()
    
    # Usar orientación vertical para formato tarjeta
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=1.8*inch,
        bottomMargin=1.0*inch,
        leftMargin=0.5*inch,
        rightMargin=0.5*inch
    )
    
    elements = []
    styles = _obtener_estilos_institucionales()
    colores_tema = _obtener_colores_tema()
    
    # Obtener fondo institucional
    fondo_path = colores_tema.get('fondo_reportes_path')
    if not fondo_path:
        fondo_path = str(FONDO_INSTITUCIONAL_PATH) if FONDO_INSTITUCIONAL_PATH.exists() else None
    
    # ========== TÍTULO ==========
    tipo_institucion = "Centro Penitenciario y de Reinserción Social" if es_cprs else "Centro de Información y Abastecimiento"
    titulo = Paragraph(f"<b>Tarjeta de Entradas/Salidas de Almacén (B)</b>", styles['TituloReporte'])
    elements.append(titulo)
    elements.append(Spacer(1, 0.15*inch))
    
    # ========== ENCABEZADO CON INFO DEL LOTE ==========
    # Estilo para labels
    label_style = ParagraphStyle('LabelB', parent=styles['Normal'], fontSize=8, textColor=COLOR_TEXTO)
    value_style = ParagraphStyle('ValueB', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold')
    
    # Nombre de la institución
    institucion_nombre = lote_info.get('centro_nombre') or 'Farmacia Central (CIA)'
    
    # Información del producto en tabla de encabezado
    header_data = [
        [Paragraph(f"<b>Institución Penitenciaria:</b>", label_style), 
         Paragraph(institucion_nombre, value_style), '', ''],
        [Paragraph(f"<b>Insumo médico:</b>", label_style), 
         Paragraph(str(lote_info.get('producto_nombre', 'N/A')), value_style),
         Paragraph(f"<b>Clave:</b>", label_style),
         Paragraph(str(lote_info.get('producto_clave', 'N/A')), value_style)],
        [Paragraph(f"<b>Presentación:</b>", label_style), 
         Paragraph(str(lote_info.get('presentacion', 'N/A')), value_style),
         Paragraph(f"<b>Fecha de Caducidad:</b>", label_style),
         Paragraph(str(lote_info.get('fecha_caducidad', 'N/A')), value_style)],
        [Paragraph(f"<b>No. Lote:</b>", label_style), 
         Paragraph(str(lote_info.get('numero_lote', 'N/A')), value_style),
         Paragraph(f"<b>No. Contrato:</b>", label_style),
         Paragraph(str(lote_info.get('numero_contrato', 'N/A')), value_style)],
    ]
    
    header_table = Table(header_data, colWidths=[1.2*inch, 2.6*inch, 1.2*inch, 2.4*inch])
    header_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_TEXTO),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GUINDA),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#FBF2F5')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#FBF2F5')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # ========== TABLA DE MOVIMIENTOS (FORMATO B) ==========
    # Encabezados según formato oficial
    mov_header = [
        Paragraph('<b>Fecha</b>', label_style),
        Paragraph('<b>Documento<br/>Entrada (Folio)</b>', label_style),
        Paragraph('<b>Entrada<br/>Piezas</b>', label_style),
        Paragraph('<b>Salida<br/>Piezas</b>', label_style),
        Paragraph('<b>Existencia<br/>Piezas</b>', label_style),
        Paragraph('<b>Nombre y firma<br/>del personal</b>', label_style),
    ]
    
    mov_data = [mov_header]
    
    # Estilo para celdas
    celda_style = ParagraphStyle('CeldaB', parent=styles['Normal'], fontSize=7, leading=9, wordWrap='CJK')
    
    for mov in movimientos_data:
        fecha = mov.get('fecha', '')
        if hasattr(fecha, 'strftime'):
            fecha = fecha.strftime('%d/%m/%Y')
        
        # Documento de entrada (folio)
        folio = mov.get('folio_documento', '') or mov.get('observaciones', '') or '-'
        folio_p = Paragraph(str(folio)[:50], celda_style)
        
        # Cantidad: positivo = entrada, negativo = salida
        cantidad = mov.get('cantidad', 0)
        tipo = str(mov.get('tipo', '')).upper()
        
        if tipo == 'ENTRADA' or cantidad > 0:
            entrada = str(abs(cantidad))
            salida = ''
        else:
            entrada = ''
            salida = str(abs(cantidad))
        
        # Saldo/existencia
        saldo = mov.get('saldo', 0)
        
        # Personal responsable
        usuario = mov.get('usuario', '') or mov.get('usuario_nombre', '') or 'Sistema'
        usuario_p = Paragraph(str(usuario), celda_style)
        
        mov_data.append([
            str(fecha),
            folio_p,
            entrada,
            salida,
            str(saldo),
            usuario_p,
        ])
    
    # Anchos de columna para formato B
    mov_col_widths = [0.8*inch, 1.8*inch, 0.7*inch, 0.7*inch, 0.8*inch, 2.0*inch]
    
    mov_table = Table(mov_data, colWidths=mov_col_widths)
    mov_table.setStyle(TableStyle([
        # Encabezado
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_GUINDA),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        # Datos
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('TEXTCOLOR', (0, 1), (-1, -1), COLOR_TEXTO),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GUINDA),
        ('ALIGN', (2, 1), (4, -1), 'CENTER'),  # Centrar números
        ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        # Filas alternas
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9F9F9')]),
    ]))
    elements.append(mov_table)
    
    # ========== SECCIÓN DE FIRMA ==========
    elements.append(Spacer(1, 0.4*inch))
    
    firma_data = [
        ['', ''],
        ['_' * 40, '_' * 40],
        ['Revisó', 'Elaboró'],
        ['Nombre y cargo:', 'Nombre y cargo:'],
    ]
    
    firma_table = Table(firma_data, colWidths=[3.5*inch, 3.5*inch])
    firma_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, 0), 30),  # Espacio para firma
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(firma_table)
    
    # ========== PIE DE PÁGINA ==========
    elements.append(Spacer(1, 0.3*inch))
    nota_style = ParagraphStyle('NotaB', parent=styles['Normal'], fontSize=7, textColor=COLOR_GRIS, alignment=TA_CENTER)
    elements.append(Paragraph(
        f"Formato B - Tarjeta de Entradas/Salidas de Almacén | {'CPRS' if es_cprs else 'CIA'} | Generado: {timezone.now().strftime('%d/%m/%Y %H:%M')}",
        nota_style
    ))
    
    # Usar canvas con fondo institucional
    def make_canvas(*args, **kwargs):
        return FondoOficialCanvas(*args, fondo_path=fondo_path, titulo_reporte='FORMATO B', **kwargs)
    
    doc.build(elements, canvasmaker=make_canvas)
    
    buffer.seek(0)
    logger.info(f"Tarjeta Formato B generada - Lote: {lote_info.get('numero_lote')}, Movimientos: {len(movimientos_data)}")
    return buffer


def generar_recibo_salida_requisicion(requisicion_data, detalles_data):
    """
    Genera PDF con formato oficial "Recibo de Salida del Almacén".
    
    Este formato acompaña el envío físico de medicamentos del CIA a un CPRS
    cuando se surte una requisición.
    
    Args:
        requisicion_data: dict con información de la requisición:
            - folio: Folio de la requisición
            - numero: Número de requisición
            - fecha_surtido: Fecha en que se surtió
            - centro_nombre: Nombre del CPRS destino
            - centro_direccion: Dirección del centro (opcional)
            - usuario_surtido: Nombre del usuario que surtió
            - periodo: Periodo correspondiente (opcional)
            - observaciones: Observaciones generales
        detalles_data: Lista de items surtidos con:
            - producto_clave: Clave del producto
            - producto_nombre: Nombre del medicamento/material
            - presentacion: Presentación
            - lote: Número de lote
            - fecha_caducidad: Fecha de vencimiento
            - cantidad_surtida: Cantidad enviada
            - precio_unitario: Precio por unidad (opcional)
    
    Returns:
        BytesIO: Buffer con el PDF generado en formato Recibo de Salida
    """
    buffer = BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=1.8*inch,
        bottomMargin=1.0*inch,
        leftMargin=0.5*inch,
        rightMargin=0.5*inch
    )
    
    elements = []
    styles = _obtener_estilos_institucionales()
    colores_tema = _obtener_colores_tema()
    
    # Obtener fondo institucional
    fondo_path = colores_tema.get('fondo_reportes_path')
    if not fondo_path:
        fondo_path = str(FONDO_INSTITUCIONAL_PATH) if FONDO_INSTITUCIONAL_PATH.exists() else None
    
    # ========== TÍTULO ==========
    titulo = Paragraph("<b>RECIBO DE SALIDA DEL ALMACÉN</b>", styles['TituloReporte'])
    elements.append(titulo)
    elements.append(Spacer(1, 0.15*inch))
    
    # ========== INFORMACIÓN DEL RECIBO ==========
    label_style = ParagraphStyle('LabelRS', parent=styles['Normal'], fontSize=8, textColor=COLOR_TEXTO)
    value_style = ParagraphStyle('ValueRS', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold')
    
    # Folio y fecha
    folio = requisicion_data.get('folio') or requisicion_data.get('numero', 'N/A')
    fecha_surtido = requisicion_data.get('fecha_surtido', timezone.now().strftime('%d/%m/%Y'))
    if hasattr(fecha_surtido, 'strftime'):
        fecha_surtido = fecha_surtido.strftime('%d/%m/%Y %H:%M')
    
    centro_nombre = requisicion_data.get('centro_nombre', 'No especificado')
    periodo = requisicion_data.get('periodo', '')
    
    # Tabla de encabezado del recibo
    header_data = [
        [Paragraph("<b>Folio:</b>", label_style), 
         Paragraph(str(folio), value_style),
         Paragraph("<b>Fecha de Elaboración:</b>", label_style),
         Paragraph(str(fecha_surtido), value_style)],
        [Paragraph("<b>C.P.R.S. Destino:</b>", label_style), 
         Paragraph(str(centro_nombre), value_style),
         Paragraph("<b>Periodo:</b>", label_style),
         Paragraph(str(periodo) if periodo else 'N/A', value_style)],
    ]
    
    header_table = Table(header_data, colWidths=[1.3*inch, 2.4*inch, 1.4*inch, 2.3*inch])
    header_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_TEXTO),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GUINDA),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#FBF2F5')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#FBF2F5')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # ========== TABLA DE PRODUCTOS SURTIDOS ==========
    # Encabezados
    detalle_header = [
        Paragraph('<b>No.</b>', label_style),
        Paragraph('<b>Clave</b>', label_style),
        Paragraph('<b>Medicamento/Material</b>', label_style),
        Paragraph('<b>Presentación</b>', label_style),
        Paragraph('<b>Lote</b>', label_style),
        Paragraph('<b>Caducidad</b>', label_style),
        Paragraph('<b>Cantidad<br/>Surtida</b>', label_style),
    ]
    
    detalle_data = [detalle_header]
    celda_style = ParagraphStyle('CeldaRS', parent=styles['Normal'], fontSize=7, leading=9, wordWrap='CJK')
    
    total_piezas = 0
    for idx, item in enumerate(detalles_data, 1):
        cantidad_surtida = item.get('cantidad_surtida', 0)
        total_piezas += cantidad_surtida
        
        # Fecha caducidad
        fecha_cad = item.get('fecha_caducidad', 'N/A')
        if hasattr(fecha_cad, 'strftime'):
            fecha_cad = fecha_cad.strftime('%d/%m/%Y')
        
        detalle_data.append([
            str(idx),
            Paragraph(str(item.get('producto_clave', '')), celda_style),
            Paragraph(str(item.get('producto_nombre', ''))[:60], celda_style),
            Paragraph(str(item.get('presentacion', ''))[:30], celda_style),
            str(item.get('lote', 'N/A')),
            str(fecha_cad),
            str(cantidad_surtida),
        ])
    
    # Fila de totales
    detalle_data.append([
        '', '', '', '', '', Paragraph('<b>TOTAL:</b>', celda_style), f'<b>{total_piezas}</b>'
    ])
    
    # Anchos de columna
    detalle_col_widths = [0.4*inch, 0.8*inch, 2.2*inch, 1.0*inch, 0.8*inch, 0.8*inch, 0.7*inch]
    
    detalle_table = Table(detalle_data, colWidths=detalle_col_widths)
    detalle_table.setStyle(TableStyle([
        # Encabezado
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_GUINDA),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        # Datos
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('TEXTCOLOR', (0, 1), (-1, -1), COLOR_TEXTO),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GUINDA),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Número
        ('ALIGN', (6, 1), (6, -1), 'CENTER'),  # Cantidad
        ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        # Filas alternas
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#F9F9F9')]),
        # Fila de totales
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#FBF2F5')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    elements.append(detalle_table)
    
    # ========== OBSERVACIONES ==========
    observaciones = requisicion_data.get('observaciones', '')
    if observaciones:
        elements.append(Spacer(1, 0.15*inch))
        obs_style = ParagraphStyle('ObsRS', parent=styles['Normal'], fontSize=8)
        elements.append(Paragraph(f"<b>Observaciones:</b> {observaciones}", obs_style))
    
    # ========== SECCIÓN DE FIRMAS ==========
    elements.append(Spacer(1, 0.4*inch))
    
    usuario_surtido = requisicion_data.get('usuario_surtido', '')
    
    firma_data = [
        ['', '', ''],
        ['_' * 35, '_' * 35, '_' * 35],
        ['AUTORIZA', 'ENTREGA', 'RECIBE'],
        [Paragraph(f'<font size="7">{usuario_surtido}</font>', celda_style) if usuario_surtido else '', '', ''],
        ['Nombre y cargo', 'Nombre y cargo', 'Nombre y cargo'],
    ]
    
    firma_table = Table(firma_data, colWidths=[2.4*inch, 2.4*inch, 2.4*inch])
    firma_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTSIZE', (0, 4), (-1, 4), 7),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, 0), 30),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TEXTCOLOR', (0, 4), (-1, 4), COLOR_GRIS),
    ]))
    elements.append(firma_table)
    
    # ========== PIE DE PÁGINA ==========
    elements.append(Spacer(1, 0.3*inch))
    nota_style = ParagraphStyle('NotaRS', parent=styles['Normal'], fontSize=7, textColor=COLOR_GRIS, alignment=TA_CENTER)
    elements.append(Paragraph(
        f"Recibo de Salida de Almacén | Folio: {folio} | Generado: {timezone.now().strftime('%d/%m/%Y %H:%M')}",
        nota_style
    ))
    
    # Usar canvas con fondo institucional
    def make_canvas(*args, **kwargs):
        return FondoOficialCanvas(*args, fondo_path=fondo_path, titulo_reporte='RECIBO SALIDA', **kwargs)
    
    doc.build(elements, canvasmaker=make_canvas)
    
    buffer.seek(0)
    logger.info(f"Recibo de Salida PDF generado - Folio: {folio}, Items: {len(detalles_data)}")
    return buffer


def generar_control_mensual_almacen(periodo_data, productos_data, centro_nombre=None):
    """
    Genera PDF con formato oficial "Control Mensual de Almacén (Formato A)".
    
    Registro mensual consolidado de todos los insumos médicos, mostrando
    existencias anteriores, entradas, salidas y saldo final.
    
    Args:
        periodo_data: dict con información del periodo:
            - mes: Número del mes (1-12)
            - anio: Año
            - fecha_inicio: Fecha inicio del periodo
            - fecha_fin: Fecha fin del periodo
            - fecha_elaboracion: Fecha de elaboración del reporte
        productos_data: Lista de productos con movimientos:
            - producto_clave: Clave del insumo
            - producto_nombre: Nombre del medicamento
            - presentacion: Forma farmacéutica
            - lote: Número de lote
            - fecha_caducidad: Vencimiento
            - existencia_anterior: Stock al inicio del periodo
            - documento_entrada: Folio del documento de entrada
            - entradas: Total de entradas en el periodo
            - salidas: Total de salidas en el periodo
            - existencia_final: Saldo al final del periodo
        centro_nombre: Nombre de la institución (None = CIA/Farmacia Central)
    
    Returns:
        BytesIO: Buffer con el PDF generado en formato Control Mensual A
    """
    buffer = BytesIO()
    
    # Usar orientación horizontal para más columnas
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        topMargin=1.5*inch,
        bottomMargin=0.8*inch,
        leftMargin=0.4*inch,
        rightMargin=0.4*inch
    )
    
    elements = []
    styles = _obtener_estilos_institucionales()
    colores_tema = _obtener_colores_tema()
    
    # Obtener fondo institucional
    fondo_path = colores_tema.get('fondo_reportes_path')
    if not fondo_path:
        fondo_path = str(FONDO_INSTITUCIONAL_PATH) if FONDO_INSTITUCIONAL_PATH.exists() else None
    
    # ========== TÍTULO ==========
    titulo = Paragraph("<b>CONTROL MENSUAL DE ALMACÉN (A)</b>", styles['TituloReporte'])
    elements.append(titulo)
    elements.append(Spacer(1, 0.1*inch))
    
    # ========== ENCABEZADO DEL REPORTE ==========
    label_style = ParagraphStyle('LabelCM', parent=styles['Normal'], fontSize=8, textColor=COLOR_TEXTO)
    value_style = ParagraphStyle('ValueCM', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold')
    
    # Información del periodo
    mes = periodo_data.get('mes', timezone.now().month)
    anio = periodo_data.get('anio', timezone.now().year)
    meses_nombres = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                     'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    periodo_texto = f"{meses_nombres[mes]} {anio}"
    
    fecha_elaboracion = periodo_data.get('fecha_elaboracion', timezone.now().strftime('%d/%m/%Y'))
    if hasattr(fecha_elaboracion, 'strftime'):
        fecha_elaboracion = fecha_elaboracion.strftime('%d/%m/%Y')
    
    institucion = centro_nombre or 'Almacén Central de Medicamentos (CIA)'
    
    header_data = [
        [Paragraph("<b>Institución Penitenciaria:</b>", label_style), 
         Paragraph(str(institucion), value_style),
         Paragraph("<b>Fecha de Elaboración:</b>", label_style),
         Paragraph(str(fecha_elaboracion), value_style)],
        [Paragraph("<b>Periodo:</b>", label_style), 
         Paragraph(periodo_texto, value_style),
         '', ''],
    ]
    
    header_table = Table(header_data, colWidths=[1.5*inch, 4.0*inch, 1.5*inch, 2.5*inch])
    header_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_TEXTO),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GUINDA),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#FBF2F5')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#FBF2F5')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('SPAN', (1, 1), (3, 1)),  # Unir celdas de periodo
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.15*inch))
    
    # ========== TABLA DE CONTROL MENSUAL ==========
    # Encabezados según formato oficial A
    control_header = [
        Paragraph('<b>Clave</b>', label_style),
        Paragraph('<b>Insumo Médico</b>', label_style),
        Paragraph('<b>Presentación</b>', label_style),
        Paragraph('<b>Lote</b>', label_style),
        Paragraph('<b>Fecha<br/>Caducidad</b>', label_style),
        Paragraph('<b>Existencia<br/>Anterior</b>', label_style),
        Paragraph('<b>Doc. Entrada<br/>(Folio)</b>', label_style),
        Paragraph('<b>Entrada</b>', label_style),
        Paragraph('<b>Salida</b>', label_style),
        Paragraph('<b>Existencia<br/>Final</b>', label_style),
    ]
    
    control_data = [control_header]
    celda_style = ParagraphStyle('CeldaCM', parent=styles['Normal'], fontSize=6, leading=8, wordWrap='CJK')
    
    totales = {'existencia_anterior': 0, 'entradas': 0, 'salidas': 0, 'existencia_final': 0}
    
    for item in productos_data:
        # Fecha caducidad
        fecha_cad = item.get('fecha_caducidad', 'N/A')
        if hasattr(fecha_cad, 'strftime'):
            fecha_cad = fecha_cad.strftime('%d/%m/%Y')
        
        existencia_anterior = item.get('existencia_anterior', 0) or 0
        entradas = item.get('entradas', 0) or 0
        salidas = item.get('salidas', 0) or 0
        existencia_final = item.get('existencia_final', 0) or 0
        
        totales['existencia_anterior'] += existencia_anterior
        totales['entradas'] += entradas
        totales['salidas'] += salidas
        totales['existencia_final'] += existencia_final
        
        control_data.append([
            Paragraph(str(item.get('producto_clave', ''))[:20], celda_style),
            Paragraph(str(item.get('producto_nombre', ''))[:50], celda_style),
            Paragraph(str(item.get('presentacion', ''))[:25], celda_style),
            str(item.get('lote', 'N/A'))[:15],
            str(fecha_cad),
            str(existencia_anterior),
            Paragraph(str(item.get('documento_entrada', '') or '-')[:20], celda_style),
            str(entradas),
            str(salidas),
            str(existencia_final),
        ])
    
    # Fila de totales
    control_data.append([
        '', '', '', '', Paragraph('<b>TOTALES:</b>', celda_style),
        f"<b>{totales['existencia_anterior']}</b>",
        '',
        f"<b>{totales['entradas']}</b>",
        f"<b>{totales['salidas']}</b>",
        f"<b>{totales['existencia_final']}</b>",
    ])
    
    # Anchos de columna para landscape
    control_col_widths = [0.7*inch, 2.5*inch, 1.0*inch, 0.7*inch, 0.7*inch, 0.6*inch, 0.9*inch, 0.55*inch, 0.55*inch, 0.6*inch]
    
    control_table = Table(control_data, colWidths=control_col_widths)
    control_table.setStyle(TableStyle([
        # Encabezado
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_GUINDA),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 6),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        # Datos
        ('FONTSIZE', (0, 1), (-1, -1), 6),
        ('TEXTCOLOR', (0, 1), (-1, -1), COLOR_TEXTO),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GUINDA),
        ('ALIGN', (5, 1), (5, -1), 'CENTER'),  # Existencia anterior
        ('ALIGN', (7, 1), (9, -1), 'CENTER'),  # Entradas, Salidas, Existencia
        ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        # Filas alternas
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#F9F9F9')]),
        # Fila de totales
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#FBF2F5')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    elements.append(control_table)
    
    # ========== SECCIÓN DE FIRMAS ==========
    elements.append(Spacer(1, 0.3*inch))
    
    firma_data = [
        ['', ''],
        ['_' * 45, '_' * 45],
        ['Revisó / Vo. Bo.', 'Elaboró'],
        ['Nombre y cargo:', 'Nombre y cargo:'],
    ]
    
    firma_table = Table(firma_data, colWidths=[4.5*inch, 4.5*inch])
    firma_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTSIZE', (0, 3), (-1, 3), 7),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, 0), 25),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TEXTCOLOR', (0, 3), (-1, 3), COLOR_GRIS),
    ]))
    elements.append(firma_table)
    
    # ========== PIE DE PÁGINA ==========
    elements.append(Spacer(1, 0.2*inch))
    nota_style = ParagraphStyle('NotaCM', parent=styles['Normal'], fontSize=7, textColor=COLOR_GRIS, alignment=TA_CENTER)
    elements.append(Paragraph(
        f"Formato A - Control Mensual de Almacén | {institucion} | Periodo: {periodo_texto} | Generado: {timezone.now().strftime('%d/%m/%Y %H:%M')}",
        nota_style
    ))
    
    # Usar canvas con fondo institucional para landscape
    class LandscapeFondoCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            self.fondo_path = fondo_path
            canvas.Canvas.__init__(self, *args, **kwargs)
            self._dibujar_fondo()
        
        def showPage(self):
            canvas.Canvas.showPage(self)
            self._dibujar_fondo()
        
        def _dibujar_fondo(self):
            if self.fondo_path and os.path.exists(self.fondo_path):
                try:
                    page_width, page_height = landscape(letter)
                    self.drawImage(
                        str(self.fondo_path),
                        0, 0,
                        width=page_width,
                        height=page_height,
                        preserveAspectRatio=False,
                        mask='auto'
                    )
                except Exception as e:
                    logger.warning(f"No se pudo cargar imagen de fondo: {e}")
    
    doc.build(elements, canvasmaker=LandscapeFondoCanvas)
    
    buffer.seek(0)
    logger.info(f"Control Mensual PDF generado - Periodo: {periodo_texto}, Items: {len(productos_data)}")
    return buffer

# =============================================================================
# FORMATO C - DISPENSACIÓN A PACIENTES
# =============================================================================

def generar_formato_c_dispensacion(dispensacion):
    """
    Genera el PDF Formato C de Dispensación a Pacientes.
    
    Documento oficial para registro de entrega de medicamentos a internos,
    con trazabilidad completa de productos y firmas de recepción.
    
    Args:
        dispensacion: Instancia del modelo Dispensacion
        
    Returns:
        BytesIO: Buffer con el PDF generado
    """
    from core.models import TemaGlobal
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.8*inch,
        bottomMargin=0.5*inch
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Obtener tema activo para colores institucionales
    try:
        tema = TemaGlobal.objects.filter(es_activo=True).first()
        color_primario = tema.color_primario if tema else '#9F2241'
        institucion = tema.titulo_sistema if tema else 'Sistema de Farmacia Penitenciaria'
        subtitulo = tema.subtitulo_sistema if tema else 'Gobierno del Estado'
    except:
        color_primario = '#9F2241'
        institucion = 'Sistema de Farmacia Penitenciaria'
        subtitulo = 'Gobierno del Estado'
    
    COLOR_GUINDA = colors.HexColor(color_primario)
    COLOR_TEXTO = colors.HexColor('#1f2937')
    COLOR_GRIS = colors.HexColor('#6b7280')
    
    # Fondo institucional
    fondo_path = obtener_fondo_institucional()
    
    # ========== ENCABEZADO ==========
    header_style = ParagraphStyle('HeaderFC', parent=styles['Heading1'], fontSize=14, 
                                   textColor=COLOR_GUINDA, alignment=TA_CENTER, spaceAfter=6)
    subheader_style = ParagraphStyle('SubHeaderFC', parent=styles['Normal'], fontSize=10, 
                                      textColor=COLOR_TEXTO, alignment=TA_CENTER, spaceAfter=3)
    
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph(institucion, header_style))
    elements.append(Paragraph(subtitulo, subheader_style))
    elements.append(Paragraph("<b>FORMATO C - DISPENSACIÓN A PACIENTES</b>", 
                              ParagraphStyle('TituloFC', parent=header_style, fontSize=12, spaceBefore=8)))
    elements.append(Spacer(1, 0.2*inch))
    
    # ========== DATOS DE LA DISPENSACIÓN ==========
    fecha_disp = dispensacion.fecha_dispensacion.strftime('%d/%m/%Y %H:%M') if dispensacion.fecha_dispensacion else 'N/A'
    
    info_data = [
        ['Folio:', dispensacion.folio or 'N/A', 'Fecha:', fecha_disp],
        ['Centro:', dispensacion.centro.nombre if dispensacion.centro else 'N/A', 
         'Tipo:', dispensacion.get_tipo_dispensacion_display()],
        ['Estado:', dispensacion.get_estado_display(), '', ''],
    ]
    
    info_table = Table(info_data, colWidths=[1.2*inch, 2.5*inch, 0.8*inch, 2.5*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_TEXTO),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.15*inch))
    
    # ========== DATOS DEL PACIENTE ==========
    seccion_style = ParagraphStyle('SeccionFC', parent=styles['Heading2'], fontSize=10, 
                                    textColor=colors.white, backColor=COLOR_GUINDA,
                                    leftIndent=6, spaceBefore=8, spaceAfter=6)
    
    elements.append(Paragraph("DATOS DEL PACIENTE", seccion_style))
    
    paciente = dispensacion.paciente
    paciente_data = [
        ['No. Expediente:', paciente.numero_expediente if paciente else 'N/A', 
         'Nombre:', paciente.nombre_completo if paciente else 'N/A'],
        ['Dormitorio:', paciente.dormitorio or 'N/A' if paciente else 'N/A', 
         'Celda:', paciente.celda or 'N/A' if paciente else 'N/A'],
        ['Edad:', f"{paciente.edad} años" if paciente and paciente.edad else 'N/A',
         'Sexo:', paciente.get_sexo_display() if paciente and paciente.sexo else 'N/A'],
    ]
    
    paciente_table = Table(paciente_data, colWidths=[1.2*inch, 2.5*inch, 0.8*inch, 2.5*inch])
    paciente_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_TEXTO),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FBF2F5')),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_GUINDA),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#E5E7EB')),
    ]))
    elements.append(paciente_table)
    elements.append(Spacer(1, 0.1*inch))
    
    # ========== PRESCRIPCIÓN MÉDICA ==========
    if dispensacion.diagnostico or dispensacion.medico_prescriptor:
        elements.append(Paragraph("PRESCRIPCIÓN MÉDICA", seccion_style))
        
        prescripcion_data = [
            ['Médico Prescriptor:', dispensacion.medico_prescriptor or 'N/A', 
             'Cédula:', dispensacion.cedula_medico or 'N/A'],
            ['Diagnóstico:', dispensacion.diagnostico or 'N/A', '', ''],
        ]
        
        prescripcion_table = Table(prescripcion_data, colWidths=[1.4*inch, 2.3*inch, 0.8*inch, 2.5*inch])
        prescripcion_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_TEXTO),
            ('SPAN', (1, 1), (3, 1)),  # Diagnóstico ocupa toda la fila
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(prescripcion_table)
        elements.append(Spacer(1, 0.1*inch))
    
    # ========== MEDICAMENTOS DISPENSADOS ==========
    elements.append(Paragraph("MEDICAMENTOS DISPENSADOS", seccion_style))
    
    # Encabezados de la tabla de medicamentos
    med_headers = ['No.', 'Clave', 'Medicamento', 'Lote', 'Prescrito', 'Dispensado', 'Dosis/Frecuencia']
    med_data = [med_headers]
    
    detalles = dispensacion.detalles.all().select_related('producto', 'lote')
    
    for idx, detalle in enumerate(detalles, 1):
        dosis_freq = []
        if detalle.dosis:
            dosis_freq.append(detalle.dosis)
        if detalle.frecuencia:
            dosis_freq.append(detalle.frecuencia)
        
        med_data.append([
            str(idx),
            detalle.producto.clave if detalle.producto else 'N/A',
            Paragraph(detalle.producto.nombre[:40] if detalle.producto else 'N/A', 
                      ParagraphStyle('MedNombre', fontSize=7)),
            detalle.lote.numero_lote[:15] if detalle.lote else 'N/A',
            str(detalle.cantidad_prescrita),
            str(detalle.cantidad_dispensada),
            ' / '.join(dosis_freq) if dosis_freq else '-'
        ])
    
    # Si no hay detalles, agregar fila vacía
    if len(med_data) == 1:
        med_data.append(['-', '-', 'Sin medicamentos registrados', '-', '-', '-', '-'])
    
    med_table = Table(med_data, colWidths=[0.35*inch, 0.7*inch, 2.3*inch, 1*inch, 0.65*inch, 0.75*inch, 1.25*inch])
    med_table.setStyle(TableStyle([
        # Encabezado
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_GUINDA),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        # Datos
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('TEXTCOLOR', (0, 1), (-1, -1), COLOR_TEXTO),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GUINDA),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # No.
        ('ALIGN', (4, 1), (5, -1), 'CENTER'),  # Cantidades
        ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        # Filas alternas
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9F9F9')]),
    ]))
    elements.append(med_table)
    elements.append(Spacer(1, 0.15*inch))
    
    # ========== INDICACIONES ==========
    if dispensacion.indicaciones:
        elements.append(Paragraph("INDICACIONES", seccion_style))
        elements.append(Paragraph(dispensacion.indicaciones, 
                                  ParagraphStyle('IndFC', fontSize=9, textColor=COLOR_TEXTO, spaceBefore=4)))
        elements.append(Spacer(1, 0.1*inch))
    
    # ========== OBSERVACIONES ==========
    if dispensacion.observaciones:
        elements.append(Paragraph("OBSERVACIONES", seccion_style))
        elements.append(Paragraph(dispensacion.observaciones,
                                  ParagraphStyle('ObsFC', fontSize=9, textColor=COLOR_TEXTO, spaceBefore=4)))
        elements.append(Spacer(1, 0.1*inch))
    
    # ========== SECCIÓN DE FIRMAS ==========
    elements.append(Spacer(1, 0.25*inch))
    
    dispensador_nombre = 'N/A'
    if dispensacion.dispensado_por:
        dispensador_nombre = f"{dispensacion.dispensado_por.first_name} {dispensacion.dispensado_por.last_name}".strip()
        if not dispensador_nombre:
            dispensador_nombre = dispensacion.dispensado_por.username
    
    firma_data = [
        ['', '', ''],
        ['_' * 35, '_' * 35, '_' * 35],
        ['PACIENTE / INTERNO', 'DISPENSADOR', 'Vo. Bo. RESPONSABLE'],
        [paciente.nombre_completo if paciente else 'N/A', dispensador_nombre, ''],
        [f'Exp: {paciente.numero_expediente}' if paciente else '', '', ''],
    ]
    
    firma_table = Table(firma_data, colWidths=[2.3*inch, 2.3*inch, 2.3*inch])
    firma_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('FONTSIZE', (0, 3), (-1, 4), 7),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, 0), 20),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TEXTCOLOR', (0, 2), (-1, 2), COLOR_GUINDA),
        ('TEXTCOLOR', (0, 3), (-1, 4), COLOR_GRIS),
    ]))
    elements.append(firma_table)
    
    # ========== PIE DE PÁGINA ==========
    elements.append(Spacer(1, 0.2*inch))
    nota_style = ParagraphStyle('NotaFC', parent=styles['Normal'], fontSize=7, textColor=COLOR_GRIS, alignment=TA_CENTER)
    elements.append(Paragraph(
        f"Formato C - Dispensación a Pacientes | {institucion} | Folio: {dispensacion.folio} | Generado: {timezone.now().strftime('%d/%m/%Y %H:%M')}",
        nota_style
    ))
    
    # Canvas con fondo institucional
    class FondoCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            self.fondo_path = fondo_path
            canvas.Canvas.__init__(self, *args, **kwargs)
            self._dibujar_fondo()
        
        def showPage(self):
            canvas.Canvas.showPage(self)
            self._dibujar_fondo()
        
        def _dibujar_fondo(self):
            if self.fondo_path and os.path.exists(self.fondo_path):
                try:
                    page_width, page_height = letter
                    self.drawImage(
                        str(self.fondo_path),
                        0, 0,
                        width=page_width,
                        height=page_height,
                        preserveAspectRatio=False,
                        mask='auto'
                    )
                except Exception as e:
                    logger.warning(f"No se pudo cargar imagen de fondo: {e}")
    
    doc.build(elements, canvasmaker=FondoCanvas)
    
    buffer.seek(0)
    logger.info(f"Formato C (Dispensación) PDF generado - Folio: {dispensacion.folio}, Items: {dispensacion.detalles.count()}")
    return buffer