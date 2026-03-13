# Guía de Implementación: Documentos Firmados en Dispensaciones

## Descripción General

Este módulo permite subir, descargar y gestionar documentos PDF firmados en las dispensaciones, reemplazando el PDF temporal generado automáticamente por un documento real firmado y escaneado.

## Características Implementadas

- ✅ Campos en base de datos para almacenar información del documento
- ✅ Almacenamiento de PDFs en Supabase Storage
- ✅ Endpoints API para subir, descargar y eliminar documentos
- ✅ Interfaz de usuario con botones para gestionar documentos
- ✅ Validación de tipo de archivo (solo PDF)
- ✅ Validación de tamaño (máximo 10MB)
- ✅ Registro en historial de dispensaciones

## Pasos de Implementación

### 1. Ejecutar Migración SQL en Supabase

Accede al SQL Editor de Supabase y ejecuta el archivo de migración:

```
backend/migrations_sql/020_dispensaciones_documentos_firmados.sql
```

Esta migración:
- Agrega campos a la tabla `dispensaciones` para almacenar información del documento
- Crea índices para optimizar búsquedas
- Crea funciones auxiliares para estadísticas y limpieza

### 2. Crear Bucket de Storage en Supabase

1. Accede a **Supabase Dashboard** > **Storage**
2. Click en **New bucket**
3. Configuración del bucket:
   - **Name**: `dispensaciones-firmadas`
   - **Public**: **No** (privado, requiere autenticación)
   - **File size limit**: `10485760` (10 MB)
   - **Allowed MIME types**: `application/pdf`

4. Click en **Create bucket**

### 3. Configurar Políticas de Seguridad (RLS)

En **Supabase Dashboard** > **Storage** > Selecciona el bucket `dispensaciones-firmadas` > **Policies**:

#### Política 1: Permitir subida a usuarios autenticados

```sql
CREATE POLICY "Usuarios autenticados pueden subir PDFs"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'dispensaciones-firmadas');
```

#### Política 2: Permitir lectura a usuarios autenticados

```sql
CREATE POLICY "Usuarios autenticados pueden leer PDFs"
ON storage.objects FOR SELECT
TO authenticated
USING (bucket_id = 'dispensaciones-firmadas');
```

#### Política 3: Permitir eliminación solo al propietario

```sql
CREATE POLICY "Usuarios pueden eliminar sus propios PDFs"
ON storage.objects FOR DELETE
TO authenticated
USING (bucket_id = 'dispensaciones-firmadas' AND owner = auth.uid());
```

### 4. Verificar Instalación del Paquete Supabase en Python

Asegúrate de que el paquete de Supabase esté instalado:

```bash
pip install supabase
```

Si no está en `requirements.txt`, agrégalo:

```
supabase>=2.0.0
```

### 5. Configurar Variables de Entorno

Verifica que las siguientes variables estén configuradas en tu archivo `.env` o en Render:

```env
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_KEY=tu-api-key-aqui
```

Estas variables ya deberían estar configuradas si estás usando Supabase para la base de datos.

### 6. Desplegar Cambios

#### Backend (Django)

1. Asegúrate de que los cambios en los archivos estén committeados:
   - `backend/core/models.py` - Modelo Dispensacion actualizado
   - `backend/core/serializers.py` - Serializador actualizado
   - `backend/core/views.py` - Nuevos endpoints API
   - `backend/inventario/services/storage_service.py` - Método download_file agregado

2. Haz commit y push:
   ```bash
   git add .
   git commit -m "feat: agregar soporte para documentos firmados en dispensaciones"
   git push
   ```

3. Render debería hacer auto-deploy. Verifica los logs.

#### Frontend (React)

1. Los cambios en el frontend son:
   - `inventario-front/src/services/api.js` - Nuevos métodos API
   - `inventario-front/src/pages/Dispensaciones.jsx` - UI actualizada

2. El build se actualiza automáticamente en el deploy.

## Uso del Sistema

### Para Usuarios con Permisos de Edición

#### Subir Documento Firmado

1. Ve a la lista de **Dispensaciones**
2. Localiza una dispensación con estado **Dispensada**
3. Si NO tiene documento firmado, verás un ícono azul de **subir** (⬆)
4. Click en el ícono
5. Selecciona el archivo PDF firmado (máximo 10MB)
6. El documento se subirá automáticamente

#### Descargar Documento Firmado

1. Si la dispensación tiene documento firmado, verás un ícono verde con check (✓)
2. Click para descargar el documento en una nueva pestaña

#### Eliminar Documento Firmado

