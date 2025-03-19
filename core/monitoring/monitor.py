import threading
import time

from dataclasses import dataclass, field
from multiprocessing.pool import ThreadPool
from timeit import default_timer as timer
from queue import Queue,Empty

from core.monitoring.polling.poll_app_level_events import PollerAppLevel
from core.monitoring.polling.poll_system_level_events import PollerSystemLevel
from core.monitoring.polling.poll_procfs import poll_affinity, poll_frequency
from core.monitoringmode import MonitoringMode
from core.monitoring.reportable_result import ReportableResult, PeriodicPIDResult, PeriodicCoreResult, OneShotSystemResult
from core.reporter import Reporter

@dataclass
class TrackingConfig:
    """
    This class represents a configuration for the monitor.
    """
    monitor_mode: MonitoringMode
    
    app_to_core: dict[str, int] = field(default_factory=dict)
    app_to_pid: dict[str, int] = field(default_factory=dict)
    
    core_to_app: dict[int, str] = field(init=False)
    cores_to_track: set[int] = field(init=False)
    pid_to_app: dict[int, str] = field(init=False)
    pids_to_track: set[int] = field(init=False)
    
    def __post_init__(self):
        self.pid_to_app = {pid: app for app,pid in self.app_to_pid.items()}
        self.core_to_app = {pid: app for app,pid in self.app_to_core.items()}
        self.pids_to_track = set(list(self.app_to_pid.values()))
        self.cores_to_track = set(list(self.app_to_core.values()))
    

