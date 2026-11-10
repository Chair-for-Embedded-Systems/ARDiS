import os

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
        try:
            tids : list[int] = [int(f) for f in os.listdir(f"/proc/{pid}/task")]
        except OSError:
            # Target PID is no longer running, so we cannot set the affinity
            return False
        
        for tid in tids:
            try:
                os.sched_setaffinity(int(tid), cores)
            except (OSError, ValueError):
                # Ignore errors for child threads, as they may have already exited.
                # Only the main thread's affinity is critical.
                if tid == pid:
                    return False
    
        # Note for "Thread Monitoring": 
        # In a master/slave thread workload, an affinity change on the master thread may not appear immediately in the 'periodic_counters.log'
        # This is expected: ARDiS logs a thread's last_sched_cpu, which only updates when the thread is actually rescheduled
        return True