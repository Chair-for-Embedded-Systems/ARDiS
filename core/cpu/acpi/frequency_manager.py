from core.cpu.frequency_manager import CPUFrequencyManager

class ACPIFrequencyManager(CPUFrequencyManager):
    
    """
    Manages CPU frequency using the ACPI cpufreq driver.
    
    - `strict_mode`: If True, only allows setting frequencies that are supported by the driver.
    If False, will warn but still attempt to set unsupported frequencies.
    """

    def __init__(
        self,
        clock_domains: list[set[int]],
        strict_mode: bool
    ) -> None:
        super().__init__(clock_domains=clock_domains)
        self.__strict_mode = strict_mode

        # Scaling driver is shared across all cores, so we can just check the first core
        scaling_driver = self.get_scaling_driver(core=0)
        if scaling_driver != "acpi-cpufreq":
            raise EnvironmentError(f"ACPI Frequency Manager requires 'acpi-cpufreq' driver, found '{scaling_driver}' instead.")
        
        # Obtain allowed frequency range from the cores
        self._allowed_frequencies: dict[int, set[int]] = {}
        for core in self.cores:
            available_freqs = self.get_available_frequencies(core)
            if available_freqs is None:
                raise EnvironmentError(f"Could not determine available frequencies for core {core}.")
            self._allowed_frequencies[core] = set(available_freqs)

        # Save the initial state of all cores
        self._save_initial_state()

        # Disable boosting if available
        self._initial_boost_state = self.get_boost_state()
        if self._initial_boost_state is True:
            self._set_boost_state(False)

    def set_cpu_freq(self, core: int, frequency_mhz: int):
        freq_khz = frequency_mhz * 1000
        
        # Check if the requested frequency is allowed for the core
        if freq_khz not in self._allowed_frequencies.get(core, set()):
            if self.__strict_mode:
                raise ValueError(
                    f"Cannot set frequency {frequency_mhz} MHz for core {core}. "
                    f"Allowed frequencies: {[f//1000 for f in self._allowed_frequencies.get(core, set())]}"
                )
            else:
                print(
                    f"[Warning] Frequency {frequency_mhz} MHz is not supported for core {core}.\n"
                    f"Allowed frequencies: {[f//1000 for f in self._allowed_frequencies.get(core, set())]}.\n"
                    "Passing the request to the driver anyway, the behavior is undefined."
                )

        # Utilize default implementation from base class
        super().set_cpu_freq(core, frequency_mhz)

    def get_cpu_freq(self, core: int) -> float:
        return super().get_cpu_freq(core)

    def restore_initial_state(self):
        # Restore initial boost state if it was changed
        if self._initial_boost_state is not None:
            self._set_boost_state(self._initial_boost_state)
        return super().restore_initial_state()

if __name__ == "__main__":
    clock_domain = [{0,1}, {2,3}, {4,5}, {6,7}, {8,9}, {10,11}, {12,13}, {14,15}, {16,17}, {18,19}, {20,21}, {22,23}]
    frequency_manager = ACPIFrequencyManager(clock_domains=clock_domain)
    frequency_manager.set_cpu_freq(0, 3800)
    frequency_manager.set_cpu_freq(4, 3800)
    
    for core in frequency_manager.cores:
        frequency = frequency_manager.get_cpu_freq(core)
        min_freq, max_freq = frequency_manager.get_scaling_limits(core) # type: ignore
        governor = frequency_manager.get_governor(core)
        print(f"Core {core}: Frequency: {frequency} MHz, Min: {min_freq} kHz, Max: {max_freq} kHz, Governor: {governor}")