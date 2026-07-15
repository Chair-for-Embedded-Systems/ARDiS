from ardis.core.dvfs import DVFSPolicy, DVFSAction
from ardis.config import *
from ardis.core.system_state import SystemState

class IntelStaticDVFSPolicy(DVFSPolicy):
    def __init__(self, static_schedule, core_frequencies=None):
        # If core_frequencies is not provided, use default
        if core_frequencies is None:
            core_frequencies = {core: 2000 for core in range(system_cores)}
        
        # Pass the core_frequencies to the parent class's __init__ method
        super().__init__(core_frequencies)
        self.static_schedule = static_schedule
        raise NotImplementedError("IntelStaticDVFS policy is currently broken")

    def get_dvfs_actions(self, system_state: SystemState) -> list[DVFSAction]:
        raise NotImplementedError
    
    def executeDVFSPolicy(self, instructions, mapping):
        tmp_mapping = mapping.copy()
        
        for app in tmp_mapping:
            # Get the static schedule for the current app
            # Default to current core and frequency
            selected_core = tmp_mapping[app]
            selected_vf_level = None  # Initialize as None to check later
            current_phase = None
            # Iterate through the schedule phases to determine the correct core and frequency
            for entry in self.static_schedule:
                if instructions >= entry["trigger_instruction"]:
                    # Map "E-core" and "P-core" to actual core IDs from your system
                    if entry["core"] == "E-core":
                        selected_core = intel_e_core_ids[0]
                    elif entry["core"] == "P-core":
                        selected_core = intel_p_core_ids[3]
                    current_phase = entry["phase"]
                    # Set the selected frequency level from the schedule
                    selected_vf_level = entry["frequency"]
                else:
                    break  # Stop once the correct phase is determined

            # If a valid frequency was found, set it for the selected core
            if selected_vf_level is not None:
                self.cpu_freq_manager.set_cpu_freq(selected_core, selected_vf_level)
                
                if DEBUG:
                    print(f"[DVFS Policy] Now entering Phase: {current_phase}, "
                          f"Core: {selected_core}, Frequency: {selected_vf_level} MHz")