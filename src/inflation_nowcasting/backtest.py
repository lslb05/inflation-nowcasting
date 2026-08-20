"""Walk-forward backtest for m/m CPI nowcasting, with a point-in-time cutoff.

Each month's model only sees prior months (never the month itself or the
future), and every value read — target, baseline or regressor — respects the
date it became publicly known. `point_in_time.py` enforces that at the query
level; here the guarantee is simply not requesting anything beyond the
current month's index.
"""

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import psycopg

from inflation_nowcasting.point_in_time import (
    cpi_first_release,
    event_value_at_cutoff,
    months_with_cpi,
)
from inflation_nowcasting.regressors import regressor_vector

DEFAULT_MIN_TRAINING = 36

_Sample = tuple[list[float], float, float]  # (regressors, actual, baseline)


@dataclass(frozen=True)
class MonthResult:
    month: date
    nowcast: float
    actual: float
    baseline: float


def backtest(
    connection: psycopg.Connection,
    *,
    start: date,
    end: date,
    min_training: int = DEFAULT_MIN_TRAINING,
) -> list[MonthResult]:
    months = months_with_cpi(connection)
    samples = _collect_samples(connection, months)

    results = []
    for index, month in enumerate(months):
        if not (start <= month <= end) or index not in samples:
            continue
        training_indices = [i for i in samples if i < index]
        if len(training_indices) < min_training:
            continue

        design = np.array([samples[i][0] for i in training_indices])
        training_target = np.array([samples[i][1] for i in training_indices])
        coefficients = _fit_ols(design, training_target)

        features, actual, baseline = samples[index]
        results.append(
            MonthResult(
                month=month,
                nowcast=_predict(coefficients, features),
                actual=actual,
                baseline=baseline,
            )
        )
    return results


def mean_absolute_error(results: list[MonthResult]) -> tuple[float, float]:
    """(nowcast MAE, baseline MAE) over the backtest months."""
    nowcast_errors = [abs(r.nowcast - r.actual) for r in results]
    baseline_errors = [abs(r.baseline - r.actual) for r in results]
    return _mean(nowcast_errors), _mean(baseline_errors)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _collect_samples(
    connection: psycopg.Connection, months: list[date]
) -> dict[int, _Sample]:
    samples: dict[int, _Sample] = {}
    for index in range(2, len(months)):
        sample = _sample_for_month(connection, months, index)
        if sample is not None:
            samples[index] = sample
    return samples


def _sample_for_month(
    connection: psycopg.Connection, months: list[date], index: int
) -> _Sample | None:
    month, month_m1, month_m2 = months[index], months[index - 1], months[index - 2]

    cutoff = _release_cutoff(connection, month)
    previous_cutoff = _release_cutoff(connection, month_m1)
    released = cpi_first_release(connection, event_date=month)
    if cutoff is None or previous_cutoff is None or released is None:
        return None

    cpi_m1 = event_value_at_cutoff(
        connection, series="CPIAUCSL", event_date=month_m1, cutoff=cutoff
    )
    cpi_m2 = event_value_at_cutoff(
        connection, series="CPIAUCSL", event_date=month_m2, cutoff=cutoff
    )
    if cpi_m1 is None or cpi_m2 is None:
        return None

    features = regressor_vector(
        connection, cutoff=cutoff, previous_cutoff=previous_cutoff
    )
    if features is None:
        return None

    actual = released[1] / cpi_m1 - 1
    baseline = cpi_m1 / cpi_m2 - 1
    return features, actual, baseline


def _release_cutoff(connection: psycopg.Connection, month: date) -> date | None:
    """One day before that month's first CPI release.

    Not an assumed calendar: it comes from the vintage's own `data_publicacao`.
    """
    release = cpi_first_release(connection, event_date=month)
    return release[0] - timedelta(days=1) if release is not None else None


def _fit_ols(design: np.ndarray, target: np.ndarray) -> np.ndarray:
    design_with_intercept = np.column_stack([np.ones(len(design)), design])
    coefficients, *_ = np.linalg.lstsq(design_with_intercept, target, rcond=None)
    return np.asarray(coefficients)


def _predict(coefficients: np.ndarray, features: list[float]) -> float:
    vector = np.concatenate([[1.0], features])
    return float(coefficients @ vector)
