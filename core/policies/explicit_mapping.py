from core.mapping import *
from config import *


#Let the mapping come from a list of cores
class ExplicitMapping(MappingPolicy):
    def __init__(self, cores = explicit_mapping_cores):
        super().__init__()
        self.__cores = cores

    def executeMapping(self, applications):
        c = 0
        for app in applications:
            self.mapping[app] = self.__cores[c]
            c += 1
        return self.mapping