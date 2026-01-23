
PARSEC_DOWNLOAD_URL="https://web.archive.org/web/20230813020110/http://parsec.cs.princeton.edu/download/3.0/parsec-3.0.tar.gz"
PARSEC_ARCHIVE_NAME="parsec-3.0.tar.gz"

# The location where PARSEC will be installed
PARSEC_BASE_DIR=$(pwd)/parsec-3.0

REMOVE_DOWNLOADED_ARCHIVE_AFTER_EXTRACT=false
DOCKER_CONTAINER_NAME="parsec_build_container"


download_parsec() {
    # Check if PARSEC is already downloaded
    if [ ! -d ${PARSEC_BASE_DIR} ]; then
        echo "Downloading Parsec benchmark suite..."
        wget ${PARSEC_DOWNLOAD_URL} -O ${PARSEC_ARCHIVE_NAME}
    else
        echo "Parsec benchmark suite already downloaded. (Skipping download!)"
    fi
}

extract_parsec() {
    # Check if PARSEC is already extracted
    if [ ! -d ${PARSEC_BASE_DIR} ]; then
        echo "Extracting PARSEC benchmark suite..."
        tar -xzf ${PARSEC_ARCHIVE_NAME}
        if [ ${REMOVE_DOWNLOADED_ARCHIVE_AFTER_EXTRACT} = true ]; then
            rm ${PARSEC_ARCHIVE_NAME}
        fi
    else
        echo "Parsec benchmark suite already extracted. (Skipping extraction!)"
    fi
}

apply_patchs_parsec() {
    echo "Applying patches to PARSEC benchmark suite..."
    
    # Patch some pod files from the ssl library which break the build
    # See https://stackoverflow.com/questions/55451472/building-parsec-dedup-workload-with-parsecmgmt-fails
    cd ${PARSEC_BASE_DIR}/pkgs/libs/ssl/src/doc/apps
    sed -i.bak 's/item \([0-9]\+\)/item C<\1>/g' *
    cd -
    cd ${PARSEC_BASE_DIR}/pkgs/libs/ssl/src/doc/ssl
    sed -i.bak 's/item \([0-9]\+\)/item C<\1>/g' *
    cd -

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
        echo "Verifying Parsec setup..."
        cd ${PARSEC_BASE_DIR}
        . env.sh
        parsecmgmt -a status
        cd -
    else
        echo "Parsec base directory does not exist. Please run the setup first."
    fi
}


run_setup() {
    download_parsec
    extract_parsec
    apply_patchs_parsec
    create_build_container
    run_build_container
    verify_parsec_setup
}

# Uncomment to open an interactive shell in the build container
# run_build_container_interactive

run_setup
