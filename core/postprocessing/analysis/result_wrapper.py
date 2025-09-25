import os
from core.postprocessing.analysis.parsing.periodic_log.periodic_log import PeriodicLog
from core.postprocessing.analysis.trace_provider import TraceProvider

class ExperimentResultWrapper:
    PERIODIC_COUNTERS_LOG_FILE = "periodic_counters.log"
    EXECUTION_LOG_FILE = "execution.log"
    
    def __init__(self, experiment_folder: str):
        if not os.path.isdir(experiment_folder):
            raise FileNotFoundError(f"Could not find {experiment_folder}")

        execution_log_file = os.path.join(experiment_folder, self.EXECUTION_LOG_FILE)
        periodic_counter_log_file = os.path.join(experiment_folder, self.PERIODIC_COUNTERS_LOG_FILE)

        if not os.path.exists(execution_log_file):
            raise FileNotFoundError(f"Could not find {execution_log_file}")

        if not os.path.exists(periodic_counter_log_file):
            raise FileNotFoundError(f"Could not find {periodic_counter_log_file}")

        self.__experiment_folder = experiment_folder
        self.__periodic_counter_log = PeriodicLog.from_log_file(periodic_counter_log_file)
        #execution_log = ExecutionLog(execution_log_file)

    def get_periodic_log(self) -> PeriodicLog:
        return self.__periodic_counter_log
    
    def get_trace_provider(self, verbose: bool = False) -> TraceProvider:
        # Cache the trace provider to avoid redundant computations
        if hasattr(self, "__trace_provider"):
            return self.__trace_provider
        self.__trace_provider = TraceProvider(self.get_periodic_log(), verbose=verbose)
        return self.__trace_provider
    
    

if __name__ == "__main__":
    core_experiment = "/home/uhqql/ARDIS/results/2025-09-23_17-54-09_Simple_Experiment_with_Specific_Applications"
    pid_experiment = "/home/uhqql/ARDIS/results/2025-09-23_17-55-37_Simple_Experiment_with_Specific_Applications"
    tid_experiment = "/home/uhqql/ARDIS/results/2025-09-23_17-56-51_Experiment_with_tid_monitoring"
    
    analyser = ExperimentResultWrapper(tid_experiment)
    pcl = analyser.get_periodic_log()
    print("Application events count:", len(pcl.app_events))
    print("System events count:", len(pcl.sys_events))
    print("Periodic application events labels:", pcl.periodic_application_events_labels)
    print("Periodic system events labels:", pcl.periodic_system_events_labels)
    app_index = pcl.get_application_index()
    for app_name, instance_ids in app_index.items():
        print(f"Application '{app_name}' has instances: {instance_ids}")
        for iid in instance_ids:
            tids = pcl.get_threads(iid)
            print(f"  Instance ID {iid} has threads: {tids}")