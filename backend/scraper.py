"""Backward-compat shim: the scraping logic now lives in the `scrapers` package
(scrapers/gamelife.py, cex.py, ebay.py, aggregator.py). Kept so `import scraper`
keeps working for anything not yet migrated to `import scrapers`.
"""
from scrapers import (  # noqa: F401
    BASE, start_browser, stop_browser, search_games, fetch_product, search_all,
)
