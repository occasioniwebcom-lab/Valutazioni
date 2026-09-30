"""eBay.it search using the official Browse API when credentials are configured."""
import asyncio
import base64
import logging
import os
import re
import time
from pathlib import Path
from urllib.parse import urlencode

from bs4 import BeautifulSoup
import httpx
from dotenv import load_dotenv

from . import browser as browser_mod
from .utils import parse_price

logger = logging.getLogger("scrapers.ebay")

BASE = "https://www.ebay.it"
API_BASE = os.environ.get("EBAY_API_BASE", "https://api.ebay.com").rstrip("/")
MARKETPLACE_ID = os.environ.get("EBAY_MARKETPLACE_ID", "EBAY_IT")
_NON_GAME_TITLE = re.compile(
    r"\b(empty box|box only|no game|no\s+gioco|senza gioco|senza disco|solo scatola|"
    r"solo custodia|solo manuale|scatola vuota|"
    r"advertisement|annuncio pubblicitario|poster|banner|action figure|figurine?|"
    r"statuette?|modellino|trading cards?|carte collezionabili|memory card|"
    r"controller|arcade stick|adesivi?|sticker|peluche|plush|portachiavi|"
    r"artbook|soundtrack|guida strategica|calendario|calendar|inserto|insert|"
    r"promo|gift|lotto|bundle|multi.?pack)\b|\bgiochi\s+x\s+\d+\b|"
    r"\bgiochi\s+(xbox|playstation|ps[2345])\b",
    re.I,
)
_token = None
_token_expires_at = 0
_token_lock = asyncio.Lock()


def _credentials():
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    return os.environ.get("EBAY_CLIENT_ID"), os.environ.get("EBAY_CLIENT_SECRET")


async def _fetch_access_token(client_id: str, client_secret: str):
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"{API_BASE}/identity/v1/oauth2/token",
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "client_credentials",
                "scope": "https://api.ebay.com/oauth/api_scope",
            },
        )
    response.raise_for_status()
    body = response.json()
    return body["access_token"], int(body.get("expires_in", 7200))


async def _get_access_token():
    global _token, _token_expires_at
    if _token and time.monotonic() < _token_expires_at:
        return _token
    client_id, client_secret = _credentials()
    if not client_id or not client_secret:
        return None
    async with _token_lock:
        if _token and time.monotonic() < _token_expires_at:
            return _token
        _token, expires_in = await _fetch_access_token(client_id, client_secret)
        _token_expires_at = time.monotonic() + max(0, expires_in - 60)
        return _token


_USED_GAME_CONDITION_IDS = frozenset({"2750", "4000", "5000", "6000"})
_ITALIAN_LOCATION = re.compile(r"\b(?:italia|italy)\b", re.I)


def _parse_api_results(body: dict, limit: int):
    items = []
    for entry in body.get("itemSummaries", []):
        location = entry.get("itemLocation") or {}
        if str(location.get("country", "")).upper() != "IT":
            continue
        price = entry.get("price") or {}
        if price.get("currency") != "EUR":
            continue
        if "FIXED_PRICE" not in entry.get("buyingOptions", []):
            continue
        # The "Giochi" leaf category grades condition as come nuovo/ottime/buone/
        # accettabili (2750/4000/5000/6000), not the generic "usato" id 3000.
        if entry.get("conditionId") not in _USED_GAME_CONDITION_IDS:
            continue
        try:
            amount = float(price["value"])
        except (KeyError, TypeError, ValueError):
            continue
        item_url = entry.get("itemWebUrl")
        title = entry.get("title")
        if not item_url or not title:
            continue
        categories = entry.get("categories") or []
        category_names = " ".join(str(category.get("categoryName", "")) for category in categories)
        if categories and re.search(
            r"merchandise|merchandising|controller|accessor|collectible|figure|poster|"
            r"manual|box art|card|sticker|music|soundtrack|toys",
            category_names,
            re.I,
        ):
            continue
        if _NON_GAME_TITLE.search(title) or re.search(r"art\s?book|display\s+card|promo\s+display", title, re.I):
            continue
        image = (entry.get("image") or {}).get("imageUrl")
        items.append({"title": title, "url": item_url, "image": image, "price": amount})
    return sorted(items, key=lambda item: item["price"])[:limit]


