import json
import signal
import subprocess

from dataclasses import dataclass

@dataclass
class ResultSystemPolling:
    events: dict[str, float|int]
    pct_running: dict[str, int]

class PollerSystemLevel:
    
    def __init__(self, sampling_rate_sec: float, periodic_events: list[str], one_shot_events: list[str]):
        self.__sampling_rate_sec = sampling_rate_sec
        self.__periodic_events = periodic_events
        self.__one_shot_events = one_shot_events
        self.__running_one_shot = False
        self.__process_one_shot = None

    def poll(self) -> ResultSystemPolling:
        """
        Runs a perf command to collect periodic-system-wide metrics and returns the result.
        Blocks for `sampling_rate_sec` seconds, which is defined in the constructor.
        
        """
        command = f"perf stat -a -j -e {','.join(self.__periodic_events)} sleep {self.__sampling_rate_sec}"
        result = subprocess.run(command.split(' '), capture_output=True, text=True)
        output = result.stderr # perf outputs on stderr
        
        return self.__parse_events(output, self.__periodic_events)
   
    def poll_one_shot(self) -> ResultSystemPolling:
        """
        Runs and returns the result of the one-shot-system wide perf command. 
        This call is blocking until `stop_one_shot()` gets called from another thread.
        """
        if self.__running_one_shot:
            raise Exception("One-shot process is already running, call stop_one_shot first")

        command = f"perf stat -a -j -e {','.join(self.__one_shot_events)}"
        
        process = subprocess.Popen(args=command.split(' '), stderr=subprocess.PIPE)
        self.__process_one_shot = process
        self.__running_one_shot = True
    
        _, stderr = process.communicate() 
        output = stderr.decode() # perf outputs on stderr
        
        return self.__parse_events(output, self.__one_shot_events)
        
    def stop_one_shot(self):
        """
        Stops the one-shot-system-wide collection of data using perf.
        If a thread was blocked while running `poll_one_shot()`, it gets released
        """
        if self.__running_one_shot and self.__process_one_shot:
            self.__process_one_shot.send_signal(sig=signal.SIGINT)
            self.__running_one_shot = False
        else:
            print(f"No one-shot process is running")

    def __parse_events(self, input: str, perf_events: list[str]) -> ResultSystemPolling:
        events: dict[str, float] = {event: 0.0 for event in perf_events}
        events_pct_running: dict[str, int] = {event: 0 for event in perf_events}

        for line in input.splitlines():
            try:
                perf_stat_event = json.loads(line)
            except json.JSONDecodeError as e:
                break
            event = str(perf_stat_event["event"])
            if "cpu_core" in event or "cpu_atom" in event:
                event = event.replace("cpu_core/","").replace("cpu_atom/","").replace("/","")
            counter_value = float(perf_stat_event["counter-value"])
            events[event] += counter_value
            events_pct_running[event] = int(perf_stat_event['pcnt-running'])
        
        return ResultSystemPolling(events, events_pct_running)