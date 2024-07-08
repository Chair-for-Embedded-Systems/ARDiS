from config import *
from core.procworker import *
from core.mapping import *
from core.reporter import *
import threading
import subprocess
from timeit import default_timer as timer
import math

lock = threading.Lock()


def getFullPath(app_str):
    if "spec" in app_str:
        name = "./scripts/" + "run_spec_app.sh " + app_str[5:] 
    elif "splash" in app_str:
        name = "./scripts/"+ app_str[7:]+".sh" 
    elif "parsec" in app_str:
        name = "./scripts/" + "run_parsec_app.sh " + app_str[7:]
    else:
        name = app_str
    return name 
 
def getCoreByApp(mapping, core):
    for app, value in mapping.items():
        if value == core:
            return app
    return None

class Engine:
    def __init__(self, experiment_name):
        self.running = False
        self.startime = 0
        self.endtime = 0
        self.__last_print_time = None
        self.mapping = {}
        self.__threads = {}
        self.__active_threads = []  
        self.__mappingPolicy = MappingPolicy()
        self.reporter = Reporter(experiment_name, RESULTS_FOLDER)
            

    def __start(self):
        self.running = True
        self.startime = timer()

    def __launchApp(self, app_name, core):
        # Build the full application execution command from the corresponding script
        app_str = getFullPath(app_name)
        str_cmd = "taskset -c " + str(core) + " " + app_str + " " + str(core)
        command = str_cmd.split(" ")
        # Execute the application
        p = subprocess.Popen(command,  stdout=subprocess.PIPE)
        start = timer()
        p.wait()
        end = timer()
        core = self.mapping[app_name]
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
    
    #TODO: logic for getting PIDs is not done yet
    def getProcessIds(self):
        return getPIDs(self.mapping.keys())
    
    def getElapsedTime(self):
        return timer() - self.startime
    
    def __startThread(self,  app):
        self.__threads[app].start()
        self.__active_threads.append(app)
        print("[" + str(round(self.getElapsedTime(), 2)) + "s]: Thread for " + app + " started!")
        self.reporter.logEvent("[" + str(round(self.getElapsedTime(), 2)) + "s]: Thread for " + app + " started!")


    def executeWorkload(self, applications, schedule):
        # Execute the mapping policy 
        self.mapping = self.__mappingPolicy.executeMapping(applications)
        self.reporter.logEvent("Mapping: " + str(self.mapping))
        print("Mapping: " + str(self.mapping))
        # Create the threads each application.
        self.__makeThreads()	
        # then start the workload execution
        self.__start()
        while self.running:
            # Check if the application is scheduled to start and if the thread is not already running
            for app in self.mapping:
                #TODO: this probably should be done by the scheduler, but we don't have access to it from here yet
                if schedule[app] <= self.getElapsedTime() and app not in self.__active_threads:
                    # Start the thread
                    self.__startThread(app)

            # Check if all threads are done before finishing
            if not any([thread.is_alive() for thread in self.__threads.values()]) and len(self.__active_threads) == len(self.mapping.keys()):
                self.running = False
                self.endtime = timer()
                print("[" + str(round(self.getElapsedTime(), 2)) + "s]: Experiment Finished!")
                self.reporter.logEvent("[" + str(round(self.getElapsedTime(), 2)) + "s]: Experiment Finished!")
                print("Total execution time of experiment = ", str(round(self.endtime - self.startime, 2)) + "s")
                self.reporter.logEvent("Total execution time of experiment = " + str(round(self.endtime - self.startime, 2)) + "s")
                break
            else:
                # Print the current mapping every 5 seconds
                current_time = self.getElapsedTime()
                if round(current_time, 1) % 5 == 0:
                    if self.__last_print_time  is None or current_time - self.__last_print_time  >= 5:
                        print("[" + str(round(current_time, 2)) + "s]: Current map")
                        map = ""
                        for app, core in self.mapping.items():
                            if app in self.__active_threads:
                                map += app + ", " + str(core) + "  | "
                        print(map)
                        # hack to make sure we only print once
                        self.__last_print_time  = current_time
            time.sleep(action_interval)
