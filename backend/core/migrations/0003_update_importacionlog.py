from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_detallerequisicion_importacionlog_lote_movimiento_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='importacionlog',
            name='errores',
        ),
        migrations.RemoveField(
            model_name='importacionlog',
            name='exitoso',
        ),
        migrations.RemoveField(
            model_name='importacionlog',
            name='productos_actualizados',
        ),
        migrations.RemoveField(
            model_name='importacionlog',
            name='productos_creados',
        ),
        migrations.AddField(
            model_name='importacionlog',
            name='modelo',
            field=models.CharField(default='Producto', max_length=50),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='importacionlog',
            name='registros_exitosos',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='importacionlog',
            name='registros_fallidos',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='importacionlog',
            name='resultado_procesamiento',
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name='importacionlog',
            name='total_registros',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='importacionlog',
            name='estado',
            field=models.CharField(choices=[('exitosa', 'Exitosa'), ('parcial', 'Parcialmente exitosa'), ('fallida', 'Fallida')], default='exitosa', max_length=20),
        ),
        migrations.AlterField(
            model_name='importacionlog',
            name='usuario',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.user'),
        ),
    ]
