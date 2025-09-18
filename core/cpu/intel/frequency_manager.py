import subprocess
from core.cpu.frequency_manager import CPUFrequencyManager
from core.cpu.intel.hwp_interface import IntelHWPInterface, HWPRequest

class IntelFrequencyManager(CPUFrequencyManager):
    
    def __init__(
        self,
        clock_domains: list[set[int]],
        use_hwp: bool = True,
        disable_thermald: bool = True
    ) -> None:
        
        self.__use_hwp = use_hwp
        self.__initial_hwp_requests: dict[int, HWPRequest] | None = None
        self.__disable_thermald = disable_thermald
        super().__init__(clock_domains=clock_domains)
        
        # Initialize HWP interface if desired
        if self.__use_hwp:
            self._hwp_interface = IntelHWPInterface()
            self._save_hwp_state()

        # Set pstate to passive
        self._set_pstate_status("passive")

        # Disable thermald service
        if self.__disable_thermald:
            self._disable_thermald()
        

    def set_cpu_freq(self, core: int, frequency_mhz: int):
        if not self.__use_hwp:
            super().set_cpu_freq(core, frequency_mhz)
        else:
            p_state = self._frequency_to_pstate(core, frequency_mhz)
            if p_state is None:
                raise ValueError(f"Cannot map frequency {frequency_mhz} MHz to a p-state")
            else:
                self._set_pstate(core, p_state)
            return
            
    def get_cpu_freq(self, core: int) -> float:
        return super().get_cpu_freq(core)

    def _set_pstate(self, core: int, pstate: int):        
        for affected_core in self.affected_cores(core):
            self._hwp_interface.set_p_state(affected_core, pstate)

    def _frequency_to_pstate(self, core: int, frequency_mhz: int) -> int | None:
        """
        Maps a frequency in MHz to the closest corresponding p-state.
        """
        raise NotImplementedError("Mapping frequency to p-state is not implemented yet")

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
        """Sets the status of the intel_pstate driver (active, passive, or off)"""
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

    def _save_hwp_state(self):
        if not self.__use_hwp:
            return
        self.__initial_hwp_requests = dict()
        for core in self.cores:
            hwp_request = self._hwp_interface.get_hwp_request(core)
            if hwp_request:
                self.__initial_hwp_requests[core] = hwp_request

    def restore_initial_state(self):
        # Re-enable thermald service if it was disabled
        if self.__disable_thermald:
            self._enable_thermald()
        
        # Restore initial HWP requests
        if self.__use_hwp and self.__initial_hwp_requests:
            for core, hwp_request in self.__initial_hwp_requests.items():
                self._hwp_interface.set_hwp_request(core, hwp_request)
        
        super().restore_initial_state()