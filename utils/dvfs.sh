#!/bin/bash

sudo echo "DVFS: ON"

export VF_HI=2035200

VF_L1=345600 
VF_L2=499200
VF_L3=652800
VF_L4=806400



while  true
do
		echo ${VF_HI} | sudo tee /sys/devices/system/cpu/cpu$1/cpufreq/scaling_max_freq
		echo ${VF_HI} | sudo tee /sys/devices/system/cpu/cpu$1/cpufreq/scaling_min_freq
		#select random low value
		var=$(($RANDOM % 4))
		case $var in
			0)
				VF_LOW=$VF_L1
				;;
			1)
				VF_LOW=$VF_L2
				;;
			2)
				VF_LOW=$VF_L3
				;;
			*)
				VF_LOW=$VF_L4
				;;
		esac
		sleep 0.0025 # beta = 9
		#sleep 0.0125 # beta = 1
		#sleep 0.0125

		echo ${VF_LOW} | sudo tee /sys/devices/system/cpu/cpu$1/cpufreq/scaling_min_freq
                echo ${VF_LOW} | sudo tee /sys/devices/system/cpu/cpu$1/cpufreq/scaling_max_freq
		sleep 0.0225 # beta = 9
		#sleep 0.0125 beta = 1
done


