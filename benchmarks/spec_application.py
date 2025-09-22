from enum import Enum
import os
import subprocess
from benchmarks.application import Application
from core.procworker import get_pid_of_app
from config import SPECPBASE, SPEC_CONFIGFILE

class SpecApplication(Application):
    
    class InputSize(Enum):
        TEST = 'test'
        TRAIN = 'train'
        REF = 'ref'

    def __init__(self, application_package: str, input: InputSize = InputSize.REF, labels: list[str] = []) -> None:
        super().__init__(labels)
        self._application_package = application_package
        self._input = input

    def _set_environment(self):
        if "SPECBIN" not in os.environ:
            # Source shrc and capture environment variables
            command = f"cd {SPECPBASE} && source ./shrc && env"
            proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True, executable="/bin/bash")
            output, error = proc.communicate()

            # Parse output and update os.environ
            for line in output.decode().splitlines():
                if "=" in line:  # Check if line contains '='
                    key, value = line.split("=", 1)
                    os.environ[key] = value

    def _execute(self, cores: set[int] | None) -> None:
    
        self._set_environment()
        self._start_affinity = cores

        input_size = self._input.value
        app = self._application_package
        log_file = "/dev/null" # f"{app}.log"

        if cores is not None:
            affinity = ",".join([str(c) for c in cores])
            command = f"taskset -c {affinity} nice -n 0 runspec --iterations 1 --size {input_size} --action onlyrun --config {SPEC_CONFIGFILE} --noreportable {app} > {log_file}"
        else:
            command = f"runspec --iterations 1 --size {input_size} --action onlyrun --config {SPEC_CONFIGFILE} --noreportable {app} > {log_file}"
        

        subprocess.run(command, shell=True, env=os.environ)

    def get_pid(self) -> int | None:
        # Return cached pid if available
        if self._pid:
            return self._pid
        
        if pid := get_pid_of_app(self._application_package, self._start_affinity):
            self._pid = pid
            return pid
    
    def get_display_name(self) -> str:
        return f"{self._application_package}_{self._input.value}"