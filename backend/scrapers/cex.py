"""CeX/WeBuy Italy scraper — 'cash' buy-back price for used games.

CeX rebranded to "WeBuy" in Italy; the search results grid shows both a cash and a
voucher price per item, we keep the cash one since it best matches "quanto paga il
negozio per l'usato". NOTE: selectors below are a best-effort based on the public
CeX/WeBuy site layout — verify against the live DOM (page.content()) and adjust the
CSS selectors in `_CARD_SEL` / `_PRICE_SEL` if the site markup has changed since.
"""
import asyncio
import logging
import os
import re
from pathlib import Path
from urllib.parse import quote

from bs4 import BeautifulSoup
import httpx
from dotenv import load_dotenv

from .gamelife import ACCESSORY_RE
from . import browser as browser_mod
from .utils import parse_price

logger = logging.getLogger("scrapers.cex")

BASE = os.environ.get("CEX_BASE_URL", "https://it.webuy.com").rstrip("/")
APIFY_ACTOR = "sync-network/cex-product-scraper-uk-webuy-com"
APIFY_BASE = "https://api.apify.com/v2"
_ACTOR_ACCESSORY_RE = re.compile(r"\b(fighting stick|arcade stick|steering wheel)\b", re.I)
_ACTOR_NON_GAME_RE = re.compile(
    r"\b(controller|fighting stick|arcade stick|figure|figurine|statua|statuetta|"
    r"custodia|cover|case|manuale|manual|artbook|soundtrack|poster|maglietta|"
    r"t-shirt|peluche|plush|adesivo|sticker|memory card|scheda memoria|"
    r"scatola|box|solo gioco|senza gioco|no game|film|blu-ray|dvd|cuffie|headset|"
    r"volante|console|accessori|merchandising)\b",
    re.I,
)

_CARD_SEL = (
    "article.search-product-card, li.search-product-card, div.product-card, "
    "div.search-result-item, .search-product, .product-result, [data-testid*='product']"
)
_TITLE_SEL = ".product-main-title, .product-title, .search-product-name, .search-product, h2, h3, a[title]"
_LINK_SEL = "a[href*='/product'], a[href*='/box'], a[href]"
_PRICE_CASH_RE = re.compile(r"(?:cash|contanti)\D{0,20}?(\d[\d.,]*)\s*€?", re.I)
_PRICE_ANY_RE = re.compile(r"€\s*(\d[\d.,]*)|(\d[\d.,]*)\s*€")


def _extract_price(card_text: str):
    m = _PRICE_CASH_RE.search(card_text)
    if m:
        return parse_price(m.group(1))
    m = _PRICE_ANY_RE.search(card_text)
    if m:
        return parse_price(m.group(1) or m.group(2))
    return None


def _parse_results(html: str):
    soup = BeautifulSoup(html, "lxml")
    items = []
    seen = set()
    cards = soup.select(_CARD_SEL)
    if not cards:
        cards = soup.select("a[href*='/product'], a[href*='/box']")
    for card in cards:
        link = card.select_one(_LINK_SEL)
        if not link:
            continue
        href = link.get("href") or ""
        if not href:
            continue
        url = href if href.startswith("http") else BASE + href
        if url in seen:
            continue
        title_el = card.select_one(_TITLE_SEL) if hasattr(card, "select_one") else None
        title = (title_el.get_text(" ", strip=True) if title_el else link.get("title") or "").strip()
        if not title:
            continue
        card_text = card.get_text(" ", strip=True)
        price = _extract_price(card_text)
        if price is None:
            continue
        seen.add(url)
        img = card.select_one("img")
        image = img.get("src") if img else None
        items.append({"title": title, "url": url, "image": image, "price": price})
    return items


def _parse_actor_items(data, limit: int):
    items = []
    for row in data if isinstance(data, list) else []:
        raw_price = row.get("trade_in_cash")
        currency = row.get("currency")
        if isinstance(raw_price, dict):
            currency = raw_price.get("currency", currency)
            raw_price = raw_price.get("amount", raw_price.get("value"))
        if currency and currency not in ("EUR", "€"):
            continue
        price = raw_price if isinstance(raw_price, (int, float)) else parse_price(str(raw_price or ""))
        title = row.get("title") or row.get("productName") or row.get("name")
        url = row.get("productUrl") or row.get("url")
        category = row.get("category") or row.get("categoryName") or ""
        category_text = " ".join(category) if isinstance(category, list) else str(category)
        non_game_category = re.search(
            r"controller|accessor|merch|figure|film|music|manual|console",
            category_text,
            re.I,
        )
        if (price is None or not title or not url
            or ACCESSORY_RE.search(title)
            or _ACTOR_ACCESSORY_RE.search(title)
            or _ACTOR_NON_GAME_RE.search(title)
            or non_game_category):
            continue
        image = row.get("image") or row.get("imageUrl")
        if isinstance(image, dict):
            image = image.get("url") or image.get("src")
        items.append({"title": title, "url": url, "image": image, "price": float(price)})
    return items[:limit]


async def _run_apify_actor(query: str, limit: int, token: str):
    actor_path = quote(APIFY_ACTOR.replace("/", "~"), safe="~")
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            f"{APIFY_BASE}/acts/{actor_path}/runs",
            params={"waitForFinish": 15},
            headers=headers,
            json={
                "country_code": "it",
                "search_input": query,
                "max_items": min(limit, 5),
                "throttle": 1,
            },
        )
        response.raise_for_status()
        run = response.json().get("data", response.json())
        run_id = run.get("id")
        deadline = asyncio.get_event_loop().time() + 15
        while run.get("status") not in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            if not run_id or asyncio.get_event_loop().time() >= deadline:
                logger.warning("Apify CeX run did not finish within the wait budget")
                return []
            await asyncio.sleep(1)
            poll = await client.get(
                f"{APIFY_BASE}/actor-runs/{quote(run_id, safe='')}",
                headers=headers,
                timeout=6,
            )
            poll.raise_for_status()
            run = poll.json().get("data", poll.json())
        if run.get("status") != "SUCCEEDED":
            logger.warning("Apify CeX run ended with status %s", run.get("status"))
            return []
        dataset_id = run.get("defaultDatasetId")
        if not dataset_id:
            return []
        dataset = await client.get(
            f"{APIFY_BASE}/datasets/{quote(dataset_id, safe='')}/items",
            params={"format": "json", "clean": "true"},
            headers=headers,
            timeout=10,
        )
    dataset.raise_for_status()
    return _parse_actor_items(dataset.json(), limit)


async def search_buyback(query: str, limit: int = 20):
    """Search WeBuy/CeX Italy for `query`, returning cash buy-back prices (used only)."""
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    apify_token = os.environ.get("APIFY_API_TOKEN")
    if apify_token:
        try:
            items = await _run_apify_actor(query, limit, apify_token)
            if items:
                return items
        except Exception as error:  # noqa: BLE001
            logger.warning("Apify CeX search failed (%s): %s", query, error)

    q = query.strip().replace(" ", "+")
    url = f"{BASE}/search/?stext={q}"
    ctx = await browser_mod.new_context()
    try:
        page = await ctx.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        try:
            await page.wait_for_selector(_CARD_SEL, timeout=12000)
        except Exception:  # noqa: BLE001
            pass
        html = await page.content()
    except Exception as e:  # noqa: BLE001
        logger.warning("cex search failed (%s): %s", query, e)
        return []
    finally:
        await ctx.close()
    try:
        return _parse_results(html)[:limit]
    except Exception as e:  # noqa: BLE001
        logger.warning("cex parse failed (%s): %s", query, e)
        return []
