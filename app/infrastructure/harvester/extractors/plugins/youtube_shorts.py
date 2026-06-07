"""YouTube Shorts plugin — yt-dlp 2-phase harvester.

Two extraction modes:

  **Channel mode** (recommended for quality):
    Scrapes the ``/shorts`` tab of curated, verified channels.
    Content is inherently high-quality (verified creators, real views).
    Config uses ``channel`` option pointing to a YouTube channel handle.

    Example::

        - name: yt-fireship
          type: youtube_shorts
          options:
            channel: "@Fireship"        # or full URL
            limit: 10

  **Search mode** (discovery / broad net):
    Uses ``ytsearch`` with ``#shorts`` in the query.
    Tends to surface small-creator content; use ``min_views`` to gate.

    Example::

        - name: yt-search-ai
          type: youtube_shorts
          options:
            query: "AI news"
            limit: 15
            min_views: 500

Architecture (both modes): 2-phase extraction for speed + quality:

  Phase 1 (fast, ~2 s):  ``extract_flat: True``
    → Returns basic metadata (title, view_count, duration, video_id)
    → Pre-filter: drop videos > max_duration, < min_views
    → Result: a short list of promising candidate IDs

  Phase 2 (slower, ~1-2 s/video):  ``extract_info`` per candidate
    → Returns FULL metadata (description, tags, upload_date, like_count, …)
    → Post-filter: drop videos older than max_age_days
    → Result: HarvestedItems with real content

Zero-hardcode: every target lives in the YAML ``options`` bag.
Compliance: public videos only. Respect YouTube ToS and rate limits.
"""

from __future__ import annotations

import asyncio
import functools
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import structlog

from app.core.config import settings
from app.infrastructure.harvester.extractors.base import BaseExtractor
from app.infrastructure.harvester.models import HarvestedItem

logger = structlog.get_logger(__name__)

