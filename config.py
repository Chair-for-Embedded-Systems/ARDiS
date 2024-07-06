SCRIPTS_DIR="/home/jef/ARDIS/scripts/"
RESULTS_FOLDER="results/"
UTILS_DIR="./utils"

# List of available applications on the system
available_apps = [#'spec-gcc', 'spec-milc', 'spec-bzip2', 'spec-sphinx3', 'spec-astar', 'spec-lbm',
                  #'spec-bwaves', 'spec-mcf', 'spec-zeusmp',  'spec-namd', 'spec-h264ref', 'spec-gobmk',
                  #'spec-povray', 'spec-gromacs', 'spec-cactusADM', 'spec-omnetpp', 'spec-hmmer', 'spec-leslie3d',
                  'parsec-blackscholes', 'parsec-bodytrack', 'parsec-canneal', 'parsec-dedup', 'parsec-facesim',
                  'parsec-ferret', 'parsec-fluidanimate', 'parsec-freqmine', 'parsec-streamcluster',
                  'parsec-swaptions', 'parsec-vips', 
                  #'parsec-x264'
                  ]

# Number of cores in the system
system_cores = 4
workloads = 2