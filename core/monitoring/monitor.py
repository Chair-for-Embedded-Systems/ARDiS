from dataclasses import dataclass, field
from multiprocessing.pool import ThreadPool
from timeit import default_timer as timer
from queue import Queue,Empty

import os
import sys
import threading
import time

# Only required if run from this files main
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from core.monitoring.polling.poll_app_level_events import PollerAppLevel, ResultCorePolling, ResultPIDPolling
from core.monitoring.polling.poll_system_level_events import PollerSystemLevel, ResultSystemPolling
from core.monitoring.polling.poll_procfs import poll_affinity, poll_frequency
from core.monitoringmode import MonitoringMode
from core.reporter import Reporter
from core.monitoring.report_helper import ReportHelper
from core.monitoring.reportable_result import PeriodicPIDResult, PeriodicCoreResult, ReportableResult

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
        self.__report_helper = ReportHelper(reporter)
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
            result_one_shot = pool.apply_async(self.__system_level_poller.start_one_shot)
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
                    # Start report thread
                    #pool.apply_async(
                    #    func=self.__report_periodic_events_core, 
                    #    args=([sys_level_thread.get(), res_perf_apps.get(), self.__tracking_config]),
                    #    error_callback=(lambda error: print(f"[reporter] exception: {error}"))
                    #)
                    self.__reporting_queue.put_nowait(result)
                    #result.report(DummyReporter())

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
                    #result.report(DummyReporter())
                    # Start report thread
                    #pool.apply_async(
                    #    func=self.__report_periodic_events_pid,
                    #    args=([sys_level_thread.get(), app_level_thread.get(), self.__tracking_config]),
                    #    error_callback=(lambda error: print(f"[reporter] exception: {error}"))
                    #)

            # Stop perf thread for system wide events and report the results.
            self.__system_level_poller.stop_one_shot()            
            self.__report_helper.report_one_shot(result_one_shot.get().events, timer() - self.__start_time)
            reporting_thread.wait(timeout=self.__sampling_rate_sec*5)

    def __run_reporter(self) -> None:
        while self.__running:
            try:
                result = self.__reporting_queue.get(timeout=self.__sampling_rate_sec)
                result.report(self.reporter)
            except Empty:
                continue

    def __report_periodic_events_core(
        self,
        sys_events: ResultSystemPolling,
        app_events: ResultCorePolling,
        tracking_config: TrackingConfig,
        report_mapping: bool = True,
        report_multiplex: bool = False
        ) -> None:
        elapsed_time_sec = timer() - self.__start_time
        
        if app_events:
            if report_mapping:
                self.__report_helper.report_current_mapped_cores(tracking_config.cores_to_track, elapsed_time_sec)
            if report_multiplex:
                self.__report_helper.report_mulitplexing("app_level", app_events.event_to_pct_running, elapsed_time_sec)

            self.__report_helper.report_periodic_app_events_core_moitoring(
                app_events=app_events,
                elapsed_time_sec=elapsed_time_sec,
                core_to_freq=poll_frequency(tracking_config.cores_to_track),
                core_to_app=tracking_config.core_to_app
            )
        
        self.__report_helper.report_periodic_system_events(elapsed_time_sec, sys_events.events)

    def __report_periodic_events_pid(
        self,
        sys_events: ResultSystemPolling,
        app_events: ResultPIDPolling,
        tracking_config: TrackingConfig,
        report_mapping: bool = True,
        report_multiplex: bool = False
        ) -> None:
        
        elapsed_time_sec = timer() - self.__start_time
        
        if app_events:
            pid_to_affinity = poll_affinity(set(app_events._pids))
            core_to_freq = poll_frequency(set(core for affinity in pid_to_affinity.values() for core in affinity))
            
            if report_multiplex:
                self.__report_helper.report_mulitplexing("app_level",app_events.event_to_pct_running, elapsed_time_sec)
            
            if report_mapping:
                self.__report_helper.report_current_mapped_cores(set(core_to_freq.keys()), elapsed_time_sec)
            
            self.__report_helper.report_periodic_app_events_pid_monitoring(
                app_events=app_events,
                elapsed_time_sec=elapsed_time_sec,
                pid_to_affinity=pid_to_affinity,
                pid_to_app=tracking_config.pid_to_app,
                core_to_freq=core_to_freq
            )

        self.__report_helper.report_periodic_system_events(elapsed_time_sec, sys_events.events)

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
    
    # TODO 
    def getMetricAtCore(self, core: int, event: str) -> float|int|None:
        raise NotImplementedError

    def getMetricForPID(self, pid: int, event: str) -> float|int|None:
        raise NotImplementedError
    
    def getSystemWideMetric(self, event: str) -> float|int|None:
        raise NotImplementedError

    def getElapsedTime(self) -> float:
        raise NotImplementedError

    def recordPeriodicEntry(self, entry: str) -> None:
        raise NotImplementedError

# Debug
class DummyReporter(Reporter):
    
    def __init__(self):
        pass

    def logPeriodicCounters(self, data):
        print(data)

    def logEvent(self, event):
        print(event)

    def logExecutionTime(self, app_name, core, time):
        print(f"{app_name} {core} {time}")


if __name__ == '__main__':
    
    import config
    
    monitor = Monitor(
        sampling_rate_sec=config.sampling_rate / 1000,
        periodic_app_level_events=config.periodic_app_level_events,
        periodic_system_level_events=config.periodic_system_wide_events,
        one_shot_system_level_events=config.one_shot_system_wide_events,
        reporter=DummyReporter(),
        inital_tracking_config=TrackingConfig(monitor_mode=MonitoringMode.PERIODIC_ON_CORE)
    )

    tracking_config=TrackingConfig(
        monitor_mode=MonitoringMode.PERIODIC_ON_CORE,
        app_to_core={"streamcluster": 4},
        app_to_pid={"streamcluster" : 3034853}
    )

    monitor.start()

    try:
        time.sleep(1)
        monitor.update_tracking_config(next_config=tracking_config)
        time.sleep(10)
    except KeyboardInterrupt as k:
        pass
    monitor.stop()
