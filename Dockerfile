# n-assistant-core (MIT, open-source) — FastAPI service
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/root/.cache/huggingface

WORKDIR /app

# build-essential + zlib1g-dev: required to compile zlib-state (C extension, dep of ir-datasets → FlagEmbedding).
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

# ── WHY --no-deps for torch ──────────────────────────────────────────────────
# On Linux, torch pulls cuda-toolkit which drags in ~2.5GB of NVIDIA libs
# (cublas 542MB, cudnn 444MB, triton 188MB, nccl 206MB, ...) — completely
# useless inside Docker on Mac (no GPU, no MPS in Linux VM).
#
# Strategy:
#   1. Install torch --no-deps → wheel only, NO cuda-toolkit pulled.
#   2. Manually install torch's pure-python deps not covered by other packages.
#   3. Install -r requirements.txt: FlagEmbedding sees torch already present
#      → pip skips reinstall → cuda-toolkit never triggered.
#
# Result: image ~4GB instead of ~10GB.
RUN pip install --upgrade pip && \
    pip install torch --no-deps && \
    pip install "sympy>=1.13" "networkx>=2.5" "jinja2>=3.1" "mpmath>=1.1"

RUN pip install -r requirements.txt

# Application code
COPY app ./app

# Tests baked in so CI can run `pytest` without volume mounts.
# In local dev, mount overrides this: `-v ./tests:/app/tests`
COPY tests ./tests

# Config (source registry + filter thresholds) and the unified CLI entry point
COPY config ./config
COPY cli.py ./

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
