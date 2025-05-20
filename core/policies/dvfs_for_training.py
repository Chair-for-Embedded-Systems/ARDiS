import random
from core.dvfs import *
import sys, os

from core.dvfs import DVFSAction
from core.actions import MigrationAction, DVFSAction
from core.system_state import SystemState

# Import the configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
import config

class DVFSForTraining(DVFSPolicy):
    def __init__(self, core_frequencies = {core: 2000 for core in range(config.system_cores)}, min_frequency=1500, max_frequency=3500, governor="userspace"):
        super().__init__(core_frequencies, min_frequency, max_frequency, governor)
    
    #def executeDVFSPolicy(self, new_core_frequencies):
    #    if config.DEBUG:
    #        print("######### New Frequencies: ", new_core_frequencies)
    #    for core in new_core_frequencies.keys():
    #        self.manager.setFrequency(core, new_core_frequencies[core])
    #        if config.DEBUG:
    #            print(f"Core {core} set to {new_core_frequencies[core]} MHz")
    #    self.__core_frequencies = new_core_frequencies

    def get_dvfs_actions(self, system_state: SystemState) -> list[DVFSAction]:
        
        if action_buffer := system_state.action_buffer:
            migrations = action_buffer.get_migration_actions(system_state.epoch)
            
            if not migrations:
                return []
            
            dvfs_actions = []
            for migration in migrations:
                if len(migration.destination) == 1:
                    dvfs_action = DVFSAction(
                        core_id=next(iter(migration.destination)),
                        frequency_mhz=random.choice(range(1500, 3701, 200))
                    )
                    dvfs_actions.append(dvfs_action)
            return dvfs_actions

        return super().get_dvfs_actions(system_state)

