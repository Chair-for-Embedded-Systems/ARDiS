FROM ubuntu:trusty

# Update the package list to get the old package information
RUN apt-get update

# Install all necessary packages for building PARSEC
RUN apt-get install -y build-essential gcc g++ make m4 pkg-config wget libx11-dev xorg-dev gettext

# Run bash by default
CMD ["/bin/bash"]