class Monitor:

    def __init__(
        self,
        sampling_rate_sec: float,
        periodic_app_level_events: list[str], 
        periodic_system_level_events: list[str],
        one_shot_system_level_events: list[str],
        reporter: Reporter,
        inital_tracking_config: TrackingConfig 
    ):
        
        self.__app_level_poller = PollerAppLevel(sampling_rate_sec, periodic_app_level_events)
        self.__system_level_poller = PollerSystemLevel(sampling_rate_sec, periodic_system_level_events, one_shot_system_level_events)
        self.__sampling_rate_sec = sampling_rate_sec
        self.__tracking_config = inital_tracking_config
        self.__tracking_config_update_queue: Queue[TrackingConfig] = Queue()
        self.reporter = reporter
        self.__reporting_queue: Queue[ReportableResult] = Queue()
        self.__running = False

    def update_tracking_config(self, next_config: TrackingConfig):
        """
        Adds the given config to the update queue of the monitor, which will be applied in the next sample epoch.
        This method can be called multiple times but only the last update gets applied to the monitor.
        This call can block for a very short amount of time.
        """
        self.__tracking_config_update_queue.put(next_config)

    def start(self):
        """
        Starts the monitoring thread. This call is non blocking.
        """
        self.__running = True
        self.__start_time = timer()
        self.__perf_thread = threading.Thread(target=self.__run)
        self.__perf_thread.start()

    def stop(self):
        """
        Stops the monitoring thread. This call blocks until the moitor is stopped or a timeout (5 * sampling_rate) is reached.
        """
        self.__running = False
        perf_thread = self.__perf_thread
        perf_thread.join(timeout=self.__sampling_rate_sec * 5)
        
        if perf_thread.is_alive():
            print("Failed to stop monitoring thread (still alive)")
        
    
    def __process_update_queue(self):
        """
        Processes the update queue for the tracking configuration. 
        This should only be called from the perf thread, otherwise a RuntimeError gets thrown.
        """
        # Configuration should only be changed between sampling epochs and only the perf thread is aware of that.
        if self.__perf_thread and self.__perf_thread.ident != threading.get_ident():
            raise RuntimeError("Tried to process the update queue from an thread that is not the perf thread")

        update_queue = self.__tracking_config_update_queue
        
        if update_queue.qsize() == 0:
            return
        
        # Only use the most recent update, discard others. This will be the case if the action_interval < sampling_rate.
        discarded_updates = 0
        while(update_queue.qsize() > 1):
            _ = update_queue.get()
            discarded_updates += 1

        # Warn the user if the action intervall is probably to high or the sampling rate to low.
        if discarded_updates > 3:
            print(f"[Monitor] Warning: skipped {discarded_updates} updates. (sampling_rate > action_interval)")

        self.__tracking_config = update_queue.get()

    def __poll_freq_and_affinity(self, pids: set[int]) -> tuple[dict[int, list[int]], dict[int, float]]:
        """"
        Returns the affinity for each pid and the frequency of the used cores
        """
        pid_to_affinity = poll_affinity(pids)
        core_to_freq = poll_frequency(set(core for affinity in pid_to_affinity.values() for core in affinity))
        return pid_to_affinity, core_to_freq

    def __run(self):
        """
        Creates a thread pool to run multiple tasks in parallel:
        - perf-system-wide [one-shot] : Starts immediatly and stops when the monitoring should stop
        - perf-periodic-app [periodic] : Collects app level events
        - perf-periodic-system [periodic] : Collects system level events
        - reporting [periodic]: Formats and writes the results of the periodic events to the reporter
        """
        with ThreadPool(processes=4) as pool:
            # Start perf thread for one-shot system events.
            system_one_shot_thread = pool.apply_async(self.__system_level_poller.poll_one_shot)
            reporting_thread = pool.apply_async(self.__run_reporter)
            while self.__running:

                # Update tracking configuration
                self.__process_update_queue()
                if not self.__tracking_config:
                    time.sleep(self.__sampling_rate_sec)
                    continue

                # Start thread that polls the system wide events
                sys_level_thread = pool.apply_async(
                    func=self.__system_level_poller.poll,
                    error_callback=(lambda error: print(f"[thread_poll_system_wide] exception: {error}")))
                
                if self.__tracking_config.monitor_mode == MonitoringMode.PERIODIC_ON_CORE:
                    # Start thread that polls the application level events (via core tracking)
                    app_level_thread = pool.apply_async(
                        func=self.__app_level_poller.poll_by_core,
                        args=([self.__tracking_config.cores_to_track]),
                        error_callback=(lambda error: print(f"[thread_poll_app_level] exception: {error}"))
                    )
                    procfs_thread = pool.apply_async(
                        func=poll_frequency,
                        args=([self.__tracking_config.cores_to_track])
                    )
                    app_events = app_level_thread.get()
                    sys_events = sys_level_thread.get()
                    frequency = procfs_thread.get()
                    
                    result = PeriodicCoreResult(
                        elapsed_time_sec=timer() - self.__start_time,
                        app_events=app_events,
                        sys_events=sys_events,
                        core_to_freq=frequency,
                        core_to_app=self.__tracking_config.core_to_app,
                    )
                    self.__reporting_queue.put_nowait(result)

                elif self.__tracking_config.monitor_mode == MonitoringMode.PERIODIC_ON_PID:
                    # Start thread that polls the application level events (via pid tracking)
                    app_level_thread = pool.apply_async(
                        func=self.__app_level_poller.poll_by_pid,
                        args=([self.__tracking_config.pids_to_track]),
                        error_callback=(lambda error: print(f"[thread_poll_app_level] exception: {error}"))
                    )
                    procfs_thread = pool.apply_async(
                        func=self.__poll_freq_and_affinity,
                        args=([self.__tracking_config.pids_to_track])
                    )

                    app_events = app_level_thread.get()
                    sys_events = sys_level_thread.get()
                    affinity, frequency = procfs_thread.get()

                    result = PeriodicPIDResult(
                        elapsed_time_sec=timer() - self.__start_time,
                        app_events=app_events,
                        sys_events=sys_events,
                        pid_to_affinity=affinity,
                        core_to_freq=frequency,
                        pid_to_app=self.__tracking_config.pid_to_app
                    )

                    self.__reporting_queue.put_nowait(result)

            # Stop perf thread for system wide events and report the results.
            self.__system_level_poller.stop_one_shot()            
            sys_one_shot = system_one_shot_thread.get()
            system_one_shot_thread = OneShotSystemResult(
                sys_events=sys_one_shot,
                elapsed_time_sec=timer() - self.__start_time
            )
            system_one_shot_thread.report(self.reporter)
            reporting_thread.wait(timeout=self.__sampling_rate_sec*5)

    def __run_reporter(self) -> None:
        while self.__running:
            try:
                result = self.__reporting_queue.get(timeout=self.__sampling_rate_sec)
                result.report(self.reporter)
            except Empty:
                continue

    # Legacy
    def updateTrackedMapping(self, mapping: dict[str, int]) -> None:
        """@deprecated Use update_tracking_config"""
        current = self.__tracking_config
        update_config = TrackingConfig(
            monitor_mode=current.monitor_mode,
            app_to_core=mapping,
            app_to_pid=current.app_to_pid
        )
        self.update_tracking_config(update_config)
    
    def updateTrackedPIDs(self, pids: dict[str, int]) -> None:
        """@deprecated Use update_tracking_config"""
        current = self.__tracking_config
        update_config = TrackingConfig(
            monitor_mode=current.monitor_mode,
            app_to_core=current.app_to_core,
            app_to_pid=pids
        )
        self.update_tracking_config(update_config)    

    def updateCoreFrequencies(self, core_frequencies: dict[int, float]):
        """@deprecated Monitor measures the frequency on its own"""
        pass
    
    # TODO (Event buffer is not yet implemented)
    def getMetricAtCore(self, core: int, event: str) -> float|int|None:
        raise NotImplementedError

    def getMetricForPID(self, pid: int, event: str) -> float|int|None:
        raise NotImplementedError
    
    def getSystemWideMetric(self, event: str) -> float|int|None:
        raise NotImplementedError

    def getElapsedTime(self) -> float:
        return timer() - self.__start_time

    def recordPeriodicEntry(self, entry: str) -> None:
        self.reporter.logPeriodicCounters(f"[{str(round(self.getElapsedTime(), 2))}s] {entry}")