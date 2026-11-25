"""Estruturas de dados do domínio de corrida."""

import dataclasses
from datetime import datetime


@dataclasses.dataclass(frozen=True)
class SegmentoRwd:
    """Um segmento da detecção automática corrida/caminhada/parado da Garmin.

    Attributes:
        tipo: `split_type` do FIT (rwd_run, rwd_walk ou rwd_stand).
        inicio_utc: Início do segmento (UTC, com fuso).
        duracao_s: Tempo do segmento em segundos (`total_timer_time`).
        distancia_m: Distância do segmento em metros (`total_distance`).
    """

    tipo: str
    inicio_utc: datetime
    duracao_s: float
    distancia_m: float


@dataclasses.dataclass(frozen=True)
class MetricasSegmentos:
    """Métricas de uma corrida derivadas dos segmentos rwd.

    Todos os campos são None quando a corrida não tem nenhum segmento rwd
    (dado ausente não é zero).
    """

    distancia_correndo_m: float | None
    tempo_correndo_s: float | None
    distancia_caminhando_m: float | None
    tempo_caminhando_s: float | None
    distancia_parado_m: float | None
    tempo_parado_s: float | None
    pct_tempo_correndo: float | None
    maior_trecho_continuo_m: float | None
    pace_correndo_min_km: float | None
    n_segmentos_correndo: int
