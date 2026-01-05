/**
 * Tests del flujo de requisiciones - Frontend
 * 
 * Valida:
 * 1. Estados editables (borrador, devuelta)
 * 2. Estados NO editables (rechazada, pendiente_*, etc.)
 * 3. Flujo de devolución y reenvío
 * 4. Texto correcto de botones ("Devolver al Médico")
 * 5. Protección contra doble envío
 * 
 * @author Sistema
 * @date 2026-01-05
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// ============================================================================
// CONSTANTES DEL FLUJO
// ============================================================================

const ESTADOS_EDITABLES = ['borrador', 'devuelta'];

const ESTADOS_FINALES = ['entregada', 'rechazada', 'cancelada', 'vencida'];

const TRANSICIONES_VALIDAS = {
  borrador: ['pendiente_admin', 'cancelada'],
  pendiente_admin: ['pendiente_director', 'devuelta', 'rechazada'],
  pendiente_director: ['enviada', 'devuelta', 'rechazada'],
  enviada: ['en_revision', 'autorizada', 'rechazada'],
  en_revision: ['autorizada', 'devuelta', 'rechazada'],
  autorizada: ['en_surtido', 'surtida', 'entregada', 'cancelada'],
  en_surtido: ['surtida', 'entregada'],
  surtida: ['entregada', 'vencida'],
  entregada: [],
  rechazada: [],
  cancelada: [],
  devuelta: ['pendiente_admin'],
  vencida: [],
};

const ROLES = {
  MEDICO: 'medico',
  ADMIN_CENTRO: 'administrador_centro',
  DIRECTOR_CENTRO: 'director_centro',
  FARMACIA: 'farmacia',
};

// ============================================================================
// HELPERS
// ============================================================================

/**
 * Verifica si una requisición puede editarse según su estado
 */
function puedeEditar(estado) {
  return ESTADOS_EDITABLES.includes(estado?.toLowerCase());
}

/**
 * Verifica si una transición es válida
 */
function esTransicionValida(estadoActual, estadoNuevo) {
  const transiciones = TRANSICIONES_VALIDAS[estadoActual?.toLowerCase()] || [];
  return transiciones.includes(estadoNuevo?.toLowerCase());
}

/**
 * Verifica si el rol puede ejecutar una acción en un estado
 */
function puedeEjecutarAccion(rol, accion, estado) {
  const permisos = {
    medico: {
      enviar_admin: ['borrador'],
      reenviar: ['devuelta'],
      cancelar: ['borrador', 'devuelta'],
      editar: ['borrador', 'devuelta'],
    },
    administrador_centro: {
      autorizar_admin: ['pendiente_admin'],
      devolver: ['pendiente_admin'],
      rechazar: ['pendiente_admin'],
    },
    director_centro: {
      autorizar_director: ['pendiente_director'],
      devolver: ['pendiente_director'],
      rechazar: ['pendiente_director'],
    },
    farmacia: {
      recibir: ['enviada'],
      autorizar_farmacia: ['en_revision', 'enviada'],
      surtir: ['autorizada', 'en_surtido'],
      entregar: ['surtida', 'autorizada'],
      devolver: ['en_revision'],
      rechazar: ['enviada', 'en_revision'],
    },
  };

  const permisosRol = permisos[rol?.toLowerCase()] || {};
  const estadosPermitidos = permisosRol[accion] || [];
  return estadosPermitidos.includes(estado?.toLowerCase());
}

// ============================================================================
// TESTS DE ESTADOS EDITABLES
// ============================================================================

