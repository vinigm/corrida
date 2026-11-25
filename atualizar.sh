#!/usr/bin/env bash
# Atualiza os dados do Garmin, regenera o dashboard e abre no navegador.
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")" && pwd)"
export UV_PROJECT_ENVIRONMENT="$HOME/.venvs/corrida"
export PATH="$HOME/.local/bin:$PATH"

cd "$RAIZ"
uv run --project "$RAIZ" python -m corrida
open "$RAIZ/dashboard.html"

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git add dashboard.html index.html
  if ! git diff --cached --quiet; then
    git commit -m "chore: atualiza dashboard ($(date +%Y-%m-%d))"
    git push
  fi
fi
