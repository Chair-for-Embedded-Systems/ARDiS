from dataclasses import dataclass
from .prompts import SimplePrompts
import os

# Interactive prompt flow to configure PARSEC benchmark settings. This includes:
#     - setting the PARSEC installation directory
#     - detecting installed PARSEC packages
#     - allowing the user to enable/disable specific packages
# 
# Use `python3 -m ardis.utils.autoconfig.flows.configure_parsec` to run this script directly.

@dataclass
class ParsecConfiguration:
    parsec_base_dir: str
    enabled_packages: set[str]
    disabled_packages: set[str]

parsec_apps = ["blackscholes", "bodytrack", "facesim", "ferret", "fluidanimate", "freqmine", "swaptions", "vips", "x264"]
parsec_kernels = ["canneal", "dedup", "streamcluster"]
parsec_networking_apps = ["netstreamcluster", "netdedup", "netferret"]
splash2x_apps = ["barnes", "fmm", "ocean_cp", "ocean_ncp", "radiosity", "water_nsquared", "water_spatial"]
splash2x_kernels = ["cholesky", "fft", "lu_cb", "lu_ncb", "radix"]

all_packages = parsec_apps + parsec_kernels + splash2x_apps + splash2x_kernels + parsec_networking_apps

def _prompt_proceed_setup() -> bool:
    while True:
        print("\033c", end="")
        print("Config - PARSEC Benchmark")
        choice = input("Proceed with PARSEC benchmark configuration? (y/n): ").strip().lower()
        if choice == 'y':
            return True
        elif choice == 'n':
            return False

def _get_parsec_home_from_env() -> str | None:
    parsec_home = os.getenv("xxPARSECDIRxx")
    
    if parsec_home and os.path.isdir(parsec_home):
        return parsec_home
    else:
        return None

def _prompt_parsec_home() -> str:
    print("\033c", end="")
    while True:
        print("Config - PARSEC Benchmark")
        parsec_home = input("Enter the path to your PARSEC installation directory: ").strip()
        
        if os.path.isdir(parsec_home):
            print(f"Valid PARSEC installation found at: {parsec_home}")

            # Some sanity check: look for 'pkgs' or 'ext' directory
            pkgs_path = os.path.join(parsec_home, "pkgs")
            ext_path = os.path.join(parsec_home, "ext")
            if not (os.path.isdir(pkgs_path) or os.path.isdir(ext_path)):
                print("\033c", end="")
                print(f"Warning: The directory '{parsec_home}' does not seem to be a valid PARSEC installation (missing 'pkgs' or 'ext' directories). Please try again.")
                continue

            return parsec_home
        else:
            print("\033c", end="")
            print(f"Directory '{parsec_home}' does not exist. Please try again.")

def _discover_parsec_packages(parsec_home: str) -> tuple[set[str], set[str]]:
    package_to_installation_path: dict[str, str] = {}
    
    # Map packages to their installation paths
    for package in parsec_apps:
        install_path = os.path.join(parsec_home, "pkgs", "apps", "", package, "inst")
        package_to_installation_path[f"parsec.{package}"] = install_path

    for kernel in parsec_kernels:
        install_path = os.path.join(parsec_home, "pkgs", "kernels", "", kernel, "inst")
        package_to_installation_path[f"parsec.{kernel}"] = install_path

    for package in parsec_networking_apps:
        install_path = os.path.join(parsec_home, "pkgs", "netapps", "", package, "inst")
        package_to_installation_path[f"parsec.{package}"] = install_path

    for package in splash2x_apps:
        install_path = os.path.join(parsec_home, "ext", "splash2x", "apps", "", package, "inst")
        package_to_installation_path[f"splash2x.{package}"] = install_path

    for kernel in splash2x_kernels:
        install_path = os.path.join(parsec_home, "ext", "splash2x", "kernels", "", kernel, "inst")
        package_to_installation_path[f"splash2x.{kernel}"] = install_path

    installed_packages: set[str] = set()
    non_installed_packages: set[str] = set()

    # Check which packages are installed
    for package, path in package_to_installation_path.items():
        if os.path.isdir(path):
            installed_packages.add(package)
        else:
            non_installed_packages.add(package)

    return installed_packages, non_installed_packages

def _adjust_package_selection(
    enabled_packages: set[str],
    disabled_packages: set[str]
) -> tuple[set[str], set[str]]:
    
    all_packages = list(enabled_packages.union(disabled_packages))
    selected_apps: set[str] = enabled_packages.copy()

    while True:
        print("\033c", end="")
        header = (
            "Config - PARSEC Benchmark\n\n"
            "Adjust the selection of enabled PARSEC packages below."
        )
        selected_apps = SimplePrompts.multi_choice_prompt(
            header_prompt=header,
            choices=sorted(all_packages),
            initial_index_selection=set(),
            max_items_per_page=24,
            max_columns=3
        )
        break

    disabled_apps = set(all_packages) - selected_apps

    return selected_apps, disabled_apps

def configure_parsec_benchmark() -> ParsecConfiguration:
    
    if not _prompt_proceed_setup():
        return ParsecConfiguration(
            parsec_base_dir="</path/to/parsec>",
            enabled_packages=set(),
            disabled_packages=set(all_packages)
        )
    
    # Automatically detect PARSEC home from environment variable or prompt user
    parsec_home = _get_parsec_home_from_env()
    if parsec_home is None:
        parsec_home = _prompt_parsec_home()

    installed_packages, non_installed_packages = _discover_parsec_packages(parsec_home)
    
    # Print discovered packages and ask for adjustments
    while True:
        print("\033c", end="")
        print(
            "Config - PARSEC Benchmark\n\n"
            "Detected the following PARSEC packages installed on this system:\n"
        )
        SimplePrompts.print_item_grid(
            items=sorted(installed_packages),
            columns=4, 
            enable_index=False,
            padding_left=2
        )      
        print(
            "\nWould you like to adjust the packages that should be enabled?\n" +
            "Enter 'a' to adjust selected packages\n" +
            "Enter 'c' to continue with the current selection."
        )

        choice = input("\n>>> ").strip().lower()
        if choice == 'a':
            enabled_packages, disabled_packages = _adjust_package_selection(installed_packages, non_installed_packages)
            installed_packages = enabled_packages
            non_installed_packages = disabled_packages
            break
        elif choice == 'c':
            break
        else:
            print("Invalid input. Please enter 'a' or 'c'.")

    conf = ParsecConfiguration(
        parsec_base_dir=parsec_home,
        enabled_packages=installed_packages,
        disabled_packages=non_installed_packages
    )
    return conf

if __name__ == "__main__":
    config = configure_parsec_benchmark()
    print("Parsec Home:", config.parsec_base_dir)
    print("Enabled Packages:", config.enabled_packages)
    print("Disabled Packages:", config.disabled_packages)