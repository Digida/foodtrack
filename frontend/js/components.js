const UI = {
  el: (tag, attrs = {}, ...children) => {
    const el = document.createElement(tag);
    Object.entries(attrs).forEach(([k, v]) => {
      if (k === 'className') el.className = v;
      else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
      else if (k.startsWith('on')) el.addEventListener(k.slice(2).toLowerCase(), v);
      else if (k === 'html') el.innerHTML = v;
      else el.setAttribute(k, v);
    });
    const flat = children.flat(Infinity).filter(c => c != null);
    flat.forEach(c => el.appendChild(typeof c === 'string' ? document.createTextNode(c) : c));
    return el;
  },

  card: (title, body, actions = null) => {
    const c = UI.el('div', { className: 'card' });
    if (title) {
      c.appendChild(UI.el('div', { className: 'card-header' }, UI.el('h3', {}, title), actions || ''));
    }
    if (typeof body === 'string') c.insertAdjacentHTML('beforeend', body);
    else c.appendChild(body);
    return c;
  },

  statCard: (value, label) =>
    UI.el('div', { className: 'card stat-card' }, UI.el('div', { className: 'stat-value' }, String(value)), UI.el('div', { className: 'stat-label' }, label)),

  badge: (text, cls = 'badge-secondary') => UI.el('span', { className: `badge ${cls}` }, text),

  btn: (text, cls, onClick) => UI.el('button', { className: `btn ${cls}`, onClick }, text),

  input: (type, id, opts = {}) => UI.el('input', { type, id, placeholder: opts.placeholder || '', value: opts.value || '' }),

  modal: (title, content, onClose) => {
    const overlay = UI.el('div', { className: 'modal-overlay' });
    const modal = UI.el('div', { className: 'modal' }, UI.el('h3', {}, title),
      typeof content === 'string' ? (() => { const d = document.createElement('div'); d.innerHTML = content; return d; })() : content);
    overlay.appendChild(modal);
    const actionsDiv = UI.el('div', { className: 'modal-actions' });
    modal.appendChild(actionsDiv);
    overlay.addEventListener('click', e => { if (e.target === overlay) { overlay.remove(); onClose?.(); } });
    document.body.appendChild(overlay);
    return { overlay, close: () => { overlay.remove(); onClose?.(); }, actions: actionsDiv };
  },

  toast: (msg, type = 'error') => {
    const container = document.getElementById('toast-container') || (() => {
      const c = document.createElement('div');
      c.id = 'toast-container';
      c.style.cssText = 'position:fixed;top:16px;right:16px;z-index:9999;display:flex;flex-direction:column;gap:8px';
      document.body.appendChild(c);
      return c;
    })();
    const div = document.createElement('div');
    div.className = `toast toast-${type}`;
    div.textContent = msg;
    div.style.position = 'relative';
    container.appendChild(div);
    div.addEventListener('click', () => {
      div.classList.add('toast-out');
      setTimeout(() => div.remove(), 300);
    });
    setTimeout(() => {
      div.classList.add('toast-out');
      setTimeout(() => div.remove(), 300);
    }, 4000);
  },

  showError: msg => UI.toast(msg, 'error'),
  showSuccess: msg => UI.toast(msg, 'success'),

  exportCSV: (data, labelKey, valueKey, filename) => {
    let csv = labelKey + ',' + valueKey + '\n';
    data.forEach(i => { csv += i[labelKey] + ',' + i[valueKey] + '\n'; });
    const blob = new Blob([csv], { type: 'text/csv' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = filename;
    document.body.appendChild(a); a.click();
    setTimeout(() => { document.body.removeChild(a); URL.revokeObjectURL(a.href); }, 100);
    UI.showSuccess('Downloaded ' + filename);
  },

  confirm: (title, message) => {
    return new Promise(resolve => {
      const m = UI.modal(title, `<p>${message}</p>`);
      m.actions.appendChild(UI.btn('Cancel', 'btn-outline', () => { m.close(); resolve(false); }));
      m.actions.appendChild(UI.btn('Confirm', 'btn-danger', () => { m.close(); resolve(true); }));
    });
  },

  validateForm: (rules) => {
    let valid = true;
    const firstInvalid = [];
    document.querySelectorAll('.field-error').forEach(e => e.remove());
    document.querySelectorAll('.input-error').forEach(e => e.classList.remove('input-error'));
    Object.entries(rules).forEach(([id, rule]) => {
      const el = document.getElementById(id);
      if (!el) return;
      const val = el.value.trim();
      const errs = [];
      if (rule.required && !val) errs.push(rule.message || 'Required');
      if (rule.minLength && val.length < rule.minLength) errs.push(`Minimum ${rule.minLength} characters`);
      if (rule.maxLength && val.length > rule.maxLength) errs.push(`Maximum ${rule.maxLength} characters`);
      if (rule.pattern && val && !rule.pattern.test(val)) errs.push(rule.message || 'Invalid format');
      if (rule.match && val !== document.getElementById(rule.match)?.value) errs.push(rule.message || 'Does not match');
      if (rule.type === 'email' && val && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val)) errs.push('Invalid email address');
      if (rule.type === 'tel' && val && !/^[\d\s\-\+\(\)]{7,20}$/.test(val)) errs.push('Invalid phone number');
      if (errs.length > 0) {
        valid = false;
        el.classList.add('input-error');
        const errEl = document.createElement('div');
        errEl.className = 'field-error';
        errEl.textContent = errs[0];
        el.parentNode.appendChild(errEl);
        if (!firstInvalid.length) firstInvalid.push(el);
      }
    });
    if (firstInvalid.length) firstInvalid[0].focus();
    return valid;
  },

  /**
   * Build an autocomplete-enabled search input.
   * @param {string} placeholder - input placeholder text
   * @param {string} searchRoute - base route to navigate on submit (e.g. '#search')
   * @returns {HTMLElement} wrapper containing input + dropdown
   */
  autocompleteSearchInput: (placeholder, searchRoute = '#search') => {
    const wrapper = UI.el('div', { className: 'autocomplete-wrap', style: 'flex:1;max-width:400px' });
    const input = UI.el('input', {
      type: 'text', placeholder: placeholder || 'Search...',
      style: 'width:100%;padding:8px 14px;border:1px solid var(--border);border-radius:var(--radius);font-size:14px;background:var(--bg);color:var(--text)',
    });
    const dropdown = UI.el('div', { className: 'autocomplete-dropdown' });
    wrapper.appendChild(input);
    wrapper.appendChild(dropdown);

    let acTimeout = null;
    let acSelectedIndex = -1;
    let acResults = [];
    let acIgnoreNext = false;

    const closeDropdown = () => {
      dropdown.classList.remove('open');
      dropdown.innerHTML = '';
      acSelectedIndex = -1;
      acResults = [];
    };

    input.addEventListener('input', () => {
      clearTimeout(acTimeout);
      const val = input.value.trim();
      if (val.length < 2) { closeDropdown(); return; }
      acTimeout = setTimeout(async () => {
        try {
          const data = await API.get(`/search/autocomplete?q=${encodeURIComponent(val)}&limit=8`);
          acResults = data.results || [];
          if (acResults.length === 0) { closeDropdown(); return; }
          dropdown.innerHTML = acResults.map((r, i) => {
            const iconClass = r.type === 'taxonomy_item' ? 'ac-icon-taxonomy' : r.type === 'product' ? 'ac-icon-product' : 'ac-icon-batch';
            const iconChar = r.type === 'taxonomy_item' ? '🌿' : r.type === 'product' ? '📦' : '🏷️';
            return `<div class="autocomplete-item" data-index="${i}" data-url="${r.url}">
              <div class="ac-icon ${iconClass}">${iconChar}</div>
              <div><div class="ac-label">${r.label}</div><div class="ac-sub">${r.subtitle || ''}</div></div>
            </div>`;
          }).join('');
          dropdown.classList.add('open');
          acSelectedIndex = -1;
          highlightItem(acSelectedIndex);
        } catch (e) { /* silent fail for autocomplete */ }
      }, 250);
    });

    const highlightItem = (idx) => {
      dropdown.querySelectorAll('.autocomplete-item').forEach((el, i) => {
        el.classList.toggle('highlighted', i === idx);
      });
    };

    input.addEventListener('keydown', (e) => {
      const items = dropdown.querySelectorAll('.autocomplete-item');
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        acSelectedIndex = Math.min(acSelectedIndex + 1, items.length - 1);
        highlightItem(acSelectedIndex);
        if (items[acSelectedIndex]) items[acSelectedIndex].scrollIntoView({ block: 'nearest' });
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        acSelectedIndex = Math.max(acSelectedIndex - 1, -1);
        highlightItem(acSelectedIndex);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (acSelectedIndex >= 0 && acResults[acSelectedIndex]) {
          closeDropdown();
          input.blur();
          Router.navigate(acResults[acSelectedIndex].url);
        } else {
          const val = input.value.trim();
          if (val) {
            closeDropdown();
            input.blur();
            Router.navigate(`${searchRoute}/${encodeURIComponent(val)}`);
          }
        }
      } else if (e.key === 'Escape') {
        closeDropdown();
      }
    });

    input.addEventListener('blur', () => {
      setTimeout(closeDropdown, 200);
    });

    // Allow clicking dropdown items
    dropdown.addEventListener('mousedown', (e) => {
      const item = e.target.closest('.autocomplete-item');
      if (item) {
        e.preventDefault();
        acIgnoreNext = true;
        const url = item.dataset.url;
        closeDropdown();
        input.blur();
        Router.navigate(url);
      }
    });

    return wrapper;
  },

  buildMainNav: () => {
    const curHash = window.location.hash || '#home';
    const loggedIn = Auth.isLoggedIn();
    const isActive = (href) => curHash === href ? 'active' : '';
    const toggle = UI.el('button', { className: 'pub-toggle', html: '&#9776;' });
    const searchInput = UI.autocompleteSearchInput('Search items, products, batches...', '#search');
    searchInput.querySelector('input').style.padding = '6px 12px';
    searchInput.querySelector('input').style.fontSize = '13px';
    const nav = UI.el('nav', { className: 'pub-nav' },
      UI.el('a', { href: '#home', className: 'pub-logo' }, 'Food', UI.el('span', {}, 'Track')),
      UI.el('div', { className: 'pub-links' },
        UI.el('a', { href: '#home', className: 'pub-link ' + isActive('#home') }, 'Home'),
        UI.el('a', { href: '#search', className: 'pub-link ' + (curHash.startsWith('#search') ? 'active' : '') }, 'Search'),
        UI.el('a', { href: '#food-items', className: 'pub-link ' + (curHash.startsWith('#food-items') || curHash.startsWith('#food-item') ? 'active' : '') }, 'Food Items'),
        ...(loggedIn ? [
          UI.el('a', { href: '#verify', className: 'pub-link ' + isActive('#verify') }, 'Verify'),
          UI.el('a', { href: '#cargo-tracking', className: 'pub-link ' + (curHash.startsWith('#cargo-tracking') ? 'active' : '') }, 'Cargo Tracking'),
        ] : []),
        UI.el('a', { href: '#about', className: 'pub-link ' + isActive('#about') }, 'About'),
        UI.el('a', { href: '#contact', className: 'pub-link ' + isActive('#contact') }, 'Contact'),
      ),
      searchInput,
      UI.el('div', { className: 'pub-auth' },
        loggedIn
          ? UI.btn('Dashboard', 'btn-primary btn-sm', () => Router.navigate('#dashboard'))
          : [UI.btn('Login', 'btn-outline btn-sm', () => Router.navigate('#login')),
             UI.btn('Get Started', 'btn-primary btn-sm', () => Router.navigate('#login'))]
      ),
      toggle
    );
    toggle.addEventListener('click', () => {
      document.querySelector('.pub-links').classList.toggle('open');
      document.querySelector('.pub-auth').classList.toggle('open');
    });
    if (UI._navCloseHandler) window.removeEventListener('hashchange', UI._navCloseHandler);
    UI._navCloseHandler = () => {
      document.querySelector('.pub-links')?.classList.remove('open');
      document.querySelector('.pub-auth')?.classList.remove('open');
    };
    window.addEventListener('hashchange', UI._navCloseHandler);
    return nav;
  },

  buildSidebar: () => {
    const user = Auth.getUser();
    const loggedIn = Auth.isLoggedIn();
    const nav = [
      { icon: '\u{1F4CA}', label: 'Dashboard', href: '#dashboard' },
      { icon: '\u{1F50D}', label: 'Search', href: '#search' },
      { icon: '\u{1F33E}', label: 'Food Items', href: '#food-items' },
      { icon: '\u{1F4E6}', label: 'Products', href: '#products' },
      { icon: '\u{1F50D}', label: 'Traceability', href: '#traceability' },
      { icon: '\u{1F4DC}', label: 'Certificates', href: '#certificates' },
      { icon: '\u{1F4C8}', label: 'Analytics', href: '#analytics' },
      { icon: '\u{1F4E4}', label: 'Share', href: '#share' },
      { icon: '\u{1FAB4}', label: 'Taxonomy', href: '#taxonomy' },
      { icon: '\u{1F9F1}', label: 'Batches', href: '#batches', loginOnly: true },
      { icon: '\u{1F3E2}', label: 'Warehouses', href: '#warehouses' },
      { icon: '\u{1F6A2}', label: 'Shipments', href: '#shipments' },
      { icon: '\u{1F69A}', label: 'Cargo Tracking', href: '#cargo-tracking', loginOnly: true },
      { icon: '\u{1F4E6}', label: 'Collections', href: '#collections' },
      { icon: '\u{2699}\uFE0F', label: 'Settings', href: '#settings' },
    ].filter(item => !item.loginOnly || loggedIn);
    const curHash = window.location.hash;
    const isActive = (href) => curHash.startsWith(href) || (href === '#food-items' && curHash.startsWith('#food-item'));
    return UI.el('aside', { className: 'sidebar sidebar-collapsed' },
      UI.el('div', { className: 'sidebar-brand' },
        UI.el('span', { className: 'brand-mark' }, '🌿'),
        UI.el('span', { className: 'brand-text' }, 'Food', UI.el('span', {}, 'Track'))
      ),
      UI.el('div', { className: 'sidebar-nav' },
        ...nav.map(item =>
          UI.el('a', { href: item.href, className: 'sidebar-link ' + (isActive(item.href) ? 'active' : '') },
            UI.el('span', { className: 'icon' }, item.icon),
            UI.el('span', { className: 'label' }, item.label)
          )
        )
      ),
      UI.el('div', { className: 'sidebar-footer' },
        UI.el('div', { className: 'sidebar-user' }, loggedIn ? (user?.full_name || user?.name || '') : 'Guest'),
        loggedIn
          ? UI.btn('Logout', 'btn-outline btn-sm', () => Auth.logout())
          : UI.btn('Login', 'btn-primary btn-sm', () => Router.navigate('#login'))
      )
    );
  },

  publicLayout: (bodyFn) => {
    const loggedIn = Auth.isLoggedIn();
    const content = UI.el('div', { className: 'pub-content' });
    const footer = UI.el('footer', { className: 'pub-footer' },
      UI.el('div', { className: 'footer-inner' },
        UI.el('div', {}, '\u00a9 2026 FoodTrack. All rights reserved.'),
        UI.el('div', { className: 'footer-links' },
          UI.el('a', { href: '#home' }, 'Home'),
          ...(loggedIn ? [UI.el('a', { href: '#verify' }, 'Verify')] : []),
          UI.el('a', { href: '#about' }, 'About'),
          UI.el('a', { href: '#contact' }, 'Contact'),
        )
      )
    );
    const wrapper = UI.el('div', { className: 'app-shell' },
      UI.buildMainNav(),
      UI.el('div', { className: 'app-body' },
        UI.buildSidebar(),
        UI.el('div', { className: 'main-content' }, content)
      ),
      footer
    );
    requestAnimationFrame(() => {
      const r = bodyFn();
      if (r && typeof r.then === 'function') {
        content.innerHTML = '<div class="spinner" style="margin:80px auto"></div>';
        r.then(h => { content.innerHTML = ''; content.appendChild(h); }).catch(e => { content.innerHTML = `<div class="empty-state" style="margin:80px auto"><p>Error: ${e.message}</p></div>`; });
      } else if (r) content.appendChild(r);
    });
    return wrapper;
  },

  layout: (title, bodyFn) => {
    const toggleSidebar = () => {
      document.querySelector('.sidebar')?.classList.toggle('open');
      document.querySelector('.sidebar-overlay')?.classList.toggle('open');
    };
    const header = UI.el('div', { className: 'topbar' },
      UI.el('button', { className: 'mobile-toggle', html: '&#9776;', onClick: toggleSidebar }),
      UI.el('h2', {}, title || 'FoodTrack'),
      UI.el('div', { id: 'topbar-search', className: 'topbar-actions', style: 'flex:1;max-width:500px;display:flex;gap:6px;align-items:center' },
        UI.el('div', { style: 'flex:1;min-width:180px' }, UI.autocompleteSearchInput('Quick search items, batches...')),
        UI.btn('\u{1F50D}', 'btn-primary btn-sm', function() {
          const input = document.querySelector('#topbar-search input');
          if (input) { const v = input.value.trim(); if (v) Router.navigate('#search/' + encodeURIComponent(v)); }
        })
      ),
      UI.el('div', { id: 'topbar-actions', className: 'topbar-actions' })
    );
    const pageContent = UI.el('div', { className: 'page-content', id: 'page-content' });
    const main = UI.el('div', { className: 'main-content' }, header, pageContent);
    const wrapper = UI.el('div', { className: 'app-shell' },
      UI.buildMainNav(),
      UI.el('div', { className: 'app-body' },
        UI.buildSidebar(),
        main
      ),
      UI.el('div', { className: 'sidebar-overlay', onClick: toggleSidebar })
    );
    requestAnimationFrame(() => {
      const r = bodyFn();
      if (r && typeof r.then === 'function') {
        const content = document.getElementById('page-content');
        if (content) content.innerHTML = '<div class="spinner" style="margin:80px auto"></div>';
        Promise.resolve(r).then(h => {
          const content = document.getElementById('page-content');
          if (content) { content.innerHTML = ''; content.appendChild(h); }
        }).catch(e => {
          const content = document.getElementById('page-content');
          if (content) content.innerHTML = `<div class="empty-state" style="margin:80px auto"><p>Error: ${e.message}</p></div>`;
        });
      }
    });
    return wrapper;
  },
};
