#!/usr/bin/env bash
# Start script for Render
set -o errexit

echo "=== Starting Gunicorn server ==="
cd backend

# Configuración de Gunicorn para Render free tier
# --timeout 120: Permitir conexiones lentas a Supabase (free tier puede ser lento)
# --workers 2: Suficiente para el free tier de Render
# --keep-alive 5: Mantener conexiones activas
# --graceful-timeout 30: Tiempo para cerrar workers gracefully
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --timeout 120 \
    --keep-alive 5 \
    --graceful-timeout 30 \
    --log-level info
