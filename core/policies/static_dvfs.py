from __future__ import annotations
from config import system_cores, clock_domains
from core.dvfs import DVFSPolicy, DVFSAction
from core.system_state import SystemState

class StaticDVFS(DVFSPolicy):
    """
    Simple DVFS Policy that staticly assigns core frequencies.
    Calls to `get_dvfs_actions` will always return an empty [].
    
    Parameters
    ----------
    - core_to_frequency_mhz: dict[int, int]
        A dictionary mapping logical cores to their desired fixed frequencies in MHz.
        For cores which are part of a clock domain, it is sufficient to specify the frequency for any core in the domain.
    - base_frequency_mhz: int
        The default frequency in MHz for any core not explicitly listed in `core_to_frequency_mhz`.
        It is used when the frequency for a core is not specified.
    """
    def __init__(
        self,
        core_to_frequency_mhz: dict[int, int] = dict(),
        base_frequency_mhz: int = 2500,
    ) -> None:
        
        # Since core_to_frequency can be partial, we need to fill in the rest.
        # Initialize a complete dictionary which assign each core the base frequency
        core_to_freq_full = {core: base_frequency_mhz for core in range(system_cores)}
        
        # Update frequency of explicitly specified cores, taking clock domains into account
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