from abc import ABC, abstractmethod

import config
from core.actions import DVFSAction
from core.system_state import SystemState
from core.cpu import CPUFrequencyManager, get_platform_frequency_manager

class DVFSPolicy(ABC):
    def __init__(
        self,
        core_frequencies: dict[int, int] = {core: 2000 for core in range(config.system_cores)},
        min_frequency: int = 1500, 
        max_frequency: int = 3500, 
        governor: str = "userspace"
    ) -> None:
        self.manager : CPUFrequencyManager = get_platform_frequency_manager()
        self.__core_frequencies = core_frequencies
        
        if governor == "userspace":

            # Validate that all cores have a specified frequency
            unassigned_cores = [core for core in self.manager.cores if core not in core_frequencies]
            if unassigned_cores:
                raise ValueError(f"All cores must have a specified frequency when using 'userspace' governor. Unassigned cores: {unassigned_cores}")

            for core in self.manager.cores:
                self.manager._set_governor(core, governor)
                self.manager.set_cpu_freq(core, core_frequencies[core])
        else:
            for core in self.manager.cores:
                self.manager._set_governor(core, governor)
                self.manager._set_scaling_limits(core, min_frequency, max_frequency)

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
            self.manager.set_cpu_freq(action.core_id, action.frequency_mhz)
            self.__core_frequencies[action.core_id] = action.frequency_mhz

    def getCoreFrequencies(self) -> dict[int, int]:
        """
        Returns a dictionary that maps each core to a frequency.
        It does not contain the actual frequency, but rather the last requested.
        """
        return self.__core_frequencies
