from config import *
from core.procworker import *
from core.mapping import *
import threading
import subprocess
from timeit import default_timer as timer

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
    def __init__(self):
        self.running = False
        self.startime = 0
        self.endtime = 0
        self.mapping = {}
        self.__threads = {}
        self.__active_threads = []  
        self.__mappingPolicy = MappingPolicy()
            

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
        print("[Core " + str(core) +"]: " + app_name + "'s execution time = " + str(round(end - start,2)) + "s" )
        
    # Create a thread for each application in the mapping 
    def __makeThreads(self):
        for app, core in self.mapping.items():
            self.__threads[app] = threading.Thread(target=self.__launchApp, args=(app, core))
            print("Thread for " + app + " created!")
    
    #TODO: logic for getting PIDs is not done yet
    def getProcessIds(self):
        return getPIDs(self.mapping.keys())
    
    def getElapsedTime(self):
        return timer() - self.startime
    
    def __startThread(self,  app):
        self.__threads[app].start()
        self.__active_threads.append(app)
        print("Thread for " + app + " started!")


    def executeWorkload(self, applications, schedule):
        # Execute the mapping policy 
        self.mapping = self.__mappingPolicy.executeMapping(applications)
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
                print("END!")
                print("Total execution time of workload = ", str(round(self.endtime - self.startime, 2)) + "s")
            else:
                if (int(self.getElapsedTime()) % 5 == 0):
                    print("Current map:", self.mapping)
                    time.sleep(0.5)
                time.sleep(action_interval)


