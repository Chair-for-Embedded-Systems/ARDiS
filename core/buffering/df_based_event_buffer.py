from core.buffering.event_buffer import EventBuffer
import pandas as pd

class DataFrameBasedEventBuffer(EventBuffer):
    """
    This class implements an EventBuffer with pandas dataframes as backend
    """
    WINDOW_INDEX_COLUMN = 'window_index'
    CORE_COLUMN = 'core'
    PID_COLUMN = 'pid'

    def __init__(self) -> None:
        self.__core_event_buffer = pd.DataFrame()
        self.__pid_event_buffer = pd.DataFrame()
        self.__system_event_buffer = pd.DataFrame()
        self.__app_event_counter = 0
        self.__system_event_counter = 0

    # [Before transposing]
    # (index)   core_x   core_y
    # event_1
    # event_2
    # event_3
    #
    # [After transposing]
    # (index)   event_1   event_2   event_3
    # core_x
    # core_y

    def push_core_events(
        self,
        app_events: dict[int, dict[str, int | float]],
        system_events: dict[str, int | float]
    ) -> None:
        
        df = pd.DataFrame(app_events).transpose()
        df[self.WINDOW_INDEX_COLUMN] = self.__app_event_counter
        df[self.CORE_COLUMN] = df.index
        self.__core_event_buffer = pd.concat([self.__core_event_buffer, df])
        self.__app_event_counter += 1

        self.__push_system_events(system_events)
    
    def push_pid_events(
        self, 
        app_events: dict[int, dict[str, int | float]],
        system_events: dict[str, int | float]
    ) -> None:
        df = pd.DataFrame(app_events).transpose()
        df[self.WINDOW_INDEX_COLUMN] = self.__app_event_counter
        df[self.PID_COLUMN] = df.index
        self.__pid_event_buffer = pd.concat([self.__pid_event_buffer, df])
        self.__app_event_counter += 1

        self.__push_system_events(system_events)
    
    def __push_system_events(self, system_events: dict[str, int | float]):
        df = pd.DataFrame({k: [v] for k,v in system_events.items()})
        df[self.WINDOW_INDEX_COLUMN] = self.__system_event_counter
        self.__system_event_buffer = pd.concat([self.__system_event_buffer, df])
        self.__system_event_counter += 1

    def get_metrics_for_core(self, core_id: int, n: int) -> list[dict[str, int | float]]:
        # Calculate window of interest
        window_start = max(0,self.__app_event_counter - n)
        window_end = self.__app_event_counter

        # Select relevant rows from the buffer (matching core index and in window)
        eb = self.__core_event_buffer
        if eb.empty:
            return list()
        relevant_events = eb[
            (eb[self.CORE_COLUMN] == core_id) &
            (eb[self.WINDOW_INDEX_COLUMN] < window_end) &
            (eb[self.WINDOW_INDEX_COLUMN] >= window_start)
        ]

        # Convert dataframe to dict
        output: list[dict[str, int|float]] = list()
        for _, row in relevant_events.iterrows():
            event = row.drop([self.CORE_COLUMN, self.WINDOW_INDEX_COLUMN]).to_dict()
            output.append(event)

        return output
    
    def get_metrics_for_pid(self, pid: int, n: int) -> list[dict[str, int | float]]:
        # Calculate window of interest
        window_start = max(0,self.__app_event_counter - n)
        window_end = self.__app_event_counter

         # Select relevant rows from the buffer (matching pid and in window)
        eb = self.__pid_event_buffer
        if eb.empty:
            return list()
        relevant_events = eb[
            (eb[self.PID_COLUMN] == pid) &
            (eb[self.WINDOW_INDEX_COLUMN] < window_end) &
            (eb[self.WINDOW_INDEX_COLUMN] >= window_start)
        ]
        # Convert dataframe to dict
        output: list[dict[str, int|float]] = list()
        for _, row in relevant_events.iterrows():
            event = row.drop([self.PID_COLUMN, self.WINDOW_INDEX_COLUMN]).to_dict()
            output.append(event)

        return output
    
    def get_system_metrics(self, n: int) -> list[dict[str, int | float]]:
        # Calculate window of interest
        window_start = max(0,self.__system_event_counter - n)
        window_end = self.__system_event_counter
         
        # Select relevant rows from the buffer (in window)
        eb = self.__system_event_buffer
        relevant_events = eb[
            (eb[self.WINDOW_INDEX_COLUMN] < window_end) &
            (eb[self.WINDOW_INDEX_COLUMN] >= window_start)
        ]
        # Convert dataframe to dict
        output: list[dict[str, int|float]] = list()
        for _, row in relevant_events.iterrows():
            event = row.drop([self.WINDOW_INDEX_COLUMN]).to_dict()
            output.append(event)
        
        return output
    
    def get_metrics_by_core(self, n: int) -> list[dict[int, dict[str, float | int]]]:
        if self.__core_event_buffer.empty:
            return []
        window_start = max(0, self.__app_event_counter - n)
        window_end = self.__app_event_counter
        
        eb = self.__core_event_buffer
        relevant_events = eb[
            (eb[self.WINDOW_INDEX_COLUMN] < window_end) &
            (eb[self.WINDOW_INDEX_COLUMN] >= window_start)
        ]
        output = []
        for _, data_in_window in relevant_events.groupby(self.WINDOW_INDEX_COLUMN):
            data_in_window = data_in_window.drop(self.WINDOW_INDEX_COLUMN, axis=1)
            core_to_events = data_in_window.set_index(self.CORE_COLUMN).to_dict(orient='index')
            output.append(core_to_events)

        return output
    
    def get_metrics_by_pid(self, n: int):
        if self.__pid_event_buffer.empty:
            return []
        window_start = max(0, self.__app_event_counter - n)
        window_end = self.__app_event_counter
        
        eb = self.__pid_event_buffer
        relevant_events = eb[
            (eb[self.WINDOW_INDEX_COLUMN] < window_end) &
            (eb[self.WINDOW_INDEX_COLUMN] >= window_start)
        ]
        output = []
        for _, data_in_window in relevant_events.groupby(self.WINDOW_INDEX_COLUMN):
            data_in_window = data_in_window.drop(self.WINDOW_INDEX_COLUMN, axis=1)
            core_to_events = data_in_window.set_index(self.PID_COLUMN).to_dict(orient='index')
            output.append(core_to_events)

        return output
    
