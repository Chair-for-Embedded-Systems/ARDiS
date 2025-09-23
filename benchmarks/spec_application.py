from enum import Enum
import os
import subprocess
from benchmarks.application import Application
from core.procworker import find_binary_in_exec_tree_recursively
from config import SPECPBASE, SPEC_CONFIGFILE, spec_apps

class SpecApplication(Application):
    
    class InputSize(Enum):
        TEST = 'test'
        TRAIN = 'train'
        REF = 'ref'

    def __init__(self, application_package: str, input: InputSize = InputSize.REF, labels: list[str] = []) -> None:
        super().__init__(labels)
        
        if not application_package in spec_apps:
            raise ValueError(f"Unknown SPEC application: {application_package}")
        
        self._application_package = application_package
        self._binary_name = application_package.replace('spec-', '')
        self._input = input
        self._process: subprocess.Popen[bytes] | None = None
        self._shell_pid: int | None = None

    def _set_environment(self):
        if "SPECBIN" not in os.environ:
            # Source shrc and capture environment variables
            command = f"cd {SPECPBASE} && source ./shrc && env"
            proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True, executable="/bin/bash")
            output, _ = proc.communicate()

            # Parse output and update os.environ
            for line in output.decode().splitlines():
                if "=" in line:  # Check if line contains '='
                    key, value = line.split("=", 1)
                    os.environ[key] = value

    def _execute(self, cores: set[int] | None) -> None:
    
        self._set_environment()
        self._start_affinity = cores

        input_size = self._input.value
        app = self._binary_name
        log_file = "/dev/null" # f"{app}.log"

        if cores is not None:
            affinity = ",".join([str(c) for c in cores])
            command = f"taskset -c {affinity} nice -n 0 runspec --iterations 1 --size {input_size} --action onlyrun --config {SPEC_CONFIGFILE} --noreportable {app} > {log_file}"
        else:
            command = f"runspec --iterations 1 --size {input_size} --action onlyrun --config {SPEC_CONFIGFILE} --noreportable {app} > {log_file}"
        

        self._process = subprocess.Popen(command, shell=True, env=os.environ)
        self._shell_pid = self._process.pid
        self._process.wait()

    def terminate(self) -> None:
        # Kill the application process if it is still running
        if self._pid is not None:
            try:
                os.kill(self._pid, 9)
            except ProcessLookupError:
                print(f"Process with PID {self._shell_pid} not found. It may have already terminated.")
            except Exception as e:
                print(f"An error occurred while trying to terminate the process: {e}")
        else:
            print("No running SPEC application to terminate.")

        # Kill the shell process if it is still running
        if self._process is not None and self._process.poll() is None:
            try:
                self._process.terminate() 
                self._process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._process.kill()
            except Exception as e:
                print(f"An error occurred while trying to terminate the shell process: {e}")

    def get_pid(self) -> int | None:
        
        # Return if a PID is already known and the process is still running
        if self._pid and os.path.exists(f"/proc/{self._pid}"):
            return self._pid
        
        # Try to find the PID in the process child tree of the shell process
        if self._shell_pid is None:
            return None
        else:
            self._pid = find_binary_in_exec_tree_recursively(self._binary_name, self._shell_pid)
            return self._pid
        
    def get_display_name(self) -> str:
        return f"{self._binary_name}-{self._input.value}"