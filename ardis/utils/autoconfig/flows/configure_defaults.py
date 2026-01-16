from dataclasses import dataclass
import json
import subprocess
from .prompts import SimplePrompts

# Interactive prompt flow to configure some default values for experiments. This includes:
#     - action interval
#     - sampling rate
#     - periodic events (app-level and system-wide)
#     - one-shot events (system-wide)

# Use `python3 -m ardis.utils.autoconfig.flows.configure_defaults` to run this script directly.

@dataclass
class DefaultConfigurations:
    action_interval_sec: float
    sampling_interval_ms: int
    periodic_app_level_events: list[str]
    periodic_system_wide_events: list[str]
    one_shot_system_wide_events: list[str]

def __fetch_perf_event_list() -> list[str]:
    # Obtain list of valid perf events (run `perf list -j` command)
    process = subprocess.Popen(['perf', 'list', '-j'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        raise Exception(f"Failed to retrieve perf events: {stderr.strip()}")
    
    # Convert output to json and extract event names
    valid_events: list[str] = []
    try:
        json_data = json.loads(stdout)
        for event in json_data:
            if event.get('EventName'):
                valid_events.append(event['EventName'])
            if event.get('EventAlias'):
                valid_events.append(event['EventAlias'])
    except json.JSONDecodeError:
        raise Exception("Failed to parse perf list output as JSON.")
    
    # Remove duplicates and preserve order 
    valid_events = list(dict.fromkeys(valid_events))
    return valid_events

def _prompt_action_interval(default: float = 0.1) -> float:
    error_msg = ""
    while True:
        print("\033c", end="")
        if len(error_msg) > 0:
            print(f"Error: {error_msg}\n")
        try:
            print(
                "Config - Experiment Default Settings\n\n"
                "Set the action interval in seconds which determines how frequent the main control loop gets invoked.\n\n"
                "Enter a positive float value to set the action interval\n"
                "Leave empty for default value (0.1)"
            )
            value = input(f"\n>>> ")
            if value.strip() == "":
                return default
            interval = float(value)
            if interval <= 0:
                error_msg = "Please enter a positive number."
                continue
            return interval
        except ValueError:
            error_msg = "Invalid input. Please enter a numeric value."

def _prompt_sampling_interval(default: int = 100) -> int:
    error_msg = ""
    while True:
        print("\033c", end="")
        if len(error_msg) > 0:
            print(f"Error: {error_msg}\n")
        try:
            print(
                "Config - Experiment Default Settings\n\n"
                "Set the sampling interval in milliseconds which determines the duration of the periodic samples.\n\n"
                "Enter a positive integer value to set the sampling interval\n"
                "Leave empty for default value (100)"
            )
            value = input(f"\n>>> ")
            if value.strip() == "":
                return default
            interval = int(value)
            if interval <= 0:
                error_msg = "Please enter a positive integer."
                continue
            return interval
        except ValueError:
            error_msg = "Invalid input. Please enter an integer value."

def _prompt_periodic_app_level_events() -> list[str]:

    preset_one = ["instructions", "cycles", "branches", "branch-misses"]
    preset_two = ["instructions", "cycles", "LLC-loads", "LLC-load-misses", "LLC-stores", "LLC-store-misses", "branches", "branch-misses"]
    
    while True:
        print("\033c", end="")
        print(
            "Config - App-Level Events Monitoring\n\n"
            "Select an option for periodic app-level events to monitor.\n\n"
            f"  1. Basic Events [{', '.join(preset_one)}]\n"
            f"  2. Detailed Cache Events [{', '.join(preset_two)}]\n"
            f"  3. Custom Selection (select from perf event list)\n"
            f"  4. No Events\n\n"
            f"Enter option (1, 2, 3, or 4)\n"
            "Leave empty for default option (1)"
        )
        choice = input("\n>>> ").strip()
        if choice == "1":
            return preset_one
        elif choice == "2":
            return preset_two
        elif choice == "3":
            available_events = __fetch_perf_event_list()
            events = SimplePrompts.multi_choice_prompt(
                header_prompt=(
                    "Config - App-Level Events Monitoring\n\n"
                    "Select periodic app-level events to monitor:"
                ),
                choices=available_events,
                initial_index_selection=set(),
                max_items_per_page=20,
                max_columns=2
            )
            return list(events)
        elif choice == "4":
            return []
        elif choice == "":
            return preset_one

def _prompt_periodic_system_wide_events() -> list[str]:
    
    preset_one = ["power/energy-psys/"]
    preset_two = ["power/energy-pkg/", "power/energy-cores/", "power/energy-psys/"]
    
    while True:
        print("\033c", end="")
        print(
            "Config - System-Wide Events Monitoring\n\n"
            "Select a preset for periodic system-wide events to monitor:\n\n"
            f"  1. System Power [{', '.join(preset_one)}]\n"
            f"  2. Detailed Power [{', '.join(preset_two)}]\n"
            f"  3. Custom Selection (select from perf event list)\n"
            f"  4. No Events\n\n"
            "Enter option (1, 2, 3, or 4)\n"
            "Leave empty for default option (1)"
        )
        choice = input("\n>>> ").strip()
        if choice == "1":
            return preset_one
        elif choice == "2":
            return preset_two
        elif choice == "3":
            available_events = __fetch_perf_event_list()
            events = SimplePrompts.multi_choice_prompt(
                header_prompt=(
                    "Config - System-Wide Events Monitoring\n\n"
                    "Select periodic system-wide events to monitor:"
                ),
                choices=available_events,
                initial_index_selection=set(),
                max_items_per_page=20,
                max_columns=2
            )
            return list(events)
        elif choice == "4":
            return []
        elif choice == "":
            return preset_one

def _prompt_one_shot_system_wide_events() -> list[str]:
    preset_one = ["power/energy-pkg/", "power/energy-cores/", "power/energy-psys/", "instructions"]
    preset_two = ["power/energy-psys/"]
    while True:
        print("\033c", end="")
        print(
            "Config - One-Shot System-Wide Events Monitoring\n\n"
            "Select a preset for one-shot system-wide events to monitor:\n\n"
            f"  1. Power and Instructions [{', '.join(preset_one)}]\n"
            f"  2. System Power Only [{', '.join(preset_two)}]\n"
            f"  3. Custom Selection (select from perf event list)\n"
            f"  4. No Events\n\n"
            "Enter option (1, 2, or 3)\n"
            "Leave empty for default option (1)"
        )
        choice = input("\n>>> ").strip()
        if choice == "1":
            return preset_one
        elif choice == "2":
            return preset_two
        elif choice == "3":
            available_events = __fetch_perf_event_list()
            events = SimplePrompts.multi_choice_prompt(
                header_prompt=(
                    "Config - App-Level Events Monitoring\n\n"
                    "Select periodic app-level events to monitor:"
                ),
                choices=available_events,
                initial_index_selection=set(),
                max_items_per_page=20,
                max_columns=2
            )
            return list(events)
        elif choice == "4":
            return []
        elif choice == "":
            return preset_one
        
def configure_exp_defaults() -> DefaultConfigurations:
    
    return DefaultConfigurations(
        action_interval_sec=_prompt_action_interval(),
        sampling_interval_ms=_prompt_sampling_interval(),
        periodic_app_level_events=_prompt_periodic_app_level_events(),
        periodic_system_wide_events=_prompt_periodic_system_wide_events(),
        one_shot_system_wide_events=_prompt_one_shot_system_wide_events()
    )

if __name__ == "__main__":
    config = configure_exp_defaults()
    print("Default Configurations:")
    print(config)