async def _search_api(query: str, token: str, limit: int):
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            f"{API_BASE}/buy/browse/v1/item_summary/search",
            params={
                "q": query,
                # 139973 = "Giochi" (leaf category), not the broad 1249 parent which
                # is dominated by merchandise/accessories and starves real matches.
                "category_ids": "139973",
                # This category grades used items (2750/4000/5000/6000 = come nuovo/
                # ottime/buone/accettabili) instead of the generic conditionId 3000,
                # which barely exists here and was silently filtering out almost
                # every real used listing.
                "filter": "conditionIds:{2750|4000|5000|6000},buyingOptions:{FIXED_PRICE},itemLocationCountry:IT",
                "limit": min(max(limit * 3, 50), 100),
                "sort": "price",
            },
            headers={
                "Authorization": f"Bearer {token}",
                "X-EBAY-C-MARKETPLACE-ID": MARKETPLACE_ID,
                "Accept": "application/json",
            },
        )
    response.raise_for_status()
    return response.json()


def _parse_results(html: str):
    soup = BeautifulSoup(html, "lxml")
    items = []
    for card in soup.select("li.s-item"):
        title_el = card.select_one(".s-item__title")
        price_el = card.select_one(".s-item__price")
        link_el = card.select_one("a.s-item__link")
        if not title_el or not price_el or not link_el:
            continue
        title = title_el.get_text(" ", strip=True)
        if not title or title.lower().startswith("nuova inserzione") or title.lower() == "annuncio":
            continue
        location_el = card.select_one(".s-item__location")
        location = location_el.get_text(" ", strip=True) if location_el else ""
        if not _ITALIAN_LOCATION.search(location):
            continue
        price_text = price_el.get_text(" ", strip=True)
        # Price ranges ("EUR 10,00 a EUR 20,00") -> take the lower bound.
        price_text = re.split(r"\s+a\s+", price_text, maxsplit=1)[0]
        price = parse_price(price_text)
        if price is None:
            continue
        url = link_el.get("href")
        if not url:
            continue
        img_el = card.select_one(".s-item__image img, img")
        image = img_el.get("src") if img_el else None
        items.append({"title": title, "url": url.split("?")[0], "image": image, "price": price})
    return sorted(items, key=lambda item: item["price"])


async def search_used_bin(query: str, limit: int = 40):
    """Search eBay.it for used items sold as Buy It Now, returning listing prices."""
    client_id, client_secret = _credentials()
    if client_id and client_secret:
        try:
            token = await _get_access_token()
            body = await _search_api(query, token, limit)
            return _parse_api_results(body, limit)
        except Exception as e:  # noqa: BLE001
            logger.warning("eBay Browse API search failed (%s): %s", query, e)
            return []

    params = {
        "_nkw": query.strip(),
        "_sacat": "0",
        "LH_ItemCondition": "3000",
        "LH_BIN": "1",
        "_sop": "15",
        "_ipg": "60",
    }
    url = f"{BASE}/sch/i.html?{urlencode(params)}"
    ctx = await browser_mod.new_context()
    try:
        page = await ctx.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        try:
            await page.wait_for_selector("li.s-item", timeout=12000)
        except Exception:  # noqa: BLE001
            pass
        html = await page.content()
    except Exception as e:  # noqa: BLE001
        logger.warning("ebay search failed (%s): %s", query, e)
        return []
    finally:
        await ctx.close()
    try:
        return _parse_results(html)[:limit]
    except Exception as e:  # noqa: BLE001
        logger.warning("ebay parse failed (%s): %s", query, e)
        return []
