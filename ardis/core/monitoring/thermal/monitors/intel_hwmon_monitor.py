import os
import io

from ..thermal_monitor import CoreTemperatureMonitor

class IntelHWMonMonitor(CoreTemperatureMonitor):

    def __init__(self, hwmon_path: str | None = None) -> None:
        self._sensor_path = hwmon_path or self._find_coretemp_hwmon_path()
        self._logical_to_handle: dict[int, io.TextIOWrapper] = {}

        label_to_input_path = self._discover_core_sensor_inputs(self._sensor_path)
        self._core_to_physical_map = self._get_logical_to_physical_mapping()
        self._open_handles(label_to_input_path)

    @staticmethod
    def _find_coretemp_hwmon_path() -> str:
        """Scans /sys/class/hwmon/ to automatically find the 'coretemp' device."""
        base_dir = "/sys/class/hwmon"
        if not os.path.exists(base_dir):
            raise RuntimeError("Sysfs hwmon path /sys/class/hwmon does not exist.")

        for entry in os.listdir(base_dir):
            path = os.path.join(base_dir, entry)
            name_file = os.path.join(path, "name")
            try:
                with open(name_file, "r") as f:
                    if f.read().strip() == "coretemp":
                        return path
            except (FileNotFoundError, IOError):
                continue

        raise RuntimeError("Could not locate a hwmon device with name 'coretemp'. Is the driver loaded?")
    
    @staticmethod
    def _discover_core_sensor_inputs(path: str) -> dict[str, str]:
        """Maps core labels (e.g. 'Core 0', 'Core 1') to their temp_input path."""
        label_map: dict[str, str] = {}
        for entry in os.listdir(path):
            if entry.startswith("temp") and entry.endswith("_label"):
                idx = entry.split("_")[0]  # temp1, temp2...
                label_file = os.path.join(path, entry)
                input_file = os.path.join(path, f"{idx}_input")

                if os.path.exists(input_file):
                    try:
                        with open(label_file, "r") as f:
                            label = f.read().strip()
                            if label.startswith("Core "):
                                label_map[label] = input_file
                    except IOError:
                        continue
        return label_map
    
    @staticmethod
    def _get_logical_to_physical_mapping() -> dict[int, int]:
        """Maps logical core IDs to physical core IDs via sysfs topology."""
        cpu_dir = "/sys/devices/system/cpu"
        mapping: dict[int, int] = {}

        if not os.path.exists(cpu_dir):
            return mapping

        for entry in os.listdir(cpu_dir):
            if entry.startswith("cpu") and entry[3:].isdigit():
                logical_id = int(entry[3:])
                topo_file = os.path.join(cpu_dir, entry, "topology", "core_id")
                try:
                    with open(topo_file, "r") as f:
                        mapping[logical_id] = int(f.read().strip())
                except (FileNotFoundError, ValueError, IOError):
                    continue

        return mapping
    
    def _open_handles(self, label_map: dict[str, str]) -> None:
        """Opens persistent file wrappers for reading core temperatures."""
        try:
            for logical_id, physical_id in self._core_to_physical_map.items():
                core_label = f"Core {physical_id}"
                if core_label in label_map:
                    self._logical_to_handle[logical_id] = open(label_map[core_label], "r")

        except Exception as e:
            self.close()
            raise RuntimeError(f"Failed to open hwmon temperature handles: {e}") from e
        
    def sample_core_temperature(self) -> dict[int, float]:
        """Samples core temperatures from persistent sysfs file descriptors."""
        core_temps: dict[int, float] = {}

        for logical_id, handle in self._logical_to_handle.items():
            handle.seek(0)
            val = handle.read().strip()
            if val:
                core_temps[logical_id] = int(val) / 1000.0

        return core_temps

    def close(self) -> None:
        """Closes all open sysfs file descriptors."""
        for handle in self._logical_to_handle.values():
            try:
                handle.close()
            except Exception:
                pass
        self._logical_to_handle.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

# python3 -m ardis.core.monitoring.thermal.monitors.intel_hwmon_monitor
if __name__ == "__main__":
    with IntelHWMonMonitor() as monitor:
        temps = monitor.sample_core_temperature()
        for core_id, temp in sorted(temps.items()):
            print(f"Core {core_id:>2}: {temp:.1f}°C")