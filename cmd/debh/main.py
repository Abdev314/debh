#!/usr/bin/env python3
"""
debh - Debian package snapshot manager
Git-like version control for your Debian system.
"""

import sys
import os
import argparse
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from internal.snapshot import create, restore, diff


def check_sudo():
    """Warn if not running as root for commands that need it."""
    commands_needing_sudo = ['restore', 'snapshot']
    if sys.argv[1] in commands_needing_sudo and os.geteuid() != 0:
        print("❌ This command requires root privileges.")
        print("   Please run with: sudo debh " + " ".join(sys.argv[1:]))
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        prog="debh",
        description="debh - Debian package snapshot manager",
        epilog="Examples:\n"
               "  debh snapshot before-upgrade    # Save current state\n"
               "  debh list                        # Show all snapshots\n"
               "  debh diff before after           # Compare snapshots\n"
               "  debh restore before-upgrade      # Roll back",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands", required=True)

    # snapshot command
    snap_parser = subparsers.add_parser("snapshot", help="Create a new snapshot")
    snap_parser.add_argument("name", help="Snapshot name (e.g., 'before-upgrade')")
    snap_parser.add_argument("--description", "-d", help="Optional description")

    # list command
    list_parser = subparsers.add_parser("list", help="List all snapshots")
    list_parser.add_argument("--verbose", "-v", action="store_true", help="Show details (timestamp, package count)")

    # restore command
    restore_parser = subparsers.add_parser("restore", help="Restore to a snapshot")
    restore_parser.add_argument("name", help="Snapshot name to restore")
    restore_parser.add_argument("--dry-run", action="store_true",
                                help="Show what would change without actually restoring")
    restore_parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")

    # diff command
    diff_parser = subparsers.add_parser("diff", help="Compare two snapshots")
    diff_parser.add_argument("snapshot1", help="First snapshot")
    diff_parser.add_argument("snapshot2", help="Second snapshot")
    diff_parser.add_argument("--verbose", "-v", action="store_true", help="Show all changes")

    # show command (new - view snapshot details)
    show_parser = subparsers.add_parser("show", help="Show snapshot details")
    show_parser.add_argument("name", help="Snapshot name")

    # rm command (new - delete snapshot)
    rm_parser = subparsers.add_parser("rm", help="Remove a snapshot")
    rm_parser.add_argument("name", help="Snapshot name")
    rm_parser.add_argument("--force", "-f", action="store_true", help="Force removal without confirmation")

    # info command (new - show tool info)
    info_parser = subparsers.add_parser("info", help="Show tool information")

    args = parser.parse_args()

    # Execute commands
    if args.command == "snapshot":
        print(f"📸 Creating snapshot '{args.name}'...")
        snap = create.create_snapshot(args.name)
        if args.description:
            # Store description in a sidecar file
            desc_path = Path(create.SNAPSHOT_DIR) / f"{args.name}.desc"
            desc_path.write_text(f"{args.description}\n")
        print(f"✅ Snapshot '{args.name}' created successfully")

    elif args.command == "list":
        snapshots = create.list_snapshots()
        if not snapshots:
            print("📭 No snapshots found. Create one with: debh snapshot <name>")
            return

        if args.verbose:
            print(f"\n📸 Snapshots ({len(snapshots)} total):\n")
            for snap_name in snapshots:
                snap_path = Path(create.SNAPSHOT_DIR) / f"{snap_name}.json"
                if snap_path.exists():
                    with open(snap_path) as f:
                        data = json.load(f)
                    timestamp = datetime.fromisoformat(data["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                    pkg_count = len(data["packages"])
                    print(f"   {snap_name}")
                    print(f"      📅 {timestamp}")
                    print(f"      📦 {pkg_count} packages")
                    # Show description if exists
                    desc_path = Path(create.SNAPSHOT_DIR) / f"{snap_name}.desc"
                    if desc_path.exists():
                        print(f"      📝 {desc_path.read_text().strip()}")
                    print()
        else:
            print("\n📸 Snapshots:")
            for snap in snapshots:
                print(f"   - {snap}")
            print(f"\n   Total: {len(snapshots)} snapshots")
            print("   Use 'debh list --verbose' for details")

    elif args.command == "restore":
        result = restore.restore_snapshot(args.name, dry_run=args.dry_run, auto_yes=args.yes)
        if not result:
            sys.exit(1)

    elif args.command == "diff":
        diff.diff_snapshots(args.snapshot1, args.snapshot2, verbose=args.verbose)

    elif args.command == "show":
        snap_path = Path(create.SNAPSHOT_DIR) / f"{args.name}.json"
        if not snap_path.exists():
            print(f"❌ Snapshot '{args.name}' not found")
            sys.exit(1)

        with open(snap_path) as f:
            data = json.load(f)

        print(f"\n📸 Snapshot: {args.name}")
        print(f"   📅 Created: {data['timestamp']}")
        print(f"   📦 Packages: {len(data['packages'])}")

        desc_path = Path(create.SNAPSHOT_DIR) / f"{args.name}.desc"
        if desc_path.exists():
            print(f"   📝 Description: {desc_path.read_text().strip()}")

        # Show first 10 packages
        print(f"\n   First 10 packages:")
        for pkg in data['packages'][:10]:
            print(f"      - {pkg['name']} = {pkg['version']}")
        if len(data['packages']) > 10:
            print(f"      ... and {len(data['packages']) - 10} more")
        print()

    elif args.command == "rm":
        snap_path = Path(create.SNAPSHOT_DIR) / f"{args.name}.json"
        if not snap_path.exists():
            print(f"❌ Snapshot '{args.name}' not found")
            sys.exit(1)

        if not args.force:
            response = input(f"Delete snapshot '{args.name}'? [y/N]: ")
            if response.lower() != 'y':
                print("Cancelled")
                sys.exit(0)

        snap_path.unlink()
        # Also remove description if exists
        desc_path = Path(create.SNAPSHOT_DIR) / f"{args.name}.desc"
        if desc_path.exists():
            desc_path.unlink()
        print(f"✅ Snapshot '{args.name}' deleted")

    elif args.command == "info":
        print("""
╔══════════════════════════════════════════════════════════╗
║  debh - Debian Package Snapshot Manager                  ║
║  Version: 0.1.0                                          ║
║                                                          ║
║  Git-like version control for your Debian system         ║
║                                                          ║
║  Commands:                                               ║
║    snapshot  - Save current system state                 ║
║    list      - Show all snapshots                        ║
║    diff      - Compare two snapshots                     ║
║    restore   - Roll back to a snapshot                   ║
║    show      - Show snapshot details                     ║
║    rm        - Delete a snapshot                         ║
║                                                          ║
║  Examples:                                               ║
║    debh snapshot before-upgrade                          ║
║    debh list -v                                          ║
║    debh diff clean broken                                ║
║    debh restore before-upgrade --dry-run                 ║
║                                                          ║
║  Snapshots stored in: /var/lib/debh/snapshots/           ║
╚══════════════════════════════════════════════════════════╝
        """)


if __name__ == "__main__":
    main()