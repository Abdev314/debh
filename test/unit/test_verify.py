"""Tests for snapshot integrity verification (internal.snapshot.verify)."""

import pytest

from internal.snapshot import verify

PACKAGES = [
    {"name": "alpha", "version": "1.0-1"},
    {"name": "beta", "version": "2.10"},
]


def make_snapshot(packages=PACKAGES):
    snap = {
        "name": "testsnap",
        "timestamp": "2026-01-01T00:00:00",
        "packages": [dict(p) for p in packages],
    }
    snap.update(verify.build_integrity_metadata(snap["packages"]))
    return snap


def test_valid_snapshot_passes():
    assert verify.verify_snapshot(make_snapshot()) is None


def test_checksum_is_deterministic():
    first = verify.compute_checksum(PACKAGES)
    second = verify.compute_checksum([dict(p) for p in PACKAGES])
    assert first == second
    assert len(first) == 64  # sha256 hexdigest


def test_checksum_ignores_key_order_and_whitespace():
    reordered = [{"version": "1.0-1", "name": "alpha"}, {"version": "2.10", "name": "beta"}]
    assert verify.compute_checksum(reordered) == verify.compute_checksum(PACKAGES)


def test_modified_package_data_fails_checksum():
    snap = make_snapshot()
    snap["packages"][0]["version"] = "9.9-9"
    with pytest.raises(verify.SnapshotVerificationError, match="checksum mismatch"):
        verify.verify_snapshot(snap)


def test_incorrect_package_count_fails():
    snap = make_snapshot()
    snap["package_count"] = 99
    with pytest.raises(verify.SnapshotVerificationError, match="package count mismatch"):
        verify.verify_snapshot(snap)


def test_missing_integrity_metadata_reports_legacy_snapshot():
    legacy = {
        "name": "old",
        "timestamp": "2025-01-01T00:00:00",
        "packages": [{"name": "a", "version": "1.0"}],
    }
    with pytest.raises(verify.SnapshotVerificationError, match="legacy snapshot"):
        verify.verify_snapshot(legacy)


def test_malformed_snapshot_not_a_dict():
    with pytest.raises(verify.SnapshotVerificationError, match="not a JSON object"):
        verify.verify_snapshot(["not", "a", "dict"])


def test_malformed_snapshot_missing_fields():
    with pytest.raises(verify.SnapshotVerificationError, match="required field"):
        verify.verify_snapshot({"name": "x"})


def test_malformed_packages_not_a_list():
    snap = make_snapshot()
    snap["packages"] = {"name": "alpha"}
    with pytest.raises(verify.SnapshotVerificationError, match="not a list"):
        verify.verify_snapshot(snap)


def test_malformed_package_entry():
    snap = make_snapshot()
    snap["packages"][1] = {"name": "beta"}  # missing version
    with pytest.raises(verify.SnapshotVerificationError, match="malformed|name.*version"):
        verify.verify_snapshot(snap)


def test_extra_top_level_fields_do_not_affect_checksum():
    snap = make_snapshot()
    snap["note"] = "added later"
    assert verify.verify_snapshot(snap) is None
