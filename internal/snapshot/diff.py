"""Compare two snapshots and show differences."""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple

# Use same snapshot directory
SNAPSHOT_DIR = Path("/var/lib/debh/snapshots")


def load_snapshot_data(name: str) -> dict:
    """Load snapshot JSON file."""
    snapshot_path = SNAPSHOT_DIR / f"{name}.json"

    if not snapshot_path.exists():
        raise FileNotFoundError(f"Snapshot '{name}' not found at {snapshot_path}")

    with open(snapshot_path, "r") as f:
        return json.load(f)


def compare_snapshots(snap1_name: str, snap2_name: str) -> Dict:
    """
    Compare two snapshots and return differences.

    Returns:
        Dictionary with:
        - added: packages in snap2 but not snap1
        - removed: packages in snap1 but not snap2
        - upgraded: packages with version increase
        - downgraded: packages with version decrease
        - version_changed: all version changes
    """
    snap1 = load_snapshot_data(snap1_name)
    snap2 = load_snapshot_data(snap2_name)

    # Convert to dicts for easy lookup
    pkgs1 = {pkg["name"]: pkg["version"] for pkg in snap1["packages"]}
    pkgs2 = {pkg["name"]: pkg["version"] for pkg in snap2["packages"]}

    added = []
    removed = []
    upgraded = []
    downgraded = []
    version_changed = []

    # Find added and upgraded packages
    for name, version2 in pkgs2.items():
        if name not in pkgs1:
            added.append((name, version2))
        else:
            version1 = pkgs1[name]
            if version1 != version2:
                version_changed.append((name, version1, version2))
                # Try to determine if upgrade or downgrade
                # Simple heuristic: compare version strings
                if version2 > version1:
                    upgraded.append((name, version1, version2))
                else:
                    downgraded.append((name, version1, version2))

    # Find removed packages
    for name in pkgs1:
        if name not in pkgs2:
            removed.append((name, pkgs1[name]))

    return {
        "snap1": snap1_name,
        "snap1_time": snap1["timestamp"],
        "snap2": snap2_name,
        "snap2_time": snap2["timestamp"],
        "added": added,
        "removed": removed,
        "upgraded": upgraded,
        "downgraded": downgraded,
        "version_changed": version_changed,
        "total_pkgs1": len(pkgs1),
        "total_pkgs2": len(pkgs2),
    }


def print_diff(diff: Dict) -> None:
    """Pretty print the diff output."""
    print(f"\n📊 Comparing snapshots:")
    print(f"   '{diff['snap1']}' ({diff['snap1_time']})")
    print(f"   '{diff['snap2']}' ({diff['snap2_time']})")
    print(f"\n   Total packages: {diff['total_pkgs1']} → {diff['total_pkgs2']}")

    if diff["added"]:
        print(f"\n➕ Added ({len(diff['added'])}):")
        for name, version in diff["added"][:10]:
            print(f"   + {name} = {version}")
        if len(diff["added"]) > 10:
            print(f"   ... and {len(diff['added']) - 10} more")

    if diff["removed"]:
        print(f"\n❌ Removed ({len(diff['removed'])}):")
        for name, version in diff["removed"][:10]:
            print(f"   - {name} = {version}")
        if len(diff["removed"]) > 10:
            print(f"   ... and {len(diff['removed']) - 10} more")

    if diff["upgraded"]:
        print(f"\n⬆️  Upgraded ({len(diff['upgraded'])}):")
        for name, old, new in diff["upgraded"][:10]:
            print(f"   {name}: {old} → {new}")
        if len(diff["upgraded"]) > 10:
            print(f"   ... and {len(diff['upgraded']) - 10} more")

    if diff["downgraded"]:
        print(f"\n⬇️  Downgraded ({len(diff['downgraded'])}):")
        for name, old, new in diff["downgraded"][:10]:
            print(f"   {name}: {old} → {new}")
        if len(diff["downgraded"]) > 10:
            print(f"   ... and {len(diff['downgraded']) - 10} more")

    if not any([diff["added"], diff["removed"], diff["upgraded"], diff["downgraded"]]):
        print("\n✨ No differences between snapshots")

    print()


def diff_snapshots(snap1: str, snap2: str, verbose: bool = False) -> None:
    """Main function to diff two snapshots."""
    try:
        diff = compare_snapshots(snap1, snap2)
        print_diff(diff)

        if verbose and diff["version_changed"]:
            print("\n📝 All version changes:")
            for name, old, new in diff["version_changed"]:
                print(f"   {name}: {old} → {new}")

    except FileNotFoundError as e:
        print(f"❌ {e}")


# CLI when run directly
if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python diff.py <snapshot1> <snapshot2>")
        print("\nAvailable snapshots:")
        from internal.snapshot.create import list_snapshots

        for snap in list_snapshots():
            print(f"  - {snap}")
        sys.exit(1)

    diff_snapshots(sys.argv[1], sys.argv[2], verbose=True)