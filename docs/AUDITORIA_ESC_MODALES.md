# Auditoría ESC en Modales - Sistema Farmacia Penitenciaria

## Estado: EN PROGRESO
**Fecha inicio:** 2026-03-05  
**Objetivo:** 100% cobertura ESC en modales/overlays  
**Reglas:** LIFO stack, respeta loading, ESC=Cancelar, no memory leaks  

---

## ✅ COMPLETADO (14 modales)

### 1. Dispensaciones.jsx - 7 modales
| Modal | ID | ESC ? | LIFO? | disabled? | Riesgo |
|-------|----|----|-------|-----------|--------|
| showModal (form) | `dispensaciones-form-modal` | ✅ | ✅ | loading | BAJO |
| detailModal | `dispensaciones-detail-modal` | ✅ | ✅ | no | BAJO |
| cancelModal | `dispensaciones-cancel-modal` | ✅ | ✅ | no | BAJO |
| dispensarModal | `dispensaciones-dispensar-modal` | ✅ | ✅ | loading | BAJO |
| historialModal | `dispensaciones-historial-modal` | ✅ | ✅ | no | BAJO |
| reporteModal | `dispensaciones-reporte-modal` | ✅ | ✅ | no | BAJO |
| formatoCModal | `dispensaciones-formatoc-modal` | ✅ | ✅ | loading | BAJO |

### 2. ComprasCajaChica.jsx - 7 modales
| Modal | ID | ESC ? | LIFO? | disabled? | Riesgo |
|-------|----|----|-------|-----------|--------|
| showModal (form) | `compras-caja-chica-form-modal` | ✅ | ✅ | loading | BAJO |
| detailModal | `compras-caja-chica-detail-modal` | ✅ | ✅ | no | BAJO |
| cancelModal | `compras-caja-chica-cancel-modal` | ✅ | ✅ | no | BAJO |
| autorizarModal | `compras-caja-chica-autorizar-modal` | ✅ | ✅ | no | BAJO |
| registrarCompraModal | `compras-caja-chica-registrar-modal` | ✅ | ✅ | no | BAJO |
| recibirModal | `compras-caja-chica-recibir-modal` | ✅ | ✅ | no | BAJO |
| stockRechazoModal | `compras-caja-chica-stock-rechazo-modal` | ✅ | ✅ | no | BAJO |

---

## ❌ PENDIENTE (36+ modales)

### 3. Productos.jsx - 4 modales
| Modal | Línea | ESC ? | LIFO? | Riesgo |
|-------|-------|-------|-------|--------|
| showModal | 2248 | ❌ | ❌ | ALTO |
| auditoriaModal | 2667 | ❌ | ❌ | MEDIO |
| historialModal | 2824 | ❌ | ❌ | MEDIO |
| showImportModal | 2942 | ❌ | ❌ | ALTO |

### 4. Donaciones.jsx - 10+ modales
| Modal | Línea | ESC ? | LIFO? | Riesgo |
|-------|-------|-------|-------|--------|
| showModal | 2973 | ❌ | ❌ | ALTO |
| showDetalleModal | 3233 | ❌ | ❌ | ALTO |
| confirmAceptar | 3433 | ❌ | ❌ | CRITICO |
| showSalidaModal | 3494 | ❌ | ❌ | ALTO |
| showHistorialModal | 3625 | ❌ | ❌ | MEDIO |
| showCatalogoModal | 3723 | ❌ | ❌ | ALTO |
| showQuickProductModal | 3864 | ❌ | ❌ | MEDIO |
| showBulkAddModal | 3953 | ❌ | ❌ | MEDIO |
| confirmMermaModal | 4123 | ❌ | ❌ | CRITICO |
| confirmEliminar | ~4200+ | ❌ | ❌ | CRITICO |

### 5. Lotes.jsx - 4 modales
| Modal | Línea | ESC ? | LIFO? | Riesgo |
|-------|-------|-------|-------|--------|
| showModal | 2074 | ❌ | ❌ | ALTO |
| showImportModal | 2666 | ❌ | ❌ | ALTO |
| showDocModal | 2695 | ❌ | ❌ | MEDIO |
| showParcialidadesModal | 2798 | ❌ | ❌ | MEDIO |

### 6. Movimientos.jsx - 6 modales
| Modal | Línea | ESC ? | LIFO? | Riesgo |
|-------|-------|-------|-------|--------|
| showSalidaMasiva | ~3700 | ❌ | ❌ | ALTO |
| detalleEntradaModal | 3737 | ❌ | ❌ | MEDIO |
| detalleSalidaModal | 3752 | ❌ | ❌ | MEDIO |
| detalleTraspasModal | 3797 | ❌ | ❌ | MEDIO |
| detalleAjusteModal | 3873 | ❌ | ❌ | MEDIO |
| confirmModal | ~3900+ | ❌ | ❌ | CRITICO |

### 7. Requisiciones.jsx - 2 modales
| Modal | Línea | ESC ? | LIFO? | Riesgo |
|-------|-------|-------|-------|--------|
| showModal | 2196 | ❌ | ❌ | AL TO |
| confirmModal | 2735 | ❌ | ❌ | CRITICO |

