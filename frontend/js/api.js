const API_BASE = '/api/v1';

async function api(method, path, body = null) {
  const headers = {};
  const token = localStorage.getItem('ft_token');
  if (token) headers['Authorization'] = `Bearer ${token}`;
  headers['Content-Type'] = 'application/json';
  try {
    const res = await fetch(`${API_BASE}${path}`, { method, headers, body: body ? JSON.stringify(body) : null });
    const data = await res.json();
    if (!res.ok) throw { status: res.status, message: data.detail || 'Request failed' };
    return data;
  } catch (err) {
    if (err.status === 401) { Auth.logout(); throw err; }
    throw err;
  }
}

const API = {
  get: p => api('GET', p),
  post: (p, b) => api('POST', p, b),
  put: (p, b) => api('PUT', p, b),
  del: p => api('DELETE', p),
};
