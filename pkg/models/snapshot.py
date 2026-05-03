"""Data models for debh snapshots."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass
class Package:
    name: str
    version: str


@dataclass
class Snapshot:
    name: str
    timestamp: datetime
    packages: List[Package] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"Snapshot(name='{self.name}', packages={len(self.packages)})"