import unittest
class TestDataFrameBasedEventBuffer(unittest.TestCase):
    
    def test_basic_insertion_core(self):
        buffer = DataFrameBasedEventBuffer()
        buffer.push_core_events(
            app_events={
                1 : {"inst": 10, "cycles": 20}, 
                2 : {"inst": 20, "cycles": 40}
            },
            system_events={ "power_system" : 100, "power_core": 10, "power_package": 20}
        )
        # Check if basic insertion works (app events)
        self.assertEqual(buffer.get_metrics_for_core(core_id=1,n=1)[-1]["inst"], 10)
        self.assertEqual(buffer.get_metrics_for_core(core_id=1,n=1)[-1]["cycles"], 20)
        self.assertEqual(buffer.get_metrics_for_core(core_id=2,n=1)[-1]["inst"], 20)
        self.assertEqual(buffer.get_metrics_for_core(core_id=2,n=1)[-1]["cycles"], 40)
        # Check if basic insertion works (system events)
        self.assertEqual(buffer.get_system_metrics(n=1)[-1]["power_system"],100)
        self.assertEqual(buffer.get_system_metrics(n=1)[-1]["power_core"],10)
        # Check edge cases
        self.assertEqual(buffer.get_metrics_for_core(core_id=-1,n=1), [])
        self.assertEqual(len(buffer.get_metrics_for_core(core_id=1,n=5)), 1)
        self.assertEqual(len(buffer.get_metrics_for_core(core_id=1,n=0)), 0)

    def test_basic_insertion_pid(self):
        buffer = DataFrameBasedEventBuffer()
        buffer.push_pid_events(
            app_events={
                1 :  {"inst": 10, "cycles": 20}, 
                42 : {"inst": 20, "cycles": 40}
            },
            system_events={ "power_system" : 100, "power_core": 10, "power_package": 20}
        )
        # Check basic insertion (application events)
        self.assertEqual(buffer.get_metrics_for_pid(pid=1,n=1)[-1]["inst"], 10)
        self.assertEqual(buffer.get_metrics_for_pid(pid=1,n=1)[-1]["cycles"], 20)
        self.assertEqual(buffer.get_metrics_for_pid(pid=42,n=1)[-1]["inst"], 20)
        self.assertEqual(buffer.get_metrics_for_pid(pid=42,n=1)[-1]["cycles"], 40)
        # Check basic insertion (system events)
        self.assertEqual(buffer.get_system_metrics(n=1)[-1]["power_system"],100)
        self.assertEqual(buffer.get_system_metrics(n=1)[-1]["power_core"],10)
        # Check edge cases
        self.assertEqual(buffer.get_metrics_for_pid(pid=-1,n=1), [])
        self.assertEqual(len(buffer.get_metrics_for_pid(pid=42,n=5)), 1)
        self.assertEqual(len(buffer.get_metrics_for_pid(pid=42,n=0)), 0)

    def test_multi_insertion(self):
        buffer = DataFrameBasedEventBuffer()
        buffer.push_core_events(
            app_events={
                0: {"instructions": 0},
                2: {"instructions": 0}
            },
            system_events={}
        )
        buffer.push_core_events(
            app_events={
                0: {"instructions": 10},
                2: {"instructions": 20}
            },
            system_events={}
        )
        print(buffer.get_metrics_by_core(2))

if __name__ == "__main__":
    unittest.main()