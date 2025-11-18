@echo off
echo Creando estructura de directorios...

mkdir inventario\management 2>nul
mkdir inventario\management\commands 2>nul

echo. > inventario\management\__init__.py
echo. > inventario\management\commands\__init__.py

echo ✅ Estructura creada
