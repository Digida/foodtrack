"""Full platform integration test with retry logic."""
import httpx, sys, time

BASE = "http://localhost:8000"
API = f"{BASE}/api/v1"

def wait_for_server(max_retries=8):
    for i in range(max_retries):
        try:
            r = httpx.get(f"{API}/auth/me", timeout=5)
            return True
        except:
            print(f"  Waiting for server... ({i+1}/{max_retries})")
            time.sleep(2)
    return False

print("=== FoodTrack Platform Integration Test ===\n")

if not wait_for_server():
    print("Server unreachable")
    sys.exit(1)

with httpx.Client(base_url=API, timeout=15) as c:
    # 1. Register
    print("1. Register")
    r = c.post("/auth/register", json={"email":"a@b.com","password":"Demo@1234","full_name":"Test User","company":"TestCo"})
    assert r.status_code == 200, f"Register failed: {r.text}"
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    print(f"   PASS (token: {token[:20]}...)")

    # 2. Create Product
    print("2. Create Product")
    r = c.post("/products", json={
        "sku":"FT-001","name":"Premium Organic Dates","category":"fresh_produce",
        "origin_country":"UAE","origin_region":"Al Ain","producer_name":"Al Foah Farms",
        "weight_kg":5.0,"storage_requirements":"Cool dry place"
    }, headers=h)
    assert r.status_code == 200, f"Product create failed: {r.text}"
    pid = r.json()["product"]["id"]
    print(f"   PASS (id={pid}, sku={r.json()['product']['sku']})")

    # 3. Add 4 trace events forming a supply chain
    print("3. Supply Chain Events")
    events = [
        ("harvest", "Al Ain Farm", "UAE", "Ali Hassan", "Al Foah Farms", "2026-07-15T06:00:00Z"),
        ("packaging", "Al Ain Packing", "UAE", "Mohammed Rashid", "Al Foah Packing", "2026-07-16T10:00:00Z"),
        ("shipping", "Jebel Ali Port", "UAE", "Omar Yusuf", "DP World Logistics", "2026-07-18T14:00:00Z"),
        ("delivery", "Dubai Marina", "UAE", "Khalid Ibrahim", "Dubai Hospitality", "2026-07-20T09:00:00Z"),
    ]
    for ev_type, loc, country, handler, org, ts in events:
        r = c.post("/traceability", json={
            "product_id":pid,"event_type":ev_type,"location_name":loc,
            "country":country,"handler_name":handler,"handler_organization":org,
            "event_timestamp":ts
        }, headers=h)
        assert r.status_code == 200, f"Event {ev_type} failed: {r.text}"
    print(f"   PASS (4 events created)")

    # 4. Get trace timeline
    print("4. Trace Timeline")
    r = c.get(f"/traceability/product/{pid}", headers=h)
    assert r.status_code == 200 and len(r.json()["events"]) == 4
    print(f"   PASS ({len(r.json()['events'])} events in timeline)")

    # 5. Issue Certificate
    print("5. Issue Certificate")
    r = c.post("/certificates", json={
        "product_id":pid,"type":"halal","issuing_body":"UAE Standards Authority",
        "recipient_entity":"Dubai Food Group","description":"Halal certification"
    }, headers=h)
    assert r.status_code == 200, f"Cert issue failed: {r.text}"
    cid = r.json()["certificate"]["certificate_id"]
    print(f"   PASS (id={cid})")

    # 6. Verify Certificate
    print("6. Verify Certificate")
    r = c.post(f"/certificates/{cid}/verify-auth", headers=h)
    assert r.status_code == 200
    print(f"   PASS ({r.json()['status']})")

    # 7. Analytics
    print("7. Analytics Dashboard")
    r = c.get("/analytics/dashboard", headers=h)
    assert r.status_code == 200
    d = r.json()
    print(f"   PASS (products={d['total_products']}, events={d['total_traceability_events']}, certs={d['total_certificates']}, verified={d['verified_certificates']})")

    # 8. QR Scan
    print("8. QR Scan Trace")
    r = c.get("/traceability/scan/FT-001", headers=h)
    assert r.status_code == 200
    print(f"   PASS (product={r.json()['product']['name']}, events={len(r.json()['events'])})")

    # 9. Share Links
    print("9. Share Links")
    r = c.post("/share/generate-link", json={"product_id":pid}, headers=h)
    assert r.status_code == 200
    links = r.json()["social_links"]
    print(f"   PASS (platforms: {', '.join(links.keys())})")

    # 10. Peer Comparison
    print("10. Peer Comparison")
    r = c.get(f"/share/peer-compare/{pid}", headers=h)
    assert r.status_code == 200
    print(f"   PASS (peers: {len(r.json()['peers'])})")

    # 11. Frontend
    print("11. Frontend")
    r = httpx.get(f"{BASE}/", timeout=5)
    assert r.status_code == 200 and "FoodTrack" in r.text
    print(f"   PASS (HTML served)")

    # 12. Product Detail with QR
    print("12. Product Detail with QR")
    r = c.get(f"/products/{pid}", headers=h)
    assert r.status_code == 200 and r.json()["product"]["qr_code"]
    print(f"   PASS (QR code: {len(r.json()['product']['qr_code'])} chars, barcode: {len(r.json()['product']['barcode'])} chars)")

print(f"\n{'='*40}")
print("ALL 12 TESTS PASSED OK")
print(f"{'='*40}")
