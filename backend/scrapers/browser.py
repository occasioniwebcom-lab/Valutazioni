"""Shared Playwright browser lifecycle, used by every source scraper.

A single Chromium instance is reused across gamelife/cex/ebay scrapers (each opens
its own short-lived browser context per request) to keep memory usage sane.
"""
import asyncio
import logging
import os
import sys

from playwright.async_api import async_playwright

# Playwright browsers are pre-installed here in this environment; the supervisor
# process env does not inherit PLAYWRIGHT_BROWSERS_PATH, so set a sane default.
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/pw-browsers")

logger = logging.getLogger("scrapers.browser")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

_pw = None
_browser = None
_launch_lock = asyncio.Lock()
_LAUNCH_ARGS = ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]


async def _install_chromium():
    """Download the Chromium build matching the installed Playwright version.

    The browser cache (/pw-browsers) can be reset when the container restarts, or
    provisioned with a mismatched build. Reinstalling on demand makes startup
    self-healing across preview restarts and fresh deploy environments.
    """
    logger.info("Installing Playwright chromium (self-heal)...")
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "playwright", "install", "chromium",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
    )
    out, _ = await proc.communicate()
    logger.info("playwright install finished rc=%s", proc.returncode)
    if out:
        logger.info("playwright install output tail: %s", out.decode(errors="ignore")[-400:])


async def start_browser():
    global _pw, _browser
    async with _launch_lock:
        if _browser is not None and _browser.is_connected():
            return _browser
        if _pw is None:
            _pw = await async_playwright().start()
        for attempt in range(2):
            try:
                _browser = await _pw.chromium.launch(headless=True, args=_LAUNCH_ARGS)
                logger.info("Playwright chromium launched")
                return _browser
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                if attempt == 0 and ("Executable doesn't exist" in msg or "playwright install" in msg):
                    await _install_chromium()
                    continue
                logger.error("Chromium launch failed: %s", msg)
                raise
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


async def get_browser():
    if _browser is None or not _browser.is_connected():
        return await start_browser()
    return _browser


async def new_context(**kwargs):
    """New isolated browser context with sane defaults (locale/timezone/UA)."""
    b = await get_browser()
    opts = {"locale": "it-IT", "timezone_id": "Europe/Rome", "user_agent": UA}
    opts.update(kwargs)
    return await b.new_context(**opts)
