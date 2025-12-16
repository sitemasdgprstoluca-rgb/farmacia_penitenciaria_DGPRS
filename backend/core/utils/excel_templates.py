"""
Generador de plantillas Excel actualizadas para carga masiva.
Basado en el esquema real de la base de datos (public.productos, public.lotes, public.usuarios).

HALLAZGO #6 - Manejo de Memoria:
- Los archivos Excel se generan completamente en memoria (sin archivos temporales)
- Para volúmenes actuales (<1000 filas de ejemplo), el consumo de RAM es aceptable (~2-5 MB por plantilla)
- Si se requieren plantillas con miles de filas o validaciones complejas (listas desplegables),
  considerar usar openpyxl en modo write_only para reducir consumo de memoria
- Las plantillas actuales no dejan archivos temporales en el servidor
- El workbook se serializa directamente al HttpResponse y se libera automáticamente

Límites recomendados por plantilla:
- Filas de ejemplo: < 100
- Hojas: < 5
- Tamaño máximo del archivo generado: < 10 MB
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from django.http import HttpResponse
from datetime import date


def aplicar_estilos_header(ws, num_columnas):
    """Aplica estilos consistentes a los encabezados."""
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="9F2241", end_color="9F2241", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    
    border_style = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    for col_num in range(1, num_columnas + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = border_style
    
    ws.freeze_panes = 'A2'


def generar_plantilla_productos():
    """
    Genera plantilla Excel para carga masiva de productos.
    Basado en tabla: public.productos
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Productos"

    # Columnas EXACTAS que coinciden con la plantilla descargable
    # IMPORTANTE: Estos nombres deben coincidir con los sinónimos en excel_importer.py
    headers = [
        "Clave",
        "Nombre",
        "Unidad",
        "Stock Minimo",
        "Categoria",
        "Sustancia Activa",
        "Presentacion",
        "Concentracion",
        "Via Admin",
        "Requiere Receta",
        "Controlado",
        "Estado"
    ]

    # Anchos personalizados por columna para mejor legibilidad
    column_widths = [15, 40, 15, 15, 20, 25, 25, 20, 20, 18, 15, 12]
    
    for col_num, header in enumerate(headers, 1):
        ws.cell(row=1, column=col_num, value=header)
        if col_num <= len(column_widths):
            ws.column_dimensions[openpyxl.utils.get_column_letter(col_num)].width = column_widths[col_num - 1]
    
    aplicar_estilos_header(ws, len(headers))

    # Fila de ejemplo que coincide con el formato actualizado
    ws.append([
        "615",
        "PARACETAMOL",
        "CAJA",
        10,
        "medicamento",
        "Paracetamol",
        "Tabletas",
        "500mg",
        "Oral",
        "No",
        "No",
        "Activo"
    ])

    # Instrucciones en hoja separada
    ws_inst = wb.create_sheet("Instrucciones")
    instrucciones = [
        ["INSTRUCCIONES DE LLENADO DE PLANTILLA - PRODUCTOS"],
        [""],
        ["Campos obligatorios marcados con asterisco (*)"],
        [""],
        ["CLAVE (REQUERIDO):", "Código único del producto. Ej: 615, 616, 1A, MED-001"],
        ["NOMBRE (REQUERIDO):", "Nombre completo del producto (mínimo 5 caracteres)"],
        ["UNIDAD (REQUERIDO):", "Unidad de medida. Valores: PIEZA, CAJA, FRASCO, SOBRE, AMPOLLETA, TABLETA, CAPSULA, ML, GR, TUBO, BOLSA"],
        ["STOCK MINIMO (REQUERIDO):", "Cantidad mínima en inventario (número entero, ej: 10)"],
        ["CATEGORIA (REQUERIDO):", "Tipo de producto. Valores: medicamento, material_curacion, insumo"],
        ["SUSTANCIA ACTIVA:", "Principio activo del medicamento (opcional)"],
        ["PRESENTACION:", "Formato de presentación (opcional, ej: Tabletas, Jarabe)"],
        ["CONCENTRACION:", "Dosis o concentración (opcional, ej: 500mg, 5ml)"],
        ["VIA ADMIN:", "Vía de administración (opcional, ej: Oral, Intramuscular)"],
        ["REQUIERE RECETA:", "Si/No - Indica si requiere receta médica (default: No)"],
        ["CONTROLADO:", "Si/No - Indica si es medicamento controlado (default: No)"],
        ["ESTADO:", "Activo/Inactivo - Estado del producto (default: Activo)"],
        [""],
        ["NOTAS IMPORTANTES:"],
        ["• La clave debe ser única en todo el sistema"],
        ["• Los valores booleanos aceptan: Si/Sí/Yes/True/1/Activo para verdadero, No/False/0/Inactivo para falso"],
        ["• La Unidad se puede escribir completa: 'CAJA CON 7 OVULOS' se convertirá automáticamente a 'CAJA'"],
        ["• Si la plantilla tiene datos de ejemplo, puede borrarlos o mantener la fila 2 como referencia"],
        ["• Puede eliminar la hoja 'Instrucciones' antes de subir el archivo"],
        ["• Máximo 10,000 filas por archivo"],
        ["• Tamaño máximo de archivo: 10MB"],
    ]
    
    for row_data in instrucciones:
        ws_inst.append(row_data)
    
    ws_inst.column_dimensions['A'].width = 25
    ws_inst.column_dimensions['B'].width = 70

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=Plantilla_Productos.xlsx'
    wb.save(response)
    wb.close()  # HALLAZGO #6: Liberar recursos explícitamente
    return response


