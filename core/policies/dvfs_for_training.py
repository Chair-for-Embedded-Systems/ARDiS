from core.dvfs import *
import sys, os

# Import the configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
import config

class DVFSForTraining(DVFSPolicy):
    def __init__(self, core_frequencies = {core: 2000 for core in range(config.system_cores)}, min_frequency=1500, max_frequency=3500, governor="userspace"):
        super().__init__(core_frequencies, min_frequency, max_frequency, governor)
    
    def executeDVFSPolicy(self, new_core_frequencies):
        if config.DEBUG:
            print("######### New Frequencies: ", new_core_frequencies)
        for core in new_core_frequencies.keys():
            self.manager.setFrequency(core, new_core_frequencies[core])
            if config.DEBUG:
                print(f"Core {core} set to {new_core_frequencies[core]} MHz")
        self.__core_frequencies = new_core_frequencies

