"""Testes do status do treino (regra 80/20 por zonas de FC) e do texto do card."""

import math
from datetime import date, datetime, timedelta

from corrida.gerar_html import status_treino_para_dicionario
from corrida.metricas import (
    NIVEL_TREINO_ATENCAO,
    NIVEL_TREINO_LEVE,
    NIVEL_TREINO_PESADO,
    NIVEL_TREINO_SEM_DADOS,
    TempoEmZonasCorrida,
    avaliar_status_treino,
)

INICIO_ULTIMA = datetime(2026, 11, 26, 17, 0, 0)


def criar_corrida(
    inicio_local: datetime,
    segundos_zonas_altas: float,
    segundos_base: float,
) -> TempoEmZonasCorrida:
    """Corrida com `segundos_base` em Z2 e `segundos_zonas_altas` em Z4."""
    return TempoEmZonasCorrida(
        inicio_local=inicio_local,
        segundos_zona_1=0.0,
        segundos_zona_2=segundos_base,
        segundos_zona_3=0.0,
        segundos_zona_4=segundos_zonas_altas,
        segundos_zona_5=0.0,
    )


def criar_corrida_sem_zona(inicio_local: datetime, valor_ausente: float | None) -> TempoEmZonasCorrida:
    return TempoEmZonasCorrida(
        inicio_local=inicio_local,
        segundos_zona_1=valor_ausente,
        segundos_zona_2=valor_ausente,
        segundos_zona_3=valor_ausente,
        segundos_zona_4=valor_ausente,
        segundos_zona_5=valor_ausente,
    )


def dias_antes(dias: int) -> datetime:
    return INICIO_ULTIMA - timedelta(days=dias)


class TestNivel:
    def test_lista_vazia_nao_tem_status(self) -> None:
        assert avaliar_status_treino([]) is None

    def test_40_por_cento_exatos_e_pesado(self) -> None:
        status = avaliar_status_treino([criar_corrida(INICIO_ULTIMA, 40, 60)])
        assert status.nivel == NIVEL_TREINO_PESADO

    def test_logo_abaixo_de_40_e_atencao(self) -> None:
        status = avaliar_status_treino([criar_corrida(INICIO_ULTIMA, 39.9, 60.1)])
        assert status.nivel == NIVEL_TREINO_ATENCAO

    def test_20_por_cento_exatos_na_ultima_e_atencao(self) -> None:
        status = avaliar_status_treino([criar_corrida(INICIO_ULTIMA, 20, 80)])
        assert status.nivel == NIVEL_TREINO_ATENCAO

    def test_logo_abaixo_de_20_e_leve(self) -> None:
        status = avaliar_status_treino([criar_corrida(INICIO_ULTIMA, 19.9, 80.1)])
        assert status.nivel == NIVEL_TREINO_LEVE

    def test_semana_acima_de_20_com_ultima_leve_e_atencao(self) -> None:
        # semana: (50 + 10) / (100 + 100) = 30%; última: 10%
        corridas = [
            criar_corrida(dias_antes(3), 50, 50),
            criar_corrida(INICIO_ULTIMA, 10, 90),
        ]
        status = avaliar_status_treino(corridas)
        assert math.isclose(status.fracao_zonas_altas_semana, 0.30)
        assert status.nivel == NIVEL_TREINO_ATENCAO

    def test_semana_em_20_exatos_ainda_cumpre_80_20(self) -> None:
        # semana: (30 + 10) / (100 + 100) = 20%; última: 10%
        corridas = [
            criar_corrida(dias_antes(3), 30, 70),
            criar_corrida(INICIO_ULTIMA, 10, 90),
        ]
        status = avaliar_status_treino(corridas)
        assert math.isclose(status.fracao_zonas_altas_semana, 0.20)
        assert status.nivel == NIVEL_TREINO_LEVE

    def test_ultima_e_a_mais_recente_mesmo_fora_de_ordem(self) -> None:
        corridas = [
            criar_corrida(INICIO_ULTIMA, 70, 30),
            criar_corrida(dias_antes(2), 0, 100),
        ]
        status = avaliar_status_treino(corridas)
        assert status.data_ultima_corrida == date(2026, 11, 26)
        assert status.nivel == NIVEL_TREINO_PESADO


class TestJanelaSemana:
    def test_seis_dias_antes_entra_e_sete_nao(self) -> None:
        corridas = [
            criar_corrida(dias_antes(7), 100, 0),
            criar_corrida(dias_antes(6), 0, 100),
            criar_corrida(INICIO_ULTIMA, 0, 100),
        ]
        status = avaliar_status_treino(corridas)
        assert status.corridas_na_semana == 2
        assert status.fracao_zonas_altas_semana == 0.0

    def test_corrida_sem_zona_fica_fora_da_semana(self) -> None:
        corridas = [
            criar_corrida_sem_zona(dias_antes(2), None),
            criar_corrida(INICIO_ULTIMA, 10, 90),
        ]
        status = avaliar_status_treino(corridas)
        assert status.corridas_na_semana == 1
        assert math.isclose(status.fracao_zonas_altas_semana, 0.10)


