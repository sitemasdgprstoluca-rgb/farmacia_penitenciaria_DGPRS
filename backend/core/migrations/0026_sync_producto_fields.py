# Generated manually to sync Producto model with existing migrations
# This migration adds all missing fields that exist in models.py but not in migrations

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0025_fix_notificacion_fields'),
    ]

    operations = [
        # Add 'nombre' field to Producto (required field)
        migrations.AddField(
            model_name='producto',
            name='nombre',
            field=models.CharField(max_length=500, default='Sin nombre'),
            preserve_default=False,
        ),
        # Add 'nombre_comercial' field (optional)
        migrations.AddField(
            model_name='producto',
            name='nombre_comercial',
            field=models.CharField(max_length=200, blank=True, null=True),
        ),
        # Add 'categoria' field 
        migrations.AddField(
            model_name='producto',
            name='categoria',
            field=models.CharField(max_length=50, default='medicamento'),
        ),
        # Add 'stock_actual' field
        migrations.AddField(
            model_name='producto',
            name='stock_actual',
            field=models.IntegerField(default=0),
        ),
        # Add 'sustancia_activa' field
        migrations.AddField(
            model_name='producto',
            name='sustancia_activa',
            field=models.CharField(max_length=200, blank=True, null=True),
        ),
        # Add 'presentacion' field
        migrations.AddField(
            model_name='producto',
            name='presentacion',
            field=models.CharField(max_length=200, blank=True, null=True),
        ),
        # Add 'concentracion' field
        migrations.AddField(
            model_name='producto',
            name='concentracion',
            field=models.CharField(max_length=100, blank=True, null=True),
        ),
        # Add 'via_administracion' field
        migrations.AddField(
            model_name='producto',
            name='via_administracion',
            field=models.CharField(max_length=50, blank=True, null=True),
        ),
        # Add 'requiere_receta' field
        migrations.AddField(
            model_name='producto',
            name='requiere_receta',
            field=models.BooleanField(default=False),
        ),
        # Add 'es_controlado' field
        migrations.AddField(
            model_name='producto',
            name='es_controlado',
            field=models.BooleanField(default=False),
        ),
        # Add 'imagen' field
        migrations.AddField(
            model_name='producto',
            name='imagen',
            field=models.CharField(max_length=255, blank=True, null=True),
        ),
        # Alter unidad_medida to allow longer values
        migrations.AlterField(
            model_name='producto',
            name='unidad_medida',
            field=models.CharField(max_length=100, default='PIEZA'),
        ),
        # Remove precio_unitario as it's not in current model
        # (price is managed at Lote level)
        migrations.RemoveField(
            model_name='producto',
            name='precio_unitario',
        ),
    ]
