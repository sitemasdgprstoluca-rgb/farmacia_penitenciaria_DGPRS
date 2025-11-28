/**
 * Tests para el componente Login
 * 
 * @module tests/Login.test
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { PermissionProvider } from '@/context/PermissionContext';
import Login from './Login';

// Mock de react-hot-toast
vi.mock('react-hot-toast', () => ({
    toast: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

// Mock de react-router-dom navigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
    const actual = await vi.importActual('react-router-dom');
    return {
        ...actual,
        useNavigate: () => mockNavigate,
    };
});

// Mock del API
vi.mock('@/services/api', () => ({
    authAPI: {
        login: vi.fn(),
        me: vi.fn(),
    },
}));

import { authAPI } from '@/services/api';
import { toast } from 'react-hot-toast';

// Wrapper con providers necesarios
const TestWrapper = ({ children }) => (
    <BrowserRouter>
        <PermissionProvider>
            {children}
        </PermissionProvider>
    </BrowserRouter>
);

describe('Login', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        localStorage.clear();
    });

    it('debe renderizar el formulario de login', () => {
        render(<Login />, { wrapper: TestWrapper });
        
        expect(screen.getByPlaceholderText(/usuario/i)).toBeInTheDocument();
        expect(screen.getByPlaceholderText(/contraseña/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /iniciar sesión/i })).toBeInTheDocument();
    });

    it('debe mostrar campos de usuario y contraseña vacíos inicialmente', () => {
        render(<Login />, { wrapper: TestWrapper });
        
        const usernameInput = screen.getByPlaceholderText(/usuario/i);
        const passwordInput = screen.getByPlaceholderText(/contraseña/i);
        
        expect(usernameInput.value).toBe('');
        expect(passwordInput.value).toBe('');
    });

    it('debe actualizar el estado al escribir en los campos', async () => {
        const user = userEvent.setup();
        render(<Login />, { wrapper: TestWrapper });
        
        const usernameInput = screen.getByPlaceholderText(/usuario/i);
        const passwordInput = screen.getByPlaceholderText(/contraseña/i);
        
        await user.type(usernameInput, 'admin');
        await user.type(passwordInput, 'password123');
        
        expect(usernameInput.value).toBe('admin');
        expect(passwordInput.value).toBe('password123');
    });

    it('debe llamar al API al enviar el formulario', async () => {
        const user = userEvent.setup();
        
        // Mock de respuesta exitosa
        authAPI.login.mockResolvedValueOnce({
            data: {
                access: 'mock-access-token',
                refresh: 'mock-refresh-token',
                user: {
                    id: 1,
                    username: 'admin',
                    rol: 'ADMIN',
                },
            },
        });
        
        render(<Login />, { wrapper: TestWrapper });
        
        const usernameInput = screen.getByPlaceholderText(/usuario/i);
        const passwordInput = screen.getByPlaceholderText(/contraseña/i);
        const submitButton = screen.getByRole('button', { name: /iniciar sesión/i });
        
        await user.type(usernameInput, 'admin');
        await user.type(passwordInput, 'password123');
        await user.click(submitButton);
        
        await waitFor(() => {
            expect(authAPI.login).toHaveBeenCalledWith({
                username: 'admin',
                password: 'password123',
            });
        });
    });

    it('debe navegar al dashboard tras login exitoso', async () => {
        const user = userEvent.setup();
        
        authAPI.login.mockResolvedValueOnce({
            data: {
                access: 'mock-access-token',
                refresh: 'mock-refresh-token',
                user: {
                    id: 1,
                    username: 'admin',
                    rol: 'ADMIN',
                },
            },
        });
        
        render(<Login />, { wrapper: TestWrapper });
        
        await user.type(screen.getByPlaceholderText(/usuario/i), 'admin');
        await user.type(screen.getByPlaceholderText(/contraseña/i), 'password123');
        await user.click(screen.getByRole('button', { name: /iniciar sesión/i }));
        
        await waitFor(() => {
            expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
        });
    });

    it('debe mostrar mensaje de error con credenciales incorrectas', async () => {
        const user = userEvent.setup();
        
        authAPI.login.mockRejectedValueOnce({
            response: {
                status: 401,
                data: { detail: 'Credenciales inválidas' },
            },
        });
        
        render(<Login />, { wrapper: TestWrapper });
        
        await user.type(screen.getByPlaceholderText(/usuario/i), 'admin');
        await user.type(screen.getByPlaceholderText(/contraseña/i), 'wrongpassword');
        await user.click(screen.getByRole('button', { name: /iniciar sesión/i }));
        
        await waitFor(() => {
            expect(screen.getByText(/usuario o contraseña incorrectos/i)).toBeInTheDocument();
        });
    });

    it('debe almacenar tokens en localStorage tras login exitoso', async () => {
        const user = userEvent.setup();
        
        authAPI.login.mockResolvedValueOnce({
            data: {
                access: 'test-access-token',
                refresh: 'test-refresh-token',
                user: {
                    id: 1,
                    username: 'admin',
                    rol: 'ADMIN',
                },
            },
        });
        
        render(<Login />, { wrapper: TestWrapper });
        
        await user.type(screen.getByPlaceholderText(/usuario/i), 'admin');
        await user.type(screen.getByPlaceholderText(/contraseña/i), 'password123');
        await user.click(screen.getByRole('button', { name: /iniciar sesión/i }));
        
        await waitFor(() => {
            expect(localStorage.getItem('token')).toBe('test-access-token');
            expect(localStorage.getItem('refresh_token')).toBe('test-refresh-token');
        });
    });

    it('debe deshabilitar el botón durante la carga', async () => {
        const user = userEvent.setup();
        
        // Mock con delay para simular carga
        authAPI.login.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));
        
        render(<Login />, { wrapper: TestWrapper });
        
        await user.type(screen.getByPlaceholderText(/usuario/i), 'admin');
        await user.type(screen.getByPlaceholderText(/contraseña/i), 'password123');
        
        const submitButton = screen.getByRole('button', { name: /iniciar sesión/i });
        await user.click(submitButton);
        
        // Durante la carga, el botón debería estar deshabilitado
        expect(submitButton).toBeDisabled();
    });

    it('debe tener link a recuperar contraseña', () => {
        render(<Login />, { wrapper: TestWrapper });
        
        expect(screen.getByText(/olvidaste tu contraseña/i)).toBeInTheDocument();
    });
});
