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
    def __init__(self, experiment_name, mapping_policy = MappingPolicy(), scheduler = Scheduler(), dvfs_policy = DVFSPolicy(), migration_policy = None, monitoring_mode = MonitoringMode.PERIODIC_ON_CORE):
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
        self.reporter = Reporter(experiment_name, RESULTS_FOLDER)
        self.__migration_policy = migration_policy
        self.__total_instructions = 0
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
        core = self.mapping[app]
        #TODO: since this is now a dictionary, the writing access should be thread safe
        # keeping the lock until properly evaluated
        with lock:
            self.mapping[app] = -1
            self.PIDs[app] = -1
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
        for app, core in self.mapping.items():
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
        self.__threads[app].start()
        #TODO: not safe-thread, need a lock here as well?
        self.__waiting_threads.remove(app)
        self.__active_threads.append(app)    
        if config.DEBUG:
            print("[" + str(round(self.getElapsedTime(), 2)) + "s]: Thread for " + app + " started!")
            self.reporter.logEvent("[" + str(round(self.getElapsedTime(), 2)) + "s]: Thread for " + app + " started!")

    def executeWorkload(self, applications):
        # First set a schedule for the applications
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
        #mapped_cores = list(self.mapping.values())
        mapped_cores = list(range(0, system_cores))
        # Start the monitoring thread
        if self.__monitoring_mode != MonitoringMode.OFF:
            self.__monitor = Monitor(tracked_cores=mapped_cores, pids=[], monitoring_mode=self.__monitoring_mode)
            self.__monitor.start()
        # Create the threads each application.
        self.__makeThreads()
        # then start the workload execution
        self.__start()
        while self.running:
            current_time = self.getElapsedTime()
            # Check if the application is scheduled to start and if the thread is not already running
            for app in self.mapping:
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
                self.postprocess_results()
                break
            else:
                for app in self.mapping:
                    self.PIDs[app] = getPIDOfApp(app)
                if self.__monitoring_mode != MonitoringMode.OFF:
                    self.__monitor.updateTrackedPIDs(list(self.PIDs.values()))
                # Print the monitored metrics every 10 epochs
                if self.__epochs % 10 == 0:
                    # monitor print
                    if config.DEBUG:
                        print("Monitored Metrics:")
                    if self.__monitoring_mode == MonitoringMode.PERIODIC_ON_CORE:
                        for core in list(self.mapping.values()):
                            app_metrics = [f"{event} = {self.__monitor.getMetricAtCore(core, event)}" for event in periodic_app_level_events]
                            if config.DEBUG:
                                print(f"[{str(round(self.getElapsedTime(), 2))}s] Core {core}: {' | '.join(app_metrics)}")
                            self.reporter.logPeriodicCounters(f"[{str(round(self.getElapsedTime(), 2))}s] Core {core}: {' | '.join(app_metrics)}")
                            self.__total_instructions += self.__monitor.getMetricAtCore(core, "instructions")
                            if config.DEBUG:
                                self.reporter.logEvent(f"[{str(round(self.getElapsedTime(), 2))}s] Core {core}: Cumulative Instructions = {self.__total_instructions}")
                    elif self.__monitoring_mode == MonitoringMode.PERIODIC_ON_PID:
                        for app in self.mapping:
                            app_metrics = [f"{event} = {self.__monitor.getMetricForPID(self.PIDs[app], event)}" for event in periodic_app_level_events]
                            if config.DEBUG:
                                print(f"[{str(round(self.getElapsedTime(), 2))}s] PID {self.PIDs[app]}: {' | '.join(app_metrics)}")
                            self.reporter.logPeriodicCounters(f"[{str(round(self.getElapsedTime(), 2))}s] PID {self.PIDs[app]}: {' | '.join(app_metrics)}")
                            self.__total_instructions += self.__monitor.getMetricForPID(self.PIDs[app], "instructions")
                            if config.DEBUG:
                                self.reporter.logEvent(f"[{str(round(self.getElapsedTime(), 2))}s] PID {self.PIDs[app]}: Cumulative Instructions = {self.__total_instructions}")
                    
                    system_metrics = [f"{event} = {self.__monitor.getSystemWideMetric(event)}" for event in periodic_system_wide_events]
                    if config.DEBUG:
                        print(f"[{str(round(self.getElapsedTime(), 2))}s] SYSTEM: {' | '.join(system_metrics)}")
                    self.reporter.logPeriodicCounters(f"[{str(round(self.getElapsedTime(), 2))}s] SYSTEM: {' | '.join(system_metrics)}")

                    if config.DEBUG:
                        print("--------------------")
                
                # Apply migration policy every 50 epochs
                if self.__epochs > 0 and  self.__epochs % 10 == 0:
                    if self.__migration_policy is not None:
                        # update PIDs before calling the migration procedure
                        if config.DEBUG:
                            print("##################### Migrating applications #####################")
                            print("########## Before PID update:", self.PIDs)
                        if config.DEBUG:
                            print("########## After PID update:", self.PIDs)
                        
                        new_mapping = self.__migration_policy.getStaticScheduleMapping(self.__total_instructions, self.mapping)
                        # Executing the migration policy
                        #print("New Mapping: ", new_mapping)
                        #print("[" + str(round(self.getElapsedTime(), 2)) + "s]: Checking Migrations")
                        self.__migration_policy.executeMigration(self.mapping, new_mapping, self.PIDs)
                        self.mapping = new_mapping
                        
                        if self.__monitoring_mode == MonitoringMode.PERIODIC_ON_CORE:
                            self.__monitor.updateTrackedCores(list(self.mapping.values()))
                        elif self.__monitoring_mode == MonitoringMode.PERIODIC_ON_PID:
                            self.__monitor.updateTrackedPIDs(list(self.PIDs.values()))
                        #print("[" + str(round(current_time, 2)) + "s]: Mapping changed to " + str(self.mapping))                    
                        if config.DEBUG:
                            self.reporter.logEvent("[" + str(round(current_time, 2)) + "s]: Mapping changed to " + str(self.mapping))
                        # Executing the DVFS policy
                        self.__dvfs_policy.executeDVFSPolicy(self.__total_instructions, self.mapping)

                # Print the current mapping every 50 epochs
                if self.__epochs % 50 == 0:
                    
                    if config.DEBUG:
                        print("[" + str(round(current_time, 2)) + "s]: Current map")
                    map = ""
                    for app, core in self.mapping.items():
                        if app in self.__active_threads:
                            map += app + ", C" + str(core) + ", PID "  + str(self.PIDs[app]) + "  | "
                            
                    if config.DEBUG:
                        print(map)
                        print("--------------------")
                # any other periodic action here
           
            # Increment the epoch counter and sleep for the action interval
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

    # Post-process the results of the experiment, which cannot be done during the experiment
    def postprocess_results(self):
        pass


    def __clearCaches(self):
        runProc("sudo sync")
        runProc("sudo echo 3 > /proc/sys/vm/drop_caches")

    def __str__(self):
            return f"Engine with mapping {self.__mapping_policy} and DVFS policy {self.__dvfs_policy}"
        
    def __repr__(self):
            return self.__str__()