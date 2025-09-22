from enum import Enum
import os
import subprocess
from benchmarks.application import Application
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
        app = self._application_package
        log_file = "/dev/null" # f"{app}.log"

        if cores is not None:
            affinity = ",".join([str(c) for c in cores])
            command = f"taskset -c {affinity} nice -n 0 runspec --iterations 1 --size {input_size} --action onlyrun --config {SPEC_CONFIGFILE} --noreportable {app} > {log_file}"
        else:
            command = f"runspec --iterations 1 --size {input_size} --action onlyrun --config {SPEC_CONFIGFILE} --noreportable {app} > {log_file}"
        

        self._process = subprocess.Popen(command, shell=True, env=os.environ)
        self._shell_pid = self._process.pid
        self._process.wait()

    def get_pid(self) -> int | None:
        
        # Return if a PID is already known and the process is still running
        if self._pid and os.path.exists(f"/proc/{self._pid}"):
            return self._pid
        
        # Try to find the PID in the process child tree of the shell process
        if self._shell_pid is None:
            return None
        else:
            self._pid = self._find_binary_in_tree_recursively(self._shell_pid, self._application_package)
            return self._pid
    
    def _find_binary_in_tree_recursively(self, pid: int, binary_name: str) -> int | None:
        """
        Recursively search for a binary in the process tree starting from the given PID.
        Returns the PID of the found binary or None if not found.
        """
        try:
            with open(f"/proc/{pid}/task/{pid}/children", "r") as f:
                children = f.read().strip().split()
                for child_pid in children:
                    child_pid = int(child_pid)
                    executable_link = f"/proc/{child_pid}/exe"
                    
                    if os.path.islink(executable_link):
                        target_path = os.readlink(executable_link)
                        # Check if the target path contains the binary name
                        if binary_name in os.path.basename(target_path):
                            return child_pid

                    result = self._find_binary_in_tree_recursively(child_pid, binary_name)
                    if result is not None:
                        return result
        except Exception as _:
            return None
        
        return None
    
    def get_display_name(self) -> str:
        return f"{self._application_package}_{self._input.value}"