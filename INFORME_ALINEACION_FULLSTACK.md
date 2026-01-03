# Informe de Alineación: Frontend, Backend y Base de Datos

**Fecha:** Generado automáticamente  
**Proyecto:** Sistema Farmacia Penitenciaria  

---

## 📊 Resumen Ejecutivo

| Aspecto | Estado |
|---------|--------|
| **Modelos Django ↔ Tablas BD** | ✅ ALINEADOS (23 tablas con modelo) |
| **APIs Backend ↔ Endpoints** | ✅ CORRECTO |
| **Frontend ↔ Backend APIs** | ⚠️ REVISAR (pequeñas diferencias) |

---

## 1. TABLAS EN BASE DE DATOS vs MODELOS DJANGO

### ✅ Tablas con Modelo Definido (23 tablas)

| Tabla BD | Modelo Django | db_table | Estado |
|----------|---------------|----------|--------|
| `usuarios` | `User` | ✅ usuarios | ALINEADO |
| `centros` | `Centro` | ✅ centros | ALINEADO |
| `productos` | `Producto` | ✅ productos | ALINEADO |
| `lotes` | `Lote` | ✅ lotes | ALINEADO |
| `movimientos` | `Movimiento` | ✅ movimientos | ALINEADO |
| `requisiciones` | `Requisicion` | ✅ requisiciones | ALINEADO |
| `detalles_requisicion` | `DetalleRequisicion` | ✅ detalles_requisicion | ALINEADO |
| `notificaciones` | `Notificacion` | ✅ notificaciones | ALINEADO |
| `tema_global` | `TemaGlobal` | ✅ tema_global | ALINEADO |
| `configuracion_sistema` | `ConfiguracionSistema` | ✅ configuracion_sistema | ALINEADO |
| `hojas_recoleccion` | `HojaRecoleccion` | ✅ hojas_recoleccion | ALINEADO |
| `detalle_hojas_recoleccion` | `DetalleHojaRecoleccion` | ✅ detalle_hojas_recoleccion | ALINEADO |
| `importacion_logs` | `ImportacionLogs` | ✅ importacion_logs | ALINEADO |
| `auditoria_logs` | `AuditoriaLogs` | ✅ auditoria_logs | ALINEADO |
| `user_profiles` | `UserProfile` | ✅ user_profiles | ALINEADO |
| `producto_imagenes` | `ProductoImagen` | ✅ producto_imagenes | ALINEADO |
| `lote_documentos` | `LoteDocumento` | ✅ lote_documentos | ALINEADO |
| `productos_donacion` | `ProductoDonacion` | ✅ productos_donacion | ALINEADO |
| `donaciones` | `Donacion` | ✅ donaciones | ALINEADO |
| `detalle_donaciones` | `DetalleDonacion` | ✅ detalle_donaciones | ALINEADO |
| `salidas_donaciones` | `SalidaDonacion` | ✅ salidas_donaciones | ALINEADO |
| `requisicion_historial_estados` | `RequisicionHistorialEstados` | ✅ requisicion_historial_estados | ALINEADO |
| `requisicion_ajustes_cantidad` | `RequisicionAjusteCantidad` | ✅ requisicion_ajustes_cantidad | ALINEADO |

### 🔄 Tablas Gestionadas por Django (sin modelo personalizado)

| Tabla BD | Descripción | Estado |
|----------|-------------|--------|
| `auth_group` | Grupos de Django | ✅ Automático |
| `auth_group_permissions` | Permisos de grupo | ✅ Automático |
| `auth_permission` | Permisos Django | ✅ Automático |
| `usuarios_groups` | Relación User-Groups | ✅ Automático |
| `usuarios_user_permissions` | Permisos de usuario | ✅ Automático |
| `django_admin_log` | Log de admin | ✅ Automático |
| `django_content_type` | Content types | ✅ Automático |
| `django_migrations` | Migraciones | ✅ Automático |
| `django_session` | Sesiones | ✅ Automático |

---

## 2. VERIFICACIÓN DE CAMPOS POR TABLA PRINCIPAL

### ✅ Tabla `usuarios` vs Modelo `User`