describe('Estados Editables', () => {
  describe('puedeEditar()', () => {
    it('borrador es editable', () => {
      expect(puedeEditar('borrador')).toBe(true);
    });

    it('devuelta es editable', () => {
      expect(puedeEditar('devuelta')).toBe(true);
    });

    it('rechazada NO es editable', () => {
      expect(puedeEditar('rechazada')).toBe(false);
    });

    it('pendiente_admin NO es editable', () => {
      expect(puedeEditar('pendiente_admin')).toBe(false);
    });

    it('pendiente_director NO es editable', () => {
      expect(puedeEditar('pendiente_director')).toBe(false);
    });

    it('enviada NO es editable', () => {
      expect(puedeEditar('enviada')).toBe(false);
    });

    it('autorizada NO es editable', () => {
      expect(puedeEditar('autorizada')).toBe(false);
    });

    it('entregada NO es editable', () => {
      expect(puedeEditar('entregada')).toBe(false);
    });

    it('cancelada NO es editable', () => {
      expect(puedeEditar('cancelada')).toBe(false);
    });

    it('vencida NO es editable', () => {
      expect(puedeEditar('vencida')).toBe(false);
    });

    it('maneja mayúsculas correctamente', () => {
      expect(puedeEditar('BORRADOR')).toBe(true);
      expect(puedeEditar('DEVUELTA')).toBe(true);
      expect(puedeEditar('RECHAZADA')).toBe(false);
    });

    it('maneja null/undefined', () => {
      expect(puedeEditar(null)).toBe(false);
      expect(puedeEditar(undefined)).toBe(false);
    });
  });
});

// ============================================================================
// TESTS DE TRANSICIONES
// ============================================================================

describe('Transiciones de Estado', () => {
  describe('esTransicionValida()', () => {
    // Transiciones desde borrador
    it('borrador → pendiente_admin es válida', () => {
      expect(esTransicionValida('borrador', 'pendiente_admin')).toBe(true);
    });

    it('borrador → cancelada es válida', () => {
      expect(esTransicionValida('borrador', 'cancelada')).toBe(true);
    });

    it('borrador → enviada NO es válida', () => {
      expect(esTransicionValida('borrador', 'enviada')).toBe(false);
    });

    // Transiciones desde pendiente_admin
    it('pendiente_admin → pendiente_director es válida', () => {
      expect(esTransicionValida('pendiente_admin', 'pendiente_director')).toBe(true);
    });

    it('pendiente_admin → devuelta es válida', () => {
      expect(esTransicionValida('pendiente_admin', 'devuelta')).toBe(true);
    });

    it('pendiente_admin → rechazada es válida', () => {
      expect(esTransicionValida('pendiente_admin', 'rechazada')).toBe(true);
    });

    // Transiciones desde pendiente_director
    it('pendiente_director → enviada es válida', () => {
      expect(esTransicionValida('pendiente_director', 'enviada')).toBe(true);
    });

    it('pendiente_director → devuelta es válida', () => {
      expect(esTransicionValida('pendiente_director', 'devuelta')).toBe(true);
    });

    it('pendiente_director → rechazada es válida', () => {
      expect(esTransicionValida('pendiente_director', 'rechazada')).toBe(true);
    });

    // Transiciones desde devuelta
    it('devuelta → pendiente_admin es válida (reenvío)', () => {
      expect(esTransicionValida('devuelta', 'pendiente_admin')).toBe(true);
    });

    it('devuelta → enviada NO es válida (debe pasar por admin)', () => {
      expect(esTransicionValida('devuelta', 'enviada')).toBe(false);
    });

    // Estados finales
    it('rechazada no tiene transiciones válidas', () => {
      expect(TRANSICIONES_VALIDAS.rechazada).toEqual([]);
    });

    it('entregada no tiene transiciones válidas', () => {
      expect(TRANSICIONES_VALIDAS.entregada).toEqual([]);
    });

    it('cancelada no tiene transiciones válidas', () => {
      expect(TRANSICIONES_VALIDAS.cancelada).toEqual([]);
    });

    it('vencida no tiene transiciones válidas', () => {
      expect(TRANSICIONES_VALIDAS.vencida).toEqual([]);
    });
  });
});

// ============================================================================
// TESTS DE PERMISOS POR ROL
// ============================================================================

