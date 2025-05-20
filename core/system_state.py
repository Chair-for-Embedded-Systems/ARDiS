from dataclasses import dataclass
from core.buffering.event_buffer import EventBuffer
from core.buffering.action_buffer import ActionBuffer

@dataclass
class SystemState:
    start_time: float
    app_to_cores: dict[str, set[int]]
    app_to_pid: dict[str, int]
    epoch: int
    event_buffer: EventBuffer | None = None
    action_buffer: ActionBuffer | None = None