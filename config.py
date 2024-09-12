import os


#RESULTS_FOLDER="./results/characterization_splash2/"
PARSEC_FIXED_FREQ_FOLDER="./results/characterization_parsec/fixed_freqs/"
PARSEC_GOVERNOR_FOLDER="./results/characterization_parsec/governors/"
PARSEC_MIXED_STATIC_FOLDERS= [
                            "./results/characterization_parsec/mixed_1.00e+09_IPJ/",
                            "./results/characterization_parsec/mixed_2.00e+09_IPJ/",
                            "./results/characterization_parsec/mixed_5.00e+08_IPJ/",
                            "./results/characterization_parsec/mixed_8.00e+08_IPJ/",
                            #"./results/characterization_parsec/mixed_2.00e+10_IPJ/",
                            ]
PARSEC_BASELINE_FOLDER="./results/baselines/"
SCHEDULES="./results/characterization_parsec/fixed_freqs/schedules/"
#RESULTS_FOLDER="./results/baselines/"
#RESULTS_FOLDER="./results/characterization_spec_ref/"
#RESULTS_FOLDER="./results/characterization_spec_train/"
#RESULTS_FOLDER="./results/motivational/ref/"
#RESULTS_FOLDER="./results/motivational/train/"
#RESULTS_FOLDER="./results/motivational/parsec/"
#RESULTS_FOLDER="./results/characterization/"
#RESULTS_FOLDER="./results/repeated_single/"
#RESULTS_FOLDER="./results/exps/"
RESULTS_FOLDER="./results/characterization_parsec/"
TESTING_FOLDER="./tests/"
#RESULTS_FOLDER="./results/characterization_parsec/mixed_5e9_EDP/"
EVALUATION_FOLDER="./evaluation/"
EVALUATION_MIXED_FOLDER="./evaluation/ours_with_periodic/"
UTILS_DIR="./utils"
ROOTPATH=os.getcwd()
DEBUG = False
#DEBUG = True
# List of available applications on the system

spec_apps = [
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
    'spec-leslie3d'
]

parsec_apps = [
    'parsec-blackscholes',
    'parsec-bodytrack',
    'parsec-canneal',
    'parsec-dedup',
    #'parsec-netdedup',
    #'parsec-facesim',
    'parsec-ferret',
    #'parsec-netferret',
    'parsec-fluidanimate',
    #'parsec-freqmine',
    'parsec-streamcluster',
    #'parsec-netstreamcluster',
    #'parsec-swaptions',
    #'parsec-vips',
    #'parsec-x264',
    'parsec-splash2x.barnes',
    #'parsec-splash2x.cholesky',
    'parsec-splash2x.fft',
    #'parsec-splash2x.fmm',
    'parsec-splash2x.lu_cb',
    'parsec-splash2x.lu_ncb',
    'parsec-splash2x.ocean_cp',
    'parsec-splash2x.ocean_ncp',
    'parsec-splash2x.radiosity',
    'parsec-splash2x.radix',
    'parsec-splash2x.water_nsquared',
    'parsec-splash2x.water_spatial'
]

# Number of cores in the system
system_cores = 24
# platform specific stuff
intel_p_core_ids = [0, 2, 4, 6, 8, 10, 12, 14]
intel_e_core_ids = [16, 17, 18, 19, 20, 21, 22, 23]
# Number of workloads to run in the experiment
num_workloads = 2
# Interval in seconds to perform actions in the experiment
action_interval = 0.1

# List of cores to use for explicit mapping
explicit_mapping_cores = [2, 4, 17, 23]

# Monitoring parameters
sampling_rate = 100 # in ms

periodic_app_level_events = [
    "instructions",
    "LLC-loads",
    "LLC-load-misses",
    "LLC-stores",
    "LLC-store-misses",
    "cycles",
    "branch-misses",
    "branches"
]

periodic_system_wide_events = [
    "power/energy-pkg/",
    "power/energy-cores/",
    "power/energy-psys/",
]

one_shot_system_wide_events = [
    "power/energy-pkg/",
    "power/energy-cores/",
    "power/energy-psys/",
    "instructions"
]

enable_monitoring = True 