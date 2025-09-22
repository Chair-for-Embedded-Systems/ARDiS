import glob
import os
from abc import ABC, abstractmethod

class CPUFrequencyManager(ABC):
    """
    Class to manage CPU frequency scaling on Linux systems.
    It provides and interface to read and modify CPU frequency settings via the sysfs interface.
    Depending on the CPU architecture, different scaling drivers may be used.
    Therefore there are different subclasses for different CPU vendors / scaling drivers in this package.
    
    **Note**: Setter methods are instance methods, as they require knowledge of the DVFS domains to coordinate adjustments.
    """

    def __init__(self, clock_domains: list[set[int]]) -> None:
    
        self.__cores: set[int] 
        self.__core_to_dvfs_domain: dict[int, set[int]] = dict()
        self.__core_to_freq_limits_khz: dict[int, tuple[int, int]] = dict()

        # Detect available cores
        logical_cores = [os.path.basename(d) for d in glob.glob(os.path.join("/sys/devices/system/cpu/", "cpu[0-9]*")) if os.path.isdir(d)]
        logical_cores = {int(core.replace('cpu','')) for core in logical_cores}
        
        # Determine allowed frequency ranges
        self.__cores = logical_cores
        for core in logical_cores:
            limits = self.get_processor_limits(core)
            if limits is None:
                raise EnvironmentError(f"Could not retrieve processor frequency limits for core {core}")
            self.__core_to_freq_limits_khz[core] = limits

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

    @abstractmethod
    def set_cpu_freq(self, core: int, frequency_mhz: int):
        """
        Sets the given core to the provided frequency in MHz.
        Automatically applies the frequency to all cores in the same DVFS domain.
        """
        affected_cores = self.__core_to_dvfs_domain[core]
        frequency_khz = frequency_mhz * 1000
        for affected_core in affected_cores:
            try:
                with open(f"/sys/devices/system/cpu/cpu{affected_core}/cpufreq/scaling_setspeed", 'w') as f:
                    f.write(str(frequency_khz))
            except IOError as e:
                print(f"Failed to set frequency for core {affected_core} to {frequency_mhz} MHz: {e}")

    @abstractmethod
    def get_cpu_freq(self, core: int) -> float:
        """
        Returns the current frequency of the given core in MHz
        """
        # This is a default implementation that should work for most drivers.
        # It is not guaranteed to work for all drivers, so subclasses can override it if necessary.
        with open(f"/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_cur_freq", 'r') as f:
            core_freq_mhz = float(f.read().strip()) / 1000
            return core_freq_mhz

    @staticmethod
    def get_governor(core: int) -> str | None:
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
        """
        Sets the governor of the given core.
        Automatically applies the governor to all cores in the same DVFS domain.
        """
        # Check if governor is available
        available_governors = self.get_available_governors(core)
        if available_governors is None:
            raise EnvironmentError(f"Could not retrieve available governors for core {core}")
        if governor not in available_governors:
            raise ValueError(f"Governor '{governor}' is not available for core {core}. Available governors: {available_governors}")
        
        # Apply governor to all cores in the same DVFS domain
        affected_cores = self.__core_to_dvfs_domain[core]
        for core in affected_cores:
            governor_path = f"/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_governor"
            try:
                with open(governor_path, 'w') as f:
                    f.write(governor)
            except IOError as e:
                print(f"Failed to set governor for core {core} to {governor}: {e}")

    @staticmethod
    def get_available_governors(core: int) -> set[str] | None:
        path = f"/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_available_governors"
        try:
            with open(path, 'r') as f:
                governos = f.read()
            return {gov.rstrip() for gov in governos.split()}
        except IOError as _:
            print(f"Failed to get available governors for core {core}")
            return None
    
    @staticmethod
    def get_scaling_limits(core: int) -> tuple[int, int] | None:
        """
        Returns the lower and upper scaling limits of the given core in KHz.
        This is the range in which the governor can set the frequency and is not necessarily the same as the processor limits.
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
            print(f"Failed to get scaling limits for core {core}: {e}")
            return None
    
    @staticmethod
    def get_processor_limits(core: int) -> tuple[int, int] | None:
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
            print(f"Failed to get processor limits for core {core}: {e}")
            return None

    def set_scaling_limits(self, core: int, min_freq_khz: int, max_freq_khz: int):
        """
        Sets the scaling limits of the given core in KHz.
        Automatically applies the limits to all cores in the same DVFS domain.
        """        
        # Check that requested limits are within processor limits
        proc_min, proc_max = self.__core_to_freq_limits_khz[core]
        if min_freq_khz < proc_min or max_freq_khz > proc_max:
            raise ValueError(f"Requested frequency limits [{min_freq_khz}, {max_freq_khz}] kHz for core {core} are outside processor limits [{proc_min}, {proc_max}] kHz")
        if min_freq_khz > max_freq_khz:
            raise ValueError(f"Requested minimum frequency {min_freq_khz} kHz is greater than requested maximum frequency {max_freq_khz} kHz for core {core}")

        # Set scaling limits for all cores in the same DVFS domain
        for affected_core in self.__core_to_dvfs_domain[core]:
            min_freq_path = f"/sys/devices/system/cpu/cpu{affected_core}/cpufreq/scaling_min_freq"
            max_freq_path = f"/sys/devices/system/cpu/cpu{affected_core}/cpufreq/scaling_max_freq"
            try:
                with open(min_freq_path, 'w') as f:
                    f.write(str(min_freq_khz))
                with open(max_freq_path, 'w') as f:
                    f.write(str(max_freq_khz))
            except IOError as e:
                print(f"Failed to set frequency limits for core {core}: {e}")

    @staticmethod
    def get_scaling_driver(core: int) -> str | None:
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
        except Exception as e:
            print(f"Failed to get scaling driver for core {core}: {e}")
            return None
    
    @staticmethod
    def get_available_frequencies(core: int) -> list[int] | None:
        """
        Returns a list of available frequencies in KHz for the given core.
        """
        path = f"/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_available_frequencies"
        try:
            with open(path, 'r') as f:
                freqs = f.read()
            return [int(freq) for freq in freqs.split()]
        except IOError as e:
            print(f"Failed to get available frequencies for core {core}: {e}")
            return None
        
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
            min_freq, max_freq = self.get_scaling_limits(core) # type: ignore
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

    def _reset(self, core: int, governor: str):
        
        # Check if governor is available
        available_governors = self.get_available_governors(core)
        if available_governors is None:
            raise EnvironmentError(f"Could not retrieve available governors for core {core}")
        if governor not in available_governors:
            raise ValueError(f"Governor '{governor}' is not available for core {core}. Available governors: {available_governors}")
        
        # Get processor min and max
        limits = self.get_processor_limits(core)
        if limits is None:
            raise EnvironmentError(f"Could not retrieve processor frequency limits for core {core}")
        min_cpu_freq_khz, max_cpu_freq_khz = limits

        self.set_governor(core, governor)
        self.set_scaling_limits(core, min_cpu_freq_khz, max_cpu_freq_khz)

    def reset_all(self, governor: str):
        """
        Resets all cores to use the specified governor and their processor frequency limits.
        """
        # Get one representative core from each DVFS domain
        core_group_representatives = {min(domain) for domain in self.__core_to_dvfs_domain.values()}
        # Reset each representative core, which will also reset all cores in the same DVFS domain
        for core in core_group_representatives:
            self._reset(core, governor)