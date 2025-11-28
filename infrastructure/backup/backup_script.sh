#!/bin/bash

# Backup script para produccion
# Uso: ./backup_script.sh [backup_dir]

set -e

# Variables con defaults
BACKUP_DIR="${1:-${BACKUP_DIR:-/backups/farmacia}}"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=${RETENTION_DAYS:-30}
PROJECT_ROOT="${PROJECT_ROOT:-/var/www/farmacia}"

# Detectar motor de base de datos
SQLITE_PATH="${SQLITE_PATH:-}"
if [ -z "$SQLITE_PATH" ] && [ -n "$DATABASE_URL" ]; then
  if [[ "$DATABASE_URL" == sqlite:* ]]; then
    SQLITE_PATH="${DATABASE_URL#sqlite:///}"
  fi
fi
if [ -z "$SQLITE_PATH" ] && [ -z "$DB_HOST" ] && [ -z "$DB_NAME" ]; then
  DEFAULT_SQLITE="${PROJECT_ROOT}/db.sqlite3"
  if [ -f "$DEFAULT_SQLITE" ]; then
    SQLITE_PATH="$DEFAULT_SQLITE"
  fi
fi

if [ -z "$SQLITE_PATH" ] && { [ -z "$DB_HOST" ] || [ -z "$DB_USER" ] || [ -z "$DB_NAME" ]; }; then
  echo "[ERROR] Faltan variables para la base de datos."
  echo "PostgreSQL requiere: DB_HOST, DB_USER, DB_NAME, DB_PASSWORD"
  echo "SQLite: defina SQLITE_PATH o DATABASE_URL=sqlite:///ruta/db.sqlite3"
  exit 1
fi

# Crear directorio si no existe
mkdir -p "$BACKUP_DIR"
if [ ! -w "$BACKUP_DIR" ]; then
  echo "[ERROR] No se puede escribir en $BACKUP_DIR"
  exit 1
fi

echo "=== FARMACIA BACKUP SCRIPT ==="
echo "Date: $DATE"
echo "Backup dir: $BACKUP_DIR"
echo "Project root: $PROJECT_ROOT"

# 1. Database backup
if [ -n "$SQLITE_PATH" ]; then
  echo "[1/4] Backing up SQLite ($SQLITE_PATH)..."
  if command -v sqlite3 >/dev/null 2>&1; then
    sqlite3 "$SQLITE_PATH" ".backup '$BACKUP_DIR/db_${DATE}.sqlite3'"
    gzip -f "$BACKUP_DIR/db_${DATE}.sqlite3"
    echo "[OK] SQLite backup: $(du -h "$BACKUP_DIR/db_${DATE}.sqlite3.gz" | cut -f1)"
  else
    cp "$SQLITE_PATH" "$BACKUP_DIR/db_${DATE}.sqlite3"
    gzip -f "$BACKUP_DIR/db_${DATE}.sqlite3"
    echo "[WARN] sqlite3 no encontrado; se copio el archivo directamente."
  fi
else
  echo "[1/4] Backing up PostgreSQL..."
  if command -v pg_dump >/dev/null 2>&1; then
    PGPASSWORD=$DB_PASSWORD pg_dump \
      -h "$DB_HOST" \
      -U "$DB_USER" \
      -d "$DB_NAME" \
      --no-owner --no-acl \
      | gzip > "$BACKUP_DIR/db_${DATE}.sql.gz"
    echo "[OK] Database backed up: $(du -h "$BACKUP_DIR/db_${DATE}.sql.gz" | cut -f1)"
  else
    echo "[WARN] pg_dump no encontrado, no se pudo respaldar la base de datos."
  fi
fi

# 2. Media files backup
echo "[2/4] Backing up media files..."
MEDIA_DIR="$PROJECT_ROOT/media"
if [ -d "$MEDIA_DIR" ] && [ "$(ls -A "$MEDIA_DIR" 2>/dev/null)" ]; then
  tar -czf "$BACKUP_DIR/media_${DATE}.tar.gz" -C "$PROJECT_ROOT" media/
  echo "[OK] Media backed up: $(du -h "$BACKUP_DIR/media_${DATE}.tar.gz" | cut -f1)"
else
  echo "[WARN] Directorio media vacio o no existe, saltando."
fi

# 3. Upload to S3 (opcional)
if [ -n "$AWS_S3_BUCKET" ] && command -v aws >/dev/null 2>&1; then
  echo "[3/4] Uploading to S3..."
  if [ -f "$BACKUP_DIR/db_${DATE}.sql.gz" ]; then
    aws s3 cp "$BACKUP_DIR/db_${DATE}.sql.gz" "s3://$AWS_S3_BUCKET/db/" && echo "[OK] DB uploaded to S3"
  fi
  if [ -f "$BACKUP_DIR/db_${DATE}.sqlite3.gz" ]; then
    aws s3 cp "$BACKUP_DIR/db_${DATE}.sqlite3.gz" "s3://$AWS_S3_BUCKET/db/" && echo "[OK] SQLite uploaded to S3"
  fi
  if [ -f "$BACKUP_DIR/media_${DATE}.tar.gz" ]; then
    aws s3 cp "$BACKUP_DIR/media_${DATE}.tar.gz" "s3://$AWS_S3_BUCKET/media/" && echo "[OK] Media uploaded to S3"
  fi
else
  echo "[3/4] S3 upload deshabilitado (AWS_S3_BUCKET no configurado o aws cli no instalado)"
fi

# 4. Cleanup old backups
echo "[4/4] Cleaning old backups..."
find "$BACKUP_DIR" -name "*.gz" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "*.sqlite3" -mtime +$RETENTION_DAYS -delete

echo "[OK] Backup completed successfully"
