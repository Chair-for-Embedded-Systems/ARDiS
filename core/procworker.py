import subprocess
import time
from core.retthreading import *

def runProc(app_str):
    command = app_str.split(" ")
    p = subprocess.Popen(command,  stdout=subprocess.PIPE)
    p.wait()

def killProc(proc_name):
    str_cmd = "sudo killall " + proc_name
    command = str_cmd.split(" ")
    p = subprocess.Popen(command, stdout=subprocess.PIPE)
    p.wait()

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
            if tries >= 200:
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