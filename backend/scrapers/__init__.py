"""Multi-source price scraping: GameLife (valutazione), CeX (ricompra usato), eBay (usato BIN).

Backward-compatible re-exports keep `scraper.py` (top-level shim) and server.py working
with the same names as before the split (search_games/fetch_product/BASE/start_browser).
"""
from . import browser, gamelife, cex, ebay, aggregator, match  # noqa: F401

start_browser = browser.start_browser
stop_browser = browser.stop_browser
search_games = gamelife.search_games
fetch_product = gamelife.fetch_product
search_all = aggregator.search_all
BASE = gamelife.BASE
