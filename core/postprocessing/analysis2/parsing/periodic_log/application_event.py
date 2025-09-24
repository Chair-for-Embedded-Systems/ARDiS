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
                frequency_mhz = float(event_value)
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

if __name__ == "__main__":
    line_core = "[2.75s] Core 3: app = parsec.blackscholes-1 | IID = 0 | frequency = 2999.969 | instructions = 1432382127 | LLC-loads = 116772 | LLC-load-misses = 107529 | LLC-stores = 53187 | LLC-store-misses = 50430 | cycles = 321992809 | branch-misses = 619706 | branches = 300850716"
    line_pid = "[61.71s] Core 6: app = parsec.blackscholes-1 | IID = 3 | PID = 2804523 | frequency = 3000.03 | instructions = 694944219 | LLC-loads = 15762 | LLC-load-misses = 9730 | LLC-stores = 1339 | LLC-store-misses = 0 | cycles = 301948876 | branch-misses = 126681 | branches = 82195320"
    line_tid = "[1.69s] Core 6: app = parsec.dedup-4 | IID = 5 | TID = 2810808 | frequency = 3499.964 | instructions = 272909433 | LLC-loads = 16721 | LLC-load-misses = 4743 | LLC-stores = 2871 | LLC-store-misses = 147 | cycles = 58924430 | branch-misses = 17468 | branches = 810653"
    event = ApplicationEvent.from_periodic_log_line(line_tid)
    print(event)

# <When> | <Where> | app = <AppName> | IID = <InstanceID> | [PID = <PID> |] [TID = <TID> |] frequency = <FrequencyMHz> | <PerfEvent1> = <Value1> | ... | <PerfEventN> = <ValueN>