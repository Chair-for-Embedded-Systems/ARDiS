import glob
import os
from core.cpu.frequency_manager import CPUFrequencyManager

class GenericCPUFrequencyManager(CPUFrequencyManager):
    
    """
    Generic implementation of the CPU frequency manager.
    It utilizes the scaling driver that is accessable via the sysfs for DVFS.
    Therefore it should work with any processor type
    """
    cores: set[int] 
    core_to_dvfs_domain : dict[int, set[int]] = dict()
    core_to_freq_limits: dict[int, tuple[int, int]] = dict()

    def __init__(self, dvfs_domains: list[set[int]]) -> None:
        super().__init__()
        # Creat LUT for DVFS domains
        for domain in dvfs_domains:
            for core in domain:
                self.core_to_dvfs_domain[core] = domain
        
        # Detect available cores
        logical_cores = [os.path.basename(d) for d in glob.glob(os.path.join("/sys/devices/system/cpu/", "cpu[0-9]*")) if os.path.isdir(d)]
        logical_cores = {int(core.replace('cpu','')) for core in logical_cores}
        
        # Determine allowed frequency domains
        self.cores = logical_cores
        for core in logical_cores:
            self.core_to_freq_limits[core] = self.get_processor_limits(core)

    def set_cpu_freq(self, core: int, frequency_mhz: int):
        affected_cores = self.core_to_dvfs_domain[core]
        print(f"Setting frequency of {affected_cores} to {frequency_mhz} mhz")
        for affected_core in affected_cores:
            self.set_scaling_limits(affected_core, frequency_mhz, frequency_mhz)

    def get_cpu_freq(self, core: int) -> float:
        print(f"Returning the frequency of core {core}")
        with open(f"/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_cur_freq", 'r') as f:
            core_freq_mhz = float(f.read().strip()) / 1000
            return core_freq_mhz

   
    def _print_core_stats(self, core: int):
        print(f"Core: {core}")
        print(f"Current governor: {self.get_governor(core)}")
        print(f"Available governors: {self.get_available_governors(core)}")
        min_khz, max_khz = self.get_scaling_limits(0)
        print(f"Min-scaling: {min_khz}, Max scaling: {max_khz}")
        print(f"Scaling driver: {self.get_scaling_driver(core)}")

    def _print_stats(self): 
        print("Generic Frequency Manager")
        print("Core, Lowest Frequency, Highest Frequency")
        for core in self.core_to_freq_limits:
            lowest_freq, highest_freq = self.core_to_freq_limits[core]
            print(f"{core} : {lowest_freq} {highest_freq}")

    def _test(self):
        self._print_core_stats(0)

if __name__ == "__main__":
    dvfs_groups = [
        {0, 1}, {2, 3}, {4, 5}, {6, 7}, {8, 9}, {10, 11}, {12, 13}, {14, 15},
        {16, 17, 18, 19}, {20, 21, 22, 23}
    ]
    cpu_manager = GenericCPUFrequencyManager(dvfs_groups)
    cpu_manager._print_stats()
    #cpu_manager._print_core_stats(2)
    #cpu_manager.set_governor(20, "userspace")
    #cpu_manager.set_governor(21, "userspace")
    #cpu_manager.set_governor(22, "userspace")
    #cpu_manager.set_governor(23, "userspace")
    #cpu_manager.set_cpu_freq(20, 2400)