from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ardis.core.monitoring.thermal.thermal_monitor import CoreTemperatureMonitor

HWMON_BASE_PATH = "/sys/class/hwmon"


def discover_hwmon_chips(hwmon_dir: str = HWMON_BASE_PATH) -> dict[str, str]:
    """Scans /sys/class/hwmon to map chip names (e.g., 'coretemp') to sysfs paths."""
    if not os.path.exists(hwmon_dir):
        return {}

    discovered_chips: dict[str, str] = {}
    for entry in os.listdir(hwmon_dir):
        chip_path = os.path.join(hwmon_dir, entry)
        name_file = os.path.join(chip_path, "name")

        try:
            with open(name_file, "r") as f:
                discovered_chips[f.read().strip()] = chip_path
        except (FileNotFoundError, IOError):
            continue

    return discovered_chips


def is_intel_cpu() -> bool:
    """Checks whether the system CPU vendor is GenuineIntel."""
    cpuinfo_path = "/proc/cpuinfo"
    if not os.path.exists(cpuinfo_path):
        return False
    try:
        with open(cpuinfo_path, "r") as f:
            for line in f:
                if line.startswith("vendor_id"):
                    vendor = line.split(":")[1].strip()
                    return vendor == "GenuineIntel"
    except IOError:
        pass
    return False


def _can_read_msr() -> bool:
    """Checks if /dev/cpu/0/msr exists and is readable by the current process."""
    msr_path = "/dev/cpu/0/msr"
    return os.path.exists(msr_path) and os.access(msr_path, os.R_OK)


def create_core_temp_monitor(
    preferred_driver: str | None = None,
) -> CoreTemperatureMonitor:
    """Factory function to instantiate the best available CoreTemperatureMonitor.

    Args:
        preferred_driver: Optional driver override ("coretemp", "msr-intel", "k10temp", "zenpower").
                          If None, auto-detection is used.
    """
    chips = discover_hwmon_chips()

    match preferred_driver:
        case "coretemp":
            if "coretemp" not in chips:
                raise RuntimeError("Driver 'coretemp' requested, but no coretemp hwmon device was found.")
            from .monitors.intel_hwmon_monitor import IntelHWMonMonitor
            return IntelHWMonMonitor(hwmon_path=chips["coretemp"])

        case "msr-intel":
            if not _can_read_msr():
                raise PermissionError(
                    "Driver 'msr-intel' requested, but permission denied for /dev/cpu/0/msr. "
                    "Run as root or grant CAP_SYS_RAWIO capability."
                )
            from .monitors.intel_msr_monitor import IntelMSRMonitor
            return IntelMSRMonitor()

        case "k10temp" | "zenpower":
            raise NotImplementedError("Support for AMD hwmon driver is not yet implemented.")

        case None:            
            # 1. Prefer Intel MSR driver if available, as it allows faster sampling (requires root)
            if is_intel_cpu() and _can_read_msr():
                from .monitors.intel_msr_monitor import IntelMSRMonitor
                return IntelMSRMonitor()
            
            # 2. Use Intel hwmon as fallback if available (unprivileged)
            if "coretemp" in chips:
                from .monitors.intel_hwmon_monitor import IntelHWMonMonitor
                return IntelHWMonMonitor(hwmon_path=chips["coretemp"])

            # 3. If Intel CPU and MSR driver is present but not readable, raise a permission error
            if is_intel_cpu() and os.path.exists("/dev/cpu/0/msr") and not _can_read_msr():
                raise PermissionError(
                    "Intel CPU and MSR driver detected, but permission denied for /dev/cpu/0/msr. "
                    "Run with root privileges, set CAP_SYS_RAWIO, or load 'coretemp' module."
                )

            raise RuntimeError(
                "No compatible CPU thermal driver discovered on this system. Please disable core temperature monitoring in the config.\n"
                f"(Active hwmon drivers: [{', '.join(chips.keys()) if chips else 'None'}])"
            )

        case invalid_driver:
            raise ValueError(f"Unknown driver requested: '{invalid_driver}'")


if __name__ == "__main__":
    with create_core_temp_monitor() as monitor:
        temps = monitor.sample_core_temperature()
        for core, temp in sorted(temps.items()):
            print(f"Core {core:>2}: {temp:.2f} °C")