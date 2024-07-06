#!/bin/bash

#switching governors to userspace

for core in {0..5}
do
	echo 1 | sudo tee /sys/devices/system/cpu/cpu$core/online
	echo "userspace" | sudo tee  /sys/devices/system/cpu/cpu$core/cpufreq/scaling_governor
done
