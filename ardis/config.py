import os
from ardis.utils.config_parser import ARDISConfigParser

# Load the configuration 
# Precenedence in descending order:
#   1. File parameter to ARDISConfigParser constructor
#   2. Environment variable ARDIS_CONFIG_FILE
#   3. Default config file in `configs/ardis-config.ini` directory
ac = ARDISConfigParser()

########################################
# Hardware and Software Configurations #
########################################

# Number of cores in the system
system_cores: int = ac.core_count
# Definition of clock domains (sets of cores which share a clock)
clock_domains: list[set[int]] = ac.clock_domains

RUNTIME_TEMP_DIR: str = ac.temp_data_dir

############################
# Benchmark Configurations #
############################
PARSECBASE: str = ac.parsec_base_dir
SPECPBASE: str = ac.spec2006_base_dir
SPEC_CONFIGFILE: str = ac.spec2006_config_name

parsec_installed: bool = ac.parsec_enabled
spec2006_installed: bool = ac.spec2006_enabled

spec_apps: list[str] = ac.spec2006_available_packages
parsec_apps: list[str] = ac.parsec_available_packages
parsec_network_apps: list[str] = [
    'parsec-netdedup', 
    'parsec-netferret',
    'parsec-netstreamcluster',
    'parsec-uptcpip',
]

#################################
# Experiment Default Parameters #
#################################

# Interval in seconds to perform actions in the experiment
action_interval_sec: float = ac.action_interval_sec

# Monitoring parameters
sampling_rate_ms: int = ac.sampling_interval_ms
enable_monitoring: bool = True 

# Perf events to monitor
periodic_app_level_events = ac.periodic_app_level_events
periodic_system_wide_events = ac.periodic_system_wide_events
one_shot_system_wide_events = ac.one_shot_system_wide_events


#########################
# Custom configurations #
#########################
DEBUG = False

ROOTPATH=os.getcwd()
RESULTS_FOLDER="./results"
MOTIVATIONAL_RESULTS_FOLDER="./results/motivational"
OVERHEAD_RESULTS_FOLDER="./results/overhead"
EVALUATION_FOLDER="./results/evaluation"
TRAINING_RESULTS_FOLDER="./results/training"
SINGLE_RESULTS_FOLDER="./results/singles"
UTILS_DIR="./utils"
PLOTS_FOLDER="./plots"

# platform specific stuff
intel_p_core_ids = [0, 2, 4, 6, 8, 10, 12, 14]
intel_e_core_ids = [16, 17, 18, 19, 20, 21, 22, 23]
intel_e_core_ids_cluster_1 = [16, 17, 18, 19]
intel_e_core_ids_cluster_2 = [20, 21, 22, 23]

# Number of workloads to run in the experiment
num_workloads = 2

# List of cores to use for explicit mapping
explicit_mapping_cores = [2, 4, 17, 23]
