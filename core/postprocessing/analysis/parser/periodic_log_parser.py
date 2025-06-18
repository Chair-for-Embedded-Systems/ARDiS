import os
import re

class ParseException(Exception):
    pass

class SystemEvent():
    def __init__(self, event_line: str):
        try:
            self.timestamp = float(re.search(r"\[(\d+\.\d+)s\] SYSTEM:", event_line).group(1))
            self.energy_package = float(re.search(r"power/energy-pkg/ = ([\d\.]+)", event_line).group(1))
            self.energy_cores = float(re.search(r"power/energy-cores/ = ([\d\.]+)", event_line).group(1))
            self.energy_sys = float(re.search(r"power/energy-psys/ = ([\d\.]+)", event_line).group(1))
        except Exception as e:
            raise ParseException()
      

class ApplicationEvent():
    def __init__(self, event_line: str):
        try:        
            self.timestamp = float(re.search(r"\[(\d+\.\d+)s\] Core[s]?", event_line).group(1))
            
            if core := re.search(r"Core (\d+):", event_line):
                self.core_id = int(core.group(1))
            if cores := re.search(r"Cores (.*):", event_line):
                cores = cores.group(1).replace('[','').replace(']','').split(',')
                self.core_id = int(cores[0]) # Todo
            
            if pid := re.search(r"PID = (\d+)", event_line):
                self.pid = int(pid.group(1))
            else:
                self.pid = -1

            self.app_name = str(re.search(r"app = (\S+)", event_line).group(1))
            
            if "frequency = not-available" in event_line:
                self.frequency = -1
            if frequency := re.search(r"frequency = (\d+)", event_line):
                self.frequency = int(frequency.group(1))
            
            self.instructions = int(re.search(r"instructions = (\d+)", event_line).group(1))
            self.llc_loads = int(re.search(r"LLC-loads = (\d+)", event_line).group(1))
            self.llc_load_misses = int(re.search(r"LLC-load-misses = (\d+)", event_line).group(1))
            self.llc_stores = int(re.search(r"LLC-stores = (\d+)", event_line).group(1))
            self.llc_store_misses = int(re.search(r"LLC-store-misses = (\d+)", event_line).group(1))
            self.instructions = int(re.search(r"instructions = (\d+)", event_line).group(1))
            self.cycles = int(re.search(r"cycles = (\d+)", event_line).group(1))
            self.branch_misses = int(re.search(r"branch-misses = (\d+)", event_line).group(1))
            self.branches = int(re.search(r"branches = (\d+)", event_line).group(1))
        except Exception as e:
            raise ParseException()
        
class MappingEvent():
    def __init__(self, event_line: str):
        try:
            self.timestamp = float(re.search(r"\[(\d+\.\d+)s\] Current mapped cores:", event_line).group(1))
        
            mapping_list = str(re.search(r"cores: (.*)", event_line).group(1))
            mapping_list = mapping_list.replace("'",'').replace("[","").replace("]","")
            if len(mapping_list) == 0:
                mapping_list = []
            else:
                mapping_list = list(map(int, mapping_list.split(",")))

            self.mapping = mapping_list
        except Exception as e:
            raise ParseException()

class PeriodicCounterLog():
    def __init__(self, file_path: str, fail_on_corrupt_lines: bool = False):
        
        # Check if file exists
        if not os.path.exists(path=file_path):
            raise FileNotFoundError(f"Colud not find {file_path}")
        
        system_events: list[SystemEvent] = []
        application_events: list[ApplicationEvent] = []
        mapping_events: list[MappingEvent] = []

        with open(file_path, "r") as file:
            for line in [line.rstrip() for line in file]:
                try:
                    if "SYSTEM" in line:
                        system_events.append(SystemEvent(line))
                    if "app = " in line:
                        application_events.append(ApplicationEvent(line))
                    if "mapped cores" in line:
                        mapping_events.append(MappingEvent(line))

                except ParseException as pe:
                    # When muliple applications are running the log sometimes contains events with no perf data
                    # for applications that just finished
                    if fail_on_corrupt_lines:
                        raise Exception(f"Failed to parse line {line} in {file_path}")    
        
        self.system_events = system_events
        self.application_events = application_events
        self.mapping_events = mapping_events


def __test_parser():

    # Test system event parse
    example_system_event = "[0.75s] SYSTEM: power/energy-pkg/ = 2.79 | power/energy-cores/ = 1.72 | power/energy-psys/ = 6.63"
    system_event = SystemEvent(example_system_event)
    assert(system_event.timestamp == 0.75)
    assert(system_event.energy_package == 2.79)
    assert(system_event.energy_sys == 6.63)
    print("System event parse test: OK")

    # Test application event parse
    example_application_event = "[0.91s] Core 6: app = parsec-canneal | frequency = 2000 | instructions = 393537582 | LLC-loads = 51639 | LLC-load-misses = 21852 | LLC-stores = 1220126 | LLC-store-misses = 1160411 | cycles = 210079501 | branch-misses = 27276 | branches = 65040020"
    application_event = ApplicationEvent(example_application_event)
    assert(application_event.timestamp == 0.91)
    assert(application_event.core_id == 6)
    assert(application_event.app_name == "parsec-canneal")
    assert(application_event.frequency == 2000)
    assert(application_event.instructions == 393537582)
    assert(application_event.llc_loads == 51639)
    assert(application_event.llc_load_misses == 21852)
    assert(application_event.llc_stores == 1220126)
    assert(application_event.llc_store_misses == 1160411)
    assert(application_event.cycles == 210079501 )
    assert(application_event.branch_misses == 27276)
    assert(application_event.branches == 65040020)
    print("Application event parse test: OK")

    # Test mapping event parse
    example_mapping_event = "[2.76s] Current mapped cores: ['6', '2', '4', '8']"
    mapping_event = MappingEvent(example_mapping_event)
    assert(mapping_event.timestamp == 2.76)
    assert(mapping_event.mapping == [6, 2, 4, 8])
    print("Mapping event parse test: OK")

if __name__ == "__main__":
    __test_parser()