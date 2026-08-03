/*
 * Full-circle audit using Puppeteer.
 * Crawls the public + authenticated routes, capturing:
 *   - console/page errors
 *   - failed requests
 *   - 4xx/5xx API responses (wiring/server errors)
 *   - missing static assets (404)
 *   - auth-guard redirects (unauthenticated -> #login)
 * Run: node puppeteer-audit.js
 */
const puppeteer = require('puppeteer');
const crypto = require('crypto');

const BASE = process.env.BASE_URL || 'http://127.0.0.1:8000';
const rand = () => crypto.randomBytes(6).toString('hex');

const GUARDED = [
  'dashboard', 'products', 'traceability', 'certificates', 'analytics',
  'share', 'taxonomy', 'batches', 'warehouses', 'shipments', 'collections',
  'feeds', 'food-items', 'cargo-tracking', 'bulking', 'settings',
];
const PUBLIC = ['home', 'about', 'contact', 'verify', 'login'];

async function registerUser() {
  const body = {
    email: `pptr-${rand()}@example.com`, password: 'Password123!',
    full_name: 'Puppeteer Audit', company: 'PptrCo', phone: `+1${rand()}`,
  };
  for (let attempt = 1; attempt <= 5; attempt++) {
    const res = await fetch(`${BASE}/api/v1/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (res.ok) return res.json();
    if (res.status === 429 && attempt < 5) {
      console.log(`rate-limited on register (attempt ${attempt}/5), backing off…`);
      await new Promise((r) => setTimeout(r, 60000));
      continue;
    }
    throw new Error(`register failed: ${res.status} ${await res.text()}`);
  }
}

function track(page) {
  const issues = { console: [], page: [], failed: [], missing: [], api4xx: [], api5xx: [], redirects: [] };
  page.on('console', (m) => { if (m.type() === 'error') issues.console.push(m.text()); });
  page.on('pageerror', (e) => issues.page.push(String(e)));
  page.on('requestfailed', (r) => issues.failed.push(`${r.method()} ${r.url()} ${r.failure() && r.failure().errorText}`));
  page.on('response', (r) => {
    const url = r.url();
    const status = r.status();
    const isStatic = /\.(js|css|png|jpe?g|svg|webp|gif|ico|woff2?)$/i.test(url.split('?')[0]);
    if (status === 404 && isStatic) issues.missing.push(`${status} ${url}`);
    else if (url.includes('/api/')) {
      if (status >= 500) issues.api5xx.push(`${status} ${r.request().method()} ${url}`);
      else if (status >= 400) issues.api4xx.push(`${status} ${r.request().method()} ${url}`);
    }
  });
  return issues;
}

async function main() {
  const browser = await puppeteer.launch({ headless: 'new' });
  let failures = 0;

  // 1. Auth guard redirects
  {
    const page = await browser.newPage();
    const issues = track(page);
    for (const route of GUARDED) {
      await page.goto(`${BASE}/#${route}`);
      await page.waitForTimeout(150);
      const url = page.url();
      if (!url.endsWith('#login')) {
        failures++;
        console.log(`FAIL auth-guard: #${route} -> ${url} (expected #login)`);
      } else {
        console.log(`ok   auth-guard: #${route} redirects to #login`);
      }
    }
    await page.close();
  }

  // 2. Public routes
  {
    const page = await browser.newPage();
    const issues = track(page);
    for (const route of PUBLIC) {
      await page.goto(`${BASE}/#${route}`);
      await page.waitForTimeout(400);
    }
    reportIssues(issues, 'public routes', (k) => { failures++; });
    await page.close();
  }

  // 3. Authenticated routes
  {
    const data = await registerUser();
    const page = await browser.newPage();
    await page.evaluateOnNewDocument((token) => {
      localStorage.setItem('ft_token', token);
      localStorage.setItem('ft_user', JSON.stringify({ full_name: 'Puppeteer Audit' }));
    }, data.access_token);
    const issues = track(page);
    for (const route of GUARDED) {
      await page.goto(`${BASE}/#${route}`);
      await page.waitForTimeout(400);
      const title = await page.$eval('.topbar h2', (el) => el.textContent).catch(() => null);
      if (!title) { failures++; console.log(`FAIL render: #${route} no .topbar h2`); }
      else console.log(`ok   render: #${route} -> "${title.trim()}"`);
    }
    reportIssues(issues, 'authenticated routes', (k) => { failures++; });
    await page.close();
  }

  console.log(failures === 0 ? '\nPUPPETEER AUDIT: ALL CLEAR' : `\nPUPPETEER AUDIT: ${failures} failure(s)`);
  await browser.close();
  process.exit(failures === 0 ? 0 : 1);
}

function reportIssues(issues, context, onFail) {
  for (const key of ['console', 'page', 'failed', 'missing', 'api4xx', 'api5xx']) {
    if (issues[key].length) {
      onFail(key);
      console.log(`\n${key.toUpperCase()} on ${context}:`);
      issues[key].slice(0, 20).forEach((i) => console.log('  - ' + i));
      if (issues[key].length > 20) console.log(`  ... and ${issues[key].length - 20} more`);
    }
  }
}

main().catch((e) => { console.error('FATAL', e); process.exit(2); });
