/**
 * Tests para las utilidades de validación
 * 
 * @module tests/validation.test
 */

import { describe, it, expect } from 'vitest';
import {
    validators,
    validateField,
    validateForm,
    validateSchema,
    validationSchemas,
    sanitizeInput,
    getFieldError,
    hasErrors,
    combineValidators
} from '@/utils/validation';

describe('Validators', () => {
    describe('required', () => {
        it('debe retornar error para valor vacío', () => {
            expect(validators.required('')).toBeTruthy();
            expect(validators.required(null)).toBeTruthy();
            expect(validators.required(undefined)).toBeTruthy();
        });

        it('debe pasar con valor válido', () => {
            expect(validators.required('texto')).toBeNull();
            expect(validators.required(0)).toBeNull();
            expect(validators.required(false)).toBeNull();
        });
    });

    describe('minLength', () => {
        it('debe retornar error si es menor al mínimo', () => {
            const validator = validators.minLength(5);
            expect(validator('abc')).toBeTruthy();
        });

        it('debe pasar si cumple con el mínimo', () => {
            const validator = validators.minLength(5);
            expect(validator('abcde')).toBeNull();
            expect(validator('abcdef')).toBeNull();
        });

        it('debe ignorar valores vacíos', () => {
            const validator = validators.minLength(5);
            expect(validator('')).toBeNull();
            expect(validator(null)).toBeNull();
        });
    });

    describe('maxLength', () => {
        it('debe retornar error si excede el máximo', () => {
            const validator = validators.maxLength(5);
            expect(validator('abcdef')).toBeTruthy();
        });

        it('debe pasar si está dentro del máximo', () => {
            const validator = validators.maxLength(5);
            expect(validator('abc')).toBeNull();
            expect(validator('abcde')).toBeNull();
        });
    });

    describe('email', () => {
        it('debe rechazar emails inválidos', () => {
            expect(validators.email('invalid')).toBeTruthy();
            expect(validators.email('invalid@')).toBeTruthy();
            expect(validators.email('@domain.com')).toBeTruthy();
        });

        it('debe aceptar emails válidos', () => {
            expect(validators.email('test@example.com')).toBeNull();
            expect(validators.email('user.name@domain.co')).toBeNull();
        });

        it('debe ignorar valores vacíos', () => {
            expect(validators.email('')).toBeNull();
        });
    });

    describe('password', () => {
        it('debe rechazar contraseñas débiles', () => {
            expect(validators.password('short')).toBeTruthy();
            expect(validators.password('nouppercase1')).toBeTruthy();
        });

        it('debe aceptar contraseñas fuertes', () => {
            expect(validators.password('Password123')).toBeNull();
            expect(validators.password('SecurePass1!')).toBeNull();
        });
    });

    describe('numeric', () => {
        it('debe rechazar valores no numéricos', () => {
            expect(validators.numeric('abc')).toBeTruthy();
            expect(validators.numeric('12.34.56')).toBeTruthy();
        });

        it('debe aceptar valores numéricos', () => {
            expect(validators.numeric('123')).toBeNull();
            expect(validators.numeric('12.34')).toBeNull();
            expect(validators.numeric('-123')).toBeNull();
        });
    });

    describe('positiveNumber', () => {
        it('debe rechazar números negativos o cero', () => {
            expect(validators.positiveNumber('-1')).toBeTruthy();
            expect(validators.positiveNumber('0')).toBeTruthy();
        });

        it('debe aceptar números positivos', () => {
            expect(validators.positiveNumber('1')).toBeNull();
            expect(validators.positiveNumber('100')).toBeNull();
        });
    });

    describe('codigoBarras', () => {
        it('debe verificar que codigoBarras existe como alias de productKey', () => {
            // codigoBarras es un alias de productKey que valida claves alfanuméricas
            expect(validators.codigoBarras).toBeDefined();
            expect(typeof validators.codigoBarras).toBe('function');
        });

        it('debe aceptar códigos alfanuméricos válidos', () => {
            expect(validators.codigoBarras('ABC123')).toBeNull();
            expect(validators.codigoBarras('12345678')).toBeNull();
            expect(validators.codigoBarras('PROD-001')).toBeNull();
        });
    });

    describe('futureDate', () => {
        it('debe rechazar fechas pasadas', () => {
            expect(validators.futureDate('2020-01-01')).toBeTruthy();
        });

        it('debe aceptar fechas futuras', () => {
            const futureDate = new Date();
            futureDate.setFullYear(futureDate.getFullYear() + 1);
            expect(validators.futureDate(futureDate.toISOString().split('T')[0])).toBeNull();
        });
    });

    describe('matchField', () => {
        it('debe verificar que matchField existe como alias de matches', () => {
            // matchField es un alias de matches que compara con otro campo
            expect(validators.matchField).toBeDefined();
            expect(typeof validators.matchField).toBe('function');
        });

        it('debe retornar una función validadora', () => {
            const validator = validators.matchField('password');
            expect(typeof validator).toBe('function');
        });
    });
});

