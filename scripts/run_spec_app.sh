#!/bin/bash
SPECPBASE=/home/sikmoh00/Subjects/RealHardware/cpu2006/
SPECPBIN=$SPECPBASE/bin
CONFIGFILE=mytest.cfg

SCRIPTPTH=`pwd`

# set spec enviroment if it hasn't been done yet
if [ -z $SPECBIN ] ; then
    cd $SPECPBASE/
    source $SPECPBASE/shrc
    cd $SCRIPTPTH
fi

# run app $1 on core $2
taskset -c $2 nice -n 0 runspec --iterations 1 --size train --action onlyrun --config $CONFIGFILE --noreportable  $1
