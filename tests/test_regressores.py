from datetime import date

import psycopg
import pytest

from nowcasting_inflacao.regressores import vetor_regressores


def _inserir(
    conexao: psycopg.Connection, *, serie: str, mes: date, valor: float
) -> None:
    conexao.execute(
        """
        INSERT INTO series_vintage
            (fonte, serie, data_evento, data_publicacao, vigente_ate, valor,
             data_disponibilidade)
        VALUES ('fred', %s, %s, %s, '9999-12-31', %s, %s)
        """,
        (serie, mes, mes, valor, mes),
    )


def test_vetor_combina_diferenca_e_variacao_percentual(
    conexao: psycopg.Connection,
) -> None:
    for serie, anterior, atual in (
        ("T10YIE", 2.0, 2.3),
        ("DCOILWTICO", 80.0, 88.0),
        ("MICH", 3.0, 3.4),
    ):
        _inserir(conexao, serie=serie, mes=date(2024, 1, 1), valor=anterior)
        _inserir(conexao, serie=serie, mes=date(2024, 2, 1), valor=atual)

    vetor = vetor_regressores(
        conexao, corte=date(2024, 2, 15), corte_anterior=date(2024, 1, 15)
    )

    assert vetor is not None
    t10yie, dcoilwtico, mich = vetor
    assert t10yie == pytest.approx(0.3)
    assert dcoilwtico == pytest.approx(0.1)
    assert mich == pytest.approx(0.4)


def test_vetor_e_none_se_faltar_algum_regressor(conexao: psycopg.Connection) -> None:
    _inserir(conexao, serie="T10YIE", mes=date(2024, 1, 1), valor=2.0)
    _inserir(conexao, serie="T10YIE", mes=date(2024, 2, 1), valor=2.3)
    # DCOILWTICO e MICH nunca ingeridos.

    vetor = vetor_regressores(
        conexao, corte=date(2024, 2, 15), corte_anterior=date(2024, 1, 15)
    )

    assert vetor is None
