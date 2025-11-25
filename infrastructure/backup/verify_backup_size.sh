#!/bin/bash

# Verify backup size script
# Alerta si el ultimo backup es sospechosamente pequeno

set -e

BACKUP_DIR="${BACKUP_DIR:-/backups/farmacia}"
MIN_SIZE_KB=100  # Minimo 100KB esperado

echo "=== BACKUP SIZE VERIFICATION ==="

# Encontrar el backup mas reciente
LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/db_*.sql.gz 2>/dev/null | head -1)

if [ -z "$LATEST_BACKUP" ]; then
  echo "[ERROR] No backups found in $BACKUP_DIR"
  exit 1
fi

# Obtener tamano en KB
SIZE_KB=$(du -k "$LATEST_BACKUP" | cut -f1)
SIZE_MB=$(echo "scale=2; $SIZE_KB / 1024" | bc)

echo "Latest backup: $(basename "$LATEST_BACKUP")"
echo "Size: ${SIZE_MB}MB (${SIZE_KB}KB)"

if [ "$SIZE_KB" -lt "$MIN_SIZE_KB" ]; then
  echo "[WARNING] Backup size is suspiciously small (< ${MIN_SIZE_KB}KB)"
  echo "This may indicate a failed backup. Please investigate."
  exit 1
else
  echo "[OK] Backup size is acceptable"
  exit 0
fi
