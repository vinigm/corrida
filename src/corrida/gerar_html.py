"""Geração do dashboard.html (arquivo único com dados embutidos em JSON)."""

import json
import math
from datetime import datetime
from pathlib import Path

import pandas as pd

from corrida.configuracao import DIAS_JANELA_FORMA_ATUAL, META_5_KM_M, META_10_KM_M, URL_CHART_JS
from corrida.metricas import IndicadoresResumo

ARQUIVO_TEMPLATE = Path(__file__).parent / "template_dashboard.html"
MARCADOR_DADOS = "/*__DADOS_JSON__*/null"
MARCADOR_CHART_JS = "__URL_CHART_JS__"


def valor_para_json(valor: object) -> object:
    """Converte nulos do pandas/NumPy em None e escalares NumPy em tipos nativos."""
    if valor is None:
        return None
    if isinstance(valor, float) and math.isnan(valor):
        return None
    if pd.isna(valor):
        return None
    if hasattr(valor, "item"):
        return valor.item()
    return valor


def corridas_para_registros(corridas: pd.DataFrame) -> list[dict]:
    """Converte o DataFrame de corridas em lista de dicionários serializáveis."""
    registros: list[dict] = []
    for _, linha in corridas.iterrows():
        registro: dict = {}
        for nome_coluna in corridas.columns:
            registro[nome_coluna] = valor_para_json(linha[nome_coluna])
        registros.append(registro)
    return registros


def volume_para_registros(volume_semanal: pd.DataFrame) -> list[dict]:
    """Converte o volume semanal em lista de dicionários serializáveis."""
    registros: list[dict] = []
    for _, linha in volume_semanal.iterrows():
        registro = {
            "semana_inicio": linha["semana_inicio"].isoformat(),
            "km_total": float(linha["km_total"]),
            "n_corridas": int(linha["n_corridas"]),
        }
        registros.append(registro)
    return registros


def indicadores_para_dicionario(indicadores: IndicadoresResumo) -> dict:
    """Converte os KPIs em dicionário serializável (datas em ISO)."""
    if indicadores.data_ultima_corrida is None:
        data_ultima = None
    else:
        data_ultima = indicadores.data_ultima_corrida.isoformat()

    if indicadores.data_recorde_trecho is None:
        data_recorde = None
    else:
        data_recorde = indicadores.data_recorde_trecho.isoformat()

    return {
        "maior_trecho_forma_atual_m": indicadores.maior_trecho_forma_atual_m,
        "maior_trecho_continuo_m": indicadores.maior_trecho_continuo_m,
        "data_recorde_trecho": data_recorde,
        "dias_janela_forma_atual": DIAS_JANELA_FORMA_ATUAL,
        "progresso_meta_5_km": indicadores.progresso_meta_5_km,
        "progresso_meta_10_km": indicadores.progresso_meta_10_km,
        "maior_distancia_total_m": indicadores.maior_distancia_total_m,
        "data_ultima_corrida": data_ultima,
        "dias_desde_ultima_corrida": indicadores.dias_desde_ultima_corrida,
        "corridas_ultimos_30_dias": indicadores.corridas_ultimos_30_dias,
    }


def montar_dados_dashboard(
    corridas: pd.DataFrame,
    volume_semanal: pd.DataFrame,
    indicadores: IndicadoresResumo,
    gerado_em: datetime,
    dados_atualizados_em: datetime | None,
) -> dict:
    """Reúne tudo que o HTML precisa em um único dicionário JSON-serializável."""
    if dados_atualizados_em is None:
        texto_atualizacao = None
    else:
        texto_atualizacao = dados_atualizados_em.isoformat(timespec="seconds")

    return {
        "corridas": corridas_para_registros(corridas),
        "volume_semanal": volume_para_registros(volume_semanal),
        "indicadores": indicadores_para_dicionario(indicadores),
        "metas_m": {"meta_5_km": META_5_KM_M, "meta_10_km": META_10_KM_M},
        "gerado_em": gerado_em.isoformat(timespec="seconds"),
        "dados_atualizados_em": texto_atualizacao,
    }


def serializar_json_para_html(dados: dict) -> str:
    """Serializa em JSON seguro para ficar dentro de uma tag <script>."""
    texto_json = json.dumps(dados, ensure_ascii=False, allow_nan=False)
    return texto_json.replace("</", "<\\/")


def renderizar_html(dados: dict) -> str:
    """Preenche o template com os dados e a URL fixada do Chart.js."""
    template = ARQUIVO_TEMPLATE.read_text(encoding="utf-8")
    html = template.replace(MARCADOR_CHART_JS, URL_CHART_JS)
    html = html.replace(MARCADOR_DADOS, serializar_json_para_html(dados))
    return html


def gravar_dashboard(html: str, arquivo: Path) -> None:
    """Grava o HTML final (sobrescreve de forma atômica)."""
    arquivo_temporario = arquivo.with_suffix(".html.tmp")
    arquivo_temporario.write_text(html, encoding="utf-8")
    arquivo_temporario.replace(arquivo)

