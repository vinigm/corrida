"""Métricas de corrida: funções puras, sem I/O."""

import dataclasses
import math
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from corrida.configuracao import (
    DIAS_JANELA_FORMA_ATUAL,
    DIAS_JANELA_RECENTE,
    DIAS_JANELA_STATUS_SEMANA,
    LIMITE_ZONAS_ALTAS_ATENCAO,
    LIMITE_ZONAS_ALTAS_TREINO_PESADO,
    META_ZONAS_ALTAS_SEMANA,
    METROS_POR_KM,
    META_5_KM_M,
    META_10_KM_M,
    SEGUNDOS_POR_MINUTO,
    TIPO_SEGMENTO_CAMINHANDO,
    TIPO_SEGMENTO_CORRENDO,
    TIPO_SEGMENTO_PARADO,
)
from corrida.modelos import MetricasSegmentos, SegmentoRwd


def somar_por_tipo(
    segmentos: list[SegmentoRwd],
    tipo: str,
) -> tuple[float, float]:
    """Soma distância (m) e tempo (s) dos segmentos de um tipo rwd.

    Returns:
        Tupla (distancia_m, tempo_s); (0.0, 0.0) se não houver segmentos do tipo.
    """
    distancia_total_m = 0.0
    tempo_total_s = 0.0
    for segmento in segmentos:
        if segmento.tipo == tipo:
            distancia_total_m += segmento.distancia_m
            tempo_total_s += segmento.duracao_s
    return distancia_total_m, tempo_total_s


def calcular_pace_min_km(tempo_s: float, distancia_m: float) -> float | None:
    """Pace em min/km = tempo_s / 60 / (distancia_m / 1000).

    Returns:
        O pace, ou None se a distância for nula ou zero.
    """
    if distancia_m <= 0:
        return None
    tempo_min = tempo_s / SEGUNDOS_POR_MINUTO
    distancia_km = distancia_m / METROS_POR_KM
    return tempo_min / distancia_km


def calcular_metricas_segmentos(
    segmentos: list[SegmentoRwd],
) -> MetricasSegmentos:
    """Calcula distâncias, tempos, % correndo, maior trecho contínuo e pace.

    Regras:
        - Sem nenhum segmento rwd: todos os campos numéricos são None.
        - `maior_trecho_continuo_m` é o maior `distancia_m` entre segmentos
          rwd_run individuais (vizinhos não são somados).
        - `pct_tempo_correndo` = tempo run / (run + walk + stand); None se o
          denominador for zero.
        - Com segmentos rwd mas nenhum rwd_run, correndo = 0 e maior trecho = 0
          (a corrida existiu e não teve trecho correndo); pace fica None.

    Args:
        segmentos: Segmentos rwd da corrida.

    Returns:
        MetricasSegmentos.
    """
    n_segmentos_correndo = 0
    for segmento in segmentos:
        if segmento.tipo == TIPO_SEGMENTO_CORRENDO:
            n_segmentos_correndo += 1

    if not segmentos:
        return MetricasSegmentos(
            distancia_correndo_m=None,
            tempo_correndo_s=None,
            distancia_caminhando_m=None,
            tempo_caminhando_s=None,
            distancia_parado_m=None,
            tempo_parado_s=None,
            pct_tempo_correndo=None,
            maior_trecho_continuo_m=None,
            pace_correndo_min_km=None,
            n_segmentos_correndo=0,
        )

    distancia_correndo_m, tempo_correndo_s = somar_por_tipo(
        segmentos, TIPO_SEGMENTO_CORRENDO
    )
    distancia_caminhando_m, tempo_caminhando_s = somar_por_tipo(
        segmentos, TIPO_SEGMENTO_CAMINHANDO
    )
    distancia_parado_m, tempo_parado_s = somar_por_tipo(
        segmentos, TIPO_SEGMENTO_PARADO
    )

    tempo_ativo_total_s = tempo_correndo_s + tempo_caminhando_s + tempo_parado_s
    if tempo_ativo_total_s > 0:
        pct_tempo_correndo = tempo_correndo_s / tempo_ativo_total_s
    else:
        pct_tempo_correndo = None

    distancias_trechos_correndo: list[float] = []
    for segmento in segmentos:
        if segmento.tipo == TIPO_SEGMENTO_CORRENDO:
            distancias_trechos_correndo.append(segmento.distancia_m)
    if distancias_trechos_correndo:
        maior_trecho_continuo_m = max(distancias_trechos_correndo)
    else:
        maior_trecho_continuo_m = 0.0

    pace_correndo_min_km = calcular_pace_min_km(
        tempo_correndo_s, distancia_correndo_m
    )

    return MetricasSegmentos(
        distancia_correndo_m=distancia_correndo_m,
        tempo_correndo_s=tempo_correndo_s,
        distancia_caminhando_m=distancia_caminhando_m,
        tempo_caminhando_s=tempo_caminhando_s,
        distancia_parado_m=distancia_parado_m,
        tempo_parado_s=tempo_parado_s,
        pct_tempo_correndo=pct_tempo_correndo,
        maior_trecho_continuo_m=maior_trecho_continuo_m,
        pace_correndo_min_km=pace_correndo_min_km,
        n_segmentos_correndo=n_segmentos_correndo,
    )


