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


available_apps = ['spec-gcc', 'spec-milc', 'spec-bzip2', 'spec-sphinx3', 'spec-astar', 'spec-lbm',
                  'spec-bwaves', 'spec-mcf', 'spec-zeusmp',  'spec-namd', 'spec-h264ref', 'spec-gobmk',
                  'spec-povray', 'spec-gromacs', 'spec-cactusADM', 'spec-omnetpp', 'spec-hmmer', 'spec-leslie3d',
                  'parsec-blackscholes', 'parsec-bodytrack', 'parsec-canneal', 'parsec-dedup', 'parsec-facesim',
                  'parsec-ferret', 'parsec-fluidanimate', 'parsec-freqmine', 'parsec-streamcluster',
                  'parsec-swaptions', 'parsec-vips', 'parsec-x264']



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
    p.wait()
    #TODO: measure execution time for the process.
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
        

        

def makeThreads(mapping):
    #creating threads
    a = threading.Thread(target=launchApp, args=(mapping[0], 0))
    b = threading.Thread(target=launchApp, args=(mapping[1], 1))
    c = threading.Thread(target=launchApp, args=(mapping[2], 2))
    d = threading.Thread(target=launchApp, args=(mapping[3], 3))
    e = threading.Thread(target=launchApp, args=(mapping[4], 4))
    f = threading.Thread(target=launchApp, args=(mapping[5], 5))
    print("Launching workload")

    a.start()
    b.start()
    c.start()
    d.start()
    e.start()
    f.start()

    return a,b,c,d,e,f


def waitForThreads(a, b, c, d, e, f):
    a.join()
    b.join()
    c.join()
    d.join()
    e.join()
    f.join()
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


def generateApps():
    apps = []
    attack_core = randrange(6)
    while len(apps) < 6:
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
    pids = [-1,-1,-1,-1,-1,-1]
    a = RetThread(target=getPIDThread, args=(procs[0],))
    b = RetThread(target=getPIDThread, args=(procs[1],))
    c = RetThread(target=getPIDThread, args=(procs[2],))
    d = RetThread(target=getPIDThread, args=(procs[3],))
    e = RetThread(target=getPIDThread, args=(procs[4],))
    f = RetThread(target=getPIDThread, args=(procs[5],))
    #print("[Thread team]: getting pids in parallel")
    a.start()
    b.start()
    c.start()
    d.start()
    e.start()
    f.start()

    pids[0] = a.join()
    pids[1] = b.join()
    pids[2] = c.join()
    pids[3] = d.join()
    pids[4] = e.join()
    pids[5] = f.join()

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
    global mapping
    mapping = list(base_map)
    if (metrics):    
        if (workdir!=None):
            mon.setworkdir(workdir)
        mon.start()
    print("Current mapping: " + str(base_map))
    ta,tb,tc,td,te,tf = makeThreads(base_map)
    pids = getPIDs(mapping)
    print("PIDs: ", pids)
    waiter =  threading.Thread(target=waitForThreads, args=(ta,tb,tc,td,te,tf,))
    waiter.start()
    start = timer()

    global end_of_experiment
    while not end_of_experiment:
        curr = timer()
        if (int(curr - start) % 5 == 0):
            print("**************  Current map: ", mapping, "*******************")
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
    for x in range(NUM_WORKLOADS):
       premaps.append(generateApps())
    mappfile.write(str(premaps))
    mappfile.close()

    for idx in range(len(premaps)):
        print("Running workload ", idx)
        run_simple(premaps[idx])
        print("Workload ", idx, " finished")
    


    



