from dataclasses import dataclass
@dataclass
class MigrationAction:
    app: str
    pid: int
    destination: set[int]
    source: set[int] | None

@dataclass
class DVFSAction:
    core_id: int
    frequency_mhz: int