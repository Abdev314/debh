"""Tests for the restore flow: confirmation, integrity, error handling."""

import json

import pytest

from internal.debian import config
from internal.snapshot import restore, verify
from pkg.models.snapshot import Package

SNAPSHOT_PACKAGES = [
    {"name": "alpha", "version": "1.0"},
    {"name": "beta", "version": "2.0"},
]

CURRENT_PACKAGES = [
    Package(name="alpha", version="1.0"),
    Package(name="beta", version="2.0"),
    Package(name="gamma", version="3.0"),  # extra package -> to_remove
]


@pytest.fixture(autouse=True)
def isolated_snapshot_dir(monkeypatch, tmp_path):
    """Point the whole project at a temp snapshot directory."""
    monkeypatch.setattr(config, "get_snapshot_dir", lambda: tmp_path)
    monkeypatch.setattr(
        restore.dpkg, "get_installed_packages", lambda: list(CURRENT_PACKAGES)
    )
    calls = {"apply": []}

    def fake_apply(to_downgrade, to_remove, to_install):
        calls["apply"].append((to_downgrade, to_remove, to_install))
        return True

    monkeypatch.setattr(restore, "apply_changes", fake_apply)
    return tmp_path, calls


def write_snapshot(directory, name, packages=SNAPSHOT_PACKAGES, mutate=None):
    data = {
        "name": name,
        "timestamp": "2026-01-01T00:00:00",
        "packages": [dict(p) for p in packages],
    }
    if mutate:
        mutate(data)
    else:
        data.update(verify.build_integrity_metadata(data["packages"]))
    path = directory / f"{name}.json"
    path.write_text(json.dumps(data))
    return path


def fail_if_prompted(prompt=""):
    raise AssertionError("user must never be prompted in this code path")


def test_yes_skips_confirmation(isolated_snapshot_dir, monkeypatch):
    directory, calls = isolated_snapshot_dir
    write_snapshot(directory, "testsnap")
    monkeypatch.setattr("builtins.input", fail_if_prompted)

    result = restore.restore_snapshot("testsnap", auto_yes=True)

    assert result is True
    assert len(calls["apply"]) == 1


def test_without_yes_prompts_exactly_once(isolated_snapshot_dir, monkeypatch):
    directory, calls = isolated_snapshot_dir
    write_snapshot(directory, "testsnap")

    prompts = []
    monkeypatch.setattr("builtins.input", lambda: prompts.append(1) or "y")

    result = restore.restore_snapshot("testsnap", auto_yes=False)

    assert result is True
    assert len(prompts) == 1
    assert len(calls["apply"]) == 1


def test_declined_confirmation_aborts(isolated_snapshot_dir, monkeypatch):
    directory, calls = isolated_snapshot_dir
    write_snapshot(directory, "testsnap")
    monkeypatch.setattr("builtins.input", lambda: "n")

    result = restore.restore_snapshot("testsnap", auto_yes=False)

    assert result is False
    assert calls["apply"] == []


def test_dry_run_never_prompts_or_applies(isolated_snapshot_dir, monkeypatch):
    directory, calls = isolated_snapshot_dir
    write_snapshot(directory, "testsnap")
    monkeypatch.setattr("builtins.input", fail_if_prompted)

    result = restore.restore_snapshot("testsnap", dry_run=True, auto_yes=False)

    assert result is True
    assert calls["apply"] == []


def test_corrupted_snapshot_cannot_be_restored(isolated_snapshot_dir):
    """Checksum tampering must stop restore before any apt execution."""
    directory, calls = isolated_snapshot_dir

    def tamper(data):
        data["packages"][0]["version"] = "99.0"  # data changed, checksum stale
        data.update(verify.build_integrity_metadata(SNAPSHOT_PACKAGES))

    write_snapshot(directory, "testsnap", mutate=tamper)

    result = restore.restore_snapshot("testsnap", auto_yes=True)

    assert result is False
    assert calls["apply"] == []


def test_package_count_mismatch_blocks_restore(isolated_snapshot_dir):
    directory, calls = isolated_snapshot_dir

    def bad_count(data):
        data.update(verify.build_integrity_metadata(data["packages"]))
        data["package_count"] = 999

    write_snapshot(directory, "testsnap", mutate=bad_count)

    result = restore.restore_snapshot("testsnap", auto_yes=True)

    assert result is False
    assert calls["apply"] == []


def test_legacy_snapshot_without_metadata_is_refused(isolated_snapshot_dir, capsys):
    directory, calls = isolated_snapshot_dir

    legacy = {
        "name": "oldsnap",
        "timestamp": "2025-06-01T00:00:00",
        "packages": [dict(p) for p in SNAPSHOT_PACKAGES],
    }
    (directory / "oldsnap.json").write_text(json.dumps(legacy))

    result = restore.restore_snapshot("oldsnap", auto_yes=True)

    assert result is False
    assert calls["apply"] == []
    assert "legacy snapshot" in capsys.readouterr().out


def test_missing_snapshot_fails_cleanly(isolated_snapshot_dir, capsys):
    result = restore.restore_snapshot("does-not-exist", auto_yes=True)

    assert result is False
    assert "not found" in capsys.readouterr().out


def test_invalid_json_fails_cleanly(isolated_snapshot_dir, capsys):
    directory, _ = isolated_snapshot_dir
    (directory / "broken.json").write_text("{ this is not json")

    result = restore.restore_snapshot("broken", auto_yes=True)

    assert result is False
    assert "Invalid snapshot JSON" in capsys.readouterr().out


def test_malformed_snapshot_structure_fails_cleanly(isolated_snapshot_dir, capsys):
    directory, calls = isolated_snapshot_dir
    (directory / "malformed.json").write_text(
        json.dumps({"name": "malformed", "timestamp": "2026-01-01T00:00:00",
                    "packages": [{"name": "noname-version"}]})
    )

    result = restore.restore_snapshot("malformed", auto_yes=True)

    assert result is False
    assert calls["apply"] == []
    assert "integrity verification" in capsys.readouterr().out
