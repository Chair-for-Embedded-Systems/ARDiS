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

def poll_affinity(pids: set[int]) -> dict[int, set[int]]:
        """
        Returns the affinity as list of allowed logical cores for the given set of pid's.
        """
        output: dict[int, set[int]] = {}
        for pid in pids:
            try:
                with open(f"/proc/{pid}/status", 'r') as f:
                    for line in f:
                        if "Cpus_allowed:" in line:
                            hex_mask = line.split(':')[1]
                            bin_mask = bin(int(hex_mask, 16))[2:]
                            bin_mask = bin_mask.zfill(len(hex_mask)*4)
                            bin_mask = bin_mask[::-1]
                            affinity = [core for core,bit in enumerate(bin_mask) if bit == '1']
                            output[pid] = set(affinity)
                            break
            except FileNotFoundError as fe:
                output[pid] = set()
                continue
    
        return output

def get_pid_of_app(binary_name: str, affinity: set[int] | None) -> int | None:
    # Find all pids with this application name
    command = f"pgrep {binary_name}"
    p = subprocess.run(command.split(" "), capture_output=True)
    pid_string = str(p.stdout.decode())
        
    # No pids found
    if len(pid_string) == 0:
        return None
        
    # Check affinity of each pid to find correct app in multi-instance scenarios
    pids = [int(p) for p in pid_string.split("\n") if p]
    pid_to_affinity = poll_affinity(set(pids))
        
    if affinity is None:
        pid_matches = pids
    else:
        pid_matches = []
        for pid, a in pid_to_affinity.items():
            if a == affinity:
                pid_matches.append(pid)
                
    if len(pid_matches) == 0:
        print(f"{binary_name} has probably not started!")
        return None
        
    if len(pid_matches) > 1:
        raise RuntimeError(f"Found multiple instances of {binary_name} with the same affinity")
    
    return pid_matches[0]

def getPIDOfApp(app: str, max_tries: int = 100):
    proc = app.split("-")[1]
    if "splash2x" in proc:
        proc = proc.replace("splash2x.", "")
    pid = getPIDThread(proc, max_tries)
    return pid