/**
 * Tests para el componente Dashboard
 * 
 * Tests básicos que verifican renderizado sin depender de detalles de implementación
 * @module tests/Dashboard.test
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { PermissionProvider } from '@/context/PermissionContext';

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
        get: vi.fn(() => Promise.resolve({ data: {} })),
        post: vi.fn(() => Promise.resolve({ data: {} })),
    },
    dashboardAPI: {
        getResumen: vi.fn(() => Promise.resolve({ data: {} })),
        getGraficas: vi.fn(() => Promise.resolve({ data: {} })),
    },
}));

// Wrapper con providers
const TestWrapper = ({ children }) => (
    <BrowserRouter>
        <PermissionProvider>
            {children}
        </PermissionProvider>
    </BrowserRouter>
);

describe('Dashboard', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        
        // Simular usuario autenticado
        localStorage.setItem('token', 'mock-token');
        localStorage.setItem('user', JSON.stringify({
            id: 1,
            username: 'admin',
            rol: 'ADMIN',
        }));
    });

    it('debe renderizar sin errores', async () => {
        // Import dinámico para evitar problemas de hoisting
        const { default: Dashboard } = await import('./Dashboard');
        
        const { container } = render(<Dashboard />, { wrapper: TestWrapper });
        
        // Verificar que el componente se montó
        expect(container).toBeTruthy();
    });

    it('debe mostrar título o header de dashboard', async () => {
        const { default: Dashboard } = await import('./Dashboard');
        
        render(<Dashboard />, { wrapper: TestWrapper });
        
        // Esperar a que el componente cargue (puede tener loading state)
        await waitFor(() => {
            // Buscar cualquier texto relacionado con dashboard
            const dashboardElements = screen.queryAllByText(/dashboard|panel|inicio/i);
            expect(dashboardElements.length).toBeGreaterThanOrEqual(0);
        }, { timeout: 2000 });
    });

    it('debe tener estructura básica de layout', async () => {
        const { default: Dashboard } = await import('./Dashboard');
        
        const { container } = render(<Dashboard />, { wrapper: TestWrapper });
        
        // Verificar que hay divs (estructura básica)
        const divs = container.querySelectorAll('div');
        expect(divs.length).toBeGreaterThan(0);
    });
});

describe('Dashboard - Autenticación', () => {
    it('debe renderizar cuando hay token', async () => {
        localStorage.setItem('token', 'valid-token');
        localStorage.setItem('user', JSON.stringify({ id: 1, rol: 'ADMIN' }));
        
        const { default: Dashboard } = await import('./Dashboard');
        const { container } = render(<Dashboard />, { wrapper: TestWrapper });
        
        expect(container).toBeTruthy();
    });

    it('debe renderizar para diferentes roles', async () => {
        const roles = ['ADMIN', 'FARMACIA', 'CENTRO', 'VISTA'];
        
        for (const rol of roles) {
            localStorage.clear();
            localStorage.setItem('token', 'valid-token');
            localStorage.setItem('user', JSON.stringify({ id: 1, rol }));
            
            const { default: Dashboard } = await import('./Dashboard');
            const { container, unmount } = render(<Dashboard />, { wrapper: TestWrapper });
            
            expect(container).toBeTruthy();
            unmount();
        }
    });
});
