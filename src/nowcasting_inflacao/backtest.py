"""Backtest walk-forward de nowcasting do CPI m/m, com corte point-in-time.

O modelo de cada mês só vê meses anteriores (nunca o próprio mês nem o
futuro), e cada valor lido — alvo, baseline ou regressor — respeita a data
em que ficou publicamente conhecido. `pontual.py` garante isso na consulta;
aqui a garantia é não pedir nada além do índice do mês corrente.
"""

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import psycopg

from nowcasting_inflacao.pontual import (
    cpi_primeira_publicacao,
    meses_com_cpi,
    valor_do_evento_no_corte,
)
from nowcasting_inflacao.regressores import vetor_regressores

TREINO_MINIMO_PADRAO = 36

_Amostra = tuple[list[float], float, float]  # (regressores, realizado, baseline)


@dataclass(frozen=True)
class ResultadoMes:
    mes: date
    nowcast: float
    realizado: float
    baseline: float


def backtest(
    conexao: psycopg.Connection,
    *,
    de: date,
    ate: date,
    treino_minimo: int = TREINO_MINIMO_PADRAO,
) -> list[ResultadoMes]:
    meses = meses_com_cpi(conexao)
    amostras = _coletar_amostras(conexao, meses)

    resultados = []
    for indice, mes in enumerate(meses):
        if not (de <= mes <= ate) or indice not in amostras:
            continue
        indices_treino = [i for i in amostras if i < indice]
        if len(indices_treino) < treino_minimo:
            continue

        design = np.array([amostras[i][0] for i in indices_treino])
        alvo_treino = np.array([amostras[i][1] for i in indices_treino])
        coeficientes = _ajustar_ols(design, alvo_treino)

        features, realizado, baseline = amostras[indice]
        resultados.append(
            ResultadoMes(
                mes=mes,
                nowcast=_prever(coeficientes, features),
                realizado=realizado,
                baseline=baseline,
            )
        )
    return resultados


def erro_absoluto_medio(resultados: list[ResultadoMes]) -> tuple[float, float]:
    """(MAE do nowcast, MAE do baseline) sobre os meses do backtest."""
    erros_nowcast = [abs(r.nowcast - r.realizado) for r in resultados]
    erros_baseline = [abs(r.baseline - r.realizado) for r in resultados]
    return _media(erros_nowcast), _media(erros_baseline)


def _media(valores: list[float]) -> float:
    return sum(valores) / len(valores)


def _coletar_amostras(
    conexao: psycopg.Connection, meses: list[date]
) -> dict[int, _Amostra]:
    amostras: dict[int, _Amostra] = {}
    for indice in range(2, len(meses)):
        amostra = _amostra_do_mes(conexao, meses, indice)
        if amostra is not None:
            amostras[indice] = amostra
    return amostras


def _amostra_do_mes(
    conexao: psycopg.Connection, meses: list[date], indice: int
) -> _Amostra | None:
    mes, mes_m1, mes_m2 = meses[indice], meses[indice - 1], meses[indice - 2]

    corte = _corte_de_publicacao(conexao, mes)
    corte_anterior = _corte_de_publicacao(conexao, mes_m1)
    publicado = cpi_primeira_publicacao(conexao, data_evento=mes)
    if corte is None or corte_anterior is None or publicado is None:
        return None

    cpi_m1 = valor_do_evento_no_corte(
        conexao, serie="CPIAUCSL", data_evento=mes_m1, corte=corte
    )
    cpi_m2 = valor_do_evento_no_corte(
        conexao, serie="CPIAUCSL", data_evento=mes_m2, corte=corte
    )
    if cpi_m1 is None or cpi_m2 is None:
        return None

    features = vetor_regressores(conexao, corte=corte, corte_anterior=corte_anterior)
    if features is None:
        return None

    realizado = publicado[1] / cpi_m1 - 1
    baseline = cpi_m1 / cpi_m2 - 1
    return features, realizado, baseline


def _corte_de_publicacao(conexao: psycopg.Connection, mes: date) -> date | None:
    """Um dia antes da primeira divulgação do CPI daquele mês.

    Não um calendário assumido: vem da própria `data_publicacao` do vintage.
    """
    publicacao = cpi_primeira_publicacao(conexao, data_evento=mes)
    return publicacao[0] - timedelta(days=1) if publicacao is not None else None


def _ajustar_ols(design: np.ndarray, alvo: np.ndarray) -> np.ndarray:
    design_com_intercepto = np.column_stack([np.ones(len(design)), design])
    coeficientes, *_ = np.linalg.lstsq(design_com_intercepto, alvo, rcond=None)
    return np.asarray(coeficientes)


def _prever(coeficientes: np.ndarray, features: list[float]) -> float:
    vetor = np.concatenate([[1.0], features])
    return float(coeficientes @ vetor)
