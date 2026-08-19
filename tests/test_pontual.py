from datetime import date

import psycopg

from nowcasting_inflacao.pontual import (
    cpi_primeira_publicacao,
    meses_com_cpi,
    valor_do_evento_no_corte,
    valor_no_corte,
)


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


def test_valor_no_corte_ignora_safra_publicada_depois(
    conexao: psycopg.Connection,
) -> None:
    """O teste que mais importa neste módulo: um valor publicado DEPOIS do
    corte não pode aparecer na consulta, mesmo que o mês dele já tenha
    passado — é exatamente esse vazamento que invalidaria o backtest inteiro.
    """
    _inserir(
        conexao,
        serie="T10YIE",
        data_evento=date(2024, 3, 1),
        data_publicacao=date(2024, 3, 1),
        vigente_ate=date(9999, 12, 31),
        valor=2.3,
    )
    _inserir(
        conexao,
        serie="T10YIE",
        data_evento=date(2024, 4, 1),
        data_publicacao=date(2024, 4, 1),
        vigente_ate=date(9999, 12, 31),
        valor=99.0,  # valor futuro absurdo, só pra ficar óbvio se vazar
    )

    resultado = valor_no_corte(conexao, serie="T10YIE", corte=date(2024, 3, 15))

    assert resultado == (date(2024, 3, 1), 2.3)


def test_valor_no_corte_sem_dado_disponivel_e_none(
    conexao: psycopg.Connection,
) -> None:
    assert valor_no_corte(conexao, serie="T10YIE", corte=date(2024, 1, 1)) is None


def test_valor_do_evento_no_corte_usa_a_revisao_vigente_naquela_data(
    conexao: psycopg.Connection,
) -> None:
    # Duas safras do mesmo mês: a original e uma revisão publicada depois.
    _inserir(
        conexao,
        serie="CPIAUCSL",
        data_evento=date(2024, 1, 1),
        data_publicacao=date(2024, 2, 13),
        vigente_ate=date(2024, 3, 12),
        valor=300.0,
    )
    _inserir(
        conexao,
        serie="CPIAUCSL",
        data_evento=date(2024, 1, 1),
        data_publicacao=date(2024, 3, 13),
        vigente_ate=date(9999, 12, 31),
        valor=300.5,  # revisão
    )

    antes_da_revisao = valor_do_evento_no_corte(
        conexao, serie="CPIAUCSL", data_evento=date(2024, 1, 1), corte=date(2024, 3, 1)
    )
    depois_da_revisao = valor_do_evento_no_corte(
        conexao, serie="CPIAUCSL", data_evento=date(2024, 1, 1), corte=date(2024, 3, 20)
    )

    assert antes_da_revisao == 300.0
    assert depois_da_revisao == 300.5


def test_cpi_primeira_publicacao_ignora_revisao(conexao: psycopg.Connection) -> None:
    _inserir(
        conexao,
        serie="CPIAUCSL",
        data_evento=date(2024, 1, 1),
        data_publicacao=date(2024, 2, 13),
        vigente_ate=date(2024, 3, 12),
        valor=300.0,
    )
    _inserir(
        conexao,
        serie="CPIAUCSL",
        data_evento=date(2024, 1, 1),
        data_publicacao=date(2024, 3, 13),
        vigente_ate=date(9999, 12, 31),
        valor=300.5,
    )

    resultado = cpi_primeira_publicacao(conexao, data_evento=date(2024, 1, 1))

    assert resultado == (date(2024, 2, 13), 300.0)


def test_meses_com_cpi_ordena_cronologicamente(conexao: psycopg.Connection) -> None:
    for mes in (date(2024, 3, 1), date(2024, 1, 1), date(2024, 2, 1)):
        _inserir(
            conexao,
            serie="CPIAUCSL",
            data_evento=mes,
            data_publicacao=mes,
            vigente_ate=date(9999, 12, 31),
            valor=300.0,
        )

    assert meses_com_cpi(conexao) == [
        date(2024, 1, 1),
        date(2024, 2, 1),
        date(2024, 3, 1),
    ]
