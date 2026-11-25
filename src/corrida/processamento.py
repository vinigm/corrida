"""Montagem das tabelas processadas (corridas e segmentos) a partir do bruto."""

from datetime import date, datetime

import pandas as pd

from corrida.configuracao import TIPOS_ATIVIDADE_ESTEIRA
from corrida.metricas import calcular_eficiencia, calcular_metricas_segmentos
from corrida.modelos import SegmentoRwd
from corrida.parse_fit import ConteudoFit

COLUNAS_CORRIDAS = [
    "id_atividade",
    "data_hora_local",
    "data_local",
    "tipo_atividade",
    "esteira",
    "distancia_total_m",
    "duracao_total_s",
    "fc_media_bpm",
    "fc_max_bpm",
    "distancia_correndo_m",
    "tempo_correndo_s",
    "distancia_caminhando_m",
    "tempo_caminhando_s",
    "distancia_parado_m",
    "tempo_parado_s",
    "pct_tempo_correndo",
    "maior_trecho_continuo_m",
    "n_segmentos_correndo",
    "pace_correndo_min_km",
    "eficiencia_m_min_por_bpm",
    "fc_zona_1_s",
    "fc_zona_2_s",
    "fc_zona_3_s",
    "fc_zona_4_s",
    "fc_zona_5_s",
]

COLUNAS_SEGMENTOS = [
    "id_atividade",
    "ordem",
    "tipo_segmento",
    "inicio_utc",
    "duracao_s",
    "distancia_m",
]

FORMATO_DATA_HORA_GARMIN = "%Y-%m-%d %H:%M:%S"


def converter_data_hora_local(texto: str) -> datetime:
    """Converte `startTimeLocal` da Garmin ("2026-09-19 15:05:07") em datetime."""
    return datetime.strptime(texto, FORMATO_DATA_HORA_GARMIN)


def montar_linha_corrida(atividade: dict, conteudo_fit: ConteudoFit) -> dict:
    """Monta a linha de `corridas.csv` de uma corrida.

    Args:
        atividade: Resumo da atividade (JSON da lista Garmin).
        conteudo_fit: Segmentos e registros lidos do FIT da atividade.

    Returns:
        Dicionário com as colunas de COLUNAS_CORRIDAS.
    """
    data_hora_local = converter_data_hora_local(atividade["startTimeLocal"])
    tipo_atividade = atividade["activityType"]["typeKey"]
    metricas = calcular_metricas_segmentos(conteudo_fit.segmentos)
    eficiencia = calcular_eficiencia(conteudo_fit.registros, conteudo_fit.segmentos)

    return {
        "id_atividade": int(atividade["activityId"]),
        "data_hora_local": data_hora_local.isoformat(sep=" "),
        "data_local": data_hora_local.date().isoformat(),
        "tipo_atividade": tipo_atividade,
        "esteira": tipo_atividade in TIPOS_ATIVIDADE_ESTEIRA,
        "distancia_total_m": atividade.get("distance"),
        "duracao_total_s": atividade.get("duration"),
        "fc_media_bpm": atividade.get("averageHR"),
        "fc_max_bpm": atividade.get("maxHR"),
        "distancia_correndo_m": metricas.distancia_correndo_m,
        "tempo_correndo_s": metricas.tempo_correndo_s,
        "distancia_caminhando_m": metricas.distancia_caminhando_m,
        "tempo_caminhando_s": metricas.tempo_caminhando_s,
        "distancia_parado_m": metricas.distancia_parado_m,
        "tempo_parado_s": metricas.tempo_parado_s,
        "pct_tempo_correndo": metricas.pct_tempo_correndo,
        "maior_trecho_continuo_m": metricas.maior_trecho_continuo_m,
        "n_segmentos_correndo": metricas.n_segmentos_correndo,
        "pace_correndo_min_km": metricas.pace_correndo_min_km,
        "eficiencia_m_min_por_bpm": eficiencia,
        "fc_zona_1_s": atividade.get("hrTimeInZone_1"),
        "fc_zona_2_s": atividade.get("hrTimeInZone_2"),
        "fc_zona_3_s": atividade.get("hrTimeInZone_3"),
        "fc_zona_4_s": atividade.get("hrTimeInZone_4"),
        "fc_zona_5_s": atividade.get("hrTimeInZone_5"),
    }


def montar_linhas_segmentos(
    id_atividade: int,
    segmentos: list[SegmentoRwd],
) -> list[dict]:
    """Monta as linhas de `segmentos.csv` de uma corrida (ordem do FIT)."""
    linhas: list[dict] = []
    for ordem, segmento in enumerate(segmentos):
        linha = {
            "id_atividade": id_atividade,
            "ordem": ordem,
            "tipo_segmento": segmento.tipo,
            "inicio_utc": segmento.inicio_utc.isoformat(),
            "duracao_s": segmento.duracao_s,
            "distancia_m": segmento.distancia_m,
        }
        linhas.append(linha)
    return linhas


def construir_tabelas(
    linhas_corridas: list[dict],
    linhas_segmentos: list[dict],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Cria os DataFrames finais; corridas ordenadas da mais antiga à mais nova."""
    corridas = pd.DataFrame(linhas_corridas, columns=COLUNAS_CORRIDAS)
    corridas = corridas.sort_values("data_hora_local").reset_index(drop=True)
    segmentos = pd.DataFrame(linhas_segmentos, columns=COLUNAS_SEGMENTOS)
    return corridas, segmentos


def extrair_datas_locais(corridas: pd.DataFrame) -> list[date]:
    """Converte a coluna `data_local` (texto ISO) em lista de `date`."""
    datas: list[date] = []
    for texto_data in corridas["data_local"]:
        datas.append(date.fromisoformat(texto_data))
    return datas
