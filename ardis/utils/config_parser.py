import ast
import configparser
import os

class ARDISConfigParser:

    def __init__(self, config_file: str) -> None:
        
        # Check if file exists
        try:
            with open(config_file, 'r') as file:
                self.config_data = file.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file '{config_file}' not found.")
        except Exception as e:
            raise Exception(f"An error occurred while reading the configuration file: {e}")
        
        self.config = self.__parse_config()
    
    def __parse_config(self) -> configparser.ConfigParser:
        config = configparser.ConfigParser()
        config.read_string(self.config_data)

        self.__parse_hardware_section(config)
        self.__parse_software_section(config)
        self.__parse_parsec_section(config)
        self.__parse_spec2006_section(config)
        self.__parse_experiment_section(config)

        return config
    
    def __parse_hardware_section(self, config: configparser.ConfigParser) -> None:
        section = "Hardware"
        
        if not config.has_section(section):
            raise ValueError(f"Missing '{section}' section in configuration file.")
        
        self.core_count = config.getint(section, "core_count")
        clock_domains_raw = config.get(section, "clock_domains")
        self.clock_domains: list[set[int]] = ast.literal_eval(clock_domains_raw)

    def __parse_software_section(self, config: configparser.ConfigParser) -> None:
        section = "Software"
        
        if not config.has_section(section):
            raise ValueError(f"Missing '{section}' section in configuration file.")
        self.temp_data_dir = config.get(section, "temp_data_dir")

    def __parse_parsec_section(self, config: configparser.ConfigParser) -> None:
        section = "Parsec_Benchmark"
        if not config.has_section(section):
            raise ValueError(f"Missing '{section}' section in configuration file.")
        
        self.parsec_base_dir = config.get(section, "benchmark_base_dir")
        self.parsec_available_packages_raw = config.get(section, "available_packages")
        self.parsec_available_packages: list[str] = self.parsec_available_packages_raw.strip().split()

    def __parse_spec2006_section(self, config: configparser.ConfigParser) -> None:
        section = "Spec2006Benchmark"
        if not config.has_section(section):
            raise ValueError(f"Missing '{section}' section in configuration file.")
        
        self.spec2006_base_dir = config.get(section, "benchmark_base_dir")
        self.spec2006_config_name = config.get(section, "config_file")
        self.spec2006_available_packages_raw = config.get(section, "available_packages")
        self.spec2006_available_packages: list[str] = self.spec2006_available_packages_raw.strip().split()

    def __parse_experiment_section(self, config: configparser.ConfigParser) -> None:
        section = "Experiment_Defaults"
        if not config.has_section(section):
            raise ValueError(f"Missing '{section}' section in configuration file.")
        
        self.action_interval_ms = config.getint(section, "action_interval_ms")
        self.sampling_interval_ms = config.getint(section, "sampling_interval_ms")
        
        periodic_app_level_events_raw = config.get(section, "periodic_app_level_events")
        self.periodic_app_level_events: list[str] = periodic_app_level_events_raw.strip().split()
        
        periodic_system_wide_events_raw = config.get(section, "periodic_system_wide_events")
        self.periodic_system_wide_events: list[str] = periodic_system_wide_events_raw.strip().split()
        
        one_shot_system_wide_events_raw = config.get(section, "one_shot_system_wide_events")
        self.one_shot_system_wide_events: list[str] = one_shot_system_wide_events_raw.strip().split()

    def print_config(self) -> None:
        print("ARDIS Configuration:")
        print(f"Core Count: {self.core_count}")
        print(f"Clock Domains: {self.clock_domains}")
        print(f"Parsec Base Directory: {self.parsec_base_dir}")
        print(f"SPEC2006 Base Directory: {self.spec2006_base_dir}")
        print(f"SPEC2006 Config Name: {self.spec2006_config_name}")
        print(f"Temporary Data Directory: {self.temp_data_dir}")
        print(f"Action Interval (ms): {self.action_interval_ms}")
        print(f"Sampling Interval (ms): {self.sampling_interval_ms}")
        print(f"Periodic App Level Events: {self.periodic_app_level_events}")
        print(f"Periodic System Wide Events: {self.periodic_system_wide_events}")
        print(f"One Shot System Wide Events: {self.one_shot_system_wide_events}")

if __name__ == "__main__":
    CONFIG_PATH = "/home/uhqql/ARDIS/configs/example-config.ini"
    parser = ARDISConfigParser(CONFIG_PATH)
    print(parser.parsec_available_packages)