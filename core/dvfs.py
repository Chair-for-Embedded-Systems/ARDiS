from utils.inteldvfs import *
from config import *

class DVFSPolicy():
    def __init__(self, core_frequencies = {core: 2000 for core in range(system_cores)}):
        self.manager = CPUFrequencyManager()
        self.__core_frequencies = core_frequencies 
        self.__setInitialFrequencies()

    def __setInitialFrequencies(self):
        for core in self.__core_frequencies.keys():
            self.manager.setFrequency(core, self.__core_frequencies[core])
            if DEBUG:
                print(f"Core {core} set to {self.__core_frequencies[core]} MHz")
    
    def executeDVFSPolicy(self, cores, frequency):
        pass

