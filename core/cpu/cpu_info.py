import os

def read_cpuinfo() -> dict[str, str]:
    """
    Reads and parses the `/proc/cpuinfo` file to extract CPU information.
    Returns a dictionary with key-value pairs from the file.
    """
    if not os.path.exists("/proc/cpuinfo"):
        raise FileNotFoundError("/proc/cpuinfo does not exist on this system.")
    
    try:
        with open("/proc/cpuinfo", "r") as f:
            cpu_info: dict[str, str] = {}
            for line in f:
                if ':' in line:
                    key, value = line.split(":", 1)
                    cpu_info[key.strip()] = value.strip()
            return cpu_info
    except IOError as e:
        raise IOError(f"Failed to read /proc/cpuinfo: {e}")

def get_cpu_flags() -> set[str]:
    """
    Returns a set of CPU flags supported by the processor.
    """
    cpu_info = read_cpuinfo()
    flags_line = cpu_info.get("flags", "")
    flags = {flag for flag in flags_line.split() if flag}
    return flags

