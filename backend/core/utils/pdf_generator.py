"""
Generador de PDFs para hojas de recolección de requisiciones
Con imagen de fondo oficial del Gobierno del Estado de México
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, KeepTogether
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from django.conf import settings
from pathlib import Path
from io import BytesIO
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

# Colores institucionales
COLOR_GUINDA = colors.HexColor('#632842')
COLOR_GUINDA_CLARO = colors.HexColor('#8a3b5c')
COLOR_DORADO = colors.HexColor('#B8860B')
COLOR_TEXTO = colors.HexColor('#1f2937')
COLOR_GRIS = colors.HexColor('#6b7280')

# Ruta a la imagen de fondo institucional (usando settings.BASE_DIR)
# Funciona tanto en desarrollo como en producción después de collectstatic
# Usar la imagen original sin degradar para que se vea el colibrí y colores
def get_fondo_institucional_path():
    """Busca el fondo institucional en múltiples ubicaciones."""
    posibles_rutas = [
        Path(settings.BASE_DIR) / 'static' / 'img' / 'pdf' / 'fondoOficial.png',
        Path(settings.BASE_DIR) / 'staticfiles' / 'img' / 'pdf' / 'fondoOficial.png',
        Path(settings.STATIC_ROOT or '') / 'img' / 'pdf' / 'fondoOficial.png' if hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT else None,
    ]
    for ruta in posibles_rutas:
        if ruta and ruta.exists():
            logger.info(f"Usando fondo institucional: {ruta}")
            return ruta
    logger.warning("No se encontró imagen de fondo institucional")
    return None

FONDO_INSTITUCIONAL_PATH = get_fondo_institucional_path()


class RequisicionCanvas(canvas.Canvas):
    """
    Canvas personalizado que agrega el fondo oficial del gobierno
    a todas las páginas de las hojas de recolección.
    El fondo se dibuja PRIMERO (debajo) y luego el contenido encima.
    """
    
    def __init__(self, *args, **kwargs):
        self.fondo_path = kwargs.pop('fondo_path', None)
        canvas.Canvas.__init__(self, *args, **kwargs)
        self.pages = []
        # Dibujar fondo en la primera página inmediatamente
        self._dibujar_fondo_oficial()
    
    def showPage(self):
        # Guardar contenido de la página actual
        self.pages.append(dict(self.__dict__))
        self._startPage()
        # Dibujar fondo para la nueva página
        self._dibujar_fondo_oficial()
    
    def save(self):
        # Agregar pie de página a cada página guardada
        num_pages = len(self.pages)
        for page_num, page_state in enumerate(self.pages, 1):
            self.__dict__.update(page_state)
            self._dibujar_pie_pagina(page_num, num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)
    
    def _dibujar_fondo_oficial(self):
        """
        Dibuja la imagen de fondo institucional ajustada a toda la página.
        Se llama AL INICIO de cada página para que quede DEBAJO del contenido.
        """
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
                logger.warning(f"No se pudo cargar imagen de fondo institucional: {e}")
    
    def _dibujar_pie_pagina(self, num_pagina, total_paginas):
        """Dibuja el pie de página"""
        self.saveState()
        page_width = letter[0]
        
        self.setStrokeColor(COLOR_GUINDA)
        self.setLineWidth(1)
        self.line(0.5*inch, 0.6*inch, page_width - 0.5*inch, 0.6*inch)
        
        self.setFillColor(COLOR_GRIS)
        self.setFont('Helvetica', 7)
        self.drawString(0.5*inch, 0.4*inch, 
                        f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        self.drawRightString(page_width - 0.5*inch, 0.4*inch, 
                             f"Página {num_pagina} de {total_paginas}")
        
        self.setFont('Helvetica-Oblique', 6)
        self.drawCentredString(page_width/2, 0.25*inch, 
                               "Documento oficial - Sistema de Control de Abasto")
        
        self.restoreState()


def generar_hoja_recoleccion(requisicion):
    """
    Genera PDF con hoja de recolección para una requisición autorizada
    Con fondo oficial del Gobierno del Estado de México
    
    Args:
        requisicion: Objeto Requisicion
    
    Returns:
        BytesIO: Buffer con PDF generado
    """
    buffer = BytesIO()
    
    # Obtener ruta del fondo institucional (compatible con desarrollo y producción)
    fondo_institucional = get_fondo_institucional_path()
    fondo_path = str(fondo_institucional) if fondo_institucional else None
    
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        topMargin=1*inch,
        bottomMargin=0.8*inch,
        leftMargin=0.5*inch,
        rightMargin=0.5*inch
    )
    story = []
    styles = getSampleStyleSheet()
    
    # Estilo personalizado para título con color guinda institucional
    titulo_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=COLOR_GUINDA,
        spaceAfter=20,
        spaceBefore=10,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Estilo para subtítulos
    subtitulo_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=11,
        textColor=COLOR_GUINDA,
        spaceAfter=10,
        fontName='Helvetica-Bold'
    )
    
    # Estilo para celdas con texto largo (descripción)
    celda_texto_style = ParagraphStyle(
        'CeldaTexto',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        wordWrap='CJK',
        alignment=TA_LEFT,
    )
    
    # Estilo para celdas de unidad (texto que puede ser largo como "CAJA CON 20 TABLETAS")
    celda_unidad_style = ParagraphStyle(
        'CeldaUnidadRecoleccion',
        parent=styles['Normal'],
        fontSize=7,
        leading=9,
        wordWrap='CJK',
        alignment=TA_CENTER,
    )
    
    # Título principal
    titulo = Paragraph("HOJA DE RECOLECCIÓN DE MEDICAMENTOS", titulo_style)
    story.append(titulo)
    story.append(Spacer(1, 0.15*inch))
    
    # Información de la requisición con colores institucionales
    # ISS-FIX-CENTRO: Usar centro_origen (el centro que SOLICITA)
    # FALLBACK: si centro_origen es NULL (datos viejos), usar centro_destino
    centro_obj = requisicion.centro_origen or requisicion.centro_destino
    centro_nombre = centro_obj.nombre if centro_obj else 'N/A'
    solicitante_nombre = requisicion.solicitante.get_full_name() if requisicion.solicitante else 'N/A'
    autorizador_nombre = requisicion.autorizador.get_full_name() if requisicion.autorizador else ''
    
    # ISS-FIX: Obtener fecha límite de recolección
    fecha_limite_texto = 'N/A'
    if hasattr(requisicion, 'fecha_recoleccion_limite') and requisicion.fecha_recoleccion_limite:
        fecha_limite_texto = requisicion.fecha_recoleccion_limite.strftime('%d/%m/%Y %H:%M')
    
    info_data = [
        ['Folio:', requisicion.folio or f'REQ-{requisicion.id}', 'Fecha de Solicitud:', requisicion.fecha_solicitud.strftime('%d/%m/%Y') if requisicion.fecha_solicitud else 'N/A'],
        ['Centro Solicitante:', centro_nombre, 'Estado:', (requisicion.estado or '').upper()],
        ['Solicitante:', solicitante_nombre, 'Fecha de Autorización:', 
         requisicion.fecha_autorizacion.strftime('%d/%m/%Y %H:%M') if requisicion.fecha_autorizacion else 'N/A'],
        ['Fecha Límite de Recolección:', fecha_limite_texto, '', ''],
    ]
    
    if requisicion.autorizador:
        info_data.append(['Autorizado por:', autorizador_nombre, '', ''])
    
    info_table = Table(info_data, colWidths=[1.5*inch, 2.5*inch, 1.5*inch, 2*inch])
    info_table.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_TEXTO),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GUINDA),
    ]))
    
    story.append(info_table)
    story.append(Spacer(1, 0.25*inch))
    
    # Subtítulo de productos
    productos_titulo = Paragraph("PRODUCTOS AUTORIZADOS", subtitulo_style)
    story.append(productos_titulo)
    story.append(Spacer(1, 0.1*inch))
    
    # Tabla de productos con Paragraph para descripción
    productos_data = [
        ['#', 'Clave', 'Descripción', 'Lote', 'Caducidad', 'Cant.', 'Unidad']
    ]
    
    for idx, detalle in enumerate(requisicion.detalles.all(), start=1):
        # Buscar lote con stock disponible para este producto
        lote_asignado = None
        try:
            lote_asignado = detalle.producto.lotes.filter(
                activo=True,
                cantidad_actual__gt=0
            ).order_by('fecha_caducidad').first()
        except Exception:
            pass
        
        # ISS-PDF FIX: Manejar descripcion None
        descripcion_texto = detalle.producto.descripcion or detalle.producto.nombre or 'N/A'
        descripcion_paragraph = Paragraph(descripcion_texto, celda_texto_style)
        
        # ISS-PDF FIX: Manejar cantidad_autorizada None
        cantidad = detalle.cantidad_solicitada or 0
        if detalle.cantidad_autorizada is not None and detalle.cantidad_autorizada > 0:
            cantidad = detalle.cantidad_autorizada
        
        # ISS-PDF FIX: unidad_medida es CharField simple, no tiene choices
        unidad = getattr(detalle.producto, 'unidad_medida', None) or 'UND'
        # Usar Paragraph para unidad - permite texto largo como "CAJA CON 20 TABLETAS"
        unidad_paragraph = Paragraph(unidad, celda_unidad_style)
        
        productos_data.append([
            str(idx),
            detalle.producto.clave or 'N/A',
            descripcion_paragraph,
            lote_asignado.numero_lote if lote_asignado else 'SIN LOTE',
            lote_asignado.fecha_caducidad.strftime('%d/%m/%Y') if lote_asignado and lote_asignado.fecha_caducidad else 'N/A',
            str(cantidad),
            unidad_paragraph
        ])
    
    # Ajustar anchos para mejor distribución (total ~7.5 pulgadas disponibles)
    # Unidad ampliada de 0.6" a 1.4" para textos largos
    productos_table = Table(
        productos_data, 
        colWidths=[0.3*inch, 0.65*inch, 2.3*inch, 0.85*inch, 0.8*inch, 0.45*inch, 1.4*inch]
    )
    productos_table.setStyle(TableStyle([
        # Header con color guinda institucional
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_GUINDA),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        
        # Data rows - transparente
        ('TEXTCOLOR', (0, 1), (-1, -1), COLOR_TEXTO),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Número
        ('ALIGN', (5, 1), (6, -1), 'CENTER'),  # Cantidad y Unidad
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GUINDA),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
    ]))
    
    story.append(productos_table)
    story.append(Spacer(1, 0.3*inch))
    
    # ==========================================================================
    # SECCIÓN DE FIRMAS - FLUJO COMPLETO V2
    # Médico (Solicitante) → Admin Centro → Director Centro → Farmacia
    # ==========================================================================
    
    # Obtener nombres de los participantes del flujo
    solicitante_nombre = ''
    if requisicion.solicitante:
        try:
            solicitante_nombre = requisicion.solicitante.get_full_name() or requisicion.solicitante.username
        except Exception:
            solicitante_nombre = ''
    
    # Admin Centro (campo: administrador_centro)
    admin_centro_nombre = ''
    if hasattr(requisicion, 'administrador_centro') and requisicion.administrador_centro:
        try:
            admin_centro_nombre = requisicion.administrador_centro.get_full_name() or requisicion.administrador_centro.username
        except Exception:
            admin_centro_nombre = ''
    
    # Director Centro (campo: director_centro)
    director_nombre = ''
    if hasattr(requisicion, 'director_centro') and requisicion.director_centro:
        try:
            director_nombre = requisicion.director_centro.get_full_name() or requisicion.director_centro.username
        except Exception:
            director_nombre = ''
    elif requisicion.autorizador:
        # Fallback: usar autorizador general si no hay director específico
        try:
            director_nombre = requisicion.autorizador.get_full_name() or requisicion.autorizador.username
        except Exception:
            director_nombre = ''
    
    # Farmacia (campo: surtidor o autorizador_farmacia)
    farmacia_nombre = ''
    if hasattr(requisicion, 'surtidor') and requisicion.surtidor:
        try:
            farmacia_nombre = requisicion.surtidor.get_full_name() or requisicion.surtidor.username
        except Exception:
            farmacia_nombre = ''
    elif hasattr(requisicion, 'autorizador_farmacia') and requisicion.autorizador_farmacia:
        try:
            farmacia_nombre = requisicion.autorizador_farmacia.get_full_name() or requisicion.autorizador_farmacia.username
        except Exception:
            farmacia_nombre = ''
    
    # Primera fila de firmas: Solicitante (Médico) y Admin Centro
    firmas_parte1 = [
        ['SOLICITANTE (MÉDICO):', 'ADMINISTRADOR CENTRO:'],
        ['', ''],
        ['_' * 35, '_' * 35],
        [solicitante_nombre, admin_centro_nombre],
        ['Nombre y Firma', 'Nombre y Firma'],
    ]
    
    # Segunda fila de firmas: Director y Farmacia
    firmas_parte2 = [
        ['', ''],
        ['DIRECTOR CENTRO:', 'FARMACIA CENTRAL:'],
        ['', ''],
        ['_' * 35, '_' * 35],
        [director_nombre, farmacia_nombre],
        ['Nombre y Firma', 'Nombre y Firma'],
    ]
    
    # Tercera fila: Recepción
    firmas_parte3 = [
        ['', ''],
        ['RECIBIDO POR:', 'FECHA Y HORA DE ENTREGA:'],
        ['', ''],
        ['_' * 35, '_' * 35],
        ['', ''],
        ['Nombre y Firma', ''],
    ]
    
    # Estilo común para tablas de firmas
    firma_style = TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('FONTSIZE', (0, 3), (-1, 3), 9),
        ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_TEXTO),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ])
    
    firmas_table1 = Table(firmas_parte1, colWidths=[3.5*inch, 3.5*inch])
    firmas_table1.setStyle(firma_style)
    
    firmas_table2 = Table(firmas_parte2, colWidths=[3.5*inch, 3.5*inch])
    firmas_table2.setStyle(firma_style)
    
    firmas_table3 = Table(firmas_parte3, colWidths=[3.5*inch, 3.5*inch])
    firmas_table3.setStyle(firma_style)
    
    # ISS-PDF-FIX: Usar KeepTogether para que TODA la sección de firmas
    # quede en la misma página y no se corte entre páginas
    seccion_firmas = KeepTogether([
        Paragraph("<b>FIRMAS DE AUTORIZACIÓN Y RECEPCIÓN</b>", ParagraphStyle(
            'FirmasTitle', fontSize=10, textColor=COLOR_GUINDA, 
            alignment=TA_CENTER, spaceAfter=10
        )),
        firmas_table1,
        firmas_table2,
        firmas_table3,
        Spacer(1, 0.2*inch)
    ])
    story.append(seccion_firmas)
    
    # Construir PDF con canvas de fondo oficial
    def make_canvas(*args, **kwargs):
        return RequisicionCanvas(*args, fondo_path=fondo_path, **kwargs)
    
    doc.build(story, canvasmaker=make_canvas)
    
    buffer.seek(0)
    logger.info(f"Hoja de recolección generada para requisición {requisicion.folio}")
    return buffer


def generar_pdf_rechazo(requisicion):
    """
    Genera PDF para una requisicion en estado rechazado.
    Con fondo oficial del Gobierno del Estado de México.
    """
    buffer = BytesIO()
    
    # Obtener ruta del fondo institucional (compatible con desarrollo y producción)
    fondo_institucional = get_fondo_institucional_path()
    fondo_path = str(fondo_institucional) if fondo_institucional else None
    
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        topMargin=1*inch,
        bottomMargin=0.8*inch,
        leftMargin=0.5*inch,
        rightMargin=0.5*inch
    )
    story = []
    styles = getSampleStyleSheet()

    titulo_style = ParagraphStyle(
        'RejectTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#dc2626'),
        spaceAfter=20,
        spaceBefore=10,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    motivo_style = ParagraphStyle(
        'RejectReason',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#7f1d1d'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        borderColor=colors.HexColor('#dc2626'),
        borderWidth=2,
        borderPadding=10,
        backColor=colors.HexColor('#fee2e2')
    )

    titulo = Paragraph('REQUISICION RECHAZADA', titulo_style)
    story.append(titulo)
    story.append(Spacer(1, 0.2 * inch))

    # ISS-FIX-CENTRO: Usar centro_origen (el centro que SOLICITA)
    # FALLBACK: si centro_origen es NULL (datos viejos), usar centro_destino
    centro_obj = requisicion.centro_origen or requisicion.centro_destino
    centro_nombre = centro_obj.nombre if centro_obj else 'N/A'
    solicitante_nombre = requisicion.solicitante.get_full_name() if requisicion.solicitante else 'N/A'
    
    info_data = [
        ['Folio:', requisicion.folio or f'REQ-{requisicion.id}', 'Fecha de Solicitud:', requisicion.fecha_solicitud.strftime('%d/%m/%Y') if requisicion.fecha_solicitud else 'N/A'],
        ['Centro Solicitante:', centro_nombre, 'Estado:', 'RECHAZADA'],
        ['Solicitante:', solicitante_nombre, 'Fecha de Rechazo:',
         requisicion.fecha_autorizacion.strftime('%d/%m/%Y %H:%M') if requisicion.fecha_autorizacion else 'N/A'],
        ['Rechazado por:', requisicion.autorizador.get_full_name() if requisicion.autorizador else 'N/A', '', ''],
    ]

    info_table = Table(info_data, colWidths=[1.5 * inch, 2.5 * inch, 1.5 * inch, 2 * inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e5e7eb')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#e5e7eb')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1f2937')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
    ]))

    story.append(info_table)
    story.append(Spacer(1, 0.3 * inch))

    motivo_titulo = Paragraph('MOTIVO DEL RECHAZO', motivo_style)
    story.append(motivo_titulo)
    story.append(Spacer(1, 0.1 * inch))

    motivo_contenido_style = ParagraphStyle(
        'MotivContent',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=15,
        alignment=TA_LEFT,
        fontName='Helvetica'
    )

    motivo_texto = Paragraph(
        requisicion.motivo_rechazo if requisicion.motivo_rechazo else 'No se especifico motivo',
        motivo_contenido_style
    )
    story.append(motivo_texto)
    story.append(Spacer(1, 0.3 * inch))

    productos_titulo_style = ParagraphStyle(
        'ProductsTitle',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#374151'),
        spaceAfter=12,
        fontName='Helvetica-Bold'
    )

    productos_titulo = Paragraph('PRODUCTOS SOLICITADOS (NO PROCESADOS)', productos_titulo_style)
    story.append(productos_titulo)
    story.append(Spacer(1, 0.1 * inch))

    # Estilo para celdas con texto largo
    celda_rechazo_style = ParagraphStyle(
        'CeldaRechazo',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        wordWrap='CJK',
        alignment=TA_LEFT,
    )
    
    # Estilo para celdas de unidad (texto largo)
    celda_unidad_rechazo_style = ParagraphStyle(
        'CeldaUnidadRechazo',
        parent=styles['Normal'],
        fontSize=7,
        leading=9,
        wordWrap='CJK',
        alignment=TA_CENTER,
    )

    productos_data = [
        ['#', 'Clave', 'Descripción', 'Cant. Solicitada', 'Unidad']
    ]

    for idx, detalle in enumerate(requisicion.detalles.all(), start=1):
        # ISS-PDF FIX: Manejar descripcion None
        descripcion_texto = detalle.producto.descripcion or detalle.producto.nombre or 'N/A'
        descripcion_paragraph = Paragraph(descripcion_texto, celda_rechazo_style)
        # ISS-PDF FIX: unidad_medida es CharField simple
        unidad = getattr(detalle.producto, 'unidad_medida', None) or 'UND'
        # Usar Paragraph para unidad - permite texto largo
        unidad_paragraph = Paragraph(unidad, celda_unidad_rechazo_style)
        productos_data.append([
            str(idx),
            detalle.producto.clave or 'N/A',
            descripcion_paragraph,
            str(detalle.cantidad_solicitada or 0),
            unidad_paragraph
        ])

    # Unidad ampliada de 0.6" a 1.4" para textos largos
    productos_table = Table(
        productos_data,
        colWidths=[0.3 * inch, 0.65 * inch, 2.5 * inch, 0.85 * inch, 1.4 * inch]
    )
    productos_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc2626')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#374151')),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('ALIGN', (3, 1), (3, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GUINDA),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ]))

    story.append(productos_table)
    story.append(Spacer(1, 0.3 * inch))

    proximos_titulo = Paragraph('PROXIMOS PASOS', productos_titulo_style)
    story.append(proximos_titulo)

    proximos_texto = Paragraph(
        '1. Revise el motivo del rechazo especificado arriba<br/>'
        '2. Si desea reenviar la solicitud, modifique la requisicion en el sistema<br/>'
        '3. Contacte con el administrador de la farmacia si tiene dudas',
        styles['Normal']
    )
    story.append(proximos_texto)
    story.append(Spacer(1, 0.2 * inch))

    # Construir PDF con canvas de fondo oficial
    def make_canvas(*args, **kwargs):
        return RequisicionCanvas(*args, fondo_path=fondo_path, **kwargs)
    
    doc.build(story, canvasmaker=make_canvas)
    buffer.seek(0)
    logger.info(f"PDF de rechazo generado para requisicion {requisicion.folio}")
    return buffer


def generar_hoja_consulta(requisicion):
    """
    Genera PDF de hoja de consulta simplificada para centros.
    Esta versión tiene un sello "SURTIDA" y NO muestra las firmas completas.
    Solo para requisiciones en estado surtida o entregada.
    
    Args:
        requisicion: Objeto Requisicion
    
    Returns:
        BytesIO: Buffer con PDF generado
    """
    buffer = BytesIO()
    
    fondo_institucional = get_fondo_institucional_path()
    fondo_path = str(fondo_institucional) if fondo_institucional else None
    
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        topMargin=1*inch,
        bottomMargin=0.8*inch,
        leftMargin=0.5*inch,
        rightMargin=0.5*inch
    )
    story = []
    styles = getSampleStyleSheet()
    
    # Estilo para título
    titulo_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=COLOR_GUINDA,
        spaceAfter=10,
        spaceBefore=10,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Determinar el sello según el estado
    estado = (requisicion.estado or '').lower()
    if estado == 'entregada':
        sello_texto = "[ ENTREGADA ]"
        sello_color = colors.HexColor('#16a34a')  # Verde
    else:
        sello_texto = "[ SURTIDA ]"
        sello_color = colors.HexColor('#2563eb')  # Azul
    
    # Estilo para subtítulo de estado
    surtida_style = ParagraphStyle(
        'SurtidaTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=sello_color,
        spaceAfter=20,
        spaceBefore=5,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Estilo para subtítulos
    subtitulo_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=11,
        textColor=COLOR_GUINDA,
        spaceAfter=10,
        fontName='Helvetica-Bold'
    )
    
    # Estilo para celdas con texto largo
    celda_texto_style = ParagraphStyle(
        'CeldaTexto',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        wordWrap='CJK',
        alignment=TA_LEFT,
    )
    
    # Estilo para celdas de unidad (texto largo)
    celda_unidad_consulta_style = ParagraphStyle(
        'CeldaUnidadConsulta',
        parent=styles['Normal'],
        fontSize=7,
        leading=9,
        wordWrap='CJK',
        alignment=TA_CENTER,
    )
    
    # Título principal
    titulo = Paragraph("HOJA DE CONSULTA - REQUISICIÓN DE MEDICAMENTOS", titulo_style)
    story.append(titulo)
    
    # SELLO DINÁMICO DE ESTADO (SURTIDA o ENTREGADA)
    surtida_stamp = Paragraph(sello_texto, surtida_style)
    story.append(surtida_stamp)
    story.append(Spacer(1, 0.1*inch))
    
    # Información de la requisición (con manejo defensivo de nulls)
    centro_obj = getattr(requisicion, 'centro_origen', None) or getattr(requisicion, 'centro_destino', None)
    centro_nombre = centro_obj.nombre if centro_obj else 'N/A'
    
    # Obtener nombre del solicitante de forma segura
    solicitante = getattr(requisicion, 'solicitante', None)
    if solicitante:
        try:
            solicitante_nombre = solicitante.get_full_name() or solicitante.username or 'N/A'
        except:
            solicitante_nombre = str(solicitante) if solicitante else 'N/A'
    else:
        solicitante_nombre = 'N/A'
    
    # Fechas (con manejo defensivo)
    fecha_surtido_texto = 'N/A'
    fecha_surtido = getattr(requisicion, 'fecha_surtido', None)
    if fecha_surtido:
        try:
            fecha_surtido_texto = fecha_surtido.strftime('%d/%m/%Y %H:%M')
        except:
            fecha_surtido_texto = str(fecha_surtido)
    
    fecha_entrega_texto = 'N/A'
    fecha_entrega = getattr(requisicion, 'fecha_entrega', None)
    if fecha_entrega:
        try:
            fecha_entrega_texto = fecha_entrega.strftime('%d/%m/%Y %H:%M')
        except:
            fecha_entrega_texto = str(fecha_entrega)
    
    # Fecha de solicitud
    fecha_solicitud_texto = 'N/A'
    fecha_solicitud = getattr(requisicion, 'fecha_solicitud', None)
    if fecha_solicitud:
        try:
            fecha_solicitud_texto = fecha_solicitud.strftime('%d/%m/%Y')
        except:
            fecha_solicitud_texto = str(fecha_solicitud)
    
    info_data = [
        ['Folio:', requisicion.folio or f'REQ-{requisicion.id}', 'Estado:', (requisicion.estado or '').upper()],
        ['Centro Solicitante:', centro_nombre, 'Fecha de Solicitud:', fecha_solicitud_texto],
        ['Solicitante:', solicitante_nombre, 'Fecha de Surtido:', fecha_surtido_texto],
        ['', '', 'Fecha de Entrega:', fecha_entrega_texto],
    ]
    
    info_table = Table(info_data, colWidths=[1.5*inch, 2.5*inch, 1.5*inch, 2*inch])
    info_table.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_TEXTO),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GUINDA),
    ]))
    
    story.append(info_table)
    story.append(Spacer(1, 0.25*inch))
    
    # Subtítulo de productos
    productos_titulo = Paragraph("PRODUCTOS SURTIDOS", subtitulo_style)
    story.append(productos_titulo)
    story.append(Spacer(1, 0.1*inch))
    
    # Tabla de productos con cantidad surtida
    productos_data = [
        ['#', 'Clave', 'Descripción', 'Solicitado', 'Surtido', 'Unidad']
    ]
    
    try:
        detalles = requisicion.detalles.all()
    except:
        detalles = []
    
    for idx, detalle in enumerate(detalles, start=1):
        try:
            producto = getattr(detalle, 'producto', None)
            if producto:
                descripcion_texto = producto.descripcion or producto.nombre or 'N/A'
                clave = producto.clave or 'N/A'
                unidad = getattr(producto, 'unidad_medida', None) or 'UND'
            else:
                descripcion_texto = 'Producto no disponible'
                clave = 'N/A'
                unidad = 'UND'
            
            descripcion_paragraph = Paragraph(descripcion_texto, celda_texto_style)
            # Usar Paragraph para unidad - permite texto largo como "CAJA CON 20 TABLETAS"
            unidad_paragraph = Paragraph(unidad, celda_unidad_consulta_style)
            
            cantidad_solicitada = getattr(detalle, 'cantidad_solicitada', 0) or 0
            cantidad_surtida = getattr(detalle, 'cantidad_entregada', None) or getattr(detalle, 'cantidad_autorizada', 0) or 0
            
            productos_data.append([
                str(idx),
                clave,
                descripcion_paragraph,
                str(cantidad_solicitada),
                str(cantidad_surtida),
                unidad_paragraph
            ])
        except Exception as e:
            # Si falla un detalle, agregar fila de error
            productos_data.append([
                str(idx),
                'ERROR',
                Paragraph(f'Error: {str(e)}', celda_texto_style),
                '0',
                '0',
                Paragraph('UND', celda_unidad_consulta_style)
            ])
    
    # Unidad ampliada de 0.7" a 1.4" para textos largos
    productos_table = Table(
        productos_data, 
        colWidths=[0.35*inch, 0.7*inch, 2.6*inch, 0.7*inch, 0.7*inch, 1.4*inch]
    )
    productos_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_GUINDA),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('TEXTCOLOR', (0, 1), (-1, -1), COLOR_TEXTO),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('ALIGN', (3, 1), (5, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GUINDA),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
    ]))
    
    story.append(productos_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Nota informativa en lugar de firmas
    nota_style = ParagraphStyle(
        'NotaStyle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=COLOR_GRIS,
        alignment=TA_CENTER,
        spaceBefore=10,
        spaceAfter=10,
    )
    
    nota = Paragraph(
        "Este documento es una copia de consulta. "
        "El documento original con firmas está en resguardo de Farmacia Central.",
        nota_style
    )
    story.append(nota)
    
    # Construir PDF con canvas de fondo oficial
    def make_canvas(*args, **kwargs):
        return RequisicionCanvas(*args, fondo_path=fondo_path, **kwargs)
    
    doc.build(story, canvasmaker=make_canvas)
    
    buffer.seek(0)
    logger.info(f"Hoja de consulta generada para requisición {requisicion.folio}")
    return buffer

def generar_hoja_entrega(datos_entrega, finalizado=False):
    """
    Genera PDF de hoja de entrega para salida masiva de Farmacia.
    Con fondo oficial del Gobierno del Estado de México.
    
    Args:
        datos_entrega: Dict con:
            - grupo_salida: ID del grupo de salida
            - centro_destino: Nombre del centro
            - fecha: Fecha de la entrega
            - usuario: Nombre del usuario que procesa
            - observaciones: Notas adicionales
            - items: Lista de productos entregados
        finalizado: bool - Si es True, muestra sello de ENTREGADO en lugar de firmas
    
    Returns:
        BytesIO: Buffer con PDF generado
    """
    buffer = BytesIO()
    
    # Obtener ruta del fondo institucional
    fondo_institucional = get_fondo_institucional_path()
    fondo_path = str(fondo_institucional) if fondo_institucional else None
    
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        topMargin=1*inch,
        bottomMargin=0.8*inch,
        leftMargin=0.5*inch,
        rightMargin=0.5*inch
    )
    story = []
    styles = getSampleStyleSheet()
    
    # Estilo para título
    titulo_style = ParagraphStyle(
        'EntregaTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=COLOR_GUINDA,
        spaceAfter=20,
        spaceBefore=10,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Estilo para subtítulos
    subtitulo_style = ParagraphStyle(
        'EntregaSubtitle',
        parent=styles['Heading2'],
        fontSize=11,
        textColor=COLOR_GUINDA,
        spaceAfter=10,
        fontName='Helvetica-Bold'
    )
    
    # Estilo para celdas con texto largo (descripción)
    celda_texto_style = ParagraphStyle(
        'CeldaTexto',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        wordWrap='CJK',
        alignment=TA_LEFT,
    )
    
    # Estilo para celdas de unidad (texto que puede ser largo)
    celda_unidad_style = ParagraphStyle(
        'CeldaUnidad',
        parent=styles['Normal'],
        fontSize=7,
        leading=9,
        wordWrap='CJK',
        alignment=TA_CENTER,
    )
    
    # Título principal
    titulo = Paragraph("HOJA DE ENTREGA DE MEDICAMENTOS", titulo_style)
    story.append(titulo)
    story.append(Spacer(1, 0.15*inch))
    
    # Información de la entrega
    fecha_str = datos_entrega['fecha'].strftime('%d/%m/%Y %H:%M') if datos_entrega.get('fecha') else 'N/A'
    
    info_data = [
        ['Folio de Salida:', datos_entrega.get('grupo_salida', 'N/A'), 'Fecha:', fecha_str],
        ['Centro Destino:', datos_entrega.get('centro_destino', 'N/A'), 'Procesado por:', datos_entrega.get('usuario', 'N/A')],
        ['Observaciones:', datos_entrega.get('observaciones', '') or 'Sin observaciones', '', ''],
    ]
    
    info_table = Table(info_data, colWidths=[1.3*inch, 2.7*inch, 1.2*inch, 2.3*inch])
    info_table.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_TEXTO),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GUINDA),
        ('SPAN', (1, 2), (3, 2)),  # Observaciones span
    ]))
    
    story.append(info_table)
    story.append(Spacer(1, 0.25*inch))
    
    # Subtítulo de productos
    productos_titulo = Paragraph("PRODUCTOS ENTREGADOS", subtitulo_style)
    story.append(productos_titulo)
    story.append(Spacer(1, 0.1*inch))
    
    # Tabla de productos - Headers
    productos_data = [
        ['#', 'Clave', 'Descripción', 'Lote', 'Caducidad', 'Cant.', 'Unidad']
    ]
    
    total_items = 0
    for idx, item in enumerate(datos_entrega.get('items', []), start=1):
        descripcion_paragraph = Paragraph(item.get('descripcion', 'N/A'), celda_texto_style)
        # Usar Paragraph para unidad también - permite texto largo como "CAJA CON 20 TABLETAS"
        unidad_paragraph = Paragraph(item.get('unidad', 'UND'), celda_unidad_style)
        productos_data.append([
            str(idx),
            item.get('clave', 'N/A'),
            descripcion_paragraph,
            item.get('lote', 'N/A'),
            item.get('caducidad', 'N/A'),
            str(item.get('cantidad', 0)),
            unidad_paragraph
        ])
        total_items += item.get('cantidad', 0)
    
    # Fila de total
    productos_data.append([
        '', '', '', '', 'TOTAL:', str(total_items), ''
    ])
    
    # Anchos ajustados: Descripción reducida, Unidad aumentada significativamente
    # Total disponible: ~7.5 inch (letter width - margins)
    productos_table = Table(
        productos_data, 
        colWidths=[0.3*inch, 0.6*inch, 2.0*inch, 0.85*inch, 0.8*inch, 0.45*inch, 1.7*inch]
    )
    productos_table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_GUINDA),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        
        # Data rows
        ('TEXTCOLOR', (0, 1), (-1, -1), COLOR_TEXTO),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('ALIGN', (5, 1), (6, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GUINDA),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        
        # Fila de total
        ('FONTNAME', (4, -1), (5, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (4, -1), (5, -1), colors.HexColor('#f3f4f6')),
    ]))
    
    story.append(productos_table)
    story.append(Spacer(1, 0.4*inch))
    
    # Estilo para notas
    nota_style = ParagraphStyle(
        'NotaLegal',
        parent=styles['Normal'],
        fontSize=8,
        textColor=COLOR_GRIS,
        alignment=TA_CENTER,
    )
    
    if finalizado:
        # Mostrar sello de ENTREGADO en lugar de firmas
        entregado_style = ParagraphStyle(
            'EntregadoSello',
            parent=styles['Heading1'],
            fontSize=36,
            textColor=colors.HexColor('#22c55e'),  # Verde
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            spaceBefore=20,
            spaceAfter=10,
        )
        
        entregado_box_style = ParagraphStyle(
            'EntregadoBox',
            parent=styles['Normal'],
            fontSize=11,
            textColor=COLOR_TEXTO,
            alignment=TA_CENTER,
        )
        
        # Sello ENTREGADO
        sello_data = [
            [Paragraph("✓ ENTREGADO", entregado_style)],
            [Spacer(1, 0.1*inch)],
            [Paragraph(f"Entrega confirmada el {datos_entrega['fecha'].strftime('%d/%m/%Y %H:%M') if datos_entrega.get('fecha') else 'N/A'}", entregado_box_style)],
            [Paragraph(f"Procesado por: {datos_entrega.get('usuario', 'N/A')}", entregado_box_style)],
        ]
        
        sello_table = Table(sello_data, colWidths=[5*inch])
        sello_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#22c55e')),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        story.append(sello_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Nota de comprobante
        comprobante_nota = Paragraph(
            "Este documento es el comprobante oficial de entrega de medicamentos. "
            "La entrega ha sido registrada en el sistema.",
            nota_style
        )
        story.append(comprobante_nota)
    else:
        # Sección de firmas (PDF para firmar)
        firmas_titulo = Paragraph("<b>FIRMAS DE ENTREGA Y RECEPCIÓN</b>", ParagraphStyle(
            'FirmasTitulo', fontSize=10, textColor=COLOR_GUINDA, 
            alignment=TA_CENTER, spaceAfter=15
        ))
        story.append(firmas_titulo)
        
        # Firmas: Farmacia entrega y Centro recibe
        firmas_data = [
            ['ENTREGA FARMACIA CENTRAL:', 'RECIBE CENTRO PENITENCIARIO:'],
            ['', ''],
            ['', ''],
            ['_' * 35, '_' * 35],
            ['Nombre y Firma', 'Nombre y Firma'],
            ['', ''],
            ['Fecha: ____/____/________', 'Fecha: ____/____/________'],
            ['Hora: ____:____', 'Hora: ____:____'],
        ]
        
        firmas_table = Table(firmas_data, colWidths=[3.5*inch, 3.5*inch])
        firmas_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_TEXTO),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        # Mantener firmas juntas
        seccion_firmas = KeepTogether([firmas_table])
        story.append(seccion_firmas)
        
        story.append(Spacer(1, 0.3*inch))
        
        # Nota legal
        nota = Paragraph(
            "Este documento ampara la entrega de medicamentos de Farmacia Central al Centro Penitenciario. "
            "Ambas partes conservarán una copia firmada.",
            nota_style
        )
        story.append(nota)
    
    # Construir PDF
    def make_canvas(*args, **kwargs):
        return RequisicionCanvas(*args, fondo_path=fondo_path, **kwargs)
    
    doc.build(story, canvasmaker=make_canvas)
    
    buffer.seek(0)
    logger.info(f"Hoja de entrega generada: {datos_entrega.get('grupo_salida')}")
    return buffer