/* ============================================================
   FoodTrack Frontend Pages — one function per route
   ============================================================ */

window.Pages = {};

// ─── SEO Helper used by page renderers ────────────────────────
function _setSEO(title, description, image) {
  if (window.SEO) {
    const url = window.location.origin + window.location.hash;
    SEO.setPage(title, description, url, image, null);
  }
}

function _getTypeBadge(type) {
  return { 'taxonomy_item': '🌿 Taxonomy', 'product': '📦 Product', 'batch': '🏷️ Batch', 'warehouse': '🏭 Warehouse', 'certificate': '📜 Certificate', 'collection': '📚 Collection' }[type] || type;
}

function _getScoreStars(score) {
  if (!score || score < 3) return '';
  if (score >= 9) return '⭐⭐⭐';
  if (score >= 6) return '⭐⭐';
  return '⭐';
}

function _buildModeSvg(mode) {
  const colors = { ferry: '#2196F3', courier: '#FF9800', truck: '#4CAF50', air: '#9C27B0', rail: '#795548', multimodal: '#607D8B' };
  const color = colors[mode] || '#6b7280';
  return `<span class="mode-icon"><span class="mi-dot" style="background:${color}"></span> ${mode}</span>`;
}

// ─── LANDING PAGE ─────────────────────────────────────────────

Pages.home = (app) => {
  app.appendChild(UI.publicLayout(() => {
    const wrapper = document.createElement('div');
    wrapper.innerHTML = `
      <section class="hero">
        <div class="hero-content">
          <h1>Digital Trust for<br>Your Food Supply Chain</h1>
          <p class="hero-sub">Blockchain-powered traceability, smart certification, and product integrity — built for the agrifood industry.</p>
          <div class="hero-actions">
            <a href="#login" class="btn btn-primary btn-lg">Get Started</a>
            <a href="#about" class="btn btn-outline btn-lg">Learn More</a>
          </div>
          <div class="hero-stats">
            <div class="hero-stat"><span class="hs-num">10,000+</span><span class="hs-label">Products Traced</span></div>
            <div class="hero-stat"><span class="hs-num">5,000+</span><span class="hs-label">Certificates Issued</span></div>
            <div class="hero-stat"><span class="hs-num">50+</span><span class="hs-label">Countries</span></div>
          </div>
        </div>
      </section>
      <section class="section features">
        <div class="section-inner">
          <h2>Everything You Need</h2>
          <p class="section-sub">From farm to fork, FoodTrack gives you full visibility and control.</p>
          <div class="features-grid">
            <div class="feature-card">
              <div class="feature-icon">\u{1F50D}</div>
              <h3>Traceability</h3>
              <p>End-to-end supply chain tracking with immutable event timelines. Scan, log, and follow every step.</p>
            </div>
            <div class="feature-card">
              <div class="feature-icon">\u{1F4DC}</div>
              <h3>Smart Certifications</h3>
              <p>Issue and verify digital certificates — Origin, Organic, Halal, Safety, and more — with one click.</p>
            </div>
            <div class="feature-card">
              <div class="feature-icon">\u{1F4CA}</div>
              <h3>Analytics & Reports</h3>
              <p>Real-time dashboards, category breakdowns, and CSV exports to inform your decisions.</p>
            </div>
            <div class="feature-card">
              <div class="feature-icon">\u{1F4E4}</div>
              <h3>Share & Compare</h3>
              <p>Generate shareable product links, QR codes, and peer benchmarking for buyer confidence.</p>
            </div>
            <div class="feature-card">
              <div class="feature-icon">\u{1F9F1}</div>
              <h3>QR & Barcode Scanner</h3>
              <p>Native camera scanning with automatic fallback. Decode and look up products in seconds.</p>
            </div>
            <div class="feature-card">
              <div class="feature-icon">\u{1F512}</div>
              <h3>Secure & Compliant</h3>
              <p>Multi-factor authentication, role-based access, and audit-ready data for regulatory compliance.</p>
            </div>
          </div>
        </div>
      </section>
      <section class="section how-it-works" style="background:var(--bg-card)">
        <div class="section-inner">
          <h2>How It Works</h2>
          <p class="section-sub">Three simple steps to full supply chain integrity.</p>
          <div class="steps">
            <div class="step"><div class="step-num">1</div><h3>Register & Onboard</h3><p>Create your account, set up your company profile, and start adding products to the platform.</p></div>
            <div class="step"><div class="step-num">2</div><h3>Track & Certify</h3><p>Log supply chain events, issue digital certificates, and generate traceability records for every product.</p></div>
            <div class="step"><div class="step-num">3</div><h3>Share & Prove</h3><p>Share product profiles with QR codes, compare against peers, and build trust with buyers and regulators.</p></div>
          </div>
        </div>
      </section>
      <section class="section cta">
        <div class="section-inner">
          <h2>Ready to Build Trust in Your Supply Chain?</h2>
          <p>Join thousands of producers, certifiers, and buyers using FoodTrack every day.</p>
          <a href="#login" class="btn btn-primary btn-lg">Get Started Free</a>
        </div>
      </section>`;
    return wrapper;
  }));
};

// ─── ABOUT PAGE ────────────────────────────────────────────────

Pages.about = (app) => {
  app.appendChild(UI.publicLayout(() => {
    const wrapper = document.createElement('div');
    wrapper.innerHTML = `
      <section class="page-header">
        <div class="section-inner">
          <h1>About FoodTrack</h1>
          <p>Building the phygital infrastructure for the future of food.</p>
        </div>
      </section>
      <section class="section">
        <div class="section-inner" style="max-width:720px">
          <h2>Our Mission</h2>
          <p style="line-height:1.8;color:var(--text-light);font-size:16px">FoodTrack is a digital trust infrastructure platform that combines traceability, smart certification, and product integrity for agrifood supply chains. We enable producers, certifiers, and buyers to interact through a transparent, verifiable, and efficient digital layer.</p>
          <p style="line-height:1.8;color:var(--text-light);font-size:16px;margin-top:16px">Headquartered in Dubai, we are focused on serving the UAE and broader MENA region, with a phased approach to global commercialization.</p>
          <h2 style="margin-top:40px">Why FoodTrack</h2>
          <p style="line-height:1.8;color:var(--text-light);font-size:16px">Food fraud costs the global food industry an estimated $40 billion annually. Consumers and regulators increasingly demand transparency. FoodTrack bridges the gap between physical products and digital trust — making every step of the supply chain visible and verifiable.</p>
        </div>
      </section>
      <section class="section" style="background:var(--bg-card)">
        <div class="section-inner" style="max-width:720px">
          <h2>Key Features</h2>
          <ul style="line-height:2;font-size:16px;color:var(--text-light)">
            <li>End-to-end product traceability with immutable event logs</li>
            <li>Digital certification issuing and verification</li>
            <li>QR code and barcode scanning for instant product lookup</li>
            <li>Peer comparison and benchmarking</li>
            <li>Real-time analytics and CSV export</li>
            <li>Multi-factor authentication and role-based access control</li>
          </ul>
        </div>
      </section>`;
    return wrapper;
  }));
};

// ─── CONTACT PAGE ──────────────────────────────────────────────

Pages.contact = (app) => {
  app.appendChild(UI.publicLayout(() => {
    const wrapper = document.createElement('div');
    wrapper.innerHTML = `
      <section class="page-header">
        <div class="section-inner">
          <h1>Contact Us</h1>
          <p>Have a question or want to learn more? Get in touch.</p>
        </div>
      </section>
      <section class="section">
        <div class="section-inner" style="max-width:600px">
          <div id="contact-form">
            <div class="form-group"><label>Name</label><input id="c-name" class="fi" placeholder="Your name"></div>
            <div class="form-group"><label>Email</label><input id="c-email" class="fi" type="email" placeholder="you@example.com"></div>
            <div class="form-group"><label>Subject</label><input id="c-subject" class="fi" placeholder="What is this about?"></div>
            <div class="form-group"><label>Message</label><textarea id="c-msg" class="fi" rows="5" placeholder="Tell us more..."></textarea></div>
            <button class="btn btn-primary btn-block" id="c-btn">Send Message</button>
          </div>
          <div id="contact-success" style="display:none;text-align:center;padding:40px 0">
            <div style="font-size:48px;margin-bottom:16px">\u2709\uFE0F</div>
            <h3>Message Sent!</h3>
            <p style="color:var(--text-light);margin-top:8px">Thank you for reaching out. We will get back to you shortly.</p>
            <a href="#home" class="btn btn-outline" style="margin-top:16px">Back to Home</a>
          </div>
        </div>
      </section>`;
    wrapper.querySelector('#c-btn').onclick = async () => {
      if (!UI.validateForm({
        'c-name': { required: true, message: 'Name required' },
        'c-email': { required: true, type: 'email' },
        'c-subject': { required: true, message: 'Subject required' },
        'c-msg': { required: true, minLength: 10, message: 'Message must be at least 10 characters' },
      })) return;
      try {
        await API.post('/contact', {
          name: document.getElementById('c-name').value,
          email: document.getElementById('c-email').value,
          subject: document.getElementById('c-subject').value,
          message: document.getElementById('c-msg').value,
        });
        document.getElementById('contact-form').style.display = 'none';
        document.getElementById('contact-success').style.display = 'block';
      } catch (e) { UI.showError(e.message); }
    };
    return wrapper;
  }));
};

// ─── PUBLIC VERIFY PAGE ────────────────────────────────────────

Pages.verify = (app) => {
  app.appendChild(UI.publicLayout(() => {
    const wrapper = document.createElement('div');
    wrapper.innerHTML = `
      <section class="page-header">
        <div class="section-inner">
          <h1>Verify a Product or Certificate</h1>
          <p>Scan a QR/barcode or enter a product SKU or certificate ID.</p>
        </div>
      </section>
      <section class="section">
        <div class="section-inner" style="max-width:600px">
          <input id="v-q" class="fi" placeholder="Enter product SKU or certificate ID..." style="max-width:400px">
          <button class="btn btn-primary" id="v-btn" style="margin-top:8px">Look Up</button>
          <div id="v-result" style="margin-top:24px"></div>
          <hr style="margin:32px 0;border:none;border-top:1px solid var(--border)">
          <h3>Scan with Camera</h3>
          <div class="scanner-container" id="scanner-box">
            <div class="scanner-overlay"><video id="v-video" autoplay playsinline muted></video></div>
            <div class="scanning-indicator"></div>
          </div>
          <div id="v-scan-result" style="margin-top:16px"></div>
        </div>
      </section>`;
    wrapper.querySelector('#v-btn').onclick = () => lookup(wrapper.querySelector('#v-q').value.trim());
    wrapper.querySelector('#v-q').addEventListener('keydown', e => { if (e.key === 'Enter') lookup(e.target.value.trim()); });

    async function lookup(query) {
      if (!query) return;
      const el = document.getElementById('v-result');
      el.innerHTML = '<div class="spinner"></div>';
      try {
        const data = await API.get(`/traceability/scan/${encodeURIComponent(query)}`);
        el.innerHTML = `<div class="scan-result">
          <h4>${data.product.name} (${data.product.sku})</h4>
          <p style="color:var(--text-light)">Producer: ${data.product.producer_name}</p>
          <p style="color:var(--text-light)">${data.events.length} trace event(s)</p>
          ${data.events.length > 0 ? `<div class="timeline" style="margin-top:12px">${data.events.map(e => `
            <div class="timeline-item"><div class="tl-title">${e.event_type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</div>
            <div class="tl-sub">${e.location_name || ''} ${e.country ? '· '+e.country : ''} · ${new Date(e.event_timestamp).toLocaleString()}</div></div>`).join('')}</div>` : ''}</div>`;
        document.getElementById('v-scan-result').innerHTML = '';
      } catch (e) {
        try {
          const cert = await API.get(`/certificates/${encodeURIComponent(query)}`);
          const statusCls = { 'verified':'badge-success', 'issued':'badge-info', 'revoked':'badge-danger', 'draft':'badge-secondary', 'expired':'badge-warning' };
          el.innerHTML = `<div class="scan-result">
            <h4>Certificate ${cert.certificate_id}</h4>
            <p>Type: ${cert.type.toUpperCase()} · <span class="badge ${statusCls[cert.status]||'badge-secondary'}">${cert.status}</span></p>
            <p style="color:var(--text-light)">Issuer: ${cert.issuer_name}${cert.recipient_entity ? ' · Recipient: '+cert.recipient_entity : ''}</p>
            <p style="color:var(--text-light)">Issued: ${new Date(cert.issued_date).toLocaleDateString()}${cert.expiry_date ? ' · Expires: '+new Date(cert.expiry_date).toLocaleDateString() : ''}</p>
            ${cert.description ? `<p style="color:var(--text-light);margin-top:4px">${cert.description}</p>` : ''}</div>`;
        } catch (e2) {
          el.innerHTML = `<div class="scan-result" style="background:#f8d7da;color:#721c24">No product or certificate found for "${query}"</div>`;
        }
      }
    }

    // Scanner
    let scanning = false, stream = null, scanTimer = null;
    (async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
        document.getElementById('v-video').srcObject = stream;
        scanning = true;
        scanLoop();
      } catch (_) { document.querySelector('#scanner-box').innerHTML += '<p style="color:#6b7280;margin-top:12px">Camera not available. Use the search field above.</p>'; }
    })();

    function scanLoop() {
      if (!scanning) return;
      const video = document.getElementById('v-video');
      if (!video || video.readyState < 2) { scanTimer = setTimeout(scanLoop, 500); return; }
      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth; canvas.height = video.videoHeight;
      canvas.getContext('2d').drawImage(video, 0, 0);
      const imgData = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height);
      let code = null;
      if ('BarcodeDetector' in window) {
        const detector = new BarcodeDetector();
        detector.detect(canvas).then(barcodes => {
          if (barcodes.length > 0) { onScan(barcodes[0].rawValue); return; }
          scanTimer = setTimeout(scanLoop, 500);
        }).catch(() => { scanTimer = setTimeout(scanLoop, 500); });
      } else {
        try {
          const result = jsQR(imgData.data, imgData.width, imgData.height);
          if (result) { onScan(result.data); return; }
        } catch (_) {}
        scanTimer = setTimeout(scanLoop, 500);
      }
    }

    let lastScanned = '';
    function onScan(data) {
      if (!data || data === lastScanned) return;
      lastScanned = data;
      document.getElementById('v-scan-result').innerHTML = `<div class="scan-result">Scanned: <strong>${data}</strong></div>`;
      lookup(data);
    }

    return wrapper;
  }));
};

Pages.login = (app) => {
  let isRegister = false;
  const render = () => {
    app.innerHTML = `
      <div class="auth-container">
        <div class="auth-card">
          <div class="logo">Food<span>Track</span></div>
          <p>${isRegister ? 'Create your account' : 'Digital Trust Infrastructure'}</p>
          <div id="auth-form"></div>
        </div>
      </div>`;
    const f = document.getElementById('auth-form');
    if (isRegister) {
      f.innerHTML = `
        <div class="form-group"><label>Full Name</label><input id="r-name" class="fi" placeholder="Ahmed Al Maktoum"></div>
        <div class="form-group"><label>Email</label><input id="r-email" class="fi" type="email" placeholder="ahmed@company.ae"></div>
        <div class="form-group"><label>Password</label><input id="r-pass" class="fi" type="password" placeholder="Min 8 characters"></div>
        <div class="form-group"><label>Company</label><input id="r-co" class="fi" placeholder="Dubai Food Group"></div>
        <div class="form-group"><label>Phone</label><input id="r-phone" class="fi" type="tel" placeholder="+971501234567"></div>
        <button class="btn btn-primary btn-block" id="r-btn">Register</button>
        <div class="auth-switch">Already have an account? <a href="#" id="switch-login">Login</a></div>`;
      document.getElementById('r-btn').onclick = async () => {
        if (!UI.validateForm({
          'r-name': { required: true, message: 'Full name required' },
          'r-email': { required: true, type: 'email' },
          'r-pass': { required: true, minLength: 8, message: 'Password min 8 characters' },
          'r-co': { required: true, message: 'Company required' },
        })) return;
        try {
          await Auth.register(
            document.getElementById('r-email').value,
            document.getElementById('r-pass').value,
            document.getElementById('r-name').value,
            document.getElementById('r-co').value,
            document.getElementById('r-phone').value
          );
          Router.navigate('#dashboard');
        } catch (e) { UI.showError(e.message); }
      };
      document.getElementById('switch-login').onclick = (e) => { e.preventDefault(); isRegister = false; render(); };
    } else {
      f.innerHTML = `
        <div class="form-group"><label>Email</label><input id="l-email" class="fi" type="email" placeholder="ahmed@company.ae"></div>
        <div class="form-group"><label>Password</label><input id="l-pass" class="fi" type="password" placeholder="Enter password"></div>
        <button class="btn btn-primary btn-block" id="l-btn">Login</button>
        <div class="auth-switch">Don\'t have an account? <a href="#" id="switch-reg">Register</a></div>
        <div class="sso-divider"><span>or continue with</span></div>
        <div class="sso-buttons" id="sso-buttons"></div>`;
      Auth.getSsoProviders().then(providers => {
        const box = document.getElementById('sso-buttons');
        if (!box) return;
        const enabled = providers.filter(p => p.enabled && p.client_id);
        if (enabled.length === 0) {
          box.innerHTML = '<p class="sso-note">SSO is not configured yet — enter the account details provided by FoodTrack.</p>';
          return;
        }
        box.innerHTML = enabled.map(p => `
          <button class="btn btn-outline btn-block sso-btn" data-provider="${p.provider}">
            ${p.provider === 'google' ? 'G' : 'M'} · ${p.provider.charAt(0).toUpperCase() + p.provider.slice(1)}
          </button>`).join('');
        box.querySelectorAll('.sso-btn').forEach(btn => {
          btn.addEventListener('click', () => {
            const p = btn.dataset.provider;
            const provider = enabled.find(x => x.provider === p);
            const redirectUri = provider.redirect_uri || window.location.origin + '/login.html';
            let url = '';
            if (p === 'google') {
              url = 'https://accounts.google.com/o/oauth2/v2/auth?client_id=' +
                encodeURIComponent(provider.client_id) +
                '&redirect_uri=' + encodeURIComponent(redirectUri) +
                '&response_type=token&scope=openid%20email%20profile';
            } else if (p === 'microsoft') {
              url = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=' +
                encodeURIComponent(provider.client_id) +
                '&redirect_uri=' + encodeURIComponent(redirectUri) +
                '&response_type=token&scope=openid%20email%20profile';
            }
            if (url) window.location.href = url;
          });
        });
      });
      document.getElementById('l-btn').onclick = async () => {
        if (!UI.validateForm({
          'l-email': { required: true, type: 'email' },
          'l-pass': { required: true, message: 'Password required' },
        })) return;
        try {
          const mfa = await Auth.login(document.getElementById('l-email').value, document.getElementById('l-pass').value);
          if (mfa) Router.navigate(`#mfa-verify?token=${mfa.temp_token}&type=${mfa.mfa_type}`);
          else Router.navigate('#dashboard');
        } catch (e) { UI.showError(e.message); }
      };
      ['l-email','l-pass'].forEach(id => document.getElementById(id).addEventListener('keydown', e => { if (e.key === 'Enter') document.getElementById('l-btn').click(); }));
      document.getElementById('switch-reg').onclick = (e) => { e.preventDefault(); isRegister = true; render(); };
    }
  };
  render();
};

