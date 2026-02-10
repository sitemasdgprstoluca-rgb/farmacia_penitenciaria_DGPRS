#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para transformar datos de productos desde Excel al formato compatible con Supabase.

Uso:
    python transformar_productos_supabase.py ruta/al/archivo.xlsx
    
Genera:
    - productos_supabase.csv: CSV limpio para importar en Supabase
    - productos_supabase.sql: Script SQL con INSERT statements
"""

import pandas as pd
import re
import sys
from datetime import datetime

# Mapeo de unidades de medida válidas
UNIDADES_VALIDAS = {
    'PIEZA', 'CAJA', 'FRASCO', 'SOBRE', 'AMPOLLETA', 
    'TABLETA', 'CAPSULA', 'ML', 'GR'
}

# Mapeo de alias para normalizar unidades
UNIDADES_ALIAS = {
    'pza': 'PIEZA', 'pz': 'PIEZA', 'pieza': 'PIEZA', 'piezas': 'PIEZA',
    'caja': 'CAJA', 'cajas': 'CAJA', 'cj': 'CAJA',
    'frasco': 'FRASCO', 'fco': 'FRASCO', 'frascos': 'FRASCO',
    'sobre': 'SOBRE', 'sobres': 'SOBRE', 'sob': 'SOBRE',
    'ampolleta': 'AMPOLLETA', 'amp': 'AMPOLLETA', 'ampolletas': 'AMPOLLETA',
    'tableta': 'TABLETA', 'tab': 'TABLETA', 'tabl': 'TABLETA', 'tabletas': 'TABLETA',
    'capsula': 'CAPSULA', 'cap': 'CAPSULA', 'caps': 'CAPSULA', 'capsulas': 'CAPSULA',
    'ml': 'ML', 'mililitro': 'ML', 'mililitros': 'ML',
    'gr': 'GR', 'g': 'GR', 'gramo': 'GR', 'gramos': 'GR',
}

# Categorías válidas
CATEGORIAS_VALIDAS = {
    'medicamento', 'material_curacion', 'insumo', 'equipo', 'otro'
}

# Mapeo de alias para categorías
CATEGORIAS_ALIAS = {
    'medicamento': 'medicamento',
    'medicamentos': 'medicamento',
    'farmaco': 'medicamento',
    'fármaco': 'medicamento',
    'generico': 'medicamento',
    'material': 'material_curacion',
    'material de curacion': 'material_curacion',
    'material curación': 'material_curacion',
    'curacion': 'material_curacion',
    'insumo': 'insumo',
    'insumos': 'insumo',
    'equipo': 'equipo',
    'equipos': 'equipo',
    'otro': 'otro',
    'otros': 'otro',
}

def extraer_unidad_base(texto):
    """
    Extrae la unidad de medida base de un texto como 'CAJA CON 7 OVULOS'.
    
    Retorna: (unidad_normalizada, texto_original)
    """
    if not texto or pd.isna(texto):
        return 'PIEZA', ''
    
    texto_str = str(texto).strip()
    texto_upper = texto_str.upper()
    
    # Buscar patrones comunes
    for unidad in ['CAJA', 'FRASCO', 'SOBRE', 'AMPOLLETA', 'TABLETA', 'CAPSULA', 'ENVASE', 'BOLSA', 'GOTERO']:
        if unidad in texto_upper:
            # Mapear a unidad válida
            if unidad in ['ENVASE', 'BOLSA', 'GOTERO']:
                return 'FRASCO', texto_str
            return unidad, texto_str
    
    # Si no encuentra nada, retornar PIEZA
    return 'PIEZA', texto_str

def normalizar_unidad(valor):
    """Normaliza una unidad de medida al código estándar."""
    if not valor or pd.isna(valor):
        return 'PIEZA'
    
    valor_str = str(valor).strip()
    valor_upper = valor_str.upper()
    valor_lower = valor_str.lower()
    
    # Si ya es válida
    if valor_upper in UNIDADES_VALIDAS:
        return valor_upper
    
    # Buscar en alias
    if valor_lower in UNIDADES_ALIAS:
        return UNIDADES_ALIAS[valor_lower]
    
    # Intentar extraer de texto largo
    unidad, _ = extraer_unidad_base(valor_str)
    return unidad

def normalizar_categoria(valor):
    """Normaliza una categoría al código estándar."""
    if not valor or pd.isna(valor):
        return 'medicamento'
    
    valor_str = str(valor).strip()
    valor_lower = valor_str.lower()
    
    # Si ya es válida
    if valor_lower in CATEGORIAS_VALIDAS:
        return valor_lower
    
    # Buscar en alias
    if valor_lower in CATEGORIAS_ALIAS:
        return CATEGORIAS_ALIAS[valor_lower]
    
    # Si contiene ciertas palabras clave
    if any(kw in valor_lower for kw in ['medic', 'farmac', 'generico', 'generic']):
        return 'medicamento'
    elif any(kw in valor_lower for kw in ['curac', 'gasa', 'venda']):
        return 'material_curacion'
    elif any(kw in valor_lower for kw in ['insum', 'supply']):
        return 'insumo'
    elif any(kw in valor_lower for kw in ['equip', 'aparato', 'device']):
        return 'equipo'
    
    # Por defecto
    return 'medicamento'

def convertir_booleano(valor):
    """Convierte valores a booleano de manera flexible."""
    if pd.isna(valor) or valor == '' or valor is None:
        return False
    
    if isinstance(valor, bool):
        return valor
    
    valor_str = str(valor).strip().lower()
    
    # Valores que se consideran True
    valores_true = ['si', 'sí', 'yes', 'y', 's', 'true', '1', 'x', 'activo']
    
    return valor_str in valores_true

def limpiar_texto(valor):
    """Limpia y normaliza texto."""
    if not valor or pd.isna(valor):
        return None
    
    texto = str(valor).strip()
    
    # Reemplazar caracteres problemáticos
    texto = texto.replace('\n', ' ').replace('\r', '')
    texto = re.sub(r'\s+', ' ', texto)  # Espacios múltiples a uno solo
    
    return texto if texto else None

def transformar_excel_a_supabase(archivo_excel, hoja=None):
    """
    Transforma un archivo Excel o CSV al formato compatible con Supabase.
    
    Args:
        archivo_excel: Ruta al archivo Excel o CSV
        hoja: Nombre de la hoja (opcional, usa la primera por defecto)
    
    Returns:
        DataFrame con los datos transformados
    """
    print(f"📂 Leyendo archivo: {archivo_excel}")
    
    # Detectar tipo de archivo
    archivo_lower = archivo_excel.lower()
    
    # Leer según extensión
    if archivo_lower.endswith('.csv'):
        df = pd.read_csv(archivo_excel, encoding='utf-8')
    elif archivo_lower.endswith(('.xlsx', '.xls')):
        if hoja:
            df = pd.read_excel(archivo_excel, sheet_name=hoja)
        else:
            df = pd.read_excel(archivo_excel)
    else:
        # Intentar como CSV por defecto
        try:
            df = pd.read_csv(archivo_excel, encoding='utf-8')
        except:
            df = pd.read_excel(archivo_excel)
    
    print(f"✓ {len(df)} filas leídas")
    print(f"\nColumnas encontradas: {list(df.columns)}")
    
    # Mapeo de columnas posibles (flexibilidad en nombres)
    mapeo_columnas = {
        'clave': ['clave', 'codigo', 'código', 'code', 'id_producto'],
        'nombre': ['nombre', 'name', 'producto', 'descripcion_corta'],
        'descripcion': ['descripcion', 'descripción', 'description', 'desc'],
        'unidad_medida': ['unidad', 'unidad medida', 'unidad_medida', 'um', 'unit'],
        'categoria': ['categoria', 'categoría', 'tipo', 'category', 'cat'],
        'sustancia_activa': ['sustancia activa', 'sustancia_activa', 'sustancia ac', 'principio activo', 'active ingredient'],
        'presentacion': ['presentacion', 'presentación', 'presentation', 'formato'],
        'concentracion': ['concentracion', 'concentración', 'concentration', 'conc'],
        'via_administracion': ['via admin', 'via administracion', 'vía administración', 'via', 'route'],
        'stock_minimo': ['stock minimo', 'stock_minimo', 'stock mínim', 'min_stock', 'minimo'],
        'stock_actual': ['stock actual', 'stock_actual', 'stock', 'existencia'],
        'requiere_receta': ['requiere rec', 'requiere receta', 'requiere_receta', 'receta', 'prescription'],
        'es_controlado': ['controlado', 'es controlado', 'es_controlado', 'controlled'],
        'activo': ['activo', 'estado', 'active', 'status'],
    }
    
    # Detectar columnas automáticamente
    columnas_detectadas = {}
    for campo, posibles_nombres in mapeo_columnas.items():
        for col in df.columns:
            col_lower = str(col).lower().strip()
            if col_lower in [n.lower() for n in posibles_nombres]:
                columnas_detectadas[campo] = col
                break
    
    print(f"\n✓ Columnas detectadas: {columnas_detectadas}")
    
    # Crear DataFrame transformado
    datos_transformados = []
    errores = []
    
    for idx, row in df.iterrows():
        try:
            # Clave (requerida)
            clave = limpiar_texto(row.get(columnas_detectadas.get('clave', 'Clave'), None))
            if not clave:
                errores.append(f"Fila {idx + 2}: Clave vacía")
                continue
            
            # Nombre (requerido)
            nombre = limpiar_texto(row.get(columnas_detectadas.get('nombre', 'Nombre'), None))
            if not nombre:
                errores.append(f"Fila {idx + 2}: Nombre vacío")
                continue
            
            # Unidad de medida
            unidad_raw = row.get(columnas_detectadas.get('unidad_medida', 'Unidad'), 'PIEZA')
            unidad_medida = normalizar_unidad(unidad_raw)
            
            # Presentación (puede contener info de unidad también)
            presentacion_raw = row.get(columnas_detectadas.get('presentacion', 'Presentacion'), None)
            if presentacion_raw and not pd.isna(presentacion_raw):
                presentacion = limpiar_texto(presentacion_raw)
                # Si la unidad viene en presentación y no en unidad, extraerla
                if unidad_raw == 'PIEZA' or pd.isna(unidad_raw):
                    unidad_extraida, _ = extraer_unidad_base(presentacion)
                    if unidad_extraida != 'PIEZA':
                        unidad_medida = unidad_extraida
            else:
                presentacion = None
            
            # Categoría
            categoria_raw = row.get(columnas_detectadas.get('categoria', 'Categoria'), 'medicamento')
            categoria = normalizar_categoria(categoria_raw)
            
            # Sustancia activa
            sustancia_activa = limpiar_texto(row.get(columnas_detectadas.get('sustancia_activa', 'Sustancia Activa'), None))
            
            # Concentración
            concentracion = limpiar_texto(row.get(columnas_detectadas.get('concentracion', 'Concentracion'), None))
            
            # Vía de administración
            via_administracion = limpiar_texto(row.get(columnas_detectadas.get('via_administracion', 'Via Admin'), None))
            
            # Stock mínimo
            stock_minimo = row.get(columnas_detectadas.get('stock_minimo', 'Stock Minimo'), 10)
            try:
                stock_minimo = int(stock_minimo) if not pd.isna(stock_minimo) else 10
            except:
                stock_minimo = 10
            
            # Stock actual
            stock_actual = row.get(columnas_detectadas.get('stock_actual', 'Stock Actual'), 0)
            try:
                stock_actual = int(stock_actual) if not pd.isna(stock_actual) else 0
            except:
                stock_actual = 0
            
            # Requiere receta
            requiere_receta = convertir_booleano(row.get(columnas_detectadas.get('requiere_receta', 'Requiere Receta'), False))
            
            # Es controlado
            es_controlado = convertir_booleano(row.get(columnas_detectadas.get('es_controlado', 'Controlado'), False))
            
            # Activo
            activo = convertir_booleano(row.get(columnas_detectadas.get('activo', 'Activo'), True))
            
            # Descripción
            descripcion = limpiar_texto(row.get(columnas_detectadas.get('descripcion', 'Descripcion'), None))
            
            # Agregar registro
            datos_transformados.append({
                'clave': clave,
                'nombre': nombre,
                'descripcion': descripcion,
                'unidad_medida': unidad_medida,
                'categoria': categoria,
                'sustancia_activa': sustancia_activa,
                'presentacion': presentacion,
                'concentracion': concentracion,
                'via_administracion': via_administracion,
                'stock_minimo': stock_minimo,
                'stock_actual': stock_actual,
                'requiere_receta': requiere_receta,
                'es_controlado': es_controlado,
                'activo': activo,
            })
            
        except Exception as e:
            errores.append(f"Fila {idx + 2}: Error - {str(e)}")
    
    # Mostrar errores
    if errores:
        print(f"\n⚠️  Se encontraron {len(errores)} errores:")
        for error in errores[:10]:  # Mostrar solo los primeros 10
            print(f"  - {error}")
        if len(errores) > 10:
            print(f"  ... y {len(errores) - 10} más")
    
    print(f"\n✓ {len(datos_transformados)} productos transformados correctamente")
    
    return pd.DataFrame(datos_transformados)

def generar_csv(df, archivo_salida='productos_supabase.csv'):
    """Genera un archivo CSV compatible con Supabase."""
    print(f"\n💾 Generando CSV: {archivo_salida}")
    
    df.to_csv(archivo_salida, index=False, encoding='utf-8')
    
    print(f"✓ CSV generado correctamente")
    return archivo_salida

def generar_sql(df, archivo_salida='productos_supabase.sql'):
    """Genera un script SQL con INSERT statements."""
    print(f"\n💾 Generando SQL: {archivo_salida}")
    
    with open(archivo_salida, 'w', encoding='utf-8') as f:
        f.write("-- Script de inserción de productos generado automáticamente\n")
        f.write(f"-- Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"-- Total de productos: {len(df)}\n\n")
        
        for idx, row in df.iterrows():
            # Escapar valores NULL
            def escape_value(val):
                if pd.isna(val) or val is None or val == '':
                    return 'NULL'
                elif isinstance(val, bool):
                    return 'TRUE' if val else 'FALSE'
                elif isinstance(val, (int, float)):
                    return str(val)
                else:
                    # Escapar comillas simples
                    val_str = str(val).replace("'", "''")
                    return f"'{val_str}'"
            
            sql = f"""INSERT INTO productos (
    clave, nombre, descripcion, unidad_medida, categoria,
    sustancia_activa, presentacion, concentracion, via_administracion,
    stock_minimo, stock_actual, requiere_receta, es_controlado, activo
) VALUES (
    {escape_value(row['clave'])},
    {escape_value(row['nombre'])},
    {escape_value(row['descripcion'])},
    {escape_value(row['unidad_medida'])},
    {escape_value(row['categoria'])},
    {escape_value(row['sustancia_activa'])},
    {escape_value(row['presentacion'])},
    {escape_value(row['concentracion'])},
    {escape_value(row['via_administracion'])},
    {escape_value(row['stock_minimo'])},
    {escape_value(row['stock_actual'])},
    {escape_value(row['requiere_receta'])},
    {escape_value(row['es_controlado'])},
    {escape_value(row['activo'])}
);\n"""
            f.write(sql)
    
    print(f"✓ SQL generado correctamente")
    return archivo_salida

def main():
    """Función principal."""
    print("=" * 70)
    print("🔄 TRANSFORMADOR DE PRODUCTOS PARA SUPABASE")
    print("=" * 70)
    
    # Obtener archivo de entrada
    if len(sys.argv) < 2:
        print("\n❌ Error: Debes proporcionar la ruta al archivo Excel")
        print("\nUso:")
        print("  python transformar_productos_supabase.py ruta/al/archivo.xlsx")
        print("\nEjemplo:")
        print("  python transformar_productos_supabase.py productos.xlsx")
        sys.exit(1)
    
    archivo_excel = sys.argv[1]
    
    try:
        # Transformar datos
        df = transformar_excel_a_supabase(archivo_excel)
        
        # Generar CSV
        csv_file = generar_csv(df)
        
        # Generar SQL
        sql_file = generar_sql(df)
        
        print("\n" + "=" * 70)
        print("✅ TRANSFORMACIÓN COMPLETADA")
        print("=" * 70)
        print(f"\n📄 Archivos generados:")
        print(f"  1. {csv_file} - Para importar en Supabase usando 'Import data from CSV'")
        print(f"  2. {sql_file} - Para ejecutar en el SQL Editor de Supabase")
        print(f"\n📊 Estadísticas:")
        print(f"  - Total de productos: {len(df)}")
        print(f"  - Categorías: {df['categoria'].value_counts().to_dict()}")
        print(f"  - Unidades: {df['unidad_medida'].value_counts().to_dict()}")
        print(f"  - Controlados: {df['es_controlado'].sum()}")
        print(f"  - Requieren receta: {df['requiere_receta'].sum()}")
        
        print("\n📝 Pasos siguientes:")
        print("  1. Abre Supabase → Table Editor → productos")
        print("  2. Opción A: Click en 'Import data' → Selecciona productos_supabase.csv")
        print("  3. Opción B: SQL Editor → Pega el contenido de productos_supabase.sql")
        
    except FileNotFoundError:
        print(f"\n❌ Error: No se encontró el archivo '{archivo_excel}'")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
