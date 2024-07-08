from config import *

class MappingPolicy():
    def __init__(self):
        self.__used_cores = []
        self.mapping = {}
    
    def executeMapping(self, applications):
        # default mapping: next available core
        for app in applications:
            for core in range(system_cores):
                if core not in self.__used_cores:
                    self.__used_cores.append(core)
                    self.mapping[app] = core
                    break
        return self.mapping
