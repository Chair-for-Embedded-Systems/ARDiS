import glob
import os

class CPUFrequencyManager():

    def __init__(self, clock_domains: list[set[int]]) -> None:
        
        self.__cores: set[int] 
        self.__core_to_dvfs_domain : dict[int, set[int]] = dict()
        self.__core_to_freq_limits_khz: dict[int, tuple[int, int]] = dict()

        # Detect available cores
        logical_cores = [os.path.basename(d) for d in glob.glob(os.path.join("/sys/devices/system/cpu/", "cpu[0-9]*")) if os.path.isdir(d)]
        logical_cores = {int(core.replace('cpu','')) for core in logical_cores}
        
        # Determine allowed frequency ranges
        self.__cores = logical_cores
        for core in logical_cores:
            self.__core_to_freq_limits_khz[core] = self.get_processor_limits(core)

        # Create LUT for DVFS domains [Core -> Cores in same domain]
        for domain in clock_domains:
            for core in domain:
                # Check that core is not already assigned to a DVFS domain
                if self.__core_to_dvfs_domain.get(core) is not None:
                    raise ValueError(f"Core {core} is assigned to multiple DVFS domains")
                self.__core_to_dvfs_domain[core] = domain

        # Check that all cores are assigned to a DVFS domain
        for core in self.__cores:
            if not core in self.__core_to_dvfs_domain:
                raise ValueError(f"Core {core} is not assigned to a DVFS domain")

        # Save initial state of all cores            
        self._save_initial_state()

    @property
    def cores(self) -> set[int]:
        """
        Set of all logical cores managed by this frequency manager.
        """
        return self.__cores
    
    def affected_cores(self, core: int) -> set[int]:
        """
        Returns the set of cores in the same DVFS domain as the given core.
        """
        return self.__core_to_dvfs_domain[core]

    def set_cpu_freq(self, core: int, frequency_mhz: int) -> None:
        """
        Sets the given core to the provided frequency in MHz.
        Automatically applies the frequency to all cores in the same DVFS domain.
        """
        affected_cores = self.__core_to_dvfs_domain[core]
        frequency_khz = frequency_mhz * 1000
        for affected_core in affected_cores:            
            self.set_scaling_limits(affected_core, frequency_khz, frequency_khz)
    
    def get_cpu_freq(self, core: int) -> float:
        """
        Returns the current frequency of the given core in MHz"""
        with open(f"/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_cur_freq", 'r') as f:
            core_freq_mhz = float(f.read().strip()) / 1000
            return core_freq_mhz

    def get_governor(self, core: int) -> str | None:
        """
        Returns the current governor of the given core."""
        governor_path = f"/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_governor"
        try:
            with open(governor_path, 'r') as f:
                gov = str(f.read()).rstrip()
            return gov
        except IOError as e:
            print(f"Failed to get governor for core {core}: {e}")
            return None
        
    def set_governor(self, core: int, governor: str):
        governor_path = f"/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_governor"
        try:
            with open(governor_path, 'w') as f:
                f.write(governor)
            print(f"Governor of core {core} set to {governor}")
        except IOError as e:
            print(f"Failed to set governor for core {core} to {governor}: {e}")

    def get_available_governors(self, core: int) -> set[str]:
        path = f"/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_available_governors"
        try:
            with open(path, 'r') as f:
                governos = f.read()
            return {gov.rstrip() for gov in governos.split()}
        except IOError as _:
            return set()
        
    def get_scaling_limits(self, core: int) -> tuple[int, int]:
        """
        Returns the scaling limits in KHz
        """
        min_path = f"/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_min_freq"
        max_path = f"/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_max_freq"
        try:
            with open(min_path, 'r') as f_min:
                freq_min_khz = int(f_min.read())
            with open(max_path, 'r') as f_max:
                freq_max_khz = int(f_max.read())
            return freq_min_khz, freq_max_khz
        
        except Exception as e:
            raise e
        
    def get_processor_limits(self, core: int) -> tuple[int, int]:
        """
        Returns the processors upper and lower frequency limits in KHz.
        """
        cpu_min_path = f"/sys/devices/system/cpu/cpu{core}/cpufreq/cpuinfo_min_freq"
        cpu_max_path = f"/sys/devices/system/cpu/cpu{core}/cpufreq/cpuinfo_max_freq"
        try:
            with open(cpu_min_path, 'r') as f_min:
                freq_min_khz = int(f_min.read())
            with open(cpu_max_path, 'r') as f_max:
                freq_max_khz = int(f_max.read())
            return freq_min_khz, freq_max_khz
        except Exception as e:
            raise e

    def set_scaling_limits(self, core: int, min_freq_khz: int, max_freq_khz: int):
        """
        Sets the scaling limits of the given core in KHz.
        """
        DEBUG = False

        min_freq_path = f"/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_min_freq"
        max_freq_path = f"/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_max_freq"
        
        try:
            # Set the minimum frequency
            with open(min_freq_path, 'w') as f:
                f.write(str(min_freq_khz))
            if DEBUG:
                print(f"Minimum frequency for core {core} set to {min_freq_khz} MHz ({min_freq_khz} kHz)")
                
            # Set the maximum frequency
            with open(max_freq_path, 'w') as f:
                f.write(str(max_freq_khz))
            if DEBUG:
                print(f"Maximum frequency for core {core} set to {max_freq_khz} MHz ({max_freq_khz} kHz)")
            
        except IOError as e:
            print(f"Failed to set frequency limits for core {core}: {e}")


    def get_scaling_driver(self, core: int) -> str:
        """
        Returns the scaling driver for the given logical core.
        Common drivers include, but are not limited to:
        
            intel_pstate: Modern Intel CPUs
            intel_cpufreq : Older Intel CPUs or Modern Intel CPUs with HWP set to passive.
            amd-pstate: Modern AMD CPUs (AMD Zen 3 and later)
            acpi-cpufreq: Legacy
        """
        path = f"/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_driver"
        try:
            with open(path, 'r') as f:
                scaling_driver = str(f.read()).rstrip()
            return scaling_driver
        except:
            return ""
        
    def get_available_frequencies(self, core: int) -> list[int]:
        """
        Returns a list of available frequencies in KHz for the given core.
        """
        path = f"/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_available_frequencies"
        try:
            with open(path, 'r') as f:
                freqs = f.read()
            return [int(freq) for freq in freqs.split()]
        except IOError as _:
            return []
        
    def get_boost_state(self) -> bool | None:
        """
        Returns True if boost is enabled, False if disabled, and None if unknown.
        """
        boost_path = "/sys/devices/system/cpu/cpufreq/boost"
        try:
            with open(boost_path, 'r') as f:
                state = f.read().strip()
                if state == '1':
                    return True
                elif state == '0':
                    return False
                else:
                    return None
        except IOError as e:
            print(f"Failed to read boost state: {e}")
            return None
        
    def _set_boost_state(self, enable: bool) -> None:
        """
        Enables or disables boosting.
        """
        boost_path = "/sys/devices/system/cpu/cpufreq/boost"
        try:
            with open(boost_path, 'w') as f:
                f.write('1' if enable else '0')
            print(f"Boost state set to {'enabled' if enable else 'disabled'}.")
        except IOError as e:
            print(f"Failed to set boost state to {'enabled' if enable else 'disabled'}: {e}")
    
    def _save_initial_state(self):
        """
        Saves the initial state of all cores, so that it can be restored later.
        """
        core_to_config: dict[int, tuple[str, int, int]] = dict()
        for core in self.__cores:
            governor = self.get_governor(core)
            min_freq, max_freq = self.get_scaling_limits(core)
            assert governor is not None
            core_to_config[core] = (governor, min_freq, max_freq)
        self.__initial_state = core_to_config


    def restore_initial_state(self):
        """
        Restores the initial state of all cores.
        """
        for core, (governor, min_freq, max_freq) in self.__initial_state.items():
            self.set_governor(core, governor)
            self.set_scaling_limits(core, min_freq, max_freq)

    def reset(self, core: int, governor: str):
        
        # Check if governor is available
        if not governor in self.get_available_governors(core):
            raise ValueError(f"Unknown governor : {governor}")
        
        # Get processor min and max
        min_cpu_freq_khz, max_cpu_freq_khz = self.get_processor_limits(core)
        self.set_governor(core, governor)
        self.set_scaling_limits(core, min_cpu_freq_khz, max_cpu_freq_khz)

    def reset_all(self, governor: str):
        for core in self.__cores:
            self.reset(core, governor)

if __name__ == "__main__":
    freq_manager = CPUFrequencyManager(clock_domains=[{core for core in range(24)}])
    freq_manager.reset_all("schedutil")