from config import *
import threading
import subprocess
import os
import time


lock = threading.Lock()

class PIDMonitor:
    def __init__(self, pids, sampling_rate_ms=100, events=["instructions", "cache-misses", "cache-references", "power/energy-pkg/", "power/energy-cores/", "power/energy-psys/"]):
        """
        Initialize the Monitor to track multiple PIDs.
        
        :param pids: List of process IDs to monitor.
        :param sampling_rate_ms: Sampling rate in milliseconds.
        :param events: List of events to monitor (e.g., instructions, cache-misses).
        """
        self.__sampling_rate = sampling_rate_ms / 1000
        self.__events = events
        self.__inst_file = os.path.join(ROOTPATH, "perf.out")
        self.__finished = False
        self.__pids = [str(pid) for pid in pids]
        self.__current_values = {str(pid): {event: 0 for event in self.__events} for pid in self.__pids}


    def start(self):
        """Start monitoring performance metrics."""
        self.__perf_thread = threading.Thread(target=self.__poll)
        self.__perf_thread.start()

    def stop(self):
        """Stop monitoring performance metrics."""
        self.__finished = True

    def getMetricForPID(self, pid, event):
        """Get the performance metric for a specific PID and event."""
        return self.__current_values[str(pid)][event]
    
    def updateTrackedPIDs(self, pids):
        """Update the list of PIDs being tracked."""
        with lock:
            self.__pids = [str(pid) for pid in pids]
            for pid in self.__pids:
                if pid not in self.__current_values:
                    self.__current_values[pid] = {event: 0 for event in self.__events}
            if DEBUG:
                print(f"Monitoring switched to new PIDs: {', '.join(self.__pids)}")

    def __poll(self):
        """Polling loop to continuously collect performance data."""
        while not self.__finished:
            self.__execute_perf_command()
        os.remove(self.__inst_file)

    def __execute_perf_command(self):
        """Execute the perf command to collect performance data for the tracked PIDs."""
        with lock:
            pids = self.__pids  # Safely read the current PIDs

        command = f"perf stat -p {','.join(pids)} -e {','.join(self.__events)} -B -o {self.__inst_file} sleep {self.__sampling_rate} 2{'> /dev/null' if not DEBUG else ''}"
        if DEBUG:
            print("Command is: ", command)
        with lock:
            subprocess.run(command, shell=True)
        self.__updateStats()

    def __updateStats(self):
        """Parse the output of the perf command and update metrics."""
        base_dir = os.path.dirname(os.path.dirname(__file__)) 
        perf_out_path = os.path.join(base_dir, self.__inst_file)
        if os.path.exists(perf_out_path):
            with open(perf_out_path, 'r') as f:
                lines = f.readlines()
        else:
            print("File not found:", perf_out_path)
            return

        # Parse the perf output for each PID
        current_pid = None
        for line in lines[5:-3]:
            if "<not supported>" in line or "<not counted>" in line:
                continue  # Skip unsupported metrics

            # Check if the line contains a new PID
            if "task-clock" in line:  # You can find the right pattern to identify PID sections
                parts = line.split()
                current_pid = parts[-1].replace("(", "").replace(")", "")
                continue

            if current_pid and current_pid in self.__current_values:
                parts = line.split()
                metric_value = int(parts[0].replace(".", "").replace(",", ""))
                for event in self.__events:
                    if event in line:
                        self.__current_values[current_pid][event] = metric_value
                        break  # Stop checking once the correct event is found
