from collections import deque

from ardis.core.actions import MigrationAction
from ardis.core.actions import DVFSAction

class ActionBuffer:
    """
    Simple deque based buffer to temporary store the resource management actions, that have been applied.
    """
    def __init__(self, capacity: int) -> None:
        self.__migr_action_deque: deque[tuple[int, list[MigrationAction]]] = deque(maxlen=capacity)
        self.__dvfs_action_deque: deque[tuple[int, list[DVFSAction]]] = deque(maxlen=capacity)

    def push_migration_actions(self, epoch: int, actions: list[MigrationAction]) -> None:
        self.__migr_action_deque.append((epoch, actions))

    def push_dvfs_actions(self, epoch: int, actions: list[DVFSAction]) -> None:
        self.__dvfs_action_deque.append((epoch, actions))

    def get_migration_actions(self, epoch: int) -> list[MigrationAction] | None:
        """
        Returns a list of migration actions that where applied in the given epoch. 
        Returns None if no migration actions occured in this epoch.
        """
        for e, actions in self.__migr_action_deque:
            if e == epoch:
                return actions
        return None
    
    def get_dvfs_actions(self, epoch: int) -> list[DVFSAction] | None:
        """
        Returns a list of dvfs actions that where applied in the given epoch. 
        Returns None if no dvfs actions occured in this epoch.
        """
        for e, actions in self.__dvfs_action_deque:
            if e == epoch:
                return actions
        return None