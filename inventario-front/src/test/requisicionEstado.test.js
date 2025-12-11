/**
 * ISS-007 FIX: Tests para la máquina de estados de requisiciones
 * Verifica transiciones válidas y cálculo de acciones permitidas
 */
import { describe, it, expect } from 'vitest';
import {
  ESTADOS_REQUISICION,
  ACCIONES_REQUISICION,
  ESTADOS_UI,
  esTransicionValida,
  obtenerSiguienteEstado,
  obtenerAccionesPermitidas,
} from '../../hooks/useRequisicionEstado';

describe('useRequisicionEstado', () => {
  describe('ESTADOS_REQUISICION', () => {
    it('debe tener todos los estados definidos', () => {
      expect(ESTADOS_REQUISICION.BORRADOR).toBe('borrador');
      expect(ESTADOS_REQUISICION.PENDIENTE).toBe('pendiente');
      expect(ESTADOS_REQUISICION.APROBADA).toBe('aprobada');
      expect(ESTADOS_REQUISICION.EN_PROCESO).toBe('en_proceso');
      expect(ESTADOS_REQUISICION.SURTIDA_PARCIAL).toBe('surtida_parcial');
      expect(ESTADOS_REQUISICION.SURTIDA).toBe('surtida');
      expect(ESTADOS_REQUISICION.RECHAZADA).toBe('rechazada');
      expect(ESTADOS_REQUISICION.CANCELADA).toBe('cancelada');
    });
  });

  describe('ESTADOS_UI', () => {
    it('debe tener configuración UI para cada estado', () => {
      Object.values(ESTADOS_REQUISICION).forEach(estado => {
        expect(ESTADOS_UI[estado]).toBeDefined();
        expect(ESTADOS_UI[estado].label).toBeDefined();
        expect(ESTADOS_UI[estado].color).toBeDefined();
        expect(ESTADOS_UI[estado].badgeClass).toBeDefined();
      });
    });
  });

  describe('esTransicionValida', () => {
    it('borrador puede enviarse', () => {
      expect(esTransicionValida('borrador', ACCIONES_REQUISICION.ENVIAR)).toBe(true);
    });

    it('borrador puede editarse', () => {
      expect(esTransicionValida('borrador', ACCIONES_REQUISICION.EDITAR)).toBe(true);
    });

    it('borrador puede eliminarse', () => {
      expect(esTransicionValida('borrador', ACCIONES_REQUISICION.ELIMINAR)).toBe(true);
    });

    it('borrador NO puede aprobarse directamente', () => {
      expect(esTransicionValida('borrador', ACCIONES_REQUISICION.APROBAR)).toBe(false);
    });

    it('pendiente puede aprobarse', () => {
      expect(esTransicionValida('pendiente', ACCIONES_REQUISICION.APROBAR)).toBe(true);
    });

    it('pendiente puede rechazarse', () => {
      expect(esTransicionValida('pendiente', ACCIONES_REQUISICION.RECHAZAR)).toBe(true);
    });

    it('pendiente NO puede editarse', () => {
      expect(esTransicionValida('pendiente', ACCIONES_REQUISICION.EDITAR)).toBe(false);
    });

    it('aprobada puede surtirse', () => {
      expect(esTransicionValida('aprobada', ACCIONES_REQUISICION.SURTIR)).toBe(true);
    });

    it('surtida NO puede cancelarse', () => {
      expect(esTransicionValida('surtida', ACCIONES_REQUISICION.CANCELAR)).toBe(false);
    });

    it('surtida puede duplicarse', () => {
      expect(esTransicionValida('surtida', ACCIONES_REQUISICION.DUPLICAR)).toBe(true);
    });

    it('rechazada puede duplicarse', () => {
      expect(esTransicionValida('rechazada', ACCIONES_REQUISICION.DUPLICAR)).toBe(true);
    });

    it('cancelada puede verse', () => {
      expect(esTransicionValida('cancelada', ACCIONES_REQUISICION.VER)).toBe(true);
    });

    it('estado inválido retorna false', () => {
      expect(esTransicionValida('estado_inexistente', ACCIONES_REQUISICION.VER)).toBe(false);
    });
  });

  describe('obtenerSiguienteEstado', () => {
    it('enviar borrador lleva a pendiente', () => {
      expect(obtenerSiguienteEstado('borrador', ACCIONES_REQUISICION.ENVIAR)).toBe('pendiente');
    });

    it('aprobar pendiente lleva a aprobada', () => {
      expect(obtenerSiguienteEstado('pendiente', ACCIONES_REQUISICION.APROBAR)).toBe('aprobada');
    });

    it('rechazar pendiente lleva a rechazada', () => {
      expect(obtenerSiguienteEstado('pendiente', ACCIONES_REQUISICION.RECHAZAR)).toBe('rechazada');
    });

    it('surtir aprobada lleva a surtida', () => {
      expect(obtenerSiguienteEstado('aprobada', ACCIONES_REQUISICION.SURTIR)).toBe('surtida');
    });

    it('surtir parcial lleva a surtida_parcial', () => {
      expect(obtenerSiguienteEstado('aprobada', ACCIONES_REQUISICION.SURTIR_PARCIAL)).toBe('surtida_parcial');
    });

    it('cancelar aprobada lleva a cancelada', () => {
      expect(obtenerSiguienteEstado('aprobada', ACCIONES_REQUISICION.CANCELAR)).toBe('cancelada');
    });

    it('ver no cambia estado (retorna null)', () => {
      expect(obtenerSiguienteEstado('surtida', ACCIONES_REQUISICION.VER)).toBeNull();
    });

    it('estado inválido retorna null', () => {
      expect(obtenerSiguienteEstado('estado_inexistente', ACCIONES_REQUISICION.ENVIAR)).toBeNull();
    });
  });

  describe('obtenerAccionesPermitidas', () => {
    it('sin permisos solo permite acciones que no requieren permiso', () => {
      const acciones = obtenerAccionesPermitidas('borrador', {});
      // Sin ningún permiso, no debería permitir acciones que requieren permisos
      expect(acciones).not.toContain(ACCIONES_REQUISICION.EDITAR);
      expect(acciones).not.toContain(ACCIONES_REQUISICION.ENVIAR);
    });

    it('con permiso de ver, puede ver en cualquier estado', () => {
      const permisos = { verRequisiciones: true };
      
      Object.values(ESTADOS_REQUISICION).forEach(estado => {
        const acciones = obtenerAccionesPermitidas(estado, permisos);
        expect(acciones).toContain(ACCIONES_REQUISICION.VER);
      });
    });

    it('con permiso de crear, puede enviar borrador', () => {
      const permisos = { crearRequisicion: true };
      const acciones = obtenerAccionesPermitidas('borrador', permisos);
      expect(acciones).toContain(ACCIONES_REQUISICION.ENVIAR);
    });

    it('con permiso de aprobar, puede aprobar y rechazar pendiente', () => {
      const permisos = { aprobarRequisicion: true };
      const acciones = obtenerAccionesPermitidas('pendiente', permisos);
      expect(acciones).toContain(ACCIONES_REQUISICION.APROBAR);
      expect(acciones).toContain(ACCIONES_REQUISICION.RECHAZAR);
    });

    it('con permiso de surtir, puede surtir aprobada', () => {
      const permisos = { surtirRequisicion: true };
      const acciones = obtenerAccionesPermitidas('aprobada', permisos);
      expect(acciones).toContain(ACCIONES_REQUISICION.SURTIR);
      expect(acciones).toContain(ACCIONES_REQUISICION.SURTIR_PARCIAL);
    });

    it('estado final solo permite ver, imprimir y duplicar', () => {
      const permisos = { 
        verRequisiciones: true, 
        crearRequisicion: true,
        aprobarRequisicion: true,
        surtirRequisicion: true,
      };
      
      const accionesSurtida = obtenerAccionesPermitidas('surtida', permisos);
      expect(accionesSurtida).toContain(ACCIONES_REQUISICION.VER);
      expect(accionesSurtida).toContain(ACCIONES_REQUISICION.IMPRIMIR);
      expect(accionesSurtida).toContain(ACCIONES_REQUISICION.DUPLICAR);
      expect(accionesSurtida).not.toContain(ACCIONES_REQUISICION.EDITAR);
      expect(accionesSurtida).not.toContain(ACCIONES_REQUISICION.CANCELAR);
    });

    it('estado inválido retorna array vacío', () => {
      const acciones = obtenerAccionesPermitidas('estado_inexistente', { verRequisiciones: true });
      expect(acciones).toEqual([]);
    });
  });

  describe('Flujo completo de requisición', () => {
    it('flujo borrador -> pendiente -> aprobada -> surtida', () => {
      let estado = 'borrador';
      
      // Enviar
      expect(esTransicionValida(estado, ACCIONES_REQUISICION.ENVIAR)).toBe(true);
      estado = obtenerSiguienteEstado(estado, ACCIONES_REQUISICION.ENVIAR);
      expect(estado).toBe('pendiente');
      
      // Aprobar
      expect(esTransicionValida(estado, ACCIONES_REQUISICION.APROBAR)).toBe(true);
      estado = obtenerSiguienteEstado(estado, ACCIONES_REQUISICION.APROBAR);
      expect(estado).toBe('aprobada');
      
      // Surtir
      expect(esTransicionValida(estado, ACCIONES_REQUISICION.SURTIR)).toBe(true);
      estado = obtenerSiguienteEstado(estado, ACCIONES_REQUISICION.SURTIR);
      expect(estado).toBe('surtida');
      
      // Estado final
      expect(esTransicionValida(estado, ACCIONES_REQUISICION.CANCELAR)).toBe(false);
      expect(esTransicionValida(estado, ACCIONES_REQUISICION.EDITAR)).toBe(false);
    });

    it('flujo borrador -> pendiente -> rechazada', () => {
      let estado = 'borrador';
      
      estado = obtenerSiguienteEstado(estado, ACCIONES_REQUISICION.ENVIAR);
      expect(estado).toBe('pendiente');
      
      estado = obtenerSiguienteEstado(estado, ACCIONES_REQUISICION.RECHAZAR);
      expect(estado).toBe('rechazada');
      
      // Estado final
      expect(esTransicionValida(estado, ACCIONES_REQUISICION.APROBAR)).toBe(false);
    });

    it('flujo con surtido parcial', () => {
      let estado = 'aprobada';
      
      estado = obtenerSiguienteEstado(estado, ACCIONES_REQUISICION.SURTIR_PARCIAL);
      expect(estado).toBe('surtida_parcial');
      
      // Puede seguir surtiendo
      expect(esTransicionValida(estado, ACCIONES_REQUISICION.SURTIR)).toBe(true);
      expect(esTransicionValida(estado, ACCIONES_REQUISICION.SURTIR_PARCIAL)).toBe(true);
      
      estado = obtenerSiguienteEstado(estado, ACCIONES_REQUISICION.SURTIR);
      expect(estado).toBe('surtida');
    });
  });
});
