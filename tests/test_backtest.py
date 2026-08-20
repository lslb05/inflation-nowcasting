from datetime import date

import psycopg
import pytest

from inflation_nowcasting.backtest import backtest, mean_absolute_error

_FAR_FUTURE = date(9999, 12, 31)


def _next_month(month: date) -> date:
    return date(month.year + month.month // 12, month.month % 12 + 1, 1)


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


def _populate_scenario(connection: psycopg.Connection, *, n_months: int) -> list[date]:
    """Synthetic CPI and regressors, no revisions, with a deterministic trend."""
    month = date(2023, 1, 1)
    months = []
    cpi = 300.0
    for i in range(n_months):
        release = _next_month(month).replace(day=12)
        cpi += 0.5 + 0.01 * i
        _insert(
            connection,
            series="CPIAUCSL",
            event_date=month,
            release_date=release,
            valid_until=_FAR_FUTURE,
            value=cpi,
        )
        for series, base in (("T10YIE", 2.0), ("DCOILWTICO", 80.0), ("MICH", 3.0)):
            _insert(
                connection,
                series=series,
                event_date=month,
                release_date=month,
                valid_until=_FAR_FUTURE,
                value=base + 0.05 * i,
            )
        months.append(month)
        month = _next_month(month)
    return months


def test_backtest_produces_one_result_per_month_with_enough_training(
    connection: psycopg.Connection,
) -> None:
    months = _populate_scenario(connection, n_months=12)

    results = backtest(connection, start=months[8], end=months[8], min_training=5)

    assert len(results) == 1
    assert results[0].month == months[8]


def test_baseline_mae_is_computed_over_the_period(
    connection: psycopg.Connection,
) -> None:
    months = _populate_scenario(connection, n_months=12)

    # Index 6 is left out: only 4 training months are available before it
    # (indices 2-5), below min_training=5. 7, 8 and 9 have enough training.
    results = backtest(connection, start=months[6], end=months[9], min_training=5)
    mae_nowcast, mae_baseline = mean_absolute_error(results)

    assert len(results) == 3
    assert mae_nowcast >= 0
    assert mae_baseline >= 0


def test_data_published_after_the_cutoff_does_not_change_a_past_nowcast(
    connection: psycopg.Connection,
) -> None:
    """The single most important test in this project: inserting a regressor
    reading with `data_publicacao` after the tested month's cutoff must not
    change the nowcast already computed for that month — if it does, the
    pipeline is leaking future information into the backtest.
    """
    months = _populate_scenario(connection, n_months=14)
    tested_month = months[10]

    result_before = backtest(
        connection, start=tested_month, end=tested_month, min_training=5
    )[0]

    # A "revision" of next month's oil price, published well after the
    # tested month's cutoff (day 11 of the following month) — must not
    # influence the nowcast already computed.
    next_month = _next_month(tested_month)
    tested_month_cutoff = next_month.replace(day=11)
    _insert(
        connection,
        series="DCOILWTICO",
        event_date=next_month,
        release_date=tested_month_cutoff.replace(day=28),
        valid_until=_FAR_FUTURE,
        value=99999.0,
    )

    result_after = backtest(
        connection, start=tested_month, end=tested_month, min_training=5
    )[0]

    assert result_after.nowcast == pytest.approx(result_before.nowcast)
    assert result_after.actual == pytest.approx(result_before.actual)
    assert result_after.baseline == pytest.approx(result_before.baseline)
