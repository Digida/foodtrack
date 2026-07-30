const Auth = {
  isLoggedIn: () => !!localStorage.getItem('ft_token'),
  getUser: () => { const r = localStorage.getItem('ft_user'); return r ? JSON.parse(r) : null; },
  setSession: (token, user) => { localStorage.setItem('ft_token', token); localStorage.setItem('ft_user', JSON.stringify(user)); },
  clearSession: () => { localStorage.removeItem('ft_token'); localStorage.removeItem('ft_user'); },
  logout: () => { Auth.clearSession(); window.location.hash = '#login'; },

  async login(email, password) {
    const data = await API.post('/auth/login', { email, password });
    if (data.requires_mfa) return data;
    Auth.setSession(data.access_token, data.user);
    return null;
  },

  async verifyMfa(tempToken, code) {
    const data = await API.post('/auth/mfa/verify', { temp_token: tempToken, code });
    Auth.setSession(data.access_token, data.user);
  },

  async register(email, password, fullName, company, phone) {
    const data = await API.post('/auth/register', { email, password, full_name: fullName, company, phone });
    Auth.setSession(data.access_token, data.user);
  },
};
