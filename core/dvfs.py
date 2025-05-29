from abc import ABC, abstractmethod

from utils.inteldvfs import *
from config import *
from core.actions import DVFSAction
from core.system_state import SystemState

class DVFSPolicy(ABC):
    def __init__(
        self,
        core_frequencies: dict[int, int] = {core: 2000 for core in range(system_cores)},
        min_frequency: int = 1500, 
        max_frequency: int = 3500, 
        governor: str = "userspace"
    ) -> None:
        self.manager = CPUFrequencyManager(min_frequency, max_frequency, governor)
        self.__core_frequencies = core_frequencies
        if governor == "userspace":
            self.__setInitialFrequencies()

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
            self.manager.setFrequency(action.core_id, action.frequency_mhz)
            self.__core_frequencies[action.core_id] = action.frequency_mhz

    def getCoreFrequencies(self) -> dict[int, int]:
        """
        Returns a dictionary that maps each core to a frequency.
        It does not contain the actual frequency, but rather the last requested.
        """
        return self.__core_frequencies

    def __setInitialFrequencies(self):
        for core in self.__core_frequencies.keys():
            self.manager.setFrequency(core, self.__core_frequencies[core])
            if DEBUG:
                print(f"Core {core} set to {self.__core_frequencies[core]} MHz")