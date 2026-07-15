from abc import ABC, abstractmethod
from ardis.benchmarks.application import Application
from ardis.core.system_state import SystemState

class Scheduler(ABC):

    @abstractmethod
    def register_workload(self, workload: list[Application]):
        """
        This method is called by the engine before the workload is executed.
        It allows the scheduler to prepare for the workload, e.g., by precomputing a schedule or validating its parameters.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def is_time_to_launch(self, application: Application, system_state: SystemState) -> bool:
        raise NotImplementedError("Subclasses must implement this method.")
    