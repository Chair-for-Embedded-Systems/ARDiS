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

def getPIDThread(proc : str, max_tries: int) -> int:
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
            tries += 1
            if tries >= max_tries:
                print("Warning: Process ", proc, " has probably not started yet.")
                found = True
            else:
                time.sleep(0.005)
    return pid


def getPIDOfApp(app, max_tries: int = 100):
    proc = app.split("-")[1]
    if "splash2x" in proc:
        proc = proc.replace("splash2x.", "")
    pid = getPIDThread(proc, max_tries)
    return pid