"""Application configuration loaded from environment variables."""

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated runtime settings."""

    model_config = SettingsConfigDict(
        env_prefix="INFLATION_NOWCASTING_", extra="ignore"
    )

    log_level: str = "INFO"
    # No prefix on purpose: this is the same variable dados-mercado-publico and
    # vol-implicita-spx use — one DSN configures all three projects.
    market_data_dsn: str = Field(
        default="postgresql://dados:dados@localhost:5433/dados_mercado_publico",
        validation_alias=AliasChoices("DADOS_MERCADO_PUBLICO_POSTGRES_DSN"),
    )
