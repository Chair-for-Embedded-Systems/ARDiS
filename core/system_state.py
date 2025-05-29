from dataclasses import dataclass
from core.buffering.event_buffer import EventBuffer
from core.buffering.action_buffer import ActionBuffer

@dataclass
class SystemState:
    start_time: float
    app_to_cores: dict[str, set[int]]
    app_to_pid: dict[str, int]
    epoch: int
    event_buffer: EventBuffer
    action_buffer: ActionBuffer

    @property
    def active_apps(self) -> set[str]:
        """
        Returns a set of currently active applications. Active means that a valid pid exist.
        """
        return {app for app, pid in self.app_to_pid.items() if pid != -1}

    @property
    def occupied_cores(self) -> set[int]:
        """
        Returns a set of currently occupied cores
        """
        return set().union(*self.app_to_cores.values())