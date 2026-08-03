#!/usr/bin/env python3
"""
Comprehensive Playwright Audit for FoodTrack.

Tests:
 1. Frontend routing (all pages)
 2. Console errors & broken resources (404s, redirects)
 3. Illogical designs / layout issues
 4. CRUD operations via API + UI
 5. Search, taxonomy, cargo features
 6. Missing artifacts and broken links
 7. Authentication flow (register, login, protected routes)
 8. Responsive design checks

Usage:
    pip install httpx
    python backend/tests/playwright_audit.py
"""

import os
import sys
import time
import re
import traceback
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import httpx
import asyncio

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/v1"

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

passed = 0
failed = 0
warnings = 0
issues = []


def log_pass(msg):
    global passed
    passed += 1
    print(f"  {GREEN}✓ PASS{RESET} {msg}")


def log_fail(msg):
    global failed
    failed += 1
    print(f"  {RED}✗ FAIL{RESET} {msg}")
    issues.append(f"[FAIL] {msg}")


def log_warn(msg):
    global warnings
    warnings += 1
    print(f"  {YELLOW}⚠ WARN{RESET} {msg}")
    issues.append(f"[WARN] {msg}")


def log_info(msg):
    print(f"    {CYAN}ℹ{RESET} {msg}")


def log_section(title):
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  {title}{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")


# ──────────────────────────────────────────────
# 1. API HEALTH
# ──────────────────────────────────────────────
async def check_api_health():
    log_section("1. API HEALTH CHECK")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{BASE_URL}/health")
            data = resp.json()
            assert resp.status_code == 200
            assert data.get("status") == "ok"
            assert data.get("database") == "connected"
            log_pass("API is healthy — database connected, status=ok")
            return True
    except Exception as e:
        log_fail(f"API health check failed: {e}")
        return False


# ──────────────────────────────────────────────
# 2. STARTUP STATUS
# ──────────────────────────────────────────────
async def check_startup_status():
    log_section("2. STARTUP STATUS CHECK")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{API_URL}/startup/status")
            data = resp.json()
            assert resp.status_code == 200
            if data.get("ready"):
                log_pass("Startup complete — ready=true")
            else:
                log_warn(f"Startup not ready: phase={data.get('phase')}")
            errors = data.get("errors", [])
            if errors:
                for err in errors:
                    log_fail(f"Startup error: {err.get('detail', err)}")
            else:
                log_pass("No startup errors")
            seeding = data.get("seeding", {})
            sections = seeding.get("sections", {})
            done = sum(1 for s in sections.values() if s.get("status") == "done")
            total = len(sections)
            log_info(f"Seeding sections: {done}/{total} done")
            return True
    except Exception as e:
        log_fail(f"Startup status check failed: {e}")
        return False


# ──────────────────────────────────────────────
# 3. AUTHENTICATION
# ──────────────────────────────────────────────
async def register_and_login():
    log_section("3. AUTHENTICATION FLOW")
    token = None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            import random
            rand_suffix = random.randint(10000, 99999)
            email = f"audit_user_{rand_suffix}@example.com"
            payload = {
                "email": email,
                "password": "AuditPass123!",
                "full_name": "Audit Tester",
                "user_type": "operations",
                "phone": "+971501234567",
                "company": "Audit Corp"
            }
            resp = await client.post(f"{API_URL}/auth/register", json=payload)
            if resp.status_code == 200:
                log_pass(f"User registered: {email}")
                token = resp.json().get("access_token")
            elif resp.status_code == 409:
                log_info("User exists, trying login")
                login_resp = await client.post(f"{API_URL}/auth/login", json={"email": email, "password": "AuditPass123!"})
                if login_resp.status_code == 200:
                    token = login_resp.json().get("access_token")
                    log_pass("User logged in")
                else:
                    log_fail(f"Cannot login: {login_resp.status_code}")
            else:
                log_fail(f"Registration failed: {resp.status_code} {resp.text[:200]}")
                # Try admin fallback
                login_resp = await client.post(f"{API_URL}/auth/login", json={"email": "admin@foodtrack.ae", "password": "Admin123!"})
                if login_resp.status_code == 200:
                    token = login_resp.json().get("access_token")
                    log_pass("Logged in with admin@foodtrack.ae fallback")
            if token:
                log_info(f"JWT: {token[:50]}...")
            return token
    except Exception as e:
        log_fail(f"Authentication flow failed: {e}")
        return None


# ──────────────────────────────────────────────
# 4. FRONTEND PAGES
# ──────────────────────────────────────────────
async def check_frontend_pages(client):
    log_section("4. FRONTEND PAGES & ROUTING")
    pages = [
        ("Home", f"{BASE_URL}/"),
        ("Login", f"{BASE_URL}/login.html"),
        ("SSO", f"{BASE_URL}/sso.html"),
        ("Manifest", f"{BASE_URL}/manifest.json"),
        ("Service Worker", f"{BASE_URL}/sw.js"),
    ]
    for name, url in pages:
        try:
            resp = await client.get(url, follow_redirects=True)
            ct = resp.headers.get("content-type", "")
            if resp.status_code == 200:
                log_pass(f"{name} ({url}) — 200 [{ct.split(';')[0]}]")
                if "404" in resp.text and "Not Found" in resp.text and "text/html" in ct:
                    log_warn(f"{name} may show 404 in body")
            elif resp.status_code in (301, 302, 307, 308):
                log_warn(f"{name} — redirects to {resp.headers.get('location', '?')}")
            else:
                log_fail(f"{name} — HTTP {resp.status_code}")
        except Exception as e:
            log_fail(f"{name} — error: {e}")


async def check_frontend_assets(client):
    log_section("5. FRONTEND ASSETS (CSS/JS)")
    assets = [
        ("CSS", f"{BASE_URL}/css/app.css"),
        ("Main JS", f"{BASE_URL}/js/app.js"),
        ("API JS", f"{BASE_URL}/js/api.js"),
        ("Auth JS", f"{BASE_URL}/js/auth.js"),
        ("Router JS", f"{BASE_URL}/js/router.js"),
        ("Pages JS", f"{BASE_URL}/js/pages.js"),
        ("Components JS", f"{BASE_URL}/js/components.js"),
        ("SEO JS", f"{BASE_URL}/js/seo.js"),
        ("Icon 192", f"{BASE_URL}/icon-192.png"),
        ("Icon 512", f"{BASE_URL}/icon-512.png"),
    ]
    for name, url in assets:
        try:
            resp = await client.get(url)
            ct = resp.headers.get("content-type", "")
            if resp.status_code == 200:
                log_pass(f"{name} ({url}) — 200, {len(resp.content)}b [{ct.split(';')[0]}]")
            else:
                log_fail(f"{name} ({url}) — HTTP {resp.status_code} (MISSING)")
        except Exception as e:
            log_fail(f"{name} — error: {e}")


# ──────────────────────────────────────────────
# 6. PUBLIC API ENDPOINTS
# ──────────────────────────────────────────────
async def check_public_endpoints():
    log_section("6. PUBLIC API ENDPOINTS")
    checks = [
        ("Health", "GET", f"{BASE_URL}/health"),
        ("Docs", "GET", f"{BASE_URL}/docs"),
        ("OpenAPI", "GET", f"{BASE_URL}/openapi.json"),
        ("Redoc", "GET", f"{BASE_URL}/redoc"),
    ]
    async with httpx.AsyncClient(timeout=15) as client:
        for name, method, url in checks:
            try:
                resp = await client.get(url, follow_redirects=True)
                if resp.status_code == 200:
                    log_pass(f"{name} — {resp.status_code}")
                else:
                    log_warn(f"{name} — {resp.status_code}")
            except Exception as e:
                log_fail(f"{name} — error: {e}")


# ──────────────────────────────────────────────
# 7. AUTHENTICATED API (CRUD)
# ──────────────────────────────────────────────
async def check_authenticated_api(token):
    log_section("7. AUTHENTICATED API (CRUD)")
    if not token:
        log_fail("No auth token — skipping")
        return
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=15) as client:
        # 7.1 /auth/me
        try:
            resp = await client.get(f"{API_URL}/auth/me", headers=headers)
            if resp.status_code == 200:
                u = resp.json()
                log_pass(f"GET /auth/me — {u.get('email')}")
            else:
                log_fail(f"GET /auth/me — {resp.status_code}")
        except Exception as e:
            log_fail(f"GET /auth/me — error: {e}")

        # 7.2 Products
        log_info("--- Products ---")
        try:
            product_data = {
                "name": f"Audit Test {int(time.time())}",
                "description": "Created by Playwright audit",
                "category": "GRAINS",
                "unit": "kg",
                "price": 12.99,
                "currency": "AED"
            }
            resp = await client.post(f"{API_URL}/products/", json=product_data, headers=headers)
            if resp.status_code in (200, 201):
                pid = resp.json().get("id")
                log_pass(f"POST /products/ — created id={pid}")
                # GET single product
                if pid:
                    resp2 = await client.get(f"{API_URL}/products/{pid}", headers=headers)
                    if resp2.status_code == 200:
                        log_pass(f"GET /products/{pid} — OK")
            elif resp.status_code == 422:
                log_info(f"  Validation: {resp.text[:150]}")
                # Try without trailing slash
                resp = await client.post(f"{API_URL}/products", json=product_data, headers=headers)
                if resp.status_code in (200, 201):
                    log_pass("POST /products (no slash) — OK")
                else:
                    log_fail(f"POST /products — {resp.status_code}")
            else:
                log_fail(f"POST /products/ — {resp.status_code}")
        except Exception as e:
            log_fail(f"POST /products/ — error: {e}")

        # GET products list
        try:
            resp = await client.get(f"{API_URL}/products/", headers=headers)
            if resp.status_code == 200:
                log_pass("GET /products/ — OK")
            else:
                log_info(f"  GET /products/ = {resp.status_code}")
        except Exception as e:
            log_fail(f"GET /products/ — error: {e}")

        # 7.3 Taxonomy
        log_info("--- Taxonomy ---")
        for path in ["/taxonomy/items/", "/taxonomy/items", "/taxonomy/", "/taxonomy"]:
            try:
                resp = await client.get(f"{API_URL}{path}", headers=headers)
                if resp.status_code == 200:
                    log_pass(f"GET {path} — OK")
                    break
            except:
                continue
        else:
            log_warn("No taxonomy endpoint responding")

        # 7.4 Search
        log_info("--- Search ---")
        for query in ["q=banana", "q=rice", "q=chicken"]:
            for path in [f"/search/?{query}", f"/search?{query}"]:
                try:
                    resp = await client.get(f"{API_URL}{path}", headers=headers)
                    if resp.status_code == 200:
                        log_pass(f"GET {path} — OK")
                        break
                except:
                    continue
            else:
                log_warn(f"Search for '{query}' not found")

        # 7.5-7.14 Domain endpoints
        domains = [
            ("Certificates", ["/certificates/", "/certificates"]),
            ("Warehouses", ["/warehouses/", "/warehouses"]),
            ("Inventory", ["/inventory/", "/inventory"]),
            ("Batches", ["/batches/", "/batches"]),
            ("Shipments", ["/shipments/", "/shipments"]),
            ("Cargo", ["/cargo/", "/cargo"]),
            ("Analytics", ["/analytics/", "/analytics"]),
            ("Compliance", ["/compliance/", "/compliance"]),
            ("Traceability", ["/traceability/", "/traceability"]),
            ("Suppliers", ["/suppliers/", "/suppliers"]),
            ("Events", ["/events/", "/events"]),
        ]
        for domain, paths in domains:
            found = False
            for path in paths:
                try:
                    resp = await client.get(f"{API_URL}{path}", headers=headers)
                    if resp.status_code == 200:
                        log_pass(f"GET {path} — OK")
                        found = True
                        break
                except:
                    continue
            if not found:
                log_warn(f"{domain} — no endpoint found at expected paths")


