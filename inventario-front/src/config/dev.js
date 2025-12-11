const devButtonFlag = (import.meta.env?.VITE_SHOW_DEV_LOGIN || '').toLowerCase() === 'true';
const devEndpointFlag = (import.meta.env?.VITE_ENABLE_DEV_LOGIN || '').toLowerCase() === 'true';
const mockFlag = (import.meta.env?.VITE_USE_MOCK_DATA || '').toLowerCase() === 'true';
const testButtonsFlag = (import.meta.env?.VITE_SHOW_TEST_USER_BUTTONS || '').toLowerCase() === 'true';
const isDevEnv = (import.meta.env?.MODE || '').toLowerCase() === 'development';

export const DEV_CONFIG = {
  // Fallback a entorno de desarrollo para no depender de que el flag exista en local.
  SHOW_BUTTON: devEndpointFlag || devButtonFlag || isDevEnv,
  ENABLED: devEndpointFlag || isDevEnv,
  MOCKS_ENABLED: mockFlag,
  SHOW_TEST_BUTTONS: testButtonsFlag || isDevEnv,
  IS_DEV_ENV: isDevEnv,
};

export const devLog = (message, data = null) => {
  if (isDevEnv) {
    console.info(`[DEV] ${message}`, data ?? '');
  }
};

export const devWarn = (message, data = null) => {
  if (isDevEnv) {
    console.warn(`[DEV] ${message}`, data ?? '');
  }
};

export const devError = (message, data = null) => {
  if (isDevEnv) {
    console.error(`[DEV] ${message}`, data ?? '');
  }
};
