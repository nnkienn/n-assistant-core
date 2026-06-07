#!/usr/bin/env pwsh
# ═══════════════════════════════════════════════════════════════════════════
# N-Assistant CLI — Docker wrapper (Windows / PowerShell)
#
# Runs cli.py *inside* the harvester container, so you never need a local
# Python install or a venv. Everything (deps, scrapers, the 3-layer filter)
# ships in the Dockerfile.harvester image.
#
#   .\nassistant.ps1 list-plugins
#   .\nassistant.ps1 harvest --source yt-long-matt-wolfe --dry-run
#   .\nassistant.ps1 filter --type youtube_long
#
# It's just a one-liner around `docker compose run` — see the raw form below.
# ═══════════════════════════════════════════════════════════════════════════
$ErrorActionPreference = "Stop"

docker compose --profile harvester run --rm harvester python cli.py @args
exit $LASTEXITCODE
