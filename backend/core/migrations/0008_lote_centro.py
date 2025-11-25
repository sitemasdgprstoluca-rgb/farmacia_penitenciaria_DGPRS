from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_lote_idx_lote_stock_lookup_lote_idx_lote_disponible_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='lote',
            name='centro',
            field=models.ForeignKey(blank=True, help_text='Centro asociado para inventario por sede', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lotes_centro', to='core.centro'),
        ),
    ]