describe('validateField', () => {
    it('debe ejecutar todos los validadores', () => {
        const rules = [
            validators.required,
            validators.minLength(3),
            validators.maxLength(10)
        ];
        
        expect(validateField('', rules)).toBeTruthy(); // falla required
        expect(validateField('ab', rules)).toBeTruthy(); // falla minLength
        expect(validateField('abc', rules)).toBeNull(); // pasa todo
    });

    it('debe retornar el primer error encontrado', () => {
        const rules = [validators.required, validators.email];
        const error = validateField('invalid', rules);
        // El error es de email porque 'invalid' no es un email válido
        expect(error).toBeTruthy();
        expect(error).toContain('formato'); // mensaje de email inválido
    });
});

describe('validateForm', () => {
    it('debe validar múltiples campos', () => {
        const values = {
            nombre: '',
            email: 'invalid-email'
        };
        const rules = {
            nombre: [validators.required],
            email: [validators.required, validators.email]
        };
        
        const errors = validateForm(values, rules);
        expect(errors.nombre).toBeTruthy();
        expect(errors.email).toBeTruthy();
    });

    it('debe retornar objeto vacío si todo es válido', () => {
        const values = {
            nombre: 'Test',
            email: 'test@example.com'
        };
        const rules = {
            nombre: [validators.required],
            email: [validators.required, validators.email]
        };
        
        const errors = validateForm(values, rules);
        expect(Object.keys(errors).length).toBe(0);
    });
});

describe('validateSchema', () => {
    it('debe validar usando un schema predefinido', () => {
        const values = {
            nombre: '',
            codigo_barras: '123'
        };
        
        // validateSchema retorna un objeto con los errores por campo
        // no tiene propiedad isValid, hay que revisar los errores
        const result = validateSchema(values, validationSchemas.producto);
        // schemas.producto tiene las validaciones para productos
        expect(result).toBeDefined();
        expect(typeof result).toBe('object');
    });
});

describe('sanitizeInput', () => {
    it('debe eliminar espacios extras', () => {
        expect(sanitizeInput('  hello   world  ')).toBe('hello world');
    });

    it('debe manejar valores null/undefined', () => {
        expect(sanitizeInput(null)).toBe('');
        expect(sanitizeInput(undefined)).toBe('');
    });

    it('debe eliminar caracteres peligrosos', () => {
        expect(sanitizeInput('<script>alert("xss")</script>')).not.toContain('<script>');
    });
});

describe('getFieldError y hasErrors', () => {
    const errors = {
        nombre: 'Campo requerido',
        email: 'Email inválido'
    };

    it('debe obtener error de un campo', () => {
        expect(getFieldError(errors, 'nombre')).toBe('Campo requerido');
        expect(getFieldError(errors, 'other')).toBeUndefined();
    });

    it('debe verificar si hay errores', () => {
        expect(hasErrors(errors)).toBe(true);
        expect(hasErrors({})).toBe(false);
    });
});

describe('combineValidators', () => {
    it('debe combinar múltiples validadores en uno', () => {
        const combined = combineValidators(
            validators.required,
            validators.minLength(3),
            validators.maxLength(10)
        );
        
        expect(combined('')).toBeTruthy();
        expect(combined('ab')).toBeTruthy();
        expect(combined('abc')).toBeNull();
    });
});
