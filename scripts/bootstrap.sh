#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "[INFO] Created .env from .env.example"
fi

mkdir -p integrations

echo "[OK] Bootstrap complete. Edit .env with your OLLAMA_API_KEY before running integrations."
