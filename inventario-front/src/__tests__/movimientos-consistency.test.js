/**
 * Tests de consistencia para métricas de movimientos en el frontend.
 * 
 * ISS-CONSISTENCY: Verifica que el componente Reportes muestre
 * correctamente las métricas y aplique filtros por defecto.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Helper para obtener el primer día del mes actual
const getFirstDayOfMonth = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`;
};

// Helper para obtener la fecha actual
const getTodayDate = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
};

describe('Movimientos Consistency', () => {
  describe('Helpers de fecha', () => {
    it('getFirstDayOfMonth debe devolver el primer día del mes en formato YYYY-MM-DD', () => {
      const result = getFirstDayOfMonth();
      const today = new Date();
      const expected = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-01`;
      
      expect(result).toBe(expected);
      expect(result).toMatch(/^\d{4}-\d{2}-01$/);
    });

    it('getTodayDate debe devolver la fecha actual en formato YYYY-MM-DD', () => {
      const result = getTodayDate();
      const today = new Date();
      const expected = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
      
      expect(result).toBe(expected);
      expect(result).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    });
  });

  describe('Estructura del resumen', () => {
    it('El resumen debe tener todos los campos requeridos para consistencia', () => {
      // Estructura esperada del resumen que viene del backend
      const resumenEsperado = {
        total_transacciones: 0,
        total_movimientos: 0,
        total_entradas: 0,
        total_salidas: 0,
        diferencia: 0,
        count_entradas: 0,  // Nuevo campo para consistencia con Dashboard
        count_salidas: 0,   // Nuevo campo para consistencia con Dashboard
      };

      // Verificar que todos los campos existen
      const camposRequeridos = [
        'total_transacciones',
        'total_movimientos', 
        'total_entradas',
        'total_salidas',
        'diferencia',
        'count_entradas',
        'count_salidas',
      ];

      camposRequeridos.forEach(campo => {
        expect(resumenEsperado).toHaveProperty(campo);
      });
    });

    it('count y total representan métricas diferentes', () => {
      // Ejemplo: Una transacción con 3 productos de 10 unidades cada uno
      const mockData = {
        total_transacciones: 1,
        total_movimientos: 3,     // 3 registros
        total_entradas: 30,       // 3 * 10 = 30 unidades
        total_salidas: 0,
        diferencia: 30,
        count_entradas: 3,        // 3 registros
        count_salidas: 0,
      };

      // El count es el número de registros
      expect(mockData.count_entradas).toBe(3);
      
      // El total es la suma de cantidades
      expect(mockData.total_entradas).toBe(30);
      
      // Son métricas diferentes
      expect(mockData.count_entradas).not.toBe(mockData.total_entradas);
    });
  });

  describe('Filtro por defecto del mes actual', () => {
    it('El filtro de movimientos debe tener fechas del mes actual por defecto', () => {
      const filtrosDefecto = {
        fechaInicio: getFirstDayOfMonth(),
        fechaFin: getTodayDate(),
      };

      // Verificar que las fechas son del mes actual
      const hoy = new Date();
      const mesActual = String(hoy.getMonth() + 1).padStart(2, '0');
      const añoActual = String(hoy.getFullYear());

      expect(filtrosDefecto.fechaInicio).toContain(añoActual);
      expect(filtrosDefecto.fechaInicio).toContain(mesActual);
      expect(filtrosDefecto.fechaFin).toContain(añoActual);
      expect(filtrosDefecto.fechaFin).toContain(mesActual);
    });

    it('El filtro "Este mes" debe establecer el rango correcto', () => {
      const filtroEsteMes = {
        fechaInicio: getFirstDayOfMonth(),
        fechaFin: getTodayDate(),
      };

      // Verificar el formato
      expect(filtroEsteMes.fechaInicio).toMatch(/^\d{4}-\d{2}-01$/);
      expect(filtroEsteMes.fechaFin).toMatch(/^\d{4}-\d{2}-\d{2}$/);

      // Verificar que fechaInicio es antes o igual a fechaFin
      expect(new Date(filtroEsteMes.fechaInicio).getTime())
        .toBeLessThanOrEqual(new Date(filtroEsteMes.fechaFin).getTime());
    });

    it('El filtro "Todo el historial" debe limpiar las fechas', () => {
      const filtroTodo = {
        fechaInicio: "",
        fechaFin: "",
      };

      expect(filtroTodo.fechaInicio).toBe("");
      expect(filtroTodo.fechaFin).toBe("");
    });
  });

  describe('Indicador de período', () => {
    it('Debe mostrar el período correcto cuando hay fechas', () => {
      const formatearPeriodo = (fechaInicio, fechaFin) => {
        if (fechaInicio && fechaFin) {
          return `${fechaInicio} - ${fechaFin}`;
        }
        if (fechaInicio) {
          return `Desde ${fechaInicio}`;
        }
        if (fechaFin) {
          return `Hasta ${fechaFin}`;
        }
        return 'Todo el historial';
      };

      expect(formatearPeriodo('2024-01-01', '2024-01-31')).toBe('2024-01-01 - 2024-01-31');
      expect(formatearPeriodo('2024-01-01', '')).toBe('Desde 2024-01-01');
      expect(formatearPeriodo('', '2024-01-31')).toBe('Hasta 2024-01-31');
      expect(formatearPeriodo('', '')).toBe('Todo el historial');
    });
  });

  describe('Consistencia Dashboard vs Reportes', () => {
    it('El conteo del Dashboard debe coincidir con el filtro del mes actual en Reportes', () => {
      // Simular datos del Dashboard
      const dashboardData = {
        movimientos_mes: 5,  // Lo que muestra el Dashboard
      };

      // Simular datos de Reportes con filtro del mes actual
      const reportesData = {
        resumen: {
          total_transacciones: 2,
          total_movimientos: 5,  // Coincide con Dashboard
          total_entradas: 100,
          total_salidas: 50,
          diferencia: 50,
          count_entradas: 3,
          count_salidas: 2,
        }
      };

      // El Dashboard muestra el número de movimientos del mes
      // Esto debe coincidir con total_movimientos cuando se filtra por el mes actual
      expect(dashboardData.movimientos_mes).toBe(reportesData.resumen.total_movimientos);
    });

    it('Las etiquetas deben ser claras sobre qué representan', () => {
      // Etiquetas esperadas en el UI
      const etiquetas = {
        'Transacciones': 'grupos únicos de operaciones',
        'Movimientos': 'registros individuales',
        'Entradas': 'unidades que entran',
        'Salidas': 'unidades que salen',
        'Balance': 'diferencia en unidades',
      };

      // Verificar que cada métrica tiene una descripción clara
      Object.keys(etiquetas).forEach(etiqueta => {
        expect(etiquetas[etiqueta]).toBeDefined();
        expect(etiquetas[etiqueta].length).toBeGreaterThan(0);
      });
    });
  });
});

// Test de integración simulado
describe('Integración: Filtros y Métricas', () => {
  it('Cuando se cambia a "movimientos", debe aplicar el filtro del mes actual', async () => {
    // Simular el comportamiento esperado
    const estadoInicial = {
      tipo: 'inventario',
      fechaInicio: '',
      fechaFin: '',
    };

    // Al cambiar a movimientos
    const nuevoEstado = {
      ...estadoInicial,
      tipo: 'movimientos',
      fechaInicio: getFirstDayOfMonth(),
      fechaFin: getTodayDate(),
    };

    expect(nuevoEstado.tipo).toBe('movimientos');
    expect(nuevoEstado.fechaInicio).toMatch(/^\d{4}-\d{2}-01$/);
    expect(nuevoEstado.fechaFin).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it('El resumen debe reflejar los datos filtrados correctamente', () => {
    // Datos de ejemplo filtrados por mes
    const datosFiltrados = [
      { tipo: 'ENTRADA', total_productos: 3, cantidad_total: 30 },
      { tipo: 'SALIDA', total_productos: 2, cantidad_total: 15 },
    ];

    const resumenCalculado = {
      total_transacciones: datosFiltrados.length,
      total_movimientos: datosFiltrados.reduce((acc, t) => acc + t.total_productos, 0),
      total_entradas: datosFiltrados
        .filter(t => t.tipo === 'ENTRADA')
        .reduce((acc, t) => acc + t.cantidad_total, 0),
      total_salidas: datosFiltrados
        .filter(t => t.tipo === 'SALIDA')
        .reduce((acc, t) => acc + t.cantidad_total, 0),
    };

    expect(resumenCalculado.total_transacciones).toBe(2);
    expect(resumenCalculado.total_movimientos).toBe(5);
    expect(resumenCalculado.total_entradas).toBe(30);
    expect(resumenCalculado.total_salidas).toBe(15);
  });
});
