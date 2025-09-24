from core.postprocessing.analysis2.parsing.periodic_log import PeriodicLog
from typing import Any

from pandas import DataFrame, Series

class TraceProvider:
    def __init__(self, pl: PeriodicLog, verbose: bool = False) -> None:
        
        verbose = False

        # Init pandas DataFrame for application events
        application_datapoints: list[dict[str, Any]] = []
        for app_event in pl.app_events:
            data_point: dict[str, Any] = {
                "timestamp": app_event.timestamp_sec,
                "app_name": app_event.application_name,
                "instance_id": app_event.instance_id,
                "thread_id": app_event.tid,
                "core_id": app_event.affinity,
                "frequency": app_event.frequency_mhz,
                **app_event.perf_events
            }
            application_datapoints.append(data_point)
        self.__app_events = DataFrame(application_datapoints)
        
        # Init pandas DataFrame for system events
        system_datapoints: list[dict[str, Any]] = []
        for sys_event in pl.sys_events:
            data_point = {
                "timestamp": sys_event.timestamp_sec,
                **sys_event.perf_events
            }
            system_datapoints.append(data_point)
        self.__sys_events = DataFrame(system_datapoints)

        # Store which events are available
        self.available_app_metrics = pl.periodic_application_events_labels
        self.available_sys_metrics = pl.periodic_system_events_labels

        # Cache some useful information
        self._app_to_instances = pl.get_application_index()
        self._instance: set[int] = { iid for iids in self._app_to_instances.values() for iid in iids}
        self._instance_to_threads: dict[int, set[int]] = {iid: pl.get_threads(iid) for iid in self._instance}
        
        if verbose:
            print(f"Loaded {len(self.__app_events)} application event traces.")
            print(f"Loaded {len(self.__sys_events)} system event traces.")
            print(f"Available application events: {self.available_app_metrics}")
            print(f"Available system events: {self.available_sys_metrics}")
            print(f"Instance to threads mapping: {self._instance_to_threads}")

    def get_app_index(self) -> dict[str, set[int]]:
        """
        Returns a dictionary mapping application names to sets of instance IDs.
        """
        return self._app_to_instances
    
    def get_threads(self, instance_id: int) -> set[int]:
        """
        Returns the set of thread IDs associated with a given application instance ID.
        """
        if instance_id not in self._instance_to_threads:
            raise ValueError(f"Instance ID {instance_id} not found.")
        return self._instance_to_threads[instance_id]

    def __filter_app_events(self, instance_id: int, thread_id: int | None = None) -> DataFrame:
        """
        Utility method to filter application events by instance ID and optional thread ID.
        """
        df = self.__app_events
        instance_events = df[df['instance_id'] == instance_id]
        if thread_id is not None:
            instance_events = instance_events[instance_events['thread_id'] == thread_id]
        if instance_events.empty:
            raise ValueError(f"No events found for instance ID {instance_id} and thread ID {thread_id}")
        return instance_events

    def get_execution_range(self, instance_id: int, thread_id: int | None = None) -> tuple[float, float]:
        """
        Returns the start and end timestamps of the execution for a given application instance ID.
        If thread_id is provided, filters the events to that specific thread.
        """
        filtered_events = self.__filter_app_events(instance_id, thread_id)

        start_time = filtered_events['timestamp'].min()
        end_time = filtered_events['timestamp'].max()
        return (start_time, end_time)
    
    def get_app_metric_trace(self, metric: str, instance_id: int, thread_id: int | None = None) -> tuple[Series, Series]:
        """
        Returns a DataFrame containing all application event traces for a given instance ID.
        If thread_id is provided, filters the events to that specific thread.
        """
        if metric not in self.available_app_metrics:
            raise ValueError(f"Event '{metric}' not found in application events. Available events: {self.available_app_metrics}")
        
        filtered_events = self.__filter_app_events(instance_id, thread_id)
        instance_events = filtered_events[['timestamp', metric]].sort_values(by='timestamp').reset_index(drop=True) # type: ignore

        # If we have data on a per thread basis, but no specific thread is requested, sum up the values across threads
        instance_events = instance_events.groupby('timestamp', as_index=False).sum() # type: ignore

        time_series: Series[float] = instance_events['timestamp']
        metric_series: Series[float|int] = instance_events[metric]
        return time_series, metric_series
    
    def get_sys_metric_trace(self, metric: str) -> tuple[Series, Series]:
        """
        Returns a DataFrame containing all system event traces for a given metric.
        """
        if metric not in self.available_sys_metrics:
            raise ValueError(f"Event '{metric}' not found in system events. Available events: {self.available_sys_metrics}")
        
        system_events = self.__sys_events[['timestamp', metric]].sort_values(by='timestamp').reset_index(drop=True) # type: ignore

        time_series: Series[float] = system_events['timestamp']
        metric_series: Series[float|int] = system_events[metric]
        return time_series, metric_series
    
    def get_instance_ids(self) -> set[int]:
        """ Returns a set of all application instance IDs."""
        return self._instance
    
    def get_thread_ids(self) -> set[int]:
        """ Returns a set of all thread IDs across all application instances."""
        return {tid for tids in self._instance_to_threads.values() for tid in tids}

if __name__ == "__main__":
    core_experiment = "/home/uhqql/ARDIS/results/2025-09-23_17-54-09_Simple_Experiment_with_Specific_Applications"
    pid_experiment = "/home/uhqql/ARDIS/results/2025-09-23_17-55-37_Simple_Experiment_with_Specific_Applications"
    tid_experiment = "/home/uhqql/ARDIS/results/2025-09-23_17-56-51_Experiment_with_tid_monitoring"
    
    experiment_folders = [core_experiment, pid_experiment, tid_experiment]
    from core.postprocessing.analysis2.result_wrapper import ExperimentResultWrapper
    for experiment in experiment_folders:
        print(f"\nAnalyzing experiment folder: {experiment}")
        wrapper = ExperimentResultWrapper(experiment)
        trace_provider = TraceProvider(wrapper.get_periodic_log())

        for app_name, instance_ids in trace_provider.get_app_index().items():
            print(f"Application '{app_name}' has instances: {instance_ids}")
            for iid in instance_ids:
                print(f"  Instance ID {iid} execution range: {trace_provider.get_execution_range(iid)}")
                
                instruction_trace = trace_provider.get_app_metric_trace("instructions", iid)
                time, metric = instruction_trace
                print(f"    Instructions trace (first 5 entries):")
                for t, m in zip(time.head(5), metric.head(5)):
                    print(f"      Time: {t:.2f}s, Instructions: {m}")
                
                threads = trace_provider.get_threads(iid)
                continue
                for tid in threads:
                    print(f"      Thread ID {tid} execution range: {trace_provider.get_execution_range(iid, tid)}")

