# Installing PARSEC
This utility script automates the retrieval, patching, and compilation of the [PARSEC 3.0](https://acs.ict.ac.cn/baoyg/pub/202203/P020220317735733258528.pdf) Benchmark Suite.

## Prerequisites
- Docker: Ensure the Docker daemon is installed and running.
- Disk Space: At least 10GB of free space is recommended for the archive and build artifacts.
- Internet Connection: Required for the initial download of the PARSEC 3.0 archive.

## How it works
The scripts executes the following steps sequentially
1. Download a PARSEC 3.0 archive (from Internet archive, since the original website is no longer available) to the current directory
2. Extract the downloaded archive in the current directory
3. Apply minor patches to some doc files to prevent build failures
4. Create a docker container which serves as build environment
5. Mount the parsec base folder `parsec-3.0` to the docker container and build all packages
6. Print installation status for all PARSEC packages

## Supported Packages
The script attempts to build all suites included in PARSEC 3.0. Based on the current build environment, the following results are expected:
- SPLASH-2x: All packages
- SPLASH-2: All packages
- PARSEC: All packages except the network packages (`netdedup`, `netferret`, `netstreamcluster`) and `parsec.swaptions`

## Usage
You can start the installation script with the following command:
``` bash
sudo ./install.sh # (sudo is requried to use docker)
```
On modern hardware with a high-speed internet connection, the script typically takes 20–30 minutes to complete.

## Post installation
Once the script finishes successfully, you will see a folder named `parsec-3.0` in your current directory. You can move this folder freely to your desired location.