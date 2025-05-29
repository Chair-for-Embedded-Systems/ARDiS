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
    def __init__(self,
                core_frequencies = {core: 2000 for core in range(config.system_cores)},
                min_frequency=1500, max_frequency=3500,
                governor="userspace"
    ) -> None:
        super().__init__(core_frequencies, min_frequency, max_frequency, governor)
    
    def get_dvfs_actions(self, system_state: SystemState) -> list[DVFSAction]:
        
        # Get migration actions of the current epoch
        mig_actions = system_state.action_buffer.get_migration_actions(system_state.epoch)
            
        # No migration happend in this epoch -> No DVFS Action 
        if not mig_actions:
            return []
            
        dvfs_actions = []
        for migration in mig_actions:
            # Exclude apps that are multicore mapped
            if len(migration.destination) != 1:
                continue

            for core in migration.destination:        
                dvfs_action = DVFSAction(core_id=core, frequency_mhz=random.choice(range(1500, 3701, 200)))
                dvfs_actions.append(dvfs_action)
                    
        return dvfs_actions
