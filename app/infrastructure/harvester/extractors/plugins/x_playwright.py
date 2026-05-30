"""X (Twitter) plugin — headless Playwright harvester.

Drives a headless Chromium to read a public X timeline or hashtag page, injects
an ``auth_token`` cookie to clear the login wall, and scrapes ``<article>`` tweet
cards. Pure data acquisition — **no LLM in this layer**.

Zero-hardcode: target URL, auth cookie, post limit and all tuning come from the
YAML ``options`` bag; nothing is baked into the code.

Example ``scraper_config.yaml`` entry::

    - name: x-elonmusk-trending
      type: x_playwright
      tenant_id: tenant_demo
      options:
        target_url: "https://x.com/elonmusk"
        auth_token: "YOUR_AUTH_TOKEN_HERE"   # X 'auth_token' cookie value
        limit: 10
        # optional tuning:
        headless: true
        wait_timeout_ms: 20000
        cookie_domain: ".x.com"
        locale: en

Compliance: public pages only; the cookie just clears X's login wall for public
content. Never harvest private/other-tenant data.
"""

from __future__ import annotations

from typing import Any

import structlog
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from app.infrastructure.harvester.extractors.base import BaseExtractor
from app.infrastructure.harvester.models import HarvestedItem

logger = structlog.get_logger(__name__)


class XPlaywrightExtractor(BaseExtractor):
    """Scrape public tweets from an X profile/hashtag page via Playwright."""

    PLUGIN_TYPE = "x_playwright"

    async def extract(self) -> list[HarvestedItem]:
        target_url = self.options.get("target_url")
        if not target_url:
            raise ValueError("x_playwright source requires options.target_url")

        auth_token = self.options.get("auth_token")
        limit = int(self.options.get("limit", 10))
        headless = bool(self.options.get("headless", True))
        wait_timeout_ms = int(self.options.get("wait_timeout_ms", 20000))
        cookie_domain = self.options.get("cookie_domain", ".x.com")
        locale = self.options.get("locale")
        log = logger.bind(target_url=target_url)

        items: list[HarvestedItem] = []

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=headless)
            context = await browser.new_context()
            try:
                # ── Inject the auth cookie to bypass the login wall ──────────
                if auth_token:
                    await context.add_cookies(
                        [
                            {
                                "name": "auth_token",
                                "value": str(auth_token),
                                "domain": cookie_domain,
                                "path": "/",
                                "httpOnly": True,
                                "secure": True,
                            }
                        ]
                    )
                else:
                    log.warning("x_no_auth_token", note="login wall may hide content")

                page = await context.new_page()
                await page.goto(target_url, wait_until="domcontentloaded")

                # ── Wait for the first tweet card; timeout → warn, not crash ──
                try:
                    await page.wait_for_selector("article", timeout=wait_timeout_ms)
                except PlaywrightTimeoutError:
                    log.warning(
                        "x_wait_timeout",
                        note="no <article> appeared (bad token, rate-limit, or layout change)",
                        timeout_ms=wait_timeout_ms,
                    )
                    return items  # nothing to harvest, but never crash the engine

                # ── Scroll to lazy-load until we reach `limit` (or run dry) ──
                seen: set[str] = set()
                stale_scrolls = 0
                max_scrolls = limit * 3 + 5
                for _ in range(max_scrolls):
                    if len(items) >= limit:
                        break
                    try:
                        articles = await page.query_selector_all("article")
                        for el in articles:
                            if len(items) >= limit:
                                break
                            text = (await el.inner_text()).strip()
                            if not text or text in seen:
                                continue
                            seen.add(text)

                            # Tweet permalink lives in a status anchor, if present.
                            href = ""
                            link_el = await el.query_selector("a[href*='/status/']")
                            if link_el:
                                href = await link_el.get_attribute("href") or ""
                            source_url = (
                                f"https://x.com{href}" if href.startswith("/") else (href or target_url)
                            )

                            # title = first line; content = full card text.
                            title = text.splitlines()[0][:280]
                            items.append(
                                HarvestedItem(
                                    source_url=source_url,
                                    title=title,
                                    content=text,
                                    locale=locale,
                                    metadata={
                                        "platform": "X",
                                        "url": target_url,
                                    },
                                )
                            )

                        before = len(seen)
                        await page.mouse.wheel(0, 3200)
                        await page.wait_for_timeout(1200)
                        # No new cards after a scroll → timeline exhausted.
                        stale_scrolls = stale_scrolls + 1 if len(seen) == before else 0
                        if stale_scrolls >= 3:
                            break
                    except PlaywrightTimeoutError:
                        log.warning("x_scroll_timeout", collected=len(items))
                        break
            finally:
                await context.close()
                await browser.close()

        log.info("x_extracted", count=len(items))
        return items[:limit]
