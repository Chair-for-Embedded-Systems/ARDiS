from __future__ import annotations
from dataclasses import dataclass
from .application_event import ApplicationEvent
from .system_event import SystemEvent, TemperatureEvent

@dataclass
class PeriodicLog:
    app_events: list[ApplicationEvent]
    sys_events: list[SystemEvent]
    temp_events: list[TemperatureEvent]
    
    @classmethod
    def from_log_file(cls, file_path: str) -> PeriodicLog:
        application_events: list[ApplicationEvent] = []
        system_events: list[SystemEvent] = []
        temp_events: list[TemperatureEvent] = []
        with open(file_path, 'r') as file:
            for line in file:
                line = line.strip()
                try:
                    if "app = " in line:
                        event = ApplicationEvent.from_periodic_log_line(line)
                        application_events.append(event)
                        continue
                    if "SYSTEM:" in line:
                        event = SystemEvent.from_log_line(line)
                        system_events.append(event)
                        continue
                    if "Temperature (°C):" in line:
                        event = TemperatureEvent.from_log_line(line)
                        temp_events.append(event)
                        continue
                    if "Current mapped" in line:
                        continue
                    print(f"Unrecognized line format: {line}")
                except ValueError as e:
                    print(f"Skipping line due to error: {e}")
        return cls(
            app_events=application_events,
            sys_events=system_events,
            temp_events=temp_events
        )
    
    @property
    def periodic_application_events_labels(self) -> list[str]:
        """Returns the labels of the application events recorded in the periodic log."""
        if not self.app_events:
            return []
        application_events = self.app_events[0].perf_events.keys()
        return list(application_events)

    @property
    def periodic_system_events_labels(self) -> list[str]:
        """Returns the labels of the system events recorded in the periodic log."""
        if not self.sys_events:
            return []
        system_events = self.sys_events[0].perf_events.keys()
        return list(system_events)
    
    def get_application_index(self) -> dict[str, set[int]]:
        """Returns a dictionary mapping application names to their instance IDs."""
        app_index: dict[str, set[int]] = dict()
        for app_event in self.app_events:
            if app_event.application_name not in app_index:
                app_index[app_event.application_name] = set()
            app_index[app_event.application_name].add(app_event.instance_id)
        
        return app_index

    def get_threads(self, instance_id: int) -> set[int]:
        """Returns the set of thread IDs associated with a given application instance ID."""
        tids: set[int] = set()
        for app_event in self.app_events:
            if app_event.instance_id == instance_id and app_event.tid is not None:
                tids.add(app_event.tid)
        return tids

    def get_events(self, instance_id: int, thread_id: int | None = None) -> list[ApplicationEvent]:
        """Returns the list of application events for a given instance ID and optional thread ID."""
        events: list[ApplicationEvent] = []
        for app_event in self.app_events:
            if app_event.instance_id == instance_id and (thread_id is None or app_event.tid == thread_id):
                events.append(app_event)
        return events