| Campo BD | Tipo BD | Campo Modelo | Estado |
|----------|---------|--------------|--------|
| `id` | bigint PK | ✅ id | ✅ OK |
| `username` | varchar(150) | ✅ username | ✅ OK |
| `email` | varchar(254) | ✅ email | ✅ OK |
| `password` | varchar(128) | ✅ password | ✅ OK |
| `first_name` | varchar(150) | ✅ first_name | ✅ OK |
| `last_name` | varchar(150) | ✅ last_name | ✅ OK |
| `is_active` | boolean | ✅ is_active | ✅ OK |
| `is_staff` | boolean | ✅ is_staff | ✅ OK |
| `is_superuser` | boolean | ✅ is_superuser | ✅ OK |
| `date_joined` | timestamp | ✅ date_joined | ✅ OK |
| `last_login` | timestamp | ✅ last_login | ✅ OK |
| `rol` | varchar(30) | ✅ rol | ✅ OK |
| `centro_id` | bigint FK | ✅ centro | ✅ OK |
| `telefono` | varchar(20) | ✅ telefono | ✅ OK |
| `puede_crear_lotes` | boolean | ✅ puede_crear_lotes | ✅ OK |
| `recibir_alertas_email` | boolean | ✅ recibir_alertas_email | ✅ OK |
| `recibir_alertas_sistema` | boolean | ✅ recibir_alertas_sistema | ✅ OK |

### ✅ Tabla `productos` vs Modelo `Producto`

| Campo BD | Tipo BD | Campo Modelo | Estado |
|----------|---------|--------------|--------|
| `id` | bigint PK | ✅ id | ✅ OK |
| `clave` | varchar(50) UNIQUE | ✅ clave | ✅ OK |
| `nombre` | varchar(255) | ✅ nombre | ✅ OK |
| `descripcion` | text | ✅ descripcion | ✅ OK |
| `unidad_medida` | varchar(50) | ✅ unidad_medida | ✅ OK |
| `stock_minimo` | integer | ✅ stock_minimo | ✅ OK |
| `stock` | integer | ✅ stock | ✅ OK |
| `precio_unitario` | numeric(10,2) | ✅ precio_unitario | ✅ OK |
| `categoria` | varchar(100) | ✅ categoria | ✅ OK |
| `presentacion` | varchar(100) | ✅ presentacion | ✅ OK |
| `principio_activo` | varchar(255) | ✅ principio_activo | ✅ OK |
| `concentracion` | varchar(100) | ✅ concentracion | ✅ OK |
| `laboratorio` | varchar(150) | ✅ laboratorio | ✅ OK |
| `temperatura_almacenamiento` | varchar(100) | ✅ temperatura_almacenamiento | ✅ OK |
| `codigo_barras` | varchar(100) | ✅ codigo_barras | ✅ OK |
| `registro_sanitario` | varchar(100) | ✅ registro_sanitario | ✅ OK |
| `activo` | boolean | ✅ activo | ✅ OK |
| `imagen` | varchar(255) | ✅ imagen | ✅ OK |
| `created_at` | timestamp | ✅ created_at | ✅ OK |
| `updated_at` | timestamp | ✅ updated_at | ✅ OK |

### ✅ Tabla `lotes` vs Modelo `Lote`

| Campo BD | Tipo BD | Campo Modelo | Estado |
|----------|---------|--------------|--------|
| `id` | bigint PK | ✅ id | ✅ OK |
| `numero_lote` | varchar(100) UNIQUE | ✅ numero_lote | ✅ OK |
| `producto_id` | bigint FK | ✅ producto | ✅ OK |
| `centro_id` | bigint FK | ✅ centro | ✅ OK |
| `cantidad_inicial` | integer | ✅ cantidad_inicial | ✅ OK |
| `cantidad_actual` | integer | ✅ cantidad_actual | ✅ OK |
| `fecha_fabricacion` | date | ✅ fecha_fabricacion | ✅ OK |
| `fecha_caducidad` | date | ✅ fecha_caducidad | ✅ OK |
| `fecha_entrada` | timestamp | ✅ fecha_entrada | ✅ OK |
| `precio_unitario` | numeric(10,2) | ✅ precio_unitario | ✅ OK |
| `proveedor` | varchar(200) | ✅ proveedor | ✅ OK |
| `ubicacion` | varchar(100) | ✅ ubicacion | ✅ OK |
| `notas` | text | ✅ notas | ✅ OK |
| `estado` | varchar(50) | ✅ estado | ✅ OK |
| `codigo_barra_lote` | varchar(100) | ✅ codigo_barra_lote | ✅ OK |
| `created_by_id` | bigint FK | ✅ created_by | ✅ OK |
| `origen` | varchar(50) | ✅ origen | ✅ OK |
| `created_at` | timestamp | ✅ created_at | ✅ OK |
| `updated_at` | timestamp | ✅ updated_at | ✅ OK |

