from django.db import migrations


def asignar_centro_a_lotes(apps, schema_editor):
    Lote = apps.get_model('core', 'Lote')
    Movimiento = apps.get_model('core', 'Movimiento')

    lotes_sin_centro = Lote.objects.filter(centro__isnull=True)
    for lote in lotes_sin_centro:
        mov = Movimiento.objects.filter(lote_id=lote.id, centro__isnull=False).order_by('-fecha').first()
        if mov and mov.centro_id:
            lote.centro_id = mov.centro_id
            lote.save(update_fields=['centro'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_lote_centro'),
    ]

    operations = [
        migrations.RunPython(asignar_centro_a_lotes, migrations.RunPython.noop),
    ]
