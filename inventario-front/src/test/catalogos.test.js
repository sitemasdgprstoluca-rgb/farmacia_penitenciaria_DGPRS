/**
 * ISS-007 FIX: Tests para el hook useCatalogos
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { getCatalogosSync, invalidarCacheCatalogos } from '../../hooks/useCatalogos';

// Mock del API
vi.mock('../../services/api', () => ({
  catalogosAPI: {
    getAll: vi.fn(),
    unidadesMedida: vi.fn(),
    categorias: vi.fn(),
    viasAdministracion: vi.fn(),
    estadosRequisicion: vi.fn(),
    tiposMovimiento: vi.fn(),
  },
}));

describe('useCatalogos utilities', () => {
  beforeEach(() => {
    // Limpiar cache antes de cada test
    invalidarCacheCatalogos();
  });

  describe('getCatalogosSync', () => {
    it('retorna fallbacks cuando no hay cache', () => {
      const { catalogos, isFromFallback } = getCatalogosSync();
      
      expect(isFromFallback).toBe(true);
      expect(catalogos.unidades).toContain('AMPOLLETA');
      expect(catalogos.unidades).toContain('TABLETA');
      expect(catalogos.categorias).toContain('medicamento');
      expect(catalogos.viasAdministracion).toContain('ORAL');
      expect(catalogos.estadosRequisicion).toContain('borrador');
      expect(catalogos.tiposMovimiento).toContain('entrada');
    });

    it('fallback de unidades tiene valores esperados', () => {
      const { catalogos } = getCatalogosSync();
      
      const unidadesEsperadas = [
        'AMPOLLETA', 'CAJA', 'CAPSULA', 'FRASCO',
        'GR', 'ML', 'PIEZA', 'SOBRE', 'TABLETA'
      ];
      
      unidadesEsperadas.forEach(unidad => {
        expect(catalogos.unidades).toContain(unidad);
      });
    });

    it('fallback de categorías tiene valores esperados', () => {
      const { catalogos } = getCatalogosSync();
      
      const categoriasEsperadas = [
        'medicamento', 'material_curacion', 'equipo_medico', 'insumo'
      ];
      
      categoriasEsperadas.forEach(cat => {
        expect(catalogos.categorias).toContain(cat);
      });
    });

    it('fallback de estados requisición tiene valores esperados', () => {
      const { catalogos } = getCatalogosSync();
      
      const estadosEsperados = [
        'borrador', 'pendiente', 'aprobada', 'en_proceso',
        'surtida_parcial', 'surtida', 'rechazada', 'cancelada'
      ];
      
      estadosEsperados.forEach(estado => {
        expect(catalogos.estadosRequisicion).toContain(estado);
      });
    });
  });

  describe('invalidarCacheCatalogos', () => {
    it('no lanza error al llamar sin cache', () => {
      expect(() => invalidarCacheCatalogos()).not.toThrow();
    });

    it('puede llamarse múltiples veces', () => {
      invalidarCacheCatalogos();
      invalidarCacheCatalogos();
      invalidarCacheCatalogos();
      
      const { isFromFallback } = getCatalogosSync();
      expect(isFromFallback).toBe(true);
    });
  });
});
