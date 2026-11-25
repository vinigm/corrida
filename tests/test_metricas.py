"""Testes das métricas puras de corrida."""

from datetime import date, datetime, timedelta, timezone

import pandas as pd
import pytest

from corrida.metricas import (
    calcular_eficiencia,
    calcular_indicadores,
    calcular_metricas_segmentos,
    calcular_pace_min_km,
    calcular_progresso_meta,
    calcular_volume_semanal,
)
from corrida.modelos import SegmentoRwd

INICIO_BASE = datetime(2026, 9, 19, 18, 0, 0, tzinfo=timezone.utc)


def criar_segmento(
    tipo: str,
    distancia_m: float,
    duracao_s: float,
    deslocamento_s: float = 0.0,
) -> SegmentoRwd:
    return SegmentoRwd(
        tipo=tipo,
        inicio_utc=INICIO_BASE + timedelta(seconds=deslocamento_s),
        duracao_s=duracao_s,
        distancia_m=distancia_m,
    )


def criar_registros(
    velocidades: list[float | None],
    frequencias: list[float | None],
) -> pd.DataFrame:
    datas: list[datetime] = []
    for indice in range(len(velocidades)):
        datas.append(INICIO_BASE + timedelta(seconds=indice))
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(datas, utc=True),
            "velocidade_m_s": pd.to_numeric(pd.Series(velocidades, dtype="float64")),
            "fc_bpm": pd.to_numeric(pd.Series(frequencias, dtype="float64")),
        }
    )


class TestMetricasSegmentos:
    def test_sem_segmentos_rwd_tudo_nulo_nunca_zero(self) -> None:
        metricas = calcular_metricas_segmentos([])
        assert metricas.maior_trecho_continuo_m is None
        assert metricas.distancia_correndo_m is None
        assert metricas.tempo_correndo_s is None
        assert metricas.pct_tempo_correndo is None
        assert metricas.pace_correndo_min_km is None
        assert metricas.n_segmentos_correndo == 0

    def test_segmento_unico_de_corrida(self) -> None:
        segmentos = [criar_segmento("rwd_run", 1000.0, 300.0)]
        metricas = calcular_metricas_segmentos(segmentos)
        assert metricas.maior_trecho_continuo_m == 1000.0
        assert metricas.distancia_correndo_m == 1000.0
        assert metricas.pct_tempo_correndo == pytest.approx(1.0)
        assert metricas.pace_correndo_min_km == pytest.approx(5.0)
        assert metricas.distancia_caminhando_m == 0.0

    def test_maior_trecho_nao_soma_segmentos_vizinhos(self) -> None:
        segmentos = [
            criar_segmento("rwd_run", 500.0, 150.0),
            criar_segmento("rwd_walk", 100.0, 80.0),
            criar_segmento("rwd_run", 513.83, 194.0),
            criar_segmento("rwd_run", 300.0, 90.0),
        ]
        metricas = calcular_metricas_segmentos(segmentos)
        assert metricas.maior_trecho_continuo_m == pytest.approx(513.83)
        assert metricas.distancia_correndo_m == pytest.approx(1313.83)
        assert metricas.n_segmentos_correndo == 3

    def test_pct_tempo_correndo_inclui_caminhada_e_parado(self) -> None:
        segmentos = [
            criar_segmento("rwd_run", 600.0, 200.0),
            criar_segmento("rwd_walk", 100.0, 60.0),
            criar_segmento("rwd_stand", 0.0, 40.0),
        ]
        metricas = calcular_metricas_segmentos(segmentos)
        assert metricas.pct_tempo_correndo == pytest.approx(200.0 / 300.0)
        assert metricas.tempo_parado_s == 40.0

    def test_so_caminhada_tem_zero_correndo_e_pace_nulo(self) -> None:
        segmentos = [criar_segmento("rwd_walk", 400.0, 300.0)]
        metricas = calcular_metricas_segmentos(segmentos)
        assert metricas.maior_trecho_continuo_m == 0.0
        assert metricas.pct_tempo_correndo == 0.0
        assert metricas.pace_correndo_min_km is None

    def test_pace_com_distancia_zero_e_nulo(self) -> None:
        assert calcular_pace_min_km(100.0, 0.0) is None


