"""Point-in-time reads of the dados-mercado-publico public interface.

Every function here filters by `data_publicacao <= cutoff`: it's that clause
— not a higher-level precaution — that stops a regressor published after the
simulated "today" from leaking into a past nowcast.
"""

from datetime import date

import psycopg


def value_at_cutoff(
    connection: psycopg.Connection, *, series: str, cutoff: date
) -> tuple[date, float] | None:
    """The most recent observation of `series` already known at `cutoff`.

    Returns `(data_evento, valor)` for the vintage in effect on that date —
    not the latest reading available today, but the one an agent standing at
    `cutoff` would have seen.
    """
    row = connection.execute(
        """
        SELECT data_evento, valor
        FROM series_vintage
        WHERE fonte = 'fred' AND serie = %s
          AND data_publicacao <= %s AND vigente_ate >= %s
          AND valor IS NOT NULL
        ORDER BY data_evento DESC
        LIMIT 1
        """,
        (series, cutoff, cutoff),
    ).fetchone()
    return (row[0], row[1]) if row is not None else None


def cpi_first_release(
    connection: psycopg.Connection, *, event_date: date
) -> tuple[date, float] | None:
    """`(data_publicacao, valor)` of the CPI's first vintage for that month.

    This is the number the market saw on release day — not a later revision.
    Comparing the nowcast against a revision would compare it against
    information that didn't exist at forecast time.
    """
    row = connection.execute(
        """
        SELECT data_publicacao, valor
        FROM series_vintage
        WHERE fonte = 'fred' AND serie = 'CPIAUCSL'
          AND data_evento = %s AND valor IS NOT NULL
        ORDER BY data_publicacao ASC
        LIMIT 1
        """,
        (event_date,),
    ).fetchone()
    return (row[0], row[1]) if row is not None else None


def event_value_at_cutoff(
    connection: psycopg.Connection, *, series: str, event_date: date, cutoff: date
) -> float | None:
    """The value of a specific observation, in the vintage in effect at `cutoff`.

    Unlike `value_at_cutoff`: here the month is fixed (e.g. always March's
    CPI), and what varies is which revision of that month was in effect at
    `cutoff` — used to build the m/m change against the prior month's CPI
    exactly as it was known on the nowcast date, not as it is today.
    """
    row = connection.execute(
        """
        SELECT valor
        FROM series_vintage
        WHERE fonte = 'fred' AND serie = %s AND data_evento = %s
          AND data_publicacao <= %s AND vigente_ate >= %s
          AND valor IS NOT NULL
        ORDER BY data_publicacao DESC
        LIMIT 1
        """,
        (series, event_date, cutoff, cutoff),
    ).fetchone()
    return row[0] if row is not None else None


def months_with_cpi(connection: psycopg.Connection) -> list[date]:
    """Every `data_evento` for CPIAUCSL already ingested, in chronological order.

    The backtest's month calendar comes from the data itself, not from a
    release calendar assumed ahead of time.
    """
    rows = connection.execute(
        """
        SELECT DISTINCT data_evento
        FROM series_vintage
        WHERE fonte = 'fred' AND serie = 'CPIAUCSL'
        ORDER BY data_evento
        """
    ).fetchall()
    return [row[0] for row in rows]
