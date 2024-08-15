from config import *
import threading
import subprocess
import os
import time



lock = threading.Lock()
class Monitor:
    def __init__(self, sampling_rate_ms = 100, events = ["instructions", "cache-misses", "cache-references","power/energy-pkg/", "power/energy-cores/", "power/energy-psys/"], 
                 tracked_cores = [0, 1, 2, 3]):
        self.__sampling_rate = sampling_rate_ms / 1000
        self.__events = events
        self.__inst_file = os.path.join(ROOTPATH, "perf.out")
        self.__finished = False
        self.__current_values = {str(core): {event: 0 for event in self.__events} for core in tracked_cores}
        self.__tracked_cores = [str(core) for core in tracked_cores]


    def start(self):
        self.__perf_thread = threading.Thread(target=self.__poll)
        self.__perf_thread.start()

    def stop(self):
        self.__finished = True

    def getMetricAtCore(self, core, event):
        return self.__current_values[str(core)][event]

    def __poll(self):
        while not self.__finished:
            self.__execute_perf_command()
        os.remove(self.__inst_file)

    def __execute_perf_command(self):
        command = f"perf stat -C {','.join(self.__tracked_cores)} -e {','.join(self.__events)} -B -A -o {self.__inst_file} sleep {self.__sampling_rate} 2{'> /dev/null' if not DEBUG else ''}"
        if DEBUG:
            print("Command is: ", command)
        with lock:
            subprocess.run(command, shell=True)
        self.__updateStats()


    def __updateStats(self):
        # Initialize or reset the lists for each metric based on the number of tracked cores
       
        base_dir = os.path.dirname(os.path.dirname(__file__)) 
        perf_out_path = os.path.join(base_dir, self.__inst_file)  
        #print("perf_out_path: ", perf_out_path)
        if os.path.exists(perf_out_path):
            with open(perf_out_path, 'r') as f:
                lines = f.readlines()  # Skip the first line
        else:
            print("file is not there")
            return
        
        for line in lines[5:-3]:
            if "<not supported>" in line or "<not counted>" in line:
                continue  # Skip unsupported metrics
            parts = line.split()
            #print("Parts are: ", parts)
            # Extract core number and convert it to an index based on tracked_cores
            core_id = parts[0].replace("CPU", "")
            if core_id not in self.__tracked_cores:
                continue  # Skip cores that are not tracked
    
            # Parse the metric value, ensuring to remove any formatting like commas or dots
            metric_value = int(parts[1].replace(".", "").replace(",", ""))
            for event in self.__events:
                if event in line:
                    self.__current_values[str(core_id)][event] = metric_value
                    break  # Break the loop once the metric is found