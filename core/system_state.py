from dataclasses import dataclass, field

@dataclass
class SystemState:
    start_time: float = 0.0
    end_time: float = 0.0
    app_to_cores: dict[str, set[int]] = field(default_factory=dict)
    app_to_pid: dict[str, int] = field(default_factory=dict)
    epoch: int = 0