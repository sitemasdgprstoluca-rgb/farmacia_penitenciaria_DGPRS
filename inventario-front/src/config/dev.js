const isDevEnv = Boolean(import.meta.env?.DEV);
const devButtonFlag = (import.meta.env?.VITE_SHOW_DEV_LOGIN || '').toLowerCase() === 'true';
const devEndpointFlag = (import.meta.env?.VITE_ENABLE_DEV_LOGIN || '').toLowerCase() === 'true';

const devEnabled = isDevEnv || devEndpointFlag;

export const DEV_CONFIG = {
  SHOW_BUTTON: devEnabled || devButtonFlag,
  ENABLED: devEnabled,
};

export const devLog = (message, data = null) => {
  if (isDevEnv) {
    console.info(`[DEV] ${message}`, data ?? '');
  }
};
