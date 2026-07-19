from .monitor import Monitor, TrackingConfig

import threading
import time

from timeit import default_timer as timer
from queue import Queue, Empty

from ardis.core.monitoring.polling.poll_app_level_events import ResultPIDPolling
from ardis.core.monitoring.polling.poll_system_level_events import ResultSystemPolling
from ardis.core.monitoring.polling.poll_app_level_events import ResultCorePolling
from ardis.core.monitoringmode import MonitoringMode
from ardis.core.monitoring.reportable_result import ReportableResult, PeriodicPIDResult, PeriodicCoreResult
from ardis.core.reporter import Reporter
from ardis.core.buffering.event_buffer import EventBuffer

from pydaemon.monitor import Monitor as PerfDaemonMonitor, Packet


def _pct_running(reading) -> float:
    if reading.enabled <= 0:
        return 100.0
    return reading.active / reading.enabled * 100


def _system_pct_running(system_raw: dict) -> dict[str, float]:
    return {name: _pct_running(reading) for name, reading in system_raw.items()}


class NativeMonitor(Monitor):
    """
    Monitor that utilizes a native C backend to collect performance data.
    It allows for more efficient data collection and lower overhead compared to the perf-based monitor.
    """
    def __init__(
        self,
        perf_daemon_path: str,
        sampling_rate_sec: float,
        periodic_app_level_events: list[str],
        periodic_system_level_events: list[str],
        one_shot_system_level_events: list[str], # Currently not used in the native monitor
        reporter: Reporter,
        event_buffer: EventBuffer | None,
        initial_tracking_config: TrackingConfig,
    ):
        self.__perf_daemon_path = perf_daemon_path
        self.__sampling_rate_sec = sampling_rate_sec
        self._periodic_app_level_events = periodic_app_level_events
        self._periodic_system_level_events = periodic_system_level_events
        self.reporter = reporter
        self.__event_buffer = event_buffer
        self.__tracking_config = initial_tracking_config

        self.__tracking_config_update_queue: Queue[TrackingConfig] = Queue()
        self.__reporting_queue: Queue[ReportableResult] = Queue()
        self.__tracked_pids: set[int] = set()
        self.__running = False
        self.__perf_thread: threading.Thread | None = None
        self.__start_time: float | None = None

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

    def update_tracking_config(self, next_config: TrackingConfig):
        self.__tracking_config_update_queue.put(next_config)

    def __process_update_queue(self, monitor: PerfDaemonMonitor) -> None:
        # Guard to prevent accidental calls from non-perf threads
        if self.__perf_thread and self.__perf_thread.ident != threading.get_ident():
            raise RuntimeError("Tried to process the update queue from a thread that is not the perf thread")

        # Get the latest tracking config from the queue, discarding any older ones
        update_queue = self.__tracking_config_update_queue
        if update_queue.qsize() > 0:
            discarded_updates = 0
            while update_queue.qsize() > 1:
                update_queue.get()
                discarded_updates += 1
            if discarded_updates > 3:
                print(f"[NativeMonitor] Warning: skipped {discarded_updates} updates. "
                      f"(sampling_rate > action_interval)")
            self.__tracking_config = update_queue.get()
        else:
            return  # No updates to process

        if self.__tracking_config.monitor_mode == MonitoringMode.PERIODIC_ON_CORE:
            # Check if the set of cores to track has changed
            cores_to_track = set(core for core in self.__tracking_config.core_to_app.keys() if core != -1)
            added_cores = cores_to_track - self.__tracked_pids
            removed_cores = self.__tracked_pids - cores_to_track
            self.__tracked_pids = cores_to_track
            if added_cores:
                monitor.add(*added_cores)
            if removed_cores:
                monitor.remove(*removed_cores)
        else:
            # Check if the set of PIDs to track has changed
            pids_to_track = set(pid for pid in self.__tracking_config.pids_to_track if pid != -1)
            added_pids = pids_to_track - self.__tracked_pids
            removed_pids = self.__tracked_pids - pids_to_track
            self.__tracked_pids = pids_to_track

            if added_pids:
                monitor.add(*added_pids)
            if removed_pids:
                monitor.remove(*removed_pids)

    def __run(self):

        mode = "tid" if self.__tracking_config.monitor_mode == MonitoringMode.PERIODIC_ON_TID else "pid"
        mode = "core" if self.__tracking_config.monitor_mode == MonitoringMode.PERIODIC_ON_CORE else mode

        with PerfDaemonMonitor(
            perf_app_events=self._periodic_app_level_events,
            perf_system_events=self._periodic_system_level_events,
            interval_ms=int(self.__sampling_rate_sec * 1000),
            perfd_path=self.__perf_daemon_path,
            mode=mode
        ) as perf_monitor:
            reporter_thread = threading.Thread(target=self.__run_reporter)
            reporter_thread.start()

            while self.__running:

                # Process any pending tracking config updates before reading the next packet
                self.__process_update_queue(perf_monitor)

                # Prevent busy waiting if nothing is being tracked
                if not self.__tracked_pids and not self._periodic_system_level_events:
                    time.sleep(self.__sampling_rate_sec)
                    continue

                packet = perf_monitor.read()

                if self.__tracking_config.monitor_mode == MonitoringMode.PERIODIC_ON_CORE:
                    self.__handle_core_packet(packet)
                elif self.__tracking_config.monitor_mode in (MonitoringMode.PERIODIC_ON_PID, MonitoringMode.PERIODIC_ON_TID):
                    self.__handle_pid_packet(packet)

            reporter_thread.join(timeout=self.__sampling_rate_sec * 5)

    def __handle_pid_packet(self, packet: Packet):

        pid_to_app = self.__tracking_config.pid_to_app
        pid_to_app_name = {pid: str(app) for pid, app in pid_to_app.items()}

        seen_pids: dict[int, None] = {}
        tid_to_events: dict[int, dict[str, int]] = {}
        tid_to_pid: dict[int, int] = {}
        tid_to_app_name: dict[int, str] = {}
        pid_to_affinity: dict[int, list[int]] = {}
        event_to_pct_running: dict[str, float] = {}

        for pid_result in packet.pids:
            seen_pids[pid_result.pid] = None
            tid_to_pid[pid_result.tid] = pid_result.pid
            tid_to_app_name[pid_result.tid] = pid_to_app_name.get(pid_result.pid, "unknown")
            pid_to_affinity[pid_result.tid] = pid_result.cores

            events: dict[str, int] = {}
            for name, reading in pid_result.values.items():
                events[name] = int(reading.scaled())
                pct = _pct_running(reading)
                event_to_pct_running[name] = min(event_to_pct_running.get(name, 100.0), pct)
            tid_to_events[pid_result.tid] = events

        pids = list(seen_pids.keys())

        app_events = ResultPIDPolling(pids, tid_to_events, tid_to_app_name, tid_to_pid, event_to_pct_running)

        
        sys_pct_running = _system_pct_running(packet.system_raw)
        sys_events = ResultSystemPolling(dict(packet.system_values), sys_pct_running) 

        core_to_freq = {i: f / 1000 for i, f in enumerate(packet.core_freqs_khz)}

        elapsed_time = packet.timestamp_ms / 1000.0  # Convert milliseconds to seconds
        result = PeriodicPIDResult(
            elapsed_time_sec=elapsed_time,
            app_events=app_events,
            sys_events=sys_events,
            pid_to_affinity=pid_to_affinity,
            core_to_freq=core_to_freq,
            pid_to_app=pid_to_app,
            log_individual_threads=True,
            log_mapped_cores=False
        )
        self.__reporting_queue.put_nowait(result)

        if buffer := self.__event_buffer:
            buffer.push_pid_and_sys_events(
                app_events=app_events.get_events(aggregate_by_pid=True),
                system_events=sys_events.events,
                frequencies=core_to_freq,
                relative_sample_duration=1.0,  # Not required for C backend
                pid_to_application=pid_to_app,
            )

    def __handle_core_packet(self, packet: Packet):

        core_to_events: dict[int, dict[str, int]] = {}
        event_to_pct_running: dict[str, float] = {}

        for core_result in packet.core_readings:
            events: dict[str, int] = {}
            for name, reading in core_result.values.items():
                events[name] = int(reading.scaled())
                pct = _pct_running(reading)
                # min(), not a conditional write -- see the identical
                # comment in __handle_pid_packet for why this matters.
                event_to_pct_running[name] = min(event_to_pct_running.get(name, 100.0), pct)
            core_to_events[core_result.core] = events

        app_events = ResultCorePolling(
            _core_to_events=core_to_events,
            event_to_pct_running=event_to_pct_running,
        )

        sys_pct_running = _system_pct_running(packet.system_raw)
        sys_events = ResultSystemPolling(dict(packet.system_values), sys_pct_running)

        # Computed once, reused below -- same redundancy fix as
        # __handle_pid_packet.
        core_to_freq = {i: f / 1000 for i, f in enumerate(packet.core_freqs_khz)}

        elapsed_time = packet.timestamp_ms / 1000.0  # Convert milliseconds to seconds
        result = PeriodicCoreResult(
            elapsed_time_sec=elapsed_time,
            app_events=app_events,
            sys_events=sys_events,
            core_to_freq=core_to_freq,
            core_to_app=self.__tracking_config.core_to_app,
        )
        self.__reporting_queue.put_nowait(result)

        # Add events to buffer
        if buffer := self.__event_buffer:
            buffer.push_core_and_sys_events(
                app_events=app_events.get_events(),
                system_events=sys_events.events,
                frequencies=core_to_freq,
                relative_sample_duration=1.0,  # Not required for C backend
                core_to_application=self.__tracking_config.core_to_app,
            )

    def __run_reporter(self):
        while self.__running:
            try:
                result = self.__reporting_queue.get(timeout=self.__sampling_rate_sec)
                result.report(self.reporter)
            except Empty:
                continue
