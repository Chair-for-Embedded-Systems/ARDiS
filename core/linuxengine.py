from benchmarks.bench_manager import *
from config import *
from core.procworker import *
from core.mapping import *
from core.pidmonitor import *
from core.postprocessor import *
from core.reporter import *
from core.dvfs import *
from core.scheduler import *
from core.migration import *
import re

import threading
from timeit import default_timer as timer

lock = threading.Lock()

class LinuxEngine:
    def __init__(self, experiment_name, governor, scheduler = Scheduler(), min_frequency = 1500, max_frequency = 3500, perf_out_file = None):
        self.running = False
        self.startime = 0
        self.endtime = 0
        self.__epochs = 0
        self.mapping = {}
        self.__threads = {}
        self.__active_threads = []
        self.__waiting_threads = []
        self.PIDs = {}  
        self.__scheduler = scheduler 
        self.__monitor = None
        self.__dvfs_policy = DVFSPolicy(min_frequency=min_frequency, max_frequency=max_frequency, governor = governor)
        self.reporter = Reporter(experiment_name, RESULTS_FOLDER)
        self.__perf_out_file = perf_out_file
        self.__benchmark_manager = BenchManager(out_file=self.__perf_out_file)

    def __start(self):
        self.running = True
        self.startime = timer()

    def __launchApp(self, app):
        self.PIDs[app] = -1
        # Build the full application execution command from the corresponding script
        start = timer()
        self.__benchmark_manager.runApplicationOnCore(app, None)
        end = timer()
        with lock:
            self.__active_threads.remove(app)
        print("[Linux Engine]: " + app + " finished execution!" )
        self.reporter.logEvent("[Linux Engine]: " + app + " finished execution!" )
        print("[Linux Engine]: " + app + "'s execution time = " + str(round(end - start,2)) + "s" )
        self.reporter.logEvent("[Linux Engine]: " + app + "'s execution time = " + str(round(end - start,2)) + "s" )
        self.reporter.logExecutionTime(app, "UNKNOWN", end - start)
        
    # Create a thread for each application in the mapping 
    def __makeThreads(self):
        for app, core in self.mapping.items():
            print("will pass to thread: ", app)
            self.__threads[app] = threading.Thread(target=self.__launchApp, args=(app,))
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
        
        for app in applications:
            self.mapping[app] = -1
            self.PIDs[app] = -1

        self.reporter.logEvent("Mapping: " + str(self.mapping))
        print("Mapping: " + str(self.mapping))
        
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
                energy, time_elapsed = self.fetch_perf_data(self.__perf_out_file)
                self.reporter.logEvent("Total energy consumed (perf)= " + str(energy) + " Joules")
                self.reporter.logEvent("Total time elapsed (perf)= " + str(time_elapsed) + " seconds")
                # Clear the caches after the experiment is done
                self.__clearCaches()
                self.postprocess_results()
                break

            # Increment the epoch counter and sleep for the action interval
            self.__epochs += 1
            time.sleep(action_interval)
    
    def fetch_perf_data(self, perf_file_path):
        # Initialize variables to store the energy and time
        energy = None
        time_elapsed = None
        
        # Open and read the perf.out file
        with open(perf_file_path, 'r') as file:
            lines = file.readlines()
        
        # Iterate through the lines to find energy and time
        for line in lines:
            # Search for the energy line using regex
            energy_match = re.search(r'([\d,\.]+)\s+Joules\s+power/energy-psys/', line)
            if energy_match:
                energy = float(energy_match.group(1).replace(',', ''))  # Remove commas and convert to float
            
            # Search for the time elapsed line using regex
            time_match = re.search(r'([\d,\.]+)\s+seconds time elapsed', line)
            if time_match:
                time_elapsed = float(time_match.group(1))  # Convert to float
        
        return energy, time_elapsed
    # Post-process the results of the experiment, which cannot be done during the experiment
    def postprocess_results(self):
        pass

    def __clearCaches(self):
        runProc("sudo sync")
        runProc("sudo echo 3 > /proc/sys/vm/drop_caches")
        
    def __repr__(self):
            return self.__str__()