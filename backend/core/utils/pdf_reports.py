"""
Generador de reportes PDF profesionales para el sistema de farmacia penitenciaria
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.platypus import Image as RLImage
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from django.utils import timezone
from io import BytesIO
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)


def crear_encabezado(styles):
    """Crea el encabezado estándar para reportes"""
    titulo_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1a1a1a'),
        alignment=TA_CENTER,
        spaceAfter=30
    )
    
    return titulo_style


def crear_pie_pagina(canvas, doc):
    """Agrega número de página al pie"""
    canvas.saveState()
    canvas.setFont('Helvetica', 9)
    page_num = canvas.getPageNumber()
    text = f"Página {page_num}"
    canvas.drawRightString(7.5 * inch, 0.5 * inch, text)
    canvas.drawString(inch, 0.5 * inch, f"Generado: {timezone.now().strftime('%d/%m/%Y %H:%M')}")
    canvas.restoreState()


def generar_reporte_inventario(productos_data, formato='pdf'):
    """
    Genera reporte PDF de inventario completo
    
    Args:
        productos_data: Lista de diccionarios con datos de productos
        formato: 'pdf' (default)
    
    Returns:
        BytesIO con el PDF generado
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.75*inch, bottomMargin=0.75*inch)
    
    # Elementos del documento
    elements = []
    styles = getSampleStyleSheet()
    titulo_style = crear_encabezado(styles)
    
    # Título
    titulo = Paragraph("REPORTE DE INVENTARIO GENERAL", titulo_style)
    elements.append(titulo)
    elements.append(Spacer(1, 0.3*inch))
    
    # Fecha y filtros
    fecha_info = Paragraph(
        f"<b>Fecha de generación:</b> {timezone.now().strftime('%d/%m/%Y %H:%M')}<br/>"
        f"<b>Total de productos:</b> {len(productos_data)}",
        styles['Normal']
    )
    elements.append(fecha_info)
    elements.append(Spacer(1, 0.2*inch))
    
    # Tabla de datos
    data = [['Clave', 'Descripción', 'Stock Actual', 'Stock Mínimo', 'Nivel', 'Precio', 'Valor Total']]
    
    for producto in productos_data:
        data.append([
            str(producto['clave']),
            str(producto['descripcion'])[:40],  # Truncar descripción
            str(producto.get('stock_actual', 0)),
            str(producto.get('stock_minimo', 0)),
            str(producto.get('nivel_stock', 'N/A')),
            f"${producto.get('precio_unitario', 0):.2f}",
            f"${producto.get('valor_inventario', 0):.2f}"
        ])
    
    # Crear tabla con estilo
    table = Table(data, colWidths=[0.8*inch, 2.2*inch, 0.8*inch, 0.8*inch, 0.7*inch, 0.8*inch, 0.9*inch])
    
    table.setStyle(TableStyle([
        # Encabezado
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Contenido
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),  # Números alineados a la derecha
        ('ALIGN', (0, 1), (1, -1), 'LEFT'),     # Texto alineado a la izquierda
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Resumen
    total_valor = sum(p.get('valor_inventario', 0) for p in productos_data)
    productos_criticos = sum(1 for p in productos_data if p.get('nivel_stock') == 'critico')
    productos_sin_stock = sum(1 for p in productos_data if p.get('stock_actual', 0) == 0)
    
    resumen_text = f"""
    <b>RESUMEN EJECUTIVO</b><br/>
    Total de productos: {len(productos_data)}<br/>
    Productos sin stock: {productos_sin_stock}<br/>
    Productos en nivel crítico: {productos_criticos}<br/>
    <b>Valor total del inventario: ${total_valor:,.2f}</b>
    """
    
    resumen = Paragraph(resumen_text, styles['Normal'])
    elements.append(resumen)
    
    # Construir PDF
    doc.build(elements, onFirstPage=crear_pie_pagina, onLaterPages=crear_pie_pagina)
    
    buffer.seek(0)
    logger.info(f"Reporte de inventario PDF generado: {len(productos_data)} productos")
    return buffer


def generar_reporte_caducidades(lotes_data, dias=30):
    """
    Genera reporte PDF de lotes próximos a caducar
    
    Args:
        lotes_data: Lista de diccionarios con datos de lotes
        dias: Días de anticipación para el reporte
    
    Returns:
        BytesIO con el PDF generado
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.75*inch, bottomMargin=0.75*inch)
    
    elements = []
    styles = getSampleStyleSheet()
    titulo_style = crear_encabezado(styles)
    
    # Título con énfasis en urgencia
    titulo = Paragraph(
        f"⚠️ REPORTE DE LOTES PRÓXIMOS A CADUCAR ({dias} DÍAS)",
        titulo_style
    )
    elements.append(titulo)
    elements.append(Spacer(1, 0.3*inch))
    
    # Información del reporte
    fecha_info = Paragraph(
        f"<b>Fecha de generación:</b> {timezone.now().strftime('%d/%m/%Y %H:%M')}<br/>"
        f"<b>Lotes identificados:</b> {len(lotes_data)}<br/>"
        f"<b>Período de análisis:</b> Próximos {dias} días",
        styles['Normal']
    )
    elements.append(fecha_info)
    elements.append(Spacer(1, 0.2*inch))
    
    # Tabla de lotes
    data = [['Producto', 'Lote', 'Fecha Caducidad', 'Días Restantes', 'Cantidad', 'Alerta', 'Proveedor']]
    
    for lote in lotes_data:
        # Color de alerta
        alerta = lote.get('alerta', 'normal')
        dias_restantes = lote.get('dias_restantes', 999)
        
        data.append([
            str(lote.get('producto_descripcion', ''))[:25],
            str(lote.get('numero_lote', '')),
            lote.get('fecha_caducidad', ''),
            str(dias_restantes),
            str(lote.get('cantidad_actual', 0)),
            alerta.upper(),
            str(lote.get('proveedor', ''))[:15]
        ])
    
    table = Table(data, colWidths=[1.8*inch, 0.9*inch, 1*inch, 0.8*inch, 0.6*inch, 0.7*inch, 1.2*inch])
    
    # Estilo base
    style_commands = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#c0392b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('ALIGN', (3, 1), (4, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]
    
    # Colorear filas según alerta
    for i, lote in enumerate(lotes_data, start=1):
        alerta = lote.get('alerta', 'normal')
        if alerta == 'vencido':
            style_commands.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#ffcccc')))
        elif alerta == 'critico':
            style_commands.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#ffe6cc')))
        elif alerta == 'proximo':
            style_commands.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#fff4cc')))
    
    table.setStyle(TableStyle(style_commands))
    elements.append(table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Resumen de alertas
    vencidos = sum(1 for l in lotes_data if l.get('alerta') == 'vencido')
    criticos = sum(1 for l in lotes_data if l.get('alerta') == 'critico')
    proximos = sum(1 for l in lotes_data if l.get('alerta') == 'proximo')
    
    resumen_text = f"""
    <b>RESUMEN DE ALERTAS</b><br/>
    <font color="red">● Vencidos: {vencidos}</font><br/>
    <font color="orange">● Críticos (≤7 días): {criticos}</font><br/>
    <font color="#cc9900">● Próximos (≤30 días): {proximos}</font><br/>
    <br/>
    <b>ACCIÓN REQUERIDA:</b> Revisar disposición de lotes vencidos y planificar uso prioritario de lotes críticos.
    """
    
    resumen = Paragraph(resumen_text, styles['Normal'])
    elements.append(resumen)
    
    doc.build(elements, onFirstPage=crear_pie_pagina, onLaterPages=crear_pie_pagina)
    
    buffer.seek(0)
    logger.info(f"Reporte de caducidades PDF generado: {len(lotes_data)} lotes")
    return buffer


def generar_reporte_requisiciones(requisiciones_data, filtros=None):
    """
    Genera reporte PDF de requisiciones
    
    Args:
        requisiciones_data: Lista de diccionarios con datos de requisiciones
        filtros: Diccionario con filtros aplicados (estado, fechas, etc.)
    
    Returns:
        BytesIO con el PDF generado
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.75*inch, bottomMargin=0.75*inch)
    
    elements = []
    styles = getSampleStyleSheet()
    titulo_style = crear_encabezado(styles)
    
    # Título
    titulo = Paragraph("REPORTE DE REQUISICIONES", titulo_style)
    elements.append(titulo)
    elements.append(Spacer(1, 0.3*inch))
    
    # Información y filtros
    filtros_text = "<b>Fecha de generación:</b> " + timezone.now().strftime('%d/%m/%Y %H:%M') + "<br/>"
    if filtros:
        if 'estado' in filtros:
            filtros_text += f"<b>Estado:</b> {filtros['estado']}<br/>"
        if 'fecha_inicio' in filtros:
            filtros_text += f"<b>Desde:</b> {filtros['fecha_inicio']}<br/>"
        if 'fecha_fin' in filtros:
            filtros_text += f"<b>Hasta:</b> {filtros['fecha_fin']}<br/>"
    filtros_text += f"<b>Total de requisiciones:</b> {len(requisiciones_data)}"
    
    info = Paragraph(filtros_text, styles['Normal'])
    elements.append(info)
    elements.append(Spacer(1, 0.2*inch))
    
    # Tabla
    data = [['Folio', 'Centro', 'Estado', 'Fecha Solicitud', 'Items', 'Usuario']]
    
    for req in requisiciones_data:
        data.append([
            str(req.get('folio', '')),
            str(req.get('centro_nombre', ''))[:20],
            str(req.get('estado', '')).upper(),
            str(req.get('fecha_solicitud', ''))[:10],
            str(req.get('total_items', 0)),
            str(req.get('usuario_solicita', ''))
        ])
    
    table = Table(data, colWidths=[1.2*inch, 1.8*inch, 1*inch, 1*inch, 0.6*inch, 1.4*inch])
    
    # Estilo
    style_commands = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (4, 1), (4, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ecf0f1')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]
    
    # Colorear por estado
    for i, req in enumerate(requisiciones_data, start=1):
        estado = req.get('estado', '').lower()
        if estado == 'autorizada':
            style_commands.append(('TEXTCOLOR', (2, i), (2, i), colors.HexColor('#27ae60')))
        elif estado == 'rechazada':
            style_commands.append(('TEXTCOLOR', (2, i), (2, i), colors.HexColor('#c0392b')))
        elif estado == 'surtida':
            style_commands.append(('TEXTCOLOR', (2, i), (2, i), colors.HexColor('#2980b9')))
    
    table.setStyle(TableStyle(style_commands))
    elements.append(table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Resumen por estados
    estados = {}
    for req in requisiciones_data:
        estado = req.get('estado', 'N/A')
        estados[estado] = estados.get(estado, 0) + 1
    
    resumen_text = "<b>RESUMEN POR ESTADOS</b><br/>"
    for estado, count in estados.items():
        resumen_text += f"{estado.upper()}: {count}<br/>"
    
    resumen = Paragraph(resumen_text, styles['Normal'])
    elements.append(resumen)
    
    doc.build(elements, onFirstPage=crear_pie_pagina, onLaterPages=crear_pie_pagina)
    
    buffer.seek(0)
    logger.info(f"Reporte de requisiciones PDF generado: {len(requisiciones_data)} registros")
    return buffer


def generar_reporte_movimientos(movimientos_data, filtros=None):
    """
    Genera reporte PDF de movimientos de inventario
    
    Args:
        movimientos_data: Lista de diccionarios con datos de movimientos
        filtros: Diccionario con filtros aplicados
    
    Returns:
        BytesIO con el PDF generado
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.75*inch, bottomMargin=0.75*inch)
    
    elements = []
    styles = getSampleStyleSheet()
    titulo_style = crear_encabezado(styles)
    
    titulo = Paragraph("REPORTE DE MOVIMIENTOS DE INVENTARIO", titulo_style)
    elements.append(titulo)
    elements.append(Spacer(1, 0.3*inch))
    
    # Información
    info_text = f"<b>Fecha de generación:</b> {timezone.now().strftime('%d/%m/%Y %H:%M')}<br/>"
    info_text += f"<b>Total de movimientos:</b> {len(movimientos_data)}"
    
    info = Paragraph(info_text, styles['Normal'])
    elements.append(info)
    elements.append(Spacer(1, 0.2*inch))
    
    # Tabla
    data = [['Fecha', 'Tipo', 'Producto', 'Lote', 'Cantidad', 'Usuario', 'Centro']]
    
    for mov in movimientos_data:
        data.append([
            str(mov.get('fecha_movimiento', ''))[:16],
            str(mov.get('tipo', '')),
            str(mov.get('producto_clave', ''))[:15],
            str(mov.get('numero_lote', ''))[:12],
            str(mov.get('cantidad', 0)),
            str(mov.get('usuario', ''))[:12],
            str(mov.get('centro', ''))[:15]
        ])
    
    table = Table(data, colWidths=[1.2*inch, 0.8*inch, 1.2*inch, 1*inch, 0.7*inch, 1*inch, 1.1*inch])
    
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16a085')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('ALIGN', (4, 1), (4, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#e8f8f5')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(table)
    
    doc.build(elements, onFirstPage=crear_pie_pagina, onLaterPages=crear_pie_pagina)
    
    buffer.seek(0)
    logger.info(f"Reporte de movimientos PDF generado: {len(movimientos_data)} registros")
    return buffer
