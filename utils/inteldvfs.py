from config import *
import struct
import subprocess

MSR_HWP_REQUEST = 0x774

class CPUFrequencyManager:
    def __init__(self, debug = False):
        self.cores = list(range(system_cores))
        self.__debug = debug
        self.__set_pstate_status_to_passive()
        self.__set_governor_to_userspace()
        self.__disable_thermald()
        

    def __set_pstate_status_to_passive(self):
        pstate_status_path = "/sys/devices/system/cpu/intel_pstate/status"
        try:
            with open(pstate_status_path, 'w') as f:
                f.write("passive")
            if self.__debug:
                print("intel_pstate status set to passive")
        except IOError as e:
                print(f"Failed to set intel_pstate status to passive: {e}")

    def __set_governor_to_userspace(self):
        for core in self.cores:
            governor_path = f"/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_governor"
            try:
                with open(governor_path, 'w') as f:
                    f.write("userspace")
                if self.__debug:
                    print(f"Governor of core {core} set to userspace")
            except IOError as e:
                if self.__debug:
                    print(f"Failed to set governor for core {core}: {e}")

    def __disable_thermald(self):
        command = ['sudo', 'systemctl', 'stop', 'thermald']
        try:
            subprocess.run(command, check=True)
            if self.__debug:
                print("thermald service stopped")
        except subprocess.CalledProcessError as e:
            if self.__debug:
                print(f"Failed to stop thermald service: {e}")

    def __read_msr(self, core, msr):
        msr_file = f"/dev/cpu/{core}/msr"
        try:
            with open(msr_file, 'rb') as f:
                f.seek(msr)
                value = f.read(8)
                return struct.unpack('Q', value)[0]
        except IOError as e:
            if self.__debug:
                print(f"Error reading MSR {msr:#x} on core {core}: {e}")
            return None

    def __write_msr(self, core, msr, value):
        msr_file = f"/dev/cpu/{core}/msr"
        try:
            with open(msr_file, 'wb') as f:
                f.seek(msr)
                f.write(struct.pack('Q', value))
        except IOError as e:
            if self.__debug:
                print(f"Error writing MSR {msr:#x} on core {core}: {e}")

    def __frequency_to_pstate(self, core, frequency):
        # m = (max_frequency - min_frequency)/len(pcore_action_to_pstate)
        scaling_factor_pcore = 97.72727272727273
        scaling_factor_ecore = 1e5
        min_frequency = 800
        max_frequency = 5100
        
        pcore_action_to_pstate = [
            11, 12, 13, 14, 16, 17, 18, 20, 21, 22, 23, 25, 26, 27, 28, 30, 31, 32, 34, 35, 36, 37, 39, 40, 41, 42, 44, 45, 46, 47, 49, 50, 51, 53, 54, 55, 56, 58, 59, 60, 61, 63, 64, 65
        ]
        
        if core < 16:
            if frequency < min_frequency or frequency > max_frequency:
                raise ValueError(f"Frequency {frequency} MHz is out of the valid range ({min_frequency}-{max_frequency} MHz)")
            pstate_index = int((frequency - min_frequency)/scaling_factor_pcore)
            if self.__debug:
                print(f"Frequency: {frequency} MHz, P-state index: {pstate_index}, P-state value: {pcore_action_to_pstate[pstate_index]}")
            pstate = pcore_action_to_pstate[min(pstate_index, len(pcore_action_to_pstate) - 1)]
        else:  # E-core handling
            pstate = int(frequency*1000 / scaling_factor_ecore)
            if self.__debug:
                print(f"Frequency: {frequency} MHz, P-state value: {pstate}")
        
        return pstate

    

    def setFrequency(self, core, frequency):
        pstate = self.__frequency_to_pstate(core, frequency)
        hwp_request = self.__read_msr(core, MSR_HWP_REQUEST)
        if hwp_request is not None:
            if self.__debug:
                print(f"Original HWP_REQUEST value: {hwp_request:#x}")
                print("Setting pstate to", pstate, "for core", core)
            hwp_request = (
            (pstate & 0xFF) |                    # Minimum Performance
            ((pstate & 0xFF) << 8) |             # Maximum Performance
            ((0x80 & 0xFF) << 24)  # Energy Performance Preference
            )

            self.__write_msr(core, MSR_HWP_REQUEST, hwp_request)
            #let's write it also to the other logical core
            if core < 16:
                # this case, due to hyperthreading, we need to write to the other logical core
                extra_core = core + 1 if core %2 == 0 else core - 1
                if self.__debug:
                    print("Setting pstate to", pstate, "for core", extra_core)
                self.__write_msr(extra_core, MSR_HWP_REQUEST, hwp_request)

            # Verify the write
            if self.__debug:
                new_hwp_request = self.__read_msr(core, MSR_HWP_REQUEST)
                print(f"Updated HWP_REQUEST value: {new_hwp_request:#x}")


# # Example usage:
# if __name__ == "__main__":
#     # Simple mode
#     cores = [0, 2, 4, 6, 16, 17, 18, 19, 20, 21, 22, 23]  # List of cores to manage
#     manager = CPUFrequencyManager(cores)
#     core = 0  # Replace with the core number you want to target
#     desired_frequency = 2000  # Example frequency value in MHz, replace with the actual desired value
#     for core in cores:
#         manager.setFrequency(core, desired_frequency)


