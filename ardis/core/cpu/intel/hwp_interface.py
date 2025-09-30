from __future__ import annotations
from dataclasses import dataclass
from ardis.core.cpu.cpu_info import get_cpu_flags
import struct

@dataclass
class HWPRequest:
    minimum_performance: int # Minimum P-State
    maximum_performance: int # Maximum P-State
    desired_performance: int # Desired P-State
    energy_performance_preference: int  # Energy Performance Preference

    @classmethod
    def from_int(cls, value: int) -> HWPRequest:
        return HWPRequest(
            minimum_performance= value & 0xFF,
            maximum_performance= value >> 8 & 0xFF,
            desired_performance= value >> 16 & 0xFF,
            energy_performance_preference= value >> 24 & 0xFF
        )
    
    def to_int(self) -> int:
        return (
            (self.minimum_performance & 0xFF) |
            ((self.maximum_performance & 0xFF) << 8) |
            ((self.desired_performance & 0xFF) << 16) |
            ((self.energy_performance_preference & 0xFF) << 24)
        )

@dataclass
class HWPCapabilities:
    highest_performance: int
    guaranteed_performance: int
    most_efficient_performance: int
    lowest_performance: int

    @classmethod
    def from_int(cls, value: int) -> HWPCapabilities:
        return HWPCapabilities(
            highest_performance= value & 0xFF,
            guaranteed_performance= value >> 8 & 0xFF,
            most_efficient_performance= value >> 16 & 0xFF,
            lowest_performance= value >> 24 & 0xFF
        )

class IntelHWPInterface:
    
    """
    Interface to Intel's Hardware P-State (HWP) functionality via Model-Specific Registers (MSRs).
    
    The use of this interface effectively bypasses the intel_pstate driver.
    I.e changing HWP settings here is not reflected in the sysfs exposed files like scaling_max_freq or scaling_min_freq.
    This interface should only be used when there is a desire to work with P-states directly.
    """

    # MSR for the HWP Programming Interface 
    # (see Intel® 64 and IA-32 Architectures Software Developer’s Manual Volume 3B: System Programming Guide, Part 2)
    # https://cdrdv2.intel.com/v1/dl/getContent/671427

    IA32_PM_ENABLE = 0x770
    IA32_HWP_CAPABILITIES = 0x771
    IA32_HWP_REQUEST = 0x774

    def __init__(self) -> None:    
        hwp_supported = "hwp" in get_cpu_flags()
        if not hwp_supported:
            raise RuntimeError("HWP is not supported on this CPU")
    
    def get_hwp_capabilities(self, core: int) -> HWPCapabilities | None:
        result = self._read_msr(core, IntelHWPInterface.IA32_HWP_CAPABILITIES)
        if result is not None:
            return HWPCapabilities.from_int(result)
        return None

    def get_hwp_request(self, core: int) -> HWPRequest | None:
        result = self._read_msr(core, IntelHWPInterface.IA32_HWP_REQUEST)
        if result is not None:
            return HWPRequest.from_int(result)
        return None
    
    def set_hwp_request(self, core: int, request: HWPRequest):
        value = request.to_int()
        self._write_msr(core, IntelHWPInterface.IA32_HWP_REQUEST, value)

    def set_p_state(self, core: int, pstate: int):
        request = HWPRequest(
            minimum_performance=pstate,
            maximum_performance=pstate,
            desired_performance=0,
            energy_performance_preference=0x80 # Balanced
        )
        self.set_hwp_request(core, request)

    @staticmethod
    def _read_msr(core: int, msr: int) -> int | None:
        msr_file = f"/dev/cpu/{core}/msr"
        try:
            with open(msr_file, 'rb') as f:
                f.seek(msr)
                value = f.read(8)
                return struct.unpack('Q', value)[0]
        except IOError as e:
            print(f"Error reading MSR {msr:#x} on core {core}: {e}")
            return None

    @staticmethod
    def _write_msr(core: int, msr: int, value: int):
        msr_file = f"/dev/cpu/{core}/msr"
        try:
            with open(msr_file, 'wb') as f:
                f.seek(msr)
                f.write(struct.pack('Q', value))
        except IOError as e:
            print(f"Error writing MSR {msr:#x} on core {core}: {e}")