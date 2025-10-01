from dataclasses import dataclass
from ardis.benchmarks.application import Application

@dataclass
class MigrationAction:
    app: Application
    source: set[int] | None
    destination: set[int]

@dataclass
class DVFSAction:
    core_id: int
    frequency_mhz: int