### 8. Pacientes.jsx - 3 modales
| Modal | Línea | ESC ? | LIFO? | Riesgo |
|-------|-------|-------|-------|--------|
| showModal | 736 | ❌ | ❌ | ALTO |
| detailModal | ~800+ | ❌ | ❌ | MEDIO |
| traspasoModal | ~900+ | ❌ | ❌ | MEDIO |

### 9. Centros.jsx - 2 modales
| Modal | Línea | ESC ? | LIFO? | Riesgo |
|-------|-------|-------|-------|--------|
| showModal | 687 | ❌ | ❌ | ALTO |
| showImportModal | 789 | ❌ | ❌ | ALTO |

### 10. InventarioCajaChica.jsx - 3 modales
| Modal | Línea | ESC ? | LIFO? | Riesgo |
|-------|-------|-------|-------|--------|
| salidaModal | 587 | ❌ | ❌ | ALTO |
| ajusteModal | 658 | ❌ | ❌ | ALTO |
| movimientosModal | 717 | ❌ | ❌ | MEDIO |

### 11. ConfiguracionTema.jsx - 1 modal
| Modal | Línea | ESC ? | LIFO? | Riesgo |
|-------|-------|-------|-------|--------|
| confirmState (ConfirmModal) | 1677 | ✅ | ✅ | BAJO (usa componente base) |

---

## 📊 Resumen Cobertura

| Estado | Cantidad | % Cobertura |
|--------|----------|-------------|
| ✅ Instrumentado | 14 | 28% |
| ❌ Pendiente | 36+ | 72% |
| **TOTAL** | **50+** | **100%** |

---

## 🔧 Plan de Acción

### Prioridad CRÍTICA (hacer primero)
1. **Donaciones.jsx** - confirmAceptar, confirmMermaModal, confirmEliminar (CRITICO - operaciones de dinero/merma)
2. **Movimientos.jsx** - confirmModal (CRITICO - afecta inventario)
3. **Requisiciones.jsx** - confirmModal (CRITICO - afecta flujo operativo)

### Prioridad ALTA (hacer después)
4. **Productos.jsx** - 4 modales (CRUD principal del sistema)
5. **Lotes.jsx** - 4 modales (entrada de inventario)
6. **Pacientes.jsx** - 3 modales (datos sensibles)
7. **Centros.jsx** - 2 modales (configuración)
8. **InventarioCajaChica.jsx** - 3 modales (operaciones inventario)

### Prioridad MEDIA
9. **Donaciones.jsx** - resto de modales informativos
10. **Movimientos.jsx** - modales de detalle

---

## ✅ Checklist Técnico

| Verificación | Estado |
|--------------|--------|
| ModalStackProvider envuelve App | ✅ |
| useEscapeToClose hook creado | ✅ |
| Componentes base instrumentados (ConfirmModal, TwoStepConfirmModal) | ✅ |
| registerModal/unregisterModal simétricos | ✅ |
| No listeners duplicados por re-render | ✅ |
| isTopModal() verifica antes de cerrar | ✅ |
| disabled prop durante loading | ✅ |
| Auto-cleanup de listeners | ✅ |
| Sin conflicto con modales externos | ⚠️ (pendiente verificar) |
| Funciona con React Portals | ⚠️ (pendiente verificar) |

---

## 🧪 Plan de Pruebas (Post-Instrumentación)

### A) Escenarios Base
- [ ] Abrir modal → ESC cierra
- [ ] Modal confirmación → ESC = Cancelar
- [ ] Foco en input → ESC cierra modal
- [ ] Autocomplete abierto → 1er ESC cierra dropdown, 2do ESC cierra modal

### B) Pila LIFO
- [ ] Modal A → Modal B → ESC cierra B → ESC cierra A
- [ ] 3 niveles: A→B→C → ESC secuencial correcto

### C) Estados Críticos
- [ ] Durante "guardando" → ESC deshabilitado
- [ ] Spam ESC → sin errores ni cierres incorrectos

### D) Edge Cases
- [ ] Abrir/cerrar 10 veces → sin memory leaks
- [ ] Cambio de ruta con modal abierto → cleanup correcto
- [ ] Chrome + Edge + Firefox → consistencia

---

## 🎯 Definition of Done

- [ ] 100% modales/overlays soportan ESC
- [ ] LIFO validado en modales anidados
- [ ] Confirmaciones: ESC = Cancelar (nunca Aceptar)
- [ ] Loading: ESC no rompe operaciones
- [ ] 0 errores en consola
- [ ] 0 memory leaks
- [ ] Plan de pruebas PASS
- [ ] Commit con mensaje descriptivo
- [ ] Deploy a producción
- [ ] QA validation en prod

---

## 📝 Notas

- **Componentes base (ConfirmModal, TwoStepConfirmModal)** ya tienen ESC - todos los usos heredan funcionalidad
- **ConfiguracionTema.jsx** usa ConfirmModal → ya funciona ESC
- **Centros.jsx, Lotes.jsx, Productos.jsx** usan ConfirmModal → sus confirmaciones ya funcionan
- **Pendiente:** Modales custom que usan `fixed inset-0` directamente → requieren instrumentación manualmental

---

**Actualizado:** 2026-03-05 | **Responsable:** GitHub Copilot (Claude Sonnet 4.5)
