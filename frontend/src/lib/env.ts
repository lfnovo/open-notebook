const defaultBaseUrl = 'http://127.0.0.1:5055/api';

export const getApiBaseUrl = () => {
  const fromEnv = import.meta.env.VITE_API_BASE_URL;
  return typeof fromEnv === 'string' && fromEnv.length > 0 ? fromEnv : defaultBaseUrl;
};

export const getWebsocketBaseUrl = () => {
  const base = getApiBaseUrl();
  if (base.startsWith('http')) {
    return base.replace('http', 'ws');
  }
  return base;
};
