"""
Generador de reportes PDF profesionales para el sistema de farmacia penitenciaria
Con imagen de fondo oficial del Gobierno del Estado de México
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
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

# Colores institucionales del Gobierno del Estado de México
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
    """
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


def _obtener_estilos_institucionales():
    """Retorna estilos personalizados con colores institucionales"""
    styles = getSampleStyleSheet()
    
    # Título principal del reporte
    styles.add(ParagraphStyle(
        'TituloReporte',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=COLOR_GUINDA,
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
        textColor=COLOR_TEXTO,
        alignment=TA_CENTER,
        spaceAfter=15,
        fontName='Helvetica'
    ))
    
    # Sección
    styles.add(ParagraphStyle(
        'SeccionTitulo',
        parent=styles['Heading3'],
        fontSize=11,
        textColor=COLOR_GUINDA,
        spaceAfter=8,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    ))
    
    return styles


def _crear_tabla_institucional(data, col_widths=None, header=True):
    """Crea una tabla con estilo institucional - fondo transparente para ver imagen de fondo"""
    table = Table(data, colWidths=col_widths)
    
    estilos = [
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GUINDA),
        ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_TEXTO),
    ]
    
    if header:
        estilos.extend([
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_GUINDA),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            # Sin ROWBACKGROUNDS para mantener transparencia
        ])
    
    table.setStyle(TableStyle(estilos))
    return table


def crear_encabezado(styles):
    """Crea el encabezado estándar para reportes"""
    titulo_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=COLOR_GUINDA,
        alignment=TA_CENTER,
        spaceAfter=30
    )
    
    return titulo_style