def calcular_eficiencia(
    registros: pd.DataFrame,
    segmentos: list[SegmentoRwd],
) -> float | None:
    """Eficiência aeróbica em m/min por bpm nos trechos rwd_run.

    Fórmula: (média de velocidade_m_s * 60) / média de fc_bpm, usando só os
    registros dentro das janelas [inicio, inicio + duracao] dos segmentos
    rwd_run. Registros com FC ou velocidade nulas (None/NaN) ou iguais a zero
    ficam fora. Maior = melhor.

    Args:
        registros: DataFrame com colunas timestamp (UTC), velocidade_m_s, fc_bpm.
        segmentos: Segmentos rwd da corrida.

    Returns:
        A eficiência, ou None se não houver registros válidos em trechos de
        corrida ou se a FC média for zero.
    """
    segmentos_correndo: list[SegmentoRwd] = []
    for segmento in segmentos:
        if segmento.tipo == TIPO_SEGMENTO_CORRENDO:
            segmentos_correndo.append(segmento)
    if not segmentos_correndo or registros.empty:
        return None

    dentro_de_janela = pd.Series(False, index=registros.index)
    for segmento in segmentos_correndo:
        inicio = pd.Timestamp(segmento.inicio_utc)
        fim = inicio + pd.Timedelta(seconds=segmento.duracao_s)
        dentro_desta_janela = (registros["timestamp"] >= inicio) & (
            registros["timestamp"] <= fim
        )
        dentro_de_janela = dentro_de_janela | dentro_desta_janela

    # Dentro de um trecho rwd_run o atleta está correndo; velocidade ou FC zero
    # ali são artefato de sensor (GPS sem sinal, esteira calibrando no início,
    # cinta sem contato). Entrar com zero puxaria a eficiência para baixo sem
    # mudança real de condicionamento. Comparação `> 0` também descarta NaN.
    tem_fc_valida = registros["fc_bpm"] > 0
    tem_velocidade_valida = registros["velocidade_m_s"] > 0
    registros_validos = registros[
        dentro_de_janela & tem_fc_valida & tem_velocidade_valida
    ]
    if registros_validos.empty:
        return None

    velocidade_media_m_s = registros_validos["velocidade_m_s"].mean()
    fc_media_bpm = registros_validos["fc_bpm"].mean()
    if fc_media_bpm <= 0:
        return None

    velocidade_media_m_min = velocidade_media_m_s * SEGUNDOS_POR_MINUTO
    return float(velocidade_media_m_min / fc_media_bpm)


def inicio_da_semana_iso(dia: date) -> date:
    """Segunda-feira da semana ISO que contém `dia`."""
    return dia - timedelta(days=dia.weekday())


