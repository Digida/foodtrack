/* ============================================================
   FoodTrack Frontend i18n — English / Arabic + language switch
   ============================================================ */

window.I18n = (() => {
  const STORAGE_KEY = 'ft_lang';

  const messages = {
    en: {
      'lang.name': 'English',
      'lang.aria': 'Switch language',

      // Public nav
      'nav.home': 'Home',
      'nav.bulking': 'Bulking',
      'nav.food-items': 'Food Items',
      'nav.verify': 'Verify',
      'nav.cargo-tracking': 'Cargo Tracking',
      'nav.about': 'About',
      'nav.contact': 'Contact',
      'nav.login': 'Login',
      'nav.get-started': 'Get Started',
      'nav.dashboard': 'Dashboard',
      'nav.logout': 'Logout',
      'nav.search': 'Search items, products, batches...',

      // Sidebar
      'sidebar.search': 'Search',
      'sidebar.products': 'Products',
      'sidebar.traceability': 'Traceability',
      'sidebar.certificates': 'Certificates',
      'sidebar.analytics': 'Analytics',
      'sidebar.share': 'Share',
      'sidebar.taxonomy': 'Taxonomy',
      'sidebar.batches': 'Batches',
      'sidebar.warehouses': 'Warehouses',
      'sidebar.shipments': 'Shipments',
      'sidebar.collections': 'Collections',
      'sidebar.settings': 'Settings',
      'sidebar.guest': 'Guest',
      'sidebar.quick-search': 'Quick search items, batches...',

      // Topbar / layout
      'common.loading': 'Loading…',
      'common.save': 'Save',
      'common.cancel': 'Cancel',
      'common.confirm': 'Confirm',
      'common.delete': 'Delete',
      'common.edit': 'Edit',
      'common.add': 'Add',
      'common.search': 'Search',
      'common.close': 'Close',
      'common.view': 'View',
      'common.details': 'Details',
      'common.back': 'Back',
      'common.required': 'Required',
      'common.downloaded': 'Downloaded',
      'common.page-not-found': 'Page not found',
      'common.go-home': 'Go home',
      'common.error': 'Error',
      'common.language': 'Language',

      // Footer
      'footer.rights': '© 2026 FoodTrack. All rights reserved.',
      'footer.dev': 'Dev:',
      'footer.home': 'Home',
      'footer.verify': 'Verify',
      'footer.about': 'About',
      'footer.contact': 'Contact',

      // Home / landing
      'home.title': 'Digital Trust for<br>Your Food Supply Chain',
      'home.subtitle': 'Blockchain-powered traceability, smart certification, investor bulking with escrow — built for the agrifood industry.',
      'home.get-started': 'Get Started',
      'home.bulk-invest': 'Bulk & Invest',
      'home.learn-more': 'Learn More',
      'home.stat-products': 'Products Traced',
      'home.stat-certs': 'Certificates Issued',
      'home.stat-countries': 'Countries',
      'home.features-title': 'Everything You Need',
      'home.features-sub': 'From farm to fork, FoodTrack gives you full visibility and control.',
      'home.feature-traceability': 'Traceability',
      'home.feature-traceability-desc': 'End-to-end supply chain tracking with immutable event timelines. Scan, log, and follow every step.',
      'home.feature-certs': 'Smart Certifications',
      'home.feature-certs-desc': 'Issue and verify digital certificates — Origin, Organic, Halal, Safety, and more — with one click.',
      'home.feature-analytics': 'Analytics & Reports',
      'home.feature-analytics-desc': 'Real-time dashboards, category breakdowns, and CSV exports to inform your decisions.',
      'home.feature-share': 'Share & Compare',
      'home.feature-share-desc': 'Generate shareable product links, QR codes, and peer benchmarking for buyer confidence.',
      'home.feature-batches': 'Batch Management',
      'home.feature-batches-desc': 'Track every batch through its full lifecycle — harvest, storage, shipment, and delivery.',
      'home.feature-trace': 'Immutable Trace',
      'home.feature-trace-desc': 'Every event recorded on a verifiable timeline your customers can trust.',
      'home.feature-scanner': 'QR & Barcode Scanner',
      'home.feature-scanner-desc': 'Native camera scanning with automatic fallback. Decode and look up products in seconds.',
      'home.feature-secure': 'Secure & Compliant',
      'home.feature-secure-desc': 'Multi-factor authentication, role-based access, and audit-ready data for regulatory compliance.',
      'home.feature-escrow': 'Investor Bulking & Escrow',
      'home.feature-escrow-desc': 'Register commodity demand, collect farmer supply, and lock deals with escrow-backed deposits — released only when the buyer receives the goods.',
      'home.feature-jobs': 'Member Job Pipeline',
      'home.feature-jobs-desc': 'Assign clerks, verifiers, packers, certifiers, and couriers to each register, with independent certification across company lines.',
      'home.how-title': 'How It Works',
      'home.how-sub': 'Three simple steps to full supply chain integrity.',
      'home.step1-title': 'Register & Onboard',
      'home.step1-desc': 'Create your account, set up your company profile, and start adding products to the platform.',
      'home.step2-title': 'Track & Certify',
      'home.step2-desc': 'Log supply chain events, issue digital certificates, and generate traceability records for every product.',
      'home.step3-title': 'Bulk & Escrow',
      'home.step3-desc': 'Register commodity demand, accept farmer bids, and deposit escrow — then release it to the seller once the buyer receives the goods.',
      'home.cta-title': 'Ready to Build Trust in Your Supply Chain?',
      'home.cta-desc': 'Join thousands of producers, certifiers, and buyers using FoodTrack every day.',
      'home.cta-button': 'Get Started Free',
    },
    ar: {
      'lang.name': 'العربية',
      'lang.aria': 'تغيير اللغة',

      // Public nav
      'nav.home': 'الرئيسية',
      'nav.bulking': 'التجميع والاستثمار',
      'nav.food-items': 'الأصناف الغذائية',
      'nav.verify': 'تحقق',
      'nav.cargo-tracking': 'تتبع الشحنات',
      'nav.about': 'عن المنصة',
      'nav.contact': 'اتصل بنا',
      'nav.login': 'تسجيل الدخول',
      'nav.get-started': 'ابدأ الآن',
      'nav.dashboard': 'لوحة التحكم',
      'nav.logout': 'تسجيل الخروج',
      'nav.search': 'ابحث عن الأصناف والمنتجات والقوافل…',

      // Sidebar
      'sidebar.search': 'بحث',
      'sidebar.products': 'المنتجات',
      'sidebar.traceability': 'التتبع',
      'sidebar.certificates': 'الشهادات',
      'sidebar.analytics': 'التحليلات',
      'sidebar.share': 'المشاركة',
      'sidebar.taxonomy': 'التصنيف',
      'sidebar.batches': 'الدفعات',
      'sidebar.warehouses': 'المستودعات',
      'sidebar.shipments': 'الشحنات',
      'sidebar.collections': 'المجموعات',
      'sidebar.settings': 'الإعدادات',
      'sidebar.guest': 'زائر',
      'sidebar.quick-search': 'بحث سريع عن الأصناف والدفعات…',

      // Topbar / layout
      'common.loading': 'جارٍ التحميل…',
      'common.save': 'حفظ',
      'common.cancel': 'إلغاء',
      'common.confirm': 'تأكيد',
      'common.delete': 'حذف',
      'common.edit': 'تعديل',
      'common.add': 'إضافة',
      'common.search': 'بحث',
      'common.close': 'إغلاق',
      'common.view': 'عرض',
      'common.details': 'التفاصيل',
      'common.back': 'رجوع',
      'common.required': 'مطلوب',
      'common.downloaded': 'تم التحميل',
      'common.page-not-found': 'الصفحة غير موجودة',
      'common.go-home': 'الانتقال إلى الرئيسية',
      'common.error': 'خطأ',
      'common.language': 'اللغة',

      // Footer
      'footer.rights': '© 2026 فودتراك. جميع الحقوق محفوظة.',
      'footer.dev': 'المطور:',
      'footer.home': 'الرئيسية',
      'footer.verify': 'تحقق',
      'footer.about': 'عن المنصة',
      'footer.contact': 'اتصل بنا',

      // Home / landing
      'home.title': 'ثقة رقمية لسلسلة<br>الإمداد الغذائي الخاصة بك',
      'home.subtitle': 'تتبّع مدعوم بالبلوك تشين، وشهادات ذكية، وتجميع واستثمار بالضمان — مبني لصناعة الأغذية.',
      'home.get-started': 'ابدأ الآن',
      'home.bulk-invest': 'تجميع واستثمار',
      'home.learn-more': 'اعرف المزيد',
      'home.stat-products': 'منتج تم تتبعه',
      'home.stat-certs': 'شهادة صادرة',
      'home.stat-countries': 'دولة',
      'home.features-title': 'كل ما تحتاجه',
      'home.features-sub': 'من المزرعة إلى المائدة، يمنحك فودتراك رؤية وتحكم كاملين.',
      'home.feature-traceability': 'التتبع',
      'home.feature-traceability-desc': 'تتبع شامل لسلسلة الإمداد بجداول زمنية ثابتة. امسح وسجل وتابع كل خطوة.',
      'home.feature-certs': 'الشهادات الذكية',
      'home.feature-certs-desc': 'أصدر وتحقّق من الشهادات الرقمية — المنشأ والعضوي والحلال والسلامة — بنقرة واحدة.',
      'home.feature-analytics': 'التحليلات والتقارير',
      'home.feature-analytics-desc': 'لوحات معلومات فورية وتفصيل حسب الفئة وتصدير CSV لدعم قراراتك.',
      'home.feature-share': 'المشاركة والمقارنة',
      'home.feature-share-desc': 'أنشئ روابط منتجات قابلة للمشاركة ورموز QR وقياس مرجعي لثقة المشتري.',
      'home.feature-batches': 'إدارة الدفعات',
      'home.feature-batches-desc': 'تتبع كل دفعة عبر دورة حياتها كاملة — الحصاد والتخزين والشحن والتسليم.',
      'home.feature-trace': 'تتبع لا يتغير',
      'home.feature-trace-desc': 'كل حدث يُسجَّل على جدول زمني قابل للتحقق يثق به عملاؤك.',
      'home.feature-scanner': 'ماسح QR والباركود',
      'home.feature-scanner-desc': 'مسح كاميرا أصلي مع خيار بديل تلقائي. فك الترميز والبحث عن المنتجات في ثوانٍ.',
      'home.feature-secure': 'آمن ومتوافق',
      'home.feature-secure-desc': 'مصادقة متعددة العوامل والوصول القائم على الأدوار وبيانات جاهزة للتدقيق للامتثال التنظيمي.',
      'home.feature-escrow': 'التجميع الاستثماري بالضمان',
      'home.feature-escrow-desc': 'سجّل طلب السلع واجمع المعروض من المزارعين وأغلق الصفقات بودائع مضمونة — لا تُفرج عنها إلا عند استلام المشتري للبضاعة.',
      'home.feature-jobs': 'خط أنابيب المهام',
      'home.feature-jobs-desc': 'عيّن موظفين ومدققين وعمال تعبئة وشهادات وسعاة لكل سجل، مع شهادات مستقلة عبر خطوط الشركات.',
      'home.how-title': 'كيف تعمل المنصة',
      'home.how-sub': 'ثلاث خطوات بسيطة لنزاهة سلسلة الإمداد.',
      'home.step1-title': 'سجّل وانضم',
      'home.step1-desc': 'أنشئ حسابك وجهّز ملف شركتك وابدأ بإضافة المنتجات إلى المنصة.',
      'home.step2-title': 'تتبّع واعتمد',
      'home.step2-desc': 'سجّل أحداث سلسلة الإمداد وأصدر شهادات رقمية وأنشئ سجلات تتبع لكل منتج.',
      'home.step3-title': 'جمّع وضمّن',
      'home.step3-desc': 'سجّل طلب السلع واقبل عروض المزارعين وأودع الضمان — ثم أفرج عنه للبائع بعد استلام المشتري للبضاعة.',
      'home.cta-title': 'جاهز لبناء الثقة في سلسلة الإمداد؟',
      'home.cta-desc': 'انضم إلى آلاف المنتجين والمعتمدين والمشترين الذين يستخدمون فودتراك يوميًا.',
      'home.cta-button': 'ابدأ مجانًا',
    },
  };

  let lang = localStorage.getItem(STORAGE_KEY) || 'en';
  if (!messages[lang]) lang = 'en';

  function t(key, fallback) {
    const dict = messages[lang] || messages.en;
    return dict[key] || (fallback !== undefined ? fallback : key);
  }

  function setLang(next) {
    if (!messages[next]) return;
    lang = next;
    localStorage.setItem(STORAGE_KEY, next);
    applyDocument();
    window.dispatchEvent(new CustomEvent('ft:langchange', { detail: { lang } }));
  }

  function applyDocument() {
    const html = document.documentElement;
    html.lang = lang;
    html.dir = lang === 'ar' ? 'rtl' : 'ltr';
  }

  function getLang() {
    return lang;
  }

  function acceptLanguageHeader() {
    return lang === 'ar' ? 'ar,en;q=0.9' : 'en,ar;q=0.7';
  }

  function langSwitcher() {
    const next = lang === 'ar' ? 'en' : 'ar';
    const btn = UI.el('button', {
      className: 'lang-switch',
      type: 'button',
      title: t('lang.aria'),
      'aria-label': t('lang.aria'),
      onClick: () => setLang(next),
    }, lang === 'ar' ? 'EN' : 'عربي');
    return btn;
  }

  function init() {
    applyDocument();
  }

  return { t, setLang, getLang, acceptLanguageHeader, langSwitcher, init };
})();
