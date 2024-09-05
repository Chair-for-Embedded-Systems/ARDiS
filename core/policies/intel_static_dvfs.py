from core.dvfs import *
import json
from config import *

class IntelStaticDVFSPolicy(DVFSPolicy):
    def __init__(self, static_schedules_path, core_frequencies=None):
        # If core_frequencies is not provided, use default
        if core_frequencies is None:
            core_frequencies = {core: 2000 for core in range(system_cores)}
        
        # Pass the core_frequencies to the parent class's __init__ method
        super().__init__(core_frequencies)
        self.static_schedules = self.load_static_schedules(static_schedules_path)
    
    def load_static_schedules(self, schedule_file):
        with open(schedule_file, 'r') as file:
            return json.load(file)
         
    def executeDVFSPolicy(self, instructions, mapping):
        tmp_mapping = mapping.copy()
        
        for app in tmp_mapping:
            # Get the static schedule for the current app
            static_schedule = self.static_schedules.get(app, [])
            
            # Default to current core and frequency
            selected_core = tmp_mapping[app]
            selected_vf_level = None  # Initialize as None to check later
            current_phase = None
            # Iterate through the schedule phases to determine the correct core and frequency
            for entry in static_schedule:
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
                self.manager.setFrequency(selected_core, selected_vf_level)
                print(f"[DVFS Policy] Now entering Phase: {current_phase}, "
                          f"Core: {selected_core}, Frequency: {selected_vf_level} MHz")