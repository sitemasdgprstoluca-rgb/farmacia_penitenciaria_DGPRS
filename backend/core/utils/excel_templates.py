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
    column_widths = [15, 45, 18, 15, 20, 25, 25, 20, 20, 18, 15, 12]
    
    for col_num, header in enumerate(headers, 1):
        ws.cell(row=1, column=col_num, value=header)
        if col_num <= len(column_widths):
            ws.column_dimensions[openpyxl.utils.get_column_letter(col_num)].width = column_widths[col_num - 1]
    
    aplicar_estilos_header(ws, len(headers))

    # ============================================================
    # FILAS DE EJEMPLO - ELIMINAR ANTES DE USAR CON DATOS REALES
    # Texto gris itálico para que sea obvio
    # ============================================================
    ejemplos = [
        ["PRUEBA001", "[EJEMPLO] Paracetamol 500mg - ELIMINAR", "CAJA", 50, "medicamento",
         "Paracetamol", "Tableta", "500 mg", "oral", "No", "No", "Activo"],
        ["PRUEBA002", "[EJEMPLO] Ibuprofeno 400mg - ELIMINAR", "FRASCO", 30, "medicamento",
         "Ibuprofeno", "Cápsula", "400 mg", "oral", "No", "No", "Activo"],
        ["PRUEBA003", "[EJEMPLO] Jeringa 10ml - ELIMINAR", "PIEZA", 100, "material_curacion",
         "", "", "", "", "No", "No", "Activo"],
    ]
    
    for ejemplo in ejemplos:
        ws.append(ejemplo)
    
    # Estilo para filas de ejemplo (gris claro, itálica)
    example_font = Font(italic=True, color="888888")
    for row_num in range(2, 2 + len(ejemplos)):
        for col in range(1, len(headers) + 1):
            cell = ws.cell(row=row_num, column=col)
            cell.font = example_font

    # Instrucciones en hoja separada
    ws_inst = wb.create_sheet("INSTRUCCIONES")
    instrucciones = [
        ["╔════════════════════════════════════════════════════════════════════╗"],
        ["║    INSTRUCCIONES PARA IMPORTACIÓN DE PRODUCTOS                    ║"],
        ["╚════════════════════════════════════════════════════════════════════╝"],
        [""],
        ["⚠️  IMPORTANTE: Las filas grises con [EJEMPLO] en la hoja 'Productos' son de muestra."],
        ["    ELIMÍNELAS antes de cargar sus datos reales."],
        [""],
        ["────────────────────────────────────────────────────────────────────────"],
        ["COLUMNAS REQUERIDAS (obligatorias):"],
        ["────────────────────────────────────────────────────────────────────────"],
        ["• Clave      - Código único del producto (ej: 001, MED001, ABC123)"],
        ["• Nombre     - Nombre completo del producto"],
        [""],
        ["────────────────────────────────────────────────────────────────────────"],
        ["COLUMNAS OPCIONALES:"],
        ["────────────────────────────────────────────────────────────────────────"],
        ["• Unidad         - CAJA, PIEZA, FRASCO, SOBRE, TABLETA, etc. (default: PIEZA)"],
        ["• Stock Minimo   - Cantidad mínima para alertas (default: 10)"],
        ["• Categoria      - medicamento, material_curacion, insumo (default: medicamento)"],
        ["• Sustancia Activa - Principio activo del medicamento"],
        ["• Presentacion   - Forma farmacéutica (tableta, cápsula, jarabe, etc.)"],
        ["• Concentracion  - Dosis (ej: 500 mg, 10 ml)"],
        ["• Via Admin      - oral, intravenosa, tópica, etc."],
        ["• Requiere Receta - Sí / No (default: No)"],
        ["• Controlado     - Sí / No (default: No)"],
        ["• Estado         - Activo / Inactivo (default: Activo)"],
        [""],
        ["────────────────────────────────────────────────────────────────────────"],
        ["NOTAS:"],
        ["────────────────────────────────────────────────────────────────────────"],
        ["• Si la CLAVE ya existe, el producto se ACTUALIZARÁ con los nuevos datos."],
        ["• Si la CLAVE no existe, se CREARÁ un nuevo producto."],
        ["• La Unidad acepta texto libre: 'CAJA CON 7 OVULOS', 'GOTERO CON 15 ML'"],
        ["• Valores booleanos: Sí/Si/Yes/True/1/Activo o No/False/0/Inactivo"],
        ["• Máximo 5000 productos por archivo."],
        ["• Tamaño máximo de archivo: 10 MB."],
        ["• Formatos aceptados: .xlsx, .xls"],
        [""],
    ]
    
    for row_data in instrucciones:
        ws_inst.append(row_data)
    
    ws_inst.column_dimensions['A'].width = 80

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
    - Activo: Estado del lote (opcional, default Activo)
    
    NOTA: La ubicación se asigna automáticamente como "Almacén Central"
    y el centro queda NULL (representa Farmacia Central).
    """
    from datetime import date, timedelta
    
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
        "Activo"
    ]

    column_widths = [15, 40, 20, 18, 18, 16, 15, 18, 35, 12]
    
    for col_num, header in enumerate(headers, 1):
        ws.cell(row=1, column=col_num, value=header)
        if col_num <= len(column_widths):
            ws.column_dimensions[openpyxl.utils.get_column_letter(col_num)].width = column_widths[col_num - 1]
    
    aplicar_estilos_header(ws, len(headers))

    # ============================================================
    # FILAS DE EJEMPLO - ELIMINAR ANTES DE USAR CON DATOS REALES
    # Texto gris itálico para que sea obvio
    # ============================================================
    fecha_cad = (date.today() + timedelta(days=365)).strftime('%Y-%m-%d')
    fecha_fab = date.today().strftime('%Y-%m-%d')
    
    ejemplos = [
        ["PRUEBA001", "[EJEMPLO] Paracetamol - ELIMINAR", "LOTE-PRUEBA-001",
         fecha_fab, fecha_cad, 100, 15.50, "CONT-PRUEBA-001",
         "[EJEMPLO] Laboratorio - ELIMINAR", "Activo"],
        ["PRUEBA002", "[EJEMPLO] Ibuprofeno - ELIMINAR", "LOTE-PRUEBA-002",
         fecha_fab, fecha_cad, 50, 18.75, "CONT-PRUEBA-002",
         "[EJEMPLO] Farmacéutica - ELIMINAR", "Activo"],
        ["PRUEBA003", "[EJEMPLO] Jeringa - ELIMINAR", "LOTE-PRUEBA-003",
         "", fecha_cad, 200, 5.00, "",
         "[EJEMPLO] Proveedor - ELIMINAR", "Activo"],
    ]
    
    for ejemplo in ejemplos:
        ws.append(ejemplo)
    
    # Estilo para filas de ejemplo (gris claro, itálica - sin fondo de color)
    example_font = Font(italic=True, color="888888")
    for row_num in range(2, 2 + len(ejemplos)):
        for col in range(1, len(headers) + 1):
            cell = ws.cell(row=row_num, column=col)
            cell.font = example_font

    # Instrucciones
    ws_inst = wb.create_sheet("INSTRUCCIONES")
    instrucciones = [
        ["╔════════════════════════════════════════════════════════════════════╗"],
        ["║    INSTRUCCIONES PARA IMPORTACIÓN DE LOTES                        ║"],
        ["╚════════════════════════════════════════════════════════════════════╝"],
        [""],
        ["⚠️  IMPORTANTE: Las filas de ejemplo (texto gris con [EJEMPLO]) son de muestra."],
        ["    ELIMÍNELAS antes de cargar sus datos reales."],
        [""],
        ["────────────────────────────────────────────────────────────────────────"],
        ["COLUMNAS REQUERIDAS (obligatorias):"],
        ["────────────────────────────────────────────────────────────────────────"],
        ["• Clave Producto  - Clave del producto (debe existir en el sistema)"],
        ["• Número Lote     - Identificador único del lote"],
        ["• Fecha Caducidad - Formato: YYYY-MM-DD (ej: 2026-12-31)"],
        ["• Cantidad Inicial - Cantidad de unidades recibidas"],
        [""],
        ["────────────────────────────────────────────────────────────────────────"],
        ["COLUMNAS OPCIONALES:"],
        ["────────────────────────────────────────────────────────────────────────"],
        ["• Nombre Producto   - Referencia visual (el sistema busca por clave)"],
        ["• Fecha Fabricación - Formato: YYYY-MM-DD"],
        ["• Precio Unitario   - Precio por unidad (default: 0)"],
        ["• Número Contrato   - Referencia del contrato de adquisición"],
        ["• Marca             - Laboratorio o fabricante"],
        ["• Activo            - Activo/Inactivo (default: Activo)"],
        [""],
        ["────────────────────────────────────────────────────────────────────────"],
        ["NOTAS:"],
        ["────────────────────────────────────────────────────────────────────────"],
        ["• Los lotes se asignan automáticamente al Almacén Central (FARMACIA)."],
        ["• El PRODUCTO debe existir antes de importar lotes."],
        ["• Si el lote ya existe (mismo producto + número de lote), se ACTUALIZA."],
        ["• La cantidad_actual se inicializa igual a cantidad_inicial."],
        ["• El stock del producto se actualiza automáticamente."],
        ["• Fechas aceptadas: YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY"],
        ["• Máximo 5000 lotes por archivo."],
        ["• Tamaño máximo de archivo: 10 MB."],
        [""],
    ]
    
    for row_data in instrucciones:
        ws_inst.append(row_data)
    
    ws_inst.column_dimensions['A'].width = 80

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