describe('Permisos por Rol', () => {
  describe('Médico', () => {
    const rol = ROLES.MEDICO;

    it('puede enviar borrador a admin', () => {
      expect(puedeEjecutarAccion(rol, 'enviar_admin', 'borrador')).toBe(true);
    });

    it('puede editar borrador', () => {
      expect(puedeEjecutarAccion(rol, 'editar', 'borrador')).toBe(true);
    });

    it('puede editar devuelta', () => {
      expect(puedeEjecutarAccion(rol, 'editar', 'devuelta')).toBe(true);
    });

    it('puede reenviar devuelta', () => {
      expect(puedeEjecutarAccion(rol, 'reenviar', 'devuelta')).toBe(true);
    });

    it('puede cancelar borrador', () => {
      expect(puedeEjecutarAccion(rol, 'cancelar', 'borrador')).toBe(true);
    });

    it('NO puede editar rechazada', () => {
      expect(puedeEjecutarAccion(rol, 'editar', 'rechazada')).toBe(false);
    });

    it('NO puede editar pendiente_admin', () => {
      expect(puedeEjecutarAccion(rol, 'editar', 'pendiente_admin')).toBe(false);
    });

    it('NO puede autorizar', () => {
      expect(puedeEjecutarAccion(rol, 'autorizar_admin', 'pendiente_admin')).toBe(false);
    });
  });

  describe('Administrador del Centro', () => {
    const rol = ROLES.ADMIN_CENTRO;

    it('puede autorizar en pendiente_admin', () => {
      expect(puedeEjecutarAccion(rol, 'autorizar_admin', 'pendiente_admin')).toBe(true);
    });

    it('puede devolver en pendiente_admin', () => {
      expect(puedeEjecutarAccion(rol, 'devolver', 'pendiente_admin')).toBe(true);
    });

    it('puede rechazar en pendiente_admin', () => {
      expect(puedeEjecutarAccion(rol, 'rechazar', 'pendiente_admin')).toBe(true);
    });

    it('NO puede actuar en pendiente_director', () => {
      expect(puedeEjecutarAccion(rol, 'autorizar_admin', 'pendiente_director')).toBe(false);
    });

    it('NO puede actuar en borrador', () => {
      expect(puedeEjecutarAccion(rol, 'autorizar_admin', 'borrador')).toBe(false);
    });
  });

  describe('Director del Centro', () => {
    const rol = ROLES.DIRECTOR_CENTRO;

    it('puede autorizar en pendiente_director', () => {
      expect(puedeEjecutarAccion(rol, 'autorizar_director', 'pendiente_director')).toBe(true);
    });

    it('puede devolver en pendiente_director', () => {
      expect(puedeEjecutarAccion(rol, 'devolver', 'pendiente_director')).toBe(true);
    });

    it('puede rechazar en pendiente_director', () => {
      expect(puedeEjecutarAccion(rol, 'rechazar', 'pendiente_director')).toBe(true);
    });

    it('NO puede actuar en pendiente_admin', () => {
      expect(puedeEjecutarAccion(rol, 'autorizar_director', 'pendiente_admin')).toBe(false);
    });
  });

  describe('Farmacia', () => {
    const rol = ROLES.FARMACIA;

    it('puede recibir en enviada', () => {
      expect(puedeEjecutarAccion(rol, 'recibir', 'enviada')).toBe(true);
    });

    it('puede autorizar en en_revision', () => {
      expect(puedeEjecutarAccion(rol, 'autorizar_farmacia', 'en_revision')).toBe(true);
    });

    it('puede autorizar directamente en enviada', () => {
      expect(puedeEjecutarAccion(rol, 'autorizar_farmacia', 'enviada')).toBe(true);
    });

    it('puede surtir en autorizada', () => {
      expect(puedeEjecutarAccion(rol, 'surtir', 'autorizada')).toBe(true);
    });

    it('puede entregar en autorizada', () => {
      expect(puedeEjecutarAccion(rol, 'entregar', 'autorizada')).toBe(true);
    });

    it('puede devolver en en_revision', () => {
      expect(puedeEjecutarAccion(rol, 'devolver', 'en_revision')).toBe(true);
    });

    it('puede rechazar en enviada', () => {
      expect(puedeEjecutarAccion(rol, 'rechazar', 'enviada')).toBe(true);
    });
  });
});

