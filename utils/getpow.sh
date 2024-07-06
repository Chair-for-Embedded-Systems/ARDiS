#!/bin/bash
PFILE=/sys/bus/i2c/drivers/ina3221x/0-0041/iio\:device1/in_power0_input
out=power.out
while IFS= read -r line
do
	power=$line
	echo $power >$out
done < $PFILE


