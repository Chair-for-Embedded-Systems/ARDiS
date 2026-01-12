# Setup

## With Virtual Environment (Recommended)

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

## Automatic Configuration
After the installation, you need to create a machine-specific configuration file.
See [here](configuration.md#creating-a-configuration-file) for more information.

## Benchmarks

### PARSEC
<mark>TODO: How to install PARSEC</mark>

### SPEC CPU2006
<mark>TODO: How to install SPEC</mark>

