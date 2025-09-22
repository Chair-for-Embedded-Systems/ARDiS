import subprocess
from core.cpu.frequency_manager import CPUFrequencyManager
from core.cpu.intel.hwp_interface import IntelHWPInterface, HWPRequest

class IntelFrequencyManager(CPUFrequencyManager):
    
    INTEL_TURBO_PATH = "/sys/devices/system/cpu/intel_pstate/no_turbo"
    INTEL_P_STATE_STATUS_PATH = "/sys/devices/system/cpu/intel_pstate/status"
    
    """
    Frequency manager for Intel CPUs using the intel_pstate driver.
    - `disable_thermald`: If True, stops the thermald service to prevent interference with manual frequency management.
    - `bypass_scaling_driver`: If True, utilizes Intels Hardware P-States (HWP) interface for frequency management. This also allows setting p-states directly.
    """
    def __init__(
        self,
        clock_domains: list[set[int]],
        disable_thermald: bool = True,
        bypass_scaling_driver: bool = False,
    ) -> None:
        
        self.__bypass_scaling_driver = bypass_scaling_driver
        self.__initial_hwp_requests: dict[int, HWPRequest] | None = None
        self.__disable_thermald = disable_thermald
        super().__init__(clock_domains=clock_domains)
        
        # Initialize HWP interface if desired
        if self.__bypass_scaling_driver:
            self._hwp_interface = IntelHWPInterface()
            self._save_hwp_state()

        # Set intel_pstate scaling driver to passive
        self._set_pstate_status("passive")

        # Make sure boost is enabled (access to larger frequency range)
        self._initial_boost_state = self.get_boost_state()
        self._set_boost_state(True)

        # Disable thermald service
        if self.__disable_thermald:
            self._disable_thermald()
        

    def set_cpu_freq(self, core: int, frequency_mhz: int):
        
        if not self.__bypass_scaling_driver:
            # The default implementation which uses `scaling_setspeed` does not work with intel_pstate.
            # (See https://www.kernel.org/doc/Documentation/cpu-freq/intel-pstate.txt)
            # Instead we adjust both limits (scaling_min_freq and scaling_max_freq) to achieve the desired frequency.
            # The driver converts the requested frequency to the closest available p-state and then writes it to the MSR of the CPU.
            frequency_khz = frequency_mhz * 1000
            for affected_core in self.affected_cores(core):
                super().set_scaling_limits(
                    core=affected_core,
                    min_freq_khz=frequency_khz,
                    max_freq_khz=frequency_khz
                )
        else:
            # Here we are doing the exact same as the scaling driver would do internally.
            if p_state := self._frequency_to_pstate(core, frequency_mhz):
                self.set_pstate(core, p_state)
            else:
                raise ValueError(f"Cannot map frequency {frequency_mhz} MHz to a p-state")

    def get_cpu_freq(self, core: int) -> float:
        # The default implementation which reads from scaling_cur_freq is sufficient
        return super().get_cpu_freq(core)

    def set_pstate(self, core: int, pstate: int):
        """
        Sets the p-state for the specified core and all cores in its clock domain.
        Requires scaling driver bypass to be enabled.
        """
        if not self.__bypass_scaling_driver:
            raise RuntimeError("Cannot set p-state when scaling driver bypass is disabled")

        for affected_core in self.affected_cores(core):
            self._hwp_interface.set_p_state(affected_core, pstate)

    def _frequency_to_pstate(self, core: int, frequency_mhz: int) -> int | None:
        """
        Maps a frequency in MHz to the closest corresponding p-state.
        """
        # Its difficult to solve this generally, as the formula depends on the specific CPU model (different scaling factors).
        # Additionally the mapping is not linear.
        # Fortunatly we can use the scaling driver if we are only interested in setting frequencies.
        raise NotImplementedError("Mapping frequency to p-state is not implemented yet")

    def _get_pstate_status(self) -> str | None:
        """Reads the current status of the intel_pstate driver (active, passive, or off)"""
        try:
            with open(self.INTEL_P_STATE_STATUS_PATH, 'r') as f:
                status = f.read().strip()
                return status
        except IOError as e:
            print(f"Failed to read intel_pstate status: {e}")
            return None
        
    def _set_pstate_status(self, status: str):
        """Sets the status of the intel_pstate driver (active, passive, or off)"""
        try:
            with open(self.INTEL_P_STATE_STATUS_PATH, 'w') as f:
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

    def get_boost_state(self) -> bool | None:
        try:
            with open(self.INTEL_TURBO_PATH, 'r') as f:
                boost_state = f.read().strip()
                return boost_state == "0"  # Note: no_turbo=0 means turbo is enabled
        except IOError as e:
            print(f"Failed to read intel_pstate no_turbo state: {e}")
            return None
        
    def _set_boost_state(self, enable: bool) -> None:
        try:
            with open(self.INTEL_TURBO_PATH, 'w') as f:
                f.write("0" if enable else "1")  # no_turbo=0 means turbo is enabled
        except IOError as e:
            print(f"Failed to set intel_pstate no_turbo state: {e}")

    def _save_hwp_state(self):
        if not self.__bypass_scaling_driver:
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
        if self.__bypass_scaling_driver and self.__initial_hwp_requests:
            for core, hwp_request in self.__initial_hwp_requests.items():
                self._hwp_interface.set_hwp_request(core, hwp_request)

        # Restore initial governors and scaling ranges
        super().restore_initial_state()

        # Restore initial boost state if it was changed
        if self._initial_boost_state is not None:
            self._set_boost_state(self._initial_boost_state)