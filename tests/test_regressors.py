from datetime import date

import psycopg
import pytest

from inflation_nowcasting.regressors import regressor_vector


def _insert(
    connection: psycopg.Connection, *, series: str, month: date, value: float
) -> None:
    connection.execute(
        """
        INSERT INTO series_vintage
            (fonte, serie, data_evento, data_publicacao, vigente_ate, valor,
             data_disponibilidade)
        VALUES ('fred', %s, %s, %s, '9999-12-31', %s, %s)
        """,
        (series, month, month, value, month),
    )


def test_vector_combines_difference_and_pct_change(
    connection: psycopg.Connection,
) -> None:
    for series, previous, current in (
        ("T10YIE", 2.0, 2.3),
        ("DCOILWTICO", 80.0, 88.0),
        ("MICH", 3.0, 3.4),
    ):
        _insert(connection, series=series, month=date(2024, 1, 1), value=previous)
        _insert(connection, series=series, month=date(2024, 2, 1), value=current)

    vector = regressor_vector(
        connection, cutoff=date(2024, 2, 15), previous_cutoff=date(2024, 1, 15)
    )

    assert vector is not None
    t10yie, dcoilwtico, mich = vector
    assert t10yie == pytest.approx(0.3)
    assert dcoilwtico == pytest.approx(0.1)
    assert mich == pytest.approx(0.4)


def test_vector_is_none_if_a_regressor_is_missing(
    connection: psycopg.Connection,
) -> None:
    _insert(connection, series="T10YIE", month=date(2024, 1, 1), value=2.0)
    _insert(connection, series="T10YIE", month=date(2024, 2, 1), value=2.3)
    # DCOILWTICO and MICH were never ingested.

    vector = regressor_vector(
        connection, cutoff=date(2024, 2, 15), previous_cutoff=date(2024, 1, 15)
    )

    assert vector is None
