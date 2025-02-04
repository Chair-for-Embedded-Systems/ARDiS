import os

RESULTS_FOLDER="./results"
MOTIVATIONAL_RESULTS_FOLDER="./results/motivational"
OVERHEAD_RESULTS_FOLDER="./results/overhead"
EVALUATION_FOLDER="./results/evaluation"
TRAINING_RESULTS_FOLDER="./results/training"
SINGLE_RESULTS_FOLDER="./results/singles"
UTILS_DIR="./utils"
PLOTS_FOLDER="./plots"

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
    'parsec-blackscholes', # excellent trend for hux
    'parsec-bodytrack', # good trend for hux
    'parsec-canneal', # interesting scaling with independent trends for hux
    #'parsec-facesim', # no scaling trend for hux
    #'parsec-ferret',
    #'parsec-netferret',
    'parsec-fluidanimate',
    #'parsec-freqmine', # interesting scaling trend for hux
    'parsec-dedup', # interesting scaling trend for hux
    'parsec-streamcluster',
    #'parsec-netstreamcluster',
    #'parsec-swaptions',
    #'parsec-vips',
    #'parsec-x264',
    'parsec-splash2x.barnes', # excellent trend for hux
    #'parsec-netdedup',
    #'parsec-splash2x.cholesky',
    'parsec-splash2x.fft', # excellent trend for hux
    #'parsec-splash2x.fmm',
    'parsec-splash2x.lu_cb', # good trend for hux
    'parsec-splash2x.lu_ncb', # good trend for hux
    'parsec-splash2x.ocean_cp', # good trend for hux
    'parsec-splash2x.ocean_ncp',
    'parsec-splash2x.radiosity',
    'parsec-splash2x.radix',
    'parsec-splash2x.water_nsquared',  # good trend for hux
    'parsec-splash2x.water_spatial'
]

# Number of cores in the system
system_cores = 24
# platform specific stuff
intel_p_core_ids = [0, 2, 4, 6, 8, 10, 12, 14]
intel_e_core_ids = [16, 17, 18, 19, 20, 21, 22, 23]


intel_e_core_ids_cluster_1 = [16, 17, 18, 19]
intel_e_core_ids_cluster_2 = [20, 21, 22, 23]
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
#scaler paths
ENERGY_SEQUENCE_SCALER_PATH="./ml/energy_sequence_scaler.joblib"
PERFORMANCE_SEQUENCE_SCALER_PATH="./ml/performance_sequence_scaler.joblib"
ENERGY_INSTANT_SCALER_PATH="./ml/energy_instant_scaler.joblib"
PERFORMANCE_INSTANT_SCALER_PATH="./ml/performance_instant_scaler.joblib"
#transformer models
ENERGY_TRANSFORMER_MODEL_PATH="./ml/energy_transformer_model_5steps.keras"
PERFORMANCE_TRANSFORMER_MODEL_PATH="./ml/performance_transformer_model_5steps.keras"
#rnn models
ENERGY_RNN_MODEL_PATH="./ml/energy_rnn_model_5steps.keras"
PERFORMANCE_RNN_MODEL_PATH="./ml/performance_rnn_model_5steps.keras"
#nn models
ENERGY_NN_MODEL_PATH="./ml/energy_nn_model.keras"
PERFORMANCE_NN_MODEL_PATH="./ml/performance_nn_model.keras"
#xgb models
ENERGY_XGB_MODEL_PATH="./ml/energy_xgb_model.keras"
PERFORMANCE_XGB_MODEL_PATH="./ml/performance_xgb_model.keras"
#RF models
ENERGY_RF_MODEL_PATH="./ml/energy_rf_model.keras"
PERFORMANCE_RF_MODEL_PATH="./ml/performance_rf_model.keras"


ML_BASED_MIGRATION_DVFS = True
