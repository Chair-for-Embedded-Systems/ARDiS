import os

RESULTS_FOLDER="./results/characterization/"
#RESULTS_FOLDER="./results/exps/"
UTILS_DIR="./utils"
ROOTPATH=os.getcwd()
DEBUG = False
#DEBUG = True
# List of available applications on the system

available_apps = [
    'spec-GemsFDTD',
    #'spec-gcc',
    'spec-milc',
    'spec-bzip2',
    'spec-sphinx3',
    'spec-astar',
    'spec-lbm',
    'spec-bwaves',
    'spec-mcf',
    'spec-zeusmp',
    'spec-namd',
    'spec-h264ref',
    'spec-gobmk',
    #'spec-libquantum',
    'spec-povray',
    'spec-gromacs',
    'spec-cactusADM',
    'spec-omnetpp',
    'spec-hmmer',
    'spec-leslie3d',
    #'parsec-blackscholes',
    #'parsec-bodytrack',
    #'parsec-canneal',
    #'parsec-dedup',
    #'parsec-facesim',
    #'parsec-ferret',
    #'parsec-fluidanimate',
    #'parsec-freqmine',
    #'parsec-streamcluster',
    #'parsec-swaptions',
    #'parsec-vips',
    #'parsec-x264'
]

# Number of cores in the system
system_cores = 24
# platform specific stuff
intel_p_core_ids = [2, 4, 6, 8, 10, 12, 14]
intel_e_core_ids = [16, 17, 18, 19, 20, 21, 22, 23]
# Number of workloads to run in the experiment
num_workloads = 2
# Interval in seconds to perform actions in the experiment
action_interval = 0.1

# List of cores to use for explicit mapping
explicit_mapping_cores = [2, 4, 17, 23]

# Monitoring parameters
events_to_track = ["instructions", "cache-misses", "cache-references", "LLC-loads", "LLC-load-misses", "LLC-stores", "LLC-store-misses", "power/energy-pkg/", "power/energy-cores/", "power/energy-psys/"]
enable_monitoring = True 