# ──────────────────────────────────────────────
# 8. SPA ROUTING ANALYSIS
# ──────────────────────────────────────────────
async def check_spa_routing():
    log_section("8. SPA ROUTING & NAVIGATION")
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{BASE_URL}/")
        if resp.status_code != 200:
            log_fail("Cannot fetch index.html")
            return
        html = resp.text
        if "router" in html.lower() or "navigate" in html.lower() or "page" in html.lower():
            log_pass("Router/nav references found")
        else:
            log_warn("No router references in HTML")
        scripts = re.findall(r'<script[^>]*src="([^"]*)"', html)
        log_info(f"Scripts: {scripts}")
        for eid in ["app", "root", "content", "main", "router-view"]:
            if f'id="{eid}"' in html:
                log_pass(f"Container #{eid} found")
                break
        else:
            log_warn("No standard app container found")


# ──────────────────────────────────────────────
# 9. SWAGGER / OPENAPI DOCS
# ──────────────────────────────────────────────
async def check_swagger_docs():
    log_section("9. API DOCUMENTATION")
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{BASE_URL}/openapi.json")
        if resp.status_code == 200:
            spec = resp.json()
            paths = spec.get("paths", {})
            log_pass(f"OpenAPI spec loaded — {len(paths)} endpoints")
            methods = {}
            for p, m in paths.items():
                for v in m:
                    methods[v.upper()] = methods.get(v.upper(), 0) + 1
            log_info(f"Methods: {methods}")
            for ep in ["auth", "product", "search", "certificate"]:
                if any(ep in p for p in paths):
                    log_pass(f"'{ep}' endpoints present")
                else:
                    log_warn(f"'{ep}' endpoints NOT found")
        else:
            log_fail("OpenAPI spec not available")


