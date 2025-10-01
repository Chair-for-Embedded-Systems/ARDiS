import subprocess

from abc import ABC, abstractmethod

from ardis.core.actions import MigrationAction
from ardis.core.system_state import SystemState
from ardis.benchmarks.application import Application

class MigrationPolicy(ABC):

    @abstractmethod
    def get_migration_actions(self, system_state: SystemState) -> list[MigrationAction]:
        """
        Returns a list of migration actions, based on the provided system state.
        """
        raise NotImplementedError
    
    @staticmethod
    def apply_migration_actions(
        actions: list[MigrationAction],
        app_to_pid: dict[Application, int],
        app_to_cores: dict[Application, set[int]],
    ) -> None:
        """
        Applys the given list of migration actions. The passed in dict `app_to_cores` will be modified.
        """
        for action in actions:
            pid = app_to_pid[action.app]
            if MigrationPolicy._setAffinity(pid, action.destination):
                app_to_cores[action.app] = action.destination
            else:
                print("[Migration Policy] Migration failed. Maybe the application has not started yet.")
    
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
        try:
            p = subprocess.Popen(command,  stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            if p.stderr and p.stderr.readlines():
                return False
            else:
                p.wait()
                return True
        except:
            return False