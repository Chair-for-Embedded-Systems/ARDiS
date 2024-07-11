#!/bin/bash
PARSECBASE=/home/sikmoh00/Subjects/RealHardware/parsec-3.0/
SCRIPTPTH=`pwd`

# set parsec enviroment if it hasn't been done yet
if [ -z $xxPARSECDIRxx ] ; then
    cd $PARSECBASE/
    source env.sh
    cd $SCRIPTPTH
fi

# run app $1 on core $2
taskset -c $2 nice -n 0 parsecmgmt -a run -i native -n 1 -p $1
