@echo off
echo ========================================
echo REINICIO COMPLETO DEL SISTEMA
echo ========================================
echo.

echo [1/5] Matando procesos Python y Node...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM node.exe 2>nul
timeout /t 3 /nobreak >nul

echo [2/5] Verificando puertos...
netstat -ano | findstr ":8000" >nul
if %errorlevel% equ 0 (
    echo ADVERTENCIA: Puerto 8000 aun ocupado
    echo Por favor cierra manualmente cualquier proceso Python en el Administrador de Tareas
    pause
)

echo [3/5] Iniciando Backend Django...
cd /d "%~dp0backend"
start "Django Backend" cmd /k "python manage.py runserver 8000"
timeout /t 5 /nobreak >nul

echo [4/5] Verificando Backend...
curl -s http://127.0.0.1:8000/api/ >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Backend no responde
    echo Revisa la ventana del servidor Django
    pause
) else (
    echo Backend OK!
)

echo [5/5] Iniciando Frontend React...
cd /d "%~dp0inventario-front"
start "React Frontend" cmd /k "npm run dev"
timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo SISTEMA INICIADO
echo ========================================
echo Backend:  http://127.0.0.1:8000
echo Frontend: http://localhost:5174
echo.
echo Presiona cualquier tecla para abrir el navegador...
pause >nul
start http://localhost:5174

exit
