# Checklist de Verificación - Panel Auditoría SUPER ADMIN

## Resumen de Implementación

El Panel de Auditoría SUPER ADMIN proporciona trazabilidad completa de todas las acciones del sistema.

### Componentes Implementados

| Componente | Archivo | Estado |
|------------|---------|--------|
| SQL Migration | `backend/migrations_sql/003_auditoria_super_admin.sql` | ✅ Creado |
| SQL Rollback | `backend/migrations_sql/003_auditoria_super_admin_rollback.sql` | ✅ Creado |
| AuditMiddleware | `backend/core/middleware.py` | ✅ Implementado |
| AuditoriaLogs Model | `backend/core/models.py` | ✅ Extendido |
| Serializers | `backend/core/serializers.py` | ✅ Actualizados |
| ViewSet | `backend/core/views.py` | ✅ Reescrito |
| Settings | `backend/config/settings.py` | ✅ Configurado |
| API Service | `inventario-front/src/services/api.js` | ✅ Extendido |
| Página Auditoría | `inventario-front/src/pages/Auditoria.jsx` | ✅ Creado |
| Ruta | `inventario-front/src/App.jsx` | ✅ Agregada |
| Menú | `inventario-front/src/components/Layout.jsx` | ✅ Agregado |

---

## Checklist de Verificación Pre-Producción

### 1. Migración SQL en Supabase

- [ ] Ejecutar `003_auditoria_super_admin.sql` en Supabase SQL Editor
- [ ] Verificar que las columnas nuevas existan:
  ```sql
  SELECT column_name FROM information_schema.columns 
  WHERE table_name = 'auditoria_logs';
  ```
- [ ] Verificar índices creados:
  ```sql
  SELECT indexname FROM pg_indexes WHERE tablename = 'auditoria_logs';
  ```
- [ ] Verificar vistas creadas:
  ```sql
  SELECT viewname FROM pg_views WHERE viewname LIKE '%audit%';
  ```

### 2. Backend - Django

- [ ] Reiniciar servidor Django después de migración
- [ ] Probar que middleware no genere errores 500:
  ```bash
  curl -X GET https://your-api/api/ -H "Authorization: Bearer TOKEN"
  ```
- [ ] Verificar logs de auditoría se crean (hacer login y verificar en DB)

### 3. Permisos - SUPER ADMIN

- [ ] **TEST CRÍTICO**: Usuario sin `is_superuser=True` debe recibir 403:
  ```bash
  curl -X GET https://your-api/api/auditoria-logs/ \
    -H "Authorization: Bearer TOKEN_USUARIO_NORMAL"
  # Esperado: 403 Forbidden
  ```
- [ ] **TEST CRÍTICO**: Usuario con `is_superuser=True` debe acceder:
  ```bash
  curl -X GET https://your-api/api/auditoria-logs/ \
    -H "Authorization: Bearer TOKEN_SUPER_ADMIN"
  # Esperado: 200 con datos
  ```

### 4. Frontend - Panel

- [ ] Verificar que menú "Auditoría" solo aparece para SUPER ADMIN
- [ ] Verificar que `/auditoria` muestra "Acceso Restringido" para usuarios normales
- [ ] Probar filtros:
  - [ ] Fecha inicio/fin
  - [ ] Usuario
  - [ ] Centro
  - [ ] Módulo
  - [ ] Acción
  - [ ] Resultado (success/fail)
  - [ ] Método HTTP
- [ ] Probar paginación (siguiente/anterior)
- [ ] Probar vista detalle (modal con before/after)
- [ ] Probar exportación Excel
- [ ] Probar exportación PDF

### 5. Seguridad

- [ ] Verificar que campos sensibles NO aparecen en auditoría:
  - password
  - token
  - secret
  - api_key
  - refresh_token
- [ ] Verificar que request_id se genera correctamente (UUID v4)

### 6. Performance

- [ ] Verificar que lista de auditoría carga en < 2 segundos
- [ ] Verificar que filtros funcionan con índices (sin full table scan)
- [ ] Verificar que estadísticas `/stats/` responden rápido

---

## Endpoints Disponibles

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/auditoria-logs/` | GET | Lista paginada con filtros |
| `/api/auditoria-logs/{id}/` | GET | Detalle de un evento |
| `/api/auditoria-logs/stats/` | GET | Estadísticas de actividad |
| `/api/auditoria-logs/modulos/` | GET | Lista de módulos registrados |
| `/api/auditoria-logs/acciones/` | GET | Lista de acciones registradas |
| `/api/auditoria-logs/criticos/` | GET | Eventos críticos recientes |
| `/api/auditoria-logs/exportar/` | GET | Exportar a Excel |
| `/api/auditoria-logs/exportar-pdf/` | GET | Exportar a PDF |

## Filtros Disponibles

| Parámetro | Tipo | Ejemplo |
|-----------|------|---------|
| `fecha_inicio` | date | `2025-01-01` |
| `fecha_fin` | date | `2025-01-31` |
| `usuario` | string | `admin` |
| `centro` | integer | `1` |
| `modulo` | string | `PRODUCTOS` |
| `accion` | string | `CREAR` |
| `resultado` | string | `success`, `fail` |
| `metodo` | string | `GET`, `POST`, `DELETE` |
| `objeto_id` | string | `123` |
| `request_id` | uuid | `550e8400-e29b-41d4-a716-446655440000` |

---

## Configuración en Settings

```python
# backend/config/settings.py
AUDIT_ENABLED = True           # Habilita auditoría
AUDIT_LOG_READS = False        # No loguear GETs (volumen alto)
AUDIT_EXCLUDE_PATHS = [        # Rutas excluidas
    '/api/health/',
    '/api/token/',
    '/api/notifications/',
]
```

---

## Troubleshooting

### Error: "Column does not exist"
La migración SQL no se ha ejecutado. Correr `003_auditoria_super_admin.sql` en Supabase.

### Error: 403 para SUPER ADMIN
Verificar que el usuario tiene `is_superuser=True` en la tabla `usuarios`:
```sql
SELECT id, username, is_superuser FROM usuarios WHERE username = 'tu_usuario';
UPDATE usuarios SET is_superuser = true WHERE username = 'admin';
```

### El menú no aparece
Verificar que `usePermissions()` devuelve `user` con `is_superuser: true`.

### Los logs no se registran
1. Verificar que `AUDIT_ENABLED = True` en settings
2. Verificar que el middleware está en la lista de MIDDLEWARE
3. Revisar logs de Django para errores del middleware

---

## Rollback

Si necesitas revertir los cambios:
```sql
-- En Supabase SQL Editor:
-- Ejecutar el contenido de: backend/migrations_sql/003_auditoria_super_admin_rollback.sql
```

Esto eliminará las columnas agregadas, índices, vistas y funciones.

---

**Fecha de implementación**: $(date)
**Versión**: 1.0.0
