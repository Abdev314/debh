"""End-to-end CLI tests in DEBH_DEV mode against a temporary HOME.

These exercise the real command dispatch, JSON files on disk, and the
sudo gate, without ever touching the system package state: the only
restore modes used are --dry-run or pre-verification failures.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MAIN = REPO_ROOT / "cmd" / "debh" / "main.py"


@pytest.fixture()
def cli(tmp_path):
    env = os.environ.copy()
    env["DEBH_DEV"] = "1"
    env["HOME"] = str(tmp_path)
    # Overriding HOME moves Python's user-site dir; keep the real one
    # (where python3-apt/pytest live) visible to the child interpreter.
    env["PYTHONUSERBASE"] = str(Path.home() / ".local")

    def run(*args, stdin=subprocess.DEVNULL):
        return subprocess.run(
            [sys.executable, str(MAIN), *args],
            capture_output=True,
            text=True,
            stdin=stdin,
            env=env,
            cwd=REPO_ROOT,
        )

    run.snapshot_dir = tmp_path / ".debh" / "snapshots"
    return run


def test_snapshot_create_writes_integrity_metadata(cli):
    result = cli("snapshot", "itest")
    assert result.returncode == 0, result.stderr

    data = json.loads((cli.snapshot_dir / "itest.json").read_text())
    assert "package_count" in data
    assert "checksum" in data
    assert data["package_count"] == len(data["packages"])


def test_list_and_show_find_created_snapshot(cli):
    assert cli("snapshot", "itest").returncode == 0

    listing = cli("list")
    assert "itest" in listing.stdout

    verbose = cli("list", "--verbose")
    assert "packages" in verbose.stdout

    show = cli("show", "itest")
    assert "Packages:" in show.stdout


def test_diff_reports_no_differences_for_identical_snapshots(cli):
    assert cli("snapshot", "itest").returncode == 0

    result = cli("diff", "itest", "itest")

    assert result.returncode == 0
    assert "No differences" in result.stdout


def test_restore_dry_run_yes_never_prompts(cli):
    assert cli("snapshot", "itest").returncode == 0

    # stdin is DEVNULL: any input() call would hit EOF and crash.
    result = cli("restore", "itest", "--dry-run", "--yes")

    assert result.returncode == 0, result.stderr
    assert "DRY RUN" in result.stdout


def test_restore_real_run_requires_root(cli):
    """Non-root real restore must stop at the sudo gate (exit before apt)."""
    assert cli("snapshot", "itest").returncode == 0

    result = cli("restore", "itest", "--yes")

    assert result.returncode == 1
    assert "root privileges" in result.stdout


def test_corrupted_snapshot_is_rejected_before_restore(cli):
    assert cli("snapshot", "itest").returncode == 0

    snap_path = cli.snapshot_dir / "itest.json"
    data = json.loads(snap_path.read_text())
    data["packages"][0]["version"] = "0.0-broken"  # stale checksum now
    snap_path.write_text(json.dumps(data))

    result = cli("restore", "itest", "--dry-run", "--yes")

    assert result.returncode == 1
    assert "integrity verification" in result.stdout


def test_legacy_snapshot_without_metadata_is_rejected(cli):
    legacy = {
        "name": "legacy",
        "timestamp": "2025-01-01T00:00:00",
        "packages": [{"name": "alpha", "version": "1.0"}],
    }
    cli.snapshot_dir.mkdir(parents=True, exist_ok=True)
    (cli.snapshot_dir / "legacy.json").write_text(json.dumps(legacy))

    result = cli("restore", "legacy", "--dry-run", "--yes")

    assert result.returncode == 1
    assert "legacy snapshot" in result.stdout


def test_snapshot_in_dev_mode_works_without_root(cli):
    """DEBH_DEV keeps development workflows root-free."""
    result = cli("snapshot", "noroot")
    assert result.returncode == 0, result.stderr
    assert (cli.snapshot_dir / "noroot.json").exists()