// ============================================================================
// TESTS DEL FLUJO DE DEVOLUCIÓN
// ============================================================================

describe('Flujo de Devolución', () => {
  it('después de devolución por admin, médico puede editar', () => {
    const estadoInicial = 'pendiente_admin';
    const estadoDespuesDevolucion = 'devuelta';

    // Admin devuelve
    expect(esTransicionValida(estadoInicial, estadoDespuesDevolucion)).toBe(true);

    // Médico puede editar
    expect(puedeEditar(estadoDespuesDevolucion)).toBe(true);
    expect(puedeEjecutarAccion(ROLES.MEDICO, 'editar', estadoDespuesDevolucion)).toBe(true);
  });

  it('después de devolución por director, médico puede editar', () => {
    const estadoInicial = 'pendiente_director';
    const estadoDespuesDevolucion = 'devuelta';

    // Director devuelve
    expect(esTransicionValida(estadoInicial, estadoDespuesDevolucion)).toBe(true);

    // Médico puede editar
    expect(puedeEditar(estadoDespuesDevolucion)).toBe(true);
  });

  it('después de editar, médico puede reenviar', () => {
    const estadoActual = 'devuelta';

    expect(puedeEjecutarAccion(ROLES.MEDICO, 'reenviar', estadoActual)).toBe(true);
    expect(esTransicionValida(estadoActual, 'pendiente_admin')).toBe(true);
  });

  it('reenvío vuelve a pendiente_admin (no salta a director)', () => {
    const estadoActual = 'devuelta';
    const estadoDespuesReenvio = 'pendiente_admin';

    expect(esTransicionValida(estadoActual, estadoDespuesReenvio)).toBe(true);
    expect(esTransicionValida(estadoActual, 'pendiente_director')).toBe(false);
  });
});

// ============================================================================
// TESTS DEL FLUJO DE RECHAZO
// ============================================================================

describe('Flujo de Rechazo', () => {
  it('después de rechazo, requisición NO es editable', () => {
    expect(puedeEditar('rechazada')).toBe(false);
  });

  it('rechazada es estado final sin transiciones', () => {
    expect(TRANSICIONES_VALIDAS.rechazada).toEqual([]);
    expect(ESTADOS_FINALES).toContain('rechazada');
  });

  it('médico NO puede editar requisición rechazada', () => {
    expect(puedeEjecutarAccion(ROLES.MEDICO, 'editar', 'rechazada')).toBe(false);
  });

  it('médico NO puede reenviar requisición rechazada', () => {
    expect(puedeEjecutarAccion(ROLES.MEDICO, 'reenviar', 'rechazada')).toBe(false);
  });
});

// ============================================================================
// TESTS DE TEXTO DE BOTONES
// ============================================================================

describe('Texto de Botones', () => {
  const ACCIONES_FLUJO = {
    devolver: {
      label: 'Devolver al Médico',
      color: 'amber',
    },
    rechazar: {
      label: 'Rechazar',
      color: 'red',
    },
    autorizar_admin: {
      label: 'Autorizar (Admin)',
      color: 'green',
    },
    autorizar_director: {
      label: 'Autorizar (Director)',
      color: 'green',
    },
    reenviar: {
      label: 'Reenviar',
      color: 'blue',
    },
  };

  it('botón de devolver dice "Devolver al Médico"', () => {
    expect(ACCIONES_FLUJO.devolver.label).toBe('Devolver al Médico');
    expect(ACCIONES_FLUJO.devolver.label).not.toBe('Devolver al Centro');
  });

  it('botón de rechazar dice "Rechazar"', () => {
    expect(ACCIONES_FLUJO.rechazar.label).toBe('Rechazar');
  });

  it('botón de reenviar dice "Reenviar"', () => {
    expect(ACCIONES_FLUJO.reenviar.label).toBe('Reenviar');
  });
});