Pages.mfaVerify = (app, params) => {
  const { token, type } = params;
  app.innerHTML = `
    <div class="auth-container">
      <div class="auth-card">
        <div class="logo">Food<span>Track</span></div>
        <p>Enter ${type.toUpperCase()} verification code</p>
        <div class="form-group"><label>Code</label><input id="mfa-code" class="fi" placeholder="000000" maxlength="6"></div>
        <button class="btn btn-primary btn-block" id="mfa-btn">Verify</button>
      </div>
    </div>`;
  document.getElementById('mfa-btn').onclick = async () => {
    if (!UI.validateForm({
      'mfa-code': { required: true, pattern: /^\d{6}$/, message: 'Enter a 6-digit code' },
    })) return;
    try {
      await Auth.verifyMfa(token, document.getElementById('mfa-code').value);
      Router.navigate('#dashboard');
  } catch (e) { UI.showError(e.message); }
  };
};

// ─── TAXONOMY PAGE ──────────────────────────────────────────────

Pages.taxonomies = (app) => {
  app.appendChild(UI.layout('Taxonomies', async () => {
    const data = await API.get('/taxonomy');
    const body = document.createElement('div');
    let html = '<div style="display:flex;gap:12px;flex-wrap:wrap">';
    if (!data.taxonomies || data.taxonomies.length === 0) {
      html += '<p style="color:var(--text-light)">No taxonomies yet.</p>';
    } else {
      data.taxonomies.forEach(t => {
        html += `<div class="card" style="flex:1;min-width:280px;cursor:pointer" onclick="Router.navigate('#taxonomy/${t.id}')">
          <div class="card-header"><h3>${t.icon || ''} ${t.name}</h3></div>
          <p style="font-size:14px;color:var(--text-light)">${t.description || ''}</p>
        </div>`;
      });
    }
    html += '</div>';
    body.innerHTML = html;
    if (Auth.getUser()?.role === 'admin') {
      document.getElementById('topbar-actions').innerHTML = '<button class="btn btn-primary btn-sm" id="add-tax-btn">+ New Taxonomy</button>';
      document.getElementById('add-tax-btn')?.addEventListener('click', () => {
        const m = UI.modal('New Taxonomy', `
          <div class="form-group"><label>Name</label><input id="tx-name" class="fi" placeholder="e.g. Produce Types"></div>
          <div class="form-group"><label>Icon (emoji)</label><input id="tx-icon" class="fi" placeholder="e.g. 🌾"></div>
          <div class="form-group"><label>Description</label><textarea id="tx-desc" class="fi" rows="2"></textarea></div>`);
        m.actions.appendChild(UI.btn('Cancel', 'btn-outline', m.close));
        m.actions.appendChild(UI.btn('Create', 'btn-primary', async (btn) => {
          if (!UI.validateForm({ 'tx-name': { required: true, message: 'Name required' } })) return;
          btn.disabled = true;
          try {
            await API.post('/taxonomy', { name: document.getElementById('tx-name').value, icon: document.getElementById('tx-icon').value || null, description: document.getElementById('tx-desc').value || null });
            m.close(); UI.showSuccess('Taxonomy created'); Router.navigate('#taxonomy');
          } catch (e) { UI.showError(e.message); btn.disabled = false; }
        }));
      });
    }
    return body;
  }));
};

// ─── TAXONOMY DETAIL PAGE ────────────────────────────────────────

Pages.taxonomyDetail = (app, id) => {
  app.appendChild(UI.layout('Taxonomy', async () => {
    const [taxData, treeData] = await Promise.all([
      API.get(`/taxonomy/${id}`),
      API.get(`/taxonomy/${id}/tree`),
    ]);
    const isAdmin = Auth.getUser()?.role === 'admin';
    const body = document.createElement('div');
    body.innerHTML = `<div class="card"><div class="card-header"><h3>${taxData.icon || ''} ${taxData.name}</h3>
      <div><button class="btn btn-sm btn-outline" id="add-node-btn">+ Add Category</button></div></div>
      <p style="color:var(--text-light)">${taxData.description || ''}</p></div>
      <div id="tax-tree" style="margin-top:16px"><div class="spinner"></div></div>
      <div id="tax-items" style="margin-top:16px"></div>`;

    function renderTree(tree, depth = 0) {
      let html = '';
      tree.forEach(node => {
        html += `<div style="padding:8px 0 8px ${depth * 24}px;display:flex;align-items:center;gap:8px">
          <span style="cursor:pointer;font-size:18px" class="node-toggle" data-node-id="${node.id}">${node.children?.length ? '▾' : '·'}</span>
          <strong style="cursor:pointer" class="node-name" data-node-id="${node.id}">${node.name}</strong>
          <span style="font-size:12px;color:var(--text-light)">${node.code}</span>
          ${isAdmin ? `<button class="btn btn-sm btn-outline node-add-item" data-node-id="${node.id}" style="margin-left:auto">+ Item</button>` : ''}
        </div>`;
        if (node.children?.length) {
          html += `<div class="node-children" data-parent="${node.id}" style="${depth < 1 ? '' : 'display:none'}">${renderTree(node.children, depth + 1)}</div>`;
        }
      });
      return html;
    }

    function renderTreeView() {
      const container = document.getElementById('tax-tree');
      container.innerHTML = renderTree(treeData.tree || []);
      container.querySelectorAll('.node-toggle').forEach(el => {
        el.addEventListener('click', () => {
          const children = document.querySelector(`.node-children[data-parent="${el.dataset.nodeId}"]`);
          if (children) { children.style.display = children.style.display === 'none' ? '' : 'none'; el.textContent = children.style.display === 'none' ? '▸' : '▾'; }
        });
      });
      container.querySelectorAll('.node-name').forEach(el => {
        el.addEventListener('click', () => loadItems(parseInt(el.dataset.nodeId)));
      });
      container.querySelectorAll('.node-add-item').forEach(el => {
        el.addEventListener('click', () => showAddItem(parseInt(el.dataset.nodeId)));
      });
      if (treeData.tree?.length) loadItems(treeData.tree[0].id);
    }

    async function loadItems(nodeId) {
      const container = document.getElementById('tax-items');
      container.innerHTML = '<div class="spinner"></div>';
      try {
        const data = await API.get(`/taxonomy/nodes/${nodeId}/items`);
        const node = findNode(treeData.tree, nodeId);
        let html = `<div class="card"><div class="card-header"><h3>Items in ${node?.name || 'Category'}</h3></div>`;
        if (!data.items || data.items.length === 0) {
          html += '<p style="color:var(--text-light);padding:16px 0">No items in this category yet.</p>';
        } else {
          html += '<div class="table-container"><table><thead><tr><th>Code</th><th>Common Name</th><th>Scientific Name</th><th>Genre</th><th>Actions</th></tr></thead><tbody>';
          data.items.forEach(item => {
            html += `<tr><td>${item.code}</td><td><strong>${item.common_name}</strong></td><td><em>${item.scientific_name || '—'}</em></td><td>${item.genre || '—'}</td>
              <td><button class="btn btn-sm btn-outline item-view" data-item-id="${item.id}">View</button></td></tr>`;
          });
          html += '</tbody></table></div>';
        }
        html += '</div>';
        container.innerHTML = html;
        container.querySelectorAll('.item-view').forEach(el => {
          el.addEventListener('click', () => showItemDetail(parseInt(el.dataset.itemId)));
        });
      } catch (e) { container.innerHTML = `<p style="color:var(--danger)">Error: ${e.message}</p>`; }
    }

    function findNode(tree, id) {
      for (const n of tree) { if (n.id === id) return n; if (n.children) { const f = findNode(n.children, id); if (f) return f; } }
      return null;
    }

    function showAddItem(nodeId) {
      const m = UI.modal('Add Taxonomy Item', `
        <div class="form-group"><label>Code</label><input id="ti-code" class="fi" placeholder="e.g. APP-FUJI"></div>
        <div class="form-group"><label>Common Name</label><input id="ti-name" class="fi" placeholder="e.g. Fuji Apple"></div>
        <div class="form-group"><label>Scientific Name</label><input id="ti-sci" class="fi" placeholder="e.g. Malus domestica"></div>
        <div class="form-group"><label>Genre</label><input id="ti-genre" class="fi" placeholder="e.g. Fruit / Pome"></div>
        <div class="form-group"><label>Description</label><textarea id="ti-desc" class="fi" rows="2"></textarea></div>`);
      m.actions.appendChild(UI.btn('Cancel', 'btn-outline', m.close));
      m.actions.appendChild(UI.btn('Add', 'btn-primary', async (btn) => {
        if (!UI.validateForm({ 'ti-code': { required: true }, 'ti-name': { required: true } })) return;
        btn.disabled = true;
        try {
          const item = await API.post('/taxonomy/items', { node_id: nodeId, code: document.getElementById('ti-code').value, common_name: document.getElementById('ti-name').value, scientific_name: document.getElementById('ti-sci').value || null, genre: document.getElementById('ti-genre').value || null, description: document.getElementById('ti-desc').value || null });
          m.close(); UI.showSuccess('Item added');
          await Promise.all([
            addName(item.id, 'en', item.common_name, true),
            item.scientific_name ? addName(item.id, 'scientific', item.scientific_name, false) : null,
          ].filter(Boolean));
          loadItems(nodeId);
        } catch (e) { UI.showError(e.message); btn.disabled = false; }
      }));
    }

    async function addName(itemId, lang, name, primary) {
      await API.post(`/taxonomy/items/${itemId}/names`, { language: lang, name, is_primary: primary });
    }

    async function showItemDetail(itemId) {
      try {
        const item = await API.get(`/taxonomy/items/${itemId}`);
        const m = UI.modal(`Item: ${item.common_name}`, `
          <table style="width:100%;font-size:14px">${[
            ['Code', item.code], ['Common Name', item.common_name], ['Scientific Name', item.scientific_name || '—'],
            ['Genre', item.genre || '—'], ['Description', item.description || '—'],
          ].map(([k,v]) => `<tr><td style="padding:4px 8px;color:var(--text-light);width:140px">${k}</td><td style="padding:4px 8px"><strong>${v}</strong></td></tr>`).join('')}</table>
          <h4 style="margin:16px 0 8px">Multilingual Names</h4>
          <div id="item-names-list">${item.names?.map(n => `<div style="display:flex;gap:8px;padding:4px 0"><span style="font-weight:600;width:80px">${n.language.toUpperCase()}</span><span>${n.name}${n.is_primary ? ' ⭐' : ''}</span></div>`).join('') || '<p style="color:var(--text-light)">No additional names</p>'}</div>
          <div style="display:flex;gap:8px;margin-top:8px">
            <input id="ni-lang" class="fi" placeholder="lang" style="width:80px" maxlength="10">
            <input id="ni-name" class="fi" placeholder="name" style="flex:1">
            <button class="btn btn-sm btn-primary" id="ni-btn">+ Add Name</button>
          </div>
          <h4 style="margin:16px 0 8px">Attributes</h4>
          <div id="item-attrs-list">${item.attributes?.map(a => `<div style="display:flex;gap:8px;padding:4px 0"><span style="font-weight:600;width:120px">${a.key}</span><span>${a.value || ''}${a.unit ? ' '+a.unit : ''}</span></div>`).join('') || '<p style="color:var(--text-light)">No attributes</p>'}</div>
          <div style="display:flex;gap:8px;margin-top:8px">
            <input id="ai-key" class="fi" placeholder="key" style="width:120px">
            <input id="ai-val" class="fi" placeholder="value" style="flex:1">
            <input id="ai-unit" class="fi" placeholder="unit" style="width:60px">
            <button class="btn btn-sm btn-primary" id="ai-btn">+ Add</button>
          </div>`);
        document.getElementById('ni-btn').onclick = async () => {
          const lang = document.getElementById('ni-lang').value.trim();
          const name = document.getElementById('ni-name').value.trim();
          if (!lang || !name) return;
          try {
            await API.post(`/taxonomy/items/${itemId}/names`, { language: lang, name });
            UI.showSuccess('Name added');
            m.close(); showItemDetail(itemId);
          } catch (e) { UI.showError(e.message); }
        };
        document.getElementById('ai-btn').onclick = async () => {
          const key = document.getElementById('ai-key').value.trim();
          const val = document.getElementById('ai-val').value.trim();
          const unit = document.getElementById('ai-unit').value.trim();
          if (!key) return;
          try {
            await API.post(`/taxonomy/items/${itemId}/attributes`, { key, value: val || null, unit: unit || null });
            UI.showSuccess('Attribute added');
            m.close(); showItemDetail(itemId);
          } catch (e) { UI.showError(e.message); }
        };
      } catch (e) { UI.showError(e.message); }
    }

    renderTreeView();

    body.querySelector('#add-node-btn')?.addEventListener('click', () => {
      const m = UI.modal('Add Category', `
        <div class="form-group"><label>Code</label><input id="nd-code" class="fi" placeholder="e.g. FRUITS"></div>
        <div class="form-group"><label>Name</label><input id="nd-name" class="fi" placeholder="e.g. Fruits"></div>
        <div class="form-group"><label>Parent (optional)</label><select id="nd-parent" class="fi"><option value="">None (root)</option>
          ${(treeData.tree || []).map(n => `<option value="${n.id}">${n.name}</option>`).join('')}</select></div>
        <div class="form-group"><label>Description</label><textarea id="nd-desc" class="fi" rows="2"></textarea></div>`);
      m.actions.appendChild(UI.btn('Cancel', 'btn-outline', m.close));
      m.actions.appendChild(UI.btn('Add', 'btn-primary', async (btn) => {
        if (!UI.validateForm({ 'nd-code': { required: true }, 'nd-name': { required: true } })) return;
        btn.disabled = true;
        try {
          await API.post(`/taxonomy/${id}/nodes`, { code: document.getElementById('nd-code').value, name: document.getElementById('nd-name').value, parent_id: parseInt(document.getElementById('nd-parent').value) || null, description: document.getElementById('nd-desc').value || null });
          m.close(); UI.showSuccess('Category added'); Router.navigate(`#taxonomy/${id}`);
        } catch (e) { UI.showError(e.message); btn.disabled = false; }
      }));
    });

    return body;
  }));
};
// ─── DASHBOARD ────────────────────────────────────────────────

Pages.dashboard = (app) => {
  app.appendChild(UI.layout('Dashboard', async () => {
    const d = await API.get('/analytics/dashboard');
    const cats = await API.get('/analytics/products-by-category');
    const evts = await API.get('/analytics/events-by-type');
    const body = document.createElement('div');
    let expiryHtml = '';
    try {
      const certData = await API.get('/certificates');
      const soon = certData.certificates.filter(c => c.expiry_date && new Date(c.expiry_date) > new Date() && new Date(c.expiry_date) < new Date(Date.now() + 30*24*60*60*1000));
      if (soon.length > 0) {
        expiryHtml = `<div class="card" style="margin-top:20px;border-color:var(--warning)"><div class="card-header"><h3>⚠️ Expiring Certificates (${soon.length})</h3></div>
          <div class="table-container"><table><tr><th>Certificate</th><th>Type</th><th>Expires</th></tr>
          ${soon.map(c => `<tr><td><a href="#certificate/${c.certificate_id}">${c.certificate_id}</a></td><td>${c.type.toUpperCase()}</td><td>${new Date(c.expiry_date).toLocaleDateString()}</td></tr>`).join('')}</table></div></div>`;
      }
    } catch (_) {}
    body.innerHTML = `
      <div class="card-grid card-grid-4" id="dash-stats">
        ${[['total_products','Products'],['total_traceability_events','Trace Events'],['total_certificates','Certificates'],['verified_certificates','Verified']].map(([k,v]) =>
          `<div class="card stat-card"><div class="stat-value">${d[k]}</div><div class="stat-label">${v}</div></div>`
        ).join('')}
      </div>
      ${expiryHtml}
      <div class="card-grid card-grid-2" style="margin-top:20px">
        <div class="card"><div class="card-header"><h3>Products by Category</h3></div>
          <table><thead><tr><th>Category</th><th>Count</th></tr></thead>
          <tbody>${cats.categories.map(c => `<tr><td>${c.category.replace(/_/g,' ')}</td><td><strong>${c.count}</strong></td></tr>`).join('') || '<tr><td colspan="2" style="text-align:center;color:#6b7280">No data</td></tr>'}</tbody></table></div>
        <div class="card"><div class="card-header"><h3>Events by Type</h3></div>
          <table><thead><tr><th>Type</th><th>Count</th></tr></thead>
          <tbody>${evts.event_types.map(e => `<tr><td>${e.type.replace(/_/g,' ')}</td><td><strong>${e.count}</strong></td></tr>`).join('') || '<tr><td colspan="2" style="text-align:center;color:#6b7280">No data</td></tr>'}</tbody></table></div>
      </div>
      <div class="card" style="margin-top:20px">
        <div class="card-header"><h3>Quick Actions</h3></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <button class="btn btn-primary" onclick="Router.navigate('#products')">Manage Products</button>
          <button class="btn btn-accent" onclick="Router.navigate('#traceability')">Trace a Product</button>
          <button class="btn btn-outline" onclick="Router.navigate('#certificates')">View Certificates</button>
          <button class="btn btn-outline" onclick="Router.navigate('#share')">Share & Compare</button>
        </div>
      </div>`;
    return body;
  }));
};

// ─── PRODUCTS ─────────────────────────────────────────────────

Pages.products = (app) => {
  app.appendChild(UI.layout('Products', async () => {
    const data = await API.get('/products');
    const allProducts = data.products;
    const body = document.createElement('div');
    const renderTable = (filter) => {
      const q = (filter || '').toLowerCase();
      const filtered = q ? allProducts.filter(p =>
        p.sku.toLowerCase().includes(q) || p.name.toLowerCase().includes(q) ||
        p.category.toLowerCase().includes(q) || (p.origin_country || '').toLowerCase().includes(q) ||
        (p.producer_name || '').toLowerCase().includes(q)
      ) : allProducts;
      let html = '<div style="display:flex;gap:8px;margin-bottom:16px;max-width:400px"><input id="prod-search" class="fi" placeholder="Search by SKU, name, category..." style="flex:1" value="' + (filter || '') + '"></div>';
      html += '<div class="table-container"><table><thead><tr><th>SKU</th><th>Name</th><th>Category</th><th>Origin</th><th>Producer</th><th>Actions</th></tr></thead><tbody>';
      if (filtered.length === 0) {
        html += '<tr><td colspan="6" style="text-align:center;padding:32px;color:#6b7280">' + (q ? 'No products match your search' : 'No products yet. Create your first product.') + '</td></tr>';
      } else {
        filtered.forEach(p => {
          html += `<tr><td><strong>${p.sku}</strong></td><td>${p.name}</td><td>${UI.badge(p.category,'badge-info').outerHTML}</td><td>${p.origin_country || '—'}</td><td>${p.producer_name || '—'}</td><td><a href="#product/${p.id}" class="btn btn-sm btn-outline">View</a></td></tr>`;
        });
      }
      html += '</tbody></table></div>';
      const tableDiv = document.getElementById('prod-table');
      if (tableDiv) tableDiv.innerHTML = html;
      const searchEl = document.getElementById('prod-search');
      if (searchEl) {
        searchEl.addEventListener('input', (e) => renderTable(e.target.value));
        searchEl.focus();
      }
    };
    body.innerHTML = '<div id="prod-table"></div>';
    renderTable('');
    const tb = document.getElementById('topbar-actions');
    tb.innerHTML = '<button class="btn btn-primary btn-sm" onclick="Pages.showCreateProduct()">+ New Product</button>';
    return body;
  }));
};

