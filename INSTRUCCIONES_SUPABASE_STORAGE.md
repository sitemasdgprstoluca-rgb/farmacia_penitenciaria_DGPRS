# 🔧 CONFIGURACIÓN DE SUPABASE STORAGE - Documentos Firmados

## 📋 Instrucciones Paso a Paso

### PASO 1: Acceder a Supabase SQL Editor

1. Abre **Supabase Dashboard** en tu navegador
2. Selecciona tu proyecto
3. Ve a **SQL Editor** (ícono de base de datos en el menú lateral)
4. Click en **New query**

---

### PASO 2: Crear Bucket y Políticas

**Copia y pega TODO el contenido del archivo:**
```
backend/migrations_sql/020b_configurar_storage_supabase.sql
```

**O copia directamente este código:**

```sql
-- Crear bucket
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'dispensaciones-firmadas',
  'dispensaciones-firmadas',
  false,
  10485760,
  ARRAY['application/pdf']::text[]
)
ON CONFLICT (id) DO NOTHING;

-- Política 1: Subir
CREATE POLICY "Usuarios autenticados pueden subir PDFs"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'dispensaciones-firmadas');

-- Política 2: Leer
CREATE POLICY "Usuarios autenticados pueden leer PDFs"
ON storage.objects FOR SELECT
TO authenticated
USING (bucket_id = 'dispensaciones-firmadas');

-- Política 3: Eliminar
CREATE POLICY "Usuarios pueden eliminar sus propios PDFs"
ON storage.objects FOR DELETE
TO authenticated
USING (bucket_id = 'dispensaciones-firmadas' AND owner = auth.uid());
```

---

### PASO 3: Ejecutar

1. Pega el código en el SQL Editor
2. Click en **Run** (o presiona Ctrl/Cmd + Enter)
3. Deberías ver: **Success. No rows returned**

---

### PASO 4: Verificar

Ejecuta este query para verificar:

```sql
-- Ver el bucket creado
SELECT id, name, public, file_size_limit, allowed_mime_types 
FROM storage.buckets 
WHERE id = 'dispensaciones-firmadas';
```

**Resultado esperado:**
```
id                       | name                      | public | file_size_limit | allowed_mime_types
-------------------------|---------------------------|--------|-----------------|-------------------
dispensaciones-firmadas  | dispensaciones-firmadas   | false  | 10485760        | {application/pdf}
```

---

### PASO 5: Verificar Políticas

```sql
-- Ver las políticas creadas
SELECT schemaname, tablename, policyname 
FROM pg_policies 
WHERE tablename = 'objects' 
AND policyname LIKE '%dispensaciones%';
```

**Resultado esperado:**
```
3 políticas creadas:
- Usuarios autenticados pueden subir PDFs
- Usuarios autenticados pueden leer PDFs
- Usuarios pueden eliminar sus propios PDFs
```

---

## ✅ CHECKLIST

Después de ejecutar el SQL, verifica:

- [ ] Bucket `dispensaciones-firmadas` aparece en **Storage** section
- [ ] File size limit: 10 MB
- [ ] Público: NO (privado)
- [ ] MIME types: application/pdf
- [ ] 3 políticas creadas en `storage.objects`

---

## 🎯 ALTERNATIVA: Crear Bucket por UI (Opcional)

Si prefieres crear el bucket manualmente:

1. Ve a **Storage** en Supabase Dashboard
2. Click **New bucket**
3. Configura:
   - **Name:** `dispensaciones-firmadas`
   - **Public:** Desmarcado (privado)
   - **File size limit:** `10485760`
   - **Allowed MIME types:** `application/pdf`
4. Click **Create bucket**
5. Luego ejecuta SOLO las 3 políticas del SQL

---

## 🚨 Posibles Errores

### Error: "policy already exists"
**Solución:** Las políticas ya están creadas. ¡Todo bien!

### Error: "relation storage.objects does not exist"
**Solución:** Asegúrate de tener Supabase Pro o que Storage esté habilitado.

### Error: "bucket already exists"
**Solución:** El bucket ya existe. ¡Todo bien! Ejecuta solo las políticas.

---

## 📝 Notas

- El bucket es **privado** (requiere autenticación)
- Tamaño máximo por archivo: **10 MB**
- Solo acepta archivos: **PDF**
- Los usuarios autenticados pueden subir/leer/eliminar PDFs

---

**¿Listo?** Una vez ejecutado, haz el deploy del código y ¡todo funcionará perfectamente! 🚀
