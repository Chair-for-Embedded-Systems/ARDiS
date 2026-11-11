from dataclasses import dataclass
import os
import shutil
import threading
import time
from timeit import default_timer as timer


from ardis.benchmarks import Application
from ardis.core.buffering.deque_based_event_buffer import DequeBasedEventBuffer, EventBuffer
from ardis.core.buffering.action_buffer import ActionBuffer
from ardis.core.dvfs import DVFSPolicy
from ardis.core.monitoring import Monitor, TrackingConfig, create_monitor
from ardis.core.mapping import MappingPolicy, MappingException
from ardis.core.migration import MigrationPolicy
from ardis.core.monitoringmode import MonitoringMode
from ardis.core.reporter import Reporter
from ardis.core.scheduler import Scheduler
from ardis.core.system_state import SystemState

thread_queue_lock = threading.Lock()
system_state_lock = threading.Lock()

@dataclass(frozen=True, slots=True)
class EngineConfig:
    # Experiment
    experiment_name: str
    results_folder: str

    # Policies
    scheduler: Scheduler
    mapping_policy: MappingPolicy
    dvfs_policy: DVFSPolicy | None
    migration_policy: MigrationPolicy | None
    action_interval_ms: float

    # Monitoring / Sampling
    monitoring_interval_ms: int
    monitoring_mode: MonitoringMode
    periodic_app_level_events: list[str]
    periodic_system_wide_events: list[str]
    periodic_system_wide_events_one_shot: list[str]
    monitoring_backend: str
    monitor_core_temperatures: bool

    # Other
    runtime_temp_dir: str
    debug: bool = False


