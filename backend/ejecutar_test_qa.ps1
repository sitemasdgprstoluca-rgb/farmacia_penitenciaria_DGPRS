# Script para ejecutar verificación QA de notificaciones de caducidad
# Autor: Sistema de QA
# Fecha: 2026-03-05

Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "VERIFICACIÓN QA - Sistema de Notificaciones por Caducidad" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# 1. Activar entorno virtual
Write-Host "1️⃣  Activando entorno virtual..." -ForegroundColor Yellow
& C:/Users/zarag/Documents/Proyectos_Code/farmacia_penitenciaria/backend/.venv_new/Scripts/Activate.ps1

# 2. Crear datos de prueba con psql (si tienes psql instalado)
Write-Host "2️⃣  Creando datos de prueba..." -ForegroundColor Yellow
Write-Host "   ⚠️  Necesitas ejecutar manualmente el SQL:" -ForegroundColor Yellow
Write-Host "   psql -U postgres -d farmacia_db -f tests\test_qa_notificaciones_caducidad.sql" -ForegroundColor Gray
Write-Host ""
Write-Host "   O ejecutar desde pgAdmin/DBeaver la sección de SETUP" -ForegroundColor Gray
Write-Host ""
Read-Host "Presiona ENTER cuando hayas ejecutado el SQL de SETUP"

# 3. Ejecutar comando en modo SIMULACIÓN
Write-Host ""
Write-Host "3️⃣  Ejecutando comando en MODO SIMULACIÓN..." -ForegroundColor Yellow
py manage.py generar_alertas_inventario --dry-run

Write-Host ""
Read-Host "¿Se muestran los lotes de prueba? Presiona ENTER para continuar"

# 4. Ejecutar comando REAL
Write-Host ""
Write-Host "4️⃣  Ejecutando comando REAL (crea notificaciones)..." -ForegroundColor Yellow
py manage.py generar_alertas_inventario

Write-Host ""
Write-Host "✅ COMANDO EJECUTADO" -ForegroundColor Green
Write-Host ""

# 5. Mostrar instrucciones de verificación
Write-Host "5️⃣  VERIFICACIÓN:" -ForegroundColor Yellow
Write-Host ""
Write-Host "Ahora ejecuta las queries de VERIFICACIÓN del SQL:" -ForegroundColor White
Write-Host ""
Write-Host "-- Notificaciones de Farmacia" -ForegroundColor Gray
Write-Host "SELECT n.titulo, u.username, n.datos::jsonb->>'tipo_alerta'" -ForegroundColor Gray
Write-Host "FROM notificaciones n JOIN usuarios u ON n.usuario_id = u.id" -ForegroundColor Gray
Write-Host "WHERE n.datos::jsonb->>'tipo_alerta' LIKE '%caducidad%'" -ForegroundColor Gray
Write-Host "  AND n.created_at::date >= CURRENT_DATE;" -ForegroundColor Gray
Write-Host ""
Write-Host "-- Notificaciones de Centros" -ForegroundColor Gray
Write-Host "SELECT n.titulo, u.username, n.datos::jsonb->>'centro_nombre'" -ForegroundColor Gray
Write-Host "FROM notificaciones n JOIN usuarios u ON n.usuario_id = u.id" -ForegroundColor Gray
Write-Host "WHERE n.datos::jsonb->>'tipo_alerta' LIKE '%_centro'" -ForegroundColor Gray
Write-Host "  AND n.created_at::date >= CURRENT_DATE;" -ForegroundColor Gray
Write-Host ""
Write-Host "-- Verificar Aislamiento por Centro" -ForegroundColor Gray
Write-Host "SELECT COUNT(*) as debe_ser_cero" -ForegroundColor Gray
Write-Host "FROM notificaciones n JOIN usuarios u ON n.usuario_id = u.id" -ForegroundColor Gray
Write-Host "WHERE u.username = 'qa_centro_norte'" -ForegroundColor Gray
Write-Host "  AND n.datos::jsonb->>'centro_nombre' LIKE '%Sur%';" -ForegroundColor Gray
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "FIN DE VERIFICACIÓN QA" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Para limpiar los datos de prueba:" -ForegroundColor Yellow
Write-Host "Ejecuta la sección LIMPIEZA del SQL" -ForegroundColor Yellow
Write-Host ""
