"""Interface de linha de comando. A lógica vive no pacote; aqui só coordena."""

import argparse
import sys
from datetime import date

import psycopg

from nowcasting_inflacao.backtest import (
    TREINO_MINIMO_PADRAO,
    backtest,
    erro_absoluto_medio,
)
from nowcasting_inflacao.config import Settings

_SERIES_NECESSARIAS = ("CPIAUCSL", "T10YIE", "DCOILWTICO", "MICH")


def _mes(texto: str) -> date:
    return date.fromisoformat(f"{texto}-01")


def _argumentos(argv: list[str] | None) -> argparse.Namespace:
    principal = argparse.ArgumentParser(prog="nowcasting-inflacao")
    comandos = principal.add_subparsers(dest="comando", required=True)

    executar = comandos.add_parser("backtest", help="backtest point-in-time do CPI m/m")
    executar.add_argument("--de", required=True, type=_mes, help="AAAA-MM")
    executar.add_argument("--ate", required=True, type=_mes, help="AAAA-MM")
    executar.add_argument("--treino-minimo", type=int, default=TREINO_MINIMO_PADRAO)

    return principal.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    argumentos = _argumentos(argv)
    config = Settings()

    try:
        conexao = psycopg.connect(config.dados_mercado_publico_dsn)
    except psycopg.OperationalError as erro:
        print(
            f"não foi possível conectar ao Postgres do dados-mercado-publico: {erro}",
            file=sys.stderr,
        )
        return 2

    with conexao:
        resultados = backtest(
            conexao,
            de=argumentos.de,
            ate=argumentos.ate,
            treino_minimo=argumentos.treino_minimo,
        )
        if not resultados:
            series = ", ".join(_SERIES_NECESSARIAS)
            print(
                "nenhum mês no intervalo tem dado suficiente. Ingerido no "
                f"dados-mercado-publico: {series}? E há pelo menos "
                f"{argumentos.treino_minimo} meses de histórico antes de --de?",
                file=sys.stderr,
            )
            return 2

        print("mes,nowcast,realizado,baseline")
        for resultado in resultados:
            print(
                f"{resultado.mes.isoformat()[:7]},{resultado.nowcast:.5f},"
                f"{resultado.realizado:.5f},{resultado.baseline:.5f}"
            )

        mae_nowcast, mae_baseline = erro_absoluto_medio(resultados)
        print(
            f"# MAE nowcast={mae_nowcast:.5f} baseline={mae_baseline:.5f}",
            file=sys.stderr,
        )
    return 0
