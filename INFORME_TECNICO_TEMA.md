# Informe Técnico: Persistencia de Tema (Colores/Logos)

**Fecha:** 4 de diciembre de 2025  
**Sistema:** SIFP - Sistema de Inventario de Farmacia Penitenciaria  
**Rama:** `dev`

---

## 1. Resumen Ejecutivo

Tras un análisis exhaustivo del código fuente, se confirma que **el sistema ya cuenta con mecanismos de persistencia implementados**, aunque existen escenarios donde el tema puede perderse. El problema original descrito no refleja completamente la arquitectura actual, que ya incluye:

- ✅ Caché local en `localStorage` 
- ✅ Endpoint público sin autenticación (`/api/tema/activo/`)
- ✅ Modelo `TemaGlobal` persistido en base de datos
- ✅ Rehidratación rápida desde caché antes de consultar API

Sin embargo, persisten **vulnerabilidades puntuales** que pueden causar pérdida del tema bajo ciertas condiciones.

---

## 2. Arquitectura Actual del Sistema de Temas

### 2.1 Backend (Django)

#### Modelo `TemaGlobal` (`backend/core/models.py`, líneas 1761-2327)

```
┌─────────────────────────────────────────────────────────────────┐
│                        TemaGlobal                               │
├─────────────────────────────────────────────────────────────────┤
│ • Tabla: tema_global                                            │
│ • Patrón: Singleton (solo un tema activo)                       │
│ • Campos: 50+ (colores, tipografía, logos, reportes)            │
│ • Método to_css_variables(): genera dict CSS listo para DOM     │
│ • Método to_json_config(): exportación completa para frontend   │
│ • Auditoría: created_at, updated_at, creado_por, modificado_por │
└─────────────────────────────────────────────────────────────────┘
```

#### Endpoints API (`backend/config/api_urls.py`)

| Endpoint | Método | Autenticación | Descripción |
|----------|--------|---------------|-------------|
| `/api/tema/activo/` | GET | **Pública** | Tema activo (login, recarga) |
| `/api/tema/` | GET | Requerida | Tema completo (admin) |
| `/api/tema/` | PUT | Superusuario | Actualizar tema |
| `/api/tema/restablecer/` | POST | Superusuario | Reset a institucional |
| `/api/tema/subir-logo/<tipo>/` | POST | Superusuario | Subir logo |
| `/api/tema/eliminar-logo/<tipo>/` | DELETE | Superusuario | Eliminar logo |

### 2.2 Frontend (React)

#### `ThemeContext.jsx` - Flujo de Carga

```
┌─────────────────────────────────────────────────────────────────┐
│                    cargarTema() - Flujo                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. REHIDRATACIÓN RÁPIDA                                        │
│     └── obtenerTemaDeCache() → localStorage                     │
│         └── Si existe → aplicarTemaCompleto() inmediatamente    │
│                                                                 │
│  2. CONSULTA API (paralela)                                     │
│     └── temaGlobalAPI.getTemaActivo()                           │
│         ├── Si responde → actualizar estado + guardarTemaEnCache│
│         └── Si falla → mantener caché aplicada en paso 1        │
│                                                                 │
│  3. FALLBACK LEGACY (si no hay caché)                           │
│     └── configuracionAPI.getTema()                              │
│         └── Si falla → aplicar temaDefault                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Constantes de Almacenamiento

```javascript
const STORAGE_KEY_TEMA = 'sifp_tema_cache';        // Datos del tema
const STORAGE_KEY_UPDATED = 'sifp_tema_updated_at'; // Timestamp para invalidación
```

#### Datos Cacheados en localStorage

```javascript
{
  css_variables: { ... },           // Variables CSS para :root
  reporte_titulo_institucion: "...", // Título del sistema
  favicon_url: "...",               // URL del favicon
  logo_header_url: "...",           // URL logo header
  logo_login_url: "...",            // URL logo login
  logo_reportes_url: "...",         // URL logo reportes
  nombre: "...",                    // Nombre del tema
  updated_at: "2025-12-04T..."      // Para invalidación de caché
}
```

---

## 3. Escenarios de Pérdida de Tema (Vulnerabilidades)

A pesar de la implementación existente, el tema puede perderse en estos casos:

### 3.1 🔴 Primer Acceso / localStorage Limpio

**Escenario:** Usuario nuevo o navegador sin caché.

| Condición | Resultado |
|-----------|-----------|
| API responde correctamente | ✅ Tema carga y se cachea |
| API no responde (servidor caído) | ❌ **Fallback a `temaDefault`** |
| API responde con error | ❌ **Fallback a `temaDefault`** |

**Impacto:** El usuario ve los colores hardcodeados (guinda institucional) en lugar del tema configurado.

### 3.2 🟡 Caché Desactualizada

**Escenario:** Admin cambia el tema pero la caché del usuario tiene valores antiguos.

| Condición | Resultado |
|-----------|-----------|
| API responde | ✅ Caché se actualiza |
| API no responde | ⚠️ Usuario ve tema viejo |

**Problema:** No hay mecanismo de invalidación proactiva (websockets, polling).

### 3.3 🔴 URLs de Logos Inaccesibles

**Escenario:** Los logos se cachean como URLs, pero el servidor de archivos no responde.

```javascript
// En caché:
logo_header_url: "http://backend/media/tema/logos/logo.png"

