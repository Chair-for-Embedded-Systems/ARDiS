import glob
import os
import subprocess
import json
from timeit import default_timer as timer
from dataclasses import dataclass

@dataclass
class ResultPIDPolling:
    _pids: list[int]
    _tid_to_events: dict[int, dict[str, int | float]]
    _tid_to_app_name: dict[int, str]
    _tid_to_pid: dict[int, int]
    event_to_pct_running: dict[str, int]

    def get_events(self, aggregate_by_pid: bool) -> dict[int, dict[str, int | float]]:
        
        if not self._tid_to_events:
            return {}
        
        if not aggregate_by_pid:
            return self._tid_to_events

        events = next(iter(self._tid_to_events.values()))
        events = events.keys()
        pid_to_event: dict[int, dict[str, float | int]] = {pid: {event: 0 for event in events} for pid in self._pids}
        for tid, events in self._tid_to_events.items():
            for event, value in events.items():
                pid = self._tid_to_pid[tid]
                try:
                    pid_to_event[pid][event] += value
                except KeyError as ke:
                    print(pid_to_event)
                    print(self.event_to_pct_running)
        
        return pid_to_event
    
    def get_app_name(self, thread_id: int) -> str:
        return self._tid_to_app_name.get(thread_id, "unknown")
        
    
@dataclass
class ResultCorePolling:
    _core_to_events: dict[int, dict[str, int|float]]
    event_to_pct_running: dict[str, int]

    def get_events(self) -> dict[int, dict[str, int|float]]:
        return self._core_to_events

class PollerAppLevel:
    
    def __init__(self, sampling_rate_sec: float, events: list[str]):
        self.__sampling_rate_sec = sampling_rate_sec
        self.__events = events

        # Perf uses the core_id instead of the logical id in some cases (e.g with -j --per-core in poll_by_core)
        # Since this mapping does not change we can cache it at the initialisation of this poller
        logical_cores = [os.path.basename(d) for d in glob.glob(os.path.join("/sys/devices/system/cpu/", "cpu[0-9]*")) if os.path.isdir(d)]
        logical_cores = [int(core.replace('cpu','')) for core in logical_cores]

        core_id_to_logical_core : dict[int, list[int]] = {}
        for logic_core in logical_cores:
            with open(f"/sys/devices/system/cpu/cpu{logic_core}/topology/core_id", 'r') as f:
                core_id = int(f.read().strip())
                if core_id in core_id_to_logical_core:
                    core_id_to_logical_core[core_id].append(logic_core)
                else:
                    core_id_to_logical_core[core_id] = [logic_core]
        
        self.__physical_to_logical_core = core_id_to_logical_core


    def poll_by_pid(self, pids: list[int]) -> ResultPIDPolling:

        # Get thread ids (tids) for each passed pid
        pid_to_tids = {}
        for pid in pids:
            try:
                # Fails when the process ends or an invalid pid has been passed
                tids = [int(tid) for tid in os.listdir(f"/proc/{pid}/task")]
                pid_to_tids[pid] = tids
            except FileNotFoundError:
                continue
        
        # Update valid pids
        pids = list(pid_to_tids.keys())

        tid_to_pid = {tid: pid for pid, tids in pid_to_tids.items() for tid in tids}
        tids = set(tid_to_pid.keys())


        # Run perf command
        perf_pid_command = f"perf stat -j --per-thread --pid {','.join([str(pid) for pid in pids])} -e {','.join(self.__events)} sleep {self.__sampling_rate_sec}"
        #start = timer()
        process = subprocess.Popen(args=perf_pid_command.split(' '), stderr=subprocess.PIPE)
        _, output = process.communicate() # perf outputs on stderr 
        #print(f"Perf command for pid tracking: {(timer()-start)*1000:2f}")
        

        events: dict[int, dict[str, int|float]] = {tid: {event: 0 for event in self.__events} for tid in tids}
        tid_names: dict[int, str] = {}
        events_pct_running: dict[str, int] = {}

        for line in output.splitlines():
            try:
                perf_stat_event = json.loads(line)
            except json.JSONDecodeError as e:
                continue
            
            app_name, tid = str(perf_stat_event['thread']).split('-')[:2]
            tid = int(tid)
            tid_names[tid] = app_name
            
            event = str(perf_stat_event['event']).replace("cpu_core","").replace("cpu_atom","").replace("/","")
            
            counter_value = str(perf_stat_event['counter-value'])
            if '<not counted>' in counter_value or '<not supported>' in counter_value:
                continue
            if '.' in counter_value:
                counter_value = counter_value.split('.')[0]
            counter_value = int(counter_value)

            # The tids for each pid are fetched before running the perf command.
            # If any new thread spawns during the measurement, it will not be present in the dictionaries.
            # It could be added on-demand, but for now it simply gets skipped (gets included in the next sampling epoch; if still running)
            # The other case where a tid is not in the perf result because it finished before, is covered by the preinitialized event dict
            if not tid in tid_to_pid:
                continue

            events[tid][event] += counter_value

            if not event in events_pct_running:
                events_pct_running[event] = int(perf_stat_event['pcnt-running'])
        
        return ResultPIDPolling(pids, events, tid_names, tid_to_pid, events_pct_running)

    def poll_by_core(self, cores: list[int]) -> ResultCorePolling:
        
        command = f"perf stat -j --per-core -C {','.join([str(core) for core in cores])} -e {','.join(self.__events)} sleep {self.__sampling_rate_sec}"
        #start = timer()
        process = subprocess.Popen(args=command.split(' '), stderr=subprocess.PIPE)
        _, output = process.communicate() # perf outputs on stderr 
        #print(f"Perf command for core tracking: {(timer()-start)*1000:2f}")
        events: dict[int, dict[str, int|float]] = {core: {event: 0 for event in self.__events} for core in cores}
        
        active_logic_cores = {}
        for physical_core, logical_cores in self.__physical_to_logical_core.items():
            active_cores = [logic_core for logic_core in logical_cores if logic_core in cores]
            active_logic_cores[physical_core] = active_cores

        events_pct_running: dict[str, int] = {}

        for line in output.splitlines():
            try:
                perf_stat_event = json.loads(line)
            except json.JSONDecodeError as e:
                continue
            event = str(perf_stat_event['event']).replace("cpu_core","").replace("cpu_atom","").replace("/","")
            
            counter_value = str(perf_stat_event['counter-value'])
            if '<not counted>' in counter_value or '<not supported>' in counter_value:
                continue
            if '.' in counter_value:
                counter_value = counter_value.split('.')[0]
            counter_value = int(counter_value)

            socket, die, core = str(perf_stat_event['core']).split('-')[:3]
            core = int(core.replace('C',''))

            # Logical cores can share the same physical core e.g due to Hyper-Threading
            # Perf can only monitor physical cores, therefore we assign the metrics of a physical core to multiple logic cores.
            # If multiple logic cores of the same physical core are monitored, the metrics get distributed evenly.            
            counter_value = int(counter_value / len(active_logic_cores[core]))
            for logical_core in active_logic_cores[core]:
                events[logical_core][event] = counter_value
            
            if not event in events_pct_running:
                events_pct_running[event] = int(perf_stat_event['pcnt-running'])
        
        return ResultCorePolling(events, events_pct_running)