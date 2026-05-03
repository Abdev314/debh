#!/usr/bin/env python
"""debh - Debian package snapshot manager CLI."""

import sys
import os
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from internal.snapshot import create, restore


def main():
    parser = argparse.ArgumentParser(
        prog="debh",
        description="Debian package snapshot manager - Git-like version control for your system"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # snapshot command
    snapshot_parser = subparsers.add_parser("snapshot", help="Create a new snapshot")
    snapshot_parser.add_argument("name", help="Snapshot name (e.g., 'before-upgrade')")

    # list command
    list_parser = subparsers.add_parser("list", help="List all snapshots")

    # restore command
    restore_parser = subparsers.add_parser("restore", help="Restore to a snapshot")
    restore_parser.add_argument("name", help="Snapshot name to restore")
    restore_parser.add_argument("--dry-run", action="store_true",
                                help="Show what would change without actually restoring")

    # diff command (coming soon)
    diff_parser = subparsers.add_parser("diff", help="Compare two snapshots")
    diff_parser.add_argument("snapshot1", help="First snapshot")
    diff_parser.add_argument("snapshot2", help="Second snapshot")

    args = parser.parse_args()

    if args.command == "snapshot":
        create.create_snapshot(args.name)

    elif args.command == "list":
        snapshots = create.list_snapshots()
        if snapshots:
            print("\n📸 Snapshots:")
            for snap in snapshots:
                print(f"  - {snap}")
            print()
        else:
            print("No snapshots found")

    elif args.command == "restore":
        restore.restore_snapshot(args.name, dry_run=args.dry_run)

    elif args.command == "diff":
        print("Diff coming soon!")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()