#from config import *
import threading
import subprocess
import time



lock = threading.Lock()
class Monitor:
    def __init__(self, sampling_rate_ms = 100, events = ["instructions", "cache-misses", "cache-references"], 
                 tracked_cores = [0, 1, 2, 3]):
        self.__sampling_rate = sampling_rate_ms / 1000
        self.__events = events
        self.__inst_file = "perf.out"
        self.__current_values = {
            "instructions": [],
            "cache_misses": [],
            "cache_references": []
        }
        self.__finished = False
        self.__tracked_cores = tracked_cores

    def start(self):
        self.__perf_thread = threading.Thread(target=self.__poll)
        self.__perf_thread.start()

    def stop(self):
        self.__finished = True

    def getIPS(self, core):
        instructions = self.__current_values["instructions"][core]
        return instructions / self.__sampling_rate
    
    def getCacheAccesses(self, core):
        cache_references = self.__current_values["cache_references"][core]
        return cache_references
    
    def getCacheMisses(self, core):
        cache_misses = self.__current_values["cache_misses"][core]
        return cache_misses


    def __poll(self):
        while not self.__finished:
            self.__execute_perf_command()


    def __execute_perf_command(self):
        command = f"perf stat -C {','.join(self.__tracked_cores)} -e {','.join(self.__events)} -B -A -o {self.__inst_file} sleep {self.__sampling_rate }"
        print("Command is: ", command)
        subprocess.run(command, shell=True)
        self.__updateStats()


    def __updateStats(self):
        # Initialize or reset the lists for each metric based on the number of tracked cores
        num_cores = len(self.__tracked_cores)
        self.__current_values["instructions"] = [0] * num_cores
        self.__current_values["cache_misses"] = [0] * num_cores
        self.__current_values["cache_references"] = [0] * num_cores

        with open(self.__inst_file, 'r') as f:
            lines = f.readlines()  # Skip the first line
        
        for line in lines[5:-3]:
            if "<not supported>" in line or "<not counted>" in line:
                continue  # Skip unsupported metrics

            parts = line.split()
            #print("Parts are: ", parts)
            # Extract core number and convert it to an index based on tracked_cores
            core_id = parts[0].replace("CPU", "")
            if core_id not in self.__tracked_cores:
                continue  # Skip cores that are not tracked
            core_index = self.__tracked_cores.index(core_id)

            # Parse the metric value, ensuring to remove any formatting like commas or dots
            metric_value = int(parts[1].replace(".", ""))

            if "instructions" in line:
                self.__current_values["instructions"][core_index] = metric_value
            elif "cache-misses" in line:
                self.__current_values["cache_misses"][core_index] = metric_value
            elif "cache-references" in line:
                self.__current_values["cache_references"][core_index] = metric_value




# if __name__ == "__main__":
#     system_cores = ["0","1","2","3","4","5"]
#     # Create an instance of the Monitor class
#     monitor = Monitor(tracked_cores = system_cores)

#     # Start monitoring
#     monitor.start()
#     time.sleep(1)

#     for t in range(10):
#         print(f"Time: {t}")
#         # Print the IPS, cache accesses, and cache misses for each core
#         for core in range(len(system_cores)):
#             ips = monitor.getIPS(core)
#             cache_accesses = monitor.getCacheAccesses(core)
#             cache_misses = monitor.getCacheMisses(core)
#             print(f"Core {core}: IPS = {ips}, Cache Accesses = {cache_accesses}, Cache Misses = {cache_misses}")
#         time.sleep(1)
        