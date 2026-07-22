from ardis.core.postprocessing.analysis.parsing.periodic_log import PeriodicLog
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

        # Init pandas DataFrame for temperature events
        temperature_datapoints: list[dict[str, Any]] = []
        for temp_event in pl.temp_events:
            for core_id, temperature in temp_event.core_temperatures.items():
                data_point = {
                    "timestamp": temp_event.timestamp_sec,
                    "core_id": core_id,
                    "temperature": temperature
                }
                temperature_datapoints.append(data_point)
        self.__temp_events = DataFrame(temperature_datapoints)

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
    
    def get_affinity_trace(self, instance_id: int, thread_id: int | None = None) -> tuple[Series, Series]:
        """
        Returns the timestamps and core affinity sets for a given application instance ID.
        If thread_id is provided, filters the events to that specific thread.
        """
        filtered_events = self.__filter_app_events(instance_id, thread_id)
        affinity_events = filtered_events[['timestamp', 'core_id']].sort_values(by='timestamp').reset_index(drop=True) # type: ignore

        # If we have data on a per thread basis, but no specific thread is requested, merge the affinity sets across threads
        affinity_events = affinity_events.groupby('timestamp', as_index=False).agg({'core_id': lambda x: set().union(*x)})

        time_series: Series[float] = affinity_events['timestamp']
        affinity_series: Series[set[int]] = affinity_events['core_id']  # type: ignore
        return time_series, affinity_series

    def get_core_frequency_traces(self) -> dict[int, tuple[Series, Series]]:
        """
        Returns a dictionary mapping core IDs to their frequency traces (timestamps and frequencies).
        """
        # Filter application events that have valid frequency values
        freq_events = self.__app_events.dropna(subset=['frequency'])
        
        # Select core_id, timestamp, frequency columns
        freq_events = freq_events[['core_id', 'timestamp', 'frequency']]
        freq_events['core_id'] = freq_events['core_id'].apply(lambda x: list(x)[0])
        freq_events['core_id_int'] = freq_events['core_id'].astype(int)

        # Group by core_id
        core_frequency_traces: dict[int, tuple[Series, Series]] = {}
        for core_id, group in freq_events.groupby('core_id_int'):
            sorted_group = group.sort_values(by='timestamp').reset_index(drop=True) 
            time_series: Series[float] = sorted_group['timestamp']
            freq_series: Series[float] = sorted_group['frequency']
            core_frequency_traces[core_id] = (time_series, freq_series)

        return core_frequency_traces

    def get_core_temp_traces(self) -> dict[int, tuple[Series, Series]]:
        """
        Returns a dictionary mapping core IDs to their temperature traces (timestamps and temperatures).
        """
        # Select core temperature columns
        temp_events = self.__temp_events
        core_temp_traces: dict[int, tuple[Series, Series]] = {}

        for core_id, group in temp_events.groupby('core_id'):
            sorted_group = group.sort_values(by='timestamp').reset_index(drop=True) 
            time_series: Series[float] = sorted_group['timestamp']
            temp_series: Series[float] = sorted_group['temperature']
            core_temp_traces[core_id] = (time_series, temp_series) # type: ignore

        return core_temp_traces

    def get_instance_ids(self) -> set[int]:
        """ Returns a set of all application instance IDs."""
        return self._instance
    
    def get_thread_ids(self) -> set[int]:
        """ Returns a set of all thread IDs across all application instances."""
        return {tid for tids in self._instance_to_threads.values() for tid in tids}
