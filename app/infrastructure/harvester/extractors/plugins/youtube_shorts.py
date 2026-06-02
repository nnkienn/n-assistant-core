"""YouTube Shorts plugin — yt-dlp topic/keyword harvester.

Searches YouTube Shorts by keyword using yt-dlp's ``ytsearch`` extractor.
No API key required — yt-dlp uses YouTube's public search endpoints, the same
ones the browser calls. Returns video metadata (title, description, channel,
metrics, thumbnail) and optionally downloads the mp4 to the Raw Data Lake.

Why yt-dlp over Playwright for YouTube:
  - Handles YouTube's JS rendering natively — no browser startup.
  - Returns structured JSON for every video (duration, views, likes, tags).
  - Shorts filter: automatically drops videos longer than 60 s.
  - Optional download: ``download_video: true`` fetches the mp4 file and
    stamps ``media_path`` on the item.

Zero-hardcode: every target (query, limit, download flag, proxy) lives in
the YAML ``options`` bag — nothing is baked into the code.

Example ``scraper_config.yaml`` entry::

    - name: youtube-shorts-ai-trends
      type: youtube_shorts
      tenant_id: tenant_demo
      options:
        query: "AI tools 2025"
        limit: 20
        download_video: false   # true → saves mp4 under RAW_DATA_LAKE_PATH
        # optional:
        proxy: ""               # "socks5://user:pass@host:port"
        locale: en
        max_duration_s: 60      # drop videos longer than this (Shorts = ≤60 s)

Compliance: public videos only. Respect YouTube ToS and rate limits.
"""

from __future__ import annotations

import asyncio
import functools
from pathlib import Path
from typing import Any

import structlog

from app.core.config import settings
from app.infrastructure.harvester.extractors.base import BaseExtractor
from app.infrastructure.harvester.models import HarvestedItem

logger = structlog.get_logger(__name__)

# YouTube Shorts are ≤ 60 seconds by definition.
_DEFAULT_MAX_DURATION = 60


def _extract_sync(ydl_opts: dict[str, Any], url: str) -> dict[str, Any] | None:
    """Run yt-dlp extract_info in a thread (it is blocking I/O)."""
    try:
        import yt_dlp  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "yt-dlp is required for youtube_shorts plugin. "
            "Add `yt-dlp>=2024.1` to requirements.txt and rebuild the image."
        ) from exc

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)


def _download_sync(ydl_opts: dict[str, Any], url: str) -> None:
    """Download a single video URL (blocking)."""
    import yt_dlp  # noqa: PLC0415

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


class YouTubeShortsExtractor(BaseExtractor):
    """Harvest YouTube Shorts by topic keyword via yt-dlp."""

    PLUGIN_TYPE = "youtube_shorts"

    async def extract(self) -> list[HarvestedItem]:
        query = self.options.get("query")
        if not query:
            raise ValueError("youtube_shorts source requires options.query")

        limit          = int(self.options.get("limit", 20))
        download_video = bool(self.options.get("download_video", False))
        proxy          = self.options.get("proxy") or None
        locale         = self.options.get("locale")
        max_duration   = int(self.options.get("max_duration_s", _DEFAULT_MAX_DURATION))
        log = logger.bind(query=query, limit=limit)

        # yt-dlp search URL: fetch up to limit*3 candidates so we still hit
        # `limit` results after dropping long videos.
        search_url = f"ytsearch{limit * 3}:{query} #shorts"

        base_opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,   # metadata only, no download
            "skip_download": True,
        }
        if proxy:
            base_opts["proxy"] = proxy

        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(
            None, functools.partial(_extract_sync, base_opts, search_url)
        )

        if not info or "entries" not in info:
            log.warning("youtube_shorts_no_results", query=query)
            return []

        items: list[HarvestedItem] = []

        for entry in info["entries"]:
            if len(items) >= limit:
                break
            if not entry:
                continue

            duration = entry.get("duration") or 0
            if duration > max_duration:
                continue

            video_id  = entry.get("id", "")
            source_url = entry.get("webpage_url") or f"https://www.youtube.com/shorts/{video_id}"
            title      = (entry.get("title") or "").strip()
            description = (entry.get("description") or "").strip()
            thumbnail  = entry.get("thumbnail") or ""
            channel    = entry.get("channel") or entry.get("uploader") or ""

            media_path_str: str | None = None

            if download_video and video_id:
                dl_dir = (
                    Path(settings.RAW_DATA_LAKE_PATH)
                    / (self.source.tenant_id or "unknown")
                    / "youtube_shorts"
                )
                dl_dir.mkdir(parents=True, exist_ok=True)
                dl_opts = {
                    **base_opts,
                    "extract_flat": False,
                    "skip_download": False,
                    "outtmpl": str(dl_dir / f"{video_id}.%(ext)s"),
                    "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                }
                try:
                    await loop.run_in_executor(
                        None,
                        functools.partial(_download_sync, dl_opts, source_url),
                    )
                    # Resolve actual filename (extension varies).
                    candidates = list(dl_dir.glob(f"{video_id}.*"))
                    if candidates:
                        media_path_str = str(candidates[0])
                except Exception as exc:  # noqa: BLE001
                    log.warning("youtube_shorts_download_failed", video_id=video_id, error=str(exc))

            items.append(HarvestedItem(
                source_url=source_url,
                title=title,
                content=description,
                locale=locale,
                media_urls=[thumbnail] if thumbnail else [],
                media_path=media_path_str,
                metadata={
                    "platform": "YouTube",
                    "video_id": video_id,
                    "channel": channel,
                    "duration_s": duration,
                    "view_count": entry.get("view_count"),
                    "like_count": entry.get("like_count"),
                    "upload_date": entry.get("upload_date"),
                    "tags": entry.get("tags") or [],
                    "downloaded": media_path_str is not None,
                },
            ))

        log.info("youtube_shorts_extracted", count=len(items))
        return items
