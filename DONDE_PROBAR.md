# 🎯 DÓNDE PROBAR LA FUNCIONALIDAD

## ❌ NO ESTÁN AQUÍ (Lo que mostraste):

### 1. Productos > Imagen del producto
```
Esta es una funcionalidad DIFERENTE (aún pendiente)
- Mensaje: "Funcionalidad pendiente: En espera de mejora..."
- Para: Subir imagen del producto farmacéutico
```

### 2. Lotes > Documentos del Lote  
```
Esta es una funcionalidad DIFERENTE (aún pendiente)
- Mensaje: "Funcionalidad pendiente: En espera de mejora..."
- Para: Adjuntar PDFs a lotes de productos
```

---

## ✅ ESTÁN AQUÍ (Lo que implementamos):

### Dispensaciones > Documentos Firmados

**Ruta:** Menú lateral > Dispensaciones

**Condición:** Solo dispensaciones con estado = **"Dispensada"**

---

## 🔍 Pasos para Verificar

### 1️⃣ Refrescar el Navegador
```
Ctrl + Shift + R (Windows)
o
Cmd + Shift + R (Mac)
```
**Por qué:** Limpiar caché del navegador

---

### 2️⃣ Ir a Dispensaciones
```
Menú > Dispensaciones
(NO Productos, NO Inventario, NO Lotes)
```

---

### 3️⃣ Buscar Dispensación Dispensada
```
En la lista, busca una fila donde:
Estado = "Dispensada" (verde)
```

**Si no hay ninguna:**
1. Crea una nueva dispensación
2. Guárdala como "Pendiente"
3. Edítala y márcala como "Dispensada"

---

### 4️⃣ Ver los Botones en "Acciones"

#### Sin Documento (Estado inicial)
```
Columna "Acciones" muestra:
[📄] [✏️] [🗑️] [⬆]
                  ↑
          Botón azul de SUBIR
```

#### Con Documento (Después de subir)
```
Columna "Acciones" muestra:
[📄] [✏️] [🗑️] [✓] [🗑️]
                  ↑   ↑
            Verde   Rojo
         Descargar Eliminar
```

---

## 🧪 Prueba Completa

### Paso A: Subir Documento
1. Click en ícono azul ⬆
2. Selecciona un PDF (máx 10MB)
3. Espera toast verde: "Documento firmado subido correctamente"

### Paso B: Descargar Documento
1. Click en ícono verde ✓
2. Se abre nueva pestaña con el PDF
3. Verifica que es el archivo correcto

### Paso C: Eliminar Documento (Opcional)
1. Click en ícono rojo 🗑️
2. Confirma la eliminación
3. El botón vuelve a ⬆ (azul)

---

## ⚠️ Solución de Problemas

### "No veo ningún botón"
✓ Verifica que estás en **Dispensaciones** (no Productos/Lotes)
✓ Verifica que hay dispensaciones con estado **"Dispensada"**
✓ Haz **Ctrl+Shift+R** para refrescar
✓ Espera 5 minutos si el deploy está en progreso

### "Sale error al subir"
✓ Archivo debe ser PDF (no imagen, no Word)
✓ Tamaño máximo 10MB
✓ Verifica que Render terminó el deploy

### "No se descarga el archivo"
✓ Verifica configuración de Supabase (buckets)
✓ Revisa logs de Render por errores
✓ Verifica variables de entorno SUPABASE_URL y SUPABASE_KEY

---

## 📊 Vista Código (Líneas exactas)

### Frontend
**Archivo:** `inventario-front/src/pages/Dispensaciones.jsx`

**Líneas 1193-1232:** Botones en vista móvil
**Líneas 1348-1387:** Botones en vista desktop

**Condición clave (línea 1193):**
```jsx
{disp.estado === 'dispensada' && (
  // ... botones de documentos
)}
```

### Backend
**Archivo:** `backend/core/views.py`

**Líneas ~800-900:** 
- `subir_documento_firmado`
- `descargar_documento_firmado`
- `eliminar_documento_firmado`

---

## ✅ Checklist Final

- [ ] Navegador refrescado (Ctrl+Shift+R)
- [ ] Estoy en la sección "Dispensaciones"
- [ ] Veo al menos una dispensación con estado "Dispensada"
- [ ] Veo el ícono azul ⬆ en la columna "Acciones"
- [ ] Puedo subir un PDF de prueba
- [ ] El ícono cambia a verde ✓ después de subir
- [ ] Puedo descargar el PDF
- [ ] Puedo eliminar el PDF (opcional)

---

**Timestamp:** 2026-03-13
**Versión:** v1.0 - Documentos Firmados en Dispensaciones
