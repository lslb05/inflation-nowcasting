from datetime import date

import psycopg
import pytest

from nowcasting_inflacao.backtest import backtest, erro_absoluto_medio

_FAR_FUTURE = date(9999, 12, 31)


def _mes_seguinte(mes: date) -> date:
    return date(mes.year + mes.month // 12, mes.month % 12 + 1, 1)


def _inserir(
    conexao: psycopg.Connection,
    *,
    serie: str,
    data_evento: date,
    data_publicacao: date,
    vigente_ate: date,
    valor: float,
) -> None:
    conexao.execute(
        """
        INSERT INTO series_vintage
            (fonte, serie, data_evento, data_publicacao, vigente_ate, valor,
             data_disponibilidade)
        VALUES ('fred', %s, %s, %s, %s, %s, %s)
        """,
        (serie, data_evento, data_publicacao, vigente_ate, valor, data_publicacao),
    )


def _popular_cenario(conexao: psycopg.Connection, *, n_meses: int) -> list[date]:
    """CPI e regressores sintéticos, sem revisão, com tendência determinística."""
    mes = date(2023, 1, 1)
    meses = []
    cpi = 300.0
    for i in range(n_meses):
        pub_cpi = date(mes.year, mes.month, 12)
        pub_cpi = _mes_seguinte(mes).replace(day=12)
        cpi += 0.5 + 0.01 * i
        _inserir(
            conexao,
            serie="CPIAUCSL",
            data_evento=mes,
            data_publicacao=pub_cpi,
            vigente_ate=_FAR_FUTURE,
            valor=cpi,
        )
        for serie, base in (("T10YIE", 2.0), ("DCOILWTICO", 80.0), ("MICH", 3.0)):
            _inserir(
                conexao,
                serie=serie,
                data_evento=mes,
                data_publicacao=mes,
                vigente_ate=_FAR_FUTURE,
                valor=base + 0.05 * i,
            )
        meses.append(mes)
        mes = _mes_seguinte(mes)
    return meses


def test_backtest_produz_um_resultado_por_mes_com_treino_suficiente(
    conexao: psycopg.Connection,
) -> None:
    meses = _popular_cenario(conexao, n_meses=12)

    resultados = backtest(conexao, de=meses[8], ate=meses[8], treino_minimo=5)

    assert len(resultados) == 1
    assert resultados[0].mes == meses[8]


def test_mae_do_baseline_e_calculado_sobre_o_periodo(
    conexao: psycopg.Connection,
) -> None:
    meses = _popular_cenario(conexao, n_meses=12)

    # Índice 6 fica de fora: só há 4 meses de treino disponíveis antes dele
    # (índices 2-5), abaixo do treino_minimo=5. 7, 8 e 9 têm treino suficiente.
    resultados = backtest(conexao, de=meses[6], ate=meses[9], treino_minimo=5)
    mae_nowcast, mae_baseline = erro_absoluto_medio(resultados)

    assert len(resultados) == 3
    assert mae_nowcast >= 0
    assert mae_baseline >= 0


def test_dado_publicado_depois_do_corte_nao_muda_o_nowcast_do_passado(
    conexao: psycopg.Connection,
) -> None:
    """O teste que mais importa neste projeto inteiro: inserir uma leitura de
    regressor com `data_publicacao` depois do corte do mês testado não pode
    alterar o nowcast já calculado para aquele mês — se alterar, o pipeline
    está vazando informação futura para dentro do backtest.
    """
    meses = _popular_cenario(conexao, n_meses=14)
    mes_testado = meses[10]

    resultado_antes = backtest(
        conexao, de=mes_testado, ate=mes_testado, treino_minimo=5
    )[0]

    # "Revisão" do petróleo do mês seguinte ao testado, publicada bem depois
    # do corte de `mes_testado` (dia 11 do mês seguinte) — não pode
    # influenciar o nowcast já calculado.
    mes_seguinte = _mes_seguinte(mes_testado)
    corte_do_mes_testado = mes_seguinte.replace(day=11)
    _inserir(
        conexao,
        serie="DCOILWTICO",
        data_evento=mes_seguinte,
        data_publicacao=corte_do_mes_testado.replace(day=28),
        vigente_ate=_FAR_FUTURE,
        valor=99999.0,
    )

    resultado_depois = backtest(
        conexao, de=mes_testado, ate=mes_testado, treino_minimo=5
    )[0]

    assert resultado_depois.nowcast == pytest.approx(resultado_antes.nowcast)
    assert resultado_depois.realizado == pytest.approx(resultado_antes.realizado)
    assert resultado_depois.baseline == pytest.approx(resultado_antes.baseline)
