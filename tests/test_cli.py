from datetime import date

import psycopg
import pytest

from inflation_nowcasting.cli import main

_FAR_FUTURE = date(9999, 12, 31)


def _next_month(month: date) -> date:
    return date(month.year + month.month // 12, month.month % 12 + 1, 1)


def _insert(
    connection: psycopg.Connection,
    *,
    series: str,
    event_date: date,
    release_date: date,
    value: float,
) -> None:
    connection.execute(
        """
        INSERT INTO series_vintage
            (fonte, serie, data_evento, data_publicacao, vigente_ate, valor,
             data_disponibilidade)
        VALUES ('fred', %s, %s, %s, %s, %s, %s)
        """,
        (series, event_date, release_date, _FAR_FUTURE, value, release_date),
    )


def _populate(connection: psycopg.Connection, *, n_months: int) -> list[date]:
    month = date(2023, 1, 1)
    months = []
    cpi = 300.0
    for i in range(n_months):
        cpi += 0.5 + 0.01 * i
        _insert(
            connection,
            series="CPIAUCSL",
            event_date=month,
            release_date=_next_month(month).replace(day=12),
            value=cpi,
        )
        for series, base in (("T10YIE", 2.0), ("DCOILWTICO", 80.0), ("MICH", 3.0)):
            _insert(
                connection,
                series=series,
                event_date=month,
                release_date=month,
                value=base + 0.05 * i,
            )
        months.append(month)
        month = _next_month(month)
    return months


@pytest.fixture(autouse=True)
def dsn_in_environment(monkeypatch: pytest.MonkeyPatch, dsn: str) -> None:
    monkeypatch.setenv("DADOS_MERCADO_PUBLICO_POSTGRES_DSN", dsn)


def test_missing_data_guides_and_exits_with_code_two() -> None:
    assert main(["backtest", "--start", "2023-01", "--end", "2023-12"]) == 2


def test_backtest_prints_csv_and_mae_summary(
    connection: psycopg.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    months = _populate(connection, n_months=8)

    code = main(
        [
            "backtest",
            "--start",
            months[7].isoformat()[:7],
            "--end",
            months[7].isoformat()[:7],
            "--min-training",
            "5",
        ]
    )

    captured = capsys.readouterr()
    assert code == 0
    assert "month,nowcast,actual,baseline" in captured.out
    assert "2023-08" in captured.out
    assert "MAE nowcast=" in captured.err
