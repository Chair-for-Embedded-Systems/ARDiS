from .frequency_manager import CPUFrequencyManager
from .intel.frequency_manager import IntelFrequencyManager
from .amd.frequency_manager import AMDFrequencyManager
from .acpi.frequency_manager import ACPIFrequencyManager
from config import clock_domains

def get_platform_frequency_manager() -> CPUFrequencyManager:
    """
    Returns an instance of the appropriate CPUFrequencyManager subclass based on the CPU vendor.
    Currently supports Intel and AMD CPUs.
    """

    # Get scaling driver for core 0 to help identify the platform
    scaling_driver = CPUFrequencyManager.get_scaling_driver(core=0)
    if scaling_driver is None:
        raise EnvironmentError("Could not determine scaling driver!")

    # Instantiate the appropriate frequency manager based on the scaling driver
    if scaling_driver == "intel_cpufreq" or scaling_driver == "intel_pstate":
        return IntelFrequencyManager(
            clock_domains=clock_domains,
            disable_thermald=True,
            disable_boost=True,
            use_hwp=False
        )
    elif scaling_driver == "amd-pstate":
        return AMDFrequencyManager(
            clock_domains=clock_domains,
        )
    elif scaling_driver == "acpi-cpufreq":
        return ACPIFrequencyManager(
            clock_domains=clock_domains,
            strict_mode=True
        )
    else:
        raise NotImplementedError(
            f"Unsupported scaling driver '{scaling_driver}'. "
            "Only 'intel_pstate', 'amd-pstate', and 'acpi-cpufreq' are supported."
        )
