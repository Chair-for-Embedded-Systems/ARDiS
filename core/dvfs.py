from utils.inteldvfs import *

class DVFSPolicy():
    def __init__(self):
        self.manager = CPUFrequencyManager()

    def setInitialFrequency(self, cores, frequency):
        for core in cores:
            self.manager.setFrequency(core, frequency)
            if DEBUG:
                print(f"Core {core} set to {frequency} MHz")
    
    def executeDVFSPolicy(self, cores, frequency):
        pass

