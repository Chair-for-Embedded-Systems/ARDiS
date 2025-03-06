import os
import re


class ExecutionLog():
    
    def __init__(self, file_path: str):
        if not os.path.exists(path=file_path):
            print(f"{file_path} does not exist")
            return

        with open(file_path, 'r') as file:
            for line in [line.rstrip() for line in file]:
                if "Total time elapsed (perf)=" in line:
                    self.__total_execution_time_sec = float(re.search(r'Total time elapsed \(perf\)= (\d+\.\d+)', line).group(1))
                if "Total instructions executed =" in line:
                    self.__total_instructions_executed = int(re.search(r'Total instructions executed = (\d+)', line).group(1))
                if "Total energy consumed (perf)=" in line:
                    self.__total_energy_consumption = float(re.search(r'Total energy consumed \(perf\)= (\d+\.\d+)', line).group(1))

    def get_total_execution_time(self) -> float:
        return self.__total_execution_time_sec
    
    def get_total_instruction(self) -> int:
        return self.__total_instructions_executed
    
    def get_total_energy_usage(self) -> float:
        return self.__total_energy_consumption
    
    def get_efficiency_ipj(self) -> float:
        return self.__total_instructions_executed / self.__total_energy_consumption
    

def __test_parser():
    import tempfile
    
    test_file = (
            "Total execution time of experiment = 72.3s\n"
            "Total instructions executed = 1323128227442\n"
            "Total energy consumed (perf)= 4654.71 Joules\n"
            "Total time elapsed (perf)= 72.28 seconds\n"
        )
    
    fd, path = tempfile.mkstemp()
    with os.fdopen(fd, 'w') as f:
        f.writelines(test_file)
    
    try:
        log = ExecutionLog(path)
        assert(log.get_total_execution_time() == 72.28)
        assert(log.get_total_instruction() == 1323128227442)
        assert(log.get_total_energy_usage() == 4654.71)
        print("Execution log parse test: OK")
    except Exception as e:
        print("Execution log parse test: Failed")
    
    if os.path.isfile(path):
        os.remove(path)
    

if __name__ == "__main__":
    __test_parser()