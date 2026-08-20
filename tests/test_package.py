import pytest

from inflation_nowcasting.config import Settings


def test_reads_settings_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INFLATION_NOWCASTING_LOG_LEVEL", "DEBUG")

    assert Settings().log_level == "DEBUG"
