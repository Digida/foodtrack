const Auth = {
  isLoggedIn: () => !!localStorage.getItem('ft_token'),
  getUser: () => { const r = localStorage.getItem('ft_user'); return r ? JSON.parse(r) : null; },
  getToken: () => localStorage.getItem('ft_token'),
  getRefreshToken: () => localStorage.getItem('ft_refresh'),
  setSession: (token, user, refreshToken) => {
    localStorage.setItem('ft_token', token);
    if (refreshToken) localStorage.setItem('ft_refresh', refreshToken);
    if (user) localStorage.setItem('ft_user', JSON.stringify(user));
  },
  clearSession: () => {
    localStorage.removeItem('ft_token');
    localStorage.removeItem('ft_refresh');
    localStorage.removeItem('ft_user');
  },
  logout: async () => {
    const refresh = Auth.getRefreshToken();
    const token = Auth.getToken();
    try {
      if (refresh) {
        const headers = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;
        await fetch(`${API_BASE}/auth/logout`, { method: 'POST', headers, body: JSON.stringify({ refresh_token: refresh }) });
      }
    } catch (_) { /* ignore — always clear locally */ }
    Auth.clearSession();
    window.location.hash = '#login';
  },

  // Exchange a stored refresh token for a new token pair. Returns true on success.
  async refreshSession() {
    const refresh = Auth.getRefreshToken();
    if (!refresh) return false;
    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!res.ok) { Auth.clearSession(); return false; }
      const data = await res.json();
      Auth.setSession(data.access_token, data.user, data.refresh_token);
      return true;
    } catch (_) {
      Auth.clearSession();
      return false;
    }
  },

  async login(email, password) {
    const data = await API.post('/auth/login', { email, password });
    if (data.requires_mfa) return data;
    Auth.setSession(data.access_token, data.user, data.refresh_token);
    return null;
  },

  async verifyMfa(tempToken, code) {
    const data = await API.post('/auth/mfa-verify', { temp_token: tempToken, code });
    Auth.setSession(data.access_token, data.user, data.refresh_token);
  },

  async register(email, password, fullName, company, phone) {
    const data = await API.post('/auth/register', { email, password, full_name: fullName, company, phone });
    Auth.setSession(data.access_token, data.user, data.refresh_token);
  },

  async requestEmailOtp() {
    return await API.post('/auth/email-otp');
  },

  async verifyEmail(code) {
    return await API.post('/auth/verify-email', { code });
  },

  async requestPhoneOtp() {
    return await API.post('/auth/phone-otp');
  },

  async verifyPhone(code) {
    return await API.post('/auth/verify-phone', { code });
  },

  async getSsoProviders() {
    try {
      const data = await API.get('/auth/sso-providers');
      return data.providers || [];
    } catch (e) {
      return [];
    }
  },

  // PKCE authorization-code flow: ask the backend for the provider authorize
  // URL (it signs the state JWT carrying the PKCE verifier), then redirect.
  async ssoAuthorize(provider) {
    const data = await API.get(`/auth/sso/${provider}/authorize`);
    if (!data.authorize_url) throw new Error('SSO authorization unavailable');
    window.location.href = data.authorize_url;
  },

  // Server-side callback flow: the backend redirects to sso.html with
  // #access_token=...&refresh_token=... after exchanging the code + PKCE.
  // Store the pair and fetch the fresh user profile.
  completeSsoTokens() {
    const params = new URLSearchParams(window.location.hash.replace(/^#/, ''));
    const token = params.get('access_token');
    const refresh = params.get('refresh_token');
    if (!token) return false;
    Auth.setSession(token, Auth.getUser(), refresh);
    API.get('/auth/me').then(user => {
      Auth.setSession(token, user, refresh);
      window.location.replace('index.html#dashboard');
    }).catch(() => {
      window.location.replace('index.html#dashboard');
    });
    return true;
  },

  // Legacy implicit-flow entry point (client-side authorize URL).
  async ssoLogin(provider, token) {
    const data = await API.post('/auth/sso', { provider, token });
    Auth.setSession(data.access_token, data.user, data.refresh_token);
  },
};
