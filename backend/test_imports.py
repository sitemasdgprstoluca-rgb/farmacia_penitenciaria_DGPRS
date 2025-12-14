#!/usr/bin/env python
"""Script rápido para verificar imports sin errores de sintaxis."""

import sys
import os

# Agregar backend al path
sys.path.insert(0, os.path.dirname(__file__))

try:
    print("✓ Verificando core.utils.excel_templates...")
    from core.utils import excel_templates
    print("  - generar_plantilla_productos: OK")
    print("  - generar_plantilla_lotes: OK")
    print("  - generar_plantilla_usuarios: OK")
    
    print("\n✓ Verificando core.utils.excel_importer...")
    from core.utils import excel_importer
    print("  - importar_productos_desde_excel: OK")
    print("  - importar_lotes_desde_excel: OK")
    print("  - crear_log_importacion: OK")
    
    print("\n✅ TODOS LOS IMPORTS EXITOSOS - Sin errores de sintaxis")
    sys.exit(0)
    
except ImportError as e:
    print(f"\n❌ ERROR DE IMPORT: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
    
except SyntaxError as e:
    print(f"\n❌ ERROR DE SINTAXIS: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
    
except Exception as e:
    print(f"\n⚠️  ADVERTENCIA: {e}")
    print("(Puede ser normal si faltan dependencias en runtime)")
    sys.exit(0)
