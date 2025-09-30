from dataclasses import dataclass,field
from abc import ABC, abstractmethod

from ardis.core.monitoring.polling.poll_app_level_events import ResultCorePolling, ResultPIDPolling
from ardis.core.monitoring.polling.poll_system_level_events import ResultSystemPolling
from ardis.core.reporter import Reporter
from ardis.benchmarks.application import Application

class ReportableResult(ABC):
    """
    This class represents an abstract reportable result.
    Its primarly used in the monitor to pass data from the main monitoring thread to the reporting thread
    """
    @abstractmethod
    def report(self, reporter: Reporter) -> None:
        """
        Reports the data provided during initialisation with the given reporter
        """
        raise NotImplementedError
    
    def get_timestamp(self, elapsed_time_sec: float) -> str:
        """
        Returns the provided elapsed time as formatted string
        """
        return f"[{elapsed_time_sec:.2f}s]"

@dataclass    
class PeriodicPIDResult(ReportableResult):
    elapsed_time_sec: float
    app_events: ResultPIDPolling
    sys_events: ResultSystemPolling
    pid_to_affinity: dict[int, list[int]]
    core_to_freq: dict[int, float]
    pid_to_app: dict[int, Application]
    use_name_from_perf: bool = field(default=False)
    log_mapped_cores: bool = field(default=True)
    log_event_multiplexing: bool = field(default=False)
    log_individual_threads: bool = field(default=False)
    
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
        if self.log_individual_threads:
            self.__log_tid_events(reporter, timestamp)
        else:
            self.__log_pid_events(reporter, timestamp)
        
        # Log system event multiplexing (optional)
        if self.log_event_multiplexing:
            flat_multiplexed_events = " | ".join([f"{event} = {pct/100}" for event, pct in self.sys_events.pct_running.items()])
            reporter.logPeriodicCounters(f"{timestamp} MULTIPLEXING (sys_level): {flat_multiplexed_events}")

        # Log system events
        sys_event_flat = " | ".join([f"{event_name} = {value:.2f}" for event_name,value in self.sys_events.events.items()])
        periodic_system_event = f"{timestamp} SYSTEM: {sys_event_flat}"
        reporter.logPeriodicCounters(periodic_system_event)

    def __log_pid_events(self, reporter: Reporter, timestamp: str) -> None:
        for pid, events in self.app_events.get_events(aggregate_by_pid=True).items():
            flatt_app_events = " | ".join([f"{event_name} = {value}" for event_name, value in events.items()])
            
            # Skip pids whose affinity could not be determined (occurs when the process has ended)
            cores = self.pid_to_affinity.get(pid, [])
            if not cores:
                continue

            app_name = f"app = {self.app_events.get_app_name(pid) if self.use_name_from_perf else self.pid_to_app[pid].get_display_name()}"
            instance_label = f"IID = {self.pid_to_app[pid].get_instance_id()}"
            one_affinity = len(cores) == 1
            core_label = f"Core {cores[0]}" if one_affinity else f"Cores {cores}"
            pid_label = f"PID = {pid}"
            frequency_label = f"frequency = {self.core_to_freq[cores[0]]}" if one_affinity else f"frequency = not-available"

            periodic_app_event = f"{timestamp} {core_label}: {app_name} | {instance_label} | {pid_label} | {frequency_label} | {flatt_app_events}"
            reporter.logPeriodicCounters(periodic_app_event)
    
    def __log_tid_events(self, reporter: Reporter, timestamp: str, append_tid_to_name: bool = False) -> None:
        for tid, events in self.app_events.get_events(aggregate_by_pid=False).items():
            flatt_app_events = " | ".join([f"{event_name} = {value}" for event_name, value in events.items()])
            
            # Skip threads whose affinity could not be determined (occurs when the thread has ended)
            if cores := self.pid_to_affinity.get(tid):
                core = cores[0]
            else:
                continue
            
            pid = self.app_events._tid_to_pid[tid]
            app_name = self.app_events.get_app_name(pid) if self.use_name_from_perf else self.pid_to_app[pid].get_display_name()
            if append_tid_to_name:
                app_name+=f"_{tid}"

            app_field = f"app = {app_name}"
            instance_field = f"IID = {self.pid_to_app[pid].get_instance_id()}"
            tid_field = f"TID = {tid}"
            core_field = f"Core {core}"
            freq_field = f"frequency = {self.core_to_freq[core]}"

            periodic_app_event = f"{timestamp} {core_field}: {app_field} | {instance_field} | {tid_field} | {freq_field} | {flatt_app_events}"
            reporter.logPeriodicCounters(periodic_app_event)

@dataclass
class PeriodicCoreResult(ReportableResult):
    elapsed_time_sec: float
    app_events: ResultCorePolling
    sys_events: ResultSystemPolling
    core_to_freq: dict[int, float]
    core_to_app: dict[int, Application]
    log_mapped_cores: bool = field(default=True)
    log_event_multiplexing: bool = field(default=False)

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
            app_name_label = f"app = {self.core_to_app[core].get_display_name()}"
            instance_label = f"IID = {self.core_to_app[core].get_instance_id()}"
            core_label = f"Core {core}"
            frequency_label = f"frequency = {self.core_to_freq[core]}"

            periodic_app_event = f"{timestamp} {core_label}: {app_name_label} | {instance_label} | {frequency_label} | {flatt_app_events}"
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

    def report(self, reporter: Reporter) -> None:
        events = self.sys_events.events
        reporter.logEvent(f"Total energy consumed (perf) =  {events['power/energy-psys/']}")
        reporter.logEvent(f"Total instructions executed = {int(events['instructions'])}")
        reporter.logEvent(f"Total time elapsed (perf) = {self.elapsed_time_sec:.2f} seconds")
        
        flat_multiplexed_events = " | ".join([f"{event} = {pct/100} " for event, pct in self.sys_events.pct_running.items()])
        reporter.logEvent(f"MULTIPLEXING: {flat_multiplexed_events}")