import os

from ..thermal_monitor import CoreTemperatureMonitor

class IntelMSRMonitor(CoreTemperatureMonitor):
    __slots__ = ("_tjmax_values", "_msr_fds")

    IA32_THERM_STATUS_REGISTER: int = 0x19C
    MSR_TEMPERATURE_TARGET_REGISTER: int = 0x1A2
    DEFAULT_TJMAX: float = 100.0

    def __init__(self, target_cores: set[int] | None = None) -> None:
        cores = target_cores or set(range(os.cpu_count() or 0))
        if not cores:
            raise RuntimeError("Unable to determine CPU core topology.")

        self._tjmax_values: dict[int, float] = {}
        self._msr_fds: dict[int, int] = {}

        for core in cores:
            msr_path = f"/dev/cpu/{core}/msr"
            try:
                fd = os.open(msr_path, os.O_RDONLY)
                self._msr_fds[core] = fd
                self._tjmax_values[core] = self._read_tjmax(fd)
            except FileNotFoundError as e:
                self.close()
                raise RuntimeError(
                    f"MSR file {msr_path} missing. Ensure 'msr' driver is loaded ('modprobe msr')."
                ) from e
            except PermissionError as e:
                self.close()
                raise RuntimeError(f"Permission denied for {msr_path}. Must run as root/sudo.") from e

    def _read_tjmax(self, fd: int) -> float:
        try:
            raw = os.pread(fd, 8, self.MSR_TEMPERATURE_TARGET_REGISTER)
            val = int.from_bytes(raw, byteorder="little")
            tjmax = (val >> 16) & 0xFF
            return float(tjmax) if tjmax > 0 else self.DEFAULT_TJMAX
        except Exception:
            return self.DEFAULT_TJMAX

    def sample_core_temperature(self) -> dict[int, float]:
        core_temps: dict[int, float] = {}

        for core, fd in self._msr_fds.items():
            raw = os.pread(fd, 8, self.IA32_THERM_STATUS_REGISTER)
            val = int.from_bytes(raw, byteorder="little")
            # Bit 31: Valid flag | Bits 22:16: DTS Delta
            is_valid = bool((val >> 31) & 0x1)
            if is_valid:
                dts_delta = (val >> 16) & 0x7F
                core_temps[core] = self._tjmax_values[core] - dts_delta
            else:
                core_temps[core] = -1.0
        return core_temps

    def close(self) -> None:
        for fd in self._msr_fds.values():
            try:
                os.close(fd)
            except Exception:
                pass
        self._msr_fds.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()