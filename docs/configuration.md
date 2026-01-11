# ARDiS Configuration file
The ARDiS configuration file is a machine-specific `.ini` file. It contains all the hardware and software parameters required to run ARDiS properly.

## Creating a Configuration File

A new configuration file can be created using one of the following methods:

- Manual: Copy and adjust the `ardis-config-example.ini` file, which can be found in the `configs` folder in the root directory.

- Automated: Use the Autoconfig generator script (`autoconfig.py`), which is a guided generation script that assists in creating a valid configuration.

## Selecting a Configuration File

There are two ways ARDiS selects which configuration file to use one explicit and one implicit:

- Explicit (Environment Variable): If the environment variable `ARDIS_CONFIG_FILE` is set, ARDiS will use the file path specified in that variable.

- Implicit (Default Fallback): If no environment variable is set, ARDiS will look for a file named `ardis-config.ini` within the `configs` folder by default.

## Sections
The configuration is divided into functional blocks. Comments can be added using the `#` symbol. For better readability, long lines can be broken into multiple lines provided that the subsequent lines are indented.

### The `Hardware` section
- `core_count`: Number of logical cores in the system
- `clock_domains`: A list of sets, which separates the logical cores into groups with a shared frequency domain. _(For guidance on determining these domains for Intel/AMD, see the [Tips](#tips-for-choosing-the-frequency-domains) section below.)_

### The `Software` section
- `temp_data_dir`: Location at which ARDiS stores temporary runtime data like e.g. runtime data of the benchmarks. (Default: `/tmp/ardis_runtime_data`)

### The `Parsec_Benchmark` section
All parameter related to the PARSEC benchmark suite
- `benchmark_base_dir`: The base directory of the PARSEC benchmark suite
- `available_packages`: List of available/compiled packages on the system

### The `Spec_Benchmark` section
All parameters related to the SPEC2006 CPU benchmark suite
- `benchmark_base_dir`: The base directory of the SPEC CPU 2006 installation.
- `config_file`: Name of the SPEC configuration file. This should be located in the `config` folder of the SPEC benchmark installation directory.
- `available_packages`: List of available/compiled packages on the system

### The `Experiment_Defaults` section
This section contains the default parameters for experiments. 

- `action_interval_sec`: Intervall in seconds at which the main controll loop, which is responsible for policy execution, gets invoked.
- `sampling_interval_ms`: The sampling rate for the periodic app level and system level perf events in milliseconds.
- `periodic_app_level_events`: Perf event which will be periodically collected per application.
- `periodic_system_wide_events`: Perf events which will be periodically collected system wide.
- `one_shot_system_wide_events`: Perf events which are one shot collected system wide.

## Tips for choosing the frequency domains

- Logical Core Enumeration: Note that Linux uses different enumeration schemes for Intel and AMD processors regarding Hyper-Threading (SMT):

    - Intel: Logical cores are typically enumerated sequentially per physical core. For example, logical cores 0 and 1 represent the two threads of the first physical core.

    - AMD: All primary threads are usually enumerated first, followed by all sibling threads. On an 8-core AMD processor with SMT, logical cores 0 and 8 belong to the first physical core, while 1 and 9 belong to the second.

- Frequency Domains: The layout of clock_domains should reflect the specific hardware architecture:

    - Intel: Modern Intel CPUs often allow per-core frequency scaling for P-Cores (Performance cores), meaning logical cores 0 and 1 would share a domain. In contrast, E-Cores (Efficiency cores) typically share a frequency domain with other E-Cores within the same cluster.

    - AMD: On AMD processors, voltage is applied per CCX (Core Complex). Consequently, all cores within a single CCX share a common frequency and belong to the same clock domain.

- Cache-Based Heuristic: A reliable way to identify frequency domains is to examine the cache hierarchy (you can get a detailed overview of this mapping by running `lscpu -e`):

    - Intel: Use the L2 cache as a guide. P-Cores have their own private L2 caches, while E-Core clusters share a single L2 cache. This sharing usually aligns with the frequency domain boundaries.

    - AMD: Use the L3 cache as a guide. Since the L3 cache is typically "shared" per CCX/CCD, it serves as an indicator for splitting cores into their respective frequency domains.

- Examples:
    - Intel Core i9 12900
        - Heterogeneous 16 Core CPU 
        - 1 x P-Cluster with 8 P-Cores and 2 x E-Cluster with 4 E-Cores
        - Frequency Doamin:  `[{0,1}, {2,3}, {4,5}, {6,7}, {8,9}, {10,11}, {12,13}, {14,15}, {16,17,18,19}, {20,21,22,23}]`
    
    - AMD Ryzen 7 2700X
        - Homogeneous 8 Core CPU with SMT
        - 1 CCD (with 2 CCX)
        - Frequency Domain: `[{0,1,2,3,8,9,10,11}, {4,5,6,7,12,13,14,15}]` 
        
    - AMD Ryzen 9 3900X
        - Homogeneous 12 Core CPU with SMT
        - 2 CCDs (2 CCX per CCD)
        - Frequency Domains: `{0,1,2,12,13,14}, {3,4,5,15,16,17}, {6,7,8,18,19,20}, {9,10,11,21,22,23}`