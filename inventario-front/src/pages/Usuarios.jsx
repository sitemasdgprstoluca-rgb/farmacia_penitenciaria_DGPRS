import { useState, useEffect, useRef } from 'react';
import { usuariosAPI, centrosAPI } from '../services/api';
import { toast } from 'react-hot-toast';
import { FaPlus, FaEdit, FaTrash, FaKey, FaUsers, FaTimes, FaDownload, FaFileUpload, FaSearch, FaFilter, FaShieldAlt, FaSpinner, FaToggleOn, FaToggleOff, FaEye, FaEyeSlash } from 'react-icons/fa';
import PageHeader from '../components/PageHeader';
import { COLORS } from '../constants/theme';
import { usePermissions } from '../hooks/usePermissions';
import { useSafeAction } from '../hooks/useSafeAction';
import { UsuariosSkeleton } from '../components/skeletons';
import Pagination from '../components/Pagination';
// ISS-SEC: Componentes para confirmación en 2 pasos
import TwoStepConfirmModal from '../components/TwoStepConfirmModal';
import { useConfirmation } from '../hooks/useConfirmation';

const PAGE_SIZE = 25;

// ROLES DEL SISTEMA - Sincronizados con backend/core/constants.py ROLES_USUARIO
// Orden: Mayor privilegio primero
const ROLES = [
  // Roles de Farmacia Central (pueden NO tener centro asignado)
  { value: 'admin', label: 'Administrador del Sistema', grupo: 'farmacia', requiereCentro: false },
  { value: 'farmacia', label: 'Personal de Farmacia', grupo: 'farmacia', requiereCentro: false },
  { value: 'vista', label: 'Usuario Vista/Consultor', grupo: 'farmacia', requiereCentro: false },
  
  // Roles de Centro Penitenciario (FLUJO V2 - REQUIEREN centro asignado)
  { value: 'director_centro', label: 'Director del Centro', grupo: 'centro', requiereCentro: true },
  { value: 'administrador_centro', label: 'Administrador del Centro', grupo: 'centro', requiereCentro: true },
  { value: 'medico', label: 'Médico del Centro', grupo: 'centro', requiereCentro: true },
  { value: 'centro', label: 'Usuario Centro (consulta)', grupo: 'centro', requiereCentro: true },
  
  // Legacy (compatibilidad con usuarios existentes - ocultos en UI normal)
  { value: 'admin_sistema', label: 'Admin Sistema (legacy)', grupo: 'legacy', requiereCentro: false },
  { value: 'superusuario', label: 'Superusuario (legacy)', grupo: 'legacy', requiereCentro: false },
];

// Constantes de validación de contraseña
const PASSWORD_MIN_LENGTH = 8;
const PASSWORD_REGEX = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/;
const PASSWORD_REQUIREMENTS = 'Mínimo 8 caracteres, 1 mayúscula, 1 minúscula y 1 número';

// Jerarquía de roles (menor número = mayor jerarquía)
// SINCRONIZADO CON backend/core/views.py ROLE_HIERARCHY
const ROL_JERARQUIA = {
  // Nivel 0: Superusuario (acceso total)
  'superuser': 0,
  'superusuario': 0,
  
  // Nivel 1: Administradores del sistema
  'admin': 1,
  'admin_sistema': 1,
  
  // Nivel 2: Personal de Farmacia Central
  'farmacia': 2,
  'admin_farmacia': 2,
  
  // Nivel 3: Directivos del Centro (FLUJO V2)
  'director_centro': 3,
  'administrador_centro': 3,
  
  // Nivel 4: Personal operativo del Centro (FLUJO V2)
  'medico': 4,
  
  // Nivel 5: Usuarios de consulta
  'centro': 5,
  'usuario_centro': 5,
  'vista': 5,
  'usuario_vista': 5,
  'usuario_normal': 5,
};

// Extensiones y tamaño máximo para importación
const IMPORT_ALLOWED_EXTENSIONS = ['.xlsx', '.xls'];
const IMPORT_MAX_FILE_SIZE_MB = 10;

