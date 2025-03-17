
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
        except FileNotFoundError as fe:
            output[pid] = []
            continue
    
    return output

def poll_frequency(logic_cores: set[int]) -> dict[int, float]:
    """
    Returns the frequency for the given set of cores.
    """
    core_to_freq = {}
    for core in logic_cores:
        with open(f"/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_cur_freq", 'r') as f:
            core_freq_mhz = int(f.read().strip()) / 1000
            core_to_freq[core] = core_freq_mhz
    return core_to_freq

if __name__ == '__main__':
    affinity = poll_affinity(set([1]))
    frequency = poll_frequency(set([0,2,4,23]))
    print(affinity)
    print(frequency)