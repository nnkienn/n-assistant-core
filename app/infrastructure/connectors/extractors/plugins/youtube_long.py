"""YouTube Long Video plugin — pure yt-dlp (metadata + subtitle download).

Two extraction modes (mirrors youtube_shorts plugin interface):

  **Channel mode** (recommended for quality):
    Scrapes the /videos tab of curated, high-signal AI channels.
    Config uses ``channel`` option pointing to a YouTube channel handle.

    Example::

        - name: yt-long-lex
          type: youtube_long
          options:
            channel: "@lexfridman"
            limit: 5
            min_duration_s: 600    # 10 min minimum
            segment_duration_s: 120

  **Search mode** (trending discovery):
    Keyword search for recent long-form AI content with engagement gate.

    Example::

        - name: yt-long-search-ai
          type: youtube_long
          options:
            query: "AI agent tutorial 2026"
            limit: 10
            min_views: 5000
            min_duration_s: 300

Key difference from youtube_shorts:
  - Duration gate is INVERTED — minimum duration (not maximum).
  - Content = REAL transcript segments fetched via yt-dlp subtitle download
    (NOT youtube-transcript-api which 429s on the timedtext endpoint).
  - Each transcript window → one HarvestedItem (N items per video).
  - source_url includes ``?t=XXs`` to link directly to the segment start.

Pipeline position:
    [yt-dlp] Phase 1 flat listing → Phase 2 metadata + subtitle write
    [JSON3 parser] parse subtitle file → transcript entries
    [segmentation] split into segment_duration_s windows
    → multiple HarvestedItems per video → Raw Data Lake

Why yt-dlp subtitle download instead of youtube-transcript-api:
  youtube-transcript-api calls the timedtext API in a separate HTTP session
  which YouTube rate-limits (429) on datacenter/Docker IPs regardless of
  cookies. yt-dlp downloads subtitles through the same authenticated session
  used for metadata — one fewer independent request context to rate-limit.

Rate-limiting etiquette (YouTube ToS compliance):
  - ``sleep_interval_requests`` in yt-dlp flat-listing options.
  - ``request_delay_s`` configurable pause between Phase 2 per-video fetches.
  - ``proxy`` forwarded to yt-dlp when provided.
  - At most ``limit`` full-info fetches per run (Phase 1 limits the pool).

Segment metadata stored in ``HarvestedItem.metadata``:
  - ``segment_index``   — 0-based index within the video's segments
  - ``total_segments``  — total segments produced for this video
  - ``start_s``         — segment start time in seconds
  - ``end_s``           — segment end time in seconds
  - ``video_title``     — original video title (all segments share this)
  - ``video_id``        — YouTube video ID
  - ``channel``         — uploader channel name
  - ``duration_s``      — full video duration in seconds
  - ``view_count``      — video view count at harvest time
  - ``upload_date``     — "YYYYMMDD" string
  - ``transcript_lang`` — language code of the fetched transcript
"""

from __future__ import annotations

import asyncio
import functools
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import structlog

from app.infrastructure.connectors.extractors.base import BaseExtractor
from app.infrastructure.connectors.models import HarvestedItem

logger = structlog.get_logger(__name__)

_DEFAULT_MIN_DURATION = 180   # 3 minutes — weed out Shorts that slip through search
_DEFAULT_MAX_DURATION = 3600  # 60 minutes — skip very long podcasts by default
_DEFAULT_SEGMENT_S    = 120   # 2-minute transcript windows
_DEFAULT_LANG         = "en"


def _extract_sync(ydl_opts: dict[str, Any], url: str) -> dict[str, Any] | None:
    """Run yt-dlp extract_info in a thread (blocking I/O)."""
    try:
        import yt_dlp  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "yt-dlp is required for youtube_long plugin. "
            "Add `yt-dlp>=2024.1` to requirements.txt."
        ) from exc

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)


def _parse_json3_subtitles(path: str) -> list[dict[str, Any]] | None:
    """Parse yt-dlp's JSON3 subtitle format into transcript entries.

    JSON3 structure: ``{"events": [{"tStartMs": N, "dDurationMs": N,
    "segs": [{"utf8": "text"}, ...]}, ...]}``.
    Returns None when the file has no usable text events.
    """
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:  # noqa: BLE001
        return None

    entries: list[dict[str, Any]] = []
    for event in data.get("events", []):
        segs = event.get("segs", [])
        text = "".join(seg.get("utf8", "") for seg in segs).strip()
        if not text or text == "\n":
            continue
        start_ms = float(event.get("tStartMs", 0))
        dur_ms   = float(event.get("dDurationMs", 0))
        entries.append({
            "text":     text,
            "start":    start_ms / 1000.0,
            "duration": dur_ms   / 1000.0,
        })

    return entries if entries else None


