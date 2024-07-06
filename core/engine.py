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

    def launchApp(self, app_name, core):
        app_str = getFullPath(app_name)
        str_cmd = "taskset -c " + str(core) + " " + app_str + " " + str(core)
        command = str_cmd.split(" ")
        #print(str_cmd)
        p = subprocess.Popen(command,  stdout=subprocess.PIPE)
        start = timer()
        p.wait()
        end = timer()
        core = -1
        app_short = app_name[5:]
        for idx in range(len(self.mapping )):
            if app_short in self.mapping [idx]:
                core = idx
        with lock:
            idcore = self.mapping .index(app_name)
            self.mapping [idcore] = self.mapping [idcore]+"*"
        #TODO: print and possibly record execution time.
        print("[Core " + str(idcore) +"]: " + app_name + " finished execution!" )
        print("[Core " + str(idcore) +"]: " + app_name + "'s execution time = " + str(round(end - start,2)) + "s" )
        
    # Create a thread for each application in the self.mapping 
    def makeThreads(self, mapping ):
        self.mapping  = mapping
        threads = []
        #TODO replace the core number (index for now) with the actual core number
        for idx in range(len(self.mapping )):
            threads.append(threading.Thread(target=self.launchApp, args=(self.mapping [idx], idx)))
        #creating threads
        print("Launching workload")
        for tidx in range(len(threads)):
            threads[tidx].start()
        self.running = True
        return threads

    # Wait for all threads to finish
    def waitForThreads(self, threads):
        for tidx in range(len(threads)):
            threads[tidx].join()
        self.running = False
        self.endtime = timer()
        print("END!")
        print("Total execution time of workload = ", str(round(self.endtime - self.startime, 2)) + "s")

    def startWorkload(self, mapping):
        threads = self.makeThreads(mapping)
        waiter = threading.Thread(target=self.waitForThreads, args=(threads,))
        waiter.start()
        self.startime = timer()
      
    def getProcessIds(self):
        return getPIDs(self.mapping)
    
    def getElapsedTime(self):
        return timer() - self.startime


