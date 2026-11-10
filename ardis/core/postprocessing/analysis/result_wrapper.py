from pathlib import Path

from ardis.core.postprocessing.analysis.dataframe_provider import DataFrameProvider
from ardis.core.postprocessing.analysis.parsing.periodic_log.periodic_log import PeriodicLog
from ardis.core.postprocessing.analysis.trace_provider import TraceProvider

class ExperimentResultWrapper:
    PERIODIC_COUNTERS_LOG_FILE = "periodic_counters.log"
    EXECUTION_LOG_FILE = "execution.log"
    
    def __init__(self, experiment_folder: str | Path) -> None:

        # Convert to Path if a string is provided
        if isinstance(experiment_folder, str):
            experiment_folder = Path(experiment_folder)

        if not (experiment_folder.exists() and experiment_folder.is_dir()):
            raise FileNotFoundError(f"Could not find {experiment_folder}")

        execution_log_file = experiment_folder / self.EXECUTION_LOG_FILE
        periodic_counter_log_file = experiment_folder / self.PERIODIC_COUNTERS_LOG_FILE

        if not execution_log_file.exists():
            raise FileNotFoundError(f"Could not find {execution_log_file}")

        if not periodic_counter_log_file.exists():
            raise FileNotFoundError(f"Could not find {periodic_counter_log_file}")

        self.__periodic_counter_log = PeriodicLog.from_log_file(str(periodic_counter_log_file))
        #execution_log = ExecutionLog(execution_log_file)

    def get_periodic_log(self) -> PeriodicLog:
        return self.__periodic_counter_log
    
    def get_trace_provider(self, verbose: bool = False) -> TraceProvider:
        # Cache the trace provider to avoid redundant computations
        if hasattr(self, "__trace_provider"):
            return self.__trace_provider
        self.__trace_provider = TraceProvider(self.get_periodic_log(), verbose=verbose)
        return self.__trace_provider

    def get_df_provider(self) -> DataFrameProvider:
        """
        Returns a DataFrameProvider instance for this experiment,
        which can be used to obtain pandas DataFrames of the periodic log data for analysis.
        """
        return DataFrameProvider(self.get_periodic_log())
