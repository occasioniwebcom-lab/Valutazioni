"""Combines GameLife/CeX/eBay searches into a single comparison list, per title.

GameLife stays the primary catalog (title/image/platform/is_game classification);
its buyback price is still fetched lazily per-product (see server.py /product,
unchanged). CeX and eBay show a price straight from search-results pages, so those
are attached eagerly here as source-tagged `offers`.
"""
import asyncio
import logging
import os

from . import cex, ebay, gamelife
from .match import best_match, matching_candidates
from .query_variants import variants

logger = logging.getLogger("scrapers.aggregator")


async def _search_variants(search_fn, queries, limit, source, timeout_seconds=18):
    items = []
    target = min(limit, 8)
    try:
        async with asyncio.timeout(timeout_seconds):
            for index, search_query in enumerate(queries):
                try:
                    batch = await search_fn(search_query, limit=limit)
                    if isinstance(batch, list):
                        items.extend(batch)
                except Exception as error:  # noqa: BLE001
                    logger.warning("%s variant search failed (%s): %s", source, search_query, error)
                items = list({
                    item.get("url"): item for item in items
                    if isinstance(item, dict) and item.get("url")
                }.values())
                if len(items) >= target or (index == 0 and items):
                    break
                if index + 1 < len(queries):
                    await asyncio.sleep(0.8)
    except TimeoutError:
        logger.warning("%s search reached %.1fs budget; returning partial results", source, timeout_seconds)
    return items[:limit * 2]


async def search_all(query: str, limit: int = 40):
    query_list = variants(query)
    gamelife_enabled = os.environ.get("GAMELIFE_ENABLED", "false").strip().lower() in {
        "1", "true", "yes", "on",
    }
    gamelife_search = (
        _search_variants(gamelife.search_games, query_list, limit, "gamelife", timeout_seconds=10)
        if gamelife_enabled else asyncio.sleep(0, result=[])
    )
    gl_items, cex_items, ebay_items = await asyncio.gather(
        gamelife_search,
        _search_variants(cex.search_buyback, query_list[:1], limit, "cex", timeout_seconds=44),
        _search_variants(ebay.search_used_bin, query_list[:4], limit, "ebay"),
        return_exceptions=True,
    )
    if isinstance(gl_items, Exception):
        logger.warning("gamelife search failed: %s", gl_items)
        gl_items = []
    if isinstance(cex_items, Exception):
        logger.warning("cex search failed: %s", cex_items)
        cex_items = []
    if isinstance(ebay_items, Exception):
        logger.warning("ebay search failed: %s", ebay_items)
        ebay_items = []

    catalog = [{**it, "offers": []} for it in gl_items]

    used_cex_urls = set()
    for row in catalog:
        for cex_hit in matching_candidates(row["title"], cex_items):
            url = cex_hit.get("url")
            if url in used_cex_urls:
                continue
            row["offers"].append({
                "source": "cex", "label": f"CeX cash · {cex_hit['title']}",
                "price": cex_hit["price"], "url": url,
            })
            used_cex_urls.add(url)

    for cex_item in cex_items:
        url = cex_item.get("url")
        if not url or url in used_cex_urls:
            continue
        used_cex_urls.add(url)
        catalog.append({
            "title": cex_item.get("title") or query.title(),
            "url": url,
            "image": cex_item.get("image"),
            "is_game": True,
            "source_only": True,
            "primary_source": "cex",
            "offers": [{
                "source": "cex", "label": f"CeX cash · {cex_item.get('title', '')}",
                "price": cex_item.get("price"), "url": url,
            }],
        })

    used_ebay_urls = set()
    for row in catalog:
        if any(o["source"] == "ebay" for o in row["offers"]):
            continue
        ebay_hit = best_match(row["title"], ebay_items)
        if not ebay_hit or ebay_hit.get("url") in used_ebay_urls:
            continue
        row["offers"].append({
            "source": "ebay", "label": "eBay usato (Compralo Subito)",
            "price": ebay_hit["price"], "url": ebay_hit["url"],
        })
        used_ebay_urls.add(ebay_hit["url"])

    for ebay_item in ebay_items:
        url = ebay_item.get("url")
        if not url or url in used_ebay_urls:
            continue
        used_ebay_urls.add(url)
        catalog.append({
            "title": ebay_item.get("title") or query.title(),
            "url": url,
            "image": ebay_item.get("image"),
            "is_game": True,
            "source_only": True,
            "primary_source": "ebay",
            "offers": [{
                "source": "ebay", "label": "eBay usato (Compralo Subito)",
                "price": ebay_item.get("price"), "url": url,
            }],
        })

    # Keep the user-facing search useful even when all three sites challenge the
    # server. Prices remain empty, never fabricated, and can be retried later.
    if not catalog and gamelife_enabled:
        catalog.append({
            "title": query.strip().title(),
            "url": f"https://www.gamelife.it/shop?search={query.strip().replace(' ', '+')}",
            "image": None,
            "is_game": True,
            "offers": [],
            "source_only": True,
        })

    def result_order(item):
        offers = item.get("offers", [])
        cex_prices = [
            offer["price"] for offer in item.get("offers", [])
            if offer.get("source") == "cex" and offer.get("price") is not None
        ]
        if item.get("primary_source") == "cex" or cex_prices:
            return (0, min(cex_prices, default=float("inf")))
        ebay_prices = [
            offer["price"] for offer in offers
            if offer.get("source") == "ebay" and offer.get("price") is not None
        ]
        if item.get("primary_source") == "ebay" or ebay_prices:
            return (1, min(ebay_prices, default=float("inf")))
        return (2, 0)

    gamelife_found = bool(gl_items)
    return sorted(catalog, key=result_order)[:limit], gamelife_found, gamelife_enabled
