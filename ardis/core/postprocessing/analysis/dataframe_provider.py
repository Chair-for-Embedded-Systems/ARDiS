from typing import Any

import pandas as pd

from ardis.core.postprocessing.analysis.parsing.periodic_log import PeriodicLog

class DataFrameProvider:
    """
    Provides methods to convert periodic log data into pandas DataFrames for analysis.
    """
    def __init__(self, periodic_log: PeriodicLog) -> None:
        self._periodic_log = periodic_log

    def get_app_level_dataframe(self) -> pd.DataFrame:
        """
        Returns a pandas DataFrame containing the periodic application-level events
        extracted from the periodic log.

        By default, the DataFrame has the following columns:

        - `timestamp_sec` (float): Timestamp in seconds.
        - `app` (str): Application name.
        - `iid` (int): Instance ID.
        - `pid` (int | None): Process ID, if available.
        - `tid` (int | None): Thread ID, if available.
        - `affinity` (set[int]): Core affinity as a set of core IDs.
        - `frequency_mhz` (float | None): CPU frequency in MHz, if available.

        In addition, there is one float column per available application-level metric,
        named after the metric.
        """
        data_rows: list[dict[str, Any]] = []
        
        for app_event in self._periodic_log.app_events:
            data: dict[str, Any] = {
                "timestamp_sec" : app_event.timestamp_sec,
                "app" : app_event.application_name,
                "iid" : app_event.instance_id,
                "pid" : app_event.pid,
                "tid" : app_event.tid,
                "affinity" : app_event.affinity,
                "frequency_mhz" : app_event.frequency_mhz,
            }
            for metric, value in app_event.perf_events.items():
                data[metric] = value

            data_rows.append(data)

        return pd.DataFrame(data_rows)

    def get_system_metrics_dataframe(self) -> pd.DataFrame:
        """
        Returns a pandas DataFrame containing the periodic system-level events
        extracted from the periodic log.

        By default, the DataFrame has the following columns:

        - `timestamp_sec` (float): Timestamp in seconds.
        - `epoch` (int): Epoch number, derived from the unique timestamps in the system-level DataFrame.

        In addition, there is one float column per available system-level metric,
        named after the metric.
        """
        if not self._periodic_log.sys_events:
            raise ValueError("No system-level events found in the periodic log.")

        data_rows: list[dict[str, Any]] = []
        for sys_event in self._periodic_log.sys_events:
            data: dict[str, Any] = {
                "timestamp_sec": sys_event.timestamp_sec,
            }
            for metric, value in sys_event.perf_events.items():
                data[metric] = value

            data_rows.append(data)

        system_df = pd.DataFrame(data_rows)

        # Determine the epoch based on the unique timestamps in the system-level DataFrame
        timestamp_to_epoch: dict[float, int] = {
            timestamp: epoch
            for epoch, timestamp in enumerate(sorted(system_df["timestamp_sec"].unique()))
        }
        epoch_series: pd.Series = system_df["timestamp_sec"].map(timestamp_to_epoch)
        # Add 'epoch' column, after timestamp column (index 1)
        system_df.insert(1, "epoch", epoch_series)

        return system_df

    def get_temperature_dataframe(self) -> pd.DataFrame:
        """
        Returns a pandas DataFrame containing the periodic temperature events
        extracted from the periodic log.

        By default, the DataFrame has the following columns:

        - `timestamp_sec` (float): Timestamp in seconds.
        - `core_{core_id}` (float): Temperature in Celsius for each core, where `{core_id}` is the ID of the core.
        """
        temp_rows: list[dict[str, Any]] = []

        if not self._periodic_log.temp_events:
            raise ValueError("No temperature events found in the periodic log.")

        for temp_event in self._periodic_log.temp_events:
            data: dict[str, Any] = {
                "timestamp_sec": temp_event.timestamp_sec,
            }
            for core_id, temp in temp_event.core_temperatures.items():
                data[f"core_{core_id}"] = temp
            
            temp_rows.append(data)

        temp_df = pd.DataFrame(temp_rows)
        
        return temp_df

    @staticmethod
    def add_epoch_column(system_level_df: pd.DataFrame, target_df: pd.DataFrame) -> pd.DataFrame:
        """
        Returns a copy of the `target_df` DataFrame with an additional 'epoch' column,
        by mapping the timestamps in `target_df` to the corresponding epochs in `system_level_df`.
        """

        if 'epoch' in target_df.columns:
            raise ValueError("The target DataFrame already contains an 'epoch' column.")
        
        if system_level_df.empty or 'timestamp_sec' not in system_level_df.columns:
            raise ValueError("The system-level DataFrame is empty or does not contain a 'timestamp_sec' column.")

        if target_df.empty or 'timestamp_sec' not in target_df.columns:
            raise ValueError("The target DataFrame is empty or does not contain a 'timestamp_sec' column.")

        timestamp_to_epoch: dict[float, int] = {
            timestamp: epoch
            for epoch, timestamp in enumerate(sorted(system_level_df["timestamp_sec"].unique()))
        }

        target_out = target_df.copy()

        target_epochs: pd.Series = target_out["timestamp_sec"].map(timestamp_to_epoch)
        if target_epochs.isna().any():
            raise ValueError("Some target DataFrame timestamps have no matching system-level timestamp.")

        # Add 'epoch' column after timestamp column
        target_out.insert(1, "epoch", target_epochs.astype(int))

        return target_out