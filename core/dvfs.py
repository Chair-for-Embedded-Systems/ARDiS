from abc import ABC, abstractmethod

from config import system_cores
from core.actions import DVFSAction
from core.system_state import SystemState
from core.cpu.frequency_manager import CPUFrequencyManager

class DVFSPolicy(ABC):
    def __init__(
        self,
        core_frequencies: dict[int, int] = {core: 2000 for core in range(system_cores)},
        min_frequency: int = 1500, 
        max_frequency: int = 3500, 
        governor: str = "userspace"
    ) -> None:
        
        self.manager : CPUFrequencyManager = CPUFrequencyManager(
            clock_domains=[{core for core in range(system_cores)}]
        )
        self.__core_frequencies = core_frequencies
        
        if governor == "userspace":
            for core in self.manager.cores:
                self.manager.set_governor(core, governor)
                self.manager.set_cpu_freq(core, core_frequencies[core])
        else:
            for core in self.manager.cores:
                self.manager.set_governor(core, governor)
                self.manager.set_scaling_limits(core, min_frequency, max_frequency)

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