def _download_subtitles_sync(
    ydl_base_opts: dict[str, Any],
    video_url: str,
    video_id: str,
    lang: str,
    tmp_dir: str,
) -> list[dict[str, Any]] | None:
    """Download subtitle file via yt-dlp and parse it (blocking).

    Uses the same yt-dlp session (cookies, proxy) as Phase 2 metadata
    extraction. This avoids the 429 rate-limit that hits the timedtext API
    when called through youtube-transcript-api's separate HTTP session.

    Args:
        ydl_base_opts: Phase 2 opts (already has cookiefile/proxy set).
        tmp_dir:       Writable temp directory; subtitle file is deleted after parsing.

    Returns:
        List of ``{'text', 'start', 'duration'}`` dicts, or None on failure.
    """
    import yt_dlp  # noqa: PLC0415

    sub_opts: dict[str, Any] = {
        **ydl_base_opts,
        # Write subtitle files without downloading the video.
        "writesubtitles":    True,
        "writeautomaticsub": True,
        "subtitleslangs":    [lang],
        "subtitlesformat":   "json3",
        "outtmpl":           os.path.join(tmp_dir, "%(id)s.%(ext)s"),
        "nooverwrites":      False,
    }

    try:
        with yt_dlp.YoutubeDL(sub_opts) as ydl:
            # download=True triggers the postprocessor pipeline that writes
            # subtitle files; skip_download=True (already in base_opts) still
            # prevents the actual video download.
            ydl.download([video_url])
    except Exception:  # noqa: BLE001
        return None

    # yt-dlp writes files as: <video_id>.<lang>.json3 or <id>.<lang>-orig.json3
    for candidate in [
        f"{video_id}.{lang}.json3",
        f"{video_id}.{lang}-orig.json3",
    ]:
        sub_path = os.path.join(tmp_dir, candidate)
        if os.path.exists(sub_path):
            entries = _parse_json3_subtitles(sub_path)
            try:
                os.unlink(sub_path)
            except OSError:
                pass
            return entries

    return None


def _segment_transcript(
    entries: list[dict[str, Any]],
    segment_duration_s: int,
) -> list[dict[str, Any]]:
    """Split transcript entries into fixed-duration windows.

    Each window dict has:
      - ``text``    — joined text of all entries within the window
      - ``start_s`` — window start in seconds (first entry's ``start``)
      - ``end_s``   — window end in seconds (last entry's ``start`` + ``duration``)

    Empty windows (all entries stripped to whitespace) are omitted.
    """
    if not entries:
        return []

    windows: list[dict[str, Any]] = []
    bucket_start = entries[0]["start"]
    bucket_end   = bucket_start + segment_duration_s
    current: list[str] = []
    first_entry_start = bucket_start
    last_entry_end    = bucket_start

    for entry in entries:
        t_start = float(entry.get("start", 0))
        t_dur   = float(entry.get("duration", 0))
        t_end   = t_start + t_dur

        if t_start >= bucket_end:
            # Flush current bucket.
            text = " ".join(current).strip()
            if text:
                windows.append({
                    "text":    text,
                    "start_s": first_entry_start,
                    "end_s":   last_entry_end,
                })
            # Advance to the correct bucket for this entry.
            while t_start >= bucket_end:
                bucket_start = bucket_end
                bucket_end   = bucket_start + segment_duration_s
            current = []
            first_entry_start = t_start

        current.append(entry.get("text", "").strip())
        last_entry_end = t_end

    # Flush the final bucket.
    text = " ".join(current).strip()
    if text:
        windows.append({
            "text":    text,
            "start_s": first_entry_start,
            "end_s":   last_entry_end,
        })

    return windows


