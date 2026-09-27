import asyncio

from scrapers import aggregator
from scrapers.ebay import _parse_api_results


def test_parse_api_results_keeps_used_fixed_price_eur_only():
    payload = {"itemSummaries": [
        {
            "title": "Tekken 6 PS3 usato economico",
            "itemWebUrl": "https://www.ebay.it/itm/used-fixed-cheap",
            "price": {"value": "7.50", "currency": "EUR"},
            "conditionId": "3000",
            "buyingOptions": ["FIXED_PRICE"],
        },
        {
            "title": "Tekken 6 PS3 usato",
            "itemWebUrl": "https://www.ebay.it/itm/used-fixed",
            "price": {"value": "12.50", "currency": "EUR"},
            "conditionId": "3000",
            "buyingOptions": ["FIXED_PRICE"],
        },
        {
            "title": "Tekken 6 asta",
            "itemWebUrl": "https://www.ebay.it/itm/used-auction",
            "price": {"value": "8.00", "currency": "EUR"},
            "conditionId": "3000",
            "buyingOptions": ["AUCTION"],
        },
        {
            "title": "Tekken 6 empty box no game",
            "itemWebUrl": "https://www.ebay.it/itm/empty-box",
            "price": {"value": "1.00", "currency": "EUR"},
            "conditionId": "3000",
            "buyingOptions": ["FIXED_PRICE"],
        },
        {
            "title": "Tekken 6 calendario promo inserto",
            "itemWebUrl": "https://www.ebay.it/itm/promo-insert",
            "price": {"value": "2.00", "currency": "EUR"},
            "conditionId": "3000",
            "buyingOptions": ["FIXED_PRICE"],
        },
        {
            "title": "Tekken 6 nuovo",
            "itemWebUrl": "https://www.ebay.it/itm/new-fixed",
            "price": {"value": "20.00", "currency": "EUR"},
            "conditionId": "1000",
            "buyingOptions": ["FIXED_PRICE"],
        },
    ]}

    results = _parse_api_results(payload, 20)

    assert [item["price"] for item in results] == [7.5, 12.5]
    assert results[0]["url"] == "https://www.ebay.it/itm/used-fixed-cheap"


def test_ebay_results_are_searchable_when_gamelife_is_unavailable(monkeypatch):
    async def no_results(*args, **kwargs):
        return []

    async def ebay_results(*args, **kwargs):
        return [{
            "title": "Tekken 6 PS3",
            "url": "https://www.ebay.it/itm/used-fixed",
            "image": None,
            "price": 12.5,
        }]

    monkeypatch.setattr(aggregator.gamelife, "search_games", no_results)
    monkeypatch.setattr(aggregator.cex, "search_buyback", no_results)
    monkeypatch.setattr(aggregator.ebay, "search_used_bin", ebay_results)

    results = asyncio.run(aggregator.search_all("tekken 6"))

    assert len(results) == 1
    assert results[0]["source_only"] is True
    assert results[0]["offers"] == [{
        "source": "ebay",
        "label": "eBay usato (Compralo Subito)",
        "price": 12.5,
        "url": "https://www.ebay.it/itm/used-fixed",
    }]


def test_ebay_search_uses_title_variants_without_unmatched_catalog_rows(monkeypatch):
    ebay_queries = []

    async def gamelife_results(query, **kwargs):
        if query == "tekken 6":
            return [{
                "title": "Tekken 6 PS3",
                "url": "https://www.gamelife.it/tekken-6",
                "image": None,
                "is_game": True,
            }]
        return []

    async def no_cex_results(*args, **kwargs):
        return []

    async def ebay_results(query, **kwargs):
        ebay_queries.append(query)
        if query == "tekken 6 videogioco":
            return [{
                "title": "Tekken Tag Tournament 2 PS3",
                "url": "https://www.ebay.it/itm/unmatched",
                "image": None,
                "price": 9.99,
            }]
        return []

    monkeypatch.setattr(aggregator.gamelife, "search_games", gamelife_results)
    monkeypatch.setattr(aggregator.cex, "search_buyback", no_cex_results)
    monkeypatch.setattr(aggregator.ebay, "search_used_bin", ebay_results)

    results = asyncio.run(aggregator.search_all("tekken 6"))

    assert ebay_queries == ["tekken 6", "tekken 6 videogioco", "tekken 6 gioco", "tekken 6 ps5"]
    assert all(row["url"] != "https://www.ebay.it/itm/unmatched" for row in results)


