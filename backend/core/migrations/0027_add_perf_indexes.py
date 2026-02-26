# Generated migration: performance indexes for audit and lot queries
from django.db import migrations


class Migration(migrations.Migration):
    """
    Adds composite indexes on tables managed outside Django (managed=False).
    These indexes speed up the ORM Subquery annotations added in LoteViewSet
    and ProductoViewSet for _creado_por_nombre / _modificado_por_nombre.
    """

    dependencies = [
        ('core', '0026_sync_producto_fields'),
    ]

    operations = [
        # auditoria_logs: subqueries filter on (modelo, objeto_id, accion) and
        # order by timestamp — covering index satisfies both filter and ORDER BY
        migrations.RunSQL(
            sql="""
            CREATE INDEX IF NOT EXISTS idx_auditoria_logs_modelo_accion_obj_ts
                ON auditoria_logs (modelo, accion, objeto_id, timestamp DESC)
                WHERE usuario_id IS NOT NULL;
            """,
            reverse_sql="DROP INDEX IF EXISTS idx_auditoria_logs_modelo_accion_obj_ts;",
        ),
        # lote_parcialidades: subquery filters by lote_id and orders by created_at
        migrations.RunSQL(
            sql="""
            CREATE INDEX IF NOT EXISTS idx_lote_parcialidades_lote_created
                ON lote_parcialidades (lote_id, created_at ASC);
            """,
            reverse_sql="DROP INDEX IF EXISTS idx_lote_parcialidades_lote_created;",
        ),
        # lotes: subquery looks up via created_by_id (undeclared FK column)
        migrations.RunSQL(
            sql="""
            CREATE INDEX IF NOT EXISTS idx_lotes_created_by_id
                ON lotes (created_by_id)
                WHERE created_by_id IS NOT NULL;
            """,
            reverse_sql="DROP INDEX IF EXISTS idx_lotes_created_by_id;",
        ),
    ]
