/**
 * Tests unitarios para movimientos - Restricción de tipo para médicos
 * 
 * Los médicos de centro SOLO pueden hacer "Dispensación por receta"
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// ============ Tests de restricción de tipo de movimiento por rol ============

describe('Restricción de tipo de movimiento para médicos', () => {
  // Simular la lógica de roles del componente Movimientos
  const getRolPrincipal = (user) => {
    if (user?.is_superuser) return 'ADMIN';
    const rol = (user?.rol_efectivo || user?.rol || '').toUpperCase();
    if (rol === 'MEDICO') return 'CENTRO';  // Médicos van a la categoría CENTRO
    if (['FARMACIA', 'ADMIN_FARMACIA'].includes(rol)) return 'FARMACIA';
    if (rol === 'ADMIN_SISTEMA') return 'ADMIN';
    if (['CENTRO', 'USUARIO_CENTRO'].includes(rol)) return 'CENTRO';
    if (rol === 'VISTA') return 'VISTA';
    return 'CENTRO';
  };

  const esMedico = (user) => {
    return (user?.rol_efectivo || user?.rol || '').toLowerCase() === 'medico';
  };

  const puedeVerTodosCentros = (user) => {
    const rol = getRolPrincipal(user);
    return ['ADMIN', 'FARMACIA', 'VISTA'].includes(rol);
  };

  const getSubtiposDisponibles = (user) => {
    if (puedeVerTodosCentros(user)) {
      return ['transferencia'];  // Farmacia solo transfiere
    }
    if (esMedico(user)) {
      return ['receta'];  // Médico SOLO puede dispensar por receta
    }
    // Otros usuarios de centro tienen todas las opciones
    return ['consumo_interno', 'receta', 'merma', 'caducidad'];
  };

  const getSubtipoInicial = (user) => {
    if (puedeVerTodosCentros(user)) return 'transferencia';
    if (esMedico(user)) return 'receta';
    return 'consumo_interno';
  };

  describe('Usuarios médicos', () => {
    const medicoUser = {
      id: 1,
      rol: 'medico',
      rol_efectivo: 'medico',
      centro_id: 1,
      centro: { id: 1, nombre: 'Centro Penitenciario Santiaguito' },
    };

    it('debe identificar correctamente al usuario como médico', () => {
      expect(esMedico(medicoUser)).toBe(true);
    });

    it('médico NO puede ver todos los centros', () => {
      expect(puedeVerTodosCentros(medicoUser)).toBe(false);
    });

    it('médico solo tiene disponible "Dispensación por receta"', () => {
      const subtipos = getSubtiposDisponibles(medicoUser);
      
      expect(subtipos).toHaveLength(1);
      expect(subtipos).toContain('receta');
      expect(subtipos).not.toContain('consumo_interno');
      expect(subtipos).not.toContain('merma');
      expect(subtipos).not.toContain('caducidad');
    });

    it('subtipo inicial para médico es "receta"', () => {
      expect(getSubtipoInicial(medicoUser)).toBe('receta');
    });

    it('médico con rol_efectivo también es detectado', () => {
      const medicoEfectivo = {
        id: 2,
        rol: 'usuario_centro',
        rol_efectivo: 'medico',
        centro_id: 1,
      };
      
      expect(esMedico(medicoEfectivo)).toBe(true);
      expect(getSubtiposDisponibles(medicoEfectivo)).toEqual(['receta']);
    });
  });

  describe('Usuarios de farmacia', () => {
    const farmaciaUser = {
      id: 10,
      rol: 'farmacia',
      rol_efectivo: 'farmacia',
      is_superuser: false,
    };

    it('NO es médico', () => {
      expect(esMedico(farmaciaUser)).toBe(false);
    });

    it('puede ver todos los centros', () => {
      expect(puedeVerTodosCentros(farmaciaUser)).toBe(true);
    });

    it('solo tiene disponible "transferencia"', () => {
      const subtipos = getSubtiposDisponibles(farmaciaUser);
      
      expect(subtipos).toHaveLength(1);
      expect(subtipos).toContain('transferencia');
    });

    it('subtipo inicial es "transferencia"', () => {
      expect(getSubtipoInicial(farmaciaUser)).toBe('transferencia');
    });
  });

  describe('Usuarios de centro (no médico)', () => {
    const centroUser = {
      id: 20,
      rol: 'usuario_centro',
      rol_efectivo: 'usuario_centro',
      centro_id: 1,
      centro: { id: 1, nombre: 'Centro Test' },
    };

    it('NO es médico', () => {
      expect(esMedico(centroUser)).toBe(false);
    });

    it('NO puede ver todos los centros', () => {
      expect(puedeVerTodosCentros(centroUser)).toBe(false);
    });

    it('tiene todas las opciones de salida disponibles', () => {
      const subtipos = getSubtiposDisponibles(centroUser);
      
      expect(subtipos).toHaveLength(4);
      expect(subtipos).toContain('consumo_interno');
      expect(subtipos).toContain('receta');
      expect(subtipos).toContain('merma');
      expect(subtipos).toContain('caducidad');
    });

    it('subtipo inicial es "consumo_interno"', () => {
      expect(getSubtipoInicial(centroUser)).toBe('consumo_interno');
    });
  });

  describe('Administradores', () => {
    const adminUser = {
      id: 99,
      rol: 'admin_sistema',
      is_superuser: true,
    };

    it('NO es médico', () => {
      expect(esMedico(adminUser)).toBe(false);
    });

    it('puede ver todos los centros', () => {
      expect(puedeVerTodosCentros(adminUser)).toBe(true);
    });

    it('subtipo inicial es "transferencia"', () => {
      expect(getSubtipoInicial(adminUser)).toBe('transferencia');
    });
  });
});

// ============ Tests de validación de formulario de movimientos ============

describe('Validación de formulario de movimientos para médicos', () => {
  const validarFormularioMedico = (formData) => {
    const errores = [];

    // Lote es requerido
    if (!formData.lote) {
      errores.push('Debe seleccionar un lote');
    }

    // Cantidad es requerida y debe ser positiva
    if (!formData.cantidad || formData.cantidad <= 0) {
      errores.push('La cantidad debe ser mayor a 0');
    }

    // Para médicos, subtipo DEBE ser "receta"
    if (formData.subtipo_salida !== 'receta') {
      errores.push('Los médicos solo pueden registrar dispensaciones por receta');
    }

    // Si es receta, número de expediente es obligatorio
    if (formData.subtipo_salida === 'receta') {
      if (!formData.numero_expediente || !formData.numero_expediente.trim()) {
        errores.push('El número de expediente es obligatorio para dispensación por receta');
      }
    }

    return {
      valido: errores.length === 0,
      errores,
    };
  };

  it('formulario válido con todos los campos', () => {
    const formData = {
      lote: 201,
      cantidad: 10,
      subtipo_salida: 'receta',
      numero_expediente: 'EXP-2026-001',
      observaciones: 'Dispensación de medicamento',
    };

    const resultado = validarFormularioMedico(formData);
    
    expect(resultado.valido).toBe(true);
    expect(resultado.errores).toHaveLength(0);
  });

  it('falla si falta el lote', () => {
    const formData = {
      lote: '',
      cantidad: 10,
      subtipo_salida: 'receta',
      numero_expediente: 'EXP-001',
    };

    const resultado = validarFormularioMedico(formData);
    
    expect(resultado.valido).toBe(false);
    expect(resultado.errores).toContain('Debe seleccionar un lote');
  });

  it('falla si cantidad es 0 o negativa', () => {
    const formDataCero = {
      lote: 201,
      cantidad: 0,
      subtipo_salida: 'receta',
      numero_expediente: 'EXP-001',
    };

    const formDataNegativa = {
      lote: 201,
      cantidad: -5,
      subtipo_salida: 'receta',
      numero_expediente: 'EXP-001',
    };

    expect(validarFormularioMedico(formDataCero).valido).toBe(false);
    expect(validarFormularioMedico(formDataNegativa).valido).toBe(false);
  });

  it('falla si subtipo no es "receta" para médico', () => {
    const formData = {
      lote: 201,
      cantidad: 10,
      subtipo_salida: 'consumo_interno',  // ¡No permitido para médicos!
      numero_expediente: '',
    };

    const resultado = validarFormularioMedico(formData);
    
    expect(resultado.valido).toBe(false);
    expect(resultado.errores).toContain('Los médicos solo pueden registrar dispensaciones por receta');
  });

  it('falla si falta número de expediente en receta', () => {
    const formData = {
      lote: 201,
      cantidad: 10,
      subtipo_salida: 'receta',
      numero_expediente: '',  // Falta el expediente
    };

    const resultado = validarFormularioMedico(formData);
    
    expect(resultado.valido).toBe(false);
    expect(resultado.errores).toContain('El número de expediente es obligatorio para dispensación por receta');
  });

  it('falla si expediente solo tiene espacios', () => {
    const formData = {
      lote: 201,
      cantidad: 10,
      subtipo_salida: 'receta',
      numero_expediente: '   ',  // Solo espacios
    };

    const resultado = validarFormularioMedico(formData);
    
    expect(resultado.valido).toBe(false);
    expect(resultado.errores).toContain('El número de expediente es obligatorio para dispensación por receta');
  });
});

// ============ Tests de UI - Elementos visibles según rol ============

describe('Elementos de UI según rol en Movimientos', () => {
  const getElementosVisibles = (user) => {
    const esMedicoUser = (user?.rol_efectivo || user?.rol || '').toLowerCase() === 'medico';
    const puedeVerTodos = ['ADMIN', 'FARMACIA', 'VISTA'].includes(
      user?.is_superuser ? 'ADMIN' : (user?.rol || '').toUpperCase()
    );

    return {
      // Selector de subtipo (dropdown)
      selectorSubtipo: !puedeVerTodos && !esMedicoUser,
      
      // Texto fijo de "Dispensación por receta" para médicos
      textoRecetaFijo: esMedicoUser,
      
      // Texto fijo de "Transferencia" para farmacia
      textoTransferenciaFijo: puedeVerTodos,
      
      // Campo de número de expediente (siempre para médicos, condicional para otros)
      campoExpediente: esMedicoUser || (!puedeVerTodos),
      
      // Selector de centro destino
      selectorCentroDestino: puedeVerTodos,
    };
  };

  describe('UI para médico', () => {
    const medico = { rol: 'medico', rol_efectivo: 'medico' };
    
    it('NO muestra selector de subtipo (dropdown)', () => {
      const elementos = getElementosVisibles(medico);
      expect(elementos.selectorSubtipo).toBe(false);
    });

    it('muestra texto fijo "Dispensación por receta"', () => {
      const elementos = getElementosVisibles(medico);
      expect(elementos.textoRecetaFijo).toBe(true);
    });

    it('NO muestra selector de centro destino', () => {
      const elementos = getElementosVisibles(medico);
      expect(elementos.selectorCentroDestino).toBe(false);
    });

    it('muestra campo de número de expediente', () => {
      const elementos = getElementosVisibles(medico);
      expect(elementos.campoExpediente).toBe(true);
    });
  });

  describe('UI para farmacia', () => {
    const farmacia = { rol: 'FARMACIA' };
    
    it('NO muestra selector de subtipo', () => {
      const elementos = getElementosVisibles(farmacia);
      expect(elementos.selectorSubtipo).toBe(false);
    });

    it('muestra texto fijo "Transferencia"', () => {
      const elementos = getElementosVisibles(farmacia);
      expect(elementos.textoTransferenciaFijo).toBe(true);
    });

    it('muestra selector de centro destino', () => {
      const elementos = getElementosVisibles(farmacia);
      expect(elementos.selectorCentroDestino).toBe(true);
    });
  });

  describe('UI para usuario centro (no médico)', () => {
    const centroDummy = { rol: 'usuario_centro' };
    
    it('muestra selector de subtipo (dropdown con 4 opciones)', () => {
      const elementos = getElementosVisibles(centroDummy);
      expect(elementos.selectorSubtipo).toBe(true);
    });

    it('NO muestra texto fijo de receta', () => {
      const elementos = getElementosVisibles(centroDummy);
      expect(elementos.textoRecetaFijo).toBe(false);
    });

    it('NO muestra selector de centro destino', () => {
      const elementos = getElementosVisibles(centroDummy);
      expect(elementos.selectorCentroDestino).toBe(false);
    });
  });
});

// ============ Tests de payload de API según rol ============

describe('Payload de API para movimientos de médico', () => {
  const construirPayload = (formData, user) => {
    const esMedicoUser = (user?.rol_efectivo || user?.rol || '').toLowerCase() === 'medico';
    const puedeVerTodos = user?.is_superuser || ['farmacia', 'admin_sistema'].includes((user?.rol || '').toLowerCase());
    const centroUsuario = user?.centro?.id || user?.centro_id;

    const payload = {
      lote: formData.lote,
      tipo: 'salida',
      cantidad: parseInt(formData.cantidad),
      centro: puedeVerTodos ? formData.centro : centroUsuario,
      observaciones: formData.observaciones || '',
      // Subtipo: transferencia para farmacia, lo que indique el form para otros
      subtipo_salida: puedeVerTodos ? 'transferencia' : formData.subtipo_salida,
    };

    // Agregar expediente si es receta
    if (formData.subtipo_salida === 'receta' && formData.numero_expediente) {
      payload.numero_expediente = formData.numero_expediente.trim();
    }

    return payload;
  };

  it('payload de médico incluye subtipo "receta" y número expediente', () => {
    const user = { rol: 'medico', centro_id: 1 };
    const formData = {
      lote: 201,
      cantidad: '5',
      subtipo_salida: 'receta',
      numero_expediente: 'EXP-2026-001',
      observaciones: 'Dispensación de paracetamol',
    };

    const payload = construirPayload(formData, user);

    expect(payload.tipo).toBe('salida');
    expect(payload.subtipo_salida).toBe('receta');
    expect(payload.numero_expediente).toBe('EXP-2026-001');
    expect(payload.centro).toBe(1);  // Usa centro del usuario
    expect(payload.cantidad).toBe(5);
  });

  it('payload de farmacia incluye subtipo "transferencia"', () => {
    const user = { rol: 'farmacia', is_superuser: false };
    const formData = {
      lote: 201,
      cantidad: '20',
      centro: 5,  // Centro destino seleccionado
      subtipo_salida: 'transferencia',
      observaciones: 'Surtimiento mensual',
    };

    const payload = construirPayload(formData, user);

    expect(payload.tipo).toBe('salida');
    expect(payload.subtipo_salida).toBe('transferencia');
    expect(payload.centro).toBe(5);  // Usa centro seleccionado
    expect(payload.numero_expediente).toBeUndefined();
  });

  it('payload de usuario centro puede tener cualquier subtipo', () => {
    const user = { rol: 'usuario_centro', centro_id: 2 };
    
    // Probar consumo interno
    const formConsumo = {
      lote: 201,
      cantidad: '3',
      subtipo_salida: 'consumo_interno',
      observaciones: '',
    };

    const payloadConsumo = construirPayload(formConsumo, user);
    expect(payloadConsumo.subtipo_salida).toBe('consumo_interno');

    // Probar merma
    const formMerma = {
      lote: 202,
      cantidad: '1',
      subtipo_salida: 'merma',
      observaciones: 'Daño por humedad',
    };

    const payloadMerma = construirPayload(formMerma, user);
    expect(payloadMerma.subtipo_salida).toBe('merma');
  });
});

// ============ Tests de filtros de movimientos ============

describe('Filtros de movimientos visibles para médicos', () => {
  const getMovimientosFiltrados = (movimientos, filtros, user) => {
    const centroUsuario = user?.centro?.id || user?.centro_id;
    const puedeVerTodos = user?.is_superuser || ['farmacia', 'admin_sistema'].includes((user?.rol || '').toLowerCase());

    return movimientos.filter(mov => {
      // Filtro por centro (obligatorio si no puede ver todos)
      if (!puedeVerTodos && mov.centro_id !== centroUsuario) {
        return false;
      }

      // Filtro por subtipo
      if (filtros.subtipo_salida && mov.subtipo_salida !== filtros.subtipo_salida) {
        return false;
      }

      // Filtro por búsqueda
      if (filtros.search) {
        const searchLower = filtros.search.toLowerCase();
        const matchProducto = mov.producto_nombre?.toLowerCase().includes(searchLower);
        const matchLote = mov.lote_numero?.toLowerCase().includes(searchLower);
        if (!matchProducto && !matchLote) {
          return false;
        }
      }

      return true;
    });
  };

  const movimientosMock = [
    { id: 1, centro_id: 1, subtipo_salida: 'receta', producto_nombre: 'Paracetamol', lote_numero: 'LOT-001' },
    { id: 2, centro_id: 1, subtipo_salida: 'consumo_interno', producto_nombre: 'Ibuprofeno', lote_numero: 'LOT-002' },
    { id: 3, centro_id: 2, subtipo_salida: 'receta', producto_nombre: 'Aspirina', lote_numero: 'LOT-003' },
    { id: 4, centro_id: 1, subtipo_salida: 'receta', producto_nombre: 'Amoxicilina', lote_numero: 'LOT-004' },
  ];

  it('médico solo ve movimientos de su centro', () => {
    const user = { rol: 'medico', centro_id: 1 };
    const filtrados = getMovimientosFiltrados(movimientosMock, {}, user);

    expect(filtrados).toHaveLength(3);
    filtrados.forEach(mov => {
      expect(mov.centro_id).toBe(1);
    });
  });

  it('médico puede filtrar por subtipo "receta"', () => {
    const user = { rol: 'medico', centro_id: 1 };
    const filtrados = getMovimientosFiltrados(movimientosMock, { subtipo_salida: 'receta' }, user);

    expect(filtrados).toHaveLength(2);
    filtrados.forEach(mov => {
      expect(mov.subtipo_salida).toBe('receta');
    });
  });

  it('médico puede buscar por nombre de producto', () => {
    const user = { rol: 'medico', centro_id: 1 };
    const filtrados = getMovimientosFiltrados(movimientosMock, { search: 'paracetamol' }, user);

    expect(filtrados).toHaveLength(1);
    expect(filtrados[0].producto_nombre).toBe('Paracetamol');
  });

  it('farmacia ve todos los movimientos', () => {
    const user = { rol: 'farmacia' };
    const filtrados = getMovimientosFiltrados(movimientosMock, {}, user);

    expect(filtrados).toHaveLength(4);
  });
});
