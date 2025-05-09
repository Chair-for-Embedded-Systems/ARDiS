from config import *

class MappingPolicy():
    def __init__(self):
        self.__used_cores: set[int] = set()
        self.mapping: dict[str, set[int]] = {}
    
    def executeMapping(self, applications: list[str]) -> dict[str, set[int]]:
        # default mapping: next available core
        for app in applications:
            for core in range(system_cores):
                if core not in self.__used_cores:
                    self.__used_cores.add(core)
                    self.mapping[app] = {core}
                    break
        return self.mapping
