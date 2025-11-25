#!/bin/bash

# Pre-flight check script
# Valida que el entorno este configurado antes de ejecutar backups/monitoring

set -e

echo "=== FARMACIA PRE-FLIGHT CHECK ==="
echo ""

ERRORS=0
WARNINGS=0

# Function helpers
check_command() {
  if command -v "$1" &> /dev/null; then
    echo "[OK] $1 is installed"
  else
    echo "[ERROR] $1 is NOT installed"
    ERRORS=$((ERRORS + 1))
  fi
}

check_dir() {
  if [ -d "$1" ]; then
    if [ -w "$1" ]; then
      echo "[OK] Directory $1 exists and is writable"
    else
      echo "[WARNING] Directory $1 exists but is NOT writable"
      WARNINGS=$((WARNINGS + 1))
    fi
  else
    echo "[WARNING] Directory $1 does NOT exist"
    WARNINGS=$((WARNINGS + 1))
  fi
}

check_env() {
  if [ -n "${!1}" ]; then
    echo "[OK] $1 is set"
  else
    echo "[WARNING] $1 is NOT set"
    WARNINGS=$((WARNINGS + 1))
  fi
}

check_port() {
  if nc -z localhost "$1" 2>/dev/null; then
    echo "[OK] Port $1 is listening"
  else
    echo "[INFO] Port $1 is NOT listening (may be OK if service is not running)"
  fi
}

# ============================
# CHECK 1: Required Commands
# ============================
echo "--- Checking Required Commands ---"
check_command "bash"
check_command "gzip"
check_command "tar"

# Database tools (optional but recommended)
if command -v pg_dump &> /dev/null; then
  echo "[OK] pg_dump is installed"
else
  echo "[WARNING] pg_dump is NOT installed (needed for database backups)"
  WARNINGS=$((WARNINGS + 1))
fi

if command -v psql &> /dev/null; then
  echo "[OK] psql is installed"
else
  echo "[WARNING] psql is NOT installed (needed for database restore)"
  WARNINGS=$((WARNINGS + 1))
fi

# Optional tools
if command -v docker &> /dev/null; then
  echo "[OK] docker is installed"
else
  echo "[INFO] docker is NOT installed (needed for ELK stack)"
fi

if command -v aws &> /dev/null; then
  echo "[OK] aws cli is installed"
else
  echo "[INFO] aws cli is NOT installed (needed for S3 backups)"
fi

echo ""

# ============================
# CHECK 2: Environment Variables
# ============================
echo "--- Checking Environment Variables ---"
check_env "DB_HOST"
check_env "DB_USER"
check_env "DB_NAME"
check_env "DB_PASSWORD"
check_env "BACKUP_DIR"
check_env "PROJECT_ROOT"

echo ""

# ============================
# CHECK 3: Directories
# ============================
echo "--- Checking Directories ---"
BACKUP_DIR="${BACKUP_DIR:-/backups/farmacia}"
PROJECT_ROOT="${PROJECT_ROOT:-/var/www/farmacia}"
LOG_DIR="${LOG_DIR:-/var/log/farmacia}"

check_dir "$BACKUP_DIR"
check_dir "$PROJECT_ROOT"
check_dir "$LOG_DIR"

if [ -d "$PROJECT_ROOT/media" ]; then
  echo "[OK] Media directory exists"
else
  echo "[INFO] Media directory does not exist yet"
fi

echo ""

# ============================
# CHECK 4: Database Connection
# ============================
echo "--- Checking Database Connection ---"
if [ -n "$DB_HOST" ] && [ -n "$DB_USER" ] && [ -n "$DB_NAME" ]; then
  if command -v psql &> /dev/null; then
    if PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" &> /dev/null; then
      echo "[OK] Database connection successful"
    else
      echo "[ERROR] Cannot connect to database"
      ERRORS=$((ERRORS + 1))
    fi
  else
    echo "[SKIP] psql not installed, cannot test database"
  fi
else
  echo "[SKIP] Database credentials not set"
fi

echo ""

# ============================
# CHECK 5: Services (if running)
# ============================
echo "--- Checking Services (Optional) ---"
check_port 8000  # Django
check_port 5432  # PostgreSQL
check_port 6379  # Redis
check_port 9090  # Prometheus
check_port 9200  # Elasticsearch
check_port 5601  # Kibana

echo ""

# ============================
# CHECK 6: Scripts Permissions
# ============================
echo "--- Checking Script Permissions ---"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for script in backup_script.sh restore_script.sh test_restore.sh; do
  if [ -f "$SCRIPT_DIR/$script" ]; then
    if [ -x "$SCRIPT_DIR/$script" ]; then
      echo "[OK] $script is executable"
    else
      echo "[WARNING] $script is NOT executable (run: chmod +x $script)"
      WARNINGS=$((WARNINGS + 1))
    fi
  else
    echo "[ERROR] $script NOT found"
    ERRORS=$((ERRORS + 1))
  fi
done

echo ""

# ============================
# SUMMARY
# ============================
echo "==================================="
echo "SUMMARY"
echo "==================================="
echo "Errors:   $ERRORS"
echo "Warnings: $WARNINGS"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
  echo "[SUCCESS] All checks passed! System is ready."
  exit 0
elif [ $ERRORS -eq 0 ]; then
  echo "[OK] No critical errors, but $WARNINGS warning(s) found."
  echo "Review warnings above and fix if needed."
  exit 0
else
  echo "[FAIL] $ERRORS critical error(s) found."
  echo "Fix errors before running backup/monitoring scripts."
  exit 1
fi
