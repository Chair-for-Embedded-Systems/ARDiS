from benchmarks.bench_manager import *
from config import *
from core.procworker import *
from core.mapping import *
from core.monitoring.monitor import Monitor, TrackingConfig
from core.postprocessor import *
from core.reporter import *
from core.dvfs import *
from core.scheduler import *
from core.migration import *
from core.monitoringmode import *
from core.buffering.deque_based_event_buffer import DequeBasedEventBuffer, EventBuffer
from core.system_state import SystemState
import re
import threading
from timeit import default_timer as timer

engine_lock = threading.Lock()
system_state_lock = threading.Lock()

class Engine:
    def __init__(self, experiment_name, mapping_policy = MappingPolicy(), scheduler = Scheduler(), dvfs_policy = DVFSPolicy(), migration_policy = None, monitoring_mode = MonitoringMode.PERIODIC_ON_CORE, results_folder = RESULTS_FOLDER):
        self.running: bool = False

        self.__threads: dict[str, threading.Thread] = {}
        self.__active_threads: list[str] = []
        self.__waiting_threads: list[str] = []
    
        self.__mapping_policy: MappingPolicy = mapping_policy
        self.__scheduler: Scheduler = scheduler 
        self.__dvfs_policy: DVFSPolicy = dvfs_policy
        self.__migration_policy: MigrationPolicy | None = migration_policy
    
        self.__monitor: Monitor | None = None
        self.__monitoring_mode: MonitoringMode = monitoring_mode
        
        self.__total_instructions: dict[str, int] = {}
    
        self.__benchmark_manager = BenchManager()
        
        self.reporter: Reporter = Reporter(experiment_name, results_folder)
        self.event_buffer: EventBuffer = DequeBasedEventBuffer(capacity=10)
        self.system_state: SystemState = SystemState()

    def __start(self) -> None:
        self.running = True
        self.system_state.start_time = timer()

    def __launchApp(self, app: str, cores: set[int]) -> None:
        
        self.system_state.app_to_pid[app] = -1
        # Build the full application execution command from the corresponding script
        
        start = timer()
        self.__benchmark_manager.runApplicationOnCore(app, None if self.__mapping_policy is None else cores)
        end = timer()
        
        # keeping the lock until properly evaluated
        with system_state_lock:
            cores = self.system_state.app_to_cores.pop(app)
            self.system_state.app_to_pid.pop(app)

            if self.__monitoring_mode != MonitoringMode.OFF and self.__monitor:
                self.__monitor.update_tracking_config(
                    TrackingConfig(
                        monitor_mode=self.__monitoring_mode,
                        app_to_cores=self.system_state.app_to_cores,
                        app_to_pid=self.system_state.app_to_pid
                    )
                )
            self.__active_threads.remove(app)
        
        core_str = ','.join([str(c) for c in cores])

        self.reporter.logEvent(event=f"[Core(s) {core_str}]: {app} finished execution!", echo=config.DEBUG)
        self.reporter.logEvent(event=f"[Core(s) {core_str}]: {app}'s execution time = {end - start:.2f} s", echo=config.DEBUG)
        self.reporter.logExecutionTime(app, core_str, end - start)
        
    # Create a thread for each application in the mapping 
    def __makeThreads(self) -> None:
        # Threads are created before the control loop which modifies the system state.
        # Therefore we dont need locking or dict copying here
        for app, cores in self.system_state.app_to_cores.items():
            self.__threads[app] = threading.Thread(target=self.__launchApp, args=(app, cores))
            if config.DEBUG:
                self.reporter.logEvent(f"Thread for {app} created!", echo=True)
    
    def getProcessID(self, app: str) -> None:
        PID = getPIDOfApp(app)
        self.system_state.app_to_pid[app] = PID
    
        if config.DEBUG:
            msg_pid_of_app = f"[{self.getElapsedTime():.2f}s]: PID of {app} is {PID}"
            self.reporter.logEvent(msg_pid_of_app, echo=True)
    
    def getElapsedTime(self) -> float:
        """Returns the elapsed time in seconds since the workload was started."""
        return timer() - self.system_state.start_time
    
    def __startThread(self, app: str) -> None:
        print(f"Starting thread for {app}")
        self.__threads[app].start()
        
        with engine_lock:
            self.__waiting_threads.remove(app)
            self.__active_threads.append(app)

        if config.DEBUG:
            msg_thread_started = f"[{self.getElapsedTime():.2f}s]: Thread for {app} started!"
            self.reporter.logEvent(msg_thread_started, echo=True)

    def executeWorkload(self, applications: list[str]) -> None:
        # First set a schedule for the applications
        self.__total_instructions = {app: 0 for app in applications}
        self.__scheduler.createSchedule(applications)
        self.__waiting_threads = list(applications)
        
        # Execute the mapping policy 
        if self.__mapping_policy is not None:
            self.system_state.app_to_cores = self.__mapping_policy.executeMapping(applications)
        else:
            self.system_state.app_to_cores = {app: {-1} for app in applications}
            self.system_state.app_to_pid = {app: -1 for app in applications}

        if config.DEBUG:
            self.reporter.logEvent(f"Mapping: {self.system_state.app_to_cores}", echo=True)
            
        # Create the threads each application.
        self.__makeThreads()
        # then start the workload execution
        self.__start()
        
        # Start the monitoring thread
        if self.__monitoring_mode != MonitoringMode.OFF:
            self.__monitor = Monitor(
                sampling_rate_sec=config.sampling_rate/1000,
                periodic_app_level_events=config.periodic_app_level_events,
                periodic_system_level_events=config.periodic_system_wide_events,
                one_shot_system_level_events=config.one_shot_system_wide_events,
                reporter=self.reporter,
                event_buffer=self.event_buffer,
                inital_tracking_config=TrackingConfig(
                    monitor_mode=self.__monitoring_mode,
                    app_to_cores=self.system_state.app_to_cores,
                )
            )
            self.__monitor.start()

        # Control loop
        while self.running:
            current_time = self.getElapsedTime()
            
            # Check if the application is scheduled to start and if the thread is not already running
            tmp_mapping = self.system_state.app_to_cores.copy()
            for app in tmp_mapping:
                if self.__scheduler.isTimeToLaunch(app, current_time) and app in self.__waiting_threads:
                    # Start the thread
                    self.__startThread(app)
                    #TODO while very unlikely, we might have a race condition here 
                    Thread(target=self.getProcessID, args=(app,)).start()
                    # using the pool executor should avoid race conditions but the performance is a bit worse
                    # self.__executor.submit(self.getProcessID, app)
                      
            # Check if all threads are done before finishing
            if not self.__active_threads and not self.__waiting_threads:
                self.running = False
                self.endtime = timer()
                elapsed_time_sec = self.endtime - self.system_state.start_time
            
                msg_exp_finished = f"[{self.getElapsedTime():.2f}s]: Experiment Finished!"
                msg_total_time = f"Total execution time of experiment = {elapsed_time_sec:.2f}s"
            
                self.reporter.logEvent(msg_exp_finished, echo=True)
                self.reporter.logEvent(msg_total_time, echo=True)
                
                # Stop the monitoring thread
                if self.__monitor:
                    self.__monitor.stop()
                
                # Clear the caches after the experiment is done
                self.__clearCaches()
                break
            else:  
                with system_state_lock:
                
                    # Update pid of apps
                    for app in self.system_state.app_to_pid:
                        self.system_state.app_to_pid[app] = getPIDOfApp(app)
                            
                    # Migration policy (if present)
                    if mig_policy := self.__migration_policy:
                        mig_actions = mig_policy.get_migration_actions(self.system_state)
                        mig_policy.apply_migration_actions(mig_actions)
                        
                        # Update system state
                        for action in mig_actions:
                            self.system_state.app_to_cores[action.app] = action.destination
                            if config.DEBUG:
                                msg_app_migrated = f"[{self.getElapsedTime():.2f}s] Migrated {action.app} from core {action.source} to core {action.destination}"
                                self.reporter.logEvent(msg_app_migrated, echo=True)

                    # DVFS policy (if present)
                    if dvfs_policy := self.__dvfs_policy:
                        dvfs_actions = dvfs_policy.get_dvfs_actions(self.system_state)
                        dvfs_policy.apply_dvfs_actions(dvfs_actions)
                    
                    # Update tracking config
                    if self.__monitoring_mode != MonitoringMode.OFF and self.__monitor:
                        self.__monitor.update_tracking_config(
                            TrackingConfig(self.__monitoring_mode, self.system_state.app_to_cores, self.system_state.app_to_pid)
                        )

                # any other periodic action here
           
            # Increment the epoch counter and sleep for the action interval
            #print("Epoch: ", self.__epochs)
            self.system_state.epoch += 1
            time.sleep(action_interval)
    
    def fetch_perf_data(self, perf_file_path):
        # Initialize variables to store the energy, time, cpu_core, and cpu_atom instructions
        energy_psys = None
        time_elapsed = None
        cpu_core_instructions = 0  # Initialize to 0 for summing
        cpu_atom_instructions = 0  # Initialize to 0 for summing
        
        # Open and read the perf.out file
        with open(perf_file_path, 'r') as file:
            lines = file.readlines()
        
        # Iterate through the lines to find energy, time, cpu_core, and cpu_atom instructions
        for line in lines:
                      
            # Search for the energy-psys line using regex
            energy_psys_match = re.search(r'([\d,\.]+)\s+Joules\s+power/energy-psys/', line)
            if energy_psys_match:
                energy_psys = float(energy_psys_match.group(1).replace(',', ''))  # Remove commas and convert to float
            
            # Search for the time elapsed line using regex
            time_match = re.search(r'([\d,\.]+)\s+seconds time elapsed', line)
            if time_match:
                time_elapsed = float(time_match.group(1))  # Convert to float
            
            # Search for the cpu_core instructions using regex
            cpu_core_match = re.search(r'([\d,\.]+)\s+cpu_core/instructions/', line)
            if cpu_core_match:
                cpu_core_instructions += int(cpu_core_match.group(1).replace(',', ''))  # Remove commas and convert to int
            
            # Search for the cpu_atom instructions using regex
            cpu_atom_match = re.search(r'([\d,\.]+)\s+cpu_atom/instructions/', line)
            if cpu_atom_match:
                cpu_atom_instructions += int(cpu_atom_match.group(1).replace(',', ''))  # Remove commas and convert to int
        
        # Sum the energy components if available
        total_energy = energy_psys
        
        # Return total energy, time elapsed, and total instructions
        return total_energy, time_elapsed, cpu_core_instructions + cpu_atom_instructions

    def __clearCaches(self):
        runProc("sudo sync")
        runProc("sudo echo 3 > /proc/sys/vm/drop_caches")

    def __str__(self):
            return f"Engine with mapping {self.__mapping_policy} and DVFS policy {self.__dvfs_policy}"
        
    def __repr__(self):
            return self.__str__()