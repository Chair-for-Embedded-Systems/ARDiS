from ardis.core.reporter import Reporter
from ardis.core.buffering.event_buffer import EventBuffer

from .monitor import Monitor, TrackingConfig

def create_monitor(
    reporter: Reporter,
    event_buffer: EventBuffer,
    initial_tracking_config: TrackingConfig,
    periodic_app_level_events: list[str],
    periodic_system_wide_events: list[str],
    one_shot_system_wide_events: list[str],
    sampling_interval_ms: int,
    monitoring_backend: str = "perf",
    monitor_core_temperatures: bool = False
) -> Monitor:
    """
    Factory function to create a monitor based on the specified monitoring backend.
    """

    if monitoring_backend == "perf":
        from .monitor_perf import PerfBasedMonitor
        return PerfBasedMonitor(
            sampling_rate_ms=sampling_interval_ms,
            periodic_app_level_events=periodic_app_level_events,
            periodic_system_level_events=periodic_system_wide_events,
            one_shot_system_level_events=one_shot_system_wide_events,
            reporter=reporter,
            event_buffer=event_buffer,
            initial_tracking_config=initial_tracking_config,
            monitor_core_temperatures=monitor_core_temperatures
        )
    elif monitoring_backend == "daemon":
        
        # Check if the 'ardis_daemon' package is installed as this is currntly an optional dependency
        import importlib.util
        
        if importlib.util.find_spec("ardis_daemon") is None:
            raise RuntimeError(
                "Please make sure that the 'ardis_daemon' package is installed!\n" \
                "Alternatively, you can use the 'perf' monitoring backend instead of 'daemon'," \
                " by setting 'monitoring_backend=perf' the config file."
            )
        
        from ardis_daemon import find_binary_path
        BINARY_PATH = find_binary_path() 

        from .monitor_daemon import DaemonMonitor
        return DaemonMonitor(
            perf_daemon_path=str(BINARY_PATH),
            sampling_rate_ms=sampling_interval_ms,
            periodic_app_level_events=periodic_app_level_events,
            periodic_system_level_events=periodic_system_wide_events,
            one_shot_system_level_events=one_shot_system_wide_events,
            reporter=reporter,
            event_buffer=event_buffer,
            initial_tracking_config=initial_tracking_config,
            monitor_core_temperatures=monitor_core_temperatures
        )
    else:
        raise ValueError(f"Unsupported monitoring backend: {monitoring_backend}")
    