# ESTADO — o que o sistema é hoje

Atualizado em 25/11/2026 · Fila viva: [`PENDENCIAS.md`](PENDENCIAS.md) · Índice: [`../CLAUDE.md`](../CLAUDE.md)

---

## O que FAZ

- **Ingestão incremental** pela Garmin Personal API (oficial):
  - token JWT de 24 h, com cache; renova sozinho quando vence (exercitado contra a API real em 26/11/2026);
  - lista de atividades → `data/raw/atividades.json`;
  - baixa só os `.fit` que faltam → `data/raw/fit/`.
- **Filtra corrida:** `running`, `treadmill_running`, `trail_running`, `track_running`, `indoor_running`. A esteira fica marcada.
- **Lê o .FIT** (`garmin-fit-sdk`):
  - segmentos `rwd_run` / `rwd_walk` / `rwd_stand` (a detecção automática de corrida/caminhada da Garmin);
  - records a 1 Hz.
- **Calcula por corrida** → `data/processed/corridas.csv` (25 colunas):
  - distância e tempo correndo, caminhando e parado;
  - % do tempo correndo;
  - **maior trecho contínuo** (métrica-mãe);
  - pace correndo;
  - eficiência (m/min por bpm, só nos trechos rwd_run, descartando velocidade ou FC nula/zero);
  - tempo em cada zona de frequência cardíaca (`fc_zona_1_s` a `fc_zona_5_s`).
- **Segmentos** → `data/processed/segmentos.csv` (1 linha por segmento rwd).
- **Painel** `dashboard.html` (e `index.html` para o GitHub Pages em `https://vinigm.github.io/corrida/`):
  - **Aba 1 — Início (Ciclo Atual, desde 21/11/2026):**
    - Painel de 3 Big Numbers no estilo card destacado (`KM Total`, `KM Médio por Semana`, `KM Médio por Mês` considerando semanas/meses ativos com corrida no ciclo);
    - Gráfico de barras diário (dias de corrida do ciclo) empilhando km correndo + caminhando, com rótulo no topo de cada barra mostrando o total em km, a variação percentual em relação à corrida anterior e a variação acumulada desde a 1ª corrida do ciclo (`+18,0% vs ant. · +32,8% acum.`);
    - Gráfico de linha **Pace médio por corrida no ciclo** (`pace_correndo_min_km`, o mesmo da tabela), eixo invertido (mais rápido no alto) e valor escrito em cada ponto;
    - Gráfico de linha **Frequência cardíaca por corrida no ciclo**: FC média (vermelha) e FC máxima (cinza tracejada), de `fc_media_bpm` e `fc_max_bpm`, com o valor em cada ponto;
    - Tabela do ciclo atual com colunas de pílula de `Variação vs anterior` e `Variação vs 1ª corrida` (acumulada no ciclo), além de FC média/máxima;
    - Dois gráficos de Zonas de FC lado a lado embaixo da tabela: **Resumo do Ciclo Atual** (barras horizontais Z5→Z1 com `%` e tempo acumulado) e **Evolução por Corrida (%)** (barras 100% empilhadas Z1..Z5 por treino);
    - Gráfico **Raio-X ao longo dos km: onde corri e onde caminhei** no final da aba Início, mostrando na linha de `0 km` até a distância final de cada corrida os blocos exatos `[km_início, km_fim]` de corrida e de caminhada.
  - **Aba 2 — Histórico Completo:**
    - KPIs: forma atual (90 dias) com barras rumo a 5 e 10 km, recorde, maior distância, dias sem correr, corridas em 30 dias;
    - 5 gráficos (6 canvas);
    - tabela de todas as corridas (incluindo variação % vs corrida anterior);
  - claro/escuro, de 320 px a desktop.
- **Filtro por ano** (Todos · um botão por ano), lembrado em `#ano=AAAA` na URL quando o navegador permite.
  - **Filtra:** os gráficos por corrida (eixo de 01/jan a 31/dez, ou até hoje no ano corrente), a tabela, as semanas (pelo ano ISO, que é o ano da quinta-feira), o recorde, a maior distância e a linha-resumo do ano.
  - **Não filtra:** forma atual, barras de meta, "sem correr há" e corridas em 30 dias, que são indicadores do momento.
  - O volume semanal de 2025 começa na semana da 1ª corrida (05/05), não em janeiro.

## Números-âncora (26/11/2026, após a corrida do dia)

- **27 corridas** (26 rua + 1 esteira), de **11/05/2025** a **26/11/2026**.
  - 2025: **12** corridas, **38,76 km**.
  - 2026: **15** corridas, **45,83 km**.
- **84,59 km** no total, dos quais **76,92 km** correndo.
- **273 segmentos** rwd; **82 semanas**, das quais **65 sem corrida**.
- **Recorde de trecho contínuo:** **5,52 km** em 18/05/2025.
- **Forma atual (90 dias):** **2,03 km** (21/11/2026), o que dá **41%** da meta de 5 km.
- **Certificação adversarial** sobre as 23 primeiras corridas:
  - recálculo independente com outro parser (`fitdecode`);
  - 1 divergência (velocidade zero entrando na eficiência), corrigida;
  - re-certificado: **APROVADO**.
- **As 4 corridas novas** (21, 23, 25 e 26/11/2026) passaram pelo mesmo código certificado.
  - Spot-check contra a API: soma rwd e nº de segmentos batem com os `splitSummaries`.

## O que PREVÊ mas não faz

- **Corridas que não chegaram ao Garmin Connect** ficam invisíveis. O painel só é tão atual quanto a última sincronização do relógio.
- `./atualizar.sh` rodou de ponta a ponta em 25/11/2026, com download incremental de 2 FIT novos.

## Limitações conhecidas (código)

- O painel carrega **Chart.js 4.4.1 do jsDelivr**: precisa de internet para abrir. No navegador do app do Claude, o arquivo aberto direto vira URL `data:` e o CDN é bloqueado; para conferir lá, servir com `.claude/launch.json` (porta 8765).
- "Dias sem correr" e as janelas de 30/90 dias ficam **congelados na hora da geração** (HTML estático). Para atualizar, rodar `./atualizar.sh`.
- **Testes** (30, pytest) cobrem só as métricas puras. `parse_fit`, ingestão e HTML não têm teste.
- Corrida com segmentos rwd mas **nenhum `rwd_run`** → maior trecho = **0** (não nulo). Não ocorre nos dados atuais.

## Maquiagem de visualização

- Nenhuma. O eixo do gráfico de trecho contínuo é fixo em 0–10,5 km para as metas ficarem sempre visíveis; isso achata a área de dados, mas não distorce valores.
- O gráfico de pace do ciclo tem eixo com **pelo menos 1:00 min/km** de amplitude, para 10–15 s de diferença não parecerem um salto grande.