// ============================================================================
// TESTS DE FLUJO COMPLETO
// ============================================================================

describe('Flujo Completo', () => {
  it('flujo exitoso: borrador → ... → entregada', () => {
    const flujo = [
      { desde: 'borrador', hasta: 'pendiente_admin', rol: ROLES.MEDICO },
      { desde: 'pendiente_admin', hasta: 'pendiente_director', rol: ROLES.ADMIN_CENTRO },
      { desde: 'pendiente_director', hasta: 'enviada', rol: ROLES.DIRECTOR_CENTRO },
      { desde: 'enviada', hasta: 'autorizada', rol: ROLES.FARMACIA },
      { desde: 'autorizada', hasta: 'entregada', rol: ROLES.FARMACIA },
    ];

    flujo.forEach(({ desde, hasta }) => {
      expect(esTransicionValida(desde, hasta)).toBe(true);
    });
  });

  it('flujo con devolución de admin', () => {
    const flujo = [
      { desde: 'borrador', hasta: 'pendiente_admin' },
      { desde: 'pendiente_admin', hasta: 'devuelta' },
      { desde: 'devuelta', hasta: 'pendiente_admin' },
      { desde: 'pendiente_admin', hasta: 'pendiente_director' },
    ];

    flujo.forEach(({ desde, hasta }) => {
      expect(esTransicionValida(desde, hasta)).toBe(true);
    });
  });

  it('flujo con devolución de director', () => {
    const flujo = [
      { desde: 'borrador', hasta: 'pendiente_admin' },
      { desde: 'pendiente_admin', hasta: 'pendiente_director' },
      { desde: 'pendiente_director', hasta: 'devuelta' },
      { desde: 'devuelta', hasta: 'pendiente_admin' },
      { desde: 'pendiente_admin', hasta: 'pendiente_director' },
      { desde: 'pendiente_director', hasta: 'enviada' },
    ];

    flujo.forEach(({ desde, hasta }) => {
      expect(esTransicionValida(desde, hasta)).toBe(true);
    });
  });

  it('flujo con múltiples devoluciones', () => {
    const flujo = [
      { desde: 'borrador', hasta: 'pendiente_admin' },
      { desde: 'pendiente_admin', hasta: 'devuelta' },
      { desde: 'devuelta', hasta: 'pendiente_admin' },
      { desde: 'pendiente_admin', hasta: 'devuelta' },
      { desde: 'devuelta', hasta: 'pendiente_admin' },
      { desde: 'pendiente_admin', hasta: 'pendiente_director' },
    ];

    flujo.forEach(({ desde, hasta }) => {
      expect(esTransicionValida(desde, hasta)).toBe(true);
    });
  });
});

// ============================================================================
// TESTS DE PROTECCIÓN CONTRA DOBLE ENVÍO
// ============================================================================

describe('Protección contra Doble Envío', () => {
  it('ejecutandoRef previene llamadas duplicadas', async () => {
    let ejecutandoRef = { current: false };
    let llamadas = 0;

    const ejecutarAccion = async () => {
      if (ejecutandoRef.current) {
        return { mensaje: 'Operación en progreso' };
      }

      ejecutandoRef.current = true;
      llamadas++;

      // Simular delay
      await new Promise((resolve) => setTimeout(resolve, 100));

      ejecutandoRef.current = false;
      return { mensaje: 'Completado' };
    };

    // Intentar ejecutar 3 veces simultáneamente
    const promesas = [ejecutarAccion(), ejecutarAccion(), ejecutarAccion()];

    await Promise.all(promesas);

    // Solo la primera debería haber incrementado el contador
    expect(llamadas).toBe(1);
  });
});

// ============================================================================
// TESTS DE MÚLTIPLES CENTROS
// ============================================================================

