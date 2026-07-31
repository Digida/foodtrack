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
    const data = await API.post('/auth/mfa-verify', { temp_token: tempToken, code });
    Auth.setSession(data.access_token, data.user);
  },

  async register(email, password, fullName, company, phone) {
    const data = await API.post('/auth/register', { email, password, full_name: fullName, company, phone });
    Auth.setSession(data.access_token, data.user);
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

  async ssoLogin(provider, token) {
    const data = await API.post('/auth/sso', { provider, token });
    Auth.setSession(data.access_token, data.user);
  },
};
