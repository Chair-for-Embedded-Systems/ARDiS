from config import *
from core.monitoringmode import *
import threading
import subprocess
import os
import time



lock = threading.Lock()
class Monitor:
    def __init__(self,
                 tracked_cores = [0, 1, 2, 3],
                 pids = [],
                 monitoring_mode = MonitoringMode.PERIODIC_ON_CORE):
        self.__sampling_rate = sampling_rate / 1000
        self.__inst_app_file = os.path.join(ROOTPATH, "perf_app.out")
        self.__inst_sys_file = os.path.join(ROOTPATH, "perf_sys.out")
        self.__one_shot_file = os.path.join(ROOTPATH, "one_shot.out")
        self.__finished = False
        self.__tracked_cores = [str(core) for core in tracked_cores]
        self.__tracked_pids = [str(pid) for pid in pids]
        self.__current_core_values = {str(core): {event: 0 for event in periodic_app_level_events} for core in self.__tracked_cores}
        self.__current_pid_values = {str(pid): {event: 0 for event in periodic_app_level_events} for pid in self.__tracked_pids}
        self.__current_system_values = {event: 0 for event in periodic_system_wide_events}
        self.__monitoring_mode = monitoring_mode


    def start(self):
        self.__perf_thread = threading.Thread(target=self.__poll)
        threading.Thread(target=self.__execute_oneshot_system_wide_perf).start()
        self.__perf_thread.start()

    def stop(self):
        self.__finished = True
        time.sleep(3)


    def getMetricAtCore(self, core, event):
        return self.__current_core_values[str(core)][event]
    
    def getMetricForPID(self, pid, event):
        """Get the performance metric for a specific PID and event."""
        return self.__current_pid_values[str(pid)][event] if pid != "-1" else 0
    
    def getSystemWideMetric(self, event):
        """Get the performance metric for an event system wide."""
        return self.__current_system_values[event]

    def updateTrackedCores(self, cores):
        self.__tracked_cores = [str(core) for core in cores]	

        
    def updateTrackedPIDs(self, pids):
        """Update the list of PIDs being tracked."""
        with lock:
            self.__tracked_pids = [str(pid) for pid in pids]
            for pid in self.__tracked_pids:
                if pid not in self.__current_pid_values:
                    self.__current_pid_values[pid] = {event: 0 for event in periodic_app_level_events}
            if DEBUG:
                print(f"Monitoring switched to new PIDs: {', '.join(self.__tracked_pids)}")

    def __poll(self):
        while not self.__finished:
            self.__execute_perf_command()
            self.__execute_periodic_system_wide_perf()
        os.remove(self.__inst_app_file)
        os.remove(self.__inst_sys_file)
        self.__kill_perf()

    def __execute_perf_command(self):
        command = ""
        if self.__monitoring_mode == MonitoringMode.PERIODIC_ON_CORE:
            command = f"perf stat -C {','.join(self.__tracked_cores)} -e {','.join(periodic_app_level_events)} -B -A -o {self.__inst_app_file} sleep {self.__sampling_rate} 2{'> /dev/null' if not DEBUG else ''}"
        elif self.__monitoring_mode == MonitoringMode.PERIODIC_ON_PID and len(self.__tracked_pids) > 0 and all(pid != "-1" for pid in self.__tracked_pids):
            command = f"perf stat -p {','.join(self.__tracked_pids)} -e {','.join(periodic_app_level_events)} -B -o {self.__inst_app_file} sleep {self.__sampling_rate} 2{'> /dev/null' if not DEBUG else ''}"
        if DEBUG:
            print("Command is: ", command)
        with lock:
            subprocess.run(command, shell=True)
        if self.__monitoring_mode == MonitoringMode.PERIODIC_ON_CORE:
            self.__update_app_core_stats()
        elif self.__monitoring_mode == MonitoringMode.PERIODIC_ON_PID and all(pid != "-1" for pid in self.__tracked_pids):
            self.__update_app_pid_stats()

    def __execute_oneshot_system_wide_perf(self):
        command = f"perf stat -a -e {','.join(one_shot_system_wide_events)} -o {self.__one_shot_file}"
        if DEBUG:
            print("Command is: ", command)
        subprocess.run(command, shell=True)

    def __execute_periodic_system_wide_perf(self):
        command = f"perf stat -a -e {','.join(periodic_system_wide_events)} -o {self.__inst_sys_file} sleep {self.__sampling_rate} 2{'> /dev/null' if not DEBUG else ''}"
        if DEBUG:
            print("Command is: ", command)
        subprocess.run(command, shell=True)
        self.__update_system_stats()


    def __kill_perf(self):
        command = "kill -2 $(pidof perf)"
        if DEBUG:
            print("Command is: ", command)
        subprocess.run(command, shell=True)


    def __update_system_stats(self):
        # Initialize or reset the lists for each metric based on the number of tracked cores
       
        base_dir = os.path.dirname(os.path.dirname(__file__)) 
        perf_out_path = os.path.join(base_dir, self.__inst_sys_file)  
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
            
            # Parse the metric value, ensuring to remove any formatting like commas or dots
            metric_value = float(parts[0])
            for event in periodic_system_wide_events:
                if event in line:
                    self.__current_system_values[event] = metric_value
                    break  # Break the loop once the metric is found

            
    def __update_app_core_stats(self):
        # Initialize or reset the lists for each metric based on the number of tracked cores
        
        base_dir = os.path.dirname(os.path.dirname(__file__)) 
        perf_out_path = os.path.join(base_dir, self.__inst_app_file)
        
        if os.path.exists(perf_out_path):
            with open(perf_out_path, 'r') as f:
                lines = f.readlines()  # Read all lines
        else:
            print("Perf output file is not available")
            return
        
        # Temporary dictionary to hold metrics for each core
        temp_core_metrics = {core: {event: {"cpu_atom": 0, "cpu_core": 0} for event in self.__events} for core in self.__tracked_cores}
        
        # Process each relevant line in the perf output
        for line in lines[5:-3]:
            if "<not supported>" in line or "<not counted>" in line:
                continue  # Skip unsupported or not counted metrics

            parts = line.split()
            if len(parts) < 2:
                continue  # Skip lines without enough information
            
            # Extract core number
            core_id = parts[0].replace("CPU", "")
            if core_id not in self.__tracked_cores:
                continue  # Skip cores that are not tracked
            
            # Parse the metric value, ensuring to remove any formatting like commas or dots
            try:
                metric_value = int(parts[1].replace(".", "").replace(",", ""))
            except ValueError:
                continue  # Skip lines where the metric value cannot be parsed
            
            # Identify if this is cpu_atom or cpu_core
            for event in periodic_app_level_events:
                if event in line:
                    if "cpu_atom" in line:
                        temp_core_metrics[core_id][event]["cpu_atom"] = metric_value
                    elif "cpu_core" in line:
                        temp_core_metrics[core_id][event]["cpu_core"] = metric_value
                    break  # Break once the event is found

        # Now sum up the cpu_atom and cpu_core values for each core and event
        for core_id in self.__tracked_cores:
            for event in periodic_app_level_events:
                total_value = temp_core_metrics[core_id][event]["cpu_atom"] + temp_core_metrics[core_id][event]["cpu_core"]
                self.__current_core_values[core_id][event] = total_value  # Store the sum in the final dictionary
                
    def __update_app_pid_stats(self):
        # Initialize or reset the lists for each metric based on the tracked PIDs
        
        base_dir = os.path.dirname(os.path.dirname(__file__)) 
        perf_out_path = os.path.join(base_dir, self.__inst_app_file)  
        
        if os.path.exists(perf_out_path):
            with open(perf_out_path, 'r') as f:
                lines = f.readlines()
        else:
            print("Perf output file is not available")
            return
        
        pid = None  # Variable to store the PID
        
        # Extract the PID from the header (assuming it's always on the 3rd line)
        for line in lines:
            if "Performance counter stats for process id" in line:
                pid = line.split("'")[1]  # Extract PID from the string
                break
        
        if pid is None:
            print("PID not found in the output")
            return
        
        # Initialize PID-based metrics dictionary if not already
        if pid not in self.__current_pid_values:
            self.__current_pid_values[pid] = {}  # Dictionary to store metrics for this PID
        
        # Temporary storage for both cpu_atom and cpu_core values
        temp_metrics = {}

        # Process the lines containing performance data
        for line in lines[5:-3]:  # Adjust this based on where relevant data starts and ends
            if "<not supported>" in line or "<not counted>" in line:
                continue  # Skip unsupported or not counted metrics

            parts = line.split()
            if len(parts) < 2:
                continue  # Skip lines that don't have enough information

            # Parse the metric value, removing commas or dots for clean conversion to int
            try:
                metric_value = int(parts[0].replace(".", "").replace(",", ""))
            except ValueError:
                continue  # In case the metric value is not parsable, skip this line
            
            # Get the event name (e.g., `cpu_atom/instructions/` or `cpu_core/instructions/`)
            event_name = parts[1]
            
            # Check if the event is in the list of events being tracked
            for event in periodic_app_level_events:
                if event in event_name:
                    # Determine if it's cpu_atom or cpu_core
                    if "cpu_atom" in event_name:
                        temp_metrics.setdefault(event, {"cpu_atom": 0, "cpu_core": 0})["cpu_atom"] = metric_value
                    elif "cpu_core" in event_name:
                        temp_metrics.setdefault(event, {"cpu_atom": 0, "cpu_core": 0})["cpu_core"] = metric_value
                    
                    break  # Break once the metric is found and stored

        # Sum cpu_atom and cpu_core values and store in the final dictionary
        for event, values in temp_metrics.items():
            total_value = values["cpu_atom"] + values["cpu_core"]
            self.__current_pid_values[pid][event] = total_value