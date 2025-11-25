#!/bin/bash

# Test restore script - valida que los backups son restaurables
# Se ejecuta semanalmente para verificar integridad

set -e

BACKUP_DIR="${BACKUP_DIR:-/backups/farmacia}"
TEST_DB="${TEST_DB_NAME:-farmacia_test_restore}"

echo "=== FARMACIA TEST RESTORE ==="
echo "Testing latest backup..."

# Encontrar el backup mas reciente
LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/db_*.sql.gz 2>/dev/null | head -1)

if [ -z "$LATEST_BACKUP" ]; then
  echo "[ERROR] No backups found in $BACKUP_DIR"
  exit 1
fi

BACKUP_DATE=$(basename "$LATEST_BACKUP" | sed 's/db_\(.*\)\.sql\.gz/\1/')
echo "Latest backup: $BACKUP_DATE"

# Validar variables de entorno
if [ -z "$DB_HOST" ] || [ -z "$DB_USER" ]; then
  echo "[WARNING] Environment variables not configured, skipping test"
  exit 0
fi

# Crear base de datos temporal
echo "[1/3] Creating test database..."
PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $TEST_DB;" 2>/dev/null || true
PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d postgres -c "CREATE DATABASE $TEST_DB;"

# Restaurar backup
echo "[2/3] Restoring backup to test database..."
gunzip -c "$LATEST_BACKUP" | \
  PGPASSWORD=$DB_PASSWORD psql \
    -h "$DB_HOST" \
    -U "$DB_USER" \
    -d "$TEST_DB" \
    --quiet

# Validar contenido
echo "[3/3] Validating restored data..."
TABLE_COUNT=$(PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$TEST_DB" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")

if [ "$TABLE_COUNT" -gt 0 ]; then
  echo "[SUCCESS] Test restore successful - $TABLE_COUNT tables found"
  
  # Cleanup
  PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d postgres -c "DROP DATABASE $TEST_DB;"
  
  exit 0
else
  echo "[ERROR] Test restore failed - no tables found"
  exit 1
fi
