import os
import io

from ..thermal_monitor import CoreTemperatureMonitor

class IntelMSRMonitor(CoreTemperatureMonitor):
    __slots__ = ("_tjmax_values", "_msr_files")

    IA32_THERM_STATUS_REGISTER: int = 0x19C
    MSR_TEMPERATURE_TARGET_REGISTER: int = 0x1A2
    DEFAULT_TJMAX: float = 100.0

    def __init__(self, target_cores: set[int] | None = None) -> None:
        cores = target_cores or set(range(os.cpu_count() or 0))
        if not cores:
            raise RuntimeError("Unable to determine CPU core topology.")

        self._tjmax_values: dict[int, float] = {}
        self._msr_files: dict[int, io.BufferedReader] = {}

        for core in cores:
            msr_path = f"/dev/cpu/{core}/msr"
            try:
                handle = open(msr_path, "rb")
                self._msr_files[core] = handle
                self._tjmax_values[core] = self._read_tjmax(handle)
            except FileNotFoundError as e:
                self.close()
                raise RuntimeError(
                    f"MSR file {msr_path} missing. Ensure 'msr' driver is loaded ('modprobe msr')."
                ) from e
            except PermissionError as e:
                self.close()
                raise RuntimeError(f"Permission denied for {msr_path}. Must run as root/sudo.") from e

    def _read_tjmax(self, handle) -> float:
        try:
            handle.seek(self.MSR_TEMPERATURE_TARGET_REGISTER)
            val = int.from_bytes(handle.read(8), byteorder="little")
            tjmax = (val >> 16) & 0xFF
            return float(tjmax) if tjmax > 0 else self.DEFAULT_TJMAX
        except Exception:
            return self.DEFAULT_TJMAX

    def sample_core_temperature(self) -> dict[int, float]:
        core_temps: dict[int, float] = {}

        for core, handle in self._msr_files.items():
            handle.seek(self.IA32_THERM_STATUS_REGISTER)
            val = int.from_bytes(handle.read(8), byteorder="little")
            # Bit 31: Valid flag | Bits 22:16: DTS Delta
            is_valid = bool((val >> 31) & 0x1)
            if is_valid:
                dts_delta = (val >> 16) & 0x7F
                core_temps[core] = self._tjmax_values[core] - dts_delta
            else:
                core_temps[core] = -1.0
        return core_temps

    def close(self) -> None:
        for handle in self._msr_files.values():
            try:
                handle.close()
            except Exception:
                pass
        self._msr_files.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

# python3 -m ardis.core.monitoring.thermal.monitors.intel_msr_monitor
if __name__ == "__main__":
    with IntelMSRMonitor() as monitor:
        temps = monitor.sample_core_temperature()
        for core, temp in temps.items():
            print(f"Core {core:>2}: {temp:.2f} °C")
        