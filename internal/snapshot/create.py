"""Create snapshots of current system state."""

import json
from datetime import datetime
from typing import List

from pkg.models.snapshot import Snapshot, Package
from internal.debian import config, dpkg
from internal.snapshot import verify


def ensure_snapshot_dir() -> None:
    """Create snapshot directory if it doesn't exist."""
    config.get_snapshot_dir().mkdir(parents=True, exist_ok=True)


def create_snapshot(name: str, verbose: bool = True) -> Snapshot:

    ensure_snapshot_dir()

    # Check if snapshot already exists
    snapshot_path = config.get_snapshot_path(name)
    if snapshot_path.exists():
        raise FileExistsError(f"Snapshot '{name}' already exists")

    if verbose:
        print(f"📸 Creating snapshot '{name}'...")

    # Get current package state
    if verbose:
        print("   Reading installed packages...")
    packages = dpkg.get_installed_packages()

    # Build snapshot object
    snapshot = Snapshot(
        name=name,
        timestamp=datetime.now(),
        packages=packages,
    )

    # Save to JSON file, including integrity metadata so the snapshot
    # can be verified before any future restore.
    data = {
        "name": snapshot.name,
        "timestamp": snapshot.timestamp.isoformat(),
        "packages": [
            {"name": p.name, "version": p.version}
            for p in snapshot.packages
        ]
    }
    data.update(verify.build_integrity_metadata(data["packages"]))

    with open(snapshot_path, "w") as f:
        json.dump(data, f, indent=2)

    if verbose:
        print(f"✓ Snapshot '{name}' created")
        print(f"  Location: {snapshot_path}")
        print(f"  Packages: {len(packages)}")

    return snapshot


def list_snapshots() -> List[str]:
    """Return list of all snapshot names."""
    ensure_snapshot_dir()
    snapshots = []
    for path in config.get_snapshot_dir().glob("*.json"):
        snapshots.append(path.stem)  # .stem removes the .json extension
    return sorted(snapshots)


# Quick test when run directly
if __name__ == "__main__":
    # Create a test snapshot
    try:
        snap = create_snapshot("test-snapshot")
        print(f"\n✅ Success! Snapshot saved.")
        print(f"\nExisting snapshots: {list_snapshots()}")
    except FileExistsError:
        print("Snapshot 'test-snapshot' already exists, skipping...")