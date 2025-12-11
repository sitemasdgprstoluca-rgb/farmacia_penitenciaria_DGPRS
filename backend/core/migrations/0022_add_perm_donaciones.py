# audit34: Add missing permission fields to Usuario
# These fields are referenced in models.py but missing from migrations

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_optimize_db_structure'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='perm_donaciones',
            field=models.BooleanField(
                null=True, 
                blank=True, 
                help_text='Permiso para ver Donaciones (almacen separado)'
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='perm_crear_requisicion',
            field=models.BooleanField(
                null=True,
                blank=True,
                help_text='Permiso para crear requisiciones'
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='perm_autorizar_admin',
            field=models.BooleanField(
                null=True,
                blank=True,
                help_text='Permiso para autorizar como admin de centro'
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='perm_autorizar_director',
            field=models.BooleanField(
                null=True,
                blank=True,
                help_text='Permiso para autorizar como director'
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='perm_recibir_farmacia',
            field=models.BooleanField(
                null=True,
                blank=True,
                help_text='Permiso para recibir en farmacia'
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='perm_autorizar_farmacia',
            field=models.BooleanField(
                null=True,
                blank=True,
                help_text='Permiso para autorizar en farmacia'
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='perm_surtir',
            field=models.BooleanField(
                null=True,
                blank=True,
                help_text='Permiso para surtir requisiciones'
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='perm_confirmar_entrega',
            field=models.BooleanField(
                null=True,
                blank=True,
                help_text='Permiso para confirmar entrega'
            ),
        ),
    ]
