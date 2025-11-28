/**
 * Configuración global de tests - Vitest + Testing Library
 * 
 * Este archivo se ejecuta antes de cada suite de tests y configura:
 * - @testing-library/jest-dom para aserciones extendidas
 * - Mocks globales para localStorage, sessionStorage
 * - Limpieza automática después de cada test
 */

import '@testing-library/jest-dom';
import { cleanup } from '@testing-library/react';
import { afterEach, beforeEach, vi } from 'vitest';

// Limpiar después de cada test
afterEach(() => {
    cleanup();
});

// Mock de localStorage con almacenamiento real
const createStorageMock = () => {
    let store = {};
    return {
        getItem: vi.fn((key) => store[key] || null),
        setItem: vi.fn((key, value) => { store[key] = String(value); }),
        removeItem: vi.fn((key) => { delete store[key]; }),
        clear: vi.fn(() => { store = {}; }),
        get length() { return Object.keys(store).length; },
        key: vi.fn((index) => Object.keys(store)[index] || null),
    };
};

const localStorageMock = createStorageMock();
const sessionStorageMock = createStorageMock();

Object.defineProperty(window, 'localStorage', { value: localStorageMock, writable: true });
Object.defineProperty(window, 'sessionStorage', { value: sessionStorageMock, writable: true });

// Limpiar storage antes de cada test
beforeEach(() => {
    localStorageMock.clear();
    sessionStorageMock.clear();
    vi.clearAllMocks();
});

// Mock de matchMedia (usado por algunos componentes de UI)
Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation(query => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
    })),
});

// Mock de scrollTo
window.scrollTo = vi.fn();

// Mock de ResizeObserver
class ResizeObserverMock {
    observe() {}
    unobserve() {}
    disconnect() {}
}
window.ResizeObserver = ResizeObserverMock;

// Mock de IntersectionObserver
class IntersectionObserverMock {
    constructor(callback) {
        this.callback = callback;
    }
    observe() {}
    unobserve() {}
    disconnect() {}
}
window.IntersectionObserver = IntersectionObserverMock;

// Suprimir errores de consola durante tests (opcional)
// Descomenta si quieres ver menos ruido en la salida de tests
// vi.spyOn(console, 'error').mockImplementation(() => {});
// vi.spyOn(console, 'warn').mockImplementation(() => {});

// Variables de entorno para tests
globalThis.process = globalThis.process || {};
globalThis.process.env = globalThis.process.env || {};
globalThis.process.env.VITE_API_URL = 'http://localhost:8000/api';
