"""Tests for Debian version comparison via apt_pkg.version_compare."""

import pytest

from internal.debian import versions
from internal.snapshot import diff


def test_patch_release_is_newer():
    assert versions.compare_versions("1.10", "1.9") > 0


def test_older_patch_release():
    assert versions.compare_versions("1.9", "1.10") < 0


def test_epoch_beats_version_number():
    assert versions.compare_versions("1:1.0", "2.0") > 0


def test_debian_revision_ordering():
    assert versions.compare_versions("1.0-1", "1.0-2") < 0
    assert versions.compare_versions("1.0-2", "1.0-1") > 0


def test_equal_versions():
    assert versions.compare_versions("2.0", "2.0") == 0


def test_upstream_vs_revision():
    assert versions.compare_versions("1.0", "1.0-1") < 0


@pytest.mark.parametrize(
    "v1, v2, expected",
    [
        ("1.9", "1.10", "upgraded"),
        ("1.10", "1.9", "downgraded"),
        ("1:0.5", "2.0", "downgraded"),  # epoch 1 beats epoch 0: this is a downgrade
        ("2.0", "1:0.5", "upgraded"),
        ("1.0-1", "1.0-2", "upgraded"),
    ],
)
def test_diff_classifies_by_debian_semantics(monkeypatch, tmp_path, v1, v2, expected):
    """diff must use Debian ordering, where e.g. 1.10 > 1.9."""
    monkeypatch.setattr(diff.config, "get_snapshot_dir", lambda: tmp_path)

    def write_snapshot(name, version):
        (tmp_path / f"{name}.json").write_text(
            '{"name": "%s", "timestamp": "2026-01-01T00:00:00",'
            ' "packages": [{"name": "pkg", "version": "%s"}]}' % (name, version)
        )

    write_snapshot("snap1", v1)
    write_snapshot("snap2", v2)

    result = diff.compare_snapshots("snap1", "snap2")
    assert len(result["version_changed"]) == 1
    assert len(result[expected]) == 1
    other = "downgraded" if expected == "upgraded" else "upgraded"
    assert result[other] == []
