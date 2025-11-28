#!/bin/bash

# ==============================================================================
# SCRIPT PARA CONFIGURAR CRONJOB PARA BACKUPS AUTOMÁTICOS
# ==============================================================================
#
# USO:
#   1. Asegúrate de que 'backup_script.sh' esté en el mismo directorio y
#      tenga permisos de ejecución (chmod +x backup_script.sh).
#   2. Ejecuta este script como superusuario: sudo ./setup_cron.sh
#
# QUÉ HACE:
#   - Define la ruta absoluta al script de backup.
#   - Define la programación del cronjob (diariamente a las 2:30 AM por defecto).
#   - Crea un archivo temporal con la nueva entrada de cron.
#   - Comprueba si el cronjob ya existe para evitar duplicados.
#   - Si no existe, añade el nuevo cronjob a la tabla de cron del usuario root.
#
# ==============================================================================

set -e

# --- Variables ---
# Obtiene la ruta absoluta del directorio donde se encuentra este script.
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
BACKUP_SCRIPT_PATH="$SCRIPT_DIR/backup_script.sh"
CRON_USER="root"

# Programación del cronjob: Minuto Hora DíaMes Mes DíaSemana
# "30 2 * * *" = todos los días a las 2:30 AM.
CRON_SCHEDULE="30 2 * * *"

# --- Lógica del Script ---

# 1. Verificar que el script de backup existe y es ejecutable
if [ ! -f "$BACKUP_SCRIPT_PATH" ]; then
    echo "Error: El script de backup '$BACKUP_SCRIPT_PATH' no se encontró."
    exit 1
fi
if [ ! -x "$BACKUP_SCRIPT_PATH" ]; then
    echo "Error: El script de backup no tiene permisos de ejecución. Ejecuta: chmod +x $BACKUP_SCRIPT_PATH"
    exit 1
fi

# 2. Construir el comando del cronjob
# Redirigimos la salida estándar y de error a /dev/null para que no envíe correos.
CRON_JOB="$CRON_SCHEDULE $BACKUP_SCRIPT_PATH > /dev/null 2>&1"

# 3. Añadir el cronjob si no existe
echo "Configurando el siguiente cronjob para el usuario '$CRON_USER':"
echo "$CRON_JOB"

# Usamos 'crontab -l' para listar los cronjobs existentes y 'grep' para buscar
# si nuestro script ya está programado.
# La opción '-F' trata el string como una cadena fija, y '-q' suprime la salida.
if (crontab -u "$CRON_USER" -l 2>/dev/null | grep -Fq "$BACKUP_SCRIPT_PATH"); then
    echo "El cronjob para este script ya existe. No se realizarán cambios."
else
    echo "Añadiendo cronjob..."
    # Creamos un archivo temporal con los cronjobs existentes y el nuevo.
    (crontab -u "$CRON_USER" -l 2>/dev/null; echo "$CRON_JOB") | crontab -u "$CRON_USER" -
    echo "Cronjob añadido correctamente."
fi

echo -e "\n✅ Configuración de cronjob completada."
echo "Para verificar, puedes ejecutar: sudo crontab -u $CRON_USER -l"
