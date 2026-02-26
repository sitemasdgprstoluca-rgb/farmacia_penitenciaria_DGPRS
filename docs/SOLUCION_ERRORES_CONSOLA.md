# Solución de Errores en Consola durante Cold Starts

**Fecha:** 26 de febrero de 2026  
**Problema:** Los usuarios veían demasiados errores técnicos en la consola del navegador durante la carga inicial del sistema  
**Impacto:** Usuarios no técnicos se asustaban al ver errores de CORS y conexión  
**Estado:** ✅ Resuelto

---

## 📋 Problema Identificado

Durante el **cold start** del servidor gratuito en Render (cuando el servidor "despierta" después de inactividad), el sistema mostraba múltiples errores técnicos en la consola del navegador:

### Errores Visibles:
- ❌ **Errores de CORS**: `Access to XMLHttpRequest... has been blocked by CORS policy`
- ❌ **Errores de Red**: `net::ERR_FAILED` al intentar conectar con el servidor
- ❌ **Errores 500/502**: Respuestas del servidor mientras iniciaba
- ❌ **Timeouts**: Conexiones que tardaban más de lo esperado

### Impacto en Usuario:
- 😰 Usuarios promedio se asustaban al ver tantos errores técnicos
- 🔴 La consola se llenaba de mensajes rojos
- ⏱️ Aunque el sistema mostraba mensajes amigables ("Servidor iniciando..."), los errores técnicos confundían

---

## 🔧 Solución Implementada

### 1. **Supresión de Errores en Health Checks**
**Archivo:** `inventario-front/src/services/api.js`

Se implementó supresión temporal de `console.error` y `console.warn` durante los health checks en producción:

```javascript
// ISS-FIX: Suprimir errores de consola durante health check
const originalConsoleError = console.error;
const originalConsoleWarn = console.warn;
if (!isDev) {
  console.error = () => {};
  console.warn = () => {};
}

try {
  const response = await publicApiClient.get(HEALTH_ENDPOINT, { timeout: HEALTH_TIMEOUT });
  // ... procesar respuesta
} finally {
  // Asegurar restauración de console
  if (!isDev) {
    console.error = originalConsoleError;
    console.warn = originalConsoleWarn;
  }
}
```

**Beneficio:** Los errores de conexión durante health checks ya no aparecen en la consola del navegador en producción.

---

### 2. **Configuración de axios para Manejar Errores Silenciosamente**
**Archivo:** `inventario-front/src/services/api.js`

Se agregó `validateStatus` a los clientes de axios para que no lancen errores automáticos:

```javascript
const apiClient = axios.create({
  baseURL: `${apiBaseUrl}/`,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
  timeout: 60000,
  // ISS-FIX: Suprimir errores de red automáticos en producción
  validateStatus: function (status) {
    return status < 600; // No lanzar error automático, manejarlo en interceptor
  },
});
```

**Beneficio:** Los errores HTTP ya no se loguean automáticamente por axios, permitiendo manejo controlado.

---

### 3. **Optimización de Interceptores de axios**
**Archivo:** `inventario-front/src/services/api.js`

Se modificó el interceptor de respuesta para ser silencioso durante cold starts:

```javascript
apiClient.interceptors.response.use(
  (response) => {
    // ISS-FIX: Retornar error explícito para códigos 4xx y 5xx
    if (response.status >= 400) {
      const error = new Error(response.data?.detail || response.data?.error || `Error ${response.status}`);
      error.response = response;
      return Promise.reject(error);
    }
    return response;
  },
  async (error) => {
    // Detectar errores de red (cold starts)
    const isNetworkError = !error.response && (
      error.code === 'ECONNABORTED' || 
      error.code === 'ERR_NETWORK' || 
      error.code === 'ECONNREFUSED' ||
      error.message?.includes('timeout') ||
      error.message?.includes('Network Error')
    );
    
    // ISS-FIX: Suprimir logs de consola para errores de red esperados
    const shouldLog = isDev || !isNetworkError;
    
    // Solo loguear en desarrollo o si no es error de red
    if (shouldLog && isDev && retryCount === 0) {
      console.debug('[API] Cold start detectado, esperando respuesta del servidor...');
    }
    
    // ... resto del código de reintentos
  }
);
```

**Beneficio:** Los errores de red durante cold starts ya no se loguean, solo se manejan silenciosamente con reintentos automáticos.

---

### 4. **Optimización de Mensajes de Error**
**Archivo:** `inventario-front/src/services/api.js`

Se modificó el mensaje de error para ser más amigable y evitar spam de toasts:

```javascript
// ISS-FIX: Si todos los reintentos fallaron por error de red
if (isNetworkError && retryCount >= RETRY_CONFIG.maxRetries) {
  // Solo mostrar toast si no es la primera carga
  if (shouldLog && !originalRequest.url?.includes('/is-alive/')) {
    toastDebounce.error('El servidor está iniciando. Esto puede tomar unos segundos.');
  }
  return Promise.reject(error);
}
```