Pages.showCreateProduct = () => {
  const m = UI.modal('Create Product', `
    <div class="form-group"><label>SKU</label><input id="p-sku" class="fi" placeholder="FT-001"></div>
    <div class="form-group"><label>Product Name</label><input id="p-name" class="fi" placeholder="Premium Organic Dates"></div>
    <div class="form-row"><div class="form-group"><label>Category</label><select id="p-cat" class="fi"><option value="fresh_produce">Fresh Produce</option><option value="meat_poultry">Meat & Poultry</option><option value="seafood">Seafood</option><option value="dairy">Dairy</option><option value="grains">Grains</option><option value="beverages">Beverages</option><option value="processed">Processed</option><option value="other">Other</option></select></div>
    <div class="form-group"><label>Weight (kg)</label><input id="p-weight" type="number" step="0.1" class="fi"></div></div>
    <div class="form-row"><div class="form-group"><label>Origin Country</label><input id="p-country" class="fi" placeholder="UAE"></div><div class="form-group"><label>Region</label><input id="p-region" class="fi" placeholder="Al Ain"></div></div>
    <div class="form-group"><label>Producer</label><input id="p-producer" class="fi" placeholder="Al Foah Farms"></div>
    <div class="form-group"><label>Storage Requirements</label><input id="p-storage" class="fi" placeholder="Cool dry place 18-25°C"></div>
    <div class="form-group"><label>Description</label><textarea id="p-desc" class="fi" rows="2"></textarea></div>
  `);
  m.actions.innerHTML = '';
  m.actions.appendChild(UI.btn('Cancel', 'btn-outline', m.close));
  m.actions.appendChild(UI.btn('Create', 'btn-primary', async (btn) => {
    if (!UI.validateForm({
      'p-sku': { required: true, message: 'SKU required' },
      'p-name': { required: true, message: 'Product name required' },
    })) return;
    btn.disabled = true;
    try {
      await API.post('/products', {
        sku: document.getElementById('p-sku').value, name: document.getElementById('p-name').value,
        category: document.getElementById('p-cat').value, weight_kg: parseFloat(document.getElementById('p-weight').value) || null,
        origin_country: document.getElementById('p-country').value || null, origin_region: document.getElementById('p-region').value || null,
        producer_name: document.getElementById('p-producer').value || null, storage_requirements: document.getElementById('p-storage').value || null,
        description: document.getElementById('p-desc').value || null,
      });
      m.close(); UI.showSuccess('Product created'); Router.navigate('#products');
    } catch (e) { UI.showError(e.message); btn.disabled = false; }
  }));
};

Pages.showEditProduct = (id, p) => {
  const m = UI.modal('Edit Product', `
    <div class="form-group"><label>SKU</label><input id="ep-sku" class="fi" value="${p.sku}"></div>
    <div class="form-group"><label>Product Name</label><input id="ep-name" class="fi" value="${p.name}"></div>
    <div class="form-row"><div class="form-group"><label>Category</label><select id="ep-cat" class="fi">${['fresh_produce','meat_poultry','seafood','dairy','grains','beverages','processed','other'].map(c => `<option value="${c}"${c===p.category?' selected':''}>${c.replace(/_/g,' ').replace(/\b\w/g,x=>x.toUpperCase())}</option>`).join('')}</select></div>
    <div class="form-group"><label>Weight (kg)</label><input id="ep-weight" type="number" step="0.1" class="fi" value="${p.weight_kg||''}"></div></div>
    <div class="form-row"><div class="form-group"><label>Origin Country</label><input id="ep-country" class="fi" value="${p.origin_country||''}"></div><div class="form-group"><label>Region</label><input id="ep-region" class="fi" value="${p.origin_region||''}"></div></div>
    <div class="form-group"><label>Producer</label><input id="ep-producer" class="fi" value="${p.producer_name||''}"></div>
    <div class="form-group"><label>Storage Requirements</label><input id="ep-storage" class="fi" value="${p.storage_requirements||''}"></div>
    <div class="form-group"><label>Description</label><textarea id="ep-desc" class="fi" rows="2">${p.description||''}</textarea></div>
  `);
  m.actions.innerHTML = '';
  m.actions.appendChild(UI.btn('Cancel', 'btn-outline', m.close));
  m.actions.appendChild(UI.btn('Save', 'btn-primary', async (btn) => {
    if (!UI.validateForm({
      'ep-name': { required: true, message: 'Product name required' },
    })) return;
    btn.disabled = true;
    try {
      await API.put(`/products/${id}`, {
        name: document.getElementById('ep-name').value,
        category: document.getElementById('ep-cat').value,
        weight_kg: parseFloat(document.getElementById('ep-weight').value) || null,
        origin_country: document.getElementById('ep-country').value || null,
        origin_region: document.getElementById('ep-region').value || null,
        producer_name: document.getElementById('ep-producer').value || null,
        storage_requirements: document.getElementById('ep-storage').value || null,
        description: document.getElementById('ep-desc').value || null,
      });
      m.close(); UI.showSuccess('Product updated'); window.location.reload();
    } catch (e) { UI.showError(e.message); btn.disabled = false; }
  }));
};

Pages.productDetail = (app, id) => {
  app.appendChild(UI.layout('Product Detail', async () => {
    const data = await API.get(`/products/${id}`);
    const p = data.product;
    const evts = data.traceability_events;
    const body = document.createElement('div');
    body.innerHTML = `
      <div class="card-grid card-grid-2">
        <div class="card"><div class="card-header"><h3>Product Information</h3>
          <div style="display:flex;gap:8px">${Auth.getUser()?.role === 'admin' ? '<button class="btn btn-sm btn-danger" id="delete-product-btn">Delete</button>' : ''}<button class="btn btn-sm btn-outline" id="edit-product-btn">Edit</button></div></div>
          <table style="width:100%;font-size:14px">${[
            ['SKU', p.sku], ['Name', p.name], ['Category', p.category], ['Origin', `${p.origin_country||'—'} ${p.origin_region ? '/ '+p.origin_region : ''}`],
            ['Producer', p.producer_name||'—'], ['Weight', p.weight_kg ? p.weight_kg+' kg' : '—'], ['Storage', p.storage_requirements||'—'],
            ['Created', new Date(p.created_at).toLocaleString()],
          ].map(([k,v]) => `<tr><td style="padding:6px 0;color:#6b7280;width:120px">${k}</td><td style="padding:6px 0"><strong>${v}</strong></td></tr>`).join('')}</table></div>
        <div class="card"><div class="card-header"><h3>Codes</h3></div>
          <div style="display:flex;gap:16px;justify-content:center">
            ${p.qr_code ? `<div class="code-display"><img src="data:image/png;base64,${p.qr_code}" alt="QR"/><div style="font-size:11px;color:#6b7280;margin-top:4px">QR Code</div></div>` : ''}
            ${p.barcode ? `<div class="code-display"><img src="data:image/png;base64,${p.barcode}" alt="Barcode" style="max-width:180px"/><div style="font-size:11px;color:#6b7280;margin-top:4px">Barcode</div></div>` : ''}
            ${p.nfc_tag_id ? `<div class="code-display"><div style="font-size:32px">📶</div><div style="font-size:11px;color:#6b7280">NFC: ${p.nfc_tag_id}</div></div>` : ''}
          </div></div></div>
      <div class="card" style="margin-top:20px"><div class="card-header"><h3>Traceability Timeline (${evts.length} events)</h3>
        <button class="btn btn-accent btn-sm" onclick="Pages.showAddEvent(${id})">+ Add Event</button></div>
        ${evts.length === 0 ? '<div style="text-align:center;padding:24px;color:#6b7280">No events recorded</div>' :
          `<div class="timeline">${evts.map(e => `
            <div class="timeline-item">
              <div class="tl-title">${e.event_type.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase())}</div>
              <div class="tl-sub">${[e.location_name, e.country].filter(Boolean).join(' · ')} · ${new Date(e.event_timestamp).toLocaleString()}</div>
              <div class="tl-desc">${e.handler_name}${e.handler_organization ? ' ('+e.handler_organization+')' : ''}${e.temperature_celsius ? ' · '+e.temperature_celsius+'°C' : ''}${e.humidity_percent ? ' · '+e.humidity_percent+'% RH' : ''}</div>
            </div>`).join('')}</div>`}</div>`;
    body.querySelector('#delete-product-btn')?.addEventListener('click', async () => {
      if (await UI.confirm('Delete Product', `Are you sure you want to delete "${p.name}" (${p.sku})? This cannot be undone.`)) {
        try {
          await API.del(`/products/${id}`);
          UI.showSuccess('Product deleted');
          Router.navigate('#products');
        } catch (e) { UI.showError(e.message); }
      }
    });
    body.querySelector('#edit-product-btn').onclick = () => Pages.showEditProduct(id, p);
    return body;
  }));
};

Pages.showAddEvent = (productId) => {
  const eventTypes = ['harvest','processing','packaging','storage','shipping','import_clearance','distribution','delivery','retail','verification'];
  const m = UI.modal('Add Trace Event', `
    <div class="form-group"><label>Event Type</label><select id="evt-type" class="fi">${eventTypes.map(t => `<option value="${t}">${t.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase())}</option>`).join('')}</select></div>
    <div class="form-row"><div class="form-group"><label>Location</label><input id="evt-loc" class="fi" placeholder="Warehouse, port..."></div><div class="form-group"><label>Country</label><input id="evt-ctry" class="fi" placeholder="UAE"></div></div>
    <div class="form-row"><div class="form-group"><label>Temperature (°C)</label><input id="evt-temp" type="number" step="0.1" class="fi"></div><div class="form-group"><label>Humidity (%)</label><input id="evt-hum" type="number" step="0.1" class="fi"></div></div>
    <div class="form-group"><label>Organization</label><input id="evt-org" class="fi" placeholder="Handling company"></div>
    <div class="form-group"><label>Notes</label><textarea id="evt-notes" class="fi" rows="2"></textarea></div>
  `);
  m.actions.appendChild(UI.btn('Cancel', 'btn-outline', m.close));
  m.actions.appendChild(UI.btn('Add Event', 'btn-primary', async (btn) => {
    if (!UI.validateForm({
      'evt-type': { required: true, message: 'Event type required' },
      'evt-loc': { required: true, message: 'Location required' },
    })) return;
    btn.disabled = true;
    try {
      await API.post('/traceability', {
        product_id: parseInt(productId), event_type: document.getElementById('evt-type').value,
        location_name: document.getElementById('evt-loc').value || null, country: document.getElementById('evt-ctry').value || null,
        temperature_celsius: parseFloat(document.getElementById('evt-temp').value) || null,
        humidity_percent: parseFloat(document.getElementById('evt-hum').value) || null,
        handler_organization: document.getElementById('evt-org').value || null,
        notes: document.getElementById('evt-notes').value || null,
        event_timestamp: new Date().toISOString(),
      });
      m.close(); UI.showSuccess('Event added'); window.location.reload();
    } catch (e) { UI.showError(e.message); btn.disabled = false; }
  }));
};

// ─── TRACEABILITY ─────────────────────────────────────────────

Pages.traceability = (app) => {
  app.appendChild(UI.layout('Traceability', async () => {
    const body = document.createElement('div');
    body.innerHTML = `
      <div class="card"><div class="card-header"><h3>Scan Product</h3></div>
        <div style="display:flex;gap:8px;max-width:500px">
          <input id="trace-q" class="fi" placeholder="Enter SKU, scan QR, or barcode..." style="flex:1">
          <button id="trace-btn" class="btn btn-primary">Search</button>
        </div>
        <div id="trace-result" style="margin-top:16px"></div></div>
      <div class="card" style="margin-top:20px"><div class="card-header"><h3>Recent Trace Events</h3></div>
        <div id="recent-events"><div class="spinner"></div></div></div>`;
    API.get('/products').then(data => {
      const el = document.getElementById('recent-events');
      if (!data.products || data.products.length === 0) {
        el.innerHTML = '<div class="empty-state"><p>No products yet. Create a product and add trace events.</p></div>';
        return;
      }
      Promise.all(data.products.slice(0, 5).map(p => API.get(`/traceability/product/${p.id}`).catch(() => null)))
        .then(results => {
          const items = results.filter(Boolean).flatMap(r => (r.events || []).slice(0, 3).map(e => ({ ...e, product: r.product })));
          if (items.length === 0) {
            el.innerHTML = '<div class="empty-state"><p>No trace events found. Add events to your products.</p></div>';
          } else {
            el.innerHTML = '<div class="timeline">' + items.sort((a, b) => new Date(b.event_timestamp) - new Date(a.event_timestamp)).slice(0, 10).map(e =>
              `<div class="timeline-item"><div class="tl-title">${e.product?.name || ''} — ${e.event_type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</div><div class="tl-sub">${e.location_name || ''} · ${new Date(e.event_timestamp).toLocaleString()}</div></div>`
            ).join('') + '</div>';
          }
        });
    }).catch(() => { document.getElementById('recent-events').innerHTML = '<div class="empty-state"><p>Could not load recent events</p></div>'; });
    body.querySelector('#trace-btn').onclick = async () => {
      const q = document.getElementById('trace-q').value.trim();
      if (!q) return;
      const r = document.getElementById('trace-result');
      try {
        const data = await API.get(`/traceability/scan/${encodeURIComponent(q)}`);
        r.innerHTML = `<div class="scan-result">
          <h4>${data.product.name} (${data.product.sku})</h4>
          <p style="color:#6b7280">Producer: ${data.product.producer_name}</p>
          ${data.events.length > 0 ? `<div class="timeline" style="margin-top:12px">${data.events.map(e => `
            <div class="timeline-item">
              <div class="tl-title">${e.event_type.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase())}</div>
              <div class="tl-sub">${[e.location_name, e.country].filter(Boolean).join(' · ')} · ${new Date(e.event_timestamp).toLocaleString()}</div>
              <div class="tl-desc">${e.handler_name}${e.handler_organization ? ' ('+e.handler_organization+')' : ''}${e.temperature_celsius ? ' · Temp: '+e.temperature_celsius+'°C' : ''}</div>
            </div>`).join('')}</div>` : '<p style="margin-top:12px;color:#6b7280">No events yet</p>'}
          <div style="margin-top:12px"><a href="#product/${data.product.id}" class="btn btn-sm btn-outline">Full Details</a></div>
        </div>`;
      } catch (e) { r.innerHTML = `<div class="scan-result" style="background:#f8d7da;color:#721c24">${e.message}</div>`; }
    };
    body.querySelector('#trace-q').addEventListener('keydown', e => { if (e.key === 'Enter') body.querySelector('#trace-btn').click(); });
    return body;
  }));
};

// ─── CERTIFICATES ─────────────────────────────────────────────

Pages.certificates = (app) => {
  app.appendChild(UI.layout('Certificates', async () => {
    const data = await API.get('/certificates');
    const allCerts = data.certificates;
    const statusCls = { 'verified':'badge-success', 'issued':'badge-info', 'revoked':'badge-danger', 'draft':'badge-secondary', 'expired':'badge-warning' };
    const body = document.createElement('div');
    const renderTable = (filter) => {
      const q = (filter || '').toLowerCase();
      const filtered = q ? allCerts.filter(c =>
        c.certificate_id.toLowerCase().includes(q) || c.type.toLowerCase().includes(q) ||
        c.status.toLowerCase().includes(q) || (c.issuer_name || '').toLowerCase().includes(q) ||
        (c.recipient_entity || '').toLowerCase().includes(q)
      ) : allCerts;
      let html = '<div style="display:flex;gap:8px;margin-bottom:16px;max-width:400px"><input id="cert-search" class="fi" placeholder="Search by ID, type, status, issuer..." style="flex:1" value="' + (filter || '') + '"></div>';
      html += '<div class="table-container"><table><thead><tr><th>ID</th><th>Type</th><th>Status</th><th>Issuer</th><th>Issued</th><th>Actions</th></tr></thead><tbody>';
      if (filtered.length === 0) {
        html += '<tr><td colspan="6" style="text-align:center;padding:32px;color:#6b7280">' + (q ? 'No certificates match your search' : 'No certificates issued yet') + '</td></tr>';
      } else {
        filtered.forEach(c => {
          html += `<tr><td><strong>${c.certificate_id}</strong></td><td>${c.type.toUpperCase()}</td><td><span class="badge ${statusCls[c.status]||'badge-secondary'}">${c.status}</span></td><td>${c.issuer_name}</td><td>${new Date(c.issued_date).toLocaleDateString()}</td><td><a href="#certificate/${c.certificate_id}" class="btn btn-sm btn-outline">View</a></td></tr>`;
        });
      }
      html += '</tbody></table></div>';
      const tableDiv = document.getElementById('cert-table');
      if (tableDiv) tableDiv.innerHTML = html;
      const searchEl = document.getElementById('cert-search');
      if (searchEl) searchEl.addEventListener('input', (e) => renderTable(e.target.value));
    };
    body.innerHTML = '<div id="cert-table"></div>';
    renderTable('');
    document.getElementById('topbar-actions').innerHTML = '<button class="btn btn-primary btn-sm" onclick="Pages.showIssueCert()">+ Issue Certificate</button>';
    return body;
  }));
};

Pages.showIssueCert = () => {
  const m = UI.modal('Issue Certificate', `
    <div class="form-group"><label>Product ID</label><input id="c-pid" type="number" class="fi" placeholder="1"></div>
    <div class="form-group"><label>Type</label><select id="c-type" class="fi"><option value="origin">Origin</option><option value="organic">Organic</option><option value="halal">Halal</option><option value="quality">Quality</option><option value="safety">Safety</option><option value="fair_trade">Fair Trade</option><option value="custom">Custom</option></select></div>
    <div class="form-group"><label>Issuing Body</label><input id="c-body" class="fi" placeholder="UAE Standards Authority"></div>
    <div class="form-group"><label>Recipient</label><input id="c-recip" class="fi" placeholder="Dubai Food Group"></div>
    <div class="form-group"><label>Description</label><textarea id="c-desc" class="fi" rows="2" placeholder="Certification details"></textarea></div>
  `);
  m.actions.appendChild(UI.btn('Cancel', 'btn-outline', m.close));
  m.actions.appendChild(UI.btn('Issue', 'btn-primary', async (btn) => {
    if (!UI.validateForm({
      'c-pid': { required: true, pattern: /^\d+$/, message: 'Valid product ID required' },
      'c-type': { required: true, message: 'Certificate type required' },
      'c-body': { required: true, message: 'Issuing body required' },
    })) return;
    btn.disabled = true;
    try {
      await API.post('/certificates', {
        product_id: parseInt(document.getElementById('c-pid').value), type: document.getElementById('c-type').value,
        issuing_body: document.getElementById('c-body').value || null, recipient_entity: document.getElementById('c-recip').value || null,
        description: document.getElementById('c-desc').value || null,
      });
      m.close(); UI.showSuccess('Certificate issued'); Router.navigate('#certificates');
    } catch (e) { UI.showError(e.message); btn.disabled = false; }
  }));
};

