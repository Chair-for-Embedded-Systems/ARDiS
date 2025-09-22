import random
from core.dvfs import *
import sys, os

from core.dvfs import DVFSAction
from core.actions import DVFSAction
from core.system_state import SystemState

# Import the configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
import config

class DVFSForTraining(DVFSPolicy):
    """
    This DVFS policy adjusts the frequency of a core, whenever an application was migrated to it.
    The frequency is randomly picked, based on the provided ranges in the constructor of this class.
    """
    def __init__(
        self,
        core_frequencies: dict[int , int] = {core: 2000 for core in range(config.system_cores)},
        p_core_range: list[int] = list(range(1800, 3201, 200)),
        e_core_range: list[int] = list(range(1800, 3201, 200)),
        p_cores: set[int] = set(config.intel_p_core_ids),
        e_cores: set[int] = set(config.intel_e_core_ids)
    ) -> None:
        super().__init__(core_to_freq_mhz=core_frequencies)
        self._pcore_range = p_core_range
        self._ecore_range = e_core_range
        self._p_cores = p_cores
        self._e_cores = e_cores
    
    def get_dvfs_actions(self, system_state: SystemState) -> list[DVFSAction]:
        
        # Get migration actions of the current epoch
        # This assumes, that migration actions are applied before dvfs actions (see engine)
        migration_actions = system_state.action_buffer.get_migration_actions(system_state.epoch)
            
        # No migration happend in this epoch -> No DVFS Action 
        if not migration_actions:
            return []
            
        dvfs_actions = []
        for mig_action in migration_actions:
            # Exclude apps that are multicore mapped
            if len(mig_action.destination) != 1:
                continue

            for core in mig_action.destination:        
                
                if core in self._p_cores:
                    freq_range = self._pcore_range
                elif core in self._e_cores:
                    freq_range = self._ecore_range
                else:
                    raise ValueError(f"Unknown core ({core})")
                
                dvfs_action = DVFSAction(core_id=core, frequency_mhz=random.choice(freq_range))
                dvfs_actions.append(dvfs_action)
                    
        return dvfs_actions
