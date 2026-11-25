"""Ingestão incremental e idempotente dos dados brutos da Garmin."""

import io
import json
import logging
import zipfile
from pathlib import Path

from corrida.api_garmin import baixar_zip_fit, listar_atividades
from corrida.configuracao import TIPOS_ATIVIDADE_CORRIDA, CaminhosProjeto

logger = logging.getLogger(__name__)


def atividade_e_corrida(atividade: dict) -> bool:
    """Indica se a atividade é de corrida (typeKey na lista de tipos de corrida)."""
    tipo_atividade = atividade.get("activityType") or {}
    chave_tipo = tipo_atividade.get("typeKey")
    return chave_tipo in TIPOS_ATIVIDADE_CORRIDA


def filtrar_corridas(atividades: list[dict]) -> list[dict]:
    """Mantém apenas atividades de corrida, preservando a ordem."""
    corridas: list[dict] = []
    for atividade in atividades:
        if atividade_e_corrida(atividade):
            corridas.append(atividade)
    return corridas


def ids_sem_fit(corridas: list[dict], pasta_fit: Path) -> list[int]:
    """Lista os `activityId` de corridas cujo .fit ainda não foi baixado."""
    ids_pendentes: list[int] = []
    for corrida in corridas:
        id_atividade = int(corrida["activityId"])
        arquivo_fit = pasta_fit / f"{id_atividade}.fit"
        if not arquivo_fit.exists():
            ids_pendentes.append(id_atividade)
    return ids_pendentes


def extrair_fit_do_zip(conteudo_zip: bytes, id_atividade: int) -> bytes:
    """Extrai `{id}_ACTIVITY.fit` do ZIP baixado.

    Raises:
        KeyError: Se o ZIP não contiver o arquivo esperado.
    """
    nome_esperado = f"{id_atividade}_ACTIVITY.fit"
    with zipfile.ZipFile(io.BytesIO(conteudo_zip)) as arquivo_zip:
        return arquivo_zip.read(nome_esperado)


def gravar_atividades(atividades: list[dict], arquivo: Path) -> None:
    """Grava a lista completa de atividades em JSON (sobrescreve de forma atômica)."""
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo_temporario = arquivo.with_suffix(".json.tmp")
    arquivo_temporario.write_text(
        json.dumps(atividades, ensure_ascii=False),
        encoding="utf-8",
    )
    arquivo_temporario.replace(arquivo)


def ler_atividades(arquivo: Path) -> list[dict]:
    """Lê a lista de atividades salva (lista vazia se o arquivo não existir)."""
    if not arquivo.exists():
        return []
    return json.loads(arquivo.read_text(encoding="utf-8"))


def ingerir(token: str, caminhos: CaminhosProjeto) -> list[dict]:
    """Atualiza `atividades.json` e baixa os .fit que faltam.

    Idempotente: só baixa .fit ausentes em disco.

    Args:
        token: JWT válido.
        caminhos: Caminhos do projeto.

    Returns:
        Lista de atividades de corrida (resumo Garmin).
    """
    atividades = listar_atividades(token)
    gravar_atividades(atividades, caminhos.arquivo_atividades)

    corridas = filtrar_corridas(atividades)
    caminhos.pasta_fit.mkdir(parents=True, exist_ok=True)
    pendentes = ids_sem_fit(corridas, caminhos.pasta_fit)
    logger.info(
        "%d corridas na conta; %d .fit a baixar.",
        len(corridas),
        len(pendentes),
    )

    for id_atividade in pendentes:
        conteudo_zip = baixar_zip_fit(token, id_atividade)
        conteudo_fit = extrair_fit_do_zip(conteudo_zip, id_atividade)
        arquivo_fit = caminhos.pasta_fit / f"{id_atividade}.fit"
        arquivo_fit.write_bytes(conteudo_fit)
        logger.info("FIT baixado: %d", id_atividade)

    return corridas