class YouTubeLongExtractor(BaseExtractor):
    """Harvest long YouTube videos and segment their transcripts.

    Each transcript segment becomes one :class:`HarvestedItem`, so the
    downstream filter pipeline receives manageable, LLM-ready chunks
    rather than hour-long monoliths.
    """

    PLUGIN_TYPE = "youtube_long"

    async def extract(self) -> list[HarvestedItem]:  # noqa: C901 — sequential phases
        channel = self.options.get("channel")  # e.g. "@lexfridman"
        query   = self.options.get("query")    # e.g. "AI agent 2026"

        if not channel and not query:
            raise ValueError(
                "youtube_long source requires options.channel OR options.query"
            )

        limit              = int(self.options.get("limit", 10))
        min_duration_s     = int(self.options.get("min_duration_s", _DEFAULT_MIN_DURATION))
        max_duration_s     = int(self.options.get("max_duration_s", _DEFAULT_MAX_DURATION))
        min_views          = int(self.options.get("min_views", 0))
        max_age_days       = int(self.options.get("max_age_days", 0))
        segment_duration_s = int(self.options.get("segment_duration_s", _DEFAULT_SEGMENT_S))
        subtitle_lang      = str(self.options.get("subtitle_lang", _DEFAULT_LANG))
        request_delay_s    = float(self.options.get("request_delay_s", 2.0))
        proxy              = self.options.get("proxy") or None
        _raw_cookie        = self.options.get("cookiefile") or ""
        # Treat unresolved placeholder ("${...}") or missing file as disabled.
        cookie_file: str | None = (
            _raw_cookie
            if _raw_cookie and not _raw_cookie.startswith("${") and os.path.exists(_raw_cookie)
            else None
        )
        locale             = self.options.get("locale")

        mode  = "channel" if channel else "search"
        label = channel or query
        log   = logger.bind(mode=mode, source=label, limit=limit)

        loop = asyncio.get_event_loop()
        # Shared temp dir for subtitle files — cleaned up after each video.
        tmp_dir = tempfile.mkdtemp(prefix="yt_subs_")

        # ── Phase 1: Fast flat listing ───────────────────────────────────
        flat_opts: dict[str, Any] = {
            "quiet":           True,
            "no_warnings":     True,
            "extract_flat":    True,
            "skip_download":   True,
            "sleep_interval_requests": max(request_delay_s / 2, 0.5),
            "extractor_args":  {"youtube": {"skip": ["dash", "hls", "translated_subs"]}},
        }
        if proxy:
            flat_opts["proxy"] = proxy
        if cookie_file:
            flat_opts["cookiefile"] = cookie_file

        if channel:
            if channel.startswith("http"):
                channel_url = channel.rstrip("/")
            elif channel.startswith("@"):
                channel_url = f"https://www.youtube.com/{channel}"
            else:
                channel_url = f"https://www.youtube.com/@{channel}"
            # /videos tab for long-form content (not /shorts).
            if not channel_url.endswith("/videos"):
                channel_url = channel_url.rstrip("/") + "/videos"
            search_url = channel_url
            flat_opts["playlistend"] = limit * 4  # over-fetch to survive filters
        else:
            # yt-dlp search: no #shorts tag so we don't get Shorts.
            search_url = f"ytsearch{limit * 5}:{query}"

        log.info("youtube_long_phase1_start", url=search_url)
        try:
            info = await loop.run_in_executor(
                None, functools.partial(_extract_sync, flat_opts, search_url)
            )
        except Exception as exc:  # noqa: BLE001
            log.error("youtube_long_phase1_failed", error=str(exc)[:120])
            return []

        if not info:
            log.warning("youtube_long_no_results")
            return []

        entries = info.get("entries", [info] if info.get("id") else [])

        # ── Pre-filter: duration gate + min_views ─────────────────────────
        candidates: list[dict[str, Any]] = []
        skipped_short    = 0
        skipped_long     = 0
        skipped_views    = 0

        for entry in entries:
            if not entry:
                continue
            if len(candidates) >= limit:
                break

            duration = entry.get("duration") or 0
            if duration > 0 and duration < min_duration_s:
                skipped_short += 1
                continue
            if duration > max_duration_s and duration > 0:
                skipped_long += 1
                continue

            views = entry.get("view_count") or 0
            if min_views > 0 and views < min_views:
                skipped_views += 1
                continue

            candidates.append(entry)

        log.info(
            "youtube_long_phase1_done",
            total_entries=len(entries),
            skipped_short=skipped_short,
            skipped_long=skipped_long,
            skipped_views=skipped_views,
            candidates=len(candidates),
        )

        if not candidates:
            log.warning("youtube_long_no_candidates")
            return []

        # ── Phase 2+3+4: Per-video — metadata, transcript, segmentation ───
        detail_opts: dict[str, Any] = {
            "quiet":                   True,
            "no_warnings":             True,
            "skip_download":           True,
            # Skip DASH/HLS manifest fetching — those URLs 403 from Docker IPs
            # even with valid cookies and spam the log. We only need page-level
            # metadata (title, duration, upload_date), not stream URLs.
            "extractor_args":          {"youtube": {"skip": ["dash", "hls", "translated_subs"]}},
            # Safety net: if skipping DASH/HLS leaves no formats, don't raise —
            # still return metadata dict so title/duration/upload_date are usable.
            "ignore_no_formats_error": True,
        }
        if proxy:
            detail_opts["proxy"] = proxy
        if cookie_file:
            detail_opts["cookiefile"] = cookie_file

        cutoff_date: str | None = None
        if max_age_days > 0:
            cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
            cutoff_date = cutoff.strftime("%Y%m%d")

        all_items: list[HarvestedItem] = []

        for video_idx, entry in enumerate(candidates):
            video_id  = entry.get("id", "")
            video_url = (
                entry.get("url")
                or entry.get("webpage_url")
                or f"https://www.youtube.com/watch?v={video_id}"
            )
            if video_url.startswith("/"):
                video_url = f"https://www.youtube.com{video_url}"

            if video_idx > 0:
                await asyncio.sleep(request_delay_s)

            # ── Phase 2: Full metadata ─────────────────────────────────
            try:
                full_info = await loop.run_in_executor(
                    None, functools.partial(_extract_sync, detail_opts, video_url)
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("youtube_long_detail_failed",
                            video_id=video_id, error=str(exc)[:120])
                continue

            if not full_info:
                continue

            # Duration recheck (Phase 2 has accurate value).
            real_duration = full_info.get("duration") or 0
            if real_duration > 0 and real_duration < min_duration_s:
                log.debug("youtube_long_skip_too_short_phase2",
                          video_id=video_id, duration=real_duration)
                continue
            if real_duration > max_duration_s and real_duration > 0:
                log.debug("youtube_long_skip_too_long_phase2",
                          video_id=video_id, duration=real_duration)
                continue

            # Date freshness filter.
            upload_date = full_info.get("upload_date") or ""
            if cutoff_date and upload_date and upload_date < cutoff_date:
                log.debug("youtube_long_skip_old",
                          video_id=video_id, upload_date=upload_date)
                continue

            title        = (full_info.get("title") or "").strip()
            channel_name = (full_info.get("channel") or full_info.get("uploader") or "")
            thumbnail    = full_info.get("thumbnail") or ""
            video_url_final = (
                full_info.get("webpage_url")
                or f"https://www.youtube.com/watch?v={video_id}"
            )

            # ── Phase 3: Download subtitle via yt-dlp ─────────────────
            # Uses the same yt-dlp session (cookiefile/proxy already in
            # detail_opts) — avoids the separate timedtext 429 rate-limit
            # that hits youtube-transcript-api's independent HTTP session.
            entries_raw = await loop.run_in_executor(
                None,
                functools.partial(
                    _download_subtitles_sync,
                    detail_opts, video_url_final, video_id, subtitle_lang, tmp_dir,
                ),
            )

            if not entries_raw:
                log.warning("youtube_long_no_transcript",
                            video_id=video_id, title=title[:60])
                continue

            # ── Phase 4: Segment transcript ────────────────────────────
            segments = _segment_transcript(entries_raw, segment_duration_s)
            if not segments:
                log.warning("youtube_long_empty_segments",
                            video_id=video_id, title=title[:60])
                continue

            total_segments = len(segments)
            for seg_idx, seg in enumerate(segments):
                start_s  = int(seg["start_s"])
                end_s    = int(seg["end_s"])
                seg_url  = f"{video_url_final}&t={start_s}s"

                all_items.append(HarvestedItem(
                    source_url=seg_url,
                    title=title,
                    content=seg["text"],
                    locale=locale,
                    media_urls=[thumbnail] if thumbnail else [],
                    metadata={
                        "platform":       "YouTube",
                        "video_id":       video_id,
                        "channel":        channel_name,
                        "duration_s":     real_duration,
                        "view_count":     full_info.get("view_count"),
                        "like_count":     full_info.get("like_count"),
                        "upload_date":    upload_date,
                        "tags":           full_info.get("tags") or [],
                        "segment_index":  seg_idx,
                        "total_segments": total_segments,
                        "start_s":        start_s,
                        "end_s":          end_s,
                        "transcript_lang": subtitle_lang,
                        "video_title":    title,
                    },
                ))

            log.info(
                "youtube_long_video_ok",
                video_id=video_id,
                title=title[:60],
                segments=total_segments,
                duration_s=real_duration,
            )

        # Clean up temp dir (any leftover files from failed downloads).
        try:
            import shutil  # noqa: PLC0415
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:  # noqa: BLE001
            pass

        log.info("youtube_long_extracted",
                 videos=len(candidates), total_segments=len(all_items))
        return all_items
