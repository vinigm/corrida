# CLAUDE.md — projeto corrida

Pipeline pessoal: dados de corrida do Garmin (Personal API oficial) → `dashboard.html` de evolução rumo às metas **5 km → 10 km**.

Criado em 25/11/2026.

---

## Fonte de verdade (por pergunta)

- **O que o sistema FAZ hoje?** → o código em `src/corrida/` vence, sempre.
- **O que o sistema DEVERIA fazer?** → a decisão mais recente do Vinicius, registrada em `docs/PENDENCIAS.md`. Diferença entre os dois = pendência ⏳, não contradição.
- **Retrato do sistema** → [`docs/ESTADO.md`](docs/ESTADO.md) (leitura deliberada).
- **Fila viva** → `docs/PENDENCIAS.md` (importado abaixo).

## Invariantes

- **Segredos fora do projeto:** a chave fica em `~/.config/corrida/.env` e o cache do token em `~/.config/corrida/token.json` (chmod 600). Nunca imprimir nem logar nenhum dos dois.
- **venv fora do Google Drive:** `~/.venvs/corrida`, via `UV_PROJECT_ENVIRONMENT`. Nunca criar `.venv` dentro da pasta.
- **Escopo = só corrida.** Saúde/wellness (sono, HRV, estresse) está fora, por decisão do Vinicius em 25/11/2026.
- **Métrica-mãe = `maior_trecho_continuo_m`:** o maior segmento `rwd_run` individual do FIT. Vizinhos não se somam. Sem segmento rwd → nulo, nunca zero.
- **Código Python** segue `~/.claude/PADRAO-CODIGO-PYTHON.md`.
- **Mudança em dado ou métrica** exige certificação adversarial independente. Teste verde não basta.
- **Git e GitHub Pages:** repositório `https://github.com/vinigm/corrida` (branch `main`). `data/` fica no `.gitignore` (contém GPS). O pipeline gera `dashboard.html` e `index.html` (servido no GitHub Pages em `https://vinigm.github.io/corrida/`).

## Como rodar

- Atualizar dados e abrir o painel: `./atualizar.sh`
- Testes: `UV_PROJECT_ENVIRONMENT=$HOME/.venvs/corrida uv run pytest -q`

## Mapa

- `src/corrida/api_garmin.py`: token + chamadas HTTP (I/O).
- `src/corrida/ingestao.py`: download incremental para `data/raw/`.
- `src/corrida/parse_fit.py`: FIT → segmentos rwd e records 1 Hz.
- `src/corrida/metricas.py`: funções puras (pace, % correndo, maior trecho, eficiência, semanas, KPIs).
- `src/corrida/processamento.py`: monta `data/processed/*.csv`.
- `src/corrida/gerar_html.py` + `template_dashboard.html`: o painel.
- `src/corrida/configuracao.py`: metas, janelas (30 e 90 dias), tipos de atividade.
- `src/corrida/pipeline.py`: orquestração.

@docs/PENDENCIAS.md
