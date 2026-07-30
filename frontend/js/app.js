(function () {
  if (localStorage.getItem('ft_dark') === '1') document.body.classList.add('dark');

  // Init SEO defaults
  if (window.SEO) SEO.reset();

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
  Router.add('dashboard', checkAuth(Pages.dashboard));
  Router.add('products', checkAuth(Pages.products));
  Router.add('product/:id', checkAuth(Pages.productDetail));
  Router.add('traceability', checkAuth(Pages.traceability));
  Router.add('certificates', checkAuth(Pages.certificates));
  Router.add('certificate/:id', checkAuth(Pages.certificateDetail));
  Router.add('analytics', checkAuth(Pages.analytics));
  Router.add('share', checkAuth(Pages.share));
  Router.add('taxonomy', checkAuth(Pages.taxonomies));
  Router.add('taxonomy/:id', checkAuth(Pages.taxonomyDetail));
  Router.add('taxonomy/item/:id', checkAuth(Pages.taxonomyItemDetail));
  Router.add('batches', checkAuth(Pages.batches));
  Router.add('batches/:id', checkAuth(Pages.batchDetail));
  Router.add('warehouses', checkAuth(Pages.warehouses));
  Router.add('warehouses/:id', checkAuth(Pages.warehouseDetail));
  Router.add('shipments', checkAuth(Pages.shipments));
  Router.add('shipments/:id', checkAuth(Pages.shipmentDetail));
  Router.add('collections', checkAuth(Pages.collections));
  Router.add('collections/:id', checkAuth(Pages.collectionDetail));
  Router.add('feeds', checkAuth(Pages.feeds));
  Router.add('settings', checkAuth(Pages.settings));
  Router.add('food-items', checkAuth(Pages.foodItems));
  Router.add('food-item/:id', checkAuth(Pages.foodItemDetail));
  Router.add('cargo-tracking', checkAuth(Pages.cargoTracking));
  Router.add('cargo-tracking/:id', checkAuth(Pages.cargoTrackingDetail));

  if (!window.location.hash || window.location.hash === '#') {
    window.location.hash = Auth.isLoggedIn() ? '#dashboard' : '#home';
  }

  Router.init();
})();
