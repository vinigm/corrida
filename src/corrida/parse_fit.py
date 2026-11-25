"""Leitura de arquivos FIT (I/O) e conversão para estruturas do domínio."""

import dataclasses
import logging
from pathlib import Path

import pandas as pd
from garmin_fit_sdk import Decoder, Stream

from corrida.configuracao import TIPOS_SEGMENTO_RWD
from corrida.modelos import SegmentoRwd

logger = logging.getLogger(__name__)

COLUNAS_REGISTROS = ["timestamp", "velocidade_m_s", "fc_bpm"]


class ErroLeituraFit(RuntimeError):
    """O decoder reportou erros ao ler o arquivo FIT."""


@dataclasses.dataclass(frozen=True)
class ConteudoFit:
    """Conteúdo útil de um FIT de atividade.

    Attributes:
        segmentos: Segmentos rwd na ordem do arquivo.
        registros: DataFrame 1 Hz com timestamp (UTC), velocidade_m_s e fc_bpm.
    """

    segmentos: list[SegmentoRwd]
    registros: pd.DataFrame


def extrair_segmentos_rwd(mensagens_split: list[dict]) -> list[SegmentoRwd]:
    """Converte `split_mesgs` em segmentos rwd, ignorando os demais tipos.

    Args:
        mensagens_split: Lista de `split_mesgs` do decoder.

    Returns:
        Segmentos cujo `split_type` é rwd_run, rwd_walk ou rwd_stand.
    """
    segmentos: list[SegmentoRwd] = []
    for mensagem in mensagens_split:
        tipo_segmento = mensagem.get("split_type")
        if tipo_segmento not in TIPOS_SEGMENTO_RWD:
            continue

        segmento = SegmentoRwd(
            tipo=tipo_segmento,
            inicio_utc=mensagem["start_time"],
            duracao_s=float(mensagem.get("total_timer_time") or 0.0),
            distancia_m=float(mensagem.get("total_distance") or 0.0),
        )
        segmentos.append(segmento)
    return segmentos


def extrair_registros(mensagens_record: list[dict]) -> pd.DataFrame:
    """Converte `record_mesgs` em DataFrame com as colunas usadas nas métricas.

    Campos ausentes viram nulos; as chaves int (campos não documentados) são
    ignoradas porque só lemos chaves nomeadas.
    """
    linhas: list[dict] = []
    for registro in mensagens_record:
        linha = {
            "timestamp": registro.get("timestamp"),
            "velocidade_m_s": registro.get("enhanced_speed"),
            "fc_bpm": registro.get("heart_rate"),
        }
        linhas.append(linha)

    registros = pd.DataFrame(linhas, columns=COLUNAS_REGISTROS)
    registros["velocidade_m_s"] = pd.to_numeric(registros["velocidade_m_s"])
    registros["fc_bpm"] = pd.to_numeric(registros["fc_bpm"])
    registros["timestamp"] = pd.to_datetime(registros["timestamp"], utc=True)
    return registros


def ler_fit(caminho: Path) -> ConteudoFit:
    """Lê um arquivo FIT e devolve segmentos rwd e registros 1 Hz.

    Raises:
        ErroLeituraFit: Se o decoder retornar erros.
    """
    decoder = Decoder(Stream.from_file(str(caminho)))
    mensagens, erros = decoder.read()
    if erros:
        raise ErroLeituraFit(f"Erros ao decodificar {caminho.name}: {erros}")

    segmentos = extrair_segmentos_rwd(mensagens.get("split_mesgs", []))
    registros = extrair_registros(mensagens.get("record_mesgs", []))
    logger.info(
        "%s: %d registros, %d segmentos rwd.",
        caminho.name,
        len(registros),
        len(segmentos),
    )
    return ConteudoFit(segmentos=segmentos, registros=registros)
