from abc import ABC, abstractmethod
from ardis.config import system_cores
from ardis.core.system_state import SystemState
from ardis.benchmarks.application import Application

class MappingException(Exception):
    """Exception raised when the system is full and a new application cannot be mapped."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class MappingPolicy(ABC):
    def __init__(self, available_cores: set[int] = set(range(system_cores))):
        self._mapping: dict[Application, set[int]] = {}
        self._available_cores: set[int] = available_cores
    
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
        Raise a MappingException if the system is full and the application cannot be mapped.
        """
        raise NotImplementedError("Subclasses must implement this method.")


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