### ✅ Tabla `requisiciones` vs Modelo `Requisicion`

**Estado:** ✅ COMPLETAMENTE ALINEADO - 40+ campos del flujo V2 verificados

Los campos clave incluyen:
- `id`, `numero`, `tipo`, `estado`, `centro_id`, `usuario_id`
- Flujo V2: `fecha_envio_admin`, `enviado_admin_por_id`, `fecha_autorizacion_admin`...
- Confirmación: `fecha_confirmacion_entrega`, `confirmado_entrega_por_id`
- Timestamps: `created_at`, `updated_at`

### ✅ Tabla `movimientos` vs Modelo `Movimiento`

| Campo BD | Tipo BD | Campo Modelo | Estado |
|----------|---------|--------------|--------|
| `id` | bigint PK | ✅ id | ✅ OK |
| `tipo` | varchar(50) | ✅ tipo | ✅ OK |
| `producto_id` | bigint FK | ✅ producto | ✅ OK |
| `lote_id` | bigint FK | ✅ lote | ✅ OK |
| `cantidad` | integer | ✅ cantidad | ✅ OK |
| `usuario_id` | bigint FK | ✅ usuario | ✅ OK |
| `centro_origen_id` | bigint FK | ✅ centro_origen | ✅ OK |
| `centro_destino_id` | bigint FK | ✅ centro_destino | ✅ OK |
| `requisicion_id` | bigint FK | ✅ requisicion | ✅ OK |
| `subtipo_salida` | varchar(50) | ✅ subtipo_salida | ✅ OK |
| `numero_expediente` | varchar(100) | ✅ numero_expediente | ✅ OK |
| `motivo_merma` | varchar(100) | ✅ motivo_merma | ✅ OK |
| `motivo_devolucion` | varchar(100) | ✅ motivo_devolucion | ✅ OK |
| `notas` | text | ✅ notas | ✅ OK |
| `fecha` | timestamp | ✅ fecha | ✅ OK |
| `created_at` | timestamp | ✅ created_at | ✅ OK |
| `grupo_salida` | varchar(50) | ✅ grupo_salida | ✅ OK |

---

## 3. APIs FRONTEND vs BACKEND ENDPOINTS

### ✅ Endpoints REST Principales

| API Frontend | Método | Endpoint Backend | Registrado Router | Estado |
|--------------|--------|------------------|-------------------|--------|
| `productosAPI.getAll()` | GET | `/api/productos/` | ✅ ProductoViewSet | ✅ OK |
| `productosAPI.create()` | POST | `/api/productos/` | ✅ ProductoViewSet | ✅ OK |
| `productosAPI.update()` | PUT | `/api/productos/{id}/` | ✅ ProductoViewSet | ✅ OK |
| `productosAPI.delete()` | DELETE | `/api/productos/{id}/` | ✅ ProductoViewSet | ✅ OK |
| `lotesAPI.getAll()` | GET | `/api/lotes/` | ✅ LoteViewSet | ✅ OK |
| `lotesAPI.create()` | POST | `/api/lotes/` | ✅ LoteViewSet | ✅ OK |
| `centrosAPI.getAll()` | GET | `/api/centros/` | ✅ CentroViewSet | ✅ OK |
| `usuariosAPI.getAll()` | GET | `/api/usuarios/` | ✅ UserViewSet | ✅ OK |
| `usuariosAPI.me()` | GET | `/api/usuarios/me/` | ✅ @action | ✅ OK |
| `requisicionesAPI.getAll()` | GET | `/api/requisiciones/` | ✅ RequisicionViewSet | ✅ OK |
| `movimientosAPI.getAll()` | GET | `/api/movimientos/` | ✅ MovimientoViewSet | ✅ OK |
| `auditoriaAPI.getAll()` | GET | `/api/auditoria/` | ✅ AuditoriaLogViewSet | ✅ OK |
| `notificacionesAPI.getAll()` | GET | `/api/notificaciones/` | ✅ NotificacionViewSet | ✅ OK |
| `donacionesAPI.getAll()` | GET | `/api/donaciones/` | ✅ DonacionViewSet | ✅ OK |
| `productosDonacionAPI.getAll()` | GET | `/api/productos-donacion/` | ✅ ProductoDonacionViewSet | ✅ OK |
| `salidasDonacionesAPI.getAll()` | GET | `/api/salidas-donaciones/` | ✅ SalidaDonacionViewSet | ✅ OK |
| `hojasRecoleccionAPI.getAll()` | GET | `/api/hojas-recoleccion/` | ✅ HojaRecoleccionViewSet | ✅ OK |

