from ardis.utils.autoconfig.flows import HardwareConfiguration, ParsecConfiguration, Spec2006Configuration, DefaultConfiurattions

class ConfigWriter:
    
    def __init__(
        self,
        filepath: str,
        hardware_config: HardwareConfiguration,
        parsec_config: ParsecConfiguration,
        spec2006_config: Spec2006Configuration,
        default_config: DefaultConfiurattions
    ) -> None:
        self.filepath = filepath
        self.hardware_config = hardware_config
        self.parsec_config = parsec_config
        self.spec2006_config = spec2006_config
        self.default_config = default_config
    
    def write(self) -> None:
        config_content = self._create_config()
        with open(self.filepath, 'w') as config_file:
            config_file.write(config_content)
        print(f"Configuration file written to: {self.filepath}")

    def _create_config(self) -> str:
        buffer = ""
        buffer = self._write_hardware_section(buffer)
        buffer = self._write_software_section(buffer)
        buffer = self._write_parsec_section(buffer)
        buffer = self._write_spec2006_section(buffer)
        buffer = self._write_default_section(buffer)
        return buffer
    
    def _write_hardware_section(self, buffer: str) -> str:
        buffer += "[Hardware]\n"
        buffer += f"core_count = {self.hardware_config.logical_cores}\n"
        buffer += f"clock_domains = {self.hardware_config.frequency_domains}\n\n"
        return buffer
    
    def _write_software_section(self, buffer: str) -> str:
        default_temp_dir = "/tmp/ardis_runtime_data"
        buffer += "[Software]\n"
        buffer += f"temp_data_dir = {default_temp_dir}\n"
        buffer += "\n"
        return buffer
    
    def _write_parsec_section(self, buffer: str) -> str:
        buffer += "[Parsec_Benchmark]\n"
        buffer += f"benchmark_base_dir = {self.parsec_config.parsec_base_dir}\n"
        buffer += "available_packages = \n"

        enabled_pkgs = self.parsec_config.enabled_packages
        disabled_pkgs = self.parsec_config.disabled_packages
        all_pkgs = enabled_pkgs.union(disabled_pkgs)

        for pkg in sorted(all_pkgs):
            if pkg in enabled_pkgs:
                buffer += f"    {pkg}\n"
            else:
                buffer += f"    # {pkg}\n"
 
        buffer += "\n"
        return buffer
    
    def _write_spec2006_section(self, buffer: str) -> str:
        buffer += "[Spec2006_Benchmark]\n"
        buffer += f"benchmark_base_dir = {self.spec2006_config.spec_base_dir}\n"
        buffer += f"config_file = {self.spec2006_config.spec_config_file}\n"
        buffer += "available_packages = \n"
        
        enabled_pkgs = self.spec2006_config.enabled_packages
        disabled_pkgs = self.spec2006_config.disabled_packages
        all_pkgs = enabled_pkgs + disabled_pkgs
        # Remove leading numbers from package name
        all_pkgs = [pkg.split('.')[1] for pkg in all_pkgs]

        for pkg in sorted(all_pkgs):
            if pkg in enabled_pkgs:
                buffer += f"    {pkg}\n"
            else:
                buffer += f"    # {pkg}\n"
        buffer += "\n"
        return buffer
    
    def _write_default_section(self, buffer: str) -> str:
        buffer += "[Experiment_Defaults]\n"
        buffer += f"sampling_interval_ms = {self.default_config.sampling_interval_ms}\n"
        buffer += f"action_interval_sec = {self.default_config.action_interval_sec}\n\n"
        
        buffer += "periodic_app_level_events = \n"
        for event in self.default_config.periodic_app_level_events:
            buffer += f"    {event}\n"
        buffer += "\n"
        buffer += "periodic_system_wide_events = \n"
        for event in self.default_config.periodic_system_wide_events:
            buffer += f"    {event}\n"
        buffer += "\n"
        buffer += "one_shot_system_wide_events = \n"
        for event in self.default_config.one_shot_system_wide_events:
            buffer += f"    {event}\n"
        buffer += "\n"

        return buffer


if __name__ == "__main__":
    
    hw_config = HardwareConfiguration(
        logical_cores=24,
        frequency_domains=[{0,1}, {2,3}, {4,5,6,7}, {8,9,10,11}, {12,13,14,15}, {16,17,18,19}, {20,21,22,23}],
    )
    parsec_config = ParsecConfiguration(
        parsec_base_dir="/path/to/your/parsec/installation",
        enabled_packages={
            "parsec.blackscholes",
            "parsec.bodytrack"
        },
        disabled_packages={
            "parsec.canneal",
            "parsec.dedup",
            "parsec.facesim",
            "parsec.fluidanimate",
            "parsec.freqmine",
            "parsec.streamcluster",
            "parsec.swaptions",
            "parsec.vips",
            "parsec.x264"
        }
    )
    spec2006_config = Spec2006Configuration(
        spec_base_dir="/path/to/your/spec2006/installation",
        spec_config_file="ardis.cfg",
        enabled_packages=[
            "400.perlbench",
            "401.bzip2",
            "403.gcc",
            "429.mcf",
            "445.gobmk"
        ],
        disabled_packages=[
            "456.hmmer",
            "458.sjeng",
            "462.libquantum",
            "464.h264ref",
            "471.omnetpp",
            "473.astar",
            "483.xalancbmk"
        ]
    )
    default_config = DefaultConfiurattions(
        sampling_interval_ms=100,
        action_interval_sec=5.0,
        periodic_app_level_events=[
            "cycles",
            "instructions",
            "cache-references",
            "cache-misses"
        ],
        periodic_system_wide_events=[
            "power/energy-pkg/",
            "power/energy-cores/",
            "power/energy-psys/"
        ],
        one_shot_system_wide_events=[
            "power/energy-pkg/",
            "power/energy-cores/",
            "power/energy-psys/",
            "instructions"
        ]
    )

    writer = ConfigWriter(
        filepath="configs/ardis-config.ini",
        hardware_config=hw_config,
        parsec_config=parsec_config,
        spec2006_config=spec2006_config,
        default_config=default_config
    )
    print(writer._create_config())