# Script de Pruebas Críticas - Sistema de Contratos Dual
# Ejecuta tests comprehensivos antes de commit

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PRUEBAS MASIVAS - SISTEMA FARMACIA" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ErrorCount = 0
$TotalTests = 0
$PassedTests = 0

# Función para ejecutar tests y reportar resultados
function Run-TestSuite {
    param(
        [string]$TestName,
        [string]$TestPath
    )
    
    Write-Host "🧪 Ejecutando: $TestName" -ForegroundColor Yellow
    Write-Host "   Archivo: $TestPath" -ForegroundColor Gray
    
    $result = python -m pytest $TestPath -v --tb=short 2>&1
    $exitCode = $LASTEXITCODE
    
    # Extraer estadísticas
    $stats = $result | Select-String "(\d+) passed"
    
    if ($exitCode -eq 0) {
        Write-Host "   ✅ PASADO" -ForegroundColor Green
        if ($stats) {
            $passed = $stats.Matches.Groups[1].Value
            Write-Host "   Tests: $passed" -ForegroundColor Green
            $script:PassedTests += [int]$passed
            $script:TotalTests += [int]$passed
        }
    } else {
        Write-Host "   ❌ FALLIDO" -ForegroundColor Red
        $script:ErrorCount++
        
        # Mostrar resumen de error
        $errorSummary = $result | Select-String "FAILED|ERROR" | Select-Object -First 5
        if ($errorSummary) {
            Write-Host "   Errores:" -ForegroundColor Red
            $errorSummary | ForEach-Object { Write-Host "   $_" -ForegroundColor Red }
        }
    }
    Write-Host ""
}

Write-Host "🎯 CATEGORÍA 1: SISTEMA DE CONTRATOS DUAL" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta
Run-TestSuite "Contratos Global (Validación Dual)" "tests/test_contrato_global.py"

Write-Host "🎯 CATEGORÍA 2: LOTES Y MOVIMIENTOS" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta
Run-TestSuite "Lotes - Tests Unitarios" "tests/test_lotes_unit.py"
Run-TestSuite "Lotes - Nuevos" "tests/test_lotes_nuevos.py"
Run-TestSuite "Movimientos - Consistencia" "tests/test_movimientos_consistency.py"
Run-TestSuite "Movimientos - Masivo" "tests/test_movimientos_masivo.py"

Write-Host "🎯 CATEGORÍA 3: INTEGRIDAD Y BASE DE DATOS" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta
Run-TestSuite "Integridad Base de Datos" "tests/test_integridad_base_datos.py"
Run-TestSuite "Database Integration" "tests/test_database_integration.py"
Run-TestSuite "Stock Integration" "tests/test_stock_integration.py"

Write-Host "🎯 CATEGORÍA 4: IMPORTACIÓN Y EXPORTACIÓN" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta
Run-TestSuite "Excel Import/Export" "tests/test_excel_import_export.py"
Run-TestSuite "Importación Lotes" "tests/test_lotes_import.py"
Run-TestSuite "Importación Productos" "tests/test_importacion_productos.py"

Write-Host "🎯 CATEGORÍA 5: FLUJOS DE NEGOCIO" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta
Run-TestSuite "Flujo Productos-Lotes" "tests/test_flujo_productos_lotes.py"
Run-TestSuite "Flujo Requisiciones" "tests/test_flujo_requisiciones.py"
Run-TestSuite "Inventario Contrato Masivo" "tests/test_inventario_contrato_masivo.py"

Write-Host "🎯 CATEGORÍA 6: DONACIONES Y EXPEDIENTES" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta
Run-TestSuite "Donaciones - Completo" "tests/test_donaciones_completo.py"
Run-TestSuite "Dispensaciones - Completo" "tests/test_dispensaciones_completo.py"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "RESUMEN FINAL" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Total de tests ejecutados: $TotalTests" -ForegroundColor White
Write-Host "Tests pasados: $PassedTests" -ForegroundColor Green
Write-Host "Suites con errores: $ErrorCount" -ForegroundColor $(if ($ErrorCount -eq 0) { "Green" } else { "Red" })
Write-Host ""

if ($ErrorCount -eq 0) {
    Write-Host "✅ TODOS LOS TESTS PASARON - LISTO PARA COMMIT" -ForegroundColor Green
    exit 0
} else {
    Write-Host "❌ HAY ERRORES - REVISAR ANTES DE COMMIT" -ForegroundColor Red
    exit 1
}