// Pero si el backend está caído:
<img src="..." onerror="???" />  // No hay fallback definido
```

**Impacto:** Logos rotos o espacios vacíos.

### 3.4 🟡 Condición de Carrera

**Escenario:** La caché se aplica instantáneamente, pero la API tarda en responder.

```
T0: Usuario carga app → ve tema de caché (v1)
T1: API responde con tema actualizado (v2)
T2: Flash de cambio de colores visible al usuario
```

**Impacto:** Experiencia visual inconsistente (parpadeo de colores).

---

## 4. Archivos Involucrados

| Archivo | Líneas Clave | Responsabilidad |
|---------|--------------|-----------------|
| `src/context/ThemeContext.jsx` | 1-658 | Gestión de estado, caché, API |
| `src/context/contexts.js` | - | Exportación del contexto |
| `src/pages/ConfiguracionTema.jsx` | 1-1587 | UI de administración |
| `src/services/api.js` | 475-520 | Definición de endpoints |
| `src/index.css` | 1-150 | Variables CSS por defecto |
| `src/App.jsx` | 1-210 | Proveedor raíz (ThemeProvider) |
| `backend/core/models.py` | 1755-2327 | Modelo TemaGlobal |
| `backend/core/views.py` | 1575-1750 | ViewSet API |
| `backend/core/serializers.py` | - | Serialización |

---

## 5. Análisis de la Propuesta Original vs Estado Actual

| Propuesta Original | Estado Actual | Acción Requerida |
|--------------------|---------------|------------------|
| Fuente de verdad en Supabase | ⚠️ Django/SQLite (no Supabase) | No aplica - diferente arquitectura |
| Persistencia en localStorage | ✅ **YA IMPLEMENTADO** | - |
| Carga inicial antes de render | ✅ **YA IMPLEMENTADO** (líneas 217-280) | - |
| Endpoint público | ✅ `/api/tema/activo/` sin auth | - |
| Caché con invalidación por `updated_at` | ⚠️ Se guarda pero no se valida | **Mejorar** |
| Fallback con registro de error | ⚠️ Solo console.warn | **Mejorar** |

---

## 6. Mejoras Recomendadas

### 6.1 Prioridad Alta

#### A. Validación de Caché con `updated_at`

```javascript
// En cargarTema(), antes de usar caché:
const cacheUpdatedAt = localStorage.getItem(STORAGE_KEY_UPDATED);
try {
  const { data: serverMeta } = await temaGlobalAPI.getMetadata(); // Nuevo endpoint ligero
  if (serverMeta.updated_at !== cacheUpdatedAt) {
    invalidarCacheTema(); // Forzar recarga desde API
  }
} catch (e) { /* usar caché como fallback */ }
```

#### B. Fallback de Logos con Placeholders

```jsx
// En componentes que usan logos:
<img 
  src={logoHeaderUrl} 
  onError={(e) => { e.target.src = '/assets/logo-fallback.svg'; }}
  alt="Logo institucional"
