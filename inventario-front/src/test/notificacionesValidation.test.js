/**
 * ISS-007 FIX: Tests para validación de notificaciones
 */
import { describe, it, expect } from 'vitest';
import {
  validarNotificacion,
  validarNotificacionesListResponse,
  validarNotificacionesCountResponse,
  normalizarNotificacion,
} from '../../utils/notificacionesValidation';

describe('notificacionesValidation', () => {
  describe('validarNotificacion', () => {
    it('valida notificación correcta', () => {
      const notif = {
        id: 1,
        tipo: 'info',
        mensaje: 'Test mensaje',
        leida: false,
        created_at: '2024-01-01T00:00:00Z',
      };
      const { valido, errores } = validarNotificacion(notif);
      expect(valido).toBe(true);
      expect(errores).toHaveLength(0);
    });

    it('rechaza null', () => {
      const { valido, errores } = validarNotificacion(null);
      expect(valido).toBe(false);
      expect(errores).toContain('La notificación debe ser un objeto');
    });

    it('rechaza undefined', () => {
      const { valido, errores } = validarNotificacion(undefined);
      expect(valido).toBe(false);
    });

    it('valida con id como string', () => {
      const notif = {
        id: 'uuid-123',
        mensaje: 'Test',
      };
      const { valido } = validarNotificacion(notif);
      expect(valido).toBe(true);
    });

    it('detecta tipo inválido', () => {
      const notif = {
        id: 1,
        tipo: 123, // debería ser string
        mensaje: 'Test',
      };
      const { valido, errores } = validarNotificacion(notif);
      expect(valido).toBe(false);
      expect(errores).toContain('tipo debe ser una cadena');
    });

    it('detecta leida inválida', () => {
      const notif = {
        id: 1,
        mensaje: 'Test',
        leida: 'true', // debería ser boolean
      };
      const { valido, errores } = validarNotificacion(notif);
      expect(valido).toBe(false);
      expect(errores).toContain('leida debe ser un booleano');
    });
  });

  describe('validarNotificacionesListResponse', () => {
    it('valida respuesta paginada de DRF', () => {
      const response = {
        results: [
          { id: 1, mensaje: 'Test 1' },
          { id: 2, mensaje: 'Test 2' },
        ],
        count: 10,
        next: 'http://api/notificaciones/?page=2',
        previous: null,
      };
      const { valido, data } = validarNotificacionesListResponse(response);
      expect(valido).toBe(true);
      expect(data.results).toHaveLength(2);
      expect(data.count).toBe(10);
      expect(data.next).toBe('http://api/notificaciones/?page=2');
    });

    it('valida array directo', () => {
      const response = [
        { id: 1, mensaje: 'Test 1' },
        { id: 2, mensaje: 'Test 2' },
      ];
      const { valido, data } = validarNotificacionesListResponse(response);
      expect(valido).toBe(true);
      expect(data.results).toHaveLength(2);
      expect(data.count).toBe(2);
      expect(data.next).toBeNull();
    });

    it('valida respuesta con data array', () => {
      const response = {
        data: [
          { id: 1, mensaje: 'Test' },
        ],
        total: 5,
      };
      const { valido, data } = validarNotificacionesListResponse(response);
      expect(valido).toBe(true);
      expect(data.results).toHaveLength(1);
      expect(data.count).toBe(5);
    });

    it('rechaza null', () => {
      const { valido, errores } = validarNotificacionesListResponse(null);
      expect(valido).toBe(false);
      expect(errores).toContain('Respuesta inválida');
    });

    it('rechaza formato no reconocido', () => {
      const response = { algo: 'otro' };
      const { valido, errores } = validarNotificacionesListResponse(response);
      expect(valido).toBe(false);
      expect(errores).toContain('Formato de respuesta no reconocido');
    });
  });

  describe('validarNotificacionesCountResponse', () => {
    it('extrae no_leidas', () => {
      const response = { no_leidas: 5 };
      const { valido, count } = validarNotificacionesCountResponse(response);
      expect(valido).toBe(true);
      expect(count).toBe(5);
    });

    it('extrae unread', () => {
      const response = { unread: 3 };
      const { valido, count } = validarNotificacionesCountResponse(response);
      expect(valido).toBe(true);
      expect(count).toBe(3);
    });

    it('extrae unread_count', () => {
      const response = { unread_count: 7 };
      const { valido, count } = validarNotificacionesCountResponse(response);
      expect(valido).toBe(true);
      expect(count).toBe(7);
    });

    it('usa 0 como fallback', () => {
      const response = {};
      const { valido, count } = validarNotificacionesCountResponse(response);
      expect(valido).toBe(true);
      expect(count).toBe(0);
    });

    it('rechaza null', () => {
      const { valido } = validarNotificacionesCountResponse(null);
      expect(valido).toBe(false);
    });

    it('rechaza conteo negativo', () => {
      // Esto no aplica ya que -0 es igual a 0 y el ?? fallback a 0 antes
      // Pero si explícitamente es negativo:
      const response = { no_leidas: -5 };
      const { valido } = validarNotificacionesCountResponse(response);
      expect(valido).toBe(false);
    });
  });

  describe('normalizarNotificacion', () => {
    it('normaliza campos estándar', () => {
      const raw = {
        id: 1,
        tipo: 'alerta',
        mensaje: 'Mensaje de prueba',
        leida: true,
        created_at: '2024-01-01T00:00:00Z',
      };
      const norm = normalizarNotificacion(raw);
      expect(norm.id).toBe(1);
      expect(norm.tipo).toBe('alerta');
      expect(norm.mensaje).toBe('Mensaje de prueba');
      expect(norm.leida).toBe(true);
    });

    it('mapea campos alternativos', () => {
      const raw = {
        id: 2,
        type: 'warning',
        message: 'Alt message',
        read: false,
        createdAt: '2024-06-01T12:00:00Z',
      };
      const norm = normalizarNotificacion(raw);
      expect(norm.tipo).toBe('warning');
      expect(norm.mensaje).toBe('Alt message');
      expect(norm.leida).toBe(false);
      expect(norm.created_at).toBe('2024-06-01T12:00:00Z');
    });

    it('usa valores por defecto', () => {
      const raw = { id: 3 };
      const norm = normalizarNotificacion(raw);
      expect(norm.tipo).toBe('info');
      expect(norm.mensaje).toBe('');
      expect(norm.leida).toBe(false);
      expect(norm.prioridad).toBe('normal');
      expect(norm.enlace).toBeNull();
    });

    it('preserva data adicional', () => {
      const raw = {
        id: 4,
        mensaje: 'Test',
        data: { requisicion_id: 123 },
      };
      const norm = normalizarNotificacion(raw);
      expect(norm.data.requisicion_id).toBe(123);
    });
  });
});
