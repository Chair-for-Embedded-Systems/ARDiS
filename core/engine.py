from benchmarks.bench_manager import *
from config import *
from core.procworker import *
from core.mapping import *
from core.monitor import *
from core.postprocessor import *
from core.reporter import *
from core.dvfs import *
from core.scheduler import *
from core.migration import *
from core.monitoringmode import *
import re
import threading
from timeit import default_timer as timer

lock = threading.Lock()

class Engine:
    def __init__(self, experiment_name, mapping_policy = MappingPolicy(), scheduler = Scheduler(), dvfs_policy = DVFSPolicy(), migration_policy = None, monitoring_mode = MonitoringMode.PERIODIC_ON_CORE, results_folder = RESULTS_FOLDER):
        self.running = False
        self.startime = 0
        self.endtime = 0
        self.__epochs = 0
        self.mapping = {}
        self.__threads = {}
        self.__active_threads = []
        self.__waiting_threads = []
        self.PIDs = {}  
        self.__mapping_policy = mapping_policy
        self.__scheduler = scheduler 
        self.__monitor = None
        self.__dvfs_policy = dvfs_policy
        self.reporter = Reporter(experiment_name, results_folder)
        self.__migration_policy = migration_policy
        self.__total_instructions = None
        self.__monitoring_mode = monitoring_mode
        self.__one_shot_file = os.path.join(ROOTPATH, "one_shot.out")
        self.__benchmark_manager = BenchManager()
            

    def __start(self):
        self.running = True
        self.startime = timer()

    def __launchApp(self, app, core):
        self.PIDs[app] = -1
        # Build the full application execution command from the corresponding script
        start = timer()
        
        self.__benchmark_manager.runApplicationOnCore(app, None if self.__mapping_policy is None else core)
        end = timer()
        # keeping the lock until properly evaluated
        with lock:
            core = self.mapping[app]
            self.mapping.pop(app)
            self.PIDs.pop(app)
            if self.__monitoring_mode != MonitoringMode.OFF:
                self.__monitor.updateTrackedMapping(self.mapping)
            if self.__monitoring_mode == MonitoringMode.PERIODIC_ON_PID:
                self.__monitor.updateTrackedPIDs(list(self.PIDs.values()))
            self.__active_threads.remove(app)
        if config.DEBUG:
            print("[Core " + str(core) +"]: " + app + " finished execution!" )
        self.reporter.logEvent("[Core " + str(core) +"]: " + app + " finished execution!" )
        
        if config.DEBUG:
            print("[Core " + str(core) +"]: " + app + "'s execution time = " + str(round(end - start,2)) + "s" )
        self.reporter.logEvent("[Core " + str(core) +"]: " + app + "'s execution time = " + str(round(end - start,2)) + "s" )
        self.reporter.logExecutionTime(app, core, end - start)
        
    # Create a thread for each application in the mapping 
    def __makeThreads(self):
        tmp_mapping = self.mapping.copy()
        for app, core in tmp_mapping.items():
            self.__threads[app] = threading.Thread(target=self.__launchApp, args=(app, core))
            if config.DEBUG:
                print("Thread for " + app + " created!")
                self.reporter.logEvent("Thread for " + app + " created!")
    
    def getProcessID(self, app):
        PID = getPIDOfApp(app)
        # writing to the dictionary should be thread safe, no need for lock here
        self.PIDs[app] = PID
    
        if config.DEBUG:
            print("[" + str(round(self.getElapsedTime(), 2)) + "s]: PID of " + app + " is " + str(PID))
            self.reporter.logEvent("[" + str(round(self.getElapsedTime(), 2)) + "s]: PID of " + app + " is " + str(PID))
    
    def getElapsedTime(self):
        return timer() - self.startime
    
    def __startThread(self,  app):
        print("Starting thread for ", app)
        self.__threads[app].start()
        with lock:
            self.__waiting_threads.remove(app)
            self.__active_threads.append(app)    
        if config.DEBUG:
            print("[" + str(round(self.getElapsedTime(), 2)) + "s]: Thread for " + app + " started!")
            self.reporter.logEvent("[" + str(round(self.getElapsedTime(), 2)) + "s]: Thread for " + app + " started!")

    def executeWorkload(self, applications):
        # First set a schedule for the applications
        self.__total_instructions = {app: 0 for app in applications}
        self.__scheduler.createSchedule(applications)
        self.__waiting_threads = list(applications)
        # Execute the mapping policy 
        if self.__mapping_policy is not None:
            self.mapping = self.__mapping_policy.executeMapping(applications)
        else:
            self.mapping = {app: -1 for app in applications}
            self.PIDs = {app: -1 for app in applications}

        if config.DEBUG:
            self.reporter.logEvent("Mapping: " + str(self.mapping))
            print("Mapping: " + str(self.mapping))
            
        # Create the threads each application.
        self.__makeThreads()
        # then start the workload execution
        self.__start()
        # Start the monitoring thread
        if self.__monitoring_mode != MonitoringMode.OFF:
            self.__monitor = Monitor(pids=[], tracked_mapping = self.mapping, monitoring_mode=self.__monitoring_mode, reporter=self.reporter, engine_start_time=self.startime, core_frequencies=self.__dvfs_policy.getCoreFrequencies())
            self.__monitor.start()
        while self.running:
            current_time = self.getElapsedTime()
            # Check if the application is scheduled to start and if the thread is not already running
            tmp_mapping = self.mapping.copy()
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
                if config.DEBUG:
                    print("[" + str(round(self.getElapsedTime(), 2)) + "s]: Experiment Finished!")
                    print("Total execution time of experiment = ", str(round(self.endtime - self.startime, 2)) + "s")
                self.reporter.logEvent("[" + str(round(self.getElapsedTime(), 2)) + "s]: Experiment Finished!")
                self.reporter.logEvent("Total execution time of experiment = " + str(round(self.endtime - self.startime, 2)) + "s")
                # Stop the monitoring thread
                if self.__monitoring_mode != MonitoringMode.OFF:
                    self.__monitor.stop()
                    
                    # Fetch the energy, time, and instructions from the one_shot.out file
                    energy, time_elapsed, executed_instructions = self.fetch_perf_data(self.__one_shot_file)
                    self.reporter.logEvent("Total instructions executed = " + str(executed_instructions))
                    self.reporter.logEvent("Total energy consumed (perf)= " + str(energy) + " Joules")
                    self.reporter.logEvent("Total time elapsed (perf)= " + str(time_elapsed) + " seconds")
                # Clear the caches after the experiment is done
                self.__clearCaches()
                break
            else:
                # Apply migration policy every X epochs
                if self.__epochs > 0 and  self.__epochs % 20 == 0:
                    #print("[" + str(round(current_time, 2)) + "s]: Checking Migrations")
                    if self.__migration_policy is not None:
                        #print("######### TRIGGERRING MIGRATION and DVFS #########")
                        #print("Current Mapping: ", self.mapping)
                        # setting the p cores to a random frequency from 1800 to 3200 with steps of 200MHz
                        with lock:
                            for app in self.mapping:
                                self.PIDs[app] = getPIDOfApp(app)

                        if self.__monitoring_mode == MonitoringMode.PERIODIC_ON_PID:
                            self.__monitor.updateTrackedPIDs(list(self.PIDs.values()))
                            
                        new_mapping, app_to_migrate, current_core, new_core = self.__migration_policy.getNewMapping(self.__total_instructions, self.mapping)
                        
                        
                        is_p_core = new_core in intel_p_core_ids
                        new_current_frequencies = self.__dvfs_policy.getCoreFrequencies()
                        if is_p_core:
                            new_current_frequencies[new_core] = random.choice(range(1800, 3201, 200))
                        else:
                            new_common_e_core_frequency = random.choice(range(1800, 3201, 200))
                            for core in new_current_frequencies.keys():
                                if core in intel_e_core_ids:
                                    new_current_frequencies[core] = new_common_e_core_frequency

                        with lock:
                            # Executing the migration
                            self.__migration_policy.executeMigration(self.mapping, new_mapping, self.PIDs)
                            self.mapping = new_mapping
                            # Executing the DVFS policy
                            if self.__dvfs_policy is not None:
                                self.__dvfs_policy.executeDVFSPolicy(new_current_frequencies)
                                self.__monitor.updateCoreFrequencies(new_current_frequencies)

                            if self.__monitoring_mode != MonitoringMode.OFF:
                                self.__monitor.updateTrackedMapping(self.mapping)
                                
                        if config.DEBUG:
                            #self.reporter.logPeriodicCounters(f"[{str(round(self.getElapsedTime(), 2))}s] Migrated {app_to_migrate} from core {current_core} to core {new_core}")
                            print(f"[{str(round(self.getElapsedTime(), 2))}s] Migrated {app_to_migrate} from core {current_core} to core {new_core}")

                        if self.__monitoring_mode == MonitoringMode.PERIODIC_ON_PID:
                            self.__monitor.updateTrackedPIDs(list(self.PIDs.values()))

                # any other periodic action here
           
            # Increment the epoch counter and sleep for the action interval
            #print("Epoch: ", self.__epochs)
            self.__epochs += 1
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