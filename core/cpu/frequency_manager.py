from abc import ABC, abstractmethod

class CPUFrequencyManager(ABC):
    
    @abstractmethod
    def set_cpu_freq(self, core: int, frequency_mhz: int):
        """
        Sets the given core to the 
        """
        raise NotImplementedError
    
    @abstractmethod
    def get_cpu_freq(self, core: int) -> float:
        raise NotImplementedError

    def get_governor(self, core: int) -> str | None:
        governor_path = f"/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_governor"
        try:
            with open(governor_path, 'r') as f:
                gov = str(f.read()).rstrip()
            return gov
        except IOError as e:
            print(f"Failed to set governor for core {core}: {e}")
            return None
        
    def set_governor(self, core: int, governor: str):
        governor_path = f"/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_governor"
        try:
            with open(governor_path, 'w') as f:
                f.write(governor)
            print(f"Governor of core {core} set to {governor}")
        except IOError as e:
            print(f"Failed to set governor for core {core}: {e}")

    def get_available_governors(self, core: int) -> set[str]:
        path = f"/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_available_governors"
        try:
            with open(path, 'r') as f:
                governos = f.read()
            return {gov.rstrip() for gov in governos.split()}
        except IOError as e:
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

    def set_scaling_limits(self, core: int, min_freq_mhz: int, max_freq_mhz: int):
        """
        Sets the scaling limits of 
        """
        DEBUG = False
        
        min_freq_khz = 1000 * min_freq_mhz
        max_freq_khz = 1000 * max_freq_mhz
        min_freq_path = f"/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_min_freq"
        max_freq_path = f"/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_max_freq"
        
        try:
            # Set the minimum frequency
            with open(min_freq_path, 'w') as f:
                f.write(str(min_freq_khz))
            if DEBUG:
                print(f"Minimum frequency for core {core} set to {min_freq_mhz} MHz ({min_freq_khz} kHz)")
                
            # Set the maximum frequency
            with open(max_freq_path, 'w') as f:
                f.write(str(max_freq_khz))
            if DEBUG:
                print(f"Maximum frequency for core {core} set to {max_freq_mhz} MHz ({max_freq_khz} kHz)")
            
        except IOError as e:
            print(f"Failed to set frequency limits for core {core}: {e}")


    def get_scaling_driver(self, core: int) -> str:
        """
        Returns the scaling driver for the given logical core.
        Common drivers include, but are not limited to:

        'intel_cpufreq' : Older Intel CPUs or Modern Intel CPUs with HWP set to passive.
        'intel_pstate': Modern Intel CPUs
        'amd-pstate': Modern AMD CPUs
        'acpi-cpufreq': Legacy
        """
        path = f"/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_driver"
        try:
            with open(path, 'r') as f:
                scaling_driver = str(f.read()).rstrip()
            return scaling_driver
        except:
            return ""
        
    def reset(self, core: int, governor: str):
        # Check if governor is available
        if not governor in self.get_available_governors(core):
            raise ValueError(f"Unknown governor : {governor}")
        
        # Get processor min and max
        min_cpu_freq, max_cpu_freq = self.get_processor_limits(core)
        self.set_governor(core, governor)
        self.set_scaling_limits(core, min_cpu_freq, max_cpu_freq)