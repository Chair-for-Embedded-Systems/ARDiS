# ARDiS
ARDiS: <u>A</u> Po<u>r</u>table and Unifie<u>d</u> Resource Management Framework <u>i</u>n Real Hardware <u>S</u>ystems

This project is a Python-based system workload executor designed to run real application workloads on specific system cores. It not only allows for the execution of real applications but also tracks their execution time and controls and monitors the specific cores on which the applications are running.

## Publication
Details of the ARDiS Framework can be found in the original paper in TODAES'26 paper.

Please consider citing this paper in your work if you find this tool useful in your research:

> Mohammed Bakr Sikal, Jeferson Gonzalez-Gomez, Andreas Noebel, Heba Khdr, and Joerg Henkel. 2026. **ARDiS: A Portable and Unified Resource Management Framework in Real Hardware Systems**. ACM Trans. Des. Autom. Electron. Syst. Just Accepted (January 2026). https://doi.org/10.1145/3793861

## Features
- **Real-world Execution**: Runs actual applications on real hardware rather than relying on simulations.

- **Comprehensive Monitoring**: Collects performance counters for both the system and applications, enabling detailed performance analysis.

- **Flexible Granularity**: Supports monitoring at different levels, including per-core, per-application, and per-thread.

- **Native Benchmark Support**: Built-in integration for PARSEC and SPEC suites, including support for multi-threading and multi-instancing.

- **Custom Binaries**: Ability to integrate and run any user-defined binary.

- **Dynamic Resource Management**: Real-time adjustment of common management "knobs" such as Scheduling, DVFS, Mapping, and Migration.

- **In-Memory Data Structures**: Optimized internal structures to support low-latency, online decision-making.

- **Modular Policy Design**: Decoupled architecture to accelerate the prototyping of new management strategies.

- **Declarative and Reproducible**: Ensures experiments are easy to define and replicate exactly, facilitating consistent research results.

- **Post-processing Library**: Includes tools to easily analyze and interpret experiment results out of the box.

## Publication
ARDiS: <u>A</u> Po<u>r</u>table and Unifie<u>d</u> Resource Management Framework <u>i</u>n Real Hardware <u>S</u>ystems

> Sikal, González-Gómez, Nöbel, Khdr and Henkel **"ARDiS: A Portable and Unified Resource Management
Framework in Real Hardware Systems"** ACM TODAES <mark>Add location in journal<mark>

[ACM Digital Library](<mark>Add link to publication<mark>)

## Requirements

- Python >= 3.10
- Administrative privileges may be required on some systems to control and monitor core-specific execution.

## Quick Start
1. Clone the repository to your local machine:
```bash 
git clone git@github.com:Chair-for-Embedded-Systems/ARDiS.git
```
2. Install ARDiS:
``` bash
cd ARDiS && ./setup.sh
```
3. Install benchmark suits (see [Installation](./docs/installation.md#2-installing-benchmark-suites) for more details). This step can be skipped if an existing benchmark installation is to be used:
``` bash
# Installs PARSEC benchmark suite in the ./benchmarks directory
./tools/parsec_build_container/install.sh benchmarks

# Verify that the installation was successful
cd benchmarks/parsec-3.0/ && . env.sh && cd - && parsecmgmt -a status
```
4. Create an ARDiS configuration file using the Automatic Configuration Generator (see [Configuration](./docs/configuration.md) for more details):
```
python3 -m ardis.utils.autoconfig.run
```

## Usage

To run the workload executor, navigate to the project directory and execute:

``` bash
python run.py
```

### Exploring the Examples

The `examples/` directory contains various scripts demonstrating the core features of ARDiS. These serve as a reference for understanding the capabilities and implementation patterns of the framework.
