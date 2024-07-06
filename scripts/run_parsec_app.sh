#!/bin/bash
PARSECBASE=/home/jetson/mitecca/parsec-benchmark/
SCRIPTPTH=`pwd`

# set parsec enviroment if it hasn't been done yet
if [ -z $xxPARSECDIRxx ] ; then
    cd $PARSECBASE/
    source env.sh
    cd $SCRIPTPTH
fi

# run app $1 on core $2
taskset -c $2 parsecmgmt -a run -i simlarge -n 1 -p $1
