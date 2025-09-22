from enum import Enum
import os
import subprocess
import tempfile
from benchmarks.application import Application
from config import parsec_apps, system_cores, PARSECBASE, RUNTIME_TEMP
from core.procworker import get_pid_of_app

class ParsecApplication(Application):
    
    class InputSize(Enum):
        SIM_DEV = 'simdev'
        SIM_SMALL = 'simsmall'
        SIM_MEDIUM = 'simmedium'
        SIM_LARGE = 'simlarge'
        NATIVE = 'native'
        TEST = 'test'

    def __init__(self, application_package: str, threads: int = 1, input_size: InputSize = InputSize.NATIVE, labels: list[str] = []) -> None:
        """
        Parameters
        ----------
            - application_package: str 
                 Name of the package e.g `parsec.blackscholes`, `splash2.lu_cb` or `splash2x.water_spatial`
            - threads: int 
                Number of threads
            - input_size: InputSize
                
        """
        super().__init__(labels)
        
        # Validate parameters (Todo)
        benchmark, application_binary = application_package.split('.')[:2]
        if not application_package in parsec_apps:
            raise ValueError(f"{application_package} is not found on this system")

        self._package = application_package
        self._benchmark = benchmark
        self._binary_name = application_binary
        self._display_name = f"{application_package}-{threads}"
        self._threads = threads
        self._input_size = input_size

    @staticmethod
    def _set_environment():
        """Set parsec environment if it hasn't been done yet"""
        if "xxPARSECDIRxx" not in os.environ:

            command = f"cd {PARSECBASE} && source env.sh && env"
            process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True, executable="/bin/bash")
            output, _ = process.communicate()

            # Parse output and update os.environ
            for line in output.decode().splitlines():
                key, value = line.split("=", 1)
                os.environ[key] = value

    def _execute(self, cores: set[int] | None) -> None:
        
        self._set_environment()
        self._start_affinity = cores

        # If no cors are provided, default to all
        cs_cores = ",".join([str(c) for c in cores]) if cores else f"0-{system_cores}"
        
        # Each application gets her own runtime directory, this is important when running multiple instances
        run_dir = tempfile.mkdtemp(dir=RUNTIME_TEMP)
        log_file = "/dev/null" # f"{self._application}.log"
        
        command = f"taskset -c {cs_cores} nice -n 0 parsecmgmt -a run -i {self._input_size.value} -d {run_dir} -n {self._threads} -p {self._package} > {log_file}"
        
        subprocess.run(command, shell=True, executable="/bin/bash")
    
    def terminate(self) -> None:
        pass

    def get_pid(self) -> int | None:
        # Return cached pid if available
        if self._pid:
            return self._pid
        
        if pid := get_pid_of_app(self._binary_name, self._start_affinity):
            self._pid = pid
            return pid
        
    def get_display_name(self) -> str:
        return self._display_name
   