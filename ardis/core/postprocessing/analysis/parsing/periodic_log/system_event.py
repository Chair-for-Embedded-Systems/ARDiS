from __future__ import annotations
from dataclasses import dataclass
import re

@dataclass
class SystemEvent:
    timestamp_sec: float
    perf_events: dict[str, int | float]

    _head_pattern = re.compile(r"\[(\d+\.\d+)s\] SYSTEM:")
    _event_pattern = re.compile(r"([^=|]+?)\s*=\s*([\d.]+)")

    @classmethod
    def from_log_line(cls, log_line: str) -> SystemEvent:
        head_group = cls._head_pattern.search(log_line)
        assert head_group
        timestamp_sec : float = float(head_group.group(1))
        
        events : dict[str, int | float] = {}
        event_group = log_line.replace(head_group.group(0), '', 1).strip()
        event_group_matches: list[tuple[str, str]] = cls._event_pattern.findall(event_group)
        
        for (event_name, event_count) in event_group_matches:
            event_value = float(event_count) if "." in event_count else int(event_count)
            events[event_name.strip()] = event_value

        return cls(
            timestamp_sec=timestamp_sec,
            perf_events=events
        )
    