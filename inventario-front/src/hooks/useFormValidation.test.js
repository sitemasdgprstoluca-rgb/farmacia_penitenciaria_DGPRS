/**
 * Tests para el hook useFormValidation
 * 
 * @module tests/useFormValidation.test
 */

import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useFormValidation, useFieldValidation } from '@/hooks/useFormValidation';
import { validators } from '@/utils/validation';

describe('useFormValidation', () => {
    const initialValues = {
        nombre: '',
        email: '',
        password: ''
    };

    const validationRules = {
        nombre: [validators.required, validators.minLength(3)],
        email: [validators.required, validators.email],
        password: [validators.required, validators.minLength(8)]
    };

    it('debe inicializar con los valores proporcionados', () => {
        const { result } = renderHook(() => 
            useFormValidation(initialValues, validationRules)
        );

        expect(result.current.values).toEqual(initialValues);
        expect(result.current.errors).toEqual({});
        expect(result.current.touched).toEqual({});
        expect(result.current.isSubmitting).toBe(false);
    });

    it('debe actualizar valores al cambiar', () => {
        const { result } = renderHook(() => 
            useFormValidation(initialValues, validationRules)
        );

        act(() => {
            result.current.handleChange({
                target: { name: 'nombre', value: 'Test', type: 'text' }
            });
        });

        expect(result.current.values.nombre).toBe('Test');
    });

    it('debe validar al perder foco (onBlur)', () => {
        const { result } = renderHook(() => 
            useFormValidation(initialValues, validationRules, { validateOnBlur: true })
        );

        act(() => {
            result.current.handleBlur({
                target: { name: 'nombre', value: '' }
            });
        });

        expect(result.current.touched.nombre).toBe(true);
        expect(result.current.errors.nombre).toBeTruthy();
    });

    it('debe validar todo el formulario al enviar', async () => {
        const { result } = renderHook(() => 
            useFormValidation(initialValues, validationRules)
        );

        let submitResult;
        await act(async () => {
            submitResult = await result.current.handleSubmit();
        });

        expect(submitResult.success).toBe(false);
        expect(Object.keys(result.current.errors).length).toBeGreaterThan(0);
    });

    it('debe llamar onSubmit con valores válidos', async () => {
        const onSubmit = vi.fn().mockResolvedValue({ success: true });
        
        const { result } = renderHook(() => 
            useFormValidation(
                { nombre: 'Test', email: 'test@example.com', password: 'Password123' },
                validationRules,
                { onSubmit }
            )
        );

        await act(async () => {
            await result.current.handleSubmit();
        });

        expect(onSubmit).toHaveBeenCalledWith({
            nombre: 'Test',
            email: 'test@example.com',
            password: 'Password123'
        });
    });

    it('debe resetear el formulario correctamente', () => {
        const { result } = renderHook(() => 
            useFormValidation(initialValues, validationRules)
        );

        act(() => {
            result.current.setFieldValue('nombre', 'Cambiado');
            result.current.setFieldError('nombre', 'Error');
        });

        expect(result.current.values.nombre).toBe('Cambiado');

        act(() => {
            result.current.resetForm();
        });

        expect(result.current.values).toEqual(initialValues);
        expect(result.current.errors).toEqual({});
    });

    it('debe detectar si el formulario fue modificado (isDirty)', () => {
        const { result } = renderHook(() => 
            useFormValidation(initialValues, validationRules)
        );

        expect(result.current.isDirty).toBe(false);

        act(() => {
            result.current.handleChange({
                target: { name: 'nombre', value: 'Nuevo', type: 'text' }
            });
        });

        expect(result.current.isDirty).toBe(true);
    });

    it('debe proporcionar getFieldProps correctamente', () => {
        const { result } = renderHook(() => 
            useFormValidation(initialValues, validationRules)
        );

        const props = result.current.getFieldProps('nombre');
        
        expect(props).toHaveProperty('name', 'nombre');
        expect(props).toHaveProperty('value', '');
        expect(props).toHaveProperty('onChange');
        expect(props).toHaveProperty('onBlur');
    });

    it('debe proporcionar getFieldState correctamente', () => {
        const { result } = renderHook(() => 
            useFormValidation(initialValues, validationRules)
        );

        act(() => {
            result.current.handleBlur({
                target: { name: 'nombre', value: '' }
            });
        });

        const state = result.current.getFieldState('nombre');
        
        expect(state.touched).toBe(true);
        expect(state.error).toBeTruthy();
        expect(state.hasError).toBe(true);
    });

    it('debe manejar checkbox correctamente', () => {
        const { result } = renderHook(() => 
            useFormValidation({ acepta: false }, {})
        );

        act(() => {
            result.current.handleChange({
                target: { name: 'acepta', checked: true, type: 'checkbox' }
            });
        });

        expect(result.current.values.acepta).toBe(true);
    });

    it('debe establecer múltiples valores a la vez', () => {
        const { result } = renderHook(() => 
            useFormValidation(initialValues, validationRules)
        );

        act(() => {
            result.current.setMultipleValues({
                nombre: 'Test',
                email: 'test@test.com'
            });
        });

        expect(result.current.values.nombre).toBe('Test');
        expect(result.current.values.email).toBe('test@test.com');
    });
});

describe('useFieldValidation', () => {
    it('debe inicializar con el valor proporcionado', () => {
        const { result } = renderHook(() => 
            useFieldValidation('inicial', [validators.required])
        );

        expect(result.current.value).toBe('inicial');
        expect(result.current.error).toBeNull();
        expect(result.current.touched).toBe(false);
    });

    it('debe validar al perder foco', () => {
        const { result } = renderHook(() => 
            useFieldValidation('', [validators.required])
        );

        act(() => {
            result.current.handleBlur();
        });

        expect(result.current.touched).toBe(true);
        expect(result.current.error).toBeTruthy();
        expect(result.current.hasError).toBe(true);
    });

    it('debe actualizar valor y validar si fue tocado', () => {
        const { result } = renderHook(() => 
            useFieldValidation('', [validators.required])
        );

        // Primero tocamos el campo
        act(() => {
            result.current.handleBlur();
        });

        // Luego cambiamos el valor
        act(() => {
            result.current.handleChange({ target: { value: 'nuevo valor' } });
        });

        expect(result.current.value).toBe('nuevo valor');
        expect(result.current.error).toBeNull();
    });

    it('debe resetear correctamente', () => {
        const { result } = renderHook(() => 
            useFieldValidation('inicial', [validators.required])
        );

        act(() => {
            result.current.handleChange({ target: { value: 'cambiado' } });
            result.current.handleBlur();
        });

        act(() => {
            result.current.reset();
        });

        expect(result.current.value).toBe('inicial');
        expect(result.current.error).toBeNull();
        expect(result.current.touched).toBe(false);
    });
});
