from collections.abc import Iterator

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

# Minimal replica of the public series_vintage schema from public-market-data
# (we don't import that project's schema — this project only reads its public
# interface).
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
def connection(_postgres_dsn: str) -> Iterator[psycopg.Connection]:
    connection = psycopg.connect(_postgres_dsn, autocommit=True)
    connection.execute(_SCHEMA)
    connection.execute("TRUNCATE TABLE series_vintage")
    yield connection
    connection.close()


@pytest.fixture
def dsn(_postgres_dsn: str, connection: psycopg.Connection) -> str:
    return _postgres_dsn