class TestEficiencia:
    def test_calculo_basico(self) -> None:
        # 3 m/s = 180 m/min; FC 150 bpm -> 1,2 m/min por bpm.
        registros = criar_registros([3.0] * 11, [150.0] * 11)
        segmentos = [criar_segmento("rwd_run", 30.0, 10.0)]
        assert calcular_eficiencia(registros, segmentos) == pytest.approx(1.2)

    def test_fc_nula_fica_fora(self) -> None:
        # O registro com FC nula (velocidade 10) não pode entrar na média.
        registros = criar_registros([3.0, 3.0, 10.0, 3.0], [150.0, 150.0, None, 150.0])
        segmentos = [criar_segmento("rwd_run", 9.0, 3.0)]
        assert calcular_eficiencia(registros, segmentos) == pytest.approx(1.2)

    def test_velocidade_zero_fica_fora(self) -> None:
        # Com o zero dentro, a média seria 2,25 m/s -> 0,9; sem ele, 3 m/s -> 1,2.
        registros = criar_registros([3.0, 0.0, 3.0, 3.0], [150.0] * 4)
        segmentos = [criar_segmento("rwd_run", 9.0, 3.0)]
        assert calcular_eficiencia(registros, segmentos) == pytest.approx(1.2)

    def test_fc_zero_fica_fora(self) -> None:
        # O registro com FC zero (velocidade 10) não pode entrar na média.
        registros = criar_registros([3.0, 3.0, 10.0], [150.0, 150.0, 0.0])
        segmentos = [criar_segmento("rwd_run", 9.0, 2.0)]
        assert calcular_eficiencia(registros, segmentos) == pytest.approx(1.2)

    def test_usa_media_da_fc_e_nao_maxima(self) -> None:
        # FC média = 150 -> 1,2; se usasse a máxima (180) daria 1,0.
        registros = criar_registros([3.0, 3.0], [120.0, 180.0])
        segmentos = [criar_segmento("rwd_run", 6.0, 1.0)]
        assert calcular_eficiencia(registros, segmentos) == pytest.approx(1.2)

    def test_todas_as_fc_nulas_retorna_nulo(self) -> None:
        registros = criar_registros([3.0, 3.0], [None, None])
        segmentos = [criar_segmento("rwd_run", 6.0, 1.0)]
        assert calcular_eficiencia(registros, segmentos) is None

    def test_sem_segmento_de_corrida_retorna_nulo(self) -> None:
        registros = criar_registros([3.0, 3.0], [150.0, 150.0])
        segmentos = [criar_segmento("rwd_walk", 6.0, 1.0)]
        assert calcular_eficiencia(registros, segmentos) is None

    def test_sem_segmentos_retorna_nulo(self) -> None:
        registros = criar_registros([3.0], [150.0])
        assert calcular_eficiencia(registros, []) is None

    def test_registros_vazios_retornam_nulo(self) -> None:
        registros = criar_registros([], [])
        segmentos = [criar_segmento("rwd_run", 6.0, 1.0)]
        assert calcular_eficiencia(registros, segmentos) is None

    def test_registros_fora_da_janela_sao_ignorados(self) -> None:
        # Janela cobre segundos 0..2; registro do segundo 3 (velocidade 9) fica fora.
        registros = criar_registros([3.0, 3.0, 3.0, 9.0], [150.0] * 4)
        segmentos = [criar_segmento("rwd_run", 9.0, 2.0)]
        assert calcular_eficiencia(registros, segmentos) == pytest.approx(1.2)

    def test_janelas_adjacentes_nao_contam_registro_duas_vezes(self) -> None:
        registros = criar_registros([3.0, 3.0, 3.0, 6.0, 6.0], [150.0] * 5)
        segmentos = [
            criar_segmento("rwd_run", 6.0, 2.0, deslocamento_s=0.0),
            criar_segmento("rwd_run", 12.0, 2.0, deslocamento_s=2.0),
        ]
        # Registros 0..4 entram uma vez cada: velocidade média = 21/5 = 4,2.
        esperado = (4.2 * 60.0) / 150.0
        assert calcular_eficiencia(registros, segmentos) == pytest.approx(esperado)


class TestVolumeSemanal:
    def test_lista_vazia(self) -> None:
        volume = calcular_volume_semanal([], [], date(2026, 9, 20))
        assert volume.empty
        assert list(volume.columns) == ["semana_inicio", "km_total", "n_corridas"]

    def test_inclui_semanas_com_zero(self) -> None:
        datas = [date(2026, 9, 1), date(2026, 9, 17)]
        volume = calcular_volume_semanal(datas, [5000.0, 3000.0], date(2026, 9, 20))
        assert list(volume["semana_inicio"]) == [
            date(2026, 8, 31),
            date(2026, 9, 7),
            date(2026, 9, 14),
        ]
        assert list(volume["n_corridas"]) == [1, 0, 1]
        assert list(volume["km_total"]) == pytest.approx([5.0, 0.0, 3.0])

    def test_estende_ate_a_semana_de_hoje(self) -> None:
        volume = calcular_volume_semanal(
            [date(2026, 9, 1)], [5000.0], date(2026, 9, 16)
        )
        assert volume["semana_inicio"].iloc[-1] == date(2026, 9, 14)
        assert volume["n_corridas"].iloc[-1] == 0

    def test_duas_corridas_na_mesma_semana_somam(self) -> None:
        datas = [date(2026, 9, 14), date(2026, 9, 20)]  # segunda e domingo
        volume = calcular_volume_semanal(datas, [2000.0, 3000.0], date(2026, 9, 20))
        assert len(volume) == 1
        assert volume["km_total"].iloc[0] == pytest.approx(5.0)
        assert volume["n_corridas"].iloc[0] == 2


