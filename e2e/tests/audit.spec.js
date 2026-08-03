const { test, expect } = require('@playwright/test');
const crypto = require('crypto');

function randEmail() { return `audit+${crypto.randomBytes(4).toString('hex')}@example.com`; }
function rand() { return crypto.randomBytes(6).toString('hex'); }

// Guarded (auth-protected) routes -> expected topbar title
const GUARDED = {
  'dashboard': 'Dashboard',
  'analytics': 'Analytics',
  'batches': 'Batches',
  'shipments': 'Shipments',
  'feeds': 'AI Feeds',
  'cargo-tracking': 'Cargo Tracking',
  'bulking': 'Bulking',
  'settings': 'Settings',
};

// Guest-open routes (sidebar shell, no auth required) -> expected content selector
const OPEN = {
  'products': '#prod-table',
  'traceability': '#trace-q',
  'certificates': '#cert-table',
  'share': '#share-sku',
  'taxonomy': '.card',
  'warehouses': '#warehouses-content',
  'collections': '.collection-card',
  'food-items': '#food-search-input',
  'search': '#search-input',
};

const PUBLIC = {
  'home': (page) => expect(page.locator('.hero h1')).toContainText('Digital Trust'),
  'about': (page) => expect(page.locator('.page-header h1')).toContainText('About'),
  'contact': (page) => expect(page.locator('.page-header h1')).toContainText('Contact'),
  'verify': (page) => expect(page.locator('.page-header h1')).toContainText('Verify'),
  'login': (page) => expect(page.locator('.auth-card p')).toContainText('Digital Trust Infrastructure'),
};

async function registerUser(request, tag) {
  const email = tag ? `audit-${tag}+${rand()}@example.com` : randEmail();
  const res = await request.post('/api/v1/auth/register', {
    data: { email, password: 'Password123!', full_name: 'Audit User', company: 'AuditCo', phone: `+1${rand()}` },
  });
  expect(res.ok()).toBeTruthy();
  const data = await res.json();
  expect(data.access_token).toBeTruthy();
  return data;
}

// Attach listeners that collect console errors, page errors, failed requests,
// missing static assets (404) and server errors (>=500) for the page's lifetime.
function trackErrors(page) {
  const issues = { console: [], page: [], failed: [], missing: [], server: [] };
  page.on('console', (m) => { if (m.type() === 'error') issues.console.push(m.text()); });
  page.on('pageerror', (e) => issues.page.push(String(e)));
  page.on('requestfailed', (r) => issues.failed.push(`${r.method()} ${r.url()} (${r.failure() && r.failure().errorText})`));
  page.on('response', (r) => {
    const url = r.url();
    const method = r.request().method();
    const isStatic = /\.(js|css|png|jpe?g|svg|webp|gif|ico|woff2?)$/i.test(url.split('?')[0]);
    if (r.status() === 404 && isStatic) issues.missing.push(`${r.status()} ${method} ${url}`);
    if (r.status() >= 500) issues.server.push(`${r.status()} ${method} ${url}`);
  });
  return issues;
}

function assertClean(issues, context) {
  expect(issues.console, `console errors on ${context}`).toEqual([]);
  expect(issues.page, `page errors on ${context}`).toEqual([]);
  expect(issues.failed, `failed requests on ${context}`).toEqual([]);
  expect(issues.missing, `missing static assets on ${context}`).toEqual([]);
  expect(issues.server, `server errors on ${context}`).toEqual([]);
}

