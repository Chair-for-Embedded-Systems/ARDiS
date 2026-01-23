from dataclasses import dataclass
from .prompts import SimplePrompts
import os

# Interactive prompt flow to configure SPEC2006 benchmark settings. This includes:
#     - setting the SPEC2006 installation directory
#     - setting the SPEC2006 configuration file
#     - detecting installed SPEC2006 packages
#     - allowing the user to enable/disable specific packages
# 
# Use `python3 -m ardis.utils.autoconfig.flows.configure_spec` to run this script directly.

@dataclass
class Spec2006Configuration:
    enabled: bool
    spec_base_dir: str
    spec_config_file: str
    enabled_packages: list[str]
    disabled_packages: list[str]

spec_apps = [
    '400.perlbench',
    '401.bzip2',
    '403.gcc',
    '410.bwaves',
    '416.gamess',
    '429.mcf',
    '433.milc',
    '434.zeusmp',
    '435.gromacs',
    '436.cactusADM',
    '437.leslie3d',
    '444.namd',
    '445.gobmk',
    '447.dealII',
    '450.soplex',
    '453.povray',
    '454.calculix',
    '456.hmmer',
    '458.sjeng',
    '459.GemsFDTD',
    '462.libquantum',
    '464.h264ref',
    '465.tonto',
    '470.lbm',
    '471.omnetpp',
    '473.astar',
    '481.wrf',
    '482.sphinx3',
]

def _prompt_proceed_setup() -> bool:
    while True:
        print("\033c", end="")
        print("Config - SPEC2006 Benchmark\n")
        choice = input("Proceed with SPEC2006 benchmark configuration? (y/n): ").strip().lower()
        if choice == 'y':
            return True
        elif choice == 'n':
            return False

def _get_spec_home_from_env() -> str | None:
    spec_home = os.getenv("SPEC")
    if spec_home and os.path.isdir(spec_home):
        return spec_home
    else:
        return None

def _prompt_spec2006_home() -> str:
    print("\033c", end="")
    while True:
        print(
            "Config - SPEC2006 Benchmark\n\n"
            "Enter the path to your SPEC2006 installation directory: "
        )
        spec_home = input(">>> ").strip()
        if os.path.isdir(spec_home):

            # Check for 'benchspec' directory
            benchspec_path = os.path.join(spec_home, "benchspec")
            if not os.path.isdir(benchspec_path):
                print("\033c", end="")
                print(f"Warning: The directory '{spec_home}' does not seem to be a valid SPEC2006 installation (missing 'benchspec' directory). Please try again.")
                continue
            
            return spec_home
        else:
            print(f"Directory '{spec_home}' does not exist. Please try again.")

def _prompt_config_file(spec_base: str) -> str:
    
    prompt_header = (
        "Config - SPEC2006 Benchmark\n\n"
        f"SPEC_HOME: {spec_base}\n"
        "Select a SPEC2006 configuration file from the list below:"
    )
    while True:        
        # Load available configs thii is inside the loop to reload on retry
        available_configs = []
        config_dir = os.path.join(spec_base, "config")
        if os.path.isdir(config_dir):
            for file in os.listdir(config_dir):
                if file.endswith(".cfg"):
                    available_configs.append(file)

        # Warn if no configs found
        if not available_configs:
            print(f"No configuration files found in '{config_dir}'. Please create a config file and try again.")
            print("Press any key to retry...")
            input()
            continue
        
        # Prompt user to select config
        return SimplePrompts.single_choice_prompt(
            header_prompt=prompt_header,
            choices=available_configs,
            max_items_per_page=12,
            max_columns=2
        )
        

def _discover_spec2006_packages(spec_base: str) -> tuple[list[str], list[str]]:
    installed_packages: list[str] = []
    non_installed_packages: list[str] = []
    for app in spec_apps:
        app_path = os.path.join(spec_base, "benchspec", "CPU2006", app)
        if not os.path.isdir(app_path):
            non_installed_packages.append(app)
        else:
            # Check if `build` directory exists to confirm installation
            build_path = os.path.join(app_path, "build")
            if os.path.isdir(build_path):
                installed_packages.append(app)
            else:
                non_installed_packages.append(app) 
    return installed_packages, non_installed_packages

def _adjust_package_selection(installed_apps: list[str], non_installed_apps: list[str]) -> tuple[set[str], set[str]]:
    header = (
        "Config - SPEC2006 Benchmark\n\n"
        "Adjust the selection of enabled SPEC2006 packages below.\n"
    )
    all_packages = installed_apps + non_installed_apps
    selected_apps = SimplePrompts.multi_choice_prompt(
        header_prompt=header,
        choices=all_packages,
        initial_index_selection={idx for idx, app in enumerate(all_packages) if app in installed_apps},
        max_items_per_page=24,
        max_columns=3
    )
    non_selected_apps = set(all_packages) - selected_apps
    return selected_apps, non_selected_apps

def configure_spec2006_benchmark() -> Spec2006Configuration:
    
    # Ask user if they want to proceed with setup
    if not _prompt_proceed_setup():
        return Spec2006Configuration(
            enabled=False,
            spec_base_dir="</path/to/spec2006>",
            spec_config_file="my_config.cfg",
            enabled_packages=[],
            disabled_packages=spec_apps
        )
    
    # Automatically detect SPEC home from environment variable or prompt user
    spec_base = _get_spec_home_from_env()
    if spec_base is None:
        spec_base = _prompt_spec2006_home()

    # Prompt for config file
    spec_config_file = _prompt_config_file(spec_base)
    
    installed_apps, non_installed_apps = _discover_spec2006_packages(spec_base)

    while True:
        print("\033c", end="")
        print(
            "Config - SPEC2006 Benchmark\n\n"
            "The following packages where detected on this system and automatically marked as enabled:\n"
        )
        SimplePrompts.print_item_grid(items=installed_apps, columns=4, enable_index=False, padding_left=2)
        print(
            "\nWould you like to adjust which packages should be enabled?\n"
            "Enter 'a' to adjust the select packages\n"
            "Enter 'c' to continue with the current selection."
        )
        choice = input("\n>>> ").strip().lower()
        
        # Ask user for adjustments
        if choice == 'a':
            installed_apps, non_installed_apps = _adjust_package_selection(installed_apps, non_installed_apps)
            break   
        elif choice == 'c':
            break

    conf = Spec2006Configuration(
        enabled=True,
        spec_base_dir=spec_base,
        spec_config_file=spec_config_file,
        enabled_packages=list(installed_apps),
        disabled_packages=list(non_installed_apps)
    )
    return conf

if __name__ == "__main__":
    config = configure_spec2006_benchmark()
    print("SPEC2006 Enabled:", config.enabled)
    print("SPEC2006 Home:", config.spec_base_dir)
    print("Config File:", config.spec_config_file)
    print("Enabled Applications:", config.enabled_packages)
    print("Disabled Applications:", config.disabled_packages)