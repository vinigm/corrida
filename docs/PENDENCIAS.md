# PENDENCIAS — fila viva

Retrato do sistema: [`ESTADO.md`](ESTADO.md). Status: ✅ resolvido · ⏳ em aberto · 🚫 descartado.

---

## Vinicius

- ✅ **Relógio sincronizado** em 25/11/2026. Entraram 2 corridas (21 e 23/11/2026).

- ⏳ **Trocar a chave da Personal API.** A atual foi colada no chat em 25/11/2026. Gerar uma nova e salvar direto em `~/.config/corrida/.env`.

- ✅ **"5 km" = correr sem parar.** O painel mede pelo maior trecho `rwd_run`. Decisão do Vinicius em 25/11/2026.

- ✅ **Versionar com git + GitHub Pages** (`https://github.com/vinigm/corrida` e `https://vinigm.github.io/corrida/`). `data/` fica fora do repositório (tem GPS). `index.html` gerado junto com `dashboard.html`.

## Claude (agente)

- ⏳ **Testes** de `parse_fit`, ingestão e HTML. Sobrevivem mutantes como trocar `startTimeLocal` por GMT e tirar o filtro de corrida.

- ✅ **Renovação de token vencido:** exercitada contra a API real em 26/11/2026 (cache vencido → token novo).

- ⏳ **Painel offline:** embutir o Chart.js no HTML, se o Vinicius quiser abrir sem internet.

## Descartado

- 🚫 **Saúde/wellness** (sono, HRV, estresse, body battery). Ele não dorme de relógio e quer só corrida. Decisão do Vinicius em 25/11/2026.

- 🚫 **Libs não oficiais** (`garth`, `python-garminconnect`): quebradas desde mar/2026. A Personal API oficial substitui. Decisão do Claude em 25/11/2026, com base na sondagem.

- 🚫 **Endpoints de splits/laps da API** (`/activity-service/activity/{id}/splits|typedsplits|laps`): retornam 404. Os segmentos vêm do .FIT. Verificado em 25/11/2026.

---

## Registro cronológico

- **26/11/2026**
  - ✅ Corrida de 26/11/2026 ingerida: 4,02 km, trecho contínuo 2,02 km. Total: 27 corridas, 84,59 km.
  - ✅ Zonas de FC (`fc_zona_*_s`) conferidas contra a API: 0 divergências em 135 valores.
  - ✅ Renovação de token vencido exercitada contra a API real.
- **25/11/2026**
  - ✅ Personal API conectada; token e chave fora do Drive.
  - ✅ Pipeline com ingestão incremental, CSVs e `dashboard.html`. 30 testes.
  - ✅ Certificação adversarial: 1 divergência (velocidade 0 na eficiência), corrigida e re-certificada como APROVADO.
  - ✅ Painel corrigido em 320 px e no desktop (barras semanais invisíveis, data estourando o cartão).
  - ✅ Meta definida: 5 km e 10 km sem parar (maior trecho contínuo).
  - ✅ Relógio sincronizado: 25 corridas; forma atual de 2,03 km (41% da meta 1).
  - ✅ Filtro por ano no painel. Âncoras por ano conferidas no navegador: 2025 = 12 corridas / 38,76 km; 2026 = 13 / 38,24 km.
  - ✅ Repositório Git conectado a `vinigm/corrida` e GitHub Pages ativado (`index.html`).
  - ✅ Aba "Início (Ciclo Atual)" desde 21/11/2026 com 3 Big Numbers (`KM Total`, `KM Médio por Semana`, `KM Médio por Mês`), gráfico de barras diário e variação % corrida a corrida.
  - ✅ Corrida de 25/11/2026 ingerida: 3,56 km, trecho contínuo 2,00 km. Total: 26 corridas, 80,57 km.
  - ⏳ Troca da chave: com o Vinicius.
