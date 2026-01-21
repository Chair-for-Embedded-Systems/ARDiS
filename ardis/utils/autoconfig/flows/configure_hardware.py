import glob
import os
from dataclasses import dataclass


# Interactive prompt flow to configure hardware-related settings. This includes:
#     - detecting logical cores
#     - separating the cores into frequency domains
# Use `python3 -m ardis.utils.autoconfig.flows.configure_hardware` to run this script directly.

@dataclass
class HardwareConfiguration:
    logical_cores: int
    frequency_domains: list[set[int]]

    
def _get_logical_cores() -> list[int]:
    return [int(os.path.basename(d).replace("cpu", "")) for d in glob.glob(os.path.join("/sys/devices/system/cpu/", "cpu[0-9]*")) if os.path.isdir(d)]

def _get_core_cache_mappings(logical_cores: list[int]) -> dict[int, tuple[int, int, int, int]]:
    core_to_cache_ids: dict[int, tuple[int, int, int, int]] = {}
    for core in logical_cores:
        cache_ids = []
        for level in range(4):
            cache_path = f"/sys/devices/system/cpu/cpu{core}/cache/index{level}/id"
            try:
                with open(cache_path, 'r') as f:
                    cache_id = int(f.read().strip())
                    cache_ids.append(cache_id)
            except FileNotFoundError:
                cache_ids.append(-1)
        core_to_cache_ids[core] = tuple(cache_ids)
    return core_to_cache_ids

def _group_cores_by_l2_cache(core_to_cache_ids: dict[int, tuple[int, int, int, int]]) -> dict[int, set[int]]:
    l2_cache_to_cores: dict[int, set[int]] = {}
    for core_id, cache_ids in core_to_cache_ids.items():
        l2_id = cache_ids[2]
        if l2_id not in l2_cache_to_cores:
            l2_cache_to_cores[l2_id] = set()
        l2_cache_to_cores[l2_id].add(core_id)
    return l2_cache_to_cores

def _group_cores_by_l3_cache(core_to_cache_ids: dict[int, tuple[int, int, int, int]]) -> dict[int, set[int]]:
    l3_cache_to_cores: dict[int, set[int]] = {}
    for core_id, cache_ids in core_to_cache_ids.items():
        l3_id = cache_ids[3]
        if l3_id not in l3_cache_to_cores:
            l3_cache_to_cores[l3_id] = set()
        l3_cache_to_cores[l3_id].add(core_id)
    return l3_cache_to_cores

def configure_hardware() -> HardwareConfiguration:
    
    logical_cores = _get_logical_cores()
    core_to_cache_ids = _get_core_cache_mappings(logical_cores)

    l2_cache_to_cores = _group_cores_by_l2_cache(core_to_cache_ids)
    l3_cache_to_cores = _group_cores_by_l3_cache(core_to_cache_ids)
    
    # Ask which option to use
    frequency_domains: list[set[int]]
    while True:
        # Clear screen
        print("\033c", end="")
        print("Config - Hardware\n")

        # Option 1
        print("Option 1 - Split on L2 Cache (Modern Intel CPUs):")
        for l2_id, cores in sorted(l2_cache_to_cores.items()):
            print(f"  Domain {l2_id}: {sorted(cores)}")

        # Option 2
        print("\nOption 2 - Split on L3 Cache (AMD CPUs):")
        for l3_id, cores in sorted(l3_cache_to_cores.items()):
            print(f"  Domain {l3_id}: {sorted(cores)}")

        # Option 3
        print("\nOption 3 - Single Group (Fallback):")
        all_cores = sorted(core_to_cache_ids.keys())
        print(f"  Domain 0: {all_cores}")

        print(
            "\nEnter option (1, 2, or 3)\n"
            "Leave empty for default (Option 3)\n"
        )
        option = input(">>> ").strip()
        if option == "1":
            frequency_domains = [set(cores) for cores in l2_cache_to_cores.values()]
            break
        elif option == "2":
            frequency_domains = [set(cores) for cores in l3_cache_to_cores.values()]
            break
        elif option == "3" or option == "":
            frequency_domains = [{core for core in core_to_cache_ids.keys()}]
            break
        else:
            print("Invalid option selected. Please try again.")

    # Sort frequency domains by lowest core ID
    frequency_domains.sort(key=lambda domain: min(domain))
    
    return HardwareConfiguration(
        logical_cores=len(logical_cores), 
        frequency_domains=frequency_domains
    )


if __name__ == "__main__":
    config = configure_hardware()
    print(f"Detected {config.logical_cores} logical cores.")
    print(f"Frequency domains: {config.frequency_domains}")