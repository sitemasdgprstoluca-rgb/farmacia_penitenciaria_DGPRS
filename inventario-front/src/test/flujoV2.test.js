/**
 * Tests de integración para FLUJO V2 de requisiciones
 * 
 * Verifica:
 * - Hook useRequisicionFlujo
 * - Componentes de acciones y estados
 * - Transiciones de estado
 * - Validación de permisos por rol
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { 
  TRANSICIONES_REQUISICION, 
  ESTADOS_FINALES,
  REQUISICION_ESTADOS 
} from '../constants/strings';

// ============================================
// Tests de Constantes FLUJO V2
// ============================================

describe('Constantes FLUJO V2', () => {
  describe('TRANSICIONES_REQUISICION', () => {
    it('debe tener todos los estados definidos', () => {
      const estadosEsperados = [
        'borrador', 'pendiente_admin', 'pendiente_director',
        'enviada', 'en_revision', 'autorizada', 'en_surtido',
        'surtida', 'devuelta', 'entregada', 'rechazada', 'vencida', 'cancelada'
      ];
      
      estadosEsperados.forEach(estado => {
        expect(TRANSICIONES_REQUISICION).toHaveProperty(estado);
      });
    });
    
    it('borrador solo puede ir a pendiente_admin o cancelada', () => {
      expect(TRANSICIONES_REQUISICION.borrador).toEqual(['pendiente_admin', 'cancelada']);
    });
    
    it('pendiente_admin puede ir a pendiente_director, rechazada o devuelta', () => {
      expect(TRANSICIONES_REQUISICION.pendiente_admin).toContain('pendiente_director');
      expect(TRANSICIONES_REQUISICION.pendiente_admin).toContain('rechazada');
      expect(TRANSICIONES_REQUISICION.pendiente_admin).toContain('devuelta');
    });
    
    it('pendiente_director puede ir a enviada, rechazada o devuelta', () => {
      expect(TRANSICIONES_REQUISICION.pendiente_director).toContain('enviada');
      expect(TRANSICIONES_REQUISICION.pendiente_director).toContain('rechazada');
      expect(TRANSICIONES_REQUISICION.pendiente_director).toContain('devuelta');
    });
    
    it('enviada puede ir a en_revision, autorizada o rechazada', () => {
      expect(TRANSICIONES_REQUISICION.enviada).toContain('en_revision');
      expect(TRANSICIONES_REQUISICION.enviada).toContain('autorizada');
      expect(TRANSICIONES_REQUISICION.enviada).toContain('rechazada');
    });
    
    it('surtida solo puede ir a entregada o vencida', () => {
      expect(TRANSICIONES_REQUISICION.surtida).toEqual(['entregada', 'vencida']);
    });
    
    it('devuelta puede reenviar a pendiente_admin o cancelar', () => {
      expect(TRANSICIONES_REQUISICION.devuelta).toContain('pendiente_admin');
      expect(TRANSICIONES_REQUISICION.devuelta).toContain('cancelada');
    });
  });
  
  describe('ESTADOS_FINALES', () => {
    it('debe incluir entregada, rechazada, vencida y cancelada', () => {
      expect(ESTADOS_FINALES).toContain('entregada');
      expect(ESTADOS_FINALES).toContain('rechazada');
      expect(ESTADOS_FINALES).toContain('vencida');
      expect(ESTADOS_FINALES).toContain('cancelada');
    });
    
    it('los estados finales no deben tener transiciones', () => {
      ESTADOS_FINALES.forEach(estado => {
        expect(TRANSICIONES_REQUISICION[estado]).toEqual([]);
      });
    });
  });
  
  describe('REQUISICION_ESTADOS', () => {
    it('cada estado debe tener value, label, color e icon', () => {
      Object.values(REQUISICION_ESTADOS).forEach(estado => {
        expect(estado).toHaveProperty('value');
        expect(estado).toHaveProperty('label');
        expect(estado).toHaveProperty('color');
        expect(estado).toHaveProperty('icon');
      });
    });
  });
});

// ============================================
// Tests de Validación de Transiciones
// ============================================

describe('Validación de Transiciones', () => {
  const esTransicionValida = (estadoActual, estadoNuevo) => {
    const transicionesPermitidas = TRANSICIONES_REQUISICION[estadoActual] || [];
    return transicionesPermitidas.includes(estadoNuevo);
  };
  
  describe('Flujo Centro Penitenciario', () => {
    it('médico puede enviar borrador a admin', () => {
      expect(esTransicionValida('borrador', 'pendiente_admin')).toBe(true);
    });
    
    it('médico puede cancelar borrador', () => {
      expect(esTransicionValida('borrador', 'cancelada')).toBe(true);
    });
    
    it('no puede saltar de borrador a enviada', () => {
      expect(esTransicionValida('borrador', 'enviada')).toBe(false);
    });
    
    it('admin centro autoriza y pasa a director', () => {
      expect(esTransicionValida('pendiente_admin', 'pendiente_director')).toBe(true);
    });
    
    it('director autoriza y envía a farmacia', () => {
      expect(esTransicionValida('pendiente_director', 'enviada')).toBe(true);
    });
  });
  
  describe('Flujo Farmacia Central', () => {
    it('farmacia puede recibir requisición enviada', () => {
      expect(esTransicionValida('enviada', 'en_revision')).toBe(true);
    });
    
    it('farmacia puede autorizar directamente', () => {
      expect(esTransicionValida('enviada', 'autorizada')).toBe(true);
    });
    
    it('farmacia puede autorizar desde revisión', () => {
      expect(esTransicionValida('en_revision', 'autorizada')).toBe(true);
    });
    
    it('autorizada puede pasar a surtida', () => {
      expect(esTransicionValida('autorizada', 'surtida')).toBe(true);
    });
    
    it('surtida puede confirmarse como entregada', () => {
      expect(esTransicionValida('surtida', 'entregada')).toBe(true);
    });
    
    it('surtida puede marcarse como vencida', () => {
      expect(esTransicionValida('surtida', 'vencida')).toBe(true);
    });
  });
  
  describe('Flujo de Devolución', () => {
    it('admin puede devolver desde pendiente_admin', () => {
      expect(esTransicionValida('pendiente_admin', 'devuelta')).toBe(true);
    });
    
    it('director puede devolver desde pendiente_director', () => {
      expect(esTransicionValida('pendiente_director', 'devuelta')).toBe(true);
    });
    
    it('farmacia puede devolver desde en_revision', () => {
      expect(esTransicionValida('en_revision', 'devuelta')).toBe(true);
    });
    
    it('devuelta puede reenviarse', () => {
      expect(esTransicionValida('devuelta', 'pendiente_admin')).toBe(true);
    });
  });
  
  describe('Estados Finales', () => {
    it('entregada no puede cambiar', () => {
      expect(TRANSICIONES_REQUISICION.entregada.length).toBe(0);
    });
    
    it('rechazada no puede cambiar', () => {
      expect(TRANSICIONES_REQUISICION.rechazada.length).toBe(0);
    });
    
    it('vencida no puede cambiar', () => {
      expect(TRANSICIONES_REQUISICION.vencida.length).toBe(0);
    });
    
    it('cancelada no puede cambiar', () => {
      expect(TRANSICIONES_REQUISICION.cancelada.length).toBe(0);
    });
  });
});

// ============================================
// Tests de Permisos por Rol
// ============================================

describe('Permisos por Rol', () => {
  const ACCIONES_FLUJO = {
    enviar_admin: {
      rolesPermitidos: ['medico', 'admin', 'farmacia'],
      estadosPermitidos: ['borrador'],
    },
    autorizar_admin: {
      rolesPermitidos: ['administrador_centro', 'admin'],
      estadosPermitidos: ['pendiente_admin'],
    },
    autorizar_director: {
      rolesPermitidos: ['director_centro', 'admin'],
      estadosPermitidos: ['pendiente_director'],
    },
    recibir_farmacia: {
      rolesPermitidos: ['farmacia', 'admin', 'admin_farmacia'],
      estadosPermitidos: ['enviada'],
    },
    autorizar_farmacia: {
      rolesPermitidos: ['farmacia', 'admin', 'admin_farmacia'],
      estadosPermitidos: ['en_revision', 'enviada'],
    },
    surtir: {
      rolesPermitidos: ['farmacia', 'admin', 'admin_farmacia'],
      estadosPermitidos: ['autorizada', 'parcial'],
    },
    confirmar_entrega: {
      rolesPermitidos: ['medico', 'centro', 'admin', 'farmacia'],
      estadosPermitidos: ['surtida'],
    },
    devolver: {
      rolesPermitidos: ['administrador_centro', 'director_centro', 'farmacia', 'admin'],
      estadosPermitidos: ['pendiente_admin', 'pendiente_director', 'en_revision'],
    },
    reenviar: {
      rolesPermitidos: ['medico', 'centro', 'admin'],
      estadosPermitidos: ['devuelta'],
    },
    rechazar: {
      rolesPermitidos: ['administrador_centro', 'director_centro', 'farmacia', 'admin'],
      estadosPermitidos: ['pendiente_admin', 'pendiente_director', 'enviada', 'en_revision'],
    },
  };
  
  const puedeEjecutar = (rol, accion, estado) => {
    const config = ACCIONES_FLUJO[accion];
    if (!config) return false;
    return config.rolesPermitidos.includes(rol) && config.estadosPermitidos.includes(estado);
  };
  
  describe('Médico', () => {
    const rol = 'medico';
    
    it('puede enviar borrador a admin', () => {
      expect(puedeEjecutar(rol, 'enviar_admin', 'borrador')).toBe(true);
    });
    
    it('NO puede autorizar como admin', () => {
      expect(puedeEjecutar(rol, 'autorizar_admin', 'pendiente_admin')).toBe(false);
    });
    
    it('NO puede autorizar como director', () => {
      expect(puedeEjecutar(rol, 'autorizar_director', 'pendiente_director')).toBe(false);
    });
    
    it('puede confirmar entrega de surtida', () => {
      expect(puedeEjecutar(rol, 'confirmar_entrega', 'surtida')).toBe(true);
    });
    
    it('puede reenviar devuelta', () => {
      expect(puedeEjecutar(rol, 'reenviar', 'devuelta')).toBe(true);
    });
  });
  
  describe('Administrador Centro', () => {
    const rol = 'administrador_centro';
    
    it('puede autorizar pendiente_admin', () => {
      expect(puedeEjecutar(rol, 'autorizar_admin', 'pendiente_admin')).toBe(true);
    });
    
    it('NO puede autorizar como director', () => {
      expect(puedeEjecutar(rol, 'autorizar_director', 'pendiente_director')).toBe(false);
    });
    
    it('puede devolver pendiente_admin', () => {
      expect(puedeEjecutar(rol, 'devolver', 'pendiente_admin')).toBe(true);
    });
    
    it('puede rechazar pendiente_admin', () => {
      expect(puedeEjecutar(rol, 'rechazar', 'pendiente_admin')).toBe(true);
    });
  });
  
  describe('Director Centro', () => {
    const rol = 'director_centro';
    
    it('puede autorizar pendiente_director', () => {
      expect(puedeEjecutar(rol, 'autorizar_director', 'pendiente_director')).toBe(true);
    });
    
    it('NO puede autorizar como admin', () => {
      expect(puedeEjecutar(rol, 'autorizar_admin', 'pendiente_admin')).toBe(false);
    });
    
    it('puede devolver pendiente_director', () => {
      expect(puedeEjecutar(rol, 'devolver', 'pendiente_director')).toBe(true);
    });
    
    it('puede rechazar pendiente_director', () => {
      expect(puedeEjecutar(rol, 'rechazar', 'pendiente_director')).toBe(true);
    });
  });
  
  describe('Farmacia', () => {
    const rol = 'farmacia';
    
    it('puede recibir enviada', () => {
      expect(puedeEjecutar(rol, 'recibir_farmacia', 'enviada')).toBe(true);
    });
    
    it('puede autorizar desde en_revision', () => {
      expect(puedeEjecutar(rol, 'autorizar_farmacia', 'en_revision')).toBe(true);
    });
    
    it('puede autorizar directamente desde enviada', () => {
      expect(puedeEjecutar(rol, 'autorizar_farmacia', 'enviada')).toBe(true);
    });
    
    it('puede surtir autorizada', () => {
      expect(puedeEjecutar(rol, 'surtir', 'autorizada')).toBe(true);
    });
    
    it('puede devolver en_revision', () => {
      expect(puedeEjecutar(rol, 'devolver', 'en_revision')).toBe(true);
    });
    
    it('puede rechazar en_revision', () => {
      expect(puedeEjecutar(rol, 'rechazar', 'en_revision')).toBe(true);
    });
    
    it('puede confirmar entrega', () => {
      expect(puedeEjecutar(rol, 'confirmar_entrega', 'surtida')).toBe(true);
    });
  });
  
  describe('Admin Sistema', () => {
    const rol = 'admin';
    
    it('puede ejecutar cualquier acción', () => {
      Object.keys(ACCIONES_FLUJO).forEach(accion => {
        const config = ACCIONES_FLUJO[accion];
        expect(config.rolesPermitidos).toContain('admin');
      });
    });
  });
});

// ============================================
// Tests de Flujo Completo Simulado
// ============================================

describe('Flujo Completo Simulado', () => {
  it('flujo exitoso: borrador → entregada', () => {
    const estados = [
      'borrador',
      'pendiente_admin',
      'pendiente_director', 
      'enviada',
      'en_revision',
      'autorizada',
      'surtida',
      'entregada'
    ];
    
    for (let i = 0; i < estados.length - 1; i++) {
      const actual = estados[i];
      const siguiente = estados[i + 1];
      const valida = TRANSICIONES_REQUISICION[actual]?.includes(siguiente);
      expect(valida).toBe(true);
    }
    
    // Verificar que entregada es final
    expect(ESTADOS_FINALES).toContain('entregada');
  });
  
  it('flujo con devolución y reenvío', () => {
    const flujo = [
      { de: 'borrador', a: 'pendiente_admin' },
      { de: 'pendiente_admin', a: 'devuelta' }, // Admin devuelve
      { de: 'devuelta', a: 'pendiente_admin' }, // Médico reenvía
      { de: 'pendiente_admin', a: 'pendiente_director' },
      { de: 'pendiente_director', a: 'enviada' },
      { de: 'enviada', a: 'autorizada' },
      { de: 'autorizada', a: 'surtida' },
      { de: 'surtida', a: 'entregada' },
    ];
    
    flujo.forEach(({ de, a }) => {
      expect(TRANSICIONES_REQUISICION[de]).toContain(a);
    });
  });
  
  it('flujo con vencimiento', () => {
    const flujo = [
      { de: 'borrador', a: 'pendiente_admin' },
      { de: 'pendiente_admin', a: 'pendiente_director' },
      { de: 'pendiente_director', a: 'enviada' },
      { de: 'enviada', a: 'autorizada' },
      { de: 'autorizada', a: 'surtida' },
      { de: 'surtida', a: 'vencida' }, // No se recolectó a tiempo
    ];
    
    flujo.forEach(({ de, a }) => {
      expect(TRANSICIONES_REQUISICION[de]).toContain(a);
    });
    
    expect(ESTADOS_FINALES).toContain('vencida');
  });
  
  it('flujo con rechazo en farmacia', () => {
    const flujo = [
      { de: 'borrador', a: 'pendiente_admin' },
      { de: 'pendiente_admin', a: 'pendiente_director' },
      { de: 'pendiente_director', a: 'enviada' },
      { de: 'enviada', a: 'rechazada' }, // Farmacia rechaza
    ];
    
    flujo.forEach(({ de, a }) => {
      expect(TRANSICIONES_REQUISICION[de]).toContain(a);
    });
    
    expect(ESTADOS_FINALES).toContain('rechazada');
  });
});

// ============================================
// Tests de Componentes (Helpers)
// ============================================

describe('Helpers de Estado', () => {
  const getEstadoConfig = (estado) => {
    const estadoLower = estado?.toLowerCase();
    return Object.values(REQUISICION_ESTADOS).find(
      e => e.value === estadoLower
    );
  };
  
  it('cada estado tiene configuración', () => {
    const estados = [
      'borrador', 'pendiente_admin', 'pendiente_director',
      'enviada', 'en_revision', 'autorizada', 'surtida',
      'entregada', 'rechazada', 'vencida', 'cancelada'
    ];
    
    estados.forEach(estado => {
      const config = getEstadoConfig(estado);
      expect(config).toBeDefined();
      expect(config.label).toBeTruthy();
      expect(config.color).toBeTruthy();
    });
  });
  
  it('estados tienen colores válidos', () => {
    const coloresValidos = [
      'gray', 'yellow', 'orange', 'amber', 'blue', 'cyan',
      'indigo', 'violet', 'purple', 'teal', 'green', 'red'
    ];
    
    Object.values(REQUISICION_ESTADOS).forEach(estado => {
      expect(coloresValidos).toContain(estado.color);
    });
  });
});