### ✅ Endpoints Funcionales

| API Frontend | Método | Endpoint Backend | Estado |
|--------------|--------|------------------|--------|
| `authAPI.login()` | POST | `/api/token/` | ✅ OK |
| `authAPI.logout()` | POST | `/api/logout/` | ✅ OK |
| `authAPI.refresh()` | POST | `/api/token/refresh/` | ✅ OK |
| `dashboardAPI.resumen()` | GET | `/api/dashboard/` | ✅ OK |
| `dashboardAPI.graficas()` | GET | `/api/dashboard/graficas/` | ✅ OK |
| `trazabilidadAPI.buscar()` | GET | `/api/trazabilidad/buscar/` | ✅ OK |
| `trazabilidadAPI.autocomplete()` | GET | `/api/trazabilidad/autocomplete/` | ✅ OK |
| `trazabilidadAPI.producto()` | GET | `/api/trazabilidad/producto/{clave}/` | ✅ OK |
| `trazabilidadAPI.lote()` | GET | `/api/trazabilidad/lote/{codigo}/` | ✅ OK |
| `trazabilidadAPI.global()` | GET | `/api/trazabilidad/global/` | ✅ OK |
| `reportesAPI.inventario()` | GET | `/api/reportes/inventario/` | ✅ OK |
| `reportesAPI.movimientos()` | GET | `/api/reportes/movimientos/` | ✅ OK |
| `reportesAPI.caducidades()` | GET | `/api/reportes/caducidades/` | ✅ OK |
| `temaGlobalAPI.get()` | GET | `/api/tema/` | ✅ OK |
| `temaGlobalAPI.update()` | PUT | `/api/tema/` | ✅ OK |
| `catalogosAPI.get()` | GET | `/api/catalogos/` | ✅ OK |
| `healthAPI.check()` | GET | `/api/health/` | ✅ OK |

### ✅ Flujo V2 de Requisiciones

| Acción Frontend | Método | Endpoint Backend | Estado |
|-----------------|--------|------------------|--------|
| `enviarAdmin()` | POST | `/api/requisiciones/{id}/enviar_admin/` | ✅ OK |
| `autorizarAdmin()` | POST | `/api/requisiciones/{id}/autorizar_admin/` | ✅ OK |
| `autorizarDirector()` | POST | `/api/requisiciones/{id}/autorizar_director/` | ✅ OK |
| `recibirFarmacia()` | POST | `/api/requisiciones/{id}/recibir_farmacia/` | ✅ OK |
| `autorizarFarmacia()` | POST | `/api/requisiciones/{id}/autorizar_farmacia/` | ✅ OK |
| `surtir()` | POST | `/api/requisiciones/{id}/surtir/` | ✅ OK |
| `confirmarEntrega()` | POST | `/api/requisiciones/{id}/confirmar_entrega/` | ✅ OK |
| `rechazar()` | POST | `/api/requisiciones/{id}/rechazar/` | ✅ OK |
| `cancelar()` | POST | `/api/requisiciones/{id}/cancelar/` | ✅ OK |

---

## 4. DISCREPANCIAS ENCONTRADAS

### ⚠️ Tablas sin Uso en Frontend

| Tabla BD | Modelo Django | API Registrada | Usado en Frontend |
|----------|---------------|----------------|-------------------|
| `producto_imagenes` | ✅ ProductoImagen | ✅ productos-imagenes | ⚠️ Verificar uso |
| `lote_documentos` | ✅ LoteDocumento | ✅ lotes-documentos | ⚠️ Verificar uso |
| `user_profiles` | ✅ UserProfile | ❌ No registrado | ⚠️ Sin API |
| `requisicion_historial_estados` | ✅ RequisicionHistorialEstados | ❌ No registrado | ⚠️ Sin API |
| `requisicion_ajustes_cantidad` | ✅ RequisicionAjusteCantidad | ❌ No registrado | ⚠️ Sin API |
| `detalle_hojas_recoleccion` | ✅ DetalleHojaRecoleccion | ❌ No registrado | ⚠️ Sin API |

