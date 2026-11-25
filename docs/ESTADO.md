# ESTADO — o que o sistema é hoje

Atualizado em 25/11/2026 · Fila viva: [`PENDENCIAS.md`](PENDENCIAS.md) · Índice: [`../CLAUDE.md`](../CLAUDE.md)

---

## O que FAZ

- **Ingestão incremental** pela Garmin Personal API (oficial):
  - token JWT de 24 h, com cache;
  - lista de atividades → `data/raw/atividades.json`;
  - baixa só os `.fit` que faltam → `data/raw/fit/`.
- **Filtra corrida:** `running`, `treadmill_running`, `trail_running`, `track_running`, `indoor_running`. A esteira fica marcada.
- **Lê o .FIT** (`garmin-fit-sdk`):
  - segmentos `rwd_run` / `rwd_walk` / `rwd_stand` (a detecção automática de corrida/caminhada da Garmin);
  - records a 1 Hz.
- **Calcula por corrida** → `data/processed/corridas.csv` (20 colunas):
  - distância e tempo correndo, caminhando e parado;
  - % do tempo correndo;
  - **maior trecho contínuo** (métrica-mãe);
  - pace correndo;
  - eficiência (m/min por bpm, só nos trechos rwd_run, descartando velocidade ou FC nula/zero).
- **Segmentos** → `data/processed/segmentos.csv` (1 linha por segmento rwd).
- **Painel** `dashboard.html` (e `index.html` para o GitHub Pages em `https://vinigm.github.io/corrida/`):
  - **Aba 1 — Início (Ciclo Atual, desde 21/11/2026):**
    - Painel de 3 Big Numbers no estilo card destacado (`KM Total`, `KM Médio por Semana`, `KM Médio por Mês` considerando semanas/meses ativos com corrida no ciclo);
    - Gráfico de barras diário (dias de corrida do ciclo) empilhando km correndo + caminhando, com rótulo no topo de cada barra mostrando o total em km e a variação percentual (`+12,5% vs ant.`) em relação à corrida anterior;
    - Tabela do ciclo atual com coluna de pílula de variação percentual entre corridas e FC média/máxima.
  - **Aba 2 — Histórico Completo:**
    - KPIs: forma atual (90 dias) com barras rumo a 5 e 10 km, recorde, maior distância, dias sem correr, corridas em 30 dias;
    - 5 gráficos (6 canvas);
    - tabela de todas as corridas (incluindo variação % vs corrida anterior);
  - claro/escuro, de 320 px a desktop.
- **Filtro por ano** (Todos · um botão por ano), lembrado em `#ano=AAAA` na URL quando o navegador permite.
  - **Filtra:** os gráficos por corrida (eixo de 01/jan a 31/dez, ou até hoje no ano corrente), a tabela, as semanas (pelo ano ISO, que é o ano da quinta-feira), o recorde, a maior distância e a linha-resumo do ano.
  - **Não filtra:** forma atual, barras de meta, "sem correr há" e corridas em 30 dias, que são indicadores do momento.
  - O volume semanal de 2025 começa na semana da 1ª corrida (05/05), não em janeiro.

## Números-âncora (25/11/2026, após a sincronização do relógio)

- **25 corridas** (24 rua + 1 esteira), de **11/05/2025** a **23/11/2026**.
  - 2025: **12** corridas, **38,76 km**.
  - 2026: **13** corridas, **38,24 km**.
- **77,00 km** no total, dos quais **69,95 km** correndo.
- **260 segmentos** rwd; **82 semanas**, das quais **65 sem corrida**.
- **Recorde de trecho contínuo:** **5,52 km** em 18/05/2025.
- **Forma atual (90 dias):** **2,03 km** (21/11/2026), o que dá **41%** da meta de 5 km.
- **Certificação adversarial** sobre as 23 primeiras corridas:
  - recálculo independente com outro parser (`fitdecode`);
  - 1 divergência (velocidade zero entrando na eficiência), corrigida;
  - re-certificado: **APROVADO**.
- **As 2 corridas novas** (21 e 23/11/2026) passaram pelo mesmo código certificado.
  - Spot-check contra a API: soma rwd e nº de segmentos batem com os `splitSummaries`.

## O que PREVÊ mas não faz

- **Corridas que não chegaram ao Garmin Connect** ficam invisíveis. O painel só é tão atual quanto a última sincronização do relógio.
- **Renovação de token vencido:** implementada, mas não exercitada contra a API real.
- `./atualizar.sh` rodou de ponta a ponta em 25/11/2026, com download incremental de 2 FIT novos.

## Limitações conhecidas (código)

- O painel carrega **Chart.js 4.4.1 do jsDelivr**: precisa de internet para abrir.
- "Dias sem correr" e as janelas de 30/90 dias ficam **congelados na hora da geração** (HTML estático). Para atualizar, rodar `./atualizar.sh`.
- **Testes** (30, pytest) cobrem só as métricas puras. `parse_fit`, ingestão e HTML não têm teste.
- Corrida com segmentos rwd mas **nenhum `rwd_run`** → maior trecho = **0** (não nulo). Não ocorre nos dados atuais.

## Maquiagem de visualização

- Nenhuma. O eixo do gráfico de trecho contínuo é fixo em 0–10,5 km para as metas ficarem sempre visíveis; isso achata a área de dados, mas não distorce valores.
