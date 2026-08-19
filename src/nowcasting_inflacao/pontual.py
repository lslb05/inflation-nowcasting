"""Leitura point-in-time da interface pública do dados-mercado-publico.

Toda função aqui filtra por `data_publicacao <= corte`: é essa cláusula —
não um cuidado de mais alto nível — que impede um regressor publicado depois
da data simulada de "hoje" de vazar para dentro de um nowcast passado.
"""

from datetime import date

import psycopg


def valor_no_corte(
    conexao: psycopg.Connection, *, serie: str, corte: date
) -> tuple[date, float] | None:
    """A observação mais recente de `serie` que já era conhecida em `corte`.

    Devolve `(data_evento, valor)` da leitura vigente naquela data — não a
    leitura mais recente disponível hoje, e sim a que um agente parado em
    `corte` teria visto.
    """
    linha = conexao.execute(
        """
        SELECT data_evento, valor
        FROM series_vintage
        WHERE fonte = 'fred' AND serie = %s
          AND data_publicacao <= %s AND vigente_ate >= %s
          AND valor IS NOT NULL
        ORDER BY data_evento DESC
        LIMIT 1
        """,
        (serie, corte, corte),
    ).fetchone()
    return (linha[0], linha[1]) if linha is not None else None


def cpi_primeira_publicacao(
    conexao: psycopg.Connection, *, data_evento: date
) -> tuple[date, float] | None:
    """`(data_publicacao, valor)` da primeira safra do CPI para esse mês.

    É o número que o mercado viu no dia da divulgação — não uma revisão
    posterior. Comparar o nowcast contra uma revisão seria comparar contra
    informação que não existia na hora da previsão.
    """
    linha = conexao.execute(
        """
        SELECT data_publicacao, valor
        FROM series_vintage
        WHERE fonte = 'fred' AND serie = 'CPIAUCSL'
          AND data_evento = %s AND valor IS NOT NULL
        ORDER BY data_publicacao ASC
        LIMIT 1
        """,
        (data_evento,),
    ).fetchone()
    return (linha[0], linha[1]) if linha is not None else None


def valor_do_evento_no_corte(
    conexao: psycopg.Connection, *, serie: str, data_evento: date, corte: date
) -> float | None:
    """O valor de uma observação específica, na safra vigente em `corte`.

    Diferente de `valor_no_corte`: aqui o mês é fixo (ex.: sempre o CPI de
    março), e o que varia é qual revisão daquele mês estava em vigor em
    `corte` — usado para montar a variação m/m com o CPI do mês anterior
    exatamente como era conhecido na data do nowcast, não como é hoje.
    """
    linha = conexao.execute(
        """
        SELECT valor
        FROM series_vintage
        WHERE fonte = 'fred' AND serie = %s AND data_evento = %s
          AND data_publicacao <= %s AND vigente_ate >= %s
          AND valor IS NOT NULL
        ORDER BY data_publicacao DESC
        LIMIT 1
        """,
        (serie, data_evento, corte, corte),
    ).fetchone()
    return linha[0] if linha is not None else None


def meses_com_cpi(conexao: psycopg.Connection) -> list[date]:
    """Todo `data_evento` de CPIAUCSL já ingerido, em ordem cronológica.

    O calendário de meses do backtest vem do próprio dado, não de um
    calendário de divulgação assumido de antemão.
    """
    linhas = conexao.execute(
        """
        SELECT DISTINCT data_evento
        FROM series_vintage
        WHERE fonte = 'fred' AND serie = 'CPIAUCSL'
        ORDER BY data_evento
        """
    ).fetchall()
    return [linha[0] for linha in linhas]
