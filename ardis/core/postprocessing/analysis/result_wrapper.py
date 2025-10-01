import os
from ardis.core.postprocessing.analysis.parsing.periodic_log.periodic_log import PeriodicLog
from ardis.core.postprocessing.analysis.trace_provider import TraceProvider

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
    