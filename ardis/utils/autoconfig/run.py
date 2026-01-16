import os

from ardis.utils.autoconfig.flows import *
from ardis.utils.autoconfig.writer import ConfigWriter

# ARDiS auto-configuration utility

CONFIG_FOLDER = os.path.join(os.path.dirname(__file__), '../../../configs/')

def _prompt_config_file_name() -> str:
    
    default_file_name = "ardis-config.ini"

    while True:
        print("\033c", end="")
        print("Config - ARDiS Configuration File\n")
        
        config_file_name = input(f"Enter the name of the configuration file to use (or press Enter for {default_file_name}): ").strip()
        if config_file_name == "":
            config_file_name = default_file_name
        else:
            if not config_file_name.endswith(".ini"):
                config_file_name += ".ini"
        
        # Warn if file does exist and ask for confirmation to overwrite
        if os.path.isfile(os.path.join(CONFIG_FOLDER, config_file_name)):
            while True:
                confirm = input(f"Configuration file '{config_file_name}' already exists. Overwrite? (y/n): ").strip().lower()
                if confirm == 'y':
                    return config_file_name
                if confirm == 'n':
                    break
        else:
            return config_file_name


def main():
    
    # Welcome message and explain flow
    print("\033c", end="")
    print(
        "ARDiS Auto-Configuration Utility\n\n"
        "This utility will guide you through configuring the ARDiS framework for your system.\n\n"
        "This setup includes the following steps:\n"
        "  1. Hardware Configuration\n"
        "  2. Benchmark Configuration (PARSEC and SPEC2006)\n"
        "  3. Experiment Default Parameters\n"
        "  4. Nameing and saving the configuration file\n\n"
        "Tip: You can load the environments for PARSEC and SPEC2006 for a quicker setup.\n\n"
        "Press any key to begin the configuration, you can exit at any time by pressing Ctrl+C"
    )
    input()
        
    # Run configuration flows
    hardware_config = configure_hardware()
    parsec_config = configure_parsec_benchmark()
    spec2006_config = configure_spec2006_benchmark()
    default_config = configure_exp_defaults()

    # Write configuration to file
    config_name = _prompt_config_file_name()
    writer = ConfigWriter(
        filepath=os.path.join(CONFIG_FOLDER, config_name),
        hardware_config=hardware_config,
        parsec_config=parsec_config,
         spec2006_config=spec2006_config,
        default_config=default_config
    )
    writer.write()


if __name__ == "__main__":
    main()