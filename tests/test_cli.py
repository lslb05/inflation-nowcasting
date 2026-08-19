from datetime import date

import psycopg
import pytest

from nowcasting_inflacao.cli import main

_FAR_FUTURE = date(9999, 12, 31)


def _mes_seguinte(mes: date) -> date:
    return date(mes.year + mes.month // 12, mes.month % 12 + 1, 1)


def _inserir(
    conexao: psycopg.Connection,
    *,
    serie: str,
    data_evento: date,
    data_publicacao: date,
    valor: float,
) -> None:
    conexao.execute(
        """
        INSERT INTO series_vintage
            (fonte, serie, data_evento, data_publicacao, vigente_ate, valor,
             data_disponibilidade)
        VALUES ('fred', %s, %s, %s, %s, %s, %s)
        """,
        (serie, data_evento, data_publicacao, _FAR_FUTURE, valor, data_publicacao),
    )


def _popular(conexao: psycopg.Connection, *, n_meses: int) -> list[date]:
    mes = date(2023, 1, 1)
    meses = []
    cpi = 300.0
    for i in range(n_meses):
        cpi += 0.5 + 0.01 * i
        _inserir(
            conexao,
            serie="CPIAUCSL",
            data_evento=mes,
            data_publicacao=_mes_seguinte(mes).replace(day=12),
            valor=cpi,
        )
        for serie, base in (("T10YIE", 2.0), ("DCOILWTICO", 80.0), ("MICH", 3.0)):
            _inserir(
                conexao,
                serie=serie,
                data_evento=mes,
                data_publicacao=mes,
                valor=base + 0.05 * i,
            )
        meses.append(mes)
        mes = _mes_seguinte(mes)
    return meses


@pytest.fixture(autouse=True)
def dsn_no_ambiente(monkeypatch: pytest.MonkeyPatch, dsn: str) -> None:
    monkeypatch.setenv("DADOS_MERCADO_PUBLICO_POSTGRES_DSN", dsn)


def test_sem_dado_ingerido_orienta_e_sai_com_codigo_dois() -> None:
    assert main(["backtest", "--de", "2023-01", "--ate", "2023-12"]) == 2


def test_backtest_imprime_csv_e_resumo_de_mae(
    conexao: psycopg.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    meses = _popular(conexao, n_meses=8)

    codigo = main(
        [
            "backtest",
            "--de",
            meses[7].isoformat()[:7],
            "--ate",
            meses[7].isoformat()[:7],
            "--treino-minimo",
            "5",
        ]
    )

    capturado = capsys.readouterr()
    assert codigo == 0
    assert "mes,nowcast,realizado,baseline" in capturado.out
    assert "2023-08" in capturado.out
    assert "MAE nowcast=" in capturado.err
