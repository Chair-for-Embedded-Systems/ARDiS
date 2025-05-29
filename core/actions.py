from dataclasses import dataclass
@dataclass
class MigrationAction:
    app: str
    source: set[int] | None
    destination: set[int]

@dataclass
class DVFSAction:
    core_id: int
    frequency_mhz: int