Pages.certificateDetail = (app, id) => {
  app.appendChild(UI.layout('Certificate Detail', async () => {
    const c = await API.get(`/certificates/${id}`);
    const body = document.createElement('div');
    body.innerHTML = `
      <div class="card"><div class="card-header"><h3>Certificate ${c.certificate_id}</h3>
        <div style="display:flex;gap:8px;align-items:center">
          ${c.status === 'issued' ? `<button class="btn btn-sm btn-success" onclick="Pages.verifyCert('${c.certificate_id}')" style="background:#28a745;color:#fff;border:none">✓ Verify</button>` : ''}
          ${c.status !== 'revoked' && Auth.getUser()?.role === 'admin' ? `<button class="btn btn-sm btn-danger" id="revoke-cert-btn">Revoke</button>` : ''}
          ${c.status === 'verified' ? `<span class="badge badge-success">VERIFIED</span>` : `<span class="badge ${c.status === 'issued' ? 'badge-info' : c.status === 'revoked' ? 'badge-danger' : 'badge-secondary'}">${c.status.toUpperCase()}</span>`}
        </div></div>
      <table style="width:100%;font-size:14px">${[
        ['Certificate ID', c.certificate_id], ['Type', c.type.toUpperCase()], ['Status', c.status.toUpperCase()],
        ['Issuer', c.issuer_name], ['Issuing Body', c.issuing_body||'—'], ['Recipient', c.recipient_entity||'—'],
        ['Issued', new Date(c.issued_date).toLocaleString()], ['Expires', c.expiry_date ? new Date(c.expiry_date).toLocaleString() : 'No expiry'],
        ['Digital Signature', `<code style="font-size:12px;background:#f1f5f3;padding:2px 6px;border-radius:3px">${c.digital_signature?.substring(0,24)||'—'}...</code>`],
        ['Document', c.document_url ? `<a href="${c.document_url}" target="_blank">View</a>` : '—'],
      ].map(([k,v]) => `<tr><td style="padding:6px 0;color:#6b7280;width:160px">${k}</td><td style="padding:6px 0"><strong>${v}</strong></td></tr>`).join('')}</table></div>
      ${c.description ? `<div class="card" style="margin-top:16px"><h3 style="margin-bottom:8px;font-size:16px">Description</h3><p>${c.description}</p></div>` : ''}`;
    body.querySelector('#revoke-cert-btn')?.addEventListener('click', async () => {
      if (await UI.confirm('Revoke Certificate', `Revoke certificate ${c.certificate_id}? This action cannot be undone.`)) {
        try {
          await API.post(`/certificates/${id}/revoke`);
          UI.showSuccess('Certificate revoked');
          window.location.reload();
        } catch (e) { UI.showError(e.message); }
      }
    });
    return body;
  }));
};

Pages.verifyCert = async (certId) => {
  try {
    await API.post(`/certificates/${certId}/verify-auth`);
    UI.showSuccess('Certificate verified');
    window.location.reload();
  } catch (e) { UI.showError(e.message); }
};

// ─── ANALYTICS ────────────────────────────────────────────────

Pages.analytics = (app) => {
  app.appendChild(UI.layout('Analytics', async () => {
    const [cats, evts, certs] = await Promise.all([
      API.get('/analytics/products-by-category'),
      API.get('/analytics/events-by-type'),
      API.get('/analytics/certificates-by-status'),
    ]);
    const body = document.createElement('div');

    const barChart = (items, labelKey, valueKey, maxVal) => {
      const max = maxVal || Math.max(...items.map(i => i[valueKey]), 1);
      return '<div class="bar-chart">' + items.map(i =>
        `<div class="bar" style="height:${(i[valueKey] / max) * 100}%"><span class="bar-label">${i[labelKey].replace(/_/g,' ').replace(/\b\w/g,x=>x.toUpperCase()).substring(0,12)}</span><span class="bar-value">${i[valueKey]}</span></div>`
      ).join('') + '</div>';
    };

    const catMax = Math.max(...cats.categories.map(c => c.count), 1);
    const evtMax = Math.max(...evts.event_types.map(e => e.count), 1);
    const certMax = Math.max(...certs.statuses.map(s => s.count), 1);

    body.innerHTML = `
      <div class="card-grid card-grid-2">
        <div class="card"><div class="card-header"><h3>Products by Category</h3>
          <button class="btn btn-sm btn-outline" id="csv-cats">CSV</button></div>
          ${barChart(cats.categories, 'category', 'count', catMax)}
          <table><thead><tr><th>Category</th><th>Count</th></tr></thead>
          <tbody>${cats.categories.map(c => `<tr><td>${c.category.replace(/_/g,' ').replace(/\b\w/g,x=>x.toUpperCase())}</td><td><strong>${c.count}</strong></td></tr>`).join('')}</tbody></table></div>
        <div class="card"><div class="card-header"><h3>Events by Type</h3>
          <button class="btn btn-sm btn-outline" id="csv-evts">CSV</button></div>
          ${barChart(evts.event_types, 'type', 'count', evtMax)}
          <table><thead><tr><th>Event Type</th><th>Count</th></tr></thead>
          <tbody>${evts.event_types.map(e => `<tr><td>${e.type.replace(/_/g,' ').replace(/\b\w/g,x=>x.toUpperCase())}</td><td><strong>${e.count}</strong></td></tr>`).join('')}</tbody></table></div>
        <div class="card"><div class="card-header"><h3>Certificates by Status</h3>
          <button class="btn btn-sm btn-outline" id="csv-certs">CSV</button></div>
          ${barChart(certs.statuses, 'status', 'count', certMax)}
          <table><thead><tr><th>Status</th><th>Count</th></tr></thead>
          <tbody>${certs.statuses.map(s => `<tr><td><span class="badge ${s.status==='verified'?'badge-success':s.status==='issued'?'badge-info':s.status==='revoked'?'badge-danger':'badge-secondary'}">${s.status.toUpperCase()}</span></td><td><strong>${s.count}</strong></td></tr>`).join('')}</tbody></table></div>
      </div>`;
    body.querySelector('#csv-cats')?.addEventListener('click', () => UI.exportCSV(cats.categories, 'category', 'count', 'categories.csv'));
    body.querySelector('#csv-evts')?.addEventListener('click', () => UI.exportCSV(evts.event_types, 'type', 'count', 'events.csv'));
    body.querySelector('#csv-certs')?.addEventListener('click', () => UI.exportCSV(certs.statuses, 'status', 'count', 'certificates.csv'));
    return body;
  }));
};

// ─── SHARE & SOCIAL ───────────────────────────────────────────

Pages.share = (app) => {
  app.appendChild(UI.layout('Share & Compare', async () => {
    const body = document.createElement('div');
    body.innerHTML = `
      <div class="card"><div class="card-header"><h3>Generate Share Links</h3></div>
        <div style="display:flex;gap:8px;max-width:500px"><input id="share-sku" class="fi" placeholder="Product SKU" style="flex:1"><button id="share-gen" class="btn btn-primary">Generate</button></div>
        <div id="share-result" style="margin-top:16px"></div></div>
      <div class="card" style="margin-top:20px"><div class="card-header"><h3>Peer Comparison</h3></div>
        <div style="display:flex;gap:8px;max-width:500px"><input id="peer-id" type="number" class="fi" placeholder="Product ID" style="flex:1"><button id="peer-btn" class="btn btn-accent">Compare</button></div>
        <div id="peer-result" style="margin-top:16px"></div></div>
      <div class="card" style="margin-top:20px"><div class="card-header"><h3>Camera Scanner</h3></div>
        <div class="scanner-container">
          <video id="scanner-video" autoplay playsinline></video>
          <div id="scan-indicator" class="scanning-indicator" style="display:none"></div>
          <div style="margin-top:12px"><button id="scan-start" class="btn btn-primary">Start Camera</button>
          <button id="scan-stop" class="btn btn-outline" style="display:none">Stop</button></div>
          <div id="scan-result" style="margin-top:12px"></div>
        </div></div>`;
    body.querySelector('#share-gen').onclick = async () => {
      if (!UI.validateForm({ 'share-sku': { required: true, message: 'SKU required' } })) return;
      const sku = document.getElementById('share-sku').value.trim();
      try {
        const prods = await API.get('/products');
        const prod = prods.products.find(p => p.sku === sku);
        if (!prod) { UI.showError('Product not found'); return; }
        const data = await API.post('/share/generate-link', { product_id: prod.id });
        document.getElementById('share-result').innerHTML = `
          <div class="scan-result">
            <h4>${data.product_name} (${data.product_sku})</h4>
            <code style="display:block;padding:8px;background:#f1f5f3;border-radius:4px;margin:8px 0;word-break:break-all">${data.share_url}</code>
            <div class="share-bar">
              ${Object.entries(data.social_links).filter(([k]) => k !== 'share_url').map(([platform, url]) =>
                `<a href="${url}" target="_blank" class="share-btn share-${platform}">${platform.charAt(0).toUpperCase()+platform.slice(1)}</a>`
              ).join('')}
            </div>
          </div>`;
      } catch (e) { UI.showError(e.message); }
    };
    body.querySelector('#peer-btn').onclick = async () => {
      if (!UI.validateForm({ 'peer-id': { required: true, pattern: /^\d+$/, message: 'Valid product ID required' } })) return;
      const pid = document.getElementById('peer-id').value.trim();
      try {
        const data = await API.get(`/share/peer-compare/${pid}`);
        const p = data.product;
        document.getElementById('peer-result').innerHTML = `
          <div class="scan-result">
            <h4>${p.name} (${p.sku})</h4>
            <p style="color:#6b7280">Origin: ${p.origin || '—'} · Producer: ${p.producer}</p>
            ${data.peers.length > 0 ? `<h5 style="margin:12px 0 8px">Similar Products</h5>
              <div class="table-container"><table><thead><tr><th>SKU</th><th>Name</th><th>Producer</th><th>Origin</th></tr></thead>
              <tbody>${data.peers.map(peer => `<tr><td>${peer.sku}</td><td>${peer.name}</td><td>${peer.producer}</td><td>${peer.origin||'—'}</td></tr>`).join('')}</tbody></table></div>`
              : '<p style="margin-top:8px;color:#6b7280">No peers found for comparison</p>'}
          </div>`;
      } catch (e) { UI.showError(e.message); }
    };
    let scanTimer = null;

    const loadJsQR = () => {
      return new Promise((resolve, reject) => {
        if (window.jsQR) return resolve();
        const s = document.createElement('script');
        s.src = 'https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.min.js';
        s.onload = () => resolve();
        s.onerror = () => reject(new Error('Failed to load QR decoder'));
        document.head.appendChild(s);
      });
    };

    const stopScanning = () => {
      if (scanTimer) { clearInterval(scanTimer); scanTimer = null; }
      const video = document.getElementById('scanner-video');
      if (video && video.srcObject) { video.srcObject.getTracks().forEach(t => t.stop()); video.srcObject = null; }
      document.getElementById('scan-start').style.display = '';
      document.getElementById('scan-stop').style.display = 'none';
      document.getElementById('scan-indicator').style.display = 'none';
      document.getElementById('scan-result').innerHTML = '';
    };

    const detectFrame = async (video, canvas) => {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0);

      if ('BarcodeDetector' in window) {
        const detector = new BarcodeDetector({ formats: ['qr_code', 'ean_13', 'ean_8', 'code_128', 'code_39', 'upc_a', 'upc_e'] });
        const barcodes = await detector.detect(canvas);
        if (barcodes.length > 0) return barcodes[0].rawValue;
      } else {
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const code = jsQR(imageData.data, imageData.width, imageData.height, { inversionAttempts: 'dontInvert' });
        if (code && code.data) return code.data;
      }
      return null;
    };

    const handleScanResult = async (code) => {
      stopScanning();
      const resultDiv = document.getElementById('scan-result');
      resultDiv.innerHTML = `<p style="color:#155724;background:#d4edda;padding:8px;border-radius:4px">Scanned: <strong>${code}</strong></p>
        <div style="margin-top:8px"><button class="btn btn-primary" id="scan-lookup">Look Up Product</button></div>`;
      document.getElementById('scan-lookup').onclick = async () => {
        try {
          const prods = await API.get('/products');
          const match = prods.products.find(p => p.sku === code || String(p.id) === code);
          if (match) {
            Router.navigate(`#product/${match.id}`);
          } else {
            const trace = await API.get(`/traceability/scan/${code}`);
            if (trace.product) {
              Router.navigate(`#product/${trace.product.id}`);
            } else {
              UI.showError('Product not found for code: ' + code);
            }
          }
        } catch (e) {
          UI.showError('Lookup failed: ' + e.message);
        }
      };
    };

    body.querySelector('#scan-start').onclick = async () => {
      try {
        if (!('BarcodeDetector' in window)) await loadJsQR();
        const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
        const video = document.getElementById('scanner-video');
        video.srcObject = stream;
        document.getElementById('scan-start').style.display = 'none';
        document.getElementById('scan-stop').style.display = '';
        document.getElementById('scan-indicator').style.display = '';
        const canvas = document.createElement('canvas');
        canvas.style.display = 'none';
        document.body.appendChild(canvas);

        await new Promise(resolve => { video.onloadedmetadata = resolve; });
        video.play();

        scanTimer = setInterval(async () => {
          if (video.readyState < 2) return;
          try {
            const code = await detectFrame(video, canvas);
            if (code) {
              clearInterval(scanTimer);
              scanTimer = null;
              await handleScanResult(code);
            }
          } catch (e) { /* frame skip */ }
        }, 500);
      } catch (e) { UI.showError('Camera access denied: ' + e.message); }
    };

    body.querySelector('#scan-stop').onclick = stopScanning;
    return body;
  }));
};

// ─── SETTINGS + ADMIN PANEL ───────────────────────────────────

Pages.settings = (app) => {
  if (!Auth.isLoggedIn()) {
    Router.navigate('#login');
    return;
  }
  app.appendChild(UI.layout('Settings', async () => {
    const me = await API.get('/auth/me');
    const isAdmin = me.role === 'admin' || me.role === 'superuser';
    let usersData = null;
    if (isAdmin) {
      try { usersData = await API.get('/auth/users'); } catch(e) { /* silent fail */ }
    }
    const body = document.createElement('div');
    const roleBadge = me.role === 'superuser' ? 'badge-danger' : me.role === 'admin' ? 'badge-danger' : me.role === 'enterprise' ? 'badge-warning' : 'badge-info';
    const verified = (v) => v ? '<span class="badge badge-success">Verified ✓</span>' : '<span class="badge badge-secondary">Unverified</span>';
    body.innerHTML = `
      <div class="card"><div class="card-header"><h3>👤 Account</h3>
        <button class="btn btn-sm btn-outline" id="edit-profile-btn">Edit Profile</button></div>
        <table style="width:100%;font-size:14px">${[
          ['Name', me.full_name], ['Email', me.email], ['Company', me.company||'—'], ['Phone', me.phone||'—'],
          ['Alternate Email', me.alternate_email||'—'], ['Alternate Phone', me.alternate_phone||'—'],
          ['Email Verified', verified(me.email_verified)], ['Phone Verified', verified(me.phone_verified)],
          ['Role', `<span class="badge ${roleBadge}">${me.role.toUpperCase()}</span>`],
        ].map(([k,v]) => `<tr><td style="padding:6px 0;color:#6b7280;width:150px">${k}</td><td style="padding:6px 0"><strong>${v}</strong></td></tr>`).join('')}</table></div>
      <div class="card" style="margin-top:20px"><div class="card-header"><h3>✅ Verification</h3></div>
        <div class="verification-grid">
          <div class="verify-box">
            <strong>Email</strong>
            <div>${me.email} ${verified(me.email_verified)}</div>
            <button class="btn btn-outline btn-sm" id="send-email-otp" ${me.email_verified ? 'disabled' : ''}>${me.email_verified ? 'Verified' : 'Send Code'}</button>
            <div id="email-verify-box" style="display:none;margin-top:8px">
              <div style="display:flex;gap:8px;max-width:280px">
                <input id="email-otp-code" class="fi" placeholder="Enter code" maxlength="8" style="flex:1">
                <button class="btn btn-primary btn-sm" id="confirm-email-otp">Verify</button>
              </div>
              <p id="email-otp-hint" class="verify-hint"></p>
            </div>
          </div>
          <div class="verify-box">
            <strong>Phone</strong>
            <div>${me.phone||'No phone on file'} ${verified(me.phone_verified)}</div>
            <button class="btn btn-outline btn-sm" id="send-phone-otp" ${me.phone_verified || !me.phone ? 'disabled' : ''}>${me.phone_verified ? 'Verified' : 'Send Code'}</button>
            <div id="phone-verify-box" style="display:none;margin-top:8px">
              <div style="display:flex;gap:8px;max-width:280px">
                <input id="phone-otp-code" class="fi" placeholder="Enter code" maxlength="8" style="flex:1">
                <button class="btn btn-primary btn-sm" id="confirm-phone-otp">Verify</button>
              </div>
              <p id="phone-otp-hint" class="verify-hint"></p>
            </div>
          </div>
        </div></div>
      <div class="card" style="margin-top:20px"><div class="card-header"><h3>🔐 Security</h3></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <button class="btn btn-outline" onclick="Pages.setupTOTP()">Setup TOTP (Authenticator)</button>
          <button class="btn btn-outline" onclick="Pages.showChangePassword()">Change Password</button>
        </div>
        <div id="totp-setup" style="margin-top:16px"></div></div>
      <div class="card" style="margin-top:20px"><div class="card-header"><h3>🎨 Appearance</h3></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <button class="btn btn-outline" id="dark-toggle">${document.body.classList.contains('dark') ? '☀️ Light Mode' : '🌙 Dark Mode'}</button>
        </div></div>
      ${isAdmin ? `
      <div class="card" style="margin-top:20px;border-color:var(--danger)">
        <div class="card-header"><h3>🛡️ Admin — User Management</h3>
          <span class="badge badge-danger">${me.role.toUpperCase()}</span>
        </div>
        <div id="admin-users-list">${renderAdminUsers(usersData, me.role)}</div>
      </div>` : ''}`;
    body.querySelector('#edit-profile-btn').onclick = () => Pages.showEditProfile(me);
    body.querySelector('#dark-toggle').onclick = () => {
      document.body.classList.toggle('dark');
      const isDark = document.body.classList.contains('dark');
      localStorage.setItem('ft_dark', isDark ? '1' : '0');
      document.getElementById('dark-toggle').textContent = isDark ? '☀️ Light Mode' : '🌙 Dark Mode';
    };
    body.querySelector('#send-email-otp')?.addEventListener('click', async () => {
      try {
        const r = await Auth.requestEmailOtp();
        document.getElementById('email-verify-box').style.display = 'block';
        document.getElementById('email-otp-hint').textContent =
          (r.dev_code ? 'Dev code: ' + r.dev_code + ' — ' : '') + r.message;
      } catch (e) { UI.showError(e.message); }
    });
    body.querySelector('#confirm-email-otp')?.addEventListener('click', async () => {
      try {
        await Auth.verifyEmail(document.getElementById('email-otp-code').value);
        UI.showSuccess('Email verified');
        Router.navigate('#settings');
      } catch (e) { UI.showError(e.message); }
    });
    body.querySelector('#send-phone-otp')?.addEventListener('click', async () => {
      try {
        const r = await Auth.requestPhoneOtp();
        document.getElementById('phone-verify-box').style.display = 'block';
        document.getElementById('phone-otp-hint').textContent =
          (r.dev_code ? 'Dev code: ' + r.dev_code + ' — ' : '') + r.message;
      } catch (e) { UI.showError(e.message); }
    });
    body.querySelector('#confirm-phone-otp')?.addEventListener('click', async () => {
      try {
        await Auth.verifyPhone(document.getElementById('phone-otp-code').value);
        UI.showSuccess('Phone verified');
        Router.navigate('#settings');
      } catch (e) { UI.showError(e.message); }
    });
    if (isAdmin) {
      document.querySelectorAll('.admin-toggle-active').forEach(btn => {
        btn.addEventListener('click', async () => {
          const uid = parseInt(btn.dataset.userId);
          try {
            await API.post(`/auth/users/${uid}/toggle-active`);
            UI.showSuccess('User status toggled');
            Router.navigate('#settings');
          } catch(e) { UI.showError(e.message); }
        });
      });
      document.querySelectorAll('.admin-set-role').forEach(sel => {
        sel.addEventListener('change', async () => {
          const uid = parseInt(sel.dataset.userId);
          const role = sel.value;
          try {
            await API.put('/auth/users/role', { user_id: uid, role });
            UI.showSuccess(`Role changed to ${role}`);
          } catch(e) { UI.showError(e.message); }
        });
      });
    }
    return body;
  }));
};

