const isDevEnv = Boolean(import.meta.env?.DEV);
const envDevFlag = (import.meta.env?.VITE_ENABLE_DEV_LOGIN || '').toLowerCase();
const DEV_LOGIN_ENABLED = isDevEnv && (envDevFlag === '' || envDevFlag === 'true');

const DEV_DEFAULT_USERNAME = import.meta.env?.VITE_DEV_USERNAME || 'admin';
const DEV_DEFAULT_PASSWORD = import.meta.env?.VITE_DEV_PASSWORD || 'admin123';

const DEV_USER = {
  id: 1,
  username: 'admin',
  first_name: 'Administrador',
  last_name: 'Penitenciario',
  email: 'admin@edomex.gob.mx',
  is_superuser: true,
  is_staff: true,
  is_active: true,
  grupos: ['FARMACIA_ADMIN'],
  centro: {
    id: 1,
    nombre: 'Oficina Central',
  },
};

export const DEV_CONFIG = {
  ENABLED: DEV_LOGIN_ENABLED,
  AUTO_USER: DEV_USER,
  CREDENTIALS: {
    username: DEV_DEFAULT_USERNAME,
    password: DEV_DEFAULT_PASSWORD,
  },
  DEBUG: DEV_LOGIN_ENABLED,
  SKIP_VALIDATION: DEV_LOGIN_ENABLED,
};

export const devLog = (message, data = null) => {
  if (DEV_CONFIG.DEBUG) {
    console.info(`[DEV] ${message}`, data ?? '');
  }
};
