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

def getPIDThread(proc):
    found = False
    str_cmd = "taskset -c 0 pgrep " + proc
    command = str_cmd.split(" ")
    pid = -1
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
            if tries >= 1000:
                print("Warning: Process ", proc, " has probably finished")
                found = True
    return pid


def getPIDOfApp(app):
    proc = app.split("-")[1]
    pid = getPIDThread(proc)
    return pid