from abc import ABC, abstractmethod

import config
from core.actions import DVFSAction
from core.system_state import SystemState
from core.cpu import CPUFrequencyManager, get_platform_frequency_manager

class DVFSPolicy(ABC):
    """
    Abstract base class for DVFS policies.

    The parameters in the constructor define the initial state of the policy.
    Either `core_to_freq` or `governor` can be specified, but not both.

    - `core_to_freq_mhz`: A dictionary mapping each core to a fixed frequency in MHz.
    - `governor`: A tuple (governor_name, min_freq, max_freq) specifying the governor and its frequency limits.

    **Note**:
    raises ValueError if both `core_to_freq` and `governor` are specified, 
    raises ValueError if `core_to_freq` does not specify a frequency for every core
    """
    def __init__(
        self,
        core_to_freq_mhz: dict[int, int] | None = None,
        governor: tuple[str, int, int] | None = None,
        cpu_freq_manager: CPUFrequencyManager | None = None,
    ) -> None:
        # Prevent invalid argument combinations
        if core_to_freq_mhz and governor:
            raise ValueError("Cannot specify both core_to_freq and governor")
        
        # Ensure all cores have a specified frequency if `core_to_freq_mhz` is provided
        if core_to_freq_mhz:
            unassigned_cores = [core for core in range(config.system_cores) if core not in core_to_freq_mhz]
            if unassigned_cores:
                raise ValueError(f"All cores must have a specified frequency. Unassigned cores: {unassigned_cores}")
        
        # Save initial configuration for later application
        self.__initial_governor = governor
        self.__initial_core_to_freq = core_to_freq_mhz
        self.__core_frequencies: dict[int, int] = dict()

        # Initialize a CPU frequency manager if none provided
        if cpu_freq_manager is None:
            self.cpu_freq_manager = get_platform_frequency_manager()

    def apply_initial_state(self) -> None:
        """
        Applies the initial state of this policy.
        This is called once at the beginning of a workload by the engine.
        Depending on how the policy was constructed, this is either setting fixed frequencies for each core,
        or setting a governor with min/max frequencies for all cores.
        Derived policies can override this method if they need to perform additional setup.
        """
        if self.__initial_core_to_freq:
            for core, freq_mhz in self.__initial_core_to_freq.items():
                self.cpu_freq_manager.set_governor(core, "userspace")
                self.cpu_freq_manager.set_cpu_freq(core, freq_mhz)
            return
        elif self.__initial_governor:
            governor, min_freq_mhz, max_freq_mhz = self.__initial_governor
            min_freq_khz = min_freq_mhz * 1000
            max_freq_khz = max_freq_mhz * 1000
            for core in self.cpu_freq_manager.cores:
                self.cpu_freq_manager.set_governor(core, governor)
                self.cpu_freq_manager.set_scaling_limits(core, min_freq_khz, max_freq_khz)
            return
        else:
            print("[DVFS Policy] No initial state to apply")

    @abstractmethod
    def get_dvfs_actions(self, system_state: SystemState) -> list[DVFSAction]:
        """
        Returns a list of DVFS actions, based on the provided system state
        If no action should be taken, an empty list is returned
        """
        raise NotImplementedError
    
    def apply_dvfs_actions(self, actions: list[DVFSAction]) -> None:
        """
        Applies the given list of dvfs actions.
        """
        for action in actions:
            self.cpu_freq_manager.set_cpu_freq(action.core_id, action.frequency_mhz)
            self.__core_frequencies[action.core_id] = action.frequency_mhz

    def getCoreFrequencies(self) -> dict[int, int]:
        """
        Returns a dictionary that maps each core to a frequency.
        It does not contain the actual frequency, but rather the last requested.
        """
        return self.__core_frequencies
