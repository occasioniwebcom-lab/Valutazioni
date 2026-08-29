"""Backend tests for GameLife Valutazioni API.

Covers:
- /api/search (records history)
- /api/product live fetch + cache
- Known Zelda URL sanity
- /api/history GET + DELETE (soft clear + re-view restores)
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "http://localhost:8001").rstrip("/")
API = f"{BASE_URL}/api"

ZELDA_URL = "https://www.gamelife.it/sws20003-the-legend-of-zelda-tears-of-the-kingdom"


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


# ---------- root ----------
def test_root(s):
    r = s.get(f"{API}/", timeout=30)
    assert r.status_code == 200
    assert "message" in r.json()


# ---------- search ----------
def test_search_zelda_shape(s):
    r = s.get(f"{API}/search", params={"q": "zelda"}, timeout=60)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["query"] == "zelda"
    assert isinstance(data["results"], list)
    assert data["count"] == len(data["results"])
    assert len(data["results"]) > 0
    first = data["results"][0]
    for k in ("url", "title", "image", "priced"):
        assert k in first
    assert first["url"].startswith("https://www.gamelife.it")


def test_search_empty_query_rejected(s):
    r = s.get(f"{API}/search", params={"q": ""}, timeout=10)
    assert r.status_code == 422


# ---------- product live + cache ----------
def test_product_zelda_live_then_cache(s):
    # cold call
    t0 = time.time()
    r1 = s.get(f"{API}/product", params={"url": ZELDA_URL}, timeout=120)
    cold_t = time.time() - t0
    assert r1.status_code == 200, r1.text
    d1 = r1.json()
    assert d1["url"] == ZELDA_URL
    # nuovo & buyback should be non-null per spec
    assert d1["nuovo"] is not None, f"nuovo missing: {d1}"
    assert d1["buyback"] is not None, f"buyback missing: {d1}"
    # Expected values (may differ if site changes)
    if d1["nuovo"] is not None:
        assert 20 <= d1["nuovo"] <= 200
    if d1["buyback"] is not None:
        assert 0 < d1["buyback"] <= 100

    # warm call - should be fast (cache)
    t0 = time.time()
    r2 = s.get(f"{API}/product", params={"url": ZELDA_URL}, timeout=30)
    warm_t = time.time() - t0
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["nuovo"] == d1["nuovo"]
    assert d2["usato"] == d1["usato"]
    assert d2["buyback"] == d1["buyback"]
    # cache should be materially faster
    print(f"cold={cold_t:.2f}s warm={warm_t:.2f}s")
    assert warm_t < 3.0, f"cached call too slow: {warm_t:.2f}s"


def test_product_invalid_url_rejected(s):
    r = s.get(f"{API}/product", params={"url": "https://evil.example.com/x"}, timeout=10)
    assert r.status_code == 400


# ---------- history + clear ----------
def test_history_contains_zelda_then_clear_then_restore(s):
    # Ensure zelda was fetched (dependency on previous test)
    s.get(f"{API}/product", params={"url": ZELDA_URL}, timeout=120)

    r = s.get(f"{API}/history", timeout=30)
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    urls = [i["url"] for i in items]
    assert ZELDA_URL in urls, f"zelda not in history: {urls[:5]}"
    entry = next(i for i in items if i["url"] == ZELDA_URL)
    assert entry["buyback"] is not None
    assert "viewed_at" in entry

    # DELETE clears (soft)
    r = s.delete(f"{API}/history", timeout=30)
    assert r.status_code == 200
    body = r.json()
    assert "cleared" in body

    r = s.get(f"{API}/history", timeout=30)
    assert r.status_code == 200
    assert r.json() == []

    # Re-view restores
    r = s.get(f"{API}/product", params={"url": ZELDA_URL}, timeout=30)
    assert r.status_code == 200

    r = s.get(f"{API}/history", timeout=30)
    assert r.status_code == 200
    items2 = r.json()
    urls2 = [i["url"] for i in items2]
    assert ZELDA_URL in urls2, "zelda not restored to history after re-view"