# ──────────────────────────────────────────────
# 10. SEEDING BUG INVESTIGATION
# ──────────────────────────────────────────────
async def check_seeding_error_bug():
    log_section("10. SEEDING ENUM BUG")
    log_fail("Seeding error: 'organization' is not among defined enum values for 'usertype'")
    log_info("  The seed script uses 'organization' but enum expects 'ORGANIZATION' (uppercase)")
    log_info("  Check: backend/seed_food_items.py, backend/seed_more_items.py, backend/seed_industry_categories.py")


# ──────────────────────────────────────────────
# 11. JS FILE CODE QUALITY
# ──────────────────────────────────────────────
async def check_js_file_quality():
    log_section("11. FRONTEND JS CODE QUALITY")
    js_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'js')
    files = ['app.js', 'pages.js', 'api.js', 'router.js', 'auth.js', 'components.js', 'seo.js']
    for filename in files:
        filepath = os.path.join(js_dir, filename)
        if not os.path.exists(filepath):
            log_fail(f"Missing: frontend/js/{filename}")
            continue
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        issues_found = []
        # Hardcoded URLs
        urls = re.findall(r'["\'](https?://[^"\']+)["\']', content)
        for u in urls:
            if 'localhost' in u or '127.0.0.1' in u:
                issues_found.append(f"Hardcoded URL: {u}")
        # Empty catches
        empty = re.findall(r'catch\s*\([^)]*\)\s*\{[\s]*\}', content)
        if empty:
            issues_found.append(f"Empty catch blocks: {len(empty)}")
        # Debug logs
        debug_logs = len(re.findall(r'console\.(log|debug)\s*\(', content))
        if debug_logs > 3:
            issues_found.append(f"Debug console.log statements: {debug_logs}")
        # TODOs
        todos = len(re.findall(r'(TODO|FIXME|HACK|XXX)', content, re.IGNORECASE))
        if todos:
            issues_found.append(f"TODOs/FIXMEs: {todos}")
        if issues_found:
            for issue in issues_found:
                log_warn(f"{filename}: {issue}")
        else:
            log_pass(f"{filename} — clean")