class TestIndicadores:
    HOJE = date(2026, 9, 25)

    def test_lista_vazia(self) -> None:
        indicadores = calcular_indicadores([], [], [], self.HOJE)
        assert indicadores.maior_trecho_continuo_m is None
        assert indicadores.maior_distancia_total_m is None
        assert indicadores.data_ultima_corrida is None
        assert indicadores.dias_desde_ultima_corrida is None
        assert indicadores.corridas_ultimos_30_dias == 0
        assert indicadores.progresso_meta_5_km == 0.0

    def test_trechos_nulos_nao_viram_zero(self) -> None:
        indicadores = calcular_indicadores(
            [date(2026, 9, 1)], [3000.0], [None], self.HOJE
        )
        assert indicadores.maior_trecho_continuo_m is None
        assert indicadores.maior_distancia_total_m == 3000.0

    def test_progresso_e_janela_de_30_dias(self) -> None:
        datas = [date(2026, 8, 26), date(2026, 8, 27), date(2026, 9, 19)]
        indicadores = calcular_indicadores(
            datas, [4000.0, 5540.0, 3000.0], [1000.0, 2500.0, 513.83], self.HOJE
        )
        assert indicadores.maior_trecho_continuo_m == 2500.0
        assert indicadores.progresso_meta_5_km == pytest.approx(0.5)
        assert indicadores.progresso_meta_10_km == pytest.approx(0.25)
        assert indicadores.dias_desde_ultima_corrida == 6
        # 26/08 está a 30 dias de 25/09: fora; 27/08 (29 dias) e 19/09: dentro.
        assert indicadores.corridas_ultimos_30_dias == 2

    def test_progresso_limitado_a_um(self) -> None:
        assert calcular_progresso_meta(12000.0, 10000.0) == 1.0
        assert calcular_progresso_meta(None, 5000.0) == 0.0
        assert calcular_progresso_meta(5000.0, 5000.0) == 1.0


class TestFormaAtual:
    HOJE = date(2026, 11, 25)

    def test_89_dias_entra_e_90_dias_fica_fora(self) -> None:
        data_89_dias = self.HOJE - timedelta(days=89)
        data_90_dias = self.HOJE - timedelta(days=90)

        so_89 = calcular_indicadores([data_89_dias], [3000.0], [700.0], self.HOJE)
        assert so_89.maior_trecho_forma_atual_m == 700.0

        so_90 = calcular_indicadores([data_90_dias], [3000.0], [700.0], self.HOJE)
        assert so_90.maior_trecho_forma_atual_m is None

    def test_janela_vazia_da_none_nunca_zero(self) -> None:
        indicadores = calcular_indicadores([], [], [], self.HOJE)
        assert indicadores.maior_trecho_forma_atual_m is None
        assert indicadores.progresso_meta_5_km == 0.0

    def test_corrida_na_janela_sem_rwd_nao_vira_zero(self) -> None:
        indicadores = calcular_indicadores(
            [self.HOJE - timedelta(days=5)], [3000.0], [None], self.HOJE
        )
        assert indicadores.maior_trecho_forma_atual_m is None

    def test_recorde_fora_da_janela_e_forma_atual_dentro(self) -> None:
        datas = [date(2025, 5, 18), date(2026, 9, 16), date(2026, 9, 19)]
        trechos = [5521.38, 553.40, 513.83]
        indicadores = calcular_indicadores(datas, [5540.0, 4740.0, 2918.5], trechos, self.HOJE)
        assert indicadores.maior_trecho_continuo_m == 5521.38
        assert indicadores.data_recorde_trecho == date(2025, 5, 18)
        assert indicadores.maior_trecho_forma_atual_m == 553.40
        assert indicadores.progresso_meta_5_km == pytest.approx(553.40 / 5000.0)
        assert indicadores.progresso_meta_10_km == pytest.approx(553.40 / 10000.0)

    def test_corrida_no_futuro_nao_entra_na_janela(self) -> None:
        indicadores = calcular_indicadores(
            [self.HOJE + timedelta(days=1)], [3000.0], [900.0], self.HOJE
        )
        assert indicadores.maior_trecho_forma_atual_m is None
        assert indicadores.maior_trecho_continuo_m == 900.0
