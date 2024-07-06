# ARDIS
A.R.D.I.S -  Application Resource Distribution and Integrated Supervision

This project is a Python-based system workload executor designed to run real application workloads on specific system cores. It not only allows for the execution of real applications but also tracks their execution time and controls and monitors the specific cores on which the applications are running.

## Features

- **Real Application Execution**: Executes real workloads (applications) on specified system cores, allowing for precise performance testing.
- **Execution Time Tracking**: Monitors and logs the execution time of each application, providing insights into performance characteristics.
- **Core Specific Execution Control and Monitoring**: Controls and tracks which core an application is executing on, enabling detailed performance analysis.
- **Dynamic Workload Mapping**: Generates random mappings of unique applications to system cores, simulating various workload scenarios.

## Requirements

- Python 3.x
- Administrative privileges may be required on some systems to control and monitor core-specific execution.

## Installation

1. Clone the repository to your local machine.
2. Ensure Python 3.x is installed on your system.
3. Install any dependencies if required (refer to `requirements.txt` if available).

## Usage

To run the workload executor, navigate to the project directory and execute:

```bash
python run.py