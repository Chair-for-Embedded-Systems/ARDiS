import ast
import json
import os

from configparser import ConfigParser
import subprocess

class ConfigLoadError(Exception):
    """Something went wrong when loading the configuration file."""
    def __init__(self, message: str) -> None:
        super().__init__(message)

class ConfigOptionError(Exception):
    """An invalid option was specified in the configuration file."""
    def __init__(self, message: str) -> None:
        super().__init__(message)

class ARDISConfigParser:

    _CONFIG_FOLDER = os.path.join(os.path.dirname(__file__), '../../configs/')
    _DEFAULT_CONFIG_NAME = "ardis-config.ini"

    @staticmethod
    def _default_config_file_path() -> str:
        
        # Check if an environment variable is set for the config file
        env_path = os.getenv("ARDIS_CONFIG_FILE")
        if env_path:
            return env_path
        
        # Check for default config file in configs directory
        config_folder = ARDISConfigParser._CONFIG_FOLDER
        config_name = ARDISConfigParser._DEFAULT_CONFIG_NAME
        potential_configs = os.listdir(ARDISConfigParser._CONFIG_FOLDER)
        if ARDISConfigParser._DEFAULT_CONFIG_NAME in potential_configs:
            return os.path.join(config_folder, config_name)
        
        raise ConfigLoadError(
            "No configuration file specified!\n"
            f"Either set the ARDIS_CONFIG_FILE environment variable or place a configuration file named '{config_name}' in the 'configs' directory."
        )

    def __init__(self, config_file: str | None = None) -> None:
        
        if config_file is None:
            config_file = self._default_config_file_path()
        
        # Check if file exists
        try:
            with open(config_file, 'r') as file:
                self.config_data = file.read()
        except FileNotFoundError:
            raise ConfigLoadError(f"Configuration file '{config_file}' not found.")
        except Exception as e:
            raise Exception(f"An error occurred while reading the configuration file: {e}")
        
        self.__parse_config()
    
    def __parse_config(self) -> None:
        config = ConfigParser()
        config.read_string(self.config_data)

        self.__parse_hardware_section(config)
        self.__parse_software_section(config)
        self.__parse_parsec_section(config)
        self.__parse_spec2006_section(config)
        self.__parse_experiment_section(config)
    
    def __parse_hardware_section(self, config: ConfigParser) -> None:
        section = "Hardware"
        
        if not config.has_section(section):
            raise ConfigOptionError(f"Missing '{section}' section in configuration file.")
        
        self.core_count = config.getint(section, "core_count")
        
        clock_domains_raw = config.get(section, "clock_domains")
        self.clock_domains: list[set[int]] = ast.literal_eval(clock_domains_raw)

    def __parse_software_section(self, config: ConfigParser) -> None:
        section = "Software"
        
        if not config.has_section(section):
            raise ValueError(f"Missing '{section}' section in configuration file.")
        self.temp_data_dir = config.get(section, "temp_data_dir")

    def __parse_parsec_section(self, config: ConfigParser) -> None:
        section = "Parsec_Benchmark"
        if not config.has_section(section):
            raise ValueError(f"Missing '{section}' section in configuration file.")
        
        self.parsec_enabled = config.getboolean(section, "enabled", fallback=False)

        # Initialize with empty values if not enabled
        if not self.parsec_enabled:
            self.parsec_base_dir = ""
            self.parsec_available_packages = []
            return
        
        self.parsec_base_dir = config.get(section, "benchmark_base_dir")
        # Check if base_dir exists
        if not os.path.isdir(self.parsec_base_dir):
            raise ConfigOptionError(f"Parsec base directory '{self.parsec_base_dir}' does not exist.")

        self.parsec_available_packages_raw = config.get(section, "available_packages")
        self.parsec_available_packages: list[str] = self.parsec_available_packages_raw.strip().split()

    def __parse_spec2006_section(self, config: ConfigParser) -> None:
        section = "Spec2006_Benchmark"
        if not config.has_section(section):
            raise ConfigOptionError(f"Missing '{section}' section in configuration file.")
        
        # Check if SPEC2006 benchmarking is enabled
        self.spec2006_enabled = config.getboolean(section, "enabled", fallback=False)
        
        # Initialize with empty values if not enabled
        if not self.spec2006_enabled:
            self.spec2006_base_dir = ""
            self.spec2006_config_name = ""
            self.spec2006_available_packages = []
            return
        
        self.spec2006_base_dir = config.get(section, "benchmark_base_dir")
        # Check if base_dir exists
        if not os.path.isdir(self.spec2006_base_dir):
            raise ConfigOptionError(f"SPEC2006 base directory '{self.spec2006_base_dir}' does not exist.")
        
        self.spec2006_config_name = config.get(section, "config_file")
        # Check if config file exists
        config_path = os.path.join(self.spec2006_base_dir, "config", self.spec2006_config_name)
        if not os.path.isfile(config_path):
            raise ConfigOptionError(f"SPEC2006 configuration file '{config_path}' does not exist.")
        
        self.spec2006_available_packages_raw = config.get(section, "available_packages")
        self.spec2006_available_packages: list[str] = self.spec2006_available_packages_raw.strip().split()

    def __parse_experiment_section(self, config: ConfigParser) -> None:
        section = "Experiment_Defaults"
        if not config.has_section(section):
            raise ConfigOptionError(f"Missing '{section}' section in configuration file.")
        
        self.action_interval_sec = config.getfloat(section, "action_interval_sec")
        self.sampling_interval_ms = config.getint(section, "sampling_interval_ms")
        
        periodic_app_level_events_raw = config.get(section, "periodic_app_level_events")
        self.periodic_app_level_events: list[str] = periodic_app_level_events_raw.strip().split()
        
        periodic_system_wide_events_raw = config.get(section, "periodic_system_wide_events")
        self.periodic_system_wide_events: list[str] = periodic_system_wide_events_raw.strip().split()
        
        one_shot_system_wide_events_raw = config.get(section, "one_shot_system_wide_events")
        self.one_shot_system_wide_events: list[str] = one_shot_system_wide_events_raw.strip().split()

        # Validate perf events (optional, can be expanded later)
        all_events = self.periodic_app_level_events + \
                     self.periodic_system_wide_events + \
                     self.one_shot_system_wide_events
        
        self.__validate_perf_events(all_events)

    def __validate_perf_events(self, events: list[str]) -> None:
        # Obtain list of valid perf events (run `perf list -j` command)
        process = subprocess.Popen(['perf', 'list', '-j'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            raise Exception(f"Failed to retrieve perf events: {stderr.strip()}")
        
        # Convert output to json and extract event names
        valid_events: set[str] = set()
        try:
            json_data = json.loads(stdout)
            for event in json_data:
                if event.get('EventName'):
                    valid_events.add(event['EventName'])
                if event.get('EventAlias'):
                    valid_events.add(event['EventAlias'])
        except json.JSONDecodeError:
            raise Exception("Failed to parse perf list output as JSON.")

        # Check if provided events are valid
        invalid_events : set[str] = {event for event in events if event not in valid_events}
        if invalid_events:
            raise ConfigOptionError(
                f"The following perf events are invalid or not supported on this system: {invalid_events}\n"
                "Some events may not be available because they require root privileges\n"
                "Please check 'perf list' output for valid events and update the configuration file accordingly."
            )

    def print_config(self) -> None:
        print("ARDIS Configuration:")
        print(f"Core Count: {self.core_count}")
        print(f"Clock Domains: {self.clock_domains}")
        print(f"Parsec Base Directory: {self.parsec_base_dir}")
        print(f"SPEC2006 Base Directory: {self.spec2006_base_dir}")
        print(f"SPEC2006 Config Name: {self.spec2006_config_name}")
        print(f"Temporary Data Directory: {self.temp_data_dir}")
        print(f"Action Interval (sec): {self.action_interval_sec}")
        print(f"Sampling Interval (ms): {self.sampling_interval_ms}")
        print(f"Periodic App Level Events: {self.periodic_app_level_events}")
        print(f"Periodic System Wide Events: {self.periodic_system_wide_events}")
        print(f"One Shot System Wide Events: {self.one_shot_system_wide_events}")

if __name__ == "__main__":
    CONFIG_PATH = "./configs/ardis-config.ini"
    parser = ARDISConfigParser(CONFIG_PATH)
    print(parser.parsec_available_packages)