from enum import Enum
import os
import subprocess
import tempfile
from benchmarks.application import Application
from config import parsec_apps, system_cores

PARSECBASE = "/home/uhqql/parsec-3.0/"

class ParsecApplication(Application):
    
    class InputSize(Enum):
        SIM_DEV = 'simdev'
        SIM_SMALL = 'simsmall'
        SIM_MEDIUM = 'simmedium'
        SIM_LARGE = 'simlarge'
        NATIVE = 'native'
        TEST = 'test'

    def __init__(self, application_package: str, threads: int, input_size: InputSize) -> None:
        """
        Parameters
        ----------
            - application_package: str 
                 Name of the package e.g `parsec.blackscholes`, `splash2.lu_cb` or `splash2x.water_spatial`
            - threads: int 
                Number of threads
            - input_size: InputSize
                
        """
        super().__init__()
        
        # Validate parameters (Todo)
        benchmark, application_binary = application_package.split('.')[:2]
        #if not application_package in parsec_apps:
        #    raise ValueError(f"{application_package} is not found on this system")

        self._package = application_package
        self._benchmark = benchmark
        self._binary_name = application_binary
        self._display_name = f"{application_package}-{threads}"
        self._threads = threads
        self._input_size = input_size
        
        self._start_cores: set[int] | None = None
        self._pid: int | None = None


    @classmethod
    def from_app_string(cls, app_string: str):
        app = ""
        threads = 1
        input_size = cls.InputSize.NATIVE
        return ParsecApplication(app, threads, input_size)


    @staticmethod
    def _set_environment():
        """Set parsec environment if it hasn't been done yet"""
        if "xxPARSECDIRxx" not in os.environ:
            
            working_directory = os.getcwd()
            os.chdir(PARSECBASE)
            
            env_script_path = os.path.join(PARSECBASE, "env.sh")
            command = f"source {env_script_path} && env"
            process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True, executable="/bin/bash")
            output, error = process.communicate()

            # Parse output and update os.environ
            for line in output.decode().splitlines():
                key, value = line.split("=", 1)
                os.environ[key] = value
            
            os.chdir(working_directory)

    def execute(self, cores: set[int] | None) -> None:
        
        self._set_environment()
        self._start_cores = cores

        # If no cors are provided, default to all
        affinity = ",".join([str(c) for c in cores]) if cores else f"0-{system_cores}"
        
        # Each application gets her own runtime directory
        # This is important when having multiple instances
        run_dir = tempfile.mkdtemp()
        log_file = "/dev/null" # f"{self._application}.log"

        
        command = f"taskset -c {affinity} nice -n 0 parsecmgmt -a run -i {self._input_size.value} -d {run_dir} -n {self._threads} -p {self._package} > {log_file}"
        #command = f"parsecmgmt -a run -i {input_size} -n 1 -p {app}"
        print("Starting")
        subprocess.run(command, shell=True, executable="/bin/bash")
        print("Finishing")
    
    def get_pid(self) -> int | None:
        # Return cached pid if available
        if self._pid:
            return self._pid
        
        # Find all pids with this application name
        command = f"pgrep {self._binary_name}"
        p = subprocess.run(command.split(" "), capture_output=True)
        pid_string = str(p.stdout.decode())
        
        # No pids found
        if len(pid_string) == 0:
            return None
        
        # Check affinity of each pid to find correct app in multi-instance scenarios
        pids = [int(p) for p in pid_string.split("\n") if p]
        pid_to_affinity = self.poll_affinity(set(pids))
        for pid, affinity in pid_to_affinity.items():
            if affinity == self._start_cores:
                self._pid = pid
                return pid
        
        print(f"{self._binary_name} has probably not started!")
        
    def get_display_name(self) -> str:
        return self._display_name

    @staticmethod
    def poll_affinity(pids: set[int]) -> dict[int, set[int]]:
        """
        Returns the affinity as list of allowed logical cores for the given set of pid's.
        """
        output: dict[int, set[int]] = {}
        for pid in pids:
            try:
                with open(f"/proc/{pid}/status", 'r') as f:
                    for line in f:
                        if "Cpus_allowed:" in line:
                            hex_mask = line.split(':')[1]
                            bin_mask = bin(int(hex_mask, 16))[2:]
                            bin_mask = bin_mask.zfill(len(hex_mask)*4)
                            bin_mask = bin_mask[::-1]
                            affinity = [core for core,bit in enumerate(bin_mask) if bit == '1']
                            output[pid] = set(affinity)
                            break
            except FileNotFoundError as fe:
                output[pid] = set()
                continue
    
        return output

if __name__ == "__main__":
    import threading
    import time
    

    blackscholes_a = ParsecApplication("parsec.blackscholes", 2, ParsecApplication.InputSize.NATIVE)
    blackscholes_b = ParsecApplication("parsec.blackscholes", 2, ParsecApplication.InputSize.NATIVE)
    
    t_1 = threading.Thread(target=blackscholes_a.execute, args=([{2, 4}]))
    t_2 = threading.Thread(target=blackscholes_b.execute, args=([{6, 8}])).start()
    t_1.start()
    
    app_to_pid = {blackscholes_a: None, blackscholes_b: None}

    while blackscholes_a.get_pid() is None and t_1.is_alive():
        time.sleep(0.5)
        print("PID not detected")
    
    print(blackscholes_a.get_pid())