/>
```

#### C. Indicador de Carga de Tema

```jsx
// En ThemeProvider, bloquear render hasta que tema esté listo:
if (!temaAplicado && cargando) {
  return <ThemeLoadingScreen />; // Pantalla de carga con colores neutrales
}
```

### 6.2 Prioridad Media

#### D. Polling Periódico (cada 5 min)

```javascript
useEffect(() => {
  const interval = setInterval(cargarTema, 5 * 60 * 1000);
  return () => clearInterval(interval);
}, [cargarTema]);
```

#### E. Service Worker para Caché Offline

```javascript
// sw.js
self.addEventListener('fetch', (event) => {
  if (event.request.url.includes('/api/tema/activo/')) {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        return fetch(event.request)
          .then((response) => {
            caches.open('tema-cache').then(cache => cache.put(event.request, response.clone()));
            return response;
          })
          .catch(() => cached);
      })
    );
  }
});
```

### 6.3 Prioridad Baja

#### F. Audit Log en Frontend

```javascript
const aplicarTemaCompleto = (tema, source) => {
  console.info(`[TEMA] Aplicando desde ${source}:`, tema.nombre);
  // ... resto de la función
};
```

---

## 7. Diagrama de Flujo Mejorado

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FLUJO DE CARGA DE TEMA (MEJORADO)                    │
└─────────────────────────────────────────────────────────────────────────────┘

Usuario abre app
       │
       ▼
┌──────────────────┐
│ ¿Hay caché local?│
└────────┬─────────┘
         │
    ┌────┴────┐
    │         │
   SÍ        NO
    │         │
    ▼         │
┌───────────┐ │
│ Aplicar   │ │
│ caché     │ │
│ (rápido)  │ │
└─────┬─────┘ │
      │       │
      └───┬───┘
          │
          ▼
┌─────────────────────┐
│ Consultar API       │
│ /api/tema/activo/   │
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     │           │
  ÉXITO       ERROR
     │           │
     ▼           ▼
┌──────────┐  ┌─────────────────┐
│ Comparar │  │ ¿Tenía caché?   │
│ updated_at│  └────────┬────────┘
└────┬─────┘           │
     │            ┌────┴────┐
     ▼            │         │
┌──────────┐     SÍ        NO
│ ¿Cambió? │      │         │
└────┬─────┘      ▼         ▼
     │       ┌────────┐  ┌────────────┐
  ┌──┴──┐    │Mantener│  │Usar        │
  │     │    │caché   │  │temaDefault │
 SÍ    NO    │actual  │  │+ LOG ERROR │
  │     │    └────────┘  └────────────┘
  ▼     ▼
┌────────────┐
│ Actualizar │
│ estado +   │
│ caché      │
└────────────┘
         │
         ▼
┌─────────────────────┐
│ Render app con tema │
│ aplicado            │
└─────────────────────┘
```

---

## 8. Conclusiones

### Lo que YA funciona:
1. ✅ Persistencia en localStorage con rehidratación rápida
2. ✅ Endpoint público para acceso sin sesión
3. ✅ Modelo robusto en backend con 50+ campos configurables
4. ✅ Generación automática de CSS variables

### Lo que necesita mejora:
1. ⚠️ Invalidación de caché basada en `updated_at`
2. ⚠️ Manejo de logos inaccesibles (fallbacks)
3. ⚠️ Bloqueo de render durante carga inicial
4. ⚠️ Logging estructurado de errores

### Esfuerzo estimado:
- Mejoras de Prioridad Alta: **4-6 horas**
- Mejoras de Prioridad Media: **8-12 horas**
- Mejoras de Prioridad Baja: **2-4 horas**

---

## 9. Apéndice: Código Relevante

### A. Funciones de Caché (ThemeContext.jsx)

```javascript
// Líneas 29-73
const guardarTemaEnCache = (tema) => { ... };
const obtenerTemaDeCache = () => { ... };
const invalidarCacheTema = () => { ... };
```

### B. Endpoint Público (views.py)

```python
# Líneas 1602-1612
@action(detail=False, methods=['get'], url_path='activo')
def tema_activo(self, request):
    tema = TemaGlobal.get_tema_activo()
    serializer = TemaGlobalPublicoSerializer(tema, context={'request': request})
    return Response(serializer.data)
```

### C. Modelo con CSS Variables (models.py)

```python
# Líneas 2144-2245
def to_css_variables(self):
    return {
        '--color-primary': self.color_primario,
        '--color-primary-hover': self.color_primario_hover,
        # ... 40+ variables más
    }
```

---

*Documento generado tras análisis de código fuente del repositorio `farmacia_penitenciaria`, rama `dev`.*
