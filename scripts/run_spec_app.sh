#!/bin/bash
SPECPBASE=/home/jetson/mitecca/spec/cpu2006
SPECPBIN=$SPECPBASE/bin
CONFIGARM=linux64-arm64-gcc.cfg

SCRIPTPTH=`pwd`

# set spec enviroment if it hasn't been done yet
if [ -z $SPECBIN ] ; then
    cd $SPECPBASE/
    source $SPECPBASE/shrc
    cd $SCRIPTPTH
fi

# run app $1 on core $2
taskset -c $2 runspec --iterations 1 --size train --action onlyrun --config $CONFIGARM --noreportable  $1
