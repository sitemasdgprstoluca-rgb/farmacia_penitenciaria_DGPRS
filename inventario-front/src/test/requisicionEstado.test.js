/**
 * ISS-007 FIX: Tests para la máquina de estados de requisiciones V2
 * Verifica transiciones válidas y cálculo de acciones permitidas
 * 
 * ACTUALIZADO: Ahora usa el flujo V2 con estados jerárquicos
 * (pendiente_admin, pendiente_director, etc.)
 */
import { describe, it, expect } from 'vitest';
import {
  ESTADOS_REQUISICION,
  ACCIONES_REQUISICION,
  ESTADOS_UI,
  esTransicionValida,
  obtenerSiguienteEstado,
  obtenerAccionesPermitidas,
} from '../hooks/useRequisicionEstado';

describe('useRequisicionEstado (V2)', () => {
  describe('ESTADOS_REQUISICION', () => {
    it('debe tener todos los estados V2 definidos', () => {
      // Estados del flujo centro
      expect(ESTADOS_REQUISICION.BORRADOR).toBe('borrador');
      expect(ESTADOS_REQUISICION.PENDIENTE_ADMIN).toBe('pendiente_admin');
      expect(ESTADOS_REQUISICION.PENDIENTE_DIRECTOR).toBe('pendiente_director');
      
      // Estados del flujo farmacia
      expect(ESTADOS_REQUISICION.ENVIADA).toBe('enviada');
      expect(ESTADOS_REQUISICION.EN_REVISION).toBe('en_revision');
      expect(ESTADOS_REQUISICION.AUTORIZADA).toBe('autorizada');
      expect(ESTADOS_REQUISICION.EN_SURTIDO).toBe('en_surtido');
      expect(ESTADOS_REQUISICION.SURTIDA).toBe('surtida');
      expect(ESTADOS_REQUISICION.ENTREGADA).toBe('entregada');
      
      // Estados negativos
      expect(ESTADOS_REQUISICION.RECHAZADA).toBe('rechazada');
      expect(ESTADOS_REQUISICION.CANCELADA).toBe('cancelada');
      
      // Estados legacy (para compatibilidad)
      expect(ESTADOS_REQUISICION.PENDIENTE).toBe('pendiente');
      expect(ESTADOS_REQUISICION.APROBADA).toBe('aprobada');
    });
  });

  describe('ESTADOS_UI', () => {
    it('debe tener configuración UI para estados V2', () => {
      const estadosV2 = [
        'borrador', 'pendiente_admin', 'pendiente_director',
        'enviada', 'en_revision', 'autorizada', 'en_surtido',
        'surtida', 'entregada', 'devuelta', 'rechazada', 'cancelada'
      ];
      estadosV2.forEach(estado => {
        expect(ESTADOS_UI[estado]).toBeDefined();
        expect(ESTADOS_UI[estado].label).toBeDefined();
        expect(ESTADOS_UI[estado].color).toBeDefined();
      });
    });
  });

  describe('esTransicionValida', () => {
    it('borrador puede enviarse a admin', () => {
      expect(esTransicionValida('borrador', ACCIONES_REQUISICION.ENVIAR_ADMIN)).toBe(true);
    });

    it('borrador puede editarse', () => {
      expect(esTransicionValida('borrador', ACCIONES_REQUISICION.EDITAR)).toBe(true);
    });

    it('borrador puede eliminarse', () => {
      expect(esTransicionValida('borrador', ACCIONES_REQUISICION.ELIMINAR)).toBe(true);
    });

    it('borrador NO puede autorizarse directamente', () => {
      expect(esTransicionValida('borrador', ACCIONES_REQUISICION.AUTORIZAR_ADMIN)).toBe(false);
    });

    it('pendiente_admin puede autorizarse por admin', () => {
      expect(esTransicionValida('pendiente_admin', ACCIONES_REQUISICION.AUTORIZAR_ADMIN)).toBe(true);
    });

    it('pendiente_admin puede rechazarse', () => {
      expect(esTransicionValida('pendiente_admin', ACCIONES_REQUISICION.RECHAZAR)).toBe(true);
    });

    it('pendiente_admin NO puede editarse', () => {
      expect(esTransicionValida('pendiente_admin', ACCIONES_REQUISICION.EDITAR)).toBe(false);
    });

    it('autorizada puede iniciar surtido', () => {
      expect(esTransicionValida('autorizada', ACCIONES_REQUISICION.INICIAR_SURTIDO)).toBe(true);
    });

    it('entregada puede verse', () => {
      expect(esTransicionValida('entregada', ACCIONES_REQUISICION.VER)).toBe(true);
    });

    it('estado inválido retorna false', () => {
      expect(esTransicionValida('estado_inexistente', ACCIONES_REQUISICION.VER)).toBe(false);
    });
  });

  describe('obtenerSiguienteEstado', () => {
    it('enviar_admin borrador lleva a pendiente_admin', () => {
      expect(obtenerSiguienteEstado('borrador', ACCIONES_REQUISICION.ENVIAR_ADMIN)).toBe('pendiente_admin');
    });

    it('autorizar_admin pendiente_admin lleva a pendiente_director', () => {
      expect(obtenerSiguienteEstado('pendiente_admin', ACCIONES_REQUISICION.AUTORIZAR_ADMIN)).toBe('pendiente_director');
    });

    it('autorizar_director pendiente_director lleva a enviada', () => {
      expect(obtenerSiguienteEstado('pendiente_director', ACCIONES_REQUISICION.AUTORIZAR_DIRECTOR)).toBe('enviada');
    });

    it('recibir_farmacia enviada lleva a en_revision', () => {
      expect(obtenerSiguienteEstado('enviada', ACCIONES_REQUISICION.RECIBIR_FARMACIA)).toBe('en_revision');
    });

    it('surtir en_surtido lleva a entregada (V2: entrega automática)', () => {
      expect(obtenerSiguienteEstado('en_surtido', ACCIONES_REQUISICION.SURTIR)).toBe('entregada');
    });

    it('devolver pendiente_admin lleva a devuelta', () => {
      expect(obtenerSiguienteEstado('pendiente_admin', ACCIONES_REQUISICION.DEVOLVER)).toBe('devuelta');
    });

    it('reenviar devuelta lleva a borrador', () => {
      expect(obtenerSiguienteEstado('devuelta', ACCIONES_REQUISICION.REENVIAR)).toBe('borrador');
    });

    it('acción no válida retorna null', () => {
      expect(obtenerSiguienteEstado('borrador', ACCIONES_REQUISICION.SURTIR)).toBe(null);
    });
  });

  describe('obtenerAccionesPermitidas', () => {
    it('borrador tiene acciones de edición con permisos', () => {
      const acciones = obtenerAccionesPermitidas('borrador', {
        crearRequisicion: true,
        editarRequisicion: true,
        eliminarRequisicion: true,
        verRequisiciones: true,
      }, { esCreador: true });
      
      expect(acciones).toContain('editar');
      expect(acciones).toContain('enviar_admin');
      expect(acciones).toContain('eliminar');
      expect(acciones).toContain('ver');
    });

    it('pendiente_admin tiene acciones de autorización', () => {
      const acciones = obtenerAccionesPermitidas('pendiente_admin', {
        autorizarAdminRequisicion: true,
        devolverRequisicion: true,
        verRequisiciones: true,
      });
      
      expect(acciones).toContain('autorizar_admin');
      expect(acciones).toContain('devolver');
      expect(acciones).toContain('ver');
    });

    it('entregada solo tiene acciones de lectura', () => {
      const acciones = obtenerAccionesPermitidas('entregada', {
        verRequisiciones: true,
      });
      
      expect(acciones).toContain('ver');
      expect(acciones).not.toContain('editar');
      expect(acciones).not.toContain('surtir');
    });

    it('sin permisos solo tiene acciones básicas', () => {
      const acciones = obtenerAccionesPermitidas('borrador', {});
      
      expect(acciones).not.toContain('editar');
      expect(acciones).not.toContain('enviar_admin');
    });
  });

  describe('Flujo completo V2', () => {
    it('flujo borrador -> entregada', () => {
      // FLUJO V2: borrador → pendiente_admin → pendiente_director → enviada
      expect(esTransicionValida('borrador', ACCIONES_REQUISICION.ENVIAR_ADMIN)).toBe(true);
      expect(obtenerSiguienteEstado('borrador', ACCIONES_REQUISICION.ENVIAR_ADMIN)).toBe('pendiente_admin');
      
      expect(esTransicionValida('pendiente_admin', ACCIONES_REQUISICION.AUTORIZAR_ADMIN)).toBe(true);
      expect(obtenerSiguienteEstado('pendiente_admin', ACCIONES_REQUISICION.AUTORIZAR_ADMIN)).toBe('pendiente_director');
      
      expect(esTransicionValida('pendiente_director', ACCIONES_REQUISICION.AUTORIZAR_DIRECTOR)).toBe(true);
      expect(obtenerSiguienteEstado('pendiente_director', ACCIONES_REQUISICION.AUTORIZAR_DIRECTOR)).toBe('enviada');
    });

    it('flujo devuelta -> borrador', () => {
      expect(esTransicionValida('devuelta', ACCIONES_REQUISICION.REENVIAR)).toBe(true);
      expect(obtenerSiguienteEstado('devuelta', ACCIONES_REQUISICION.REENVIAR)).toBe('borrador');
    });
  });
});
