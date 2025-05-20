import os
import datetime
class Reporter():
    def __init__(self, experiment_name, results_dir):
        # Format the current date and time
        datetime_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        # Construct the directory name
        dir_name = f"{datetime_str}_{experiment_name.replace(' ', '_')}/"
        # Create the full path for the new directory
        self.workdir = os.path.join(os.path.abspath(results_dir), dir_name)
        # Create the directory, including any necessary parent directories
        os.makedirs(self.workdir, exist_ok=True)
        # Create the execution log file
        with open(self.workdir + "summary.log", "a") as f:
            f.write("Core(s) \t Application \t Execution time (s)\n")
    
    def logEvent(self, event: str, echo: bool = False) -> None:
        with open(self.workdir + "execution.log", "a") as f:
            f.write(event + "\n")
        
        if echo:
            print(event)

    def logExecutionTime(self, app_name: str, core: str, time: float) -> None:
        with open(self.workdir + "summary.log", "a") as f:
            f.write(f"{core}\t{app_name}\t{round(time, 2)}\n")
            
    def logPeriodicCounters(self, data: str) -> None:
        with open(self.workdir + "periodic_counters.log", "a") as f:
            f.write(data + "\n")
    