class TestFolga:
    def test_pesado_pede_folga_no_dia_seguinte(self) -> None:
        status = avaliar_status_treino([criar_corrida(INICIO_ULTIMA, 61, 39)])
        assert status.data_folga_recomendada == date(2026, 11, 27)

    def test_dias_seguidos_com_ultima_puxada_pede_folga(self) -> None:
        corridas = [
            criar_corrida(dias_antes(1), 0, 100),
            criar_corrida(INICIO_ULTIMA, 25, 75),
        ]
        status = avaliar_status_treino(corridas)
        assert status.correu_dia_anterior is True
        assert status.nivel == NIVEL_TREINO_ATENCAO
        assert status.data_folga_recomendada == date(2026, 11, 27)

    def test_dias_seguidos_com_ultima_leve_nao_pede_folga(self) -> None:
        corridas = [
            criar_corrida(dias_antes(1), 0, 100),
            criar_corrida(INICIO_ULTIMA, 19, 81),
        ]
        status = avaliar_status_treino(corridas)
        assert status.correu_dia_anterior is True
        assert status.data_folga_recomendada is None

    def test_duas_corridas_no_mesmo_dia_nao_sao_dias_seguidos(self) -> None:
        corridas = [
            criar_corrida(INICIO_ULTIMA - timedelta(hours=8), 0, 100),
            criar_corrida(INICIO_ULTIMA, 25, 75),
        ]
        status = avaliar_status_treino(corridas)
        assert status.correu_dia_anterior is False
        assert status.data_folga_recomendada is None

    def test_atencao_sem_dia_anterior_nao_pede_folga(self) -> None:
        corridas = [
            criar_corrida(dias_antes(2), 0, 100),
            criar_corrida(INICIO_ULTIMA, 25, 75),
        ]
        status = avaliar_status_treino(corridas)
        assert status.data_folga_recomendada is None


class TestSemDados:
    def test_ultima_sem_zona_none_fica_sem_dados(self) -> None:
        corridas = [
            criar_corrida(dias_antes(1), 50, 50),
            criar_corrida_sem_zona(INICIO_ULTIMA, None),
        ]
        status = avaliar_status_treino(corridas)
        assert status.nivel == NIVEL_TREINO_SEM_DADOS
        assert status.fracao_zonas_altas_ultima is None
        assert status.data_folga_recomendada is None

    def test_nan_conta_como_ausente(self) -> None:
        status = avaliar_status_treino([criar_corrida_sem_zona(INICIO_ULTIMA, float("nan"))])
        assert status.nivel == NIVEL_TREINO_SEM_DADOS
        assert status.corridas_na_semana == 0
        assert status.fracao_zonas_altas_semana is None


class TestTextoCard:
    def test_sem_status_vira_nulo(self) -> None:
        assert status_treino_para_dicionario(None) is None

    def test_cenario_pesado_de_26_11(self) -> None:
        # Espelha 26/11/2026: última 61% em Z4/Z5, correu no dia anterior.
        corridas = [
            criar_corrida(dias_antes(1), 4, 96),
            criar_corrida(INICIO_ULTIMA, 61, 39),
        ]
        dicionario = status_treino_para_dicionario(avaliar_status_treino(corridas))
        assert dicionario["nivel"] == NIVEL_TREINO_PESADO
        assert dicionario["titulo"] == "Treino pesado: Z4/Z5 em excesso"
        assert dicionario["itens"][0] == "Última corrida (26/11): 61% do tempo em Z4/Z5."
        assert dicionario["itens"][1] == (
            "7 dias até 26/11 (2 corridas): 32% em Z4/Z5. Alvo do 80/20: até 20%."
        )
        assert dicionario["itens"][2] == "Correu 2 dias seguidos (25/11 e 26/11)."
        assert dicionario["recomendacao"].startswith("Folga em 27/11. Próximo treino leve")
        assert dicionario["data_folga_recomendada"] == "2026-11-27"

    def test_leve_sem_dia_anterior(self) -> None:
        dicionario = status_treino_para_dicionario(
            avaliar_status_treino([criar_corrida(INICIO_ULTIMA, 5, 95)])
        )
        assert dicionario["itens"][1].startswith("7 dias até 26/11 (1 corrida): 5%")
        assert len(dicionario["itens"]) == 2
        assert dicionario["recomendacao"].startswith("Pode manter")
