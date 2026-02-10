# 🔧 Fix Deployment en Render - HALLAZGO #8

## ❌ Problema Actual

El deployment en Render está fallando con:
```
django.db.utils.OperationalError: no such table: usuarios
```

**Causa raíz**: El buildCommand configurado en el dashboard de Render está usando un comando antiguo que intenta acceder a la tabla `usuarios` en SQLite (que no existe porque `managed=False`).

## ✅ Solución

El buildCommand en el dashboard de Render debe actualizarse manualmente (render.yaml no actualiza servicios existentes automáticamente).

### Pasos para Fix Manual en Render Dashboard

1. **Ir al dashboard de Render**: https://dashboard.render.com/
2. **Seleccionar el servicio**: `farmacia-api` (o el nombre de tu servicio backend)
3. **Ir a Settings** (menú lateral izquierdo)
4. **Buscar "Build Command"**
5. **Reemplazar** el comando actual:
   ```bash
   # COMANDO ANTIGUO (REMOVER):
   pip install -r backend/requirements.txt && python backend/manage.py collectstatic --noinput && python backend/manage.py migrate && python backend/manage.py shell -c "from core.models import User; u=User.objects.get(username='admin'); u.set_password('Admin123!'); u.save(); print('Admin password set!')"
   ```
   
   Por este **COMANDO NUEVO**:
   ```bash
   chmod +x build.sh && ./build.sh
   ```

6. **Guardar cambios** (botón "Save Changes" al final de la página)
7. **Trigger Manual Deploy**: Ir a "Manual Deploy" → "Deploy latest commit"

### ¿Qué hace el nuevo comando?

El script `set_admin_password.py` detecta automáticamente el motor de BD:
- **Si es PostgreSQL** (producción con Supabase): Cambia el password del admin
- **Si es SQLite** (fallback cuando DATABASE_URL no está configurado): Muestra mensaje informativo y NO falla el deployment

## 📋 Verificación Post-Deploy

Después del fix, el deployment debería:
1. ✅ Instalar dependencias
2. ✅ Collectstatic sin errores
3. ✅ Migrations aplicadas correctamente
4. ✅ Script set_admin_password ejecuta sin errores (info log si es SQLite)
5. ✅ Servicio inicia correctamente

## 🔍 Notas Adicionales

### Warnings Esperados
Los siguientes warnings son **normales** y no bloquean el deployment:
```
WARNING: ISS-001: Divergencia de esquema en tabla 'requisiciones'
WARNING: ISS-001: No se pudo verificar CHECK constraint
```
Estos warnings aparecen porque estamos usando SQLite temporalmente y el schema validator está diseñado para PostgreSQL.

### Configurar DATABASE_URL (Opcional pero Recomendado)

Si quieres usar PostgreSQL desde el inicio (Supabase):

1. En Render Dashboard → Environment Variables
2. Agregar/editar `DATABASE_URL`:
   ```
   postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-us-west-1.pooler.supabase.com:6543/postgres
   ```
3. Trigger redeploy

Con DATABASE_URL configurado:
- Usará PostgreSQL (Supabase) en lugar de SQLite
- El script `set_admin_password.py` ejecutará el cambio de password
- Los warnings de schema desaparecerán

## 📝 Commits Relacionados

- `5baa0f3`: Creación de script `set_admin_password.py` con detección de vendor
- `dbea04f`: Actualización de buildCommand en render.yaml

---

**Status**: ⏳ Esperando actualización manual en Render Dashboard