function renderAdminUsers(data, callerRole) {
  if (!data || !data.users || data.users.length === 0) {
    return '<p style="color:var(--text-light);padding:12px 0">No users found or insufficient permissions.</p>';
  }
  return '<div class="table-container"><table><thead><tr>' +
    '<th>ID</th><th>Name</th><th>Email</th><th>Role</th><th>Active</th><th>MFA</th><th>Actions</th>' +
    '</tr></thead><tbody>' + data.users.map(u => {
      const roleCls = u.role === 'superuser' ? 'badge-danger' : u.role === 'admin' ? 'badge-danger' : u.role === 'enterprise' ? 'badge-warning' : u.role === 'verifier' ? 'badge-info' : 'badge-secondary';
      const canChangeRole = callerRole === 'superuser' || u.role !== 'superuser';
      return '<tr><td>' + u.id + '</td><td><strong>' + u.full_name + '</strong></td><td>' + u.email + '</td>' +
        '<td><span class="badge ' + roleCls + '">' + u.role + '</span></td>' +
        '<td>' + (u.is_active ? '<span class="badge badge-success">Active</span>' : '<span class="badge badge-danger">Inactive</span>') + '</td>' +
        '<td>' + (u.totp_enabled ? '<span class="badge badge-success">🔐</span>' : '<span class="badge badge-secondary">—</span>') + '</td>' +
        '<td><div style="display:flex;gap:4px;flex-wrap:wrap">' +
        (canChangeRole
          ? '<select class="fi admin-set-role" data-user-id="' + u.id + '" style="width:auto;padding:2px 6px;font-size:12px">' +
            ['superuser','admin','enterprise','verifier','viewer'].map(r => '<option value="' + r + '"' + (r === u.role ? ' selected' : '') + '>' + r + '</option>').join('') +
            '</select>'
          : '<span class="badge badge-secondary">—</span>') +
        '<button class="btn btn-sm btn-outline admin-toggle-active" data-user-id="' + u.id + '">' + (u.is_active ? '🔒 Deactivate' : '🔓 Activate') + '</button>' +
        '</div></td></tr>';
    }).join('') + '</tbody></table></div>' +
    '<p style="font-size:12px;color:var(--text-light);margin-top:8px">Page ' + data.page + ' of ' + data.total_pages + ' · ' + data.total + ' total users</p>';
}

Pages.showEditProfile = (me) => {
  const m = UI.modal('Edit Profile', `
    <div class="form-group"><label>Full Name</label><input id="ep-name" class="fi" value="${me.name}"></div>
    <div class="form-group"><label>Company</label><input id="ep-co" class="fi" value="${me.company||''}"></div>
    <div class="form-group"><label>Phone</label><input id="ep-phone" class="fi" type="tel" value="${me.phone||''}"></div>
  `);
  m.actions.appendChild(UI.btn('Cancel', 'btn-outline', m.close));
  m.actions.appendChild(UI.btn('Save', 'btn-primary', async (btn) => {
    if (!UI.validateForm({ 'ep-name': { required: true, message: 'Name required' } })) return;
    btn.disabled = true;
    try {
      const updated = await API.put('/auth/me', {
        full_name: document.getElementById('ep-name').value,
        company: document.getElementById('ep-co').value || null,
        phone: document.getElementById('ep-phone').value || null,
      });
      m.close();
      UI.showSuccess('Profile updated');
      const user = Auth.getUser();
      if (user) { user.name = updated.name; localStorage.setItem('ft_user', JSON.stringify(user)); }
      Router.navigate('#settings');
    } catch (e) { UI.showError(e.message); btn.disabled = false; }
  }));
};

Pages.showChangePassword = () => {
  const m = UI.modal('Change Password', `
    <div class="form-group"><label>Current Password</label><input id="cp-old" class="fi" type="password"></div>
    <div class="form-group"><label>New Password</label><input id="cp-new" class="fi" type="password" placeholder="Min 8 characters"></div>
    <div class="form-group"><label>Confirm New Password</label><input id="cp-confirm" class="fi" type="password"></div>
  `);
  m.actions.appendChild(UI.btn('Cancel', 'btn-outline', m.close));
  m.actions.appendChild(UI.btn('Change Password', 'btn-primary', async (btn) => {
    if (!UI.validateForm({
      'cp-old': { required: true, message: 'Current password required' },
      'cp-new': { required: true, minLength: 8, message: 'New password min 8 characters' },
      'cp-confirm': { required: true, match: 'cp-new', message: 'Passwords must match' },
    })) return;
    btn.disabled = true;
    try {
      await API.post('/auth/change-password', {
        old_password: document.getElementById('cp-old').value,
        new_password: document.getElementById('cp-new').value,
      });
      m.close();
      UI.showSuccess('Password changed');
    } catch (e) { UI.showError(e.message); btn.disabled = false; }
  }));
};

// ─── ENHANCED SEARCH PAGE ─────────────────────────────────────────

Pages.search = (app, query) => {
  const isAuth = Auth.isLoggedIn();
  const layoutFn = isAuth ? UI.layout : (bodyFn) => UI.publicLayout(bodyFn);
  const title = query ? `Search: ${query}` : 'Search';
  app.appendChild(layoutFn(title, async () => {
    const body = document.createElement('div');
    const q = query || '';
    body.innerHTML = `
      <div class="card">
        <form id="search-form" style="display:flex;gap:8px">
          <div class="autocomplete-wrap" style="flex:1">
            <input id="search-input" class="fi" placeholder="Search taxonomy items, products, batches, warehouses, collections..." style="width:100%" value="${q.replace(/"/g, '"')}">
          </div>
          <button class="btn btn-primary" id="search-btn">🔍 Search</button>
        </form>
        <div class="search-filters" id="search-filters" style="margin-top:12px;display:none;flex-wrap:wrap;gap:6px">
          <button class="filter-btn active" data-type="">✨ All</button>
          <button class="filter-btn" data-type="items">🌿 Taxonomy</button>
          <button class="filter-btn" data-type="products">📦 Products</button>
          <button class="filter-btn" data-type="batches">🏷️ Batches</button>
          <button class="filter-btn" data-type="warehouses">🏭 Warehouses</button>
          <button class="filter-btn" data-type="certificates">📜 Certificates</button>
          <button class="filter-btn" data-type="collections">📚 Collections</button>
        </div>
        <div id="search-facets" class="search-filters" style="margin-top:8px;display:none"></div>
      </div>
      <div id="search-results" style="margin-top:16px"></div>
      <div id="search-pagination" class="pagination"></div>`;

    let currentFilter = '';
    let currentPage = 1;

    // Autocomplete on search page
    const searchInput = body.querySelector('#search-input');
    let acTimeout = null;
    searchInput.addEventListener('input', () => {
      clearTimeout(acTimeout);
      // Autocomplete handled by global UI.autocompleteSearchInput, but page search is manual
    });
    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); doSearch(1); }
    });

    body.querySelector('#search-form').onsubmit = (e) => { e.preventDefault(); doSearch(1); };
    body.querySelector('#search-btn').onclick = () => doSearch(1);

    async function doSearch(page) {
      const val = document.getElementById('search-input').value.trim();
      if (!val) return;
      currentPage = page;
      document.getElementById('search-filters').style.display = '';
      const resultsEl = document.getElementById('search-results');
      const paginationEl = document.getElementById('search-pagination');
      const facetsEl = document.getElementById('search-facets');
      resultsEl.innerHTML = '<div class="spinner" style="margin:40px auto"></div>';
      paginationEl.innerHTML = '';
      facetsEl.style.display = 'none';
      try {
        const params = new URLSearchParams({ q: val, page: String(page) });
        if (currentFilter) params.set('entity_type', currentFilter);
        const data = await API.get('/search?' + params.toString());
        renderResults(data, resultsEl, paginationEl, facetsEl, val);
        _setSEO(`Search: ${val} — FoodTrack`, `${data.total} results found for "${val}"`);
      } catch (e) { resultsEl.innerHTML = `<p style="color:var(--danger);text-align:center">${e.message}</p>`; }
    }

    function renderResults(data, resultsEl, paginationEl, facetsEl, query) {
      if (!data.results || data.results.length === 0) {
        const suggestion = data.suggestion ? `<p style="margin-top:8px">Did you mean <a href="#" onclick="document.getElementById('search-input').value='${data.suggestion}';doSearch(1);return false"><strong>${data.suggestion}</strong></a>?</p>` : '';
        resultsEl.innerHTML = `<div class="empty-state"><div class="icon">🔍</div><h3>No results found</h3><p style="color:var(--text-light)">Try a different search term</p>${suggestion}</div>`;
        return;
      }

      // Facets
      if (data.facets && Object.keys(data.facets.types).length > 1) {
        let fhtml = '<strong style="font-size:13px;color:var(--text-light);margin-right:8px">Types:</strong>';
        Object.entries(data.facets.types).forEach(([type, count]) => {
          const label = { taxonomy_item: '🌿 Taxonomy', product: '📦 Products', batch: '🏷️ Batches', warehouse: '🏭 Warehouses', certificate: '📜 Certificates', collection: '📚 Collections' }[type] || type;
          fhtml += `<span class="search-badge" style="background:var(--primary);cursor:default;margin:2px">${label} (${count})</span> `;
        });
        facetsEl.innerHTML = fhtml;
        facetsEl.style.display = '';
      }

      let html = `<p style="font-size:14px;color:var(--text-light);margin-bottom:12px">${data.total} result(s) for "<strong>${query}</strong>" ${_getScoreStars(10)}</p>`;
      data.results.forEach(r => {
        const typeBadge = _getTypeBadge(r.type);
        const stars = _getScoreStars(r.score);
        let extraHtml = '';
        if (r.extra) {
          if (r.extra.phylum) extraHtml += `<span class="taxonomy-badge phylum">Phylum: ${r.extra.phylum}</span> `;
          if (r.extra.family) extraHtml += `<span class="taxonomy-badge family">Family: ${r.extra.family}</span> `;
          if (r.extra.gestation && r.extra.gestation !== ' ') extraHtml += `<span class="search-badge" style="background:#6b7280">Gestation: ${r.extra.gestation}</span> `;
          if (r.extra.local_uses) extraHtml += `<span style="font-size:12px;color:var(--text-light)">Uses: ${r.extra.local_uses.substring(0, 80)}</span> `;
          if (r.extra.scientific_name) extraHtml += `<span class="search-badge" style="background:#6b7280"><em>${r.extra.scientific_name}</em></span> `;
          if (r.extra.status) extraHtml += `<span class="search-badge">${r.extra.status}</span> `;
          if (r.extra.producer) extraHtml += `<span style="font-size:12px;color:var(--text-light)">${r.extra.producer}</span> `;
        }
        html += `<div class="search-result-card" onclick="Router.navigate('${r.url}')">
          <div style="flex:1">
            <div class="search-result-type"><span class="search-badge" style="background:var(--primary)">${typeBadge}</span> ${stars} ${r.category || ''}</div>
            <div class="search-result-title">${r.title}</div>
            <div class="search-result-sub">${r.subtitle ? '<strong>' + r.subtitle + '</strong> ' : ''}${r.description || ''}</div>
            <div style="margin-top:4px">${extraHtml}</div>
          </div>
          ${r.image_url ? `<img src="${r.image_url}" style="width:60px;height:60px;object-fit:cover;border-radius:4px" alt="">` : ''}
        </div>`;
      });
      resultsEl.innerHTML = html;

      // Pagination
      if (data.total_pages > 1) {
        let phtml = '';
        phtml += `<button class="page-btn" ${currentPage <= 1 ? 'disabled' : ''} data-p="${Math.max(1, currentPage - 1)}">← Prev</button>`;
        const start = Math.max(1, currentPage - 3);
        const end = Math.min(data.total_pages, currentPage + 3);
        if (start > 1) { phtml += `<button class="page-btn" data-p="1">1</button>`; if (start > 2) phtml += `<span class="page-btn" style="border:none;cursor:default">…</span>`; }
        for (let i = start; i <= end; i++) {
          phtml += `<button class="page-btn ${i === currentPage ? 'active' : ''}" data-p="${i}">${i}</button>`;
        }
        if (end < data.total_pages) { if (end < data.total_pages - 1) phtml += `<span class="page-btn" style="border:none;cursor:default">…</span>`; phtml += `<button class="page-btn" data-p="${data.total_pages}">${data.total_pages}</button>`; }
        phtml += `<button class="page-btn" ${currentPage >= data.total_pages ? 'disabled' : ''} data-p="${currentPage + 1}">Next →</button>`;
        paginationEl.innerHTML = phtml;
        paginationEl.querySelectorAll('.page-btn:not(:disabled):not([style])').forEach(btn => {
          btn.addEventListener('click', () => doSearch(parseInt(btn.dataset.p)));
        });
      }
    }

    body.querySelector('#search-filters').addEventListener('click', (e) => {
      const btn = e.target.closest('.filter-btn');
      if (!btn) return;
      document.querySelectorAll('#search-filters .filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentFilter = btn.dataset.type;
      doSearch(1);
    });

    if (q) { body.querySelector('#search-btn').click(); }
    return body;
  }));
};

// ─── ENHANCED TAXONOMY ITEM DETAIL ─────────────────────────────

Pages.taxonomyItemDetail = (app, id) => {
  app.appendChild(UI.layout('Taxonomy Item', async () => {
    const item = await API.get(`/taxonomy/items/${id}`);
    const body = document.createElement('div');
    body.innerHTML = `
      <div class="card">
        <div class="card-header"><h3>${item.common_name}</h3>
          <span class="badge badge-info">${item.code}</span>
        </div>
        <div class="inv-grid">
          <div>
            <div class="info-row"><div class="info-label">Scientific Name</div><div class="info-value"><em>${item.scientific_name || '—'}</em></div></div>
            <div class="info-row"><div class="info-label">Genre</div><div class="info-value">${item.genre || '—'}</div></div>
            <div class="info-row"><div class="info-label">Phylum</div><div class="info-value">${item.phylum || '—'}</div></div>
            <div class="info-row"><div class="info-label">Class</div><div class="info-value">${item.tax_class || '—'}</div></div>
            <div class="info-row"><div class="info-label">Order</div><div class="info-value">${item.order_name || '—'}</div></div>
            <div class="info-row"><div class="info-label">Family</div><div class="info-value">${item.family || '—'}</div></div>
          </div>
          <div>
            <div class="info-row"><div class="info-label">Gestation Period</div><div class="info-value">${item.gestation_period ? item.gestation_period + ' ' + (item.gestation_unit || '') : '—'}</div></div>
            <div class="info-row"><div class="info-label">Local Uses</div><div class="info-value">${item.local_uses || '—'}</div></div>
            <div class="info-row"><div class="info-label">Description</div><div class="info-value">${item.description || '—'}</div></div>
            ${item.image_url ? `<div style="margin-top:8px"><img src="${item.image_url}" style="max-width:200px;border-radius:4px" alt=""></div>` : ''}
          </div>
        </div>
      </div>
      <div class="card" style="margin-top:16px">
        <div class="card-header"><h3>Multilingual Names</h3></div>
        <div id="item-names">${(item.names || []).map(n => `<div style="display:flex;gap:8px;padding:4px 0"><span style="font-weight:600;width:100px">${n.language.toUpperCase()}</span><span>${n.name}${n.is_primary ? ' ⭐' : ''}</span></div>`).join('') || '<p style="color:var(--text-light)">No names</p>'}</div>
      </div>
      <div class="card" style="margin-top:16px">
        <div class="card-header"><h3>Attributes</h3></div>
        <div id="item-attrs">${(item.attributes || []).map(a => `<div style="display:flex;gap:8px;padding:4px 0"><span style="font-weight:600;width:160px">${a.key}</span><span>${a.value || ''}${a.unit ? ' ' + a.unit : ''}</span></div>`).join('') || '<p style="color:var(--text-light)">No attributes</p>'}</div>
      </div>`;
    return body;
  }));
};

// ─── BATCHES ────────────────────────────────────────────────────

Pages.batches = (app) => {
  app.appendChild(UI.layout('Batches', async () => {
    const body = document.createElement('div');
    body.innerHTML = '<div id="batches-content"><div class="spinner"></div></div>';
    const load = async (page = 1) => {
      const data = await API.get('/batches?page=' + page);
      const el = document.getElementById('batches-content');
      let html = `<div class="list-header">
        <p style="color:var(--text-light)">${data.total} batch(es)</p>
        <button class="btn btn-primary btn-sm" id="add-batch-btn">+ New Batch</button></div>`;
      if (!data.batches || data.batches.length === 0) {
        html += '<div class="empty-state"><p>No batches yet</p></div>';
      } else {
        html += '<div class="table-container"><table><thead><tr><th>Batch #</th><th>Product</th><th>Qty</th><th>Serial / MPN</th><th>Status</th><th>Locations</th><th>Actions</th></tr></thead><tbody>';
        data.batches.forEach(b => {
          const idStr = [b.serial_number, b.manufacturer_part_number].filter(Boolean).join(' · ') || '—';
          html += `<tr><td><strong>${b.batch_number}</strong></td><td>${b.product_name || b.product_sku}</td><td>${b.quantity}</td>
            <td style="font-size:12px;max-width:160px;overflow:hidden;text-overflow:ellipsis">${idStr}</td>
            <td><span class="badge ${b.status === 'active' ? 'badge-success' : b.status === 'recalled' ? 'badge-danger' : 'badge-secondary'}">${b.status}</span></td>
            <td>${(b.locations || []).map(l => l.warehouse_name).join(', ') || '—'}</td>
            <td><a href="#batches/${b.id}" class="btn btn-sm btn-outline">View</a></td></tr>`;
        });
        html += '</tbody></table></div>';
        if (data.total_pages > 1) {
          html += '<div class="pagination">';
          for (let i = 1; i <= data.total_pages; i++) {
            html += `<button class="page-btn ${i === page ? 'active' : ''}" data-p="${i}">${i}</button>`;
          }
          html += '</div>';
        }
      }
      el.innerHTML = html;
      el.querySelectorAll('.page-btn:not(.active)').forEach(b => b.addEventListener('click', () => load(parseInt(b.dataset.p))));
      document.getElementById('add-batch-btn')?.addEventListener('click', showAddBatch);
    };
    load();
    return body;
  }));
};

