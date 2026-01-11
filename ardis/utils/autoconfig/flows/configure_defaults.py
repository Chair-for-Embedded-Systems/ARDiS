from dataclasses import dataclass

@dataclass
class DefaultConfiurattions:
    action_interval_sec: float
    sampling_interval_ms: int
    periodic_app_level_events: list[str]
    periodic_system_wide_events: list[str]
    one_shot_system_wide_events: list[str]

def _prompt_action_interval(default: float = 0.1) -> float:
    error_msg = ""
    while True:
        print("\033c", end="")
        if len(error_msg) > 0:
            print(f"Error: {error_msg}\n")
        try:
            interval = float(input(f"Enter the action interval in seconds (default {default}): "))
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
            interval = int(input(f"Enter the sampling interval in milliseconds (default {default}): "))
            if interval <= 0:
                error_msg = "Please enter a positive integer."
                continue
            return interval
        except ValueError:
            error_msg = "Invalid input. Please enter an integer value."

def _prompt_periodic_app_level_events() -> list[str]:

    option_one = ["instructions", "cycles", "branches", "branch-misses"]
    option_two = ["instuctions", "cycles", "LLC-loads", "LLC-load-misses", "LLC-stores", "LLC-store-misses", "branches", "branch-misses"]

    while True:
        print("\033c", end="")
        print("Select a preset for periodic app-level events to monitor:\n")
        print("1. Basic Events (instructions, cycles, branches, branch-misses)")
        print("2. Detailed Cache Events (instructions, cycles, LLC-loads, LLC-load-misses, LLC-stores, LLC-store-misses, branches, branch-misses)")
        print("3. Custom Selection (use perf list to view available events)")
        print("4. No Events")
        choice = input("Enter option (1, 2, or 3): ").strip()
        if choice == "1":
            return option_one
        elif choice == "2":
            return option_two
        elif choice == "3":
            events = input("Enter periodic app-level events separated by spaces (or leave blank for none): ")
            return events.strip().split() if events.strip() else []
        elif choice == "4":
            return []

def _prompt_periodic_system_wide_events() -> list[str]:
    
    option_one = ["power/energy-psys/"]
    option_two = ["power/energy-pkg/", "power/energy-cores/", "power/energy-psys/"]
    
    while True:
        print("\033c", end="")
        print("Select a preset for periodic system-wide events to monitor:\n")
        print("1. System Power (power/energy-psys/)")
        print("2. Detailed Power (power/energy-pkg/, power/energy-cores/, power/energy-psys/)")
        print("3. Custom Selection (use perf list to view available events)")
        print("4. No Events")
        choice = input("\nEnter option (1, 2, 3, or 4): ").strip()
        if choice == "1":
            return option_one
        elif choice == "2":
            return option_two
        elif choice == "3":
            events = input("Enter periodic system-wide events separated by spaces (or leave blank for none): ")
            return events.strip().split() if events.strip() else []
        elif choice == "4":
            return []

def _prompt_one_shot_system_wide_events() -> list[str]:
    
    option_one = ["power/energy-pkg/", "power/energy-cores/", "power/energy-psys/", "instructions"]
    while True:
        print("\033c", end="")
        print("Select a preset for one-shot system-wide events to monitor:\n")
        print("1. Power and Instructions (power/energy-pkg/, power/energy-cores/, power/energy-psys/, instructions)")
        print("2. Custom Selection (use perf list to view available events)")
        print("3. No Events")
        choice = input("\nEnter option (1, 2, or 3): ").strip()
        if choice == "1":
            return option_one
        elif choice == "2":
            events = input("Enter one-shot system-wide events separated by spaces (or leave blank for none): ")
            return events.strip().split() if events.strip() else []
        elif choice == "3":
            return []

def configure_exp_defaults() -> DefaultConfiurattions:
    
    return DefaultConfiurattions(
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