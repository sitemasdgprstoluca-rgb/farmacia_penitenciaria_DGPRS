#!/bin/bash

echo "=== Configuración de Farmacia Penitenciaria ==="

# Crear migraciones
echo "Creando migraciones..."
python manage.py makemigrations

# Aplicar migraciones
echo "Aplicando migraciones..."
python manage.py migrate

# Crear superusuario (opcional)
echo "¿Desea crear un superusuario? (s/n)"
read respuesta
if [ "$respuesta" = "s" ]; then
    python manage.py createsuperuser
fi

echo "=== Configuración completada ==="
echo "Puede iniciar el servidor con: python manage.py runserver"
