#!/bin/bash

# Backup script para producción
# Uso: ./backup_script.sh [backup_dir]

set -e

# Variables con defaults
BACKUP_DIR="${1:-${BACKUP_DIR:-/backups/farmacia}}"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=${RETENTION_DAYS:-30}
PROJECT_ROOT="${PROJECT_ROOT:-/var/www/farmacia}"

# Validar variables requeridas
if [ -z "$DB_HOST" ] || [ -z "$DB_USER" ] || [ -z "$DB_NAME" ]; then
  echo "❌ Error: Variables de entorno faltantes"
  echo "Requeridas: DB_HOST, DB_USER, DB_NAME, DB_PASSWORD"
  echo "Ejemplo: export DB_HOST=localhost DB_USER=postgres DB_NAME=farmacia DB_PASSWORD=..."
  exit 1
fi

# Crear directorio si no existe
mkdir -p "$BACKUP_DIR"
if [ ! -w "$BACKUP_DIR" ]; then
  echo "❌ Error: No se puede escribir en $BACKUP_DIR"
  exit 1
fi

echo "=== FARMACIA BACKUP SCRIPT ==="
echo "Date: $DATE"
echo "Backup dir: $BACKUP_DIR"

# 1. PostgreSQL backup
echo "[1/4] Backing up PostgreSQL..."
if command -v pg_dump &> /dev/null; then
  PGPASSWORD=$DB_PASSWORD pg_dump \
    -h "$DB_HOST" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --no-owner --no-acl \
    | gzip > "$BACKUP_DIR/db_$DATE.sql.gz"
  echo "✓ Database backed up: $(du -h "$BACKUP_DIR/db_$DATE.sql.gz" | cut -f1)"
else
  echo "⚠️  pg_dump no encontrado, saltando backup de PostgreSQL"
fi

# 2. Media files backup
echo "[2/4] Backing up media files..."
MEDIA_DIR="$PROJECT_ROOT/media"
if [ -d "$MEDIA_DIR" ] && [ "$(ls -A "$MEDIA_DIR" 2>/dev/null)" ]; then
  tar -czf "$BACKUP_DIR/media_$DATE.tar.gz" -C "$PROJECT_ROOT" media/
  echo "✓ Media backed up: $(du -h "$BACKUP_DIR/media_$DATE.tar.gz" | cut -f1)"
else
  echo "⚠️  Directorio media vacío o no existe, saltando"
fi

# 3. Upload to S3 (opcional)
if [ -n "$AWS_S3_BUCKET" ] && command -v aws &> /dev/null; then
  echo "[3/4] Uploading to S3..."
  if [ -f "$BACKUP_DIR/db_$DATE.sql.gz" ]; then
    aws s3 cp "$BACKUP_DIR/db_$DATE.sql.gz" "s3://$AWS_S3_BUCKET/db/" && echo "✓ DB uploaded to S3"
  fi
  if [ -f "$BACKUP_DIR/media_$DATE.tar.gz" ]; then
    aws s3 cp "$BACKUP_DIR/media_$DATE.tar.gz" "s3://$AWS_S3_BUCKET/media/" && echo "✓ Media uploaded to S3"
  fi
else
  echo "[3/4] S3 upload deshabilitado (AWS_S3_BUCKET no configurado o aws cli no instalado)"
fi

# 4. Cleanup old backups
echo "[4/4] Cleaning old backups..."
find $BACKUP_DIR -name "*.gz" -mtime +$RETENTION_DAYS -delete
echo "✓ Cleanup done"

echo ""
echo "✅ Backup completed successfully"
