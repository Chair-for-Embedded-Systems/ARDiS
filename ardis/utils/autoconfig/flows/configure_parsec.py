from dataclasses import dataclass
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

parsec_apps = [
    "blackscholes",
    "bodytrack",
    "facesim",
    "ferret",
    "fluidanimate",
    "freqmine",
    "swaptions",
    "vips",
    "x264"
]
parsec_kernels = ["canneal", "dedup", "streamcluster"]

splash2x_apps = [
    "barnes",
    "fmm",
    "ocean_cp",
    "ocean_ncp",
    "radiosity",
    "water_nsquared",
    "water_spatial",
]
splash2x_kernels = ["cholesky", "fft", "lu_cb", "lu_ncb", "radix"]
parsec_networking_apps = ["netstreamcluster", "netdedup", "netferret"]

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
        print("Config - PARSEC Benchmark")
        print("Select available PARSEC applications on this system:\n")
        for idx, app in enumerate(all_packages, start=1):
            mark = "[X]" if app in selected_apps else "[ ]"
            print(f"{idx:2}. {mark} {app.split('.')[1]}")
        
        print("\n[x] = Selected, [ ] = Not Selected")
        print("\nEnter application numbers separated by spaces to toggle selection.")
        print("Enter 'done' when finished.")

        user_input = input("Your choice: ").strip()
        if user_input.lower() == 'done':
            break

        indices = user_input.split()
        for index_str in indices:
            if index_str.isdigit():
                index = int(index_str) - 1
                if 0 <= index < len(all_packages):
                    app = all_packages[index]
                    if app in selected_apps:
                        selected_apps.remove(app)
                    else:
                        selected_apps.add(app)

    disabled_apps = set(all_packages) - selected_apps

    return selected_apps, disabled_apps

def configure_parsec_benchmark() -> ParsecConfiguration:
    
    parsec_home = _prompt_parsec_home()
    installed_packages, non_installed_packages = _discover_parsec_packages(parsec_home)
    
    # Print discovered packages and ask for adjustments
    while True:
        print("\033c", end="")
        print("Config - PARSEC Benchmark")
        print("Detected the following PARSEC packages installed on this system:\n")
        for idx, package in enumerate(sorted(installed_packages), start=1):
            print(f"{idx:2}. {package}")
        print("\nWould you like to adjust the packages that should be enabled?")
        choice = input("Enter 'a' to adjust selected packages, or 'c' to continue: ").strip().lower()
        if choice == 'a':
            enabled_packages, disabled_packages = _adjust_package_selection(
                installed_packages,
                non_installed_packages
            )
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