function showAddBatch() {
  const m = UI.modal('New Batch', `
    <div class="form-group"><label>Batch Number</label><input id="b-num" class="fi" placeholder="e.g. BATCH-2026-001"></div>
    <div class="form-group"><label>Product ID</label><input id="b-pid" type="number" class="fi" placeholder="Product ID"></div>
    <div class="form-group"><label>Quantity</label><input id="b-qty" type="number" class="fi" placeholder="0"></div>
    <div class="form-row"><div class="form-group"><label>Serial Number</label><input id="b-serial" class="fi" placeholder="e.g. SN-001234"></div>
    <div class="form-group"><label>Mfr Part #</label><input id="b-mpn" class="fi" placeholder="e.g. MPN-9876"></div></div>
    <div class="form-row"><div class="form-group"><label>Production Date</label><input id="b-prod" type="date" class="fi"></div>
    <div class="form-group"><label>Expiry Date</label><input id="b-exp" type="date" class="fi"></div></div>
    <div class="form-group"><label>Notes</label><textarea id="b-notes" class="fi" rows="2"></textarea></div>`);
  m.actions.appendChild(UI.btn('Cancel', 'btn-outline', m.close));
  m.actions.appendChild(UI.btn('Create', 'btn-primary', async (btn) => {
    if (!UI.validateForm({ 'b-num': { required: true }, 'b-pid': { required: true, pattern: /^\d+$/ } })) return;
    btn.disabled = true;
    try {
      await API.post('/batches', {
        batch_number: document.getElementById('b-num').value,
        product_id: parseInt(document.getElementById('b-pid').value),
        quantity: parseInt(document.getElementById('b-qty').value) || 0,
        serial_number: document.getElementById('b-serial').value || null,
        manufacturer_part_number: document.getElementById('b-mpn').value || null,
        production_date: document.getElementById('b-prod').value || null,
        expiry_date: document.getElementById('b-exp').value || null,
        notes: document.getElementById('b-notes').value || null,
      });
      m.close(); UI.showSuccess('Batch created'); Router.navigate('#batches');
    } catch (e) { UI.showError(e.message); btn.disabled = false; }
  }));
}

Pages.batchDetail = (app, id) => {
  app.appendChild(UI.layout('Batch Detail', async () => {
    const data = await API.get(`/batches/${id}`);
    const body = document.createElement('div');
    const locs = (data.locations || []).map(l => `<div style="display:flex;gap:8px;padding:4px 0"><span class="zone-badge">${l.warehouse_name}</span><span>Qty: ${l.quantity}</span>${l.zone ? ' · Zone: ' + l.zone : ''}${l.rack ? ' · Rack: ' + l.rack : ''}</div>`).join('') || '<span style="color:var(--text-light)">Not stored in any warehouse</span>';
    body.innerHTML = `
      <div class="card">
        <div class="card-header"><h3>Batch ${data.batch_number}</h3>
          <span class="badge ${data.status === 'active' ? 'badge-success' : data.status === 'recalled' ? 'badge-danger' : 'badge-secondary'}">${data.status}</span>
        </div>
        <div class="info-row"><div class="info-label">Product</div><div class="info-value">${data.product_name} (${data.product_sku})</div></div>
        <div class="info-row"><div class="info-label">Quantity</div><div class="info-value">${data.quantity}</div></div>
        <div class="info-row"><div class="info-label">Serial Number</div><div class="info-value">${data.serial_number || '—'}</div></div>
        <div class="info-row"><div class="info-label">Mfr Part #</div><div class="info-value">${data.manufacturer_part_number || '—'}</div></div>
        <div class="info-row"><div class="info-label">Production Date</div><div class="info-value">${data.production_date ? new Date(data.production_date).toLocaleDateString() : '—'}</div></div>
        <div class="info-row"><div class="info-label">Expiry Date</div><div class="info-value">${data.expiry_date ? new Date(data.expiry_date).toLocaleDateString() : '—'}</div></div>
        <div class="info-row"><div class="info-label">Notes</div><div class="info-value">${data.notes || '—'}</div></div>
      </div>
      <div class="card" style="margin-top:16px">
        <div class="card-header"><h3>Warehouse Locations</h3></div>
        ${locs}
      </div>
      <div style="margin-top:16px;display:flex;gap:8px">
        <button class="btn btn-outline" onclick="Router.navigate('#batches')">Back to Batches</button>
        <a href="#product/${data.product_id}" class="btn btn-outline">View Product</a>
      </div>`;
    return body;
  }));
};

// ─── WAREHOUSES ─────────────────────────────────────────────────

Pages.warehouses = (app) => {
  app.appendChild(UI.layout('Warehouses', async () => {
    const body = document.createElement('div');
    body.innerHTML = '<div id="warehouses-content"><div class="spinner"></div></div>';
    const load = async (page = 1) => {
      const data = await API.get('/warehouses?page=' + page);
      const el = document.getElementById('warehouses-content');
      let html = `<div class="list-header">
        <p style="color:var(--text-light)">${data.total} warehouse(s)</p>
        <button class="btn btn-primary btn-sm" id="add-wh-btn">+ New Warehouse</button></div>
        <div class="card-grid card-grid-3">`;
      if (!data.warehouses || data.warehouses.length === 0) {
        html += '<p style="color:var(--text-light)">No warehouses yet</p>';
      } else {
        data.warehouses.forEach(w => {
          html += `<div class="card" style="cursor:pointer" onclick="Router.navigate('#warehouses/${w.id}')">
            <div class="card-header"><h3>${w.name}</h3><span class="badge badge-info">${w.code}</span></div>
            <p style="font-size:13px;color:var(--text-light)">${w.city || ''} ${w.country || ''}</p>
            <p style="font-size:13px;color:var(--text-light)">Items: ${w.item_count} · Cap: ${w.capacity_items || '—'}</p>
            ${w.temperature_celsius ? `<p style="font-size:13px;color:var(--text-light)">Temp: ${w.temperature_celsius}°C · RH: ${w.humidity_percent || '—'}%</p>` : ''}
          </div>`;
        });
      }
      html += '</div>';
      if (data.total_pages > 1) {
        html += '<div class="pagination">';
        for (let i = 1; i <= data.total_pages; i++) {
          html += `<button class="page-btn ${i === page ? 'active' : ''}" data-p="${i}">${i}</button>`;
        }
        html += '</div>';
      }
      el.innerHTML = html;
      el.querySelectorAll('.page-btn:not(.active)').forEach(b => b.addEventListener('click', () => load(parseInt(b.dataset.p))));
      document.getElementById('add-wh-btn')?.addEventListener('click', showAddWarehouse);
    };
    load();
    return body;
  }));
};

function showAddWarehouse() {
  const m = UI.modal('New Warehouse', `
    <div class="form-row"><div class="form-group"><label>Code</label><input id="wh-code" class="fi" placeholder="e.g. WH-DXB-01"></div>
    <div class="form-group"><label>Name</label><input id="wh-name" class="fi" placeholder="Dubai Cold Storage"></div></div>
    <div class="form-group"><label>Address</label><input id="wh-addr" class="fi" placeholder="Street address"></div>
    <div class="form-row"><div class="form-group"><label>City</label><input id="wh-city" class="fi" placeholder="Dubai"></div>
    <div class="form-group"><label>Country</label><input id="wh-country" class="fi" placeholder="UAE"></div></div>
    <div class="form-row"><div class="form-group"><label>Contact Name</label><input id="wh-contact" class="fi"></div>
    <div class="form-group"><label>Contact Phone</label><input id="wh-phone" class="fi"></div></div>
    <div class="form-row"><div class="form-group"><label>Capacity (items)</label><input id="wh-cap" type="number" class="fi"></div>
    <div class="form-group"><label>Temperature (°C)</label><input id="wh-temp" type="number" step="0.1" class="fi"></div></div>`);
  m.actions.appendChild(UI.btn('Cancel', 'btn-outline', m.close));
  m.actions.appendChild(UI.btn('Create', 'btn-primary', async (btn) => {
    if (!UI.validateForm({ 'wh-code': { required: true }, 'wh-name': { required: true } })) return;
    btn.disabled = true;
    try {
      await API.post('/warehouses', {
        code: document.getElementById('wh-code').value,
        name: document.getElementById('wh-name').value,
        address: document.getElementById('wh-addr').value || null,
        city: document.getElementById('wh-city').value || null,
        country: document.getElementById('wh-country').value || null,
        contact_name: document.getElementById('wh-contact').value || null,
        contact_phone: document.getElementById('wh-phone').value || null,
        capacity_items: parseInt(document.getElementById('wh-cap').value) || null,
        temperature_celsius: parseFloat(document.getElementById('wh-temp').value) || null,
      });
      m.close(); UI.showSuccess('Warehouse created'); Router.navigate('#warehouses');
    } catch (e) { UI.showError(e.message); btn.disabled = false; }
  }));
}

Pages.warehouseDetail = (app, id) => {
  app.appendChild(UI.layout('Warehouse Detail', async () => {
    const data = await API.get(`/warehouses/${id}`);
    const body = document.createElement('div');
    const itemsHtml = (data.items || []).map(i => `<tr><td>${i.batch_number}</td><td>${i.quantity}</td><td>${i.zone || '—'}</td><td>${i.rack || '—'}</td><td>${i.bin || '—'}</td><td>${i.last_counted_at ? new Date(i.last_counted_at).toLocaleDateString() : '—'}</td></tr>`).join('');
    body.innerHTML = `
      <div class="card">
        <div class="card-header"><h3>${data.name} (${data.code})</h3></div>
        <div class="info-row"><div class="info-label">Address</div><div class="info-value">${data.address || '—'}</div></div>
        <div class="info-row"><div class="info-label">City / Country</div><div class="info-value">${data.city || '—'}${data.country ? ', ' + data.country : ''}</div></div>
        <div class="info-row"><div class="info-label">Contact</div><div class="info-value">${data.contact_name || '—'} ${data.contact_phone ? '· ' + data.contact_phone : ''}</div></div>
        <div class="info-row"><div class="info-label">Capacity</div><div class="info-value">${data.capacity_items || '—'} items</div></div>
        <div class="info-row"><div class="info-label">Environment</div><div class="info-value">${data.temperature_celsius ? data.temperature_celsius + '°C' : '—'} / ${data.humidity_percent ? data.humidity_percent + '% RH' : '—'}</div></div>
      </div>
      <div class="card" style="margin-top:16px">
        <div class="card-header"><h3>Inventory (${(data.items || []).length} items)</h3>
        <button class="btn btn-sm btn-primary" id="add-inv-btn">+ Add Stock</button></div>
        <div class="table-container"><table><thead><tr><th>Batch</th><th>Qty</th><th>Zone</th><th>Rack</th><th>Bin</th><th>Last Counted</th></tr></thead>
        <tbody>${itemsHtml || '<tr><td colspan="6" style="text-align:center;color:var(--text-light)">No inventory</td></tr>'}</tbody></table></div>
      </div>
      <div style="margin-top:16px"><button class="btn btn-outline" onclick="Router.navigate('#warehouses')">Back to Warehouses</button></div>`;
    body.querySelector('#add-inv-btn')?.addEventListener('click', () => showAddInventory(id));
    return body;
  }));
};

function showAddInventory(warehouseId) {
  const m = UI.modal('Add Stock', `
    <div class="form-group"><label>Batch ID</label><input id="inv-batch" type="number" class="fi" placeholder="Batch ID"></div>
    <div class="form-group"><label>Quantity</label><input id="inv-qty" type="number" class="fi" placeholder="0"></div>
    <div class="form-row"><div class="form-group"><label>Zone</label><input id="inv-zone" class="fi" placeholder="e.g. A-1"></div>
    <div class="form-group"><label>Rack</label><input id="inv-rack" class="fi" placeholder="e.g. R-01"></div></div>
    <div class="form-group"><label>Bin</label><input id="inv-bin" class="fi" placeholder="e.g. B-001"></div>`);
  m.actions.appendChild(UI.btn('Cancel', 'btn-outline', m.close));
  m.actions.appendChild(UI.btn('Add', 'btn-primary', async (btn) => {
    if (!UI.validateForm({ 'inv-batch': { required: true, pattern: /^\d+$/ }, 'inv-qty': { required: true, pattern: /^\d+$/ } })) return;
    btn.disabled = true;
    try {
      await API.post(`/warehouses/${warehouseId}/items`, {
        batch_id: parseInt(document.getElementById('inv-batch').value),
        quantity: parseInt(document.getElementById('inv-qty').value),
        zone: document.getElementById('inv-zone').value || null,
        rack: document.getElementById('inv-rack').value || null,
        bin: document.getElementById('inv-bin').value || null,
      });
      m.close(); UI.showSuccess('Stock added'); Router.navigate('#warehouses/' + warehouseId);
    } catch (e) { UI.showError(e.message); btn.disabled = false; }
  }));
}

// ─── SHIPMENTS ──────────────────────────────────────────────────

Pages.shipments = (app) => {
  app.appendChild(UI.layout('Shipments', async () => {
    const body = document.createElement('div');
    body.innerHTML = '<div id="shipments-content"><div class="spinner"></div></div>';
    const load = async (page = 1) => {
      const data = await API.get('/shipments?page=' + page);
      const el = document.getElementById('shipments-content');
      let html = `<div class="list-header">
        <p style="color:var(--text-light)">${data.total} shipment(s)</p>
        <button class="btn btn-primary btn-sm" id="add-ship-btn">+ New Shipment</button></div>`;
      if (!data.shipments || data.shipments.length === 0) {
        html += '<div class="empty-state"><p>No shipments yet</p></div>';
      } else {
        html += '<div class="table-container"><table><thead><tr><th>Shipment #</th><th>Mode</th><th>Status</th><th>From</th><th>To</th><th>Carrier</th><th>Tracking</th><th>Actions</th></tr></thead><tbody>';
        data.shipments.forEach(s => {
          const statusCls = { 'delivered':'badge-success', 'in_transit':'badge-info', 'on_ferry':'badge-warning', 'exception':'badge-danger', 'created':'badge-secondary' };
          html += `<tr><td><strong>${s.shipment_number}</strong></td>
            <td><span class="badge badge-info">${s.mode}</span></td>
            <td><span class="badge ${statusCls[s.status] || 'badge-secondary'}">${s.status.replace(/_/g, ' ')}</span></td>
            <td>${s.origin_name || '—'}</td><td>${s.destination_name || '—'}</td>
            <td>${s.carrier_name || '—'}</td>
            <td>${s.courier_tracking_code ? `<span style="font-size:12px">${s.courier_tracking_code}</span>` : '—'}</td>
            <td><a href="#shipments/${s.id}" class="btn btn-sm btn-outline">View</a></td></tr>`;
        });
        html += '</tbody></table></div>';
        if (data.total_pages > 1) {
          html += '<div class="pagination">';
          for (let i = 1; i <= data.total_pages; i++) {
            html += `<button class="page-btn ${i === page ? 'active' : ''}" data-p="${i}">${i}</button>`;
          }
          html += '</div>';
        }
      }
      el.innerHTML = html;
      el.querySelectorAll('.page-btn:not(.active)').forEach(b => b.addEventListener('click', () => load(parseInt(b.dataset.p))));
      document.getElementById('add-ship-btn')?.addEventListener('click', showAddShipment);
    };
    load();
    return body;
  }));
};

function showAddShipment() {
  const m = UI.modal('New Shipment', `
    <div class="form-row"><div class="form-group"><label>Shipment Number</label><input id="s-num" class="fi" placeholder="SHP-001"></div>
    <div class="form-group"><label>Mode</label><select id="s-mode" class="fi"><option value="courier">Courier</option><option value="ferry">Ferry</option><option value="truck">Truck</option><option value="air">Air</option><option value="rail">Rail</option><option value="multimodal">Multimodal</option></select></div></div>
    <div class="form-row"><div class="form-group"><label>Origin Warehouse ID</label><input id="s-origin" type="number" class="fi"></div>
    <div class="form-group"><label>Destination WH ID</label><input id="s-dest" type="number" class="fi"></div></div>
    <div class="form-row"><div class="form-group"><label>Carrier Name</label><input id="s-carrier" class="fi" placeholder="e.g. DP World"></div>
    <div class="form-group"><label>Vessel / Ferry</label><input id="s-vessel" class="fi" placeholder="e.g. Al Marfa"></div></div>
    <div class="form-row"><div class="form-group"><label>Ferry Route</label><input id="s-route" class="fi" placeholder="e.g. Dubai-Bandar Abbas"></div>
    <div class="form-group"><label>Courier Tracking Code</label><input id="s-tracking" class="fi"></div></div>
    <div class="form-group"><label>Notes</label><textarea id="s-notes" class="fi" rows="2"></textarea></div>`);
  m.actions.appendChild(UI.btn('Cancel', 'btn-outline', m.close));
  m.actions.appendChild(UI.btn('Create', 'btn-primary', async (btn) => {
    if (!UI.validateForm({ 's-num': { required: true } })) return;
    btn.disabled = true;
    try {
      await API.post('/shipments', {
        shipment_number: document.getElementById('s-num').value,
        mode: document.getElementById('s-mode').value,
        origin_id: parseInt(document.getElementById('s-origin').value) || null,
        destination_id: parseInt(document.getElementById('s-dest').value) || null,
        carrier_name: document.getElementById('s-carrier').value || null,
        vessel_name: document.getElementById('s-vessel').value || null,
        ferry_route: document.getElementById('s-route').value || null,
        courier_tracking_code: document.getElementById('s-tracking').value || null,
        notes: document.getElementById('s-notes').value || null,
      });
      m.close(); UI.showSuccess('Shipment created'); Router.navigate('#shipments');
    } catch (e) { UI.showError(e.message); btn.disabled = false; }
  }));
}

Pages.shipmentDetail = (app, id) => {
  app.appendChild(UI.layout('Shipment Detail', async () => {
    const data = await API.get(`/shipments/${id}`);
    const body = document.createElement('div');
    const statusCls = { 'delivered':'badge-success', 'in_transit':'badge-info', 'on_ferry':'badge-warning', 'exception':'badge-danger', 'created':'badge-secondary', 'picked_up':'badge-info', 'at_ferry':'badge-warning', 'arrived_port':'badge-info', 'out_for_delivery':'badge-info' };
    const batchesHtml = (data.batches || []).map(b => `<tr><td><a href="#batches/${b.batch_id}">${b.batch_number}</a></td><td>${b.quantity}</td></tr>`).join('');
    const trackingHtml = (data.tracking_events || []).map(te => `<div class="tracking-item ${te.status === 'delivered' ? 'delivered' : te.status === 'exception' ? 'exception' : ''}">
      <div class="tt-status"><span class="badge ${statusCls[te.status] || 'badge-secondary'}">${te.status.replace(/_/g, ' ')}</span></div>
      <div class="tt-loc">${te.location_name || ''}</div>
      <div class="tt-time">${te.event_timestamp ? new Date(te.event_timestamp).toLocaleString() : ''}</div>
      ${te.message ? `<div style="font-size:13px;margin-top:2px">${te.message}</div>` : ''}
    </div>`).join('') || '<p style="color:var(--text-light)">No tracking events yet</p>';

    body.innerHTML = `
      <div class="card">
        <div class="card-header"><h3>${data.shipment_number}</h3>
          <span class="badge badge-info">${data.mode.toUpperCase()}</span>
          <span class="badge ${statusCls[data.status] || 'badge-secondary'}">${data.status.replace(/_/g, ' ')}</span>
        </div>
        <div class="info-row"><div class="info-label">Origin</div><div class="info-value">${data.origin ? data.origin.name + ' (' + (data.origin.city || '') + ')' : '—'}</div></div>
        <div class="info-row"><div class="info-label">Destination</div><div class="info-value">${data.destination ? data.destination.name + ' (' + (data.destination.city || '') + ')' : '—'}</div></div>
        <div class="info-row"><div class="info-label">Carrier</div><div class="info-value">${data.carrier_name || '—'} ${data.carrier_ref ? '· Ref: ' + data.carrier_ref : ''}</div></div>
        <div class="info-row"><div class="info-label">Vessel / Ferry</div><div class="info-value">${data.vessel_name || '—'} ${data.ferry_route ? '· Route: ' + data.ferry_route : ''}</div></div>
        <div class="info-row"><div class="info-label">Courier Tracking</div><div class="info-value">${data.courier_tracking_code ? data.courier_tracking_code + (data.courier_url ? ' · <a href="' + data.courier_url + '" target="_blank">Track</a>' : '') : '—'}</div></div>
        <div class="info-row"><div class="info-label">Weight / Volume</div><div class="info-value">${data.total_weight_kg ? data.total_weight_kg + ' kg' : '—'} / ${data.total_volume_m3 ? data.total_volume_m3 + ' m³' : '—'}</div></div>
        <div class="info-row"><div class="info-label">Est. Departure</div><div class="info-value">${data.estimated_departure ? new Date(data.estimated_departure).toLocaleString() : '—'}</div></div>
        <div class="info-row"><div class="info-label">Est. Arrival</div><div class="info-value">${data.estimated_arrival ? new Date(data.estimated_arrival).toLocaleString() : '—'}</div></div>
        ${data.actual_departure ? `<div class="info-row"><div class="info-label">Actual Departure</div><div class="info-value">${new Date(data.actual_departure).toLocaleString()}</div></div>` : ''}
        ${data.actual_arrival ? `<div class="info-row"><div class="info-label">Actual Arrival</div><div class="info-value">${new Date(data.actual_arrival).toLocaleString()}</div></div>` : ''}
        ${data.notes ? `<div class="info-row"><div class="info-label">Notes</div><div class="info-value">${data.notes}</div></div>` : ''}
      </div>
      <div class="inv-grid" style="margin-top:16px">
        <div class="card">
          <div class="card-header"><h3>Batches (${(data.batches || []).length})</h3>
          <button class="btn btn-sm btn-primary" id="add-batch-ship-btn">+ Add Batch</button></div>
          <div class="table-container"><table><thead><tr><th>Batch</th><th>Qty</th></tr></thead>
          <tbody>${batchesHtml || '<tr><td colspan="2" style="text-align:center;color:var(--text-light)">No batches</td></tr>'}</tbody></table></div>
        </div>
        <div class="card">
          <div class="card-header"><h3>Tracking (${(data.tracking_events || []).length})</h3>
          <button class="btn btn-sm btn-primary" id="add-tracking-btn">+ Add Event</button></div>
          <div class="tracking-timeline">${trackingHtml}</div>
        </div>
      </div>
      <div style="margin-top:16px;display:flex;gap:8px">
        <button class="btn btn-outline" onclick="Router.navigate('#shipments')">Back to Shipments</button>
        ${data.courier_url ? `<a href="${data.courier_url}" target="_blank" class="btn btn-accent">Track on Courier Site</a>` : ''}
      </div>`;
    body.querySelector('#add-batch-ship-btn')?.addEventListener('click', () => showAddBatchToShipment(id));
    body.querySelector('#add-tracking-btn')?.addEventListener('click', () => showAddTrackingEvent(id));
    return body;
  }));
};

