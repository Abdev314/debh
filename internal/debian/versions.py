"""Debian package version comparison.

Thin wrapper around python3-apt's version_compare so the rest of debh
never reimplements (or string-compares) Debian version semantics.
"""

import apt_pkg

# apt_pkg.version_compare requires the library to be initialized first.
apt_pkg.init()


def compare_versions(version_a: str, version_b: str) -> int:
    """
    Compare two Debian package versions.

    Follows full Debian version semantics (epochs, upstream versions and
    revisions). Returns a positive number if version_a is newer than
    version_b, zero if they are equal, and a negative number otherwise.
    """
    return apt_pkg.version_compare(version_a, version_b)
