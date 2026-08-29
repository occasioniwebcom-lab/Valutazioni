"""Tests for the 502 bug fix and the new is_game filter on /api/search.

The 502 was transient (backend --reload during file edits). This suite confirms
several consecutive real queries return HTTP 200 with a JSON body containing a
`results` list of up to 20 items, each carrying an `is_game` boolean.
"""
import os
import re
import time
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "http://localhost:8001").rstrip("/")
API = f"{BASE_URL}/api"

QUERIES = ["zelda", "mario", "assassin's creed", "spiderman"]

ACCESSORY_KEYWORDS = re.compile(
    r"\b(amiibo|funko|custodia|volante|portachiav\w*|peluche|playset|il film|"
    r"tazza|steelbook|lego|figurines|figure|figures|cosbi|blu-?ray|4k ultra)\b",
    re.I,
)


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


# 502 bug regression -- each query MUST return 200 across two consecutive calls.
@pytest.mark.parametrize("q", QUERIES)
def test_search_status_200_repeated(s, q):
    for i in range(2):
        r = s.get(f"{API}/search", params={"q": q}, timeout=90)
        assert r.status_code == 200, f"[{q} pass {i}] status={r.status_code} body={r.text[:300]}"
        data = r.json()
        assert data["query"] == q
        assert isinstance(data["results"], list)
        assert data["count"] == len(data["results"])
        assert len(data["results"]) <= 20
        for row in data["results"]:
            for k in ("url", "title", "priced", "is_game"):
                assert k in row, f"missing {k} in {row}"
            assert isinstance(row["is_game"], bool)
        # small delay so the site doesn't rate-limit the second try
        time.sleep(1.0)


# Non-empty results check with retry (site occasionally returns 0 items)
@pytest.mark.parametrize("q", QUERIES)
def test_search_returns_results(s, q):
    got = 0
    for _ in range(3):
        r = s.get(f"{API}/search", params={"q": q}, timeout=90)
        assert r.status_code == 200
        got = len(r.json()["results"])
        if got > 0:
            break
        time.sleep(2)
    assert got > 0, f"[{q}] still 0 results after 3 tries"


def _search_with_retry(s, q, tries=4):
    for _ in range(tries):
        r = s.get(f"{API}/search", params={"q": q}, timeout=90)
        assert r.status_code == 200
        results = r.json()["results"]
        if results:
            return results
        time.sleep(2)
    return results


def test_is_game_accessories_flagged_false_zelda(s):
    results = _search_with_retry(s, "zelda")
    assert results, "no zelda results after retries"
    # Any title clearly matching accessory keywords must be is_game=False
    for row in results:
        if ACCESSORY_KEYWORDS.search(row["title"]):
            assert row["is_game"] is False, f"accessory not flagged: {row['title']}"


def test_is_game_real_game_flagged_true_zelda(s):
    results = _search_with_retry(s, "zelda")
    assert results, "no zelda results after retries"
    # A pure "The Legend of Zelda Tears of the Kingdom" entry (no accessory word) must be is_game=True
    hit = next(
        (row for row in results
         if "tears of the kingdom" in row["title"].lower()
         and not ACCESSORY_KEYWORDS.search(row["title"])),
        None,
    )
    assert hit is not None, "no clean Zelda ToTK entry found"
    assert hit["is_game"] is True, f"ToTK misflagged: {hit['title']}"


def test_is_game_real_game_flagged_true_ac(s):
    results = _search_with_retry(s, "assassin's creed")
    if not results:
        pytest.skip("empty results this run (site transient)")
    # Any Valhalla / Odyssey / Origins / Mirage / Shadows without an accessory word must be a game
    for row in results:
        if re.search(r"valhalla|odyssey|origins|mirage|shadows", row["title"], re.I):
            if not ACCESSORY_KEYWORDS.search(row["title"]):
                assert row["is_game"] is True, f"AC game misflagged: {row['title']}"
                return
    # If no such row, at least assert at least one row is a game
    assert any(r_["is_game"] for r_ in results), "no AC row flagged as game"
