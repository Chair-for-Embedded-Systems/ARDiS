from ardis.config import *
import struct
import subprocess

MSR_HWP_REQUEST = 0x774

class CPUFrequencyManager:
    def __init__(self, min_frequency, max_frequency, governor="userspace"):
        self.cores = list(range(system_cores))
        self.governor = governor
        if self.governor == "userspace":
            self.__set_pstate_status_to_passive()
            self.__disable_thermald()
        else:
            # TODO: Make sure this is reset at the end of the experiment
            self.set_frequency_limits(min_frequency, max_frequency)
        self.__set_governor_to(governor)
        

    def __set_pstate_status_to_passive(self):
        pstate_status_path = "/sys/devices/system/cpu/intel_pstate/status"
        try:
            with open(pstate_status_path, 'w') as f:
                f.write("passive")
            if DEBUG:
                print("intel_pstate status set to passive")
        except IOError as e:
                print(f"Failed to set intel_pstate status to passive: {e}")

    def __set_governor_to(self, governor):
        for core in self.cores:
            governor_path = f"/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_governor"
            try:
                with open(governor_path, 'w') as f:
                    f.write(governor)
                if DEBUG:
                    print(f"Governor of core {core} set to {governor}")
            except IOError as e:
                if DEBUG:
                    print(f"Failed to set governor for core {core}: {e}")

    def __disable_thermald(self):
        command = ['sudo', 'systemctl', 'stop', 'thermald']
        try:
            subprocess.run(command, check=True)
            if DEBUG:
                print("thermald service stopped")
        except subprocess.CalledProcessError as e:
            if DEBUG:
                print(f"Failed to stop thermald service: {e}")

    def __read_msr(self, core, msr):
        msr_file = f"/dev/cpu/{core}/msr"
        try:
            with open(msr_file, 'rb') as f:
                f.seek(msr)
                value = f.read(8)
                return struct.unpack('Q', value)[0]
        except IOError as e:
            if DEBUG:
                print(f"Error reading MSR {msr:#x} on core {core}: {e}")
            return None

    def __write_msr(self, core, msr, value):
        msr_file = f"/dev/cpu/{core}/msr"
        try:
            with open(msr_file, 'wb') as f:
                f.seek(msr)
                f.write(struct.pack('Q', value))
        except IOError as e:
            if DEBUG:
                print(f"Error writing MSR {msr:#x} on core {core}: {e}")

    def __frequency_to_pstate(self, core, frequency):
        # m = (max_frequency - min_frequency)/len(pcore_action_to_pstate)
        #TODO: should be changed based on processor capabilities and configuration 
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
            if DEBUG:
                print(f"Frequency: {frequency} MHz, P-state index: {pstate_index}, P-state value: {pcore_action_to_pstate[pstate_index]}")
            pstate = pcore_action_to_pstate[min(pstate_index, len(pcore_action_to_pstate) - 1)]
        else:  # E-core handling
            pstate = int(frequency*1000 / scaling_factor_ecore)
            if DEBUG:
                print(f"Frequency: {frequency} MHz, P-state value: {pstate}")
        
        return pstate

    

    def setFrequency(self, core, frequency):
        pstate = self.__frequency_to_pstate(core, frequency)
        hwp_request = self.__read_msr(core, MSR_HWP_REQUEST)
        if hwp_request is not None:
            hwp_request = (
            (pstate & 0xFF) |                    # Minimum Performance
            ((pstate & 0xFF) << 8) |             # Maximum Performance
            ((0x80 & 0xFF) << 24)  # Energy Performance Preference
            )

            #If it's a p-core. let's write to both logical cores
            if core  in intel_p_core_ids:
                # this case, due to hyperthreading, we need to write to the other logical core
                extra_core = core + 1 if core %2 == 0 else core - 1
                if DEBUG:
                    print("Setting pstate to", pstate, "for cores", core, extra_core)
                self.__write_msr(core, MSR_HWP_REQUEST, hwp_request)
                self.__write_msr(extra_core, MSR_HWP_REQUEST, hwp_request)
            # if it's an e-core, we need to write to all cores from the cluster   
            elif core in intel_e_core_ids:
                #TODO: check batch write
                if core < intel_e_core_ids[4]:
                    if DEBUG:
                        print(f"Original HWP_REQUEST value: {hwp_request:#x}")
                        print("Setting pstate to", pstate, "for cores", intel_e_core_ids[:4])
                    self.__write_msr(intel_e_core_ids[0], MSR_HWP_REQUEST, hwp_request)
                    self.__write_msr(intel_e_core_ids[1], MSR_HWP_REQUEST, hwp_request)
                    self.__write_msr(intel_e_core_ids[2], MSR_HWP_REQUEST, hwp_request)
                    self.__write_msr(intel_e_core_ids[3], MSR_HWP_REQUEST, hwp_request)
                else:
                    if DEBUG:
                        print(f"Original HWP_REQUEST value: {hwp_request:#x}")
                        print("Setting pstate to", pstate, "for cores", intel_e_core_ids[4:])
                    self.__write_msr(intel_e_core_ids[4], MSR_HWP_REQUEST, hwp_request)
                    self.__write_msr(intel_e_core_ids[5], MSR_HWP_REQUEST, hwp_request)
                    self.__write_msr(intel_e_core_ids[6], MSR_HWP_REQUEST, hwp_request)
                    self.__write_msr(intel_e_core_ids[7], MSR_HWP_REQUEST, hwp_request)

            # Verify the write
            if DEBUG:
                new_hwp_request = self.__read_msr(core, MSR_HWP_REQUEST)
                print(f"Updated HWP_REQUEST value: {new_hwp_request:#x}")

    def set_frequency_limits(self, min_freq_mhz, max_freq_mhz):
        """
        Set the minimum and maximum frequencies for all cores.
        :param min_freq_mhz: Minimum frequency in MHz.
        :param max_freq_mhz: Maximum frequency in MHz.
        """
        # Convert MHz to kHz
        min_freq_khz = min_freq_mhz * 1000
        max_freq_khz = max_freq_mhz * 1000

        for core in self.cores:
            min_freq_path = f"/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_min_freq"
            max_freq_path = f"/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_max_freq"
            
            try:
                # Set the minimum frequency
                with open(min_freq_path, 'w') as f:
                    f.write(str(min_freq_khz))
                if DEBUG:
                    print(f"Minimum frequency for core {core} set to {min_freq_mhz} MHz ({min_freq_khz} kHz)")
                
                # Set the maximum frequency
                with open(max_freq_path, 'w') as f:
                    f.write(str(max_freq_khz))
                if DEBUG:
                    print(f"Maximum frequency for core {core} set to {max_freq_mhz} MHz ({max_freq_khz} kHz)")
            
            except IOError as e:
                print(f"Failed to set frequency limits for core {core}: {e}")


# Example usage:
# manager = CPUFrequencyManager(governor="performance")  # Set the desired governor, e.g., "ondemand", "powersave"
# manager.setFrequency(0, 2000)  # Example of setting frequency to 2000 MHz for core 0