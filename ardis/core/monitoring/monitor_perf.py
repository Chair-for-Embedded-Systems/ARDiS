import threading
import time

from multiprocessing.pool import ThreadPool, AsyncResult
from timeit import default_timer as timer
from queue import Queue, Empty

from ardis.core.monitoringmode import MonitoringMode
from ardis.core.monitoring.reportable_result import ReportableResult, PeriodicPIDResult, PeriodicCoreResult, OneShotSystemResult
from ardis.core.reporter import Reporter
from ardis.core.buffering.event_buffer import EventBuffer

from .monitor import Monitor, TrackingConfig
from .polling.poll_app_level_events import PollerAppLevel
from .polling.poll_system_level_events import PollerSystemLevel, ResultSystemPolling
from .polling.poll_procfs import poll_affinity, poll_frequency, poll_last_sceduled_cpu


class PerfBasedMonitor(Monitor):
    """
    Monitor that utilizes the Linux perf cli tool to collect performance data.
    """
    def __init__(
        self,
        sampling_rate_ms: int,
        periodic_app_level_events: list[str], 
        periodic_system_level_events: list[str],
        one_shot_system_level_events: list[str],
        reporter: Reporter,
        event_buffer: EventBuffer|None,
        initial_tracking_config: TrackingConfig,
        monitor_core_temperatures: bool = False
    ):
        
        self.__sampling_rate_sec = sampling_rate_ms / 1000.0
        self.__app_level_poller = PollerAppLevel(self.__sampling_rate_sec, periodic_app_level_events)
        self.__system_level_poller = PollerSystemLevel(self.__sampling_rate_sec, periodic_system_level_events, one_shot_system_level_events)
        self.__tracking_config = initial_tracking_config
        self.__tracking_config_update_queue: Queue[TrackingConfig] = Queue()
        self.reporter = reporter
        self.__reporting_queue: Queue[ReportableResult] = Queue()
        self.__running = False
        self.__perf_thread: threading.Thread | None = None
        self.__event_buffer = event_buffer
        self.__last_sample_timestamp: float | None = None
        self.__monitor_core_temperatures = monitor_core_temperatures

    def update_tracking_config(self, next_config: TrackingConfig):
        self.__tracking_config_update_queue.put(next_config)

    def start(self):
        self.__running = True
        self.__start_time = timer()
        self.__perf_thread = threading.Thread(target=self.__run)
        self.__perf_thread.start()

    def stop(self):
        self.__running = False

        if self.__perf_thread is None:
            return

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

    def __init_thermal_monitor(self):
        try:
            from ardis.core.monitoring.thermal import create_core_temp_monitor
            self.__temperature_monitor = create_core_temp_monitor()
        except Exception as e:
            raise RuntimeError(f"[Monitor] Failed to initialize temperature monitor: {e}")

    def __poll_freq_affinity_temp(
        self,
        pids: set[int],
        affinity_per_thread: bool = False
    ) -> tuple[dict[int, list[int]], dict[int, float], dict[int, float]]:
        """"
        Returns the affinity for each pid/tid and the frequency of the used cores
        """
        if affinity_per_thread:
            tid_to_affinity = poll_last_sceduled_cpu(pids)
            active_cores = set(core for core in tid_to_affinity.values())
            # Convert from dict[int, int] -> dict[int, list[int]]
            affinity = {k: [v] for k,v in tid_to_affinity.items()} 
        else:
            pid_to_affinity = poll_affinity(pids)
            active_cores = set(core for affinity in pid_to_affinity.values() for core in affinity)
            affinity = pid_to_affinity

        if self.__monitor_core_temperatures and self.__temperature_monitor:
            core_temps = self.__temperature_monitor.sample_core_temperature()
        else:
            core_temps = {}
        
        core_to_freq = poll_frequency(active_cores)
        return affinity, core_to_freq, core_temps
    
    def __poll_freq_temp(self, cores: set[int]) -> tuple[dict[int, float], dict[int, float]]:
        """
        Returns the frequency and temperature for the given set of cores.
        """
        if self.__monitor_core_temperatures and self.__temperature_monitor:
            core_temps = self.__temperature_monitor.sample_core_temperature()
        else:
            core_temps = {}
        
        core_to_freq = poll_frequency(cores)
        return core_to_freq, core_temps
        
    def __run(self):
        """
        Creates a thread pool to run multiple tasks in parallel:
        - perf-system-wide [one-shot] : Starts immediatly and stops when the monitoring should stop
        - perf-periodic-app [periodic] : Collects app level events
        - perf-periodic-system [periodic] : Collects system level events
        - reporting [periodic]: Formats and writes the results of the periodic events to the reporter
        """
        with ThreadPool(processes=4) as pool:
            
            # Start the thermal monitor if requested
            if self.__monitor_core_temperatures:
                self.__init_thermal_monitor()

            # Start perf thread for one-shot system events.
            system_one_shot_thread = pool.apply_async(self.__system_level_poller.poll_one_shot)
            reporting_thread = pool.apply_async(
                func=self.__run_reporter,
                error_callback=(lambda error: print(f"[thread_reporter] exception: {error}"))
            )

            while self.__running:

                # Update tracking configuration
                self.__process_update_queue()
                if not self.__tracking_config:
                    time.sleep(self.__sampling_rate_sec)
                    continue

                # Start thread that polls the system wide events
                sys_level_thread: AsyncResult[ResultSystemPolling] = pool.apply_async(
                    func=self.__system_level_poller.poll,
                    error_callback=(lambda error: print(f"[thread_poll_system_wide] exception: {error}"))
                )
                
                if self.__tracking_config.monitor_mode == MonitoringMode.PERIODIC_ON_CORE:
                    self.__monitor_core(pool, sys_level_thread)
                
                elif self.__tracking_config.monitor_mode == MonitoringMode.PERIODIC_ON_PID:
                    self.__monitor_pid(pool, sys_level_thread, per_thread_results=False)
                
                elif self.__tracking_config.monitor_mode == MonitoringMode.PERIODIC_ON_TID:
                    self.__monitor_pid(pool, sys_level_thread, per_thread_results=True)

            # Stop perf thread for system wide events and report the results.
            self.__system_level_poller.stop_one_shot()            
            sys_one_shot = system_one_shot_thread.get()
            system_one_shot_thread = OneShotSystemResult(
                sys_events=sys_one_shot,
                elapsed_time_sec=timer() - self.__start_time
            )
            system_one_shot_thread.report(self.reporter)
            reporting_thread.wait(timeout=self.__sampling_rate_sec*5)

            # Stop the thermal monitor if it was started
            if self.__monitor_core_temperatures and self.__temperature_monitor:
                self.__temperature_monitor.close()

    def __monitor_core(self, pool: ThreadPool, sys_level_thread: AsyncResult[ResultSystemPolling]) -> None:
        # Start thread that polls the application level events (via core tracking)
        app_level_thread = pool.apply_async(
            func=self.__app_level_poller.poll_by_core,
            args=([self.__tracking_config.cores_to_track]),
            error_callback=(lambda error: print(f"[thread_poll_app_level] exception: {error}"))
        )
        # Fetch frequency of cpu cores
        procfs_thread = pool.apply_async(
            func=self.__poll_freq_temp,
            args=([self.__tracking_config.cores_to_track])
        )
        # Wait for all polling threads
        app_events = app_level_thread.get()
        sys_events = sys_level_thread.get()
        frequency, temperatures = procfs_thread.get()

        relative_sample_duration = self.__get_relative_sample_duration()

        result = PeriodicCoreResult(
            elapsed_time_sec=timer() - self.__start_time,
            app_events=app_events,
            sys_events=sys_events,
            core_to_freq=frequency,
            core_to_app=self.__tracking_config.core_to_app,
            core_to_temperature=temperatures,
        )
        self.__reporting_queue.put_nowait(result)
        
        # Add events to buffer
        if buffer := self.__event_buffer:
            buffer.push_core_and_sys_events(
                app_events=app_events.get_events(),
                system_events=sys_events.events,
                frequencies=frequency,
                temperatures=temperatures,
                relative_sample_duration=relative_sample_duration,
                core_to_application=self.__tracking_config.core_to_app,
            )

    def __monitor_pid(self, pool: ThreadPool, sys_level_thread: AsyncResult[ResultSystemPolling], per_thread_results: bool) -> None:
        # Start thread that polls the application level events (via pid tracking)
        app_level_thread = pool.apply_async(
            func=self.__app_level_poller.poll_by_pid,
            args=([self.__tracking_config.pids_to_track]),
            error_callback=(lambda error: print(f"[thread_poll_app_level] exception: {error}"))
        )
        procfs_thread = pool.apply_async(
            func=self.__poll_freq_affinity_temp,
            args=([self.__tracking_config.pids_to_track, per_thread_results]),
            error_callback=(lambda error: print(f"[thread_poll_procfs] exception: {error}"))
        )

        app_events = app_level_thread.get()
        sys_events = sys_level_thread.get()
        affinity, frequency, temperatures = procfs_thread.get()
        
        relative_sample_duration = self.__get_relative_sample_duration()

        result = PeriodicPIDResult(
            elapsed_time_sec=timer() - self.__start_time,
            app_events=app_events,
            sys_events=sys_events,
            pid_to_affinity=affinity,
            core_to_freq=frequency,
            core_to_temperature=temperatures,
            pid_to_app=self.__tracking_config.pid_to_app,
            log_individual_threads=per_thread_results
        )

        self.__reporting_queue.put_nowait(result)

        # Add pid and sys events to buffer
        if buffer := self.__event_buffer:
            buffer.push_pid_and_sys_events(
                app_events=app_events.get_events(aggregate_by_pid=True),
                system_events= sys_events.events,
                frequencies=frequency,
                temperatures=temperatures,
                relative_sample_duration=relative_sample_duration,
                pid_to_application=self.__tracking_config.pid_to_app
            )
        
    def __get_relative_sample_duration(self) -> float:
        """
        Calculate relative sample duration (sample_duration + overhead / sample_duration).
        Assuming a sample duration of 100 ms:
            A value of 1 represents no overehad
            A value of 1.2 implies an sampling overhead of 20%, (i.e. 20 ms overhead)
        """
        if self.__last_sample_timestamp == None:
            # Estimation of overhead is not possible for first sample
            rel_sample_duration = 1.0
        else:
            rel_sample_duration = (timer() - self.__last_sample_timestamp) / self.__sampling_rate_sec
        
        self.__last_sample_timestamp = timer()
        return rel_sample_duration

    def __run_reporter(self) -> None:
        while self.__running:
            try:
                result = self.__reporting_queue.get(timeout=self.__sampling_rate_sec)
                result.report(self.reporter)
            except Empty:
                continue

    # Legacy
    # This methods are primarly here to ensure backwards compatibility.
    # They will be removed in the future.
    def getMetricAtCore(self, core: int, event: str) -> float|int|None:
        """@deprecated Get event buffer directly from the engine"""
        if buffer := self.__event_buffer:
            last_events_for_core = buffer.get_metrics_for_core(core, 1)[-1]
            if event_value := last_events_for_core.get(event):
                return event_value
        return None

    def getMetricForPID(self, pid: int, event: str) -> float|int|None:
        """@deprecated Get event buffer directly from the engine"""
        if buffer := self.__event_buffer:
            last_events_for_core = buffer.get_metrics_for_pid(pid, 1)[-1]
            if event_value := last_events_for_core.get(event):
                return event_value
        return None
    
    def getSystemWideMetric(self, event: str) -> float|int|None:
        """@deprecated Get event buffer directly from the engine"""
        if buffer := self.__event_buffer:
            last_sys_events = buffer.get_system_metrics(1)[-1]
            if event_value := last_sys_events.get(event):
                return event_value
        return None

    def getElapsedTime(self) -> float:
        return timer() - self.__start_time

    def recordPeriodicEntry(self, entry: str) -> None:
        self.reporter.logPeriodicCounters(f"[{str(round(self.getElapsedTime(), 2))}s] {entry}")