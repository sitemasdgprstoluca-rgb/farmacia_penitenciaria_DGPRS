/**
 * Tests para el flujo V2 de requisiciones (audit27)
 * 
 * Cobertura:
 * - Máquina de estados V2 con transiciones jerárquicas
 * - Normalización de estados legacy
 * - Permisos dinámicos
 * - Grupos de estados
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';

// Importar funciones y constantes del módulo V2
import {
  ESTADOS_REQUISICION,
  ACCIONES_REQUISICION,
  GRUPOS_ESTADOS,
  ESTADOS_TERMINALES,
  ESTADOS_EDITABLES,
  MAPEO_ESTADOS_LEGACY,
  normalizarEstado,
  esTransicionValida,
  obtenerSiguienteEstado,
  obtenerAccionesPermitidas,
  obtenerGrupoEstado,
  useRequisicionEstado,
} from '../useRequisicionEstadoV2';

describe('useRequisicionEstadoV2', () => {
  describe('ESTADOS_REQUISICION', () => {
    it('debe incluir todos los estados V2', () => {
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
      expect(ESTADOS_REQUISICION.VENCIDA).toBe('vencida');
      expect(ESTADOS_REQUISICION.CANCELADA).toBe('cancelada');
      expect(ESTADOS_REQUISICION.DEVUELTA).toBe('devuelta');
    });

    it('debe incluir estados legacy para compatibilidad', () => {
      expect(ESTADOS_REQUISICION.PENDIENTE).toBe('pendiente');
      expect(ESTADOS_REQUISICION.APROBADA).toBe('aprobada');
      expect(ESTADOS_REQUISICION.EN_PROCESO).toBe('en_proceso');
      expect(ESTADOS_REQUISICION.SURTIDA_PARCIAL).toBe('surtida_parcial');
    });
  });

  describe('ACCIONES_REQUISICION', () => {
    it('debe incluir todas las acciones V2', () => {
      // Acciones flujo centro
      expect(ACCIONES_REQUISICION.ENVIAR_ADMIN).toBe('enviar_admin');
      expect(ACCIONES_REQUISICION.AUTORIZAR_ADMIN).toBe('autorizar_admin');
      expect(ACCIONES_REQUISICION.AUTORIZAR_DIRECTOR).toBe('autorizar_director');
      
      // Acciones flujo farmacia
      expect(ACCIONES_REQUISICION.RECIBIR_FARMACIA).toBe('recibir_farmacia');
      expect(ACCIONES_REQUISICION.AUTORIZAR_FARMACIA).toBe('autorizar_farmacia');
      expect(ACCIONES_REQUISICION.INICIAR_SURTIDO).toBe('iniciar_surtido');
      expect(ACCIONES_REQUISICION.CONFIRMAR_ENTREGA).toBe('confirmar_entrega');
      
      // Acciones especiales
      expect(ACCIONES_REQUISICION.DEVOLVER).toBe('devolver');
      expect(ACCIONES_REQUISICION.REENVIAR).toBe('reenviar');
      expect(ACCIONES_REQUISICION.MARCAR_VENCIDA).toBe('marcar_vencida');
    });
  });

  describe('normalizarEstado', () => {
    it('debe normalizar estados legacy a V2', () => {
      expect(normalizarEstado('pendiente')).toBe('pendiente_admin');
      expect(normalizarEstado('aprobada')).toBe('autorizada');
      expect(normalizarEstado('en_proceso')).toBe('en_surtido');
      expect(normalizarEstado('surtida_parcial')).toBe('en_surtido');
    });

    it('debe devolver estados V2 sin cambios', () => {
      expect(normalizarEstado('pendiente_admin')).toBe('pendiente_admin');
      expect(normalizarEstado('pendiente_director')).toBe('pendiente_director');
      expect(normalizarEstado('enviada')).toBe('enviada');
      expect(normalizarEstado('entregada')).toBe('entregada');
    });

    it('debe manejar null/undefined', () => {
      expect(normalizarEstado(null)).toBe('borrador');
      expect(normalizarEstado(undefined)).toBe('borrador');
    });

    it('debe ser case-insensitive', () => {
      expect(normalizarEstado('PENDIENTE')).toBe('pendiente_admin');
      expect(normalizarEstado('Borrador')).toBe('borrador');
    });
  });

  describe('GRUPOS_ESTADOS', () => {
    it('debe agrupar estados del centro', () => {
      const { centro } = GRUPOS_ESTADOS;
      expect(centro.estados).toContain('borrador');
      expect(centro.estados).toContain('pendiente_admin');
      expect(centro.estados).toContain('pendiente_director');
      expect(centro.estados).toContain('devuelta');
    });

    it('debe agrupar estados de farmacia', () => {
      const { farmacia } = GRUPOS_ESTADOS;
      expect(farmacia.estados).toContain('enviada');
      expect(farmacia.estados).toContain('en_revision');
      expect(farmacia.estados).toContain('autorizada');
      expect(farmacia.estados).toContain('en_surtido');
      expect(farmacia.estados).toContain('surtida');
    });

    it('debe identificar estados completados', () => {
      const { completadas } = GRUPOS_ESTADOS;
      expect(completadas.estados).toContain('entregada');
    });

    it('debe identificar estados finalizados negativos', () => {
      const { finalizadas } = GRUPOS_ESTADOS;
      expect(finalizadas.estados).toContain('rechazada');
      expect(finalizadas.estados).toContain('vencida');
      expect(finalizadas.estados).toContain('cancelada');
    });
  });

  describe('ESTADOS_TERMINALES', () => {
    it('debe incluir estados que no permiten más transiciones', () => {
      expect(ESTADOS_TERMINALES).toContain('entregada');
      expect(ESTADOS_TERMINALES).toContain('rechazada');
      expect(ESTADOS_TERMINALES).toContain('vencida');
      expect(ESTADOS_TERMINALES).toContain('cancelada');
    });

    it('no debe incluir estados intermedios', () => {
      expect(ESTADOS_TERMINALES).not.toContain('borrador');
      expect(ESTADOS_TERMINALES).not.toContain('enviada');
      expect(ESTADOS_TERMINALES).not.toContain('surtida');
      expect(ESTADOS_TERMINALES).not.toContain('devuelta');
    });
  });

  describe('ESTADOS_EDITABLES', () => {
    it('debe incluir solo estados que permiten edición', () => {
      expect(ESTADOS_EDITABLES).toContain('borrador');
      expect(ESTADOS_EDITABLES).toContain('devuelta');
    });

    it('no debe incluir estados no editables', () => {
      expect(ESTADOS_EDITABLES).not.toContain('enviada');
      expect(ESTADOS_EDITABLES).not.toContain('surtida');
      expect(ESTADOS_EDITABLES).not.toContain('entregada');
    });
  });

  describe('esTransicionValida', () => {
    it('debe validar transiciones del flujo V2', () => {
      // Borrador → pendiente_admin
      expect(esTransicionValida('borrador', 'enviar_admin')).toBe(true);
      
      // pendiente_admin → pendiente_director
      expect(esTransicionValida('pendiente_admin', 'autorizar_admin')).toBe(true);
      
      // pendiente_director → enviada
      expect(esTransicionValida('pendiente_director', 'autorizar_director')).toBe(true);
      
      // enviada → en_revision
      expect(esTransicionValida('enviada', 'recibir_farmacia')).toBe(true);
    });

    it('debe rechazar transiciones inválidas', () => {
      // No se puede saltar de borrador a surtida
      expect(esTransicionValida('borrador', 'surtir')).toBe(false);
      
      // No se puede aprobar desde enviada (debe ir a en_revision primero)
      expect(esTransicionValida('enviada', 'surtir')).toBe(false);
    });

    it('debe permitir acciones de visualización en todos los estados', () => {
      expect(esTransicionValida('borrador', 'ver')).toBe(true);
      expect(esTransicionValida('surtida', 'ver')).toBe(true);
      expect(esTransicionValida('entregada', 'ver')).toBe(true);
    });
  });

  describe('obtenerSiguienteEstado', () => {
    it('debe devolver el siguiente estado correcto', () => {
      expect(obtenerSiguienteEstado('borrador', 'enviar_admin')).toBe('pendiente_admin');
      expect(obtenerSiguienteEstado('pendiente_admin', 'autorizar_admin')).toBe('pendiente_director');
      expect(obtenerSiguienteEstado('pendiente_director', 'autorizar_director')).toBe('enviada');
      expect(obtenerSiguienteEstado('enviada', 'recibir_farmacia')).toBe('en_revision');
      // FLUJO V2 ACTUALIZADO: en_surtido → surtir → entregada (entrega automática)
      expect(obtenerSiguienteEstado('en_surtido', 'surtir')).toBe('entregada');
    });

    it('debe devolver null para acciones sin transición', () => {
      expect(obtenerSiguienteEstado('entregada', 'ver')).toBe(null);
      expect(obtenerSiguienteEstado('borrador', 'ver')).toBe(null);
    });

    it('debe manejar devoluciones correctamente', () => {
      expect(obtenerSiguienteEstado('pendiente_admin', 'devolver')).toBe('devuelta');
      expect(obtenerSiguienteEstado('pendiente_director', 'devolver')).toBe('devuelta');
      expect(obtenerSiguienteEstado('en_revision', 'devolver')).toBe('devuelta');
    });

    it('debe manejar reenvío desde devuelta', () => {
      expect(obtenerSiguienteEstado('devuelta', 'reenviar')).toBe('borrador');
    });
  });

  describe('obtenerAccionesPermitidas', () => {
    it('debe devolver acciones para borrador', () => {
      // Nota: 'editar' requiere editarRequisicion + esCreador o editarCualquierRequisicion
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

    it('debe devolver acciones para pendiente_admin', () => {
      const acciones = obtenerAccionesPermitidas('pendiente_admin', {
        autorizarAdminRequisicion: true,
        devolverRequisicion: true,
        rechazarRequisicion: true,
        verRequisiciones: true,
      });
      
      expect(acciones).toContain('autorizar_admin');
      expect(acciones).toContain('devolver');
      expect(acciones).toContain('rechazar');
    });

    it('debe filtrar acciones sin permiso', () => {
      const acciones = obtenerAccionesPermitidas('borrador', {
        verRequisiciones: true,
        // Sin permiso de crear/eliminar
      });
      
      expect(acciones).toContain('ver');
      expect(acciones).not.toContain('enviar_admin');
      expect(acciones).not.toContain('eliminar');
    });

    it('debe restringir edición a creador', () => {
      const accionesSinCreador = obtenerAccionesPermitidas('borrador', {
        editarRequisicion: true,
        verRequisiciones: true,
      }, { esCreador: false });
      
      expect(accionesSinCreador).not.toContain('editar');
      
      const accionesConCreador = obtenerAccionesPermitidas('borrador', {
        editarRequisicion: true,
        verRequisiciones: true,
      }, { esCreador: true });
      
      expect(accionesConCreador).toContain('editar');
    });
  });

  describe('obtenerGrupoEstado', () => {
    it('debe identificar estados del centro', () => {
      expect(obtenerGrupoEstado('borrador')).toBe('centro');
      expect(obtenerGrupoEstado('pendiente_admin')).toBe('centro');
      expect(obtenerGrupoEstado('pendiente_director')).toBe('centro');
      expect(obtenerGrupoEstado('devuelta')).toBe('centro');
    });

    it('debe identificar estados de farmacia', () => {
      expect(obtenerGrupoEstado('enviada')).toBe('farmacia');
      expect(obtenerGrupoEstado('en_revision')).toBe('farmacia');
      expect(obtenerGrupoEstado('autorizada')).toBe('farmacia');
      expect(obtenerGrupoEstado('en_surtido')).toBe('farmacia');
      expect(obtenerGrupoEstado('surtida')).toBe('farmacia');
    });

    it('debe identificar estados terminales', () => {
      expect(obtenerGrupoEstado('entregada')).toBe('terminal');
      expect(obtenerGrupoEstado('rechazada')).toBe('terminal');
      expect(obtenerGrupoEstado('vencida')).toBe('terminal');
      expect(obtenerGrupoEstado('cancelada')).toBe('terminal');
    });
  });

  describe('useRequisicionEstado hook', () => {
    it('debe devolver estado normalizado', () => {
      const { result } = renderHook(() => 
        useRequisicionEstado({ estado: 'pendiente' })
      );
      
      // Estado legacy normalizado a V2
      expect(result.current.estado).toBe('pendiente_admin');
      expect(result.current.estadoOriginal).toBe('pendiente');
    });

    it('debe calcular flags correctamente', () => {
      const { result } = renderHook(() => 
        useRequisicionEstado({ estado: 'borrador' })
      );
      
      expect(result.current.esEditable).toBe(true);
      expect(result.current.esFinal).toBe(false);
      expect(result.current.esEnCentro).toBe(true);
      expect(result.current.esEnFarmacia).toBe(false);
    });

    it('debe identificar estados terminales', () => {
      const { result } = renderHook(() => 
        useRequisicionEstado({ estado: 'entregada' })
      );
      
      expect(result.current.esFinal).toBe(true);
      expect(result.current.esEditable).toBe(false);
    });

    it('debe calcular helpers V2', () => {
      const { result } = renderHook(() => 
        useRequisicionEstado(
          { estado: 'borrador' },
          { crearRequisicion: true, verRequisiciones: true }
        )
      );
      
      expect(result.current.puedeEnviarAdmin).toBe(true);
      expect(result.current.puedeVer).toBe(true);
    });

    it('debe manejar requisición null', () => {
      const { result } = renderHook(() => 
        useRequisicionEstado(null)
      );
      
      expect(result.current.estado).toBe('borrador');
    });

    it('debe devolver UI correcta para cada estado', () => {
      const estados = [
        'borrador', 'pendiente_admin', 'pendiente_director',
        'enviada', 'en_revision', 'autorizada', 'en_surtido',
        'surtida', 'entregada', 'devuelta', 'rechazada', 'vencida', 'cancelada'
      ];
      
      estados.forEach(estado => {
        const { result } = renderHook(() => 
          useRequisicionEstado({ estado })
        );
        
        expect(result.current.estadoUI).toBeDefined();
        expect(result.current.estadoUI.label).toBeTruthy();
        expect(result.current.estadoUI.color).toBeTruthy();
      });
    });
  });
});

describe('Flujo completo V2', () => {
  it('debe permitir el flujo completo de requisición', () => {
    // FLUJO V2 ACTUALIZADO: al surtir se entrega automáticamente (sin confirmación del centro)
    const flujo = [
      { estado: 'borrador', accion: 'enviar_admin', siguiente: 'pendiente_admin' },
      { estado: 'pendiente_admin', accion: 'autorizar_admin', siguiente: 'pendiente_director' },
      { estado: 'pendiente_director', accion: 'autorizar_director', siguiente: 'enviada' },
      { estado: 'enviada', accion: 'recibir_farmacia', siguiente: 'en_revision' },
      { estado: 'en_revision', accion: 'autorizar_farmacia', siguiente: 'autorizada' },
      { estado: 'autorizada', accion: 'iniciar_surtido', siguiente: 'en_surtido' },
      // CAMBIO V2: en_surtido → surtir → entregada (entrega automática)
      { estado: 'en_surtido', accion: 'surtir', siguiente: 'entregada' },
    ];

    flujo.forEach(({ estado, accion, siguiente }) => {
      expect(esTransicionValida(estado, accion)).toBe(true);
      expect(obtenerSiguienteEstado(estado, accion)).toBe(siguiente);
    });
  });

  it('debe permitir flujo de devolución y reenvío', () => {
    // Devolución desde pendiente_admin
    expect(esTransicionValida('pendiente_admin', 'devolver')).toBe(true);
    expect(obtenerSiguienteEstado('pendiente_admin', 'devolver')).toBe('devuelta');
    
    // Reenvío desde devuelta
    expect(esTransicionValida('devuelta', 'reenviar')).toBe(true);
    expect(obtenerSiguienteEstado('devuelta', 'reenviar')).toBe('borrador');
  });

  it('debe permitir cancelación desde devuelta', () => {
    // FLUJO V2: Solo devuelta permite cancelar directamente
    // pendiente_admin y pendiente_director usan rechazar/devolver
    expect(esTransicionValida('devuelta', 'cancelar')).toBe(true);
    expect(obtenerSiguienteEstado('devuelta', 'cancelar')).toBe('cancelada');
  });

  it('debe permitir marcar vencida desde surtida', () => {
    // FLUJO V2: Estado surtida es legacy, pero sigue permitiendo marcar_vencida
    expect(esTransicionValida('surtida', 'marcar_vencida')).toBe(true);
    expect(obtenerSiguienteEstado('surtida', 'marcar_vencida')).toBe('vencida');
  });
});
