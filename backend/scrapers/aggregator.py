"""Combines GameLife/CeX/eBay searches into a single comparison list, per title.

GameLife stays the primary catalog (title/image/platform/is_game classification);
its buyback price is still fetched lazily per-product (see server.py /product,
unchanged). CeX and eBay show a price straight from search-results pages, so those
are attached eagerly here as source-tagged `offers`.
"""
import asyncio
import logging

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


async def search_all(query: str, limit: int = 20):
    query_list = variants(query)
    gl_items, cex_items, ebay_items = await asyncio.gather(
        _search_variants(gamelife.search_games, query_list, limit, "gamelife"),
        _search_variants(cex.search_buyback, query_list, limit, "cex", timeout_seconds=44),
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

    results = []

    # GameLife is the preferred catalog, but it must not be a hard dependency:
    # a Cloudflare challenge there should not erase usable CeX/eBay results.
    catalog = list(gl_items)
    if not catalog:
        seen = set()
        for source, items in (("ebay", ebay_items), ("cex", cex_items)):
            for it in items:
                title = it.get("title") or query.title()
                key = (title.lower(), it.get("url"))
                if key in seen:
                    continue
                seen.add(key)
                catalog.append({
                    "title": title,
                    "url": it.get("url") or f"https://www.gamelife.it/shop?search={query}",
                    "image": it.get("image"),
                    "price": it.get("price"),
                    "is_game": True,
                    "offers": [],
                    "source_only": True,
                    "primary_source": source,
                })

    for it in catalog:
        offers = []
        for cex_hit in matching_candidates(it["title"], cex_items):
            offers.append({
                "source": "cex", "label": f"CeX cash · {cex_hit['title']}",
                "price": cex_hit["price"], "url": cex_hit["url"],
            })
        ebay_hit = best_match(it["title"], ebay_items)
        if ebay_hit and not any(o["source"] == "ebay" for o in offers):
            offers.append({
                "source": "ebay", "label": "eBay usato (Compralo Subito)",
                "price": ebay_hit["price"], "url": ebay_hit["url"],
            })
        if it.get("source_only") and it.get("primary_source") == "ebay":
            offers = [{
                "source": "ebay", "label": "eBay usato (Compralo Subito)",
                "price": it.get("price"), "url": it.get("url"),
            }]
        results.append({**it, "offers": offers})

    if not gl_items:
        matched_ebay_urls = {
            hit.get("url")
            for game in gl_items
            if (hit := best_match(game.get("title", ""), ebay_items)) is not None
        }
        existing_urls = {item.get("url") for item in results}
        for item in ebay_items:
            if item.get("url") in matched_ebay_urls or item.get("url") in existing_urls:
                continue
            results.append({
                "title": item.get("title") or query.title(),
                "url": item["url"],
                "image": item.get("image"),
                "price": item.get("price"),
                "is_game": True,
                "source_only": True,
                "primary_source": "ebay",
                "offers": [{
                    "source": "ebay",
                    "label": "eBay usato (Compralo Subito)",
                    "price": item.get("price"),
                    "url": item["url"],
                }],
            })
            existing_urls.add(item["url"])

    # Keep the user-facing search useful even when all three sites challenge the
    # server. Prices remain empty, never fabricated, and can be retried later.
    if not results:
        results.append({
            "title": query.strip().title(),
            "url": f"https://www.gamelife.it/shop?search={query.strip().replace(' ', '+')}",
            "image": None,
            "is_game": True,
            "offers": [],
            "source_only": True,
        })
    def result_order(item):
        if not item.get("source_only"):
            return (0, 0)
        ebay_prices = [
            offer["price"] for offer in item.get("offers", [])
            if offer.get("source") == "ebay" and offer.get("price") is not None
        ]
        return (1, min(ebay_prices, default=float("inf")))

    return sorted(results, key=result_order)