function showAddBatchToShipment(shipmentId) {
  const m = UI.modal('Add Batch to Shipment', `
    <div class="form-group"><label>Batch ID</label><input id="sb-batch" type="number" class="fi"></div>
    <div class="form-group"><label>Quantity</label><input id="sb-qty" type="number" class="fi"></div>`);
  m.actions.appendChild(UI.btn('Cancel', 'btn-outline', m.close));
  m.actions.appendChild(UI.btn('Add', 'btn-primary', async (btn) => {
    if (!UI.validateForm({ 'sb-batch': { required: true, pattern: /^\d+$/ }, 'sb-qty': { required: true, pattern: /^\d+$/ } })) return;
    btn.disabled = true;
    try {
      await API.post(`/shipments/${shipmentId}/batches`, {
        batch_id: parseInt(document.getElementById('sb-batch').value),
        quantity: parseInt(document.getElementById('sb-qty').value),
      });
      m.close(); UI.showSuccess('Batch added'); Router.navigate('#shipments/' + shipmentId);
    } catch (e) { UI.showError(e.message); btn.disabled = false; }
  }));
}

function showAddTrackingEvent(shipmentId) {
  const m = UI.modal('Add Tracking Event', `
    <div class="form-group"><label>Status</label><select id="te-status" class="fi">
      <option value="picked_up">Picked Up</option><option value="in_transit">In Transit</option>
      <option value="at_ferry">At Ferry Terminal</option><option value="on_ferry">On Ferry</option>
      <option value="arrived_port">Arrived at Port</option><option value="out_for_delivery">Out for Delivery</option>
      <option value="delivered">Delivered</option><option value="exception">Exception</option>
    </select></div>
    <div class="form-group"><label>Location</label><input id="te-loc" class="fi" placeholder="City, port..."></div>
    <div class="form-group"><label>Message</label><textarea id="te-msg" class="fi" rows="2" placeholder="Status details..."></textarea></div>`);
  m.actions.appendChild(UI.btn('Cancel', 'btn-outline', m.close));
  m.actions.appendChild(UI.btn('Add Event', 'btn-primary', async (btn) => {
    btn.disabled = true;
    try {
      await API.post(`/shipments/${shipmentId}/tracking`, {
        status: document.getElementById('te-status').value,
        location_name: document.getElementById('te-loc').value || null,
        message: document.getElementById('te-msg').value || null,
      });
      m.close(); UI.showSuccess('Tracking event added'); Router.navigate('#shipments/' + shipmentId);
    } catch (e) { UI.showError(e.message); btn.disabled = false; }
  }));
}

// ─── COLLECTIONS (ENHANCED) ─────────────────────────────────────

Pages.collections = (app) => {
  app.appendChild(UI.layout('Collections', async () => {
    const data = await API.get('/collections');
    const body = document.createElement('div');
    let html = `<div class="list-header">
      <p style="color:var(--text-light)">${data.total} collection(s)</p>
      <div style="display:flex;gap:8px">
        <button class="btn btn-outline btn-sm" onclick="Router.navigate('#feeds')">🤖 AI Feeds</button>
        <button class="btn btn-primary btn-sm" id="add-col-btn">+ New Collection</button>
      </div></div>
      <div class="card-grid card-grid-3">`;
    if (!data.collections || data.collections.length === 0) {
      html += '<p style="color:var(--text-light)">No collections yet. Create one or configure an AI feed source.</p>';
    } else {
      data.collections.forEach(c => {
        const badges = [];
        if (c.is_ai_generated) badges.push('<span class="badge badge-info">🤖 AI</span>');
        const desc = (c.description || '').substring(0, 120);
        html += `<div class="collection-card" onclick="Router.navigate('#collections/${c.id}')">
          ${c.image_url ? `<img class="cc-img" src="${c.image_url}" alt="">` : `<div class="cc-img" style="background:linear-gradient(135deg,var(--primary),var(--accent));display:flex;align-items:center;justify-content:center;font-size:28px;color:#fff">${c.is_ai_generated ? '🤖' : '📚'}</div>`}
          <div class="cc-body">
            <div class="cc-title">${c.name} ${badges.join(' ')}</div>
            <div class="cc-desc">${desc}${desc.length >= 120 ? '…' : ''}</div>
            <div class="cc-meta">${c.item_count} item(s) · ${new Date(c.created_at).toLocaleDateString()}</div>
          </div>
        </div>`;
      });
    }
    html += '</div>';
    body.innerHTML = html;
    body.querySelector('#add-col-btn')?.addEventListener('click', () => {
      const m = UI.modal('New Collection', `
        <div class="form-group"><label>Name</label><input id="col-name" class="fi" placeholder="Seasonal Produce"></div>
        <div class="form-group"><label>Description</label><textarea id="col-desc" class="fi" rows="2"></textarea></div>
        <div class="form-group"><label>Image URL</label><input id="col-img" class="fi" placeholder="https://example.com/image.jpg"></div>`);
      m.actions.appendChild(UI.btn('Cancel', 'btn-outline', m.close));
      m.actions.appendChild(UI.btn('Create', 'btn-primary', async (btn) => {
        if (!UI.validateForm({ 'col-name': { required: true } })) return;
        btn.disabled = true;
        try {
          await API.post('/collections', {
            name: document.getElementById('col-name').value,
            description: document.getElementById('col-desc').value || null,
            image_url: document.getElementById('col-img').value || null,
          });
          m.close(); UI.showSuccess('Collection created'); Router.navigate('#collections');
        } catch (e) { UI.showError(e.message); btn.disabled = false; }
      }));
    });
    _setSEO('Collections — FoodTrack', `Browse ${data.total} curated collections of taxonomy items, products, and more.`);
    return body;
  }));
};

Pages.collectionDetail = (app, id) => {
  app.appendChild(UI.layout('Collection Detail', async () => {
    const data = await API.get(`/collections/${id}`);
    const body = document.createElement('div');
    const itemsHtml = (data.items || []).map((item, i) => {
      const badges = [];
      if (item.phylum) badges.push(`<span class="taxonomy-badge phylum">${item.phylum}</span>`);
      if (item.family) badges.push(`<span class="taxonomy-badge family">${item.family}</span>`);
      return `<div class="linked-card" onclick="Router.navigate('#taxonomy/item/${item.id}')" style="cursor:pointer">
        <div class="lc-icon" style="font-size:28px">🌿</div>
        <div class="lc-body">
          <div class="lc-title">${item.common_name}</div>
          <div class="lc-sub"><em>${item.scientific_name || '—'}</em> · ${item.code}</div>
          <div class="lc-meta">${badges.join(' ')} ${item.image_url ? `<img src="${item.image_url}" style="height:32px;vertical-align:middle;border-radius:4px;margin-left:4px">` : ''}</div>
        </div>
        <a href="#taxonomy/item/${item.id}" class="btn btn-sm btn-outline" style="flex-shrink:0">View</a>
      </div>`;
    }).join('') || '<p style="color:var(--text-light);padding:12px 0">No items in this collection yet.</p>';
    body.innerHTML = `
      <div class="card">
        <div class="card-header"><h3>${data.name}</h3>
          <div style="display:flex;gap:6px;flex-wrap:wrap">
            ${data.is_ai_generated ? '<span class="badge badge-info">🤖 AI Generated</span>' : ''}
            <span class="badge badge-secondary">${(data.items || []).length} items</span>
          </div>
        </div>
        ${data.image_url ? `<div style="text-align:center;margin-bottom:12px"><img src="${data.image_url}" style="max-height:160px;border-radius:8px;object-fit:cover;max-width:100%"></div>` : ''}
        <p style="color:var(--text-light)">${data.description || 'No description'}</p>
        ${data.feed_source_id ? `<p style="font-size:12px;color:var(--text-light);margin-top:8px">📡 Feed Source ID: ${data.feed_source_id} · Created: ${new Date(data.created_at).toLocaleDateString()}</p>` : ''}
      </div>
      <div class="card" style="margin-top:16px">
        <div class="card-header"><h3>📦 Items in this Collection</h3>
          <button class="btn btn-sm btn-primary" id="add-col-item-btn">+ Add Item</button>
        </div>
        ${itemsHtml}
      </div>
      <div style="margin-top:16px;display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn btn-outline" onclick="Router.navigate('#collections')">← Back to Collections</button>
        <button class="btn btn-outline" onclick="Router.navigate('#search/' + encodeURIComponent('${data.name}'))">🔍 Search "${data.name}"</button>
        ${data.is_ai_generated ? `<button class="btn btn-accent" onclick="Router.navigate('#feeds')">🤖 Manage AI Feeds</button>` : ''}
      </div>`;
    body.querySelector('#add-col-item-btn')?.addEventListener('click', () => {
      const m = UI.modal('Add Item', `
        <div class="form-group"><label>Taxonomy Item ID or Code</label>
          <div style="display:flex;gap:8px"><input id="ci-item-id" type="number" class="fi" placeholder="Item ID" style="flex:1">
          <span style="line-height:40px;color:var(--text-light)">or</span>
          <input id="ci-item-code" class="fi" placeholder="Item Code" style="flex:1"></div></div>
        <div class="form-group"><label>Sort Order</label><input id="ci-order" type="number" class="fi" value="0"></div>
        <div class="form-group"><label>Notes</label><textarea id="ci-notes" class="fi" rows="2"></textarea></div>`);
      m.actions.appendChild(UI.btn('Cancel', 'btn-outline', m.close));
      m.actions.appendChild(UI.btn('Add', 'btn-primary', async (btn) => {
        btn.disabled = true;
        try {
          let itemId = parseInt(document.getElementById('ci-item-id').value);
          if (!itemId) {
            const code = document.getElementById('ci-item-code').value.trim();
            if (code) {
              const itemData = await API.get(`/taxonomy/by-code/${encodeURIComponent(code)}`);
              itemId = itemData.id;
            }
          }
          if (!itemId) { UI.showError('Enter an Item ID or Code'); btn.disabled = false; return; }
          await API.post(`/collections/${id}/items`, {
            item_id: itemId,
            sort_order: parseInt(document.getElementById('ci-order').value) || 0,
            notes: document.getElementById('ci-notes').value || null,
          });
          m.close(); UI.showSuccess('Item added'); Router.navigate('#collections/' + id);
        } catch (e) { UI.showError(e.message); btn.disabled = false; }
      }));
    });
    _setSEO(`${data.name} — FoodTrack Collection`, (data.description || '').substring(0, 250), data.image_url || undefined);
    return body;
  }));
};

// ─── AI FEEDS ────────────────────────────────────────────────────

Pages.feeds = (app) => {
  app.appendChild(UI.layout('AI Feeds', async () => {
    const body = document.createElement('div');
    try {
      const data = await API.get('/collections/feeds/list');
      let html = `<div class="list-header">
        <p style="color:var(--text-light)">${data.feeds.length} feed source(s)</p>
        <button class="btn btn-primary btn-sm" id="add-feed-btn">+ New Feed Source</button></div>`;
      if (data.feeds.length === 0) {
        html += '<div class="empty-state"><p>No feed sources configured. Add RSS/Atom feeds to auto-generate collections.</p></div>';
      } else {
        html += '<div class="table-container"><table><thead><tr><th>Name</th><th>Type</th><th>URL</th><th>Schedule</th><th>Last Fetched</th><th>Actions</th></tr></thead><tbody>';
        data.feeds.forEach(f => {
          html += `<tr><td><strong>${f.name}</strong></td><td><span class="badge badge-info">${f.feed_type}</span></td>
            <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis">${f.url || '—'}</td>
            <td>${f.schedule_minutes} min</td>
            <td>${f.last_fetched_at ? new Date(f.last_fetched_at).toLocaleString() : 'Never'}</td>
            <td><button class="btn btn-sm btn-primary run-feed-btn" data-id="${f.id}">Run Now</button></td></tr>`;
        });
        html += '</tbody></table></div>';
      }
      body.innerHTML = html;
      document.getElementById('add-feed-btn')?.addEventListener('click', () => {
        const m = UI.modal('New Feed Source', `
          <div class="form-group"><label>Name</label><input id="fd-name" class="fi" placeholder="e.g. FAO Fish Updates"></div>
          <div class="form-group"><label>Feed URL</label><input id="fd-url" class="fi" placeholder="https://example.com/feed.xml"></div>
          <div class="form-group"><label>Schedule (minutes)</label><input id="fd-sched" type="number" class="fi" value="1440"></div>`);
        m.actions.appendChild(UI.btn('Cancel', 'btn-outline', m.close));
        m.actions.appendChild(UI.btn('Create', 'btn-primary', async (btn) => {
          if (!UI.validateForm({ 'fd-name': { required: true }, 'fd-url': { required: true } })) return;
          btn.disabled = true;
          try {
            await API.post('/collections/feeds', {
              name: document.getElementById('fd-name').value,
              url: document.getElementById('fd-url').value,
              schedule_minutes: parseInt(document.getElementById('fd-sched').value) || 1440,
            });
            m.close(); UI.showSuccess('Feed source created'); Router.navigate('#feeds');
          } catch (e) { UI.showError(e.message); btn.disabled = false; }
        }));
      });
      body.querySelectorAll('.run-feed-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
          btn.disabled = true; btn.textContent = 'Running...';
          try {
            const result = await API.post(`/collections/feeds/${btn.dataset.id}/run`);
            UI.showSuccess(`Feed run complete: ${result.collection_name} (${result.items_added} items)`);
            Router.navigate('#feeds');
          } catch (e) { UI.showError(e.message); btn.disabled = false; btn.textContent = 'Run Now'; }
        });
      });
    } catch (e) {
      body.innerHTML = `<div class="card"><p style="color:var(--danger)">${e.message}</p></div>`;
    }
    return body;
  }));
};

Pages.setupTOTP = async () => {
  const div = document.getElementById('totp-setup');
  try {
    const data = await API.post('/auth/setup-totp');
    div.innerHTML = `
      <div class="mfa-setup">
        <p style="margin-bottom:12px">Scan this QR code with your authenticator app:</p>
        <div class="qr-display"><img src="https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(data.uri)}" alt="TOTP QR"/></div>
        <p style="font-size:12px;color:#6b7280;margin:8px 0">Or enter this key manually:</p>
        <div class="secret-key">${data.secret}</div>
        <div style="margin-top:16px;display:flex;gap:8px;max-width:300px;margin-left:auto;margin-right:auto">
          <input id="totp-code" class="fi" placeholder="Enter 6-digit code" maxlength="6" style="text-align:center;letter-spacing:4px">
          <button class="btn btn-primary" id="totp-verify-btn">Verify</button>
        </div>
      </div>`;
    document.querySelector('#totp-verify-btn').onclick = async () => {
      try {
        await API.post('/auth/verify-totp', { code: document.getElementById('totp-code').value });
        UI.showSuccess('TOTP enabled successfully');
        div.innerHTML = '<div style="padding:12px;background:#d4edda;color:#155724;border-radius:8px;margin-top:12px">✅ Two-factor authentication is active</div>';
      } catch (e) { UI.showError(e.message); }
    };
  } catch (e) { UI.showError(e.message); }
};

// ─── ENHANCED TAXONOMY ITEM DETAIL ──────────────────────────────

