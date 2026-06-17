# n-assistant-core (MIT, open-source) — FastAPI service
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/root/.cache/huggingface

WORKDIR /app

# build-essential + zlib1g-dev: compile zlib-state (C ext, dep of ir-datasets → FlagEmbedding).
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

# NOTE: torch trên Linux aarch64 (Docker trên Mac Apple Silicon) kéo theo ~2.5GB CUDA libs.
# Không thể tách ra vì torch._C.cpython-311.so hard-link libcudart + libcudnn tại import time.
# Image ~9.7GB là chi phí cố định — build 1 lần, pip layer được cache, không rebuild lại trừ
# khi requirements.txt thay đổi.
RUN pip install --upgrade pip && pip install -r requirements.txt

# Application code
COPY app ./app

# Tests baked in — CI chạy `pytest` không cần volume mount.
# Local dev: `-v ./tests:/app/tests` để override.
COPY tests ./tests

# Config and CLI
COPY config ./config
COPY cli.py ./

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
