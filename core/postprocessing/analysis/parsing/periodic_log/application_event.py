from __future__ import annotations
from dataclasses import dataclass
import re

@dataclass
class ApplicationEvent:
    timestamp_sec: float
    instance_id: int 
    application_name: str
    affinity: set[int]
    pid: int | None
    tid: int | None
    frequency_mhz: float | None
    perf_events: dict[str, int]

    # Regex that captures Time, Core(s), App Name, Instance ID
    __head_pattern = re.compile(r"\[(\d+\.\d+)s\] (?:Cores \[(.*)\]|Core (\d+)): app = (.*) \| IID = (\d+) \|")
    
    # Regex that captures key=value pairs in the tail of the log line 
    __field_pattern = re.compile(r"\b(\w[\w\-]*)\s*=\s*([\w\.\-]+)")

    @classmethod
    def from_periodic_log_line(cls, line: str) -> ApplicationEvent:
        
        head_match = cls.__head_pattern.match(line)
        if not head_match:
            raise ValueError(f"Line does not match expected format: {line}")
        
        timestamp_sec = float(head_match.group(1))
        
        affinity_str = head_match.group(2)
        core_str = head_match.group(3)
        if affinity_str:
            affinity = {int(core_id) for core_id in affinity_str.split(',')}
        elif core_str:
            affinity = {int(core_str)}
        else:
            raise ValueError("Could not determine core affinity from log line.")
        
        app_name = head_match.group(4)
        instance_id = int(head_match.group(5))
        pid = None
        tid = None
        frequency_mhz = None
        perf_events: dict[str, int] = {}

        tail = line[head_match.end():]
        for event_match in cls.__field_pattern.finditer(tail):
            event_name = event_match.group(1)
            event_value = event_match.group(2)
            if event_name == "PID":
                pid = int(event_value)
            elif event_name == "TID":
                tid = int(event_value)
            elif event_name == "frequency":
                # There is a configuration in which the frequency field has the value <not available> 
                # (PID_MONITORING, with an application that is assigned to multiple cores)
                try:
                    frequency_mhz = float(event_value)
                except ValueError:
                    frequency_mhz = None
            else:
                # Assumes, that perf events are typically integers
                perf_events[event_name] = int(event_value)

        return cls(
            timestamp_sec=timestamp_sec,
            instance_id=instance_id,
            application_name=app_name,
            affinity=affinity,
            pid=pid,
            tid=tid,
            frequency_mhz=frequency_mhz,
            perf_events=perf_events
        )
