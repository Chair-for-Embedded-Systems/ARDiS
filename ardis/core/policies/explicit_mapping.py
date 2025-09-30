from ardis.core.mapping import *
from ardis.config import *


#Let the mapping come from a list of cores
class ExplicitMapping(MappingPolicy):
    def __init__(self, cores: list[set[int]]):
        super().__init__()

        # Check if provided mapping is disjunct (core monitoring requires this assumption)
        if len(set.union(*cores)) != sum(len(c) for c in cores):
            raise ValueError(f"Mappings must be disjunct {cores}")

        self.__cores = cores

    @classmethod
    def from_list(cls, cores: list[int]):
        """
        Constructs the mapping from a list of cores, were each applications gets assigned a single core.
        (This represents the old behaviour)
        """
        cores_set = [{core} for core in cores]
        return cls(cores_set)
    
    @classmethod
    def from_config(cls):
        """
        Constructs the mapping based on the values provided in the configuration.
        """
        return cls([{core} for core in explicit_mapping_cores])

    def executeMapping(self, applications):
        
        if len(applications) > len(self.__cores):
            raise ValueError("More applications than explicit mappings")

        for i, app in enumerate(applications):
            self.mapping[app] = self.__cores[i]

        return self.mapping