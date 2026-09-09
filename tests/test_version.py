import os
from github_account_manager.version import __version__, get_version, set_version
import github_account_manager
from github_account_manager.config import APP_VERSION


def test_get_version_returns_valid_string():
    v = get_version()
    assert isinstance(v, str)
    assert len(v.split(".")) >= 3
    assert not v.startswith("v")


def test_get_version_respects_env_override(monkeypatch):
    monkeypatch.setenv("APP_VERSION_OVERRIDE", "v9.9.99")
    assert get_version() == "9.9.99"

    monkeypatch.setenv("APP_VERSION_OVERRIDE", "2.0.1")
    assert get_version() == "2.0.1"


def test_init_and_config_match_central_version():
    assert github_account_manager.__version__ == __version__
    assert APP_VERSION == get_version()


def test_set_version_updates_canonical(monkeypatch):
    monkeypatch.delenv("APP_VERSION_OVERRIDE", raising=False)
    original = __version__
    try:
        updated = set_version("0.9.87")
        assert updated == "0.9.87"
        # Reload to verify persistence
        import importlib
        import github_account_manager.version as v_mod
        importlib.reload(v_mod)
        assert v_mod.__version__ == "0.9.87"
    finally:
        set_version(original)
        import importlib
        import github_account_manager.version as v_mod
        importlib.reload(v_mod)
        assert v_mod.__version__ == original


def test_version_txt_matches_canonical():
    from pathlib import Path
    root_v = Path(__file__).resolve().parent.parent / "version.txt"
    assert root_v.exists()
    file_val = root_v.read_text(encoding="utf-8").strip().lstrip("v")
    assert file_val == __version__
    assert get_version() == file_val

