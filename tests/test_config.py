import pytest

from src.utils.config import Settings


def test_settings_validate_runtime_requires_remote_credentials() -> None:
    with pytest.raises(ValueError, match="GITHUB_TOKEN"):
        Settings().validate_runtime()


def test_auto_merge_is_disabled_by_default() -> None:
    assert Settings().auto_merge is False
