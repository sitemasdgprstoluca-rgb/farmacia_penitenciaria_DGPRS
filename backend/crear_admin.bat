@echo off
echo ========================================
echo Creando Superusuario Automaticamente
echo ========================================
echo.

cd backend
call venv\Scripts\activate.bat

python manage.py create_superadmin

echo.
echo ========================================
echo Presiona cualquier tecla para continuar...
pause > nul
