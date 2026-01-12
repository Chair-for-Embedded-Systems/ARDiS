from dataclasses import dataclass
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

def _prompt_spec2006_home() -> str:
    while True:
        print("\033c", end="")
        print("Config - SPEC2006 Benchmark")
        spec_home = input("Enter the path to your SPEC2006 installation directory: ").strip()
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
    while True:
        print("\033c", end="")
        print("Config - SPEC2006 Benchmark")
        config_file = input("Enter the name of the SPEC2006 configuration file (e.g., 'speccpu2006.cfg'): ").strip()
        config_path = os.path.join(spec_base, "config", config_file)
        if os.path.isfile(config_path):
            print(f"Found configuration file at: {config_path}")
            return config_file
        else:
            print(f"Configuration file '{config_path}' does not exist. Please try again.")

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

def _adjust_package_selection(installed_apps: list[str], non_installed_apps: list[str]) -> tuple[list[str], list[str]]:
    selected_apps = set(installed_apps)

    while True:
        print("\033c", end="")
        print("Config - SPEC2006 Benchmark")
        print("Select available SPEC2006 applications on this system:\n")
        all_packages = installed_apps + non_installed_apps
        for idx, app in enumerate(all_packages, start=1):
            mark = "[X]" if app in selected_apps else "[ ]"
            print(f"{idx:2}. {mark} {app.split('.')[1]}")
        print("\nEnter application numbers separated by spaces to toggle selection.")
        print("Enter 'done' when finished.")

        user_input = input("Your choice: ").strip()
        if user_input.lower() == 'done':
            break

        selections = user_input.split()
        for sel in selections:
            if sel.isdigit():
                idx = int(sel) - 1
                if 0 <= idx < len(all_packages):
                    app = all_packages[idx]
                    if app in selected_apps:
                        selected_apps.remove(app)
                    else:
                        selected_apps.add(app)

    final_installed = [app for app in installed_apps if app in selected_apps]
    final_non_installed = [app for app in non_installed_apps if app in selected_apps]

    return final_installed, final_non_installed

def configure_spec2006_benchmark() -> Spec2006Configuration:
    spec_base = _prompt_spec2006_home()
    spec_config_file = _prompt_config_file(spec_base)
    
    installed_apps, non_installed_apps = _discover_spec2006_packages(spec_base)

    while True:
        print("\033c", end="")
        print("Config - SPEC2006 Benchmark")
        print("Detected the following SPEC2006 packages installed on this system:\n")
        for idx, app in enumerate(installed_apps, start=1):
            print(f"{idx:2}. {app}")
        
        print("\nWould you like to adjust which packages should be enabled?")
        choice = input("Enter 'a' to adjust the select packages, or 'c' to continue: ").strip().lower()
        if choice == 'a':
            installed_apps, non_installed_apps = _adjust_package_selection(installed_apps, non_installed_apps)
            break   
        elif choice == 'c':
            break

    conf = Spec2006Configuration(
        spec_base_dir=spec_base,
        spec_config_file=spec_config_file,
        enabled_packages=installed_apps,
        disabled_packages=non_installed_apps
    )
    return conf

if __name__ == "__main__":
    config = configure_spec2006_benchmark()
    print("SPEC2006 Home:", config.spec_base_dir)
    print("Selected Applications:", config.enabled_packages)