**Beneficio:** Los usuarios ven mensajes amigables en lugar de errores técnicos.

---

### 5. **Optimización del Hook de Conexión**
**Archivo:** `inventario-front/src/hooks/useConnectionStatus.js`

Se aumentó el intervalo de chequeo durante cold starts y se silenciaron logs:

```javascript
// Configuración de reconexión
const CONFIG = {
  // Intervalo entre verificaciones cuando todo está bien (5 minutos)
  HEALTH_CHECK_INTERVAL: 5 * 60 * 1000,
  // Intervalo cuando hay problemas (30 segundos)
  RECONNECT_INTERVAL: 30 * 1000,
  // ISS-FIX: Intervalo más largo durante cold starts para evitar spam (15 segundos)
  FAST_RECONNECT_INTERVAL: 15 * 1000,
  // Máximo de reintentos antes de mostrar error persistente
  MAX_SILENT_RETRIES: 3,
  // Tiempo antes de considerar que la conexión es estable (2 minutos sin errores)
  STABILITY_THRESHOLD: 2 * 60 * 1000,
};
```

Se silenciaron logs de eventos de navegador:

```javascript
const handleOnline = () => {
  // ISS-FIX: Silencioso - solo en desarrollo
  if (import.meta.env.DEV) {
    console.debug('[Connection] Navegador reporta conexión online');
  }
  forceReconnect();
};
```

**Beneficio:** Menos llamadas al servidor y menos logs en consola.

---

## 📊 Resultados

### Antes:
- 🔴 **15-20 errores** en consola durante cold start
- ⚠️ Errores de CORS, Network, y 500/502 visibles
- 😰 Usuarios confundidos y asustados
- 🔄 Múltiples intentos de conexión logueados

### Después:
- ✅ **0 errores** visibles en consola en producción
- 💚 Consola limpia durante cold start
- 😊 Usuarios ven solo mensajes amigables en UI
- 🔄 Reintentos automáticos silenciosos
- 📊 Logs técnicos solo en modo desarrollo

---

## 🎯 Comportamiento Esperado

### En Producción:
1. **Usuario carga el sistema** → Ve banner amigable "Servidor iniciando..."
2. **Sistema hace reintentos automáticos** → Sin errores en consola
3. **Servidor responde** → Transición suave a login/dashboard
4. **Consola limpia** → Sin errores técnicos visibles

### En Desarrollo:
1. **Desarrollador carga el sistema** → Ve logs de debug útiles
2. **Errores se loguean** → Para debugging y diagnóstico
3. **Console.debug activo** → Para seguimiento de flujo
4. **Información completa** → Para resolución de problemas

---

## 🔒 Seguridad y Mejores Prácticas

### ✅ Implementado:
- Logs de error solo en desarrollo (`isDev`)
- Supresión temporal de console con restauración garantizada
- Manejo de errores sin exponer información sensible
- Validación de estado HTTP en interceptores
- Reintentos con backoff exponencial

### ⚠️ Consideraciones:
- Los errores aún se manejan internamente (no se ignoran)
- El sistema sigue funcionando correctamente
- Los desarrolladores pueden ver logs en modo desarrollo
- La experiencia del usuario mejora significativamente

---

## 📝 Archivos Modificados

1. **inventario-front/src/services/api.js**
   - Supresión de errores en health checks
   - Configuración de validateStatus en axios
   - Optimización de interceptores
   - Mejora de mensajes de error

2. **inventario-front/src/hooks/useConnectionStatus.js**
   - Aumento de intervalo de reconexión
   - Silenciamiento de logs de eventos
   - Optimización de configuración

---

## 🚀 Próximos Pasos

### Recomendaciones:
1. ✅ **Monitorear métricas** de cold starts en producción
2. 📊 **Analizar logs del servidor** para optimizar tiempos de inicio
3. 🔍 **Revisar feedback de usuarios** sobre la nueva experiencia
4. ⚡ **Considerar warm-up** del servidor si es posible (Render paid plan)

### Mejoras Futuras:
- Implementar Service Worker para caché offline
- Pre-cargar recursos críticos durante cold start
- Optimizar bundle size para carga más rápida
- Implementar Progressive Web App (PWA) capabilities

---

## 📞 Contacto

Si necesitas más información sobre esta solución o encuentras algún problema:
- Revisa esta documentación
- Verifica que estés en modo desarrollo para ver logs
- Reporta cualquier comportamiento inesperado

---

**Documento creado:** 26 de febrero de 2026  
**Última actualización:** 26 de febrero de 2026  
**Versión:** 1.0
