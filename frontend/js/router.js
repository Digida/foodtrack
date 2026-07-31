const Router = {
  routes: {},
  add: (pattern, handler) => { Router.routes[pattern] = handler; },

  navigate(path) {
    const hash = path.startsWith('#') ? path : '#' + path;
    if (window.location.hash === hash) this.resolve();
    else window.location.hash = hash;
  },

  init() {
    window.addEventListener('hashchange', () => this.resolve());
    if (!window.location.hash || window.location.hash === '#') {
      window.location.hash = Auth.isLoggedIn() ? '#dashboard' : '#home';
    }
    this.resolve();
  },

  resolve() {
    const hash = window.location.hash || '#home';
    const path = hash.slice(1).split('?')[0];
    const params = {};
    const qs = hash.slice(1).split('?')[1];
    if (qs) qs.split('&').forEach(p => { const [k, v] = p.split('='); params[k] = decodeURIComponent(v || ''); });
    const app = document.getElementById('app');
    for (const [pattern, handler] of Object.entries(this.routes)) {
      const regex = new RegExp('^' + pattern.replace(/:\w+/g, '([^/]+)') + '$');
      const match = path.match(regex);
      if (match) {
        app.innerHTML = '<div class="spinner" style="margin:80px auto"></div>';
        handler(app, ...match.slice(1), params);
        return;
      }
    }
    app.innerHTML = '<div class="empty-state" style="margin:80px auto"><h3>Page not found</h3><p style="color:#6b7280;margin-top:8px"><a href="#home">Go home</a></p></div>';
  },
};
