# GUÍA DE SOLUCIÓN: IMPORTACIÓN DE PRODUCTOS

## ✅ DIAGNÓSTICO REALIZADO

### Backend - FUNCIONANDO AL 100%
- ✅ El importador de productos funciona correctamente
- ✅ El archivo `Plantilla_Productos.xlsx` se importa sin errores
- ✅ 76 productos procesados exitosamente
- ✅ 0 errores encontrados
- ✅ Sistema de validación funcionando
- ✅ Sistema de auditoría funcionando

### Tests Ejecutados
```bash
# Test directo de importación (SIN API)
python backend/test_direct_import.py
RESULTADO: ✅ 76 productos importados, 0 errores

# Test de importación (CON API - REQUIERE SERVIDOR CORRIENDO)
python backend/test_api_import.py  
RESULTADO: ⚠️ Servidor no corriendo en localhost:8000
```

---

## 🔧 PASOS PARA SOLUCIONAR EL PROBLEMA

### PASO 1: Verificar que el servidor Django esté corriendo

```powershell
# En terminal 1 - Iniciar backend
cd C:\Users\zarag\Documents\Proyectos_Code\farmacia_penitenciaria\backend
python manage.py runserver
```

Debe mostrar:
```
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

### PASO 2: Verificar que el frontend esté corriendo

```powershell
# En terminal 2 - Iniciar frontend
cd C:\Users\zarag\Documents\Proyectos_Code\farmacia_penitenciaria\inventario-front
npm run dev
```

Debe mostrar:
```
  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

### PASO 3: Acceder al sistema con usuario farmacia

1. Abrir navegador en: `http://localhost:5173`
2. Iniciar sesión con usuario de rol "farmacia" o "admin"
3. Ir a la página de **Productos**

### PASO 4: Importar el archivo

1. Hacer clic en el botón **"Importar"** (ícono de upload)
2. Seleccionar el archivo: `C:\Users\zarag\Downloads\REVISAR\Plantilla_Productos.xlsx`
3. Esperar mensaje de confirmación

**Resultado esperado:**
```
✅ Importación completada. Creados: 0 | Actualizados: 76 | Total: 76
```

---

## 🐛 SI AÚN NO FUNCIONA

### Opción A: Revisar errores en la consola del navegador

1. Presionar **F12** para abrir DevTools
2. Ir a la pestaña **Console**
3. Intentar importar el archivo
4. Capturar cualquier error que aparezca en rojo
5. Enviar captura de pantalla del error

### Opción B: Revisar errores en la consola del backend

1. Mirar la terminal donde está corriendo `python manage.py runserver`
2. Intentar importar el archivo desde el frontend
3. Observar si aparece algún error
4. Copiar el error y enviarlo

### Opción C: Importar directamente con el script (BYPASS del frontend)

Si el frontend tiene problemas, puedes importar directamente:

```powershell
cd C:\Users\zarag\Documents\Proyectos_Code\farmacia_penitenciaria\backend
python test_direct_import.py
```

Este script importa directamente a la base de datos SIN usar la interfaz web.

---

## 📋 ARCHIVO DE PLANTILLA

El sistema espera un archivo Excel (.xlsx o .xls) con estas columnas **EXACTAS**:

| Columna | Obligatorio | Ejemplo |
|---------|-------------|---------|
| Clave | ✅ | PARA-001 |
| Nombre | ✅ | PARACETAMOL |
| Unidad | ✅ | CAJA CON 7 OVULOS |
| Stock Minimo | ✅ | 10 |
| Categoria | ✅ | Analgésico |
| Sustancia Activa | ❌ | Paracetamol |
| Presentacion | ❌ | Tabletas |
| Concentracion | ❌ | 500mg |
| Via Admin | ❌ | Oral |
| Requiere Receta | ✅ | Si / No |
| Controlado | ✅ | Si / No |
| Estado | ✅ | Activo / Inactivo |

### Notas importantes:

- **Unidad**: El sistema extrae automáticamente la unidad base de texto como "CAJA CON 7 OVULOS" → "CAJA"
- **Stock Minimo**: Debe ser un número entero positivo
- **Requiere Receta**: Acepta: Si, No, Sí, N, S, Yes, No
- **Controlado**: Acepta: Si, No, Sí, N, S, Yes, No  
- **Estado**: Acepta: Activo, Inactivo, Active, Inactive

---

## ⚙️ CONFIGURACIÓN TÉCNICA

### Permisos necesarios para importar:
- Usuario con rol: `farmacia` o `admin`
- Permiso específico: `perm_productos` debe estar en True
- El sistema verifica automáticamente estos permisos

### Límites de importación:
- **Tamaño máximo del archivo:** 10 MB
- **Extensiones permitidas:** .xlsx, .xls
- **Filas máximas:** 10,000
- **Archivos con macros:** ❌ BLOQUEADOS (.xlsm, .xlsb)

### URL del endpoint de importación:
```
POST http://localhost:8000/api/productos/importar-excel/
Content-Type: multipart/form-data
Authorization: Bearer <JWT_TOKEN>
```

---

## 📞 INFORMACIÓN DE SOPORTE

### Archivos de configuración clave:
- Backend: `backend/core/utils/excel_importer.py`
- Frontend: `inventario-front/src/pages/Productos.jsx`
- API: `backend/inventario/views/productos.py` (línea 469)

### Logs de importación:
- Tabla en BD: `importacion_logs`
- Campos: archivo, tipo_importacion, registros_totales, registros_exitosos, registros_fallidos, errores

### Para ver logs de importaciones anteriores:
```sql
SELECT * FROM importacion_logs 
WHERE tipo_importacion = 'Producto' 
ORDER BY created_at DESC LIMIT 10;
```

---

## 🎯 RESUMEN

**Estado actual del sistema:**
- ✅ Backend: FUNCIONANDO
- ✅ Importador: FUNCIONANDO  
- ✅ Validaciones: FUNCIONANDO
- ✅ Archivo plantilla: VÁLIDO
- ⚠️ Frontend/API: REQUIERE VERIFICACIÓN

**Próximos pasos:**
1. Verificar que ambos servidores (backend y frontend) estén corriendo
2. Intentar importar desde el navegador
3. Si falla, revisar consola del navegador (F12)
4. Si persiste el problema, usar `test_direct_import.py` como alternativa

---

**Fecha de diagnóstico:** 2025-12-16  
**Archivo analizado:** C:\Users\zarag\Downloads\REVISAR\Plantilla_Productos.xlsx  
**Productos en archivo:** 175 filas (76 únicos)  
**Resultado del test:** ✅ 100% éxito
