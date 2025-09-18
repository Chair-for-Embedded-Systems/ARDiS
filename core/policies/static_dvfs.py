from __future__ import annotations
from config import system_cores, clock_domains
from core.dvfs import DVFSPolicy, DVFSAction
from core.system_state import SystemState

class StaticDVFS(DVFSPolicy):
    """
    Simple DVFS Policy that staticly assigns core frequencies.
    Calls to `get_dvfs_actions` will always return an empty [].
    """
    def __init__(
        self,
        core_to_frequency_mhz: dict[int, int] = dict(),
        base_frequency_mhz: int = 2500,
    ) -> None:
        
        # core_to_frequency can be partial, we need to fill in the rest.
        
        # Initialize full mapping with base frequency
        core_to_freq_full = {core: base_frequency_mhz for core in range(system_cores)}
        
        # Update with specified frequencies, considering clock domains
        for core, freq in core_to_frequency_mhz.items():
            affected_cores = [c for domain in clock_domains if core in domain for c in domain]
            for affected_core in affected_cores:
                core_to_freq_full[affected_core] = freq

        super().__init__(core_to_freq_mhz=core_to_freq_full)

    def get_dvfs_actions(self, system_state: SystemState) -> list[DVFSAction]:
        return []
    
class StaticGovernorDVFS(DVFSPolicy):
    """
    Simple DVFS Policy that staticly assigns the governor and the min/max frequencies.
    Calls to `get_dvfs_actions` will always return an empty [].
    """
    def __init__(
        self,
        governor: str = "ondemand",
        min_frequency: int = 1500,
        max_frequency: int = 3500,
    ) -> None:
        super().__init__(governor=(governor, min_frequency, max_frequency))

    def get_dvfs_actions(self, system_state: SystemState) -> list[DVFSAction]:
        return []