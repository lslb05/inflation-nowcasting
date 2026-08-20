"""Command-line interface. Logic lives in the package; this only coordinates."""

import argparse
import sys
from datetime import date

import psycopg

from inflation_nowcasting.backtest import (
    DEFAULT_MIN_TRAINING,
    backtest,
    mean_absolute_error,
)
from inflation_nowcasting.config import Settings

_REQUIRED_SERIES = ("CPIAUCSL", "T10YIE", "DCOILWTICO", "MICH")


def _month(text: str) -> date:
    return date.fromisoformat(f"{text}-01")


def _arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="inflation-nowcasting")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("backtest", help="point-in-time backtest of m/m CPI")
    run.add_argument("--start", required=True, type=_month, help="YYYY-MM")
    run.add_argument("--end", required=True, type=_month, help="YYYY-MM")
    run.add_argument("--min-training", type=int, default=DEFAULT_MIN_TRAINING)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _arguments(argv)
    config = Settings()

    try:
        connection = psycopg.connect(config.market_data_dsn)
    except psycopg.OperationalError as error:
        print(
            f"could not connect to public-market-data's Postgres: {error}",
            file=sys.stderr,
        )
        return 2

    with connection:
        results = backtest(
            connection,
            start=args.start,
            end=args.end,
            min_training=args.min_training,
        )
        if not results:
            series = ", ".join(_REQUIRED_SERIES)
            print(
                "no month in the interval has enough data. Ingested in "
                f"public-market-data: {series}? And is there at least "
                f"{args.min_training} months of history before --start?",
                file=sys.stderr,
            )
            return 2

        print("month,nowcast,actual,baseline")
        for result in results:
            print(
                f"{result.month.isoformat()[:7]},{result.nowcast:.5f},"
                f"{result.actual:.5f},{result.baseline:.5f}"
            )

        mae_nowcast, mae_baseline = mean_absolute_error(results)
        print(
            f"# MAE nowcast={mae_nowcast:.5f} baseline={mae_baseline:.5f}",
            file=sys.stderr,
        )
    return 0
