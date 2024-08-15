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

import threading
from timeit import default_timer as timer

lock = threading.Lock()

class Engine:
    def __init__(self, experiment_name, mapping_policy = MappingPolicy(), scheduler = Scheduler(), dvfs_policy = DVFSPolicy()):
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
        self.__benchmark_manager = BenchManager()
        self.__migration_policy = MigrationPolicy()
            

    def __start(self):
        self.running = True
        self.startime = timer()

    def __launchApp(self, app, core):
        self.PIDs[app] = -1
        # Build the full application execution command from the corresponding script
        start = timer()
        self.__benchmark_manager.runApplicationOnCore(app, core)
        end = timer()
        core = self.mapping[app]
        #TODO: since this is now a dictionary, the writing access should be thread safe
        # keeping the lock until properly evaluated
        with lock:
            self.mapping[app] = -1
            self.__active_threads.remove(app)
        print("[Core " + str(core) +"]: " + app + " finished execution!" )
        self.reporter.logEvent("[Core " + str(core) +"]: " + app + " finished execution!" )
        print("[Core " + str(core) +"]: " + app + "'s execution time = " + str(round(end - start,2)) + "s" )
        self.reporter.logEvent("[Core " + str(core) +"]: " + app + "'s execution time = " + str(round(end - start,2)) + "s" )
        self.reporter.logExecutionTime(app, core, end - start)
        
    # Create a thread for each application in the mapping 
    def __makeThreads(self):
        for app, core in self.mapping.items():
            self.__threads[app] = threading.Thread(target=self.__launchApp, args=(app, core))
            print("Thread for " + app + " created!")
            self.reporter.logEvent("Thread for " + app + " created!")
    
    def getProcessID(self, app):
        PID = getPIDOfApp(app)
        # writing to the dictionary should be thread safe, no need for lock here
        self.PIDs[app] = PID
        print("[" + str(round(self.getElapsedTime(), 2)) + "s]: PID of " + app + " is " + str(PID))
        self.reporter.logEvent("[" + str(round(self.getElapsedTime(), 2)) + "s]: PID of " + app + " is " + str(PID))
    
    def getElapsedTime(self):
        return timer() - self.startime
    
    def __startThread(self,  app):
        self.__threads[app].start()
        #TODO: not safe-thread, need a lock here as well?
        self.__waiting_threads.remove(app)
        self.__active_threads.append(app)
        print("[" + str(round(self.getElapsedTime(), 2)) + "s]: Thread for " + app + " started!")
        self.reporter.logEvent("[" + str(round(self.getElapsedTime(), 2)) + "s]: Thread for " + app + " started!")

    def executeWorkload(self, applications):
        # First set a schedule for the applications
        self.__scheduler.createSchedule(applications)
        self.__waiting_threads = list(applications)
        # Execute the mapping policy 
        self.mapping = self.__mapping_policy.executeMapping(applications)
        self.reporter.logEvent("Mapping: " + str(self.mapping))
        print("Mapping: " + str(self.mapping))
        mapped_cores = list(self.mapping.values())
        # Start the monitoring thread
        if(enable_monitoring):
            self.__monitor = Monitor(sampling_rate, events_to_track, mapped_cores)
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
                print("[" + str(round(self.getElapsedTime(), 2)) + "s]: Experiment Finished!")
                self.reporter.logEvent("[" + str(round(self.getElapsedTime(), 2)) + "s]: Experiment Finished!")
                print("Total execution time of experiment = ", str(round(self.endtime - self.startime, 2)) + "s")
                self.reporter.logEvent("Total execution time of experiment = " + str(round(self.endtime - self.startime, 2)) + "s")
                # Stop the monitoring thread
                if(enable_monitoring):
                    self.__monitor.stop()
                # Clear the caches after the experiment is done
                self.__clearCaches()
                self.postprocess_results()
                break
            else:
                # Print the monitored metrics every 10 epochs
                if self.__epochs % 10 == 0:
                    # monitor print
                    print("Monitored Metrics:")
                    for core in mapped_cores:
                        metrics = [f"{event} = {self.__monitor.getMetricAtCore(core, event)}" for event in events_to_track]
                        print(f"[{str(round(self.getElapsedTime(), 2))}s] Core {core}: {' | '.join(metrics)}")
                        self.reporter.logPeriodicCounters(f"[{str(round(self.getElapsedTime(), 2))}s] Core {core}: {' | '.join(metrics)}")
                    print("--------------------")
                
                # Apply migration policy every 25 epochs
                if self.__epochs % 25 == 0:
                    new_mapping = self.__migration_policy.getShuffledMapping(self.mapping)
                    self.PIDs = self.__migration_policy.executeMigration(self.mapping, new_mapping, self.PIDs)
                    self.mapping = new_mapping
                    print("[" + str(round(current_time, 2)) + "s]: Mapping changed to " + str(self.mapping))
                    self.reporter.logEvent("[" + str(round(current_time, 2)) + "s]: Mapping changed to " + str(self.mapping))

                # Print the current mapping every 50 epochs
                if self.__epochs % 50 == 0:
                    print("[" + str(round(current_time, 2)) + "s]: Current map")
                    map = ""
                    for app, core in self.mapping.items():
                        if app in self.__active_threads:
                            map += app + ", C" + str(core) + ", PID "  + str(self.PIDs[app]) + "  | "
                    print(map)
                    print("--------------------")
                # any other periodic action here
           
            # Increment the epoch counter and sleep for the action interval
            self.__epochs += 1
            time.sleep(action_interval)
    
    # Post-process the results of the experiment, which cannot be done during the experiment
    def postprocess_results(self):
        post_processor = PostProcessor(self.reporter.workdir)
        total_energy = post_processor.compute_total_energy()
        energy_efficiency = post_processor.compute_energy_efficiency()
        self.reporter.logEvent(f"Total Energy Consumption (Package): {total_energy['total_energy_pkg']} Joules")
        self.reporter.logEvent(f"Total Energy Consumption (Cores): {total_energy['total_energy_cores']} Joules")
        self.reporter.logEvent(f"Total Energy Consumption (PSYS): {total_energy['total_energy_psys']} Joules")
        self.reporter.logEvent(f"Energy Efficiency: {energy_efficiency} Instructions per Joule")


    def __clearCaches(self):
        runProc("sudo sync")
        runProc("sudo echo 3 > /proc/sys/vm/drop_caches")

    def __str__(self):
            return f"Engine with mapping {self.__mapping_policy} and DVFS policy {self.__dvfs_policy}"
        
    def __repr__(self):
            return self.__str__()