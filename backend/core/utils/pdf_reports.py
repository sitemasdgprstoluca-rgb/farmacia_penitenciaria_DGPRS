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
from datetime import date, timedelta
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
    
    # Tabla de datos con Paragraph para texto largo
    data = [['Clave', 'Descripción', 'Stock', 'Mín.', 'Nivel', 'Unidad']]
    
    for producto in productos_data:
        nivel = str(producto.get('nivel', producto.get('nivel_stock', 'N/A'))).upper()
        descripcion = str(producto.get('descripcion', ''))
        # Usar Paragraph para la descripción para que se ajuste automáticamente
        desc_paragraph = Paragraph(descripcion, estilo_celda)
        data.append([
            str(producto.get('clave', '')),
            desc_paragraph,
            str(producto.get('stock_actual', 0)),
            str(producto.get('stock_minimo', 0)),
            nivel,
            str(producto.get('unidad', producto.get('unidad_medida', '')))
        ])
    
    # Ajustar anchos para que sumen exactamente el ancho disponible (7 pulgadas)
    # Descripción más ancha, columnas numéricas más estrechas y compactas
    col_widths = [0.9*inch, 3.6*inch, 0.7*inch, 0.5*inch, 0.6*inch, 0.7*inch]
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
        producto_desc = str(lote.get('producto_nombre', lote.get('producto', '')))[:30]
        producto_paragraph = Paragraph(producto_desc, estilo_celda)
        
        centro = str(lote.get('centro_nombre', lote.get('centro', 'Farmacia Central')))[:15]
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
        
        data.append([
            str(idx),
            str(lote.get('producto_clave', lote.get('clave', '')))[:12],
            producto_paragraph,
            str(lote.get('numero_lote', ''))[:12],
            str(lote.get('fecha_fabricacion', ''))[:10],
            str(lote.get('fecha_caducidad', ''))[:10],
            str(lote.get('cantidad_inicial', 0)),
            str(lote.get('cantidad_actual', 0)),
            centro_paragraph,
            f"{activo}\n{estado_cad}"
        ])
    
    # Anchos ajustados para orientación horizontal
    col_widths = [0.35*inch, 0.7*inch, 1.8*inch, 0.8*inch, 0.75*inch, 0.75*inch, 0.6*inch, 0.6*inch, 1.1*inch, 0.85*inch]
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
            str(req.get('fecha_solicitud', ''))[:10],
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
        productos_data = [['Clave', 'Producto', 'Solicitado', 'Autorizado', 'Entregado']]
        
        for prod in productos:
            nombre = str(prod.get('nombre', 'N/A'))
            if len(nombre) > 40:
                nombre = nombre[:37] + '...'
            productos_data.append([
                str(prod.get('clave', 'N/A')),
                Paragraph(nombre, estilo_celda),
                str(prod.get('cantidad_solicitada', 0)),
                str(prod.get('cantidad_autorizada', 0)),
                str(prod.get('cantidad_entregada', 0)),
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


def generar_reporte_movimientos(movimientos_data, filtros=None):
    """
    Genera reporte PDF de movimientos de inventario con fondo oficial
    
    Args:
        movimientos_data: Lista de diccionarios con datos de movimientos
        filtros: Diccionario con filtros aplicados
    
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
    
    titulo = Paragraph("REPORTE DE MOVIMIENTOS DE INVENTARIO", styles['TituloReporte'])
    elements.append(titulo)
    elements.append(Spacer(1, 0.2*inch))
    
    # Información
    info_text = f"<b>Fecha de generación:</b> {timezone.now().strftime('%d/%m/%Y %H:%M')}<br/>"
    info_text += f"<b>Total de movimientos:</b> {len(movimientos_data)}"
    
    if filtros:
        if filtros.get('fecha_inicio'):
            info_text += f"<br/><b>Desde:</b> {filtros['fecha_inicio']}"
        if filtros.get('fecha_fin'):
            info_text += f"<br/><b>Hasta:</b> {filtros['fecha_fin']}"
        if filtros.get('tipo'):
            info_text += f"<br/><b>Tipo:</b> {filtros['tipo'].upper()}"
    
    info = Paragraph(info_text, styles['Normal'])
    elements.append(info)
    elements.append(Spacer(1, 0.2*inch))
    
    # Resumen de movimientos
    total_entradas = sum(1 for m in movimientos_data if str(m.get('tipo', '')).lower() == 'entrada')
    total_salidas = sum(1 for m in movimientos_data if str(m.get('tipo', '')).lower() == 'salida')
    total_ajustes = sum(1 for m in movimientos_data if str(m.get('tipo', '')).lower() == 'ajuste')
    
    resumen_titulo = Paragraph("RESUMEN", styles['SeccionTitulo'])
    elements.append(resumen_titulo)
    
    resumen_data = [
        ['Tipo', 'Cantidad'],
        ['Entradas', str(total_entradas)],
        ['Salidas', str(total_salidas)],
        ['Ajustes', str(total_ajustes)],
        ['TOTAL', str(len(movimientos_data))],
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
    
    # Tabla de movimientos - MEJORA: Extendida con subtipo, expediente y observaciones
    mov_titulo = Paragraph("DETALLE DE MOVIMIENTOS", styles['SeccionTitulo'])
    elements.append(mov_titulo)
    
    # Estilo para celdas de texto largo
    estilo_celda = ParagraphStyle(
        'CeldaTextoMov',
        parent=styles['Normal'],
        fontSize=6,
        leading=8,
        wordWrap='CJK',
    )
    
    data = [['Fecha', 'Tipo', 'Subtipo', 'Producto', 'Lote', 'Cant.', 'Centro', 'Expediente', 'Obs.']]
    
    for mov in movimientos_data:
        tipo = str(mov.get('tipo', '')).upper()
        subtipo = str(mov.get('subtipo', ''))
        cantidad = mov.get('cantidad', 0)
        signo = '+' if cantidad >= 0 else ''
        producto = str(mov.get('producto_clave', mov.get('producto', '')))
        producto_paragraph = Paragraph(producto, estilo_celda)
        centro = str(mov.get('centro', ''))[:15]
        centro_paragraph = Paragraph(centro, estilo_celda)
        expediente = str(mov.get('expediente', ''))[:12]
        observaciones = str(mov.get('observaciones', ''))[:30]
        obs_paragraph = Paragraph(observaciones, estilo_celda)
        
        data.append([
            str(mov.get('fecha_movimiento', mov.get('fecha', '')))[:16],
            tipo,
            subtipo[:10],
            producto_paragraph,
            str(mov.get('numero_lote', mov.get('lote', '')))[:10],
            f"{signo}{cantidad}",
            centro_paragraph,
            expediente,
            obs_paragraph
        ])
    
    # Anchos ajustados para 9 columnas en orientación portrait
    col_widths = [0.85*inch, 0.5*inch, 0.55*inch, 1.1*inch, 0.7*inch, 0.4*inch, 0.9*inch, 0.7*inch, 0.9*inch]
    table = _crear_tabla_institucional(data, col_widths)
    elements.append(table)
    
    # Usar canvas con fondo institucional
    def make_canvas(*args, **kwargs):
        return FondoOficialCanvas(*args, fondo_path=fondo_path, titulo_reporte='MOVIMIENTOS', **kwargs)
    
    doc.build(elements, canvasmaker=make_canvas)
    
    buffer.seek(0)
    logger.info(f"Reporte de movimientos PDF generado: {len(movimientos_data)} registros")
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
            fecha = str(fecha)[:16]
        
        descripcion = str(log.get('objeto_repr', log.get('descripcion', '')))
        descripcion_paragraph = Paragraph(descripcion, estilo_celda)
        
        data.append([
            fecha,
            str(log.get('usuario', log.get('usuario_username', 'Sistema')))[:12],
            str(log.get('accion', ''))[:12],
            str(log.get('modelo', ''))[:15],
            descripcion_paragraph,
            str(log.get('ip_address', log.get('ip', '')))[:15]
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
        
        prod_data = [
            ['Clave:', str(producto_info.get('clave', 'N/A')), 'Descripción:', desc_paragraph],
            ['Unidad:', str(producto_info.get('unidad_medida', 'N/A')), 'Precio:', f"${producto_info.get('precio_unitario', 0):.2f}" if producto_info.get('precio_unitario') else 'N/A'],
            ['Stock Actual:', str(producto_info.get('stock_actual', 0)), 'Stock Mínimo:', str(producto_info.get('stock_minimo', 0))],
        ]
        
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
    
    # Información del reporte
    info_text = f"<b>Fecha de generación:</b> {timezone.now().strftime('%d/%m/%Y %H:%M')}<br/>"
    info_text += f"<b>Total de movimientos:</b> {len(trazabilidad_data)}"
    
    if filtros:
        if filtros.get('fecha_inicio'):
            info_text += f"<br/><b>Desde:</b> {filtros['fecha_inicio']}"
        if filtros.get('fecha_fin'):
            info_text += f"<br/><b>Hasta:</b> {filtros['fecha_fin']}"
        if filtros.get('lote'):
            info_text += f"<br/><b>Lote:</b> {filtros['lote']}"
    
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
    
    # Estilo para celdas de texto largo
    estilo_celda = ParagraphStyle(
        'CeldaTextoTraz',
        parent=styles['Normal'],
        fontSize=7,
        leading=9,
        wordWrap='CJK',
    )
    
    data = [['Fecha', 'Tipo', 'Lote', 'Cant.', 'Centro/Destino', 'Usuario', 'Referencia']]
    
    for mov in trazabilidad_data:
        fecha = mov.get('fecha', mov.get('fecha_movimiento', ''))
        if hasattr(fecha, 'strftime'):
            fecha = fecha.strftime('%d/%m/%Y %H:%M')
        else:
            fecha = str(fecha)[:16]
        
        cantidad = mov.get('cantidad', 0)
        tipo = str(mov.get('tipo', '')).upper()
        signo = '+' if tipo == 'ENTRADA' else ('-' if tipo == 'SALIDA' else '')
        
        centro = str(mov.get('centro_nombre', mov.get('centro', mov.get('destino', ''))))
        centro_paragraph = Paragraph(centro, estilo_celda)
        referencia = str(mov.get('documento_referencia', mov.get('referencia', '')))
        ref_paragraph = Paragraph(referencia, estilo_celda)
        
        data.append([
            fecha,
            tipo[:8],
            str(mov.get('numero_lote', mov.get('lote', '')))[:12],
            f"{signo}{cantidad}",
            centro_paragraph,
            str(mov.get('usuario', mov.get('usuario_username', '')))[:12],
            ref_paragraph
        ])
    
    col_widths = [0.95*inch, 0.55*inch, 0.85*inch, 0.5*inch, 1.3*inch, 0.85*inch, 1.15*inch]
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
