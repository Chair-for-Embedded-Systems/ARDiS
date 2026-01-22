# Setup

## 1. Installing ARDiS

### Prerequisites
* Make sure you have installed **pip3** and **python3-venv**.
* No root privileges are required.

### Installation
Run the setup script.
It creates a new virtual environment, installs the `ardis` package and all required dependencies. The `ardis` package will be installed as **editable**, allowing for adjustments to the source code.

```bash
./setup.sh
```

### Post-Installation
After the installation was sucessful, you can load the virtual environment by sourcing the `env.sh` in the root folder of the directory:
```bash
source env.sh
``` 

> [!IMPORTANT]
> While the installation of ARDiS may not require root privileges, running ARDiS certainly does. Be aware that environment variables are generally not passed when calling `sudo`.

## 2. Installing Benchmark Suites
This step is optional but highly recommended. You are not required to install all benchmark suits.

### PARSEC 3.0
The PARSEC (Princeton Application Repository for Shared-Memory Computers) benchmark suite is an open-source collection of diverse workloads designed to evaluate next-generation chip-multiprocessors.

While the original website at [parsec.cs.princeton.edu](http://parsec.cs.princeton.edu/) is no longer available, a [mirror](https://web.archive.org/web/20230813020110/http://parsec.cs.princeton.edu/) is preserved on the Wayback Machine, where the suite and its datasets can still be downloaded.

In the folder `tools/parsec_build_container`, there is a script which assists with obtaining and compiling the benchmark suite.

### SPEC CPU® 2006
The SPEC CPU® 2006 benchmark suite is a proprietary, industry-standardized collection of workloads used to measure and compare compute performance. To obtain the source files and get guidance on installation, please refer to the [Standard Performance Evaluation Corporation (SPEC)](https://www.spec.org/cpu2006/) website.


## 3. Creating an ARDiS configuration file
After ARDiS has been installed, you need to create a machine-specific configuration file.
See [here](configuration.md#creating-a-configuration-file) for more information.