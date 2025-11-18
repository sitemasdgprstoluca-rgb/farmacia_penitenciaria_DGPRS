Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CONFIGURACIÓN COMPLETA DEL SISTEMA" -ForegroundColor Cyan
Write-Host "Sistema de Farmacia Penitenciaria" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar que estamos en la carpeta backend
if (-not (Test-Path "manage.py")) {
    Write-Host "[ERROR] Este script debe ejecutarse desde la carpeta backend" -ForegroundColor Red
    pause
    exit 1
}

# Paso 1: Verificar entorno virtual
Write-Host "[1/6] Verificando entorno virtual..." -ForegroundColor Yellow
if (-not (Test-Path "venv")) {
    Write-Host "Creando entorno virtual..." -ForegroundColor Yellow
    python -m venv venv
}

# Activar entorno virtual
Write-Host "Activando entorno virtual..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

# Paso 2: Instalar dependencias
Write-Host ""
Write-Host "[2/6] Instalando dependencias..." -ForegroundColor Yellow
pip install -r requirements.txt

# Paso 3: Crear migraciones
Write-Host ""
Write-Host "[3/6] Creando migraciones de base de datos..." -ForegroundColor Yellow
python manage.py makemigrations farmacia
python manage.py migrate

# Paso 4: Configurar grupos y permisos
Write-Host ""
Write-Host "[4/6] Configurando grupos y permisos..." -ForegroundColor Yellow
python manage.py setup_permissions

# Paso 5: Crear superusuario
Write-Host ""
Write-Host "[5/6] Creando superusuario..." -ForegroundColor Yellow
Write-Host "Por favor ingresa los datos del SUPERUSUARIO:" -ForegroundColor Cyan
Write-Host ""
python manage.py createsuperuser

# Paso 6: Crear usuarios de prueba
Write-Host ""
Write-Host "[6/6] Creando usuarios de prueba..." -ForegroundColor Yellow
python manage.py create_test_users

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "CONFIGURACIÓN COMPLETADA EXITOSAMENTE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "URLs del sistema:" -ForegroundColor Cyan
Write-Host "  Backend API:  http://localhost:8000/api" -ForegroundColor White
Write-Host "  Django Admin: http://localhost:8000/admin" -ForegroundColor White
Write-Host "  Frontend:     http://localhost:5173" -ForegroundColor White
Write-Host ""
Write-Host "Para iniciar el sistema ejecuta: ..\start.bat" -ForegroundColor Yellow
Write-Host ""
pause
