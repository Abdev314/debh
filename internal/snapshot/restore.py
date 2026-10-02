"""Restore system state from a snapshot."""

import json
import subprocess
from typing import List, Tuple

from pkg.models.snapshot import Package
from internal.debian import config, dpkg
from internal.snapshot import verify


def load_snapshot(name: str) -> dict:
    """Load a snapshot JSON file by name."""
    snapshot_path = config.get_snapshot_path(name)

    if not snapshot_path.exists():
        raise FileNotFoundError(f"Snapshot '{name}' not found at {snapshot_path}")

    with open(snapshot_path, "r") as f:
        return json.load(f)


def calculate_diff(target_snapshot: dict) -> Tuple[List[str], List[str], List[str]]:
    """
    Compare current system with target snapshot.

    Returns:
        Tuple of (to_downgrade, to_remove, to_install)
        Each is a list of package strings like "package=version"
    """
    # Get current packages
    current_packages = dpkg.get_installed_packages()

    # Build maps for quick lookup
    current_map = {pkg.name: pkg.version for pkg in current_packages}
    target_map = {pkg["name"]: pkg["version"] for pkg in target_snapshot["packages"]}

    to_downgrade = []  # Package needs to go to older version
    to_remove = []  # Package exists in current but not in target
    to_install = []  # Package exists in target but not in current

    # Check packages that should be at specific versions
    for name, target_version in target_map.items():
        if name not in current_map:
            to_install.append(f"{name}={target_version}")
        elif current_map[name] != target_version:
            to_downgrade.append(f"{name}={target_version}")

    # Check packages that should not exist
    for name in current_map:
        if name not in target_map:
            to_remove.append(name)

    return to_downgrade, to_remove, to_install


def show_changes(to_downgrade: List[str], to_remove: List[str], to_install: List[str]) -> None:
    """Print the changes that a restore would apply."""
    if not any([to_downgrade, to_remove, to_install]):
        print("System already matches snapshot. Nothing to do.")
        return

    print("\nChanges to apply:")

    if to_install:
        print(f"\n  Install ({len(to_install)}):")
        for pkg in to_install[:5]:
            print(f"     + {pkg}")
        if len(to_install) > 5:
            print(f"     ... and {len(to_install) - 5} more")

    if to_downgrade:
        print(f"\n  Downgrade ({len(to_downgrade)}):")
        for pkg in to_downgrade[:5]:
            print(f"     - {pkg}")
        if len(to_downgrade) > 5:
            print(f"     ... and {len(to_downgrade) - 5} more")

    if to_remove:
        print(f"\n  Remove ({len(to_remove)}):")
        for pkg in to_remove[:5]:
            print(f"     - {pkg}")
        if len(to_remove) > 5:
            print(f"     ... and {len(to_remove) - 5} more")


def confirm_action(to_downgrade: List[str], to_remove: List[str], to_install: List[str]) -> bool:
    """
    Single source of truth for the interactive restore confirmation.

    Shows the pending changes and prompts exactly once. Returns True if
    the user confirms, False if they decline or there is nothing to do.
    """
    show_changes(to_downgrade, to_remove, to_install)
    if not any([to_downgrade, to_remove, to_install]):
        return False

    print("\nWARNING: This will change your system. Continue? [y/N]: ", end="")
    response = input().strip().lower()
    return response == 'y'


def apply_changes(to_downgrade: List[str], to_remove: List[str], to_install: List[str]) -> bool:
    """Execute the package changes using apt."""
    try:
        # Remove packages first (order matters)
        if to_remove:
            print("\nRemoving packages...")
            cmd = ["sudo", "apt", "remove", "--purge", "-y"] + to_remove
            subprocess.run(cmd, check=True)

        # Install/downgrade packages
        if to_install or to_downgrade:
            print("\nInstalling/downgrading packages...")
            cmd = ["sudo", "apt", "install", "--allow-downgrades", "-y"]
            cmd.extend(to_install)
            cmd.extend(to_downgrade)
            subprocess.run(cmd, check=True)

        return True

    except subprocess.CalledProcessError as e:
        print(f"\nError applying changes: {e}")
        print("Your system may be in an inconsistent state.")
        print("Run 'sudo apt --fix-broken install' to recover.")
        return False


def restore_snapshot(name: str, dry_run: bool = False, auto_yes: bool = False) -> bool:
    """
    Restore system to a previous snapshot.

    Args:
        name: Snapshot name to restore
        dry_run: If True, only show what would change
        auto_yes: If True, skip the interactive confirmation prompt
                  (integrity verification still runs)

    Returns:
        True if successful, False otherwise
    """
    print(f"Restoring to snapshot '{name}'...")

    # Load the snapshot
    try:
        snapshot_data = load_snapshot(name)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"Invalid snapshot JSON for '{name}': {e}")
        return False

    # Verify integrity BEFORE anything can touch the system. A corrupted
    # or unverifiable snapshot must never reach confirmation or apt.
    try:
        verify.verify_snapshot(snapshot_data)
    except verify.SnapshotVerificationError as e:
        print(f"Snapshot '{name}' failed integrity verification: {e}")
        return False

    print(f"   Snapshot from: {snapshot_data['timestamp']}")
    print(f"   Target packages: {len(snapshot_data['packages'])}")

    # Calculate what needs to change
    to_downgrade, to_remove, to_install = calculate_diff(snapshot_data)

    # Dry run mode: show the changes, never prompt, never touch the system
    if dry_run:
        print("\n DRY RUN - No changes will be made")
        show_changes(to_downgrade, to_remove, to_install)
        return True

    # Single confirmation gate. --yes skips ONLY this prompt; all
    # validation and integrity checks above already ran.
    if not auto_yes and not confirm_action(to_downgrade, to_remove, to_install):
        print("Restore cancelled.")
        return False

    # Apply the changes
    success = apply_changes(to_downgrade, to_remove, to_install)

    if success:
        print("\n Restore complete! System should now match snapshot.")
        print("   You may need to restart some services or reboot.")
    else:
        print("\nRestore failed. Check errors above.")

    return success


# CLI test when run directly
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python restore.py <snapshot-name> [--dry-run] [--yes]")
        print("\nAvailable snapshots:")
        from internal.snapshot.create import list_snapshots

        for snap in list_snapshots():
            print(f"  - {snap}")
        sys.exit(1)

    name = sys.argv[1]
    dry_run = "--dry-run" in sys.argv
    auto_yes = "--yes" in sys.argv or "-y" in sys.argv

    restore_snapshot(name, dry_run, auto_yes)
