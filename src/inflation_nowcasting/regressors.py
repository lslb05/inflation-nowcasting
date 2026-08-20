"""Bridge equation regressors and the transform used for each one."""

from datetime import date
from typing import Literal

import psycopg

from inflation_nowcasting.point_in_time import value_at_cutoff

Transform = Literal["difference", "pct_change"]

# Price (DCOILWTICO) enters as percent change; rate/expectation index
# (T10YIE, MICH), already in percentage points, enters as a plain difference.
REGRESSORS: dict[str, Transform] = {
    "T10YIE": "difference",
    "DCOILWTICO": "pct_change",
    "MICH": "difference",
}


def regressor_vector(
    connection: psycopg.Connection, *, cutoff: date, previous_cutoff: date
) -> list[float] | None:
    """One value per regressor, in `REGRESSORS` order, or `None` if data is missing."""
    values = []
    for series, transform in REGRESSORS.items():
        current = value_at_cutoff(connection, series=series, cutoff=cutoff)
        previous = value_at_cutoff(connection, series=series, cutoff=previous_cutoff)
        if current is None or previous is None:
            return None
        values.append(_transform(transform, current[1], previous[1]))
    return values


def _transform(transform: Transform, current: float, previous: float) -> float:
    if transform == "difference":
        return current - previous
    return current / previous - 1
