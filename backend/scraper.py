"""GameLife.it scraper using Playwright (bypasses Cloudflare from this environment).

The site (Odoo) rate-limits bursts and intermittently serves product pages without
the server-rendered price cards, so product fetches use a small retry loop with a
fresh browser context per attempt. Results are cached in MongoDB (see server.py).
"""
import asyncio
import re
import os
import logging
from typing import Optional

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# Playwright browsers are pre-installed here in this environment; the supervisor
# process env does not inherit PLAYWRIGHT_BROWSERS_PATH, so set a sane default.
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/pw-browsers")

logger = logging.getLogger("scraper")

BASE = "https://www.gamelife.it"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

_pw = None
_browser = None
_launch_lock = asyncio.Lock()


async def start_browser():
    global _pw, _browser
    async with _launch_lock:
        if _browser is not None and _browser.is_connected():
            return _browser
        _pw = await async_playwright().start()
        _browser = await _pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        )
        logger.info("Playwright chromium launched")
        return _browser


async def stop_browser():
    global _pw, _browser
    try:
        if _browser is not None:
            await _browser.close()
        if _pw is not None:
            await _pw.stop()
    except Exception as e:  # noqa: BLE001
        logger.warning("Error stopping browser: %s", e)
    finally:
        _browser = None
        _pw = None


async def _get_browser():
    if _browser is None or not _browser.is_connected():
        return await start_browser()
    return _browser


def parse_price(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    s = text.replace("\xa0", " ").strip()
    m = re.search(r"\d[\d.,]*", s)
    if not m:
        return None
    num = m.group(0)
    if "." in num and "," in num:
        num = num.replace(".", "").replace(",", ".")
    elif "," in num:
        num = num.replace(",", ".")
    try:
        return float(num)
    except ValueError:
        return None


def _thumb(url: Optional[str]) -> Optional[str]:
    """Downsize Odoo image URLs to a lighter thumbnail."""
    if not url:
        return None
    if url.startswith("/"):
        url = BASE + url
    return re.sub(r"image_\d+", "image_256", url)


ACCESSORY_RE = re.compile(
    r"\b(amiibo|funko|pop!?|peluche|plush|custodia|cover|cavo|caricabatteri\w*|adattatore|"
    r"controller|joy-?con|volante|borsa|zaino\w*|cuffi\w*|headset|auricolari|steelbook|"
    r"gadget|magliet\w*|t-shirt|tazza|mug|poster|statuin\w*|statua|figure|figures|spill\w*|"
    r"felpa|cappell\w*|tappetino|mousepad|dock|supporto|stand|batteria|memory card|"
    r"protezione|pellicola|grip|skin|lampada|lamp|portafogli\w*|wallet|sciarpa|calzini|"
    r"carte da gioco|playing cards|sticker|adesiv\w*|termos|borraccia|orologio|sveglia|"
    r"puzzle|lego|portachiav\w*|bundle accessori|playset|interattiv\w*|il film|blu-?ray|"
    r"dvd|4k ultra|steelbook)\b",
    re.I,
)


def _is_game(title: str) -> bool:
    """Heuristic: a result is a video game unless the title looks like an accessory/gadget."""
    if not title:
        return True
    return ACCESSORY_RE.search(title) is None


def _parse_grid(html: str):
    soup = BeautifulSoup(html, "lxml")
    items = []
    seen = set()
    for card in soup.select(".oe_product"):
        a = card.select_one("a[href]")
        if not a:
            continue
        href = a.get("href") or ""
        if not href or href.startswith("#"):
            continue
        url = BASE + href if href.startswith("/") else href
        if url in seen:
            continue
        seen.add(url)
        h = card.select_one("h2")
        title = (h.get_text(" ", strip=True) if h else a.get("title") or "").strip()
        img = card.select_one("img.oe_product_image_img") or card.select_one("img")
        image = _thumb(img.get("src") if img else None)
        pid_input = card.select_one("input[name='product_id']")
        pid = pid_input.get("value") if pid_input else None
        items.append({"title": title, "url": url, "image": image, "product_id": pid, "is_game": _is_game(title)})
    return items


def _parse_product(html: str):
    soup = BeautifulSoup(html, "lxml")
    prices = {"nuovo": None, "usato": None, "buyback": None}
    found_card = False
    for wrap in soup.select(".gamelife-price-card"):
        head = wrap.select_one(".gamelife-price-card__header")
        body = wrap.select_one(".gamelife-price-card__body")
        if not head or not body:
            continue
        label = head.get_text(" ", strip=True).lower()
        cur = body.select_one(".oe_currency_value")
        val = parse_price(cur.get_text() if cur else body.get_text(" ", strip=True))
        if val is None:
            continue
        found_card = True
        if "buyback" in label:
            prices["buyback"] = val
        elif "usato" in label:
            prices["usato"] = val
        elif "nuovo" in label:
            prices["nuovo"] = val
    # Fallback new price from the standard Odoo price element
    if prices["nuovo"] is None:
        el = soup.select_one(".product_price .oe_price .oe_currency_value")
        if el:
            prices["nuovo"] = parse_price(el.get_text())

    title = None
    h1 = soup.select_one("#product_detail h1, h1")
    if h1:
        title = h1.get_text(" ", strip=True)
    image = None
    og = soup.select_one("meta[property='og:image']")
    if og:
        image = _thumb(og.get("content"))
    return {**prices, "title": title, "image": image, "_found_card": found_card}


async def search_games(query: str, limit: int = 20):
    browser = await _get_browser()
    q = re.sub(r"\s+", "+", query.strip())
    url = f"{BASE}/shop?search={q}"
    items = []
    for attempt in range(2):
        ctx = await browser.new_context(locale="it-IT", timezone_id="Europe/Rome", user_agent=UA)
        try:
            page = await ctx.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            try:
                await page.wait_for_selector(".oe_product", timeout=12000)
            except Exception:  # noqa: BLE001
                pass
            html = await page.content()
        finally:
            await ctx.close()
        items = _parse_grid(html)[:limit]
        if items:
            return items
        await asyncio.sleep(0.5)
    return items


async def fetch_product(url: str, attempts: int = 3):
    """Fetch a single product page with retry. Returns dict with prices/title/image.

    `ok` is True when the price cards were server-rendered on this attempt.
    """
    if not url.startswith(BASE):
        return None
    browser = await _get_browser()
    last = {"nuovo": None, "usato": None, "buyback": None, "title": None, "image": None}
    for attempt in range(attempts):
        ctx = await browser.new_context(locale="it-IT", timezone_id="Europe/Rome", user_agent=UA)
        try:
            page = await ctx.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            try:
                await page.wait_for_selector(".gamelife-price-card__body .oe_currency_value", timeout=9000)
            except Exception:  # noqa: BLE001
                pass
            data = _parse_product(await page.content())
        except Exception as e:  # noqa: BLE001
            logger.warning("fetch_product error (%s) attempt %s: %s", url, attempt, e)
            data = None
        finally:
            await ctx.close()

        if data:
            last = {k: data.get(k) for k in ("nuovo", "usato", "buyback", "title", "image")}
            if data.get("_found_card"):
                return {**last, "ok": True}
        await asyncio.sleep(0.6)
    return {**last, "ok": last.get("nuovo") is not None}
