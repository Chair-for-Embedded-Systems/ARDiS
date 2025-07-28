import os


def poll_affinity(pids: set[int]) -> dict[int, list[int]]:
    """
    Returns the affinity as list of allowed logical cores for the given set of pid's.
    """
    output: dict[int, list[int]] = {}
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
                        output[pid] = affinity
                        break
        except (FileNotFoundError, PermissionError, OSError) as e:
            output[pid] = []
            continue
    
    return output

def poll_last_sceduled_cpu(pids: set[int]) -> dict[int, int]:
    """
    Extracts the `tids` for the given set of pids and fetches the last cpu that was scheduled fot the tid.
    Note: For each pid there is always one thread with tid==pid.

    Returns a map from `tid` to last executed cpu
    
    Example:
    >>> poll_last_sceduled_cpu(pids={37, 42})
    {
        37 : 4,      # PID 37, TID 37, Thread #1
        38 : 4,      # PID 37, TID 38, Thread #2
        42 : 6,      # PID 42, TID 42, Thread #1
    }
    """
    output: dict[int, int] = {}
    for pid in pids:
        try:
            tids = [int(tid) for tid in os.listdir(f"/proc/{pid}/task")]
        except (FileNotFoundError, PermissionError, OSError) as e:
            continue
            
        for tid in tids:
            try:
                with open(f"/proc/{pid}/task/{tid}/stat", 'r') as f:
                    # CPU number last executed on (39, index starts at 1)
                    # https://www.man7.org/linux/man-pages//man5/proc_pid_stat.5.html
                    fields = f.read().split(' ')
                    cpu = int(fields[38])
                    output[tid] = cpu
            except (FileNotFoundError, PermissionError, OSError) as e:
                continue
    
    return output

def poll_frequency(logic_cores: set[int]) -> dict[int, float]:
    """
    Returns the frequency for the given set of cores.
    """
    core_to_freq = {}
    for core in logic_cores:
        try:
            with open(f"/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_cur_freq", 'r') as f:
                core_freq_mhz = int(f.read().strip()) / 1000
                core_to_freq[core] = core_freq_mhz
        except (FileNotFoundError, PermissionError, OSError) as e:
            continue
    return core_to_freq