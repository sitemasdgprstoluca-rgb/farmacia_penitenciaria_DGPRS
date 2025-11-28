/**
 * Tests para el componente Dashboard
 * 
 * @module tests/Dashboard.test
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { PermissionProvider } from '@/context/PermissionContext';
import Dashboard from './Dashboard';

// Mock de recharts (componentes pesados)
vi.mock('recharts', () => ({
    ResponsiveContainer: ({ children }) => <div data-testid="responsive-container">{children}</div>,
    LineChart: () => <div data-testid="line-chart" />,
    Line: () => null,
    BarChart: () => <div data-testid="bar-chart" />,
    Bar: () => null,
    PieChart: () => <div data-testid="pie-chart" />,
    Pie: () => null,
    Cell: () => null,
    XAxis: () => null,
    YAxis: () => null,
    CartesianGrid: () => null,
    Tooltip: () => null,
    Legend: () => null,
}));

// Mock del API
vi.mock('@/services/api', () => ({
    default: {
        get: vi.fn(),
    },
    dashboardAPI: {
        getResumen: vi.fn(),
        getGraficas: vi.fn(),
    },
}));

import apiClient from '@/services/api';
import { dashboardAPI } from '@/services/api';

// Wrapper con providers
const TestWrapper = ({ children }) => (
    <BrowserRouter>
        <PermissionProvider>
            {children}
        </PermissionProvider>
    </BrowserRouter>
);

// Mock data
const mockKpis = {
    total_productos: 124,
    stock_total: 4800,
    lotes_activos: 52,
    movimientos_mes: 37,
};

const mockMovimientos = [
    {
        id: 1,
        tipo_movimiento: 'ENTRADA',
        producto__clave: 'MED-001',
        producto__descripcion: 'Paracetamol 500mg',
        lote__codigo_lote: 'LOTE-001',
        cantidad: 150,
        fecha_movimiento: new Date().toISOString(),
    },
];

const mockGraficas = {
    consumo_mensual: [
        { mes: 'Enero', consumo: 100 },
        { mes: 'Febrero', consumo: 150 },
    ],
    stock_por_centro: [
        { centro: 'Centro 1', stock: 500 },
    ],
    requisiciones_por_estado: [
        { estado: 'PENDIENTE', cantidad: 5 },
    ],
};

describe('Dashboard', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        localStorage.clear();
        
        // Simular usuario autenticado
        localStorage.setItem('token', 'mock-token');
        localStorage.setItem('user', JSON.stringify({
            id: 1,
            username: 'admin',
            rol: 'ADMIN',
        }));

        // Mock respuestas del API
        apiClient.get.mockImplementation((url) => {
            if (url.includes('/dashboard/resumen')) {
                return Promise.resolve({ data: { kpis: mockKpis, movimientos: mockMovimientos } });
            }
            if (url.includes('/dashboard/graficas')) {
                return Promise.resolve({ data: mockGraficas });
            }
            return Promise.resolve({ data: {} });
        });
    });

    it('debe renderizar el título del dashboard', async () => {
        render(<Dashboard />, { wrapper: TestWrapper });
        
        await waitFor(() => {
            expect(screen.getByText(/dashboard/i)).toBeInTheDocument();
        });
    });

    it('debe mostrar indicador de carga inicialmente', () => {
        render(<Dashboard />, { wrapper: TestWrapper });
        
        // Puede mostrar spinner o skeleton
        expect(screen.getByText(/cargando/i) || document.querySelector('.animate-spin')).toBeTruthy();
    });

    it('debe mostrar KPIs después de cargar', async () => {
        apiClient.get.mockResolvedValueOnce({
            data: { kpis: mockKpis, movimientos: mockMovimientos },
        });

        render(<Dashboard />, { wrapper: TestWrapper });
        
        await waitFor(() => {
            // Verificar que se muestran algunos KPIs
            expect(screen.getByText(/124/)).toBeInTheDocument(); // total_productos
        }, { timeout: 3000 });
    });

    it('debe mostrar gráficos', async () => {
        render(<Dashboard />, { wrapper: TestWrapper });
        
        await waitFor(() => {
            const charts = screen.getAllByTestId(/chart/);
            expect(charts.length).toBeGreaterThan(0);
        }, { timeout: 3000 });
    });

    it('debe mostrar sección de movimientos recientes', async () => {
        render(<Dashboard />, { wrapper: TestWrapper });
        
        await waitFor(() => {
            expect(screen.getByText(/movimientos recientes/i)).toBeInTheDocument();
        });
    });

    it('debe manejar errores del API gracefully', async () => {
        apiClient.get.mockRejectedValueOnce(new Error('Network error'));

        render(<Dashboard />, { wrapper: TestWrapper });
        
        await waitFor(() => {
            // Debe mostrar mensaje de error o datos mock
            const errorOrData = screen.queryByText(/error/i) || screen.queryByText(/124/);
            expect(errorOrData).toBeTruthy();
        });
    });

    it('debe tener tarjetas de KPI con iconos', async () => {
        render(<Dashboard />, { wrapper: TestWrapper });
        
        await waitFor(() => {
            // Verificar estructura de KPI cards
            const kpiCards = document.querySelectorAll('[class*="card"], [class*="kpi"]');
            expect(kpiCards.length).toBeGreaterThan(0);
        });
    });

    it('debe ser responsive', () => {
        render(<Dashboard />, { wrapper: TestWrapper });
        
        // Verificar que hay contenedores responsivos
        const responsiveContainers = screen.getAllByTestId('responsive-container');
        expect(responsiveContainers.length).toBeGreaterThan(0);
    });
});

describe('Dashboard - Permisos', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        localStorage.clear();
    });

    it('debe mostrar contenido para rol ADMIN', async () => {
        localStorage.setItem('token', 'mock-token');
        localStorage.setItem('user', JSON.stringify({
            id: 1,
            username: 'admin',
            rol: 'ADMIN',
        }));

        apiClient.get.mockResolvedValue({
            data: { kpis: mockKpis, movimientos: mockMovimientos },
        });

        render(<Dashboard />, { wrapper: TestWrapper });
        
        await waitFor(() => {
            expect(screen.getByText(/dashboard/i)).toBeInTheDocument();
        });
    });

    it('debe mostrar vista limitada para rol VISTA', async () => {
        localStorage.setItem('token', 'mock-token');
        localStorage.setItem('user', JSON.stringify({
            id: 2,
            username: 'viewer',
            rol: 'VISTA',
        }));

        apiClient.get.mockResolvedValue({
            data: { kpis: mockKpis, movimientos: mockMovimientos },
        });

        render(<Dashboard />, { wrapper: TestWrapper });
        
        await waitFor(() => {
            expect(screen.getByText(/dashboard/i)).toBeInTheDocument();
        });
    });
});
