"""Auth tests for GameLife Valutazioni: login, guards, change-password, token revocation.

IMPORTANT: This test suite restores the password back to the preview default at the end
so subsequent runs / the preview UI keep working.
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback to local backend for pytest runs where the frontend env isn't loaded.
    BASE_URL = "http://localhost:8001"

DEFAULT_PW = "valutazioni2026"
NEW_PW = "nuova1234"


def _login(pw: str):
    return requests.post(f"{BASE_URL}/api/login", json={"password": pw}, timeout=15)


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


# -------- Login --------
class TestLogin:
    def test_login_ok(self):
        r = _login(DEFAULT_PW)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("token_type") == "bearer"
        assert isinstance(body.get("access_token"), str) and len(body["access_token"]) > 20

    def test_login_wrong_pw(self):
        r = _login("obviously-wrong")
        assert r.status_code == 401


# -------- Auth guard on data endpoints --------
class TestAuthGuard:
    @pytest.fixture(scope="class")
    def token(self):
        r = _login(DEFAULT_PW)
        assert r.status_code == 200
        return r.json()["access_token"]

    def test_search_without_auth(self):
        r = requests.get(f"{BASE_URL}/api/search", params={"q": "zelda"}, timeout=15)
        assert r.status_code == 401

    def test_search_with_auth(self, token):
        # Live scrape can be slow / transient; retry up to 3x.
        last = None
        for _ in range(3):
            r = requests.get(f"{BASE_URL}/api/search", params={"q": "zelda"},
                             headers=_auth(token), timeout=45)
            last = r
            if r.status_code == 200:
                break
            time.sleep(2)
        assert last.status_code == 200, last.text
        body = last.json()
        assert body["query"] == "zelda"
        assert isinstance(body["results"], list)

    def test_product_without_auth(self):
        r = requests.get(f"{BASE_URL}/api/product",
                         params={"url": "https://www.gamelife.it/sws20003-the-legend-of-zelda-tears-of-the-kingdom"},
                         timeout=15)
        assert r.status_code == 401

    def test_history_without_auth(self):
        r = requests.get(f"{BASE_URL}/api/history", timeout=15)
        assert r.status_code == 401

    def test_history_with_auth(self, token):
        r = requests.get(f"{BASE_URL}/api/history", headers=_auth(token), timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_delete_history_without_auth(self):
        r = requests.delete(f"{BASE_URL}/api/history", timeout=15)
        assert r.status_code == 401

    def test_bad_token(self):
        r = requests.get(f"{BASE_URL}/api/search", params={"q": "zelda"},
                         headers=_auth("not.a.valid.jwt"), timeout=15)
        assert r.status_code == 401


# -------- Change password + revocation --------
class TestChangePassword:
    """Runs sequentially: change PW -> old token revoked -> new PW works -> restore PW."""

    def test_full_cycle(self):
        # 1) get an initial token (BEFORE change)
        r = _login(DEFAULT_PW)
        assert r.status_code == 200
        old_token = r.json()["access_token"]

        # sanity: old_token works
        r = requests.get(f"{BASE_URL}/api/history", headers=_auth(old_token), timeout=15)
        assert r.status_code == 200

        # 2) change password to NEW_PW
        r = requests.post(f"{BASE_URL}/api/change-password",
                          json={"current_password": DEFAULT_PW, "new_password": NEW_PW},
                          headers=_auth(old_token), timeout=15)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

        # 3) OLD token must now be revoked (password_version bump)
        r = requests.get(f"{BASE_URL}/api/search", params={"q": "zelda"},
                         headers=_auth(old_token), timeout=15)
        assert r.status_code == 401, f"old token should be revoked, got {r.status_code}"

        # 4) login with OLD password now fails
        assert _login(DEFAULT_PW).status_code == 401

        # 5) login with NEW password works
        r = _login(NEW_PW)
        assert r.status_code == 200, r.text
        new_token = r.json()["access_token"]

        # 6) new token is accepted on a guarded endpoint
        r = requests.get(f"{BASE_URL}/api/history", headers=_auth(new_token), timeout=15)
        assert r.status_code == 200

        # 7) wrong current password on change-password → 403
        r = requests.post(f"{BASE_URL}/api/change-password",
                          json={"current_password": "wrong-current", "new_password": "whatever"},
                          headers=_auth(new_token), timeout=15)
        assert r.status_code == 403

        # 8) too-short new password → 400
        r = requests.post(f"{BASE_URL}/api/change-password",
                          json={"current_password": NEW_PW, "new_password": "abc"},
                          headers=_auth(new_token), timeout=15)
        assert r.status_code == 400

        # 9) RESTORE original password so preview credentials stay valid
        r = requests.post(f"{BASE_URL}/api/change-password",
                          json={"current_password": NEW_PW, "new_password": DEFAULT_PW},
                          headers=_auth(new_token), timeout=15)
        assert r.status_code == 200, f"failed to restore password: {r.text}"

        # 10) final sanity: default password logs in again
        r = _login(DEFAULT_PW)
        assert r.status_code == 200
