"""Geração do dashboard.html (arquivo único com dados embutidos em JSON)."""

import json
import math
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from corrida.configuracao import (
    DATA_INICIO_CICLO_ATUAL,
    DIAS_JANELA_FORMA_ATUAL,
    DIAS_JANELA_STATUS_SEMANA,
    FC_TETO_ZONA_3_BPM,
    META_5_KM_M,
    META_10_KM_M,
    META_ZONAS_ALTAS_SEMANA,
    URL_CHART_JS,
)
from corrida.metricas import (
    NIVEL_TREINO_ATENCAO,
    NIVEL_TREINO_LEVE,
    NIVEL_TREINO_PESADO,
    NIVEL_TREINO_SEM_DADOS,
    IndicadoresResumo,
    StatusTreino,
)

ARQUIVO_TEMPLATE = Path(__file__).parent / "template_dashboard.html"

TITULOS_STATUS_TREINO = {
    NIVEL_TREINO_PESADO: "Treino pesado: Z4/Z5 em excesso",
    NIVEL_TREINO_ATENCAO: "Atenção à intensidade",
    NIVEL_TREINO_LEVE: "Na base: Z2/Z3 em dia",
    NIVEL_TREINO_SEM_DADOS: "Sem dados de zona na última corrida",
}
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


def segmentos_para_registros(segmentos: pd.DataFrame | None) -> list[dict]:
    """Converte o DataFrame de segmentos rwd em lista serializável."""
    if segmentos is None or segmentos.empty:
        return []
    registros: list[dict] = []
    for _, linha in segmentos.iterrows():
        registros.append(
            {
                "id_atividade": int(linha["id_atividade"]),
                "ordem": int(linha["ordem"]),
                "tipo_segmento": str(linha["tipo_segmento"]),
                "duracao_s": float(linha["duracao_s"]),
                "distancia_m": float(linha["distancia_m"]),
            }
        )
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
    segmentos: pd.DataFrame | None = None,
    status_treino: StatusTreino | None = None,
) -> dict:
    """Reúne tudo que o HTML precisa em um único dicionário JSON-serializável."""
    if dados_atualizados_em is None:
        texto_atualizacao = None
    else:
        texto_atualizacao = dados_atualizados_em.isoformat(timespec="seconds")

    return {
        "corridas": corridas_para_registros(corridas),
        "segmentos": segmentos_para_registros(segmentos),
        "volume_semanal": volume_para_registros(volume_semanal),
        "indicadores": indicadores_para_dicionario(indicadores),
        "metas_m": {"meta_5_km": META_5_KM_M, "meta_10_km": META_10_KM_M},
        "data_inicio_ciclo_atual": DATA_INICIO_CICLO_ATUAL,
        "status_treino": status_treino_para_dicionario(status_treino),
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


# ---------------------------------------------------------------------------
# Status do treino: texto do card abaixo dos Big Numbers
# ---------------------------------------------------------------------------


def formatar_percentual(fracao: float) -> str:
    """Fração em percentual inteiro: 0.6129 -> "61%"."""
    percentual = fracao * 100
    return f"{percentual:.0f}%"


def formatar_dia_mes(dia: date) -> str:
    """Data curta no formato brasileiro: 26/11."""
    return dia.strftime("%d/%m")


def redigir_itens_status(status: StatusTreino) -> list[str]:
    """Fatos do treino atual, um por linha: última corrida, semana e dias seguidos."""
    itens: list[str] = []
    dia_ultima = formatar_dia_mes(status.data_ultima_corrida)

    if status.fracao_zonas_altas_ultima is not None:
        percentual_ultima = formatar_percentual(status.fracao_zonas_altas_ultima)
        itens.append(f"Última corrida ({dia_ultima}): {percentual_ultima} do tempo em Z4/Z5.")

    if status.fracao_zonas_altas_semana is not None:
        percentual_semana = formatar_percentual(status.fracao_zonas_altas_semana)
        percentual_meta = formatar_percentual(META_ZONAS_ALTAS_SEMANA)
        if status.corridas_na_semana == 1:
            texto_corridas = "1 corrida"
        else:
            texto_corridas = f"{status.corridas_na_semana} corridas"
        itens.append(
            f"{DIAS_JANELA_STATUS_SEMANA} dias até {dia_ultima} ({texto_corridas}): "
            f"{percentual_semana} em Z4/Z5. Alvo do 80/20: até {percentual_meta}."
        )

    if status.correu_dia_anterior:
        dia_anterior = formatar_dia_mes(status.data_ultima_corrida - timedelta(days=1))
        itens.append(f"Correu 2 dias seguidos ({dia_anterior} e {dia_ultima}).")

    return itens


def redigir_recomendacao_status(status: StatusTreino) -> str:
    """Orientação para o próximo treino, conforme folga e nível."""
    orientacao_leve = (
        f"em Z2/Z3 (até {FC_TETO_ZONA_3_BPM} bpm), num ritmo em que dê para conversar"
    )

    if status.data_folga_recomendada is not None:
        dia_folga = formatar_dia_mes(status.data_folga_recomendada)
        return f"Folga em {dia_folga}. Próximo treino leve, {orientacao_leve}."
    if status.nivel == NIVEL_TREINO_ATENCAO:
        return f"Próximo treino leve, {orientacao_leve}, para equilibrar a semana."
    if status.nivel == NIVEL_TREINO_LEVE:
        return "Pode manter: base em Z2/Z3 e no máximo 1 treino forte (Z4/Z5) por semana."
    return "Sem as zonas de FC da Garmin, não dá para avaliar a intensidade."


def status_treino_para_dicionario(status: StatusTreino | None) -> dict | None:
    """Converte o status em dicionário serializável, já com o texto do card."""
    if status is None:
        return None

    if status.data_folga_recomendada is None:
        data_folga = None
    else:
        data_folga = status.data_folga_recomendada.isoformat()

    return {
        "nivel": status.nivel,
        "titulo": TITULOS_STATUS_TREINO[status.nivel],
        "itens": redigir_itens_status(status),
        "recomendacao": redigir_recomendacao_status(status),
        "data_ultima_corrida": status.data_ultima_corrida.isoformat(),
        "fracao_zonas_altas_ultima": status.fracao_zonas_altas_ultima,
        "fracao_zonas_altas_semana": status.fracao_zonas_altas_semana,
        "corridas_na_semana": status.corridas_na_semana,
        "correu_dia_anterior": status.correu_dia_anterior,
        "data_folga_recomendada": data_folga,
    }
