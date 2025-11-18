#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para corregir todos los encoding errors del proyecto
Reemplaza caracteres corruptos por sus equivalentes correctos en español
"""

import os
import re
from pathlib import Path

# Mapeo de patrones corruptos a caracteres correctos
ENCODING_FIXES = {
    # Nuevos patrones encontrados
    r' ⢢⬡⢢⬡⬦⢢⬡⬡⢢⬡⬡⦾': '📦',  # Emoji de paquete
    r' ⢢⬡ó': '¿',  # Signo de interrogación
    r' ⢢⬡⢢⬡⬦⢢⬡⬡': '✓',  # Checkmark
    r'ií': 'ió',  # Error de doble í
    r'í ': 'á ',  # Espacio después de í que debería ser á
    
    # Vocales con acento
    r' ⢢ ⬢⢢⬡⬡': 'í',  # í con espacios
    r'⢢ ⬢⢢⬡⬡': 'í',   # í sin espacios iniciales
    r' ⦡⢢⬡⬡': 'ó',     # ó alternativo
    r'⦡⢢⬡⬡': 'ó',      # ó
    r' ⢢⬡⢢⬡⬡⢢⬡⬡': 'ó', # ó con espacios
    r'⢢⬡⢢⬡⬡⢢⬡⬡': 'ó',  # ó triple
    
    # Símbolos especiales
    r' ⢢⬡⦡⢢⬡⬡': '¿',   # ¿ con espacio
    r'⢢⬡⦡⢢⬡⬡': '¿',    # ¿
    r' ⢢⬡⢢⬡⬡⢢⬡⬡s ': '⚠',  # ⚠ (advertencia)
    r'⢢⬡⢢⬡⬡⢢⬡⬡s ': '⚠',   # ⚠
    r' ⢢⬡⢢⬡⬡⢢⬡⬡o"': '✓',   # ✓ (checkmark)
    r'⢢⬡⢢⬡⬡⢢⬡⬡o"': '✓',    # ✓
    r' ⢢⬡⢢⬡⬡⢢⬡⬡': '-',     # guión/dash
    r'⢢⬡⢢⬡⬡⢢⬡⬡': '-',      # guión
    
    # Letras especiales
    r'⢢ ⬢⢢⬡⬡⦢': 'Ó',        # Ó mayúscula
    r' ⢢ ⬢⢢⬡⬡': 'í',         # í
    r'⢢ ⬢⢢⬡': 'í',            # í variante
    
    # Patrones comunes en palabras
    r'Cr ⢢ ⬢⢢⬡⬡tico': 'Crítico',
    r'Pr ⢢ ⬢⢢⬡⬡ximo': 'Próximo',
    r'Gesti ⢢⬡⢢⬡⬡⢢⬡⬡n': 'Gestión',
    r'Gesti ⢢ ⬢⢢⬡⬡n': 'Gestión',
    r'P ⢢⬡⢢⬡⬡⢢⬡⬡gina': 'Página',
    r'sesi ⢢ ⬢⢢⬡⬡n': 'sesión',
    r'descripci ⢢ ⬢⢢⬡⬡n': 'descripción',
    r'Descripci ⢢ ⬢⢢⬡⬡n': 'Descripción',
    r'requisici ⢢ ⬢⢢⬡⬡n': 'requisición',
    r'Requisici ⢢ ⬢⢢⬡⬡n': 'Requisición',
    r'acci ⢢ ⬢⢢⬡⬡n': 'acción',
    r'Acci ⢢ ⬢⢢⬡⬡n': 'Acción',
    r'informaci ⢢ ⬢⢢⬡⬡n': 'información',
    r'Informaci ⢢ ⬢⢢⬡⬡n': 'Información',
    r'autorizaci ⢢ ⬢⢢⬡⬡n': 'autorización',
    r'Importaci ⢢ ⬢⢢⬡⬡n': 'Importación',
    r'Expiraci ⢢ ⬢⢢⬡⬡n': 'Expiración',
    r'Paginaci ⢢ ⬢⢢⬡⬡n': 'Paginación',
    r'creaci ⢢ ⬢⢢⬡⬡n': 'creación',
    r'conexi ⢢ ⬢⢢⬡⬡n': 'conexión',
    r'Atenci ⢢ ⬢⢢⬡⬡n': 'Atención',
    r'Anticipaci ⢢ ⬢⢢⬡⬡n': 'Anticipación',
    
    # Números y símbolos
    r'N ⢢ ⬢⢢⬡⬡mero': 'Número',
    r'n ⢢ ⬢⢢⬡⬡mero': 'número',
    r'C ⢢ ⬢⢢⬡⬡digo': 'Código',
    r'c ⢢ ⬢⢢⬡⬡digo': 'código',
    r'C ⢢ ⬢⢢⬡⬡⦢DIGO': 'CÓDIGO',
    r'Tel ⢢ ⬢⢢⬡⬡fono': 'Teléfono',
    r'Direcci ⢢ ⬢⢢⬡⬡n': 'Dirección',
    r'direcci ⢢ ⬢⢢⬡⬡n': 'dirección',
    
    # Días
    r'd ⢢ ⬢⢢⬡⬡as': 'días',
    r'D ⢢ ⬢⢢⬡⬡as': 'Días',
    
    # Palabras específicas
    r'B ⢢ ⬢⢢⬡⬡squeda': 'Búsqueda',
    r'b ⢢ ⬢⢢⬡⬡squeda': 'búsqueda',
    r'M ⢢ ⬢⢢⬡⬡dulo': 'Módulo',
    r'm ⢢ ⬢⢢⬡⬡dulo': 'módulo',
    r'auditor ⢢ ⬢⢢⬡⬡a': 'auditoría',
    r'Auditor ⢢ ⬢⢢⬡⬡a': 'Auditoría',
    r'M ⢢ ⬢⢢⬡⬡xico': 'México',
    r'Contrase ⢢ ⬢⢢⬡⬡a': 'Contraseña',
    r'contrase ⢢ ⬢⢢⬡⬡a': 'contraseña',
    r'contrase ña': 'contraseña',
    r'Subsecretar ⢢ ⬢⢢⬡⬡a': 'Subsecretaría',
    r'configuraci ⢢ ⬢⢢⬡⬡n': 'configuración',
    
    # Adjetivos
    r'm ⢢ ⬢⢢⬡⬡nimo': 'mínimo',
    r'M ⢢ ⬢⢢⬡⬡nimo': 'Mínimo',
    r'Stock m ⢢ ⬢⢢⬡⬡nimo': 'Stock mínimo',
    r'pr ⢢ ⬢⢢⬡⬡ximo': 'próximo',
    r'pr ⢢ ⬢⢢⬡⬡ximos': 'próximos',
    r'v ⢢ ⬢⢢⬡⬡lida': 'válida',
    r' ⢢ ⬢⢢⬡⬦ltimos': 'Últimos',
    r'may ⢢ ⬢⢢⬡⬡sculas': 'mayúsculas',
    r'autom ⢢ ⬢⢢⬡⬡ticamente': 'automáticamente',
    r' ⢢ ⬢⢢⬡⬦nico': 'único',
    r'estar ⢢ ⬢⢢⬡⬡n': 'estarán',
    r'aparecer ⢢ ⬢⢢⬡⬡n': 'aparecerán',
    r'afectar ⢢ ⬢⢢⬡⬡': 'afectará',
    r'convertir ⢢ ⬢⢢⬡⬡': 'convertirá',
    r'quedar ⢢ ⬢⢢⬡⬡': 'quedará',
    
    # Verbos
    r'est ⢢ ⬢⢢⬡⬡': 'está',
    r'Est ⢢ ⬢⢢⬡⬡': 'Está',
    r' ⢢⬡⦡⢢⬡⬡Est ⢢ ⬢⢢⬡⬡': '¿Está',
    r' ⢢⬡⦡⢢⬡⬡Confirma': '¿Confirma',
    
    # Nombres propios
    r'Mar ⢢ ⬢⢢⬡⬡a': 'María',
    r'Garc ⢢ ⬢⢢⬡⬡a': 'García',
    r'Hern ⢢ ⬢⢢⬡⬡ndez': 'Hernández',
    r'Mart ⢢ ⬢⢢⬡⬡nez': 'Martínez',
    
    # Medicamentos (mock data)
    r'c ⢢ ⬢⢢⬡⬡psulas': 'cápsulas',
    r'et ⢢ ⬢⢢⬡⬡lico': 'etílico',
    r's ⢢ ⬢⢢⬡⬡dico': 'sódico',
    
    # Símbolos en comentarios
    r' ⢢⬡⢢⬡⬡⢢⬡⬡o\.': 'No.',
    r'â¢¢â¬¡â¢¢â¬¡â¬¡â¢¢â¬¡â¬¡': '',  # Garbage al inicio de archivos
    
    # Más patrones de símbolos
    r'm ⢢ ⬢⢢⬡⬡s': 'más',
    r'A ⢢ ⬢⢢⬡⬦n': 'Aún',
}

def fix_encoding_in_file(file_path):
    """Corrige encoding errors en un archivo"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes_made = 0
        
        # Aplicar todas las correcciones
        for pattern, replacement in ENCODING_FIXES.items():
            old_content = content
            content = re.sub(pattern, replacement, content)
            if content != old_content:
                changes_made += content.count(replacement) - old_content.count(replacement)
        
        # Solo escribir si hubo cambios
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return changes_made
        
        return 0
    
    except Exception as e:
        print(f"❌ Error en {file_path}: {e}")
        return 0

def main():
    """Procesa todos los archivos .jsx en el proyecto"""
    project_root = Path(r"c:\Users\Alexander Z\OneDrive\Documents\Proyectos_Code\farmacia_penitenciaria")
    frontend_path = project_root / "inventario-front" / "src"
    
    total_files = 0
    total_changes = 0
    
    print("🔧 Iniciando corrección masiva de encoding...\n")
    
    # Procesar todos los archivos .jsx
    for jsx_file in frontend_path.rglob("*.jsx"):
        changes = fix_encoding_in_file(jsx_file)
        if changes > 0:
            total_files += 1
            total_changes += changes
            print(f"✅ {jsx_file.name}: {changes} correcciones")
    
    print(f"\n{'='*60}")
    print(f"✨ COMPLETADO")
    print(f"{'='*60}")
    print(f"📁 Archivos corregidos: {total_files}")
    print(f"🔧 Total de correcciones: {total_changes}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
