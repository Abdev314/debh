"""Tests for the CLI root-privilege gate (check_sudo in cmd/debh/main.py)."""

import importlib.util
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

spec = importlib.util.spec_from_file_location("debh_main", REPO_ROOT / "cmd" / "debh" / "main.py")
debh_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(debh_main)


def make_args(command, name="snap", dry_run=False):
    return SimpleNamespace(command=command, name=name, dry_run=dry_run)


@pytest.fixture(autouse=True)
def non_root(monkeypatch):
    monkeypatch.setattr(os, "geteuid", lambda: 1000)
    monkeypatch.delenv("DEBH_DEV", raising=False)


def test_restore_requires_root():
    with pytest.raises(SystemExit) as exc:
        debh_main.check_sudo(make_args("restore"))
    assert exc.value.code == 1


def test_restore_dry_run_does_not_require_root():
    assert debh_main.check_sudo(make_args("restore", dry_run=True)) is None


def test_snapshot_requires_root_in_prod_mode():
    with pytest.raises(SystemExit):
        debh_main.check_sudo(make_args("snapshot"))


def test_snapshot_allowed_without_root_in_dev_mode(monkeypatch):
    monkeypatch.setenv("DEBH_DEV", "1")
    assert debh_main.check_sudo(make_args("snapshot")) is None


def test_rm_requires_root_in_prod_mode():
    with pytest.raises(SystemExit):
        debh_main.check_sudo(make_args("rm"))


def test_read_only_commands_never_require_root():
    for command in ("list", "diff", "show", "info"):
        assert debh_main.check_sudo(make_args(command)) is None


def test_root_user_passes_all_commands():
    debh_main.os.geteuid = lambda: 0
    try:
        for command in ("restore", "snapshot", "rm", "list", "diff", "show", "info"):
            assert debh_main.check_sudo(make_args(command)) is None
    finally:
        debh_main.os.geteuid = os.geteuid


def test_error_message_is_human_readable(capsys):
    with pytest.raises(SystemExit):
        debh_main.check_sudo(make_args("restore"))
    out = capsys.readouterr().out
    assert "root privileges" in out
    assert "sudo debh restore snap" in out


def test_main_calls_check_sudo_before_dispatch(monkeypatch):
    """main() must run the privilege gate before executing any command."""
    called = []
    monkeypatch.setattr(debh_main, "check_sudo", lambda args: called.append(args.command))
    executed = []
    monkeypatch.setattr(
        debh_main.restore,
        "restore_snapshot",
        lambda name, dry_run=False, auto_yes=False: executed.append((name, auto_yes)) or True,
    )
    monkeypatch.setattr(sys, "argv", ["debh", "restore", "snap", "--yes"])

    debh_main.main()

    assert called == ["restore"]
    assert executed == [("snap", True)]


def test_main_aborts_privileged_command_before_running_it(monkeypatch, capsys):
    """As non-root, 'debh restore' must exit at the gate, never reaching apt."""
    monkeypatch.setattr(sys, "argv", ["debh", "restore", "snap", "--yes"])
    executed = []
    monkeypatch.setattr(
        debh_main.restore,
        "restore_snapshot",
        lambda *a, **k: executed.append(True) or True,
    )

    with pytest.raises(SystemExit) as exc:
        debh_main.main()

    assert exc.value.code == 1
    assert executed == []
    assert "root privileges" in capsys.readouterr().out
