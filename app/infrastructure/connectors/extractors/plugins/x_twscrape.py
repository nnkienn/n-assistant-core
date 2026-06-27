"""X (Twitter) plugin — twscrape harvester.

Uses X's internal GraphQL API via ``twscrape`` — the same endpoints the
official mobile app calls. Compared to the Playwright approach this plugin:

* Returns structured JSON (no DOM parsing, no fragile CSS selectors).
* Provides video URLs natively at all quality variants — no network interception.
* Is ~10× faster (no browser startup) and less detectable.
* Handles pagination, deduplication, and rate-limit back-off internally.

Auth: twscrape uses the same ``auth_token`` + ``ct0`` pair you already have.
Both values come from YAML ``options`` (resolved from .env — never hardcoded).

Example ``scraper_config.yaml`` entry::

    - name: x-ai-trending
      type: x_twscrape
      tenant_id: tenant_demo
      options:
        query: "AI agent trending lang:en"
        limit: 50
        auth_token: "${X_AUTH_TOKEN}"
        ct0: "${X_CT0_TOKEN}"
        product: "Top"    # "Latest" | "Top" | "Media"
        locale: en

Auth tokens (get from browser devtools → Application → Cookies → x.com):
  auth_token — the long session cookie (name: auth_token)
  ct0        — CSRF token (name: ct0)

Compliance: public search results only. Never query private or
other-tenant accounts. Respect X's ToS and rate limits.
"""

from __future__ import annotations

import os
import tempfile

import structlog

from app.infrastructure.connectors.extractors.base import BaseExtractor
from app.infrastructure.connectors.models import HarvestedItem

logger = structlog.get_logger(__name__)


class XTwscrapeExtractor(BaseExtractor):
    """Scrape public X search results via twscrape (GraphQL API)."""

    PLUGIN_TYPE = "x_twscrape"

    async def extract(self) -> list[HarvestedItem]:
        try:
            from twscrape import API  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "twscrape is required for x_twscrape plugin. "
                "Add `twscrape>=0.14` to requirements.txt and rebuild the image."
            ) from exc

        query = self.options.get("query")
        if not query:
            raise ValueError("x_twscrape source requires options.query")

        auth_token = self.options.get("auth_token")
        ct0        = self.options.get("ct0")
        limit      = int(self.options.get("limit", 20))
        locale     = self.options.get("locale")
        product    = self.options.get("product", "Latest")
        log = logger.bind(query=query, product=product)

        if not auth_token or not ct0 or "${" in str(auth_token) or "${" in str(ct0):
            raise ValueError(
                "x_twscrape requires X_AUTH_TOKEN and X_CT0_TOKEN in .env. "
                "Get both from browser devtools → F12 → Application → Cookies → x.com"
            )

        # twscrape uses aiosqlite; ":memory:" opens a new DB per async connection
        # so schema migrations don't survive across calls. Use a temp file instead
        # and clean it up when done.
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        db_path = tmp.name

        items: list[HarvestedItem] = []
        try:
            api = API(db_path)
            await api.pool.add_account(
                username=f"acct_{auth_token[:8]}",
                password="unused",
                email="unused@n-assistant.local",
                email_password="unused",
                cookies=f"auth_token={auth_token}; ct0={ct0}",
            )

            async for tweet in api.search(query, limit=limit, kv={"product": product}):
                source_url = f"https://x.com/{tweet.user.username}/status/{tweet.id}"

                video_urls: list[str] = []
                if tweet.media and tweet.media.videos:
                    for vid in tweet.media.videos:
                        variants = sorted(
                            vid.variants or [],
                            key=lambda v: v.bitrate or 0,
                            reverse=True,
                        )
                        video_urls.extend(v.url for v in variants if v.url)

                image_urls: list[str] = []
                if tweet.media and tweet.media.photos:
                    image_urls = [p.url for p in tweet.media.photos if p.url]

                items.append(HarvestedItem(
                    source_url=source_url,
                    title=tweet.rawContent.splitlines()[0][:280],
                    content=tweet.rawContent,
                    locale=locale,
                    media_urls=video_urls + image_urls,
                    metadata={
                        "platform": "X",
                        "tweet_id": str(tweet.id),
                        "author": tweet.user.username,
                        "like_count": tweet.likeCount,
                        "retweet_count": tweet.retweetCount,
                        "reply_count": tweet.replyCount,
                        "view_count": tweet.viewCount,
                        "created_at": tweet.date.isoformat() if tweet.date else None,
                        "has_video": bool(video_urls),
                        "has_image": bool(image_urls),
                        "lang": tweet.lang,
                    },
                ))
        finally:
            try:
                os.unlink(db_path)
            except OSError:
                pass

        video_count = sum(1 for i in items if i.media_urls)
        log.info("x_twscrape_extracted", count=len(items), with_video=video_count)
        return items