def crear_pie_pagina(canvas, doc):
    """Agrega número de página al pie - LEGACY, usar FondoOficialCanvas"""
    canvas.saveState()
    canvas.setFont('Helvetica', 9)
    page_num = canvas.getPageNumber()
    text = f"Página {page_num}"
    canvas.drawRightString(7.5 * inch, 0.5 * inch, text)
    canvas.drawString(inch, 0.5 * inch, f"Generado: {timezone.now().strftime('%d/%m/%Y %H:%M')}")
    canvas.restoreState()


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
    
    # Usar documento con fondo institucional
    fondo_path = str(FONDO_INSTITUCIONAL_PATH) if FONDO_INSTITUCIONAL_PATH.exists() else None
    
    doc = _crear_doc_con_fondo(buffer, fondo_path)
    
    elements = []
    styles = _obtener_estilos_institucionales()
    
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
    
    # Tabla de datos
    data = [['Clave', 'Descripción', 'Stock Actual', 'Stock Mín.', 'Nivel', 'Unidad']]
    
    for producto in productos_data:
        nivel = str(producto.get('nivel', producto.get('nivel_stock', 'N/A'))).upper()
        data.append([
            str(producto.get('clave', '')),
            str(producto.get('descripcion', ''))[:45],
            str(producto.get('stock_actual', 0)),
            str(producto.get('stock_minimo', 0)),
            nivel,
            str(producto.get('unidad', producto.get('unidad_medida', '')))
        ])
    
    col_widths = [0.8*inch, 2.8*inch, 0.8*inch, 0.7*inch, 0.8*inch, 0.6*inch]
    table = _crear_tabla_institucional(data, col_widths)
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
    
    data = [['Producto', 'Lote', 'Caducidad', 'Días', 'Cantidad', 'Estado']]
    
    for lote in lotes_data:
        alerta = str(lote.get('alerta', lote.get('estado_caducidad', 'N/A'))).upper()
        dias_restantes = lote.get('dias_restantes', lote.get('dias_para_caducar', 'N/A'))
        
        data.append([
            str(lote.get('producto_descripcion', lote.get('producto', '')))[:30],
            str(lote.get('numero_lote', '')),
            lote.get('fecha_caducidad', ''),
            str(dias_restantes),
            str(lote.get('cantidad_actual', 0)),
            alerta
        ])
    
    col_widths = [2.2*inch, 1*inch, 0.9*inch, 0.5*inch, 0.7*inch, 0.9*inch]
    table = _crear_tabla_institucional(data, col_widths)
    elements.append(table)
    
    # Usar canvas con fondo institucional
    def make_canvas(*args, **kwargs):
        return FondoOficialCanvas(*args, fondo_path=fondo_path, titulo_reporte='CADUCIDADES', **kwargs)
    
    doc.build(elements, canvasmaker=make_canvas)
    
    buffer.seek(0)
    logger.info(f"Reporte de caducidades PDF generado: {len(lotes_data)} lotes")
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
    
    data = [['Folio', 'Centro', 'Estado', 'Fecha', 'Items', 'Solicitante']]
    
    for req in requisiciones_data:
        data.append([
            str(req.get('folio', '')),
            str(req.get('centro_nombre', req.get('centro', '')))[:25],
            str(req.get('estado', '')).upper(),
            str(req.get('fecha_solicitud', ''))[:10],
            str(req.get('total_items', req.get('total_productos', 0))),
            str(req.get('usuario_solicita', req.get('solicitante', '')))[:15]
        ])
    
    col_widths = [1*inch, 2*inch, 0.9*inch, 0.9*inch, 0.5*inch, 1.2*inch]
    table = _crear_tabla_institucional(data, col_widths)
    elements.append(table)
    
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
    
    # Tabla de movimientos
    mov_titulo = Paragraph("DETALLE DE MOVIMIENTOS", styles['SeccionTitulo'])
    elements.append(mov_titulo)
    
    data = [['Fecha', 'Tipo', 'Producto', 'Lote', 'Cantidad', 'Usuario']]
    
    for mov in movimientos_data:
        tipo = str(mov.get('tipo', '')).upper()
        cantidad = mov.get('cantidad', 0)
        signo = '+' if cantidad >= 0 else ''
        
        data.append([
            str(mov.get('fecha_movimiento', mov.get('fecha', '')))[:16],
            tipo,
            str(mov.get('producto_clave', mov.get('producto', '')))[:20],
            str(mov.get('numero_lote', mov.get('lote', '')))[:12],
            f"{signo}{cantidad}",
            str(mov.get('usuario', ''))[:15]
        ])
    
    col_widths = [1.1*inch, 0.7*inch, 1.8*inch, 1*inch, 0.7*inch, 1.2*inch]
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
    
    data = [['Fecha', 'Usuario', 'Acción', 'Módulo', 'Descripción', 'IP']]
    
    for log in auditoria_data:
        fecha = log.get('fecha', '')
        if hasattr(fecha, 'strftime'):
            fecha = fecha.strftime('%d/%m/%Y %H:%M')
        else:
            fecha = str(fecha)[:16]
        
        data.append([
            fecha,
            str(log.get('usuario', log.get('usuario_username', 'Sistema')))[:12],
            str(log.get('accion', ''))[:10],
            str(log.get('modelo', ''))[:15],
            str(log.get('objeto_repr', log.get('descripcion', '')))[:30],
            str(log.get('ip_address', log.get('ip', '')))[:15]
        ])
    
    col_widths = [1.1*inch, 0.9*inch, 0.7*inch, 1*inch, 2*inch, 0.8*inch]
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
        
        prod_data = [
            ['Clave:', str(producto_info.get('clave', 'N/A')), 'Descripción:', str(producto_info.get('descripcion', 'N/A'))[:40]],
            ['Unidad:', str(producto_info.get('unidad_medida', 'N/A')), 'Precio:', f"${producto_info.get('precio_unitario', 0):.2f}" if producto_info.get('precio_unitario') else 'N/A'],
            ['Stock Actual:', str(producto_info.get('stock_actual', 0)), 'Stock Mínimo:', str(producto_info.get('stock_minimo', 0))],
        ]
        
        prod_table = Table(prod_data, colWidths=[1.2*inch, 2.3*inch, 1.2*inch, 2.3*inch])
        prod_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_TEXTO),
            ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GUINDA),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
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
    
    data = [['Fecha', 'Tipo', 'Lote', 'Cantidad', 'Centro/Destino', 'Usuario', 'Referencia']]
    
    for mov in trazabilidad_data:
        fecha = mov.get('fecha', mov.get('fecha_movimiento', ''))
        if hasattr(fecha, 'strftime'):
            fecha = fecha.strftime('%d/%m/%Y %H:%M')
        else:
            fecha = str(fecha)[:16]
        
        cantidad = mov.get('cantidad', 0)
        tipo = str(mov.get('tipo', '')).upper()
        signo = '+' if tipo == 'ENTRADA' else ('-' if tipo == 'SALIDA' else '')
        
        data.append([
            fecha,
            tipo[:8],
            str(mov.get('numero_lote', mov.get('lote', '')))[:12],
            f"{signo}{cantidad}",
            str(mov.get('centro_nombre', mov.get('centro', mov.get('destino', ''))))[:15],
            str(mov.get('usuario', mov.get('usuario_username', '')))[:12],
            str(mov.get('documento_referencia', mov.get('referencia', '')))[:15]
        ])
    
    col_widths = [1*inch, 0.6*inch, 0.9*inch, 0.6*inch, 1.2*inch, 0.9*inch, 1.1*inch]
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
