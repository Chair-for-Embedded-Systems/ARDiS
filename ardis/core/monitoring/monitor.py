from dataclasses import dataclass, field

from abc import ABC, abstractmethod
from ardis.core.monitoringmode import MonitoringMode
from ardis.benchmarks.application import Application

@dataclass
class TrackingConfig:
    """
    This class represents a configuration for the monitor.
    When using `MonitoringMode.PERIODIC_ON_CORE`, an application needs to be present
    in the `app_to_core` and `app_to_pid` dict. Otherwise it will not be tracked.
    For `MonitorngMode.PERIODIC_ON_PID`, only the `app_to_pid` dict is necessary.
    """
    monitor_mode: MonitoringMode
    
    app_to_cores: dict[Application, set[int]] = field(default_factory=dict)
    app_to_pid: dict[Application, int] = field(default_factory=dict)
    
    core_to_app: dict[int, Application] = field(init=False)
    cores_to_track: set[int] = field(init=False)
    pid_to_app: dict[int, Application] = field(init=False)
    pids_to_track: set[int] = field(init=False)
    
    def __post_init__(self):
        self.pid_to_app = {pid: app for app,pid in self.app_to_pid.items()}
        self.core_to_app = {core: app for app, cores in self.app_to_cores.items() for core in cores}
        
        self.pids_to_track = set(self.app_to_pid.values())
        # Only track cores where the corresponding app has started i.e pid != -1
        self.cores_to_track = {core for core, app in self.core_to_app.items() 
                               if app in self.app_to_pid and self.app_to_pid[app] != -1}
    

class Monitor(ABC):

    @abstractmethod
    def update_tracking_config(self, next_config: TrackingConfig):
        """
        Adds the given config to the update queue of the monitor, which will be applied in the next sample epoch.
        This method can be called multiple times but only the last update gets applied to the monitor.
        This call can block for a very short amount of time.
        """
        raise NotImplementedError("The update_tracking_config method must be implemented by subclasses of Monitor.")
    
    @abstractmethod
    def start(self):
        """
        Starts the monitoring thread. This call may block for a short amount of time.
        """
        raise NotImplementedError("The start method must be implemented by subclasses of Monitor.")

    @abstractmethod
    def stop(self):
        """
        Stops the monitoring thread. This call blocks until the moitor is stopped or a timeout (5 * sampling_rate) is reached.
        If the monitor is currently **not** running this call will return immediatly.
        """
        raise NotImplementedError("The stop method must be implemented by subclasses of Monitor.")
        