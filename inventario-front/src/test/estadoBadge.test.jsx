/**
 * Tests de componentes FLUJO V2
 * 
 * Verifica:
 * - EstadoBadge renderiza correctamente
 * - getEstadoBadgeClasses retorna clases válidas
 * - getEstadoLabel retorna etiquetas correctas
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { 
  EstadoBadge, 
  getEstadoBadgeClasses, 
  getEstadoLabel,
  getEstadoConfig 
} from '../components/EstadoBadge';

describe('EstadoBadge Component', () => {
  describe('getEstadoConfig', () => {
    it('retorna configuración para borrador', () => {
      const config = getEstadoConfig('borrador');
      expect(config).toBeDefined();
      expect(config.label).toBe('Borrador');
      expect(config.color).toBe('gray');
    });
    
    it('retorna configuración para pendiente_admin', () => {
      const config = getEstadoConfig('pendiente_admin');
      expect(config).toBeDefined();
      expect(config.label).toBe('Pendiente Admin');
    });
    
    it('retorna configuración para pendiente_director', () => {
      const config = getEstadoConfig('pendiente_director');
      expect(config).toBeDefined();
      expect(config.label).toBe('Pendiente Director');
    });
    
    it('retorna configuración para enviada', () => {
      const config = getEstadoConfig('enviada');
      expect(config).toBeDefined();
      expect(config.label).toBe('Enviada a Farmacia');
      expect(config.color).toBe('blue');
    });
    
    it('retorna configuración para en_revision', () => {
      const config = getEstadoConfig('en_revision');
      expect(config).toBeDefined();
      expect(config.label).toBe('En Revisión');
    });
    
    it('retorna configuración para autorizada', () => {
      const config = getEstadoConfig('autorizada');
      expect(config).toBeDefined();
      expect(config.label).toBe('Autorizada');
    });
    
    it('retorna configuración para surtida', () => {
      const config = getEstadoConfig('surtida');
      expect(config).toBeDefined();
      expect(config.label).toBe('Surtida');
    });
    
    it('retorna configuración para entregada', () => {
      const config = getEstadoConfig('entregada');
      expect(config).toBeDefined();
      expect(config.label).toBe('Entregada');
      expect(config.color).toBe('green');
    });
    
    it('retorna configuración para rechazada', () => {
      const config = getEstadoConfig('rechazada');
      expect(config).toBeDefined();
      expect(config.label).toBe('Rechazada');
      expect(config.color).toBe('red');
    });
    
    it('retorna configuración para vencida', () => {
      const config = getEstadoConfig('vencida');
      expect(config).toBeDefined();
      expect(config.label).toBe('Vencida');
      expect(config.color).toBe('red');
    });
    
    it('retorna configuración para cancelada', () => {
      const config = getEstadoConfig('cancelada');
      expect(config).toBeDefined();
      expect(config.label).toBe('Cancelada');
    });
    
    it('retorna configuración para devuelta', () => {
      const config = getEstadoConfig('devuelta');
      expect(config).toBeDefined();
      expect(config.label).toBe('Devuelta');
      expect(config.color).toBe('amber');
    });
    
    it('maneja estado desconocido graciosamente', () => {
      const config = getEstadoConfig('estado_inventado');
      expect(config).toBeDefined();
      expect(config.color).toBe('gray');
    });
    
    it('maneja null/undefined graciosamente', () => {
      expect(getEstadoConfig(null)).toBeDefined();
      expect(getEstadoConfig(undefined)).toBeDefined();
    });
  });
  
  describe('getEstadoBadgeClasses', () => {
    it('retorna clases CSS válidas para borrador', () => {
      const classes = getEstadoBadgeClasses('borrador');
      expect(classes).toContain('bg-gray');
      expect(classes).toContain('text-gray');
    });
    
    it('retorna clases CSS válidas para entregada', () => {
      const classes = getEstadoBadgeClasses('entregada');
      expect(classes).toContain('bg-green');
      expect(classes).toContain('text-green');
    });
    
    it('retorna clases CSS válidas para rechazada', () => {
      const classes = getEstadoBadgeClasses('rechazada');
      expect(classes).toContain('bg-red');
      expect(classes).toContain('text-red');
    });
    
    it('retorna clases CSS válidas para enviada', () => {
      const classes = getEstadoBadgeClasses('enviada');
      expect(classes).toContain('bg-blue');
      expect(classes).toContain('text-blue');
    });
    
    it('retorna clases para estado desconocido', () => {
      const classes = getEstadoBadgeClasses('unknown');
      expect(classes).toBeTruthy();
      expect(classes).toContain('gray');
    });
  });
  
  describe('getEstadoLabel', () => {
    // getEstadoLabel retorna labels en MAYÚSCULAS para consistencia visual
    const casosEsperados = [
      ['borrador', 'BORRADOR'],
      ['pendiente_admin', 'PENDIENTE ADMIN'],
      ['pendiente_director', 'PENDIENTE DIRECTOR'],
      ['enviada', 'ENVIADA A FARMACIA'],
      ['en_revision', 'EN REVISIÓN'],
      ['autorizada', 'AUTORIZADA'],
      ['surtida', 'SURTIDA'],
      ['entregada', 'ENTREGADA'],
      ['rechazada', 'RECHAZADA'],
      ['vencida', 'VENCIDA'],
      ['cancelada', 'CANCELADA'],
      ['devuelta', 'DEVUELTA'],
    ];
    
    casosEsperados.forEach(([estado, labelEsperado]) => {
      it(`retorna "${labelEsperado}" para "${estado}"`, () => {
        expect(getEstadoLabel(estado)).toBe(labelEsperado);
      });
    });
    
    it('retorna el estado original si no tiene label definido', () => {
      const label = getEstadoLabel('estado_raro');
      expect(label).toBeTruthy();
    });
  });
  
  describe('EstadoBadge render', () => {
    it('renderiza badge para borrador', () => {
      render(<EstadoBadge estado="borrador" />);
      expect(screen.getByText('Borrador')).toBeDefined();
    });
    
    it('renderiza badge para entregada', () => {
      render(<EstadoBadge estado="entregada" />);
      expect(screen.getByText('Entregada')).toBeDefined();
    });
    
    it('renderiza badge para rechazada', () => {
      render(<EstadoBadge estado="rechazada" />);
      expect(screen.getByText('Rechazada')).toBeDefined();
    });
    
    it('renderiza badge con size sm', () => {
      const { container } = render(<EstadoBadge estado="borrador" size="sm" />);
      expect(container.querySelector('.text-xs')).toBeDefined();
    });
    
    it('renderiza badge con size lg', () => {
      const { container } = render(<EstadoBadge estado="borrador" size="lg" />);
      expect(container.querySelector('.text-base')).toBeDefined();
    });
    
    it('renderiza badge sin ícono cuando showIcon=false', () => {
      const { container } = render(<EstadoBadge estado="borrador" showIcon={false} />);
      // No debe haber emoji en el texto
      const text = container.textContent;
      expect(text).toBe('Borrador');
    });
  });
});

describe('Colores de Estado', () => {
  // Colores reales según REQUISICION_ESTADOS
  const coloresEsperados = {
    borrador: 'gray',
    pendiente_admin: 'yellow',
    pendiente_director: 'orange',
    enviada: 'blue',
    en_revision: 'cyan',
    autorizada: 'indigo',
    en_surtido: 'violet',
    surtida: 'teal', // Corregido: surtida es teal
    entregada: 'green',
    rechazada: 'red',
    vencida: 'red',
    cancelada: 'gray',
    devuelta: 'amber',
    parcial: 'purple', // Corregido: parcial es purple
  };
  
  Object.entries(coloresEsperados).forEach(([estado, colorEsperado]) => {
    it(`estado "${estado}" tiene color "${colorEsperado}"`, () => {
      const config = getEstadoConfig(estado);
      expect(config.color).toBe(colorEsperado);
    });
  });
});
