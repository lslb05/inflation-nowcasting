from collections.abc import Iterator

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

# Réplica mínima do schema public de series_vintage do dados-mercado-publico
# (não importamos o schema de lá — este projeto só lê a interface pública).
_SCHEMA = """
CREATE TABLE IF NOT EXISTS series_vintage (
    fonte TEXT NOT NULL,
    serie TEXT NOT NULL,
    data_evento DATE NOT NULL,
    data_publicacao DATE NOT NULL,
    vigente_ate DATE NOT NULL,
    valor DOUBLE PRECISION,
    data_disponibilidade DATE NOT NULL,
    PRIMARY KEY (fonte, serie, data_evento, data_publicacao)
);
"""


@pytest.fixture(scope="session")
def _postgres_dsn() -> Iterator[str]:
    with PostgresContainer("postgres:16-alpine") as container:
        url = container.get_connection_url()
        yield "postgresql://" + url.split("://", 1)[1]


@pytest.fixture
def conexao(_postgres_dsn: str) -> Iterator[psycopg.Connection]:
    conexao = psycopg.connect(_postgres_dsn, autocommit=True)
    conexao.execute(_SCHEMA)
    conexao.execute("TRUNCATE TABLE series_vintage")
    yield conexao
    conexao.close()


@pytest.fixture
def dsn(_postgres_dsn: str, conexao: psycopg.Connection) -> str:
    return _postgres_dsn
