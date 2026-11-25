"""Acesso à Garmin Personal API (I/O de rede e cache de token).

Nenhuma função desta camada registra ou imprime a chave ou o token.
"""

import base64
import json
import logging
import os
import time
from pathlib import Path

import requests

from corrida.configuracao import (
    CHAVE_ENV_API,
    MARGEM_VALIDADE_TOKEN_S,
    TAMANHO_PAGINA_API,
    TIMEOUT_REQUISICAO_S,
    URL_DOWNLOAD_FIT,
    URL_LISTA_ATIVIDADES,
    URL_TOKEN,
)

logger = logging.getLogger(__name__)


class ErroChaveApiAusente(RuntimeError):
    """A chave da Personal API não foi encontrada no arquivo .env."""


def ler_chave_api(arquivo_env: Path) -> str:
    """Lê a chave da API do arquivo .env (formato CHAVE=valor).

    Args:
        arquivo_env: Caminho do .env fora da pasta do projeto.

    Returns:
        A chave da API.

    Raises:
        ErroChaveApiAusente: Se o arquivo ou a variável não existirem.
    """
    if not arquivo_env.exists():
        raise ErroChaveApiAusente(f"Arquivo {arquivo_env} não encontrado.")

    for linha in arquivo_env.read_text(encoding="utf-8").splitlines():
        linha_limpa = linha.strip()
        if not linha_limpa.startswith(CHAVE_ENV_API + "="):
            continue
        valor_bruto = linha_limpa.split("=", 1)[1]
        return valor_bruto.strip().strip('"').strip("'")

    variavel_ambiente = os.environ.get(CHAVE_ENV_API)
    if variavel_ambiente:
        return variavel_ambiente

    raise ErroChaveApiAusente(f"{CHAVE_ENV_API} ausente em {arquivo_env}.")


def extrair_expiracao_jwt(token: str) -> int:
    """Extrai o claim `exp` (epoch em segundos) de um JWT, sem validar assinatura.

    Args:
        token: JWT em texto puro.

    Returns:
        Epoch (segundos) em que o token expira.

    Raises:
        ValueError: Se o token não tiver payload legível ou claim `exp`.
    """
    partes_token = token.split(".")
    if len(partes_token) != 3:
        raise ValueError("Token JWT com formato inesperado.")

    payload_base64 = partes_token[1]
    preenchimento = "=" * (-len(payload_base64) % 4)
    payload_bytes = base64.urlsafe_b64decode(payload_base64 + preenchimento)
    payload = json.loads(payload_bytes)

    if "exp" not in payload:
        raise ValueError("Token JWT sem claim 'exp'.")
    return int(payload["exp"])


def token_em_cache_e_valido(
    arquivo_token: Path,
    agora_epoch: float,
) -> str | None:
    """Devolve o token do cache se faltar mais que a margem para expirar.

    Args:
        arquivo_token: Caminho do cache de token.
        agora_epoch: Epoch atual em segundos.

    Returns:
        O token válido ou None se não houver cache utilizável.
    """
    if not arquivo_token.exists():
        return None

    try:
        conteudo = json.loads(arquivo_token.read_text(encoding="utf-8"))
        token = str(conteudo["token"])
        expiracao = int(conteudo["exp"])
    except (json.JSONDecodeError, KeyError, ValueError):
        logger.warning("Cache de token ilegível; será renovado.")
        return None

    segundos_restantes = expiracao - agora_epoch
    if segundos_restantes > MARGEM_VALIDADE_TOKEN_S:
        return token
    return None


def gravar_cache_token(arquivo_token: Path, token: str, expiracao: int) -> None:
    """Grava o token em cache com permissão 600."""
    arquivo_token.parent.mkdir(parents=True, exist_ok=True)
    conteudo = json.dumps({"token": token, "exp": expiracao})
    arquivo_token.write_text(conteudo, encoding="utf-8")
    arquivo_token.chmod(0o600)


def obter_token(chave_api: str, arquivo_token: Path) -> str:
    """Obtém um JWT válido, reutilizando o cache quando possível.

    Args:
        chave_api: Chave da Personal API.
        arquivo_token: Cache de token (fora da pasta do projeto).

    Returns:
        JWT para uso no header Bearer.

    Raises:
        requests.HTTPError: Se a API recusar a chave.
    """
    token_em_cache = token_em_cache_e_valido(arquivo_token, time.time())
    if token_em_cache is not None:
        logger.info("Token reutilizado do cache.")
        return token_em_cache

    cabecalhos = {
        "Authorization": f"ApiKey {chave_api}",
        # Com application/json a API responde HTTP 406.
        "Accept": "*/*",
    }
    resposta = requests.post(
        URL_TOKEN,
        headers=cabecalhos,
        timeout=TIMEOUT_REQUISICAO_S,
    )
    resposta.raise_for_status()

    token_novo = resposta.text.strip()
    expiracao = extrair_expiracao_jwt(token_novo)
    gravar_cache_token(arquivo_token, token_novo, expiracao)
    logger.info("Token novo obtido e salvo em cache.")
    return token_novo


def _cabecalhos_bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Accept": "*/*"}


def listar_atividades(token: str) -> list[dict]:
    """Baixa a lista completa de atividades, paginando com `start`.

    Args:
        token: JWT válido.

    Returns:
        Lista de atividades (dicionários com os campos do resumo Garmin).
    """
    todas_atividades: list[dict] = []
    inicio = 0

    while True:
        resposta = requests.get(
            URL_LISTA_ATIVIDADES,
            headers=_cabecalhos_bearer(token),
            params={"start": inicio, "limit": TAMANHO_PAGINA_API},
            timeout=TIMEOUT_REQUISICAO_S,
        )
        resposta.raise_for_status()
        pagina = resposta.json()
        todas_atividades.extend(pagina)

        if len(pagina) < TAMANHO_PAGINA_API:
            break
        inicio += TAMANHO_PAGINA_API

    logger.info("Lista de atividades baixada: %d itens.", len(todas_atividades))
    return todas_atividades


def baixar_zip_fit(token: str, id_atividade: int) -> bytes:
    """Baixa o ZIP (contendo o .fit) de uma atividade.

    Args:
        token: JWT válido.
        id_atividade: `activityId` Garmin.

    Returns:
        Bytes do arquivo ZIP.
    """
    resposta = requests.get(
        f"{URL_DOWNLOAD_FIT}/{id_atividade}",
        headers=_cabecalhos_bearer(token),
        timeout=TIMEOUT_REQUISICAO_S,
    )
    resposta.raise_for_status()
    return resposta.content
