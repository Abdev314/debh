"""Read package state from dpkg database."""

import subprocess
from typing import List

from pkg.models.snapshot import  Package


def get_installed_packages() -> List[Package]:

    cmd = ["dpkg-query", "-W", "-f=${Package} ${Version}\\n"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    packages = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split()
        if len(parts) == 2:
            packages.append(Package(name=parts[0], version=parts[1]))

    return packages


def package_count() -> int:
    """Return number of installed packages."""
    return len(get_installed_packages())


# Quick test when run directly
if __name__ == "__main__":
    pkgs = get_installed_packages()
    print(f"Found {len(pkgs)} packages on this system")
    print("\nFirst 5 packages:")
    for pkg in pkgs[:5]:
        print(f"  {pkg.name} = {pkg.version}")