/**
 * Utilidades de Testing - Farmacia Penitenciaria
 * 
 * Proporciona funciones helper y wrappers para facilitar
 * la escritura de tests con React Testing Library.
 */

import { render } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '@/context/AuthContext';
import { vi } from 'vitest';

/**
 * Renderiza un componente con todos los providers necesarios
 * 
 * @param {React.ReactElement} ui - Componente a renderizar
 * @param {Object} options - Opciones adicionales
 * @returns {Object} - Resultado de render con helpers adicionales
 */
export const renderWithProviders = (ui, options = {}) => {
    const {
        route = '/',
        authValue = null,
        ...renderOptions
    } = options;

    // Configurar ruta inicial
    window.history.pushState({}, 'Test page', route);

    const AllProviders = ({ children }) => (
        <BrowserRouter>
            <AuthProvider value={authValue}>
                {children}
            </AuthProvider>
        </BrowserRouter>
    );

    return {
        ...render(ui, { wrapper: AllProviders, ...renderOptions }),
    };
};

/**
 * Renderiza solo con Router (sin Auth)
 */
export const renderWithRouter = (ui, { route = '/' } = {}) => {
    window.history.pushState({}, 'Test page', route);
    
    return render(ui, { wrapper: BrowserRouter });
};

/**
 * Crea un mock de usuario autenticado
 */
export const createMockUser = (overrides = {}) => ({
    id: 1,
    username: 'testuser',
    email: 'test@example.com',
    first_name: 'Test',
    last_name: 'User',
    rol: 'ADMIN',
    is_active: true,
    ...overrides
});

/**
 * Crea un mock de producto
 */
export const createMockProduct = (overrides = {}) => ({
    id: 1,
    clave: 'MED-001',
    descripcion: 'Producto de Prueba',
    unidad_medida: 'CAJA',
    stock_minimo: 10,
    stock_actual: 100,
    activo: true,
    ...overrides
});

/**
 * Crea un mock de lote
 */
export const createMockLote = (overrides = {}) => ({
    id: 1,
    numero_lote: 'LOTE001',
    producto: 1,
    producto_nombre: 'Producto de Prueba',
    fecha_caducidad: '2025-12-31',
    cantidad_inicial: 100,
    cantidad_actual: 100,
    ubicacion: 'A-1-1',
    activo: true,
    ...overrides
});

/**
 * Crea un mock de movimiento
 */
export const createMockMovimiento = (overrides = {}) => ({
    id: 1,
    tipo: 'ENTRADA',
    producto: 1,
    producto_nombre: 'Producto de Prueba',
    lote: 1,
    lote_numero: 'LOTE001',
    cantidad: 50,
    motivo: 'Ingreso de inventario',
    usuario: 1,
    usuario_nombre: 'testuser',
    fecha: new Date().toISOString(),
    ...overrides
});

/**
 * Mock del módulo axios
 */
export const createAxiosMock = () => ({
    get: vi.fn().mockResolvedValue({ data: {} }),
    post: vi.fn().mockResolvedValue({ data: {} }),
    put: vi.fn().mockResolvedValue({ data: {} }),
    patch: vi.fn().mockResolvedValue({ data: {} }),
    delete: vi.fn().mockResolvedValue({ data: {} }),
    create: vi.fn().mockReturnThis(),
    interceptors: {
        request: { use: vi.fn(), eject: vi.fn() },
        response: { use: vi.fn(), eject: vi.fn() }
    },
    defaults: {
        headers: {
            common: {}
        }
    }
});

/**
 * Helper para esperar cambios asíncronos
 */
export const waitForLoadingToFinish = async () => {
    return new Promise(resolve => setTimeout(resolve, 0));
};

/**
 * Mock de API responses comunes
 */
export const mockApiResponses = {
    productos: {
        list: {
            count: 2,
            results: [
                createMockProduct({ id: 1, nombre: 'Producto 1' }),
                createMockProduct({ id: 2, nombre: 'Producto 2' })
            ]
        },
        detail: createMockProduct()
    },
    lotes: {
        list: {
            count: 2,
            results: [
                createMockLote({ id: 1, numero_lote: 'LOTE001' }),
                createMockLote({ id: 2, numero_lote: 'LOTE002' })
            ]
        },
        detail: createMockLote()
    },
    auth: {
        login: {
            access: 'mock-access-token',
            user: createMockUser()
        },
        user: createMockUser()
    }
};

/**
 * Helper para simular eventos de formulario
 */
export const fillForm = async (userEvent, fields) => {
    for (const [selector, value] of Object.entries(fields)) {
        const element = document.querySelector(selector);
        if (element) {
            await userEvent.clear(element);
            await userEvent.type(element, value);
        }
    }
};

/**
 * Helper para verificar que un elemento tiene cierta clase CSS
 */
export const hasClass = (element, className) => {
    return element.classList.contains(className);
};

/**
 * Helper para crear mock de toast
 */
export const createToastMock = () => ({
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
    dismiss: vi.fn()
});

export default {
    renderWithProviders,
    renderWithRouter,
    createMockUser,
    createMockProduct,
    createMockLote,
    createMockMovimiento,
    createAxiosMock,
    waitForLoadingToFinish,
    mockApiResponses,
    fillForm,
    hasClass,
    createToastMock
};