def generar_plantilla_lotes(centro=None):
    """
    Genera plantilla Excel para carga masiva de lotes/inventario inicial.
    Basado en tabla: public.lotes
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Lotes Inventario"

    headers = [
        "Clave Producto*\n(Debe existir)",
        "Número Lote*\n(Único)",
        "Cantidad Inicial*",
        "Fecha Caducidad*\n(YYYY-MM-DD)",
        "Fecha Fabricación\n(YYYY-MM-DD)",
        "Precio Unitario*\n(Decimal)",
        "Número Contrato",
        "Marca",
        "Ubicación\n(Ej: Estante A1)"
    ]

    for col_num, header in enumerate(headers, 1):
        ws.cell(row=1, column=col_num, value=header)
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_num)].width = 20
    
    aplicar_estilos_header(ws, len(headers))

    # Ejemplo
    ws.append([
        "PAR-500",
        "LOTE-2024-ABC-001",
        100,
        "2026-12-31",
        "2024-01-15",
        15.50,
        "CTR-2024-001",
        "Laboratorios XYZ",
        "Estante A1-Nivel 2"
    ])

    # Instrucciones
    ws_inst = wb.create_sheet("Instrucciones")
    instrucciones = [
        ["INSTRUCCIONES DE LLENADO DE PLANTILLA - LOTES"],
        [""],
        ["Campos obligatorios marcados con asterisco (*)"],
        [""],
        ["CLAVE PRODUCTO*:", "Debe coincidir con una clave existente en el catálogo de productos"],
        ["NÚMERO LOTE*:", "Identificador único del lote proporcionado por el fabricante"],
        ["CANTIDAD INICIAL*:", "Cantidad de unidades del lote (número entero positivo)"],
        ["FECHA CADUCIDAD*:", "Formato: YYYY-MM-DD (Ej: 2026-12-31)"],
        ["FECHA FABRICACIÓN:", "Formato: YYYY-MM-DD (Ej: 2024-01-15) - opcional"],
        ["PRECIO UNITARIO*:", "Precio por unidad (decimal, ej: 15.50)"],
        ["NÚMERO CONTRATO:", "Número del contrato de adquisición (opcional)"],
        ["MARCA:", "Marca o laboratorio fabricante (opcional)"],
        ["UBICACIÓN:", "Ubicación física en almacén (opcional, ej: Estante A1)"],
        [""],
        [f"CENTRO ASIGNADO:", centro.nombre if centro else "Se asignará automáticamente"],
        [""],
        ["NOTAS IMPORTANTES:"],
        ["• El producto debe existir antes de cargar lotes"],
        ["• La cantidad_actual se inicializa igual a cantidad_inicial"],
        ["• El stock del producto se actualiza automáticamente"],
        ["• Las fechas deben estar en formato ISO: YYYY-MM-DD"],
        ["• Elimine esta hoja antes de subir el archivo"],
    ]
    
    for row_data in instrucciones:
        ws_inst.append(row_data)
    
    ws_inst.column_dimensions['A'].width = 25
    ws_inst.column_dimensions['B'].width = 70

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=Plantilla_Lotes_Inventario.xlsx'
    wb.save(response)
    wb.close()  # HALLAZGO #6: Liberar recursos explícitamente
    return response


def generar_plantilla_usuarios():
    """
    Genera plantilla Excel para carga masiva de usuarios.
    Basado en tabla: public.usuarios (User model extendido)
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Usuarios"

    headers = [
        "Username*\n(Único, 3-150 chars)",
        "Email*\n(Único)",
        "Nombre*\n(first_name)",
        "Apellidos*\n(last_name)",
        "Password*\n(Mín 8 chars)",
        "Rol*\n(Ver instrucciones)",
        "Centro ID\n(Número o vacío)",
        "Adscripción",
        "Teléfono",
        "Activo\n(Si/No, default: Si)"
    ]

    for col_num, header in enumerate(headers, 1):
        ws.cell(row=1, column=col_num, value=header)
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_num)].width = 20
    
    aplicar_estilos_header(ws, len(headers))

    # Ejemplos
    ws.append([
        "medico01",
        "medico@centro.gob.mx",
        "Juan",
        "Pérez García",
        "Temporal123!",
        "medico",
        1,
        "Área Médica",
        "5551234567",
        "Si"
    ])
    
    ws.append([
        "admin_farmacia",
        "farmacia@sistema.gob.mx",
        "María",
        "López Hernández",
        "Admin2024!",
        "farmacia",
        "",
        "Farmacia Central",
        "5559876543",
        "Si"
    ])

    # Instrucciones
    ws_inst = wb.create_sheet("Instrucciones")
    instrucciones = [
        ["INSTRUCCIONES DE LLENADO DE PLANTILLA - USUARIOS"],
        [""],
        ["Campos obligatorios marcados con asterisco (*)"],
        [""],
        ["USERNAME*:", "Nombre de usuario único (3-150 caracteres, sin espacios)"],
        ["EMAIL*:", "Correo electrónico único y válido"],
        ["NOMBRE*:", "Nombre(s) del usuario"],
        ["APELLIDOS*:", "Apellido(s) del usuario"],
        ["PASSWORD*:", "Contraseña temporal (mínimo 8 caracteres, se debe cambiar al primer ingreso)"],
        ["ROL*:", "Ver tabla de roles permitidos abajo"],
        ["CENTRO ID:", "ID numérico del centro penitenciario (dejar vacío para Farmacia Central)"],
        ["ADSCRIPCIÓN:", "Área de trabajo o departamento (opcional)"],
        ["TELÉFONO:", "Número telefónico (opcional)"],
        ["ACTIVO:", "Si/No - Estado del usuario (default: Si)"],
        [""],
        ["ROLES DISPONIBLES:"],
        [""],
        ["ROL", "DESCRIPCIÓN", "REQUIERE CENTRO"],
        ["admin", "Administrador del sistema", "No"],
        ["farmacia", "Personal de Farmacia Central", "No"],
        ["vista", "Solo lectura (Farmacia)", "No"],
        ["medico", "Médico del centro (crea requisiciones)", "Sí*"],
        ["administrador_centro", "Administrador del centro penitenciario", "Sí*"],
        ["director_centro", "Director del centro penitenciario", "Sí*"],
        ["centro", "Personal general del centro", "Sí"],
        [""],
        ["* Si el rol requiere centro, debe proporcionar un Centro ID válido"],
        [""],
        ["NOTAS IMPORTANTES:"],
        ["• El username y email deben ser únicos en todo el sistema"],
        ["• Los usuarios deben cambiar su contraseña en el primer acceso"],
        ["• Los permisos se asignan automáticamente según el rol"],
        ["• Para rol 'admin' use un email institucional verificado"],
        ["• Elimine esta hoja antes de subir el archivo"],
    ]
    
    for row_data in instrucciones:
        ws_inst.append(row_data)
    
    ws_inst.column_dimensions['A'].width = 25
    ws_inst.column_dimensions['B'].width = 70
    ws_inst.column_dimensions['C'].width = 20

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=Plantilla_Usuarios.xlsx'
    wb.save(response)
    wb.close()  # HALLAZGO #6: Liberar recursos explícitamente
    return response
