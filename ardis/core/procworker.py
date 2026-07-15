import os
import subprocess

def get_affinity(pids: set[int]) -> dict[int, set[int]]:
    """
    Returns the affinity as list of allowed logical cores for the given set of pid's.
    """
    output: dict[int, set[int]] = {}
    for pid in pids:
        try:
            affinity = os.sched_getaffinity(pid)
            output[pid] = affinity
        except Exception:
            output[pid] = set()
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
    pid_to_affinity = get_affinity(set(pids))
        
    if affinity is None:
        pid_matches = pids
    else:
        pid_matches: list[int] = []
        for pid, a in pid_to_affinity.items():
            if a == affinity:
                pid_matches.append(pid)
                
    if len(pid_matches) == 0:
        #print(f"{binary_name} has probably not started!")
        return None
        
    if len(pid_matches) > 1:
        raise RuntimeError(f"Found multiple instances of {binary_name} with the same affinity")
    
    return pid_matches[0]

def find_binary_in_exec_tree_recursively(binary_name: str, pid: int) -> int | None:
    """
    Recursively search for a binary in the process tree starting from the given PID.
    Returns the PID of the found binary or None if not found.
    """
    try:
        with open(f"/proc/{pid}/task/{pid}/children", "r") as f:
            children = f.read().strip().split()
            for child_pid in children:
                child_pid = int(child_pid)
                # Potential symbolic link to the executable of this child
                executable_link = f"/proc/{child_pid}/exe"
                    
                if os.path.islink(executable_link):
                    target_path = os.readlink(executable_link)
                    # Check if the target path contains the binary name
                    if binary_name in os.path.basename(target_path):
                        return child_pid

                result = find_binary_in_exec_tree_recursively(binary_name, child_pid)
                if result is not None:
                    return result
    except Exception as _:
        return None
        
    return None