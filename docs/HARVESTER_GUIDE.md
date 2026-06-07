# Harvester Guide — Phase 1: Data Acquisition Engine

> **Scope:** This guide covers **only Phase 1 (Harvester)**. RAG, Qdrant, agents, and publishing are out of scope.
>
> 🌐 **English** · 🇻🇳 [Tiếng Việt](./HARVESTER_GUIDE.vi.md)

---

## Table of Contents

1. [Project structure](#1-project-structure)
2. [What the Harvester does](#2-what-the-harvester-does)
3. [Plugin Architecture](#3-plugin-architecture)
4. [Unified CLI Reference (Docker)](#4-unified-cli-reference-docker)
5. [How to add a new Plugin](#5-how-to-add-a-new-plugin)
6. [How to configure a source](#6-how-to-configure-a-source)
7. [The 3-layer filter pipeline](#7-the-3-layer-filter-pipeline)
8. [Raw Data Lake layout](#8-raw-data-lake-layout)
9. [Engineering rules](#9-engineering-rules)

---

## 1. Project structure

```
n-assistant-core/
│
├── cli.py                           ← Single entry point for all harvest ops (runs inside Docker)
├── nassistant.sh / nassistant.ps1   ← Docker CLI wrapper (Linux·macOS / Windows)
│
├── config/                          ← All configuration (tracked except cookies)
│   ├── scraper_config.yaml          ← Source registry + filter thresholds
│   ├── yt_cookies.txt               ← YouTube session cookies (gitignored)
│   └── yt_cookies.txt.example       ← Placeholder for fresh clones
│
├── docs/
│   ├── HARVESTER_GUIDE.md           ← This guide (English)
│   └── HARVESTER_GUIDE.vi.md        ← Vietnamese version
│
├── app/
│   ├── core/
│   │   └── config.py                ← Settings (HARVESTER_CONFIG_PATH points here)
│   ├── application/
│   │   └── services/
│   │       ├── filter_pipeline.py   ← Unified 3-layer filter (all source types)
│   │       └── llm_evaluator.py     ← Layer 3: LLM judge
│   └── infrastructure/
│       └── harvester/
│           ├── engine.py            ← Orchestrator: discovers + runs plugins
│           ├── models.py            ← SourceConfig, HarvestedItem, RawEnvelope
│           ├── extractors/
│           │   ├── base.py          ← BaseExtractor contract
│           │   └── plugins/         ← Drop zone: one file = one source type
│           │       ├── x_twscrape.py
│           │       ├── youtube_shorts.py
│           │       └── youtube_long.py
│           └── filters/             ← Layer 1 + 2 per source type (CPU-only)
│               ├── x_heuristic.py        ← L1 for X/Twitter
│               ├── x_text_cleaner.py     ← L2 for X/Twitter
│               ├── yt_shorts_heuristic.py ← L1 for YouTube Shorts
│               ├── yt_long_heuristic.py  ← L1 for YouTube Long
│               └── yt_text_cleaner.py    ← L2 for both YouTube types
│
└── raw_data_lake/
    ├── texts/<tenant>/<plugin_type>/  ← Raw envelopes (immutable)
    └── filtered/                      ← Approved items after filter pipeline
```

**Naming convention for filter files:** `<source>_<layer>.py`
- Source prefixes: `x_`, `yt_shorts_`, `yt_long_`
- Layer suffixes: `_heuristic` (Layer 1), `_text_cleaner` (Layer 2)

---

## 2. What the Harvester does

```
┌──────────────────────────────────────────────────────────────┐
│                      PHASE 1: HARVESTER                      │
│                                                              │
│  config/scraper_config.yaml                                  │
│       │                                                      │
│       ▼                                                      │
│  HarvesterEngine ────── auto-discovers plugins               │
│       │                                                      │
│       ├── [x_twscrape plugin]   ──► raw JSON envelopes       │
│       ├── [youtube_long plugin] ──► raw JSON envelopes       │
│       └── [your plugin here]   ──► raw JSON envelopes        │
│                                          │                   │
│                                          ▼                   │
│                                   raw_data_lake/             │
│                                   texts/<tenant>/            │
│                                          │                   │
│                                          ▼                   │
│                               filter_pipeline.py             │
│                               L1: heuristic (O(1) CPU)       │
│                               L2: text clean (O(n) CPU)      │
│                               L3: LLM judge  (async)         │
│                                          │                   │
│                                          ▼                   │
│                               filtered/approved.json         │
│                               (Qdrant-ready — Phase 2)       │
└──────────────────────────────────────────────────────────────┘
```

**Key design decisions:**
- The Harvester layer **never calls an LLM**. Data acquisition ≠ inference.
- One crashing plugin never stops the rest. Each source runs in isolated `try/except`.
- Every artifact is stamped with `tenant_id`. A source without `tenant_id` is silently discarded.
- All scraping targets live in `config/scraper_config.yaml` — never hardcoded in Python.

---

## 3. Plugin Architecture

The engine auto-discovers every file under `extractors/plugins/` at startup using `pkgutil`. Adding a source = dropping one file. No core edits, no import registration.

### The contract (`BaseExtractor`)

```python
# app/infrastructure/harvester/extractors/plugins/my_platform.py

from app.infrastructure.harvester.extractors.base import BaseExtractor
from app.infrastructure.harvester.models import HarvestedItem

class MyPlatformExtractor(BaseExtractor):
    PLUGIN_TYPE = "my_platform"      # unique; referenced by type: in scraper_config.yaml

    async def extract(self) -> list[HarvestedItem]:
        url   = self.options["url"]  # always from self.options — never hardcode
        limit = self.options.get("limit", 20)
        # ... fetch logic ...
        return [HarvestedItem(source_url=url, content="...")]
```

**Rules every plugin must follow:**

| Rule | Reason |
|---|---|
| Set a unique `PLUGIN_TYPE` string | Engine uses this as the registry key |
| Return `list[HarvestedItem]` | Uniform output contract |
| Read everything from `self.options` | Zero-hardcode rule — URLs/keys live in YAML |
| Never call an LLM | Harvester layer is inference-free |
| Raise on failure | Engine catches per-source; other sources keep running |

---

## 4. Unified CLI Reference (Docker)

All operations go through a single entry point — `cli.py` — run **inside Docker**, so you never need a local Python install or a venv. A thin wrapper script execs `cli.py` inside the `harvester` container (the only image that ships it):

```bash
# Run from the repo root:
./nassistant.sh <command> [options]      # Linux / macOS
.\nassistant.ps1 <command> [options]     # Windows / PowerShell

./nassistant.sh --help                   # all commands
./nassistant.sh <command> --help         # options for one command
```

The wrapper is just a one-liner around `docker compose run`. The raw form (if you prefer no wrapper) is:

```bash
docker compose --profile harvester run --rm harvester python cli.py <command> [options]
```

> First run builds the harvester image automatically. Subsequent runs reuse it.
> The examples below use `./nassistant.sh`; swap in `.\nassistant.ps1` on Windows.

### `list-plugins`

Show every registered plugin and the on/off status of each configured source.

```bash
./nassistant.sh list-plugins           # registry + config status
./nassistant.sh list-plugins --verbose # + option details (secrets masked)
```

### `harvest`

Fetch raw data from enabled sources into the Raw Data Lake.

```bash
# Run all enabled sources
./nassistant.sh harvest

# Preview matching sources without fetching
./nassistant.sh harvest --dry-run

# Run one source by name (defined in config/scraper_config.yaml)
./nassistant.sh harvest --source yt-long-matt-wolfe

# Run all sources of one plugin type
./nassistant.sh harvest --type youtube_long

# Override the items limit for all matched sources
./nassistant.sh harvest --type youtube_long --limit 5

# Skip the TTL cleanup step
./nassistant.sh harvest --no-cleanup
```

| Option | Short | Description |
|---|---|---|
| `--source NAME` | `-s` | Source name from `config/scraper_config.yaml` |
| `--type TYPE` | `-t` | Plugin type: `x_twscrape`, `youtube_long`, `youtube_shorts` |
| `--limit N` | `-l` | Override items limit |
| `--no-cleanup` | | Skip Raw Data Lake TTL cleanup |
| `--dry-run` | | Print matched sources without fetching |

### `filter`

Run the 3-layer anti-spam filter pipeline over harvested raw data.

```bash
./nassistant.sh filter                        # all source types
./nassistant.sh filter --type youtube_long
./nassistant.sh filter --type youtube_shorts
./nassistant.sh filter --type x_twscrape
```

| Source type | Output file |
|---|---|
| `x_twscrape` | `raw_data_lake/filtered/approved.json` |
| `youtube_shorts` | `raw_data_lake/filtered/yt_approved.json` |
| `youtube_long` | `raw_data_lake/filtered/yt_long_approved.json` |

---

## 5. How to add a new Plugin

**Time to ship a new source: ~30 minutes. No engine changes needed.**

### Step 1 — Create the plugin file

```python
# app/infrastructure/harvester/extractors/plugins/reddit.py
from __future__ import annotations

import httpx
from app.infrastructure.harvester.extractors.base import BaseExtractor
from app.infrastructure.harvester.models import HarvestedItem


class RedditExtractor(BaseExtractor):
    PLUGIN_TYPE = "reddit"

    async def extract(self) -> list[HarvestedItem]:
        subreddit = self.options["subreddit"]
        limit     = self.options.get("limit", 25)
        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers={"User-Agent": "n-assistant-core/1.0"})
            resp.raise_for_status()
            posts = resp.json()["data"]["children"]

        return [
            HarvestedItem(
                source_url=f"https://reddit.com{p['data']['permalink']}",
                title=p["data"]["title"],
                content=p["data"]["selftext"] or p["data"]["title"],
                metadata={"score": p["data"]["score"]},
            )
            for p in posts
        ]
```

### Step 2 — Register in `config/scraper_config.yaml`

```yaml
sources:
  - name: reddit-ai-news
    type: reddit           # ← matches PLUGIN_TYPE exactly
    tenant_id: tenant_demo
    enabled: true
    options:
      subreddit: artificial
      limit: 30
```

### Step 3 — (Optional) Add a heuristic filter

```python
# app/infrastructure/harvester/filters/reddit_heuristic.py
def is_viable_post(text: str, config: dict) -> bool:
    min_words = int(config.get("min_words", 20))
    return bool(text) and len(text.split()) >= min_words
```

Then register it as a strategy in `filter_pipeline.py`:

```python
from app.infrastructure.harvester.filters.reddit_heuristic import is_viable_post

_STRATEGIES["reddit"] = _FilterStrategy(
    config_section="reddit_heuristic",
    l1_fn=is_viable_post,
    l2_fn=clean_noise,          # reuse X cleaner or write a custom one
    l1_pass_title=False,
    l2_fallback_to_title=False,
    initial_delay=0.0,
    batch_delay=2.0,
    format_llm=_x_format,       # or write a custom formatter
)
```

Add the output path to `cli.py`:

```python
_FILTER_OUTPUTS["reddit"] = Path("raw_data_lake/filtered/reddit_approved.json")
```

### Step 4 — Verify (via Docker)

```bash
# A code change means a rebuild — pass --build once so the image picks up the new plugin:
docker compose --profile harvester run --rm --build harvester python cli.py list-plugins
# ✓  reddit    RedditExtractor    (1 configured)

# Then the wrapper reuses the freshly built image:
./nassistant.sh harvest --source reddit-ai-news --dry-run
./nassistant.sh harvest --source reddit-ai-news
./nassistant.sh filter --type reddit
```

> **Why `--build`?** The harvester image bakes in `app/` and `cli.py` at build time. The
> wrapper does **not** rebuild on every run, so after editing Python code, rebuild once
> with `--build` (or `docker compose --profile harvester build harvester`).
> `config/scraper_config.yaml` and `raw_data_lake/` are bind-mounted, so YAML/data edits
> need **no** rebuild.

---

## 6. How to configure a source

All sources live in `config/scraper_config.yaml`. Each entry:

```yaml
sources:
  - name: my-source-name     # unique ID (used with --source flag)
    type: plugin_type        # must match BaseExtractor.PLUGIN_TYPE
    tenant_id: tenant_demo   # MANDATORY — missing → source discarded silently
    enabled: true            # toggle without deleting the entry
    options:                 # free-form bag passed verbatim to the plugin
      any_key: any_value
      secret: "${MY_ENV_VAR}"  # ${VAR} → resolved from .env at load time
```

**Secrets:** use `${VAR_NAME}` in `options`. Expanded from environment at runtime.

**Cookies:** put `yt_cookies.txt` in `config/` and set `YT_COOKIES_FILE=/app/config/yt_cookies.txt` in `.env`.

Because `config/scraper_config.yaml` is bind-mounted into the container, edits take effect on the **next** `./nassistant.sh` run — no rebuild needed.

---

## 7. The 3-layer filter pipeline

All source types share one parametrised pipeline (`filter_pipeline.py`). The variation per source type is encapsulated in `_FilterStrategy`:

```
raw item
   │
   ▼
┌──────────────────────────────────────────┐
│  Layer 1 — Heuristic  (O(1) CPU, ~2 ms) │
│  Source-specific gate function           │
│  Thresholds from config/scraper_config   │
└──────────────────────────────────────────┘
   │ fail → discard (free)
   ▼ pass
┌──────────────────────────────────────────┐
│  Layer 2 — Text Clean  (O(n) CPU)        │
│  Source-specific cleaner function        │
└──────────────────────────────────────────┘
   │ fail → discard (free)
   ▼ pass
┌──────────────────────────────────────────┐
│  Layer 3 — LLM Judge  (async, ~300 ms)   │
│  Shared: batch_is_high_quality()         │
│  Text formatted per source type          │
└──────────────────────────────────────────┘
   │ fail → discard
   ▼ pass
approved.json  (Qdrant-ready — Phase 2)
```

**Thresholds live in `config/scraper_config.yaml`:**

```yaml
filter_config:
  heuristic:
    max_hashtags: 3
    min_words: 15
    max_mentions: 2
  youtube_shorts_heuristic:
    min_transcript_words: 10
  youtube_long_heuristic:
    min_segment_words: 40
```

**Layer 3 needs an LLM endpoint** (set in `.env`):

```bash
INFERENCE_PROVIDER=openai
INFERENCE_BASE_URL=https://api.openai.com/v1
INFERENCE_MODEL=gpt-4o-mini
INFERENCE_API_KEY=sk-...
```

Layers 1 and 2 are CPU-only — no key needed.

---

## 8. Raw Data Lake layout

```
raw_data_lake/
├── texts/
│   └── <tenant_id>/
│       └── <plugin_type>/
│           └── <harvest_id>.json   ← RawEnvelope (immutable)
└── filtered/
    ├── approved.json               ← x_twscrape approved
    ├── yt_approved.json            ← youtube_shorts approved
    └── yt_long_approved.json       ← youtube_long approved
```

`raw_data_lake/` is bind-mounted, so everything the container writes lands on your host for inspection.

---

## 9. Engineering rules

| Rule | What it means |
|---|---|
| **Inference-free Harvester** | No LLM calls inside `BaseExtractor.extract()` or `HarvesterEngine`. |
| **Zero-hardcode** | URLs, selectors, limits, thresholds → `config/scraper_config.yaml`. Never in Python. |
| **`tenant_id` mandatory** | Every source must declare `tenant_id`. Missing = discarded. No exceptions. |
| **Public pages only** | Scrape only pages accessible without login. Respect `robots.txt` and ToS. |
| **Plugin isolation** | One crashing plugin must not affect others. Let exceptions propagate to the engine. |
| **Secrets in env** | Use `${VAR}` in YAML → resolved from `.env`. Never commit real tokens or cookies. |
| **Single CLI entry point** | All operations go through `cli.py`, run inside Docker via `./nassistant.sh`. No `run_*.py` scripts. |