_DEFAULT_MAX_DURATION = 60  # YouTube Shorts are ≤ 60 s.


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
    """Harvest YouTube Shorts via channel tabs or keyword search (2-phase)."""

    PLUGIN_TYPE = "youtube_shorts"

    async def extract(self) -> list[HarvestedItem]:
        channel = self.options.get("channel")  # e.g. "@Fireship"
        query = self.options.get("query")       # e.g. "AI news"

        if not channel and not query:
            raise ValueError(
                "youtube_shorts source requires options.channel OR options.query"
            )

        limit          = int(self.options.get("limit", 20))
        download_video = bool(self.options.get("download_video", False))
        proxy          = self.options.get("proxy") or None
        locale         = self.options.get("locale")
        max_duration   = int(self.options.get("max_duration_s", _DEFAULT_MAX_DURATION))
        min_views      = int(self.options.get("min_views", 0))
        max_age_days   = int(self.options.get("max_age_days", 0))  # 0 = disabled

        mode = "channel" if channel else "search"
        label = channel or query
        log = logger.bind(mode=mode, source=label, limit=limit, min_views=min_views)

        loop = asyncio.get_event_loop()

        # ── Phase 1: Fast flat listing ───────────────────────────────
        if channel:
            # Channel mode: scrape the /shorts tab directly.
            # Channel can be "@handle", "UCxxxxx", or a full URL.
            if channel.startswith("http"):
                channel_url = channel.rstrip("/")
            elif channel.startswith("@"):
                channel_url = f"https://www.youtube.com/{channel}"
            else:
                channel_url = f"https://www.youtube.com/@{channel}"
            # Append /shorts to target the Shorts tab specifically.
            if not channel_url.endswith("/shorts"):
                channel_url += "/shorts"

            search_url = channel_url
            flat_opts: dict[str, Any] = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": True,
                "skip_download": True,
                "playlistend": limit * 3,  # fetch extra to compensate for filters
            }
        else:
            # Search mode: ytsearch with #shorts tag.
            search_url = f"ytsearch{limit * 10}:{query} #shorts"
            flat_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": True,
                "skip_download": True,
            }

        if proxy:
            flat_opts["proxy"] = proxy

        info = await loop.run_in_executor(
            None, functools.partial(_extract_sync, flat_opts, search_url)
        )

        if not info:
            log.warning("youtube_shorts_no_results")
            return []

        # Handle both playlist-style (entries) and single-video responses.
        entries = info.get("entries", [info] if info.get("id") else [])

        # ── Pre-filter: duration + min_views ─────────────────────────
        candidates: list[dict[str, Any]] = []
        skipped_views = 0
        skipped_duration = 0

        for entry in entries:
            if not entry:
                continue
            if len(candidates) >= limit:
                break

            duration = entry.get("duration") or 0
            # duration=0 means unknown in flat mode — let through to Phase 2.
            if duration > max_duration and duration > 0:
                skipped_duration += 1
                continue

            views = entry.get("view_count") or 0
            if min_views > 0 and views < min_views:
                skipped_views += 1
                continue

            candidates.append(entry)

        log.info(
            "youtube_shorts_phase1_done",
            total_entries=len(entries),
            skipped_duration=skipped_duration,
            skipped_views=skipped_views,
            candidates=len(candidates),
        )

        if not candidates:
            log.warning("youtube_shorts_no_candidates_after_prefilter")
            return []

        # ── Phase 2: Full info for each candidate ────────────────────
        detail_opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }
        if proxy:
            detail_opts["proxy"] = proxy

        # Date cutoff for freshness filter.
        cutoff_date: str | None = None
        if max_age_days > 0:
            cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
            cutoff_date = cutoff.strftime("%Y%m%d")

        items: list[HarvestedItem] = []

        for idx, entry in enumerate(candidates):
            video_id = entry.get("id", "")
            video_url = (
                entry.get("url")
                or entry.get("webpage_url")
                or f"https://www.youtube.com/watch?v={video_id}"
            )
            # Ensure absolute URL for channel-mode entries.
            if video_url.startswith("/"):
                video_url = f"https://www.youtube.com{video_url}"

            try:
                full_info = await loop.run_in_executor(
                    None, functools.partial(_extract_sync, detail_opts, video_url)
                )
            except Exception as exc:  # noqa: BLE001
                log.warning(
                    "youtube_shorts_detail_failed",
                    video_id=video_id, error=str(exc)[:120],
                )
                continue

            if not full_info:
                continue

            # ── Duration recheck (Phase 2 has accurate duration) ─────
            real_duration = full_info.get("duration") or 0
            if real_duration > max_duration and real_duration > 0:
                log.debug("youtube_shorts_skip_long_phase2",
                          video_id=video_id, duration=real_duration)
                continue

            # ── Date freshness filter ────────────────────────────────
            upload_date = full_info.get("upload_date") or ""  # "YYYYMMDD"
            if cutoff_date and upload_date and upload_date < cutoff_date:
                log.debug("youtube_shorts_skip_old",
                          video_id=video_id, upload_date=upload_date)
                continue

            title       = (full_info.get("title") or "").strip()
            description = (full_info.get("description") or "").strip()
            thumbnail   = full_info.get("thumbnail") or ""
            channel_name = (full_info.get("channel")
                            or full_info.get("uploader") or "")
            duration    = full_info.get("duration") or 0
            source_url  = (full_info.get("webpage_url")
                           or f"https://www.youtube.com/shorts/{video_id}")

            # ── Optional video download ──────────────────────────────
            media_path_str: str | None = None

            if download_video and video_id:
                dl_dir = (
                    Path(settings.RAW_DATA_LAKE_PATH)
                    / (self.source.tenant_id or "unknown")
                    / "youtube_shorts"
                )
                dl_dir.mkdir(parents=True, exist_ok=True)
                dl_opts = {
                    **detail_opts,
                    "skip_download": False,
                    "outtmpl": str(dl_dir / f"{video_id}.%(ext)s"),
                    "format": (
                        "bestvideo[ext=mp4]+bestaudio[ext=m4a]"
                        "/best[ext=mp4]/best"
                    ),
                }
                try:
                    await loop.run_in_executor(
                        None,
                        functools.partial(_download_sync, dl_opts, source_url),
                    )
                    found = list(dl_dir.glob(f"{video_id}.*"))
                    if found:
                        media_path_str = str(found[0])
                except Exception as exc:  # noqa: BLE001
                    log.warning(
                        "youtube_shorts_download_failed",
                        video_id=video_id, error=str(exc)[:120],
                    )

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
                    "channel": channel_name,
                    "duration_s": duration,
                    "view_count": full_info.get("view_count"),
                    "like_count": full_info.get("like_count"),
                    "upload_date": upload_date,
                    "tags": full_info.get("tags") or [],
                    "downloaded": media_path_str is not None,
                },
            ))

            log.debug(
                "youtube_shorts_item_ok",
                idx=idx + 1, video_id=video_id, title=title[:60],
                views=full_info.get("view_count"),
                desc_len=len(description),
            )

        log.info("youtube_shorts_extracted", count=len(items))
        return items
