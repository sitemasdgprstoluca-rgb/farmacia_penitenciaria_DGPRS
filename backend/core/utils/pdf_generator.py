"""
Generador de PDFs para hojas de recolección de requisiciones
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def generar_hoja_recoleccion(requisicion):
    """
    Genera PDF con hoja de recolección para una requisición autorizada
    
    Args:
        requisicion: Objeto Requisicion
    
    Returns:
        BytesIO: Buffer con PDF generado
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Estilo personalizado para título
    titulo_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Estilo para subtítulos
    subtitulo_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#374151'),
        spaceAfter=12,
        fontName='Helvetica-Bold'
    )
    
    # Título principal
    titulo = Paragraph("HOJA DE RECOLECCIÓN DE MEDICAMENTOS", titulo_style)
    story.append(titulo)
    story.append(Spacer(1, 0.2*inch))
    
    # Información de la requisición
    info_data = [
        ['Folio:', requisicion.folio, 'Fecha de Solicitud:', requisicion.fecha_solicitud.strftime('%d/%m/%Y')],
        ['Centro Solicitante:', requisicion.centro.nombre, 'Estado:', requisicion.estado.upper()],
        ['Solicitante:', requisicion.usuario_solicita.get_full_name(), 'Fecha de Autorización:', 
         requisicion.fecha_autorizacion.strftime('%d/%m/%Y %H:%M') if requisicion.fecha_autorizacion else 'N/A'],
    ]
    
    if requisicion.usuario_autoriza:
        info_data.append(['Autorizado por:', requisicion.usuario_autoriza.get_full_name(), '', ''])
    
    info_table = Table(info_data, colWidths=[1.5*inch, 2.5*inch, 1.5*inch, 2*inch])
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
    story.append(Spacer(1, 0.3*inch))
    
    # Subtítulo de productos
    productos_titulo = Paragraph("PRODUCTOS AUTORIZADOS", subtitulo_style)
    story.append(productos_titulo)
    story.append(Spacer(1, 0.1*inch))
    
    # Tabla de productos
    productos_data = [
        ['#', 'Clave', 'Descripción', 'Lote', 'Caducidad', 'Cantidad', 'Unidad']
    ]
    
    for idx, detalle in enumerate(requisicion.detalles.all(), start=1):
        # Buscar lote con stock disponible para este producto
        lote_asignado = detalle.producto.lotes.filter(
            estado='disponible',
            cantidad_actual__gt=0
        ).order_by('fecha_caducidad').first()
        
        productos_data.append([
            str(idx),
            detalle.producto.clave,
            detalle.producto.descripcion[:40] + ('...' if len(detalle.producto.descripcion) > 40 else ''),
            lote_asignado.numero_lote if lote_asignado else 'SIN LOTE',
            lote_asignado.fecha_caducidad.strftime('%d/%m/%Y') if lote_asignado else 'N/A',
            str(detalle.cantidad_autorizada if detalle.cantidad_autorizada > 0 else detalle.cantidad_solicitada),
            detalle.producto.get_unidad_medida_display()
        ])
    
    productos_table = Table(
        productos_data, 
        colWidths=[0.4*inch, 0.8*inch, 2.5*inch, 1*inch, 0.9*inch, 0.7*inch, 0.7*inch]
    )
    productos_table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        
        # Data rows
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#374151')),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Número
        ('ALIGN', (5, 1), (6, -1), 'CENTER'),  # Cantidad y Unidad
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ]))
    
    story.append(productos_table)
    story.append(Spacer(1, 0.4*inch))
    
    # Sección de firmas
    firmas_data = [
        ['', ''],
        ['AUTORIZADO POR:', 'ENTREGADO POR:'],
        ['', ''],
        ['_' * 40, '_' * 40],
        [requisicion.usuario_autoriza.get_full_name() if requisicion.usuario_autoriza else '', ''],
        ['Nombre y Firma', 'Nombre y Firma'],
        ['', ''],
        ['RECIBIDO POR:', 'FECHA Y HORA DE ENTREGA:'],
        ['', ''],
        ['_' * 40, '_' * 40],
        [requisicion.centro.responsable if requisicion.centro.responsable else '', ''],
        ['Nombre y Firma', ''],
    ]
    
    firmas_table = Table(firmas_data, colWidths=[3.5*inch, 3.5*inch])
    firmas_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTNAME', (0, 7), (-1, 7), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTSIZE', (0, 4), (-1, 4), 10),
        ('FONTSIZE', (0, 10), (-1, 10), 10),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1f2937')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    
    story.append(firmas_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Pie de página
    nota_style = ParagraphStyle(
        'Nota',
        parent=styles['Normal'],
        fontSize=7,
        textColor=colors.HexColor('#6b7280'),
        alignment=TA_CENTER
    )
    
    nota = Paragraph(
        f"Documento generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M:%S')} | "
        f"Sistema de Control de Abasto - Farmacia Penitenciaria",
        nota_style
    )
    story.append(nota)
    
    # Construir PDF
    doc.build(story)
    
    buffer.seek(0)
    logger.info(f"Hoja de recolección generada para requisición {requisicion.folio}")
    return buffer


def generar_pdf_rechazo(requisicion):
    """
    Genera PDF para una requisicion en estado rechazado.
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from io import BytesIO
    from datetime import datetime

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    titulo_style = ParagraphStyle(
        'RejectTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#dc2626'),
        spaceAfter=30,
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

    info_data = [
        ['Folio:', requisicion.folio, 'Fecha de Solicitud:', requisicion.fecha_solicitud.strftime('%d/%m/%Y')],
        ['Centro Solicitante:', requisicion.centro.nombre, 'Estado:', 'RECHAZADA'],
        ['Solicitante:', requisicion.usuario_solicita.get_full_name(), 'Fecha de Rechazo:',
         requisicion.fecha_autorizacion.strftime('%d/%m/%Y %H:%M') if requisicion.fecha_autorizacion else 'N/A'],
        ['Rechazado por:', requisicion.usuario_autoriza.get_full_name() if requisicion.usuario_autoriza else 'N/A', '', ''],
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

    productos_data = [
        ['#', 'Clave', 'Descripcion', 'Cantidad Solicitada', 'Unidad']
    ]

    for idx, detalle in enumerate(requisicion.detalles.all(), start=1):
        productos_data.append([
            str(idx),
            detalle.producto.clave,
            detalle.producto.descripcion[:40] + ('...' if len(detalle.producto.descripcion) > 40 else ''),
            str(detalle.cantidad_solicitada),
            detalle.producto.get_unidad_medida_display() if hasattr(detalle.producto, 'get_unidad_medida_display') else getattr(detalle.producto, 'unidad_medida', 'UND')
        ])

    productos_table = Table(
        productos_data,
        colWidths=[0.4 * inch, 0.8 * inch, 2.5 * inch, 1.2 * inch, 0.7 * inch]
    )
    productos_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc2626')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#374151')),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('ALIGN', (3, 1), (3, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f4f6')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
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
    story.append(Spacer(1, 0.4 * inch))

    nota_style = ParagraphStyle(
        'Nota',
        parent=styles['Normal'],
        fontSize=7,
        textColor=colors.HexColor('#6b7280'),
        alignment=TA_CENTER
    )

    nota = Paragraph(
        f"Documento generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M:%S')} | "
        f"Sistema de Control de Abasto - Farmacia Penitenciaria",
        nota_style
    )
    story.append(nota)

    doc.build(story)
    buffer.seek(0)
    logger.info(f"PDF de rechazo generado para requisicion {requisicion.folio}")
    return buffer
