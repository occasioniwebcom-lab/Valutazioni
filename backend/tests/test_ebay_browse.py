import asyncio

from scrapers import aggregator
from scrapers.ebay import _parse_api_results


def test_parse_api_results_keeps_used_fixed_price_eur_only():
    payload = {"itemSummaries": [
        {
            "title": "Tekken 6 PS3 usato economico",
            "itemWebUrl": "https://www.ebay.it/itm/used-fixed-cheap",
            "price": {"value": "7.50", "currency": "EUR"},
            "conditionId": "5000",
            "buyingOptions": ["FIXED_PRICE"],
            "itemLocation": {"country": "IT"},
        },
        {
            "title": "Tekken 6 PS3 usato",
            "itemWebUrl": "https://www.ebay.it/itm/used-fixed",
            "price": {"value": "12.50", "currency": "EUR"},
            "conditionId": "5000",
            "buyingOptions": ["FIXED_PRICE"],
            "itemLocation": {"country": "IT"},
        },
        {
            "title": "Tekken 6 asta",
            "itemWebUrl": "https://www.ebay.it/itm/used-auction",
            "price": {"value": "8.00", "currency": "EUR"},
            "conditionId": "5000",
            "buyingOptions": ["AUCTION"],
            "itemLocation": {"country": "IT"},
        },
        {
            "title": "Tekken 6 empty box no game",
            "itemWebUrl": "https://www.ebay.it/itm/empty-box",
            "price": {"value": "1.00", "currency": "EUR"},
            "conditionId": "5000",
            "buyingOptions": ["FIXED_PRICE"],
            "itemLocation": {"country": "IT"},
        },
        {
            "title": "Tekken 6 calendario promo inserto",
            "itemWebUrl": "https://www.ebay.it/itm/promo-insert",
            "price": {"value": "2.00", "currency": "EUR"},
            "conditionId": "5000",
            "buyingOptions": ["FIXED_PRICE"],
            "itemLocation": {"country": "IT"},
        },
        {
            "title": "Tekken 6 nuovo",
            "itemWebUrl": "https://www.ebay.it/itm/new-fixed",
            "price": {"value": "20.00", "currency": "EUR"},
            "conditionId": "1000",
            "buyingOptions": ["FIXED_PRICE"],
            "itemLocation": {"country": "IT"},
        },
        {
            "title": "Tekken 6 PS3 usato estero",
            "itemWebUrl": "https://www.ebay.it/itm/foreign-item",
            "price": {"value": "3.00", "currency": "EUR"},
            "conditionId": "5000",
            "buyingOptions": ["FIXED_PRICE"],
            "itemLocation": {"country": "DE"},
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

    results, gamelife_found, gamelife_enabled = asyncio.run(aggregator.search_all("tekken 6"))

    assert gamelife_found is False
    assert gamelife_enabled is False
    assert len(results) == 1
    assert results[0]["source_only"] is True
    assert results[0]["offers"] == [{
        "source": "ebay",
        "label": "eBay usato (Compralo Subito)",
        "price": 12.5,
        "url": "https://www.ebay.it/itm/used-fixed",
    }]


def test_ebay_search_uses_title_variants_and_stays_independent_from_gamelife(monkeypatch):
    monkeypatch.setenv("GAMELIFE_ENABLED", "true")
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

    results, gamelife_found, gamelife_enabled = asyncio.run(aggregator.search_all("tekken 6"))

    assert gamelife_found is True
    assert gamelife_enabled is True
    assert ebay_queries == ["tekken 6", "tekken 6 videogioco", "tekken 6 gioco", "tekken 6 ps5"]
    # eBay results independent of GameLife: an unmatched listing still surfaces
    # as its own row instead of being dropped just because GameLife found data.
    unmatched = next(row for row in results if row["url"] == "https://www.ebay.it/itm/unmatched")
    assert unmatched["primary_source"] == "ebay"
    assert unmatched["offers"][0]["price"] == 9.99


def test_search_rows_are_limited_to_40_with_cex_first_then_ebay_by_price(monkeypatch):
    async def cex_results(*args, **kwargs):
        return [
            {"title": f"CEX Unique Game Product {index}", "url": f"https://it.webuy.com/{index}", "price": 50.0 - index}
            for index in range(25)
        ]

    async def ebay_results(*args, **kwargs):
        return [
            {"title": f"EBAY Distinct Listing Item {index}", "url": f"https://www.ebay.it/itm/{index}", "price": 40.0 - index}
            for index in range(25)
        ]

    async def no_results(*args, **kwargs):
        return []

    monkeypatch.setattr(aggregator.gamelife, "search_games", no_results)
    monkeypatch.setattr(aggregator.cex, "search_buyback", cex_results)
    monkeypatch.setattr(aggregator.ebay, "search_used_bin", ebay_results)

    results, gamelife_found, gamelife_enabled = asyncio.run(aggregator.search_all("game"))

    assert gamelife_found is False
    assert gamelife_enabled is False
    assert len(results) == 40
    sources = [row["primary_source"] for row in results]
    assert sources[:25] == ["cex"] * 25
    assert sources[25:] == ["ebay"] * 15
    assert [row["offers"][0]["price"] for row in results[:25]] == sorted(
        row["offers"][0]["price"] for row in results[:25]
    )
    assert [row["offers"][0]["price"] for row in results[25:]] == sorted(
        row["offers"][0]["price"] for row in results[25:]
    )


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
    monkeypatch.setenv("GAMELIFE_ENABLED", "true")
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

    results, gamelife_found, gamelife_enabled = asyncio.run(aggregator.search_all("tekken 8"))

    assert gamelife_found is True
    assert gamelife_enabled is True
    cex_prices = [o["price"] for o in results[0]["offers"] if o["source"] == "cex"]
    assert cex_prices == [12.0, 14.0]


def test_one_failed_source_variant_does_not_discard_other_results(monkeypatch):
    monkeypatch.setenv("GAMELIFE_ENABLED", "true")
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

    results, gamelife_found, gamelife_enabled = asyncio.run(aggregator.search_all("god of war"))

    assert gamelife_found is True
    assert gamelife_enabled is True
    assert any(row["title"] == "God of War" for row in results)


def test_disabled_gamelife_keeps_other_sources(monkeypatch):
    monkeypatch.setenv("GAMELIFE_ENABLED", "false")
    gamelife_calls = []

    async def slow_gamelife(*args, **kwargs):
        gamelife_calls.append(args[0])
        await asyncio.sleep(1)
        return []

    async def cex_results(*args, **kwargs):
        return [{"title": "Tekken 8", "url": "https://it.webuy.com/tekken8", "price": 12.0}]

    async def no_results(*args, **kwargs):
        return []

    monkeypatch.setattr(aggregator.gamelife, "search_games", slow_gamelife)
    monkeypatch.setattr(aggregator.cex, "search_buyback", cex_results)
    monkeypatch.setattr(aggregator.ebay, "search_used_bin", no_results)

    results, gamelife_found, gamelife_enabled = asyncio.run(aggregator.search_all("tekken 8"))

    assert gamelife_found is False
    assert gamelife_enabled is False
    assert gamelife_calls == []
    assert any(row["primary_source"] == "cex" for row in results)


def test_disabled_gamelife_does_not_create_placeholder_row(monkeypatch):
    monkeypatch.setenv("GAMELIFE_ENABLED", "false")

    async def no_results(*args, **kwargs):
        return []

    monkeypatch.setattr(aggregator.gamelife, "search_games", no_results)
    monkeypatch.setattr(aggregator.cex, "search_buyback", no_results)
    monkeypatch.setattr(aggregator.ebay, "search_used_bin", no_results)

    results, gamelife_found, gamelife_enabled = asyncio.run(aggregator.search_all("unknown game"))

    assert results == []
    assert gamelife_found is False
    assert gamelife_enabled is False


def test_cex_uses_only_the_original_query_to_limit_apify_runs(monkeypatch):
    monkeypatch.setenv("GAMELIFE_ENABLED", "false")
    cex_queries = []

    async def cex_results(query, **kwargs):
        cex_queries.append(query)
        return [{"title": "Tekken 8 PS5", "url": "https://it.webuy.com/tekken8", "price": 12.0}]

    async def ebay_results(query, **kwargs):
        return [{"title": "Tekken 8 PS5", "url": "https://www.ebay.it/itm/tekken8", "price": 20.0}]

    async def unexpected_gamelife(*args, **kwargs):
        raise AssertionError("GameLife search must remain disabled")

    monkeypatch.setattr(aggregator.gamelife, "search_games", unexpected_gamelife)
    monkeypatch.setattr(aggregator.cex, "search_buyback", cex_results)
    monkeypatch.setattr(aggregator.ebay, "search_used_bin", ebay_results)

    results, gamelife_found, gamelife_enabled = asyncio.run(aggregator.search_all("tekken 8"))

    assert cex_queries == ["tekken 8"]
    assert gamelife_found is False
    assert gamelife_enabled is False
    assert len(results) == 1
    assert {offer["source"] for offer in results[0]["offers"]} == {"cex", "ebay"}


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