"""Snapshot integrity verification.

Every snapshot created by debh carries integrity metadata:

    {
        "name": ...,
        "timestamp": ...,
        "packages": [{"name": ..., "version": ...}, ...],
        "package_count": <int>,
        "checksum": "<sha256 hexdigest>"
    }

The checksum is a SHA-256 hash over the canonical JSON serialization of
the snapshot's package data. It is computed with sorted keys and compact
separators so the same package data always hashes to the same digest.
The metadata fields themselves are never part of the hashed data.
"""

import hashlib
import json
from typing import Any, Dict, List


class SnapshotVerificationError(Exception):
    """Raised when a snapshot fails structure or integrity verification."""


def compute_checksum(packages: List[Dict[str, Any]]) -> str:
    """Return the deterministic SHA-256 checksum for package data."""
    canonical = json.dumps(packages, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_integrity_metadata(packages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Return the integrity metadata block for newly created snapshots."""
    return {
        "package_count": len(packages),
        "checksum": compute_checksum(packages),
    }


def verify_snapshot(snapshot: Dict[str, Any]) -> None:
    """
    Verify the structure and integrity of a loaded snapshot.

    Checks, in order:
      1. required top-level structure (name, timestamp, packages)
      2. every package entry has a string name and version
      3. the declared package_count matches the actual package list
      4. the declared checksum matches the package data

    Raises SnapshotVerificationError with a human-readable message on
    any failure. Returns None when the snapshot is fully valid.
    """
    if not isinstance(snapshot, dict):
        raise SnapshotVerificationError("snapshot is not a JSON object")

    for field in ("name", "timestamp", "packages"):
        if field not in snapshot:
            raise SnapshotVerificationError(
                f"snapshot is missing required field '{field}'"
            )

    packages = snapshot["packages"]
    if not isinstance(packages, list):
        raise SnapshotVerificationError("snapshot 'packages' is not a list")

    for entry in packages:
        if not isinstance(entry, dict):
            raise SnapshotVerificationError(
                "snapshot contains a malformed package entry"
            )
        if not isinstance(entry.get("name"), str) or not isinstance(
            entry.get("version"), str
        ):
            raise SnapshotVerificationError(
                "snapshot package entries must have string 'name' and 'version'"
            )

    # Snapshots without integrity metadata were created by an older debh
    # version. They cannot be proven trustworthy, so refuse them with a
    # clear message instead of crashing on a missing key.
    if "package_count" not in snapshot or "checksum" not in snapshot:
        raise SnapshotVerificationError(
            "snapshot has no integrity metadata (legacy snapshot from an "
            "older debh version); recreate it with 'debh snapshot' or restore "
            "from a verified copy"
        )

    package_count = snapshot["package_count"]
    if not isinstance(package_count, int) or isinstance(package_count, bool):
        raise SnapshotVerificationError(
            "snapshot 'package_count' is not an integer"
        )
    if package_count != len(packages):
        raise SnapshotVerificationError(
            f"package count mismatch: snapshot declares {package_count} "
            f"packages but contains {len(packages)}"
        )

    expected_checksum = compute_checksum(packages)
    if snapshot["checksum"] != expected_checksum:
        raise SnapshotVerificationError(
            "checksum mismatch: snapshot package data has been modified "
            "or corrupted"
        )
