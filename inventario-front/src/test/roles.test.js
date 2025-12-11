/**
 * Tests para utils/roles.js
 * FRONT-005: Agregar tests básicos para módulos críticos
 */

import { describe, it, expect } from 'vitest';
import {
  esAdmin,
  esFarmacia,
  esFarmaciaAdmin,
  esCentro,
  esVista,
  puedeVerGlobal,
  getRolPrincipal,
  normalizarRol,
  puedeEjecutarAccionFlujo,
  ADMIN_ROLES,
  FARMACIA_ROLES,
  CENTRO_ROLES,
  VISTA_ROLES,
} from '../utils/roles';

describe('Módulo de Roles', () => {
  describe('normalizarRol', () => {
    it('debe convertir a minúsculas', () => {
      expect(normalizarRol('ADMIN')).toBe('admin');
      expect(normalizarRol('Farmacia')).toBe('farmacia');
    });

    it('debe manejar null y undefined', () => {
      expect(normalizarRol(null)).toBe('');
      expect(normalizarRol(undefined)).toBe('');
    });

    it('debe eliminar espacios', () => {
      expect(normalizarRol('  admin  ')).toBe('admin');
    });
  });

  describe('esAdmin', () => {
    it('debe retornar true para superusuario', () => {
      expect(esAdmin({ is_superuser: true })).toBe(true);
      expect(esAdmin({ isSuperuser: true })).toBe(true);
    });

    it('debe retornar true para roles admin', () => {
      expect(esAdmin({ rol: 'admin' })).toBe(true);
      expect(esAdmin({ rol: 'admin_sistema' })).toBe(true);
      expect(esAdmin({ rol: 'superusuario' })).toBe(true);
    });

    it('debe retornar false para otros roles', () => {
      expect(esAdmin({ rol: 'farmacia' })).toBe(false);
      expect(esAdmin({ rol: 'centro' })).toBe(false);
      expect(esAdmin(null)).toBe(false);
    });
  });

  describe('esFarmacia', () => {
    it('debe retornar true para roles farmacia', () => {
      expect(esFarmacia({ rol: 'farmacia' })).toBe(true);
      expect(esFarmacia({ rol: 'admin_farmacia' })).toBe(true);
    });

    it('debe retornar false para otros roles', () => {
      expect(esFarmacia({ rol: 'admin' })).toBe(false);
      expect(esFarmacia({ rol: 'centro' })).toBe(false);
    });
  });

  describe('esFarmaciaAdmin', () => {
    it('debe retornar true para superusuario', () => {
      expect(esFarmaciaAdmin({ is_superuser: true })).toBe(true);
    });

    it('debe retornar true para admin', () => {
      expect(esFarmaciaAdmin({ rol: 'admin' })).toBe(true);
    });

    it('debe retornar true para farmacia', () => {
      expect(esFarmaciaAdmin({ rol: 'farmacia' })).toBe(true);
    });

    it('debe retornar false para centro', () => {
      expect(esFarmaciaAdmin({ rol: 'centro' })).toBe(false);
    });
  });

  describe('esCentro', () => {
    it('debe retornar true para roles centro FLUJO V2', () => {
      expect(esCentro({ rol: 'centro' })).toBe(true);
      expect(esCentro({ rol: 'medico' })).toBe(true);
      expect(esCentro({ rol: 'administrador_centro' })).toBe(true);
      expect(esCentro({ rol: 'director_centro' })).toBe(true);
    });

    it('debe retornar true para rol legacy', () => {
      expect(esCentro({ rol: 'usuario_normal' })).toBe(true);
    });

    it('debe retornar false para farmacia', () => {
      expect(esCentro({ rol: 'farmacia' })).toBe(false);
    });
  });

  describe('esVista', () => {
    it('debe retornar true para roles vista', () => {
      expect(esVista({ rol: 'vista' })).toBe(true);
      expect(esVista({ rol: 'usuario_vista' })).toBe(true);
    });

    it('debe retornar false para otros roles', () => {
      expect(esVista({ rol: 'admin' })).toBe(false);
      expect(esVista({ rol: 'centro' })).toBe(false);
    });
  });

  describe('puedeVerGlobal', () => {
    it('debe retornar true para superusuario', () => {
      expect(puedeVerGlobal({ is_superuser: true }, { isSuperuser: true })).toBe(true);
    });

    it('debe retornar true para admin', () => {
      expect(puedeVerGlobal({ rol: 'admin' })).toBe(true);
    });

    it('debe retornar true para farmacia', () => {
      expect(puedeVerGlobal({ rol: 'farmacia' })).toBe(true);
    });

    it('debe retornar true para vista', () => {
      expect(puedeVerGlobal({ rol: 'vista' })).toBe(true);
    });

    it('debe retornar false para centro', () => {
      expect(puedeVerGlobal({ rol: 'centro' })).toBe(false);
      expect(puedeVerGlobal({ rol: 'medico' })).toBe(false);
    });
  });

  describe('getRolPrincipal', () => {
    it('debe retornar ADMIN para superusuario', () => {
      expect(getRolPrincipal({ is_superuser: true })).toBe('ADMIN');
    });

    it('debe retornar ADMIN para rol admin', () => {
      expect(getRolPrincipal({ rol: 'admin' })).toBe('ADMIN');
      expect(getRolPrincipal({ rol: 'admin_sistema' })).toBe('ADMIN');
    });

    it('debe retornar FARMACIA para rol farmacia', () => {
      expect(getRolPrincipal({ rol: 'farmacia' })).toBe('FARMACIA');
      expect(getRolPrincipal({ rol: 'admin_farmacia' })).toBe('FARMACIA');
    });

    it('debe retornar CENTRO para roles FLUJO V2', () => {
      expect(getRolPrincipal({ rol: 'centro' })).toBe('CENTRO');
      expect(getRolPrincipal({ rol: 'medico' })).toBe('CENTRO');
      expect(getRolPrincipal({ rol: 'administrador_centro' })).toBe('CENTRO');
      expect(getRolPrincipal({ rol: 'director_centro' })).toBe('CENTRO');
    });

    it('debe retornar VISTA para rol vista', () => {
      expect(getRolPrincipal({ rol: 'vista' })).toBe('VISTA');
    });

    it('debe retornar FARMACIA para staff sin rol', () => {
      expect(getRolPrincipal({ is_staff: true })).toBe('FARMACIA');
    });

    it('debe retornar SIN_ROL para usuario sin rol', () => {
      expect(getRolPrincipal({})).toBe('SIN_ROL');
      expect(getRolPrincipal(null)).toBe('SIN_ROL');
    });

    it('debe usar grupos si están disponibles', () => {
      expect(getRolPrincipal({ rol: '' }, [{ name: 'FARMACIA_ADMIN' }])).toBe('FARMACIA');
      expect(getRolPrincipal({ rol: '' }, [{ name: 'CENTRO_USER' }])).toBe('CENTRO');
      expect(getRolPrincipal({ rol: '' }, [{ name: 'VISTA_USER' }])).toBe('VISTA');
    });
  });

  describe('Constantes de roles', () => {
    it('ADMIN_ROLES debe contener roles correctos', () => {
      expect(ADMIN_ROLES).toContain('admin');
      expect(ADMIN_ROLES).toContain('admin_sistema');
      expect(ADMIN_ROLES).toContain('superusuario');
    });

    it('FARMACIA_ROLES debe contener roles correctos', () => {
      expect(FARMACIA_ROLES).toContain('farmacia');
      expect(FARMACIA_ROLES).toContain('admin_farmacia');
    });

    it('CENTRO_ROLES debe contener roles FLUJO V2', () => {
      expect(CENTRO_ROLES).toContain('centro');
      expect(CENTRO_ROLES).toContain('medico');
      expect(CENTRO_ROLES).toContain('administrador_centro');
      expect(CENTRO_ROLES).toContain('director_centro');
    });

    it('VISTA_ROLES debe contener roles correctos', () => {
      expect(VISTA_ROLES).toContain('vista');
      expect(VISTA_ROLES).toContain('usuario_vista');
    });
  });

  // ISS-009 FIX: Tests para puedeEjecutarAccionFlujo
  describe('puedeEjecutarAccionFlujo (ISS-009)', () => {
    describe('Roles de Centro', () => {
      it('médico puede enviar_admin y confirmar_entrega', () => {
        const medico = { rol: 'medico' };
        expect(puedeEjecutarAccionFlujo(medico, 'enviar_admin')).toBe(true);
        expect(puedeEjecutarAccionFlujo(medico, 'confirmar_entrega')).toBe(true);
        expect(puedeEjecutarAccionFlujo(medico, 'reenviar')).toBe(true);
      });

      it('médico NO puede autorizar ni surtir', () => {
        const medico = { rol: 'medico' };
        expect(puedeEjecutarAccionFlujo(medico, 'autorizar_admin')).toBe(false);
        expect(puedeEjecutarAccionFlujo(medico, 'surtir')).toBe(false);
      });

      it('administrador_centro puede autorizar_admin y devolver', () => {
        const adminCentro = { rol: 'administrador_centro' };
        expect(puedeEjecutarAccionFlujo(adminCentro, 'autorizar_admin')).toBe(true);
        expect(puedeEjecutarAccionFlujo(adminCentro, 'devolver')).toBe(true);
        expect(puedeEjecutarAccionFlujo(adminCentro, 'rechazar')).toBe(true);
      });

      it('director_centro puede autorizar_director', () => {
        const director = { rol: 'director_centro' };
        expect(puedeEjecutarAccionFlujo(director, 'autorizar_director')).toBe(true);
        expect(puedeEjecutarAccionFlujo(director, 'devolver')).toBe(true);
      });
    });

    describe('Roles de Farmacia', () => {
      it('farmacia puede recibir, autorizar y surtir', () => {
        const farmacia = { rol: 'farmacia' };
        expect(puedeEjecutarAccionFlujo(farmacia, 'recibir_farmacia')).toBe(true);
        expect(puedeEjecutarAccionFlujo(farmacia, 'autorizar_farmacia')).toBe(true);
        expect(puedeEjecutarAccionFlujo(farmacia, 'surtir')).toBe(true);
      });

      it('farmacia NO puede autorizar como centro', () => {
        const farmacia = { rol: 'farmacia' };
        expect(puedeEjecutarAccionFlujo(farmacia, 'autorizar_admin')).toBe(false);
        expect(puedeEjecutarAccionFlujo(farmacia, 'autorizar_director')).toBe(false);
      });
    });

    describe('Admin y Superusuario', () => {
      it('admin puede ejecutar todas las acciones', () => {
        const admin = { rol: 'admin' };
        const acciones = [
          'enviar_admin', 'autorizar_admin', 'autorizar_director',
          'recibir_farmacia', 'autorizar_farmacia', 'surtir',
          'confirmar_entrega', 'devolver', 'rechazar', 'cancelar'
        ];
        acciones.forEach(accion => {
          expect(puedeEjecutarAccionFlujo(admin, accion)).toBe(true);
        });
      });

      it('superusuario puede ejecutar todas las acciones', () => {
        const superuser = { is_superuser: true };
        expect(puedeEjecutarAccionFlujo(superuser, 'autorizar_director')).toBe(true);
        expect(puedeEjecutarAccionFlujo(superuser, 'surtir')).toBe(true);
      });
    });

    describe('Seguridad', () => {
      it('usuario nulo no puede ejecutar acciones', () => {
        expect(puedeEjecutarAccionFlujo(null, 'surtir')).toBe(false);
        expect(puedeEjecutarAccionFlujo(undefined, 'autorizar_admin')).toBe(false);
      });

      it('acción desconocida retorna false', () => {
        expect(puedeEjecutarAccionFlujo({ rol: 'admin' }, 'accion_inexistente')).toBe(false);
      });
    });
  });
});
