"""
Test de diagnóstico para verificar importación de Cantidad Contrato Global
"""
import pytest
from io import BytesIO
from openpyxl import Workbook
from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from core.models import Centro, Producto, Lote
from core.utils.excel_importer import importar_lotes_desde_excel

User = get_user_model()


@pytest.mark.django_db
def test_diagnostico_ccg_importacion():
    """
    Verificar que Cantidad Contrato Global se importe correctamente desde Excel
    """
    # Setup
    admin = User.objects.create_user(
        username='admin_test',
        email='admin@test.com',
        password='test123',
        is_staff=True,
        is_superuser=True
    )
    
    producto = Producto.objects.create(
        id=615,
        clave="615",
        nombre="PARACETAMOL",
        presentacion="500 MG",
        activo=True
    )
    
    # Crear Excel con CCG
    wb = Workbook()
    ws = wb.active
    
    # Headers (EXACTOS como en la plantilla)
    headers = [
        "Clave Producto",
        "Nombre Producto",
        "Número Lote",
        "Fecha Recepción",
        "Fecha Caducidad",
        "Cantidad Inicial",
        "Cantidad Contrato Lote",
        "Cantidad Contrato Global",
        "Precio Unitario",
        "Número Contrato",
        "Marca",
        "Activo"
    ]
    ws.append(headers)
    
    # Datos de prueba con CCG
    fecha_cad = (date.today() + timedelta(days=365)).strftime('%Y-%m-%d')
    fecha_rec = date.today().strftime('%Y-%m-%d')
    
    # 3 lotes del mismo producto con CCG = 1000
    filas = [
        ["615", "PARACETAMOL", "LOTE-TEST-001", fecha_rec, fecha_cad, 
         300, 300, 1000, 15.50, "CONT-2026-TEST", "Lab Test", "Activo"],
        ["615", "PARACETAMOL", "LOTE-TEST-002", fecha_rec, fecha_cad,
         250, 250, 1000, 15.50, "CONT-2026-TEST", "Lab Test", "Activo"],
        ["615", "PARACETAMOL", "LOTE-TEST-003", fecha_rec, fecha_cad,
         200, 200, 1000, 15.50, "CONT-2026-TEST", "Lab Test", "Activo"],
    ]
    
    for fila in filas:
        ws.append(fila)
    
    # Guardar en BytesIO
    excel_file = BytesIO()
    wb.save(excel_file)
    excel_file.seek(0)
    
    # Importar
    print("\n" + "="*70)
    print("🧪 TEST DE DIAGNÓSTICO: Importación CCG")
    print("="*70)
    
    resultado = importar_lotes_desde_excel(excel_file, admin, centro_id=None)
    
    print(f"\n📊 Resultado Importación:")
    print(f"   Tipo: {type(resultado)}")
    print(f"   Contenido: {resultado}")
    
    # El resultado puede ser dict o objeto
    if isinstance(resultado, dict):
        creados = resultado.get('creados', 0)
        actualizados = resultado.get('actualizados', 0)
        errores = resultado.get('errores', [])
    else:
        creados = resultado.creados
        actualizados = resultado.actualizados
        errores = resultado.errores
    
    print(f"   Creados: {creados}")
    print(f"   Actualizados: {actualizados}")
    print(f"   Errores: {len(errores)}")
    
    if errores:
        print(f"\n❌ Errores encontrados:")
        for err in errores[:5]:
            print(f"   - {err}")
    
    # Verificar lotes creados
    lotes = Lote.objects.filter(producto=producto, activo=True).order_by('numero_lote')
    
    print(f"\n📦 Lotes creados: {lotes.count()}")
    
    for lote in lotes:
        print(f"\n   Lote: {lote.numero_lote}")
        print(f"   ├─ cantidad_inicial: {lote.cantidad_inicial}")
        print(f"   ├─ cantidad_contrato: {lote.cantidad_contrato}")
        print(f"   ├─ cantidad_contrato_global: {lote.cantidad_contrato_global}")
        print(f"   ├─ numero_contrato: {lote.numero_contrato}")
        print(f"   └─ marca: {lote.marca}")
    
    # Assertions
    assert lotes.count() == 3, f"Debe haber 3 lotes, hay {lotes.count()}"
    
    for lote in lotes:
        ccg = lote.cantidad_contrato_global
        print(f"\n🔍 Verificando CCG del lote {lote.numero_lote}: {ccg}")
        
        if ccg is None:
            print(f"   ❌ CCG es NULL - PROBLEMA DETECTADO")
            print(f"   Datos del lote completos:")
            print(f"   {vars(lote)}")
        else:
            print(f"   ✅ CCG está presente: {ccg}")
        
        assert ccg is not None, \
            f"Lote {lote.numero_lote} debe tener cantidad_contrato_global, pero es NULL"
        assert ccg == 1000, \
            f"Lote {lote.numero_lote} debe tener CCG=1000, tiene {ccg}"
    
    print("\n" + "="*70)
    print("✅ TEST COMPLETADO CON ÉXITO")
    print("="*70)
    
    return True


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
