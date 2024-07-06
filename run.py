from config import *
from monitor import *
from retthreading import *
import time
from timeit import default_timer as timer
import subprocess
import random
from datetime import datetime
from random import randrange

import argparse

lock = threading.Lock()
end_of_experiment = False


def runProc(app_str):
    command = app_str.split(" ")
    p = subprocess.Popen(command,  stdout=subprocess.PIPE)
    p.wait()

def killProc(proc_name):
    str_cmd = "sudo killall " + proc_name
    command = str_cmd.split(" ")
    p = subprocess.Popen(command, stdout=subprocess.PIPE)
    p.wait()
    
    
def launchApp(app_name, core):
    app_str = getFullPath(app_name)
    str_cmd = "taskset -c " + str(core) + " " + app_str + " " + str(core)
    command = str_cmd.split(" ")
    #print(str_cmd)
    p = subprocess.Popen(command,  stdout=subprocess.PIPE)
    start = timer()
    p.wait()
    end = timer()
    global mapping
    core = -1
    app_short = app_name[5:]
    for idx in range(len(mapping)):
        if app_short in mapping[idx]:
            core = idx
    with lock:
        idcore = mapping.index(app_name)
        mapping[idcore] = mapping[idcore]+"*"
    #TODO: print and possibly record execution time.
    print("[Core " + str(idcore) +"]: " + app_name + " finished execution!" )
    print("[Core " + str(idcore) +"]: " + app_name + "'s execution time = " + str(round(end - start,2)) + "s" )
        

        
# Create a thread for each application in the mapping
def makeThreads(mapping):
    threads = []
    #TODO replace the core number (index for now) with the actual core number
    for idx in range(len(mapping)):
        threads.append(threading.Thread(target=launchApp, args=(mapping[idx], idx)))
    #creating threads
    print("Launching workload")
    for tidx in range(len(threads)):
        threads[tidx].start()
    return threads

# Wait for all threads to finish
def waitForThreads(threads):
    for tidx in range(len(threads)):
        threads[tidx].join()
    global end_of_experiment
    end_of_experiment = True
    print("END!")


def getFullPath(app_str):
    if "spec" in app_str:
        name = SCRIPTS_DIR + "run_spec_app.sh " + app_str[5:] 
    elif "splash" in app_str:
        name = SCRIPTS_DIR + app_str[7:]+".sh" 
    elif "parsec" in app_str:
        name = SCRIPTS_DIR + "run_parsec_app.sh " + app_str[7:]
    else:
        name = app_str
    return name


def getProcessName(app_str):
    if "spec" in app_str:
        if "xalan" in app_str:
            name = "Xalan_base.lnx64-gcc"
        elif "sphinx" in app_str:
            name = "sphinx_livepretend_base.lnx64-gcc"
        else:
            name = app_str[5:] +"_base.lnx64-gcc"
    elif "splash" in app_str:
        name = app_str[7:].upper()
    elif "parsec" in app_str:
        name = app_str[7:]
    else:
        name = app_str
    return name

# Generate a random mapping of unique applications to cores
def generateApps():
    apps = []
    while len(apps) < system_cores:
        candidate = available_apps[randrange(len(available_apps))]
        if candidate not in apps:
            apps.append(candidate)
    return apps

def containsMap(map_list, map):
    for m in map_list:
        if m == map:
            return True
    return False


def generateVariant(mapping):
    tmp_map = list(mapping)
    random.shuffle(tmp_map)
    return tmp_map




def getProcessNamesFromMap(mapping):
    procs = []
    for app in mapping:
        procs.append(getProcessName(app))
    return procs



def getPIDThread(proc):
    found = False
    str_cmd = "taskset -c 0 pidof " + proc
    command = str_cmd.split(" ")
    pid = -1
    #print(str_cmd)
    tries = 0
    while not found:
        p = subprocess.run(command,capture_output=True)
        ans = p.stdout
        try:
            a = int(ans.decode("utf-8")) + 1 - 1
            found = True
            pid = a
        except:
            tries+=1
            time.sleep(0.005)
            if tries >= 100:
                print("Warning: Process ", proc, " has probably finished")
                found = True
    return pid


#this is an overkill, I am not sorry.
def getPIDs(mapping):
    procs = getProcessNamesFromMap(mapping)
    #print(procs)
    pids = []
    thread_workers = []
    for proc in procs:
        thread_workers.append(RetThread(target=getPIDThread, args=(proc,)))
    #print("[Thread team]: getting pids in parallel")
    for tidx in range(len(thread_workers)):
        thread_workers[tidx].start()
    for tidx in range(len(thread_workers)):
        pids.append(thread_workers[tidx].join())

    return pids


def setAffinity(pid, core):
    cmd_str = "taskset -cp " + str(core) + " " + str(pid)
    command = cmd_str.split(" ")    
    p = subprocess.Popen(command,  stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    if p.stderr.readlines():
        return False
    else:
        p.wait()
        return True
   

def executeMigration(newmap, pids):
    global mapping
    print(newmap)
    tmp_pids = list(pids)
    #Only apply migration if the new candidate is different than current mapping
    if (newmap != mapping):
        #check each app for its new core
        for idx in range(len(mapping)):
            pid = pids[idx]
            #the application might have finished, so check first if it exists still
            try:
                new_idx = newmap.index(mapping[idx])
                # let's check if it needs to be moved
                if new_idx != idx:
                    #if so then save the new pid in the corresponding core position
                    tmp_pids[new_idx] = pid
                    #and move it
                    setAffinity(pid, new_idx)
            #if the app finished already
            except:
                #remove the * of app name for comparison
                new_idx = newmap.index(mapping[idx][:-1])
                #and add it again in the new mapping
                newmap[new_idx] = newmap[new_idx] +"*"
                #then set the pid to undefined (-1)
                tmp_pids[new_idx] = -1
        #finally make the current mapping as the new one
        with lock:    
            mapping = newmap
    return tmp_pids  


def run_simple(base_map, workdir=None, metrics = False):
    global end_of_experiment
    end_of_experiment = False
    global mapping
    mapping = list(base_map)
    if (metrics):    
        if (workdir!=None):
            mon.setworkdir(workdir)
        mon.start()
    start = timer()
    print("Current mapping: " + str(base_map))

    threads = makeThreads(base_map)
    pids = getPIDs(mapping)
    print("PIDs: ", pids)
    
    waiter =  threading.Thread(target=waitForThreads, args=(threads,))
    waiter.start()


    while not end_of_experiment:
        curr = timer()
        if (int(curr - start) % 5 == 0):
            print("Current map:", mapping)
            time.sleep(1)
        time.sleep(0.1)

    if metrics:
        mon.stop()
    end = timer()
    elapsed = end - start
    print("Experiment finished successfully") 
    print("Total execution time = ", str(round(elapsed,2)) + "s")
    return elapsed

    
    
if __name__ == "__main__":
    premaps = []

    mappfile=open("results/maps.txt", "w")
    for x in range(workloads):
       premaps.append(generateApps())
    mappfile.write(str(premaps))
    mappfile.close()

    for idx in range(len(premaps)):
        print("Running workload ", idx)
        run_simple(premaps[idx])
        print("Workload ", idx, " finished")
    


    



