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


    ##def getShuffledMapping(self, mapping):
    ##    tmp_mapping = mapping.copy()
    ##    available_cores = list(mapping.values())
    ##    random.shuffle(available_cores)
    ##    for app in mapping:
    ##        tmp_mapping[app] = available_cores.pop()
    ##    return tmp_mapping
    ##
    ##def getFixedMapping(self, mapping):
    ##    tmp_mapping = mapping.copy()
    ##    ctr = 2
    ##    for app in mapping:
    ##        tmp_mapping[app] = ctr
    ##        ctr += 2
    ##    return tmp_mapping
    ##
    ##def getRandomMapping(self, mapping):
    ##    tmp_mapping = mapping.copy()
    ##    available_cores = list(range(2, config.system_cores))
    ##    random.shuffle(available_cores)
    ##    for app in mapping:
    ##        tmp_mapping[app] = available_cores.pop()
    ##    return tmp_mapping