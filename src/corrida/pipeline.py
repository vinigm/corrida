"""Orquestração do pipeline: ingestão -> FIT -> métricas -> CSVs -> dashboard."""

import logging
from datetime import datetime

import pandas as pd

from corrida.api_garmin import ler_chave_api, obter_token
from corrida.configuracao import CaminhosProjeto, criar_caminhos_padrao
from corrida.gerar_html import (
    gravar_dashboard,
    montar_dados_dashboard,
    renderizar_html,
)
from corrida.ingestao import ingerir
from corrida.metricas import calcular_indicadores, calcular_volume_semanal
from corrida.parse_fit import ler_fit
from corrida.processamento import (
    construir_tabelas,
    extrair_datas_locais,
    montar_linha_corrida,
    montar_linhas_segmentos,
)

logger = logging.getLogger(__name__)


def processar_corridas(
    corridas_resumo: list[dict],
    caminhos: CaminhosProjeto,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Lê cada FIT e monta as tabelas `corridas` e `segmentos`.

    Args:
        corridas_resumo: Resumos Garmin das atividades de corrida.
        caminhos: Caminhos do projeto.

    Returns:
        (corridas, segmentos) como DataFrames.
    """
    linhas_corridas: list[dict] = []
    linhas_segmentos: list[dict] = []

    for atividade in corridas_resumo:
        id_atividade = int(atividade["activityId"])
        arquivo_fit = caminhos.pasta_fit / f"{id_atividade}.fit"
        conteudo_fit = ler_fit(arquivo_fit)

        linha_corrida = montar_linha_corrida(atividade, conteudo_fit)
        linhas_corridas.append(linha_corrida)

        linhas_do_fit = montar_linhas_segmentos(id_atividade, conteudo_fit.segmentos)
        linhas_segmentos.extend(linhas_do_fit)

    return construir_tabelas(linhas_corridas, linhas_segmentos)


def gravar_csvs(
    corridas: pd.DataFrame,
    segmentos: pd.DataFrame,
    caminhos: CaminhosProjeto,
) -> None:
    """Grava `corridas.csv` e `segmentos.csv` (sobrescreve)."""
    caminhos.pasta_processada.mkdir(parents=True, exist_ok=True)
    corridas.to_csv(caminhos.arquivo_corridas, index=False)
    segmentos.to_csv(caminhos.arquivo_segmentos, index=False)
    logger.info(
        "CSVs gravados: %d corridas, %d segmentos.",
        len(corridas),
        len(segmentos),
    )


def gerar_dashboard(
    corridas: pd.DataFrame,
    caminhos: CaminhosProjeto,
    agora: datetime,
    segmentos: pd.DataFrame | None = None,
) -> None:
    """Calcula volume semanal e KPIs e grava o `dashboard.html`."""
    hoje = agora.date()
    datas_corridas = extrair_datas_locais(corridas)

    distancias_totais_m: list[float] = []
    for distancia in corridas["distancia_total_m"]:
        distancias_totais_m.append(float(distancia))

    maiores_trechos_m: list[float | None] = []
    for trecho in corridas["maior_trecho_continuo_m"]:
        if pd.isna(trecho):
            maiores_trechos_m.append(None)
        else:
            maiores_trechos_m.append(float(trecho))

    volume_semanal = calcular_volume_semanal(datas_corridas, distancias_totais_m, hoje)
    indicadores = calcular_indicadores(
        datas_corridas, distancias_totais_m, maiores_trechos_m, hoje
    )

    if caminhos.arquivo_atividades.exists():
        instante_arquivo = caminhos.arquivo_atividades.stat().st_mtime
        dados_atualizados_em = datetime.fromtimestamp(instante_arquivo)
    else:
        dados_atualizados_em = None

    if segmentos is None and caminhos.arquivo_segmentos.exists():
        segmentos = pd.read_csv(caminhos.arquivo_segmentos)

    dados = montar_dados_dashboard(
        corridas, volume_semanal, indicadores, agora, dados_atualizados_em, segmentos
    )
    html = renderizar_html(dados)
    gravar_dashboard(html, caminhos.arquivo_dashboard)
    gravar_dashboard(html, caminhos.arquivo_index)
    logger.info(
        "Dashboard gravado em %s e %s",
        caminhos.arquivo_dashboard,
        caminhos.arquivo_index,
    )


def executar() -> None:
    """Executa o pipeline completo com a API real."""
    caminhos = criar_caminhos_padrao()
    chave_api = ler_chave_api(caminhos.arquivo_env)
    token = obter_token(chave_api, caminhos.arquivo_token)

    corridas_resumo = ingerir(token, caminhos)
    corridas, segmentos = processar_corridas(corridas_resumo, caminhos)
    gravar_csvs(corridas, segmentos, caminhos)
    gerar_dashboard(corridas, caminhos, datetime.now(), segmentos)


def principal() -> None:
    """Ponto de entrada de linha de comando."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    executar()
