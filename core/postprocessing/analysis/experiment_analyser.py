import os

from pandas import DataFrame, Series
from .parser.periodic_log_parser import PeriodicCounterLog
from .parser.execution_log_parser import ExecutionLog

EXECUTION_LOG_FILE = "execution.log"
PERIODIC_COUNTERS_LOG_FILE = "periodic_counters.log"

class ExperimentAnalyser():

    def __init__(self, experiment_folder: str):
        
        if not os.path.isdir(experiment_folder):
            raise FileNotFoundError(f"Could not find {experiment_folder}")

        execution_log_file = os.path.join(experiment_folder, EXECUTION_LOG_FILE)
        periodic_counter_log_file = os.path.join(experiment_folder, PERIODIC_COUNTERS_LOG_FILE)

        if not os.path.exists(execution_log_file):
            raise FileNotFoundError(f"Could not find {execution_log_file}")

        if not os.path.exists(periodic_counter_log_file):
            raise FileNotFoundError(f"Could not find {periodic_counter_log_file}")
        
        periodic_counter_log = PeriodicCounterLog(periodic_counter_log_file)
        execution_log = ExecutionLog(execution_log_file)

        system_events = []
        for event in periodic_counter_log.system_events:
            data_point = {
                "timestamp": event.timestamp,
                "power_cores": event.energy_cores,
                "power_package": event.energy_package,
                "power_system": event.energy_sys
            }
            system_events.append(data_point)
        
        application_events = []
        for event in periodic_counter_log.application_events:
            data_point = {
                "timestamp": event.timestamp,
                "app_name": f"{event.app_name}_{event.pid}",
                "core": event.core_id,
                "frequency": event.frequency,
                "instructions": event.instructions,
                "cycles": event.cycles,
                "branches": event.branches,
                "branch_misses": event.branch_misses,
                "llc_loads": event.llc_loads,
                "llc_stores": event.llc_stores,
                "llc_store_misses": event.llc_store_misses,
                "llc_load_misses": event.llc_load_misses,
            }
            application_events.append(data_point)
        
        self.__system_events = DataFrame(system_events)
        self.__application_events = DataFrame(application_events)

    def get_applications(self) -> list[str]:
        """Returns a list of the applications that were used in this experiment"""
        return self.__application_events["app_name"].unique()
    
    def __get_feature_time_series(self, 
                            application_of_interest: str,
                            feature_column_name: str,
                            normalize_time: bool = False,
                            shift_to_zero: bool = False) -> tuple[Series, Series]:
        
        data = self.__application_events[self.__application_events["app_name"] == application_of_interest]
        time_series = data["timestamp"]
        feature_series = data[feature_column_name]

        if shift_to_zero:
            time_series = time_series - time_series.min()
        if normalize_time:
            time_series = time_series / time_series.max()

        return (time_series, feature_series)

    def get_frequency_series(self, aoi: str, normalize_time: bool = False, shift_to_zero: bool = False):
        return self.__get_feature_time_series(aoi, "frequency", normalize_time, shift_to_zero)

    def get_instruction_series(self, aoi: str, normalize_time: bool = False, shift_to_zero: bool = False):
        return self.__get_feature_time_series(aoi, "instructions", normalize_time, shift_to_zero)
    
    def get_cycle_series(self, aoi: str, normalize_time: bool = False, shift_to_zero: bool = False):
        return self.__get_feature_time_series(aoi, "cycles", normalize_time, shift_to_zero)
    
    def get_branch_series(self, aoi: str, normalize_time: bool = False, shift_to_zero: bool = False):
        return self.__get_feature_time_series(aoi, "branches", normalize_time, shift_to_zero)
    
    def get_branch_misses_series(self, aoi: str, normalize_time: bool = False, shift_to_zero: bool = False):
        return self.__get_feature_time_series(aoi, "branch_misses", normalize_time, shift_to_zero)
    
    def get_llc_load_series(self, aoi: str, normalize_time: bool = False, shift_to_zero: bool = False):
        return self.__get_feature_time_series(aoi, "llc_loads", normalize_time, shift_to_zero)
    
    def get_llc_store_series(self, aoi: str, normalize_time: bool = False, shift_to_zero: bool = False):
        return self.__get_feature_time_series(aoi, "llc_stores", normalize_time, shift_to_zero)
    
    def get_llc_store_misses_series(self, aoi: str, normalize_time: bool = False, shift_to_zero: bool = False):
        return self.__get_feature_time_series(aoi, "llc_store_misses", normalize_time, shift_to_zero)
    
    def get_llc_load_misses_series(self, aoi: str, normalize_time: bool = False, shift_to_zero: bool = False):
        return self.__get_feature_time_series(aoi, "llc_load_misses", normalize_time, shift_to_zero)
    
    def get_energy_core_series(self) -> tuple[Series, Series]:
        return (self.__system_events["timestamp"], self.__system_events["power_cores"])
    
    def get_energy_package_series(self) -> tuple[Series, Series]:
        return (self.__system_events["timestamp"], self.__system_events["power_package"])
    
    def get_energy_system_series(self) -> tuple[Series, Series]:
        return (self.__system_events["timestamp"], self.__system_events["power_system"])

    def get_core_mapping_intervalls(self, aoi: str) -> list[tuple[str, float, float]]:
        """Returns a list of tuples (core_id, start_time, end_time) for the specified aoi, indicating in which time period it was mapped to which core"""
        data = self.__application_events[self.__application_events["app_name"] == aoi]
        
        output = []
        current_core = data.iloc[0]["core"]
        current_start_time = data.iloc[0]["timestamp"]
        
        for _, row in data.iterrows():
            if current_core != row["core"]:
                core_range = (current_core, current_start_time, row["timestamp"])
                output.append(core_range)
                current_start_time = row["timestamp"]
                current_core = row["core"]
        
        core_range = (current_core, current_start_time, data.iloc[-1]["timestamp"])
        output.append(core_range)
        return output
    
    def get_execution_range(self, aoi: str) -> tuple[float, float]:
        """Returns the execution range (start_timestamp, end_timestamp) for the given `aoi`"""
        aoi_data = self.__application_events[self.__application_events["app_name"] == aoi]
        timestamps_aoi = aoi_data["timestamp"]
        if timestamps_aoi.empty:
            raise ValueError(f"{aoi} not in dataset")
        return timestamps_aoi.min(), timestamps_aoi.max()

if __name__ == "__main__":
    pass