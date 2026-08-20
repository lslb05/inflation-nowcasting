from datetime import date

import psycopg

from inflation_nowcasting.point_in_time import (
    cpi_first_release,
    event_value_at_cutoff,
    months_with_cpi,
    value_at_cutoff,
)


def _insert(
    connection: psycopg.Connection,
    *,
    series: str,
    event_date: date,
    release_date: date,
    valid_until: date,
    value: float,
) -> None:
    connection.execute(
        """
        INSERT INTO series_vintage
            (fonte, serie, data_evento, data_publicacao, vigente_ate, valor,
             data_disponibilidade)
        VALUES ('fred', %s, %s, %s, %s, %s, %s)
        """,
        (series, event_date, release_date, valid_until, value, release_date),
    )


def test_value_at_cutoff_ignores_vintage_published_after(
    connection: psycopg.Connection,
) -> None:
    """The single most important test in this module: a value published
    AFTER the cutoff must not appear in the query, even if its own month has
    already passed — that's exactly the leak that would invalidate the whole
    backtest.
    """
    _insert(
        connection,
        series="T10YIE",
        event_date=date(2024, 3, 1),
        release_date=date(2024, 3, 1),
        valid_until=date(9999, 12, 31),
        value=2.3,
    )
    _insert(
        connection,
        series="T10YIE",
        event_date=date(2024, 4, 1),
        release_date=date(2024, 4, 1),
        valid_until=date(9999, 12, 31),
        value=99.0,  # absurd future value, just to make a leak obvious
    )

    result = value_at_cutoff(connection, series="T10YIE", cutoff=date(2024, 3, 15))

    assert result == (date(2024, 3, 1), 2.3)


def test_value_at_cutoff_with_no_data_available_is_none(
    connection: psycopg.Connection,
) -> None:
    assert value_at_cutoff(connection, series="T10YIE", cutoff=date(2024, 1, 1)) is None


def test_event_value_at_cutoff_uses_the_revision_in_effect_on_that_date(
    connection: psycopg.Connection,
) -> None:
    # Two vintages of the same month: the original and a later revision.
    _insert(
        connection,
        series="CPIAUCSL",
        event_date=date(2024, 1, 1),
        release_date=date(2024, 2, 13),
        valid_until=date(2024, 3, 12),
        value=300.0,
    )
    _insert(
        connection,
        series="CPIAUCSL",
        event_date=date(2024, 1, 1),
        release_date=date(2024, 3, 13),
        valid_until=date(9999, 12, 31),
        value=300.5,  # revision
    )

    before_revision = event_value_at_cutoff(
        connection,
        series="CPIAUCSL",
        event_date=date(2024, 1, 1),
        cutoff=date(2024, 3, 1),
    )
    after_revision = event_value_at_cutoff(
        connection,
        series="CPIAUCSL",
        event_date=date(2024, 1, 1),
        cutoff=date(2024, 3, 20),
    )

    assert before_revision == 300.0
    assert after_revision == 300.5


def test_cpi_first_release_ignores_revision(connection: psycopg.Connection) -> None:
    _insert(
        connection,
        series="CPIAUCSL",
        event_date=date(2024, 1, 1),
        release_date=date(2024, 2, 13),
        valid_until=date(2024, 3, 12),
        value=300.0,
    )
    _insert(
        connection,
        series="CPIAUCSL",
        event_date=date(2024, 1, 1),
        release_date=date(2024, 3, 13),
        valid_until=date(9999, 12, 31),
        value=300.5,
    )

    result = cpi_first_release(connection, event_date=date(2024, 1, 1))

    assert result == (date(2024, 2, 13), 300.0)


def test_months_with_cpi_orders_chronologically(connection: psycopg.Connection) -> None:
    for month in (date(2024, 3, 1), date(2024, 1, 1), date(2024, 2, 1)):
        _insert(
            connection,
            series="CPIAUCSL",
            event_date=month,
            release_date=month,
            valid_until=date(9999, 12, 31),
            value=300.0,
        )

    assert months_with_cpi(connection) == [
        date(2024, 1, 1),
        date(2024, 2, 1),
        date(2024, 3, 1),
    ]