test.describe('Routing & wiring audit', () => {

  test('auth guard redirects unauthenticated users to login for every protected route', async ({ page }) => {
    for (const route of Object.keys(GUARDED)) {
      await page.goto(`/#${route}`);
      await expect(page, `route #${route} should redirect to #login`).toHaveURL(/#login$/);
    }
  });

  test('unknown route renders the Page not found empty state', async ({ page }) => {
    await page.goto('/#definitely-not-a-route');
    await expect(page.locator('.empty-state h3')).toContainText('Page not found');
  });

  test('public pages render cleanly without console/network errors', async ({ page }) => {
    for (const [route, assert] of Object.entries(PUBLIC)) {
      const issues = trackErrors(page);
      await page.goto(`/#${route}`);
      await assert(page);
      assertClean(issues, `public page #${route}`);
    }
  });

  test('guest-open routes render for unauthenticated users without redirect or errors', async ({ page }) => {
    for (const [route, selector] of Object.entries(OPEN)) {
      const issues = trackErrors(page);
      await page.goto(`/#${route}`);
      await expect(page, `route #${route} should stay on the page`).toHaveURL(new RegExp('#'.concat(route, '$')));
      await expect(page.locator(selector).first()).toBeVisible();
      assertClean(issues, `guest-open route #${route}`);
    }
  });

  test('every protected route renders with a valid session and no errors', async ({ request, browser }) => {
    const data = await registerUser(request, 'nav');
    const page = await browser.newPage();
    await page.addInitScript((token) => {
      localStorage.setItem('ft_token', token);
      localStorage.setItem('ft_user', JSON.stringify({ full_name: 'Audit User' }));
    }, data.access_token);

    for (const [route, title] of Object.entries(GUARDED)) {
      const issues = trackErrors(page);
      await page.goto(`/#${route}`);
      await expect(page.locator('.topbar h2')).toContainText(title);
      await expect(page).toHaveURL(new RegExp('#'.concat(route, '$')));
      assertClean(issues, `protected route #${route}`);
    }
    await page.close();
  });
});

test.describe('CRUD round-trip audit', () => {

  test('taxonomy item -> product -> batch -> warehouse -> shipment -> certificate, then UI detail pages', async ({ request, browser }) => {
    const data = await registerUser(request, 'crud');
    const H = { Authorization: `Bearer ${data.access_token}` };
    const created = {};

    // 1. Taxonomy item
    const tax = await request.post('/api/v1/taxonomy', { headers: H, data: { name: `AuditTax ${rand()}`, description: 'audit' } });
    expect(tax.ok(), `create taxonomy: ${tax.status()} ${await tax.text()}`).toBeTruthy();
    const taxJson = await tax.json();
    const taxonomy_id = taxJson.id;

    const node = await request.post(`/api/v1/taxonomy/${taxonomy_id}/nodes`, { headers: H, data: { code: `N${rand()}`, name: 'Audit Node' } });
    expect(node.ok(), `create node: ${node.status()} ${await node.text()}`).toBeTruthy();
    const nodeJson = await node.json();
    const node_id = nodeJson.id;

    const item = await request.post('/api/v1/taxonomy/items', { headers: H, data: { node_id, code: `AUD-${rand()}`, common_name: 'Audit Mango', scientific_name: 'Mangifera indica' } });
    expect(item.ok(), `create taxonomy item: ${item.status()} ${await item.text()}`).toBeTruthy();
    const itemJson = await item.json();
    created.item_id = itemJson.id;
    expect(created.item_id).toBeTruthy();

    // 2. Product referencing the item
    const prod = await request.post('/api/v1/products', { headers: H, data: { sku: `FT-AUD-${rand()}`, name: 'Audit Product', category: 'fresh_produce', origin_country: 'UAE', producer_name: 'Audit Farms' } });
    expect(prod.ok(), `create product: ${prod.status()} ${await prod.text()}`).toBeTruthy();
    const prodJson = await prod.json();
    created.product_id = prodJson.id || prodJson.product?.id;
    expect(created.product_id).toBeTruthy();

    // 3. Batch for the product
    const batch = await request.post('/api/v1/batches', { headers: H, data: { batch_number: `B-AUD-${rand()}`, product_id: created.product_id, quantity: 250 } });
    expect(batch.ok(), `create batch: ${batch.status()} ${await batch.text()}`).toBeTruthy();
    const batchJson = await batch.json();
    created.batch_id = batchJson.id;
    expect(created.batch_id).toBeTruthy();

    // 4. Warehouse + put batch into it
    const wh = await request.post('/api/v1/warehouses', { headers: H, data: { code: `WH-${rand()}`, name: 'Audit Warehouse', city: 'Abu Dhabi', country: 'UAE', capacity_items: 1000 } });
    expect(wh.ok(), `create warehouse: ${wh.status()} ${await wh.text()}`).toBeTruthy();
    const whJson = await wh.json();
    created.warehouse_id = whJson.id;
    expect(created.warehouse_id).toBeTruthy();

    const whItem = await request.post(`/api/v1/warehouses/${created.warehouse_id}/items`, { headers: H, data: { batch_id: created.batch_id, quantity: 250, zone: 'A', rack: 'R1', bin: 'B1' } });
    expect(whItem.ok(), `add batch to warehouse: ${whItem.status()} ${await whItem.text()}`).toBeTruthy();

    // 5. Shipment + attach batch
    const ship = await request.post('/api/v1/shipments', { headers: H, data: { shipment_number: `SH-${rand()}`, mode: 'truck', carrier_name: 'Audit Logistics', total_weight_kg: 250 } });
    expect(ship.ok(), `create shipment: ${ship.status()} ${await ship.text()}`).toBeTruthy();
    const shipJson = await ship.json();
    created.shipment_id = shipJson.id;
    expect(created.shipment_id).toBeTruthy();

    const attach = await request.post(`/api/v1/shipments/${created.shipment_id}/batches`, { headers: H, data: { batch_id: created.batch_id, quantity: 250 } });
    expect(attach.ok(), `attach batch to shipment: ${attach.status()} ${await attach.text()}`).toBeTruthy();

    // 6. Certificate for the product
    const cert = await request.post('/api/v1/certificates', { headers: H, data: { product_id: created.product_id, type: 'organic', issuing_body: 'Audit Certifier', recipient_entity: 'Audit Farms' } });
    expect(cert.ok(), `create certificate: ${cert.status()} ${await cert.text()}`).toBeTruthy();
    const certJson = await cert.json();
    const certOut = certJson.certificate || certJson;
    created.certificate_id = certOut.certificate_id;
    expect(created.certificate_id).toBeTruthy();

    // Verify read-backs
    for (const [endpoint, key] of [
      ['/api/v1/products', 'products'],
      ['/api/v1/batches', 'batches'],
      ['/api/v1/warehouses', 'warehouses'],
      ['/api/v1/shipments', 'shipments'],
      ['/api/v1/certificates', 'certificates'],
      [`/api/v1/taxonomy/items/${created.item_id}`, 'item'],
    ]) {
      const res = await request.get(endpoint, { headers: H });
      expect(res.ok(), `GET ${endpoint} -> ${res.status()}`).toBeTruthy();
    }

    // UI detail pages render
    const page = await browser.newPage();
    await page.addInitScript((token) => {
      localStorage.setItem('ft_token', token);
      localStorage.setItem('ft_user', JSON.stringify({ full_name: 'Audit User' }));
    }, data.access_token);

    const detailRoutes = [
      [`product/${created.product_id}`, 'Product Detail'],
      [`batches/${created.batch_id}`, 'Batch Detail'],
      [`warehouses/${created.warehouse_id}`, 'Warehouse Detail'],
      [`shipments/${created.shipment_id}`, 'Shipment Detail'],
      [`certificate/${created.certificate_id}`, 'Certificate Detail'],
    ];
    for (const [route, title] of detailRoutes) {
      const issues = trackErrors(page);
      await page.goto(`/#${route}`);
      await expect(page.locator('.topbar h2')).toContainText(title);
      assertClean(issues, `detail page #${route}`);
    }
    await page.close();
  });
});
