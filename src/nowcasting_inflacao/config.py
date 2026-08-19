"""Application configuration loaded from environment variables."""

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated runtime settings."""

    model_config = SettingsConfigDict(env_prefix="NOWCASTING_INFLACAO_", extra="ignore")

    log_level: str = "INFO"
    # Sem prefixo de propósito: é a mesma variável que o dados-mercado-publico
    # e o vol-implicita-spx usam — um único DSN configura os três projetos.
    dados_mercado_publico_dsn: str = Field(
        default="postgresql://dados:dados@localhost:5433/dados_mercado_publico",
        validation_alias=AliasChoices("DADOS_MERCADO_PUBLICO_POSTGRES_DSN"),
    )
