from utils.inteldvfs import *
from config import *

from dataclasses import dataclass
from core.system_state import SystemState

@dataclass
class DVFSAction:
    core_id: int
    frequency_mhz: float

class DVFSPolicy():
    def __init__(self, core_frequencies = {core: 2000 for core in range(system_cores)}, min_frequency=1500, max_frequency=3500, governor="userspace"):
        self.manager = CPUFrequencyManager(min_frequency, max_frequency, governor)
        self.__core_frequencies = core_frequencies
        if governor == "userspace":
            self.__setInitialFrequencies()

    def __setInitialFrequencies(self):
        for core in self.__core_frequencies.keys():
            self.manager.setFrequency(core, self.__core_frequencies[core])
            if DEBUG:
                print(f"Core {core} set to {self.__core_frequencies[core]} MHz")
    
    def getCoreFrequencies(self):
        return self.__core_frequencies
    
    def executeDVFSPolicy(self, new_core_frequencies):
        pass

    def get_dvfs_actions(self, system_state: SystemState) -> list[DVFSAction]:
        return []
    
    def apply_dvfs_actions(self, actions: list[DVFSAction]) -> None:
        for action in actions:
            self.manager.setFrequency(action.core_id, action.frequency_mhz)
