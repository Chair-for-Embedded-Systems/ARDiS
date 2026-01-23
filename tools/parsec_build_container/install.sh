
PARSEC_DOWNLOAD_URL="https://web.archive.org/web/20230813020110/http://parsec.cs.princeton.edu/download/3.0/parsec-3.0.tar.gz"

# Location where the PARSEC archive will be stored
PARSEC_ARCHIVE_FILE=$(pwd)/parsec-3.0.tar.gz
# The location where PARSEC benchmark suite will be installed
PARSEC_BASE_DIR=$(pwd)/parsec-3.0

REMOVE_DOWNLOADED_ARCHIVE_AFTER_EXTRACT=false
DOCKER_CONTAINER_NAME="parsec_build_container"


download_parsec() {
    # Check if PARSEC is already downloaded
    if [ ! -f ${PARSEC_ARCHIVE_FILE} ]; then
        echo "Downloading PARSEC benchmark suite..."
        wget ${PARSEC_DOWNLOAD_URL} -O ${PARSEC_ARCHIVE_FILE}
        
        # Ensure that download was successful before proceeding
        if [ $? -ne 0 ]; then
            echo "Error downloading PARSEC benchmark suite. (Aborting!)"
            echo "Please check that the URL is reachable: ${PARSEC_DOWNLOAD_URL}"
            exit 1
        fi
    else
        echo "PARSEC benchmark suite already downloaded. (Skipping download!)"
    fi
}

extract_parsec() {
    # Check if PARSEC is already extracted and contains the .parsec_unique_file
    if [ ! -d ${PARSEC_BASE_DIR} ] || [ ! -f ${PARSEC_BASE_DIR}/.parsec_unique_file ]; then
        echo "Extracting PARSEC benchmark suite..."

        # Create base directory if it does not exist
        mkdir -p ${PARSEC_BASE_DIR}

        tar -xzvf ${PARSEC_ARCHIVE_NAME} -C $(dirname ${PARSEC_BASE_DIR})

        if [ ${REMOVE_DOWNLOADED_ARCHIVE_AFTER_EXTRACT} = true ]; then
            rm ${PARSEC_ARCHIVE_NAME}
        fi
    else
        echo "PARSEC benchmark suite already extracted. (Skipping extraction!)"
    fi
}

apply_patches_parsec() {
    echo "Applying patches to PARSEC benchmark suite..."
    
    # Store current directory
    CURRENT_DIR=$(pwd)

    # Patch some pod files from the ssl library which break the build
    # See https://stackoverflow.com/questions/55451472/building-parsec-dedup-workload-with-parsecmgmt-fails
    cd ${PARSEC_BASE_DIR}/pkgs/libs/ssl/src/doc/apps \
        && sed -i.bak 's/item \([0-9]\+\)/item C<\1>/g' *\
        && cd -\
        || { echo "Failed to patch apps documentation. (Aborting!)" && exit 1; }
    
    cd ${PARSEC_BASE_DIR}/pkgs/libs/ssl/src/doc/ssl \
        && sed -i.bak 's/item \([0-9]\+\)/item C<\1>/g' *\
        && cd -\
        || { echo "Failed to patch ssl documentation. (Aborting!)" && exit 1; }

    # Restore original directory
    cd ${CURRENT_DIR}

    echo "Patches applied!"
}

create_build_container() {
    echo "Creating Docker build container (you may be prompted for root)..."
    sudo docker build -t ${DOCKER_CONTAINER_NAME} .
}

run_build_container() {
    echo "Running Docker build container..."
    # Splash2 and Splash2x build without any issues
    # Some PARSEC benchmarks fail to build, therefore we build only a subset here
    sudo docker run --rm -v ${PARSEC_BASE_DIR}:/parsec-3.0 --entrypoint=/bin/bash ${DOCKER_CONTAINER_NAME} \
        -c "cd /parsec-3.0 && . env.sh &&\
            parsecmgmt -a build -p splash2 &&\
            parsecmgmt -a build -p splash2x &&\
            parsecmgmt -a build -p parsec.blackscholes &&\
            parsecmgmt -a build -p parsec.bodytrack &&\
            parsecmgmt -a build -p parsec.canneal &&\
            parsecmgmt -a build -p parsec.dedup &&\
            parsecmgmt -a build -p parsec.facesim &&\
            parsecmgmt -a build -p parsec.fluidanimate &&\
            parsecmgmt -a build -p parsec.ferret &&\
            parsecmgmt -a build -p parsec.freqmine &&\
            parsecmgmt -a build -p parsec.raytrace &&\
            parsecmgmt -a build -p parsec.streamcluster
            parsecmgmt -a build -p parsec.vips &&\
            parsecmgmt -a build -p parsec.x264"
            #parsecmgmt -a build -p parsec.netdedup &&\
            #parsecmgmt -a build -p parsec.netferret &&\
            #parsecmgmt -a build -p parsec.netstreamcluster &&\
            #parsecmgmt -a build -p parsec.swaptions &&\
}

run_build_container_interactive() {
    echo "Running Docker build container in interactive mode..."
    sudo docker run --rm -v ${PARSEC_BASE_DIR}:/parsec-3.0 -it --entrypoint=/bin/bash ${DOCKER_CONTAINER_NAME}
}

verify_parsec_setup() {
    if [ -d ${PARSEC_BASE_DIR} ]; then
        echo "Verifying PARSEC setup..."
        cd ${PARSEC_BASE_DIR}
        . env.sh
        parsecmgmt -a status
        cd -
    else
        echo "PARSEC base directory does not exist. Please run the setup first."
    fi
}


run_setup() {
    download_parsec
    extract_parsec
    apply_patches_parsec
    create_build_container
    run_build_container
    verify_parsec_setup
}

# Uncomment to open an interactive shell in the build container
# run_build_container_interactive

run_setup
