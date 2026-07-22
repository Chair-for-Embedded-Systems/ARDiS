from abc import ABC, abstractmethod

class CoreTemperatureMonitor(ABC):
    
    @abstractmethod
    def sample_core_temperature(self) -> dict[int, float]:
        """
        Samples the current temperature of each core and returns a dictionary mapping core IDs to their respective temperatures.
        """
        raise NotImplementedError("sample_core_temperature method must be implemented by subclasses")
    
    def close(self) -> None:
        """
        Optional method to clean up resources when the monitor is no longer needed.
        Subclasses can override this method if they have specific cleanup tasks.
        """
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
