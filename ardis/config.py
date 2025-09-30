import os

RESULTS_FOLDER="./results"
MOTIVATIONAL_RESULTS_FOLDER="./results/motivational"
OVERHEAD_RESULTS_FOLDER="./results/overhead"
EVALUATION_FOLDER="./results/evaluation"
TRAINING_RESULTS_FOLDER="./results/training"
SINGLE_RESULTS_FOLDER="./results/singles"
UTILS_DIR="./utils"
PLOTS_FOLDER="./plots"

PARSECBASE = "/home/kg3813/Subjects/RealHardware/parsec-3.0/"
SPECPBASE = "/home/kg3813/Subjects/RealHardware/cpu2006/"
SPEC_CONFIGFILE = "mytest.cfg"

ROOTPATH=os.getcwd()
RUNTIME_TEMP = "/tmp/ardis_runtime_data"
DEBUG = False
#DEBUG = True
# List of available applications on the system

spec_apps = [
    'spec-GemsFDTD',
    #'spec-gcc',
    'spec-milc',
    'spec-bzip2',
    'spec-sphinx',
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
    'parsec.blackscholes', 
    'parsec.bodytrack',
    'parsec.canneal',
    #'parsec-facesim',
    #'parsec-ferret',
    #'parsec-netferret',
    'parsec.fluidanimate',
    #'parsec-freqmine',
    'parsec.dedup',
    'parsec.streamcluster',
    #'parsec-netstreamcluster',
    #'parsec-swaptions',
    #'parsec-vips',
    #'parsec-x264',
    'splash2x.barnes',
    #'parsec-netdedup',
    #'parsec-splash2x.cholesky',
    'splash2x.fft',
    #'parsec-splash2x.fmm',
    'splash2x.lu_cb',
    'splash2x.lu_ncb',
    'splash2x.ocean_cp',
    'splash2x.ocean_ncp',
    'splash2x.radiosity',
    'splash2x.radix',
    'splash2x.water_nsquared',
    'splash2x.water_spatial'
]

parsec_network_apps = [
    'parsec-netdedup', 
    'parsec-netferret',
    'parsec-netstreamcluster',
    'parsec-uptcpip',
]
# Number of cores in the system
system_cores = 24
# Definition of clock domains (sets of cores which share a clock)
clock_domains = [{0, 1}, {2, 3}, {4, 5}, {6, 7}, {8, 9}, {10, 11}, {12, 13}, {14, 15},
                 {16, 17, 18, 19}, {20, 21, 22, 23}]
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
    #"net:net_dev_xmit",
    #"net:netif_receive_skb",
    #"irq:softirq_entry",
    #"irq:softirq_exit",
    #"tcp:tcp_bad_csum",    
    #"tcp:tcp_cong_state_set",
    #"tcp:tcp_destroy_sock",
    #"tcp:tcp_probe",   
    #"tcp:tcp_rcv_space_adjust",
    #"tcp:tcp_receive_reset",
    #"tcp:tcp_retransmit_skb",
    #"tcp:tcp_retransmit_synack",
    #"tcp:tcp_send_reset",
    #"sock:inet_sock_set_state"
]

one_shot_system_wide_events = [
    "power/energy-pkg/",
    "power/energy-cores/",
    "power/energy-psys/",
    "instructions"
]

enable_monitoring = True 