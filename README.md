# Corrida: Garmin -> dashboard de evolução

Uso: `./atualizar.sh` (baixa só o que falta, recalcula e abre `dashboard.html`).
GitHub Pages: `https://vinigm.github.io/corrida/` (servido via `index.html`).

- Chave: `~/.config/corrida/.env` (`GARMIN_PERSONAL_API_KEY=...`); token em cache em `~/.config/corrida/token.json`.
- venv fora do Drive: `~/.venvs/corrida` (via `UV_PROJECT_ENVIRONMENT`).
- Dados: `data/raw/` (JSON + FIT) e `data/processed/` (`corridas.csv`, `segmentos.csv`).
- Testes: `UV_PROJECT_ENVIRONMENT=$HOME/.venvs/corrida uv run pytest`.
- O dashboard carrega Chart.js 4.4.1 do jsDelivr (precisa de internet para abrir).
