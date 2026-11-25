#!/usr/bin/env bash
# Atualiza os dados do Garmin, regenera o dashboard e abre no navegador.
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")" && pwd)"
export UV_PROJECT_ENVIRONMENT="$HOME/.venvs/corrida"
export PATH="$HOME/.local/bin:$PATH"

cd "$RAIZ"
uv run --project "$RAIZ" python -m corrida
open "$RAIZ/dashboard.html"
