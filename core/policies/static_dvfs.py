from config import system_cores
from core.dvfs import DVFSPolicy, DVFSAction
from core.system_state import SystemState

class StaticDVFS(DVFSPolicy):
    """
    Simple DVFS Policy that staticly assigns the governor and the core frequencies.
    Calls to `get_dvfs_actions` will always return an empty [].
    This class is required, beacaue the base class DVFSPolicy is abstract.
    """
    def __init__(
        self,
        core_frequencies: dict[int, int] = { core: 2000 for core in range(system_cores) },
        min_frequency: int = 1500,
        max_frequency: int = 3500,
        governor: str = "userspace",
    ) -> None:
        super().__init__(core_frequencies, min_frequency, max_frequency, governor)

    def get_dvfs_actions(self, system_state: SystemState) -> list[DVFSAction]:
        return []