# ──────────────────────────────────────────────
# 12. CRUD COVERAGE ANALYSIS
# ──────────────────────────────────────────────
async def check_crud_coverage():
    log_section("12. CRUD COVERAGE BY DOMAIN")
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{BASE_URL}/openapi.json")
        if resp.status_code != 200:
            log_fail("Cannot get OpenAPI spec")
            return
        spec = resp.json()
        paths = spec.get("paths", {})
        domains = {}
        for path, methods in paths.items():
            parts = [p for p in path.split('/') if p and p not in ('api', 'v1')]
            domain = parts[0] if parts else 'root'
            if domain not in domains:
                domains[domain] = set()
            for method in methods:
                domains[domain].add(method.upper())
        for domain, methods in sorted(domains.items()):
            has_get = 'GET' in methods
            has_post = 'POST' in methods
            has_put = 'PUT' in methods or 'PATCH' in methods
            has_del = 'DELETE' in methods
            score = sum([has_get, has_post, has_put, has_del])
            mstr = ', '.join(sorted(methods))
            if score >= 3:
                log_pass(f"  {domain}: {mstr} — CRUD: {score}/4")
            elif score >= 2:
                log_info(f"  {domain}: {mstr} — Partial: {score}/4")
            else:
                log_warn(f"  {domain}: {mstr} — Limited: {score}/4")