Pages.taxonomyItemDetail = (app, id) => {
  app.appendChild(UI.layout('Taxonomy Item', async () => {
    const item = await API.get(`/taxonomy/items/${id}`);
    const body = document.createElement('div');

    // Names
    const namesHtml = (item.names || []).map(n =>
      `<div style="display:flex;gap:8px;padding:4px 0"><span style="font-weight:600;width:100px">${n.language.toUpperCase()}</span><span>${n.name}${n.is_primary ? ' ⭐' : ''}</span></div>`
    ).join('') || '<p style="color:var(--text-light)">No alternative names</p>';

    // Attributes
    const attrsHtml = (item.attributes || []).map(a =>
      `<div style="display:flex;gap:8px;padding:4px 0"><span style="font-weight:600;width:160px">${a.key}</span><span>${a.value || ''}${a.unit ? ' ' + a.unit : ''}</span></div>`
    ).join('') || '<p style="color:var(--text-light)">No attributes</p>';

    // Linked Products
    const linkedProductsHtml = (item.linked_products || []).map(p =>
      `<a href="${p.url}" class="linked-card" style="text-decoration:none;color:inherit">
        <div class="lc-icon">📦</div>
        <div class="lc-body">
          <div class="lc-title">${p.name}</div>
          <div class="lc-sub">SKU: ${p.sku} · ${p.category}${p.producer_name ? ' · ' + p.producer_name : ''}</div>
        </div>
      </a>`
    ).join('') || '<p style="color:var(--text-light);padding:12px 0">No linked products found.</p>';

    // Linked Batches with warehouse locations
    const linkedBatchesHtml = (item.linked_batches || []).map(b => {
      const locs = (b.locations || []).map(l =>
        `<span class="taxonomy-badge" style="background:#e8f5e9;color:#2e7d32">${l.warehouse_name}${l.zone ? ' [' + l.zone + ']' : ''} x${l.quantity}</span>`
      ).join(' ');
      return `<a href="#batches/${b.id}" class="linked-card" style="text-decoration:none;color:inherit">
        <div class="lc-icon">🏷️</div>
        <div class="lc-body">
          <div class="lc-title">Batch ${b.batch_number}</div>
          <div class="lc-sub">Qty: ${b.quantity} · Status: ${b.status}${b.production_date ? ' · Prod: ' + new Date(b.production_date).toLocaleDateString() : ''}</div>
          <div class="lc-meta">${locs}</div>
        </div>
      </a>`;
    }).join('') || '<p style="color:var(--text-light);padding:12px 0">No batches linked yet.</p>';

    body.innerHTML = `
      <div class="card">
        <div class="card-header"><h3>${item.common_name}</h3>
          <div style="display:flex;gap:6px;flex-wrap:wrap">
            <span class="badge badge-info">${item.code}</span>
            <span class="badge badge-success">ID: ${item.id}</span>
          </div>
        </div>
        <div class="item-detail-grid" style="margin-top:12px">
          <div>
            <div class="info-row"><div class="info-label">Scientific Name</div><div class="info-value"><em>${item.scientific_name || '—'}</em></div></div>
            <div class="info-row"><div class="info-label">Phylum</div><div class="info-value">${item.phylum ? `<span class="taxonomy-badge phylum">${item.phylum}</span>` : '—'}</div></div>
            <div class="info-row"><div class="info-label">Class</div><div class="info-value">${item.tax_class ? `<span class="taxonomy-badge class">${item.tax_class}</span>` : '—'}</div></div>
            <div class="info-row"><div class="info-label">Order</div><div class="info-value">${item.order_name ? `<span class="taxonomy-badge order">${item.order_name}</span>` : '—'}</div></div>
            <div class="info-row"><div class="info-label">Family</div><div class="info-value">${item.family ? `<span class="taxonomy-badge family">${item.family}</span>` : '—'}</div></div>
            <div class="info-row"><div class="info-label">Genre</div><div class="info-value">${item.genre ? `<span class="taxonomy-badge genre">${item.genre}</span>` : '—'}</div></div>
          </div>
          <div>
            <div class="info-row"><div class="info-label">Gestation</div><div class="info-value">${item.gestation_period ? item.gestation_period + ' ' + (item.gestation_unit || '') : '—'}</div></div>
            <div class="info-row"><div class="info-label">Local Uses</div><div class="info-value">${item.local_uses || '—'}</div></div>
            <div class="info-row"><div class="info-label">Description</div><div class="info-value">${item.description || '—'}</div></div>
            ${item.image_url ? `<div style="margin-top:8px;text-align:center"><img src="${item.image_url}" style="max-width:240px;max-height:180px;border-radius:8px;object-fit:cover" alt="${item.common_name}"></div>` : ''}
          </div>
        </div>
      </div>

      <div class="card" style="margin-top:16px">
        <div class="card-header"><h3>🌐 Multilingual / Local Names</h3></div>
        ${namesHtml}
      </div>

      <div class="card" style="margin-top:16px">
        <div class="card-header"><h3>📋 Attributes</h3></div>
        ${attrsHtml}
      </div>

      <div class="card" style="margin-top:16px">
        <div class="card-header"><h3>📦 Linked Products (${(item.linked_products || []).length})</h3></div>
        ${linkedProductsHtml}
      </div>

      <div class="card" style="margin-top:16px">
        <div class="card-header"><h3>🏷️ Linked Batches & Warehouse Locations (${(item.linked_batches || []).length})</h3>
          <a href="#search/${encodeURIComponent(item.common_name)}" class="btn btn-sm btn-outline">🔍 Search Related</a>
        </div>
        ${linkedBatchesHtml}
      </div>

      <div style="margin-top:16px;display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn btn-outline" onclick="Router.navigate('#taxonomy')">← Back to Taxonomies</button>
      </div>`;

    // SEO
    _setSEO(
      `${item.common_name} — FoodTrack Taxonomy`,
      `${item.scientific_name ? item.scientific_name + ' — ' : ''}${item.description ? item.description.substring(0, 200) : ''} Phylum: ${item.phylum || 'N/A'}, Family: ${item.family || 'N/A'}, Gestation: ${item.gestation_period || 'N/A'}`,
      item.image_url || undefined
    );

    return body;
  }));
};

// ─── FOOD ITEMS BROWSE ──────────────────────────────────────────

Pages.foodItems = (app) => {
  app.appendChild(UI.layout('Food Items', async () => {
    const data = await API.get('/taxonomy/items/grouped/by-category');
    const body = document.createElement('div');

    let html = `<div class="list-header">
      <p style="color:var(--text-light)">${data.total_items} food items across ${data.total_categories} categories</p>
      <input id="food-search-input" class="fi" placeholder="🔍 Filter by name, scientific, family..." style="max-width:320px">
    </div>`;

    (data.categories || []).forEach(cat => {
      html += `<div class="card" style="margin-bottom:16px">
        <div class="card-header"><h3>${cat.category_name}</h3>
          <span class="badge badge-info">${cat.total} items</span>
        </div>
        <p style="font-size:13px;color:var(--text-light);margin-bottom:12px">${cat.description || ''}</p>
        <div class="food-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px">`;
      (cat.items || []).forEach(item => {
        const badges = [];
        if (item.phylum) badges.push(`<span class="tax-badge">${item.phylum.split(' ')[0]}</span>`);
        if (item.family) badges.push(`<span class="tax-badge">${item.family}</span>`);
        html += `<div class="card food-item-card" style="cursor:pointer;padding:12px;margin:0" data-search="${item.common_name.toLowerCase()} ${(item.scientific_name||'').toLowerCase()} ${(item.family||'').toLowerCase()} ${(item.genre||'').toLowerCase()}" onclick="Router.navigate('#food-item/${item.id}')">
          <div style="font-size:24px;text-align:center;margin-bottom:4px">${item.phylum === 'Chordata' ? '🐟' : item.phylum === 'Arthropoda' ? '🦐' : '🌿'}</div>
          <div style="font-weight:600;font-size:14px;text-align:center">${item.common_name}</div>
          <div style="font-size:12px;color:var(--text-light);text-align:center"><em>${item.scientific_name || ''}</em></div>
          <div style="margin-top:4px;text-align:center">${badges.join(' ')}</div>
          <div style="font-size:12px;color:var(--text-muted);margin-top:4px;text-align:center">${(item.description || '').substring(0,50)}${(item.description||'').length > 50 ? '…' : ''}</div>
        </div>`;
      });
      html += '</div></div>';
    });

    body.innerHTML = html;

    // Category toggle
    body.querySelectorAll('.card-header').forEach(h => {
      h.addEventListener('click', (e) => {
        if (e.target.closest('.badge') || e.target.tagName === 'SPAN') return;
        const grid = h.parentElement.querySelector('.food-grid');
        if (grid) {
          grid.style.display = grid.style.display === 'none' ? '' : 'none';
          h.querySelector('.badge').textContent = grid.style.display === 'none' ? '▶' : cat.total + ' items';
        }
      });
    });

    // Client-side search filter
    body.querySelector('#food-search-input').addEventListener('input', function() {
      const q = this.value.toLowerCase().trim();
      document.querySelectorAll('.food-item-card').forEach(card => {
        const txt = card.dataset.search || '';
        card.style.display = (!q || txt.includes(q)) ? '' : 'none';
      });
      // Hide empty categories
      document.querySelectorAll('.card').forEach(catCard => {
        const visible = catCard.querySelectorAll('.food-item-card[style*="display: none"]').length;
        const total = catCard.querySelectorAll('.food-item-card').length;
        if (total === 0) return;
        catCard.style.display = (visible === total && q) ? 'none' : '';
      });
    });

    _setSEO('Food Items Catalog — FoodTrack', `Browse ${data.total_items} food items with taxonomic data across ${data.total_categories} categories.`);
    return body;
  }));
};

// ─── FOOD ITEM DETAIL (reuses taxonomy/item/:id but dedicated route) ─────

Pages.foodItemDetail = (app, id) => {
  // Reuse the existing taxonomyItemDetail logic for the dedicated food-item route
  Pages.taxonomyItemDetail(app, id);
};

// ─── CARGO TRACKING SEARCH ──────────────────────────────────────

Pages.cargoTracking = (app) => {
  app.appendChild(UI.layout('Cargo Tracking', async () => {
    const body = document.createElement('div');
    body.innerHTML = `
      <div class="card">
        <div class="card-header"><h3>🔍 Advanced Cargo Search</h3></div>
        <form id="cargo-search-form" style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px">
          <input id="cs-q" class="fi" placeholder="Free text (number, carrier, vessel...)" style="grid-column:1/-1">
          <input id="cs-source" class="fi" placeholder="Source (city/warehouse)">
          <input id="cs-dest" class="fi" placeholder="Destination (city/warehouse)">
          <input id="cs-port" class="fi" placeholder="Port name">
          <input id="cs-carrier" class="fi" placeholder="Carrier name">
          <input id="cs-vessel" class="fi" placeholder="Vessel / Ferry name">
          <input id="cs-route" class="fi" placeholder="Ferry route">
          <select id="cs-mode" class="fi"><option value="">All modes</option><option value="courier">Courier</option><option value="ferry">Ferry</option><option value="truck">Truck</option><option value="air">Air</option><option value="rail">Rail</option><option value="multimodal">Multimodal</option></select>
          <select id="cs-status" class="fi"><option value="">All statuses</option><option value="created">Created</option><option value="picked_up">Picked Up</option><option value="in_transit">In Transit</option><option value="at_ferry">At Ferry</option><option value="on_ferry">On Ferry</option><option value="arrived_port">Arrived Port</option><option value="delivered">Delivered</option><option value="exception">Exception</option></select>
          <input id="cs-arrival-from" class="fi" type="date" placeholder="Arrival from">
          <input id="cs-arrival-to" class="fi" type="date" placeholder="Arrival to">
          <input id="cs-depart-from" class="fi" type="date" placeholder="Depart from">
          <input id="cs-depart-to" class="fi" type="date" placeholder="Depart to">
          <button class="btn btn-primary" id="cs-btn" style="grid-column:1/-1;margin-top:4px">🔍 Search Cargo</button>
        </form>
      </div>
      <div id="cs-results" style="margin-top:16px"><div class="empty-state"><p>Enter search criteria to find cargo shipments</p></div></div>
      <div id="cs-pagination" class="pagination"></div>`;

    async function doCargoSearch(page = 1) {
      const resultsEl = document.getElementById('cs-results');
      const paginationEl = document.getElementById('cs-pagination');
      resultsEl.innerHTML = '<div class="spinner" style="margin:40px auto"></div>';
      paginationEl.innerHTML = '';

      const params = new URLSearchParams();
      const fields = [
        ['q', 'cs-q'], ['source', 'cs-source'], ['destination', 'cs-dest'],
        ['port', 'cs-port'], ['carrier', 'cs-carrier'], ['vessel', 'cs-vessel'],
        ['ferry_route', 'cs-route'], ['mode', 'cs-mode'], ['status', 'cs-status'],
        ['arrival_from', 'cs-arrival-from'], ['arrival_to', 'cs-arrival-to'],
        ['departure_from', 'cs-depart-from'], ['departure_to', 'cs-depart-to'],
      ];
      fields.forEach(([key, elId]) => {
        const val = document.getElementById(elId)?.value?.trim();
        if (val) params.set(key, val);
      });
      params.set('page', String(page));

      try {
        const data = await API.get('/shipments/search?' + params.toString());
        renderCargoResults(data, resultsEl, paginationEl);
      } catch (e) {
        resultsEl.innerHTML = `<p style="color:var(--danger);text-align:center">${e.message}</p>`;
      }
    }

    function renderCargoResults(data, resultsEl, paginationEl) {
      if (!data.shipments || data.shipments.length === 0) {
        resultsEl.innerHTML = '<div class="empty-state"><p>No cargo shipments match your filters</p></div>';
        return;
      }
      const statusCls = { 'delivered':'badge-success', 'in_transit':'badge-info', 'on_ferry':'badge-warning', 'exception':'badge-danger', 'created':'badge-secondary', 'picked_up':'badge-info', 'at_ferry':'badge-warning', 'arrived_port':'badge-info' };
      let html = `<p style="font-size:14px;color:var(--text-light);margin-bottom:12px">${data.total} cargo shipment(s) found</p>
        <div class="table-container"><table><thead><tr><th>Shipment #</th><th>Mode</th><th>Status</th><th>From → To</th><th>Carrier / Vessel</th><th>Est. Arrival</th><th>Actions</th></tr></thead><tbody>`;
      data.shipments.forEach(s => {
        const originName = s.origin ? (s.origin.city || s.origin.name || '—') : '—';
        const destName = s.destination ? (s.destination.city || s.destination.name || '—') : '—';
        const carrierInfo = [s.carrier_name, s.vessel_name, s.ferry_route].filter(Boolean).join(' · ') || '—';
        const arrivalDate = s.estimated_arrival ? new Date(s.estimated_arrival).toLocaleDateString() : '—';
        html += `<tr>
          <td><strong>${s.shipment_number}</strong></td>
          <td><span class="badge badge-info">${s.mode}</span></td>
          <td><span class="badge ${statusCls[s.status] || 'badge-secondary'}">${(s.status_label || s.status).replace(/_/g,' ')}</span></td>
          <td>${originName} → ${destName}</td>
          <td style="font-size:13px">${carrierInfo}</td>
          <td>${arrivalDate}</td>
          <td><a href="#cargo-tracking/${s.id}" class="btn btn-sm btn-outline">View</a></td>
        </tr>`;
      });
      html += '</tbody></table></div>';
      resultsEl.innerHTML = html;

      if (data.total_pages > 1) {
        let phtml = '';
        for (let i = 1; i <= data.total_pages; i++) {
          phtml += `<button class="page-btn ${i === data.page ? 'active' : ''}" data-p="${i}">${i}</button>`;
        }
        paginationEl.innerHTML = phtml;
        paginationEl.querySelectorAll('.page-btn:not(.active)').forEach(b => b.addEventListener('click', () => doCargoSearch(parseInt(b.dataset.p))));
      }
    }

    body.querySelector('#cargo-search-form').onsubmit = (e) => { e.preventDefault(); doCargoSearch(1); };
    body.querySelector('#cs-btn').onclick = () => doCargoSearch(1);

    _setSEO('Cargo Tracking — FoodTrack', 'Search and filter cargo shipments by source, destination, port, carrier, vessel, ferry route, arrival date and more.');
    return body;
  }));
};

// ─── CARGO TRACKING DETAIL ───────────────────────────────────────

Pages.cargoTrackingDetail = (app, id) => {
  app.appendChild(UI.layout('Cargo Detail', async () => {
    const data = await API.get(`/shipments/${id}`);
    const s = data;
    const statusCls = { 'delivered':'badge-success', 'in_transit':'badge-info', 'on_ferry':'badge-warning', 'exception':'badge-danger', 'created':'badge-secondary', 'picked_up':'badge-info', 'at_ferry':'badge-warning', 'arrived_port':'badge-info', 'out_for_delivery':'badge-info' };
    const body = document.createElement('div');

    const trackingHtml = (s.tracking_events || []).map(te =>
      `<div class="tracking-item ${te.status === 'delivered' ? 'delivered' : te.status === 'exception' ? 'exception' : ''}">
        <div class="tt-status"><span class="badge ${statusCls[te.status] || 'badge-secondary'}">${te.status.replace(/_/g, ' ')}</span></div>
        <div class="tt-loc">${te.location_name || '—'}</div>
        <div class="tt-time">${te.event_timestamp ? new Date(te.event_timestamp).toLocaleString() : ''}</div>
        ${te.message ? `<div style="font-size:13px;margin-top:2px">${te.message}</div>` : ''}
      </div>`
    ).join('') || '<p style="color:var(--text-light)">No tracking events</p>';

    const productsHtml = (s.products || []).map(p =>
      `<div style="display:flex;gap:8px;padding:4px 0"><span class="badge badge-info">${p.product_name}</span><span style="font-size:13px;color:var(--text-light)">SKU: ${p.product_sku} · Batch: ${p.batch_number}</span></div>`
    ).join('') || '—';

    body.innerHTML = `
      <div class="card">
        <div class="card-header"><h3>🚢 ${s.shipment_number}</h3>
          <div style="display:flex;gap:6px;flex-wrap:wrap">
            <span class="badge badge-info">${s.mode.toUpperCase()}</span>
            <span class="badge ${statusCls[s.status] || 'badge-secondary'}">${(s.status_label || s.status).replace(/_/g, ' ')}</span>
          </div>
        </div>
        <div class="info-grid" style="margin-top:12px">
          <div class="info-row"><div class="info-label">Origin</div><div class="info-value">${s.origin ? s.origin.name + (s.origin.city ? ' (' + s.origin.city + ')' : '') : '—'}</div></div>
          <div class="info-row"><div class="info-label">Destination</div><div class="info-value">${s.destination ? s.destination.name + (s.destination.city ? ' (' + s.destination.city + ')' : '') : '—'}</div></div>
          <div class="info-row"><div class="info-label">Carrier</div><div class="info-value">${s.carrier_name || '—'}${s.carrier_ref ? ' · Ref: ' + s.carrier_ref : ''}</div></div>
          <div class="info-row"><div class="info-label">Vessel / Ferry</div><div class="info-value">${s.vessel_name || '—'}${s.ferry_route ? ' · ' + s.ferry_route : ''}</div></div>
          <div class="info-row"><div class="info-label">Weight / Volume</div><div class="info-value">${s.total_weight_kg ? s.total_weight_kg + ' kg' : '—'} / ${s.total_volume_m3 ? s.total_volume_m3 + ' m³' : '—'}</div></div>
          <div class="info-row"><div class="info-label">Tracking Code</div><div class="info-value">${s.courier_tracking_code ? s.courier_tracking_code + (s.courier_url ? ' <a href="' + s.courier_url + '" target="_blank">🔗 Track</a>' : '') : '—'}</div></div>
          <div class="info-row"><div class="info-label">Est. Departure</div><div class="info-value">${s.estimated_departure ? new Date(s.estimated_departure).toLocaleString() : '—'}</div></div>
          <div class="info-row"><div class="info-label">Est. Arrival</div><div class="info-value">${s.estimated_arrival ? new Date(s.estimated_arrival).toLocaleString() : '—'}</div></div>
        </div>
        ${s.notes ? `<div style="margin-top:12px;padding:8px;background:var(--bg-card);border-radius:6px;font-size:13px;color:var(--text-light)">📝 ${s.notes}</div>` : ''}
      </div>
      <div class="inv-grid" style="margin-top:16px">
        <div class="card">
          <div class="card-header"><h3>📦 Products in Shipment (${(s.products || []).length})</h3></div>
          ${productsHtml}
          <div style="margin-top:8px"><a href="#search/${encodeURIComponent(s.shipment_number)}" class="btn btn-sm btn-outline">🔍 Search Related</a></div>
        </div>
        <div class="card">
          <div class="card-header"><h3>📍 Tracking (${(s.tracking_events || []).length})</h3></div>
          <div class="tracking-timeline">${trackingHtml}</div>
        </div>
      </div>
      <div style="margin-top:16px;display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn btn-outline" onclick="Router.navigate('#cargo-tracking')">← Back to Cargo Search</button>
        <button class="btn btn-outline" onclick="Router.navigate('#shipments/${id}')">Full Shipment View</button>
      </div>`;

    _setSEO(`Cargo ${s.shipment_number} — FoodTrack`, `Shipment from ${s.origin?.name || '?'} to ${s.destination?.name || '?'} via ${s.carrier_name || s.mode}`);
    return body;
  }));
};