function Usuarios() {
  const [usuarios, setUsuarios] = useState([]);
  const [filteredUsuarios, setFilteredUsuarios] = useState([]);
  const [centros, setCentros] = useState([]);
  const [loading, setLoading] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [importLoading, setImportLoading] = useState(false);
  const [savingUser, setSavingUser] = useState(false); // Guardando en modal
  const { getRequestId: getUserRequestId, resetRequestId: resetUserRequestId } = useSafeAction();
  const [actionLoading, setActionLoading] = useState(null); // ID del usuario en acción
  const [showModal, setShowModal] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  // Estados para visibilidad de contraseñas en modal de cambio
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  // Estados para visibilidad de contraseñas en modal de crear usuario
  const [showCreatePassword, setShowCreatePassword] = useState(false);
  const [showCreateConfirmPassword, setShowCreateConfirmPassword] = useState(false);
  const [showPermisosAvanzados, setShowPermisosAvanzados] = useState(false);
  const [editingUsuario, setEditingUsuario] = useState(null);
  const fileInputRef = useRef(null);
  const { user, permisos, getRolPrincipal } = usePermissions();
  
  // ISS-SEC: Hook para confirmación en 2 pasos
  const {
    confirmState,
    requestDeleteConfirmation,
    executeWithConfirmation,
    cancelConfirmation,
  } = useConfirmation();
  
  // Paginación
  const [currentPage, setCurrentPage] = useState(1);
  const [totalUsuarios, setTotalUsuarios] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  
  // ID del usuario actual (desde el contexto, ya cargado)
  const currentUserId = user?.id;
  
  // Sistema de permisos completo
  const rolPrincipal = getRolPrincipal(); // ADMIN | FARMACIA | CENTRO | VISTA | SIN_ROL
  const esAdmin = rolPrincipal === 'ADMIN';
  const esFarmacia = rolPrincipal === 'FARMACIA';
  const esVista = rolPrincipal === 'VISTA';
  const esSuperusuario = permisos?.isSuperuser;
  const esAdminOFarmacia = esAdmin || esFarmacia || esSuperusuario;
  
  // Admin, Farmacia y superusuario pueden gestionar usuarios
  const tienePermisoGestion = esAdmin || esFarmacia || esSuperusuario;
  // Vista solo puede ver (sin acciones de modificacin)
  const soloLectura = esVista;
  
  // Filtros
  const [searchTerm, setSearchTerm] = useState('');
  const [filterRol, setFilterRol] = useState('');
  const [filterEstado, setFilterEstado] = useState('');
  const [filterCentro, setFilterCentro] = useState('');
  
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    adscripcion: '',
    password: '',
    password_confirm: '',
    rol: 'centro',
    centro: '',
    is_active: true,
    // Permisos personalizados por módulo (null = usar permisos del rol)
    perm_dashboard: null,
    perm_productos: null,
    perm_lotes: null,
    perm_requisiciones: null,
    perm_centros: null,
    perm_usuarios: null,
    perm_reportes: null,
    perm_trazabilidad: null,
    perm_auditoria: null,
    perm_notificaciones: null,
    perm_movimientos: null,
    perm_donaciones: null,
    // FLUJO V2: Permisos granulares del flujo de requisiciones
    perm_crear_requisicion: null,
    perm_autorizar_admin: null,
    perm_autorizar_director: null,
    perm_recibir_farmacia: null,
    perm_autorizar_farmacia: null,
    perm_surtir: null,
    perm_confirmar_entrega: null,
  });
  
  const [passwordData, setPasswordData] = useState({
    new_password: '',
    confirm_password: ''
  });

  // Construir los parámetros de filtro para enviar al backend
  const buildFilterParams = () => {
    const params = {
      page: currentPage,
      page_size: PAGE_SIZE,
    };
    
    // Si no es admin/farmacia, siempre filtrar por centro del usuario
    if (!esAdminOFarmacia && user?.centro?.id) {
      params.centro = user.centro.id;
    } else if (filterCentro) {
      // Admin/farmacia pueden filtrar por cualquier centro
      params.centro = filterCentro;
    }
    
    if (searchTerm.trim()) {
      params.search = searchTerm.trim();
    }
    
    if (filterRol) {
      params.rol = filterRol;
    }
    
    if (filterEstado === 'activo') {
      params.is_active = 'true';
    } else if (filterEstado === 'inactivo') {
      params.is_active = 'false';
    }
    
    return params;
  };

  // Ref para debounce
  const debounceRef = useRef(null);
  
  // Cargar usuarios con filtros server-side
  const cargarUsuarios = async (showLoading = true) => {
    if (showLoading) setLoading(true);
    try {
      const params = buildFilterParams();
      const response = await usuariosAPI.getAll(params);
      const data = response.data.results || response.data;
      setUsuarios(data);
      setFilteredUsuarios(data);
      
      // Manejar paginación del backend
      const total = response.data.count || (Array.isArray(data) ? data.length : 0);
      setTotalUsuarios(total);
      setTotalPages(Math.max(1, Math.ceil(total / PAGE_SIZE)));
    } catch (error) {
      toast.error('Error al cargar usuarios');
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  useEffect(() => {
    cargarCentros();
  }, []);

  // Resetear a página 1 cuando cambian los filtros
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, filterRol, filterEstado, filterCentro]);

  // Cargar usuarios cuando los filtros o página cambian (con debounce para búsqueda)
  useEffect(() => {
    // Si es la primera carga o cambió algo que no sea searchTerm, cargar inmediatamente
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    
    // Debounce solo para searchTerm (300ms), el resto es inmediato
    const delay = searchTerm ? 300 : 0;
    
    debounceRef.current = setTimeout(() => {
      cargarUsuarios();
    }, delay);
    
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchTerm, filterRol, filterEstado, filterCentro, currentPage, esAdminOFarmacia, user?.centro?.id]);
  
  const cargarCentros = async () => {
    try {
      const response = await centrosAPI.getAll({ activo: true });
      setCentros(response.data.results || response.data);
    } catch (error) {
      console.error('Error al cargar centros');
    }
  };
  
  const handleOpenModal = (usuario = null) => {
    if (usuario) {
      setEditingUsuario(usuario);
      // Normalizar centro: puede venir como objeto {id, nombre} o como número
      const centroValue = usuario.centro 
        ? (typeof usuario.centro === 'object' ? usuario.centro.id : usuario.centro)
        : '';
      setFormData({
        username: usuario.username,
        email: usuario.email || '',
        first_name: usuario.first_name || '',
        last_name: usuario.last_name || '',
        adscripcion: usuario.adscripcion || '',
        password: '',
        password_confirm: '',
        rol: usuario.rol || 'centro',
        centro: centroValue,
        is_active: usuario.is_active !== false,
        // Cargar permisos personalizados existentes
        perm_dashboard: usuario.perm_dashboard,
        perm_productos: usuario.perm_productos,
        perm_lotes: usuario.perm_lotes,
        perm_requisiciones: usuario.perm_requisiciones,
        perm_centros: usuario.perm_centros,
        perm_usuarios: usuario.perm_usuarios,
        perm_reportes: usuario.perm_reportes,
        perm_trazabilidad: usuario.perm_trazabilidad,
        perm_auditoria: usuario.perm_auditoria,
        perm_notificaciones: usuario.perm_notificaciones,
        perm_movimientos: usuario.perm_movimientos,
        perm_donaciones: usuario.perm_donaciones,
        // FLUJO V2: Permisos del flujo de requisiciones
        perm_crear_requisicion: usuario.perm_crear_requisicion,
        perm_autorizar_admin: usuario.perm_autorizar_admin,
        perm_autorizar_director: usuario.perm_autorizar_director,
        perm_recibir_farmacia: usuario.perm_recibir_farmacia,
        perm_autorizar_farmacia: usuario.perm_autorizar_farmacia,
        perm_surtir: usuario.perm_surtir,
        perm_confirmar_entrega: usuario.perm_confirmar_entrega,
      });
      // Mostrar permisos avanzados si hay alguno personalizado
      const tienePermisosPersonalizados = [
        usuario.perm_dashboard, usuario.perm_productos, usuario.perm_lotes,
        usuario.perm_requisiciones, usuario.perm_centros, usuario.perm_usuarios,
        usuario.perm_reportes, usuario.perm_trazabilidad, usuario.perm_auditoria,
        usuario.perm_notificaciones, usuario.perm_movimientos, usuario.perm_donaciones,
        // FLUJO V2
        usuario.perm_crear_requisicion, usuario.perm_autorizar_admin, usuario.perm_autorizar_director,
        usuario.perm_recibir_farmacia, usuario.perm_autorizar_farmacia, usuario.perm_surtir,
        usuario.perm_confirmar_entrega
      ].some(p => p !== null && p !== undefined);
      setShowPermisosAvanzados(tienePermisosPersonalizados);
    } else {
      setEditingUsuario(null);
      setFormData({
        username: '',
        email: '',
        first_name: '',
        last_name: '',
        adscripcion: '',
        password: '',
        password_confirm: '',
        rol: 'centro',
        centro: '',
        is_active: true,
        perm_dashboard: null,
        perm_productos: null,
        perm_lotes: null,
        perm_requisiciones: null,
        perm_centros: null,
        perm_usuarios: null,
        perm_reportes: null,
        perm_trazabilidad: null,
        perm_auditoria: null,
        perm_notificaciones: null,
        perm_movimientos: null,
        perm_donaciones: null,
        // FLUJO V2
        perm_crear_requisicion: null,
        perm_autorizar_admin: null,
        perm_autorizar_director: null,
        perm_recibir_farmacia: null,
        perm_autorizar_farmacia: null,
        perm_surtir: null,
        perm_confirmar_entrega: null,
      });
      setShowPermisosAvanzados(false);
    }
    // Resetear visibilidad de contraseñas
    setShowCreatePassword(false);
    setShowCreateConfirmPassword(false);
    setShowModal(true);
  };
  
  const handleCloseModal = () => {
    setShowModal(false);
    setEditingUsuario(null);
    setShowPermisosAvanzados(false);
    setFormData({
      username: '',
      email: '',
      first_name: '',
      last_name: '',
      adscripcion: '',
      password: '',
      password_confirm: '',
      rol: 'centro',
      centro: '',
      is_active: true,
      perm_dashboard: null,
      perm_productos: null,
      perm_lotes: null,
      perm_requisiciones: null,
      perm_centros: null,
      perm_usuarios: null,
      perm_reportes: null,
      perm_trazabilidad: null,
      perm_auditoria: null,
      perm_notificaciones: null,
      perm_movimientos: null,
      perm_donaciones: null,
      // FLUJO V2
      perm_crear_requisicion: null,
      perm_autorizar_admin: null,
      perm_autorizar_director: null,
      perm_recibir_farmacia: null,
      perm_autorizar_farmacia: null,
      perm_surtir: null,
      perm_confirmar_entrega: null,
    });
  };
  
  // Validar si el rol actual puede asignar el rol objetivo
  // ISS-013 FIX: Solo puede asignar roles de MENOR privilegio (mayor número)
  const puedeAsignarRol = (rolObjetivo) => {
    if (esSuperusuario) return true;
    const miJerarquia = ROL_JERARQUIA[rolPrincipal?.toLowerCase()] || 99;
    const objetivoJerarquia = ROL_JERARQUIA[rolObjetivo] || 99;
    // Solo puede asignar roles de menor privilegio (mayor número en jerarquía)
    return miJerarquia < objetivoJerarquia;
  };

  // Validar si el usuario actual puede modificar/eliminar a otro usuario
  // ISS-004 FIX: Solo puede modificar usuarios con MENOR privilegio (mayor número en jerarquía)
  // Un usuario NO puede modificar a otro del mismo rol (excepto superusuarios)
  const puedeModificarUsuario = (usuario) => {
    if (esSuperusuario) return true;
    if (!tienePermisoGestion) return false;
    const miJerarquia = ROL_JERARQUIA[rolPrincipal?.toLowerCase()] || 99;
    const usuarioJerarquia = ROL_JERARQUIA[usuario.rol] || 99;
    // Solo puede modificar si el objetivo tiene MENOR privilegio (mayor número)
    return miJerarquia < usuarioJerarquia;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validar contraseña para nuevos usuarios
    if (!editingUsuario) {
      // CRÍTICO: La contraseña es obligatoria para nuevos usuarios
      if (!formData.password || formData.password.trim() === '') {
        toast.error('La contraseña es obligatoria para nuevos usuarios');
        return;
      }
      
      if (formData.password !== formData.password_confirm) {
        toast.error('Las contraseñas no coinciden');
        return;
      }
      
      if (formData.password.length < PASSWORD_MIN_LENGTH) {
        toast.error(`La contraseña debe tener al menos ${PASSWORD_MIN_LENGTH} caracteres`);
        return;
      }

      if (!PASSWORD_REGEX.test(formData.password)) {
        toast.error(PASSWORD_REQUIREMENTS);
        return;
      }
    }
    
    // Validar que roles que requieren centro lo tengan asignado
    // Usar la propiedad requiereCentro del rol definido en ROLES
    const rolSeleccionado = ROLES.find(r => r.value === formData.rol);
    if (rolSeleccionado?.requiereCentro && !formData.centro) {
      toast.error(`Los usuarios con rol "${rolSeleccionado.label}" deben tener un centro asignado`);
      return;
    }

    // ISS-SEC: Validar escalamiento de privilegios con confirmación en 2 pasos
    if (editingUsuario) {
      const rolAnterior = editingUsuario.rol;
      const rolNuevo = formData.rol;
      const jerarquiaAnterior = ROL_JERARQUIA[rolAnterior] || 99;
      const jerarquiaNueva = ROL_JERARQUIA[rolNuevo] || 99;
      
      // Si está elevando privilegios, pedir confirmación en 2 pasos
      if (jerarquiaNueva < jerarquiaAnterior) {
        if (!puedeAsignarRol(rolNuevo)) {
          toast.error('No tiene permisos para asignar ese rol');
          return;
        }
        
        // Solicitar confirmación en 2 pasos para elevación de privilegios
        requestDeleteConfirmation({
          title: '⚠️ Elevación de Privilegios',
          message: `Está elevando los privilegios de "${editingUsuario.username}". Esta es una operación sensible de seguridad.`,
          itemInfo: {
            'Usuario': editingUsuario.username,
            'Rol anterior': ROLES.find(r => r.value === rolAnterior)?.label || rolAnterior,
            'Rol nuevo': ROLES.find(r => r.value === rolNuevo)?.label || rolNuevo
          },
          onConfirm: () => doSaveUser(),
          isCritical: true,
          confirmPhrase: 'ELEVAR',
          confirmText: 'Confirmar elevación'
        });
        return; // No continuar hasta que se confirme
      }
    } else {
      // Validar que puede crear usuario con ese rol
      if (!puedeAsignarRol(formData.rol)) {
        toast.error('No tiene permisos para crear usuarios con ese rol');
        return;
      }
    }
    
    // Si no hay elevación de privilegios, guardar directamente
    doSaveUser();
  };
  
  // ISS-SEC: Función interna para guardar el usuario (después de confirmaciones)
  const doSaveUser = async () => {
    setSavingUser(true);
    try {
      const payload = {
        username: formData.username,
        email: formData.email,
        first_name: formData.first_name,
        last_name: formData.last_name,
        adscripcion: formData.adscripcion,
        rol: formData.rol,
        is_active: formData.is_active,
        // Usar centro_id para escritura (el serializer lo espera así)
        centro_id: formData.centro ? parseInt(formData.centro, 10) : null
      };
      
      if (!editingUsuario && formData.password) {
        payload.password = formData.password;
      }
      
      // Admin y Farmacia pueden configurar permisos personalizados
      if (esAdmin || esFarmacia || esSuperusuario) {
        payload.perm_dashboard = formData.perm_dashboard;
        payload.perm_productos = formData.perm_productos;
        payload.perm_lotes = formData.perm_lotes;
        payload.perm_requisiciones = formData.perm_requisiciones;
        payload.perm_centros = formData.perm_centros;
        payload.perm_usuarios = formData.perm_usuarios;
        payload.perm_reportes = formData.perm_reportes;
        payload.perm_trazabilidad = formData.perm_trazabilidad;
        payload.perm_auditoria = formData.perm_auditoria;
        payload.perm_notificaciones = formData.perm_notificaciones;
        payload.perm_movimientos = formData.perm_movimientos;
        payload.perm_donaciones = formData.perm_donaciones;
        // FLUJO V2: Permisos del flujo de requisiciones
        payload.perm_crear_requisicion = formData.perm_crear_requisicion;
        payload.perm_autorizar_admin = formData.perm_autorizar_admin;
        payload.perm_autorizar_director = formData.perm_autorizar_director;
        payload.perm_recibir_farmacia = formData.perm_recibir_farmacia;
        payload.perm_autorizar_farmacia = formData.perm_autorizar_farmacia;
        payload.perm_surtir = formData.perm_surtir;
        payload.perm_confirmar_entrega = formData.perm_confirmar_entrega;
      }
      
      if (editingUsuario) {
        await usuariosAPI.update(editingUsuario.id, { ...payload, client_request_id: getUserRequestId() });
        toast.success('Usuario actualizado correctamente');
      } else {
        await usuariosAPI.create({ ...payload, client_request_id: getUserRequestId() });
        toast.success('Usuario creado correctamente');
      }
      
      resetUserRequestId();
      handleCloseModal();
      cargarUsuarios();
    } catch (error) {
      const errorMsg = error.response?.data?.error 
        || error.response?.data?.detail 
        || Object.values(error.response?.data || {}).flat().join(', ')
        || 'Error al guardar usuario';
      toast.error(errorMsg);
    } finally {
      setSavingUser(false);
    }
  };
  
  // ISS-SEC: Función auxiliar para ejecutar eliminación de usuario con confirmación
  const executeDeleteUsuario = async ({ confirmed, actionData }) => {
    const { usuario } = actionData;
    
    setActionLoading(usuario.id);
    try {
      await usuariosAPI.delete(usuario.id, { confirmed });
      toast.success('Usuario eliminado correctamente');
      cargarUsuarios();
    } catch (error) {
      const errorMsg = error.response?.data?.error ||
                       error.response?.data?.detail ||
                       'Error al eliminar usuario';
      toast.error(errorMsg);
      throw error;
    } finally {
      setActionLoading(null);
    }
  };
  
  // ISS-SEC: handleDelete ahora inicia el flujo de confirmación en 2 pasos
  const handleDelete = (usuario) => {
    // Prevenir auto-eliminación (validación robusta)
    if (!currentUserId) {
      toast.error('Espere a que se cargue la sesión antes de eliminar usuarios');
      return;
    }
    if (usuario.id === currentUserId) {
      toast.error('No puede eliminarse a sí mismo. Contacte a otro administrador.');
      return;
    }

    // ISS-004 FIX: Prevenir eliminar usuarios de igual o mayor jerarquía
    const miJerarquia = ROL_JERARQUIA[rolPrincipal?.toLowerCase()] || 99;
    const usuarioJerarquia = ROL_JERARQUIA[usuario.rol] || 99;
    if (usuarioJerarquia <= miJerarquia && !esSuperusuario) {
      toast.error('No puede eliminar usuarios con rol igual o superior al suyo');
      return;
    }

    // Solicitar confirmación en 2 pasos con escritura de "ELIMINAR"
    requestDeleteConfirmation({
      title: 'Confirmar Eliminación de Usuario',
      message: '¿Confirma ELIMINAR PERMANENTEMENTE este usuario?',
      warnings: [
        'Esta acción NO se puede deshacer',
        'El usuario perderá todo acceso al sistema',
        'Se eliminarán las credenciales y configuración del usuario'
      ],
      itemInfo: {
        'Usuario': usuario.username,
        'Nombre': `${usuario.first_name} ${usuario.last_name}`.trim() || 'N/A',
        'Rol': ROLES.find(r => r.value === usuario.rol)?.label || usuario.rol,
        'Email': usuario.email || 'N/A'
      },
      isCritical: true,
      confirmPhrase: 'ELIMINAR',
      confirmText: 'Eliminar Usuario',
      cancelText: 'Cancelar',
      tone: 'danger',
      onConfirm: executeDeleteUsuario,
      actionData: { usuario }
    });
  };

  // ISS-SEC: Función auxiliar para ejecutar toggle de usuario
  const executeToggleUsuario = async ({ actionData }) => {
    const { usuario, nuevoEstado, accion } = actionData;
    
    setActionLoading(usuario.id);
    try {
      await usuariosAPI.update(usuario.id, { is_active: nuevoEstado });
      toast.success(`Usuario ${nuevoEstado ? 'activado' : 'desactivado'} correctamente`);
      cargarUsuarios();
    } catch (error) {
      const errorMsg = error.response?.data?.error ||
                       error.response?.data?.detail ||
                       `Error al ${accion} usuario`;
      toast.error(errorMsg);
      throw error;
    } finally {
      setActionLoading(null);
    }
  };

  // ISS-SEC: Toggle activar/desactivar usuario ahora usa confirmación en 2 pasos
  const handleToggleActivo = (usuario) => {
    // Prevenir auto-desactivación
    if (usuario.id === currentUserId) {
      toast.error('No puede desactivarse a sí mismo');
      return;
    }

    const nuevoEstado = !usuario.is_active;
    const accion = nuevoEstado ? 'activar' : 'desactivar';
    
    requestDeleteConfirmation({
      title: `${nuevoEstado ? 'Activar' : 'Desactivar'} usuario`,
      message: `¿Está seguro de ${accion} al usuario "${usuario.username}"?`,
      itemInfo: {
        'Usuario': usuario.username,
        'Nombre': `${usuario.first_name} ${usuario.last_name}`.trim() || 'N/A',
        'Estado actual': usuario.is_active ? 'Activo' : 'Inactivo',
        'Nuevo estado': nuevoEstado ? 'Activo' : 'Inactivo'
      },
      onConfirm: executeToggleUsuario,
      actionData: { usuario, nuevoEstado, accion },
      isCritical: false,
      confirmText: nuevoEstado ? 'Activar' : 'Desactivar'
    });
  };
  
  const handleOpenPasswordModal = (usuario) => {
    setEditingUsuario(usuario);
    setPasswordData({ new_password: '', confirm_password: '' });
    setShowNewPassword(false);
    setShowConfirmPassword(false);
    setShowPasswordModal(true);
  };
  
  const handleChangePassword = async (e) => {
    e.preventDefault();
    
    if (passwordData.new_password !== passwordData.confirm_password) {
      toast.error('Las contraseñas no coinciden');
      return;
    }
    
    if (passwordData.new_password.length < PASSWORD_MIN_LENGTH) {
      toast.error(`La contraseña debe tener al menos ${PASSWORD_MIN_LENGTH} caracteres`);
      return;
    }

    if (!PASSWORD_REGEX.test(passwordData.new_password)) {
      toast.error(PASSWORD_REQUIREMENTS);
      return;
    }
    
    setActionLoading(editingUsuario.id);
    try {
      await usuariosAPI.cambiarPassword(editingUsuario.id, {
        new_password: passwordData.new_password
      });
      toast.success('Contraseña actualizada correctamente');
      setShowPasswordModal(false);
      setPasswordData({ new_password: '', confirm_password: '' });
    } catch (error) {
      const errorMsg = error.response?.data?.error ||
                       error.response?.data?.detail ||
                       'Error al cambiar contraseña';
      toast.error(errorMsg);
    } finally {
      setActionLoading(null);
    }
  };

  // Exportar usuarios a Excel (con los mismos filtros que la vista)
  const handleExportar = async () => {
    if (exportLoading) return; // Prevenir doble clic
    
    try {
      setExportLoading(true);
      // Usar los mismos filtros que el listado para coherencia
      const params = buildFilterParams();
      const response = await usuariosAPI.exportar(params);
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `usuarios_${new Date().toISOString().slice(0, 10)}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success('Usuarios exportados correctamente');
    } catch (error) {
      toast.error('Error al exportar usuarios');
    } finally {
      setExportLoading(false);
    }
  };

  // Handler para descargar plantilla de importación
  const handleDescargarPlantilla = async () => {
    try {
      const response = await usuariosAPI.plantilla();
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'Plantilla_Usuarios.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success('Plantilla descargada correctamente');
    } catch (err) {
      console.error('Error al descargar plantilla', err);
      toast.error('No se pudo descargar la plantilla');
    }
  };

  // Importar usuarios desde Excel
  const handleImportar = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validar extensión localmente
    const extension = '.' + file.name.split('.').pop().toLowerCase();
    if (!IMPORT_ALLOWED_EXTENSIONS.includes(extension)) {
      toast.error(`Extensión no permitida: ${extension}. Use: ${IMPORT_ALLOWED_EXTENSIONS.join(', ')}`);
      e.target.value = null;
      return;
    }

    // Validar tamaño localmente
    const sizeMB = file.size / (1024 * 1024);
    if (sizeMB > IMPORT_MAX_FILE_SIZE_MB) {
      toast.error(`Archivo demasiado grande: ${sizeMB.toFixed(1)}MB. Máximo: ${IMPORT_MAX_FILE_SIZE_MB}MB`);
      e.target.value = null;
      return;
    }

    const formDataFile = new FormData();
    formDataFile.append('file', file);

    try {
      setImportLoading(true);
      const response = await usuariosAPI.importar(formDataFile);
      // Backend devuelve { resumen: { creados, actualizados, errores }, errores: [...] }
      const resumen = response.data.resumen || response.data;
      const { creados, actualizados } = resumen;
      const errores = response.data.errores || [];
      toast.success(`Importación completada: ${creados || 0} creados, ${actualizados || 0} actualizados`);
      
      if (errores?.length) {
        console.warn('Errores de importación:', errores);
        // Mostrar hasta 5 errores en toasts
        errores.slice(0, 5).forEach((err, idx) => {
          const fila = err.fila || idx + 1;
          const msg = err.error || err.mensaje || JSON.stringify(err);
          toast.error(`Fila ${fila}: ${msg}`, { duration: 5000 });
        });
        if (errores.length > 5) {
          toast.error(`... y ${errores.length - 5} errores más. Revise la consola.`, { duration: 5000 });
        }
      }
      cargarUsuarios();
    } catch (error) {
      const errorMsg = error.response?.data?.error ||
                       error.response?.data?.detail ||
                       'Error al importar usuarios';
      toast.error(errorMsg);
    } finally {
      e.target.value = null;
      setImportLoading(false);
    }
  };

  // Limpiar filtros
  const limpiarFiltros = () => {
    setSearchTerm('');
    setFilterRol('');
    setFilterEstado('');
    setFilterCentro('');
  };

  // Cruzar tienePermisoGestion con permisos del backend para respetar permisos personalizados
  // Un usuario puede tener rol farmacia pero permisos limitados por el admin
  const tieneGestionBackend = permisos?.gestionUsuarios !== false;
  const puedeGestionar = tienePermisoGestion && tieneGestionBackend;

  const puede = {
    ver: puedeGestionar || soloLectura,
    crear: puedeGestionar,
    editar: puedeGestionar,
    eliminar: puedeGestionar,
    cambiarPassword: puedeGestionar,
    exportar: puedeGestionar,
    importar: puedeGestionar
  };

  const headerActions = (
    <div className="flex flex-wrap gap-2">
      {puede.exportar && (
        <button
          type="button"
          onClick={handleExportar}
          disabled={exportLoading || importLoading}
          className="cc-btn cc-btn-secondary"
        >
          {exportLoading ? (
            <>
              <FaSpinner className="animate-spin" />
              Exportando...
            </>
          ) : (
            <>
              <FaDownload /> Exportar
            </>
          )}
        </button>
      )}
      {puede.importar && (
        <>
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={exportLoading || importLoading}
            className="cc-btn cc-btn-secondary"
          >
            {importLoading ? (
              <>
                <FaSpinner className="animate-spin" />
                Importando...
              </>
            ) : (
              <>
                <FaFileUpload /> Importar
              </>
            )}
          </button>
          
          {/* Botón de descarga de plantilla */}
          <button
            type="button"
            onClick={handleDescargarPlantilla}
            className="cc-btn cc-btn-ghost"
            title="Descargar plantilla Excel para importación"
          >
            <FaDownload /> Plantilla
          </button>
          
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx,.xls"
            className="hidden"
            onChange={handleImportar}
          />
        </>
      )}
      {puede.crear && (
        <button
          type="button"
          onClick={() => handleOpenModal()}
          disabled={exportLoading || importLoading}
          className="cc-btn cc-btn-primary"
        >
          <FaPlus /> Nuevo Usuario
        </button>
      )}
    </div>
  );

  return (
    <div className="p-4 sm:p-6 space-y-6">
      <PageHeader
        icon={FaUsers}
        title="Gestión de Usuarios"
        subtitle={`Total: ${totalUsuarios} usuarios | Página ${currentPage} de ${totalPages}`}
        actions={headerActions}
      />

      {/* Filtros */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div className="relative">
            <FaSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar usuario, email, nombre..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent focus:ring-theme-primary"
            />
          </div>
          <div>
            <select
              value={filterRol}
              onChange={(e) => setFilterRol(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
            >
              <option value="">Todos los roles</option>
              <optgroup label="Farmacia Central">
                {ROLES.filter(r => r.grupo === 'farmacia').map(rol => (
                  <option key={rol.value} value={rol.value}>{rol.label}</option>
                ))}
              </optgroup>
              <optgroup label="Centro Penitenciario">
                {ROLES.filter(r => r.grupo === 'centro').map(rol => (
                  <option key={rol.value} value={rol.value}>{rol.label}</option>
                ))}
              </optgroup>
              {/* Solo mostrar legacy si hay usuarios con esos roles */}
              {esSuperusuario && (
                <optgroup label="Legacy">
                  {ROLES.filter(r => r.grupo === 'legacy').map(rol => (
                    <option key={rol.value} value={rol.value}>{rol.label}</option>
                  ))}
                </optgroup>
              )}
            </select>
          </div>
          <div>
            <select
              value={esAdminOFarmacia ? filterCentro : (user?.centro?.id?.toString() || '')}
              onChange={(e) => esAdminOFarmacia && setFilterCentro(e.target.value)}
              disabled={!esAdminOFarmacia}
              className={`w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent ${
                !esAdminOFarmacia ? 'bg-gray-100 cursor-not-allowed' : ''
              }`}
              title={!esAdminOFarmacia ? 'Solo puedes ver usuarios de tu centro' : ''}
            >
              {esAdminOFarmacia ? (
                <>
                  <option value="">Todos los centros</option>
                  {centros.map(centro => (
                    <option key={centro.id} value={centro.id}>{centro.nombre}</option>
                  ))}
                </>
              ) : (
                <option value={user?.centro?.id || ''}>
                  {centros.find(c => c.id === user?.centro?.id)?.nombre || 'Tu centro'}
                </option>
              )}
            </select>
          </div>
          <div>
            <select
              value={filterEstado}
              onChange={(e) => setFilterEstado(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
            >
              <option value="">Todos los estados</option>
              <option value="activo">Activos</option>
              <option value="inactivo">Inactivos</option>
            </select>
          </div>
          <div>
            <button
              type="button"
              onClick={limpiarFiltros}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50 font-semibold transition"
            >
              <FaFilter className="inline mr-2" /> Limpiar
            </button>
          </div>
        </div>
      </div>

      {loading ? (
        <UsuariosSkeleton />
      ) : (
        <>
        {/* Vista móvil: tarjetas */}
        <div className="lg:hidden space-y-3">
          {filteredUsuarios.length === 0 ? (
            <div className="bg-white rounded-lg border border-gray-200 shadow-md p-6 text-center text-gray-500">
              {totalUsuarios === 0 && !searchTerm && !filterRol && !filterEstado && !filterCentro
                ? 'No hay usuarios registrados' 
                : 'No se encontraron usuarios con los filtros aplicados'}
            </div>
          ) : filteredUsuarios.map((usuario, idx) => (
            <div key={usuario.id} className="bg-white rounded-lg border border-gray-200 shadow-md p-4">
              {/* Header con usuario y estado */}
              <div className="flex items-start justify-between gap-2 mb-2">
                <div>
                  <div className="font-medium text-gray-900">{usuario.username}</div>
                  <div className="text-sm text-gray-600">{usuario.first_name} {usuario.last_name}</div>
                </div>
                <span className={`px-2 py-1 text-xs font-semibold rounded-full shrink-0 ${
                  usuario.is_active !== false ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                }`}>
                  {usuario.is_active !== false ? 'Activo' : 'Inactivo'}
                </span>
              </div>
              
              {/* Info */}
              <div className="space-y-1 text-sm mb-3">
                {usuario.email && (
                  <div className="text-gray-600 truncate">{usuario.email}</div>
                )}
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                    usuario.rol === 'admin' || usuario.rol === 'admin_sistema' ? 'bg-purple-100 text-purple-800' :
                    usuario.rol === 'farmacia' ? 'bg-blue-100 text-blue-800' :
                    usuario.rol === 'director_centro' ? 'bg-amber-100 text-amber-800' :
                    usuario.rol === 'administrador_centro' ? 'bg-orange-100 text-orange-800' :
                    usuario.rol === 'medico' ? 'bg-teal-100 text-teal-800' :
                    usuario.rol === 'centro' ? 'bg-green-100 text-green-800' :
                    usuario.rol === 'vista' ? 'bg-gray-100 text-gray-700' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {ROLES.find(r => r.value === usuario.rol)?.label || usuario.rol || 'Sin rol'}
                  </span>
                  {usuario.centro?.nombre && (
                    <span className="text-gray-500">{usuario.centro.nombre}</span>
                  )}
                </div>
              </div>
              
              {/* Acciones */}
              {puedeModificarUsuario(usuario) && (
                <div className="flex items-center gap-2 pt-2 border-t border-gray-100">
                  {puede.editar && (
                    <button 
                      onClick={() => handleOpenModal(usuario)}
                      disabled={actionLoading === usuario.id}
                      className="flex-1 px-3 py-2 text-sm text-blue-600 bg-blue-50 rounded-lg flex items-center justify-center gap-1 disabled:opacity-50"
                    >
                      <FaEdit /> Editar
                    </button>
                  )}
                  {puede.cambiarPassword && (
                    <button 
                      onClick={() => handleOpenPasswordModal(usuario)}
                      disabled={actionLoading === usuario.id}
                      className="flex-1 px-3 py-2 text-sm text-green-600 bg-green-50 rounded-lg flex items-center justify-center gap-1 disabled:opacity-50"
                    >
                      <FaKey /> Password
                    </button>
                  )}
                  {puede.editar && usuario.id !== currentUserId && (
                    <button 
                      onClick={() => handleToggleActivo(usuario)}
                      disabled={actionLoading === usuario.id}
                      className={`px-3 py-2 text-sm rounded-lg disabled:opacity-50 ${
                        usuario.is_active !== false 
                          ? 'text-red-600 bg-red-50' 
                          : 'text-green-600 bg-green-50'
                      }`}
                    >
                      {usuario.is_active !== false ? <FaBan /> : <FaCheck />}
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
        
        {/* Vista desktop: tabla */}
        <div className="hidden lg:block w-full overflow-x-auto rounded-lg border border-gray-200 shadow-md">
          <table className="w-full min-w-[700px] divide-y divide-gray-200">
            <thead className="bg-theme-gradient sticky top-0 z-10">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold text-white uppercase whitespace-nowrap">#</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-white uppercase whitespace-nowrap">Usuario</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-white uppercase whitespace-nowrap">Nombre</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-white uppercase whitespace-nowrap">Email</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-white uppercase whitespace-nowrap">Rol</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-white uppercase whitespace-nowrap">Centro</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-white uppercase whitespace-nowrap">Estado</th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-white uppercase whitespace-nowrap">Acciones</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredUsuarios.length === 0 ? (
                <tr>
                  <td colSpan="8" className="px-6 py-12 text-center text-gray-500">
                    {totalUsuarios === 0 && !searchTerm && !filterRol && !filterEstado && !filterCentro
                      ? 'No hay usuarios registrados' 
                      : 'No se encontraron usuarios con los filtros aplicados'}
                  </td>
                </tr>
              ) : filteredUsuarios.map((usuario, idx) => (
                <tr key={usuario.id} className={`hover:bg-gray-50 ${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}`}>
                  <td className="px-6 py-4 text-sm text-gray-500">{(currentPage - 1) * PAGE_SIZE + idx + 1}</td>
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">{usuario.username}</td>
                  <td className="px-6 py-4 text-sm text-gray-700">{usuario.first_name} {usuario.last_name}</td>
                  <td className="px-6 py-4 text-sm text-gray-600">{usuario.email}</td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                      usuario.rol === 'admin' || usuario.rol === 'admin_sistema' ? 'bg-purple-100 text-purple-800' :
                      usuario.rol === 'farmacia' ? 'bg-blue-100 text-blue-800' :
                      usuario.rol === 'director_centro' ? 'bg-amber-100 text-amber-800' :
                      usuario.rol === 'administrador_centro' ? 'bg-orange-100 text-orange-800' :
                      usuario.rol === 'medico' ? 'bg-teal-100 text-teal-800' :
                      usuario.rol === 'centro' ? 'bg-green-100 text-green-800' :
                      usuario.rol === 'vista' ? 'bg-gray-100 text-gray-700' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {ROLES.find(r => r.value === usuario.rol)?.label || usuario.rol || 'Sin rol'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">{usuario.centro?.nombre || '-'}</td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                      usuario.is_active !== false ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {usuario.is_active !== false ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right space-x-2">
                    {/* Solo mostrar botones si el usuario actual puede modificar a este usuario */}
                    {puedeModificarUsuario(usuario) ? (
                      <>
                        {puede.editar && (
                          <button 
                            onClick={() => handleOpenModal(usuario)}
                            disabled={actionLoading === usuario.id}
                            className="text-blue-600 hover:text-blue-800 transition disabled:opacity-50"
                            title="Editar"
                          >
                            <FaEdit />
                          </button>
                        )}
                        {puede.cambiarPassword && (
                          <button 
                            onClick={() => handleOpenPasswordModal(usuario)}
                            disabled={actionLoading === usuario.id}
                            className="text-green-600 hover:text-green-800 transition disabled:opacity-50"
                            title="Cambiar contraseña"
                          >
                            <FaKey />
                          </button>
                        )}
                        {/* Toggle activar/desactivar */}
                        {puede.editar && usuario.id !== currentUserId && (
                          <button 
                            onClick={() => handleToggleActivo(usuario)}
                            disabled={actionLoading === usuario.id}
                            className={`transition disabled:opacity-50 ${
                              usuario.is_active 
                                ? 'text-amber-600 hover:text-amber-800' 
                                : 'text-emerald-600 hover:text-emerald-800'
                            }`}
                            title={usuario.is_active ? "Desactivar usuario" : "Activar usuario"}
                          >
                            {usuario.is_active ? <FaToggleOn size={18} /> : <FaToggleOff size={18} />}
                          </button>
                        )}
                        {puede.eliminar && usuario.id !== currentUserId && (
                          <button 
                            onClick={() => handleDelete(usuario)}
                            disabled={actionLoading === usuario.id || !currentUserId}
                            className="text-red-600 hover:text-red-800 transition disabled:opacity-50"
                            title={!currentUserId ? "Cargando sesión..." : "Eliminar"}
                          >
                            {actionLoading === usuario.id ? (
                              <FaSpinner className="animate-spin" />
                            ) : (
                              <FaTrash />
                            )}
                          </button>
                        )}
                        {usuario.id === currentUserId && (
                          <span className="text-gray-400 text-xs italic" title="No puede eliminarse a sí mismo">
                            (Tú)
                          </span>
                        )}
                      </>
                    ) : (
                      <span className="text-gray-400 text-xs italic" title="Usuario con mayor privilegio">
                        🔒 Protegido
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {/* Paginación */}
        {totalPages > 1 && (
          <Pagination
            page={currentPage}
            totalPages={totalPages}
            onPageChange={setCurrentPage}
            totalItems={totalUsuarios}
            pageSize={PAGE_SIZE}
          />
        )}
        </>
      )}
      
      {/* Modal Crear/Editar Usuario */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-theme-gradient px-6 py-4 flex justify-between items-center rounded-t-2xl">
              <h3 className="text-xl font-bold text-white">
                {editingUsuario ? 'Editar Usuario' : 'Nuevo Usuario'}
              </h3>
              <button onClick={handleCloseModal} className="text-white/70 hover:text-white">
                <FaTimes size={24} />
              </button>
            </div>
            
            <form onSubmit={handleSubmit} className="p-6 space-y-5">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-1">
                    Usuario <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.username}
                    onChange={(e) => setFormData({...formData, username: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    required
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-1">
                    Email <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({...formData, email: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    required
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-1">
                    Nombre <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.first_name}
                    onChange={(e) => setFormData({...formData, first_name: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    required
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-1">
                    Apellidos <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.last_name}
                    onChange={(e) => setFormData({...formData, last_name: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    required
                  />
                </div>
                
                <div className="md:col-span-2">
                  <label className="block text-sm font-semibold text-gray-700 mb-1">
                    Adscripción
                  </label>
                  <input
                    type="text"
                    value={formData.adscripcion}
                    onChange={(e) => setFormData({...formData, adscripcion: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Ej: Departamento de Sistemas, Área Médica, etc."
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-1">
                    Rol <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={formData.rol}
                    onChange={(e) => setFormData({...formData, rol: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    required
                  >
                    {/* Agrupar roles por grupo, ocultar legacy salvo que el usuario ya tenga ese rol */}
                    {ROLES
                      .filter(rol => rol.grupo !== 'legacy' || editingUsuario?.rol === rol.value)
                      .map(rol => {
                        const disabled = !puedeAsignarRol(rol.value);
                        return (
                          <option 
                            key={rol.value} 
                            value={rol.value}
                            disabled={disabled}
                          >
                            {rol.label}{disabled ? ' (sin permiso)' : ''}{rol.requiereCentro ? ' *' : ''}
                          </option>
                        );
                      })}
                  </select>
                  <p className="text-xs text-gray-500 mt-1">
                    * Roles marcados con asterisco requieren centro asignado
                  </p>
                  {editingUsuario && formData.rol !== editingUsuario.rol && (
                    <p className="text-xs text-amber-600 mt-1">
                      ⚠️ Cambiar el rol afectará los permisos del usuario
                    </p>
                  )}
                </div>
                
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-1">
                    Centro {ROLES.find(r => r.value === formData.rol)?.requiereCentro && <span className="text-red-500">*</span>}
                  </label>
                  <select
                    value={formData.centro}
                    onChange={(e) => setFormData({...formData, centro: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    required={ROLES.find(r => r.value === formData.rol)?.requiereCentro}
                  >
                    <option value="">Sin asignar</option>
                    {centros.map(centro => (
                      <option key={centro.id} value={centro.id}>{centro.nombre}</option>
                    ))}
                  </select>
                </div>
                
                {!editingUsuario && (
                  <>
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-1">
                        Contraseña <span className="text-red-500">*</span>
                      </label>
                      <div className="relative">
                        <input
                          type={showCreatePassword ? "text" : "password"}
                          value={formData.password}
                          onChange={(e) => setFormData({...formData, password: e.target.value})}
                          className={`w-full px-3 py-2 pr-10 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                            formData.password && !PASSWORD_REGEX.test(formData.password) 
                              ? 'border-amber-400' 
                              : 'border-gray-300'
                          }`}
                          required
                          minLength={8}
                        />
                        <button
                          type="button"
                          onClick={() => setShowCreatePassword(!showCreatePassword)}
                          className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600"
                          tabIndex={-1}
                        >
                          {showCreatePassword ? <FaEyeSlash size={16} /> : <FaEye size={16} />}
                        </button>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        {PASSWORD_REQUIREMENTS}
                      </p>
                      {formData.password && (
                        <div className="text-xs mt-1 space-y-0.5">
                          <p className={formData.password.length >= 8 ? 'text-green-600' : 'text-red-500'}>
                            {formData.password.length >= 8 ? '✓' : '✗'} Mínimo 8 caracteres
                          </p>
                          <p className={/[A-Z]/.test(formData.password) ? 'text-green-600' : 'text-red-500'}>
                            {/[A-Z]/.test(formData.password) ? '✓' : '✗'} Al menos 1 mayúscula
                          </p>
                          <p className={/[a-z]/.test(formData.password) ? 'text-green-600' : 'text-red-500'}>
                            {/[a-z]/.test(formData.password) ? '✓' : '✗'} Al menos 1 minúscula
                          </p>
                          <p className={/\d/.test(formData.password) ? 'text-green-600' : 'text-red-500'}>
                            {/\d/.test(formData.password) ? '✓' : '✗'} Al menos 1 número
                          </p>
                        </div>
                      )}
                    </div>
                    
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-1">
                        Confirmar Contraseña <span className="text-red-500">*</span>
                      </label>
                      <div className="relative">
                        <input
                          type={showCreateConfirmPassword ? "text" : "password"}
                          value={formData.password_confirm}
                          onChange={(e) => setFormData({...formData, password_confirm: e.target.value})}
                          className={`w-full px-3 py-2 pr-10 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                            formData.password_confirm && formData.password !== formData.password_confirm 
                              ? 'border-red-400' 
                              : 'border-gray-300'
                          }`}
                          required
                          minLength={8}
                        />
                        <button
                          type="button"
                          onClick={() => setShowCreateConfirmPassword(!showCreateConfirmPassword)}
                          className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600"
                          tabIndex={-1}
                        >
                          {showCreateConfirmPassword ? <FaEyeSlash size={16} /> : <FaEye size={16} />}
                        </button>
                      </div>
                      {formData.password_confirm && formData.password !== formData.password_confirm && (
                        <p className="text-xs text-red-500 mt-1">Las contraseñas no coinciden</p>
                      )}
                      {formData.password_confirm && formData.password === formData.password_confirm && (
                        <p className="text-xs text-green-600 mt-1">✓ Las contraseñas coinciden</p>
                      )}
                    </div>
                  </>
                )}
                
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="is_active"
                    checked={formData.is_active}
                    onChange={(e) => setFormData({...formData, is_active: e.target.checked})}
                    className="w-4 h-4 rounded border-gray-300 focus:ring-2 focus:ring-blue-500"
                  />
                  <label htmlFor="is_active" className="text-sm font-medium text-gray-700">
                    Usuario activo
                  </label>
                </div>
              </div>
              
              {/* Sección de Permisos Avanzados - Visible para Admin y Farmacia */}
              {(esAdmin || esFarmacia || esSuperusuario) && (
                <div className="border-t pt-4 mt-4">
                  <button
                    type="button"
                    onClick={() => setShowPermisosAvanzados(!showPermisosAvanzados)}
                    className="flex items-center gap-2 text-sm font-semibold mb-3 text-theme-primary hover:opacity-80 transition"
                  >
                    <FaShieldAlt />
                    <span>{showPermisosAvanzados ? '▼' : '▶'} Configurar Permisos Personalizados</span>
                  </button>
                  
                  {showPermisosAvanzados && (
                    <div className="bg-gray-50 rounded-lg p-5 space-y-4">
                      <p className="text-xs text-gray-600">
                        Configure permisos específicos para este usuario. Dejar en &quot;Por defecto&quot; usa los permisos del rol asignado.
                      </p>
                      
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                        {[
                          { key: 'perm_dashboard', label: 'Dashboard', icon: '📊' },
                          { key: 'perm_productos', label: 'Productos', icon: '📦' },
                          { key: 'perm_lotes', label: 'Lotes', icon: '🏷️' },
                          { key: 'perm_requisiciones', label: 'Requisiciones', icon: '📋' },
                          { key: 'perm_movimientos', label: 'Movimientos', icon: '🔄' },
                          { key: 'perm_donaciones', label: 'Donaciones', icon: '🎁' },
                          { key: 'perm_centros', label: 'Centros', icon: '🏢' },
                          { key: 'perm_usuarios', label: 'Usuarios', icon: '👥' },
                          { key: 'perm_reportes', label: 'Reportes', icon: '📈' },
                          { key: 'perm_trazabilidad', label: 'Trazabilidad', icon: '🔍' },
                          { key: 'perm_auditoria', label: 'Auditoría', icon: '🛡️' },
                          { key: 'perm_notificaciones', label: 'Notificaciones', icon: '🔔' },
                        ].map(({ key, label, icon }) => (
                          <div key={key} className="flex items-center gap-3 bg-white p-3 rounded-lg border border-gray-200 shadow-sm">
                            <span>{icon}</span>
                            <span className="text-xs font-medium flex-1">{label}</span>
                            <select
                              value={formData[key] === null ? 'default' : formData[key] ? 'true' : 'false'}
                              onChange={(e) => {
                                const val = e.target.value;
                                setFormData({
                                  ...formData,
                                  [key]: val === 'default' ? null : val === 'true'
                                });
                              }}
                              className="text-xs border rounded px-2 py-1 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                              <option value="default">Por defecto</option>
                              <option value="true"> Permitir</option>
                              <option value="false"> Denegar</option>
                            </select>
                          </div>
                        ))}
                      </div>
                      
                      {/* FLUJO V2: Permisos del flujo de requisiciones */}
                      <div className="border-t pt-4 mt-4">
                        <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                          📋 Permisos de Flujo de Requisiciones
                        </h4>
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                          {[
                            { key: 'perm_crear_requisicion', label: 'Crear Requisición', icon: '✏️' },
                            { key: 'perm_autorizar_admin', label: 'Autorizar (Admin Centro)', icon: '✅' },
                            { key: 'perm_autorizar_director', label: 'Autorizar (Director)', icon: '👔' },
                            { key: 'perm_recibir_farmacia', label: 'Recibir en Farmacia', icon: '📥' },
                            { key: 'perm_autorizar_farmacia', label: 'Autorizar en Farmacia', icon: '💊' },
                            { key: 'perm_surtir', label: 'Surtir Requisición', icon: '📤' },
                            { key: 'perm_confirmar_entrega', label: 'Confirmar Entrega', icon: '✔️' },
                          ].map(({ key, label, icon }) => (
                            <div key={key} className="flex items-center gap-3 bg-white p-3 rounded-lg border border-gray-200 shadow-sm">
                              <span>{icon}</span>
                              <span className="text-xs font-medium flex-1">{label}</span>
                              <select
                                value={formData[key] === null ? 'default' : formData[key] ? 'true' : 'false'}
                                onChange={(e) => {
                                  const val = e.target.value;
                                  setFormData({
                                    ...formData,
                                    [key]: val === 'default' ? null : val === 'true'
                                  });
                                }}
                                className="text-xs border rounded px-2 py-1 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
                              >
                                <option value="default">Por defecto</option>
                                <option value="true"> Permitir</option>
                                <option value="false"> Denegar</option>
                              </select>
                            </div>
                          ))}
                        </div>
                      </div>
                      
                      <div className="flex gap-2 mt-3">
                        <button
                          type="button"
                          onClick={() => setFormData({
                            ...formData,
                            perm_dashboard: null, perm_productos: null, perm_lotes: null,
                            perm_requisiciones: null, perm_centros: null, perm_usuarios: null,
                            perm_reportes: null, perm_trazabilidad: null, perm_auditoria: null,
                            perm_notificaciones: null, perm_movimientos: null, perm_donaciones: null,
                            // FLUJO V2
                            perm_crear_requisicion: null, perm_autorizar_admin: null, perm_autorizar_director: null,
                            perm_recibir_farmacia: null, perm_autorizar_farmacia: null, perm_surtir: null,
                            perm_confirmar_entrega: null,
                          })}
                          className="text-xs px-3 py-1 bg-gray-200 hover:bg-gray-300 rounded transition font-semibold"
                        >
                          Restablecer todos
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
              
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={handleCloseModal}
                  disabled={savingUser}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-semibold transition disabled:opacity-50"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={savingUser}
                  className="flex-1 px-4 py-2 text-white rounded-lg font-semibold transition hover:opacity-90 bg-theme-gradient disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {savingUser ? (
                    <>
                      <FaSpinner className="animate-spin" />
                      Guardando...
                    </>
                  ) : (
                    <>
                      {editingUsuario ? 'Actualizar' : 'Crear'} Usuario
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      
      {/* Modal Cambiar Contraseña */}
      {showPasswordModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full overflow-hidden">
            <div className="px-6 py-4 bg-theme-gradient rounded-t-2xl flex justify-between items-center">
              <h3 className="text-xl font-bold text-white">
                Cambiar Contraseña
              </h3>
              <button onClick={() => setShowPasswordModal(false)} className="text-white/70 hover:text-white">
                <FaTimes size={24} />
              </button>
            </div>
            
            <div className="px-6 py-2 bg-gray-50 border-b">
              <p className="text-sm text-gray-600">
                Usuario: <span className="font-semibold">{editingUsuario?.username}</span>
              </p>
            </div>
            
            <form onSubmit={handleChangePassword} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">
                  Nueva Contraseña <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <input
                    type={showNewPassword ? "text" : "password"}
                    value={passwordData.new_password}
                    onChange={(e) => setPasswordData({...passwordData, new_password: e.target.value})}
                    className={`w-full px-3 py-2 pr-10 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                      passwordData.new_password && !PASSWORD_REGEX.test(passwordData.new_password) 
                        ? 'border-amber-400' 
                        : 'border-gray-300'
                    }`}
                    required
                    minLength={8}
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600"
                    tabIndex={-1}
                  >
                    {showNewPassword ? <FaEyeSlash size={16} /> : <FaEye size={16} />}
                  </button>
                </div>
                <p className="text-xs text-gray-500 mt-1">{PASSWORD_REQUIREMENTS}</p>
                {passwordData.new_password && (
                  <div className="text-xs mt-1 space-y-0.5">
                    <p className={passwordData.new_password.length >= 8 ? 'text-green-600' : 'text-red-500'}>
                      {passwordData.new_password.length >= 8 ? '✓' : '✗'} Mínimo 8 caracteres
                    </p>
                    <p className={/[A-Z]/.test(passwordData.new_password) ? 'text-green-600' : 'text-red-500'}>
                      {/[A-Z]/.test(passwordData.new_password) ? '✓' : '✗'} Al menos 1 mayúscula
                    </p>
                    <p className={/[a-z]/.test(passwordData.new_password) ? 'text-green-600' : 'text-red-500'}>
                      {/[a-z]/.test(passwordData.new_password) ? '✓' : '✗'} Al menos 1 minúscula
                    </p>
                    <p className={/\d/.test(passwordData.new_password) ? 'text-green-600' : 'text-red-500'}>
                      {/\d/.test(passwordData.new_password) ? '✓' : '✗'} Al menos 1 número
                    </p>
                  </div>
                )}
              </div>
              
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">
                  Confirmar Contraseña <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <input
                    type={showConfirmPassword ? "text" : "password"}
                    value={passwordData.confirm_password}
                    onChange={(e) => setPasswordData({...passwordData, confirm_password: e.target.value})}
                    className={`w-full px-3 py-2 pr-10 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                      passwordData.confirm_password && passwordData.new_password !== passwordData.confirm_password 
                        ? 'border-red-400' 
                        : 'border-gray-300'
                    }`}
                    required
                    minLength={8}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600"
                    tabIndex={-1}
                  >
                    {showConfirmPassword ? <FaEyeSlash size={16} /> : <FaEye size={16} />}
                  </button>
                </div>
                {passwordData.confirm_password && passwordData.new_password !== passwordData.confirm_password && (
                  <p className="text-xs text-red-500 mt-1">Las contraseñas no coinciden</p>
                )}
                {passwordData.confirm_password && passwordData.new_password === passwordData.confirm_password && (
                  <p className="text-xs text-green-600 mt-1">✓ Las contraseñas coinciden</p>
                )}
              </div>
              
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowPasswordModal(false)}
                  disabled={actionLoading}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-semibold transition disabled:opacity-50"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={actionLoading || !PASSWORD_REGEX.test(passwordData.new_password) || passwordData.new_password !== passwordData.confirm_password}
                  className="flex-1 px-4 py-2 text-white rounded-lg font-semibold transition hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed bg-theme-gradient flex items-center justify-center gap-2"
                >
                  {actionLoading ? (
                    <>
                      <FaSpinner className="animate-spin" />
                      Cambiando...
                    </>
                  ) : (
                    'Cambiar Contraseña'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      
      {/* ISS-SEC: Modal de confirmación en 2 pasos */}
      <TwoStepConfirmModal
        open={confirmState.isOpen}
        title={confirmState.title}
        message={confirmState.message}
        warnings={confirmState.warnings}
        confirmText={confirmState.confirmText}
        cancelText={confirmState.cancelText}
        tone={confirmState.tone}
        confirmPhrase={confirmState.confirmPhrase}
        itemInfo={confirmState.itemInfo}
        loading={confirmState.loading}
        onConfirm={executeWithConfirmation}
        onCancel={cancelConfirmation}
      />
    </div>
  );
}

export default Usuarios;