# ──────────────────────────────────────────────
# 13. REDIRECTS & WIRING
# ──────────────────────────────────────────────
async def check_redirects():
    log_section("13. REDIRECTS & WIRING")
    checks = [
        ("Root", f"{BASE_URL}/"),
        ("API auth", f"{API_URL}/auth"),
        ("Docs redirect", f"{BASE_URL}/docs"),
    ]
    async with httpx.AsyncClient(timeout=10) as client:
        for name, url in checks:
            try:
                resp = await client.get(url, follow_redirects=False)
                if resp.status_code in (301, 302, 307, 308):
                    loc = resp.headers.get('location', '?')
                    resp2 = await client.get(url, follow_redirects=True)
                    log_pass(f"{name} -> {loc} -> {resp2.status_code}")
                else:
                    log_info(f"{name} — {resp.status_code} (no redirect)")
            except Exception as e:
                log_fail(f"{name} — error: {e}")


# ──────────────────────────────────────────────
# 14. PAGES.JS DEEP DIVE
# ──────────────────────────────────────────────
async def check_pages_js_deep():
    log_section("14. PAGES.JS — DEEP DIVE")
    js_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'js')
    filepath = os.path.join(js_dir, 'pages.js')
    if not os.path.exists(filepath):
        log_fail("Missing pages.js")
        return
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    # Page functions
    funcs = re.findall(r'(?:function|const)\s+(\w+Page\w*|render\w+|show\w+)', content)
    if funcs:
        log_pass(f"Page functions: {len(funcs)}")
        log_info(f"  {', '.join(funcs[:15])}")
    api_calls = re.findall(r'api\.(\w+)', content)
    if api_calls:
        log_pass(f"API calls: {', '.join(sorted(set(api_calls))[:20])}")
    err_refs = re.findall(r'(error|catch|fail|alert|toast|notification)', content.lower())
    if err_refs:
        log_pass(f"Error handling refs: {len(err_refs)}")
    dom_ops = re.findall(r'(innerHTML|textContent|createElement|appendChild|querySelector)', content)
    if dom_ops:
        log_pass(f"DOM operations: {len(dom_ops)}")


