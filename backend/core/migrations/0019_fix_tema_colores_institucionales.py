# Generated migration to fix institutional colors
from django.db import migrations


def actualizar_colores_institucionales(apps, schema_editor):
    """
    Actualiza todos los temas existentes para usar los colores 
    institucionales rojos en lugar de los azules anteriores.
    """
    TemaGlobal = apps.get_model('core', 'TemaGlobal')
    
    # Mapeo de colores antiguos (azul) a nuevos (rojo institucional)
    cambios_colores = {
        # Primarios
        'color_primario': ('#1e3a5f', '#9F2241'),
        'color_primario_hover': ('#15293f', '#6B1839'),
        # Secundarios
        'color_secundario': ('#3b82f6', '#424242'),
        'color_secundario_hover': ('#2563eb', '#2E2E2E'),
        # Fondos
        'color_fondo_sidebar': ('#1e3a5f', '#9F2241'),
        'color_fondo_header': ('#1e3a5f', '#9F2241'),
        # Links y focus
        'color_texto_links': ('#3b82f6', '#9F2241'),
        'color_borde_focus': ('#3b82f6', '#9F2241'),
        # Reportes
        'reporte_color_encabezado': ('#1e3a5f', '#9F2241'),
    }
    
    # Actualizar todos los temas existentes
    temas = TemaGlobal.objects.all()
    for tema in temas:
        modificado = False
        for campo, (color_viejo, color_nuevo) in cambios_colores.items():
            valor_actual = getattr(tema, campo, None)
            # Solo actualizar si tiene el color azul antiguo
            if valor_actual and valor_actual.lower() == color_viejo.lower():
                setattr(tema, campo, color_nuevo)
                modificado = True
        
        if modificado:
            tema.save()
            print(f"  Tema '{tema.nombre}' actualizado con colores institucionales")
    
    print(f"  Total de temas procesados: {temas.count()}")


def revertir_colores(apps, schema_editor):
    """
    Revierte los colores a los valores azules anteriores.
    """
    TemaGlobal = apps.get_model('core', 'TemaGlobal')
    
    # Mapeo inverso
    cambios_colores = {
        'color_primario': ('#9F2241', '#1e3a5f'),
        'color_primario_hover': ('#6B1839', '#15293f'),
        'color_secundario': ('#424242', '#3b82f6'),
        'color_secundario_hover': ('#2E2E2E', '#2563eb'),
        'color_fondo_sidebar': ('#9F2241', '#1e3a5f'),
        'color_fondo_header': ('#9F2241', '#1e3a5f'),
        'color_texto_links': ('#9F2241', '#3b82f6'),
        'color_borde_focus': ('#9F2241', '#3b82f6'),
        'reporte_color_encabezado': ('#9F2241', '#1e3a5f'),
    }
    
    temas = TemaGlobal.objects.all()
    for tema in temas:
        modificado = False
        for campo, (color_nuevo, color_viejo) in cambios_colores.items():
            valor_actual = getattr(tema, campo, None)
            if valor_actual and valor_actual.lower() == color_nuevo.lower():
                setattr(tema, campo, color_viejo)
                modificado = True
        
        if modificado:
            tema.save()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_audit5_contratos_reservas_recepcion'),
    ]

    operations = [
        migrations.RunPython(
            actualizar_colores_institucionales,
            revertir_colores,
        ),
    ]