class Engine:
    def __init__(self, engine_config: EngineConfig) -> None:
        
        self._cfg = engine_config
        
        self.running: bool = False
        self.__threads: dict[Application, threading.Thread] = {}
        self.__active_threads: list[Application] = []
        self.__waiting_threads: list[Application] = []

        self.reporter: Reporter = Reporter(engine_config.experiment_name, engine_config.results_folder)
        self.event_buffer: EventBuffer = DequeBasedEventBuffer(capacity=10, collect_total_metrics=True)
        self.action_buffer: ActionBuffer = ActionBuffer(capacity=10)
        
        self.__start_time: float = 0.0
        self.__app_to_pid: dict[Application, int] = {}
        self.__app_to_cores: dict[Application, set[int]] = {}
        self.__epoch: int = 0
        self.__monitor: Monitor | None = None

        #self.__debug = engine_config.debug

        self.__clear_runtime_data()

    def __start_engine(self) -> None:
        self.running = True
        self.__start_time = timer()
        
        # Start the monitoring thread if monitoring is enabled
        if self._cfg.monitoring_mode != MonitoringMode.OFF and self.__monitor:
            self.__monitor.start()

    def __launchApp(self, app: Application, cores: set[int]) -> None:
        
        # Execute and meassure the execution time of the application
        start = timer()
        try:
            app.execute(cores)
        except Exception as e:
            print(f"Error occurred while executing {app}: {e}")
        end = timer()
        
        # keeping the lock until properly evaluated
        with system_state_lock:
            cores = self.__app_to_cores.pop(app)
            self.__app_to_pid.pop(app)

            if self._cfg.monitoring_mode != MonitoringMode.OFF and self.__monitor:
                self.__monitor.update_tracking_config(
                    TrackingConfig(
                        monitor_mode=self._cfg.monitoring_mode,
                        app_to_cores=self.__app_to_cores.copy(),
                        app_to_pid=self.__app_to_pid.copy()
                    )
                )
        
        with thread_queue_lock:
            self.__active_threads.remove(app)
        
        core_str = ','.join([str(c) for c in cores])

        self.reporter.logEvent(event=f"[Core(s) {core_str}]: {app} finished execution!", echo=self._cfg.debug)
        self.reporter.logEvent(event=f"[Core(s) {core_str}]: {app}'s execution time = {end - start:.2f} s", echo=self._cfg.debug)
        self.reporter.logExecutionTime(app.get_display_name(), core_str, end - start)
        
    def getProcessID(self, app: Application, attempts: int = 20, delay: float = 0.005) -> None:
        """
        Tries to get the PID of the application by checking multiple times with a delay in between.
        This allows quick discovery of the PID for fastly starting applications.
        """
        for _ in range(attempts):
            # Try to get the PID of the application
            if pid := app.get_pid():
                with system_state_lock:
                    self.__app_to_pid[app] = pid
                if self._cfg.debug:
                    msg_pid_of_app = f"[{self.getElapsedTime():.2f}s]: PID of {app} is {pid}"
                    self.reporter.logEvent(msg_pid_of_app, echo=True)
                return
            
            # Wait for the specified delay before checking again
            time.sleep(delay)
        
    def getElapsedTime(self) -> float:
        """Returns the elapsed time in seconds since the workload was started."""
        return timer() - self.__start_time
    
    def __startThread(self, app: Application) -> None:
        print(f"[{self.getElapsedTime():.2f}s] Starting thread for {app.get_display_name()}")
        self.__threads[app].start()
        
        with thread_queue_lock:
            self.__waiting_threads.remove(app) # remove is not atomic
            self.__active_threads.append(app)

        if self._cfg.debug:
            msg_thread_started = f"[{self.getElapsedTime():.2f}s] Thread for {app.get_display_name()} started!"
            self.reporter.logEvent(msg_thread_started, echo=True)

    def executeWorkload(self, applications: list[Application]) -> None:
        
        self.__waiting_threads = list(applications)
        
        self._cfg.scheduler.register_workload(applications)
        self._cfg.mapping_policy.register_workload(applications)

        # Execute initial DVFS policy (if present)
        if self._cfg.dvfs_policy is not None:
            self._cfg.dvfs_policy.apply_initial_state()
        
        # Prepare the monitor if monitoring is enabled
        self.__inititalize_monitor()

        # Then start the workload execution
        try:
            self.__start_engine()
        except Exception as e:
            raise RuntimeError(f"Failed to start the engine: {e}")

        # Control loop
        while self.running:

            # Check if all threads are done before finishing
            with thread_queue_lock:
                if not self.__active_threads and not self.__waiting_threads:
                    self.__stop_engine()
                    break
            
            with system_state_lock:
                elapsed_time_sec = self.getElapsedTime()
                
                # Get or update the PIDs of the active applications. This is necessary as some applications change their PID during execution.
                self.__update_pids()
                            
                # Construct system state object, which gets passed to the individual policies
                system_state: SystemState = SystemState(
                    start_time=self.__start_time,
                    elapsed_time_sec=elapsed_time_sec,
                    app_to_cores=self.__app_to_cores,
                    app_to_pid=self.__app_to_pid,
                    epoch=self.__epoch,
                    event_buffer=self.event_buffer,
                    action_buffer=self.action_buffer
                )

                # Check scheduler to see if any applications are scheduled to start
                self.__launch_waiting_threads(system_state)

                # Execute Migration-Policy
                self.__execute_migration_policy(system_state)

                # Execute DVFS-Policy
                self.__execute_dvfs_policy(system_state)
                    
                # Update tracking config
                if self._cfg.monitoring_mode != MonitoringMode.OFF and self.__monitor:
                    self.__monitor.update_tracking_config(
                        TrackingConfig(self._cfg.monitoring_mode, self.__app_to_cores.copy(), self.__app_to_pid.copy())
                    )

                # any other periodic action here
           
            # Increment the epoch counter and sleep for the action interval
            self.__epoch += 1
            time.sleep(self._cfg.action_interval_ms / 1000.0)
    
    def __inititalize_monitor(self):
        
        if self._cfg.monitoring_mode == MonitoringMode.OFF:
            self.__monitor = None
            return
        
        self.__monitor = create_monitor(
            sampling_interval_ms=self._cfg.monitoring_interval_ms,
            periodic_app_level_events=self._cfg.periodic_app_level_events,
            periodic_system_wide_events=self._cfg.periodic_system_wide_events,
            one_shot_system_wide_events=self._cfg.periodic_system_wide_events_one_shot,
            reporter=self.reporter,
            event_buffer=self.event_buffer,
            initial_tracking_config=TrackingConfig(
                monitor_mode=self._cfg.monitoring_mode,
                app_to_cores=self.__app_to_cores,
            ),
            monitoring_backend=self._cfg.monitoring_backend,
            monitor_core_temperatures=self._cfg.monitor_core_temperatures
        )

    def __launch_waiting_threads(self, system_state: SystemState) -> None:
        # Requires SystemState lock to be held by the caller
        
        # Check if the application is scheduled to start and if the thread is not already running
        for app in list(self.__waiting_threads):
            
            if not self._cfg.scheduler.is_time_to_launch(app, system_state):
                continue
                
            # Get the cores assigned to the application
            try:
                cores = self._cfg.mapping_policy.get_mapping(app, system_state)
            except MappingException as e:
                self.reporter.logEvent(f"[{self.getElapsedTime():.2f}s]: {e.message}", echo=True)
                continue
            self.__app_to_cores[app] = cores
            self.__app_to_pid[app] = -1  
                
            # Start the application thread
            self.__threads[app] = threading.Thread(target=self.__launchApp, args=(app, cores))
            self.__startThread(app)

            # Start a thread to fast discover the PID
            pid_thread = threading.Thread(target=self.getProcessID, args=(app,))
            pid_thread.start()


    def __execute_migration_policy(self, system_state: SystemState) -> None:

        if self._cfg.migration_policy is None:
            return
        
        try:
            mig_actions = self._cfg.migration_policy.get_migration_actions(system_state)
            self._cfg.migration_policy.apply_migration_actions(mig_actions, self.__app_to_pid, self.__app_to_cores)
        except Exception as e:
            self.reporter.logEvent(f"[{self.getElapsedTime():.2f}s]: Error occurred while executing migration policy: {e}", echo=True)
            return

        # Log migration actions if desired
        if self._cfg.debug:
            for action in mig_actions:
                msg_app_migrated = f"[{self.getElapsedTime():.2f}s] Migrated {action.app} from core {action.source} to core {action.destination}"
                self.reporter.logEvent(msg_app_migrated, echo=True)
                        
        # Writes the migration action to the action buffer. 
        # Since this is done here, the dvfs poilcy will have access to this information.
        if mig_actions:
            self.action_buffer.push_migration_actions(self.__epoch, mig_actions)

    def __execute_dvfs_policy(self, system_state: SystemState) -> None:
        
        if self._cfg.dvfs_policy is None:
            return
        
        try:
            dvfs_actions = self._cfg.dvfs_policy.get_dvfs_actions(system_state)
            self._cfg.dvfs_policy.apply_dvfs_actions(dvfs_actions)
        except Exception as e:
            self.reporter.logEvent(f"[{self.getElapsedTime():.2f}s]: Error occurred while executing DVFS policy: {e}", echo=True)
            return
                        
        # Log dvfs actions if desired
        if self._cfg.debug:
            for action in dvfs_actions:
                msg_app_migrated = f"[{self.getElapsedTime():.2f}s] Changed frequency of core {action.core_id} to {action.frequency_mhz} Mhz"
                self.reporter.logEvent(msg_app_migrated, echo=True)

        # Write dvfs action to action buffer
        if dvfs_actions:
            self.action_buffer.push_dvfs_actions(self.__epoch, dvfs_actions)

    def __update_pids(self):
        # Requires SystemState lock to be held by the caller
        # Update pid of (active) apps. This is necessary as there are some benchmark applications
        # which change their PID during execution.
        # All PARSEC applications keep their PIDs,
        # Some SPEC2006 applications change their PIDs (e.g. bzip2, ...),
        with thread_queue_lock:
            for app in self.__active_threads:
                if pid := app.get_pid():
                    if self.__app_to_pid[app] != pid:
                        MigrationPolicy._setAffinity(pid, self.__app_to_cores[app])
                        self.__app_to_pid[app] = pid

    def __stop_engine(self):
        self.running = False
        self.endtime = timer()
        elapsed_time_sec = self.endtime - self.__start_time
    
        msg_exp_finished = f"[{self.getElapsedTime():.2f}s]: Experiment Finished!"
        msg_total_time = f"Total execution time of experiment = {elapsed_time_sec:.2f}s"
    
        self.reporter.logEvent(msg_exp_finished, echo=True)
        self.reporter.logEvent(msg_total_time, echo=True)
        
        # Stop the monitoring thread
        if self.__monitor:
            self.__monitor.stop()
        
        # Clear the caches after the experiment is done
        self.__clearCaches()
        
        # Restore initial CPU state
        if self._cfg.dvfs_policy:
            self._cfg.dvfs_policy.cpu_freq_manager.restore_initial_state() 

    def interrupt(self):
        """Interrupt the engine and terminate all running applications."""
        self.running = False
        if self.__monitor:
            self.__monitor.stop()
        for app in self.__active_threads + self.__waiting_threads:
            app.terminate()

    def __clearCaches(self):
        try:
            os.sync() # Flush all caches and buffers to disk
            with open('/proc/sys/vm/drop_caches', 'w') as f:
                # 1 = page cache, 2 = free slab objects, 3 = page cache + slab objects
                f.write('3\n')
        except Exception as e:
            print(f"Failed to drop caches: {e}")

    def __clear_runtime_data(self):
        if os.path.exists(self._cfg.runtime_temp_dir):
            shutil.rmtree(self._cfg.runtime_temp_dir, ignore_errors=True)
        
        os.makedirs(self._cfg.runtime_temp_dir, exist_ok=True)

    def __str__(self):
            return f"Engine with mapping {self._cfg.mapping_policy} and DVFS policy {self._cfg.dvfs_policy}"
        
    def __repr__(self):
            return self.__str__()