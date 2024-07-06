#!/bin/bash
while true
do 	echo "Freq util ***********************************************"
	for core in {0..5}
	do
		while IFS= read -r line; 
		do
			freq=$line
		done < /sys/devices/system/cpu/cpu$core/cpufreq/scaling_cur_freq
		echo "Core $core: Frequency $freq"

	done
	sleep 1.5
	clear
done


