from dataclasses import dataclass, field
from core.buffering.event_buffer import EventBuffer

@dataclass
class SystemState:
    start_time: float
    app_to_cores: dict[str, set[int]]
    app_to_pid: dict[str, int]
    epoch: int
    event_buffer: EventBuffer | None = None