def calcular_volume_semanal(
    datas_corridas: list[date],
    distancias_m: list[float],
    hoje: date,
) -> pd.DataFrame:
    """Volume por semana ISO, incluindo semanas sem nenhuma corrida.

    A série vai da semana da primeira corrida até a semana de `hoje`; as
    lacunas aparecem com 0 km e 0 corridas.

    Args:
        datas_corridas: Data local de cada corrida.
        distancias_m: Distância total (m) de cada corrida, alinhada às datas.
        hoje: Data de referência (define a última semana).

    Returns:
        DataFrame com colunas semana_inicio (date), km_total, n_corridas.
        Vazio (com as colunas) se não houver corridas.
    """
    colunas = ["semana_inicio", "km_total", "n_corridas"]
    if not datas_corridas:
        return pd.DataFrame(columns=colunas)

    metros_por_semana: dict[date, float] = {}
    corridas_por_semana: dict[date, int] = {}
    for data_corrida, distancia_m in zip(datas_corridas, distancias_m):
        semana = inicio_da_semana_iso(data_corrida)
        metros_por_semana[semana] = metros_por_semana.get(semana, 0.0) + distancia_m
        corridas_por_semana[semana] = corridas_por_semana.get(semana, 0) + 1

    primeira_semana = min(metros_por_semana)
    ultima_semana = max(max(metros_por_semana), inicio_da_semana_iso(hoje))

    linhas: list[dict] = []
    semana_atual = primeira_semana
    while semana_atual <= ultima_semana:
        metros = metros_por_semana.get(semana_atual, 0.0)
        linha = {
            "semana_inicio": semana_atual,
            "km_total": metros / METROS_POR_KM,
            "n_corridas": corridas_por_semana.get(semana_atual, 0),
        }
        linhas.append(linha)
        semana_atual = semana_atual + timedelta(days=7)

    return pd.DataFrame(linhas, columns=colunas)


@dataclasses.dataclass(frozen=True)
class IndicadoresResumo:
    """KPIs do topo do dashboard.

    Attributes:
        maior_trecho_forma_atual_m: Maior trecho contínuo entre corridas dos
            últimos 90 dias (None se não houver corrida na janela).
        progresso_meta_5_km: Fração (0 a 1, limitada) da forma atual sobre 5 km.
        progresso_meta_10_km: Idem para 10 km.
        maior_trecho_continuo_m: Recorde de todos os tempos (None se nenhuma
            corrida tem segmentos rwd).
        data_recorde_trecho: Data em que o recorde aconteceu.
        maior_distancia_total_m: Maior distância total numa corrida.
        data_ultima_corrida: Data da última corrida (None se não houver).
        dias_desde_ultima_corrida: Dias entre a última corrida e hoje.
        corridas_ultimos_30_dias: Corridas nos 30 dias até hoje (inclusive).
    """

    maior_trecho_forma_atual_m: float | None
    progresso_meta_5_km: float
    progresso_meta_10_km: float
    maior_trecho_continuo_m: float | None
    data_recorde_trecho: date | None
    maior_distancia_total_m: float | None
    data_ultima_corrida: date | None
    dias_desde_ultima_corrida: int | None
    corridas_ultimos_30_dias: int


def calcular_progresso_meta(valor_m: float | None, meta_m: float) -> float:
    """Fração do valor sobre a meta, limitada a [0, 1]; None conta como 0."""
    if valor_m is None:
        return 0.0
    fracao = valor_m / meta_m
    return float(min(max(fracao, 0.0), 1.0))


def calcular_indicadores(
    datas_corridas: list[date],
    distancias_totais_m: list[float],
    maiores_trechos_m: list[float | None],
    hoje: date,
) -> IndicadoresResumo:
    """Calcula os KPIs do dashboard.

    Forma atual = maior trecho contínuo entre corridas com
    0 <= (hoje - data).days < DIAS_JANELA_FORMA_ATUAL; sem corrida com trecho
    conhecido na janela, é None (nunca 0). Em empate de recorde vale a corrida
    mais antiga.

    Args:
        datas_corridas: Data local de cada corrida.
        distancias_totais_m: Distância total de cada corrida.
        maiores_trechos_m: Maior trecho contínuo de cada corrida (None = sem rwd).
        hoje: Data de referência.

    Returns:
        IndicadoresResumo (campos None quando não há dados).
    """
    recorde_trecho_m: float | None = None
    data_recorde: date | None = None
    forma_atual_m: float | None = None

    for data_corrida, trecho in zip(datas_corridas, maiores_trechos_m):
        if trecho is None or np.isnan(trecho):
            continue

        if recorde_trecho_m is None or trecho > recorde_trecho_m:
            recorde_trecho_m = trecho
            data_recorde = data_corrida

        dias_atras = (hoje - data_corrida).days
        dentro_da_janela = 0 <= dias_atras < DIAS_JANELA_FORMA_ATUAL
        if dentro_da_janela and (forma_atual_m is None or trecho > forma_atual_m):
            forma_atual_m = trecho

    if distancias_totais_m:
        maior_distancia_m = max(distancias_totais_m)
    else:
        maior_distancia_m = None

    if datas_corridas:
        ultima_corrida = max(datas_corridas)
        dias_desde_ultima = (hoje - ultima_corrida).days
    else:
        ultima_corrida = None
        dias_desde_ultima = None

    corridas_recentes = 0
    for data_corrida in datas_corridas:
        dias_atras = (hoje - data_corrida).days
        if 0 <= dias_atras < DIAS_JANELA_RECENTE:
            corridas_recentes += 1

    return IndicadoresResumo(
        maior_trecho_forma_atual_m=forma_atual_m,
        progresso_meta_5_km=calcular_progresso_meta(forma_atual_m, META_5_KM_M),
        progresso_meta_10_km=calcular_progresso_meta(forma_atual_m, META_10_KM_M),
        maior_trecho_continuo_m=recorde_trecho_m,
        data_recorde_trecho=data_recorde,
        maior_distancia_total_m=maior_distancia_m,
        data_ultima_corrida=ultima_corrida,
        dias_desde_ultima_corrida=dias_desde_ultima,
        corridas_ultimos_30_dias=corridas_recentes,
    )


