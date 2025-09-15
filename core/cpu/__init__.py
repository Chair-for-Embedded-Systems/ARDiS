from .cpu_info import read_cpuinfo
from .frequency_manager import CPUFrequencyManager
from .intel_frequency_manager import IntelFrequencyManager
from config import clock_domains

def get_platform_frequency_manager() -> CPUFrequencyManager:
    """
    Returns an instance of the appropriate CPUFrequencyManager subclass based on the CPU vendor.
    Currently supports Intel and AMD CPUs.
    """
    cpu_info = read_cpuinfo()
    vendor_id = cpu_info.get("vendor_id", "")
    
    if vendor_id == "":
        raise ValueError("Could not determine CPU vendor from /proc/cpuinfo")
    elif "GenuineIntel" in vendor_id:
        print(f"Detected Intel CPU: {cpu_info.get('model name', 'Unknown Model')}")
        return IntelFrequencyManager(clock_domains=clock_domains, use_hwp=False)
    elif "AuthenticAMD" in vendor_id:
        print(f"Detected AMD CPU: {cpu_info.get('model name', 'Unknown Model')}")
        return CPUFrequencyManager(clock_domains=clock_domains)
    else:
        raise NotImplementedError("Unsupported CPU vendor. Only Intel and AMD are supported.")
    