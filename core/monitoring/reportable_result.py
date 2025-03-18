from dataclasses import dataclass,field

from core.monitoring.polling.poll_app_level_events import ResultCorePolling, ResultPIDPolling
from core.monitoring.polling.poll_system_level_events import ResultSystemPolling
from core.reporter import Reporter

class ReportableResult:
    def report(self, reporter: Reporter) -> None:
        raise NotImplementedError
    
    def get_timestamp(self, elapsed_time_sec) -> str:
        return f"[{elapsed_time_sec:.2f}s]"

@dataclass    
class PeriodicPIDResult(ReportableResult):
    elapsed_time_sec: float
    app_events: ResultPIDPolling
    sys_events: ResultSystemPolling
    pid_to_affinity: dict[int, list[int]]
    core_to_freq: dict[int, float]
    pid_to_app: dict[int, str]
    use_name_from_perf: bool = field(default=False)
    log_mapped_cores: bool = field(default=True)
    log_event_multiplexing: bool = field(default=False)
    
    def report(self, reporter: Reporter) -> None:
        timestamp = self.get_timestamp(self.elapsed_time_sec)
        
        # Log mapped cores (optional)
        if self.log_mapped_cores:
            reporter.logPeriodicCounters(f"{timestamp} Current mapped cores: {list(self.core_to_freq.keys())}")

        # Log app multiplexing (optional)
        if self.log_event_multiplexing:
            flat_multiplexed_events = " | ".join([f"{event} = {pct/100} " for event, pct in self.app_events.event_to_pct_running.items()])
            reporter.logPeriodicCounters(f"{timestamp} MULTIPLEXING (app_level): {flat_multiplexed_events}")

        # Log app events
        for pid, events in self.app_events.get_events(aggregate_by_pid=True).items():
            flatt_app_events = " | ".join([f"{event_name} = {value}" for event_name, value in events.items()])
            cores = self.pid_to_affinity.get(pid, [])
            if not cores:
                continue
            app_name = f"app = {self.app_events.get_app_name(pid) if self.use_name_from_perf else self.pid_to_app[pid]}"
            one_affinity = len(cores) == 1
            core_label = f"Core {cores[0]}" if one_affinity else f"Cores {cores}"
            frequency_label = f"frequency = {self.core_to_freq[cores[0]]}" if one_affinity else f"frequency = not-available"

            periodic_app_event = f"{timestamp} {core_label}: {app_name} | {frequency_label} | {flatt_app_events}"
            reporter.logPeriodicCounters(periodic_app_event)
        
        # Log system event multiplexing (optional)
        if self.log_event_multiplexing:
            flat_multiplexed_events = " | ".join([f"{event} = {pct/100} " for event, pct in self.sys_events.pct_running.items()])
            reporter.logPeriodicCounters(f"{timestamp} MULTIPLEXING (sys_level): {flat_multiplexed_events}")

        # Log system events
        sys_event_flat = " | ".join([f"{event_name} = {value:.2f}" for event_name,value in self.sys_events.events.items()])
        periodic_system_event = f"{timestamp} SYSTEM: {sys_event_flat}"
        reporter.logPeriodicCounters(periodic_system_event)

@dataclass
class PeriodicCoreResult(ReportableResult):
    elapsed_time_sec: float
    app_events: ResultCorePolling
    sys_events: ResultSystemPolling
    core_to_freq: dict[int, float]
    core_to_app: dict[int, str]
    log_mapped_cores: bool = field(default=True)
    log_event_multiplexing: bool = field(default=True)

    def report(self, reporter: Reporter) -> None:
        
        timestamp = self.get_timestamp(elapsed_time_sec=self.elapsed_time_sec)
        
        # Log mapped cores (optional)
        if self.log_mapped_cores:
            reporter.logPeriodicCounters(f"{timestamp} Current mapped cores: {list(self.core_to_freq.keys())}")

        # Log application multiplexing (optional)
        if self.log_event_multiplexing:
            flat_multiplexed_events = " | ".join([f"{event} = {pct/100} " for event, pct in self.app_events.event_to_pct_running.items()])
            reporter.logPeriodicCounters(f"{timestamp} MULTIPLEXING (app_level): {flat_multiplexed_events}")

        # Log app events
        for core, events in self.app_events.get_events().items():
            flatt_app_events = " | ".join([f"{event_name} = {value}" for event_name, value in events.items()])
            app_name_label = f"app = {self.core_to_app[core]}"
            core_label = f"Core {core}"
            frequency_label = f"frequency = {self.core_to_freq[core]}"

            periodic_app_event = f"{timestamp} {core_label}: {app_name_label} | {frequency_label} | {flatt_app_events}"
            reporter.logPeriodicCounters(periodic_app_event)
        
        # Log system event multiplexing (optional)
        if self.log_event_multiplexing:
            flat_multiplexed_events = " | ".join([f"{event} = {pct/100} " for event, pct in self.sys_events.pct_running.items()])
            reporter.logPeriodicCounters(f"{timestamp} MULTIPLEXING (sys_level): {flat_multiplexed_events}")

        # Log system events
        sys_event_flat = " | ".join([f"{event_name} = {value:.2f}" for event_name,value in self.sys_events.events.items()])
        periodic_system_event = f"{timestamp} SYSTEM: {sys_event_flat}"
        reporter.logPeriodicCounters(periodic_system_event)

@dataclass
class OneShotSystemResult(ReportableResult):
    sys_events: ResultSystemPolling
    elapsed_time_sec: float

    def report(self, reporter: Reporter):
        events = self.sys_events.events
        reporter.logEvent(f"Total energy consumed (perf) =  {events['power/energy-psys/']}")
        reporter.logEvent(f"Total instructions executed = {int(events['instructions'])}")
        reporter.logEvent(f"Total time elapsed (perf) = {self.elapsed_time_sec:.2f} seconds")
        
        flat_multiplexed_events = " | ".join([f"{event} = {pct/100} " for event, pct in self.sys_events.pct_running.items()])
        reporter.logEvent(f"MULTIPLEXING: {flat_multiplexed_events}")