# ---------------------------------------------------------------------------
# Status do treino (regra 80/20 por zonas de FC)
# ---------------------------------------------------------------------------

NIVEL_TREINO_PESADO = "pesado"
NIVEL_TREINO_ATENCAO = "atencao"
NIVEL_TREINO_LEVE = "leve"
NIVEL_TREINO_SEM_DADOS = "sem_dados"


def segundos_ou_zero(segundos: float | None) -> float:
    """Tempo em zona informado pela Garmin; ausente (None ou NaN) conta como 0."""
    if segundos is None:
        return 0.0
    if math.isnan(segundos):
        return 0.0
    return float(segundos)


@dataclasses.dataclass(frozen=True)
class TempoEmZonasCorrida:
    """Tempo de uma corrida em cada zona de FC, como a Garmin reporta (`hrTimeInZone_N`).

    Attributes:
        inicio_local: Início da corrida no horário local; ordena corridas do mesmo dia.
        segundos_zona_1: Segundos em Z1 (None/NaN = não informado).
        segundos_zona_2: Segundos em Z2.
        segundos_zona_3: Segundos em Z3.
        segundos_zona_4: Segundos em Z4.
        segundos_zona_5: Segundos em Z5.
    """

    inicio_local: datetime
    segundos_zona_1: float | None
    segundos_zona_2: float | None
    segundos_zona_3: float | None
    segundos_zona_4: float | None
    segundos_zona_5: float | None

    def segundos_zonas_altas(self) -> float:
        """Segundos em Z4 + Z5 (intensidade alta na regra 80/20)."""
        segundos_z4 = segundos_ou_zero(self.segundos_zona_4)
        segundos_z5 = segundos_ou_zero(self.segundos_zona_5)
        return segundos_z4 + segundos_z5

    def segundos_com_zona(self) -> float:
        """Soma do tempo nas 5 zonas; 0 quando a Garmin não informou nenhuma."""
        total = 0.0
        for segundos in (
            self.segundos_zona_1,
            self.segundos_zona_2,
            self.segundos_zona_3,
            self.segundos_zona_4,
            self.segundos_zona_5,
        ):
            total += segundos_ou_zero(segundos)
        return total


@dataclasses.dataclass(frozen=True)
class StatusTreino:
    """Avaliação da intensidade do treino atual (card abaixo dos Big Numbers).

    Attributes:
        nivel: pesado, atencao, leve ou sem_dados.
        data_ultima_corrida: Dia da corrida avaliada (a mais recente).
        fracao_zonas_altas_ultima: Fração do tempo da última corrida em Z4/Z5
            (None sem dados de zona).
        fracao_zonas_altas_semana: Mesma fração somando as corridas com zona dos
            7 dias corridos que terminam no dia da última corrida.
        corridas_na_semana: Corridas com dados de zona nessa janela.
        correu_dia_anterior: Houve corrida no dia anterior ao da última.
        data_folga_recomendada: Dia seguinte à última corrida, quando a regra pede folga.
    """

    nivel: str
    data_ultima_corrida: date
    fracao_zonas_altas_ultima: float | None
    fracao_zonas_altas_semana: float | None
    corridas_na_semana: int
    correu_dia_anterior: bool
    data_folga_recomendada: date | None


def obter_inicio_local(corrida: TempoEmZonasCorrida) -> datetime:
    """Chave de ordenação das corridas."""
    return corrida.inicio_local


