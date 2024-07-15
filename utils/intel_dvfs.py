import os
import struct
import subprocess

MSR_HWP_REQUEST = 0x774

class CPUFrequencyManager:
    def __init__(self, cores):
        self.cores = cores
        self.set_pstate_status_to_passive()
        self.set_governor_to_userspace()
        self.disable_thermald()

    def set_pstate_status_to_passive(self):
        pstate_status_path = "/sys/devices/system/cpu/intel_pstate/status"
        try:
            with open(pstate_status_path, 'w') as f:
                f.write("passive")
            print("intel_pstate status set to passive")
        except IOError as e:
            print(f"Failed to set intel_pstate status to passive: {e}")

    def set_governor_to_userspace(self):
        for core in self.cores:
            governor_path = f"/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_governor"
            try:
                with open(governor_path, 'w') as f:
                    f.write("userspace")
                print(f"Governor of core {core} set to userspace")
            except IOError as e:
                print(f"Failed to set governor for core {core}: {e}")

    def disable_thermald(self):
        command = ['sudo', 'systemctl', 'stop', 'thermald']
        try:
            subprocess.run(command, check=True)
            print("thermald service stopped")
        except subprocess.CalledProcessError as e:
            print(f"Failed to stop thermald service: {e}")

    def read_msr(self, core, msr):
        msr_file = f"/dev/cpu/{core}/msr_safe"
        try:
            with open(msr_file, 'rb') as f:
                f.seek(msr)
                value = f.read(8)
                return struct.unpack('Q', value)[0]
        except IOError as e:
            print(f"Error reading MSR {msr:#x} on core {core}: {e}")
            return None

    def write_msr(self, core, msr, value):
        msr_file = f"/dev/cpu/{core}/msr_safe"
        try:
            with open(msr_file, 'wb') as f:
                f.seek(msr)
                f.write(struct.pack('Q', value))
        except IOError as e:
            print(f"Error writing MSR {msr:#x} on core {core}: {e}")

    def frequency_to_pstate(self, core, frequency):
        scaling_factor_pcore = 0.78741
        scaling_factor_ecore = 1e5
        min_frequency = 800
        max_frequency = 5100
        
        pcore_action_to_pstate = [
            11, 12, 13, 14, 16, 17, 18, 20, 21, 22, 23, 25, 26, 27, 28, 30, 31, 32, 34, 35, 36, 37, 39, 40, 41, 42, 44, 45, 46, 47, 49, 50, 51, 53, 54, 55, 56, 58, 59, 60, 61, 63, 64, 65
        ]
        
        if core < 16:
            if frequency < min_frequency or frequency > max_frequency:
                raise ValueError(f"Frequency {frequency} MHz is out of the valid range ({min_frequency}-{max_frequency} MHz)")

            # Find the nearest P-state for P-core
            pstate_index = int((frequency - min_frequency) * scaling_factor_pcore)
            pstate = pcore_action_to_pstate[min(pstate_index, len(pcore_action_to_pstate) - 1)]
        
        else:  # E-core handling
            pstate = int(frequency / scaling_factor_ecore)
        
        return pstate

    def pstate_to_frequency(self, core, pstate):
        scaling_factor_pcore = 0.78741
        scaling_factor_ecore = 1e5
        min_frequency = 800
        
        pcore_action_to_pstate = [
            11, 12, 13, 14, 16, 17, 18, 20, 21, 22, 23, 25, 26, 27, 28, 30, 31, 32, 34, 35, 36, 37, 39, 40, 41, 42, 44, 45, 46, 47, 49, 50, 51, 53, 54, 55, 56, 58, 59, 60, 61, 63, 64, 65
        ]

        if core < 16:
            if pstate not in pcore_action_to_pstate:
                raise ValueError(f"P-state {pstate} is not in the list of valid P-states")

            pstate_index = pcore_action_to_pstate.index(pstate)
            frequency = int(pstate_index / scaling_factor_pcore + min_frequency)
        else:  # E-core handling
            frequency = int(pstate * scaling_factor_ecore)
        
        return frequency

    def set_frequency(self, core, frequency):
        pstate = self.frequency_to_pstate(core, frequency)
        hwp_request = self.read_msr(core, MSR_HWP_REQUEST)
        if hwp_request is not None:
            print(f"Original HWP_REQUEST value: {hwp_request:#x}")

            # Update the HWP_REQUEST value with the desired P-state
            hwp_request = (hwp_request & ~0xFFFF) | pstate

            self.write_msr(core, MSR_HWP_REQUEST, hwp_request)

            # Verify the write
            new_hwp_request = self.read_msr(core, MSR_HWP_REQUEST)
            print(f"Updated HWP_REQUEST value: {new_hwp_request:#x}")

    def set_frequency_batch(self, frequencies):
        operations = []
        for core, frequency in frequencies.items():
            pstate = self.frequency_to_pstate(core, frequency)
            hwp_request = self.read_msr(core, MSR_HWP_REQUEST)
            if hwp_request is not None:
                hwp_request = (hwp_request & ~0xFFFF) | pstate
                operations.append((core, MSR_HWP_REQUEST, hwp_request))
        
        self.write_msrs_batch(operations)

    def write_msrs_batch(self, operations):
        batch_msr_file = "/dev/cpu/msr_batch"
        try:
            with open(batch_msr_file, 'wb') as f:
                for core, msr, value in operations:
                    f.write(struct.pack('IIQ', core, msr, value))
            print("Batch MSR write successful")
        except IOError as e:
            print(f"Error writing batch MSR: {e}")

    def get_frequency(self, core):
        hwp_request = self.read_msr(core, MSR_HWP_REQUEST)
        if hwp_request is not None:
            print(f"Current HWP_REQUEST value: {hwp_request:#x}")
            frequency = self.pstate_to_frequency(core, hwp_request & 0xFFFF)
            return frequency
        else:
            return None

# Example usage:
if __name__ == "__main__":
    # Simple mode
    cores = [0, 1, 2, 3, 16, 17, 18, 19, 20, 21, 22, 23]  # List of cores to manage
    manager = CPUFrequencyManager(cores)
    core = 0  # Replace with the core number you want to target
    desired_frequency = 2800  # Example frequency value in MHz, replace with the actual desired value

    manager.set_frequency(core, desired_frequency)
    current_frequency = manager.get_frequency(core)
    print(f"Current frequency of core {core}: {current_frequency} MHz")

    # Batch mode
    cores = [0, 1, 2, 3, 16, 17, 18, 19]  # List of cores to manage
    manager = CPUFrequencyManager(cores)
    
    frequencies = {
        0: 2800,
        1: 3000,
        2: 3200,
        3: 3400,
        16: 2800,
        17: 3000,
        18: 3200,
        19: 3400,
    }

    manager.set_frequency_batch(frequencies)
    
    for core in cores:
        current_frequency = manager.get_frequency(core)
        print(f"Current frequency of core {core}: {current_frequency} MHz")


