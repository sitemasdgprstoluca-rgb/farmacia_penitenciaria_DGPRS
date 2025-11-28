#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# SCRIPT DE BUILD PARA RENDER
# ══════════════════════════════════════════════════════════════════════════════
# Este script se ejecuta durante el despliegue en Render.
# Configúralo en Render como "Build Command": ./build.sh
# ══════════════════════════════════════════════════════════════════════════════

set -o errexit  # Salir si hay cualquier error

echo "═══════════════════════════════════════════════════════════════════"
echo "▶ Verificando variables de entorno requeridas..."
echo "═══════════════════════════════════════════════════════════════════"

# Variables obligatorias para producción
REQUIRED_VARS=(
    "SECRET_KEY"
    "DATABASE_URL"
    "ALLOWED_HOSTS"
    "CORS_ALLOWED_ORIGINS"
    "CSRF_TRUSTED_ORIGINS"
)

MISSING_VARS=()
for VAR in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!VAR}" ]; then
        MISSING_VARS+=("$VAR")
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo "❌ ERROR: Faltan variables de entorno requeridas:"
    for VAR in "${MISSING_VARS[@]}"; do
        echo "   - $VAR"
    done
    echo ""
    echo "Configura estas variables en el Dashboard de Render antes de desplegar."
    exit 1
fi

echo "✔ Todas las variables de entorno requeridas están configuradas"

# Validar que DATABASE_URL es PostgreSQL
if [[ ! "$DATABASE_URL" =~ ^postgres(ql)?:// ]]; then
    echo "❌ ERROR: DATABASE_URL debe ser una URL de PostgreSQL válida"
    echo "   Formato esperado: postgresql://usuario:password@host:puerto/database"
    exit 1
fi

echo "✔ DATABASE_URL es PostgreSQL válido"

echo "═══════════════════════════════════════════════════════════════════"
echo "▶ Instalando dependencias..."
echo "═══════════════════════════════════════════════════════════════════"
pip install --upgrade pip
pip install -r requirements.txt

echo "═══════════════════════════════════════════════════════════════════"
echo "▶ Verificando conexión a la base de datos..."
echo "═══════════════════════════════════════════════════════════════════"
python -c "
import dj_database_url
import psycopg2
import os

db_url = os.environ['DATABASE_URL']
db_config = dj_database_url.parse(db_url)

try:
    conn = psycopg2.connect(
        dbname=db_config['NAME'],
        user=db_config['USER'],
        password=db_config['PASSWORD'],
        host=db_config['HOST'],
        port=db_config['PORT'],
        sslmode='require',
        connect_timeout=10
    )
    cur = conn.cursor()
    cur.execute('SELECT version();')
    version = cur.fetchone()[0]
    print(f'✔ Conexión exitosa: {version[:50]}...')
    cur.close()
    conn.close()
except Exception as e:
    print(f'❌ Error de conexión: {e}')
    exit(1)
"

echo "═══════════════════════════════════════════════════════════════════"
echo "▶ Verificando configuración de seguridad de Django..."
echo "═══════════════════════════════════════════════════════════════════"
python manage.py check --deploy

echo "═══════════════════════════════════════════════════════════════════"
echo "▶ Recolectando archivos estáticos..."
echo "═══════════════════════════════════════════════════════════════════"
python manage.py collectstatic --noinput

echo "═══════════════════════════════════════════════════════════════════"
echo "▶ Aplicando migraciones de base de datos..."
echo "═══════════════════════════════════════════════════════════════════"
python manage.py migrate --noinput

# Verificar que las migraciones se aplicaron correctamente
echo "▶ Verificando estado de migraciones..."
python -c "
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute('SELECT COUNT(*) FROM django_migrations')
    count = cursor.fetchone()[0]
    print(f'✔ {count} migraciones aplicadas')
    if count == 0:
        print('❌ ERROR: No hay migraciones aplicadas')
        exit(1)
"

echo "═══════════════════════════════════════════════════════════════════"
echo "✔ Build completado exitosamente"
echo "═══════════════════════════════════════════════════════════════════"
