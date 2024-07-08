from config import *
from core.procworker import *
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

class Engine:
    def __init__(self):
        self.mapping  = []
        self.running = False
        self.startime = 0
        self.endtime = 0       

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
        core = -1
        #TODO: probably need a cleaner way to do this
        app_short = app_name
        if "spec" or "parsec" in app_name:
            app_short = app_name[5:]
        #TODO: the mapping itself is just a list of apps for now
        # we need to adapt the structure of the mapping to  explicitly
        # include the core for each app
        for idx in range(len(self.mapping )):
            if app_short in self.mapping [idx]:
                core = idx
        with lock:
            idcore = self.mapping .index(app_name)
            self.mapping [idcore] = self.mapping [idcore]+"*"
        #TODO: print and possibly record execution time.
        print("[Core " + str(idcore) +"]: " + app_name + " finished execution!" )
        print("[Core " + str(idcore) +"]: " + app_name + "'s execution time = " + str(round(end - start,2)) + "s" )
        
    # Create a thread for each application in the mapping 
    def __makeThreads(self, mapping):
        self.mapping  = mapping
        threads = []
        #TODO replace the core number (index for now) with the actual core number
        for idx in range(len(self.mapping)):
            threads.append(threading.Thread(target=self.__launchApp, args=(self.mapping[idx], idx)))
        #creating threads
        print("Launching workload")
        for tidx in range(len(threads)):
            threads[tidx].start()
        self.running = True
        return threads

    # Wait for all threads to finish
    def __waitForThreads(self, threads):
        # Barrier here to wait for all threads to finish
        for tidx in range(len(threads)):
            threads[tidx].join()
        # Threads have finished, set running to false
        self.running = False
        self.endtime = timer()
        print("END!")
        print("Total execution time of workload = ", str(round(self.endtime - self.startime, 2)) + "s")

   
    def executeWorkload(self, mapping):
        threads = self.__makeThreads(mapping)
        waiter = threading.Thread(target=self.__waitForThreads, args=(threads,))
        waiter.start()
        self.startime = timer()
        self.mainLoop()
        
      
    def getProcessIds(self):
        return getPIDs(self.mapping)
    
    def getElapsedTime(self):
        return timer() - self.startime
    
    def mainLoop(self):
        # Print the PIDs of the applications
        pids = self.getProcessIds()
        print("PIDs: ", pids)
        # Add any periodic actions here
        while self.running:
            # print the current mapping every 5 seconds
            if (int(self.getElapsedTime()) % 5 == 0):
                print("Current map:", self.mapping)
                time.sleep(0.5)
            time.sleep(action_interval)