1. Si tienes permisos de edición, verás un ícono rojo de eliminar (🗑)
2. Click para eliminar el documento
3. Confirma la acción
4. El documento se eliminará del storage y de la base de datos

### Generar PDF Temporal (Formato C)

El botón con ícono de PDF rojo genera el Formato C temporal (el que se usaba antes).
Esto sigue disponible como respaldo o para generar borradores.

## Campos en Base de Datos

La tabla `dispensaciones` ahora incluye:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `documento_firmado_url` | TEXT | URL del documento en Supabase Storage |
| `documento_firmado_nombre` | VARCHAR(255) | Nombre original del archivo |
| `documento_firmado_fecha` | TIMESTAMP | Fecha de subida |
| `documento_firmado_por_id` | INTEGER | Usuario que subió el documento |
| `documento_firmado_tamano` | INTEGER | Tamaño en bytes |

## Endpoints API

### POST /api/dispensaciones/{id}/subir_documento_firmado/

Sube un documento PDF firmado.

**Request:**
```
Content-Type: multipart/form-data

archivo: <PDF file>
```

**Response:**
```json
{
  "message": "Documento firmado subido exitosamente",
  "dispensacion": { ... }
}
```

### GET /api/dispensaciones/{id}/descargar_documento_firmado/

Descarga el documento PDF firmado.

**Response:**
```
Content-Type: application/pdf
Content-Disposition: attachment; filename="..."
```

### DELETE /api/dispensaciones/{id}/eliminar_documento_firmado/

Elimina el documento PDF firmado.

**Response:**
```json
{
  "message": "Documento firmado eliminado exitosamente"
}
```

## Funciones SQL Auxiliares

### stats_documentos_firmados_dispensaciones()

Obtiene estadísticas sobre documentos firmados:

```sql
SELECT * FROM stats_documentos_firmados_dispensaciones(
    p_centro_id := NULL,
    p_fecha_inicio := '2026-01-01',
    p_fecha_fin := '2026-03-31'
);
```

Retorna:
- Total de dispensaciones
- Con documento firmado
- Sin documento firmado
- Porcentaje con documento

### limpiar_documentos_huerfanos_dispensaciones()

Limpia referencias a documentos que ya no existen en Storage:

```sql
SELECT limpiar_documentos_huerfanos_dispensaciones();
```

## Troubleshooting

### Error: "Servicio de almacenamiento no disponible"

**Causa:** El paquete `supabase` no está instalado o las credenciales no están configuradas.

**Solución:**
```bash
pip install supabase
```

Verifica las variables de entorno `SUPABASE_URL` y `SUPABASE_KEY`.

### Error: "Error al subir el documento"

**Causa:** El bucket no existe o no tiene las políticas correctas.

**Solución:**
1. Verifica que el bucket `dispensaciones-firmadas` existe en Supabase Storage
2. Verifica que las políticas RLS estén creadas correctamente
3. Verifica que el tamaño del archivo no exceda 10MB

### Error: "Solo se permiten archivos PDF"

**Causa:** El archivo seleccionado no es un PDF.

**Solución:** Asegúrate de seleccionar solo archivos con extensión `.pdf`.

### El ícono de subir no aparece

**Causa:** La dispensación no está en estado "Dispensada".

**Solución:** Solo las dispensaciones con estado "Dispensada" pueden tener documentos firmados.

## Seguridad

- ✅ Solo usuarios autenticados pueden subir/descargar documentos
- ✅ Los archivos se almacenan en un bucket privado (no público)
- ✅ Se valida tipo y tamaño de archivo antes de subir
- ✅ Se registra quién subió cada documento y cuándo
- ✅ Solo usuarios con permisos de edición pueden eliminar documentos

## Mantenimiento

### Limpieza de Documentos Huérfanos

Ejecutar periódicamente (mensual):

```sql
SELECT limpiar_documentos_huerfanos_dispensaciones();
```

Esto elimina referencias en la BD a archivos que ya no existen en Storage.

### Monitoreo de Uso de Storage

En Supabase Dashboard > Storage > Usage puedes ver:
- Cantidad de archivos
- Espacio usado
- Tendencias de uso

## Notas Adicionales

- El límite de 10MB por archivo es configurable en el bucket de Supabase
- Los documentos se organizan por fecha: `YYYY/MM/FOLIO_nombre.pdf`
- El sistema mantiene el PDF generado temporal como respaldo
- Al reemplazar un documento, el anterior se elimina automáticamente del storage

## Contacto y Soporte

Para dudas o problemas con esta funcionalidad, contacta al equipo de desarrollo.