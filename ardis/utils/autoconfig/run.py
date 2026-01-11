import os

from ardis.utils.autoconfig.configure_hardware import configure_hardware
from ardis.utils.autoconfig.configure_parsec import configure_parsec_benchmark
from ardis.utils.autoconfig.configure_spec import configure_spec2006_benchmark
from ardis.utils.autoconfig.configure_defaults import configure_exp_defaults

CONFIG_FOLDER = os.path.join(os.path.dirname(__file__), '../../../configs/')

def main():
    # List config foles in the configs directory
    config_files = [f for f in os.listdir(CONFIG_FOLDER) if f.endswith('.ini')]
    print("Available configuration files:")
    for idx, cfg in enumerate(config_files, start=1):
        print(f"{idx}. {cfg}")

if __name__ == "__main__":
    main()