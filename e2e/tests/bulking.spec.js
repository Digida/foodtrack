const { test, expect } = require('@playwright/test');
const crypto = require('crypto');

function rand() { return crypto.randomBytes(5).toString('hex'); }
function randEmail(tag) { return `${tag}+${rand()}@example.com`; }

async function register(request, tag, opts = {}) {
  const res = await request.post('/api/v1/auth/register', {
    data: {
      email: randEmail(tag), password: 'Password123!',
      full_name: opts.full_name || 'Bulking User',
      company: opts.company || 'InvestCo',
      phone: `+1${rand()}`,
    },
  });
  expect(res.ok(), `register ${tag}: ${res.status()} ${await res.text()}`).toBeTruthy();
  return (await res.json());
}

function trackErrors(page) {
  const issues = { console: [], page: [], failed: [], missing: [], server: [] };
  page.on('console', (m) => { if (m.type() === 'error') issues.console.push(m.text()); });
  page.on('pageerror', (e) => issues.page.push(String(e)));
  page.on('requestfailed', (r) => issues.failed.push(`${r.method()} ${r.url()} (${r.failure() && r.failure().errorText})`));
  page.on('response', (r) => {
    const url = r.url();
    if (/\.(js|css|png|jpe?g|svg|webp|gif|ico|woff2?)$/i.test(url.split('?')[0]) && r.status() === 404) issues.missing.push(`${r.status()} ${url}`);
    if (r.status() >= 500) issues.server.push(`${r.status()} ${url}`);
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

test.describe('Investor bulking cycle (escrow, member jobs, pack, certify, deliver)', () => {

  test('full pipeline runs end-to-end and the UI reflects it without errors', async ({ request, browser }) => {
    const entity = `Green Valley Coop ${rand()}`;
    const certCo = `Acme Cert ${rand()}`;

    // ── Users ────────────────────────────────────────────────────────────────
    const investor = await register(request, 'investor', { full_name: 'Investor', company: 'InvestCo' });
    const H = { Authorization: `Bearer ${investor.access_token}` };
    const members = {};
    for (const name of ['Clerk', 'Verifier', 'Packer', 'Courier']) {
      members[name] = await register(request, name.toLowerCase(), { full_name: `${name} User`, company: entity });
      // small pacing to avoid SQLite lock races
      await new Promise(r => setTimeout(r, 300));
    }
    const certifier = await register(request, 'certifier', { full_name: 'Certifier User', company: certCo });
    const sameCo = await register(request, 'selfcert', { full_name: 'Self Certifier', company: entity });

    // ── Setup: rare item + register with sourcing entity ────────────────────
    const tax = await (await request.post('/api/v1/taxonomy', { headers: H, data: { name: `BulkTax ${rand()}`, description: 'e2e' } })).json();
    const node = await (await request.post(`/api/v1/taxonomy/${tax.id}/nodes`, { headers: H, data: { code: `N${rand()}`, name: 'Node' } })).json();
    const item = await (await request.post('/api/v1/taxonomy/items', { headers: H, data: { node_id: node.id, code: `RARE-${rand()}`, common_name: `Rare Spice ${rand()}`, supply_band: 'rare' } })).json();

    const regRes = await request.post('/api/v1/commerce/registers', {
      headers: H,
      data: { item_id: item.id, target_quantity: 1000, target_price: 5, currency: 'USD', sourcing_entity_name: entity, auto_generate: true },
    });
    expect(regRes.ok(), `register: ${regRes.status()} ${await regRes.text()}`).toBeTruthy();
    const registerId = (await regRes.json()).id;

    // ── Contact + bid + accept + escrow (65% for rare) ──────────────────────
    const contact = await (await request.post(`/api/v1/commerce/registers/${registerId}/contacts`, { headers: H, data: { name: 'Farmer Mwangi', contact_type: 'farmer', location: 'Lake Zone' } })).json();
    const bid = await (await request.post(`/api/v1/commerce/registers/${registerId}/bids`, { headers: H, data: { quantity: 1000, unit_price: 5, unit: 'kg', contact_id: contact.id } })).json();
    await request.post(`/api/v1/commerce/bids/${bid.id}/accept`, { headers: H });

    const escrowReq = await (await request.get(`/api/v1/commerce/registers/${registerId}/escrow`, { headers: H })).json();
    expect(escrowReq.supply_band).toBe('rare');
    expect(escrowReq.escrow_percentage).toBe(65.0);
    const deposit = await (await request.post(`/api/v1/commerce/registers/${registerId}/escrow/deposit`, { headers: H, data: { method: 'bank_transfer' } })).json();
    expect(deposit.status).toBe('deposited');

    // ── Same-company certifier is blocked (400) ─────────────────────────────
    const blocked = await request.post(`/api/v1/commerce/registers/${registerId}/job-assignments`, {
      headers: H,
      data: { role: 'certifier', assignee_id: sameCo.user.id },
    });
    expect(blocked.status(), 'same-company certifier should be blocked').toBe(400);
    expect((await blocked.json()).detail).toMatch(/sourcing entity|self-certification/i);

    // ── Assign all five roles (certifier from a different company) ──────────
    const assignments = {};
    for (const [name, role] of [['Clerk', 'clerk'], ['Verifier', 'verifier'], ['Packer', 'packer'], ['Courier', 'courier']]) {
      const a = await (await request.post(`/api/v1/commerce/registers/${registerId}/job-assignments`, {
        headers: H, data: { role, assignee_id: members[name].user.id, assignee_location: 'Lake Zone' },
      })).json();
      assignments[role] = a.id;
    }
    const certAssign = await (await request.post(`/api/v1/commerce/registers/${registerId}/job-assignments`, {
      headers: H, data: { role: 'certifier', assignee_id: certifier.user.id, assignee_location: 'City' },
    })).json();
    assignments.certifier = certAssign.id;

    // ── Complete all jobs ────────────────────────────────────────────────────
    for (const id of Object.values(assignments)) {
      expect((await request.patch(`/api/v1/commerce/job-assignments/${id}/status`, { headers: H, data: { status: 'in_progress' } })).ok()).toBeTruthy();
      expect((await request.patch(`/api/v1/commerce/job-assignments/${id}/status`, { headers: H, data: { status: 'completed' } })).ok()).toBeTruthy();
    }

    // ── Certificate + packing record + certify ──────────────────────────────
    const cert = await (await request.post('/api/v1/certificates', { headers: H, data: { item_id: item.id, type: 'organic', issuing_body: certCo } })).json();
    const certificateId = cert.certificate.certificate_id;
    const pack = await (await request.post(`/api/v1/commerce/registers/${registerId}/packing-records`, {
      headers: H, data: { quantity: 1000, unit: 'kg', package_type: 'sacks', package_count: 50 },
    })).json();
    const certPack = await request.patch(`/api/v1/commerce/packing-records/${pack.id}/status`, { headers: H, data: { status: 'certified', certificate_id: certificateId } });
    expect(certPack.ok(), `certify packing: ${certPack.status()} ${await certPack.text()}`).toBeTruthy();

    // ── Courier deliver-to-buyer -> escrow released ─────────────────────────
    const courier = await (await request.post(`/api/v1/commerce/registers/${registerId}/courier-jobs`, {
      headers: H, data: { pickup_location: 'Warehouse A', quantity: 1000, budget: 200, deliver_to_buyer: true },
    })).json();
    for (const s of ['assigned', 'in_transit', 'delivered']) {
      expect((await request.patch(`/api/v1/commerce/courier-jobs/${courier.id}/status`, { headers: H, data: { status: s } })).ok()).toBeTruthy();
    }
    const escrowAfter = await (await request.get(`/api/v1/commerce/registers/${registerId}/escrow`, { headers: H })).json();
    expect(escrowAfter.status).toBe('released');

    // ── Pipeline trace ───────────────────────────────────────────────────────
    const trace = await (await request.get(`/api/v1/commerce/registers/${registerId}/pipeline`, { headers: H })).json();
    const stageStatus = Object.fromEntries(trace.stages.map(s => [s.key, s.status]));
    expect(stageStatus.escrow).toBe('released');
    expect(stageStatus.jobs).toBe('5/5 completed');
    expect(stageStatus.pack).toBe('packed');
    expect(stageStatus.certify).toBe('certified');
    expect(stageStatus.deliver).toBe('delivered');
    expect(stageStatus.receive).toBe('received');
    for (const r of Object.values(trace.roles)) {
      expect(r.completed).toBe(r.assigned);
    }

    // ── UI: register detail page shows escrow, jobs, trace, no errors ───────
    const page = await browser.newPage();
    await page.addInitScript((token) => {
      localStorage.setItem('ft_token', token);
      localStorage.setItem('ft_user', JSON.stringify({ full_name: 'Investor' }));
    }, investor.access_token);

    const issues = trackErrors(page);
    await page.goto(`/#bulking/${registerId}`);
    await expect(page.locator('.topbar h2')).toContainText('Bulking Register');
    await expect(page.locator('.card-header h3', { hasText: 'Investor Escrow' })).toBeVisible();
    await expect(page.locator('.trace-cell.trace-done')).toHaveCount(8);
    await expect(page.locator('#bulk-pipeline-trace')).toContainText('received');
    assertClean(issues, 'register detail after full cycle');
    await page.close();

    // ── UI: home page shows the expanded bulking/escrow cards ───────────────
    const home = await browser.newPage();
    const hIssues = trackErrors(home);
    await home.goto('/#home');
    await expect(home.locator('.feature-card h3', { hasText: 'Investor Bulking & Escrow' })).toBeVisible();
    await expect(home.locator('.feature-card h3', { hasText: 'Member Job Pipeline' })).toBeVisible();
    await expect(home.locator('.hero-actions a', { hasText: 'Bulk & Invest' })).toBeVisible();
    assertClean(hIssues, 'home page');
    await home.close();
  });

  test('UI register modal supports sourcing entity and navigates to the new register', async ({ request, browser }) => {
    const investor = await register(request, 'uimodal', { full_name: 'UI Modal User', company: 'InvestCo' });
    const H = { Authorization: `Bearer ${investor.access_token}` };
    const tax = await (await request.post('/api/v1/taxonomy', { headers: H, data: { name: `ModalTax ${rand()}`, description: 'e2e' } })).json();
    const node = await (await request.post(`/api/v1/taxonomy/${tax.id}/nodes`, { headers: H, data: { code: `N${rand()}`, name: 'Node' } })).json();
    const item = await (await request.post('/api/v1/taxonomy/items', { headers: H, data: { node_id: node.id, code: `MOD-${rand()}`, common_name: `Modal Item ${rand()}`, supply_band: 'abundant' } })).json();

    const page = await browser.newPage();
    await page.addInitScript((token) => {
      localStorage.setItem('ft_token', token);
      localStorage.setItem('ft_user', JSON.stringify({ full_name: 'UI Modal User' }));
    }, investor.access_token);

    const issues = trackErrors(page);
    await page.goto('/#bulking');
    await expect(page.locator('.topbar h2')).toContainText('Bulking');
    await page.click('text=+ New Register');

    await page.fill('#bq-item-search', item.common_name.slice(0, 12));
    await page.waitForSelector('.autocomplete-dropdown.open .autocomplete-item', { timeout: 8000 });
    await page.click('.autocomplete-dropdown.open .autocomplete-item');

    await page.fill('#bq-qty', '500');
    await page.fill('#bq-price', '4');
    await page.fill('#bq-entity', `Sourcing Coop ${rand()}`);

    await page.click('button:has-text("Create")');
    await expect(page).toHaveURL(/#bulking\/\d+$/);
    await expect(page.locator('.topbar h2')).toContainText('Bulking Register');
    await expect(page.locator('.info-row .info-value', { hasText: 'Sourcing Coop' })).toBeVisible();
    await expect(page.locator('.card-header h3', { hasText: 'Investor Escrow' })).toBeVisible();
    assertClean(issues, 'register modal flow');
    await page.close();
  });
});
