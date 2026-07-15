import shutil
import threading
import time
from timeit import default_timer as timer

from ardis.core.procworker import *
from ardis.core.mapping import MappingPolicy
from ardis.core.monitoring.monitor import Monitor, TrackingConfig
from ardis.core.reporter import Reporter
from ardis.core.dvfs import DVFSPolicy
from ardis.core.scheduler import Scheduler
from ardis.core.migration import MigrationPolicy
from ardis.core.monitoringmode import MonitoringMode
from ardis.core.buffering.deque_based_event_buffer import DequeBasedEventBuffer, EventBuffer
from ardis.core.buffering.action_buffer import ActionBuffer
from ardis.core.system_state import SystemState
from ardis.benchmarks.application import Application
import ardis.config as config

thread_queue_lock = threading.Lock()
system_state_lock = threading.Lock()

class Engine:
    def __init__(self, 
                experiment_name: str,
                mapping_policy: MappingPolicy,
                scheduler: Scheduler,
                dvfs_policy: DVFSPolicy | None = None,
                migration_policy: MigrationPolicy | None = None,
                monitoring_mode: MonitoringMode = MonitoringMode.PERIODIC_ON_CORE,
                results_folder: str = config.RESULTS_FOLDER
    ) -> None:
        self.running: bool = False

        self.__threads: dict[Application, threading.Thread] = {}
        self.__active_threads: list[Application] = []
        self.__waiting_threads: list[Application] = []

        self.__mapping_policy = mapping_policy
        self.__scheduler = scheduler 
        self.__dvfs_policy = dvfs_policy
        self.__migration_policy = migration_policy
    
        self.__monitor: Monitor | None = None
        self.__monitoring_mode: MonitoringMode = monitoring_mode
        
        self.reporter: Reporter = Reporter(experiment_name, results_folder)
        self.event_buffer: EventBuffer = DequeBasedEventBuffer(capacity=10, collect_total_metrics=True)
        self.action_buffer: ActionBuffer = ActionBuffer(capacity=10)
        
        self.__start_time: float = 0.0
        self.__app_to_pid: dict[Application, int] = {}
        self.__app_to_cores: dict[Application, set[int]] = {}
        self.__epoch: int = 0

        self.__clear_runtime_data()

    def __start_engine(self) -> None:
        self.running = True
        self.__start_time = timer()
        
        # Start the monitoring thread if monitoring is enabled
        if self.__monitoring_mode != MonitoringMode.OFF and self.__monitor:
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

            if self.__monitoring_mode != MonitoringMode.OFF and self.__monitor:
                self.__monitor.update_tracking_config(
                    TrackingConfig(
                        monitor_mode=self.__monitoring_mode,
                        app_to_cores=self.__app_to_cores.copy(),
                        app_to_pid=self.__app_to_pid.copy()
                    )
                )
        
        with thread_queue_lock:
            self.__active_threads.remove(app)
        
        core_str = ','.join([str(c) for c in cores])

        self.reporter.logEvent(event=f"[Core(s) {core_str}]: {app} finished execution!", echo=config.DEBUG)
        self.reporter.logEvent(event=f"[Core(s) {core_str}]: {app}'s execution time = {end - start:.2f} s", echo=config.DEBUG)
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
                if config.DEBUG:
                    msg_pid_of_app = f"[{self.getElapsedTime():.2f}s]: PID of {app} is {pid}"
                    self.reporter.logEvent(msg_pid_of_app, echo=True)
                return
            
            # Wait for the specified delay before checking again
            time.sleep(delay)
        
    def getElapsedTime(self) -> float:
        """Returns the elapsed time in seconds since the workload was started."""
        return timer() - self.__start_time
    
    def __startThread(self, app: Application) -> None:
        print(f"Starting thread for {app.get_display_name()}")
        self.__threads[app].start()
        
        with thread_queue_lock:
            self.__waiting_threads.remove(app) # remove is not atomic
            self.__active_threads.append(app)

        if config.DEBUG:
            msg_thread_started = f"[{self.getElapsedTime():.2f}s]: Thread for {app} started!"
            self.reporter.logEvent(msg_thread_started, echo=True)

    def executeWorkload(self, applications: list[Application]) -> None:
        
        self.__waiting_threads = list(applications)
        
        self.__scheduler.register_workload(applications)
        self.__mapping_policy.register_workload(applications)

        # Execute initial DVFS policy (if present)
        if self.__dvfs_policy is not None:
            self.__dvfs_policy.apply_initial_state()
        
        # Prepare the monitor if monitoring is enabled
        self.__inititalize_monitor()

        # Then start the workload execution
        self.__start_engine()

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
                if self.__monitoring_mode != MonitoringMode.OFF and self.__monitor:
                    self.__monitor.update_tracking_config(
                        TrackingConfig(self.__monitoring_mode, self.__app_to_cores.copy(), self.__app_to_pid.copy())
                    )

                # any other periodic action here
           
            # Increment the epoch counter and sleep for the action interval
            self.__epoch += 1
            time.sleep(config.action_interval_sec)
    
    def __inititalize_monitor(self):
        
        if self.__monitoring_mode == MonitoringMode.OFF:
            self.__monitor = None
            return
        
        self.__monitor = Monitor(
            sampling_rate_sec=config.sampling_rate_ms/1000,
            periodic_app_level_events=config.periodic_app_level_events,
            periodic_system_level_events=config.periodic_system_wide_events,
            one_shot_system_level_events=config.one_shot_system_wide_events,
            reporter=self.reporter,
            event_buffer=self.event_buffer,
            inital_tracking_config=TrackingConfig(
                monitor_mode=self.__monitoring_mode,
                app_to_cores=self.__app_to_cores,
            )
        )

    def __launch_waiting_threads(self, system_state: SystemState) -> None:
        # Requires SystemState lock to be held by the caller
        
        # Check if the application is scheduled to start and if the thread is not already running
        for app in list(self.__waiting_threads):
            
            if not self.__scheduler.is_time_to_launch(app, system_state):
                continue
                
            # Get the cores assigned to the application
            cores = self.__mapping_policy.get_mapping(app, system_state)
            self.__app_to_cores[app] = cores
            self.__app_to_pid[app] = -1  
                
            # Start the application thread
            self.__threads[app] = threading.Thread(target=self.__launchApp, args=(app, cores))
            self.__startThread(app)

            # Start a thread to fast discover the PID
            pid_thread = threading.Thread(target=self.getProcessID, args=(app,))
            pid_thread.start()


    def __execute_migration_policy(self, system_state: SystemState) -> None:

        if self.__migration_policy is None:
            return
        
        mig_actions = self.__migration_policy.get_migration_actions(system_state)
        self.__migration_policy.apply_migration_actions(mig_actions, self.__app_to_pid, self.__app_to_cores)
                    
        # Log migration actions if desired
        if config.DEBUG:
            for action in mig_actions:
                msg_app_migrated = f"[{self.getElapsedTime():.2f}s] Migrated {action.app} from core {action.source} to core {action.destination}"
                self.reporter.logEvent(msg_app_migrated, echo=True)
                        
        # Writes the migration action to the action buffer. 
        # Since this is done here, the dvfs poilcy will have access to this information.
        if mig_actions:
            self.action_buffer.push_migration_actions(self.__epoch, mig_actions)

    def __execute_dvfs_policy(self, system_state: SystemState) -> None:
        
        if self.__dvfs_policy is None:
            return
        
        dvfs_actions = self.__dvfs_policy.get_dvfs_actions(system_state)
        self.__dvfs_policy.apply_dvfs_actions(dvfs_actions)
                        
        # Log dvfs actions if desired
        if config.DEBUG:
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
        if self.__dvfs_policy:
            self.__dvfs_policy.cpu_freq_manager.restore_initial_state() 

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
        if os.path.exists(config.RUNTIME_TEMP_DIR):
            shutil.rmtree(config.RUNTIME_TEMP_DIR, ignore_errors=True)
        
        os.makedirs(config.RUNTIME_TEMP_DIR, exist_ok=True)

    def __str__(self):
            return f"Engine with mapping {self.__mapping_policy} and DVFS policy {self.__dvfs_policy}"
        
    def __repr__(self):
            return self.__str__()