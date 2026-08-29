"""Regression: password change flow for shared-password auth.

Contract:
  - Current live password is '1234' (per test_credentials.md)
  - POST /api/login {password:'1234'} -> 200 with access_token
  - Wrong password -> 401
  - GET /api/search without Bearer -> 401
  - GET /api/search with Bearer -> 200
  - POST /api/change-password revokes the current token via password_version
  - After change, login with new password -> 200; login with old -> 401
  - Restore password back to '1234' at the end (idempotent guard).
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL") or os.environ.get("EXPO_BACKEND_URL")
if not BASE_URL:
    # Fallback: read frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("EXPO_PUBLIC_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().strip('"')
                break
BASE_URL = BASE_URL.rstrip("/")
LIVE_PW = "1234"
TEMP_PW = "temp9876"


@pytest.fixture(scope="session")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


def _login(s, pw):
    return s.post(f"{BASE_URL}/api/login", json={"password": pw}, timeout=20)


# ---- login ----
def test_login_current_password_ok(s):
    r = _login(s, LIVE_PW)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("token_type") == "bearer"
    assert isinstance(body.get("access_token"), str) and len(body["access_token"]) > 20


def test_login_wrong_password_401(s):
    r = _login(s, "not-the-password")
    assert r.status_code == 401


# ---- protected endpoint gating ----
def test_search_requires_bearer(s):
    r = s.get(f"{BASE_URL}/api/search", params={"q": "zelda"}, timeout=20)
    assert r.status_code == 401


def test_search_with_bearer_ok(s):
    token = _login(s, LIVE_PW).json()["access_token"]
    r = s.get(f"{BASE_URL}/api/search", params={"q": "zelda"},
              headers={"Authorization": f"Bearer {token}"}, timeout=60)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("query") == "zelda"
    assert isinstance(data.get("results"), list)


# ---- change-password full cycle: 1234 -> TEMP -> 1234 ----
def test_full_change_password_cycle(s):
    # Login with current
    r = _login(s, LIVE_PW)
    assert r.status_code == 200, r.text
    tok_old = r.json()["access_token"]

    # Change 1234 -> TEMP
    r = s.post(f"{BASE_URL}/api/change-password",
               json={"current_password": LIVE_PW, "new_password": TEMP_PW},
               headers={"Authorization": f"Bearer {tok_old}"}, timeout=30)
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True}

    # Old token should be revoked (pv bump)
    r = s.get(f"{BASE_URL}/api/search", params={"q": "zelda"},
              headers={"Authorization": f"Bearer {tok_old}"}, timeout=20)
    assert r.status_code == 401, f"Expected old token revoked, got {r.status_code}"

    # Old password no longer works
    assert _login(s, LIVE_PW).status_code == 401

    # New password works, and its token can call protected endpoints (mirrors what
    # the frontend does: signIn(newPassword) right after change)
    r = _login(s, TEMP_PW)
    assert r.status_code == 200, r.text
    tok_new = r.json()["access_token"]
    r = s.get(f"{BASE_URL}/api/search", params={"q": "zelda"},
              headers={"Authorization": f"Bearer {tok_new}"}, timeout=60)
    assert r.status_code == 200

    # Restore TEMP -> 1234
    r = s.post(f"{BASE_URL}/api/change-password",
               json={"current_password": TEMP_PW, "new_password": LIVE_PW},
               headers={"Authorization": f"Bearer {tok_new}"}, timeout=30)
    assert r.status_code == 200, r.text

    # Final: login with 1234 works again
    assert _login(s, LIVE_PW).status_code == 200