def calcular_fracao_zonas_altas(corridas: list[TempoEmZonasCorrida]) -> float | None:
    """Fração do tempo em Z4/Z5 somando as corridas; None se nenhuma tem tempo em zona."""
    segundos_altos = 0.0
    segundos_totais = 0.0
    for corrida in corridas:
        segundos_altos += corrida.segundos_zonas_altas()
        segundos_totais += corrida.segundos_com_zona()

    if segundos_totais <= 0:
        return None
    return segundos_altos / segundos_totais


def classificar_nivel_treino(
    fracao_ultima: float,
    fracao_semana: float | None,
) -> str:
    """Classifica a intensidade pela regra 80/20.

    Precedência: pesado (última >= 40% em Z4/Z5) > atenção (última >= 20% ou
    semana > 20%) > leve. A semana exatamente em 20% ainda cumpre o 80/20.
    """
    treino_pesado = fracao_ultima >= LIMITE_ZONAS_ALTAS_TREINO_PESADO
    ultima_acima_da_base = fracao_ultima >= LIMITE_ZONAS_ALTAS_ATENCAO
    semana_fora_do_80_20 = (
        fracao_semana is not None and fracao_semana > META_ZONAS_ALTAS_SEMANA
    )

    if treino_pesado:
        return NIVEL_TREINO_PESADO
    if ultima_acima_da_base or semana_fora_do_80_20:
        return NIVEL_TREINO_ATENCAO
    return NIVEL_TREINO_LEVE


def decidir_data_folga(
    nivel: str,
    fracao_ultima: float,
    correu_dia_anterior: bool,
    data_ultima: date,
) -> date | None:
    """Folga no dia seguinte após treino pesado, ou após 2 dias seguidos com a
    última corrida em >= 20% de Z4/Z5. Caso contrário, None."""
    ultima_puxada = fracao_ultima >= LIMITE_ZONAS_ALTAS_ATENCAO
    precisa_folga = nivel == NIVEL_TREINO_PESADO or (correu_dia_anterior and ultima_puxada)

    if precisa_folga:
        return data_ultima + timedelta(days=1)
    return None


def avaliar_status_treino(
    corridas: list[TempoEmZonasCorrida],
) -> StatusTreino | None:
    """Avalia a intensidade do treino atual (a corrida mais recente).

    Janela da semana = 7 dias corridos terminando no dia da última corrida
    (inclusive), só com corridas que têm tempo em zona. "Dia anterior" = uma
    corrida no dia imediatamente anterior ao da última; duas corridas no mesmo
    dia não contam como dias seguidos.

    Args:
        corridas: Tempo em zonas de cada corrida, em qualquer ordem.

    Returns:
        StatusTreino; None se a lista estiver vazia. Se a última corrida não tem
        tempo em zona, o nível é sem_dados e não há folga.
    """
    if not corridas:
        return None

    ultima = max(corridas, key=obter_inicio_local)
    data_ultima = ultima.inicio_local.date()
    inicio_janela = data_ultima - timedelta(days=DIAS_JANELA_STATUS_SEMANA - 1)
    dia_anterior = data_ultima - timedelta(days=1)

    corridas_semana: list[TempoEmZonasCorrida] = []
    correu_dia_anterior = False

    for corrida in corridas:
        data_corrida = corrida.inicio_local.date()
        dentro_da_janela = inicio_janela <= data_corrida <= data_ultima
        tem_zona = corrida.segundos_com_zona() > 0
        if dentro_da_janela and tem_zona:
            corridas_semana.append(corrida)

        if data_corrida == dia_anterior:
            correu_dia_anterior = True

    fracao_ultima = calcular_fracao_zonas_altas([ultima])
    fracao_semana = calcular_fracao_zonas_altas(corridas_semana)

    if fracao_ultima is None:
        nivel = NIVEL_TREINO_SEM_DADOS
        data_folga = None
    else:
        nivel = classificar_nivel_treino(fracao_ultima, fracao_semana)
        data_folga = decidir_data_folga(nivel, fracao_ultima, correu_dia_anterior, data_ultima)

    return StatusTreino(
        nivel=nivel,
        data_ultima_corrida=data_ultima,
        fracao_zonas_altas_ultima=fracao_ultima,
        fracao_zonas_altas_semana=fracao_semana,
        corridas_na_semana=len(corridas_semana),
        correu_dia_anterior=correu_dia_anterior,
        data_folga_recomendada=data_folga,
    )
