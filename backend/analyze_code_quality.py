"""
Script para analizar errores de sintaxis, coherencia y duplicados en el código
Ejecutar desde: backend/
"""

import os
import sys
import ast
import json
from pathlib import Path
from collections import defaultdict
import hashlib

class CodeAnalyzer:
    def __init__(self, root_dir):
        self.root_dir = Path(root_dir)
        self.errors = []
        self.warnings = []
        self.duplicates = []
        self.stats = {
            'total_files': 0,
            'syntax_errors': 0,
            'coherence_issues': 0,
            'duplicate_blocks': 0
        }
    
    def analyze_all(self):
        """Analiza todos los archivos Python en el directorio"""
        print(f"🔍 Analizando código en: {self.root_dir}")
        print("=" * 80)
        
        # Buscar todos los archivos .py
        py_files = list(self.root_dir.rglob('*.py'))
        self.stats['total_files'] = len(py_files)
        
        print(f"📁 Archivos Python encontrados: {len(py_files)}\n")
        
        for py_file in py_files:
            # Ignorar migraciones y __pycache__
            if '__pycache__' in str(py_file) or 'migrations' in str(py_file):
                continue
            
            self.analyze_file(py_file)
        
        self.find_duplicates(py_files)
        self.print_report()
    
    def analyze_file(self, filepath):
        """Analiza un archivo Python individual"""
        rel_path = filepath.relative_to(self.root_dir)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 1. Verificar sintaxis Python
            try:
                ast.parse(content)
            except SyntaxError as e:
                self.errors.append({
                    'file': str(rel_path),
                    'line': e.lineno,
                    'type': 'SYNTAX_ERROR',
                    'message': f"Error de sintaxis: {e.msg}",
                    'severity': 'CRITICAL'
                })
                self.stats['syntax_errors'] += 1
                print(f"❌ SYNTAX ERROR: {rel_path}:{e.lineno} - {e.msg}")
                return
            
            # 2. Verificar coherencia (análisis AST)
            tree = ast.parse(content)
            self.check_coherence(tree, filepath, rel_path)
            
        except UnicodeDecodeError:
            self.errors.append({
                'file': str(rel_path),
                'type': 'ENCODING_ERROR',
                'message': 'Error de codificación (no UTF-8)',
                'severity': 'HIGH'
            })
            print(f"⚠️  ENCODING ERROR: {rel_path}")
        except Exception as e:
            self.errors.append({
                'file': str(rel_path),
                'type': 'UNKNOWN_ERROR',
                'message': str(e),
                'severity': 'MEDIUM'
            })
            print(f"⚠️  ERROR: {rel_path} - {e}")
    
    def check_coherence(self, tree, filepath, rel_path):
        """Verifica problemas de coherencia en el código"""
        
        # Detectar imports duplicados
        imports = defaultdict(list)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports[alias.name].append(node.lineno)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for alias in node.names:
                        key = f"{node.module}.{alias.name}"
                        imports[key].append(node.lineno)
        
        # Reportar imports duplicados
        for imp, lines in imports.items():
            if len(lines) > 1:
                self.warnings.append({
                    'file': str(rel_path),
                    'lines': lines,
                    'type': 'DUPLICATE_IMPORT',
                    'message': f"Import duplicado: {imp} en líneas {lines}",
                    'severity': 'LOW'
                })
                self.stats['coherence_issues'] += 1
        
        # Detectar funciones/clases duplicadas
        names = defaultdict(list)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                names[node.name].append(node.lineno)
        
        for name, lines in names.items():
            if len(lines) > 1:
                self.warnings.append({
                    'file': str(rel_path),
                    'lines': lines,
                    'type': 'DUPLICATE_DEFINITION',
                    'message': f"Definición duplicada: {name} en líneas {lines}",
                    'severity': 'MEDIUM'
                })
                self.stats['coherence_issues'] += 1
        
        # Detectar variables no usadas (solo en funciones)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self.check_unused_variables(node, rel_path)
    
    def check_unused_variables(self, func_node, rel_path):
        """Detecta variables definidas pero no usadas en una función"""
        assigned = set()
        used = set()
        
        for node in ast.walk(func_node):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        assigned.add(target.id)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                used.add(node.id)
        
        unused = assigned - used - {'_'}  # Ignorar '_'
        if unused:
            self.warnings.append({
                'file': str(rel_path),
                'line': func_node.lineno,
                'type': 'UNUSED_VARIABLE',
                'message': f"Variables no usadas en {func_node.name}: {', '.join(unused)}",
                'severity': 'LOW'
            })
    
    def find_duplicates(self, py_files):
        """Encuentra bloques de código duplicados"""
        print("\n🔎 Buscando código duplicado...")
        
        code_hashes = defaultdict(list)
        
        for py_file in py_files:
            if '__pycache__' in str(py_file) or 'migrations' in str(py_file):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Analizar bloques de 5+ líneas
                for i in range(len(lines) - 4):
                    block = ''.join(lines[i:i+5]).strip()
                    if len(block) > 100:  # Solo bloques significativos
                        block_hash = hashlib.md5(block.encode()).hexdigest()
                        code_hashes[block_hash].append({
                            'file': py_file.relative_to(self.root_dir),
                            'start_line': i + 1
                        })
            except:
                pass
        
        # Reportar duplicados
        for hash_val, locations in code_hashes.items():
            if len(locations) > 1:
                self.duplicates.append({
                    'locations': [str(loc['file']) + f":{loc['start_line']}" for loc in locations],
                    'count': len(locations)
                })
                self.stats['duplicate_blocks'] += 1
    
    def print_report(self):
        """Imprime el reporte final"""
        print("\n" + "=" * 80)
        print("📊 REPORTE DE ANÁLISIS DE CÓDIGO")
        print("=" * 80)
        
        print(f"\n📈 Estadísticas:")
        print(f"  • Archivos analizados: {self.stats['total_files']}")
        print(f"  • Errores de sintaxis: {self.stats['syntax_errors']}")
        print(f"  • Problemas de coherencia: {self.stats['coherence_issues']}")
        print(f"  • Bloques duplicados: {self.stats['duplicate_blocks']}")
        
        # Errores críticos
        critical_errors = [e for e in self.errors if e.get('severity') == 'CRITICAL']
        if critical_errors:
            print(f"\n❌ ERRORES CRÍTICOS ({len(critical_errors)}):")
            for err in critical_errors[:10]:  # Mostrar primeros 10
                print(f"  • {err['file']}:{err.get('line', '?')} - {err['message']}")
        
        # Warnings
        if self.warnings:
            print(f"\n⚠️  ADVERTENCIAS ({len(self.warnings)}):")
            # Agrupar por tipo
            by_type = defaultdict(list)
            for w in self.warnings:
                by_type[w['type']].append(w)
            
            for wtype, items in by_type.items():
                print(f"\n  {wtype} ({len(items)}):")
                for item in items[:5]:  # Mostrar primeros 5 de cada tipo
                    print(f"    - {item['file']} - {item['message']}")
        
        # Duplicados
        if self.duplicates:
            print(f"\n🔄 CÓDIGO DUPLICADO ({len(self.duplicates)} bloques):")
            for dup in self.duplicates[:5]:  # Mostrar primeros 5
                print(f"  • Encontrado en {dup['count']} ubicaciones:")
                for loc in dup['locations']:
                    print(f"    - {loc}")
        
        # Guardar reporte JSON
        report_file = self.root_dir / 'code_analysis_report.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                'stats': self.stats,
                'errors': self.errors,
                'warnings': self.warnings,
                'duplicates': self.duplicates
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Reporte completo guardado en: {report_file}")
        
        # Resumen final
        print("\n" + "=" * 80)
        if self.stats['syntax_errors'] == 0:
            print("✅ No se encontraron errores de sintaxis")
        else:
            print(f"❌ Se encontraron {self.stats['syntax_errors']} errores de sintaxis que deben corregirse")
        
        if self.stats['coherence_issues'] > 0:
            print(f"⚠️  Se encontraron {self.stats['coherence_issues']} problemas de coherencia")
        
        if self.stats['duplicate_blocks'] > 0:
            print(f"🔄 Se encontraron {self.stats['duplicate_blocks']} bloques de código duplicado")
        
        print("=" * 80)


if __name__ == '__main__':
    # Ejecutar desde el directorio backend
    current_dir = Path(__file__).parent
    analyzer = CodeAnalyzer(current_dir)
    analyzer.analyze_all()
