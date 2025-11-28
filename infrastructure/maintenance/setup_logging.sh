#!/bin/bash

# ==============================================================================
# SCRIPT PARA CONFIGURAR LOGGING Y ROTACIÓN DE LOGS EN PRODUCCIÓN
# ==============================================================================
#
# USO:
#   1. Copia este script al servidor de producción.
#   2. Dale permisos de ejecución: chmod +x setup_logging.sh
#   3. Ejecútalo como superusuario: sudo ./setup_logging.sh
#
# QUÉ HACE:
#   - Crea el directorio /var/log/farmacia para los logs de la aplicación.
#   - Asigna la propiedad del directorio al usuario 'www-data' (común para
#     servidores web como Gunicorn/Nginx). Cambia 'www-data' si tu
#     aplicación corre con otro usuario.
#   - Crea una configuración para 'logrotate' que gestiona los logs de Django:
#     - Rota los logs diariamente.
#     - Comprime los logs antiguos.
#     - Mantiene los logs de los últimos 30 días.
#     - Evita errores si el archivo de log no existe.
#     - Recarga el servicio de Gunicorn después de rotar para que siga
#       escribiendo en el nuevo archivo.
#
# ==============================================================================

set -e  # Termina el script si un comando falla

# --- Variables (ajusta si es necesario) ---
LOG_DIR="/var/log/farmacia"
APP_USER="www-data" # Usuario con el que corre Gunicorn/Django
LOGROTATE_CONF_FILE="/etc/logrotate.d/farmacia"
GUNICORN_SERVICE_NAME="gunicorn" # Nombre del servicio de systemd para Gunicorn

# 1. Crear directorio de logs
echo "Creando directorio de logs en $LOG_DIR..."
if [ ! -d "$LOG_DIR" ]; then
    sudo mkdir -p "$LOG_DIR"
    echo "Directorio creado."
else
    echo "El directorio ya existe."
fi

# 2. Asignar permisos
echo "Asignando permisos del directorio a $APP_USER..."
sudo chown -R "$APP_USER:$APP_USER" "$LOG_DIR"
sudo chmod -R 755 "$LOG_DIR"
echo "Permisos asignados."

# 3. Crear configuración de logrotate
echo "Creando configuración de logrotate en $LOGROTATE_CONF_FILE..."

# Usamos 'heredoc' para escribir el bloque de configuración.
# La configuración se escribe en el archivo especificado por LOGROTATE_CONF_FILE.
sudo tee "$LOGROTATE_CONF_FILE" > /dev/null <<EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $APP_USER $APP_USER
    sharedscripts
    postrotate
        # Recarga Gunicorn para que use el nuevo archivo de log.
        # El comando 'systemctl' busca el servicio y le envía la señal USR1.
        # Esto hace que Gunicorn reabra sus archivos de log sin reiniciar la aplicación.
        if [ -f /var/run/gunicorn.pid ]; then
            kill -USR1 \`cat /var/run/gunicorn.pid\`
        else
            # Como fallback, si no se encuentra el PID, se recarga el servicio.
            # Esto puede causar una breve interrupción, por lo que se prefiere el PID.
            systemctl reload $GUNICORN_SERVICE_NAME
        fi
    endscript
}
EOF

echo "Configuración de logrotate creada."

# 4. Verificar y forzar la rotación (opcional, para pruebas)
echo "Verificando la sintaxis de logrotate..."
sudo logrotate -d "$LOGROTATE_CONF_FILE"
echo "Sintaxis correcta."

echo "Puedes forzar una rotación para probar con: sudo logrotate -f $LOGROTATE_CONF_FILE"

echo -e "\n✅ Configuración de logging completada."
echo "Asegúrate de que la variable de entorno LOG_FILE en tu .env de producción apunte a '$LOG_DIR/django.log'."
