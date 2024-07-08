import os
import datetime
class Reporter():
    def __init__(self, experiment_name, results_dir):
        # Format the current date and time
        datetime_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        # Construct the directory name
        dir_name = f"{experiment_name.replace(' ', '_')}_{datetime_str}/"
        # Create the full path for the new directory
        self.workdir = os.path.join(os.path.abspath(results_dir), dir_name)
        # Create the directory, including any necessary parent directories
        os.makedirs(self.workdir, exist_ok=True)
        # Create the execution log file
        with open(self.workdir + "summary.log", "a") as f:
            f.write("Core\tApplication\tExecution time (s)\n")
    
    def logEvent(self, event):
        with open(self.workdir + "execution.log", "a") as f:
            f.write(event + "\n")
    def logExecutionTime(self, app_name, core, time):
        with open(self.workdir + "summary.log", "a") as f:
            f.write(f"{core}\t{app_name}\t{round(time, 2)}\n")
    