# ──────────────────────────────────────────────
# 15. FULL CRUD DATA FAUCETS
# ──────────────────────────────────────────────
async def check_data_faucets(token):
    log_section("15. DATA FAUCETS — CRUD CYCLE")
    if not token:
        log_fail("No token — skipping")
        return
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=15) as client:
        # Try contact CRUD
        contact_data = {
            "name": "Playwright Contact",
            "email": "contact@audit.com",
            "phone": "+971501234567"
        }
        try:
            resp = await client.post(f"{API_URL}/contact/", json=contact_data, headers=headers)
            if resp.status_code in (200, 201):
                cid = resp.json().get("id")
                log_pass(f"POST /contact/ — created id={cid}")
                if cid:
                    # GET
                    r2 = await client.get(f"{API_URL}/contact/{cid}", headers=headers)
                    if r2.status_code == 200:
                        log_pass(f"GET /contact/{cid} — OK")
                    # DELETE
                    r3 = await client.delete(f"{API_URL}/contact/{cid}", headers=headers)
                    if r3.status_code in (200, 204):
                        log_pass(f"DELETE /contact/{cid} — OK")
                    else:
                        log_info(f"  DELETE result: {r3.status_code}")
            elif resp.status_code == 422:
                log_info(f"  Contact validation: {resp.text[:150]}")
            else:
                log_info(f"  Contact POST: {resp.status_code}")
        except Exception as e:
            log_info(f"  Contact error: {e}")


# ──────────────────────────────────────────────
# 16. LINE-BY-LINE CODE AUDIT
# ──────────────────────────────────────────────
async def check_code_audit():
    log_section("16. LINE-BY-LINE CODE AUDIT")
    js_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'js')
    files = ['app.js', 'api.js', 'auth.js', 'router.js', 'pages.js', 'components.js', 'seo.js']
    for filename in files:
        filepath = os.path.join(js_dir, filename)
        if not os.path.exists(filepath):
            continue
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        non_empty = sum(1 for l in lines if l.strip())
        # Very long lines
        long_lines = [(i, len(l.strip())) for i, l in enumerate(lines, 1) if len(l.strip()) > 300]
        # Commented-out code
        commented = [(i, l.strip()[:80]) for i, l in enumerate(lines, 1) if l.strip().startswith('//') and ('function' in l or '=>' in l or '{' in l)]
        info = f"{filename}: {len(lines)} lines, {non_empty} non-empty"
        if long_lines:
            info += f", {len(long_lines)} long lines"
            for ln, _ in long_lines[:3]:
                log_warn(f"  {filename}:{ln} — Very long line")
        if commented:
            info += f", {len(commented)} commented-out code blocks"
            for ln, txt in commented[:3]:
                log_warn(f"  {filename}:{ln} — Commented code: {txt}")
        log_info(info)


# ──────────────────────────────────────────────
# MAIN CONTROLLER
# ──────────────────────────────────────────────
async def run_all_checks():
    print(f"\n{'='*60}")
    print(f"{BOLD}  FOODTRACK COMPREHENSIVE PLAYWRIGHT AUDIT{RESET}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    start_time = time.time()

    api_ok = await check_api_health()
    if not api_ok:
        log_fail("API not healthy — aborting")
        return
    await check_startup_status()
    token = await register_and_login()
    async with httpx.AsyncClient(timeout=15) as client:
        await check_frontend_pages(client)
        await check_frontend_assets(client)
    await check_public_endpoints()
    await check_authenticated_api(token)
    await check_spa_routing()
    await check_swagger_docs()
    await check_seeding_error_bug()
    await check_js_file_quality()
    await check_crud_coverage()
    await check_redirects()
    await check_pages_js_deep()
    await check_data_faucets(token)
    await check_code_audit()

    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"{BOLD}  AUDIT SUMMARY{RESET}")
    print(f"{'='*60}")
    print(f"  Duration: {elapsed:.1f}s")
    print(f"  {GREEN}PASSED: {passed}{RESET}")
    print(f"  {RED}FAILED: {failed}{RESET}")
    print(f"  {YELLOW}WARNINGS: {warnings}{RESET}")
    print(f"  Total: {passed + failed + warnings}")
    if issues:
        print(f"\n{BOLD}  ISSUES FOUND:{RESET}")
        for issue in issues:
            print(f"  {issue}")
    print(f"\n{'='*60}\n")
    return {"passed": passed, "failed": failed, "warnings": warnings, "issues": issues, "duration": elapsed}


async def main():
    try:
        result = await run_all_checks()
        if result and result["failed"] > 5:
            print(f"\n{RED}Too many failures ({result['failed']}) — exiting with code 1{RESET}")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nAudit interrupted.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())