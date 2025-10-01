import os
import subprocess
from ardis.benchmarks.application import Application
from ardis.config import system_cores

class BinaryApplication(Application):
    
    def __init__(self, start_command: str, labels: list[str] = []) -> None:
        super().__init__(labels)

        parts = start_command.split()
        binary_path = parts[0]
        arguments = parts[1:]

        # Check if binary exists
        if not os.path.exists(binary_path):
            raise FileNotFoundError
        
        self._binary_path = binary_path
        self._arguments = arguments
        self._binary_name = os.path.basename(binary_path)
        self._pid: int | None = None

    def _execute(self, cores: set[int] | None) -> None:
        # Build command
        cs_cores = ",".join([str(c) for c in cores]) if cores else f"0-{system_cores}"
        arguments = " ".join(self._arguments)
        command = f"taskset -c {cs_cores} {self._binary_path} {arguments}"
        
        # Start and get pid
        process = subprocess.Popen(args=command.split(" "), stderr=subprocess.PIPE, stdout=subprocess.DEVNULL)
        self._start_affinity = cores
        self._pid = process.pid
        
        # Block until executed
        process.wait()
    
    def terminate(self) -> None:
        # Terminates properly when ARDiS is interrupted, no need for extra handling
        pass

    def get_pid(self) -> int | None:
        return self._pid
    
    def get_display_name(self) -> str:
        return self._binary_name