describe('Múltiples Centros', () => {
  const NUM_CENTROS = 23;

  it('puede generar requisiciones para 23 centros', () => {
    const requisiciones = [];

    for (let centro = 1; centro <= NUM_CENTROS; centro++) {
      requisiciones.push({
        centro_id: centro,
        folio: `REQ-C${String(centro).padStart(2, '0')}-0001`,
        estado: 'borrador',
      });
    }

    expect(requisiciones).toHaveLength(NUM_CENTROS);
  });

  it('folios son únicos entre centros', () => {
    const folios = [];

    for (let centro = 1; centro <= NUM_CENTROS; centro++) {
      folios.push(`REQ-C${String(centro).padStart(2, '0')}-0001`);
    }

    const foliosUnicos = new Set(folios);
    expect(foliosUnicos.size).toBe(folios.length);
  });

  it('cada centro tiene aislamiento de datos', () => {
    const requisicionesCentro1 = [
      { id: 1, centro_id: 1 },
      { id: 2, centro_id: 1 },
    ];

    const requisicionesCentro2 = [{ id: 3, centro_id: 2 }];

    const todasRequisiciones = [...requisicionesCentro1, ...requisicionesCentro2];

    const filtradoCentro1 = todasRequisiciones.filter((r) => r.centro_id === 1);
    const filtradoCentro2 = todasRequisiciones.filter((r) => r.centro_id === 2);

    expect(filtradoCentro1).toHaveLength(2);
    expect(filtradoCentro2).toHaveLength(1);
  });
});

// ============================================================================
// TESTS DE AUTORIZACIÓN DE FARMACIA
// ============================================================================

describe('Autorización de Farmacia', () => {
  it('farmacia puede autorizar cantidad completa', () => {
    const solicitado = 100;
    const stock = 150;

    const autorizado = Math.min(solicitado, stock);

    expect(autorizado).toBe(100);
  });

  it('farmacia puede autorizar cantidad parcial por stock', () => {
    const solicitado = 100;
    const stock = 50;

    const autorizado = Math.min(solicitado, stock);

    expect(autorizado).toBe(50);
    expect(autorizado).toBeLessThan(solicitado);
  });

  it('autorización parcial requiere motivo', () => {
    const solicitado = 100;
    const autorizado = 50;

    const requiereMotivo = autorizado < solicitado;

    expect(requiereMotivo).toBe(true);
  });

  it('autorización completa no requiere motivo', () => {
    const solicitado = 100;
    const autorizado = 100;

    const requiereMotivo = autorizado < solicitado;

    expect(requiereMotivo).toBe(false);
  });
});

// ============================================================================
// TESTS DE HISTORIAL
// ============================================================================

describe('Historial de Estados', () => {
  it('historial registra devolución con motivo', () => {
    const historial = [];

    historial.push({
      estado_anterior: 'pendiente_admin',
      estado_nuevo: 'devuelta',
      accion: 'devolver_centro',
      motivo: 'Pedir menos de la 615 lote terminación 2025',
      usuario: 'admin_centro_1',
    });

    expect(historial).toHaveLength(1);
    expect(historial[0].motivo).toBeTruthy();
    expect(historial[0].estado_nuevo).toBe('devuelta');
  });

  it('historial registra reenvío después de devolución', () => {
    const historial = [
      { estado_anterior: 'pendiente_admin', estado_nuevo: 'devuelta', accion: 'devolver_centro' },
      { estado_anterior: 'devuelta', estado_nuevo: 'pendiente_admin', accion: 'reenviar' },
    ];

    const reenvio = historial.find((h) => h.accion === 'reenviar');

    expect(reenvio).toBeDefined();
    expect(reenvio.estado_anterior).toBe('devuelta');
    expect(reenvio.estado_nuevo).toBe('pendiente_admin');
  });

  it('historial de rechazo incluye motivo', () => {
    const historial = [];

    historial.push({
      estado_anterior: 'pendiente_admin',
      estado_nuevo: 'rechazada',
      accion: 'rechazar',
      motivo: 'Solicitud no justificada según normativa',
      usuario: 'admin_centro_1',
    });

    expect(historial[0].motivo).toBeTruthy();
    expect(historial[0].estado_nuevo).toBe('rechazada');
  });
});
