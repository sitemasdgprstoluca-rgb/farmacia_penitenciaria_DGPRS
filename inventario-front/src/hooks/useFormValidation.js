/**
 * Hook personalizado para validación de formularios
 * 
 * @module hooks/useFormValidation
 * @description Proporciona una forma declarativa de validar formularios
 * con soporte para validación en tiempo real y al enviar.
 * 
 * @example
 * const { values, errors, handleChange, handleBlur, handleSubmit, isValid } = useFormValidation(
 *   { nombre: '', email: '' },
 *   {
 *     nombre: [validators.required, validators.minLength(3)],
 *     email: [validators.required, validators.email]
 *   }
 * );
 */

import { useState, useCallback, useMemo } from 'react';

/**
 * Custom hook para manejo de validación de formularios
 * 
 * @param {Object} initialValues - Valores iniciales del formulario
 * @param {Object} validationRules - Reglas de validación por campo
 * @param {Object} options - Opciones de configuración
 * @param {boolean} options.validateOnChange - Validar al cambiar (default: false)
 * @param {boolean} options.validateOnBlur - Validar al perder foco (default: true)
 * @param {Function} options.onSubmit - Callback al enviar formulario válido
 * @returns {Object} Estado y funciones del formulario
 */
export const useFormValidation = (
    initialValues = {},
    validationRules = {},
    options = {}
) => {
    const {
        validateOnChange = false,
        validateOnBlur = true,
        onSubmit = null
    } = options;

    // Estado del formulario
    const [values, setValues] = useState(initialValues);
    const [errors, setErrors] = useState({});
    const [touched, setTouched] = useState({});
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [submitCount, setSubmitCount] = useState(0);

    /**
     * Valida un campo individual
     */
    const validateField = useCallback((name, value) => {
        const rules = validationRules[name];
        if (!rules || !Array.isArray(rules)) {
            return null;
        }

        for (const rule of rules) {
            const error = rule(value, values);
            if (error) {
                return error;
            }
        }
        return null;
    }, [validationRules, values]);

    /**
     * Valida todos los campos del formulario
     */
    const validateForm = useCallback(() => {
        const newErrors = {};
        let isValid = true;

        Object.keys(validationRules).forEach(fieldName => {
            const error = validateField(fieldName, values[fieldName]);
            if (error) {
                newErrors[fieldName] = error;
                isValid = false;
            }
        });

        setErrors(newErrors);
        return isValid;
    }, [validationRules, values, validateField]);

    /**
     * Maneja el cambio de valor de un campo
     */
    const handleChange = useCallback((e) => {
        const { name, value, type, checked } = e.target;
        const newValue = type === 'checkbox' ? checked : value;

        setValues(prev => ({
            ...prev,
            [name]: newValue
        }));

        if (validateOnChange || touched[name]) {
            const error = validateField(name, newValue);
            setErrors(prev => ({
                ...prev,
                [name]: error
            }));
        }
    }, [validateOnChange, touched, validateField]);

    /**
     * Maneja el evento blur (pérdida de foco)
     */
    const handleBlur = useCallback((e) => {
        const { name, value } = e.target;

        setTouched(prev => ({
            ...prev,
            [name]: true
        }));

        if (validateOnBlur) {
            const error = validateField(name, value);
            setErrors(prev => ({
                ...prev,
                [name]: error
            }));
        }
    }, [validateOnBlur, validateField]);

    /**
     * Establece el valor de un campo programáticamente
     */
    const setFieldValue = useCallback((name, value) => {
        setValues(prev => ({
            ...prev,
            [name]: value
        }));

        if (validateOnChange || touched[name]) {
            const error = validateField(name, value);
            setErrors(prev => ({
                ...prev,
                [name]: error
            }));
        }
    }, [validateOnChange, touched, validateField]);

    /**
     * Establece el error de un campo programáticamente
     */
    const setFieldError = useCallback((name, error) => {
        setErrors(prev => ({
            ...prev,
            [name]: error
        }));
    }, []);

    /**
     * Establece múltiples valores a la vez
     */
    const setMultipleValues = useCallback((newValues) => {
        setValues(prev => ({
            ...prev,
            ...newValues
        }));
    }, []);

    /**
     * Maneja el envío del formulario
     */
    const handleSubmit = useCallback(async (e) => {
        if (e) {
            e.preventDefault();
        }

        setSubmitCount(prev => prev + 1);
        
        // Marcar todos los campos como touched
        const allTouched = {};
        Object.keys(validationRules).forEach(key => {
            allTouched[key] = true;
        });
        setTouched(allTouched);

        // Validar todo el formulario
        const isValid = validateForm();

        if (!isValid) {
            return { success: false, errors };
        }

        if (onSubmit) {
            setIsSubmitting(true);
            try {
                const result = await onSubmit(values);
                setIsSubmitting(false);
                return { success: true, data: result };
            } catch (error) {
                setIsSubmitting(false);
                return { success: false, error };
            }
        }

        return { success: true, values };
    }, [validationRules, validateForm, onSubmit, values, errors]);

    /**
     * Reinicia el formulario a sus valores iniciales
     */
    const resetForm = useCallback(() => {
        setValues(initialValues);
        setErrors({});
        setTouched({});
        setIsSubmitting(false);
        setSubmitCount(0);
    }, [initialValues]);

    /**
     * Reinicia un campo específico
     */
    const resetField = useCallback((name) => {
        setValues(prev => ({
            ...prev,
            [name]: initialValues[name] ?? ''
        }));
        setErrors(prev => {
            const newErrors = { ...prev };
            delete newErrors[name];
            return newErrors;
        });
        setTouched(prev => ({
            ...prev,
            [name]: false
        }));
    }, [initialValues]);

    /**
     * Verifica si el formulario es válido (memoizado)
     */
    const isValid = useMemo(() => {
        return Object.keys(validationRules).every(fieldName => {
            const error = validateField(fieldName, values[fieldName]);
            return !error;
        });
    }, [validationRules, values, validateField]);

    /**
     * Verifica si el formulario ha sido modificado
     */
    const isDirty = useMemo(() => {
        return Object.keys(values).some(key => values[key] !== initialValues[key]);
    }, [values, initialValues]);

    /**
     * Helper para obtener props de un input
     */
    const getFieldProps = useCallback((name) => ({
        name,
        value: values[name] ?? '',
        onChange: handleChange,
        onBlur: handleBlur
    }), [values, handleChange, handleBlur]);

    /**
     * Helper para obtener el estado de error de un campo
     */
    const getFieldState = useCallback((name) => ({
        error: errors[name],
        touched: touched[name],
        hasError: touched[name] && !!errors[name]
    }), [errors, touched]);

    return {
        // Estado
        values,
        errors,
        touched,
        isSubmitting,
        isValid,
        isDirty,
        submitCount,

        // Handlers
        handleChange,
        handleBlur,
        handleSubmit,

        // Setters
        setFieldValue,
        setFieldError,
        setMultipleValues,
        setValues,
        setErrors,

        // Reset
        resetForm,
        resetField,

        // Helpers
        getFieldProps,
        getFieldState,
        validateField,
        validateForm
    };
};

/**
 * Hook simplificado para campos individuales
 * 
 * @param {*} initialValue - Valor inicial
 * @param {Array} validators - Array de funciones validadoras
 * @returns {Object} Estado y handlers del campo
 */
export const useFieldValidation = (initialValue = '', validators = []) => {
    const [value, setValue] = useState(initialValue);
    const [error, setError] = useState(null);
    const [touched, setTouched] = useState(false);

    const validate = useCallback((val) => {
        for (const validator of validators) {
            const validationError = validator(val);
            if (validationError) {
                setError(validationError);
                return false;
            }
        }
        setError(null);
        return true;
    }, [validators]);

    const handleChange = useCallback((e) => {
        const newValue = e.target.value;
        setValue(newValue);
        if (touched) {
            validate(newValue);
        }
    }, [touched, validate]);

    const handleBlur = useCallback(() => {
        setTouched(true);
        validate(value);
    }, [value, validate]);

    const reset = useCallback(() => {
        setValue(initialValue);
        setError(null);
        setTouched(false);
    }, [initialValue]);

    return {
        value,
        error,
        touched,
        hasError: touched && !!error,
        isValid: !error,
        handleChange,
        handleBlur,
        setValue,
        setError,
        validate,
        reset
    };
};

export default useFormValidation;
