# Solución: Error en Recuperación de Contraseña

## Problema Identificado

El enlace del email de recuperación apuntaba a `http://localhost:5173` en lugar de la URL real del frontend en Render.

## Cambios Realizados

### 1. Actualizado `render.yaml`
Agregada variable de entorno `FRONTEND_URL` para el backend:

```yaml
- key: FRONTEND_URL
  sync: false  # Configura con la URL de tu frontend
```

### 2. Actualizado `backend/config/settings.py`
Mejorado el fallback para detectar automáticamente el entorno:

```python
# Si DEBUG=False (producción), usa URL de producción
# Si DEBUG=True (desarrollo), usa localhost:5173
_default_frontend = 'http://localhost:5173' if DEBUG else 'https://farmacia-penitenciaria-front.onrender.com'
FRONTEND_URL = config('FRONTEND_URL', default=_default_frontend)
```

## Configuración Requerida en Render Dashboard

### Opción 1: Configurar Variable de Entorno (Recomendado)

1. Ve a https://dashboard.render.com/
2. Selecciona tu servicio **farmacia-api** (backend)
3. Ve a **Environment** en el menú lateral
4. Agrega una nueva variable de entorno:
   - **Key**: `FRONTEND_URL`
   - **Value**: `https://TU-FRONTEND.onrender.com` (reemplaza con tu URL real)
5. Guarda y espera a que el servicio se redeploy automáticamente

### Opción 2: Usar el Fallback Automático

Si tu frontend está desplegado en Render con el nombre por defecto, el código automáticamente usará:
- **Desarrollo** (DEBUG=True): `http://localhost:5173`
- **Producción** (DEBUG=False): `https://farmacia-penitenciaria-front.onrender.com`

**IMPORTANTE**: Verifica que tu URL de frontend coincida. Si es diferente, configura la variable de entorno.

## Verificar la Configuración Actual

Ejecuta este comando en tu terminal del backend para ver qué URL está usando:

```bash
python manage.py shell -c "from django.conf import settings; print(f'FRONTEND_URL: {settings.FRONTEND_URL}')"
```

## Probar el Flujo de Recuperación

### 1. En Desarrollo Local

```bash
# Terminal 1 - Backend
cd backend
python manage.py runserver

# Terminal 2 - Frontend
cd inventario-front
npm run dev

# Navega a: http://localhost:5173/recuperar-password
# Ingresa un email válido
# Revisa la consola del backend para ver el enlace generado
```

### 2. En Producción (Render)

1. Asegúrate de haber configurado `FRONTEND_URL` correctamente
2. Haz commit y push de los cambios:
   ```bash
   git add render.yaml backend/config/settings.py
   git commit -m "fix: Configurar FRONTEND_URL para recuperación de contraseña en producción"
   git push origin main
   ```
3. Espera a que Render redeploy automáticamente
4. Prueba el flujo de recuperación desde tu frontend en producción

## Problemas Comunes

### El email sigue usando localhost

**Causa**: La variable de entorno no está configurada en Render Dashboard o el servicio no se ha redeployeado.

**Solución**:
1. Verifica que `FRONTEND_URL` esté configurada en Environment variables
2. Fuerza un redeploy manual desde Render Dashboard
3. Verifica con el comando de arriba qué URL está usando

### El enlace da error 404 o CORS

**Causa**: La URL del frontend no coincide con la configurada.

**Solución**:
1. En Render Dashboard, ve a tu servicio de frontend
2. Copia la URL exacta (ej: `https://farmacia-front-xyz.onrender.com`)
3. Actualiza `FRONTEND_URL` en las variables de entorno del backend
4. Asegúrate de que `CORS_ALLOWED_ORIGINS` incluya esta URL

### El token expira muy rápido

**Causa**: El token de Django tiene un tiempo de vida por defecto de 1 día.

**Configuración actual**: El enlace expira en 24 horas (configurable en `password_reset.py`).

Si necesitas aumentar el tiempo:
```python
# En backend/core/password_reset.py, línea ~65
<p><strong>⚠️ Este enlace expirará en 24 horas.</strong></p>
```

## Documentos Relacionados

- [`backend/core/password_reset.py`](../backend/core/password_reset.py) - Lógica de envío de emails
- [`inventario-front/src/pages/RecuperarPassword.jsx`](../inventario-front/src/pages/RecuperarPassword.jsx) - Formulario de solicitud
- [`inventario-front/src/pages/RestablecerPassword.jsx`](../inventario-front/src/pages/RestablecerPassword.jsx) - Formulario de cambio
- [`render.yaml`](../render.yaml) - Configuración de despliegue

## Estado Actual

✅ **Código actualizado** - Los cambios ya están implementados
⚠️ **Requiere configuración** - Debes configurar `FRONTEND_URL` en Render Dashboard
🔄 **Requiere redeploy** - Haz push a main para aplicar en producción

## Siguiente Paso

**IMPORTANTE**: Después de hacer push, ve al Dashboard de Render y configura la variable `FRONTEND_URL` con la URL correcta de tu frontend.

---
**Fecha**: 26 de febrero de 2026  
**Autor**: GitHub Copilot  
**Prioridad**: Alta - Funcionalidad crítica de seguridad
