(function () {
  if (localStorage.getItem('ft_dark') === '1') document.body.classList.add('dark');

  // Init SEO defaults
  if (window.SEO) SEO.reset();

  // ── Startup / seeding progress banner ──────────────────────────────────────
  // Poll GET /api/v1/startup/status while the platform is initialising.
  // A slim banner is injected above the app div and auto-removes when done.

  (function startupBanner() {
    const banner = document.createElement('div');
    banner.id = 'ft-startup-banner';
    banner.style.cssText = [
      'position:fixed', 'top:0', 'left:0', 'right:0', 'z-index:9999',
      'background:#1a6b3c', 'color:#fff', 'font-size:13px',
      'padding:6px 16px', 'display:flex', 'align-items:center',
      'justify-content:space-between', 'gap:12px',
      'box-shadow:0 2px 6px rgba(0,0,0,.25)', 'transition:opacity .4s',
    ].join(';');
    banner.innerHTML = `
      <span id="ft-sb-text">⏳ Platform initialising — loading data in background…</span>
      <div style="flex:1;max-width:220px;background:rgba(255,255,255,.25);border-radius:4px;height:6px;overflow:hidden">
        <div id="ft-sb-bar" style="height:100%;background:#fff;width:0%;transition:width .5s;border-radius:4px"></div>
      </div>
      <span id="ft-sb-count" style="white-space:nowrap;opacity:.8"></span>
    `;
    document.body.prepend(banner);

    // Push the app div down so the banner doesn't overlap content
    document.getElementById('app').style.paddingTop = '34px';

    let pollInterval = null;

    function updateBanner(status) {
      const text    = document.getElementById('ft-sb-text');
      const bar     = document.getElementById('ft-sb-bar');
      const counter = document.getElementById('ft-sb-count');
      const seeding = status.seeding || {};
      const sections = seeding.sections || {};
      const total    = Object.keys(sections).length;
      const done     = Object.values(sections).filter(s => s.status === 'done').length;
      const inserted = seeding.total_inserted || 0;
      const pct      = total > 0 ? Math.round((done / total) * 100) : 0;

      if (status.ready) {
        text.textContent     = '✅ Platform ready — all data loaded';
        bar.style.width      = '100%';
        counter.textContent  = `${inserted} items`;
        banner.style.background = '#2e7d32';
        // Fade out and remove after 3 seconds
        setTimeout(() => {
          banner.style.opacity = '0';
          setTimeout(() => {
            banner.remove();
            document.getElementById('app').style.paddingTop = '';
          }, 500);
        }, 3000);
        clearInterval(pollInterval);
        return;
      }

      const phase = status.phase || 'pending';
      if (phase === 'migrating') {
        const mig = status.migration || {};
        text.textContent = `🔄 Applying database migrations (${mig.current || '…'} → ${mig.head || '…'})`;
        bar.style.width  = '5%';
      } else if (phase === 'seeding') {
        text.textContent = `🌱 Seeding catalogue data — ${done}/${total} sections complete`;
        bar.style.width  = pct + '%';
        counter.textContent = inserted > 0 ? `${inserted} items added` : '';
      } else if (phase === 'error') {
        text.textContent   = '⚠️ Startup error — some data may be unavailable. Check /api/v1/startup/status';
        banner.style.background = '#b71c1c';
        clearInterval(pollInterval);
      }
    }

    async function poll() {
      try {
        const res = await fetch('/api/v1/startup/status');
        if (!res.ok) return;
        const status = await res.json();
        updateBanner(status);
      } catch (_) { /* server not yet ready */ }
    }

    // Poll immediately, then every 2 seconds
    poll();
    pollInterval = setInterval(poll, 2000);
  })();

  // ── Route definitions ───────────────────────────────────────────────────────

  const checkAuth = (handler) => {
    return (app, ...args) => {
      if (!Auth.isLoggedIn()) {
        Router.navigate('#login');
        return;
      }
      handler(app, ...args);
    };
  };

  Router.add('home', Pages.home);
  Router.add('about', Pages.about);
  Router.add('contact', Pages.contact);
  Router.add('verify', Pages.verify);
  Router.add('login', Pages.login);
  Router.add('mfa-verify', Pages.mfaVerify);
  Router.add('search', Pages.search);
  Router.add('search/:query', Pages.search);
  Router.add('bulking', Pages.bulking);
  Router.add('bulking/:id', Pages.bulkingRegister);
  Router.add('dashboard', Pages.dashboard);
  Router.add('products', Pages.products);
  Router.add('product/:id', Pages.productDetail);
  Router.add('traceability', Pages.traceability);
  Router.add('certificates', Pages.certificates);
  Router.add('certificate/:id', Pages.certificateDetail);
  Router.add('analytics', Pages.analytics);
  Router.add('share', Pages.share);
  Router.add('taxonomy', Pages.taxonomies);
  Router.add('taxonomy/:id', Pages.taxonomyDetail);
  Router.add('taxonomy/item/:id', Pages.taxonomyItemDetail);
  Router.add('batches', checkAuth(Pages.batches));
  Router.add('batches/:id', checkAuth(Pages.batchDetail));
  Router.add('warehouses', Pages.warehouses);
  Router.add('warehouses/:id', Pages.warehouseDetail);
  Router.add('shipments', Pages.shipments);
  Router.add('shipments/:id', Pages.shipmentDetail);
  Router.add('collections', Pages.collections);
  Router.add('collections/:id', Pages.collectionDetail);
  Router.add('feeds', Pages.feeds);
  Router.add('settings', Pages.settings);
  Router.add('food-items', Pages.foodItems);
  Router.add('food-item/:id', Pages.foodItemDetail);
  Router.add('cargo-tracking', checkAuth(Pages.cargoTracking));
  Router.add('cargo-tracking/:id', checkAuth(Pages.cargoTrackingDetail));

  if (!window.location.hash || window.location.hash === '#') {
    window.location.hash = Auth.isLoggedIn() ? '#dashboard' : '#home';
  }

  Router.init();
})();
