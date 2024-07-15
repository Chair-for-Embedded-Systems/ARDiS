from utils.intel_dvfs import *

class DVFSPolicy():
    def __init__(self, debug=False):
        self.__debug = debug
        self.__CPUFrequencyManager(self.__debug)

    def setInitialFrequency(self, cores, frequency):
        for core in cores:
            self.__CPUFrequencyManager.set_frequency(core, frequency)
            if self.__debug:
                print(f"Core {core} set to {frequency} MHz")
    def executeDVFSPolicy(self, cores, frequency):
        pass

