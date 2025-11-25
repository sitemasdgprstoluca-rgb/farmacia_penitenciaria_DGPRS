#!/bin/bash

# Restore script
# Uso: ./restore_script.sh <backup_date> [backup_dir]

set -e

if [ $# -lt 1 ]; then
  echo "Usage: ./restore_script.sh <backup_date> [backup_dir]"
  echo "Example: ./restore_script.sh 20240101_120000"
  echo ""
  echo "Backups disponibles:"
  ls -lh "${BACKUP_DIR:-/backups/farmacia}/" 2>/dev/null | grep -E '(db_|media_)' || echo "  (ninguno)"
  exit 1
fi

BACKUP_DATE=$1
BACKUP_DIR="${2:-${BACKUP_DIR:-/backups/farmacia}}"
PROJECT_ROOT="${PROJECT_ROOT:-/var/www/farmacia}"

# Validar que existe el backup
if [ ! -f "$BACKUP_DIR/db_$BACKUP_DATE.sql.gz" ]; then
  echo "❌ Error: Backup no encontrado: $BACKUP_DIR/db_$BACKUP_DATE.sql.gz"
  exit 1
fi

# Validar variables de entorno
if [ -z "$DB_HOST" ] || [ -z "$DB_USER" ] || [ -z "$DB_NAME" ]; then
  echo "❌ Error: Variables de entorno faltantes"
  echo "Requeridas: DB_HOST, DB_USER, DB_NAME, DB_PASSWORD"
  exit 1
fi

echo "=== FARMACIA RESTORE SCRIPT ==="
echo "Restoring from: $BACKUP_DATE"

# 1. Restore database
echo "[1/2] Restoring PostgreSQL..."
echo "⚠️  ADVERTENCIA: Esto sobreescribirá la base de datos $DB_NAME"
read -p "Continuar? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
  echo "❌ Restore cancelado"
  exit 1
fi

if command -v psql &> /dev/null; then
  gunzip -c "$BACKUP_DIR/db_$BACKUP_DATE.sql.gz" | \
    PGPASSWORD=$DB_PASSWORD psql \
      -h "$DB_HOST" \
      -U "$DB_USER" \
      -d "$DB_NAME" \
      --quiet
  echo "✓ Database restored"
else
  echo "❌ Error: psql no encontrado"
  exit 1
fi

# 2. Restore media files
if [ -f "$BACKUP_DIR/media_$BACKUP_DATE.tar.gz" ]; then
  echo "[2/2] Restoring media files..."
  if [ -d "$PROJECT_ROOT/media" ]; then
    rm -rf "$PROJECT_ROOT/media"/*
  fi
  mkdir -p "$PROJECT_ROOT"
  tar -xzf "$BACKUP_DIR/media_$BACKUP_DATE.tar.gz" -C "$PROJECT_ROOT"
  echo "✓ Media restored"
else
  echo "[2/2] No hay backup de media para esta fecha"
fi

echo ""
echo "✅ Restore completed successfully"
