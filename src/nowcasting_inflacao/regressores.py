"""Regressores do bridge equation e a transformação usada por cada um."""

from datetime import date
from typing import Literal

import psycopg

from nowcasting_inflacao.pontual import valor_no_corte

Transformacao = Literal["diferenca", "variacao_percentual"]

# Preço (DCOILWTICO) entra em variação percentual; taxa/índice de expectativa
# (T10YIE, MICH), já em pontos percentuais, entra em diferença simples.
REGRESSORES: dict[str, Transformacao] = {
    "T10YIE": "diferenca",
    "DCOILWTICO": "variacao_percentual",
    "MICH": "diferenca",
}


def vetor_regressores(
    conexao: psycopg.Connection, *, corte: date, corte_anterior: date
) -> list[float] | None:
    """Um valor por regressor, na ordem de `REGRESSORES`, ou `None` se faltar dado."""
    valores = []
    for serie, transformacao in REGRESSORES.items():
        atual = valor_no_corte(conexao, serie=serie, corte=corte)
        anterior = valor_no_corte(conexao, serie=serie, corte=corte_anterior)
        if atual is None or anterior is None:
            return None
        valores.append(_transformar(transformacao, atual[1], anterior[1]))
    return valores


def _transformar(transformacao: Transformacao, atual: float, anterior: float) -> float:
    if transformacao == "diferenca":
        return atual - anterior
    return atual / anterior - 1
