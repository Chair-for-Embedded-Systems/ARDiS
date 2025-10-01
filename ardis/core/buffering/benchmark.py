import random
from ardis.core.buffering.deque_based_event_buffer import DequeBasedEventBuffer
from ardis.core.buffering.event_buffer import EventBuffer
from ardis.config import periodic_app_level_events, periodic_system_wide_events
import time

def run():

    sample_size = 1000
    window_size = 10

    # Benchmark deque based buffer
    buffer = DequeBasedEventBuffer(capacity=window_size)
    elapsed_time_sec = _benchmark_buffer(buffer, sample_size, window_size)
    print(f"Deque based buffer ({sample_size} samples):  {elapsed_time_sec:.3f} sec")
    

def _benchmark_buffer(buffer: EventBuffer, sample_size: int, window_size: int) -> float:
    
    # Generate test data
    app_pid_events = [_generate_random_app_event for _ in range(sample_size)]
    sys_events = [_generate_random_sys_event for _ in range(sample_size)]
    
    # Run benchmark
    start = time.perf_counter()
    for app_event, sys_event in zip(app_pid_events, sys_events):
        # Push events to buffer
        buffer.push_pid_and_sys_events(
            app_events=app_event(),
            system_events=sys_event()
        )
        # Retrive last `window_size` events
        _ = buffer.get_system_metrics(window_size)
        _ = buffer.get_metrics_by_pid(window_size)
    
    # Return elapsed time
    end = time.perf_counter()
    return end - start
    

def _generate_random_app_event() -> dict[int, dict[str, int|float]]:
    
    random_pids: list[int] = [random.randint(1, 10000) for _ in range(8)]
    events: dict[int, dict[str, int|float]] = {}
    for pid in random_pids:
        pid_events: dict[str, int|float] = {event: 42 for event in periodic_app_level_events}
        events[pid] = pid_events
    
    return events

def _generate_random_sys_event() -> dict[str, int|float]:
    sys_events : dict[str, int|float] = {event: 42 for event in periodic_system_wide_events}
    return sys_events

if __name__ == "__main__":
    run()