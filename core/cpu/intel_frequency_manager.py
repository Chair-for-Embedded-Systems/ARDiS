import struct
import subprocess
from core.cpu.frequency_manager import CPUFrequencyManager

class IntelFrequencyManager(CPUFrequencyManager):
    
    # MSR for the HWP Programming Interface 
    # (see Intel® 64 and IA-32 Architectures Software Developer’s Manual Volume 3B: System Programming Guide, Part 2)
    # https://cdrdv2.intel.com/v1/dl/getContent/671427
    IA32_PM_ENABLE = 0x770
    IA32_HWP_CAPABILITIES = 0x771
    IA32_HWP_REQUEST = 0x774

    def __init__(
        self,
        clock_domains: list[set[int]],
        use_hwp: bool = False,
        disable_thermald: bool = True
    ) -> None:
        
        self.__use_hwp = use_hwp
        self.__disable_thermald = disable_thermald
        super().__init__(clock_domains=clock_domains)
        
        # Set pstate to passive
        self._set_pstate_status("passive")

        # Disable thermald service
        if self.__disable_thermald:
            self._disable_thermald()
        

    def set_cpu_freq(self, core: int, frequency_mhz: float):
        ...
    
    def get_cpu_freq(self, core: int) -> float:
        ...

    def _read_msr(self, core: int, msr: int) -> int | None:
        msr_file = f"/dev/cpu/{core}/msr"
        try:
            with open(msr_file, 'rb') as f:
                f.seek(msr)
                value = f.read(8)
                return struct.unpack('Q', value)[0]
        except IOError as e:
            print(f"Error reading MSR {msr:#x} on core {core}: {e}")
            return None

    def _write_msr(self, core: int, msr: int, value: int):
        msr_file = f"/dev/cpu/{core}/msr"
        try:
            with open(msr_file, 'wb') as f:
                f.seek(msr)
                f.write(struct.pack('Q', value))
        except IOError as e:
            print(f"Error writing MSR {msr:#x} on core {core}: {e}")

    def _set_pstate(self, core: int, pstate: int):        
        hwp_request = (
            (pstate & 0xFF) |                    # Minimum Performance
            ((pstate & 0xFF) << 8) |             # Maximum Performance
            #((pstate & 0xFF) << 16) |            # Desired Performance
            ((0x80 & 0xFF) << 24)                # Energy Performance Preference
        )
        self._write_msr(core, self.IA32_HWP_REQUEST, hwp_request)

    @staticmethod
    def _parse_hwp_capabilities(result: int) -> dict[str, int]:
        return {
            "Highest_Performance" : result & 0xFF,
            "Guaranteed_Performance" : result >> 8 & 0xFF,
            "Most_Efficient_Performance" : result >> 16 & 0xFF,
            "Lowest_Performance" : result >> 24 & 0xFF
        }
    
    @staticmethod
    def _parse_hwp_request(result: int) -> dict[str, int]:
        return {
            "Minimum_performance" : result & 0xFF,
            "Maximum_performance" : result >> 8 & 0xFF,
            "Desired_performance" : result >> 16 & 0xFF,
            "Energy_performance_preference" : result >> 24 & 0xFF
        }
    
    def _get_pstate_status(self) -> str | None:
        """Reads the current status of the intel_pstate driver (active, passive, or off)"""
        pstate_status_path = "/sys/devices/system/cpu/intel_pstate/status"
        try:
            with open(pstate_status_path, 'r') as f:
                status = f.read().strip()
                return status
        except IOError as e:
            print(f"Failed to read intel_pstate status: {e}")
            return None
        
    def _set_pstate_status(self, status: str):
        pstate_status_path = "/sys/devices/system/cpu/intel_pstate/status"
        try:
            with open(pstate_status_path, 'w') as f:
                f.write(status)
        except IOError as e:
            print(f"Failed to set intel_pstate status: {e}")

    def _disable_thermald(self):
        command = ['sudo', 'systemctl', 'stop', 'thermald']
        try:
            subprocess.run(command, check=True)
            print("thermald service stopped")
        except subprocess.CalledProcessError as e:
            print(f"Failed to stop thermald service: {e}")

    def _enable_thermald(self):
        command = ['sudo', 'systemctl', 'start', 'thermald']
        try:
            subprocess.run(command, check=True)
            print("thermald service started")
        except subprocess.CalledProcessError as e:
            print(f"Failed to start thermald service: {e}")

    def restore_initial_state(self):
        super().restore_initial_state()
        # Re-enable thermald service if it was disabled
        if self.__disable_thermald:
            self._enable_thermald()

    def _print_core_stats(self, core: int):
        print(f"Core: {core}")
        print(f"Scaling driver: {self.get_scaling_driver(core)}")
        print(f"Current governor: {self.get_governor(core)}")
        
        scaling_min_khz, scaling_max_khz = self.get_scaling_limits(core)
        print(f"Scaling_Min: {scaling_min_khz/1000:.1f} MHz, Scalin_Max: {scaling_max_khz/1000:.1f} MHz")

        cpu_min_khz, cpu_max_khz = self.get_processor_limits(core)
        print(f"CPU_Min: {cpu_min_khz / 1000 :.1f} MHz, CPU_Max: {cpu_max_khz / 1000 :.1f} MHz")
        
        if hwp_capabilities := freq_manager._read_msr(core, IntelFrequencyManager.IA32_HWP_CAPABILITIES):
            cap = freq_manager._parse_hwp_capabilities(hwp_capabilities)
            print(cap)

        if hwp_request := freq_manager._read_msr(core, IntelFrequencyManager.IA32_HWP_REQUEST):
            print(freq_manager._parse_hwp_request(hwp_request))

        print(f"Available governors: {self.get_available_governors(core)}")

if __name__ == "__main__":
    from config import clock_domains
    freq_manager = IntelFrequencyManager(clock_domains=clock_domains)
    
    freq_manager._print_core_stats(0) # type: ignore
    
    #print(freq_manager.get_governor(2))
    #print(freq_manager.get_available_governors(2))
    #freq_manager.set_governor(16, "userspace")
    #freq_manager.set_governor(17, "userspace")
    #freq_manager.set_governor(18, "userspace")
    #freq_manager.set_governor(19, "userspace")
    #freq_manager.set_governor(3, "userspace")
    
    if False:
        p_state = 12
        freq_manager._set_pstate(3, p_state)
        freq_manager._set_pstate(2, p_state)
    #freq_manager.set_scaling_limits(2, 1000, 2000)
    #freq_manager.set_scaling_limits(3, 1000, 2000)

    #freq_manager._print_core_stats(2)
    if False:
        freq = 2000 
        freq_manager.set_scaling_limits(16, freq, freq)
        freq_manager.set_scaling_limits(17, freq, freq)
        freq_manager.set_scaling_limits(18, freq, freq)
        freq_manager.set_scaling_limits(19, freq, freq)
        #freq_manager.set_scaling_limits(3, freq, freq)
    
    #freq_manager._print_core_stats(16)
    #freq_manager._print_core_stats(17)
    #freq_manager._print_core_stats(18)
    #freq_manager._print_core_stats(19)
    #print()
    #freq_manager._print_core_stats(3)