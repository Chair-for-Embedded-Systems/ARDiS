import subprocess

from abc import ABC, abstractmethod
from dataclasses import dataclass

from core.system_state import SystemState

@dataclass
class MigrationAction:
    app: str
    pid: int
    destination: set[int]
    source: set[int] | None

class MigrationPolicy(ABC):

    @abstractmethod
    def get_migration_actions(self, system_state: SystemState) -> list[MigrationAction]:
        """
        Returns a list of migration actions, based on the provided system state.
        """
        raise NotImplementedError
    
    @staticmethod
    def apply_migration_actions(actions: list[MigrationAction]) -> None:
        """
        Applys the given list of migration actions
        """
        for action in actions:
            MigrationPolicy._setAffinity(action.pid, action.destination)
    
    @staticmethod
    def _setAffinity(pid: int, cores: set[int]) -> bool:
        """
        Applies the given affinity to the given pid.
        Returns true if successfull otherwise false
        """
        affinity = ",".join([str(c) for c in cores])
        cmd_str = f"taskset -cpa {affinity} {pid}"
        command = cmd_str.split(" ")
        #print ("Executing: ", cmd_str)    
        p = subprocess.Popen(command,  stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        if p.stderr and p.stderr.readlines():
            return False
        else:
            p.wait()
            return True