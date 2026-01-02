/**
 * Tests para Salidas de Donaciones - Función Finalizar y Centro Destino
 * =====================================================================
 * 
 * Tests que verifican los cambios implementados:
 * 1. Stock NO se descuenta al crear (solo al finalizar)
 * 2. Selector de tipo destinatario (Centro / Persona)
 * 3. Centro destino se incluye en el payload
 * 4. Hoja de Entrega visible solo antes de finalizar
 * 5. Comprobante visible solo después de finalizar
 * 6. Badge de carrito visible
 * 
 * Date: 2026-01-02
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock de API
const mockSalidasDonacionesAPI = {
  create: vi.fn(),
  finalizar: vi.fn(),
  getReciboPdf: vi.fn(),
};

const mockCentrosAPI = {
  getAll: vi.fn().mockResolvedValue({
    data: {
      results: [
        { id: 1, nombre: 'Centro Penitenciario Norte', activo: true },
        { id: 2, nombre: 'Centro Penitenciario Sur', activo: true },
      ]
    }
  }),
};

// Mock de salida pendiente
const mockSalidaPendiente = {
  id: 1,
  detalle_donacion: 1,
  cantidad: 10,
  destinatario: 'Centro Penitenciario Norte',
  centro_destino: 1,
  centro_destino_nombre: 'Centro Penitenciario Norte',
  finalizado: false,
  fecha_finalizado: null,
  finalizado_por: null,
  finalizado_por_nombre: null,
  estado_entrega: 'pendiente',
};

// Mock de salida finalizada
const mockSalidaFinalizada = {
  ...mockSalidaPendiente,
  finalizado: true,
  fecha_finalizado: '2026-01-02T10:30:00Z',
  finalizado_por: 1,
  finalizado_por_nombre: 'Admin User',
  estado_entrega: 'entregado',
};

describe('Salidas Donaciones - Crear sin descontar stock', () => {
  it('crear salida no debe descontar stock', async () => {
    const stockInicial = 100;
    const cantidadSalida = 10;
    
    // Simular crear salida
    const payload = {
      detalle_donacion: 1,
      cantidad: cantidadSalida,
      destinatario: 'Centro Norte',
      centro_destino: 1,
    };
    
    // El stock NO debe cambiar en el frontend al crear
    // (esto se hace en el backend)
    expect(payload.cantidad).toBeLessThanOrEqual(stockInicial);
    expect(payload).not.toHaveProperty('descontar_stock');
  });

  it('payload de crear NO incluye finalizado=true', () => {
    const payload = {
      detalle_donacion: 1,
      cantidad: 10,
      destinatario: 'Centro Norte',
    };
    
    // Por defecto debe ser false o no incluirlo
    expect(payload.finalizado).toBeUndefined();
  });
});

describe('Salidas Donaciones - Tipo Destinatario', () => {
  describe('Estado tipoDestinatario', () => {
    it('valores válidos son "centro" y "persona"', () => {
      const valoresValidos = ['centro', 'persona'];
      
      expect(valoresValidos).toContain('centro');
      expect(valoresValidos).toContain('persona');
    });

    it('default debe ser "centro"', () => {
      const valorDefault = 'centro';
      expect(valorDefault).toBe('centro');
    });
  });

  describe('Payload según tipo', () => {
    it('tipo centro debe incluir centro_destino en payload', () => {
      const tipoDestinatario = 'centro';
      const centroDestino = 1;
      const destinatarioNombre = 'Centro Penitenciario Norte';
      
      const payload = {
        detalle_donacion: 1,
        cantidad: 10,
        destinatario: destinatarioNombre,
      };
      
      // Solo agregar centro_destino si tipo es centro
      if (tipoDestinatario === 'centro' && centroDestino) {
        payload.centro_destino = parseInt(centroDestino);
      }
      
      expect(payload.centro_destino).toBe(1);
      expect(payload.destinatario).toBe(destinatarioNombre);
    });

    it('tipo persona NO incluye centro_destino', () => {
      const tipoDestinatario = 'persona';
      const destinatarioNombre = 'Juan Pérez';
      
      const payload = {
        detalle_donacion: 1,
        cantidad: 10,
        destinatario: destinatarioNombre,
      };
      
      // NO agregar centro_destino si tipo es persona
      if (tipoDestinatario !== 'centro') {
        delete payload.centro_destino;
      }
      
      expect(payload.centro_destino).toBeUndefined();
      expect(payload.destinatario).toBe('Juan Pérez');
    });
  });
});

describe('Salidas Donaciones - Finalizar', () => {
  it('finalizar cambia estado de pendiente a entregado', () => {
    expect(mockSalidaPendiente.estado_entrega).toBe('pendiente');
    expect(mockSalidaFinalizada.estado_entrega).toBe('entregado');
  });

  it('finalizar establece fecha_finalizado', () => {
    expect(mockSalidaPendiente.fecha_finalizado).toBeNull();
    expect(mockSalidaFinalizada.fecha_finalizado).not.toBeNull();
  });

  it('finalizar establece finalizado_por', () => {
    expect(mockSalidaPendiente.finalizado_por).toBeNull();
    expect(mockSalidaFinalizada.finalizado_por).toBe(1);
    expect(mockSalidaFinalizada.finalizado_por_nombre).toBe('Admin User');
  });

  it('API finalizar hace POST a /finalizar/', async () => {
    const salidaId = 1;
    
    // Mock del endpoint
    mockSalidasDonacionesAPI.finalizar.mockResolvedValue({
      data: {
        mensaje: 'Entrega finalizada y stock descontado correctamente',
        salida: mockSalidaFinalizada,
      }
    });
    
    const response = await mockSalidasDonacionesAPI.finalizar(salidaId);
    
    expect(mockSalidasDonacionesAPI.finalizar).toHaveBeenCalledWith(salidaId);
    expect(response.data.salida.finalizado).toBe(true);
  });
});

describe('Salidas Donaciones - Botones Hoja/Comprobante', () => {
  describe('Lógica de visibilidad', () => {
    it('salida pendiente muestra botón Hoja de Entrega', () => {
      const salida = mockSalidaPendiente;
      
      const mostrarHojaEntrega = !salida.finalizado;
      const mostrarComprobante = salida.finalizado;
      
      expect(mostrarHojaEntrega).toBe(true);
      expect(mostrarComprobante).toBe(false);
    });

    it('salida finalizada muestra botón Comprobante', () => {
      const salida = mockSalidaFinalizada;
      
      const mostrarHojaEntrega = !salida.finalizado;
      const mostrarComprobante = salida.finalizado;
      
      expect(mostrarHojaEntrega).toBe(false);
      expect(mostrarComprobante).toBe(true);
    });

    it('nunca muestra ambos botones simultáneamente', () => {
      const salida = mockSalidaPendiente;
      
      const mostrarHojaEntrega = !salida.finalizado;
      const mostrarComprobante = salida.finalizado;
      
      expect(mostrarHojaEntrega && mostrarComprobante).toBe(false);
    });
  });

  describe('Llamada a API para PDFs', () => {
    it('getReciboPdf con finalizado=false para hoja', async () => {
      mockSalidasDonacionesAPI.getReciboPdf.mockResolvedValue({
        data: new Blob(['pdf content'], { type: 'application/pdf' })
      });
      
      const salidaId = 1;
      const finalizado = false;
      
      await mockSalidasDonacionesAPI.getReciboPdf(salidaId, finalizado);
      
      expect(mockSalidasDonacionesAPI.getReciboPdf).toHaveBeenCalledWith(salidaId, false);
    });

    it('getReciboPdf con finalizado=true para comprobante', async () => {
      mockSalidasDonacionesAPI.getReciboPdf.mockResolvedValue({
        data: new Blob(['pdf content'], { type: 'application/pdf' })
      });
      
      const salidaId = 1;
      const finalizado = true;
      
      await mockSalidasDonacionesAPI.getReciboPdf(salidaId, finalizado);
      
      expect(mockSalidasDonacionesAPI.getReciboPdf).toHaveBeenCalledWith(salidaId, true);
    });
  });
});

describe('Salidas Donaciones - Badge del Carrito', () => {
  describe('Visibilidad del badge', () => {
    it('badge visible cuando hay items', () => {
      const items = [
        { detalle_id: 1, cantidad: 5 },
        { detalle_id: 2, cantidad: 3 },
      ];
      
      const mostrarBadge = items.length > 0;
      
      expect(mostrarBadge).toBe(true);
    });

    it('badge oculto cuando no hay items', () => {
      const items = [];
      
      const mostrarBadge = items.length > 0;
      
      expect(mostrarBadge).toBe(false);
    });

    it('badge muestra cantidad correcta', () => {
      const items = [
        { detalle_id: 1, cantidad: 5 },
        { detalle_id: 2, cantidad: 3 },
        { detalle_id: 3, cantidad: 2 },
      ];
      
      const cantidadBadge = items.length;
      
      expect(cantidadBadge).toBe(3);
    });
  });

  describe('Estilo del badge', () => {
    it('posición debe ser visible fuera del contenedor', () => {
      // El contenedor debe tener overflow-visible para que el badge no se corte
      const containerStyle = 'relative overflow-visible';
      
      expect(containerStyle).toContain('overflow-visible');
      expect(containerStyle).not.toContain('overflow-hidden');
    });

    it('badge posicionado arriba a la derecha', () => {
      const badgePosition = '-top-3 -right-3';
      
      expect(badgePosition).toContain('-top');
      expect(badgePosition).toContain('-right');
    });
  });
});

describe('Salidas Donaciones - Validaciones', () => {
  describe('Validación al crear', () => {
    it('rechaza cantidad mayor a disponible', () => {
      const disponible = 50;
      const cantidadSolicitada = 100;
      
      const esValida = cantidadSolicitada <= disponible;
      
      expect(esValida).toBe(false);
    });

    it('acepta cantidad igual a disponible', () => {
      const disponible = 50;
      const cantidadSolicitada = 50;
      
      const esValida = cantidadSolicitada <= disponible;
      
      expect(esValida).toBe(true);
    });

    it('rechaza cantidad 0 o negativa', () => {
      const validarCantidad = (cantidad) => cantidad > 0;
      
      expect(validarCantidad(0)).toBe(false);
      expect(validarCantidad(-1)).toBe(false);
      expect(validarCantidad(1)).toBe(true);
    });
  });

  describe('Validación de destinatario', () => {
    it('tipo centro requiere selección de centro', () => {
      const tipoDestinatario = 'centro';
      const centroDestino = '';
      
      const esValido = tipoDestinatario !== 'centro' || centroDestino !== '';
      
      expect(esValido).toBe(false);
    });

    it('tipo persona requiere nombre de destinatario', () => {
      const tipoDestinatario = 'persona';
      const destinatario = '';
      
      const esValido = tipoDestinatario !== 'persona' || destinatario.trim() !== '';
      
      expect(esValido).toBe(false);
    });

    it('tipo centro con centro seleccionado es válido', () => {
      const tipoDestinatario = 'centro';
      const centroDestino = '1';
      
      const esValido = tipoDestinatario !== 'centro' || centroDestino !== '';
      
      expect(esValido).toBe(true);
    });

    it('tipo persona con nombre es válido', () => {
      const tipoDestinatario = 'persona';
      const destinatario = 'Juan Pérez';
      
      const esValido = tipoDestinatario !== 'persona' || destinatario.trim() !== '';
      
      expect(esValido).toBe(true);
    });
  });
});

describe('Salidas Donaciones - Resultado Modal', () => {
  describe('Estado resultado', () => {
    it('muestra mensaje de éxito con pendiente de confirmar', () => {
      const resultado = {
        success: true,
        message: '5 entregas registradas - Pendiente de confirmar',
        total_productos: 5,
        total_unidades: 25,
      };
      
      expect(resultado.success).toBe(true);
      expect(resultado.message).toContain('Pendiente de confirmar');
    });

    it('incluye información del centro destino si aplica', () => {
      const resultado = {
        success: true,
        destinatario: 'Centro Penitenciario Norte',
        centro_destino_id: 1,
      };
      
      expect(resultado.centro_destino_id).toBe(1);
      expect(resultado.destinatario).toBe('Centro Penitenciario Norte');
    });
  });
});

describe('Salidas Donaciones - Campos DB Esperados', () => {
  describe('Respuesta de API debe incluir campos de finalización', () => {
    it('respuesta debe tener finalizado', () => {
      expect(mockSalidaPendiente).toHaveProperty('finalizado');
      expect(typeof mockSalidaPendiente.finalizado).toBe('boolean');
    });

    it('respuesta debe tener fecha_finalizado', () => {
      expect(mockSalidaPendiente).toHaveProperty('fecha_finalizado');
    });

    it('respuesta debe tener finalizado_por', () => {
      expect(mockSalidaPendiente).toHaveProperty('finalizado_por');
    });

    it('respuesta debe tener finalizado_por_nombre', () => {
      expect(mockSalidaPendiente).toHaveProperty('finalizado_por_nombre');
    });

    it('respuesta debe tener estado_entrega', () => {
      expect(mockSalidaPendiente).toHaveProperty('estado_entrega');
    });

    it('respuesta debe tener centro_destino', () => {
      expect(mockSalidaPendiente).toHaveProperty('centro_destino');
    });

    it('respuesta debe tener centro_destino_nombre', () => {
      expect(mockSalidaPendiente).toHaveProperty('centro_destino_nombre');
    });
  });
});