**Nota:** Estas tablas son de uso interno/auditoría y no necesariamente requieren API pública.

### 📋 Tablas de Django no Usadas Directamente

Las siguientes tablas son de gestión interna de Django y no requieren modelos personalizados:
- `auth_group`, `auth_group_permissions`, `auth_permission`
- `usuarios_groups`, `usuarios_user_permissions`
- `django_admin_log`, `django_content_type`, `django_migrations`, `django_session`

---

## 5. RECOMENDACIONES

### ✅ Estado General: CORRECTO

El sistema está **bien alineado** entre los tres niveles (BD, Backend, Frontend).

### Mejoras Sugeridas (Opcionales)

1. **UserProfile API**: Considerar exponer `/api/perfil/` si se necesita en frontend
2. **Historial de Requisiciones**: Considerar API de solo lectura para auditoría
3. **ProductoImagen/LoteDocumento**: Verificar si hay componentes frontend que usen estas APIs

---

## 6. VERIFICACIÓN DE CONSISTENCIA DE DATOS

### Tipos de Datos Verificados ✅

| Tipo BD | Modelo Django | Estado |
|---------|---------------|--------|
| `bigint` | `BigAutoField` / `ForeignKey` | ✅ Correcto |
| `varchar(n)` | `CharField(max_length=n)` | ✅ Correcto |
| `text` | `TextField` | ✅ Correcto |
| `boolean` | `BooleanField` | ✅ Correcto |
| `timestamp` | `DateTimeField` | ✅ Correcto |
| `date` | `DateField` | ✅ Correcto |
| `integer` | `IntegerField` | ✅ Correcto |
| `numeric(10,2)` | `DecimalField` | ✅ Correcto |
| `jsonb` | `JSONField` | ✅ Correcto |

### Foreign Keys Verificadas ✅

| Tabla | Campo FK | Tabla Referenciada | Modelo Django | Estado |
|-------|----------|-------------------|---------------|--------|
| productos | - | - | - | ✅ Sin FK |
| lotes | producto_id | productos | `ForeignKey(Producto)` | ✅ OK |
| lotes | centro_id | centros | `ForeignKey(Centro)` | ✅ OK |
| lotes | created_by_id | usuarios | `ForeignKey(User)` | ✅ OK |
| movimientos | producto_id | productos | `ForeignKey(Producto)` | ✅ OK |
| movimientos | lote_id | lotes | `ForeignKey(Lote)` | ✅ OK |
| movimientos | usuario_id | usuarios | `ForeignKey(User)` | ✅ OK |
| movimientos | requisicion_id | requisiciones | `ForeignKey(Requisicion)` | ✅ OK |
| requisiciones | centro_id | centros | `ForeignKey(Centro)` | ✅ OK |
| requisiciones | usuario_id | usuarios | `ForeignKey(User)` | ✅ OK |
| detalles_requisicion | requisicion_id | requisiciones | `ForeignKey(Requisicion)` | ✅ OK |
| detalles_requisicion | producto_id | productos | `ForeignKey(Producto)` | ✅ OK |
| donaciones | centro_destino_id | centros | `ForeignKey(Centro)` | ✅ OK |
| donaciones | recibido_por_id | usuarios | `ForeignKey(User)` | ✅ OK |
| detalle_donaciones | donacion_id | donaciones | `ForeignKey(Donacion)` | ✅ OK |
| salidas_donaciones | detalle_donacion_id | detalle_donaciones | `ForeignKey(DetalleDonacion)` | ✅ OK |

---

## CONCLUSIÓN

✅ **El sistema está correctamente alineado.**

- **23 tablas de negocio** con modelos Django definidos y `managed=False`
- **9 tablas de Django** gestionadas automáticamente
- **Todos los endpoints REST** del frontend corresponden a vistas registradas en backend
- **Flujo V2 de requisiciones** completamente implementado en los 3 niveles
- **Tipos de datos** correctamente mapeados entre PostgreSQL y Django
- **Foreign keys** correctamente definidas en modelos

**No se encontraron discrepancias críticas.**
