from utils.inteldvfs import *

class DVFSPolicy():
    def __init__(self, debug=False):
        self.__debug = debug
        self.manager = CPUFrequencyManager(self.__debug)

    def setInitialFrequency(self, cores, frequency):
        for core in cores:
            self.manager.setFrequency(core, frequency)
            if self.__debug:
                print(f"Core {core} set to {frequency} MHz")
    
    def executeDVFSPolicy(self, cores, frequency):
        pass

