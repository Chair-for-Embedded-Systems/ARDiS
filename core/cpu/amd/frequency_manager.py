from core.cpu.frequency_manager import CPUFrequencyManager

class AMDFrequencyManager(CPUFrequencyManager):
    
    P_STATE_STATUS_PATH = "/sys/devices/system/cpu/amd_pstate/status"
    CPB_BOOST_PATH = "/sys/devices/system/cpu/amd_pstate/cpb_boost"
    
    def __init__(self, clock_domains: list[set[int]]):
        super().__init__(clock_domains)
        
        # Check if the scaling driver is amd-pstate
        scaling_driver = self.get_scaling_driver(core=0)
        if scaling_driver != "amd-pstate":
            raise EnvironmentError(f"AMD Frequency Manager requires 'amd-pstate' driver, found '{scaling_driver}' instead.")
        
        # Set scaling driver to passive
        self._set_pstate_status("passive")

        # Disable boosting (optional)
        self._set_boost_state(False)

    def set_cpu_freq(self, core: int, frequency_mhz: int):
        super().set_cpu_freq(core, frequency_mhz)

    def get_cpu_freq(self, core: int) -> float:
        return super().get_cpu_freq(core)

    def _get_pstate_status(self) -> str | None:
        """Reads the current status of the amd_pstate driver (active, passive, or off)"""
        try:
            with open(self.P_STATE_STATUS_PATH, 'r') as f:
                status = f.read().strip()
                return status
        except IOError as e:
            print(f"Failed to read amd_pstate status: {e}")
            return None
    
    def _set_pstate_status(self, status: str):
        """Sets the status of the amd_pstate driver (active, passive, or off)"""
        pstate_status_path = self.P_STATE_STATUS_PATH
        try:
            with open(pstate_status_path, 'w') as f:
                f.write(status)
        except IOError as e:
            print(f"Failed to set amd_pstate status: {e}")

    def get_boost_state(self) -> bool | None:
        try:
            with open(self.CPB_BOOST_PATH, 'r') as f:
                boost_state = f.read().strip()
                return boost_state == "1"
        except IOError as e:
            print(f"Failed to read cpb_boost state: {e}")
            return None

    def _set_boost_state(self, enable: bool) -> None:
        try:
            with open(self.CPB_BOOST_PATH, 'w') as f:
                f.write("1" if enable else "0")
        except IOError as e:
            print(f"Failed to set cpb_boost state: {e}")
