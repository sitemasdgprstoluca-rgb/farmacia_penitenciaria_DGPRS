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
        "CAJA CON 7 OVULOS",
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
        ["UNIDAD (REQUERIDO):", "Unidad de medida con texto libre. Ejemplos: PIEZA, CAJA, CAJA CON 7 OVULOS, GOTERO CON 15 MILILITROS, BOLSA FLEX-OVAL DE 500 ML"],
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
        ["• La Unidad acepta texto libre: escriba la descripción completa como 'CAJA CON 7 OVULOS' o 'GOTERO CON 15 MILILITROS'"],
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
    
    Columnas:
    - Clave Producto* (o ID Producto*): Identificador del producto
    - Nombre Producto: Referencia (opcional si se usa Clave/ID)
    - Número Lote*: Identificador único del lote
    - Fecha Fabricación: Fecha de fabricación (opcional)
    - Fecha Caducidad*: Fecha de caducidad (obligatorio)
    - Cantidad Inicial*: Cantidad de unidades (obligatorio)
    - Precio Unitario*: Precio por unidad (default 0)
    - Número Contrato: Número de contrato (opcional)
    - Marca: Marca o laboratorio (opcional)
    - Ubicación: Ubicación física (opcional)
    - Centro: Nombre del centro (opcional)
    - Activo: Estado del lote (opcional, default Activo)
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Lotes Inventario"

    headers = [
        "Clave Producto",
        "Nombre Producto",
        "Número Lote",
        "Fecha Fabricación",
        "Fecha Caducidad",
        "Cantidad Inicial",
        "Precio Unitario",
        "Número Contrato",
        "Marca",
        "Ubicación",
        "Centro",
        "Activo"
    ]

    for col_num, header in enumerate(headers, 1):
        ws.cell(row=1, column=col_num, value=header)
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_num)].width = 18
    
    aplicar_estilos_header(ws, len(headers))

    # Ejemplo
    ws.append([
        "PAR-500",
        "PARACETAMOL 500MG",
        "LOTE-2024-ABC-001",
        "2024-01-15",
        "2026-12-31",
        100,
        15.50,
        "CTR-2024-001",
        "Laboratorios XYZ",
        "Estante A1-Nivel 2",
        "Farmacia Central",
        "Activo"
    ])

    # Instrucciones
    ws_inst = wb.create_sheet("Instrucciones")
    instrucciones = [
        ["INSTRUCCIONES DE LLENADO DE PLANTILLA - LOTES"],
        [""],
        ["IDENTIFICACIÓN DEL PRODUCTO (Usar al menos UNO):"],
        ["  • Clave Producto: Código alfanumérico del producto (ej: PAR-500)"],
        ["  • O bien usar ID numérico si lo conoce en la columna 'Clave Producto'"],
        ["  • Nombre Producto es referencia visual (opcional)"],
        [""],
        ["CAMPOS OBLIGATORIOS:"],
        ["  Número Lote*:", "Identificador único del lote del fabricante"],
        ["  Fecha Caducidad*:", "Formato: YYYY-MM-DD (Ej: 2026-12-31)"],
        ["  Cantidad Inicial*:", "Cantidad de unidades del lote (número entero positivo)"],
        ["  Precio Unitario*:", "Precio por unidad (decimal, ej: 15.50) - usar 0 si no aplica"],
        [""],
        ["CAMPOS OPCIONALES:"],
        ["  Fecha Fabricación:", "Formato: YYYY-MM-DD (Ej: 2024-01-15)"],
        ["  Número Contrato:", "Número del contrato de adquisición"],
        ["  Marca:", "Marca o laboratorio fabricante"],
        ["  Ubicación:", "Ubicación física en almacén (ej: Estante A1)"],
        ["  Centro:", "Nombre del centro donde se almacena el lote"],
        ["  Activo:", "Estado: Activo/Inactivo (default: Activo)"],
        [""],
        [f"CENTRO ASIGNADO:", centro.nombre if centro else "Se asignará automáticamente o desde columna Centro"],
        [""],
        ["NOTAS IMPORTANTES:"],
        ["• El producto debe existir antes de cargar lotes"],
        ["• Puede usar Clave, ID o Nombre del producto para identificarlo"],
        ["• El sistema detecta automáticamente la fila de encabezados"],
        ["• La cantidad_actual se inicializa igual a cantidad_inicial"],
        ["• El stock del producto se actualiza automáticamente"],
        ["• Las fechas deben estar en formato ISO: YYYY-MM-DD"],
        ["• Si el lote ya existe, se omitirá (no se duplica)"],
        ["• Elimine esta hoja de instrucciones antes de subir el archivo"],
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
