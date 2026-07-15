from abc import ABC, abstractmethod
from ardis.config import system_cores
from ardis.core.system_state import SystemState
from ardis.benchmarks.application import Application

class MappingPolicy(ABC):
    def __init__(self, available_cores: set[int] = set(range(system_cores))):
        self._mapping: dict[Application, set[int]] = {}
        self._available_cores: set[int] = available_cores
    
    #def executeMapping(self, applications: list[Application]) -> dict[Application, set[int]]:
    #    # default mapping: next available core
    #    for app in applications:
    #        for core in range(system_cores):
    #            if core not in self.__used_cores:
    #                self.__used_cores.add(core)
    #                self.mapping[app] = {core}
    #                break
    #    return self.mapping
    
    @abstractmethod
    def register_workload(self, workload: list[Application]) -> None:
        """
        This method is called by the engine before the workload is executed.
        It allows the mapping policy to prepare for the workload, e.g., by precomputing a mapping.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def get_mapping(self, application: Application, system_state: SystemState) -> set[int]:
        """
        Return the set of cores to which the application should be mapped.
        """
        raise NotImplementedError("Subclasses must implement this method.")


class NextAvailableCoreMapping(MappingPolicy):
    
    def __init__(self, available_cores: list[int]):
        super().__init__(set(available_cores))
        self._prefered_order = list(available_cores)

    def register_workload(self, workload: list[Application]) -> None:
        # No precomputation needed for this simple mapping policy
        return

    def get_mapping(self, application: Application, system_state: SystemState) -> set[int]:
        
        required_core = 1 # Currently, we assume that each application requires only one core. This can be extended in the future.

        mapping : set[int] = set()
        occupied_cores = system_state.occupied_cores

        for core in self._prefered_order:
            if core in occupied_cores:
                continue
            mapping.add(core)
            if len(mapping) == required_core:
                break

        return self._mapping[application]

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