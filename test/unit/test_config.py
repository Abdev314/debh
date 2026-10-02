"""Tests for centralized path configuration (internal.debian.config)."""

from pathlib import Path

import pytest

from internal.debian import config
from internal.snapshot import create, diff, restore


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv(config.DEV_MODE_ENV_VAR, raising=False)


def test_prod_snapshot_dir_default():
    assert config.get_snapshot_dir() == Path("/var/lib/debh/snapshots")


def test_dev_mode_uses_home_directory(monkeypatch, tmp_path):
    monkeypatch.setenv(config.DEV_MODE_ENV_VAR, "1")
    monkeypatch.setenv("HOME", str(tmp_path))
    assert config.get_snapshot_dir() == tmp_path / ".debh" / "snapshots"


def test_get_snapshot_path_appends_json():
    assert config.get_snapshot_path("mysnap") == config.get_snapshot_dir() / "mysnap.json"


def test_all_snapshot_modules_resolve_same_directory(monkeypatch, tmp_path):
    """create/diff/restore must all read from the configured directory."""
    monkeypatch.setattr(config, "get_snapshot_dir", lambda: tmp_path)

    snapshot_file = tmp_path / "testsnap.json"
    snapshot_file.write_text('{"name": "testsnap", "packages": []}')

    assert "testsnap" in create.list_snapshots()
    assert restore.load_snapshot("testsnap")["name"] == "testsnap"
    assert diff.load_snapshot_data("testsnap")["name"] == "testsnap"
    assert config.get_snapshot_path("testsnap") == snapshot_file


def test_debh_dev_is_only_read_by_config():
    """No production module other than config may interpret DEBH_DEV directly."""
    repo_root = Path(__file__).resolve().parents[2]
    source_dirs = [repo_root / "cmd", repo_root / "internal", repo_root / "pkg"]
    offenders = []
    for source_dir in source_dirs:
        for path in sorted(source_dir.rglob("*.py")):
            if path == Path(config.__file__).resolve():
                continue
            if config.DEV_MODE_ENV_VAR in path.read_text(encoding="utf-8"):
                offenders.append(str(path.relative_to(repo_root)))
    assert offenders == [], f"DEBH_DEV read outside config.py: {offenders}"
