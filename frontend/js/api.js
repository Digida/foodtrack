const API_BASE = '/api/v1';

async function api(method, path, body = null, retried = false) {
  const headers = {};
  const token = localStorage.getItem('ft_token');
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (body) headers['Content-Type'] = 'application/json';
  try {
    const res = await fetch(`${API_BASE}${path}`, { method, headers, body: body ? JSON.stringify(body) : null });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw { status: res.status, message: data.detail || 'Request failed' };
    return data;
  } catch (err) {
    // Access token expired → try a single refresh, then retry once.
    if (err.status === 401 && !retried && path !== '/auth/refresh') {
      const refreshed = await Auth.refreshSession();
      if (refreshed) return api(method, path, body, true);
    }
    if (err.status === 401) Auth.logout();
    throw err;
  }
}

const API = {
  get: p => api('GET', p),
  post: (p, b) => api('POST', p, b),
  put: (p, b) => api('PUT', p, b),
  patch: (p, b) => api('PATCH', p, b),
  del: p => api('DELETE', p),
};
