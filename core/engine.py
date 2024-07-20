from config import *
from scripts.run_spec import *
from scripts.run_parsec import *
from core.procworker import *
from core.mapping import *
from core.monitor import *
from core.reporter import *
from core.dvfs import *
import threading
import subprocess
from timeit import default_timer as timer

lock = threading.Lock()

class Engine:
    def __init__(self, experiment_name, mapping_policy = MappingPolicy()):
        self.running = False
        self.startime = 0
        self.endtime = 0
        self.__epochs = 0
        self.mapping = {}
        self.__threads = {}
        self.__active_threads = []
        self.PIDs = {}  
        self.__mapping_policy = mapping_policy
        self.__monitor = None
        #TODO: replace for argument
        self.__dvfs_policy = DVFSPolicy()
        #default frequency  = 2000 MHz
        self.__static_frequency  = 2000
        self.reporter = Reporter(experiment_name, RESULTS_FOLDER)
            

    def __start(self):
        self.running = True
        self.startime = timer()

    def __launchApp(self, app_name, core):
        # Build the full application execution command from the corresponding script
        start = timer()
        if "spec" in app_name:
            run_spec_app(app_name[5:], core) 
        elif "parsec" in app_name:
            run_parsec_app(app_name[7:], core)

        end = timer()
        core = self.mapping[app_name]
        #TODO: since this is now a dictionary, the writing access should be thread safe
        # keeping the lock until properly evaluated
        with lock:
            self.mapping[app_name] = -1
        print("[Core " + str(core) +"]: " + app_name + " finished execution!" )
        self.reporter.logEvent("[Core " + str(core) +"]: " + app_name + " finished execution!" )
        print("[Core " + str(core) +"]: " + app_name + "'s execution time = " + str(round(end - start,2)) + "s" )
        self.reporter.logEvent("[Core " + str(core) +"]: " + app_name + "'s execution time = " + str(round(end - start,2)) + "s" )
        self.reporter.logExecutionTime(app_name, core, end - start)
        
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
        self.__active_threads.append(app)
        print("[" + str(round(self.getElapsedTime(), 2)) + "s]: Thread for " + app + " started!")
        self.reporter.logEvent("[" + str(round(self.getElapsedTime(), 2)) + "s]: Thread for " + app + " started!")

    def setStaticFrequency(self, frequency):
        self.__static_frequency = frequency

    def executeWorkload(self, applications, schedule):
        # Execute the mapping policy 
        self.mapping = self.__mapping_policy.executeMapping(applications)
        self.reporter.logEvent("Mapping: " + str(self.mapping))
        print("Mapping: " + str(self.mapping))
        mapped_cores = list(self.mapping.values())
        # Start the monitoring thread
        if(enable_monitoring):
            self.__monitor = Monitor(sampling_rate, events_to_track, mapped_cores)
            self.__monitor.start()
        # Set the static frequency for all soon-to-be-used cores
        self.__dvfs_policy.setInitialFrequency(mapped_cores, self.__static_frequency)
        self.reporter.logEvent("Initial core frequency: " + str(self.__static_frequency))
        print("Initial core frequency: " + str(self.__static_frequency))
        # Create the threads each application.
        self.__makeThreads()	
        # then start the workload execution
        self.__start()
        while self.running:
            current_time = self.getElapsedTime()
            # Check if the application is scheduled to start and if the thread is not already running
            for app in self.mapping:
                #TODO: this probably should be done by the scheduler, but we don't have access to it from here yet
                if schedule[app] <= self.getElapsedTime() and app not in self.__active_threads:
                    # Start the thread
                    self.__startThread(app)
                    #TODO while very unlikely, we might have a race condition here 
                    Thread(target=self.getProcessID, args=(app,)).start()
                    # using the pool executor should avoid race conditions but the performance is a bit worse
                    # self.__executor.submit(self.getProcessID, app)

            # Check if all threads are done before finishing
            if not any([thread.is_alive() for thread in self.__threads.values()]) and len(self.__active_threads) == len(self.mapping.keys()):
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
                break
            else:
                # Print the monitored metrics every 10 epochs
                if self.__epochs % 10 == 0:
                    # monitor print
                    print("Monitored Metrics:")
                    for core in mapped_cores:
                        metrics = [f"{event} = {self.__monitor.getMetricAtCore(core, event)}" for event in events_to_track]
                        print(f"Core {core}: {' | '.join(metrics)}")
                    print("--------------------")
                # Print the current mapping every 50 epochs
                if self.__epochs % 50 == 0:
                    print("[" + str(round(current_time, 2)) + "s]: Current map")
                    map = ""
                    for app, core in self.mapping.items():
                        if app in self.__active_threads:
                            map += app + ", " + str(core) + "  | "
                    print(map)
                    print("--------------------")
                # any other periodic action here
           
            # Increment the epoch counter and sleep for the action interval
            self.__epochs += 1
            time.sleep(action_interval)
            
            
    def __clearCaches(self):
        runProc("sudo sync")
        runProc("sudo echo 3 > /proc/sys/vm/drop_caches")

    def __str__(self):
            return f"Engine with mapping {self.__mapping_policy} and DVFS policy {self.__dvfs_policy}"
        
    def __repr__(self):
            return self.__str__()