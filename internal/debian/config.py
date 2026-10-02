"""Central configuration for debh paths and runtime modes.

This module is the single source of truth for where debh stores its
snapshots. No other module should hardcode snapshot paths or read
DEBH_DEV directly.
"""

import os
from pathlib import Path

# Environment variable that enables development mode. In development
# mode snapshots are stored in the user's home directory instead of the
# system-wide location, so debh can be exercised without root privileges.
DEV_MODE_ENV_VAR = "DEBH_DEV"

# System-wide snapshot location used in production.
_PROD_SNAPSHOT_DIR = Path("/var/lib/debh/snapshots")


def is_dev_mode() -> bool:
    """Return True if debh runs in development mode (DEBH_DEV set)."""
    return bool(os.environ.get(DEV_MODE_ENV_VAR))


def get_snapshot_dir() -> Path:
    """Return the directory where snapshot JSON files are stored."""
    if is_dev_mode():
        return Path.home() / ".debh" / "snapshots"
    return _PROD_SNAPSHOT_DIR


def get_snapshot_path(name: str) -> Path:
    """Return the JSON file path for the snapshot called ``name``."""
    return get_snapshot_dir() / f"{name}.json"
