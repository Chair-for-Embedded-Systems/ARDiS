import os
from core.migration import *
import sys

# Import the configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config

class StaticScheduleMigration(MigrationPolicy):
    def __init__(self, static_schedule):
        super().__init__()
        self.static_schedule = static_schedule
    
    def executeMigration(self, currmap , newmap , pids):
        tmp_pids = pids.copy()
        #Only apply migration if the new map is different than current map
        #check each app for its new core
        for app in currmap:
            #if the app is still running, then move it to the new core
            #if setting the affinity fails, it means the app finished
            if pids[app] != -1:
                try:
                    self.__setAffinity(pids[app], newmap[app])
                    tmp_pids[app] = pids[app]
                #if the app finished, then set the pid to undefined (-1)
                except:
                    tmp_pids[app] = -1                 
        return tmp_pids
    
    def getNewMapping(self, instructions, mapping):
        tmp_mapping = mapping.copy()
        for app in tmp_mapping:
            selected_core = tmp_mapping[list(tmp_mapping.keys())[0]]  # Default to current core
            current_phase = None
            for entry in self.static_schedule:
                if instructions >= entry["trigger_instruction"]:
                    selected_core = config.intel_e_core_ids[0] if "E-core" in entry["core"] else config.intel_p_core_ids[3]
                    current_phase = entry["phase"]
                else:
                    break  # Stop once the correct phase is determined

            if tmp_mapping[app] != selected_core:
                tmp_mapping[app] = selected_core
                if config.DEBUG:
                    print("[Migration Policy] Now entering Phase: ", current_phase, "Core: ", selected_core)
        
        return tmp_mapping