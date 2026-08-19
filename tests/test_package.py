import pytest

from nowcasting_inflacao.config import Settings


def test_reads_settings_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NOWCASTING_INFLACAO_LOG_LEVEL", "DEBUG")

    assert Settings().log_level == "DEBUG"
