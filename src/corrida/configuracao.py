"""Constantes e configurações do pipeline de corrida."""

import dataclasses
from pathlib import Path

TIPOS_ATIVIDADE_CORRIDA = frozenset(
    {
        "running",
        "treadmill_running",
        "trail_running",
        "track_running",
        "indoor_running",
    }
)

TIPOS_ATIVIDADE_ESTEIRA = frozenset(
    {
        "treadmill_running",
        "indoor_running",
    }
)

META_5_KM_M = 5000.0
META_10_KM_M = 10000.0

TIPO_SEGMENTO_CORRENDO = "rwd_run"
TIPO_SEGMENTO_CAMINHANDO = "rwd_walk"
TIPO_SEGMENTO_PARADO = "rwd_stand"
TIPOS_SEGMENTO_RWD = (
    TIPO_SEGMENTO_CORRENDO,
    TIPO_SEGMENTO_CAMINHANDO,
    TIPO_SEGMENTO_PARADO,
)

DIAS_JANELA_RECENTE = 30
DIAS_JANELA_FORMA_ATUAL = 90
DATA_INICIO_CICLO_ATUAL = "2026-11-21"

SEGUNDOS_POR_MINUTO = 60.0
METROS_POR_KM = 1000.0

TAMANHO_PAGINA_API = 1000
MARGEM_VALIDADE_TOKEN_S = 3600
TIMEOUT_REQUISICAO_S = 60

URL_BASE_API = "https://personal.connectapi.garmin.com"
URL_TOKEN = (
    URL_BASE_API
    + "/personalapitoken-service/personal-api/personal-api-key/token"
)
URL_LISTA_ATIVIDADES = (
    URL_BASE_API + "/activitylist-service/activities/search/activities"
)
URL_DOWNLOAD_FIT = URL_BASE_API + "/download-service/files/activity"

CHAVE_ENV_API = "GARMIN_PERSONAL_API_KEY"

URL_CHART_JS = "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"


@dataclasses.dataclass(frozen=True)
class CaminhosProjeto:
    """Caminhos de entrada e saída do pipeline.

    Segredos (chave e token) ficam fora da pasta do projeto.
    """

    raiz: Path
    arquivo_env: Path
    arquivo_token: Path

    @property
    def pasta_bruta(self) -> Path:
        return self.raiz / "data" / "raw"

    @property
    def arquivo_atividades(self) -> Path:
        return self.pasta_bruta / "atividades.json"

    @property
    def pasta_fit(self) -> Path:
        return self.pasta_bruta / "fit"

    @property
    def pasta_processada(self) -> Path:
        return self.raiz / "data" / "processed"

    @property
    def arquivo_corridas(self) -> Path:
        return self.pasta_processada / "corridas.csv"

    @property
    def arquivo_segmentos(self) -> Path:
        return self.pasta_processada / "segmentos.csv"

    @property
    def arquivo_dashboard(self) -> Path:
        return self.raiz / "dashboard.html"

    @property
    def arquivo_index(self) -> Path:
        return self.raiz / "index.html"


def criar_caminhos_padrao() -> CaminhosProjeto:
    """Monta os caminhos padrão a partir da localização deste pacote."""
    raiz_projeto = Path(__file__).resolve().parents[2]
    pasta_config = Path.home() / ".config" / "corrida"
    return CaminhosProjeto(
        raiz=raiz_projeto,
        arquivo_env=pasta_config / ".env",
        arquivo_token=pasta_config / "token.json",
    )
