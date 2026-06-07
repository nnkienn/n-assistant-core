# Hướng dẫn Harvester — Chặng 1: Động cơ Thu thập Dữ liệu

> **Phạm vi:** Hướng dẫn này chỉ nói về **Chặng 1 (Harvester)**. RAG, Qdrant, agent và phần xuất bản nằm ngoài phạm vi.
>
> 🌐 [English](./HARVESTER_GUIDE.md) · 🇻🇳 **Tiếng Việt**

---

## Mục lục

1. [Cấu trúc dự án](#1-cấu-trúc-dự-án)
2. [Harvester làm gì](#2-harvester-làm-gì)
3. [Kiến trúc Plugin](#3-kiến-trúc-plugin)
4. [Tham chiếu CLI thống nhất (Docker)](#4-tham-chiếu-cli-thống-nhất-docker)
5. [Cách thêm một Plugin mới](#5-cách-thêm-một-plugin-mới)
6. [Cách cấu hình một nguồn](#6-cách-cấu-hình-một-nguồn)
7. [Pipeline lọc 3 lớp](#7-pipeline-lọc-3-lớp)
8. [Bố cục Raw Data Lake](#8-bố-cục-raw-data-lake)
9. [Quy tắc kỹ thuật](#9-quy-tắc-kỹ-thuật)

---

## 1. Cấu trúc dự án

```
n-assistant-core/
│
├── cli.py                           ← Điểm vào duy nhất cho mọi thao tác cào (chạy trong Docker)
├── nassistant.sh / nassistant.ps1   ← Wrapper CLI bằng Docker (Linux·macOS / Windows)
│
├── config/                          ← Toàn bộ cấu hình (được track, trừ cookie)
│   ├── scraper_config.yaml          ← Sổ đăng ký nguồn + ngưỡng lọc
│   ├── yt_cookies.txt               ← Cookie phiên YouTube (gitignore)
│   └── yt_cookies.txt.example       ← File mẫu cho bản clone mới
│
├── docs/
│   ├── HARVESTER_GUIDE.md           ← Hướng dẫn này (bản tiếng Anh)
│   └── HARVESTER_GUIDE.vi.md        ← Bản tiếng Việt
│
├── app/
│   ├── core/
│   │   └── config.py                ← Settings (HARVESTER_CONFIG_PATH trỏ vào đây)
│   ├── application/
│   │   └── services/
│   │       ├── filter_pipeline.py   ← Bộ lọc 3 lớp thống nhất (mọi loại nguồn)
│   │       └── llm_evaluator.py     ← Lớp 3: LLM judge
│   └── infrastructure/
│       └── harvester/
│           ├── engine.py            ← Bộ điều phối: phát hiện + chạy plugin
│           ├── models.py            ← SourceConfig, HarvestedItem, RawEnvelope
│           ├── extractors/
│           │   ├── base.py          ← Hợp đồng BaseExtractor
│           │   └── plugins/         ← Vùng thả: một file = một loại nguồn
│           │       ├── x_twscrape.py
│           │       ├── youtube_shorts.py
│           │       └── youtube_long.py
│           └── filters/             ← Lớp 1 + 2 cho từng loại nguồn (chỉ CPU)
│               ├── x_heuristic.py        ← L1 cho X/Twitter
│               ├── x_text_cleaner.py     ← L2 cho X/Twitter
│               ├── yt_shorts_heuristic.py ← L1 cho YouTube Shorts
│               ├── yt_long_heuristic.py  ← L1 cho YouTube Long
│               └── yt_text_cleaner.py    ← L2 cho cả hai loại YouTube
│
└── raw_data_lake/
    ├── texts/<tenant>/<plugin_type>/  ← Phong bì dữ liệu thô (bất biến)
    └── filtered/                      ← Item được duyệt sau pipeline lọc
```

**Quy ước đặt tên file filter:** `<nguồn>_<lớp>.py`
- Tiền tố nguồn: `x_`, `yt_shorts_`, `yt_long_`
- Hậu tố lớp: `_heuristic` (Lớp 1), `_text_cleaner` (Lớp 2)

---

## 2. Harvester làm gì

```
┌──────────────────────────────────────────────────────────────┐
│                      CHẶNG 1: HARVESTER                      │
│                                                              │
│  config/scraper_config.yaml                                  │
│       │                                                      │
│       ▼                                                      │
│  HarvesterEngine ────── tự phát hiện plugin                  │
│       │                                                      │
│       ├── [plugin x_twscrape]   ──► phong bì JSON thô        │
│       ├── [plugin youtube_long] ──► phong bì JSON thô        │
│       └── [plugin của bạn]      ──► phong bì JSON thô        │
│                                          │                   │
│                                          ▼                   │
│                                   raw_data_lake/             │
│                                   texts/<tenant>/            │
│                                          │                   │
│                                          ▼                   │
│                               filter_pipeline.py             │
│                               L1: heuristic (O(1) CPU)       │
│                               L2: làm sạch text (O(n) CPU)   │
│                               L3: LLM judge  (async)         │
│                                          │                   │
│                                          ▼                   │
│                               filtered/approved.json         │
│                               (sẵn sàng cho Qdrant — Chặng 2)│
└──────────────────────────────────────────────────────────────┘
```

**Các quyết định thiết kế cốt lõi:**
- Tầng Harvester **không bao giờ gọi LLM**. Thu thập dữ liệu ≠ suy luận.
- Một plugin lỗi không bao giờ làm dừng phần còn lại. Mỗi nguồn chạy trong `try/except` cô lập.
- Mọi artifact đều được đóng dấu `tenant_id`. Nguồn thiếu `tenant_id` sẽ bị âm thầm loại bỏ.
- Mọi mục tiêu cào nằm trong `config/scraper_config.yaml` — không bao giờ hardcode trong Python.

---

## 3. Kiến trúc Plugin

Engine tự phát hiện mọi file trong `extractors/plugins/` lúc khởi động bằng `pkgutil`. Thêm một nguồn = thả một file. Không sửa code lõi, không cần đăng ký import.

### Hợp đồng (`BaseExtractor`)

```python
# app/infrastructure/harvester/extractors/plugins/my_platform.py

from app.infrastructure.harvester.extractors.base import BaseExtractor
from app.infrastructure.harvester.models import HarvestedItem

class MyPlatformExtractor(BaseExtractor):
    PLUGIN_TYPE = "my_platform"      # duy nhất; được tham chiếu qua type: trong scraper_config.yaml

    async def extract(self) -> list[HarvestedItem]:
        url   = self.options["url"]  # luôn lấy từ self.options — không bao giờ hardcode
        limit = self.options.get("limit", 20)
        # ... logic fetch ...
        return [HarvestedItem(source_url=url, content="...")]
```

**Quy tắc mọi plugin phải tuân theo:**

| Quy tắc | Lý do |
|---|---|
| Đặt chuỗi `PLUGIN_TYPE` duy nhất | Engine dùng nó làm khoá registry |
| Trả về `list[HarvestedItem]` | Hợp đồng đầu ra đồng nhất |
| Đọc mọi thứ từ `self.options` | Quy tắc zero-hardcode — URL/key nằm trong YAML |
| Không bao giờ gọi LLM | Tầng Harvester không suy luận |
| Ném lỗi khi thất bại | Engine bắt lỗi theo từng nguồn; các nguồn khác vẫn chạy |

---

## 4. Tham chiếu CLI thống nhất (Docker)

Mọi thao tác đi qua một điểm vào duy nhất — `cli.py` — chạy **bên trong Docker**, nên bạn không cần cài Python local hay tạo venv. Một script wrapper mỏng exec `cli.py` bên trong container `harvester` (image duy nhất ship file này):

```bash
# Chạy từ thư mục gốc của repo:
./nassistant.sh <lệnh> [tuỳ chọn]        # Linux / macOS
.\nassistant.ps1 <lệnh> [tuỳ chọn]       # Windows / PowerShell

./nassistant.sh --help                   # tất cả lệnh
./nassistant.sh <lệnh> --help            # tuỳ chọn của một lệnh
```

Wrapper chỉ là một dòng bọc quanh `docker compose run`. Dạng thuần (nếu bạn không muốn dùng wrapper):

```bash
docker compose --profile harvester run --rm harvester python cli.py <lệnh> [tuỳ chọn]
```

> Lần chạy đầu sẽ tự build image harvester. Các lần sau dùng lại image đó.
> Các ví dụ bên dưới dùng `./nassistant.sh`; trên Windows thay bằng `.\nassistant.ps1`.

### `list-plugins`

Hiển thị mọi plugin đã đăng ký và trạng thái bật/tắt của từng nguồn đã cấu hình.

```bash
./nassistant.sh list-plugins           # registry + trạng thái config
./nassistant.sh list-plugins --verbose # + chi tiết tuỳ chọn (che secret)
```

### `harvest`

Cào dữ liệu thô từ các nguồn đang bật vào Raw Data Lake.

```bash
# Chạy mọi nguồn đang bật
./nassistant.sh harvest

# Xem trước các nguồn khớp mà không cào
./nassistant.sh harvest --dry-run

# Chạy một nguồn theo tên (định nghĩa trong config/scraper_config.yaml)
./nassistant.sh harvest --source yt-long-matt-wolfe

# Chạy mọi nguồn của một loại plugin
./nassistant.sh harvest --type youtube_long

# Ghi đè giới hạn item cho tất cả nguồn khớp
./nassistant.sh harvest --type youtube_long --limit 5

# Bỏ qua bước dọn dẹp theo TTL
./nassistant.sh harvest --no-cleanup
```

| Tuỳ chọn | Viết tắt | Mô tả |
|---|---|---|
| `--source NAME` | `-s` | Tên nguồn trong `config/scraper_config.yaml` |
| `--type TYPE` | `-t` | Loại plugin: `x_twscrape`, `youtube_long`, `youtube_shorts` |
| `--limit N` | `-l` | Ghi đè giới hạn item |
| `--no-cleanup` | | Bỏ qua dọn dẹp TTL của Raw Data Lake |
| `--dry-run` | | In các nguồn khớp mà không cào |

### `filter`

Chạy pipeline lọc chống spam 3 lớp trên dữ liệu thô đã cào.

```bash
./nassistant.sh filter                        # mọi loại nguồn
./nassistant.sh filter --type youtube_long
./nassistant.sh filter --type youtube_shorts
./nassistant.sh filter --type x_twscrape
```

| Loại nguồn | File đầu ra |
|---|---|
| `x_twscrape` | `raw_data_lake/filtered/approved.json` |
| `youtube_shorts` | `raw_data_lake/filtered/yt_approved.json` |
| `youtube_long` | `raw_data_lake/filtered/yt_long_approved.json` |

---

## 5. Cách thêm một Plugin mới

**Thời gian để ra một nguồn mới: ~30 phút. Không cần sửa engine.**

### Bước 1 — Tạo file plugin

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

### Bước 2 — Đăng ký trong `config/scraper_config.yaml`

```yaml
sources:
  - name: reddit-ai-news
    type: reddit           # ← khớp chính xác PLUGIN_TYPE
    tenant_id: tenant_demo
    enabled: true
    options:
      subreddit: artificial
      limit: 30
```

### Bước 3 — (Tuỳ chọn) Thêm bộ lọc heuristic

```python
# app/infrastructure/harvester/filters/reddit_heuristic.py
def is_viable_post(text: str, config: dict) -> bool:
    min_words = int(config.get("min_words", 20))
    return bool(text) and len(text.split()) >= min_words
```

Sau đó đăng ký nó như một strategy trong `filter_pipeline.py`:

```python
from app.infrastructure.harvester.filters.reddit_heuristic import is_viable_post

_STRATEGIES["reddit"] = _FilterStrategy(
    config_section="reddit_heuristic",
    l1_fn=is_viable_post,
    l2_fn=clean_noise,          # dùng lại cleaner của X hoặc viết riêng
    l1_pass_title=False,
    l2_fallback_to_title=False,
    initial_delay=0.0,
    batch_delay=2.0,
    format_llm=_x_format,       # hoặc viết formatter riêng
)
```

Thêm đường dẫn đầu ra vào `cli.py`:

```python
_FILTER_OUTPUTS["reddit"] = Path("raw_data_lake/filtered/reddit_approved.json")
```

### Bước 4 — Kiểm chứng (qua Docker)

```bash
# Sửa code = phải build lại — truyền --build một lần để image nhận plugin mới:
docker compose --profile harvester run --rm --build harvester python cli.py list-plugins
# ✓  reddit    RedditExtractor    (1 configured)

# Sau đó wrapper dùng lại image vừa build:
./nassistant.sh harvest --source reddit-ai-news --dry-run
./nassistant.sh harvest --source reddit-ai-news
./nassistant.sh filter --type reddit
```

> **Tại sao cần `--build`?** Image harvester nướng sẵn `app/` và `cli.py` lúc build. Wrapper
> **không** build lại mỗi lần chạy, nên sau khi sửa code Python, hãy build lại một lần với
> `--build` (hoặc `docker compose --profile harvester build harvester`).
> Còn `config/scraper_config.yaml` và `raw_data_lake/` được bind-mount, nên sửa YAML/dữ liệu
> **không** cần build lại.

---

## 6. Cách cấu hình một nguồn

Mọi nguồn nằm trong `config/scraper_config.yaml`. Mỗi mục:

```yaml
sources:
  - name: my-source-name     # ID duy nhất (dùng với cờ --source)
    type: plugin_type        # phải khớp BaseExtractor.PLUGIN_TYPE
    tenant_id: tenant_demo   # BẮT BUỘC — thiếu → nguồn bị loại âm thầm
    enabled: true            # bật/tắt mà không cần xoá mục
    options:                 # túi tự do, truyền nguyên văn cho plugin
      any_key: any_value
      secret: "${MY_ENV_VAR}"  # ${VAR} → giải từ .env lúc load
```

**Secret:** dùng `${VAR_NAME}` trong `options`. Được giải từ biến môi trường lúc runtime.

**Cookie:** đặt `yt_cookies.txt` trong `config/` và set `YT_COOKIES_FILE=/app/config/yt_cookies.txt` trong `.env`.

Vì `config/scraper_config.yaml` được bind-mount vào container, thay đổi sẽ có hiệu lực ở lần chạy `./nassistant.sh` **kế tiếp** — không cần build lại.

---

## 7. Pipeline lọc 3 lớp

Mọi loại nguồn dùng chung một pipeline tham số hoá (`filter_pipeline.py`). Khác biệt theo từng loại nguồn được gói trong `_FilterStrategy`:

```
item thô
   │
   ▼
┌──────────────────────────────────────────┐
│  Lớp 1 — Heuristic  (O(1) CPU, ~2 ms)   │
│  Hàm cổng riêng theo nguồn               │
│  Ngưỡng lấy từ config/scraper_config     │
└──────────────────────────────────────────┘
   │ trượt → loại (miễn phí)
   ▼ đạt
┌──────────────────────────────────────────┐
│  Lớp 2 — Làm sạch text  (O(n) CPU)       │
│  Hàm cleaner riêng theo nguồn            │
└──────────────────────────────────────────┘
   │ trượt → loại (miễn phí)
   ▼ đạt
┌──────────────────────────────────────────┐
│  Lớp 3 — LLM Judge  (async, ~300 ms)     │
│  Dùng chung: batch_is_high_quality()     │
│  Text được format theo từng loại nguồn   │
└──────────────────────────────────────────┘
   │ trượt → loại
   ▼ đạt
approved.json  (sẵn sàng cho Qdrant — Chặng 2)
```

**Ngưỡng nằm trong `config/scraper_config.yaml`:**

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

**Lớp 3 cần một endpoint LLM** (đặt trong `.env`):

```bash
INFERENCE_PROVIDER=openai
INFERENCE_BASE_URL=https://api.openai.com/v1
INFERENCE_MODEL=gpt-4o-mini
INFERENCE_API_KEY=sk-...
```

Lớp 1 và 2 chỉ dùng CPU — không cần key.

---

## 8. Bố cục Raw Data Lake

```
raw_data_lake/
├── texts/
│   └── <tenant_id>/
│       └── <plugin_type>/
│           └── <harvest_id>.json   ← RawEnvelope (bất biến)
└── filtered/
    ├── approved.json               ← x_twscrape đã duyệt
    ├── yt_approved.json            ← youtube_shorts đã duyệt
    └── yt_long_approved.json       ← youtube_long đã duyệt
```

`raw_data_lake/` được bind-mount, nên mọi thứ container ghi ra đều nằm trên máy host của bạn để kiểm tra.

---

## 9. Quy tắc kỹ thuật

| Quy tắc | Nghĩa là gì |
|---|---|
| **Harvester không suy luận** | Không gọi LLM trong `BaseExtractor.extract()` hay `HarvesterEngine`. |
| **Zero-hardcode** | URL, selector, limit, ngưỡng → `config/scraper_config.yaml`. Không bao giờ trong Python. |
| **`tenant_id` bắt buộc** | Mọi nguồn phải khai báo `tenant_id`. Thiếu = bị loại. Không ngoại lệ. |
| **Chỉ trang công khai** | Chỉ cào trang truy cập được mà không cần đăng nhập. Tôn trọng `robots.txt` và ToS. |
| **Cô lập plugin** | Một plugin lỗi không được ảnh hưởng plugin khác. Để exception lan tới engine. |
| **Secret trong env** | Dùng `${VAR}` trong YAML → giải từ `.env`. Không bao giờ commit token/cookie thật. |
| **Một điểm vào CLI duy nhất** | Mọi thao tác đi qua `cli.py`, chạy trong Docker bằng `./nassistant.sh`. Không có script `run_*.py`. |
