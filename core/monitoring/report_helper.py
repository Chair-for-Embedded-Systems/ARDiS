from core.monitoring.polling.poll_app_level_events import ResultCorePolling, ResultPIDPolling
from core.reporter import Reporter

class ReportHelper():
    def __init__(self, reporter: Reporter) -> None:
        self.reporter = reporter

    def report_periodic_app_events_core_moitoring(
        self,
        app_events: ResultCorePolling,
        elapsed_time_sec: float,
        core_to_freq: dict[int, float],
        core_to_app: dict[int, str],
    ):
        time_stamp = f"[{elapsed_time_sec:.2f}s]"
        for core, events in app_events.get_events().items():
            flatt_app_events = " | ".join([f"{event_name} = {value}" for event_name, value in events.items()])
            app_name_label = f"app = {core_to_app[core]}"
            core_label = f"Core {core}"
            frequency_label = f"frequency = {core_to_freq[core]}"
        
            periodic_app_event = f"{time_stamp} {core_label}: {app_name_label} | {frequency_label} | {flatt_app_events}"
            self.reporter.logPeriodicCounters(periodic_app_event)

    def report_periodic_app_events_pid_monitoring(
        self,
        app_events: ResultPIDPolling,
        elapsed_time_sec: float,
        pid_to_affinity: dict[int, list[int]],
        pid_to_app: dict[int, str],
        core_to_freq: dict[int, float],
        use_name_from_perf: bool = False
    ):           
        time_stamp = f"[{elapsed_time_sec:.2f}s]"
        for pid, events in app_events.get_events(aggregate_by_pid=True).items():
            flatt_app_events = " | ".join([f"{event_name} = {value}" for event_name, value in events.items()])
            
            cores = pid_to_affinity.get(pid, [])
            if not cores:
                continue
        
            app_name = f"app = {app_events.get_app_name(pid) if use_name_from_perf else pid_to_app[pid]}"
            one_affinity = len(cores) == 1
            core_label = f"Core {cores[0]}" if one_affinity else f"Cores {cores}"
            frequency_label = f"frequency = {core_to_freq[cores[0]]}" if one_affinity else f"frequency = not-available"

            periodic_app_event = f"{time_stamp} {core_label}: {app_name} | {frequency_label} | {flatt_app_events}"
            self.reporter.logPeriodicCounters(periodic_app_event)
        
    def report_periodic_app_events_tid_monitoring(
        self,
        app_events: ResultPIDPolling,
        elapsed_time_sec: float,
        tid_to_affinity: dict[int, list[int]],
        core_to_freq: dict[int, float],
    ):           
        time_stamp = f"[{elapsed_time_sec:.2f}s]"
        for tid, events in app_events.get_events(aggregate_by_pid=False).items():
            flatt_app_events = " | ".join([f"{event_name} = {value}" for event_name, value in events.items()])
            
            cores = tid_to_affinity.get(tid, [])
            if not cores:
                continue
        
            app_name = f"app = {app_events.get_app_name(tid)}"
            one_affinity = len(cores) == 1
            core_label = f"Core {cores[0]}" if one_affinity else f"Cores {cores}"
            frequency_label = f"frequency = {core_to_freq[cores[0]]}" if one_affinity else f"frequency = not-available"

            periodic_app_event = f"{time_stamp} {core_label}: {app_name} | {frequency_label} | {flatt_app_events}"
            self.reporter.logPeriodicCounters(periodic_app_event)

    def report_periodic_system_events(
        self,
        elapsed_time_sec: float,
        sys_events: dict[str, float],
    ):
        time_stamp = f"[{elapsed_time_sec:.2f}s]"
        sys_event_flat = " | ".join([f"{event_name} = {value:.2f}" for event_name,value in sys_events.items()])
    
        periodic_system_event = f"{time_stamp} SYSTEM: {sys_event_flat}"
        self.reporter.logPeriodicCounters(periodic_system_event)

    def report_one_shot(
        self,
        system_level_events: dict[str, float],
        elapsed_time_sec: float,
    ):
        self.reporter.logEvent(f"Total energy consumed (perf) =  {system_level_events['power/energy-psys/']}")
        self.reporter.logEvent(f"Total instructions executed = {system_level_events['instructions']}")
        self.reporter.logEvent(f"Total time elapsed (perf) = {elapsed_time_sec:.2f} seconds")

    def report_current_mapped_cores(
        self,
        mapped_cores: set[int],
        elapsed_time_sec: float
    ):
        time_stamp = f"[{elapsed_time_sec:.2f}s]"
        self.reporter.logPeriodicCounters(f"{time_stamp} Current mapped cores: {list(mapped_cores)}")

    def report_mulitplexing(
        self,
        category: str,
        event_to_pct_running: dict[str, int],
        elapsed_time_sec: float
    ):
        time_stamp = f"[{elapsed_time_sec:.2f}s]"
        flat_multiplexed_events = " | ".join([f"{event} = {pct/100} " for event, pct in event_to_pct_running.items()])
        self.reporter.logPeriodicCounters(f"{time_stamp} MULTIPLEXING ({category}): {flat_multiplexed_events}")