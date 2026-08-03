const { test, expect } = require('@playwright/test');
const crypto = require('crypto');

function randEmail() { return `e2e+${crypto.randomBytes(4).toString('hex')}@example.com`; }

test('API: register, create bulking register, add contact, submit bid, accept bid', async ({ request }) => {
  const clerk = { email: randEmail(), password: 'Password123!', full_name: 'Clerk User', company: 'ClerkCo', phone: `+1${crypto.randomBytes(8).toString('hex')}` };
  const verifier = { email: randEmail(), password: 'Password123!', full_name: 'Verifier User', company: 'VerifyCo', phone: `+1${crypto.randomBytes(8).toString('hex')}` };

  // Register clerk
  const r1 = await request.post('/api/v1/auth/register', { data: { email: clerk.email, password: clerk.password, full_name: clerk.full_name, company: clerk.company, phone: clerk.phone } });
  expect(r1.ok()).toBeTruthy();
  const clerkData = await r1.json();
  expect(clerkData.access_token).toBeTruthy();

  // Register verifier
  const r2 = await request.post('/api/v1/auth/register', { data: { email: verifier.email, password: verifier.password, full_name: verifier.full_name, company: verifier.company, phone: verifier.phone } });
  expect(r2.ok()).toBeTruthy();
  const verifierData = await r2.json();
  expect(verifierData.access_token).toBeTruthy();

  // Clerk creates a bulking register
  const authClerk = { headers: { Authorization: `Bearer ${clerkData.access_token}` } };

  // Find an existing item to reference: GET /api/v1/products
  let products = await request.get('/api/v1/products', authClerk);
  expect(products.ok()).toBeTruthy();
  const prodJson = await products.json();
  const item_id = (prodJson.products && prodJson.products[0] && prodJson.products[0].id) || null;
  expect(item_id).not.toBeNull();

  const createRes = await request.post('/api/v1/commerce/registers', { data: { item_id, target_quantity: 100, title: 'E2E Register', unit: 'kg', target_price: 1.5 }, headers: { Authorization: `Bearer ${clerkData.access_token}` } });
  expect(createRes.ok()).toBeTruthy();
  const register = await createRes.json();
  expect(register.id).toBeTruthy();

  // Add contact
  const contactRes = await request.post(`/api/v1/commerce/registers/${register.id}/contacts`, { data: { name: 'Farmer Joe', contact_type: 'farmer', phone: '+1234567890' }, headers: { Authorization: `Bearer ${clerkData.access_token}` } });
  expect(contactRes.ok()).toBeTruthy();
  const contact = await contactRes.json();
  expect(contact.id).toBeTruthy();

  // Owner (buyer) submits a farmer offer as a bid
  const bidRes = await request.post(`/api/v1/commerce/registers/${register.id}/bids`, { data: { quantity: 50, unit_price: 1.6, contact_id: contact.id }, headers: { Authorization: `Bearer ${clerkData.access_token}` } });
  expect(bidRes.ok()).toBeTruthy();
  const bid = await bidRes.json();
  expect(bid.id).toBeTruthy();

  // Owner accepts the bid
  const acceptRes = await request.post(`/api/v1/commerce/bids/${bid.id}/accept`, { headers: { Authorization: `Bearer ${clerkData.access_token}` } });
  expect(acceptRes.ok()).toBeTruthy();
  const accept = await acceptRes.json();
  expect(accept.status).toBeTruthy();
});

test('UI routes load and auth-protected dashboard accessible when token set', async ({ browser, request }) => {
  const page = await browser.newPage();
  await page.goto('/');
  await expect(page.locator('h1')).toContainText('Digital Trust');

  // Create a user via API and seed localStorage
  const email = `e2e+${crypto.randomBytes(4).toString('hex')}@example.com`;
  const reg = await request.post('/api/v1/auth/register', { data: { email, password: 'Password123!', full_name: 'UI User' } });
  const data = await reg.json();
  // Set token and user in localStorage before any script runs
  await page.addInitScript(token => {
    localStorage.setItem('ft_token', token);
  }, data.access_token);
  await page.reload();
  await page.goto('/#dashboard');
  // Expect dashboard heading present (UI.layout renders title in an h2)
  await expect(page.locator('.topbar h2')).toContainText('Dashboard');
  await page.close();
});