def test_ebay_only_rows_are_sorted_by_bin_price(monkeypatch):
    async def no_results(*args, **kwargs):
        return []

    async def ebay_results(*args, **kwargs):
        return [
            {"title": "Game expensive", "url": "https://www.ebay.it/itm/expensive", "price": 20.0},
            {"title": "Game cheap", "url": "https://www.ebay.it/itm/cheap", "price": 5.0},
        ]

    monkeypatch.setattr(aggregator.gamelife, "search_games", no_results)
    monkeypatch.setattr(aggregator.cex, "search_buyback", no_results)
    monkeypatch.setattr(aggregator.ebay, "search_used_bin", ebay_results)

    results = asyncio.run(aggregator.search_all("game"))

    assert [row["offers"][0]["price"] for row in results] == [5.0, 20.0]


def test_cex_actor_uses_cash_value_and_ignores_accessories():
    from scrapers.cex import _parse_actor_items

    results = _parse_actor_items([
        {
            "title": "Tekken 8 (Senza DLC)",
            "productUrl": "https://it.webuy.com/game/tekken8",
            "trade_in_cash": "€ 14,00",
            "trade_in_voucher": "€ 18,00",
            "currency": "EUR",
        },
        {
            "title": "HORI Fighting Stick Tekken 8 Edition",
            "productUrl": "https://it.webuy.com/controller/tekken8",
            "trade_in_cash": "€ 80,00",
            "currency": "EUR",
        },
        {
            "title": "Tekken 8 statuetta Kratos",
            "productUrl": "https://it.webuy.com/figure/tekken8",
            "trade_in_cash": "€ 80,00",
            "category": "Gaming Merchandise",
            "currency": "EUR",
        },
    ], 5)

    assert len(results) == 1
    assert results[0]["price"] == 14.0


def test_cex_comparison_keeps_all_cash_values_across_platforms(monkeypatch):
    async def gamelife_results(*args, **kwargs):
        return [{"title": "Tekken 8", "url": "https://www.gamelife.it/tekken8", "is_game": True}]

    async def cex_results(*args, **kwargs):
        return [
            {"title": "Tekken 8 PS5", "url": "https://it.webuy.com/ps5", "price": 14.0},
            {"title": "Tekken 8 Xbox Series", "url": "https://it.webuy.com/xbox", "price": 12.0},
        ]

    async def no_results(*args, **kwargs):
        return []

    monkeypatch.setattr(aggregator.gamelife, "search_games", gamelife_results)
    monkeypatch.setattr(aggregator.cex, "search_buyback", cex_results)
    monkeypatch.setattr(aggregator.ebay, "search_used_bin", no_results)

    results = asyncio.run(aggregator.search_all("tekken 8"))

    cex_prices = [o["price"] for o in results[0]["offers"] if o["source"] == "cex"]
    assert cex_prices == [12.0, 14.0]


def test_one_failed_source_variant_does_not_discard_other_results(monkeypatch):
    async def gamelife_results(query, **kwargs):
        if query == "god of war ps4":
            raise RuntimeError("temporary source error")
        if query == "god of war":
            return [{
                "title": "God of War",
                "url": "https://www.gamelife.it/god-of-war",
                "image": None,
                "is_game": True,
            }]
        return []

    async def no_results(*args, **kwargs):
        return []

    monkeypatch.setattr(aggregator.gamelife, "search_games", gamelife_results)
    monkeypatch.setattr(aggregator.cex, "search_buyback", no_results)
    monkeypatch.setattr(aggregator.ebay, "search_used_bin", no_results)

    results = asyncio.run(aggregator.search_all("god of war"))

    assert any(row["title"] == "God of War" for row in results)


def test_source_search_returns_partial_results_at_its_deadline():
    async def partial_then_hang(query, **kwargs):
        if query == "god of war":
            return [{"title": "God of War", "url": "https://example.test/gow"}]
        await asyncio.Event().wait()

    results = asyncio.run(aggregator._search_variants(
        partial_then_hang,
        ["god of war", "god of war videogioco"],
        limit=20,
        source="test",
        timeout_seconds=0.01,
    ))

    assert results == [{"title": "God of War", "url": "https://example.test/gow"}]