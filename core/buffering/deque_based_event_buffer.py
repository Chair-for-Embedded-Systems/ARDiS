import copy
import threading
from threading import Lock
from core.buffering.event_buffer import EventBuffer
from collections import deque

class DequeBasedEventBuffer(EventBuffer):
    def __init__(self, capacity: int | None):
        self.__capacity = capacity
        self.__pid_event_deque: deque[dict[int, dict[str, int | float]]] = deque(maxlen=capacity)
        self.__core_event_deque: deque[dict[int, dict[str, int | float]]] = deque(maxlen=capacity)
        self.__sys_event_deque: deque[dict[str, int | float]] = deque(maxlen=capacity)
        self.__lock = threading.Lock()

    def push_core_and_sys_events(
        self, app_events: dict[int, dict[str, int | float]],
        system_events: dict[str, int | float]
    ) -> None:
        with self.__lock:
            self.__core_event_deque.append(app_events)
            self.__sys_event_deque.append(system_events)
    
    def push_pid_and_sys_events(
        self, 
        app_events: dict[int, dict[str, int | float]],
        system_events: dict[str, int | float]
    ) -> None:
        with self.__lock:
            self.__pid_event_deque.append(app_events)
            self.__sys_event_deque.append(system_events)

    def get_metrics_by_core(self, n: int) -> list[dict[int, dict[str, float | int]]]:
        if self.__capacity and n > self.__capacity:
            raise ValueError(f"n({n}) is larger than the buffer size ({self.__capacity})")
        window = min(n, len(self.__core_event_deque))
        return list(self.__core_event_deque)[-window:]
    
    def get_metrics_by_pid(self, n) -> list[dict[int, dict[str, float| int]]]:
        if self.__capacity and n > self.__capacity:
            raise ValueError(f"n({n}) is larger than the buffer size ({self.__capacity})")
        window = min(n, len(self.__pid_event_deque))
        return list(self.__pid_event_deque)[-window:]
    
    def get_system_metrics(self, n: int) -> list[dict[str, int | float]]:
        if self.__capacity and n > self.__capacity:
            raise ValueError(f"n({n}) is larger than the buffer size ({self.__capacity})")
        window = min(n, len(self.__sys_event_deque))
        return list(self.__sys_event_deque)[-window:]
    
    def get_metrics_for_pid(self, pid: int, n: int) -> list[dict[str, int | float]]:
        if n <= 0:
            return []
        if self.__capacity and n > self.__capacity:
            raise ValueError(f"n({n}) is larger than the buffer size ({self.__capacity})")
        
        window = min(n, len(self.__pid_event_deque))
        output = []
        for window in list(self.__pid_event_deque)[-window:]:
            for p, events in window.items():
                if p == pid:
                    output.append(events)
        return output
    
    def get_metrics_for_core(self, core_id: int, n: int) -> list[dict[str, int | float]]:
        
        if n <= 0:
            return []
        if self.__capacity and n > self.__capacity:
            raise ValueError(f"n({n}) is larger than the buffer size ({self.__capacity})")
        window = min(n, len(self.__core_event_deque))
        output = []
        for w in list(self.__core_event_deque)[-window:]:
            for core, events in w.items():
                if core == core_id:
                    output.append(events)
        return output
    
    def get_lock(self) -> Lock:
        return self.__lock
    
import unittest
class TestDequeBasedEventBuffer(unittest.TestCase):
    
    def test_basic_insertion_core(self):
        buffer = DequeBasedEventBuffer(10)
        buffer.push_core_and_sys_events(
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
        self.assertEqual(buffer.get_metrics_for_core(core_id=-1,n=1), []) # invalid core
        self.assertEqual(len(buffer.get_metrics_for_core(core_id=1,n=5)), 1) # requested window size > buffer content
        self.assertEqual(len(buffer.get_metrics_for_core(core_id=1,n=0)), 0) # requested window size == 0

    def test_basic_insertion_pid(self):
        buffer = DequeBasedEventBuffer(10)
        buffer.push_pid_and_sys_events(
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
        self.assertEqual(buffer.get_metrics_for_pid(pid=-1,n=1), []) # invalid pid
        self.assertEqual(len(buffer.get_metrics_for_pid(pid=42,n=5)), 1) # requested window size > buffer content
        self.assertEqual(len(buffer.get_metrics_for_pid(pid=42,n=0)), 0) # requested window size == 0

    def test_multi_insertion(self):
        buffer = DequeBasedEventBuffer(10)
        buffer.push_core_and_sys_events(
            app_events={
                0: {"instructions": 0},
                2: {"instructions": 0}
            },
            system_events={}
        )
        buffer.push_core_and_sys_events(
            app_events={
                0: {"instructions": 42},
                2: {"instructions": 20}
            },
            system_events={}
        )
        core_event_trace = buffer.get_metrics_for_core(core_id=0, n=2)
        instructions = [events["instructions"] for events in core_event_trace]
        self.assertEqual(instructions, [0, 42])
        

if __name__ == "__main__":
    unittest.main()